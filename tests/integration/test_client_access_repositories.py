from __future__ import annotations

from uuid import uuid4

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.access.repository import AccessRepository
from app.identity.repository import IdentityRepository
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


def test_create_client_account_and_user_for_client() -> None:
    session = _create_session()
    identity_repository = IdentityRepository(session)

    client_account = identity_repository.create_client_account(
        name="Acme Corp",
        slug="acme",
    )
    user = identity_repository.create_user(
        client_account_id=client_account.id,
        email="manager@acme.test",
        password_hash="hash-1",
    )

    assert identity_repository.get_client_account_by_slug("acme") is not None
    assert identity_repository.get_client_account_by_slug("acme").id == client_account.id
    assert identity_repository.get_user_by_email("manager@acme.test") is not None
    assert identity_repository.get_user_by_email("manager@acme.test").id == user.id
    assert identity_repository.get_user_by_id(user.id) is not None
    assert identity_repository.get_user_by_id(user.id).client_account_id == client_account.id

    session.close()


def test_training_config_assignment_and_session_ownership() -> None:
    session = _create_session()
    identity_repository = IdentityRepository(session)
    access_repository = AccessRepository(session)

    client_account = identity_repository.create_client_account(
        name="Beta LLC",
        slug="beta",
    )
    user = identity_repository.create_user(
        client_account_id=client_account.id,
        email="seller@beta.test",
        password_hash="hash-2",
    )
    training_config = access_repository.create_training_config(
        client_account_id=client_account.id,
        name="Outbound Core",
        default_scenario_id="sales_audit_cold_outreach",
        product_line="accounting_outsourcing",
        persona_generation_prompt="Owner persona for accounting outsourcing discovery.",
        persona_policy={"persona_ids": ["owner"]},
        ui_config={"theme": "light"},
        limits={"max_turns": 12},
    )

    assignment = access_repository.assign_training_config_to_user(
        user_id=user.id,
        training_config_id=training_config.id,
        is_default=True,
    )
    default_config = access_repository.get_default_training_config_for_user(user.id)

    assert assignment.is_default is True
    assert default_config is not None
    assert default_config.id == training_config.id
    assert default_config.client_account_id == client_account.id
    assert default_config.persona_generation_prompt == "Owner persona for accounting outsourcing discovery."
    assert default_config.persona_policy == {"persona_ids": ["owner"]}

    session_id = uuid4()
    ownership = access_repository.create_training_session_ownership(
        session_id=session_id,
        user_id=user.id,
        client_account_id=client_account.id,
        training_config_id=training_config.id,
    )

    assert ownership.session_id == session_id
    assert access_repository.check_session_ownership(
        session_id=session_id,
        user_id=user.id,
        client_account_id=client_account.id,
    )
    assert not access_repository.check_session_ownership(
        session_id=session_id,
        user_id=uuid4(),
        client_account_id=client_account.id,
    )

    session.close()
