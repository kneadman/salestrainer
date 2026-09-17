from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    redis_url: str = "redis://localhost:6379/0"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/sales_trainer"
    session_ttl_seconds: int = Field(default=1800, ge=60)
    app_env: str = "local"
    log_level: str = "INFO"
    debug_cli: bool = False
    debug_llm_payload: bool = False
    llm_backend: str = "fake"
    allow_fake_llm_fallback: bool = False
    allow_in_memory_repository: bool = True
    llm_request_timeout_seconds: int = Field(default=30, ge=1, le=120)
    # Provider-neutral OpenAI-compatible router settings (used when llm_backend=openai_compatible).
    # LLM_BASE_URL lets deployments swap the router without code changes.
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_api_style: str = "chat_completions"
    llm_model: str = ""
    llm_dialogue_model: str = ""
    llm_persona_model: str = ""
    llm_judge_model: str = ""
    llm_summary_model: str = ""
    llm_response_format: str = "json_schema"
    # "provider_default" | "off" | "effort:<minimal|low|medium|high>".
    # Reasoning models add seconds of hidden thinking to every turn; "off" trades
    # some reasoning quality for latency. See reasoning_params() for the wire shape.
    llm_reasoning_mode: str = "provider_default"
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
    # Pre-generated persona reserve per training config. 0 disables the pool and
    # falls back to generating a persona inline on every session start.
    # ``target`` is the reserve size, ``low`` the watermark at which a refill starts.
    persona_pool_enabled: bool = True
    persona_pool_target_size: int = Field(default=8, ge=0, le=50)
    persona_pool_low_watermark: int = Field(default=3, ge=0, le=49)
    persona_pool_refill_batch_size: int = Field(default=4, ge=1, le=25)
    # Seconds between background refill sweeps of the reserve.
    persona_pool_refill_interval_seconds: int = Field(default=120, ge=10, le=3600)
    default_training_scenario_id: str = "first_contact_discovery"
    auth_cookie_name: str = "salestrainer_session"
    auth_session_ttl_seconds: int = 1209600
    auth_cookie_secure: bool = True
    auth_cookie_samesite: str = "lax"
    csrf_cookie_name: str = "salestrainer_csrf"
    csrf_token_ttl_seconds: int = 3600
    login_rate_limit_attempts: int = Field(default=5, ge=0)
    login_rate_limit_window_seconds: int = Field(default=300, ge=1)
    lead_rate_limit_attempts: int = Field(default=10, ge=0)
    lead_rate_limit_window_seconds: int = Field(default=3600, ge=1)
    trusted_proxy_ips: str = ""
    secret_encryption_key: str = ""
    stt_enabled: bool = False
    stt_backend: str = "fake"
    stt_language: str = "ru"
    stt_max_upload_bytes: int = Field(default=6_000_000, ge=100_000, le=25_000_000)
    stt_max_audio_seconds: int = Field(default=90, ge=1, le=300)
    stt_timeout_seconds: int = Field(default=120, ge=5, le=300)
    stt_concurrency: int = Field(default=1, ge=1, le=2)
    stt_max_concurrent_jobs: int = Field(default=1, ge=1, le=2)
    stt_queue_wait_timeout_seconds: int = Field(default=20, ge=1, le=120)
    stt_per_user_concurrency: int = Field(default=1, ge=1, le=2)
    stt_rate_limit_attempts: int = Field(default=20, ge=0)
    stt_rate_limit_window_seconds: int = Field(default=3600, ge=1)
    stt_global_rate_limit_attempts: int = Field(default=120, ge=0)
    stt_reject_unknown_duration: bool = True
    stt_temp_dir: str = "/tmp/salestrainer-stt"
    stt_whisper_cpp_binary: str = ""
    stt_model_path: str = ""
    stt_ffprobe_binary: str = "ffprobe"
    stt_ffmpeg_binary: str = "ffmpeg"
    stt_normalization_mode: str = "light"
    telegram_bot_token: str = ""
    telegram_lead_chat_id: str = ""

    @property
    def is_local_env(self) -> bool:
        return self.app_env.lower().strip() == "local"


def is_fake_fallback_allowed(settings: Settings) -> bool:
    """Allow fake LLM fallback only in explicitly non-production-like environments."""
    env = settings.app_env.lower().strip()
    return env in {"local", "dev", "development", "test", "demo"} and settings.allow_fake_llm_fallback


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
