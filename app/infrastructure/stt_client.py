from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.domain.errors import SpeechToTextConfigurationError, SpeechTranscriptionError
from app.infrastructure.config import Settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class STTResult:
    """Carry the raw transcription result from the configured STT backend."""

    text: str
    duration_ms: int | None = None


class STTClient(Protocol):
    """Describe the small synchronous STT surface used by the application service."""

    def transcribe(self, audio_path: Path, *, language: str) -> STTResult:
        """Transcribe one uploaded audio file into text."""


class FakeSTTClient:
    """Return a deterministic transcript for local runs and tests."""

    def transcribe(self, audio_path: Path, *, language: str) -> STTResult:
        return STTResult(text=f"test transcription {audio_path.stem} {language}".strip())


class WhisperCppSTTClient:
    """Call whisper.cpp through a bounded subprocess and read its text output."""

    def __init__(
        self,
        *,
        binary_path: str,
        model_path: str,
        timeout_seconds: int,
    ) -> None:
        self._binary_path = binary_path
        self._model_path = model_path
        self._timeout_seconds = timeout_seconds

    def transcribe(self, audio_path: Path, *, language: str) -> STTResult:
        output_prefix = audio_path.with_suffix("")
        output_file = Path(f"{output_prefix}.txt")
        command = [
            self._binary_path,
            "-m",
            self._model_path,
            "-f",
            str(audio_path),
            "-l",
            language,
            "-otxt",
            "-of",
            str(output_prefix),
        ]
        logger.info(
            "stt_whisper_cpp_start binary=%s model=%s language=%s",
            Path(self._binary_path).name,
            Path(self._model_path).name,
            language,
        )
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=self._timeout_seconds,
            )
        except subprocess.TimeoutExpired as error:
            raise SpeechTranscriptionError("Speech transcription timed out.") from error
        except OSError as error:
            raise SpeechTranscriptionError("Speech transcription backend could not be started.") from error
        if completed.returncode != 0:
            logger.warning(
                "stt_whisper_cpp_failed returncode=%s stdout_tail=%s stderr_tail=%s",
                completed.returncode,
                completed.stdout[-2000:],
                completed.stderr[-2000:],
            )
            raise SpeechTranscriptionError("Speech transcription failed.")
        if not output_file.exists():
            logger.warning(
                "stt_whisper_cpp_missing_output output_file=%s stdout_tail=%s stderr_tail=%s",
                output_file,
                completed.stdout[-2000:],
                completed.stderr[-2000:],
            )
            raise SpeechTranscriptionError("Speech transcription output was not produced.")
        return STTResult(text=output_file.read_text(encoding="utf-8").strip())


def build_stt_client(settings: Settings) -> STTClient:
    """Build the configured STT client with local-safe fallback behavior."""
    if not settings.stt_enabled:
        return FakeSTTClient()
    backend = settings.stt_backend.lower().strip()
    if backend == "fake":
        return FakeSTTClient()
    if backend == "whisper_cpp":
        if settings.stt_whisper_cpp_binary and settings.stt_model_path:
            return WhisperCppSTTClient(
                binary_path=settings.stt_whisper_cpp_binary,
                model_path=settings.stt_model_path,
                timeout_seconds=settings.stt_timeout_seconds,
            )
        if settings.is_local_env:
            logger.warning("stt_backend_incomplete_config backend=%s fallback=fake", backend)
            return FakeSTTClient()
        raise SpeechToTextConfigurationError(
            "Incomplete whisper.cpp STT configuration."
        )
    if settings.is_local_env:
        logger.warning("stt_backend_unknown backend=%s fallback=fake", settings.stt_backend)
        return FakeSTTClient()
    raise SpeechToTextConfigurationError(f"Unknown stt_backend '{settings.stt_backend}'.")
