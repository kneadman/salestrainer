from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.models import ClientState, PersonaProfile, Scenario, TrainingSessionState, TurnEvaluation
from app.domain.scenarios import get_scenario


JudgementSeverity = Literal["green", "yellow", "red", "neutral"]
JudgementGrade = Literal["critical", "weak", "normal", "good", "strong"]
FindingImpact = Literal["low", "medium", "high"]
BentoBlockType = Literal[
    "summary",
    "score",
    "strength",
    "weakness",
    "missed_context",
    "recommendation",
    "timeline",
    "next_step",
]


class JudgeTurnInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    turn_index: int = Field(ge=1)
    manager_message: str
    client_answer: str
    interest_before: int = Field(ge=0, le=100)
    interest_delta: int = Field(ge=-15, le=15)
    interest_after: int = Field(ge=0, le=100)
    stage_before: str
    stage_after: str


class JudgeSessionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task: Literal["judge_training_session"] = "judge_training_session"
    schema_version: Literal[1] = 1
    scenario: Scenario
    persona: PersonaProfile
    final_client_state: ClientState
    conversation_summary: str
    turns: list[JudgeTurnInput]
    heuristic_evaluations: list[TurnEvaluation] = Field(default_factory=list)
    final_interest_score: int = Field(ge=0, le=100)
    final_stage: str
    turn_count: int = Field(ge=0)


class BentoReportBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=160)
    type: BentoBlockType
    severity: JudgementSeverity
    score: int | None = Field(default=None, ge=0, le=100)
    short_text: str = Field(min_length=1, max_length=280)
    detail: str = Field(min_length=1, max_length=1200)
    evidence_turn_indexes: list[int] = Field(default_factory=list)


class SkillScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=160)
    score: int = Field(ge=0, le=100)
    severity: JudgementSeverity
    explanation: str = Field(min_length=1, max_length=1000)
    evidence_turn_indexes: list[int] = Field(default_factory=list)


class ReportFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=1000)
    evidence_turn_indexes: list[int] = Field(default_factory=list)
    impact: FindingImpact


class ReportRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=1000)
    example_phrase: str | None = Field(default=None, max_length=500)
    priority: FindingImpact


class JudgeSessionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    overall_score: int = Field(ge=0, le=100)
    overall_grade: JudgementGrade
    outcome: str = Field(min_length=1, max_length=240)
    executive_summary: str = Field(min_length=1, max_length=1200)
    bento_blocks: list[BentoReportBlock]
    skill_scores: list[SkillScore]
    key_strengths: list[ReportFinding] = Field(default_factory=list)
    key_weaknesses: list[ReportFinding] = Field(default_factory=list)
    missed_opportunities: list[ReportFinding] = Field(default_factory=list)
    recommendations: list[ReportRecommendation] = Field(default_factory=list)
    final_verdict: str = Field(min_length=1, max_length=1200)
    risk_flags: list[str] = Field(default_factory=list)


def build_judge_input_from_session(session: TrainingSessionState) -> JudgeSessionInput:
    """Build strict judge input from canonical training session state."""
    return JudgeSessionInput(
        scenario=get_scenario(session.scenario_id),
        persona=session.persona,
        final_client_state=session.client_state,
        conversation_summary=session.summary,
        turns=[
            JudgeTurnInput(
                turn_index=turn.index,
                manager_message=turn.manager_message,
                client_answer=turn.client_answer,
                interest_before=turn.interest_before,
                interest_delta=turn.interest_delta,
                interest_after=turn.interest_after,
                stage_before=turn.stage_before,
                stage_after=turn.stage_after,
            )
            for turn in session.turns
        ],
        heuristic_evaluations=session.turn_evaluations,
        final_interest_score=session.interest_score,
        final_stage=session.stage,
        turn_count=session.turn_count,
    )
