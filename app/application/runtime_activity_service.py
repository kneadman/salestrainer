from __future__ import annotations

import logging
from uuid import UUID

from app.application.session_service import TrainingSessionService
from app.domain.errors import SessionHistorySyncPendingError, SessionNotActiveError, SessionNotFoundError
from app.history.service import HistoryService

logger = logging.getLogger(__name__)


class RuntimeActivityService:
    def __init__(self, session_service: TrainingSessionService, history_service: HistoryService) -> None:
        """Coordinate runtime TTL and durable activity refresh for active sessions."""
        self._session_service = session_service
        self._history_service = history_service

    def touch_active_session(self, session_id: str) -> None:
        """Refresh durable activity first, then runtime TTL, for one active session."""
        try:
            durable_session_id = UUID(session_id)
        except ValueError as error:
            raise SessionNotFoundError("Session not found.") from error

        self._session_service.resume_session(session_id)
        try:
            touched = self._history_service.touch_runtime_session_activity(durable_session_id)
        except Exception as error:
            logger.warning("durable_session_touch_failed session_id=%s", session_id, exc_info=True)
            raise SessionHistorySyncPendingError(
                "Session activity could not be persisted. Please retry this action."
            ) from error
        if not touched:
            raise SessionNotActiveError(f"Session '{session_id}' is not active in durable history.")

        self._session_service.touch_session(session_id)
