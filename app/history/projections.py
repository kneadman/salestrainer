from __future__ import annotations

from app.history.models import TrainingReportRecord, TrainingSessionRecord, TrainingTurnRecord
from app.history.schemas import ClientHistorySessionSummaryDTO, HistoryReportDTO, HistorySessionSummaryDTO, HistoryTurnDTO
from app.domain.models import RevealedFact
from app.domain.public_facts import is_probably_technical_value, normalize_public_fact_text, sanitize_revealed_fact_dicts


def _legacy_revealed_facts_from_snapshot(client_state: dict[str, object]) -> list[dict[str, object]]:
    if "revealed_facts" in client_state:
        return sanitize_revealed_fact_dicts(client_state.get("revealed_facts"))

    candidates: list[tuple[str, object]] = [
        ("role", client_state.get("discovered_role")),
        ("authority", client_state.get("discovered_authority_level")),
        ("current_process", client_state.get("discovered_current_process", [])),
        ("decision_criterion", client_state.get("discovered_decision_criteria", [])),
        ("constraint", client_state.get("discovered_constraints", [])),
        ("buying_signal", client_state.get("buying_signals", [])),
        ("pain", client_state.get("discovered_pains", [])),
    ]
    result: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for category, raw_values in candidates:
        values = raw_values if isinstance(raw_values, list) else [raw_values]
        for raw_value in values:
            if not isinstance(raw_value, str):
                continue
            text = normalize_public_fact_text(raw_value)
            if is_probably_technical_value(text):
                continue
            dedupe_key = (category, text.casefold())
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            result.append(
                RevealedFact(category=category, text=text, turn_index=1).model_dump(mode="json")
            )
    return result


def session_summary_dto(
    record: TrainingSessionRecord,
    *,
    user_email: str,
    training_config_name: str | None = None,
) -> HistorySessionSummaryDTO:
    """Project a persistent session record to the public-safe history summary DTO."""
    return HistorySessionSummaryDTO(
        session_id=record.id,
        user_id=record.user_id,
        user_email=user_email,
        client_account_id=record.client_account_id,
        training_config_id=record.training_config_id,
        training_config_name=training_config_name,
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


def client_session_summary_dto(
    record: TrainingSessionRecord,
    *,
    user_email: str,
    training_config_name: str | None = None,
) -> ClientHistorySessionSummaryDTO:
    """Project a persistent session record without tenant/config ownership identifiers."""
    return ClientHistorySessionSummaryDTO(
        session_id=record.id,
        user_email=user_email,
        training_config_name=training_config_name,
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
    revealed_facts = _legacy_revealed_facts_from_snapshot(client_state)
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
            "revealed_facts": revealed_facts,
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
