from __future__ import annotations

from app.api.main import create_app
from app.infrastructure.config import Settings
from app.infrastructure.llm_client import FakeLLMClient
from app.infrastructure.session_repository import InMemorySessionRepository
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
