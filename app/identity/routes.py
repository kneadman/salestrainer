from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel

from app.identity.dependencies import get_auth_service, get_auth_settings, get_current_session
from app.identity.models import User
from app.identity.service import AuthService, AuthenticationError, CurrentSession
from app.infrastructure.config import Settings

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class ClientAccountDTO(BaseModel):
    id: UUID
    name: str
    slug: str


class AuthUserDTO(BaseModel):
    id: UUID
    email: str
    role: str
    client_account: ClientAccountDTO


class AuthUserResponse(BaseModel):
    user: AuthUserDTO


@router.post("/login", response_model=AuthUserResponse)
def login(
    request_body: LoginRequest,
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_auth_settings),
) -> AuthUserResponse:
    try:
        login_result = auth_service.login(
            email=request_body.email,
            password=request_body.password,
            ip_address=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    except AuthenticationError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)) from error

    response.set_cookie(
        key=settings.auth_cookie_name,
        value=login_result.raw_token,
        max_age=settings.auth_session_ttl_seconds,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        path="/",
    )
    return AuthUserResponse(user=_user_dto(login_result.user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    current_session: CurrentSession = Depends(get_current_session),
    auth_service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_auth_settings),
) -> Response:
    response.status_code = status.HTTP_204_NO_CONTENT
    auth_service.logout(
        current_session=current_session,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    response.delete_cookie(
        key=settings.auth_cookie_name,
        path="/",
        secure=settings.auth_cookie_secure,
        httponly=True,
        samesite=settings.auth_cookie_samesite,
    )
    return response


@router.get("/me", response_model=AuthUserResponse)
def me(current_session: CurrentSession = Depends(get_current_session)) -> AuthUserResponse:
    return AuthUserResponse(user=_user_dto(current_session.user))


def _user_dto(user: User) -> AuthUserDTO:
    return AuthUserDTO(
        id=user.id,
        email=user.email,
        role=user.role,
        client_account=ClientAccountDTO(
            id=user.client_account.id,
            name=user.client_account.name,
            slug=user.client_account.slug,
        ),
    )


def _client_ip(request: Request) -> str | None:
    if request.client is None:
        return None
    return request.client.host
