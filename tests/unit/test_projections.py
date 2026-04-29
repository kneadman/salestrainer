from app.application.projections import build_session_public_dto, build_turn_public_dto
from app.application.session_service import TrainingSessionService
from app.application.turn_service import TurnService
from app.infrastructure.llm_client import FakeLLMClient
from app.infrastructure.session_repository import InMemorySessionRepository


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

    assert public_session.persona_name == "Owner"
    assert "visible_objections" in public_session.client_state_public
    assert len(public_turns) == 1
    assert public_turns[0].client_answer
