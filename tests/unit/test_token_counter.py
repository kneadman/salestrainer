from __future__ import annotations

import pytest

from app.domain.token_counter import TokenCounterService


@pytest.fixture
def service() -> TokenCounterService:
    return TokenCounterService()


def test_count_string_known_text(service: TokenCounterService) -> None:
    """A well-known string produces the expected cl100k_base token count."""
    assert service.count_string("hello world") == 2


def test_count_string_empty(service: TokenCounterService) -> None:
    assert service.count_string("") == 0


def test_count_json_dict(service: TokenCounterService) -> None:
    """count_json serialises and counts tokens consistently."""
    payload = {"role": "user", "content": "hello world"}
    tokens = service.count_json(payload)
    assert tokens > 0
    # JSON-serialised form should have more tokens than the raw content alone.
    assert tokens >= service.count_string("hello world")
