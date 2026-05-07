from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass
from typing import Protocol

from app.domain.errors import SpeechConcurrencyLimitError, SpeechQueueTimeoutError


class STTConcurrencyLimiter(Protocol):
    """Describe the async limiter used by the speech service."""

    async def acquire(self, *, user_key: str) -> "STTConcurrencyLease":
        """Acquire one global STT slot for the given user."""


@dataclass
class STTConcurrencyLease:
    """Represent one acquired STT slot that must be released."""

    _limiter: "LocalSTTConcurrencyLimiter"
    _user_key: str
    _released: bool = False

    async def release(self) -> None:
        """Release the previously acquired limiter slot once."""
        if self._released:
            return
        self._released = True
        await self._limiter.release(user_key=self._user_key)


class LocalSTTConcurrencyLimiter:
    """Keep STT work bounded with a global queue and a per-user lock."""

    def __init__(
        self,
        *,
        max_jobs: int,
        queue_wait_timeout_seconds: int,
        per_user_limit: int,
    ) -> None:
        self._max_jobs = max_jobs
        self._queue_wait_timeout_seconds = queue_wait_timeout_seconds
        self._per_user_limit = per_user_limit
        self._global_active_jobs = 0
        self._user_active_jobs: dict[str, int] = defaultdict(int)
        self._condition = asyncio.Condition()

    async def acquire(self, *, user_key: str) -> STTConcurrencyLease:
        """Reserve one job slot or fail with a controlled queue/per-user error."""
        async with self._condition:
            if self._user_active_jobs[user_key] >= self._per_user_limit:
                raise SpeechConcurrencyLimitError("Another speech transcription is already running for this user.")
            try:
                await asyncio.wait_for(
                    self._condition.wait_for(lambda: self._global_active_jobs < self._max_jobs),
                    timeout=self._queue_wait_timeout_seconds,
                )
            except TimeoutError as error:
                raise SpeechQueueTimeoutError("Speech transcription queue is busy. Please try again later.") from error
            self._global_active_jobs += 1
            self._user_active_jobs[user_key] += 1
            return STTConcurrencyLease(self, user_key)

    async def release(self, *, user_key: str) -> None:
        """Return one user/global slot and wake one waiting request."""
        async with self._condition:
            self._global_active_jobs = max(0, self._global_active_jobs - 1)
            if self._user_active_jobs.get(user_key, 0) <= 1:
                self._user_active_jobs.pop(user_key, None)
            else:
                self._user_active_jobs[user_key] -= 1
            self._condition.notify_all()
