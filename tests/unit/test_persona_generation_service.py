from __future__ import annotations

from uuid import uuid4

import pytest

from app.access.models import RuntimeTrainingConfig
from app.application.persona_generation_service import PersonaGenerationService, PersonaGeneratorClientFactory
from app.domain.errors import LLMProviderConfigurationError, PersonaGenerationError
from app.domain.persona_generation import UniversalFakePersonaGenerator
from app.infrastructure.config import Settings


def _training_config(*, prompt: str = "Generate a beauty retail decision-maker persona.") -> RuntimeTrainingConfig:
    return RuntimeTrainingConfig(
        id=uuid4(),
        client_account_id=uuid4(),
        name="Default config",
        default_scenario_id="needs_diagnosis",
        persona_generation_context=prompt,
        persona_policy={
            "allowed_roles": ["owner"],
            "target_action": "book_intro_call",
            "randomization_seed": 123,
            "organization_context": {"secret": "legacy"},
            "constraints": {"region": "legacy"},
        },
        ui_config={},
        limits={},
        llm_provider_config_id=None,
    )


def test_persona_generation_service_build_input_uses_prompt_and_settings_default_scenario() -> None:
    service = PersonaGenerationService(  # type: ignore[arg-type]
        db_session=None,
        settings=Settings(default_training_scenario_id="first_contact_discovery"),
    )

    payload = service.build_input(training_config=_training_config())

    assert payload.scenario.id == "first_contact_discovery"
    assert payload.training_config_name == "Default config"
    assert payload.persona_generation_context == "Generate a beauty retail decision-maker persona."
    assert payload.persona_policy == {}
    assert payload.organization_context == {}
    assert payload.target_action is None
    assert payload.allowed_roles is None
    assert payload.manager_training_goal is None
    assert payload.difficulty_level is None
    assert payload.randomization_seed is None
    assert payload.constraints == {}


def test_persona_generation_service_build_input_prefers_explicit_scenario() -> None:
    service = PersonaGenerationService(  # type: ignore[arg-type]
        db_session=None,
        settings=Settings(default_training_scenario_id="first_contact_discovery"),
    )

    payload = service.build_input(training_config=_training_config(), scenario_id="objection_handling")

    assert payload.scenario.id == "objection_handling"


def test_persona_generation_client_factory_uses_global_persona_yandex_settings(monkeypatch) -> None:
    captured: dict[str, object] = {}
    settings = Settings(
        llm_backend="yandex_compatible",
        allow_fake_llm_fallback=False,
        yandex_api_key="persona-key",
        yandex_base_url="https://ai.api.cloud.yandex.net/v1",
        yandex_persona_folder_id="persona-folder",
        yandex_persona_agent_id="persona-agent",
    )

    class CapturingClient:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

    monkeypatch.setattr("app.application.persona_generation_service.StructuredPersonaGeneratorClient", CapturingClient)

    PersonaGeneratorClientFactory(settings=settings).build_global_persona_client(
        fallback_generator=UniversalFakePersonaGenerator(),
    )

    assert captured["api_key"] == "persona-key"
    assert captured["folder_id"] == "persona-folder"
    assert captured["agent_id"] == "persona-agent"
    assert captured["base_url"] == "https://ai.api.cloud.yandex.net/v1"
    assert "fallback_client" not in captured


def test_persona_generation_service_falls_back_to_local_without_prompt_in_local_mode() -> None:
    service = PersonaGenerationService(
        db_session=None,  # type: ignore[arg-type]
        settings=Settings(),
        fallback_generator=UniversalFakePersonaGenerator(seed=1),
    )

    persona = service.generate_for_training_config(training_config=_training_config(prompt=""))

    assert persona.id.startswith("generated_first_contact_discovery_")
    assert persona.role in {
        "owner",
        "founder",
        "ceo",
        "general_director",
        "managing_partner",
        "commercial_director",
        "cfo",
        "operations_director",
        "sales_director",
        "purchase_manager",
    }
    assert persona.authority_level == "final_decider"


def test_persona_generation_service_rejects_empty_prompt_without_fallback() -> None:
    service = PersonaGenerationService(
        db_session=None,  # type: ignore[arg-type]
        settings=Settings(app_env="prod", allow_fake_llm_fallback=False),
    )

    with pytest.raises(LLMProviderConfigurationError, match="persona_generation_context"):
        service.generate_for_training_config(training_config=_training_config(prompt=""))


def test_persona_generation_service_does_not_fallback_when_prompted_client_fails() -> None:
    class FailingClient:
        def generate_persona(self, payload):  # type: ignore[no-untyped-def]
            from app.infrastructure.llm_client import LLMClientError

            raise LLMClientError("bad output")

    class FailingFactory:
        def build_global_persona_client(self, *, fallback_generator):  # type: ignore[no-untyped-def]
            del fallback_generator
            return FailingClient()

    service = PersonaGenerationService(
        db_session=None,  # type: ignore[arg-type]
        settings=Settings(),
        fallback_generator=UniversalFakePersonaGenerator(seed=2),
        client_factory=FailingFactory(),  # type: ignore[arg-type]
    )

    with pytest.raises(PersonaGenerationError):
        service.generate_for_training_config(training_config=_training_config())
