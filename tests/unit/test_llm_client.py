from __future__ import annotations

import json
import logging

import pytest
from pydantic import BaseModel, ConfigDict

from app.domain.errors import LLMProviderConfigurationError
from app.domain.models import LLMTurnInput
from app.domain.personas import get_persona
from app.domain.scenarios import get_scenario
from app.infrastructure.llm_client import (
    FakeLLMClient,
    LLMClientError,
    YandexCompatibleLLMClient,
    build_llm_client,
    parse_llm_turn_response,
)
from app.infrastructure.config import Settings
from app.infrastructure.fake_llm_client import FakeLLMClient as ActiveFakeLLMClient
from app.prompts.schemas import build_strict_json_schema, llm_turn_response_schema


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def model_dump(self) -> dict[str, object]:
        return self._payload


def sample_payload() -> LLMTurnInput:
    return LLMTurnInput(
        task="simulate_next_client_reply",
        scenario=get_scenario("sales_audit_cold_outreach"),
        hidden_profile=get_persona("owner"),
        current_state={
            "interest_score": 25,
            "interest_band": "skeptical",
            "stage": "first_contact",
            "client_state": {
                "tone": "skeptical",
                "trust": 20,
                "irritation": 10,
                "urgency": 20,
                "price_sensitivity": 45,
                "open_objections": [],
                "known_pains": [],
                "buying_signals": [],
                "red_flags": [],
                "discovered_role": None,
                "discovered_authority_level": None,
                "discovered_pains": [],
                "discovered_decision_criteria": [],
                "discovered_constraints": [],
                "discovered_current_process": [],
            },
        },
        discovered_facts={},
        conversation_summary="Training started.",
        recent_turns=[],
        manager_message="How do you track conversion losses now?",
    )


def test_parse_llm_turn_response_from_yandex_prompt_response_payload() -> None:
    raw = {
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": json.dumps(
                            {
                                "answer": "What exactly do you review?",
                                "interest_delta": 3,
                                "state_patch": {
                                    "tone": "skeptical",
                                    "trust_delta": 1,
                                    "irritation_delta": 0,
                                    "urgency_delta": 0,
                                    "add_open_objections": [],
                                    "remove_open_objections": [],
                                    "add_known_pains": [],
                                    "add_buying_signals": [],
                                    "add_red_flags": [],
                                },
                                "stage": "value_clarification",
                                "internal_notes": "Valid JSON in nested payload.",
                            }
                        ),
                    }
                ],
            }
        ],
        "output_text": "{\"answer\":\"What exactly do you review?\",\"interest_delta\":3,\"state_patch\":{\"tone\":\"skeptical\",\"trust_delta\":1,\"irritation_delta\":0,\"urgency_delta\":0,\"add_open_objections\":[],\"remove_open_objections\":[],\"add_known_pains\":[],\"add_buying_signals\":[],\"add_red_flags\":[]},\"stage\":\"value_clarification\",\"internal_notes\":\"Valid JSON in nested payload.\"}",
    }
    parsed = parse_llm_turn_response(raw)
    assert parsed.answer == "What exactly do you review?"
    assert parsed.stage == "value_clarification"


