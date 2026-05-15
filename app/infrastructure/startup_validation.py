from __future__ import annotations

from app.domain.errors import LLMProviderConfigurationError
from app.infrastructure.config import Settings, is_fake_fallback_allowed
from app.infrastructure.secrets import SecretEncryptionError, require_secret_encryption_key

_DEFAULT_DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/sales_trainer"
_ALLOWED_LLM_BACKENDS = {"fake", "yandex_compatible"}


def validate_runtime_settings(settings: Settings) -> None:
    """Fail fast on production-like misconfiguration before service construction begins."""
    if settings.is_local_env:
        return
    env = settings.app_env.lower().strip()
    if env in {"test", "dev", "development", "demo"}:
        return
    _validate_database_url(settings)
    _validate_secret_encryption(settings)
    _validate_llm_runtime(settings)


def _validate_database_url(settings: Settings) -> None:
    """Reject the baked-in local PostgreSQL DSN outside local-style environments."""
    if settings.database_url.strip() == _DEFAULT_DATABASE_URL:
        raise RuntimeConfigurationError(
            "DATABASE_URL must be overridden outside local/dev/test/demo environments."
        )


def _validate_secret_encryption(settings: Settings) -> None:
    """Require a real secret-encryption key anywhere local fallback is not allowed."""
    try:
        require_secret_encryption_key(settings)
    except SecretEncryptionError as error:
        raise RuntimeConfigurationError(str(error)) from error


def _validate_llm_runtime(settings: Settings) -> None:
    """Reject unknown backends, incomplete Yandex config, and fake fallback in production-like envs."""
    backend = settings.llm_backend.lower().strip()
    if backend not in _ALLOWED_LLM_BACKENDS:
        raise LLMProviderConfigurationError(f"Unknown llm_backend '{settings.llm_backend}'.")
    if settings.allow_fake_llm_fallback:
        raise LLMProviderConfigurationError(
            "ALLOW_FAKE_LLM_FALLBACK is not permitted outside local/dev/test/demo environments."
        )
    if backend == "fake":
        raise LLMProviderConfigurationError(
            "LLM_BACKEND=fake is not permitted outside local/dev/test/demo environments."
        )

    missing_fields: list[str] = []
    if not settings.yandex_api_key:
        missing_fields.append("YANDEX_API_KEY")
    if not (settings.yandex_dialogue_folder_id or settings.yandex_folder_id):
        missing_fields.append("YANDEX_DIALOGUE_FOLDER_ID/YANDEX_FOLDER_ID")
    if not (settings.yandex_dialogue_agent_id or settings.yandex_agent_id):
        missing_fields.append("YANDEX_DIALOGUE_AGENT_ID/YANDEX_AGENT_ID")
    if not (settings.yandex_judge_folder_id or settings.yandex_folder_id):
        missing_fields.append("YANDEX_JUDGE_FOLDER_ID/YANDEX_FOLDER_ID")
    if not (settings.yandex_judge_agent_id or settings.yandex_agent_id):
        missing_fields.append("YANDEX_JUDGE_AGENT_ID/YANDEX_AGENT_ID")
    if not (settings.yandex_persona_folder_id or settings.yandex_folder_id):
        missing_fields.append("YANDEX_PERSONA_FOLDER_ID/YANDEX_FOLDER_ID")
    if not (settings.yandex_persona_agent_id or settings.yandex_agent_id):
        missing_fields.append("YANDEX_PERSONA_AGENT_ID/YANDEX_AGENT_ID")
    if missing_fields:
        raise LLMProviderConfigurationError(
            "Incomplete Yandex LLM configuration: missing " + ", ".join(missing_fields) + "."
        )


class RuntimeConfigurationError(RuntimeError):
    """Raised when startup configuration is unsafe for production-like environments."""
