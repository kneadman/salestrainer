from __future__ import annotations

from threading import RLock
from typing import Protocol

from redis import Redis
from redis.exceptions import WatchError

from app.domain.errors import SessionNotFoundError, StateVersionConflictError
from app.domain.models import TrainingSessionState


class SessionRepository(Protocol):
    def create(self, session: TrainingSessionState) -> None:
        ...

    def get(self, session_id: str) -> TrainingSessionState | None:
        ...

    def save(self, session: TrainingSessionState, *, expected_version: int | None = None) -> None:
        ...

    def touch(self, session_id: str) -> None:
        ...

    def delete(self, session_id: str) -> None:
        ...


class InMemorySessionRepository:
    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        self._lock = RLock()

    def create(self, session: TrainingSessionState) -> None:
        with self._lock:
            self._store[str(session.session_id)] = session.model_dump_json()

    def get(self, session_id: str) -> TrainingSessionState | None:
        with self._lock:
            data = self._store.get(str(session_id))
            if data is None:
                return None
            return TrainingSessionState.model_validate_json(data)

    def save(self, session: TrainingSessionState, *, expected_version: int | None = None) -> None:
        session_id = str(session.session_id)
        with self._lock:
            current_payload = self._store.get(session_id)
            if current_payload is None:
                raise SessionNotFoundError(f"Session '{session_id}' not found.")
            current_session = TrainingSessionState.model_validate_json(current_payload)
            if expected_version is not None and current_session.state_version != expected_version:
                raise StateVersionConflictError(
                    f"Session '{session_id}' was updated concurrently."
                )
            self._store[session_id] = session.model_dump_json()

    def touch(self, session_id: str) -> None:
        with self._lock:
            if str(session_id) not in self._store:
                raise SessionNotFoundError(f"Session '{session_id}' not found.")

    def delete(self, session_id: str) -> None:
        with self._lock:
            self._store.pop(str(session_id), None)


class RedisSessionRepository:
    def __init__(self, client: Redis, ttl_seconds: int = 1800) -> None:
        self._client = client
        self._ttl_seconds = ttl_seconds

    def _session_key(self, session_id: str) -> str:
        return f"sales_trainer:session:{session_id}"

    def create(self, session: TrainingSessionState) -> None:
        created = self._client.set(
            self._session_key(str(session.session_id)),
            session.model_dump_json(),
            ex=self._ttl_seconds,
            nx=True,
        )
        if not created:
            raise StateVersionConflictError(
                f"Session '{session.session_id}' already exists."
            )

    def get(self, session_id: str) -> TrainingSessionState | None:
        payload = self._client.get(self._session_key(str(session_id)))
        if payload is None:
            return None
        return TrainingSessionState.model_validate_json(payload)

    def touch(self, session_id: str) -> None:
        key = self._session_key(str(session_id))
        if not self._client.expire(key, self._ttl_seconds):
            raise SessionNotFoundError(f"Session '{session_id}' not found.")

    def save(self, session: TrainingSessionState, *, expected_version: int | None = None) -> None:
        session_id = str(session.session_id)
        key = self._session_key(session_id)
        payload = session.model_dump_json()

        with self._client.pipeline() as pipeline:
            try:
                pipeline.watch(key)
                current_payload = pipeline.get(key)
                if current_payload is None:
                    raise SessionNotFoundError(f"Session '{session_id}' not found.")
                if expected_version is not None:
                    current_session = TrainingSessionState.model_validate_json(current_payload)
                    if current_session.state_version != expected_version:
                        raise StateVersionConflictError(
                            f"Session '{session_id}' was updated concurrently."
                        )
                pipeline.multi()
                pipeline.set(key, payload, ex=self._ttl_seconds)
                pipeline.execute()
            except WatchError as error:
                raise StateVersionConflictError(
                    f"Session '{session_id}' was updated concurrently."
                ) from error

    def delete(self, session_id: str) -> None:
        self._client.delete(self._session_key(str(session_id)))
