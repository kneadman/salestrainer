from __future__ import annotations

import pytest

from app.api.rate_limit import (
    InMemoryLeadRateLimiter,
    LeadRateLimitExceeded,
    NoopLeadRateLimiter,
)


def test_noop_limiter_never_raises() -> None:
    limiter = NoopLeadRateLimiter()
    for _ in range(1000):
        limiter.hit(ip_address="1.2.3.4", email="test@example.com", phone="+123")


def test_in_memory_limiter_blocks_after_max_attempts_by_ip() -> None:
    limiter = InMemoryLeadRateLimiter(max_attempts=2, window_seconds=60)
    limiter.hit(ip_address="1.2.3.4")
    limiter.hit(ip_address="1.2.3.4")
    with pytest.raises(LeadRateLimitExceeded):
        limiter.hit(ip_address="1.2.3.4")


def test_in_memory_limiter_resets_after_window_via_fake_clock() -> None:
    current_time = 0.0

    def fake_clock() -> float:
        return current_time

    limiter = InMemoryLeadRateLimiter(max_attempts=1, window_seconds=10, time_provider=fake_clock)
    limiter.hit(ip_address="1.2.3.4")
    with pytest.raises(LeadRateLimitExceeded):
        limiter.hit(ip_address="1.2.3.4")

    current_time = 11.0
    limiter.hit(ip_address="1.2.3.4")


def test_email_key_is_normalized_to_lowercase() -> None:
    limiter = InMemoryLeadRateLimiter(max_attempts=1, window_seconds=60)
    limiter.hit(ip_address=None, email="Test@Example.COM")
    with pytest.raises(LeadRateLimitExceeded):
        limiter.hit(ip_address=None, email="test@example.com")


def test_phone_key_is_separate() -> None:
    limiter = InMemoryLeadRateLimiter(max_attempts=1, window_seconds=60)
    limiter.hit(ip_address=None, phone="+111")
    # Different phone should be allowed because phone creates a separate key
    limiter.hit(ip_address=None, phone="+222")
    with pytest.raises(LeadRateLimitExceeded):
        limiter.hit(ip_address=None, phone="+111")


def test_global_key_when_no_identifiers() -> None:
    limiter = InMemoryLeadRateLimiter(max_attempts=1, window_seconds=60)
    limiter.hit(ip_address=None, email=None, phone=None)
    with pytest.raises(LeadRateLimitExceeded):
        limiter.hit(ip_address=None, email=None, phone=None)


def test_any_key_exceeded_raises() -> None:
    limiter = InMemoryLeadRateLimiter(max_attempts=1, window_seconds=60)
    limiter.hit(ip_address="1.2.3.4", email="a@example.com")
    # IP exceeded, even though email is different
    with pytest.raises(LeadRateLimitExceeded):
        limiter.hit(ip_address="1.2.3.4", email="b@example.com")
