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

REQUEST_ID_HEADER = "X-Request-ID"


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
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.include_router(router)
    return app


app = create_app()
