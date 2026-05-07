from __future__ import annotations

import json
import subprocess
import wave
from pathlib import Path
from typing import Protocol


class AudioDurationProbe(Protocol):
    """Describe the tiny audio-duration surface used by the speech service."""

    def get_duration_ms(self, audio_path: Path, *, content_type: str | None) -> int | None:
        """Return audio duration in milliseconds when it can be measured."""


class LocalAudioDurationProbe:
    """Measure WAV locally and fall back to ffprobe for other supported containers."""

    def __init__(self, *, ffprobe_binary: str, timeout_seconds: int) -> None:
        self._ffprobe_binary = ffprobe_binary.strip()
        self._timeout_seconds = min(timeout_seconds, 10)

    def get_duration_ms(self, audio_path: Path, *, content_type: str | None) -> int | None:
        if content_type in {"audio/wav", "audio/x-wav"}:
            return self._read_wav_duration_ms(audio_path)
        if not self._ffprobe_binary:
            return None
        return self._read_ffprobe_duration_ms(audio_path)

    def _read_wav_duration_ms(self, audio_path: Path) -> int | None:
        try:
            with wave.open(str(audio_path), "rb") as wav_file:
                frame_rate = wav_file.getframerate()
                if frame_rate <= 0:
                    return None
                frame_count = wav_file.getnframes()
                return int((frame_count / frame_rate) * 1000)
        except wave.Error:
            return None

    def _read_ffprobe_duration_ms(self, audio_path: Path) -> int | None:
        command = [
            self._ffprobe_binary,
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            str(audio_path),
        ]
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=self._timeout_seconds,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        if completed.returncode != 0:
            return None
        try:
            payload = json.loads(completed.stdout or "{}")
            duration_value = payload.get("format", {}).get("duration")
            if duration_value is None:
                return None
            duration_seconds = float(duration_value)
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
        if duration_seconds < 0:
            return None
        return int(duration_seconds * 1000)
