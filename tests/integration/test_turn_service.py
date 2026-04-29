from app.application.session_service import TrainingSessionService
from app.application.summary_compressor import FakeSummaryCompressor
from app.application.turn_service import TurnService
from app.domain.models import LLMTurnResponse, StatePatch
from app.infrastructure.llm_client import FakeLLMClient
from app.infrastructure.session_repository import InMemorySessionRepository


def test_turn_service_updates_session_and_recent_turns() -> None:
    repository = InMemorySessionRepository()
    session_service = TrainingSessionService(repository)
    turn_service = TurnService(repository, FakeLLMClient(), recent_turn_limit=6)
    session = session_service.start_session("sales_audit_cold_outreach", "owner")

    result = turn_service.process_message(
        str(session.session_id),
        "We usually start with a diagnostic of conversion losses. How do you track drop-off now?",
    )

    updated_session = repository.get(str(session.session_id))
    assert updated_session is not None
    assert updated_session.turn_count == 1
    assert updated_session.state_version == 2
    assert len(updated_session.recent_turns) == 1
    assert updated_session.recent_turns[0].client_answer == result.client_answer
    assert updated_session.interest_score == result.interest_after
    assert updated_session.summary


class AggressiveSuccessLLMClient:
    def generate_client_turn(self, payload):
        return LLMTurnResponse(
            answer="Let's move forward.",
            interest_delta=2,
            state_patch=StatePatch(
                tone="ready_next_step",
                trust_delta=2,
                irritation_delta=0,
                urgency_delta=1,
                add_buying_signals=[],
            ),
            stage="finished_success",
            internal_notes="Provider jumped too far.",
        )


def test_turn_service_rejects_invalid_finished_success_transition() -> None:
    repository = InMemorySessionRepository()
    session_service = TrainingSessionService(repository)
    turn_service = TurnService(repository, AggressiveSuccessLLMClient(), recent_turn_limit=6)
    session = session_service.start_session("sales_audit_cold_outreach", "owner")

    result = turn_service.process_message(str(session.session_id), "Tell me more.")

    assert result.stage_after == "first_contact"


class AliasStageLLMClient:
    def generate_client_turn(self, payload):
        return LLMTurnResponse(
            answer="Привет. Я сейчас занят, если что-то конкретное — пишите.",
            interest_delta=-5,
            state_patch=StatePatch(
                tone="cold",
                trust_delta=0,
                irritation_delta=5,
                urgency_delta=0,
                add_open_objections=["Нет времени на общие разговоры"],
                add_red_flags=["Раздражен общим подходом"],
            ),
            stage="initial_contact",
            internal_notes="Provider returned alias stage.",
        )


def test_turn_service_normalizes_provider_stage_aliases() -> None:
    repository = InMemorySessionRepository()
    session_service = TrainingSessionService(repository)
    turn_service = TurnService(repository, AliasStageLLMClient(), recent_turn_limit=6)
    session = session_service.start_session("accounting_outsource_cold_outreach", "owner")

    result = turn_service.process_message(str(session.session_id), "Здравствуйте")

    assert result.stage_before == "first_contact"
    assert result.stage_after == "first_contact"


def test_turn_service_compresses_overflow_turns_into_summary() -> None:
    repository = InMemorySessionRepository()
    session_service = TrainingSessionService(repository)
    turn_service = TurnService(
        repository,
        FakeLLMClient(),
        recent_turn_limit=2,
        summary_compressor=FakeSummaryCompressor(),
    )
    session = session_service.start_session("sales_audit_cold_outreach", "owner")

    turn_service.process_message(str(session.session_id), "How do you track conversion losses now?")
    turn_service.process_message(str(session.session_id), "What does your funnel look like by stage?")
    turn_service.process_message(str(session.session_id), "Where do deals drop most often?")

    updated_session = repository.get(str(session.session_id))
    assert updated_session is not None
    assert len(updated_session.recent_turns) == 2
    assert "T1:" in updated_session.summary
