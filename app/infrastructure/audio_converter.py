from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Protocol

from app.domain.errors import SpeechTranscriptionError


class AudioConverter(Protocol):
    """Describe the audio normalization step that prepares browser audio for STT."""

    def to_wav_16k_mono(self, source_path: Path, *, source_content_type: str) -> Path:
        """Convert the source audio into a WAV 16k mono file for STT."""


class LocalFFmpegAudioConverter:
    """Normalize browser/container audio into a conservative WAV format via ffmpeg."""

    def __init__(self, *, ffmpeg_binary: str, timeout_seconds: int) -> None:
        self._ffmpeg_binary = ffmpeg_binary.strip()
        self._timeout_seconds = min(timeout_seconds, 30)

    def to_wav_16k_mono(self, source_path: Path, *, source_content_type: str) -> Path:
        if source_content_type in {"audio/wav", "audio/x-wav"}:
            return source_path
        output_path = source_path.with_suffix(".wav")
        command = [
            self._ffmpeg_binary,
            "-y",
            "-i",
            str(source_path),
            "-ac",
            "1",
            "-ar",
            "16000",
            "-vn",
            str(output_path),
        ]
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=self._timeout_seconds,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise SpeechTranscriptionError("Audio conversion failed.") from error
        if completed.returncode != 0 or not output_path.exists():
            raise SpeechTranscriptionError("Audio conversion failed.")
        return output_path
