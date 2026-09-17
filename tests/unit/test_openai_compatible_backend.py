from __future__ import annotations

import json

import pytest

from app.domain.errors import LLMProviderConfigurationError
from app.infrastructure.config import Settings
from app.infrastructure.judge_client import FakeJudgeClient, StructuredJudgeClient, build_judge_client
from app.infrastructure.llm_client import (
    FakeLLMClient,
    OpenAICompatibleLLMClient,
    build_llm_client,
)
from app.infrastructure.persona_generator_client import (
    FakePersonaGeneratorClient,
    StructuredPersonaGeneratorClient,
)
from app.infrastructure.responses_client import (
    LLMClientError,
    OpenAICompatibleClient,
    reasoning_params,
)
from app.infrastructure.startup_validation import validate_runtime_settings
from app.infrastructure.summary_compressor import (
    FakeSummaryCompressor,
    OpenAICompatibleSummaryCompressor,
    build_summary_compressor,
)
from tests.unit.test_llm_client import sample_payload


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def model_dump(self) -> dict[str, object]:
        return self._payload


def _chat_completion(json_text: str) -> dict[str, object]:
    return {"choices": [{"index": 0, "message": {"role": "assistant", "content": json_text}}]}


def _router_settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "llm_backend": "openai_compatible",
        "allow_fake_llm_fallback": False,
        "llm_base_url": "https://router.example.test/v1",
        "llm_api_key": "router-key",
        "llm_model": "some/model",
    }
    base.update(overrides)
    return Settings(**base)


def test_responses_client_rejects_unknown_api_style() -> None:
    with pytest.raises(LLMClientError, match="Unsupported llm_api_style"):
        OpenAICompatibleClient(base_url="https://x/v1", api_key="k", api_style="grpc")


def test_chat_completions_request_maps_messages_and_json_schema() -> None:
    client = OpenAICompatibleClient(
        base_url="https://router.example.test/v1",
        api_key="k",
        model="openai/gpt-4.1-mini",
        api_style="chat_completions",
    )

    request = client._chat_completions_request(
        {
            "input": "hello",
            "system_prompt": "be a client",
            "text": {"format": {"type": "json_schema", "name": "answer", "schema": {"type": "object"}, "strict": True}},
        }
    )

    assert request["model"] == "openai/gpt-4.1-mini"
    assert request["messages"] == [
        {"role": "system", "content": "be a client"},
        {"role": "user", "content": "hello"},
    ]
    assert request["response_format"] == {
        "type": "json_schema",
        "json_schema": {"name": "answer", "schema": {"type": "object"}, "strict": True},
    }
    assert client.endpoint_url == "https://router.example.test/v1/chat/completions"


def test_chat_completions_request_downgrades_to_json_object() -> None:
    client = OpenAICompatibleClient(
        base_url="https://router.example.test/v1",
        api_key="k",
        model="m",
        api_style="chat_completions",
        response_format="json_object",
    )

    request = client._chat_completions_request(
        {"input": "hello", "text": {"format": {"type": "json_schema", "name": "answer", "schema": {}}}}
    )

    assert request["response_format"] == {"type": "json_object"}


def test_chat_completions_request_omits_response_format_when_disabled() -> None:
    client = OpenAICompatibleClient(
        base_url="https://router.example.test/v1",
        api_key="k",
        model="m",
        api_style="chat_completions",
        response_format="none",
    )

    request = client._chat_completions_request(
        {"input": "hello", "text": {"format": {"type": "json_schema", "name": "answer", "schema": {}}}}
    )

    assert "response_format" not in request


def test_chat_completions_request_requires_model_name() -> None:
    client = OpenAICompatibleClient(
        base_url="https://router.example.test/v1",
        api_key="k",
        api_style="chat_completions",
    )

    with pytest.raises(LLMClientError, match="requires a model name"):
        client._chat_completions_request({"input": "hello"})


def test_reasoning_params_default_sends_nothing() -> None:
    assert reasoning_params("provider_default") == {}
    assert reasoning_params("") == {}


def test_reasoning_params_off_disables_thinking() -> None:
    assert reasoning_params("off") == {"thinking": {"type": "disabled"}}


def test_reasoning_params_supports_explicit_effort_levels() -> None:
    for level in ("minimal", "low", "medium", "high"):
        assert reasoning_params(f"effort:{level}") == {"reasoning_effort": level}


def test_reasoning_params_rejects_unknown_mode() -> None:
    for mode in ("nope", "effort:extreme", "effort:", "true"):
        with pytest.raises(LLMClientError, match="Unsupported llm_reasoning_mode"):
            reasoning_params(mode)


def test_reasoning_mode_off_is_added_to_chat_completions_request() -> None:
    client = OpenAICompatibleClient(
        base_url="https://router.example.test/v1",
        api_key="k",
        model="m",
        api_style="chat_completions",
        reasoning_mode="off",
    )

    request = client._chat_completions_request({"input": "hello"})

    assert request["thinking"] == {"type": "disabled"}


def test_reasoning_mode_provider_default_keeps_request_clean() -> None:
    client = OpenAICompatibleClient(
        base_url="https://router.example.test/v1",
        api_key="k",
        model="m",
        api_style="chat_completions",
    )

    request = client._chat_completions_request({"input": "hello"})

    assert "thinking" not in request
    assert "reasoning_effort" not in request


def test_reasoning_mode_is_validated_at_construction() -> None:
    with pytest.raises(LLMClientError, match="Unsupported llm_reasoning_mode"):
        OpenAICompatibleClient(
            base_url="https://router.example.test/v1",
            api_key="k",
            api_style="chat_completions",
            reasoning_mode="bogus",
        )


