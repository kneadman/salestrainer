from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_report_service, get_session_service, get_turn_service
from app.api.errors import conflict, not_found
from app.access.service import AccessService
from app.api.schemas import (
    ErrorResponse,
    FinishSessionResponse,
    LandingLeadRequest,
    LandingSubmitResponse,
    PersonaOptionDTO,
    QuizLeadRequest,
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
from app.domain.errors import (
    SalesTrainerError,
    SessionNotActiveError,
    SessionNotFoundError,
    StateVersionConflictError,
    UnknownPersonaError,
    UnknownScenarioError,
)
from app.domain.personas import list_personas
from app.domain.scenarios import list_scenarios
from app.identity.dependencies import (
    get_access_service,
    require_current_user,
    require_internal_admin,
)
from app.identity.service import CurrentSession

router = APIRouter(prefix="/api")


ERROR_RESPONSES = {
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
}


def raise_api_error(error: SalesTrainerError) -> None:
    if isinstance(error, (SessionNotFoundError, UnknownScenarioError, UnknownPersonaError)):
        raise not_found(str(error)) from error
    if isinstance(error, (SessionNotActiveError, StateVersionConflictError)):
        raise conflict(str(error)) from error
    raise error


@router.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/leads", response_model=LandingSubmitResponse, status_code=status.HTTP_202_ACCEPTED)
def submit_landing_lead(request: LandingLeadRequest) -> LandingSubmitResponse:
    # TODO: Persist leads or send them to CRM once the integration target is chosen.
    return LandingSubmitResponse(status="accepted")


@router.post("/quiz-leads", response_model=LandingSubmitResponse, status_code=status.HTTP_202_ACCEPTED)
def submit_quiz_lead(request: QuizLeadRequest) -> LandingSubmitResponse:
    # TODO: Persist quiz answers or send them to CRM once the integration target is chosen.
    return LandingSubmitResponse(status="accepted")


@router.get("/scenarios", response_model=list[ScenarioOptionDTO], responses=ERROR_RESPONSES)
def get_scenarios(
    access_service: AccessService = Depends(get_access_service),
    current_session: CurrentSession = Depends(require_current_user),
) -> list[ScenarioOptionDTO]:
    scenarios = list_scenarios()
    if current_session.user.role != "internal_admin":
        try:
            training_config = access_service.get_default_training_config_for_user(current_session.user.id)
        except LookupError as error:
            raise not_found(str(error)) from error
        allowed_ids = set(training_config.allowed_scenario_ids())
        scenarios = [scenario for scenario in scenarios if scenario.id in allowed_ids]

    return [
        ScenarioOptionDTO(
            scenario_id=scenario.id,
            name=scenario.name,
            offer=scenario.offer,
            target_audience=scenario.target_audience,
        )
        for scenario in scenarios
    ]


@router.get("/personas", response_model=list[PersonaOptionDTO], responses={**ERROR_RESPONSES, 403: {"model": ErrorResponse}})
def get_personas(
    current_session: CurrentSession = Depends(require_internal_admin),
) -> list[PersonaOptionDTO]:
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
    access_service: AccessService = Depends(get_access_service),
    current_session: CurrentSession = Depends(require_current_user),
) -> SessionStateResponse:
    try:
        user_role = current_session.user.role
        if user_role != "internal_admin" and request.persona_id is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="persona_id is not allowed for client_user sessions.",
            )

        training_config = access_service.get_default_training_config_for_user(current_session.user.id)
        if user_role == "internal_admin" and request.persona_id is not None:
            session = session_service.start_session(
                scenario_id=request.scenario_id,
                persona_id=request.persona_id,
            )
        else:
            session = session_service.start_session(
                scenario_id=request.scenario_id,
                training_config=training_config,
            )
        access_service.bind_session_to_user(
            session.session_id,
            current_session.user.id,
            training_config.client_account_id,
            training_config.id,
        )
    except SalesTrainerError as error:
        raise_api_error(error)
    except LookupError as error:
        raise not_found(str(error)) from error
    return SessionStateResponse(session=build_session_public_dto(session))


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse, responses=ERROR_RESPONSES)
def get_session(
    session_id: str,
    session_service: TrainingSessionService = Depends(get_session_service),
    access_service: AccessService = Depends(get_access_service),
    current_session: CurrentSession = Depends(require_current_user),
) -> SessionDetailResponse:
    try:
        access_service.require_session_access(session_id, current_session.user.id)
    except LookupError as error:
        raise not_found(str(error)) from error
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
    access_service: AccessService = Depends(get_access_service),
    current_session: CurrentSession = Depends(require_current_user),
) -> SessionStateResponse:
    try:
        access_service.require_session_access(session_id, current_session.user.id)
        session = session_service.resume_session(session_id)
    except SalesTrainerError as error:
        raise_api_error(error)
    except LookupError as error:
        raise not_found(str(error)) from error
    return SessionStateResponse(session=build_session_public_dto(session))


@router.post("/sessions/{session_id}/messages", response_model=TurnResponse, responses=ERROR_RESPONSES)
def post_manager_message(
    session_id: str,
    request: TurnRequest,
    turn_service: TurnService = Depends(get_turn_service),
    session_service: TrainingSessionService = Depends(get_session_service),
    access_service: AccessService = Depends(get_access_service),
    current_session: CurrentSession = Depends(require_current_user),
) -> TurnResponse:
    try:
        access_service.require_session_access(session_id, current_session.user.id)
        turn_result = turn_service.process_message(session_id, request.manager_message)
    except SalesTrainerError as error:
        raise_api_error(error)
    except LookupError as error:
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
    access_service: AccessService = Depends(get_access_service),
    current_session: CurrentSession = Depends(require_current_user),
) -> FinishSessionResponse:
    try:
        access_service.require_session_access(session_id, current_session.user.id)
        report_text = report_service.finish_session(session_id)
    except SalesTrainerError as error:
        raise_api_error(error)
    except LookupError as error:
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
    access_service: AccessService = Depends(get_access_service),
    current_session: CurrentSession = Depends(require_current_user),
) -> SessionReportResponse:
    try:
        access_service.require_session_access(session_id, current_session.user.id)
    except LookupError as error:
        raise not_found(str(error)) from error
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
