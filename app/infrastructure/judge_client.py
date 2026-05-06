from __future__ import annotations

import json
import logging
from json import JSONDecodeError
from typing import Any, Callable, Protocol

from pydantic import ValidationError

from app.domain.errors import LLMProviderConfigurationError
from app.domain.judgement_models import (
    BentoReportBlock,
    JudgeSessionInput,
    JudgeSessionOutput,
    JudgementGrade,
    JudgementSeverity,
    ReportFinding,
    ReportRecommendation,
    SkillScore,
)
from app.domain.models import TurnEvaluation
from app.infrastructure.config import Settings
from app.infrastructure.llm_client import (
    LLMClientError,
    _extract_json_object,
    _payload_size,
    _response_to_payload,
    _sanitize_api_key,
    _should_allow_fake_fallback,
)

logger = logging.getLogger(__name__)


class JudgeClient(Protocol):
    def judge_session(self, payload: JudgeSessionInput) -> JudgeSessionOutput:
        ...


Transport = Callable[[dict[str, Any]], Any]


class FakeJudgeClient:
    def judge_session(self, payload: JudgeSessionInput) -> JudgeSessionOutput:
        """Return a deterministic judgement result without any external LLM dependency."""
        overall_score = self._build_overall_score(payload)
        overall_grade = self._grade_for_score(overall_score)
        overall_severity = self._severity_for_score(overall_score)
        evidence_indexes = self._evidence_indexes(payload)
        skill_scores = self._build_skill_scores(payload)
        key_strengths = self._build_key_strengths(payload, skill_scores, overall_score)
        key_weaknesses = self._build_key_weaknesses(payload, skill_scores, overall_score)
        missed_opportunities = self._build_missed_opportunities(payload, skill_scores)
        recommendations = self._build_recommendations(skill_scores)
        bento_blocks = self._build_bento_blocks(
            payload=payload,
            overall_score=overall_score,
            overall_grade=overall_grade,
            overall_severity=overall_severity,
            key_strengths=key_strengths,
            key_weaknesses=key_weaknesses,
            recommendations=recommendations,
            evidence_indexes=evidence_indexes,
        )
        return JudgeSessionOutput(
            overall_score=overall_score,
            overall_grade=overall_grade,
            outcome=self._build_outcome(payload, overall_grade),
            executive_summary=self._build_executive_summary(payload, overall_score, overall_grade),
            bento_blocks=bento_blocks,
            skill_scores=skill_scores,
            key_strengths=key_strengths,
            key_weaknesses=key_weaknesses,
            missed_opportunities=missed_opportunities,
            recommendations=recommendations,
            final_verdict=self._build_final_verdict(payload, overall_score, overall_grade),
            risk_flags=self._build_risk_flags(payload, skill_scores),
        )

    def _build_overall_score(self, payload: JudgeSessionInput) -> int:
        """Average heuristic scores when available, otherwise fall back to final interest."""
        if not payload.heuristic_evaluations:
            return payload.final_interest_score
        score_values: list[int] = []
        for evaluation in payload.heuristic_evaluations:
            score_values.extend(self._evaluation_score_values(evaluation))
        average_score = sum(score_values) / len(score_values)
        return int(round((average_score / 5) * 100))

    def _build_skill_scores(self, payload: JudgeSessionInput) -> list[SkillScore]:
        """Project current heuristic dimensions into normalized 0..100 skill scores."""
        if not payload.heuristic_evaluations:
            return []
        skill_definitions = [
            ("discovery_quality", "Discovery quality", "discovery_quality_score"),
            ("role_identification", "Role identification", "role_identification_score"),
            ("pain_identification", "Pain identification", "pain_identification_score"),
            ("relevance", "Relevance", "relevance_score"),
            ("pressure_control", "Pressure control", "pressure_score"),
            ("objection_handling", "Objection handling", "objection_handling_score"),
            ("next_step_timing", "Next-step timing", "next_step_timing_score"),
            ("conversation_control", "Conversation control", "conversation_control_score"),
        ]
        evidence_indexes = self._evaluation_evidence_indexes(payload)
        skill_scores: list[SkillScore] = []
        for skill_id, title, field_name in skill_definitions:
            raw_average = sum(getattr(item, field_name) for item in payload.heuristic_evaluations) / len(
                payload.heuristic_evaluations
            )
            score = int(round((raw_average / 5) * 100))
            skill_scores.append(
                SkillScore(
                    id=skill_id,
                    title=title,
                    score=score,
                    severity=self._severity_for_score(score),
                    explanation=f"{title} is estimated from heuristic turn evaluations.",
                    evidence_turn_indexes=evidence_indexes,
                )
            )
        return skill_scores

    def _build_bento_blocks(
        self,
        *,
        payload: JudgeSessionInput,
        overall_score: int,
        overall_grade: JudgementGrade,
        overall_severity: JudgementSeverity,
        key_strengths: list[ReportFinding],
        key_weaknesses: list[ReportFinding],
        recommendations: list[ReportRecommendation],
        evidence_indexes: list[int],
    ) -> list[BentoReportBlock]:
        """Build a small deterministic bento set for future report rendering."""
        blocks = [
            BentoReportBlock(
                id="summary",
                title="Session summary",
                type="summary",
                severity="neutral",
                short_text=f"Finished at stage '{payload.final_stage}' after {payload.turn_count} turns.",
                detail=payload.conversation_summary or "Conversation summary is not available.",
                evidence_turn_indexes=evidence_indexes,
            ),
            BentoReportBlock(
                id="overall-score",
                title="Overall score",
                type="score",
                severity=overall_severity,
                score=overall_score,
                short_text=f"Overall result: {overall_score}/100.",
                detail=self._build_executive_summary(payload, overall_score, overall_grade),
                evidence_turn_indexes=evidence_indexes,
            ),
        ]
        if key_strengths:
            strength = key_strengths[0]
            blocks.append(
                BentoReportBlock(
                    id="top-strength",
                    title=strength.title,
                    type="strength",
                    severity="green",
                    short_text=strength.title,
                    detail=strength.description,
                    evidence_turn_indexes=strength.evidence_turn_indexes,
                )
            )
        else:
            weakness = key_weaknesses[0] if key_weaknesses else ReportFinding(
                title="Baseline weakness",
                description="The session needs more explicit evidence before a stronger verdict is possible.",
                evidence_turn_indexes=evidence_indexes,
                impact="medium",
            )
            blocks.append(
                BentoReportBlock(
                    id="top-weakness",
                    title=weakness.title,
                    type="weakness",
                    severity="red",
                    short_text=weakness.title,
                    detail=weakness.description,
                    evidence_turn_indexes=weakness.evidence_turn_indexes,
                )
            )
        recommendation = recommendations[0]
        blocks.append(
            BentoReportBlock(
                id="next-recommendation",
                title=recommendation.title,
                type="recommendation",
                severity="yellow",
                short_text=recommendation.title,
                detail=recommendation.description,
                evidence_turn_indexes=evidence_indexes,
            )
        )
        return blocks

    def _build_key_strengths(
        self,
        payload: JudgeSessionInput,
        skill_scores: list[SkillScore],
        overall_score: int,
    ) -> list[ReportFinding]:
        """Emit deterministic strengths from strong skill signals or session outcome."""
        evidence_indexes = self._evidence_indexes(payload)
        strengths = [
            ReportFinding(
                title=skill.title,
                description=f"{skill.title} stayed above the expected baseline in this session.",
                evidence_turn_indexes=skill.evidence_turn_indexes,
                impact="medium",
            )
            for skill in skill_scores
            if skill.score >= 70
        ]
        if strengths:
            return strengths[:2]
        if overall_score >= 70:
            return [
                ReportFinding(
                    title="Constructive session control",
                    description="The conversation ended with a generally constructive trajectory.",
                    evidence_turn_indexes=evidence_indexes,
                    impact="medium",
                )
            ]
        return []

    def _build_key_weaknesses(
        self,
        payload: JudgeSessionInput,
        skill_scores: list[SkillScore],
        overall_score: int,
    ) -> list[ReportFinding]:
        """Emit deterministic weaknesses from weak skill signals or low score fallback."""
        evidence_indexes = self._evidence_indexes(payload)
        weaknesses = [
            ReportFinding(
                title=skill.title,
                description=f"{skill.title} stayed below the expected baseline in this session.",
                evidence_turn_indexes=skill.evidence_turn_indexes,
                impact="high" if skill.score < 35 else "medium",
            )
            for skill in skill_scores
            if skill.score < 50
        ]
        if weaknesses:
            return weaknesses[:2]
        if overall_score < 50:
            return [
                ReportFinding(
                    title="Low overall session quality",
                    description="The final session outcome remained below the expected baseline.",
                    evidence_turn_indexes=evidence_indexes,
                    impact="high",
                )
            ]
        return []

    def _build_missed_opportunities(
        self,
        payload: JudgeSessionInput,
        skill_scores: list[SkillScore],
    ) -> list[ReportFinding]:
        """Flag missing discovery and next-step moves with simple deterministic rules."""
        evidence_indexes = self._evidence_indexes(payload)
        score_by_id = {skill.id: skill for skill in skill_scores}
        missed: list[ReportFinding] = []
        discovery = score_by_id.get("discovery_quality")
        if discovery is not None and discovery.score < 60:
            missed.append(
                ReportFinding(
                    title="Deeper discovery was available",
                    description="The manager could have explored the client's context more deeply before advancing.",
                    evidence_turn_indexes=evidence_indexes,
                    impact="medium",
                )
            )
        next_step = score_by_id.get("next_step_timing")
        if next_step is not None and next_step.score < 60:
            missed.append(
                ReportFinding(
                    title="Next step was not fully earned",
                    description="The conversation left room for a more clearly justified next step.",
                    evidence_turn_indexes=evidence_indexes,
                    impact="medium",
                )
            )
        return missed

    def _build_recommendations(self, skill_scores: list[SkillScore]) -> list[ReportRecommendation]:
        """Generate bounded next recommendations from the weakest current signals."""
        weakest = sorted(skill_scores, key=lambda item: item.score)[:2] if skill_scores else []
        if not weakest:
            return [
                ReportRecommendation(
                    title="Clarify the next question earlier",
                    description="Use the next turn to narrow the client's current process and pain more explicitly.",
                    example_phrase="How is this handled today, and where does it usually break first?",
                    priority="medium",
                )
            ]
        recommendations: list[ReportRecommendation] = []
        for skill in weakest:
            if skill.id == "discovery_quality":
                recommendations.append(
                    ReportRecommendation(
                        title="Ask narrower discovery questions",
                        description="Move from generic questions to concrete process and pain discovery.",
                        example_phrase="What part of the current process costs you the most time each month?",
                        priority="high",
                    )
                )
            elif skill.id == "role_identification":
                recommendations.append(
                    ReportRecommendation(
                        title="Clarify decision ownership",
                        description="Establish who owns the decision and who influences the next step.",
                        example_phrase="Who else is usually involved when you evaluate a change like this?",
                        priority="high",
                    )
                )
            elif skill.id == "pain_identification":
                recommendations.append(
                    ReportRecommendation(
                        title="Diagnose the pain before pitching",
                        description="Anchor the conversation in a concrete operational or business pain.",
                        example_phrase="What is the business impact when this issue happens?",
                        priority="high",
                    )
                )
            elif skill.id == "next_step_timing":
                recommendations.append(
                    ReportRecommendation(
                        title="Earn the next step later",
                        description="Advance only after the client context and decision criteria are clear enough.",
                        example_phrase="Before we discuss a next step, what would you need to see to consider it relevant?",
                        priority="medium",
                    )
                )
            else:
                recommendations.append(
                    ReportRecommendation(
                        title=f"Improve {skill.title.lower()}",
                        description=f"Raise {skill.title.lower()} with a more specific and contextual follow-up.",
                        example_phrase=None,
                        priority="medium",
                    )
                )
        return recommendations

    def _build_outcome(self, payload: JudgeSessionInput, overall_grade: JudgementGrade) -> str:
        """Summarize the session outcome in one bounded sentence."""
        return (
            f"Session ended at stage '{payload.final_stage}' after {payload.turn_count} turns "
            f"with a {overall_grade} judgement."
        )

    def _build_executive_summary(
        self,
        payload: JudgeSessionInput,
        overall_score: int,
        overall_grade: JudgementGrade,
    ) -> str:
        """Build a deterministic human-readable summary for the future bento report."""
        return (
            f"The session finished at stage '{payload.final_stage}' with overall score {overall_score}/100 "
            f"and grade '{overall_grade}'. Final client interest reached {payload.final_interest_score}/100."
        )

    def _build_final_verdict(
        self,
        payload: JudgeSessionInput,
        overall_score: int,
        overall_grade: JudgementGrade,
    ) -> str:
        """Produce a stable final verdict string."""
        return (
            f"Deterministic fake judgement: {overall_grade} result, score {overall_score}/100, "
            f"final stage '{payload.final_stage}', {payload.turn_count} turns processed."
        )

    def _build_risk_flags(self, payload: JudgeSessionInput, skill_scores: list[SkillScore]) -> list[str]:
        """Expose lightweight deterministic risk flags for future report use."""
        flags: list[str] = []
        if payload.turn_count == 0:
            flags.append("empty_dialogue")
        if payload.final_interest_score < 35:
            flags.append("low_final_interest")
        if any(skill.id == "pressure_control" and skill.score < 50 for skill in skill_scores):
            flags.append("pressure_risk")
        return flags

    def _evaluation_score_values(self, evaluation: TurnEvaluation) -> list[int]:
        """Return the normalized score fields that contribute to the fake overall score."""
        return [
            evaluation.discovery_quality_score,
            evaluation.role_identification_score,
            evaluation.pain_identification_score,
            evaluation.relevance_score,
            evaluation.pressure_score,
            evaluation.objection_handling_score,
            evaluation.next_step_timing_score,
            evaluation.conversation_control_score,
        ]

    def _evaluation_evidence_indexes(self, payload: JudgeSessionInput) -> list[int]:
        """Map heuristic turn indexes to existing 1-based turns only."""
        existing_indexes = {turn.turn_index for turn in payload.turns}
        evidence_indexes = [
            evaluation.turn_index
            for evaluation in payload.heuristic_evaluations
            if evaluation.turn_index in existing_indexes
        ]
        return evidence_indexes or self._evidence_indexes(payload)

    def _evidence_indexes(self, payload: JudgeSessionInput) -> list[int]:
        """Return all available existing 1-based turn indexes or an empty list."""
        return [turn.turn_index for turn in payload.turns]

    def _grade_for_score(self, score: int) -> JudgementGrade:
        """Map a normalized 0..100 score to the fixed qualitative grade bands."""
        if score <= 30:
            return "critical"
        if score <= 50:
            return "weak"
        if score <= 70:
            return "normal"
        if score <= 85:
            return "good"
        return "strong"

    def _severity_for_score(self, score: int) -> JudgementSeverity:
        """Map a normalized score to the fixed traffic-light severity."""
        if score >= 75:
            return "green"
        if score >= 50:
            return "yellow"
        return "red"


