from __future__ import annotations

import base64
import hashlib
import hmac
import os

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
    key = _derive_key(require_secret_encryption_key(settings))
    nonce = os.urandom(16)
    data = plaintext.encode("utf-8")
    ciphertext = _xor_with_keystream(data, key, nonce)
    tag = hmac.new(key, nonce + ciphertext, hashlib.sha256).digest()
    return "v1:" + base64.urlsafe_b64encode(nonce + tag + ciphertext).decode("ascii")


def decrypt_secret(token: str, settings: Settings) -> str:
    key = _derive_key(require_secret_encryption_key(settings))
    if not token.startswith("v1:"):
        raise SecretEncryptionError("Unsupported encrypted secret format.")
    try:
        payload = base64.urlsafe_b64decode(token[3:].encode("ascii"))
    except ValueError as error:
        raise SecretEncryptionError("Invalid encrypted secret payload.") from error
    if len(payload) < 48:
        raise SecretEncryptionError("Invalid encrypted secret payload.")
    nonce = payload[:16]
    tag = payload[16:48]
    ciphertext = payload[48:]
    expected_tag = hmac.new(key, nonce + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(tag, expected_tag):
        raise SecretEncryptionError("Encrypted secret authentication failed.")
    return _xor_with_keystream(ciphertext, key, nonce).decode("utf-8")


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


def _derive_key(secret_key: str) -> bytes:
    return hashlib.sha256(secret_key.encode("utf-8")).digest()


def _xor_with_keystream(data: bytes, key: bytes, nonce: bytes) -> bytes:
    output = bytearray()
    counter = 0
    while len(output) < len(data):
        block = hmac.new(key, nonce + counter.to_bytes(8, "big"), hashlib.sha256).digest()
        output.extend(block)
        counter += 1
    return bytes(value ^ output[index] for index, value in enumerate(data))
