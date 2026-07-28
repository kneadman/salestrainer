from __future__ import annotations

import json
import logging
from json import JSONDecodeError
from typing import Any, Protocol

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
from app.domain.token_counter import TokenCountedResult, TokenCounterService
from app.infrastructure.config import Settings
from app.infrastructure.responses_client import (
    LLMClientError,
    OpenAICompatibleResponsesClient,
    Transport,
    _payload_size,
    _response_to_payload,
    _sanitize_api_key,
    parse_enveloped_json_output,
)
from app.infrastructure.config import is_fake_fallback_allowed

logger = logging.getLogger(__name__)


class JudgeClient(Protocol):
    def judge_session(self, payload: JudgeSessionInput) -> TokenCountedResult[JudgeSessionOutput]:
        ...



class JudgeOutputValidationError(ValueError):
    """Raised when a structured judge output violates backend-level contract rules."""


def validate_judge_output(output: JudgeSessionOutput, input_payload: JudgeSessionInput) -> JudgeSessionOutput:
    """Reject judge outputs that reference non-existent 1-based turn indexes."""
    valid_turn_indexes = {turn.turn_index for turn in input_payload.turns}
    for block in output.bento_blocks:
        _validate_evidence_indexes(
            block.evidence_turn_indexes,
            valid_turn_indexes,
            location=f"bento_blocks[{block.id}]",
        )
    for skill in output.skill_scores:
        _validate_evidence_indexes(
            skill.evidence_turn_indexes,
            valid_turn_indexes,
            location=f"skill_scores[{skill.id}]",
        )
    for collection_name, findings in [
        ("key_strengths", output.key_strengths),
        ("key_weaknesses", output.key_weaknesses),
        ("missed_opportunities", output.missed_opportunities),
    ]:
        for index, finding in enumerate(findings):
            _validate_evidence_indexes(
                finding.evidence_turn_indexes,
                valid_turn_indexes,
                location=f"{collection_name}[{index}]",
            )
    return output


def _validate_evidence_indexes(indexes: list[int], valid_turn_indexes: set[int], *, location: str) -> None:
    """Ensure every evidence turn index points to an existing input turn."""
    invalid_indexes = [index for index in indexes if index not in valid_turn_indexes]
    if invalid_indexes:
        raise JudgeOutputValidationError(
            f"Invalid evidence_turn_indexes in {location}: {invalid_indexes}"
        )


