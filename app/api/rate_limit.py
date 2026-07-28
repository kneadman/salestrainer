from __future__ import annotations

import time
from collections.abc import Callable

from redis import Redis
from redis.exceptions import RedisError

from app.infrastructure.config import Settings
from app.infrastructure.rate_limit import InMemoryFixedWindowRateLimiter, RedisFixedWindowRateLimiter
from app.infrastructure.redis_client import create_redis_client


class LeadRateLimitExceeded(Exception):
    pass


class LeadRateLimiter:
    def hit(self, *, ip_address: str | None, email: str | None = None, phone: str | None = None) -> None:
        raise NotImplementedError


class NoopLeadRateLimiter(LeadRateLimiter):
    def hit(self, *, ip_address: str | None, email: str | None = None, phone: str | None = None) -> None:
        return None


class InMemoryLeadRateLimiter(LeadRateLimiter):
    def __init__(
        self,
        *,
        max_attempts: int,
        window_seconds: int,
        time_provider: Callable[[], float] = time.monotonic,
    ) -> None:
        self._max_attempts = max_attempts
        self._engine = InMemoryFixedWindowRateLimiter(window_seconds=window_seconds, time_provider=time_provider)

    def hit(self, *, ip_address: str | None, email: str | None = None, phone: str | None = None) -> None:
        keys = _lead_rate_limit_keys(ip_address=ip_address, email=email, phone=phone)
        self._engine.hit(
            buckets=[(key, self._max_attempts) for key in keys],
            exceeded_error=LeadRateLimitExceeded,
        )


class RedisLeadRateLimiter(LeadRateLimiter):
    def __init__(self, *, client: Redis, max_attempts: int, window_seconds: int) -> None:
        self._max_attempts = max_attempts
        self._engine = RedisFixedWindowRateLimiter(
            client=client,
            window_seconds=window_seconds,
            key_prefix="lead-rate:",
        )

    def hit(self, *, ip_address: str | None, email: str | None = None, phone: str | None = None) -> None:
        keys = _lead_rate_limit_keys(ip_address=ip_address, email=email, phone=phone)
        self._engine.hit(
            buckets=[(key, self._max_attempts) for key in keys],
            exceeded_error=LeadRateLimitExceeded,
        )


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
