from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    redis_url: str = "redis://localhost:6379/0"
    session_ttl_seconds: int = 86400
    app_env: str = "local"
    log_level: str = "INFO"
    debug_cli: bool = False
    llm_backend: str = "fake"
    llm_request_timeout_seconds: int = Field(default=30, ge=1, le=120)
    yandex_api_key: str = ""
    yandex_folder_id: str = ""
    yandex_agent_id: str = ""
    yandex_base_url: str = "https://ai.api.cloud.yandex.net/v1"
    recent_turn_limit: int = Field(default=6, ge=1, le=20)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
