from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.history.repository import HistoryRepository
from app.history.service import HistoryService
from app.infrastructure.db import get_db_session


def get_history_repository(db_session: Session = Depends(get_db_session)) -> HistoryRepository:
    """Build a history repository on the request-scoped database session."""
    return HistoryRepository(db_session)


def get_history_service(
    request: Request,
    repository: HistoryRepository = Depends(get_history_repository),
) -> HistoryService:
    """Build the persistent history service for API route handlers."""
    settings = request.app.state.settings
    return HistoryService(repository, inactive_ttl_seconds=settings.session_ttl_seconds)
