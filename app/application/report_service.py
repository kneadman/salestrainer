from __future__ import annotations

from datetime import UTC, datetime
import logging

from app.domain.errors import SessionNotFoundError
from app.domain.interest import interest_band
from app.infrastructure.session_repository import SessionRepository

logger = logging.getLogger(__name__)


class ReportService:
    def __init__(self, repository: SessionRepository) -> None:
        self._repository = repository

    def finish_session(self, session_id: str) -> str:
        session = self._repository.get(session_id)
        if session is None:
            raise SessionNotFoundError(f"Session '{session_id}' not found.")
        if session.status != "finished":
            session.status = "finished"
            session.state_version += 1
            session.updated_at = datetime.now(tz=UTC)
            self._repository.save(session)
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
        objections = ", ".join(session.client_state.open_objections) or "none"
        signals = ", ".join(session.client_state.buying_signals) or "none"
        return (
            f"Session {session.session_id}\n"
            f"Scenario: {session.scenario_id}\n"
            f"Persona: {session.persona.display_name}\n"
            f"Turns: {session.turn_count}\n"
            f"Final interest: {session.interest_score}/100 ({interest_band(session.interest_score)})\n"
            f"Final stage: {session.stage}\n"
            f"Open objections: {objections}\n"
            f"Buying signals: {signals}\n"
            f"Summary: {session.summary}"
        )
