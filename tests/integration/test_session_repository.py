from __future__ import annotations

import pytest

from app.application.session_service import TrainingSessionService
from app.domain.errors import RepositoryUnavailableError
from app.infrastructure.config import Settings
from app.infrastructure.redis_client import build_repository, create_redis_client, redis_is_available
from app.infrastructure.session_repository import InMemorySessionRepository, RedisSessionRepository


def test_redis_session_repository_roundtrip() -> None:
    settings = Settings()
    if not redis_is_available(settings):
        pytest.skip(f"Redis is not available at {settings.redis_url}")

    client = create_redis_client(settings)
    repository = RedisSessionRepository(client=client, ttl_seconds=30)
    session_service = TrainingSessionService(repository)
    session = session_service.start_session("sales_audit_cold_outreach", "owner")

    loaded = repository.get(str(session.session_id))
    assert loaded is not None
    assert loaded.session_id == session.session_id
    assert loaded.scenario_id == session.scenario_id
    assert loaded.status == "active"

    loaded.turn_count = 2
    repository.save(loaded)
    saved_again = repository.get(str(session.session_id))
    assert saved_again is not None
    assert saved_again.turn_count == 2

    ttl = client.ttl(f"sales_trainer:session:{session.session_id}")
    assert ttl > 0

    repository.delete(str(session.session_id))
    assert repository.get(str(session.session_id)) is None


def test_build_repository_falls_back_to_in_memory_in_local_mode(monkeypatch) -> None:
    monkeypatch.setattr("app.infrastructure.redis_client.redis_is_available", lambda settings: False)
    repository = build_repository(Settings(app_env="local", allow_in_memory_repository=False))
    assert isinstance(repository, InMemorySessionRepository)


def test_build_repository_raises_when_redis_is_unavailable_and_fallback_is_disabled(monkeypatch) -> None:
    monkeypatch.setattr("app.infrastructure.redis_client.redis_is_available", lambda settings: False)

    with pytest.raises(RepositoryUnavailableError, match="in-memory fallback is disabled"):
        build_repository(Settings(app_env="prod", allow_in_memory_repository=False))
