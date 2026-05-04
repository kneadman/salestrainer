from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.infrastructure.config import Settings, get_settings


class Base(DeclarativeBase):
    """Shared declarative base for future relational models."""


def import_model_modules() -> None:
    """Import ORM model modules before metadata access when models are added."""
    import app.access.models  # noqa: F401
    import app.history.models  # noqa: F401
    import app.identity.models  # noqa: F401


def create_db_engine(settings: Settings | None = None) -> Engine:
    resolved_settings = settings or get_settings()
    return create_engine(
        resolved_settings.database_url,
        pool_pre_ping=True,
    )


@lru_cache(maxsize=1)
def get_db_engine() -> Engine:
    return create_db_engine()


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(
        bind=get_db_engine(),
        autoflush=False,
        expire_on_commit=False,
        class_=Session,
    )


def get_db_session() -> Generator[Session, None, None]:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
