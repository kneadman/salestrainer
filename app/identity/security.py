from __future__ import annotations

import hashlib
import re
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError, VerificationError
from argon2.low_level import Type

_PASSWORD_HASHER = PasswordHasher(type=Type.ID)

# Permanent passwords must contain only ASCII letters and digits.
_PERMANENT_PASSWORD_PATTERN = re.compile(r"^[a-zA-Z0-9]+$")
MAX_PASSWORD_LENGTH = 256


class PasswordValidationError(ValueError):
    """Raised when a password does not meet the permanent password policy."""


def validate_permanent_password(password: str) -> None:
    """Validate a permanent user password against the product policy.

    Rules:
    - Minimum 8 characters.
    - Maximum 256 characters.
    - Only Latin letters and digits (no spaces, no special characters).
    """
    if len(password) < 8:
        raise PasswordValidationError("Password must be at least 8 characters long.")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise PasswordValidationError(f"Password must be at most {MAX_PASSWORD_LENGTH} characters long.")
    if not _PERMANENT_PASSWORD_PATTERN.match(password):
        raise PasswordValidationError("Password must contain only Latin letters and digits.")


def hash_password(password: str) -> str:
    return _PASSWORD_HASHER.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _PASSWORD_HASHER.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def generate_secure_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
