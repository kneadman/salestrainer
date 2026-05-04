from __future__ import annotations

from uuid import uuid4

from app.access.models import LLMProviderConfig
from app.application import persona_generation_service as service_module
from app.application.persona_generation_service import PersonaGeneratorClientFactory
from app.domain.persona_generation import PersonaGenerator
from app.infrastructure.config import Settings
from app.infrastructure.secrets import encrypt_secret


def test_persona_generation_client_factory_uses_persona_yandex_set(monkeypatch) -> None:
    captured: dict[str, object] = {}
    settings = Settings(secret_encryption_key="test-secret-key", allow_fake_llm_fallback=False)
    provider_config = LLMProviderConfig(
        id=uuid4(),
        client_account_id=uuid4(),
        name="Demo",
        provider="yandex_compatible",
        persona_api_key_encrypted=encrypt_secret("persona-key", settings),
        persona_folder_id="persona-folder",
        persona_agent_id="persona-agent",
        persona_master_prompt="persona prompt",
        persona_json_template="{\"persona\": {}}",
        dialogue_api_key_encrypted=encrypt_secret("dialogue-key", settings),
        dialogue_folder_id="dialogue-folder",
        dialogue_agent_id="dialogue-agent",
    )

    class CapturingClient:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

    monkeypatch.setattr(service_module, "StructuredPersonaGeneratorClient", CapturingClient)

    PersonaGeneratorClientFactory(settings=settings).build(provider_config, fallback_generator=PersonaGenerator())

    assert captured["api_key"] == "persona-key"
    assert captured["folder_id"] == "persona-folder"
    assert captured["agent_id"] == "persona-agent"
    assert captured["master_prompt"] == "persona prompt"
    assert captured["json_template"] == "{\"persona\": {}}"
