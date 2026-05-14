from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from fastapi import UploadFile
from starlette.concurrency import run_in_threadpool

from app.domain.errors import (
    SpeechDisabledError,
    SpeechDurationUnknownError,
    SpeechTranscriptionError,
    SpeechUploadTooLargeError,
    UnsupportedAudioTypeError,
)
from app.infrastructure.audio_converter import AudioConverter, LocalFFmpegAudioConverter
from app.infrastructure.audio_duration_probe import AudioDurationProbe, LocalAudioDurationProbe
from app.infrastructure.config import Settings
from app.infrastructure.stt_client import STTClient
from app.infrastructure.stt_concurrency import STTConcurrencyLimiter
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
        concurrency_limiter: STTConcurrencyLimiter,
        duration_probe: AudioDurationProbe | None = None,
        audio_converter: AudioConverter | None = None,
    ) -> None:
        self._stt_client = stt_client
        self._settings = settings
        self._concurrency_limiter = concurrency_limiter
        self._duration_probe = duration_probe or LocalAudioDurationProbe(
            ffprobe_binary=settings.stt_ffprobe_binary,
            timeout_seconds=settings.stt_timeout_seconds,
        )
        self._audio_converter = audio_converter or LocalFFmpegAudioConverter(
            ffmpeg_binary=settings.stt_ffmpeg_binary,
            timeout_seconds=settings.stt_timeout_seconds,
        )

    async def transcribe_upload(
        self,
        *,
        upload: UploadFile,
        user_id: str,
        session_id: str | None = None,
        language: str | None = None,
    ) -> dict[str, object]:
        """Transcribe an uploaded audio file without mutating any training session state."""
        if not self._settings.stt_enabled:
            raise SpeechDisabledError("Speech transcription is disabled.")
        normalized_content_type = self._normalize_content_type(upload.content_type)
        self._validate_content_type(normalized_content_type)
        temp_dir = Path(self._settings.stt_temp_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)
        resolved_language = (language or self._settings.stt_language).strip() or self._settings.stt_language
        lease = await self._concurrency_limiter.acquire(user_key=user_id)
        temp_path: Path | None = None
        converted_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                suffix=self._suffix_for_content_type(normalized_content_type),
                prefix="speech-",
                delete=False,
                dir=temp_dir,
            ) as temp_file:
                temp_path = Path(temp_file.name)
                bytes_written = await self._write_bounded_upload(upload, temp_file)
            duration_ms = await run_in_threadpool(
                self._duration_probe.get_duration_ms,
                temp_path,
                content_type=normalized_content_type,
            )
            converted_path = await run_in_threadpool(
                self._audio_converter.to_wav_16k_mono,
                temp_path,
                source_content_type=normalized_content_type,
            )
            if duration_ms is None and normalized_content_type not in {"audio/wav", "audio/x-wav"}:
                duration_ms = await run_in_threadpool(
                    self._duration_probe.get_duration_ms,
                    converted_path,
                    content_type="audio/wav",
                )
            self._validate_duration(duration_ms, normalized_content_type=normalized_content_type)
            stt_result = await run_in_threadpool(
                self._stt_client.transcribe,
                converted_path,
                language=resolved_language,
            )
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
                "normalized": normalized,
                "duration_ms": stt_result.duration_ms if stt_result.duration_ms is not None else duration_ms,
            }
        finally:
            await upload.close()
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
            if converted_path is not None and converted_path != temp_path:
                converted_path.unlink(missing_ok=True)
            if converted_path is not None:
                converted_path.with_suffix(".txt").unlink(missing_ok=True)
            if temp_path is not None and converted_path != temp_path:
                temp_path.with_suffix(".txt").unlink(missing_ok=True)
            await lease.release()

    def _normalize_content_type(self, content_type: str | None) -> str:
        """Strip content-type parameters and lowercase the media type."""
        if not content_type:
            return ""
        return content_type.split(";", 1)[0].strip().lower()

    def _validate_content_type(self, content_type: str) -> None:
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

    def _validate_duration(self, duration_ms: int | None, *, normalized_content_type: str) -> None:
        """Reject audio that is longer than the configured upper bound when duration is known."""
        if (
            duration_ms is None
            and normalized_content_type not in {"audio/wav", "audio/x-wav"}
            and self._settings.stt_reject_unknown_duration
        ):
            raise SpeechDurationUnknownError("Audio duration could not be verified.")
        if duration_ms is None:
            return
        if duration_ms > self._settings.stt_max_audio_seconds * 1000:
            raise SpeechUploadTooLargeError(
                f"Audio is longer than the configured {self._settings.stt_max_audio_seconds} seconds limit."
            )

    def _suffix_for_content_type(self, content_type: str) -> str:
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
