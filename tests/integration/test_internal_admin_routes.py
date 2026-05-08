from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.access.models import AuditLog, ClientTrainingConfig, LLMProviderConfig, UserTrainingConfig
from app.api.main import create_app
from app.history.models import TrainingReportRecord, TrainingSessionRecord
from app.identity.dependencies import get_db_session
from app.identity.models import User
from app.identity.repository import IdentityRepository
from app.identity.security import hash_password, verify_password
from app.infrastructure.config import Settings
from app.infrastructure.db import Base, import_model_modules
from app.infrastructure.llm_client import FakeLLMClient
from app.infrastructure.secrets import decrypt_secret
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
        settings=Settings(
            auth_cookie_secure=False,
            login_rate_limit_attempts=0,
            secret_encryption_key="test-secret-key",
        ),
        repository=InMemorySessionRepository(),
        llm_client=FakeLLMClient(),
    )

    def override_get_db_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    return TestClient(app)


def _seed_user(
    session: Session,
    *,
    email: str,
    role: str,
    slug: str,
    password: str = "password",
    must_change_password: bool = False,
) -> User:
    identity_repository = IdentityRepository(session)
    account = identity_repository.create_client_account(name=slug.title(), slug=slug)
    return identity_repository.create_user(
        client_account_id=account.id,
        email=email,
        password_hash=hash_password(password),
        role=role,
        must_change_password=must_change_password,
    )


def _login(client: TestClient, *, email: str, password: str = "password") -> None:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    csrf_response = client.get("/auth/csrf")
    assert csrf_response.status_code == 200
    client.headers.update({"X-CSRF-Token": csrf_response.json()["csrf_token"]})


def _admin_client(session: Session) -> TestClient:
    _seed_user(session, email="admin@example.com", role="internal_admin", slug="platform")
    client = _create_client(session)
    _login(client, email="admin@example.com")
    return client


def _create_org(client: TestClient, slug: str = "acme") -> dict[str, object]:
    response = client.post("/api/internal/organizations", json={"name": "Acme", "slug": slug})
    assert response.status_code == 201
    return response.json()


def _create_training_config(client: TestClient, organization_id: str, name: str = "Default") -> dict[str, object]:
    response = client.post(
        f"/api/internal/organizations/{organization_id}/training-configs",
        json={
            "name": name,
            "persona_generation_context": "Hidden decision-maker for an SMB accounting outsourcing scenario.",
        },
    )
    assert response.status_code == 201
    return response.json()


def _add_history(
    session: Session,
    *,
    user_id: UUID,
    client_account_id: UUID,
    training_config_id: UUID | None,
    status: str = "finished",
    final_interest_score: int | None = 72,
    turn_count: int = 3,
    started_at: datetime | None = None,
) -> TrainingSessionRecord:
    now = started_at or datetime.now(UTC)
    record = TrainingSessionRecord(
        id=uuid4(),
        client_account_id=client_account_id,
        user_id=user_id,
        training_config_id=training_config_id,
        scenario_id="generic_b2b_first_contact",
        status=status,
        started_at=now,
        finished_at=now if status == "finished" else None,
        last_activity_at=now,
        turn_count=turn_count,
        final_interest_score=final_interest_score,
        final_stage="needs_analysis",
        persona_snapshot={"hidden_persona": "secret"},
        initial_state_snapshot={"raw_llm_payload": "secret"},
        final_state_snapshot={"raw_llm_response": "secret"},
        public_brief="brief",
        summary="summary",
    )
    session.add(record)
    session.commit()
    return record


def _add_report(session: Session, *, session_id: UUID, overall_score: int) -> None:
    session.add(
        TrainingReportRecord(
            session_id=session_id,
            report_text="Saved report",
            report_payload={
                "schema_version": 1,
                "overall_score": overall_score,
                "overall_grade": "good",
                "outcome": "meeting",
                "executive_summary": "Summary",
                "bento_blocks": [],
                "skill_scores": [],
                "key_strengths": [],
                "key_weaknesses": [],
                "missed_opportunities": [],
                "recommendations": [],
                "final_verdict": "Verdict",
                "risk_flags": [],
            },
        )
    )
    session.commit()


def test_client_roles_cannot_access_internal_admin_api() -> None:
    for role in ("client_manager", "client_lead"):
        session = _create_session()
        _seed_user(session, email=f"{role}@example.com", role=role, slug=f"{role}-org")
        client = _create_client(session)
        _login(client, email=f"{role}@example.com")

        response = client.get("/api/internal/organizations")

        assert response.status_code == 403
        session.close()