class FakeJudgeClient:
    def __init__(self, token_counter: TokenCounterService | None = None) -> None:
        self._token_counter = token_counter or TokenCounterService()

    def judge_session(self, payload: JudgeSessionInput) -> TokenCountedResult[JudgeSessionOutput]:
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
        output = JudgeSessionOutput(
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
        result = validate_judge_output(output, payload)
        input_tokens = self._token_counter.count_json(payload.model_dump(mode="json"))
        output_tokens = self._token_counter.count_json(result.model_dump(mode="json"))
        return TokenCountedResult(value=result, input_tokens=input_tokens, output_tokens=output_tokens)

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
        skill_definitions = [
            ("discovery_quality", "Качество диагностики", "discovery_quality_score"),
            ("role_identification", "Выявление роли", "role_identification_score"),
            ("pain_identification", "Выявление боли", "pain_identification_score"),
            ("relevance", "Релевантность", "relevance_score"),
            ("pressure_control", "Контроль давления", "pressure_score"),
            ("objection_handling", "Работа с возражениями", "objection_handling_score"),
            ("next_step_timing", "Тайминг следующего шага", "next_step_timing_score"),
            ("conversation_control", "Контроль диалога", "conversation_control_score"),
        ]
        evidence_indexes = self._evaluation_evidence_indexes(payload)
        skill_scores: list[SkillScore] = []
        for skill_id, title, field_name in skill_definitions:
            if payload.heuristic_evaluations:
                raw_average = sum(getattr(item, field_name) for item in payload.heuristic_evaluations) / len(
                    payload.heuristic_evaluations
                )
                score = int(round((raw_average / 5) * 100))
            else:
                score = payload.final_interest_score
            skill_scores.append(
                SkillScore(
                    id=skill_id,
                    title=title,
                    score=score,
                    severity=self._severity_for_score(score),
                    explanation=f"{title} оценено по эвристическим оценкам отдельных ходов.",
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
                title="Итог сессии",
                type="summary",
                severity="neutral",
                short_text=f"Сессия завершилась на этапе «{payload.final_stage}» после {payload.turn_count} ходов.",
                detail=payload.conversation_summary or "Краткая сводка по разговору недоступна.",
                evidence_turn_indexes=evidence_indexes,
            ),
            BentoReportBlock(
                id="overall-score",
                title="Общая оценка",
                type="score",
                severity=overall_severity,
                score=overall_score,
                short_text=f"Итоговый результат: {overall_score}/100.",
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
                title="Зона для усиления",
                description="Для более сильного вердикта в сессии не хватило убедительных подтверждений.",
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
                description=f"По этой сессии навык «{skill.title}» оказался выше ожидаемого базового уровня.",
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
                    title="Конструктивный ход разговора",
                    description="Разговор завершился по в целом конструктивной траектории.",
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
                description=f"По этой сессии навык «{skill.title}» оказался ниже ожидаемого базового уровня.",
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
                    title="Низкое итоговое качество сессии",
                    description="Финальный результат сессии остался ниже ожидаемого базового уровня.",
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
                    title="Можно было углубить диагностику",
                    description="Перед продвижением разговора менеджер мог глубже раскрыть контекст клиента.",
                    evidence_turn_indexes=evidence_indexes,
                    impact="medium",
                )
            )
        next_step = score_by_id.get("next_step_timing")
        if next_step is not None and next_step.score < 60:
            missed.append(
                ReportFinding(
                    title="Следующий шаг был подготовлен не полностью",
                    description="В разговоре осталось пространство для более обоснованного следующего шага.",
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
                    title="Быстрее уточнить следующий вопрос",
                    description="В следующем ходе стоит точнее сузить текущий процесс клиента и его боль.",
                    example_phrase="Как это устроено у вас сейчас и где обычно возникает первый сбой?",
                    priority="medium",
                )
            ]
        recommendations: list[ReportRecommendation] = []
        for skill in weakest:
            if skill.id == "discovery_quality":
                recommendations.append(
                    ReportRecommendation(
                        title="Задавать более точные диагностические вопросы",
                        description="Нужно перейти от общих вопросов к конкретике по процессу и боли клиента.",
                        example_phrase="Какой участок текущего процесса забирает у вас больше всего времени каждый месяц?",
                        priority="high",
                    )
                )
            elif skill.id == "role_identification":
                recommendations.append(
                    ReportRecommendation(
                        title="Уточнить владельца решения",
                        description="Нужно понять, кто принимает решение и кто влияет на следующий шаг.",
                        example_phrase="Кто ещё обычно участвует у вас в оценке такого изменения?",
                        priority="high",
                    )
                )
            elif skill.id == "pain_identification":
                recommendations.append(
                    ReportRecommendation(
                        title="Сначала диагностировать боль, потом предлагать",
                        description="Разговор стоит опереть на конкретную операционную или бизнес-боль клиента.",
                        example_phrase="Во что для бизнеса выливается эта проблема, когда она возникает?",
                        priority="high",
                    )
                )
            elif skill.id == "next_step_timing":
                recommendations.append(
                    ReportRecommendation(
                        title="Чуть позже переходить к следующему шагу",
                        description="К следующему шагу лучше переходить после прояснения контекста и критериев решения.",
                        example_phrase="Прежде чем обсуждать следующий шаг, что вам нужно понять, чтобы он был уместен?",
                        priority="medium",
                    )
                )
            else:
                recommendations.append(
                    ReportRecommendation(
                        title=f"Усилить навык «{skill.title.lower()}»",
                        description=f"Этот навык можно поднять более точным и контекстным уточняющим вопросом.",
                        example_phrase=None,
                        priority="medium",
                    )
                )
        return recommendations

    def _build_outcome(self, payload: JudgeSessionInput, overall_grade: JudgementGrade) -> str:
        """Summarize the session outcome in one bounded sentence."""
        return (
            f"Сессия завершилась на этапе «{payload.final_stage}» после {payload.turn_count} ходов "
            f"с итоговой оценкой уровня «{overall_grade}»."
        )

    def _build_executive_summary(
        self,
        payload: JudgeSessionInput,
        overall_score: int,
        overall_grade: JudgementGrade,
    ) -> str:
        """Build a deterministic human-readable summary for the future bento report."""
        return (
            f"Сессия завершилась на этапе «{payload.final_stage}» с общей оценкой {overall_score}/100 "
            f"и уровнем «{overall_grade}». Финальный интерес клиента составил {payload.final_interest_score}/100."
        )

    def _build_final_verdict(
        self,
        payload: JudgeSessionInput,
        overall_score: int,
        overall_grade: JudgementGrade,
    ) -> str:
        """Produce a stable final verdict string."""
        return (
            f"Итоговая оценка: уровень «{overall_grade}», оценка {overall_score}/100, "
            f"финальный этап «{payload.final_stage}», обработано ходов: {payload.turn_count}."
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


class StructuredJudgeClient(OpenAICompatibleResponsesClient):
    _openai_missing_message = "openai package is required for judge providers."

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
        token_counter: TokenCounterService | None = None,
    ) -> None:
        """Configure an OpenAI/Yandex-compatible structured judge client."""
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            folder_id=folder_id,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            transport=transport,
            debug_payload_logging=debug_payload_logging,
        )
        self._provider = provider
        self._agent_id = agent_id
        self._model_or_agent_label = model_or_agent_label
        self._fallback_client = fallback_client
        self._token_counter = token_counter or TokenCounterService()

    def judge_session(self, payload: JudgeSessionInput) -> TokenCountedResult[JudgeSessionOutput]:
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
                output = parse_judge_session_output(raw_response)
                result = validate_judge_output(output, payload)
                input_tokens = self._token_counter.count_string(request_payload.get("input", ""))
                output_tokens = self._token_counter.count_json(result.model_dump(mode="json"))
                return TokenCountedResult(value=result, input_tokens=input_tokens, output_tokens=output_tokens)
            except (JudgeOutputValidationError, LLMClientError, ValidationError, JSONDecodeError, TimeoutError) as error:
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

