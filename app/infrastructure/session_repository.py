from __future__ import annotations

from typing import Protocol

from redis import Redis

from app.domain.models import TrainingSessionState


class SessionRepository(Protocol):
    def create(self, session: TrainingSessionState) -> None:
        ...

    def get(self, session_id: str) -> TrainingSessionState | None:
        ...

    def save(self, session: TrainingSessionState) -> None:
        ...

    def delete(self, session_id: str) -> None:
        ...


class InMemorySessionRepository:
    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def create(self, session: TrainingSessionState) -> None:
        self.save(session)

    def get(self, session_id: str) -> TrainingSessionState | None:
        data = self._store.get(str(session_id))
        if data is None:
            return None
        return TrainingSessionState.model_validate_json(data)

    def save(self, session: TrainingSessionState) -> None:
        self._store[str(session.session_id)] = session.model_dump_json()

    def delete(self, session_id: str) -> None:
        self._store.pop(str(session_id), None)


class RedisSessionRepository:
    def __init__(self, client: Redis, ttl_seconds: int = 86400) -> None:
        self._client = client
        self._ttl_seconds = ttl_seconds

    def _session_key(self, session_id: str) -> str:
        return f"sales_trainer:session:{session_id}"

    def create(self, session: TrainingSessionState) -> None:
        self.save(session)

    def get(self, session_id: str) -> TrainingSessionState | None:
        payload = self._client.get(self._session_key(str(session_id)))
        if payload is None:
            return None
        return TrainingSessionState.model_validate_json(payload)

    def save(self, session: TrainingSessionState) -> None:
        self._client.set(
            self._session_key(str(session.session_id)),
            session.model_dump_json(),
            ex=self._ttl_seconds,
        )

    def delete(self, session_id: str) -> None:
        self._client.delete(self._session_key(str(session_id)))

