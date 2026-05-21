from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.access.models import AuditLog
from app.access.repository import AccessRepository
from app.admin.cli import (
    _assign_config,
    _cleanup_expired_sessions,
    _create_config,
    _create_internal_admin,
    _create_user,
    _disable_user,
    _reset_password,
    _update_config,
)
from app.identity.models import LoginSession
from app.identity.repository import IdentityRepository
from app.identity.security import hash_password, hash_token, verify_password
from app.infrastructure.db import Base, import_model_modules


def _create_session() -> Session:
    import_model_modules()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:  # type: ignore[no-untyped-def]
        del connection_record
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)
    return session_factory()


def test_create_user_stores_hash_not_raw_password() -> None:
    session = _create_session()
    identity_repository = IdentityRepository(session)
    client = identity_repository.create_client_account(name="Romashka", slug="romashka")

    _create_user(
        identity_repository=identity_repository,
        client_slug=client.slug,
        email="manager@romashka.test",
        password="TempPass123",
    )

    created_user = identity_repository.get_user_by_email("manager@romashka.test")
    assert created_user is not None
    assert created_user.password_hash != "TempPass123"
    assert verify_password("TempPass123", created_user.password_hash)
    session.close()


def test_create_internal_admin_bootstraps_first_admin_only() -> None:
    session = _create_session()
    identity_repository = IdentityRepository(session)
    access_repository = AccessRepository(session)

    message = _create_internal_admin(
        identity_repository=identity_repository,
        access_repository=access_repository,
        client_name="Platform",
        client_slug="platform",
        email="admin@example.test",
        password="TempPass123",
    )
    created_user = identity_repository.get_user_by_email("admin@example.test")

    assert "created internal admin" in message
    assert created_user is not None
    assert created_user.role == "internal_admin"
    audit_record = session.scalar(select(AuditLog).where(AuditLog.action == "internal_admin_bootstrapped"))
    assert audit_record is not None
    assert audit_record.payload["client_account_id"] == str(created_user.client_account_id)

    try:
        _create_internal_admin(
            identity_repository=identity_repository,
            access_repository=access_repository,
            client_name="Platform",
            client_slug="platform",
            email="other-admin@example.test",
            password="TempPass123",
        )
    except Exception as error:
        assert "internal admin already exists" in str(error)
    else:
        raise AssertionError("second internal admin bootstrap should fail")
    session.close()


def test_reset_password_changes_hash() -> None:
    session = _create_session()
    identity_repository = IdentityRepository(session)
    client = identity_repository.create_client_account(name="Romashka", slug="romashka")
    user = identity_repository.create_user(
        client_account_id=client.id,
        email="manager@romashka.test",
        password_hash=hash_password("old-password"),
        must_change_password=False,
    )
    old_hash = user.password_hash

    access_repository = AccessRepository(session)
    _reset_password(
        identity_repository=identity_repository,
        access_repository=access_repository,
        email=user.email,
        password="newtemppass",
    )

    updated_user = identity_repository.get_user_by_email(user.email)
    assert updated_user is not None
    assert updated_user.password_hash != old_hash
    assert updated_user.must_change_password is True
    assert verify_password("newtemppass", updated_user.password_hash)
    audit_record = session.scalar(select(AuditLog).where(AuditLog.action == "password_reset"))
    assert audit_record is not None
    assert audit_record.entity_id == user.id
    session.close()


def test_reset_password_rejects_invalid_permanent_password() -> None:
    session = _create_session()
    identity_repository = IdentityRepository(session)
    client = identity_repository.create_client_account(name="Romashka", slug="romashka")
    user = identity_repository.create_user(
        client_account_id=client.id,
        email="manager@romashka.test",
        password_hash=hash_password("old-password"),
        must_change_password=False,
    )

    access_repository = AccessRepository(session)
    try:
        _reset_password(
            identity_repository=identity_repository,
            access_repository=access_repository,
            email=user.email,
            password="short",
        )
    except Exception as error:
        assert "at least 8 characters" in str(error)
    else:
        raise AssertionError("expected password validation error")
    session.close()


