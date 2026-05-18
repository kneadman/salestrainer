from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.application.persona_generation_service import PersonaGenerationService
from app.application.report_service import ReportService
from app.application.runtime_activity_service import RuntimeActivityService
from app.application.session_service import TrainingSessionService
from app.application.speech_service import SpeechService
from app.application.turn_service import TurnService
from app.history.dependencies import get_history_service
from app.history.service import HistoryService
from app.infrastructure.config import Settings
from app.infrastructure.db import get_db_session


@dataclass
class ServiceContainer:
    session_service: TrainingSessionService
    turn_service: TurnService
    report_service: ReportService


def get_service_container(request: Request) -> ServiceContainer:
    return request.app.state.services


def get_session_service(
    container: ServiceContainer = Depends(get_service_container),
) -> TrainingSessionService:
    return container.session_service


def get_turn_service(
    container: ServiceContainer = Depends(get_service_container),
) -> TurnService:
    return container.turn_service


def get_report_service(
    container: ServiceContainer = Depends(get_service_container),
) -> ReportService:
    return container.report_service


def get_runtime_activity_service(
    session_service: TrainingSessionService = Depends(get_session_service),
    history_service: HistoryService = Depends(get_history_service),
) -> RuntimeActivityService:
    """Build a request-scoped coordinator for runtime/durable activity touches."""
    return RuntimeActivityService(session_service, history_service)


def get_speech_service(request: Request) -> SpeechService:
    """Return the shared speech transcription service."""
    return request.app.state.speech_service


def get_app_settings(request: Request) -> Settings:
    """Return app settings for request-scoped services."""
    return request.app.state.settings


def get_persona_generation_service(
    db_session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> PersonaGenerationService:
    """Build the request-scoped persona generation service."""
    return PersonaGenerationService(db_session, settings=settings)
