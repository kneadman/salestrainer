from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.identity.dependencies import require_internal_admin
from app.identity.service import CurrentSession
from app.infrastructure.config import Settings
from app.infrastructure.db import get_db_session
from app.internal_admin.service import InternalAdminService


def get_internal_admin_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_internal_admin_service(
    db_session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_internal_admin_settings),
) -> InternalAdminService:
    return InternalAdminService(db_session, settings=settings)


def require_internal_admin_session(
    current_session: CurrentSession = Depends(require_internal_admin),
) -> CurrentSession:
    return current_session
