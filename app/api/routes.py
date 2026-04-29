from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_report_service, get_session_service, get_turn_service
from app.api.errors import conflict, not_found
from app.api.schemas import (
    ErrorResponse,
    FinishSessionResponse,
    PersonaOptionDTO,
    ScenarioOptionDTO,
    SessionCreateRequest,
    SessionDetailResponse,
    SessionReportResponse,
    SessionStateResponse,
    TurnRequest,
    TurnResponse,
)
from app.application.projections import build_session_public_dto, build_turn_public_dto
from app.application.report_service import ReportService
from app.application.session_service import TrainingSessionService
from app.application.turn_service import TurnService
from app.domain.personas import list_personas
from app.domain.scenarios import list_scenarios

router = APIRouter(prefix="/api")


ERROR_RESPONSES = {
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
}


@router.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/scenarios", response_model=list[ScenarioOptionDTO])
def get_scenarios() -> list[ScenarioOptionDTO]:
    return [
        ScenarioOptionDTO(
            scenario_id=scenario.id,
            name=scenario.name,
            offer=scenario.offer,
            target_audience=scenario.target_audience,
        )
        for scenario in list_scenarios()
    ]


@router.get("/personas", response_model=list[PersonaOptionDTO])
def get_personas() -> list[PersonaOptionDTO]:
    return [
        PersonaOptionDTO(
            persona_id=persona.id,
            display_name=persona.display_name,
            role=persona.role,
            authority_level=persona.authority_level,
            behavior_model=persona.behavior_model,
        )
        for persona in list_personas()
    ]


@router.post(
    "/sessions",
    response_model=SessionStateResponse,
    status_code=status.HTTP_201_CREATED,
    responses=ERROR_RESPONSES,
)
def create_session(
    request: SessionCreateRequest,
    session_service: TrainingSessionService = Depends(get_session_service),
) -> SessionStateResponse:
    session = session_service.start_session(
        scenario_id=request.scenario_id,
        persona_id=request.persona_id,
    )
    return SessionStateResponse(session=build_session_public_dto(session))


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse, responses=ERROR_RESPONSES)
def get_session(
    session_id: str,
    session_service: TrainingSessionService = Depends(get_session_service),
) -> SessionDetailResponse:
    session = session_service.get_session(session_id)
    if session is None:
        raise not_found("Session not found.")
    return SessionDetailResponse(
        session=build_session_public_dto(session),
        turns=build_turn_public_dto(session),
    )


@router.post("/sessions/{session_id}/resume", response_model=SessionStateResponse, responses=ERROR_RESPONSES)
def resume_session(
    session_id: str,
    session_service: TrainingSessionService = Depends(get_session_service),
) -> SessionStateResponse:
    try:
        session = session_service.resume_session(session_id)
    except ValueError as error:
        raise not_found(str(error)) from error
    return SessionStateResponse(session=build_session_public_dto(session))


@router.post("/sessions/{session_id}/messages", response_model=TurnResponse, responses=ERROR_RESPONSES)
def post_manager_message(
    session_id: str,
    request: TurnRequest,
    turn_service: TurnService = Depends(get_turn_service),
    session_service: TrainingSessionService = Depends(get_session_service),
) -> TurnResponse:
    try:
        turn_result = turn_service.process_message(session_id, request.manager_message)
    except ValueError as error:
        raise not_found(str(error)) from error
    session = session_service.get_session(session_id)
    if session is None:
        raise not_found("Session not found after turn.")
    return TurnResponse(
        session=build_session_public_dto(session),
        turns=build_turn_public_dto(session),
        client_answer=turn_result.client_answer,
        interest_before=turn_result.interest_before,
        interest_delta=turn_result.interest_delta,
        interest_after=turn_result.interest_after,
        stage_before=turn_result.stage_before,
        stage_after=turn_result.stage_after,
        turn_index=turn_result.turn_index,
    )


@router.post("/sessions/{session_id}/finish", response_model=FinishSessionResponse, responses=ERROR_RESPONSES)
def finish_session(
    session_id: str,
    report_service: ReportService = Depends(get_report_service),
    session_service: TrainingSessionService = Depends(get_session_service),
) -> FinishSessionResponse:
    try:
        report_text = report_service.finish_session(session_id)
    except ValueError as error:
        raise not_found(str(error)) from error
    session = session_service.get_session(session_id)
    if session is None:
        raise not_found("Session not found after finish.")
    return FinishSessionResponse(
        session=build_session_public_dto(session),
        report=report_text,
    )


@router.get("/sessions/{session_id}/report", response_model=SessionReportResponse, responses=ERROR_RESPONSES)
def get_report(
    session_id: str,
    report_service: ReportService = Depends(get_report_service),
    session_service: TrainingSessionService = Depends(get_session_service),
) -> SessionReportResponse:
    session = session_service.get_session(session_id)
    if session is None:
        raise not_found("Session not found.")
    if session.status != "finished":
        raise conflict("Session is not finished yet.")
    report_text = report_service.generate_report(session_id)
    session = session_service.get_session(session_id)
    if session is None:
        raise not_found("Session not found after report.")
    return SessionReportResponse(
        session=build_session_public_dto(session),
        report=report_text,
    )
