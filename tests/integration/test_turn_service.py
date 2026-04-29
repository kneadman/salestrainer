from app.application.session_service import TrainingSessionService
from app.application.summary_compressor import FakeSummaryCompressor
from app.application.turn_service import TurnService
from app.domain.errors import StateVersionConflictError
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
    assert len(updated_session.turns) == 1
    assert len(updated_session.recent_turns) == 1
    assert updated_session.recent_turns[0].client_answer == result.client_answer
    assert updated_session.interest_score == result.interest_after
    assert updated_session.summary
    assert updated_session.turn_evaluations


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
    assert len(updated_session.turns) == 3
    assert len(updated_session.recent_turns) == 2
    assert "T1:" in updated_session.summary


def test_turn_service_discovers_role_and_pain_from_questions() -> None:
    repository = InMemorySessionRepository()
    session_service = TrainingSessionService(repository)
    turn_service = TurnService(repository, FakeLLMClient(), recent_turn_limit=6)
    session = session_service.start_session()

    turn_service.process_message(str(session.session_id), "Кто вы и за что отвечаете?")
    turn_service.process_message(str(session.session_id), "Что у вас сейчас болит в процессе?")

    updated_session = repository.get(str(session.session_id))
    assert updated_session is not None
    assert updated_session.client_state.discovered_role is not None
    assert updated_session.client_state.discovered_pains


def test_turn_service_evaluator_penalizes_early_pressure() -> None:
    repository = InMemorySessionRepository()
    session_service = TrainingSessionService(repository)
    turn_service = TurnService(repository, FakeLLMClient(), recent_turn_limit=6)
    session = session_service.start_session()

    turn_service.process_message(str(session.session_id), "Давайте сразу купите, это срочно и только сегодня.")

    updated_session = repository.get(str(session.session_id))
    assert updated_session is not None
    assert updated_session.turn_evaluations[-1].pressure_score < 5


def test_turn_service_uses_state_version_and_rejects_stale_save() -> None:
    repository = InMemorySessionRepository()
    session_service = TrainingSessionService(repository)
    session = session_service.start_session("sales_audit_cold_outreach", "owner")

    stale_session = repository.get(str(session.session_id))
    fresh_session = repository.get(str(session.session_id))
    assert stale_session is not None
    assert fresh_session is not None

    fresh_session.summary = "fresh update"
    fresh_session.state_version += 1
    repository.save(fresh_session, expected_version=1)

    stale_session.summary = "stale update"
    stale_session.state_version += 1

    try:
        repository.save(stale_session, expected_version=1)
    except StateVersionConflictError:
        pass
    else:
        raise AssertionError("Expected stale save to fail with StateVersionConflictError.")
