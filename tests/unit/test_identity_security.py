from __future__ import annotations

import pytest

from app.identity.security import (
    PasswordValidationError,
    hash_password,
    validate_permanent_password,
    verify_password,
)


def test_hash_password_and_verify_success() -> None:
    password = "temporary-password"

    password_hash = hash_password(password)

    assert password_hash != password
    assert verify_password(password, password_hash) is True


def test_verify_password_returns_false_for_wrong_password() -> None:
    password_hash = hash_password("temporary-password")

    assert verify_password("wrong-password", password_hash) is False


def test_validate_permanent_password_accepts_valid_password() -> None:
    validate_permanent_password("Password123")


def test_validate_permanent_password_rejects_too_short() -> None:
    with pytest.raises(PasswordValidationError, match="at least 8 characters"):
        validate_permanent_password("short1")


def test_validate_permanent_password_rejects_special_characters() -> None:
    with pytest.raises(PasswordValidationError, match="only Latin letters and digits"):
        validate_permanent_password("Password!")


def test_validate_permanent_password_rejects_spaces() -> None:
    with pytest.raises(PasswordValidationError, match="only Latin letters and digits"):
        validate_permanent_password("Pass word1")


def test_validate_permanent_password_rejects_cyrillic() -> None:
    with pytest.raises(PasswordValidationError, match="only Latin letters and digits"):
        validate_permanent_password("Пароль123")


def test_validate_permanent_password_accepts_exactly_eight_chars() -> None:
    validate_permanent_password("A1b2C3d4")


def test_validate_permanent_password_rejects_too_long() -> None:
    with pytest.raises(PasswordValidationError, match="at most 256 characters"):
        validate_permanent_password("A" * 257)