def test_openai_compatible_dialogue_client_parses_chat_completions_response() -> None:
    calls: list[dict[str, object]] = []

    def transport(request_payload: dict[str, object]) -> FakeResponse:
        calls.append(request_payload)
        return FakeResponse(
            _chat_completion(
                json.dumps(
                    {
                        "answer": "What exactly do you review?",
                        "interest_delta": 3,
                        "state_patch": {"tone": "skeptical"},
                        "stage": "value_clarification",
                        "internal_notes": "ok",
                    }
                )
            )
        )

    client = OpenAICompatibleLLMClient(
        base_url="https://router.example.test/v1",
        api_key="router-key",
        model="openai/gpt-4.1-mini",
        system_prompt="You are the client.",
        transport=transport,
        max_retries=0,
    )

    result = client.generate_client_turn(sample_payload())

    assert result.value.answer == "What exactly do you review?"
    assert result.input_tokens > 0
    assert calls[0]["model"] == "openai/gpt-4.1-mini"
    assert calls[0]["system_prompt"] == "You are the client."


def test_build_llm_client_builds_openai_compatible_client_from_env() -> None:
    client = build_llm_client(_router_settings(llm_dialogue_model="dialogue/model"))

    assert isinstance(client, OpenAICompatibleLLMClient)
    assert client._base_url == "https://router.example.test/v1"
    assert client._model == "dialogue/model"
    assert client._system_prompt


def test_reasoning_mode_is_plumbed_from_settings_to_dialogue_client() -> None:
    client = build_llm_client(
        _router_settings(llm_dialogue_model="dialogue/model", llm_reasoning_mode="off")
    )

    assert isinstance(client, OpenAICompatibleLLMClient)
    assert client._reasoning_mode == "off"
    assert client._reasoning_params == {"thinking": {"type": "disabled"}}


def test_build_llm_client_falls_back_to_fake_for_incomplete_router_config() -> None:
    client = build_llm_client(
        _router_settings(app_env="local", allow_fake_llm_fallback=True, llm_base_url="", llm_model="")
    )

    assert isinstance(client, FakeLLMClient)


def test_build_judge_client_builds_openai_compatible_client() -> None:
    client = build_judge_client(_router_settings(llm_judge_model="judge/model"))

    assert isinstance(client, StructuredJudgeClient)
    assert client._model_or_agent_label == "judge/model"
    assert client._system_prompt


def test_build_judge_client_falls_back_to_fake_for_incomplete_router_config() -> None:
    client = build_judge_client(
        _router_settings(app_env="local", allow_fake_llm_fallback=True, llm_api_key="")
    )

    assert isinstance(client, FakeJudgeClient)


def test_build_summary_compressor_builds_openai_compatible_compressor() -> None:
    compressor = build_summary_compressor(_router_settings())

    assert isinstance(compressor, OpenAICompatibleSummaryCompressor)
    assert compressor._model == "some/model"


def test_build_summary_compressor_falls_back_to_fake_for_incomplete_router_config() -> None:
    compressor = build_summary_compressor(
        _router_settings(app_env="local", allow_fake_llm_fallback=True, llm_model="")
    )

    assert isinstance(compressor, FakeSummaryCompressor)


def test_persona_factory_builds_openai_compatible_client() -> None:
    from app.application.persona_generation_service import PersonaGeneratorClientFactory
    from app.domain.persona_generation import UniversalFakePersonaGenerator

    client = PersonaGeneratorClientFactory(
        settings=_router_settings(llm_persona_model="persona/model")
    ).build_global_persona_client(fallback_generator=UniversalFakePersonaGenerator())

    assert isinstance(client, StructuredPersonaGeneratorClient)
    assert client._model_or_agent_label == "persona/model"
    assert client._system_prompt


def test_persona_factory_raises_for_incomplete_router_config() -> None:
    from app.application.persona_generation_service import PersonaGeneratorClientFactory
    from app.domain.persona_generation import UniversalFakePersonaGenerator

    with pytest.raises(LLMProviderConfigurationError, match="OpenAI-compatible persona"):
        PersonaGeneratorClientFactory(settings=_router_settings(llm_model="")).build_global_persona_client(
            fallback_generator=UniversalFakePersonaGenerator()
        )


def test_startup_validation_accepts_complete_router_config_in_production() -> None:
    validate_runtime_settings(
        _router_settings(
            app_env="production",
            database_url="postgresql+psycopg://user:pass@db:5432/sales_trainer",
            secret_encryption_key="prod-secret",
        )
    )


def test_startup_validation_rejects_incomplete_router_config_in_production() -> None:
    with pytest.raises(LLMProviderConfigurationError, match="Incomplete OpenAI-compatible LLM configuration"):
        validate_runtime_settings(
            _router_settings(
                app_env="production",
                database_url="postgresql+psycopg://user:pass@db:5432/sales_trainer",
                secret_encryption_key="prod-secret",
                llm_api_key="",
            )
        )


def test_startup_validation_rejects_placeholder_router_url_in_production() -> None:
    with pytest.raises(LLMProviderConfigurationError, match="LLM_BASE_URL"):
        validate_runtime_settings(
            _router_settings(
                app_env="production",
                database_url="postgresql+psycopg://user:pass@db:5432/sales_trainer",
                secret_encryption_key="prod-secret",
                llm_base_url="   ",
                llm_model="",
            )
        )


def test_startup_validation_rejects_unknown_reasoning_mode_in_production() -> None:
    with pytest.raises(LLMProviderConfigurationError, match="Unsupported llm_reasoning_mode"):
        validate_runtime_settings(
            _router_settings(
                app_env="production",
                database_url="postgresql+psycopg://user:pass@db:5432/sales_trainer",
                secret_encryption_key="prod-secret",
                llm_reasoning_mode="sometimes",
            )
        )
