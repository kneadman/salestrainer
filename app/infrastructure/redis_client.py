from __future__ import annotations

from redis import Redis
from redis.exceptions import RedisError

from app.infrastructure.config import Settings
from app.infrastructure.session_repository import InMemorySessionRepository, RedisSessionRepository, SessionRepository


def create_redis_client(settings: Settings) -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True)


def redis_is_available(settings: Settings) -> bool:
    try:
        client = create_redis_client(settings)
        return bool(client.ping())
    except RedisError:
        return False


def build_repository(settings: Settings) -> SessionRepository:
    if redis_is_available(settings):
        client = create_redis_client(settings)
        return RedisSessionRepository(client=client, ttl_seconds=settings.session_ttl_seconds)
    else:
        return InMemorySessionRepository()
