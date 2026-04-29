from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domain.models import ClientState, LLMTurnResponse, PersonaProfile, StatePatch, TrainingSessionState


def test_client_state_rejects_invalid_score_ranges() -> None:
    with pytest.raises(ValidationError):
        ClientState(
            tone="cold",
            trust=101,
            irritation=0,
            urgency=0,
            price_sensitivity=0,
        )


def test_llm_turn_response_rejects_invalid_interest_delta() -> None:
    with pytest.raises(ValidationError):
        LLMTurnResponse(
            answer="ok",
            interest_delta=16,
            state_patch=StatePatch(),
            stage="first_contact",
        )


def test_training_session_state_contains_required_fields() -> None:
    session = TrainingSessionState(
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
        interest_score=25,
        stage="first_contact",
        client_state=ClientState(
            tone="cold",
            trust=20,
            irritation=10,
            urgency=20,
            price_sensitivity=50,
        ),
        summary="started",
        recent_turns=[],
        turn_count=0,
        state_version=1,
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
    )
    assert session.turn_count == 0

