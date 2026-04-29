from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

from app.application.summary_compressor import FakeSummaryCompressor
from app.domain.models import ClientState, PersonaProfile, TrainingSessionState, Turn
from app.infrastructure.config import Settings
from app.infrastructure.summary_compressor import (
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
        persona=PersonaProfile(
            id="owner",
            display_name="Owner",
            role="owner",
            industry="b2b",
            company_size="30-100",
            authority_level="final_decider",
            behavior_model="skeptical_but_rational",
        ),
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
