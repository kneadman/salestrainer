from __future__ import annotations

from io import BytesIO
from pathlib import Path
from threading import Event, Lock, Thread
from types import SimpleNamespace
import tempfile
import time

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.api.main import create_app
from app.domain.errors import SpeechTranscriptionError
from app.identity.dependencies import get_access_service, require_current_user
from app.infrastructure.audio_converter import AudioConverter
from app.infrastructure.audio_duration_probe import AudioDurationProbe
from app.infrastructure.config import Settings
from app.infrastructure.llm_client import FakeLLMClient
from app.infrastructure.session_repository import InMemorySessionRepository
from app.infrastructure.stt_client import FakeSTTClient, STTResult


class StubAccessService:
    def require_session_access(self, session_id: str, user_id: str) -> None:
        del session_id, user_id


class RecordingSTTClient(FakeSTTClient):
    def __init__(self) -> None:
        self.audio_paths: list[Path] = []

    def transcribe(self, audio_path: Path, *, language: str) -> STTResult:
        self.audio_paths.append(audio_path)
        return STTResult(text=f"voice ok {audio_path.suffix} {language}")


class BlockingSTTClient(FakeSTTClient):
    def __init__(self) -> None:
        self.release = Event()
        self.call_count = 0
        self._lock = Lock()

    def transcribe(self, audio_path: Path, *, language: str) -> STTResult:
        del audio_path, language
        with self._lock:
            self.call_count += 1
        self.release.wait(timeout=5)
        if not self.release.is_set():
            raise SpeechTranscriptionError("blocking test client timed out")
        return STTResult(text="blocked request finished")


class FixedDurationProbe(AudioDurationProbe):
    def __init__(self, duration_ms: int | None) -> None:
        self._duration_ms = duration_ms

    def get_duration_ms(self, audio_path: Path, *, content_type: str | None) -> int | None:
        del audio_path, content_type
        return self._duration_ms


class SourceThenWavDurationProbe(AudioDurationProbe):
    def __init__(self, *, source_duration_ms: int | None, wav_duration_ms: int | None) -> None:
        self._source_duration_ms = source_duration_ms
        self._wav_duration_ms = wav_duration_ms

    def get_duration_ms(self, audio_path: Path, *, content_type: str | None) -> int | None:
        del audio_path
        if content_type in {"audio/wav", "audio/x-wav"}:
            return self._wav_duration_ms
        return self._source_duration_ms


class FakeAudioConverter(AudioConverter):
    def to_wav_16k_mono(self, source_path: Path, *, source_content_type: str) -> Path:
        output_path = source_path if source_content_type in {"audio/wav", "audio/x-wav"} else source_path.with_suffix(".wav")
        if output_path != source_path:
            output_path.write_bytes(source_path.read_bytes())
        return output_path


def _speech_settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "auth_cookie_secure": False,
        "login_rate_limit_attempts": 0,
        "stt_enabled": True,
        "stt_backend": "fake",
        "stt_temp_dir": tempfile.mkdtemp(prefix="salestrainer-stt-tests-"),
        "stt_queue_wait_timeout_seconds": 1,
        "stt_reject_unknown_duration": True,
    }
    defaults.update(overrides)
    return Settings(**defaults)