def test_yandex_compatible_client_builds_expected_request_and_retries_then_succeeds() -> None:
    calls: list[dict[str, object]] = []

    def transport(request_payload: dict[str, object]) -> FakeResponse | str:
        calls.append(request_payload)
        if len(calls) == 1:
            return "not-json"
        return FakeResponse({
            "output_text": json.dumps(
                {
                    "answer": "Understood. How long does that take?",
                    "interest_delta": 4,
                    "state_patch": {
                        "tone": "neutral",
                        "trust_delta": 2,
                        "irritation_delta": -1,
                        "urgency_delta": 1,
                        "add_open_objections": [],
                        "remove_open_objections": [],
                        "add_known_pains": [],
                        "add_buying_signals": [],
                        "add_red_flags": [],
                    },
                    "stage": "need_discovery",
                    "internal_notes": "Retry returned valid JSON.",
                }
            ),
            "output": [
                {
                    "type": "message",
                    "content": [],
                },
            ]
        })

    client = YandexCompatibleLLMClient(
        base_url="https://ai.api.cloud.yandex.net/v1",
        api_key="token",
        folder_id="folder-id",
        agent_id="agent-id",
        transport=transport,
        max_retries=1,
    )

    response = client.generate_client_turn(sample_payload())
    assert response.interest_delta == 4
    assert len(calls) == 2
    request_payload = calls[0]
    assert request_payload["prompt"]["id"] == "agent-id"
    assert request_payload["text"]["format"]["type"] == "json_schema"
    assert request_payload["text"]["format"]["name"] == "llm_turn_response"
    assert request_payload["text"]["format"]["strict"] is True
    input_payload = json.loads(request_payload["input"])
    assert input_payload["task"] == "simulate_next_client_reply"
    assert input_payload["manager_message"] == "How do you track conversion losses now?"
    assert input_payload["scenario"]["id"] == "first_contact_discovery"
    assert input_payload["hidden_profile"]["id"] == "owner"
    assert "latent_pains" in input_payload["hidden_profile"]
    assert input_payload["current_state"]["stage"] == "first_contact"
    assert input_payload["discovered_facts"] == {}
    assert input_payload["recent_turns"] == []
    retry_input_payload = json.loads(calls[1]["input"])
    assert "Previous answer was invalid" in retry_input_payload["retry_instruction"]


def test_yandex_compatible_client_falls_back_to_fake_client() -> None:
    client = YandexCompatibleLLMClient(
        base_url="https://ai.api.cloud.yandex.net/v1",
        api_key="token",
        folder_id="folder-id",
        agent_id="agent-id",
        transport=lambda *_: "still-not-json",
        max_retries=1,
        fallback_client=FakeLLMClient(),
    )

    response = client.generate_client_turn(sample_payload())
    assert response.answer
    assert -15 <= response.interest_delta <= 15


def test_llm_client_exports_single_active_fake_client() -> None:
    assert FakeLLMClient is ActiveFakeLLMClient


def test_fake_llm_client_discovers_current_process_from_russian_accounting_question() -> None:
    payload = sample_payload().model_copy(
        update={"manager_message": "Как сейчас ведёте бухгалтерию и где теряется процесс?"}
    )

    response = FakeLLMClient().generate_client_turn(payload)

    discovered_process = response.state_patch.add_discovered_current_process
    assert discovered_process
    assert any(
        "Owner wants more control" in item or "Текущее решение" in item
        for item in discovered_process
    )


def test_build_llm_client_uses_fake_when_provider_config_is_incomplete() -> None:
    settings = Settings(
        llm_backend="yandex_compatible",
        yandex_api_key="",
        yandex_folder_id="folder-id",
        yandex_agent_id="agent-id",
    )
    client = build_llm_client(settings)
    assert isinstance(client, FakeLLMClient)


def test_build_llm_client_uses_dialogue_specific_yandex_settings() -> None:
    settings = Settings(
        llm_backend="yandex_compatible",
        allow_fake_llm_fallback=False,
        yandex_api_key="token",
        yandex_folder_id="legacy-folder",
        yandex_agent_id="legacy-agent",
        yandex_dialogue_folder_id="dialogue-folder",
        yandex_dialogue_agent_id="dialogue-agent",
    )

    client = build_llm_client(settings)

    assert isinstance(client, YandexCompatibleLLMClient)
    assert client._folder_id == "dialogue-folder"
    assert client._agent_id == "dialogue-agent"


def test_build_llm_client_falls_back_to_legacy_yandex_agent_settings() -> None:
    settings = Settings(
        llm_backend="yandex_compatible",
        allow_fake_llm_fallback=False,
        yandex_api_key="token",
        yandex_folder_id="legacy-folder",
        yandex_agent_id="legacy-agent",
    )

    client = build_llm_client(settings)

    assert isinstance(client, YandexCompatibleLLMClient)
    assert client._folder_id == "legacy-folder"
    assert client._agent_id == "legacy-agent"