def test_create_user_rejects_invalid_password() -> None:
    session = _create_session()
    identity_repository = IdentityRepository(session)
    client = identity_repository.create_client_account(name="Romashka", slug="romashka")

    try:
        _create_user(
            identity_repository=identity_repository,
            client_slug=client.slug,
            email="manager@romashka.test",
            password="short",
        )
    except Exception as error:
        assert "at least 8 characters" in str(error)
    else:
        raise AssertionError("expected password validation error")
    session.close()


def test_create_internal_admin_rejects_invalid_password() -> None:
    session = _create_session()
    identity_repository = IdentityRepository(session)
    access_repository = AccessRepository(session)

    try:
        _create_internal_admin(
            identity_repository=identity_repository,
            access_repository=access_repository,
            client_name="Platform",
            client_slug="platform",
            email="admin@example.test",
            password="short",
        )
    except Exception as error:
        assert "at least 8 characters" in str(error)
    else:
        raise AssertionError("expected password validation error")
    session.close()


def test_disable_user_sets_user_inactive() -> None:
    session = _create_session()
    identity_repository = IdentityRepository(session)
    client = identity_repository.create_client_account(name="Romashka", slug="romashka")
    user = identity_repository.create_user(
        client_account_id=client.id,
        email="manager@romashka.test",
        password_hash=hash_password("password"),
    )
    assert user.is_active is True

    access_repository = AccessRepository(session)
    _disable_user(
        identity_repository=identity_repository,
        access_repository=access_repository,
        email=user.email,
    )

    updated_user = identity_repository.get_user_by_email(user.email)
    assert updated_user is not None
    assert updated_user.is_active is False
    audit_record = session.scalar(select(AuditLog).where(AuditLog.action == "user_disabled"))
    assert audit_record is not None
    assert audit_record.entity_id == user.id
    session.close()


def test_assign_config_sets_default_config() -> None:
    session = _create_session()
    identity_repository = IdentityRepository(session)
    access_repository = AccessRepository(session)
    client = identity_repository.create_client_account(name="Romashka", slug="romashka")
    user = identity_repository.create_user(
        client_account_id=client.id,
        email="manager@romashka.test",
        password_hash=hash_password("password"),
    )
    other_config = access_repository.create_training_config(client_account_id=client.id, name="Other Config")
    access_repository.assign_training_config_to_user(
        user_id=user.id,
        training_config_id=other_config.id,
        is_default=True,
    )
    target_config = access_repository.create_training_config(client_account_id=client.id, name="Accounting Config")

    _assign_config(
        identity_repository=identity_repository,
        access_repository=access_repository,
        email=user.email,
        config_name=target_config.name,
        is_default=True,
    )

    default_config = access_repository.get_default_training_config_for_user(user.id)
    assert default_config is not None
    assert default_config.id == target_config.id
    audit_record = session.scalar(select(AuditLog).where(AuditLog.action == "config_assigned"))
    assert audit_record is not None
    assert audit_record.entity_id == target_config.id
    session.close()


def test_create_config_writes_audit_log() -> None:
    session = _create_session()
    identity_repository = IdentityRepository(session)
    access_repository = AccessRepository(session)
    client = identity_repository.create_client_account(name="Romashka", slug="romashka")

    _create_config(
        identity_repository=identity_repository,
        access_repository=access_repository,
        client_slug=client.slug,
        name="Accounting Config",
    )

    audit_record = session.scalar(select(AuditLog).where(AuditLog.action == "config_created"))
    assert audit_record is not None
    assert audit_record.entity_type == "client_training_config"
    session.close()


def test_update_config_writes_audit_log() -> None:
    session = _create_session()
    identity_repository = IdentityRepository(session)
    access_repository = AccessRepository(session)
    client = identity_repository.create_client_account(name="Romashka", slug="romashka")
    config = access_repository.create_training_config(client_account_id=client.id, name="Accounting Config")

    _update_config(
        identity_repository=identity_repository,
        access_repository=access_repository,
        client_slug=client.slug,
        config_name=config.name,
        new_name="Updated Config",
    )

    audit_record = session.scalar(select(AuditLog).where(AuditLog.action == "config_updated"))
    assert audit_record is not None
    assert audit_record.entity_id == config.id
    session.close()