def test_internal_admin_can_access_internal_admin_api() -> None:
    session = _create_session()
    client = _admin_client(session)

    response = client.get("/api/internal/organizations")

    assert response.status_code == 200
    session.close()


def test_organization_create_duplicate_disable_enable_and_audit() -> None:
    session = _create_session()
    client = _admin_client(session)

    organization = _create_org(client)
    duplicate = client.post("/api/internal/organizations", json={"name": "Other", "slug": "acme"})
    disabled = client.post(f"/api/internal/organizations/{organization['id']}/disable")
    enabled = client.post(f"/api/internal/organizations/{organization['id']}/enable")
    audit_actions = [record.action for record in session.scalars(select(AuditLog))]

    assert duplicate.status_code == 409
    assert disabled.status_code == 200
    assert disabled.json()["is_active"] is False
    assert enabled.status_code == 200
    assert enabled.json()["is_active"] is True
    assert "organization_created" in audit_actions
    assert "organization_disabled" in audit_actions
    assert "organization_enabled" in audit_actions
    session.close()


def test_user_management_create_roles_reject_admin_reset_disable_enable() -> None:
    session = _create_session()
    client = _admin_client(session)
    organization = _create_org(client)

    manager = client.post(
        f"/api/internal/organizations/{organization['id']}/users",
        json={"email": "manager@example.com", "password": "temporary", "role": "client_manager"},
    )
    lead = client.post(
        f"/api/internal/organizations/{organization['id']}/users",
        json={"email": "lead@example.com", "password": "temporary", "role": "client_lead"},
    )
    rejected = client.post(
        f"/api/internal/organizations/{organization['id']}/users",
        json={"email": "bad@example.com", "password": "temporary", "role": "internal_admin"},
    )
    legacy_rejected = client.post(
        f"/api/internal/organizations/{organization['id']}/users",
        json={"email": "legacy@example.com", "password": "temporary", "role": "client_user"},
    )
    user_id = manager.json()["id"]
    reset = client.post(f"/api/internal/users/{user_id}/reset-password", json={"password": "new-temp"})
    disabled = client.post(f"/api/internal/users/{user_id}/disable")
    login_disabled = client.post("/auth/login", json={"email": "manager@example.com", "password": "new-temp"})
    enabled = client.post(f"/api/internal/users/{user_id}/enable")
    login_enabled = client.post("/auth/login", json={"email": "manager@example.com", "password": "new-temp"})
    user = session.scalar(select(User).where(User.email == "manager@example.com"))

    assert manager.status_code == 201
    assert manager.json()["role"] == "client_manager"
    assert manager.json()["must_change_password"] is True
    assert lead.status_code == 201
    assert lead.json()["role"] == "client_lead"
    assert rejected.status_code == 422
    assert legacy_rejected.status_code == 422
    assert reset.status_code == 200
    assert reset.json()["must_change_password"] is True
    assert user is not None
    assert verify_password("new-temp", user.password_hash)
    assert disabled.status_code == 200
    assert login_disabled.status_code == 401
    assert enabled.status_code == 200
    assert login_enabled.status_code == 200
    session.close()


