from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from redis import Redis
from redis.exceptions import RedisError

from app.infrastructure.config import Settings
from app.infrastructure.redis_client import create_redis_client


class LoginRateLimitExceeded(Exception):
    pass


class LoginRateLimiter:
    def hit(self, *, email: str, ip_address: str | None) -> None:
        raise NotImplementedError


class NoopLoginRateLimiter(LoginRateLimiter):
    def hit(self, *, email: str, ip_address: str | None) -> None:
        return None


@dataclass
class _Bucket:
    count: int
    reset_at: float


class InMemoryLoginRateLimiter(LoginRateLimiter):
    def __init__(self, *, max_attempts: int, window_seconds: int) -> None:
        self._max_attempts = max_attempts
        self._window_seconds = window_seconds
        self._buckets: dict[str, _Bucket] = {}
        self._lock = threading.Lock()

    def hit(self, *, email: str, ip_address: str | None) -> None:
        key = _rate_limit_key(email=email, ip_address=ip_address)
        now = time.monotonic()
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None or bucket.reset_at <= now:
                bucket = _Bucket(count=0, reset_at=now + self._window_seconds)
                self._buckets[key] = bucket
            bucket.count += 1
            if bucket.count > self._max_attempts:
                raise LoginRateLimitExceeded


class RedisLoginRateLimiter(LoginRateLimiter):
    def __init__(self, *, client: Redis, max_attempts: int, window_seconds: int) -> None:
        self._client = client
        self._max_attempts = max_attempts
        self._window_seconds = window_seconds

    def hit(self, *, email: str, ip_address: str | None) -> None:
        key = f"login-rate:{_rate_limit_key(email=email, ip_address=ip_address)}"
        try:
            count = int(self._client.incr(key))
            if count == 1:
                self._client.expire(key, self._window_seconds)
        except RedisError:
            return None
        if count > self._max_attempts:
            raise LoginRateLimitExceeded


def build_login_rate_limiter(settings: Settings) -> LoginRateLimiter:
    if settings.login_rate_limit_attempts <= 0:
        return NoopLoginRateLimiter()
    try:
        client = create_redis_client(settings)
        client.ping()
        return RedisLoginRateLimiter(
            client=client,
            max_attempts=settings.login_rate_limit_attempts,
            window_seconds=settings.login_rate_limit_window_seconds,
        )
    except RedisError:
        return InMemoryLoginRateLimiter(
            max_attempts=settings.login_rate_limit_attempts,
            window_seconds=settings.login_rate_limit_window_seconds,
        )


def _rate_limit_key(*, email: str, ip_address: str | None) -> str:
    normalized_email = email.strip().lower() or "unknown"
    normalized_ip = (ip_address or "unknown").strip() or "unknown"
    return f"{normalized_email}:{normalized_ip}"
