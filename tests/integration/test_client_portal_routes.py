from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.access.repository import AccessRepository
from app.api.main import create_app
from app.history.models import TrainingReportRecord, TrainingSessionRecord
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
    started_at: datetime | None = None,
) -> TrainingSessionRecord:
    """Insert one persistent history row for analytics endpoint tests."""
    now = started_at or datetime.now(UTC)
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


def _valid_judge_payload(*, overall_score: int, skill_score: int, skill_id: str = "discovery_quality", skill_title: str = "Качество диагностики") -> dict[str, object]:
    """Build one minimal valid saved judge payload for analytics aggregation tests."""
    return {
        "schema_version": 1,
        "overall_score": overall_score,
        "overall_grade": "good" if overall_score >= 71 else "normal",
        "outcome": "Итог сессии сформирован.",
        "executive_summary": "Краткая структурированная сводка по завершённой тренировке.",
        "bento_blocks": [
            {
                "id": "summary",
                "title": "Итог сессии",
                "type": "summary",
                "severity": "neutral",
                "short_text": "Краткий итог.",
                "detail": "Подробный итог.",
                "evidence_turn_indexes": [1],
            }
        ],
        "skill_scores": [
            {
                "id": skill_id,
                "title": skill_title,
                "score": skill_score,
                "severity": "yellow",
                "explanation": "Тестовая агрегированная оценка навыка.",
                "evidence_turn_indexes": [1],
            }
        ],
        "key_strengths": [],
        "key_weaknesses": [],
        "missed_opportunities": [],
        "recommendations": [],
        "final_verdict": "Тестовый вердикт.",
        "risk_flags": [],
    }


def _add_report_payload(db_session: Session, *, session_id: UUID, payload: dict[str, object]) -> None:
    """Persist one saved structured report payload for analytics endpoint tests."""
    db_session.add(
        TrainingReportRecord(
            session_id=session_id,
            report_text="Saved report text",
            report_payload=payload,
        )
    )
    db_session.commit()


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
    history_response = client.get(f"/api/team/users/{users['manager@example.com'].id}/history/sessions")

    assert users_response.status_code == 200
    assert {user["email"] for user in users_response.json()} == {"lead@example.com", "manager@example.com"}
    manager_payload = next(user for user in users_response.json() if user["email"] == "manager@example.com")
    assert manager_payload["total_sessions"] == 1
    assert manager_payload["finished_sessions"] == 1
    assert summary_response.status_code == 200
    assert summary_response.json()["total_sessions"] == 1
    assert summary_response.json()["finished_sessions"] == 1
    assert summary_response.json()["users"]
    assert history_response.status_code == 200
    assert history_response.json()[0]["user_email"] == "manager@example.com"
    assert history_response.json()[0]["training_config_name"] == "Default"
    assert "user_id" not in history_response.json()[0]
    assert "client_account_id" not in history_response.json()[0]
    assert "training_config_id" not in history_response.json()[0]
    db_session.close()


def test_client_training_configs_returns_assigned_active_options() -> None:
    """Client config selector should expose safe names and ids for assigned active configs only."""
    db_session = _create_db_session()
    account, config, users = _seed_account(
        db_session,
        slug="config-options",
        users=[("manager@example.com", "client_manager")],
    )
    access_repository = AccessRepository(db_session)
    inactive_config = access_repository.create_training_config(
        client_account_id=account.id,
        name="Inactive",
        is_active=False,
    )
    access_repository.assign_training_config_to_user(
        user_id=users["manager@example.com"].id,
        training_config_id=inactive_config.id,
    )
    client = _create_client(db_session)
    _login(client, "manager@example.com")

    response = client.get("/api/client/training-configs")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": str(config.id),
            "name": "Default",
            "is_default": True,
        }
    ]
    db_session.close()