class StructuredJudgeClient:
    def __init__(
        self,
        *,
        provider: str,
        base_url: str,
        api_key: str,
        folder_id: str | None,
        agent_id: str | None,
        model_or_agent_label: str | None = None,
        timeout_seconds: int = 30,
        max_retries: int = 1,
        fallback_client: JudgeClient | None = None,
        transport: Transport | None = None,
        debug_payload_logging: bool = False,
    ) -> None:
        """Configure an OpenAI/Yandex-compatible structured judge client."""
        self._provider = provider
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._folder_id = folder_id
        self._agent_id = agent_id
        self._model_or_agent_label = model_or_agent_label
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._fallback_client = fallback_client
        self._transport = transport or self._default_transport
        self._debug_payload_logging = debug_payload_logging

    def judge_session(self, payload: JudgeSessionInput) -> JudgeSessionOutput:
        """Call the provider and validate its response as JudgeSessionOutput."""
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            retry_instruction = ""
            if attempt > 0:
                retry_instruction = (
                    "Previous answer failed backend validation. Return exactly one JudgeSessionOutput JSON object. "
                    "No markdown. No extra fields. Use existing 1-based turn indexes only."
                )
            request_payload = self._build_request_payload(payload, retry_instruction)
            metadata = self._safe_request_metadata(attempt=attempt + 1, request_payload=request_payload)
            logger.info("judge_request %s", metadata)
            if self._debug_payload_logging:
                logger.debug("judge_request_payload %s", request_payload)
            try:
                raw_response = _response_to_payload(self._transport(request_payload))
                return parse_judge_session_output(raw_response)
            except (LLMClientError, ValidationError, JSONDecodeError, TimeoutError) as error:
                last_error = error
                logger.warning("judge_request_failed attempt=%s error=%s", attempt + 1, error)
            except Exception as error:
                last_error = error
                logger.warning(
                    "judge_http_error attempt=%s status=%s error=%s",
                    attempt + 1,
                    getattr(error, "status_code", None),
                    error,
                )
        if self._fallback_client is not None:
            logger.warning("judge_fallback_to_fake reason=%s", last_error)
            return self._fallback_client.judge_session(payload)
        raise LLMClientError(f"Judge request failed after retries: {last_error}") from last_error

    def _build_request_payload(self, payload: JudgeSessionInput, retry_instruction: str) -> dict[str, Any]:
        """Build a provider request that carries the strict JudgeSessionOutput schema."""
        snapshot = payload.model_dump(mode="json")
        if retry_instruction:
            snapshot["retry_instruction"] = retry_instruction
        request_payload: dict[str, Any] = {
            "input": json.dumps(snapshot, ensure_ascii=False),
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "judge_session_output",
                    "schema": JudgeSessionOutput.model_json_schema(),
                    "strict": True,
                }
            },
        }
        if self._agent_id:
            request_payload["prompt"] = {"id": self._agent_id}
        else:
            request_payload["model"] = self._model_or_agent_label or "gpt-4.1-mini"
        return request_payload

    def _safe_request_metadata(self, *, attempt: int, request_payload: dict[str, Any]) -> dict[str, object]:
        """Log only routing metadata and payload sizes, never raw persona data or API keys."""
        return {
            "provider": self._provider,
            "attempt": attempt,
            "endpoint_url": self.endpoint_url,
            "api_key": _sanitize_api_key(self._api_key),
            "folder_id_present": bool(self._folder_id),
            "agent_id_present": bool(self._agent_id),
            "payload_size": _payload_size(request_payload),
        }

    def _default_transport(self, request_payload: dict[str, Any]) -> Any:
        """Execute the responses API call through the optional OpenAI-compatible SDK."""
        try:
            from openai import OpenAI
        except ImportError as error:
            raise LLMClientError("openai package is required for judge providers.") from error

        client = OpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
            project=self._folder_id,
            timeout=self._timeout_seconds,
        )
        return client.responses.create(**request_payload)

    @property
    def endpoint_url(self) -> str:
        """Return the provider endpoint used for sanitized request metadata."""
        return f"{self._base_url}/responses"


