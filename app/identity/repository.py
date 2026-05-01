from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.identity.models import ClientAccount, User


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
        role: str = "client_user",
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
        statement = select(User).where(User.email == email)
        return self._session.scalar(statement)

    def get_user_by_id(self, user_id: UUID) -> User | None:
        statement = select(User).where(User.id == user_id)
        return self._session.scalar(statement)
