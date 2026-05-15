from datetime import UTC, datetime
from uuid import uuid4

from app.history.models import TrainingTurnRecord
from app.history.projections import turn_dto


def _turn_record(client_state_snapshot: dict[str, object]) -> TrainingTurnRecord:
    return TrainingTurnRecord(
        id=uuid4(),
        session_id=uuid4(),
        turn_index=3,
        manager_message="question",
        client_answer="answer",
        interest_before=20,
        interest_delta=1,
        interest_after=21,
        stage_before="first_contact",
        stage_after="need_discovery",
        client_state_snapshot=client_state_snapshot,
        llm_payload_snapshot=None,
        llm_response_snapshot=None,
        evaluation_snapshot=None,
        created_at=datetime.now(tz=UTC),
    )


def test_history_projection_exposes_saved_revealed_facts() -> None:
    dto = turn_dto(
        _turn_record(
            {
                "tone": "neutral",
                "trust": 20,
                "revealed_facts": [
                    {"category": "role", "text": "финансовый директор", "turn_index": 2}
                ],
            }
        )
    )

    assert dto.client_state_public is not None
    assert dto.client_state_public["revealed_facts"] == [
        {"category": "role", "text": "финансовый директор", "turn_index": 2}
    ]


def test_history_projection_uses_filtered_legacy_fallback_when_revealed_facts_are_missing() -> None:
    dto = turn_dto(
        _turn_record(
            {
                "tone": "neutral",
                "trust": 20,
                "discovered_role": "cfo",
                "discovered_constraints": ["current_vendor_loyalty", "нужно внедрить до конца месяца"],
            }
        )
    )

    assert dto.client_state_public is not None
    assert dto.client_state_public["revealed_facts"] == [
        {"category": "constraint", "text": "нужно внедрить до конца месяца", "turn_index": 1}
    ]


def test_history_projection_does_not_fallback_when_new_revealed_facts_are_empty() -> None:
    dto = turn_dto(
        _turn_record(
            {
                "tone": "neutral",
                "trust": 20,
                "revealed_facts": [],
                "discovered_current_process": ["should not leak"],
                "discovered_pains": ["should not leak either"],
            }
        )
    )

    assert dto.client_state_public is not None
    assert dto.client_state_public["revealed_facts"] == []
