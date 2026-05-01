from __future__ import annotations

import hmac
import secrets

from fastapi import Response

from app.infrastructure.config import Settings

CSRF_HEADER_NAME = "X-CSRF-Token"


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def set_csrf_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=token,
        max_age=settings.csrf_token_ttl_seconds,
        httponly=False,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        path="/",
    )


def clear_csrf_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.csrf_cookie_name,
        path="/",
        secure=settings.auth_cookie_secure,
        httponly=False,
        samesite=settings.auth_cookie_samesite,
    )


def csrf_tokens_match(cookie_token: str | None, header_token: str | None) -> bool:
    if not cookie_token or not header_token:
        return False
    return hmac.compare_digest(cookie_token, header_token)
