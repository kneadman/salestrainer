from datetime import UTC, datetime
from uuid import uuid4

from app.application.judgement_service import JudgementService
from app.domain.judgement_models import BentoReportBlock, JudgeSessionOutput, SkillScore, build_judge_input_from_session
from app.domain.models import ClientState, PersonaProfile, TrainingSessionState, Turn, TurnEvaluation
from tests.unit._persona_fixtures import valid_minimal_persona


class SpyJudgeClient:
    def __init__(self) -> None:
        """Store the last payload and return a stable output for assertions."""
        self.last_payload = None

    def judge_session(self, payload):
        """Capture the payload and return a deterministic output model."""
        self.last_payload = payload
        return JudgeSessionOutput(
            overall_score=72,
            overall_grade="good",
            outcome="Solid result.",
            executive_summary="The fake spy client received a valid payload.",
            bento_blocks=[
                BentoReportBlock(
                    id="summary",
                    title="Итог",
                    type="summary",
                    severity="neutral",
                    short_text="Краткий итог.",
                    detail="Подробный итог.",
                    evidence_turn_indexes=[1],
                )
            ],
            skill_scores=[
                SkillScore(
                    id="discovery_quality",
                    title="Discovery quality",
                    score=72,
                    severity="green",
                    explanation="Навык проявлен на хорошем уровне.",
                    evidence_turn_indexes=[1],
                )
            ],
            final_verdict="Stable test verdict.",
        )


def _build_session_state() -> TrainingSessionState:
    """Create a compact session fixture for judgement service tests."""
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
            )
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
        turn_count=1,
        state_version=3,
        created_at=now,
        updated_at=now,
    )


def test_judgement_service_calls_client_and_returns_output() -> None:
    """Judgement service should delegate to the client and return its output."""
    spy_client = SpyJudgeClient()
    service = JudgementService(spy_client)

    result = service.judge_session(_build_session_state())

    assert isinstance(result, JudgeSessionOutput)
    assert result.overall_score == 72
    assert spy_client.last_payload is not None


def test_judgement_service_uses_build_judge_input_from_session_correctly() -> None:
    """Judgement service should pass the same mapped payload as the helper builder."""
    session = _build_session_state()
    spy_client = SpyJudgeClient()
    service = JudgementService(spy_client)

    service.judge_session(session)

    assert spy_client.last_payload == build_judge_input_from_session(session)
