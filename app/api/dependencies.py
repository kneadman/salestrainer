from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.application.persona_generation_service import PersonaGenerationService
from app.application.report_service import ReportService
from app.application.session_service import TrainingSessionService
from app.application.turn_service import TurnService
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


def get_app_settings(request: Request) -> Settings:
    """Return app settings for request-scoped services."""
    return request.app.state.settings


def get_persona_generation_service(
    db_session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> PersonaGenerationService:
    """Build the request-scoped persona generation service."""
    return PersonaGenerationService(db_session, settings=settings)