def test_internal_admin_can_open_user_analytics_detail_for_organization_user() -> None:
    session = _create_session()
    client = _admin_client(session)
    organization = _create_org(client)
    user_response = client.post(
        f"/api/internal/organizations/{organization['id']}/users",
        json={"email": "manager@example.com", "password": "temporary", "role": "client_manager"},
    )
    user_payload = user_response.json()
    config = _create_training_config(client, str(organization["id"]), "Default")
    current_session = _add_history(
        session,
        user_id=UUID(user_payload["id"]),
        client_account_id=UUID(str(organization["id"])),
        training_config_id=UUID(config["id"]),
        status="finished",
        final_interest_score=81,
        turn_count=4,
        started_at=datetime.now(UTC) - timedelta(days=1),
    )
    previous_session = _add_history(
        session,
        user_id=UUID(user_payload["id"]),
        client_account_id=UUID(str(organization["id"])),
        training_config_id=UUID(config["id"]),
        status="active",
        final_interest_score=None,
        turn_count=2,
        started_at=datetime.now(UTC) - timedelta(days=9),
    )
    _add_report(session, session_id=current_session.id, overall_score=87)
    _add_report(session, session_id=previous_session.id, overall_score=63)

    response = client.get(f"/api/internal/organizations/{organization['id']}/users/{user_payload['id']}/analytics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["user"]["email"] == "manager@example.com"
    assert payload["analytics"]["total_sessions"] == 2
    assert "trends_7d" in payload["analytics"]
    assert isinstance(payload["history"], list)
    assert len(payload["history"]) == 2
    first_history = payload["history"][0]
    assert "persona_snapshot" not in first_history
    assert "raw_llm_payload" not in first_history
    assert "raw_llm_response" not in first_history


def test_internal_admin_user_analytics_returns_404_for_other_organization_user() -> None:
    session = _create_session()
    client = _admin_client(session)
    organization_a = _create_org(client, "org-a")
    organization_b = _create_org(client, "org-b")
    other_user = client.post(
        f"/api/internal/organizations/{organization_b['id']}/users",
        json={"email": "other@example.com", "password": "temporary", "role": "client_manager"},
    ).json()

    response = client.get(f"/api/internal/organizations/{organization_a['id']}/users/{other_user['id']}/analytics")

    assert response.status_code == 404


def test_client_roles_cannot_access_internal_admin_user_analytics_endpoint() -> None:
    for role in ("client_manager", "client_lead"):
        session = _create_session()
        _seed_user(session, email=f"{role}@example.com", role=role, slug=f"{role}-org")
        client = _create_client(session)
        _login(client, email=f"{role}@example.com")
        random_org_id = "11111111-1111-1111-1111-111111111111"
        random_user_id = "22222222-2222-2222-2222-222222222222"

        response = client.get(f"/api/internal/organizations/{random_org_id}/users/{random_user_id}/analytics")

        assert response.status_code == 403
        session.close()


def test_training_config_management_assignment_cross_org_and_default() -> None:
    session = _create_session()
    client = _admin_client(session)
    org_a = _create_org(client, "org-a")
    org_b = _create_org(client, "org-b")
    user = client.post(
        f"/api/internal/organizations/{org_a['id']}/users",
        json={"email": "manager@example.com", "password": "temporary", "role": "client_manager"},
    ).json()
    config_a1 = _create_training_config(client, str(org_a["id"]), "A1")
    config_a2 = _create_training_config(client, str(org_a["id"]), "A2")
    config_b = _create_training_config(client, str(org_b["id"]), "B")

    assign_a1 = client.post(f"/api/internal/users/{user['id']}/training-configs/{config_a1['id']}/assign")
    assign_a2 = client.post(f"/api/internal/users/{user['id']}/training-configs/{config_a2['id']}/assign")
    cross_org = client.post(f"/api/internal/users/{user['id']}/training-configs/{config_b['id']}/assign")
    make_default = client.post(f"/api/internal/users/{user['id']}/training-configs/{config_a2['id']}/make-default")
    assignments = list(session.scalars(select(UserTrainingConfig).where(UserTrainingConfig.user_id == UUID(user["id"]))))

    assert assign_a1.status_code == 200
    assert assign_a2.status_code == 200
    assert cross_org.status_code == 422
    assert make_default.status_code == 200
    assert make_default.json()["is_default"] is True
    assert sum(1 for assignment in assignments if assignment.is_default) == 1
    session.close()


def test_training_config_create_and_update_work_without_llm_provider_config() -> None:
    session = _create_session()
    client = _admin_client(session)
    organization = _create_org(client)

    create_response = client.post(
        f"/api/internal/organizations/{organization['id']}/training-configs",
        json={
            "name": "Prompt config",
            "persona_generation_context": "Final decision-maker for accounting outsourcing with objections about control.",
        },
    )
    config_id = create_response.json()["id"]
    update_response = client.patch(
        f"/api/internal/training-configs/{config_id}",
        json={"persona_generation_context": "Updated persona context for generation."},
    )

    assert create_response.status_code == 201
    assert create_response.json()["persona_generation_context"].startswith("Final decision-maker")
    assert "default_scenario_id" not in create_response.json()
    assert "persona_policy" not in create_response.json()
    assert "ui_config" not in create_response.json()
    assert "limits" not in create_response.json()
    assert "llm_provider_config_id" not in create_response.json()
    assert update_response.status_code == 200
    assert update_response.json()["persona_generation_context"] == "Updated persona context for generation."
    session.close()


def test_training_config_create_accepts_minimal_payload() -> None:
    session = _create_session()
    client = _admin_client(session)
    organization = _create_org(client)

    response = client.post(
        f"/api/internal/organizations/{organization['id']}/training-configs",
        json={
            "name": "Accounting outsourcing",
            "persona_generation_context": "Final decision-maker for accounting outsourcing with objections about control.",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["name"] == "Accounting outsourcing"
    assert payload["persona_generation_context"].startswith("Final decision-maker")
    assert set(payload) == {
        "id",
        "client_account_id",
        "name",
        "is_active",
        "persona_generation_context",
        "created_at",
        "updated_at",
    }
    stored = session.get(ClientTrainingConfig, UUID(str(payload["id"])))
    assert stored is not None
    column_names = {column["name"] for column in inspect(session.bind).get_columns("client_training_configs")}
    assert "default_scenario_id" not in column_names
    assert "persona_policy" not in column_names
    assert "ui_config" not in column_names
    assert "limits" not in column_names
    assert "llm_provider_config_id" not in column_names
    assert "default_scenario_id" not in ClientTrainingConfig.__table__.columns.keys()
    assert "persona_policy" not in ClientTrainingConfig.__table__.columns.keys()
    assert "ui_config" not in ClientTrainingConfig.__table__.columns.keys()
    assert "limits" not in ClientTrainingConfig.__table__.columns.keys()
    assert "llm_provider_config_id" not in ClientTrainingConfig.__table__.columns.keys()
    session.close()


def test_training_config_create_rejects_legacy_payload() -> None:
    session = _create_session()
    client = _admin_client(session)
    organization = _create_org(client)

    response = client.post(
        f"/api/internal/organizations/{organization['id']}/training-configs",
        json={
            "name": "Legacy rejected",
            "default_scenario_id": "generic_b2b_first_contact",
            "persona_generation_context": "Legacy frontend adapter payload.",
            "persona_policy": {},
            "ui_config": {},
            "limits": {},
            "llm_provider_config_id": "11111111-1111-1111-1111-111111111111",
        },
    )

    assert response.status_code == 422
    session.close()


def test_training_config_update_accepts_minimal_payload() -> None:
    session = _create_session()
    client = _admin_client(session)
    organization = _create_org(client)
    config = _create_training_config(client, str(organization["id"]))

    response = client.patch(
        f"/api/internal/training-configs/{config['id']}",
        json={
            "name": "Updated",
            "persona_generation_context": "Updated context",
        },
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated"
    assert response.json()["persona_generation_context"] == "Updated context"
    assert "default_scenario_id" not in response.json()
    assert "persona_policy" not in response.json()
    assert "ui_config" not in response.json()
    assert "limits" not in response.json()
    assert "llm_provider_config_id" not in response.json()
    session.close()


def test_training_config_update_rejects_legacy_fields() -> None:
    session = _create_session()
    client = _admin_client(session)
    organization = _create_org(client)
    config = _create_training_config(client, str(organization["id"]))

    response = client.patch(
        f"/api/internal/training-configs/{config['id']}",
        json={
            "default_scenario_id": "generic_b2b_first_contact",
            "persona_policy": {},
            "ui_config": {},
            "limits": {},
            "llm_provider_config_id": "11111111-1111-1111-1111-111111111111",
        },
    )

    assert response.status_code == 422
    session.close()


def test_llm_provider_config_secret_masking_storage_update_disable() -> None:
    session = _create_session()
    client = _admin_client(session)
    organization = _create_org(client)

    create_response = client.post(
        f"/api/internal/organizations/{organization['id']}/llm-provider-configs",
        json={
            "name": "Yandex main agent",
            "provider": "yandex_compatible",
            "api_key": "abcd-secret-yz",
            "folder_id": "folder",
            "agent_id": "agent",
            "base_url": "https://ai.api.cloud.yandex.net/v1",
        },
    )
    payload = create_response.json()
    stored = session.get(LLMProviderConfig, UUID(payload["id"]))
    update_response = client.patch(
        f"/api/internal/llm-provider-configs/{payload['id']}",
        json={"name": "Yandex updated"},
    )
    disable_response = client.post(f"/api/internal/llm-provider-configs/{payload['id']}/disable")
    assert create_response.status_code == 201
    assert payload["has_api_key"] is True
    assert payload["api_key_preview"] == "abcd...yz"
    assert "api_key" not in payload
    assert stored is not None
    assert stored.encrypted_api_key != "abcd-secret-yz"
    assert decrypt_secret(stored.encrypted_api_key, Settings(secret_encryption_key="test-secret-key")) == "abcd-secret-yz"
    assert update_response.status_code == 200
    assert update_response.json()["api_key_preview"] == "abcd...yz"
    assert disable_response.status_code == 200
    assert disable_response.json()["is_active"] is False
    assert "abcd-secret-yz" not in str([record.payload for record in session.scalars(select(AuditLog))])
    session.close()


def test_llm_provider_config_two_yandex_sets_and_blank_key_update() -> None:
    session = _create_session()
    client = _admin_client(session)
    organization = _create_org(client)

    create_response = client.post(
        f"/api/internal/organizations/{organization['id']}/llm-provider-configs",
        json={
            "name": "Yandex demo",
            "provider": "yandex_compatible",
            "persona_api_key": "persona-secret-key",
            "persona_folder_id": "persona-folder",
            "persona_agent_id": "persona-agent",
            "dialogue_api_key": "dialogue-secret-key",
            "dialogue_folder_id": "dialogue-folder",
            "dialogue_agent_id": "dialogue-agent",
        },
    )
    payload = create_response.json()
    stored = session.get(LLMProviderConfig, UUID(payload["id"]))
    update_response = client.patch(
        f"/api/internal/llm-provider-configs/{payload['id']}",
        json={"persona_api_key": "", "dialogue_api_key": "", "name": "Yandex demo updated"},
    )
    updated = session.get(LLMProviderConfig, UUID(payload["id"]))
    audit_payloads = [record.payload for record in session.scalars(select(AuditLog))]

    assert create_response.status_code == 201
    assert payload["has_persona_api_key"] is True
    assert payload["persona_api_key_preview"] == "pers...ey"
    assert payload["has_dialogue_api_key"] is True
    assert payload["dialogue_api_key_preview"] == "dial...ey"
    assert "persona_api_key" not in payload
    assert "dialogue_api_key" not in payload
    assert stored is not None
    assert stored.persona_api_key_encrypted != "persona-secret-key"
    assert stored.dialogue_api_key_encrypted != "dialogue-secret-key"
    assert decrypt_secret(stored.persona_api_key_encrypted, Settings(secret_encryption_key="test-secret-key")) == "persona-secret-key"
    assert decrypt_secret(stored.dialogue_api_key_encrypted, Settings(secret_encryption_key="test-secret-key")) == "dialogue-secret-key"
    assert update_response.status_code == 200
    assert updated is not None
    assert decrypt_secret(updated.persona_api_key_encrypted, Settings(secret_encryption_key="test-secret-key")) == "persona-secret-key"
    assert decrypt_secret(updated.dialogue_api_key_encrypted, Settings(secret_encryption_key="test-secret-key")) == "dialogue-secret-key"
    assert "persona-secret-key" not in str(audit_payloads)
    assert "dialogue-secret-key" not in str(audit_payloads)
    session.close()


def test_internal_admin_schema_validation_rejects_invalid_inputs() -> None:
    session = _create_session()
    client = _admin_client(session)

    invalid_slug = client.post("/api/internal/organizations", json={"name": "Acme", "slug": "Bad Slug"})
    organization = _create_org(client)
    invalid_email = client.post(
        f"/api/internal/organizations/{organization['id']}/users",
        json={"email": "not-email", "password": "temporary", "role": "client_manager"},
    )
    short_password = client.post(
        f"/api/internal/organizations/{organization['id']}/users",
        json={"email": "short@example.com", "password": "short", "role": "client_manager"},
    )
    legacy_training_config_payload = client.post(
        f"/api/internal/organizations/{organization['id']}/training-configs",
        json={
            "name": "Legacy payload",
            "default_scenario_id": "missing",
        },
    )
    invalid_provider = client.post(
        f"/api/internal/organizations/{organization['id']}/llm-provider-configs",
        json={"name": "Provider", "provider": "unknown"},
    )

    assert invalid_slug.status_code == 422
    assert invalid_email.status_code == 422
    assert short_password.status_code == 422
    assert legacy_training_config_payload.status_code == 422
    assert invalid_provider.status_code == 422
    session.close()


def test_audit_log_filters_by_organization_before_limit_and_payload_has_org_id() -> None:
    session = _create_session()
    client = _admin_client(session)
    org_a = _create_org(client, "audit-a")
    org_b = _create_org(client, "audit-b")
    _create_training_config(client, str(org_b["id"]), "B1")
    _create_training_config(client, str(org_b["id"]), "B2")
    _create_training_config(client, str(org_a["id"]), "A1")

    response = client.get(f"/api/internal/audit-log?organization_id={org_a['id']}&limit=1")
    payload = response.json()

    assert response.status_code == 200
    assert len(payload) == 1
    assert payload[0]["payload"]["organization_id"] == org_a["id"]
    for record in session.scalars(select(AuditLog).where(AuditLog.action.like("%created"))):
        assert "organization_id" in record.payload
        assert "client_account_id" in record.payload
    session.close()
