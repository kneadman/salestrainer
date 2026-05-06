from __future__ import annotations

from collections.abc import Generator
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.access.repository import AccessRepository
from app.api.main import create_app
from app.history.models import TrainingReportRecord, TrainingSessionRecord, TrainingTurnRecord, UsageEventRecord
from app.identity.dependencies import get_db_session
from app.identity.models import User
from app.identity.repository import IdentityRepository
from app.identity.security import hash_password
from app.infrastructure.config import Settings
from app.infrastructure.db import Base, import_model_modules
from app.infrastructure.llm_client import FakeLLMClient
from app.infrastructure.session_repository import InMemorySessionRepository


def _create_db_session() -> Session:
    """Create an in-memory database with all ORM models registered."""
    import_model_modules()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)
    return session_factory()


def _create_client(db_session: Session, repository: InMemorySessionRepository) -> TestClient:
    """Create a TestClient wired to the provided database and runtime repository."""
    app = create_app(
        settings=Settings(auth_cookie_secure=False, login_rate_limit_attempts=0),
        repository=repository,
        llm_client=FakeLLMClient(),
    )

    def override_get_db_session() -> Generator[Session, None, None]:
        """Yield the shared test database session for FastAPI dependencies."""
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    return TestClient(app)


def _seed_account_with_users(
    db_session: Session,
    *,
    slug: str,
    users: list[tuple[str, str]],
) -> tuple[object, object, dict[str, User]]:
    """Seed one client account, one config, and requested users for access tests."""
    identity_repository = IdentityRepository(db_session)
    access_repository = AccessRepository(db_session)
    account = identity_repository.create_client_account(name=slug.title(), slug=slug)
    training_config = access_repository.create_training_config(
        client_account_id=account.id,
        name="Default config",
        default_scenario_id="generic_b2b_first_contact",
        persona_policy={},
        ui_config={},
    )
    created_users: dict[str, User] = {}
    for email, role in users:
        user = identity_repository.create_user(
            client_account_id=account.id,
            email=email,
            password_hash=hash_password("password"),
            role=role,
            must_change_password=False,
        )
        access_repository.assign_training_config_to_user(
            user_id=user.id,
            training_config_id=training_config.id,
            is_default=True,
        )
        created_users[email] = user
    return account, training_config, created_users


def _login(client: TestClient, email: str) -> None:
    """Authenticate the test client and install the CSRF header."""
    response = client.post("/auth/login", json={"email": email, "password": "password"})
    assert response.status_code == 200
    csrf_response = client.get("/auth/csrf")
    assert csrf_response.status_code == 200
    client.headers.update({"X-CSRF-Token": csrf_response.json()["csrf_token"]})


def _start_turn_finish(client: TestClient) -> str:
    """Run the minimal API training flow that creates persistent history."""
    create_response = client.post("/api/sessions", json={})
    assert create_response.status_code == 201
    session_id = create_response.json()["session"]["session_id"]
    turn_response = client.post(
        f"/api/sessions/{session_id}/messages",
        json={"manager_message": "How do you solve this process today?"},
    )
    assert turn_response.status_code == 200
    finish_response = client.post(f"/api/sessions/{session_id}/finish")
    assert finish_response.status_code == 200
    return session_id


