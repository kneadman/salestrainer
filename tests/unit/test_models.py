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
            target_action="book_meeting",
            current_business_context="Growing B2B company.",
            business_facts=["10-50 employees", "Expanding sales team."],
            cares_about=["growth", "control", "ROI"],
            current_solution="Excel + manual process",
            alternative_solutions=[
                "статус-кво: продолжать как сейчас",
                "buy a CRM",
            ],
            information_gaps=[
                "Thinks implementation takes months.",
                "Does not know about pilot programs.",
            ],
            latent_pains=["Leads are slipping through.", "Reporting is manual."],
            buying_motivation=["Close more deals.", "Reduce manual work."],
            decision_criteria=["Ease of use", "Price", "Support"],
            hidden_constraints=["Limited budget this quarter."],
            typical_objections=["We already have a process.", "Too busy to change."],
            proof_sensitivity=["case studies", "free trial"],
            call_scoring_criteria=["discovery", "objection handling", "next step"],
            communication_style="Direct and brief.",
            initial_openness=25,
            starting_interest=25,
            price_sensitivity=50,
            urgency=20,
            trust_baseline=20,
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
        public_brief="brief",
        turn_count=0,
        state_version=1,
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
    )
    assert session.turn_count == 0
    assert session.turns == []
