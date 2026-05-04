from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.access.repository import AccessRepository
from app.api.main import create_app
from app.history.models import TrainingSessionRecord
from app.identity.dependencies import get_db_session
from app.identity.models import User
from app.identity.repository import IdentityRepository
from app.identity.security import hash_password
from app.infrastructure.config import Settings
from app.infrastructure.db import Base, import_model_modules
from app.infrastructure.llm_client import FakeLLMClient
from app.infrastructure.session_repository import InMemorySessionRepository


def _create_db_session() -> Session:
    """Create an in-memory DB with all application ORM models."""
    import_model_modules()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)
    return session_factory()


def _create_client(db_session: Session) -> TestClient:
    """Create a TestClient bound to a shared DB session."""
    app = create_app(
        settings=Settings(auth_cookie_secure=False, login_rate_limit_attempts=0),
        repository=InMemorySessionRepository(),
        llm_client=FakeLLMClient(),
    )

    def override_get_db_session() -> Generator[Session, None, None]:
        """Yield the shared DB session for FastAPI dependencies."""
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    return TestClient(app)


def _seed_account(
    db_session: Session,
    *,
    slug: str,
    users: list[tuple[str, str]],
) -> tuple[object, object, dict[str, User]]:
    """Seed one account, one training config, and requested users."""
    identity_repository = IdentityRepository(db_session)
    access_repository = AccessRepository(db_session)
    account = identity_repository.create_client_account(name=slug.title(), slug=slug)
    config = access_repository.create_training_config(
        client_account_id=account.id,
        name="Default",
        default_scenario_id="generic_b2b_first_contact",
        product_line="accounting_outsourcing",
    )
    created: dict[str, User] = {}
    for email, role in users:
        user = identity_repository.create_user(
            client_account_id=account.id,
            email=email,
            password_hash=hash_password("password"),
            role=role,
            must_change_password=False,
        )
        access_repository.assign_training_config_to_user(user_id=user.id, training_config_id=config.id, is_default=True)
        created[email] = user
    return account, config, created


def _login(client: TestClient, email: str) -> None:
    """Authenticate a test client as the requested user."""
    response = client.post("/auth/login", json={"email": email, "password": "password"})
    assert response.status_code == 200
    csrf_response = client.get("/auth/csrf")
    assert csrf_response.status_code == 200
    client.headers.update({"X-CSRF-Token": csrf_response.json()["csrf_token"]})


def _add_history(
    db_session: Session,
    *,
    user: User,
    client_account_id: UUID,
    training_config_id: UUID,
    status: str = "finished",
    final_interest_score: int | None = 72,
    turn_count: int = 3,
) -> TrainingSessionRecord:
    """Insert one persistent history row for analytics endpoint tests."""
    now = datetime.now(UTC)
    record = TrainingSessionRecord(
        id=uuid4(),
        client_account_id=client_account_id,
        user_id=user.id,
        training_config_id=training_config_id,
        scenario_id="generic_b2b_first_contact",
        status=status,
        started_at=now,
        finished_at=now if status == "finished" else None,
        last_activity_at=now,
        turn_count=turn_count,
        final_interest_score=final_interest_score,
        final_stage="needs_analysis",
        persona_snapshot={},
        initial_state_snapshot={},
        final_state_snapshot={},
        public_brief="brief",
        summary="summary",
    )
    db_session.add(record)
    db_session.commit()
    return record


def test_client_manager_cannot_access_team_endpoints() -> None:
    """Verify team endpoints reject normal managers."""
    db_session = _create_db_session()
    _seed_account(db_session, slug="acme", users=[("manager@example.com", "client_manager")])
    client = _create_client(db_session)
    _login(client, "manager@example.com")

    response = client.get("/api/team/users")

    assert response.status_code == 403
    db_session.close()


def test_client_lead_can_read_same_org_team_users_and_usage_summary() -> None:
    """Verify a lead sees same-organization users and aggregate usage."""
    db_session = _create_db_session()
    account, config, users = _seed_account(
        db_session,
        slug="acme",
        users=[("lead@example.com", "client_lead"), ("manager@example.com", "client_manager")],
    )
    _add_history(
        db_session,
        user=users["manager@example.com"],
        client_account_id=account.id,
        training_config_id=config.id,
    )
    client = _create_client(db_session)
    _login(client, "lead@example.com")

    users_response = client.get("/api/team/users")
    summary_response = client.get("/api/team/usage-summary")

    assert users_response.status_code == 200
    assert {user["email"] for user in users_response.json()} == {"lead@example.com", "manager@example.com"}
    manager_payload = next(user for user in users_response.json() if user["email"] == "manager@example.com")
    assert manager_payload["total_sessions"] == 1
    assert manager_payload["finished_sessions"] == 1
    assert summary_response.status_code == 200
    assert summary_response.json()["total_sessions"] == 1
    assert summary_response.json()["finished_sessions"] == 1
    assert summary_response.json()["users"]
    db_session.close()


def test_client_lead_cannot_read_other_org_user_detail() -> None:
    """Verify a lead cannot inspect users from another organization."""
    db_session = _create_db_session()
    _seed_account(db_session, slug="acme", users=[("lead@example.com", "client_lead")])
    _, _, other_users = _seed_account(db_session, slug="beta", users=[("other@example.com", "client_manager")])
    client = _create_client(db_session)
    _login(client, "lead@example.com")

    response = client.get(f"/api/team/users/{other_users['other@example.com'].id}/analytics")
    history_response = client.get(f"/api/team/users/{other_users['other@example.com'].id}/history/sessions")

    assert response.status_code == 404
    assert history_response.status_code == 404
    db_session.close()


def test_team_endpoints_require_authentication() -> None:
    """Verify anonymous clients cannot access team APIs."""
    db_session = _create_db_session()
    client = _create_client(db_session)

    response = client.get("/api/team/users")

    assert response.status_code == 401
    db_session.close()
