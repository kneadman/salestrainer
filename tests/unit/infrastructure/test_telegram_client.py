from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.infrastructure.telegram_client import (
    FakeTelegramClient,
    HttpxTelegramClient,
    build_telegram_client,
)
from app.infrastructure.config import Settings


def test_fake_client_logs_but_does_not_raise(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    client = FakeTelegramClient()
    client.send_message("test message")
    assert "fake_telegram_notification" in caplog.text
    assert "text_len=12" in caplog.text


def test_real_client_sends_post_with_correct_json() -> None:
    client = HttpxTelegramClient(bot_token="fake-token", chat_id="12345")
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None

    with patch("httpx.Client") as mock_client_cls:
        mock_client_instance = MagicMock()
        mock_client_instance.post.return_value = mock_response
        mock_client_cls.return_value.__enter__.return_value = mock_client_instance

        client.send_message("Hello, world!")

        mock_client_instance.post.assert_called_once_with(
            "https://api.telegram.org/botfake-token/sendMessage",
            json={"chat_id": "12345", "text": "Hello, world!"},
        )
        mock_response.raise_for_status.assert_called_once()


def test_real_client_logs_error_on_http_status_error(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.ERROR)
    client = HttpxTelegramClient(bot_token="fake-token", chat_id="12345")
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = "Bad Request"
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "error", request=MagicMock(), response=mock_response
    )

    with patch("httpx.Client") as mock_client_cls:
        mock_client_instance = MagicMock()
        mock_client_instance.post.return_value = mock_response
        mock_client_cls.return_value.__enter__.return_value = mock_client_instance

        client.send_message("Hello")

    assert "telegram_send_failed" in caplog.text
    assert "400" in caplog.text


def test_real_client_logs_error_on_network_error(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.ERROR)
    client = HttpxTelegramClient(bot_token="fake-token", chat_id="12345")

    with patch("httpx.Client") as mock_client_cls:
        mock_client_instance = MagicMock()
        mock_client_instance.post.side_effect = httpx.ConnectError("Connection failed")
        mock_client_cls.return_value.__enter__.return_value = mock_client_instance

        client.send_message("Hello")

    assert "telegram_send_failed" in caplog.text


def test_build_returns_fake_when_settings_empty() -> None:
    settings = Settings(telegram_bot_token="", telegram_lead_chat_id="")
    client = build_telegram_client(settings)
    assert isinstance(client, FakeTelegramClient)


def test_build_returns_fake_when_only_token_set() -> None:
    settings = Settings(telegram_bot_token="token", telegram_lead_chat_id="")
    client = build_telegram_client(settings)
    assert isinstance(client, FakeTelegramClient)


def test_build_returns_fake_when_only_chat_id_set() -> None:
    settings = Settings(telegram_bot_token="", telegram_lead_chat_id="chat")
    client = build_telegram_client(settings)
    assert isinstance(client, FakeTelegramClient)


def test_build_returns_real_when_both_set() -> None:
    settings = Settings(telegram_bot_token="real-token", telegram_lead_chat_id="999")
    client = build_telegram_client(settings)
    assert isinstance(client, HttpxTelegramClient)
