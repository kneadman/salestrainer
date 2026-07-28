from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from redis import Redis
from redis.exceptions import RedisError


@dataclass
class _Bucket:
    count: int
    reset_at: float


class InMemoryFixedWindowRateLimiter:
    """Increment local fixed-window buckets and raise when one exceeds its limit."""

    def __init__(self, *, window_seconds: int, time_provider: Callable[[], float] = time.monotonic) -> None:
        self._window_seconds = window_seconds
        self._time_provider = time_provider
        self._buckets: dict[str, _Bucket] = {}
        self._lock = threading.Lock()

    def hit(self, *, buckets: list[tuple[str, int]], exceeded_error: type[Exception]) -> None:
        now = self._time_provider()
        with self._lock:
            for key, max_attempts in buckets:
                bucket = self._buckets.get(key)
                if bucket is None or bucket.reset_at <= now:
                    bucket = _Bucket(count=0, reset_at=now + self._window_seconds)
                    self._buckets[key] = bucket
                bucket.count += 1
                if bucket.count > max_attempts:
                    raise exceeded_error


class RedisFixedWindowRateLimiter:
    """Increment shared Redis fixed-window buckets and raise when one exceeds its limit."""

    def __init__(
        self,
        *,
        client: Redis,
        window_seconds: int,
        key_prefix: str,
        on_redis_error: Callable[[], None] | None = None,
    ) -> None:
        self._client = client
        self._window_seconds = window_seconds
        self._key_prefix = key_prefix
        self._on_redis_error = on_redis_error

    def hit(self, *, buckets: list[tuple[str, int]], exceeded_error: type[Exception]) -> None:
        for key, max_attempts in buckets:
            redis_key = f"{self._key_prefix}{key}"
            try:
                count = int(self._client.incr(redis_key))
                if count == 1:
                    self._client.expire(redis_key, self._window_seconds)
            except RedisError:
                if self._on_redis_error is not None:
                    self._on_redis_error()
                continue
            if count > max_attempts:
                raise exceeded_error