def test_cleanup_expired_sessions_deletes_only_expired_sessions() -> None:
    session = _create_session()
    identity_repository = IdentityRepository(session)
    client = identity_repository.create_client_account(name="Romashka", slug="romashka")
    user = identity_repository.create_user(
        client_account_id=client.id,
        email="manager@romashka.test",
        password_hash=hash_password("password"),
    )
    expired_session = LoginSession(
        user_id=user.id,
        token_hash=hash_token("expired"),
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    active_session = LoginSession(
        user_id=user.id,
        token_hash=hash_token("active"),
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    session.add_all([expired_session, active_session])
    session.commit()

    message = _cleanup_expired_sessions(identity_repository=identity_repository)

    assert message == "cleaned up expired login sessions: 1"
    remaining_sessions = list(session.scalars(select(LoginSession)))
    assert [login_session.token_hash for login_session in remaining_sessions] == [active_session.token_hash]
    session.close()


def test_snapshot_token_usage_creates_daily_snapshot() -> None:
    """Verify snapshot-token-usage CLI creates a TokenUsageSnapshot from TokenUsageRecord rows."""
    from datetime import UTC, datetime, timedelta
    from uuid import uuid4

    from app.admin.cli import _snapshot_token_usage
    from app.history.models import TokenUsageRecord, TokenUsageSnapshot
    from app.history.repository import HistoryRepository
    from app.history.service import HistoryService
    from app.identity.repository import IdentityRepository

    session = _create_session()
    identity_repository = IdentityRepository(session)
    client = identity_repository.create_client_account(name="Snapshot Corp", slug="snapshot-corp")
    user = identity_repository.create_user(
        client_account_id=client.id,
        email="manager@snapshot.test",
        password_hash=hash_password("password"),
        role="client_manager",
    )

    # Seed token usage records for yesterday
    yesterday = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    session.add_all([
        TokenUsageRecord(
            id=uuid4(),
            client_account_id=client.id,
            user_id=user.id,
            session_id=uuid4(),
            event_type="dialogue",
            input_tokens=100,
            output_tokens=50,
            created_at=yesterday + timedelta(hours=10),
        ),
        TokenUsageRecord(
            id=uuid4(),
            client_account_id=client.id,
            user_id=user.id,
            session_id=uuid4(),
            event_type="judge",
            input_tokens=200,
            output_tokens=100,
            created_at=yesterday + timedelta(hours=11),
        ),
    ])
    session.commit()

    history_repository = HistoryRepository(session)
    history_service = HistoryService(history_repository)

    date_str = yesterday.strftime("%Y-%m-%d")
    message = _snapshot_token_usage(
        history_service=history_service,
        date_str=date_str,
    )

    assert "created" in message
    snapshot = session.scalar(select(TokenUsageSnapshot).where(TokenUsageSnapshot.client_account_id == client.id))
    assert snapshot is not None
    assert snapshot.input_tokens == 300
    assert snapshot.output_tokens == 150
    assert snapshot.total_tokens == 450
    assert snapshot.snapshot_date.date() == yesterday.date()

    session.close()


def test_snapshot_token_usage_is_idempotent() -> None:
    """Verify running snapshot-token-usage twice for the same date does not raise."""
    from datetime import UTC, datetime, timedelta
    from uuid import uuid4

    from app.admin.cli import _snapshot_token_usage
    from app.history.models import TokenUsageRecord
    from app.history.repository import HistoryRepository
    from app.history.service import HistoryService
    from app.identity.repository import IdentityRepository

    session = _create_session()
    identity_repository = IdentityRepository(session)
    client = identity_repository.create_client_account(name="Idempotent Corp", slug="idempotent-corp")
    user = identity_repository.create_user(
        client_account_id=client.id,
        email="manager@idempotent.test",
        password_hash=hash_password("password"),
        role="client_manager",
    )

    yesterday = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    session.add(
        TokenUsageRecord(
            id=uuid4(),
            client_account_id=client.id,
            user_id=user.id,
            session_id=uuid4(),
            event_type="dialogue",
            input_tokens=50,
            output_tokens=25,
            created_at=yesterday + timedelta(hours=10),
        )
    )
    session.commit()

    history_repository = HistoryRepository(session)
    history_service = HistoryService(history_repository)
    date_str = yesterday.strftime("%Y-%m-%d")

    _snapshot_token_usage(history_service=history_service, date_str=date_str)
    # Second run should not raise (upsert/unique constraint handled gracefully)
    message = _snapshot_token_usage(history_service=history_service, date_str=date_str)
    assert "created" in message or "0 organizations" in message

    session.close()
