from __future__ import annotations

import pytest

from app.application.session_service import TrainingSessionService
from app.infrastructure.config import Settings
from app.infrastructure.redis_client import create_redis_client, redis_is_available
from app.infrastructure.session_repository import RedisSessionRepository


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
