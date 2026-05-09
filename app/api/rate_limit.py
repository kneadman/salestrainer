from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from redis import Redis
from redis.exceptions import RedisError

from app.infrastructure.config import Settings
from app.infrastructure.redis_client import create_redis_client


class LeadRateLimitExceeded(Exception):
    pass


class LeadRateLimiter:
    def hit(self, *, ip_address: str | None, email: str | None = None, phone: str | None = None) -> None:
        raise NotImplementedError


class NoopLeadRateLimiter(LeadRateLimiter):
    def hit(self, *, ip_address: str | None, email: str | None = None, phone: str | None = None) -> None:
        return None


@dataclass
class _Bucket:
    count: int
    reset_at: float


class InMemoryLeadRateLimiter(LeadRateLimiter):
    def __init__(self, *, max_attempts: int, window_seconds: int) -> None:
        self._max_attempts = max_attempts
        self._window_seconds = window_seconds
        self._buckets: dict[str, _Bucket] = {}
        self._lock = threading.Lock()

    def hit(self, *, ip_address: str | None, email: str | None = None, phone: str | None = None) -> None:
        keys = _lead_rate_limit_keys(ip_address=ip_address, email=email, phone=phone)
        now = time.monotonic()
        with self._lock:
            for key in keys:
                bucket = self._buckets.get(key)
                if bucket is None or bucket.reset_at <= now:
                    bucket = _Bucket(count=0, reset_at=now + self._window_seconds)
                    self._buckets[key] = bucket
                bucket.count += 1
                if bucket.count > self._max_attempts:
                    raise LeadRateLimitExceeded


class RedisLeadRateLimiter(LeadRateLimiter):
    def __init__(self, *, client: Redis, max_attempts: int, window_seconds: int) -> None:
        self._client = client
        self._max_attempts = max_attempts
        self._window_seconds = window_seconds

    def hit(self, *, ip_address: str | None, email: str | None = None, phone: str | None = None) -> None:
        keys = _lead_rate_limit_keys(ip_address=ip_address, email=email, phone=phone)
        for key in keys:
            redis_key = f"lead-rate:{key}"
            try:
                count = int(self._client.incr(redis_key))
                if count == 1:
                    self._client.expire(redis_key, self._window_seconds)
            except RedisError:
                continue
            if count > self._max_attempts:
                raise LeadRateLimitExceeded


def build_lead_rate_limiter(settings: Settings) -> LeadRateLimiter:
    if settings.lead_rate_limit_attempts <= 0:
        return NoopLeadRateLimiter()
    try:
        client = create_redis_client(settings)
        client.ping()
        return RedisLeadRateLimiter(
            client=client,
            max_attempts=settings.lead_rate_limit_attempts,
            window_seconds=settings.lead_rate_limit_window_seconds,
        )
    except RedisError:
        return InMemoryLeadRateLimiter(
            max_attempts=settings.lead_rate_limit_attempts,
            window_seconds=settings.lead_rate_limit_window_seconds,
        )


def _lead_rate_limit_keys(*, ip_address: str | None, email: str | None, phone: str | None) -> list[str]:
    keys: list[str] = []
    if ip_address:
        keys.append(f"ip:{ip_address.strip()}")
    if email:
        keys.append(f"email:{email.strip().lower()}")
    if phone:
        keys.append(f"phone:{phone.strip()}")
    return keys if keys else ["global"]
