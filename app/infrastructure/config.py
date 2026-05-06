from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    redis_url: str = "redis://localhost:6379/0"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/sales_trainer"
    session_ttl_seconds: int = 86400
    app_env: str = "local"
    log_level: str = "INFO"
    debug_cli: bool = False
    debug_llm_payload: bool = False
    llm_backend: str = "fake"
    allow_fake_llm_fallback: bool = True
    allow_in_memory_repository: bool = True
    llm_request_timeout_seconds: int = Field(default=30, ge=1, le=120)
    yandex_api_key: str = ""
    yandex_folder_id: str = ""
    yandex_agent_id: str = ""
    yandex_persona_folder_id: str = ""
    yandex_persona_agent_id: str = ""
    yandex_dialogue_folder_id: str = ""
    yandex_dialogue_agent_id: str = ""
    yandex_judge_folder_id: str = ""
    yandex_judge_agent_id: str = ""
    yandex_base_url: str = "https://ai.api.cloud.yandex.net/v1"
    recent_turn_limit: int = Field(default=6, ge=1, le=20)
    persona_random_seed: int | None = None
    default_training_scenario_id: str = "first_contact_discovery"
    auth_cookie_name: str = "salestrainer_session"
    auth_session_ttl_seconds: int = 1209600
    auth_cookie_secure: bool = True
    auth_cookie_samesite: str = "lax"
    csrf_cookie_name: str = "salestrainer_csrf"
    csrf_token_ttl_seconds: int = 3600
    login_rate_limit_attempts: int = Field(default=5, ge=0)
    login_rate_limit_window_seconds: int = Field(default=300, ge=1)
    secret_encryption_key: str = ""

    @property
    def is_local_env(self) -> bool:
        return self.app_env.lower().strip() == "local"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