def parse_judge_session_output(raw_payload: dict[str, Any] | str) -> JudgeSessionOutput:
    """Parse known provider response envelopes into a strict JudgeSessionOutput."""
    if isinstance(raw_payload, dict) and "overall_score" in raw_payload:
        return JudgeSessionOutput.model_validate(raw_payload)
    if isinstance(raw_payload, dict):
        output_text = raw_payload.get("output_text")
        if isinstance(output_text, str):
            return JudgeSessionOutput.model_validate_json(_extract_json_object(output_text))
        output = raw_payload.get("output")
        if isinstance(output, list):
            for item in output:
                if not isinstance(item, dict):
                    continue
                content = item.get("content")
                if isinstance(content, list):
                    for chunk in content:
                        if not isinstance(chunk, dict):
                            continue
                        text = chunk.get("text")
                        if isinstance(text, str):
                            return JudgeSessionOutput.model_validate_json(_extract_json_object(text))
        alternatives = raw_payload.get("alternatives")
        if isinstance(alternatives, list) and alternatives:
            message = alternatives[0].get("message", {})
            text = message.get("text")
            if isinstance(text, str):
                return JudgeSessionOutput.model_validate_json(_extract_json_object(text))
        raise LLMClientError("Judge provider response does not contain structured text output.")
    try:
        decoded = json.loads(raw_payload)
    except JSONDecodeError:
        return JudgeSessionOutput.model_validate_json(_extract_json_object(raw_payload))
    return parse_judge_session_output(decoded)


