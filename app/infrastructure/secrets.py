from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.infrastructure.config import Settings


class SecretEncryptionError(Exception):
    pass


def require_secret_encryption_key(settings: Settings) -> str:
    key = settings.secret_encryption_key.strip()
    if key:
        return key
    if settings.is_local_env:
        return "local-development-secret-encryption-key"
    raise SecretEncryptionError("SECRET_ENCRYPTION_KEY is required outside local environment.")


def encrypt_secret(plaintext: str, settings: Settings) -> str:
    fernet = _build_fernet(require_secret_encryption_key(settings))
    encrypted = fernet.encrypt(plaintext.encode("utf-8")).decode("ascii")
    return f"fernet:v1:{encrypted}"


def decrypt_secret(token: str, settings: Settings) -> str:
    if not token.startswith("fernet:v1:"):
        raise SecretEncryptionError("Unsupported encrypted secret format.")
    fernet = _build_fernet(require_secret_encryption_key(settings))
    try:
        return fernet.decrypt(token.removeprefix("fernet:v1:").encode("ascii")).decode("utf-8")
    except InvalidToken as error:
        raise SecretEncryptionError("Encrypted secret authentication failed.") from error


def mask_secret(plaintext: str | None) -> str | None:
    if not plaintext:
        return None
    if len(plaintext) <= 8:
        return "****"
    return f"{plaintext[:4]}...{plaintext[-2:]}"


def preview_encrypted_secret(token: str | None, settings: Settings) -> str | None:
    if token is None:
        return None
    return mask_secret(decrypt_secret(token, settings))


def _build_fernet(secret_key: str) -> Fernet:
    digest = hashlib.sha256(secret_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))
