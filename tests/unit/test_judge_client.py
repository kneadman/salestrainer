from datetime import UTC, datetime
from uuid import uuid4

from app.domain.judgement_models import JudgeSessionInput, JudgeSessionOutput
from app.domain.models import ClientState, PersonaProfile, Scenario, TurnEvaluation
from app.infrastructure.judge_client import FakeJudgeClient


def _build_payload(*, heuristic: bool = True) -> JudgeSessionInput:
    """Create a compact judge input payload for fake client tests."""
    evaluations = []
    if heuristic:
        evaluations = [
            TurnEvaluation(
                turn_index=1,
                discovery_quality_score=4,
                role_identification_score=3,
                pain_identification_score=4,
                relevance_score=4,
                pressure_score=5,
                objection_handling_score=3,
                next_step_timing_score=4,
                conversation_control_score=4,
                notes=["Solid first turn."],
            )
        ]
    return JudgeSessionInput(
        scenario=Scenario(
            id="first_contact_discovery",
            name="Discovery",
            training_format="first_contact_discovery",
            default_starting_interest=25,
            default_stage="first_contact",
            manager_goal="Discover context.",
            success_condition="Earn a relevant next step.",
            failure_condition="Pitch too early.",
        ),
        persona=PersonaProfile(
            id="persona-1",
            display_name="Owner",
            role="owner",
            industry="b2b",
            company_size="30-100",
            authority_level="final_decider",
            behavior_model="skeptical_but_rational",
        ),
        final_client_state=ClientState(
            tone="interested",
            trust=45,
            irritation=10,
            urgency=25,
            price_sensitivity=50,
        ),
        conversation_summary="Manager discovered pain and moved the discussion forward.",
        turns=[
            {
                "turn_index": 1,
                "manager_message": "How does reporting work today?",
                "client_answer": "Mostly manually.",
                "interest_before": 25,
                "interest_delta": 5,
                "interest_after": 30,
                "stage_before": "first_contact",
                "stage_after": "qualification",
            },
            {
                "turn_index": 2,
                "manager_message": "Where does it slow you down most?",
                "client_answer": "At month end.",
                "interest_before": 30,
                "interest_delta": 8,
                "interest_after": 38,
                "stage_before": "qualification",
                "stage_after": "needs_analysis",
            },
        ],
        heuristic_evaluations=evaluations,
        final_interest_score=38,
        final_stage="needs_analysis",
        turn_count=2,
    )


def test_fake_judge_client_returns_judge_session_output() -> None:
    """Fake judge client should return the strict domain output model."""
    result = FakeJudgeClient().judge_session(_build_payload())

    assert isinstance(result, JudgeSessionOutput)


def test_fake_judge_client_keeps_overall_score_in_range() -> None:
    """Overall fake score should stay within the normalized 0..100 range."""
    result = FakeJudgeClient().judge_session(_build_payload())

    assert 0 <= result.overall_score <= 100


def test_fake_judge_client_maps_grade_from_score() -> None:
    """Overall grade should match the configured score bands."""
    result = FakeJudgeClient().judge_session(_build_payload(heuristic=False))

    assert result.overall_score == 38
    assert result.overall_grade == "weak"


def test_fake_judge_client_returns_non_empty_bento_blocks() -> None:
    """Fake judge client should always emit the minimum bento block set."""
    result = FakeJudgeClient().judge_session(_build_payload())

    assert result.bento_blocks


def test_fake_judge_client_returns_skill_scores_when_heuristics_exist() -> None:
    """Skill scores should be derived from heuristic evaluations when present."""
    result = FakeJudgeClient().judge_session(_build_payload())

    assert result.skill_scores


def test_fake_judge_client_uses_one_based_evidence_indexes() -> None:
    """Evidence indexes should remain one-based and point only to existing turns."""
    result = FakeJudgeClient().judge_session(_build_payload())

    existing_indexes = {1, 2}
    for block in result.bento_blocks:
        assert all(index >= 1 for index in block.evidence_turn_indexes)
        assert set(block.evidence_turn_indexes).issubset(existing_indexes)
