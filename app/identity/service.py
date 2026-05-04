from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.access.repository import AccessRepository
from app.identity.models import LoginSession, User
from app.identity.repository import IdentityRepository
from app.identity.security import generate_secure_token, hash_password, hash_token, verify_password
from app.infrastructure.config import Settings


class AuthenticationError(Exception):
    """Raised when credentials or a session cookie cannot authenticate a user."""


@dataclass(frozen=True)
class LoginResult:
    user: User
    login_session: LoginSession
    raw_token: str


@dataclass(frozen=True)
class CurrentSession:
    user: User
    login_session: LoginSession


class AuthService:
    def __init__(
        self,
        *,
        identity_repository: IdentityRepository,
        access_repository: AccessRepository,
        settings: Settings,
    ) -> None:
        self._identity_repository = identity_repository
        self._access_repository = access_repository
        self._settings = settings

    def login(
        self,
        *,
        email: str,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> LoginResult:
        normalized_email = email.strip().lower()
        user = self._identity_repository.get_user_by_email(normalized_email)
        if (
            user is None
            or not user.is_active
            or not user.client_account.is_active
            or not verify_password(password, user.password_hash)
        ):
            self._access_repository.create_audit_log_record(
                action="login_failed",
                entity_type="user",
                entity_id=user.id if user is not None else None,
                payload={"email": normalized_email},
                ip_address=ip_address,
                user_agent=user_agent,
            )
            raise AuthenticationError("Invalid email or password.")

        raw_token = generate_secure_token()
        now = datetime.now(UTC)
        login_session = self._identity_repository.create_login_session(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=now + timedelta(seconds=self._settings.auth_session_ttl_seconds),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self._access_repository.create_audit_log_record(
            action="login_success",
            entity_type="login_session",
            actor_user_id=user.id,
            entity_id=login_session.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return LoginResult(user=user, login_session=login_session, raw_token=raw_token)

    def authenticate_session(self, raw_token: str | None) -> CurrentSession:
        if not raw_token:
            raise AuthenticationError("Not authenticated.")

        login_session = self._identity_repository.get_login_session_by_token_hash(hash_token(raw_token))
        now = datetime.now(UTC)
        if (
            login_session is None
            or login_session.revoked_at is not None
            or _as_utc(login_session.expires_at) <= now
            or not login_session.user.is_active
            or not login_session.user.client_account.is_active
        ):
            raise AuthenticationError("Not authenticated.")

        return CurrentSession(user=login_session.user, login_session=login_session)

    def logout(
        self,
        *,
        current_session: CurrentSession,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        self._identity_repository.revoke_login_session(
            login_session_id=current_session.login_session.id,
            revoked_at=datetime.now(UTC),
        )
        self._access_repository.create_audit_log_record(
            action="logout",
            entity_type="login_session",
            actor_user_id=current_session.user.id,
            entity_id=current_session.login_session.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    def change_password(
        self,
        *,
        current_session: CurrentSession,
        current_password: str,
        new_password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> User:
        user = current_session.user
        if not verify_password(current_password, user.password_hash):
            raise AuthenticationError("Invalid current password.")
        updated_user = self._identity_repository.update_user_password(
            user_id=user.id,
            password_hash=hash_password(new_password),
            must_change_password=False,
        )
        if updated_user is None:
            raise AuthenticationError("Not authenticated.")
        self._access_repository.create_audit_log_record(
            action="password_changed",
            entity_type="user",
            actor_user_id=updated_user.id,
            entity_id=updated_user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return updated_user


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
