from __future__ import annotations

import logging
from json import JSONDecodeError

from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.orm import Session

from app.access.models import RuntimeTrainingConfig
from app.domain.errors import LLMProviderConfigurationError, PersonaGenerationError
from app.domain.models import PersonaGenerationInput, PersonaProfile
from app.domain.persona_generation import UniversalFakePersonaGenerator
from app.domain.scenarios import get_scenario
from app.domain.seed_config import PersonaSeedConfig
from app.domain.token_counter import TokenCountedResult
from app.application.seed_prompt_renderer import SeedPromptRenderer
from app.infrastructure.config import Settings, is_fake_fallback_allowed
from app.infrastructure.persona_generator_client import (
    FakePersonaGeneratorClient,
    PersonaGenerationBusinessValidationError,
    PersonaGeneratorClient,
    StructuredPersonaGeneratorClient,
    validate_generated_persona,
)
from app.infrastructure.llm_client import LLMClientError
from app.prompts.schemas import load_persona_generator_prompt

logger = logging.getLogger(__name__)

_seed_prompt_renderer = SeedPromptRenderer()


class PersonaGenerationService:
    def __init__(
        self,
        db_session: Session,
        *,
        settings: Settings,
        fallback_generator: UniversalFakePersonaGenerator | None = None,
        client_factory: PersonaGeneratorClientFactory | None = None,
    ) -> None:
        """Keep request-scoped dependencies needed for authenticated session startup."""
        self._session = db_session
        self._settings = settings
        self._fallback_generator = fallback_generator or UniversalFakePersonaGenerator(settings.persona_random_seed)
        self._client_factory = client_factory or PersonaGeneratorClientFactory(settings=settings)

    def generate_for_training_config(
        self,
        *,
        training_config: RuntimeTrainingConfig,
        scenario_id: str | None = None,
    ) -> TokenCountedResult[PersonaProfile]:
        """Generate a hidden PersonaProfile from training-config business context."""
        del self._session
        input_payload = self.build_input(training_config=training_config, scenario_id=scenario_id)
        client = self._build_client(training_config=training_config, input_payload=input_payload)
        try:
            result = client.generate_persona(input_payload)
            persona = validate_generated_persona(result.value, input_payload)
        except (
            JSONDecodeError,
            LLMClientError,
            PydanticValidationError,
            PersonaGenerationBusinessValidationError,
            TimeoutError,
        ) as error:
            raise PersonaGenerationError("Persona generator failed to produce a valid profile.") from error
        logger.info(
            "persona_generated training_config_id=%s client_account_id=%s provider=%s persona_id=%s input_tokens=%s output_tokens=%s",
            training_config.id,
            training_config.client_account_id,
            self._provider_label(client),
            persona.id,
            result.input_tokens,
            result.output_tokens,
        )
        return TokenCountedResult(value=persona, input_tokens=result.input_tokens, output_tokens=result.output_tokens)

    def build_input(
        self,
        *,
        training_config: RuntimeTrainingConfig,
        scenario_id: str | None = None,
    ) -> PersonaGenerationInput:
        """Normalize training-config business context into the persona-generator contract."""
        resolved_scenario_id = scenario_id or self._settings.default_training_scenario_id
        context = self._resolve_generation_context(training_config)
        return PersonaGenerationInput(
            scenario=get_scenario(resolved_scenario_id),
            training_config_name=training_config.name,
            persona_generation_context=context,
            persona_policy={},
            organization_context={},
            target_action=None,
            allowed_roles=None,
            manager_training_goal=None,
            difficulty_level=None,
            randomization_seed=None,
            constraints={},
        )

    def _resolve_generation_context(self, training_config: RuntimeTrainingConfig) -> str:
        """Prefer structured seed config; fall back to legacy free-text prompt."""
        if training_config.seed_config:
            try:
                seed = PersonaSeedConfig.model_validate(training_config.seed_config)
                rendered = _seed_prompt_renderer.render(seed)
                logger.info(
                    "seed_prompt_rendered training_config_id=%s prompt_length=%s",
                    training_config.id,
                    len(rendered),
                )
                return rendered
            except (PydanticValidationError, FileNotFoundError, ValueError) as error:
                logger.warning(
                    "seed_prompt_render_failed training_config_id=%s error=%s falling_back_to_legacy",
                    training_config.id,
                    error,
                )
        return training_config.persona_generation_context.strip()

    def _build_client(
        self,
        *,
        training_config: RuntimeTrainingConfig,
        input_payload: PersonaGenerationInput,
    ) -> PersonaGeneratorClient:
        """Use global Yandex settings for MVP, with local fallback when explicitly allowed."""
        if input_payload.persona_generation_context:
            return self._client_factory.build_global_persona_client(fallback_generator=self._fallback_generator)
        if self._allow_local_fallback():
            logger.warning("persona_generator_missing_prompt fallback=local training_config_id=%s", training_config.id)
            return FakePersonaGeneratorClient(self._fallback_generator)
        raise LLMProviderConfigurationError(
            "Training config does not have persona_generation_context and local fallback is disabled."
        )

    def _provider_label(self, client: PersonaGeneratorClient) -> str:
        """Return a stable label for sanitized logs."""
        if isinstance(client, FakePersonaGeneratorClient):
            return "local_fallback"
        if isinstance(client, StructuredPersonaGeneratorClient):
            return getattr(client, "_provider", "openai_compatible") or "openai_compatible"
        return "global_yandex"

    def _allow_local_fallback(self) -> bool:
        """Allow local persona fallback only in local/debug-compatible environments."""
        env = self._settings.app_env.lower().strip()
        local_like_env = env in {"local", "dev", "development", "test", "demo"}
        return local_like_env or is_fake_fallback_allowed(self._settings)

