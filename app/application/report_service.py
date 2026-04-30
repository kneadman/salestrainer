from __future__ import annotations

from datetime import UTC, datetime
import logging

from app.application.report_formatter import build_human_report
from app.domain.errors import SessionNotFoundError
from app.infrastructure.session_repository import SessionRepository

logger = logging.getLogger(__name__)


class ReportService:
    def __init__(self, repository: SessionRepository) -> None:
        self._repository = repository

    def finish_session(self, session_id: str) -> str:
        session = self._repository.get(session_id)
        if session is None:
            raise SessionNotFoundError(f"Session '{session_id}' not found.")
        expected_version = session.state_version
        if session.status != "finished":
            session.status = "finished"
            session.state_version = expected_version + 1
            session.updated_at = datetime.now(tz=UTC)
            self._repository.save(session, expected_version=expected_version)
            logger.info(
                "session_finished session_id=%s turns=%s final_interest=%s final_stage=%s",
                session.session_id,
                session.turn_count,
                session.interest_score,
                session.stage,
            )
        return self.generate_report(session_id)

    def generate_report(self, session_id: str) -> str:
        session = self._repository.get(session_id)
        if session is None:
            raise SessionNotFoundError(f"Session '{session_id}' not found.")
        return build_human_report(session)
