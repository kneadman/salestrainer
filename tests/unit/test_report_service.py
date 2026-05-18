from datetime import UTC, datetime
from uuid import uuid4

from app.application.judgement_service import JudgementService
from app.application.report_service import ReportService
from app.domain.judgement_models import JudgeSessionOutput
from app.domain.models import ClientState, PersonaProfile, TrainingSessionState
from tests.unit._persona_fixtures import valid_minimal_persona
from app.infrastructure.judge_client import FakeJudgeClient
from app.infrastructure.session_repository import InMemorySessionRepository


def _create_finished_session(repository: InMemorySessionRepository) -> str:
    """Persist one finished session in the in-memory repository for report service tests."""
    now = datetime.now(tz=UTC)
    session = TrainingSessionState(
        session_id=uuid4(),
        scenario_id="sales_audit_cold_outreach",
        status="finished",
        persona=valid_minimal_persona(
            id="generated_persona",
            display_name="Unknown B2B contact",
            behavior_model="analytical_and_cautious",
        ),
        interest_score=52,
        stage="need_discovery",
        client_state=ClientState(
            tone="neutral",
            trust=38,
            irritation=10,
            urgency=24,
            price_sensitivity=40,
        ),
        summary="Manager asked several broad questions but did not deepen discovery enough.",
        turns=[],
        turn_evaluations=[],
        recent_turns=[],
        turn_count=0,
        state_version=2,
        created_at=now,
        updated_at=now,
    )
    repository.create(session)
    return str(session.session_id)


def test_report_service_without_judgement_service_works_as_before() -> None:
    """Human-readable report generation should remain available without a judge service."""
    repository = InMemorySessionRepository()
    session_id = _create_finished_session(repository)
    service = ReportService(repository)

    report = service.generate_report(session_id)
    payload = service.generate_report_payload(session_id)

    assert isinstance(report, str)
    assert payload is None


def test_report_service_with_judgement_service_returns_report_payload() -> None:
    """Structured report payload should be available when judgement service is configured."""
    repository = InMemorySessionRepository()
    session_id = _create_finished_session(repository)
    service = ReportService(
        repository,
        judgement_service=JudgementService(FakeJudgeClient()),
    )

    payload = service.generate_report_payload(session_id)

    assert payload is not None
    assert payload["schema_version"] == 1
    assert "overall_score" in payload
    assert payload["bento_blocks"]
    assert payload["skill_scores"]


class CrashingJudgementService:
    def judge_session(self, session: TrainingSessionState) -> JudgeSessionOutput:
        """Raise a deterministic error to verify the fail-open wrapper."""
        raise RuntimeError("judge exploded")


def test_report_service_generate_report_payload_safely_returns_none_on_judge_error() -> None:
    """Safe payload generation should not propagate judge failures into the caller."""
    repository = InMemorySessionRepository()
    session_id = _create_finished_session(repository)
    service = ReportService(
        repository,
        judgement_service=CrashingJudgementService(),
    )

    payload = service.generate_report_payload_safely(session_id)

    assert payload is None
