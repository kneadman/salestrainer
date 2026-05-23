from __future__ import annotations

import logging
from typing import Protocol

import httpx

from app.infrastructure.config import Settings

logger = logging.getLogger(__name__)


class TelegramClient(Protocol):
    """Protocol for sending Telegram notifications."""

    def send_message(self, text: str) -> None:
        """Send a plain-text message to the configured chat.

        Implementations must not raise on failure; errors are logged.
        """
        ...


class HttpxTelegramClient:
    """Real Telegram client using httpx with a short timeout."""

    def __init__(self, *, bot_token: str, chat_id: str, timeout_seconds: float = 7.0) -> None:
        self._bot_token = bot_token
        self._chat_id = chat_id
        self._timeout_seconds = timeout_seconds
        self._api_url = f"https://api.telegram.org/bot{self._bot_token}/sendMessage"

    def send_message(self, text: str) -> None:
        try:
            with httpx.Client(timeout=self._timeout_seconds) as client:
                response = client.post(
                    self._api_url,
                    json={"chat_id": self._chat_id, "text": text},
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "telegram_send_failed status=%s body=%s",
                exc.response.status_code,
                exc.response.text,
            )
        except Exception:
            logger.error("telegram_send_failed", exc_info=True)


class FakeTelegramClient:
    """No-op client for local/test environments."""

    def send_message(self, text: str) -> None:
        logger.info("fake_telegram_notification text_len=%d", len(text))


def build_telegram_client(settings: Settings) -> TelegramClient:
    """Return a real client if credentials are configured, otherwise a fake."""
    if not settings.telegram_bot_token or not settings.telegram_lead_chat_id:
        logger.info("Telegram credentials not configured; using fake client.")
        return FakeTelegramClient()
    return HttpxTelegramClient(
        bot_token=settings.telegram_bot_token,
        chat_id=settings.telegram_lead_chat_id,
    )
