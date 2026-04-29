from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Request

from app.application.report_service import ReportService
from app.application.session_service import TrainingSessionService
from app.application.turn_service import TurnService


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