def test_client_lead_training_configs_returns_all_active_org_options() -> None:
    """Client leads should filter team history by all active organization configs."""
    db_session = _create_db_session()
    identity_repository = IdentityRepository(db_session)
    access_repository = AccessRepository(db_session)
    account = identity_repository.create_client_account(name="Lead Configs", slug="lead-configs")
    lead = identity_repository.create_user(
        client_account_id=account.id,
        email="lead@example.com",
        password_hash=hash_password("password"),
        role="client_lead",
        must_change_password=False,
    )
    manager = identity_repository.create_user(
        client_account_id=account.id,
        email="manager@example.com",
        password_hash=hash_password("password"),
        role="client_manager",
        must_change_password=False,
    )
    lead_config = access_repository.create_training_config(
        client_account_id=account.id,
        name="Lead default",
    )
    manager_only_config = access_repository.create_training_config(
        client_account_id=account.id,
        name="Manager only",
    )
    inactive_config = access_repository.create_training_config(
        client_account_id=account.id,
        name="Inactive",
        is_active=False,
    )
    access_repository.assign_training_config_to_user(
        user_id=lead.id,
        training_config_id=lead_config.id,
        is_default=True,
    )
    access_repository.assign_training_config_to_user(
        user_id=manager.id,
        training_config_id=manager_only_config.id,
        is_default=True,
    )
    access_repository.assign_training_config_to_user(
        user_id=lead.id,
        training_config_id=inactive_config.id,
    )
    client = _create_client(db_session)
    _login(client, "lead@example.com")

    response = client.get("/api/client/training-configs")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": str(lead_config.id),
            "name": "Lead default",
            "is_default": False,
        },
        {
            "id": str(manager_only_config.id),
            "name": "Manager only",
            "is_default": False,
        },
    ]
    assert all(set(item) == {"id", "name", "is_default"} for item in response.json())
    assert str(inactive_config.id) not in response.text
    db_session.close()


def test_personal_analytics_aggregates_saved_judgement_payloads_and_ignores_invalid_ones() -> None:
    """Personal analytics should aggregate only valid saved judge payloads and expose weakest skill data."""
    db_session = _create_db_session()
    account, config, users = _seed_account(
        db_session,
        slug="analytics",
        users=[("manager@example.com", "client_manager")],
    )
    first_session = _add_history(
        db_session,
        user=users["manager@example.com"],
        client_account_id=account.id,
        training_config_id=config.id,
    )
    second_session = _add_history(
        db_session,
        user=users["manager@example.com"],
        client_account_id=account.id,
        training_config_id=config.id,
        final_interest_score=68,
    )
    invalid_session = _add_history(
        db_session,
        user=users["manager@example.com"],
        client_account_id=account.id,
        training_config_id=config.id,
        final_interest_score=41,
    )
    _add_report_payload(db_session, session_id=first_session.id, payload=_valid_judge_payload(overall_score=80, skill_score=55))
    _add_report_payload(db_session, session_id=second_session.id, payload=_valid_judge_payload(overall_score=60, skill_score=45))
    _add_report_payload(db_session, session_id=invalid_session.id, payload={"status": "finished"})
    client = _create_client(db_session)
    _login(client, "manager@example.com")

    response = client.get("/api/client/analytics/me")

    assert response.status_code == 200
    payload = response.json()
    assert payload["sessions_with_judgement"] == 2
    assert payload["avg_judgement_score"] == 70.0
    assert payload["weakest_skill_id"] == "discovery_quality"
    assert payload["weakest_skill_title"] == "Качество диагностики"
    assert payload["weakest_skill_avg_score"] == 50.0
    db_session.close()


