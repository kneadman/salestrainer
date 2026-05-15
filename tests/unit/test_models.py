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


def test_llm_turn_response_accepts_revealed_facts_and_rejects_extra_fact_fields() -> None:
    parsed = LLMTurnResponse.model_validate(
        {
            "answer": "I am the financial director.",
            "interest_delta": 2,
            "state_patch": {},
            "revealed_facts": [{"category": "role", "text": "financial director"}],
            "stage": "role_discovery",
        }
    )

    assert parsed.revealed_facts[0].category == "role"

    with pytest.raises(ValidationError):
        LLMTurnResponse.model_validate(
            {
                "answer": "I am the financial director.",
                "interest_delta": 2,
                "state_patch": {},
                "revealed_facts": [{"category": "role", "text": "financial director", "raw": "cfo"}],
                "stage": "role_discovery",
            }
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
    assert session.client_state.revealed_facts == []


def test_training_session_state_normalizes_legacy_persona_payload() -> None:
    now = datetime.now(tz=UTC)
    payload = {
        "session_id": uuid4(),
        "scenario_id": "first_contact_discovery",
        "status": "active",
        "persona": {
            "id": "legacy_owner",
            "display_name": "Legacy Owner",
            "role": "owner",
            "industry": "services",
            "company_size": "10-30",
            "authority_level": "final_decider",
            "behavior_model": "skeptical_but_rational",
            "target_action": "book_meeting",
            "current_business_context": "Legacy context.",
            "business_facts": ["Fact 1", "Fact 2"],
            "cares_about": ["control", "risk", "time"],
            "current_accounting_model": "owner_does_accounting",
            "legal_form": "ООО",
            "tax_system": "УСН",
            "accounting_software": "Excel",
            "accounting_software_mode": "local",
            "primary_docs_owner": "owner",
            "latent_pains": ["Pain 1", "Pain 2"],
            "buying_motivation": ["Motivation 1", "Motivation 2"],
            "decision_criteria": ["Criteria 1", "Criteria 2", "Criteria 3"],
            "hidden_constraints": ["Constraint 1"],
            "typical_objections": ["Objection 1", "Objection 2"],
            "proof_sensitivity": ["Proof 1", "Proof 2"],
            "call_scoring_criteria": ["Score 1", "Score 2", "Score 3"],
            "communication_style": "Direct and cautious.",
            "initial_openness": 25,
            "starting_interest": 25,
            "price_sensitivity": 50,
            "urgency": 20,
            "trust_baseline": 20,
        },
        "interest_score": 25,
        "stage": "first_contact",
        "client_state": {
            "tone": "cold",
            "trust": 20,
            "irritation": 10,
            "urgency": 20,
            "price_sensitivity": 50,
        },
        "summary": "started",
        "public_brief": "brief",
        "turns": [],
        "turn_evaluations": [],
        "recent_turns": [],
        "turn_count": 0,
        "state_version": 1,
        "created_at": now,
        "updated_at": now,
    }

    session = TrainingSessionState.model_validate(payload)

    assert session.persona.authority_level == "final_decider"
    assert session.persona.current_solution == "Excel + ручной учёт собственником"
    assert session.persona.alternative_solutions
    assert session.persona.information_gaps

    persona_dump = session.persona.model_dump()
    assert "current_accounting_model" not in persona_dump
    assert "legal_form" not in persona_dump
    assert "tax_system" not in persona_dump
    assert "accounting_software" not in persona_dump
    assert "accounting_software_mode" not in persona_dump
    assert "primary_docs_owner" not in persona_dump


def test_training_session_state_normalizes_legacy_non_decider_authority() -> None:
    now = datetime.now(tz=UTC)
    payload = {
        "session_id": uuid4(),
        "scenario_id": "first_contact_discovery",
        "status": "active",
        "persona": {
            "id": "legacy_gatekeeper",
            "display_name": "Legacy Gatekeeper",
            "role": "owner",
            "industry": "services",
            "company_size": "10-30",
            "authority_level": "gatekeeper",
            "behavior_model": "skeptical_but_rational",
            "target_action": "book_meeting",
            "current_business_context": "Legacy context.",
            "business_facts": ["Fact 1", "Fact 2"],
            "cares_about": ["control", "risk", "time"],
            "current_accounting_model": "outsourced_accounting",
            "legal_form": "ООО",
            "tax_system": "УСН",
            "accounting_software": "1С",
            "accounting_software_mode": "cloud",
            "primary_docs_owner": "accountant",
            "latent_pains": ["Pain 1", "Pain 2"],
            "buying_motivation": ["Motivation 1", "Motivation 2"],
            "decision_criteria": ["Criteria 1", "Criteria 2", "Criteria 3"],
            "hidden_constraints": ["Constraint 1"],
            "typical_objections": ["Objection 1", "Objection 2"],
            "proof_sensitivity": ["Proof 1", "Proof 2"],
            "call_scoring_criteria": ["Score 1", "Score 2", "Score 3"],
            "communication_style": "Direct and cautious.",
            "initial_openness": 25,
            "starting_interest": 25,
            "price_sensitivity": 50,
            "urgency": 20,
            "trust_baseline": 20,
        },
        "interest_score": 25,
        "stage": "first_contact",
        "client_state": {
            "tone": "cold",
            "trust": 20,
            "irritation": 10,
            "urgency": 20,
            "price_sensitivity": 50,
        },
        "summary": "started",
        "public_brief": "brief",
        "turns": [],
        "turn_evaluations": [],
        "recent_turns": [],
        "turn_count": 0,
        "state_version": 1,
        "created_at": now,
        "updated_at": now,
    }

    session = TrainingSessionState.model_validate(payload)

    assert session.persona.authority_level == "final_decider"
    assert session.persona.current_solution == "текущий бухгалтерский аутсорсер"