def parse_judge_session_output(raw_payload: dict[str, Any] | str) -> JudgeSessionOutput:
    """Parse known provider response envelopes into a strict JudgeSessionOutput."""
    return parse_enveloped_json_output(
        raw_payload,
        model=JudgeSessionOutput,
        direct_key="overall_score",
        no_output_message="Judge provider response does not contain structured text output.",
    )


def build_judge_client(settings: Settings) -> JudgeClient:
    """Build the configured judge client while preserving fake fallback behavior."""
    backend = settings.llm_backend.lower().strip()
    if backend == "fake":
        return FakeJudgeClient()
    if backend == "yandex_compatible":
        folder_id = settings.yandex_judge_folder_id or settings.yandex_folder_id
        agent_id = settings.yandex_judge_agent_id or settings.yandex_agent_id
        if not all([settings.yandex_api_key, folder_id, agent_id]):
            if is_fake_fallback_allowed(settings):
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
            fallback_client=FakeJudgeClient() if is_fake_fallback_allowed(settings) else None,
            debug_payload_logging=settings.debug_llm_payload,
        )
    if is_fake_fallback_allowed(settings):
        logger.warning("judge_backend_unknown backend=%s fallback=fake", settings.llm_backend)
        return FakeJudgeClient()
    raise LLMProviderConfigurationError(
        f"Unknown llm_backend '{settings.llm_backend}' and fake fallback is disabled."
    )
