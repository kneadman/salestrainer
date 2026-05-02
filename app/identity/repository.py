from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, joinedload

from app.identity.models import ClientAccount, LoginSession, User
from app.identity.roles import UserRole


class IdentityRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_client_account(
        self,
        *,
        name: str,
        slug: str,
        is_active: bool = True,
        account_id: UUID | None = None,
    ) -> ClientAccount:
        account_kwargs = dict(
            name=name,
            slug=slug,
            is_active=is_active,
        )
        if account_id is not None:
            account_kwargs["id"] = account_id
        account = ClientAccount(**account_kwargs)
        self._session.add(account)
        self._session.commit()
        self._session.refresh(account)
        return account

    def get_client_account_by_slug(self, slug: str) -> ClientAccount | None:
        statement = select(ClientAccount).where(ClientAccount.slug == slug)
        return self._session.scalar(statement)

    def create_user(
        self,
        *,
        client_account_id: UUID,
        email: str,
        password_hash: str,
        role: str = UserRole.CLIENT_MANAGER.value,
        is_active: bool = True,
        must_change_password: bool = True,
        user_id: UUID | None = None,
    ) -> User:
        user_kwargs = dict(
            client_account_id=client_account_id,
            email=email,
            password_hash=password_hash,
            role=role,
            is_active=is_active,
            must_change_password=must_change_password,
        )
        if user_id is not None:
            user_kwargs["id"] = user_id
        user = User(**user_kwargs)
        self._session.add(user)
        self._session.commit()
        self._session.refresh(user)
        return user

    def get_user_by_email(self, email: str) -> User | None:
        statement = (
            select(User)
            .options(joinedload(User.client_account))
            .where(func.lower(User.email) == email.strip().lower())
        )
        return self._session.scalar(statement)

    def get_user_by_id(self, user_id: UUID) -> User | None:
        statement = select(User).options(joinedload(User.client_account)).where(User.id == user_id)
        return self._session.scalar(statement)

    def get_client_account_by_id(self, client_account_id: UUID) -> ClientAccount | None:
        return self._session.get(ClientAccount, client_account_id)

    def update_user_password(
        self,
        *,
        user_id: UUID,
        password_hash: str,
        must_change_password: bool = True,
    ) -> User | None:
        user = self.get_user_by_id(user_id)
        if user is None:
            return None

        user.password_hash = password_hash
        user.must_change_password = must_change_password
        self._session.commit()
        self._session.refresh(user)
        return user

    def create_login_session(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        user_agent: str | None = None,
        ip_address: str | None = None,
        login_session_id: UUID | None = None,
    ) -> LoginSession:
        login_session_kwargs = dict(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        if login_session_id is not None:
            login_session_kwargs["id"] = login_session_id
        login_session = LoginSession(**login_session_kwargs)
        user = self.get_user_by_id(user_id)
        if user is not None:
            user.last_login_at = datetime.now(UTC)
        self._session.add(login_session)
        self._session.commit()
        self._session.refresh(login_session)
        return login_session

    def get_login_session_by_token_hash(self, token_hash: str) -> LoginSession | None:
        statement = (
            select(LoginSession)
            .options(joinedload(LoginSession.user).joinedload(User.client_account))
            .where(LoginSession.token_hash == token_hash)
        )
        return self._session.scalar(statement)

    def revoke_login_session(
        self,
        *,
        login_session_id: UUID,
        revoked_at: datetime,
    ) -> LoginSession | None:
        login_session = self._session.get(LoginSession, login_session_id)
        if login_session is None:
            return None

        login_session.revoked_at = revoked_at
        self._session.commit()
        self._session.refresh(login_session)
        return login_session

    def delete_expired_login_sessions(self, *, expired_before: datetime) -> int:
        result = self._session.execute(
            delete(LoginSession).where(LoginSession.expires_at <= expired_before)
        )
        self._session.commit()
        return int(result.rowcount or 0)

    def disable_user(self, *, user_id: UUID) -> User | None:
        user = self.get_user_by_id(user_id)
        if user is None:
            return None

        user.is_active = False
        self._session.commit()
        self._session.refresh(user)
        return user

    def enable_user(self, *, user_id: UUID) -> User | None:
        user = self.get_user_by_id(user_id)
        if user is None:
            return None

        user.is_active = True
        self._session.commit()
        self._session.refresh(user)
        return user
