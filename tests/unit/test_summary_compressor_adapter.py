from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.application.summary_compressor import FakeSummaryCompressor
from app.domain.errors import LLMProviderConfigurationError
from app.domain.models import ClientState, PersonaProfile, TrainingSessionState, Turn
from tests.unit._persona_fixtures import valid_minimal_persona
from app.infrastructure.config import Settings
from app.infrastructure.summary_compressor import (
    OpenAICompatibleSummaryCompressor,
    YandexSummaryCompressor,
    build_summary_compressor,
    parse_summary_text,
)


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def model_dump(self) -> dict[str, object]:
        return self._payload


def make_session() -> TrainingSessionState:
    return TrainingSessionState(
        session_id=uuid4(),
        scenario_id="sales_audit_cold_outreach",
        status="active",
        persona=valid_minimal_persona(),
        interest_score=40,
        stage="need_discovery",
        client_state=ClientState(
            tone="neutral",
            trust=30,
            irritation=10,
            urgency=20,
            price_sensitivity=45,
            open_objections=["Need proof"],
            known_pains=["Lead leakage"],
            buying_signals=[],
            red_flags=[],
        ),
        summary="Existing summary.",
        recent_turns=[],
        turn_count=2,
        state_version=3,
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
    )


def make_turn() -> Turn:
    return Turn(
        index=1,
        manager_message="We start with a diagnostic.",
        client_answer="Why do you think we need this?",
        interest_before=25,
        interest_delta=4,
        interest_after=29,
        stage_before="first_contact",
        stage_after="value_clarification",
        created_at=datetime.now(tz=UTC),
    )


def test_parse_summary_text_from_prompt_response_payload() -> None:
    raw = {
        "output_text": "Compact summary of earlier turns.",
        "output": [{"type": "message", "content": []}],
    }
    assert parse_summary_text(raw) == "Compact summary of earlier turns."


def test_parse_summary_text_from_chat_completions_payload() -> None:
    raw = {
        "choices": [
            {"index": 0, "message": {"role": "assistant", "content": "Compressed summary from router."}}
        ]
    }
    assert parse_summary_text(raw) == "Compressed summary from router."


def test_openai_compatible_summary_compressor_uses_router_payload() -> None:
    calls: list[dict[str, object]] = []

    def transport(request_payload: dict[str, object]) -> FakeResponse:
        calls.append(request_payload)
        return FakeResponse(
            {"choices": [{"index": 0, "message": {"content": "Compressed summary from router."}}]}
        )

    compressor = OpenAICompatibleSummaryCompressor(
        base_url="https://router.example.test/v1",
        api_key="router-key",
        model="summary/model",
        system_prompt="Summarize.",
        transport=transport,
    )

    summary = compressor.compress(
        existing_summary="Existing summary.",
        overflow_turns=[make_turn()],
        session=make_session(),
        latest_internal_notes="Client is slightly warmer.",
    )

    assert summary == "Compressed summary from router."
    assert calls[0]["model"] == "summary/model"
    assert "Overflow turns:" in calls[0]["input"]


def test_yandex_summary_compressor_retries_then_succeeds() -> None:
    calls: list[dict[str, object]] = []

    def transport(request_payload):
        calls.append(request_payload)
        if len(calls) == 1:
            return ""
        return FakeResponse({"output_text": "Compressed summary from LLM."})

    compressor = YandexSummaryCompressor(
        base_url="https://ai.api.cloud.yandex.net/v1",
        api_key="token",
        folder_id="folder-id",
        agent_id="agent-id",
        transport=transport,
    )

    summary = compressor.compress(
        existing_summary="Existing summary.",
        overflow_turns=[make_turn()],
        session=make_session(),
        latest_internal_notes="Client is slightly warmer.",
    )

    assert summary == "Compressed summary from LLM."
    assert len(calls) == 2
    assert calls[0]["prompt"]["id"] == "agent-id"
    assert "Overflow turns:" in calls[0]["input"]
    assert "Previous answer was invalid" in calls[1]["input"]


def test_yandex_summary_compressor_falls_back_to_fake_compressor() -> None:
    compressor = YandexSummaryCompressor(
        base_url="https://ai.api.cloud.yandex.net/v1",
        api_key="token",
        folder_id="folder-id",
        agent_id="agent-id",
        transport=lambda *_: "",
        fallback_compressor=FakeSummaryCompressor(),
    )

    summary = compressor.compress(
        existing_summary="Existing summary.",
        overflow_turns=[make_turn()],
        session=make_session(),
        latest_internal_notes="Client is slightly warmer.",
    )

    assert "Existing summary." in summary
    assert "T1:" in summary


def test_build_summary_compressor_defaults_to_fake_without_yandex_backend() -> None:
    compressor = build_summary_compressor(Settings(llm_backend="fake"))
    assert isinstance(compressor, FakeSummaryCompressor)


def test_build_summary_compressor_raises_when_config_is_incomplete_and_fallback_is_disabled() -> None:
    settings = Settings(
        app_env="prod",
        llm_backend="yandex_compatible",
        allow_fake_llm_fallback=False,
        yandex_api_key="",
        yandex_folder_id="folder-id",
        yandex_agent_id="agent-id",
    )

    with pytest.raises(LLMProviderConfigurationError, match="Incomplete summary compressor configuration"):
        build_summary_compressor(settings)


def test_summary_compressor_info_logs_do_not_include_full_payload(caplog) -> None:
    caplog.set_level(logging.INFO, logger="app.infrastructure.summary_compressor")
    compressor = YandexSummaryCompressor(
        base_url="https://ai.api.cloud.yandex.net/v1",
        api_key="super-secret-token",
        folder_id="folder-id",
        agent_id="agent-id",
        transport=lambda *_: FakeResponse({"output_text": "Compressed summary from LLM."}),
    )

    compressor.compress(
        existing_summary="Existing summary with internal data.",
        overflow_turns=[make_turn()],
        session=make_session(),
        latest_internal_notes="Client is slightly warmer.",
    )

    info_messages = [record.getMessage() for record in caplog.records if record.levelno == logging.INFO]
    assert any("payload_size" in message for message in info_messages)
    assert all("Existing summary with internal data." not in message for message in info_messages)
    assert all("super-secret-token" not in message for message in info_messages)