class PersonaGeneratorClientFactory:
    def __init__(self, *, settings: Settings) -> None:
        """Keep settings needed for global persona-generator client construction."""
        self._settings = settings

    def build_global_persona_client(
        self,
        *,
        fallback_generator: UniversalFakePersonaGenerator,
    ) -> PersonaGeneratorClient:
        """Build the global MVP persona client from environment settings."""
        provider = self._settings.llm_backend.lower().strip()
        if provider == "fake":
            return FakePersonaGeneratorClient(fallback_generator)
        if provider == "openai_compatible":
            model = self._settings.llm_persona_model or self._settings.llm_model
            if not all([self._settings.llm_base_url, self._settings.llm_api_key, model]):
                raise LLMProviderConfigurationError(
                    "Incomplete global OpenAI-compatible persona configuration and local fallback is disabled."
                )
            return StructuredPersonaGeneratorClient(
                provider="openai_compatible",
                base_url=self._settings.llm_base_url,
                api_key=self._settings.llm_api_key,
                model_or_agent_label=model,
                system_prompt=load_persona_generator_prompt(),
                api_style=self._settings.llm_api_style,
                response_format=self._settings.llm_response_format,
                timeout_seconds=self._settings.llm_request_timeout_seconds,
                debug_payload_logging=self._settings.debug_llm_payload,
            )
        if provider != "yandex_compatible":
            raise LLMProviderConfigurationError(
                f"Unsupported llm_backend '{self._settings.llm_backend}' for persona generation."
            )

        agent_id = self._settings.yandex_persona_agent_id or self._settings.yandex_agent_id
        folder_id = self._settings.yandex_persona_folder_id or self._settings.yandex_folder_id
        if not all([self._settings.yandex_api_key, agent_id, folder_id]):
            raise LLMProviderConfigurationError(
                "Incomplete global Yandex persona configuration and local fallback is disabled."
            )

        return StructuredPersonaGeneratorClient(
            provider="yandex_compatible",
            base_url=self._settings.yandex_base_url,
            api_key=self._settings.yandex_api_key,
            folder_id=folder_id,
            agent_id=agent_id,
            timeout_seconds=self._settings.llm_request_timeout_seconds,
            debug_payload_logging=self._settings.debug_llm_payload,
        )
