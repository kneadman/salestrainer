from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.access.repository import AccessRepository
from app.api.main import create_app
from app.application.report_service import ReportService
from app.domain.judgement_models import BentoReportBlock, JudgeSessionOutput, ReportRecommendation, SkillScore
from app.domain.models import ClientState, PersonaProfile, TrainingSessionState
from tests.unit._persona_fixtures import valid_minimal_persona
from app.history.models import TrainingReportRecord, TrainingSessionRecord, TrainingTurnRecord, UsageEventRecord
from app.history.repository import HistoryRepository
from app.history.service import HistoryService
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


class CountingJudgementService:
    def __init__(self) -> None:
        """Count how many times report payload generation actually invokes judge logic."""
        self.calls = 0

    def judge_session(self, session: TrainingSessionState) -> JudgeSessionOutput:
        """Return a minimal valid structured judge payload and increment the call counter."""
        self.calls += 1
        evidence_indexes = [1] if session.turn_count else []
        return JudgeSessionOutput(
            overall_score=70,
            overall_grade="normal",
            outcome="Итог нормальный.",
            executive_summary="Сессия завершена и оценена.",
            bento_blocks=[
                BentoReportBlock(
                    id="summary",
                    title="Итог",
                    type="summary",
                    severity="neutral",
                    short_text="Краткий итог.",
                    detail="Подробный итог.",
                    evidence_turn_indexes=evidence_indexes,
                )
            ],
            skill_scores=[
                SkillScore(
                    id="discovery_quality",
                    title="Discovery quality",
                    score=70,
                    severity="yellow",
                    explanation="Навык проявлен на среднем уровне.",
                    evidence_turn_indexes=evidence_indexes,
                )
            ],
            recommendations=[
                ReportRecommendation(
                    title="Уточнить следующий шаг",
                    description="Нужно добавить больше конкретики перед следующим шагом.",
                    example_phrase=None,
                    priority="medium",
                )
            ],
            final_verdict="Стабильный тестовый вердикт.",
        )


class CrashingJudgementService:
    def judge_session(self, session: TrainingSessionState) -> JudgeSessionOutput:
        """Raise a deterministic error to verify fail-open API behavior."""
        raise RuntimeError("judge exploded")


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
    assert report.report_payload is not None
    assert {"session_started", "turn_processed", "session_finished", "report_generated"}.issubset(set(event_types))

    history_list_response = client.get("/api/history/sessions")
    history_response = client.get(f"/api/history/sessions/{session_id}")
    report_response = client.get(f"/api/history/sessions/{session_id}/report")

    assert history_list_response.status_code == 200
    assert history_list_response.json()[0]["session_id"] == session_id
    assert "user_id" not in history_list_response.json()[0]
    assert "client_account_id" not in history_list_response.json()[0]
    assert "training_config_id" not in history_list_response.json()[0]
    assert history_response.status_code == 200
    assert history_response.json()["session"]["session_id"] == session_id
    assert "user_id" not in history_response.json()["session"]
    assert "client_account_id" not in history_response.json()["session"]
    assert "training_config_id" not in history_response.json()["session"]
    assert len(history_response.json()["turns"]) == 1
    assert "persona_snapshot" not in history_response.text
    assert "llm_payload_snapshot" not in history_response.text
    assert "llm_response_snapshot" not in history_response.text
    assert report_response.status_code == 200
    assert report_response.json()["report"] == report.report_text
    assert "report_payload" in report_response.json()
    assert report_response.json()["report_payload"] == report.report_payload
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


def test_history_service_persists_report_payload_without_exposing_it_in_dto() -> None:
    """Verify explicit report_payload is saved in the persistent report record."""
    db_session = _create_db_session()
    account, training_config, users = _seed_account_with_users(
        db_session,
        slug="acme-payload",
        users=[("manager@example.com", "client_manager")],
    )
    history_service = HistoryService(HistoryRepository(db_session))
    now = datetime.now(tz=UTC)
    session = TrainingSessionState(
        session_id=uuid4(),
        scenario_id="sales_audit_cold_outreach",
        status="finished",
        persona=valid_minimal_persona(
            id="generated_persona",
            display_name="Unknown B2B contact",
            behavior_model="analytical_and_cautious",
        ),
        interest_score=52,
        stage="need_discovery",
        client_state=ClientState(
            tone="neutral",
            trust=38,
            irritation=10,
            urgency=24,
            price_sensitivity=40,
        ),
        summary="Finished session for payload persistence test.",
        public_brief="Brief",
        turns=[],
        turn_evaluations=[],
        recent_turns=[],
        turn_count=0,
        state_version=2,
        created_at=now,
        updated_at=now,
    )
    history_service.record_session_started(
        session=session,
        client_account_id=account.id,
        user_id=users["manager@example.com"].id,
        training_config_id=training_config.id,
    )
    payload = {
        "schema_version": 1,
        "overall_score": 74,
        "overall_grade": "good",
    }

    history_service.record_session_finished_with_report(
        session=session,
        report_text="Report text",
        report_payload=payload,
        user_id=users["manager@example.com"].id,
        client_account_id=account.id,
        training_config_id=training_config.id,
    )

    record = db_session.scalar(select(TrainingReportRecord).where(TrainingReportRecord.session_id == session.session_id))

    assert record is not None
    assert record.report_payload == payload
    db_session.close()