def test_history_persists_session_turn_report_and_usage_events() -> None:
    """Verify session, turn, report, event rows and public-safe history API output."""
    db_session = _create_db_session()
    repository = InMemorySessionRepository()
    _, training_config, users = _seed_account_with_users(
        db_session,
        slug="acme",
        users=[("manager@example.com", "client_manager")],
    )
    client = _create_client(db_session, repository)
    _login(client, "manager@example.com")

    session_id = _start_turn_finish(client)

    session_record = db_session.get(TrainingSessionRecord, UUID(session_id))
    turns = list(db_session.scalars(select(TrainingTurnRecord).where(TrainingTurnRecord.session_id == UUID(session_id))))
    report = db_session.scalar(select(TrainingReportRecord).where(TrainingReportRecord.session_id == UUID(session_id)))
    event_types = [event.event_type for event in db_session.scalars(select(UsageEventRecord))]

    assert session_record is not None
    assert session_record.user_id == users["manager@example.com"].id
    assert session_record.training_config_id == training_config.id
    assert session_record.status == "finished"
    assert session_record.turn_count == 1
    assert session_record.final_interest_score is not None
    assert session_record.final_stage is not None
    assert session_record.persona_snapshot
    assert session_record.initial_state_snapshot
    assert session_record.final_state_snapshot
    assert len(turns) == 1
    assert turns[0].turn_index == 1
    assert turns[0].client_state_snapshot is not None
    assert report is not None
    assert report.report_text
    assert {"session_started", "turn_processed", "session_finished", "report_generated"}.issubset(set(event_types))

    history_response = client.get(f"/api/history/sessions/{session_id}")
    report_response = client.get(f"/api/history/sessions/{session_id}/report")

    assert history_response.status_code == 200
    assert history_response.json()["session"]["session_id"] == session_id
    assert len(history_response.json()["turns"]) == 1
    assert "persona_snapshot" not in history_response.text
    assert "llm_payload_snapshot" not in history_response.text
    assert "llm_response_snapshot" not in history_response.text
    assert report_response.status_code == 200
    assert report_response.json()["report"] == report.report_text
    db_session.close()


def test_history_access_rules_for_manager_lead_and_internal_admin() -> None:
    """Verify manager, lead, internal admin, and anonymous access boundaries."""
    db_session = _create_db_session()
    repository = InMemorySessionRepository()
    org_a, _, users_a = _seed_account_with_users(
        db_session,
        slug="org-a",
        users=[
            ("manager-a@example.com", "client_manager"),
            ("manager-b@example.com", "client_manager"),
            ("lead-a@example.com", "client_lead"),
        ],
    )
    _seed_account_with_users(
        db_session,
        slug="org-b",
        users=[("lead-b@example.com", "client_lead")],
    )
    _seed_account_with_users(
        db_session,
        slug="platform",
        users=[("admin@example.com", "internal_admin")],
    )
    owner_client = _create_client(db_session, repository)
    _login(owner_client, "manager-a@example.com")
    session_id = _start_turn_finish(owner_client)

    manager_b_client = _create_client(db_session, repository)
    _login(manager_b_client, "manager-b@example.com")
    assert manager_b_client.get(f"/api/history/sessions/{session_id}").status_code == 404
    assert manager_b_client.get("/api/history/sessions").json() == []

    lead_a_client = _create_client(db_session, repository)
    _login(lead_a_client, "lead-a@example.com")
    lead_a_list = lead_a_client.get(f"/api/history/sessions?user_id={users_a['manager-a@example.com'].id}")
    lead_a_detail = lead_a_client.get(f"/api/history/sessions/{session_id}")
    assert lead_a_list.status_code == 200
    assert [item["session_id"] for item in lead_a_list.json()] == [session_id]
    assert lead_a_detail.status_code == 200

    lead_b_client = _create_client(db_session, repository)
    _login(lead_b_client, "lead-b@example.com")
    lead_b_list = lead_b_client.get(f"/api/history/sessions?user_id={users_a['manager-a@example.com'].id}")
    lead_b_detail = lead_b_client.get(f"/api/history/sessions/{session_id}")
    assert lead_b_list.status_code == 200
    assert lead_b_list.json() == []
    assert lead_b_detail.status_code == 404

    admin_client = _create_client(db_session, repository)
    _login(admin_client, "admin@example.com")
    internal_list = admin_client.get(f"/api/internal/organizations/{org_a.id}/history/sessions")
    usage_summary = admin_client.get(f"/api/internal/organizations/{org_a.id}/usage-summary")
    internal_user_list = admin_client.get(f"/api/internal/users/{users_a['manager-a@example.com'].id}/history/sessions")
    assert internal_list.status_code == 200
    assert [item["session_id"] for item in internal_list.json()] == [session_id]
    assert usage_summary.status_code == 200
    assert usage_summary.json()["total_sessions"] == 1
    assert usage_summary.json()["finished_sessions"] == 1
    assert usage_summary.json()["total_turns"] == 1
    assert usage_summary.json()["unique_users"] == 1
    assert internal_user_list.status_code == 200
    assert [item["session_id"] for item in internal_user_list.json()] == [session_id]

    anonymous_client = _create_client(db_session, repository)
    assert anonymous_client.get("/api/history/sessions").status_code == 401
    db_session.close()
