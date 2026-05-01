from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.main import create_app
from app.identity.dependencies import get_db_session
from app.identity.models import LoginSession
from app.identity.repository import IdentityRepository
from app.identity.security import hash_password, hash_token
from app.infrastructure.config import Settings
from app.infrastructure.db import Base, import_model_modules
from app.infrastructure.llm_client import FakeLLMClient
from app.infrastructure.session_repository import InMemorySessionRepository


def _create_session() -> Session:
    import_model_modules()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)
    return session_factory()


def _create_client(session: Session) -> TestClient:
    app = create_app(
        settings=Settings(auth_cookie_secure=False),
        repository=InMemorySessionRepository(),
        llm_client=FakeLLMClient(),
    )

    def override_get_db_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    return TestClient(app)


def _create_user(
    session: Session,
    *,
    email: str = "manager@example.com",
    password: str = "password",
    is_active: bool = True,
) -> None:
    identity_repository = IdentityRepository(session)
    client_account = identity_repository.create_client_account(name="ООО Ромашка", slug="romashka")
    identity_repository.create_user(
        client_account_id=client_account.id,
        email=email,
        password_hash=hash_password(password),
        is_active=is_active,
    )


def test_login_success_sets_cookie() -> None:
    session = _create_session()
    _create_user(session)
    client = _create_client(session)

    response = client.post(
        "/auth/login",
        json={"email": "manager@example.com", "password": "password"},
    )

    assert response.status_code == 200
    assert "salestrainer_session=" in response.headers["set-cookie"]
    payload = response.json()
    assert payload["user"]["email"] == "manager@example.com"
    assert payload["user"]["role"] == "client_user"
    assert payload["user"]["client_account"]["slug"] == "romashka"
    assert session.scalar(select(LoginSession)).token_hash != client.cookies["salestrainer_session"]

    session.close()


def test_wrong_password_returns_401() -> None:
    session = _create_session()
    _create_user(session)
    client = _create_client(session)

    response = client.post(
        "/auth/login",
        json={"email": "manager@example.com", "password": "wrong"},
    )

    assert response.status_code == 401
    session.close()


def test_unknown_email_returns_401_without_leaking_whether_user_exists() -> None:
    session = _create_session()
    _create_user(session)
    client = _create_client(session)

    unknown_response = client.post(
        "/auth/login",
        json={"email": "unknown@example.com", "password": "password"},
    )
    wrong_password_response = client.post(
        "/auth/login",
        json={"email": "manager@example.com", "password": "wrong"},
    )

    assert unknown_response.status_code == 401
    assert unknown_response.json()["error"]["message"] == wrong_password_response.json()["error"]["message"]
    session.close()


def test_disabled_user_cannot_login() -> None:
    session = _create_session()
    _create_user(session, is_active=False)
    client = _create_client(session)

    response = client.post(
        "/auth/login",
        json={"email": "manager@example.com", "password": "password"},
    )

    assert response.status_code == 401
    session.close()


def test_auth_me_with_valid_cookie_returns_user() -> None:
    session = _create_session()
    _create_user(session)
    client = _create_client(session)
    client.post("/auth/login", json={"email": "manager@example.com", "password": "password"})

    response = client.get("/auth/me")

    assert response.status_code == 200
    assert response.json()["user"]["email"] == "manager@example.com"
    assert response.json()["user"]["client_account"]["name"] == "ООО Ромашка"
    session.close()


def test_auth_me_without_cookie_returns_401() -> None:
    session = _create_session()
    _create_user(session)
    client = _create_client(session)

    response = client.get("/auth/me")

    assert response.status_code == 401
    session.close()


def test_logout_revokes_session() -> None:
    session = _create_session()
    _create_user(session)
    client = _create_client(session)
    client.post("/auth/login", json={"email": "manager@example.com", "password": "password"})

    response = client.post("/auth/logout")

    assert response.status_code == 204
    login_session = session.scalar(select(LoginSession))
    assert login_session.revoked_at is not None
    assert "salestrainer_session=" in response.headers["set-cookie"]
    session.close()


def test_revoked_session_cannot_be_used_for_auth_me() -> None:
    session = _create_session()
    _create_user(session)
    client = _create_client(session)
    client.post("/auth/login", json={"email": "manager@example.com", "password": "password"})
    token = client.cookies["salestrainer_session"]
    client.post("/auth/logout")
    client.cookies.set("salestrainer_session", token)

    response = client.get("/auth/me")

    assert response.status_code == 401
    session.close()


def test_expired_session_cannot_be_used_for_auth_me() -> None:
    session = _create_session()
    _create_user(session)
    user = IdentityRepository(session).get_user_by_email("manager@example.com")
    assert user is not None
    session.add(
        LoginSession(
            user_id=user.id,
            token_hash=hash_token("expired-token"),
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        )
    )
    session.commit()
    client = _create_client(session)
    client.cookies.set("salestrainer_session", "expired-token")

    response = client.get("/auth/me")

    assert response.status_code == 401
    session.close()
