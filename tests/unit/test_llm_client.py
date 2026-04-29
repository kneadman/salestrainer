from __future__ import annotations

import json

from app.domain.models import LLMTurnInput
from app.domain.personas import get_persona
from app.domain.scenarios import get_scenario
from app.infrastructure.llm_client import (
    FakeLLMClient,
    YandexCompatibleLLMClient,
    build_llm_client,
    parse_llm_turn_response,
)
from app.infrastructure.config import Settings


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def model_dump(self) -> dict[str, object]:
        return self._payload


def sample_payload() -> LLMTurnInput:
    return LLMTurnInput(
        task="simulate_next_client_reply",
        scenario=get_scenario("sales_audit_cold_outreach"),
        persona=get_persona("owner"),
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
            },
        },
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
    assert input_payload["scenario"]["id"] == "sales_audit_cold_outreach"
    assert input_payload["persona"]["id"] == "owner"
    assert input_payload["current_state"]["stage"] == "first_contact"
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


def test_build_llm_client_uses_fake_when_provider_config_is_incomplete() -> None:
    settings = Settings(
        llm_backend="yandex_compatible",
        yandex_api_key="",
        yandex_folder_id="folder-id",
        yandex_agent_id="agent-id",
    )
    client = build_llm_client(settings)
    assert isinstance(client, FakeLLMClient)
