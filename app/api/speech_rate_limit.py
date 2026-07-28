from __future__ import annotations

import logging
import time
from collections.abc import Callable

from redis import Redis
from redis.exceptions import RedisError

from app.infrastructure.config import Settings
from app.infrastructure.rate_limit import InMemoryFixedWindowRateLimiter, RedisFixedWindowRateLimiter
from app.infrastructure.redis_client import create_redis_client

logger = logging.getLogger(__name__)


class SpeechRateLimitExceeded(Exception):
    """Raised when an STT request exceeds a configured rate bucket."""

    pass


class SpeechRateLimiter:
    """Describe a limiter for authenticated STT requests."""

    def hit(self, *, user_id: str) -> None:
        """Record one request for the authenticated user or raise when limited."""
        raise NotImplementedError


class NoopSpeechRateLimiter(SpeechRateLimiter):
    """Disable STT request rate limiting."""

    def hit(self, *, user_id: str) -> None:
        """Accept every STT request."""
        return None


class InMemorySpeechRateLimiter(SpeechRateLimiter):
    """Apply local fixed-window STT limits for one process."""

    def __init__(
        self,
        *,
        max_user_attempts: int,
        max_global_attempts: int,
        window_seconds: int,
        time_provider: Callable[[], float] = time.monotonic,
    ) -> None:
        self._max_user_attempts = max_user_attempts
        self._max_global_attempts = max_global_attempts
        self._engine = InMemoryFixedWindowRateLimiter(window_seconds=window_seconds, time_provider=time_provider)

    def hit(self, *, user_id: str) -> None:
        """Increment user/global buckets and reject requests over either limit."""
        self._engine.hit(
            buckets=_speech_rate_limit_keys(
                user_id=user_id,
                max_user_attempts=self._max_user_attempts,
                max_global_attempts=self._max_global_attempts,
            ),
            exceeded_error=SpeechRateLimitExceeded,
        )


class RedisSpeechRateLimiter(SpeechRateLimiter):
    """Apply shared Redis-backed fixed-window STT limits."""

    def __init__(
        self,
        *,
        client: Redis,
        max_user_attempts: int,
        max_global_attempts: int,
        window_seconds: int,
    ) -> None:
        self._max_user_attempts = max_user_attempts
        self._max_global_attempts = max_global_attempts
        self._engine = RedisFixedWindowRateLimiter(
            client=client,
            window_seconds=window_seconds,
            key_prefix="stt-rate:",
            on_redis_error=lambda: logger.warning("speech_rate_limiter_redis_hit_failed", exc_info=True),
        )

    def hit(self, *, user_id: str) -> None:
        """Increment Redis user/global buckets and reject requests over either limit."""
        self._engine.hit(
            buckets=_speech_rate_limit_keys(
                user_id=user_id,
                max_user_attempts=self._max_user_attempts,
                max_global_attempts=self._max_global_attempts,
            ),
            exceeded_error=SpeechRateLimitExceeded,
        )


def build_speech_rate_limiter(settings: Settings) -> SpeechRateLimiter:
    """Build an STT rate limiter without making local/test startup depend on Redis."""
    if settings.stt_rate_limit_attempts <= 0 and settings.stt_global_rate_limit_attempts <= 0:
        return NoopSpeechRateLimiter()
    if settings.is_local_env:
        return InMemorySpeechRateLimiter(
            max_user_attempts=settings.stt_rate_limit_attempts,
            max_global_attempts=settings.stt_global_rate_limit_attempts,
            window_seconds=settings.stt_rate_limit_window_seconds,
        )
    try:
        client = create_redis_client(settings)
        client.ping()
        return RedisSpeechRateLimiter(
            client=client,
            max_user_attempts=settings.stt_rate_limit_attempts,
            max_global_attempts=settings.stt_global_rate_limit_attempts,
            window_seconds=settings.stt_rate_limit_window_seconds,
        )
    except RedisError:
        logger.warning("speech_rate_limiter_redis_unavailable_falling_back_to_in_memory", exc_info=True)
        return InMemorySpeechRateLimiter(
            max_user_attempts=settings.stt_rate_limit_attempts,
            max_global_attempts=settings.stt_global_rate_limit_attempts,
            window_seconds=settings.stt_rate_limit_window_seconds,
        )


def _speech_rate_limit_keys(
    *,
    user_id: str,
    max_user_attempts: int,
    max_global_attempts: int,
) -> list[tuple[str, int]]:
    """Return active rate-limit buckets and their configured thresholds."""
    keys: list[tuple[str, int]] = []
    if max_user_attempts > 0:
        keys.append((f"user:{user_id.strip()}", max_user_attempts))
    if max_global_attempts > 0:
        keys.append(("global", max_global_attempts))
    return keys
