from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.access.repository import AccessRepository
from app.admin.cli import _assign_config, _create_user, _disable_user, _reset_password
from app.identity.repository import IdentityRepository
from app.identity.security import hash_password, verify_password
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
        password="temporary-password",
    )

    created_user = identity_repository.get_user_by_email("manager@romashka.test")
    assert created_user is not None
    assert created_user.password_hash != "temporary-password"
    assert verify_password("temporary-password", created_user.password_hash)
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

    _reset_password(
        identity_repository=identity_repository,
        email=user.email,
        password="new-temporary-password",
    )

    updated_user = identity_repository.get_user_by_email(user.email)
    assert updated_user is not None
    assert updated_user.password_hash != old_hash
    assert updated_user.must_change_password is True
    assert verify_password("new-temporary-password", updated_user.password_hash)
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

    _disable_user(
        identity_repository=identity_repository,
        email=user.email,
    )

    updated_user = identity_repository.get_user_by_email(user.email)
    assert updated_user is not None
    assert updated_user.is_active is False
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
    other_config = access_repository.create_training_config(
        client_account_id=client.id,
        name="Other Config",
        default_scenario_id="generic_b2b_first_contact",
        product_line="accounting_outsourcing",
        persona_policy={},
    )
    access_repository.assign_training_config_to_user(
        user_id=user.id,
        training_config_id=other_config.id,
        is_default=True,
    )
    target_config = access_repository.create_training_config(
        client_account_id=client.id,
        name="Accounting Config",
        default_scenario_id="generic_b2b_first_contact",
        product_line="accounting_outsourcing",
        persona_policy={},
    )

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
    session.close()
