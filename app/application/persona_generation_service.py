from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.access.models import LLMProviderConfig, RuntimeTrainingConfig
from app.domain.errors import LLMProviderConfigurationError, PersonaGenerationError
from app.domain.models import PersonaGenerationInput, PersonaProfile
from app.domain.persona_generation import PersonaGenerator
from app.domain.scenarios import get_scenario
from app.infrastructure.config import Settings
from app.infrastructure.llm_client import LLMClientError
from app.infrastructure.persona_generator_client import (
    FakePersonaGeneratorClient,
    PersonaGeneratorClient,
    StructuredPersonaGeneratorClient,
    validate_generated_persona,
)
from app.infrastructure.secrets import decrypt_secret

logger = logging.getLogger(__name__)


class PersonaGenerationService:
    def __init__(
        self,
        db_session: Session,
        *,
        settings: Settings,
        fallback_generator: PersonaGenerator | None = None,
        client_factory: PersonaGeneratorClientFactory | None = None,
    ) -> None:
        """Keep request-scoped DB access for organization LLM provider config resolution."""
        self._session = db_session
        self._settings = settings
        self._fallback_generator = fallback_generator or PersonaGenerator(settings.persona_random_seed)
        self._client_factory = client_factory or PersonaGeneratorClientFactory(settings=settings)

    def generate_for_training_config(
        self,
        *,
        training_config: RuntimeTrainingConfig,
        scenario_id: str | None = None,
    ) -> PersonaProfile:
        """Generate a hidden PersonaProfile from the runtime training config."""
        input_payload = self.build_input(training_config=training_config, scenario_id=scenario_id)
        client = self._build_client(training_config)
        try:
            output = client.generate_persona(input_payload)
        except LLMClientError as error:
            raise PersonaGenerationError("Persona generator failed to produce a valid profile.") from error
        persona = validate_generated_persona(output)
        logger.info(
            "persona_generated training_config_id=%s client_account_id=%s provider=%s persona_id=%s",
            training_config.id,
            training_config.client_account_id,
            self._provider_label(training_config.llm_provider_config_id),
            persona.id,
        )
        return persona

    def build_input(
        self,
        *,
        training_config: RuntimeTrainingConfig,
        scenario_id: str | None = None,
    ) -> PersonaGenerationInput:
        """Normalize free-form persona policy into the structured LLM input contract."""
        resolved_scenario_id = scenario_id or training_config.default_scenario_id
        persona_policy = dict(training_config.persona_policy or {})
        return PersonaGenerationInput(
            product_line=training_config.product_line,
            scenario=get_scenario(resolved_scenario_id),
            training_config_name=training_config.name,
            persona_policy=persona_policy,
            organization_context=self._dict_policy_value(persona_policy, "organization_context"),
            target_action=self._string_policy_value(persona_policy, "target_action"),
            allowed_roles=self._string_list_policy_value(persona_policy, "allowed_roles"),
            allowed_product_lines=self._string_list_policy_value(persona_policy, "allowed_product_lines"),
            manager_training_goal=self._string_policy_value(persona_policy, "manager_training_goal"),
            difficulty_level=self._string_policy_value(persona_policy, "difficulty_level"),
            randomization_seed=self._int_policy_value(persona_policy, "randomization_seed"),
            constraints=self._dict_policy_value(persona_policy, "constraints"),
            schema_version=1,
        )

    def _build_client(self, training_config: RuntimeTrainingConfig) -> PersonaGeneratorClient:
        """Resolve the configured persona generator client or local fallback policy."""
        provider_config_id = training_config.llm_provider_config_id
        if provider_config_id is None:
            if self._allow_local_fallback():
                logger.warning("persona_generator_missing_provider fallback=local training_config_id=%s", training_config.id)
                return FakePersonaGeneratorClient(self._fallback_generator)
            raise LLMProviderConfigurationError("Training config does not have an LLM provider config for persona generation.")

        provider_config = self._get_provider_config(provider_config_id)
        if provider_config.client_account_id != training_config.client_account_id:
            raise LLMProviderConfigurationError("LLM provider config belongs to another organization.")
        if not provider_config.is_active:
            raise LLMProviderConfigurationError("LLM provider config is disabled.")
        return self._client_factory.build(provider_config, fallback_generator=self._fallback_generator)

    def _get_provider_config(self, provider_config_id: UUID) -> LLMProviderConfig:
        """Load provider config without exposing its encrypted secret."""
        provider_config = self._session.get(LLMProviderConfig, provider_config_id)
        if provider_config is None:
            raise LLMProviderConfigurationError("LLM provider config was not found.")
        return provider_config

    def _provider_label(self, provider_config_id: UUID | None) -> str:
        """Return a safe provider label for logs."""
        if provider_config_id is None:
            return "local_fallback"
        provider_config = self._session.get(LLMProviderConfig, provider_config_id)
        return provider_config.provider if provider_config is not None else "missing"

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
        """Keep settings needed for decrypting and constructing provider clients."""
        self._settings = settings

    def build(
        self,
        provider_config: LLMProviderConfig,
        *,
        fallback_generator: PersonaGenerator,
    ) -> PersonaGeneratorClient:
        """Build a persona generator client from a stored provider config."""
        provider = provider_config.provider.lower().strip()
        if provider == "fake":
            return FakePersonaGeneratorClient(fallback_generator)
        if provider in {"yandex_compatible", "openai_compatible"}:
            return self._structured_client(provider_config, provider=provider, fallback_generator=fallback_generator)
        if self._allow_local_fallback():
            logger.warning("persona_generator_unknown_provider provider=%s fallback=local", provider_config.provider)
            return FakePersonaGeneratorClient(fallback_generator)
        raise LLMProviderConfigurationError(f"Unsupported persona generator provider '{provider_config.provider}'.")

    def _structured_client(
        self,
        provider_config: LLMProviderConfig,
        *,
        provider: str,
        fallback_generator: PersonaGenerator,
    ) -> StructuredPersonaGeneratorClient:
        """Create an OpenAI/Yandex-compatible persona generator without logging secrets."""
        if provider_config.encrypted_api_key is None:
            if self._allow_local_fallback():
                logger.warning("persona_generator_missing_api_key provider=%s fallback=local", provider)
                return FakePersonaGeneratorClient(fallback_generator)
            raise LLMProviderConfigurationError("Persona generator provider config does not have an API key.")
        api_key = decrypt_secret(provider_config.encrypted_api_key, self._settings)
        return StructuredPersonaGeneratorClient(
            provider=provider,
            base_url=provider_config.base_url or self._default_base_url(provider),
            api_key=api_key,
            folder_id=provider_config.folder_id,
            agent_id=provider_config.agent_id,
            model_or_agent_label=provider_config.model_or_agent_label,
            timeout_seconds=self._settings.llm_request_timeout_seconds,
            fallback_client=FakePersonaGeneratorClient(fallback_generator) if self._allow_local_fallback() else None,
            debug_payload_logging=self._settings.debug_llm_payload,
        )

    def _allow_local_fallback(self) -> bool:
        """Mirror LLM fallback policy for persona generation."""
        return self._settings.allow_fake_llm_fallback or self._settings.is_local_env

    def _default_base_url(self, provider: str) -> str:
        """Return a provider-specific default base URL."""
        if provider == "yandex_compatible":
            return self._settings.yandex_base_url
        return "https://api.openai.com/v1"
