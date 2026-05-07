from __future__ import annotations

import logging
import tempfile
import wave
from pathlib import Path
from threading import BoundedSemaphore

from fastapi import UploadFile

from app.domain.errors import (
    SpeechConcurrencyLimitError,
    SpeechTranscriptionError,
    SpeechUploadTooLargeError,
    UnsupportedAudioTypeError,
)
from app.infrastructure.config import Settings
from app.infrastructure.stt_client import STTClient
from app.infrastructure.text_normalizer import normalize_transcribed_text

logger = logging.getLogger(__name__)

_ALLOWED_AUDIO_CONTENT_TYPES = {
    "audio/webm",
    "audio/ogg",
    "audio/wav",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp4",
    "video/mp4",
}


class SpeechService:
    """Validate one uploaded audio batch, transcribe it, and normalize the text."""

    def __init__(
        self,
        stt_client: STTClient,
        *,
        settings: Settings,
    ) -> None:
        self._stt_client = stt_client
        self._settings = settings
        self._semaphore = BoundedSemaphore(value=settings.stt_concurrency)

    async def transcribe_upload(
        self,
        *,
        upload: UploadFile,
        session_id: str | None = None,
        language: str | None = None,
    ) -> dict[str, object]:
        """Transcribe an uploaded audio file without mutating any training session state."""
        if not self._settings.stt_enabled:
            raise SpeechTranscriptionError("Speech transcription is disabled.")
        self._validate_content_type(upload.content_type)
        if not self._semaphore.acquire(blocking=False):
            raise SpeechConcurrencyLimitError("Speech transcription is busy. Please try again in a moment.")
        resolved_language = (language or self._settings.stt_language).strip() or self._settings.stt_language
        temp_dir = Path(self._settings.stt_temp_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                suffix=self._suffix_for_content_type(upload.content_type),
                prefix="speech-",
                delete=False,
                dir=temp_dir,
            ) as temp_file:
                temp_path = Path(temp_file.name)
                bytes_written = await self._write_bounded_upload(upload, temp_file)
            duration_ms = self._read_duration_ms(temp_path, upload.content_type)
            if duration_ms is not None and duration_ms > self._settings.stt_max_audio_seconds * 1000:
                raise SpeechUploadTooLargeError(
                    f"Audio is longer than the configured {self._settings.stt_max_audio_seconds} seconds limit."
                )
            stt_result = self._stt_client.transcribe(temp_path, language=resolved_language)
            raw_text = stt_result.text.strip()
            final_text, normalized = normalize_transcribed_text(
                raw_text,
                mode=self._settings.stt_normalization_mode,
            )
            logger.info(
                "speech_transcription_completed session_id_present=%s bytes=%s duration_ms=%s normalized=%s",
                bool(session_id),
                bytes_written,
                stt_result.duration_ms if stt_result.duration_ms is not None else duration_ms,
                normalized,
            )
            return {
                "text": final_text,
                "raw_text": raw_text,
                "normalized": normalized,
                "duration_ms": stt_result.duration_ms if stt_result.duration_ms is not None else duration_ms,
            }
        finally:
            await upload.close()
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
                temp_path.with_suffix(".txt").unlink(missing_ok=True)
            self._semaphore.release()

    def _validate_content_type(self, content_type: str | None) -> None:
        """Allow only the small set of explicitly supported audio container types."""
        if content_type not in _ALLOWED_AUDIO_CONTENT_TYPES:
            raise UnsupportedAudioTypeError("Unsupported audio content type.")

    async def _write_bounded_upload(self, upload: UploadFile, temp_file) -> int:
        """Copy the uploaded audio in chunks and stop once the configured size limit is exceeded."""
        total_bytes = 0
        chunk_size = 1024 * 256
        while True:
            chunk = await upload.read(chunk_size)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > self._settings.stt_max_upload_bytes:
                raise SpeechUploadTooLargeError(
                    f"Uploaded audio exceeds {self._settings.stt_max_upload_bytes} bytes."
                )
            temp_file.write(chunk)
        temp_file.flush()
        return total_bytes

    def _read_duration_ms(self, audio_path: Path, content_type: str | None) -> int | None:
        """Read WAV duration locally when available; return unknown for other containers."""
        if content_type not in {"audio/wav", "audio/x-wav"}:
            return None
        try:
            with wave.open(str(audio_path), "rb") as wav_file:
                frame_rate = wav_file.getframerate()
                if frame_rate <= 0:
                    return None
                frame_count = wav_file.getnframes()
                return int((frame_count / frame_rate) * 1000)
        except wave.Error:
            return None

    def _suffix_for_content_type(self, content_type: str | None) -> str:
        """Preserve a matching file extension so the STT backend sees a familiar container."""
        return {
            "audio/webm": ".webm",
            "audio/ogg": ".ogg",
            "audio/wav": ".wav",
            "audio/x-wav": ".wav",
            "audio/mpeg": ".mp3",
            "audio/mp4": ".m4a",
            "video/mp4": ".mp4",
        }.get(content_type, ".bin")
