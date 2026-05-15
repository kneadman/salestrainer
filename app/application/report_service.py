from __future__ import annotations

from datetime import UTC, datetime
import logging

from app.application.judgement_service import JudgementService
from app.application.report_formatter import build_human_report
from app.domain.errors import SessionNotFoundError
from app.domain.models import TrainingSessionState
from app.infrastructure.session_repository import SessionRepository

logger = logging.getLogger(__name__)


class ReportService:
    def __init__(
        self,
        repository: SessionRepository,
        judgement_service: JudgementService | None = None,
    ) -> None:
        """Keep runtime session access and an optional post-finish judgement service."""
        self._repository = repository
        self._judgement_service = judgement_service

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
        """Return the current human-readable report text without changing existing flow."""
        session = self._repository.get(session_id)
        if session is None:
            raise SessionNotFoundError(f"Session '{session_id}' not found.")
        return self.generate_report_for_session(session)

    def generate_report_for_session(self, session: TrainingSessionState) -> str:
        """Return a human-readable report for an already loaded session snapshot."""
        return build_human_report(session)

    def generate_report_payload(self, session_id: str) -> dict[str, object] | None:
        """Return an optional structured judge payload for persistence or future consumers."""
        if self._judgement_service is None:
            return None
        session = self._repository.get(session_id)
        if session is None:
            raise SessionNotFoundError(f"Session '{session_id}' not found.")
        return self.generate_report_payload_for_session(session)

    def generate_report_payload_for_session(self, session: TrainingSessionState) -> dict[str, object] | None:
        """Return structured judge payload for an already loaded session snapshot."""
        if self._judgement_service is None:
            return None
        judgement = self._judgement_service.judge_session(session)
        return judgement.model_dump(mode="json")

    def generate_report_payload_safely(self, session_id: str) -> dict[str, object] | None:
        """Generate optional judge payload without breaking the core finish/report flow on provider errors."""
        try:
            return self.generate_report_payload(session_id)
        except Exception:
            logger.warning("judge_payload_generation_failed session_id=%s", session_id, exc_info=True)
            return None

    def generate_report_payload_safely_for_session(self, session: TrainingSessionState) -> dict[str, object] | None:
        """Generate optional judge payload from a provided snapshot without breaking finish flow."""
        try:
            return self.generate_report_payload_for_session(session)
        except Exception:
            logger.warning("judge_payload_generation_failed session_id=%s", session.session_id, exc_info=True)
            return None
