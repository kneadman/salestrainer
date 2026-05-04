from __future__ import annotations

import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.dependencies import ServiceContainer
from app.api.routes import router
from app.api.schemas import ErrorBody, ErrorResponse
from app.application.report_service import ReportService
from app.application.session_service import TrainingSessionService
from app.application.turn_service import TurnService
from app.domain.persona_generation import PersonaGenerator
from app.infrastructure.config import Settings, get_settings
from app.infrastructure.llm_client import LLMClient, build_llm_client
from app.infrastructure.logging import setup_logging
from app.infrastructure.redis_client import build_repository
from app.infrastructure.session_repository import SessionRepository
from app.infrastructure.summary_compressor import build_summary_compressor
from app.identity.csrf import CSRF_HEADER_NAME, csrf_tokens_match
from app.identity.rate_limit import build_login_rate_limiter
from app.identity.routes import router as auth_router
from app.internal_admin.routes import router as internal_admin_router
from app.history.internal_routes import router as internal_history_router
from app.history.routes import router as history_router
from app.client_portal.routes import router as client_portal_router
from app.web.static import mount_frontend

REQUEST_ID_HEADER = "X-Request-ID"
CSRF_PROTECTED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
CSRF_EXEMPT_PATHS = {"/auth/login", "/auth/csrf", "/api/health"}


def _error_response(
    *,
    request_id: str | None,
    status_code: int,
    code: str,
    message: str,
    details: list[dict[str, object]] | None = None,
) -> JSONResponse:
    payload = ErrorResponse(
        error=ErrorBody(code=code, message=message, request_id=request_id, details=details or []),
    )
    response = JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))
    if request_id:
        response.headers[REQUEST_ID_HEADER] = request_id
    return response


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    code = {
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        422: "validation_error",
    }.get(exc.status_code, "http_error")
    message = str(exc.detail)
    return _error_response(
        request_id=getattr(request.state, "request_id", None),
        status_code=exc.status_code,
        code=code,
        message=message,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        {
            "loc": list(error["loc"]),
            "msg": error["msg"],
            "type": error["type"],
        }
        for error in exc.errors()
    ]
    return _error_response(
        request_id=getattr(request.state, "request_id", None),
        status_code=422,
        code="validation_error",
        message="Request validation failed.",
        details=details,
    )


def create_app(
    *,
    settings: Settings | None = None,
    repository: SessionRepository | None = None,
    llm_client: LLMClient | None = None,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    setup_logging(resolved_settings.log_level)
    resolved_repository = repository or build_repository(resolved_settings)
    resolved_llm_client = llm_client or build_llm_client(resolved_settings)

    session_service = TrainingSessionService(
        resolved_repository,
        persona_generator=PersonaGenerator(resolved_settings.persona_random_seed),
        default_scenario_id=resolved_settings.default_training_scenario_id,
    )
    turn_service = TurnService(
        resolved_repository,
        resolved_llm_client,
        recent_turn_limit=resolved_settings.recent_turn_limit,
        debug_mode=resolved_settings.debug_cli,
        summary_compressor=build_summary_compressor(resolved_settings),
    )
    report_service = ReportService(resolved_repository)

    app = FastAPI(title="Sales Trainer MVP API", version="0.1.0")

    @app.middleware("http")
    async def security_headers_middleware(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if request.url.path.startswith("/auth/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.middleware("http")
    async def csrf_middleware(request: Request, call_next):
        if _requires_csrf(request):
            settings = request.app.state.settings
            if not csrf_tokens_match(
                request.cookies.get(settings.csrf_cookie_name),
                request.headers.get(CSRF_HEADER_NAME),
            ):
                request_id = (
                    getattr(request.state, "request_id", None)
                    or request.headers.get(REQUEST_ID_HEADER)
                    or str(uuid.uuid4())
                )
                request.state.request_id = request_id
                return _error_response(
                    request_id=request_id,
                    status_code=403,
                    code="forbidden",
                    message="Missing or invalid CSRF token.",
                )
        return await call_next(request)

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response

    app.state.services = ServiceContainer(
        session_service=session_service,
        turn_service=turn_service,
        report_service=report_service,
    )
    app.state.settings = resolved_settings
    app.state.login_rate_limiter = build_login_rate_limiter(resolved_settings)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.include_router(auth_router)
    app.include_router(router)
    app.include_router(history_router)
    app.include_router(client_portal_router)
    app.include_router(internal_admin_router)
    app.include_router(internal_history_router)
    mount_frontend(app)
    return app


def _requires_csrf(request: Request) -> bool:
    path = request.url.path
    if request.method.upper() not in CSRF_PROTECTED_METHODS:
        return False
    if path in CSRF_EXEMPT_PATHS:
        return False
    settings = request.app.state.settings
    if not request.cookies.get(settings.auth_cookie_name):
        return False
    return path.startswith("/auth/") or path.startswith("/api/")


app = create_app()
