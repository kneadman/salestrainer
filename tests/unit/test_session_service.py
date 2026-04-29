import pytest

from app.application.session_service import TrainingSessionService
from app.domain.errors import SessionNotFoundError
from app.infrastructure.session_repository import InMemorySessionRepository


def test_resume_session_returns_active_session() -> None:
    repository = InMemorySessionRepository()
    service = TrainingSessionService(repository)
    session = service.start_session("sales_audit_cold_outreach", "owner")

    resumed = service.resume_session(str(session.session_id))

    assert resumed.session_id == session.session_id
    assert resumed.status == "active"


def test_resume_session_rejects_missing_session() -> None:
    repository = InMemorySessionRepository()
    service = TrainingSessionService(repository)

    with pytest.raises(SessionNotFoundError, match="not found"):
        service.resume_session("missing-session-id")
