from __future__ import annotations

from io import BytesIO
from pathlib import Path
from threading import Event, Lock, Thread
from types import SimpleNamespace
import tempfile

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

import app.api.main as api_main_module
from app.api.main import create_app
from app.domain.errors import SpeechTranscriptionError
from app.identity.dependencies import get_access_service, require_current_user
from app.infrastructure.config import Settings
from app.infrastructure.llm_client import FakeLLMClient
from app.infrastructure.session_repository import InMemorySessionRepository
from app.infrastructure.stt_client import FakeSTTClient, STTResult


class StubAccessService:
    def require_session_access(self, session_id: str, user_id: str) -> None:
        del session_id, user_id


class RecordingSTTClient(FakeSTTClient):
    def transcribe(self, audio_path: Path, *, language: str) -> STTResult:
        return STTResult(text=f"voice ok {audio_path.suffix} {language}")


class BlockingSTTClient(FakeSTTClient):
    def __init__(self) -> None:
        self.started = Event()
        self.release = Event()
        self.call_count = 0
        self._lock = Lock()

    def transcribe(self, audio_path: Path, *, language: str) -> STTResult:
        del audio_path, language
        with self._lock:
            self.call_count += 1
        self.started.set()
        self.release.wait(timeout=5)
        if not self.release.is_set():
            raise SpeechTranscriptionError("blocking test client timed out")
        return STTResult(text="blocked request finished")


class FixedDurationProbe:
    def __init__(self, duration_ms: int | None) -> None:
        self._duration_ms = duration_ms

    def get_duration_ms(self, audio_path: Path, *, content_type: str | None) -> int | None:
        del audio_path, content_type
        return self._duration_ms


def _speech_settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "auth_cookie_secure": False,
        "login_rate_limit_attempts": 0,
        "stt_enabled": True,
        "stt_backend": "fake",
        "stt_temp_dir": tempfile.mkdtemp(prefix="salestrainer-stt-tests-"),
        "stt_queue_wait_timeout_seconds": 1,
    }
    defaults.update(overrides)
    return Settings(
        **defaults,
    )


def _build_speech_test_app(
    *,
    settings: Settings | None = None,
    stt_client: FakeSTTClient | None = None,
) -> FastAPI:
    app = create_app(
        settings=settings or _speech_settings(),
        repository=InMemorySessionRepository(),
        llm_client=FakeLLMClient(),
        stt_client=stt_client or RecordingSTTClient(),
    )

    def override_current_user(request: Request):
        token = request.cookies.get("salestrainer_session", "anonymous")
        return SimpleNamespace(user=SimpleNamespace(id=token))

    app.dependency_overrides[require_current_user] = override_current_user
    app.dependency_overrides[get_access_service] = lambda: StubAccessService()
    return app


def _authorize_client(client: TestClient, *, token: str) -> None:
    client.cookies.set("salestrainer_session", token)
    client.cookies.set("salestrainer_csrf", "csrf-token")
    client.headers.update({"X-CSRF-Token": "csrf-token"})


def test_speech_route_accepts_audio_webm_with_codecs_parameter() -> None:
    app = _build_speech_test_app()
    client = TestClient(app)
    _authorize_client(client, token="user-1")

    response = client.post(
        "/api/speech/transcribe",
        files={"audio": ("voice.webm", BytesIO(b"fake-audio"), "audio/webm;codecs=opus")},
    )

    assert response.status_code == 200
    assert response.json()["text"] == "Voice ok .webm ru"


def test_create_app_does_not_require_multipart_when_stt_disabled(monkeypatch) -> None:
    def fail_if_called():
        raise RuntimeError("python-multipart missing")

    monkeypatch.setattr(api_main_module, "build_speech_router", fail_if_called)

    app = create_app(
        settings=Settings(auth_cookie_secure=False, login_rate_limit_attempts=0, stt_enabled=False),
        repository=InMemorySessionRepository(),
        llm_client=FakeLLMClient(),
    )

    assert isinstance(app, FastAPI)


def test_same_user_parallel_transcription_is_rejected_with_conflict() -> None:
    blocking_client = BlockingSTTClient()
    app = _build_speech_test_app(stt_client=blocking_client)
    client_one = TestClient(app)
    client_two = TestClient(app)
    _authorize_client(client_one, token="same-user")
    _authorize_client(client_two, token="same-user")
    first_response: dict[str, int] = {}

    def run_first_request() -> None:
        response = client_one.post(
            "/api/speech/transcribe",
            files={"audio": ("voice.webm", BytesIO(b"fake-audio"), "audio/webm")},
        )
        first_response["status_code"] = response.status_code

    thread = Thread(target=run_first_request)
    thread.start()
    assert blocking_client.started.wait(timeout=2)

    second_response = client_two.post(
        "/api/speech/transcribe",
        files={"audio": ("voice.webm", BytesIO(b"fake-audio"), "audio/webm")},
    )

    blocking_client.release.set()
    thread.join(timeout=3)

    assert second_response.status_code == 409
    assert second_response.json()["error"]["code"] == "conflict"
    assert first_response["status_code"] == 200


def test_global_busy_transcription_returns_too_many_requests_after_wait_timeout() -> None:
    blocking_client = BlockingSTTClient()
    app = _build_speech_test_app(
        settings=_speech_settings(stt_queue_wait_timeout_seconds=1),
        stt_client=blocking_client,
    )
    client_one = TestClient(app)
    client_two = TestClient(app)
    _authorize_client(client_one, token="user-1")
    _authorize_client(client_two, token="user-2")
    first_response: dict[str, int] = {}

    def run_first_request() -> None:
        response = client_one.post(
            "/api/speech/transcribe",
            files={"audio": ("voice.webm", BytesIO(b"fake-audio"), "audio/webm")},
        )
        first_response["status_code"] = response.status_code

    thread = Thread(target=run_first_request)
    thread.start()
    assert blocking_client.started.wait(timeout=2)

    second_response = client_two.post(
        "/api/speech/transcribe",
        files={"audio": ("voice.webm", BytesIO(b"fake-audio"), "audio/webm")},
    )

    blocking_client.release.set()
    thread.join(timeout=3)

    assert second_response.status_code == 429
    assert second_response.json()["error"]["code"] == "too_many_requests"
    assert first_response["status_code"] == 200


def test_non_wav_long_audio_is_rejected_before_transcription() -> None:
    app = _build_speech_test_app()
    app.state.speech_service._duration_probe = FixedDurationProbe(duration_ms=91_000)
    client = TestClient(app)
    _authorize_client(client, token="user-1")

    response = client.post(
        "/api/speech/transcribe",
        files={"audio": ("voice.webm", BytesIO(b"fake-audio"), "audio/webm;codecs=opus")},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"
