from __future__ import annotations

from app.history.models import TrainingReportRecord, TrainingSessionRecord, TrainingTurnRecord
from app.history.schemas import HistoryReportDTO, HistorySessionSummaryDTO, HistoryTurnDTO


def session_summary_dto(record: TrainingSessionRecord, *, user_email: str) -> HistorySessionSummaryDTO:
    """Project a persistent session record to the public-safe history summary DTO."""
    return HistorySessionSummaryDTO(
        session_id=record.id,
        user_id=record.user_id,
        user_email=user_email,
        client_account_id=record.client_account_id,
        training_config_id=record.training_config_id,
        scenario_id=record.scenario_id,
        status=record.status,
        started_at=record.started_at,
        finished_at=record.finished_at,
        last_activity_at=record.last_activity_at,
        turn_count=record.turn_count,
        final_interest_score=record.final_interest_score,
        final_stage=record.final_stage,
        summary=record.summary,
    )


def turn_dto(record: TrainingTurnRecord) -> HistoryTurnDTO:
    """Project a turn record without exposing raw LLM payloads or hidden persona fields."""
    client_state = record.client_state_snapshot or {}
    return HistoryTurnDTO(
        turn_index=record.turn_index,
        manager_message=record.manager_message,
        client_answer=record.client_answer,
        interest_before=record.interest_before,
        interest_delta=record.interest_delta,
        interest_after=record.interest_after,
        stage_before=record.stage_before,
        stage_after=record.stage_after,
        client_state_public={
            "tone": client_state.get("tone"),
            "trust": client_state.get("trust"),
            "visible_objections": client_state.get("open_objections", []),
            "known_pains": client_state.get("discovered_pains", []),
            "buying_signals": client_state.get("buying_signals", []),
            "discovered_role": client_state.get("discovered_role"),
            "discovered_authority_level": client_state.get("discovered_authority_level"),
            "discovered_decision_criteria": client_state.get("discovered_decision_criteria", []),
            "discovered_constraints": client_state.get("discovered_constraints", []),
            "discovered_current_process": client_state.get("discovered_current_process", []),
        },
        evaluation=record.evaluation_snapshot,
        created_at=record.created_at,
    )


def report_dto(record: TrainingReportRecord) -> HistoryReportDTO:
    """Project a saved report record to the client/internal API response DTO."""
    return HistoryReportDTO(
        session_id=record.session_id,
        report=record.report_text,
        report_payload=record.report_payload,
        report_version=record.report_version,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )
