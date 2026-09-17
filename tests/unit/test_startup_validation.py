from __future__ import annotations

import pytest

from app.domain.errors import LLMProviderConfigurationError
from app.infrastructure.config import Settings
from app.infrastructure.startup_validation import RuntimeConfigurationError, validate_runtime_settings


def test_validate_runtime_settings_allows_local_defaults() -> None:
    validate_runtime_settings(Settings())


def test_validate_runtime_settings_rejects_default_database_url_in_production() -> None:
    with pytest.raises(RuntimeConfigurationError, match="DATABASE_URL"):
        validate_runtime_settings(
            Settings(
                app_env="production",
                llm_backend="fake",
                database_url="postgresql+psycopg://postgres:postgres@localhost:5432/sales_trainer",
                secret_encryption_key="prod-secret",
            )
        )


def test_validate_runtime_settings_rejects_missing_secret_in_production() -> None:
    with pytest.raises(RuntimeConfigurationError, match="SECRET_ENCRYPTION_KEY"):
        validate_runtime_settings(
            Settings(
                app_env="production",
                llm_backend="fake",
                database_url="postgresql+psycopg://user:pass@db:5432/sales_trainer",
                secret_encryption_key="",
            )
        )


def test_validate_runtime_settings_rejects_unknown_llm_backend_in_production() -> None:
    with pytest.raises(LLMProviderConfigurationError, match="Unknown llm_backend"):
        validate_runtime_settings(
            Settings(
                app_env="production",
                llm_backend="mystery",
                database_url="postgresql+psycopg://user:pass@db:5432/sales_trainer",
                secret_encryption_key="prod-secret",
            )
        )


def test_validate_runtime_settings_rejects_fake_fallback_flag_in_production() -> None:
    with pytest.raises(LLMProviderConfigurationError, match="ALLOW_FAKE_LLM_FALLBACK"):
        validate_runtime_settings(
            Settings(
                app_env="production",
                llm_backend="yandex_compatible",
                allow_fake_llm_fallback=True,
                database_url="postgresql+psycopg://user:pass@db:5432/sales_trainer",
                secret_encryption_key="prod-secret",
                yandex_api_key="token",
                yandex_folder_id="folder",
                yandex_agent_id="agent",
                yandex_dialogue_folder_id="dialogue-folder",
                yandex_dialogue_agent_id="dialogue-agent",
                yandex_judge_folder_id="judge-folder",
                yandex_judge_agent_id="judge-agent",
                yandex_persona_folder_id="persona-folder",
                yandex_persona_agent_id="persona-agent",
            )
        )


def test_validate_runtime_settings_rejects_fake_backend_in_production() -> None:
    with pytest.raises(LLMProviderConfigurationError, match="LLM_BACKEND=fake"):
        validate_runtime_settings(
            Settings(
                app_env="production",
                llm_backend="fake",
                allow_fake_llm_fallback=False,
                database_url="postgresql+psycopg://user:pass@db:5432/sales_trainer",
                secret_encryption_key="prod-secret",
            )
        )


def test_validate_runtime_settings_rejects_incomplete_yandex_config_in_production() -> None:
    with pytest.raises(LLMProviderConfigurationError, match="Incomplete Yandex LLM configuration"):
        validate_runtime_settings(
            Settings(
                app_env="production",
                llm_backend="yandex_compatible",
                allow_fake_llm_fallback=False,
                database_url="postgresql+psycopg://user:pass@db:5432/sales_trainer",
                secret_encryption_key="prod-secret",
                yandex_api_key="token",
                yandex_dialogue_folder_id="dialogue-folder",
                yandex_dialogue_agent_id="dialogue-agent",
                yandex_folder_id="",
                yandex_agent_id="",
                yandex_judge_folder_id="",
                yandex_judge_agent_id="",
                yandex_persona_folder_id="",
                yandex_persona_agent_id="",
            )
        )


def test_validate_runtime_settings_accepts_complete_yandex_config_in_production() -> None:
    validate_runtime_settings(
        Settings(
            app_env="production",
            llm_backend="yandex_compatible",
            allow_fake_llm_fallback=False,
            database_url="postgresql+psycopg://user:pass@db:5432/sales_trainer",
            secret_encryption_key="prod-secret",
            yandex_api_key="token",
            yandex_dialogue_folder_id="dialogue-folder",
            yandex_dialogue_agent_id="dialogue-agent",
            yandex_judge_folder_id="judge-folder",
            yandex_judge_agent_id="judge-agent",
            yandex_persona_folder_id="persona-folder",
            yandex_persona_agent_id="persona-agent",
        )
    )