def build_judge_client(settings: Settings) -> JudgeClient:
    """Build the configured judge client while preserving fake fallback behavior."""
    backend = settings.llm_backend.lower().strip()
    if backend == "fake":
        return FakeJudgeClient()
    if backend == "yandex_compatible":
        folder_id = settings.yandex_judge_folder_id or settings.yandex_folder_id
        agent_id = settings.yandex_judge_agent_id or settings.yandex_agent_id
        if not all([settings.yandex_api_key, folder_id, agent_id]):
            if _should_allow_fake_fallback(settings):
                logger.warning("judge_backend_incomplete_config backend=%s fallback=fake", backend)
                return FakeJudgeClient()
            raise LLMProviderConfigurationError(
                "Incomplete Yandex judge configuration and fake fallback is disabled."
            )
        return StructuredJudgeClient(
            provider="yandex_compatible",
            base_url=settings.yandex_base_url,
            api_key=settings.yandex_api_key,
            folder_id=folder_id,
            agent_id=agent_id,
            timeout_seconds=settings.llm_request_timeout_seconds,
            max_retries=1,
            fallback_client=FakeJudgeClient() if _should_allow_fake_fallback(settings) else None,
            debug_payload_logging=settings.debug_llm_payload,
        )
    if _should_allow_fake_fallback(settings):
        logger.warning("judge_backend_unknown backend=%s fallback=fake", settings.llm_backend)
        return FakeJudgeClient()
    raise LLMProviderConfigurationError(
        f"Unknown llm_backend '{settings.llm_backend}' and fake fallback is disabled."
    )