def test_build_llm_client_raises_when_provider_config_is_incomplete_and_fallback_is_disabled() -> None:
    settings = Settings(
        app_env="prod",
        llm_backend="yandex_compatible",
        allow_fake_llm_fallback=False,
        yandex_api_key="",
        yandex_folder_id="folder-id",
        yandex_agent_id="agent-id",
    )

    with pytest.raises(LLMProviderConfigurationError, match="Incomplete Yandex LLM configuration"):
        build_llm_client(settings)


def test_yandex_compatible_client_info_logs_do_not_include_full_payload(caplog) -> None:
    caplog.set_level(logging.INFO, logger="app.infrastructure.llm_client")
    client = YandexCompatibleLLMClient(
        base_url="https://ai.api.cloud.yandex.net/v1",
        api_key="super-secret-token",
        folder_id="folder-id",
        agent_id="agent-id",
        transport=lambda *_: FakeResponse(
            {
                "output_text": json.dumps(
                    {
                        "answer": "Understood. How long does that take?",
                        "interest_delta": 4,
                        "state_patch": {
                            "tone": "neutral",
                            "trust_delta": 2,
                            "irritation_delta": -1,
                            "urgency_delta": 1,
                            "add_open_objections": [],
                            "remove_open_objections": [],
                            "add_known_pains": [],
                            "add_buying_signals": [],
                            "add_red_flags": [],
                        },
                        "stage": "need_discovery",
                        "internal_notes": "Retry returned valid JSON.",
                    }
                )
            }
        ),
    )

    client.generate_client_turn(sample_payload())

    info_messages = [record.getMessage() for record in caplog.records if record.levelno == logging.INFO]
    assert any("payload_size" in message for message in info_messages)
    assert all("How do you track conversion losses now?" not in message for message in info_messages)
    assert all("super-secret-token" not in message for message in info_messages)


def test_parse_llm_turn_response_accepts_json_in_markdown_fence() -> None:
    raw = """```json
    {
      "answer": "Fence response",
      "interest_delta": 2,
      "state_patch": {
        "tone": "neutral",
        "trust_delta": 1,
        "irritation_delta": 0,
        "urgency_delta": 0,
        "add_open_objections": [],
        "remove_open_objections": [],
        "add_known_pains": [],
        "add_buying_signals": [],
        "add_red_flags": []
      },
      "stage": "need_discovery",
      "internal_notes": "ok"
    }
    ```"""
    parsed = parse_llm_turn_response(raw)
    assert parsed.answer == "Fence response"


def test_parse_llm_turn_response_accepts_wrapped_json_with_braces_inside_strings() -> None:
    raw = (
        "Provider text before JSON.\n"
        '{"answer":"Value mentions {CRM} safely.","interest_delta":1,'
        '"state_patch":{"tone":"neutral","trust_delta":1,"irritation_delta":0,"urgency_delta":0,'
        '"add_open_objections":[],"remove_open_objections":[],"add_known_pains":[],"add_buying_signals":[],"add_red_flags":[]},'
        '"stage":"need_discovery","internal_notes":"wrapped"}\n'
        "Provider text after JSON."
    )
    parsed = parse_llm_turn_response(raw)
    assert parsed.answer == "Value mentions {CRM} safely."


def test_parse_llm_turn_response_rejects_invalid_json_with_controlled_error() -> None:
    with pytest.raises(LLMClientError, match="does not contain valid JSON"):
        parse_llm_turn_response("no structured payload here")


def test_llm_turn_response_schema_contains_key_fields() -> None:
    schema = llm_turn_response_schema()
    properties = schema["properties"]

    assert "answer" in properties
    assert "interest_delta" in properties
    assert "state_patch" in properties
    assert "stage" in properties
    assert "internal_notes" in properties


def test_llm_turn_response_schema_forbids_additional_properties_at_top_level() -> None:
    schema = llm_turn_response_schema()
    assert schema["additionalProperties"] is False


def test_build_strict_json_schema_reflects_model_shape() -> None:
    class DerivedResponse(BaseModel):
        model_config = ConfigDict(extra="forbid")

        answer: str
        new_field: int

    schema = build_strict_json_schema(DerivedResponse)
    assert "new_field" in schema["properties"]
    assert "new_field" in schema["required"]