def _build_speech_test_app(
    *,
    settings: Settings | None = None,
    stt_client: FakeSTTClient | None = None,
    duration_probe: AudioDurationProbe | None = None,
    audio_converter: AudioConverter | None = None,
) -> FastAPI:
    app = create_app(
        settings=settings or _speech_settings(),
        repository=InMemorySessionRepository(),
        llm_client=FakeLLMClient(),
        stt_client=stt_client or RecordingSTTClient(),
        audio_duration_probe=duration_probe or FixedDurationProbe(4_000),
        audio_converter=audio_converter or FakeAudioConverter(),
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


def _wait_for_call_count(stt_client: BlockingSTTClient, expected: int, *, timeout_seconds: float = 2.0) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if stt_client.call_count >= expected:
            return True
        time.sleep(0.02)
    return False


def test_speech_route_exists_when_stt_disabled_and_returns_controlled_error() -> None:
    app = _build_speech_test_app(settings=_speech_settings(stt_enabled=False))
    client = TestClient(app)
    _authorize_client(client, token="user-1")

    response = client.post(
        "/api/speech/transcribe",
        files={"audio": ("voice.webm", BytesIO(b"fake-audio"), "audio/webm;codecs=opus")},
    )

    assert response.status_code == 409
    assert response.json()["error"]["message"] == "Speech transcription is disabled."


def test_speech_route_accepts_audio_webm_with_codecs_parameter() -> None:
    recording_client = RecordingSTTClient()
    app = _build_speech_test_app(stt_client=recording_client)
    client = TestClient(app)
    _authorize_client(client, token="user-1")

    response = client.post(
        "/api/speech/transcribe",
        files={"audio": ("voice.webm", BytesIO(b"fake-audio"), "audio/webm;codecs=opus")},
    )

    assert response.status_code == 200
    assert response.json()["text"] == "Voice ok .wav ru"
    assert recording_client.audio_paths[-1].suffix == ".wav"


def test_non_wav_unknown_duration_is_rejected_when_fail_closed() -> None:
    app = _build_speech_test_app(duration_probe=FixedDurationProbe(None))
    client = TestClient(app)
    _authorize_client(client, token="user-1")

    response = client.post(
        "/api/speech/transcribe",
        files={"audio": ("voice.webm", BytesIO(b"fake-audio"), "audio/webm")},
    )

    assert response.status_code == 422
    assert response.json()["error"]["message"] == "Audio duration could not be verified."


def test_non_wav_valid_duration_passes() -> None:
    app = _build_speech_test_app(duration_probe=FixedDurationProbe(5_000))
    client = TestClient(app)
    _authorize_client(client, token="user-1")

    response = client.post(
        "/api/speech/transcribe",
        files={"audio": ("voice.webm", BytesIO(b"fake-audio"), "audio/webm")},
    )

    assert response.status_code == 200


def test_non_wav_unknown_source_duration_but_known_wav_duration_passes() -> None:
    app = _build_speech_test_app(
        duration_probe=SourceThenWavDurationProbe(source_duration_ms=None, wav_duration_ms=5_000),
    )
    client = TestClient(app)
    _authorize_client(client, token="user-1")

    response = client.post(
        "/api/speech/transcribe",
        files={"audio": ("voice.webm", BytesIO(b"fake-audio"), "audio/webm")},
    )

    assert response.status_code == 200


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
    assert _wait_for_call_count(blocking_client, 1)

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
    assert _wait_for_call_count(blocking_client, 1)

    second_response = client_two.post(
        "/api/speech/transcribe",
        files={"audio": ("voice.webm", BytesIO(b"fake-audio"), "audio/webm")},
    )

    blocking_client.release.set()
    thread.join(timeout=3)

    assert second_response.status_code == 429
    assert second_response.json()["error"]["code"] == "too_many_requests"
    assert first_response["status_code"] == 200


def test_same_user_queued_request_rejected_with_conflict_when_two_global_slots_are_busy() -> None:
    blocking_client = BlockingSTTClient()
    app = _build_speech_test_app(
        settings=_speech_settings(stt_concurrency=2, stt_max_concurrent_jobs=2, stt_per_user_concurrency=1),
        stt_client=blocking_client,
    )
    client_one = TestClient(app)
    client_two = TestClient(app)
    queued_client = TestClient(app)
    duplicate_client = TestClient(app)
    _authorize_client(client_one, token="user-a")
    _authorize_client(client_two, token="user-b")
    _authorize_client(queued_client, token="user-c")
    _authorize_client(duplicate_client, token="user-c")

    active_statuses: list[int] = []
    queued_status: dict[str, int] = {}

    def run_active_request(client: TestClient) -> None:
        response = client.post(
            "/api/speech/transcribe",
            files={"audio": ("voice.webm", BytesIO(b"fake-audio"), "audio/webm")},
        )
        active_statuses.append(response.status_code)

    def run_queued_request() -> None:
        response = queued_client.post(
            "/api/speech/transcribe",
            files={"audio": ("voice.webm", BytesIO(b"fake-audio"), "audio/webm")},
        )
        queued_status["status_code"] = response.status_code

    active_thread_one = Thread(target=run_active_request, args=(client_one,))
    active_thread_two = Thread(target=run_active_request, args=(client_two,))
    active_thread_one.start()
    active_thread_two.start()
    assert _wait_for_call_count(blocking_client, 2)

    queued_thread = Thread(target=run_queued_request)
    queued_thread.start()
    time.sleep(0.15)

    duplicate_response = duplicate_client.post(
        "/api/speech/transcribe",
        files={"audio": ("voice.webm", BytesIO(b"fake-audio"), "audio/webm")},
    )

    blocking_client.release.set()
    queued_thread.join(timeout=3)
    active_thread_one.join(timeout=3)
    active_thread_two.join(timeout=3)

    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["error"]["code"] == "conflict"
    assert queued_status["status_code"] == 200
    assert sorted(active_statuses) == [200, 200]


def test_webm_audio_is_converted_to_wav_before_stt() -> None:
    recording_client = RecordingSTTClient()
    app = _build_speech_test_app(
        stt_client=recording_client,
        duration_probe=FixedDurationProbe(5_000),
        audio_converter=FakeAudioConverter(),
    )
    client = TestClient(app)
    _authorize_client(client, token="user-1")

    response = client.post(
        "/api/speech/transcribe",
        files={"audio": ("voice.webm", BytesIO(b"fake-audio"), "audio/webm")},
    )

    assert response.status_code == 200
    assert recording_client.audio_paths[-1].suffix == ".wav"
