from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.history.repository import HistoryRepository
from app.history.service import HistoryService
from app.infrastructure.db import get_db_session


def get_history_repository(db_session: Session = Depends(get_db_session)) -> HistoryRepository:
    """Build a history repository on the request-scoped database session."""
    return HistoryRepository(db_session)


def get_history_service(
    repository: HistoryRepository = Depends(get_history_repository),
) -> HistoryService:
    """Build the persistent history service for API route handlers."""
    return HistoryService(repository)
