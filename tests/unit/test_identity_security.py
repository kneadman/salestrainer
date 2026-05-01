from __future__ import annotations

from app.identity.security import hash_password, verify_password


def test_hash_password_and_verify_success() -> None:
    password = "temporary-password"

    password_hash = hash_password(password)

    assert password_hash != password
    assert verify_password(password, password_hash) is True


def test_verify_password_returns_false_for_wrong_password() -> None:
    password_hash = hash_password("temporary-password")

    assert verify_password("wrong-password", password_hash) is False
