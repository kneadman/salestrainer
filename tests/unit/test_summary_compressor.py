from datetime import UTC, datetime
from uuid import uuid4

from app.application.summary_compressor import FakeSummaryCompressor
from app.domain.models import ClientState, PersonaProfile, TrainingSessionState, Turn


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
        interest_score=48,
        stage="need_discovery",
        client_state=ClientState(
            tone="neutral",
            trust=35,
            irritation=10,
            urgency=20,
            price_sensitivity=45,
            open_objections=["Need proof"],
            known_pains=["Lead leakage"],
            buying_signals=["Asked follow-up"],
            red_flags=[],
        ),
        summary="Initial summary.",
        recent_turns=[],
        turn_count=2,
        state_version=3,
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
    )


def test_fake_summary_compressor_carries_existing_summary_and_turn_facts() -> None:
    compressor = FakeSummaryCompressor()
    session = make_session()
    overflow_turns = [
        Turn(
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
    ]

    summary = compressor.compress(
        existing_summary=session.summary,
        overflow_turns=overflow_turns,
        session=session,
        latest_internal_notes="Client became a bit more open.",
    )

    assert "Initial summary." in summary
    assert "T1:" in summary
    assert "interest=25->29" in summary
    assert "Current state: interest=48/100" in summary