def test_team_usage_summary_aggregates_saved_judgement_payloads() -> None:
    """Team analytics should expose average judge score and judged session count from saved payloads."""
    db_session = _create_db_session()
    account, config, users = _seed_account(
        db_session,
        slug="team-analytics",
        users=[("lead@example.com", "client_lead"), ("manager@example.com", "client_manager")],
    )
    judged_session = _add_history(
        db_session,
        user=users["manager@example.com"],
        client_account_id=account.id,
        training_config_id=config.id,
    )
    ignored_session = _add_history(
        db_session,
        user=users["lead@example.com"],
        client_account_id=account.id,
        training_config_id=config.id,
        final_interest_score=55,
    )
    _add_report_payload(db_session, session_id=judged_session.id, payload=_valid_judge_payload(overall_score=78, skill_score=52))
    _add_report_payload(db_session, session_id=ignored_session.id, payload={"unexpected": "shape"})
    client = _create_client(db_session)
    _login(client, "lead@example.com")

    response = client.get("/api/team/usage-summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["sessions_with_judgement"] == 1
    assert payload["avg_judgement_score"] == 78.0
    db_session.close()


def test_personal_analytics_returns_real_7d_trends_for_current_and_previous_windows() -> None:
    """Personal analytics should expose current and previous 7-day windows without frontend-derived deltas."""
    db_session = _create_db_session()
    account, config, users = _seed_account(
        db_session,
        slug="trend-analytics",
        users=[("manager@example.com", "client_manager")],
    )
    now = datetime.now(UTC).replace(microsecond=0)
    current_finished = _add_history(
        db_session,
        user=users["manager@example.com"],
        client_account_id=account.id,
        training_config_id=config.id,
        status="finished",
        final_interest_score=80,
        turn_count=4,
        started_at=now,
    )
    _add_history(
        db_session,
        user=users["manager@example.com"],
        client_account_id=account.id,
        training_config_id=config.id,
        status="active",
        final_interest_score=None,
        turn_count=2,
        started_at=now - timedelta(days=3),
    )
    previous_finished = _add_history(
        db_session,
        user=users["manager@example.com"],
        client_account_id=account.id,
        training_config_id=config.id,
        status="finished",
        final_interest_score=40,
        turn_count=6,
        started_at=now - timedelta(days=10),
    )
    _add_history(
        db_session,
        user=users["manager@example.com"],
        client_account_id=account.id,
        training_config_id=config.id,
        status="active",
        final_interest_score=None,
        turn_count=8,
        started_at=now - timedelta(days=12),
    )
    _add_report_payload(db_session, session_id=current_finished.id, payload=_valid_judge_payload(overall_score=90, skill_score=70))
    _add_report_payload(db_session, session_id=previous_finished.id, payload=_valid_judge_payload(overall_score=60, skill_score=50))
    client = _create_client(db_session)
    _login(client, "manager@example.com")

    response = client.get("/api/client/analytics/me")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_sessions"] == 4
    assert payload["trends_7d"]["total_sessions"] == {
        "current_7d": 2,
        "previous_7d": 2,
        "delta": 0,
        "delta_percent": 0.0,
        "direction": "flat",
    }
    assert payload["trends_7d"]["finished_sessions"] == {
        "current_7d": 1,
        "previous_7d": 1,
        "delta": 0,
        "delta_percent": 0.0,
        "direction": "flat",
    }
    assert payload["trends_7d"]["completion_rate"] == {
        "current_7d": 0.5,
        "previous_7d": 0.5,
        "delta": 0.0,
        "delta_percent": 0.0,
        "direction": "flat",
    }
    assert payload["trends_7d"]["avg_turn_count"] == {
        "current_7d": 3.0,
        "previous_7d": 7.0,
        "delta": -4.0,
        "delta_percent": pytest.approx(-57.14285714285714),
        "direction": "down",
    }
    assert payload["trends_7d"]["avg_final_interest_score"] == {
        "current_7d": 80.0,
        "previous_7d": 40.0,
        "delta": 40.0,
        "delta_percent": 100.0,
        "direction": "up",
    }
    assert payload["trends_7d"]["avg_judgement_score"] == {
        "current_7d": 90.0,
        "previous_7d": 60.0,
        "delta": 30.0,
        "delta_percent": 50.0,
        "direction": "up",
    }
    assert payload["trends_7d"]["sessions_with_judgement"] == {
        "current_7d": 1,
        "previous_7d": 1,
        "delta": 0,
        "delta_percent": 0.0,
        "direction": "flat",
    }
    db_session.close()


def test_personal_analytics_returns_none_delta_percent_when_previous_window_is_zero() -> None:
    """Personal analytics should avoid dividing by zero when the previous 7-day window is empty."""
    db_session = _create_db_session()
    account, config, users = _seed_account(
        db_session,
        slug="current-only-trends",
        users=[("manager@example.com", "client_manager")],
    )
    current_session = _add_history(
        db_session,
        user=users["manager@example.com"],
        client_account_id=account.id,
        training_config_id=config.id,
        status="finished",
        final_interest_score=77,
        turn_count=5,
        started_at=datetime.now(UTC) - timedelta(days=1),
    )
    _add_report_payload(db_session, session_id=current_session.id, payload=_valid_judge_payload(overall_score=88, skill_score=66))
    client = _create_client(db_session)
    _login(client, "manager@example.com")

    response = client.get("/api/client/analytics/me")

    assert response.status_code == 200
    payload = response.json()
    assert payload["trends_7d"]["total_sessions"] == {
        "current_7d": 1,
        "previous_7d": 0,
        "delta": 1,
        "delta_percent": None,
        "direction": "up",
    }
    assert payload["trends_7d"]["completion_rate"] == {
        "current_7d": 1.0,
        "previous_7d": None,
        "delta": 1.0,
        "delta_percent": None,
        "direction": "up",
    }
    assert payload["trends_7d"]["avg_judgement_score"] == {
        "current_7d": 88.0,
        "previous_7d": None,
        "delta": 88.0,
        "delta_percent": None,
        "direction": "up",
    }
    db_session.close()


def test_personal_analytics_keeps_session_window_counts_without_report_payloads() -> None:
    """Session-window metrics should not depend on whether reports exist for sessions in the same window."""
    db_session = _create_db_session()
    account, config, users = _seed_account(
        db_session,
        slug="report-optional-trends",
        users=[("manager@example.com", "client_manager")],
    )
    now = datetime.now(UTC).replace(microsecond=0)
    reported_session = _add_history(
        db_session,
        user=users["manager@example.com"],
        client_account_id=account.id,
        training_config_id=config.id,
        status="finished",
        final_interest_score=82,
        turn_count=4,
        started_at=now - timedelta(days=1),
    )
    _add_history(
        db_session,
        user=users["manager@example.com"],
        client_account_id=account.id,
        training_config_id=config.id,
        status="finished",
        final_interest_score=64,
        turn_count=6,
        started_at=now - timedelta(days=2),
    )
    previous_reported_session = _add_history(
        db_session,
        user=users["manager@example.com"],
        client_account_id=account.id,
        training_config_id=config.id,
        status="finished",
        final_interest_score=55,
        turn_count=7,
        started_at=now - timedelta(days=10),
    )
    _add_report_payload(db_session, session_id=reported_session.id, payload=_valid_judge_payload(overall_score=91, skill_score=71))
    _add_report_payload(db_session, session_id=previous_reported_session.id, payload=_valid_judge_payload(overall_score=73, skill_score=53))
    client = _create_client(db_session)
    _login(client, "manager@example.com")

    response = client.get("/api/client/analytics/me")

    assert response.status_code == 200
    payload = response.json()
    assert payload["trends_7d"]["total_sessions"]["current_7d"] == 2
    assert payload["trends_7d"]["finished_sessions"]["current_7d"] == 2
    assert payload["trends_7d"]["sessions_with_judgement"]["current_7d"] == 1
    assert payload["trends_7d"]["avg_judgement_score"]["current_7d"] == 91.0
    assert payload["trends_7d"]["total_sessions"]["previous_7d"] == 1
    assert payload["trends_7d"]["sessions_with_judgement"]["previous_7d"] == 1
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
