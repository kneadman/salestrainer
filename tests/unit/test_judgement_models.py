from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domain.judgement_models import (
    BentoReportBlock,
    JudgeSessionOutput,
    ReportRecommendation,
    SkillScore,
    build_judge_input_from_session,
)
from app.domain.models import ClientState, PersonaProfile, TrainingSessionState, Turn, TurnEvaluation
from tests.unit._persona_fixtures import valid_minimal_persona
from app.domain.scenarios import get_scenario


def _build_session_state() -> TrainingSessionState:
    """Create a compact session fixture for judgement model tests."""
    now = datetime.now(tz=UTC)
    return TrainingSessionState(
        session_id=uuid4(),
        scenario_id="sales_audit_cold_outreach",
        status="finished",
        persona=valid_minimal_persona(
            id="persona-1",
            display_name="Owner",
        ),
        interest_score=41,
        stage="needs_analysis",
        client_state=ClientState(
            tone="interested",
            trust=45,
            irritation=10,
            urgency=22,
            price_sensitivity=50,
            open_objections=["price"],
            known_pains=["late reports"],
            buying_signals=["asked for process"],
        ),
        summary="Manager clarified current process and surfaced one pain.",
        turns=[
            Turn(
                index=1,
                manager_message="How do you handle reporting now?",
                client_answer="Mostly manually and it is slow.",
                interest_before=25,
                interest_delta=6,
                interest_after=31,
                stage_before="first_contact",
                stage_after="qualification",
                created_at=now,
            ),
            Turn(
                index=2,
                manager_message="What breaks most often in that process?",
                client_answer="We lose time on reconciliations every month.",
                interest_before=31,
                interest_delta=10,
                interest_after=41,
                stage_before="qualification",
                stage_after="needs_analysis",
                created_at=now,
            ),
        ],
        turn_evaluations=[
            TurnEvaluation(
                turn_index=1,
                discovery_quality_score=4,
                role_identification_score=2,
                pain_identification_score=3,
                relevance_score=4,
                pressure_score=5,
                objection_handling_score=3,
                next_step_timing_score=2,
                conversation_control_score=4,
                notes=["Good opening question."],
            )
        ],
        recent_turns=[],
        turn_count=2,
        state_version=3,
        created_at=now,
        updated_at=now,
    )


def test_judge_session_input_builds_from_training_session_state() -> None:
    """Judge input should be assembled from the canonical session state."""
    session = _build_session_state()

    judge_input = build_judge_input_from_session(session)

    assert judge_input.task == "judge_training_session"
    assert judge_input.schema_version == 1
    assert judge_input.scenario == get_scenario(session.scenario_id)
    assert judge_input.persona == session.persona
    assert judge_input.final_client_state == session.client_state
    assert judge_input.conversation_summary == session.summary
    assert judge_input.heuristic_evaluations == session.turn_evaluations
    assert judge_input.final_interest_score == session.interest_score
    assert judge_input.final_stage == session.stage
    assert judge_input.turn_count == session.turn_count


def test_output_schema_forbids_extra_fields() -> None:
    """Judge output contract should reject undeclared fields."""
    with pytest.raises(ValidationError):
        JudgeSessionOutput(
            overall_score=82,
            overall_grade="good",
            outcome="Manager reached a reasonable next step.",
            executive_summary="Strong discovery with incomplete objection handling.",
            bento_blocks=[_minimal_block()],
            skill_scores=[_minimal_skill_score()],
            final_verdict="Good session overall.",
            unexpected_field=True,
        )


@pytest.mark.parametrize("score", [-1, 101])
def test_score_validation_rejects_out_of_range_values(score: int) -> None:
    """Judge output scores should stay within 0..100."""
    with pytest.raises(ValidationError):
        JudgeSessionOutput(
            overall_score=score,
            overall_grade="weak",
            outcome="Outcome",
            executive_summary="Summary",
            bento_blocks=[_minimal_block()],
            skill_scores=[_minimal_skill_score()],
            final_verdict="Verdict",
        )


def test_bento_report_block_supports_severity_and_evidence_turn_indexes() -> None:
    """Bento blocks should preserve severity and evidence indexes."""
    block = BentoReportBlock(
        id="strength-1",
        title="Discovery",
        type="strength",
        severity="green",
        score=78,
        short_text="Good discovery cadence.",
        detail="The manager asked contextual questions before moving to value.",
        evidence_turn_indexes=[1, 2],
    )

    assert block.severity == "green"
    assert block.evidence_turn_indexes == [1, 2]


def test_build_judge_input_from_session_maps_turns_correctly() -> None:
    """Turn mapping should preserve turn-by-turn conversation transitions."""
    session = _build_session_state()

    judge_input = build_judge_input_from_session(session)

    assert len(judge_input.turns) == 2
    assert judge_input.turns[0].turn_index == 1
    assert judge_input.turns[0].manager_message == session.turns[0].manager_message
    assert judge_input.turns[0].interest_before == 25
    assert judge_input.turns[0].stage_after == "qualification"
    assert judge_input.turns[1].turn_index == 2
    assert judge_input.turns[1].client_answer == session.turns[1].client_answer
    assert judge_input.turns[1].interest_delta == 10
    assert judge_input.turns[1].stage_before == "qualification"


def test_output_schema_version_rejects_unknown_version() -> None:
    """Judge output schema version should stay pinned to the first contract version."""
    with pytest.raises(ValidationError):
        JudgeSessionOutput(
            schema_version=2,
            overall_score=82,
            overall_grade="good",
            outcome="Manager reached a reasonable next step.",
            executive_summary="Strong discovery with incomplete objection handling.",
            bento_blocks=[_minimal_block()],
            skill_scores=[_minimal_skill_score()],
            final_verdict="Good session overall.",
        )


def test_outcome_longer_than_max_length_is_truncated() -> None:
    """Judge output should silently truncate strings that exceed max_length."""
    long_outcome = "а" * 300
    output = JudgeSessionOutput(
        overall_score=82,
        overall_grade="good",
        outcome=long_outcome,
        executive_summary="Summary",
        bento_blocks=[_minimal_block()],
        skill_scores=[_minimal_skill_score()],
        final_verdict="Verdict",
    )
    assert len(output.outcome) == 240


def test_bento_block_short_text_truncated() -> None:
    """Bento block short_text should be clamped to its max_length."""
    long_text = "б" * 400
    block = BentoReportBlock(
        id="summary",
        title="Итог",
        type="summary",
        severity="neutral",
        short_text=long_text,
        detail="Подробный итог.",
        evidence_turn_indexes=[1],
    )
    assert len(block.short_text) == 280


def test_recommendation_example_phrase_truncated() -> None:
    """Recommendation example_phrase should be clamped to its max_length."""
    long_phrase = "в" * 700
    rec = ReportRecommendation(
        title="Уточнить",
        description="Описание",
        example_phrase=long_phrase,
        priority="medium",
    )
    assert len(rec.example_phrase) == 500


def _minimal_block() -> BentoReportBlock:
    """Build one minimal valid bento block for output validation tests."""
    return BentoReportBlock(
        id="summary",
        title="Итог",
        type="summary",
        severity="neutral",
        short_text="Краткий итог.",
        detail="Подробный итог.",
        evidence_turn_indexes=[1],
    )


def _minimal_skill_score() -> SkillScore:
    """Build one minimal valid skill score for output validation tests."""
    return SkillScore(
        id="discovery_quality",
        title="Discovery quality",
        score=80,
        severity="green",
        explanation="Навык проявлен на хорошем уровне.",
        evidence_turn_indexes=[1],
    )
