from __future__ import annotations

import logging

from redis import Redis
from redis.exceptions import RedisError

from app.domain.errors import RepositoryUnavailableError
from app.infrastructure.config import Settings
from app.infrastructure.session_repository import InMemorySessionRepository, RedisSessionRepository, SessionRepository

logger = logging.getLogger(__name__)


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
    if settings.allow_in_memory_repository or settings.is_local_env:
        logger.warning("redis_unavailable fallback=in_memory redis_url=%s", settings.redis_url)
        return InMemorySessionRepository()
    raise RepositoryUnavailableError(
        f"Redis is unavailable at '{settings.redis_url}' and in-memory fallback is disabled."
    )