def test_get_report_reuses_saved_report_payload_without_regenerating_judge() -> None:
    """GET /report should reuse persisted report_payload instead of re-running judge logic."""
    db_session = _create_db_session()
    repository = InMemorySessionRepository()
    _seed_account_with_users(
        db_session,
        slug="acme-reuse",
        users=[("manager@example.com", "client_manager")],
    )
    client = _create_client(db_session, repository)
    counting_judgement_service = CountingJudgementService()
    client.app.state.services.report_service = ReportService(
        repository,
        judgement_service=counting_judgement_service,
    )
    _login(client, "manager@example.com")

    session_id = _start_turn_finish(client)

    assert counting_judgement_service.calls == 1

    first_report = db_session.scalar(select(TrainingReportRecord).where(TrainingReportRecord.session_id == UUID(session_id)))
    assert first_report is not None
    assert first_report.report_payload is not None

    report_response = client.get(f"/api/sessions/{session_id}/report")

    assert report_response.status_code == 200
    assert counting_judgement_service.calls == 1
    assert "report_payload" in report_response.json()
    assert report_response.json()["report_payload"] == first_report.report_payload
    db_session.close()


def test_finish_session_returns_null_payload_but_persists_fallback_report_payload_when_judge_fails() -> None:
    """API returns report_payload=null after judge failure, while HistoryService persists a fallback DB payload by design.

    The response-level null payload is expected because Judge generation crashed in the request flow.
    The persisted fallback payload is also expected because HistoryService keeps minimal structured report data in DB.
    That difference is intentional and should not be treated as a contradiction.
    """
    db_session = _create_db_session()
    repository = InMemorySessionRepository()
    _seed_account_with_users(
        db_session,
        slug="acme-judge-fail-open",
        users=[("manager@example.com", "client_manager")],
    )
    client = _create_client(db_session, repository)
    client.app.state.services.report_service = ReportService(
        repository,
        judgement_service=CrashingJudgementService(),
    )
    _login(client, "manager@example.com")

    create_response = client.post("/api/sessions", json={})
    assert create_response.status_code == 201
    session_id = create_response.json()["session"]["session_id"]
    turn_response = client.post(
        f"/api/sessions/{session_id}/messages",
        json={"manager_message": "How do you solve this process today?"},
    )
    assert turn_response.status_code == 200

    finish_response = client.post(f"/api/sessions/{session_id}/finish")
    report_record = db_session.scalar(select(TrainingReportRecord).where(TrainingReportRecord.session_id == UUID(session_id)))

    assert finish_response.status_code == 200
    assert finish_response.json()["report"]
    assert "report_payload" in finish_response.json()
    assert finish_response.json()["report_payload"] is None
    assert report_record is not None
    assert report_record.report_text
    assert report_record.report_payload == {
        "status": "finished",
        "turn_count": finish_response.json()["session"]["turn_count"],
        "final_interest_score": finish_response.json()["session"]["interest"]["score"],
        "final_stage": finish_response.json()["session"]["stage"],
    }
    db_session.close()


def test_history_report_response_exposes_saved_report_payload() -> None:
    """Persistent history report DTO should include the saved structured judge payload."""
    db_session = _create_db_session()
    repository = InMemorySessionRepository()
    _seed_account_with_users(
        db_session,
        slug="acme-history-payload",
        users=[("manager@example.com", "client_manager")],
    )
    client = _create_client(db_session, repository)
    counting_judgement_service = CountingJudgementService()
    client.app.state.services.report_service = ReportService(
        repository,
        judgement_service=counting_judgement_service,
    )
    _login(client, "manager@example.com")

    session_id = _start_turn_finish(client)
    report_record = db_session.scalar(select(TrainingReportRecord).where(TrainingReportRecord.session_id == UUID(session_id)))
    history_report_response = client.get(f"/api/history/sessions/{session_id}/report")

    assert history_report_response.status_code == 200
    assert "report_payload" in history_report_response.json()
    assert history_report_response.json()["report_payload"] == report_record.report_payload
    db_session.close()
