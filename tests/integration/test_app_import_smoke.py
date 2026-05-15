from __future__ import annotations

import pytest

from app.api.main import create_app
from app.infrastructure.config import Settings
from app.infrastructure.llm_client import FakeLLMClient
from app.infrastructure.session_repository import InMemorySessionRepository
from app.infrastructure.startup_validation import RuntimeConfigurationError
from app.internal_admin import schemas as internal_admin_schemas


def test_fastapi_app_imports_with_internal_admin_schemas() -> None:
    assert internal_admin_schemas.UserCreateRequest is not None

    app = create_app(
        settings=Settings(
            auth_cookie_secure=False,
            login_rate_limit_attempts=0,
            secret_encryption_key="test-secret-key",
        ),
        repository=InMemorySessionRepository(),
        llm_client=FakeLLMClient(),
    )

    assert app is not None


def test_create_app_fails_fast_on_production_like_default_database_url() -> None:
    with pytest.raises(RuntimeConfigurationError, match="DATABASE_URL"):
        create_app(
            settings=Settings(
                app_env="production",
                llm_backend="fake",
                database_url="postgresql+psycopg://postgres:postgres@localhost:5432/sales_trainer",
                secret_encryption_key="prod-secret",
                auth_cookie_secure=False,
                login_rate_limit_attempts=0,
            ),
            repository=InMemorySessionRepository(),
            llm_client=FakeLLMClient(),
        )
