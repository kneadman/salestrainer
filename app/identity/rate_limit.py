from __future__ import annotations

from redis import Redis
from redis.exceptions import RedisError

from app.infrastructure.config import Settings
from app.infrastructure.rate_limit import InMemoryFixedWindowRateLimiter, RedisFixedWindowRateLimiter
from app.infrastructure.redis_client import create_redis_client


class LoginRateLimitExceeded(Exception):
    pass


class LoginRateLimiter:
    def hit(self, *, email: str, ip_address: str | None) -> None:
        raise NotImplementedError


class NoopLoginRateLimiter(LoginRateLimiter):
    def hit(self, *, email: str, ip_address: str | None) -> None:
        return None


class InMemoryLoginRateLimiter(LoginRateLimiter):
    def __init__(self, *, max_attempts: int, window_seconds: int) -> None:
        self._max_attempts = max_attempts
        self._engine = InMemoryFixedWindowRateLimiter(window_seconds=window_seconds)

    def hit(self, *, email: str, ip_address: str | None) -> None:
        key = _rate_limit_key(email=email, ip_address=ip_address)
        self._engine.hit(buckets=[(key, self._max_attempts)], exceeded_error=LoginRateLimitExceeded)


class RedisLoginRateLimiter(LoginRateLimiter):
    def __init__(self, *, client: Redis, max_attempts: int, window_seconds: int) -> None:
        self._max_attempts = max_attempts
        self._engine = RedisFixedWindowRateLimiter(
            client=client,
            window_seconds=window_seconds,
            key_prefix="login-rate:",
        )

    def hit(self, *, email: str, ip_address: str | None) -> None:
        key = _rate_limit_key(email=email, ip_address=ip_address)
        self._engine.hit(buckets=[(key, self._max_attempts)], exceeded_error=LoginRateLimitExceeded)


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
