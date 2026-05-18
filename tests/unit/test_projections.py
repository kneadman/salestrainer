from app.application.projections import build_session_public_dto, build_turn_public_dto
from app.application.session_service import TrainingSessionService
from app.application.turn_service import TurnService
from app.domain.models import RevealedFact
from app.infrastructure.llm_client import FakeLLMClient
from app.infrastructure.session_repository import InMemorySessionRepository

FACT_LABELS = {
    "role": "Роль",
    "authority": "Полномочия",
    "current_process": "Текущий процесс",
    "decision_criterion": "Критерии решения",
    "constraint": "Ограничения",
    "buying_signal": "Сигналы интереса",
    "pain": "Выявленные боли",
    "objection": "Возражения",
}


def test_public_projection_hides_internal_persona_structure_and_exposes_public_state() -> None:
    repository = InMemorySessionRepository()
    session_service = TrainingSessionService(repository)
    turn_service = TurnService(repository, FakeLLMClient())
    session = session_service.start_session("sales_audit_cold_outreach", "owner")
    turn_service.process_message(str(session.session_id), "How do you track conversion losses now?")
    updated = repository.get(str(session.session_id))
    assert updated is not None

    public_session = build_session_public_dto(updated)
    public_turns = build_turn_public_dto(updated)

    assert "persona_name" not in public_session.model_dump()
    assert public_session.public_brief
    assert public_session.client_state_public["trust"] == updated.client_state.trust
    assert "visible_objections" in public_session.client_state_public
    assert "revealed_facts" in public_session.client_state_public
    assert "known_pains" not in public_session.client_state_public
    assert "discovered_role" not in public_session.client_state_public
    assert "discovered_authority_level" not in public_session.client_state_public
    assert "discovered_decision_criteria" not in public_session.client_state_public
    assert "discovered_constraints" not in public_session.client_state_public
    assert "discovered_current_process" not in public_session.client_state_public
    assert public_session.client_state_public["revealed_facts"] == [
        fact.model_dump(mode="json")
        for fact in updated.client_state.revealed_facts
    ]
    assert public_session.facts_panel.items == [
        {
            "category": fact.category,
            "label": FACT_LABELS[fact.category],
            "text": fact.text,
            "turn_index": fact.turn_index,
        }
        for fact in updated.client_state.revealed_facts
    ]
    assert updated.persona.role not in public_session.model_dump_json()
    assert updated.persona.authority_level not in public_session.model_dump_json()
    for hidden_value in updated.persona.latent_pains + updated.persona.hidden_constraints:
        assert hidden_value not in public_session.model_dump_json()
    assert len(public_turns) == 1
    assert public_turns[0].client_answer


def test_public_projection_does_not_expose_technical_state_keys() -> None:
    """Public DTO must not contain raw internal state keys like discovered_* or known_pains."""
    repository = InMemorySessionRepository()
    session_service = TrainingSessionService(repository)
    turn_service = TurnService(repository, FakeLLMClient())
    session = session_service.start_session("sales_audit_cold_outreach", "owner")
    turn_service.process_message(str(session.session_id), "How do you track conversion losses now?")
    updated = repository.get(str(session.session_id))
    assert updated is not None

    public_session = build_session_public_dto(updated)
    public_json = public_session.model_dump_json()

    # Legacy technical keys must not appear in public DTO
    assert "known_pains" not in public_json
    assert "discovered_role" not in public_json
    assert "discovered_authority_level" not in public_json
    assert "discovered_decision_criteria" not in public_json
    assert "discovered_constraints" not in public_json
    assert "discovered_current_process" not in public_json
    assert "state_patch" not in public_json
    assert "hidden_profile" not in public_json
    assert "latent_pains" not in public_json

    # Facts panel must expose only the safe category/label/text/turn_index shape
    for item in public_session.facts_panel.items:
        assert set(item.model_dump().keys()) == {"category", "label", "text", "turn_index"}
        assert item.label in FACT_LABELS.values()
