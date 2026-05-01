from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.access.repository import AccessRepository
from app.access.service import AccessService
from app.identity.repository import IdentityRepository
from app.identity.service import AuthService, AuthenticationError, CurrentSession
from app.infrastructure.config import Settings
from app.infrastructure.db import get_db_session


def get_auth_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_identity_repository(
    db_session: Session = Depends(get_db_session),
) -> IdentityRepository:
    return IdentityRepository(db_session)


def get_access_repository(
    db_session: Session = Depends(get_db_session),
) -> AccessRepository:
    return AccessRepository(db_session)


def get_access_service(
    access_repository: AccessRepository = Depends(get_access_repository),
) -> AccessService:
    return AccessService(access_repository)


def get_auth_service(
    identity_repository: IdentityRepository = Depends(get_identity_repository),
    access_repository: AccessRepository = Depends(get_access_repository),
    settings: Settings = Depends(get_auth_settings),
) -> AuthService:
    return AuthService(
        identity_repository=identity_repository,
        access_repository=access_repository,
        settings=settings,
    )


def get_current_session(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_auth_settings),
) -> CurrentSession:
    try:
        return auth_service.authenticate_session(request.cookies.get(settings.auth_cookie_name))
    except AuthenticationError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)) from error


def require_current_user(
    current_session: CurrentSession = Depends(get_current_session),
) -> CurrentSession:
    return current_session
