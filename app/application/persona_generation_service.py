from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.access.models import RuntimeTrainingConfig
from app.domain.errors import LLMProviderConfigurationError, PersonaGenerationError
from app.domain.models import PersonaGenerationInput, PersonaProfile
from app.domain.persona_generation import UniversalFakePersonaGenerator
from app.domain.scenarios import get_scenario
from app.infrastructure.config import Settings
from app.infrastructure.persona_generator_client import (
    FakePersonaGeneratorClient,
    PersonaGeneratorClient,
    StructuredPersonaGeneratorClient,
    validate_generated_persona,
)

logger = logging.getLogger(__name__)


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
    ) -> PersonaProfile:
        """Generate a hidden PersonaProfile from training-config business context."""
        del self._session
        input_payload = self.build_input(training_config=training_config, scenario_id=scenario_id)
        client = self._build_client(training_config=training_config, input_payload=input_payload)
        try:
            output = client.generate_persona(input_payload)
        except Exception as error:
            raise PersonaGenerationError("Persona generator failed to produce a valid profile.") from error
        persona = validate_generated_persona(output, input_payload)
        logger.info(
            "persona_generated training_config_id=%s client_account_id=%s provider=%s persona_id=%s",
            training_config.id,
            training_config.client_account_id,
            self._provider_label(client),
            persona.id,
        )
        return persona

    def build_input(
        self,
        *,
        training_config: RuntimeTrainingConfig,
        scenario_id: str | None = None,
    ) -> PersonaGenerationInput:
        """Normalize training-config business context into the persona-generator contract."""
        resolved_scenario_id = scenario_id or training_config.default_scenario_id
        persona_policy = dict(training_config.persona_policy or {})
        return PersonaGenerationInput(
            scenario=get_scenario(resolved_scenario_id),
            training_config_name=training_config.name,
            product_line=training_config.product_line.strip(),
            persona_generation_prompt=training_config.persona_generation_prompt.strip(),
            persona_policy=persona_policy,
            organization_context=self._dict_policy_value(persona_policy, "organization_context"),
            target_action=self._string_policy_value(persona_policy, "target_action"),
            allowed_roles=self._string_list_policy_value(persona_policy, "allowed_roles"),
            manager_training_goal=self._string_policy_value(persona_policy, "manager_training_goal"),
            difficulty_level=self._string_policy_value(persona_policy, "difficulty_level"),
            randomization_seed=self._int_policy_value(persona_policy, "randomization_seed"),
            constraints=self._dict_policy_value(persona_policy, "constraints"),
            schema_version=1,
        )

    def _build_client(
        self,
        *,
        training_config: RuntimeTrainingConfig,
        input_payload: PersonaGenerationInput,
    ) -> PersonaGeneratorClient:
        """Use global Yandex settings for MVP, with local fallback when explicitly allowed."""
        if input_payload.persona_generation_prompt:
            return self._client_factory.build_global_persona_client(fallback_generator=self._fallback_generator)
        if self._allow_local_fallback():
            logger.warning("persona_generator_missing_prompt fallback=local training_config_id=%s", training_config.id)
            return FakePersonaGeneratorClient(self._fallback_generator)
        raise LLMProviderConfigurationError(
            "Training config does not have persona_generation_prompt and local fallback is disabled."
        )

    def _provider_label(self, client: PersonaGeneratorClient) -> str:
        """Return a stable label for sanitized logs."""
        if isinstance(client, FakePersonaGeneratorClient):
            return "local_fallback"
        return "global_yandex"

    def _allow_local_fallback(self) -> bool:
        """Allow local persona fallback only in local/debug-compatible environments."""
        return self._settings.allow_fake_llm_fallback or self._settings.is_local_env

    def _string_policy_value(self, persona_policy: dict[str, object], key: str) -> str | None:
        """Extract a non-empty string policy value from free-form JSON."""
        value = persona_policy.get(key)
        return value.strip() if isinstance(value, str) and value.strip() else None

    def _string_list_policy_value(self, persona_policy: dict[str, object], key: str) -> list[str] | None:
        """Extract string-list policy values while ignoring unsupported entries."""
        value = persona_policy.get(key)
        if not isinstance(value, list):
            return None
        items = [item for item in value if isinstance(item, str) and item.strip()]
        return items or None

    def _dict_policy_value(self, persona_policy: dict[str, object], key: str) -> dict[str, object]:
        """Extract object-like policy values and keep invalid shapes out of the LLM input."""
        value = persona_policy.get(key)
        return dict(value) if isinstance(value, dict) else {}

    def _int_policy_value(self, persona_policy: dict[str, object], key: str) -> int | None:
        """Extract integer policy values without accepting booleans as integers."""
        value = persona_policy.get(key)
        if isinstance(value, bool):
            return None
        return value if isinstance(value, int) else None


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
