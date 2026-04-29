from __future__ import annotations

import json
import logging
from json import JSONDecodeError
import re
from typing import Any, Callable, Protocol

from pydantic import ValidationError

from app.domain.errors import LLMProviderConfigurationError
from app.domain.interest import interest_band
from app.domain.models import LLMTurnInput, LLMTurnResponse, StatePatch
from app.infrastructure.config import Settings
from app.infrastructure.fake_llm_client import FakeLLMClient as CleanFakeLLMClient
from app.prompts.schemas import llm_turn_response_schema_json

logger = logging.getLogger(__name__)


class LLMClient(Protocol):
    def generate_client_turn(self, payload: LLMTurnInput) -> LLMTurnResponse:
        ...


class LLMClientError(RuntimeError):
    """Raised when the external LLM client cannot produce a valid structured response."""


def _sanitize_api_key(api_key: str) -> str:
    if not api_key:
        return ""
    if len(api_key) <= 6:
        return "***"
    return f"{api_key[:4]}...{api_key[-2:]}"


def _payload_size(value: Any) -> int:
    try:
        return len(json.dumps(value, ensure_ascii=False))
    except (TypeError, ValueError):
        return len(str(value))


def _safe_request_metadata(
    *,
    provider: str,
    endpoint_url: str,
    api_key: str,
    project_id: str,
    prompt_id: str,
    attempt: int,
    request_payload: dict[str, Any],
) -> dict[str, Any]:
    input_payload = request_payload.get("input", "")
    return {
        "provider": provider,
        "attempt": attempt,
        "endpoint_url": endpoint_url,
        "api_key": _sanitize_api_key(api_key),
        "project_id": project_id,
        "prompt_id": prompt_id,
        "payload_size": _payload_size(request_payload),
        "input_size": _payload_size(input_payload),
    }


def _should_allow_fake_fallback(settings: Settings) -> bool:
    return settings.allow_fake_llm_fallback or settings.is_local_env


def _response_to_payload(response: Any) -> dict[str, Any] | str:
    if isinstance(response, (dict, str)):
        return response
    model_dump = getattr(response, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        if isinstance(dumped, dict):
            return dumped
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str):
        return {"output_text": output_text}
    raise LLMClientError("Provider response cannot be converted to a structured payload.")


def _extract_json_object(raw_text: str) -> str:
    for candidate in _json_candidates(raw_text):
        try:
            json.loads(candidate)
            return candidate
        except JSONDecodeError:
            continue
    raise JSONDecodeError("No valid JSON object found", raw_text, 0)


def _json_candidates(raw_text: str) -> list[str]:
    candidates: list[str] = []
    stripped = raw_text.strip()
    if stripped:
        candidates.append(stripped)
    for fenced in re.findall(r"```(?:json)?\s*(.*?)```", raw_text, flags=re.IGNORECASE | re.DOTALL):
        fenced_text = fenced.strip()
        if fenced_text:
            candidates.append(fenced_text)
    extracted = _find_json_object_substring(raw_text)
    if extracted:
        candidates.append(extracted)
    for fenced in re.findall(r"```(?:json)?\s*(.*?)```", raw_text, flags=re.IGNORECASE | re.DOTALL):
        extracted_fenced = _find_json_object_substring(fenced)
        if extracted_fenced:
            candidates.append(extracted_fenced)
    return candidates


def _find_json_object_substring(raw_text: str) -> str | None:
    start: int | None = None
    depth = 0
    in_string = False
    escape = False

    for index, char in enumerate(raw_text):
        if start is None:
            if char == "{":
                start = index
                depth = 1
                in_string = False
                escape = False
            continue

        if escape:
            escape = False
            continue
        if char == "\\" and in_string:
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
            continue
        if char == "}":
            depth -= 1
            if depth == 0:
                return raw_text[start : index + 1].strip()
    return None


def parse_llm_turn_response(raw_payload: dict[str, Any] | str) -> LLMTurnResponse:
    if isinstance(raw_payload, dict) and "answer" in raw_payload:
        return LLMTurnResponse.model_validate(raw_payload)
    if isinstance(raw_payload, dict):
        output_text = raw_payload.get("output_text")
        if isinstance(output_text, str):
            return LLMTurnResponse.model_validate_json(_extract_json_object(output_text))
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
                            return LLMTurnResponse.model_validate_json(_extract_json_object(text))
        alternatives = raw_payload.get("alternatives")
        if isinstance(alternatives, list) and alternatives:
            message = alternatives[0].get("message", {})
            text = message.get("text")
            if isinstance(text, str):
                return LLMTurnResponse.model_validate_json(_extract_json_object(text))
        raise LLMClientError("Provider response does not contain structured text output.")
    try:
        decoded = json.loads(raw_payload)
    except JSONDecodeError:
        try:
            return LLMTurnResponse.model_validate_json(_extract_json_object(raw_payload))
        except JSONDecodeError as error:
            raise LLMClientError("Provider response does not contain valid JSON.") from error
    return parse_llm_turn_response(decoded)


class FakeLLMClient:
    def generate_client_turn(self, payload: LLMTurnInput) -> LLMTurnResponse:
        message = payload.manager_message.strip()
        message_lower = message.lower()
        profile = payload.hidden_profile
        discovered = payload.discovered_facts
        current_interest = int(payload.current_state["interest_score"])
        delta = self._score_message(message_lower, profile)
        next_interest = max(0, min(100, current_interest + delta))
        band = interest_band(next_interest)
        stage = self._choose_stage(
            message_lower,
            current_stage=str(payload.current_state["stage"]),
            next_interest=next_interest,
            discovered=discovered,
        )
        answer = self._build_answer(band, stage, payload)
        patch = self._build_patch(message_lower, band, profile, discovered)
        notes = self._build_notes(delta, band, message)
        return LLMTurnResponse(
            answer=answer,
            interest_delta=delta,
            state_patch=patch,
            stage=stage,
            internal_notes=notes,
        )

    def _score_message(self, message_lower: str, profile) -> int:
        score = 0
        if len(message_lower) < 12:
            score -= 4
        if "?" in message_lower:
            score += 4
        if any(
            token in message_lower
            for token in [
                "кто вы",
                "ваша роль",
                "за что отвечаете",
                "как сейчас устроено",
                "какая проблема",
                "что болит",
                "болит",
                "проблем",
                "воронка",
                "продажи",
                "бухгалтерия",
                "финансы",
                "заявки",
                "лиды",
                "потери",
                "контроль",
                "diagnostic",
                "conversion",
                "funnel",
                "loss",
                "problem",
            ]
        ):
            score += 3
        if any(token in message_lower for token in ["you must", "buy", "urgent offer", "only today", "купите", "срочно", "только сегодня"]):
            score -= 6
        if any(token in message_lower for token in ["price", "cost", "roi", "result", "стоимость", "цена", "окупаемость", "результат"]):
            score += 2
        if any(token in message_lower for token in profile.industry.lower().split("_")):
            score += 1
        return max(-15, min(15, score))

    def _choose_stage(self, message_lower: str, current_stage: str, next_interest: int, discovered: dict[str, Any]) -> str:
        if any(token in message_lower for token in ["кто вы", "ваша роль", "за что отвечаете"]):
            return "role_discovery"
        if next_interest >= 75 and "?" in message_lower and discovered.get("role") and discovered.get("pains"):
            return "next_step_negotiation"
        if any(token in message_lower for token in ["why", "how", "problem", "loss", "как", "почему", "что болит", "болит", "какая проблема", "проблем"]):
            return "need_discovery"
        if any(token in message_lower for token in ["example", "result", "roi", "diagnostic", "результат", "окупаемость", "эффект"]):
            return "value_clarification"
        return current_stage

    def _build_answer(self, band: str, stage: str, payload: LLMTurnInput) -> str:
        profile = payload.hidden_profile
        discovered = payload.discovered_facts
        if any(token in payload.manager_message.lower() for token in ["кто вы", "ваша роль", "за что отвечаете"]):
            return self._role_answer(profile, discovered)
        if any(token in payload.manager_message.lower() for token in ["как сейчас устроено", "что происходит", "как работает", "воронка", "процесс"]):
            return profile.current_business_context[:180]
        if any(token in payload.manager_message.lower() for token in ["какая проблема", "что болит", "болит", "где потери", "что мешает", "проблем"]):
            return profile.latent_pains[0]
        if any(token in payload.manager_message.lower() for token in ["кто принимает решение", "кто согласует", "есть ли полномочия"]):
            return self._authority_answer(profile)
        if any(token in payload.manager_message.lower() for token in ["цена", "стоимость", "окупаемость", "результат"]):
            return "Сначала хочу понять, в чем конкретно для нас будет ценность."
        if band == "cold":
            return "Пока звучит слишком общо. Уточните, что именно вы хотите понять."
        if band == "skeptical":
            return "Сформулируйте короче и привяжите к нашей ситуации."
        if band == "neutral":
            return "Допустим. Какие данные вам обычно нужны, чтобы понять ситуацию?"
        if band == "warm":
            return "Уже ближе к делу. Если быстро поймете контекст, что предложите как следующий шаг?"
        return "Ок. Тогда покажите, как вы обычно переводите это в конкретный следующий шаг."

    def _role_answer(self, profile, discovered: dict[str, Any]) -> str:
        if discovered.get("role") == profile.role:
            return "Я уже сказал, что отвечаю за этот блок."
        answers = {
            "owner": "Я собственник, отвечаю за ключевые решения и финансовый результат.",
            "founder": "Я основатель компании, держу в фокусе рост и управляемость.",
            "ceo": "Я CEO, отвечаю за общий результат и ключевые управленческие решения.",
            "general_director": "Я генеральный директор, отвечаю за операционное управление и результат.",
            "managing_partner": "Я управляющий партнёр, отвечаю за развитие и качество управления.",
            "commercial_director": "Я коммерческий директор, отвечаю за продажи, маржу и выполнение плана.",
            "cfo": "Я финансовый директор, отвечаю за цифры, денежный поток и финансовую прозрачность.",
            "chief_accountant": "Я главный бухгалтер, отвечаю за учёт, отчётность и налоговые риски.",
            "operations_director": "Я операционный директор, отвечаю за процессы и устойчивость работы.",
            "sales_director": "Я руководитель отдела продаж, отвечаю за воронку, менеджеров и план.",
            "purchase_manager": "Я отвечаю за выбор подрядчиков и первичную оценку предложений.",
        }
        return answers.get(profile.role, "Я отвечаю за часть управленческих решений в компании.")

    def _authority_answer(self, profile) -> str:
        return {
            "final_decider": "Финальное решение могу принять сам, если вижу смысл.",
            "influencer": "Я влияю на решение, но финально нужен еще другой участник.",
            "gatekeeper": "Сначала мне нужно понять релевантность, потом могу передать дальше.",
            "evaluator": "Я оцениваю экономику и риски, финальное решение не только за мной.",
        }[profile.authority_level]

    def _build_patch(self, message_lower: str, band: str, profile, discovered: dict[str, Any]) -> StatePatch:
        add_open_objections: list[str] = []
        remove_open_objections: list[str] = []
        known_pains: list[str] = []
        buying_signals: list[str] = []
        red_flags: list[str] = []
        discovered_pains: list[str] = []
        decision_criteria: list[str] = []
        constraints: list[str] = []
        current_process: list[str] = []
        trust_delta = 0
        irritation_delta = 0
        urgency_delta = 0
        tone = None
        discovered_role = None
        discovered_authority_level = None

        if "?" in message_lower:
            trust_delta += 3
            irritation_delta -= 1
            known_pains.append("Manager asked a diagnostic question instead of generic pitching.")
        if any(token in message_lower for token in ["conversion", "loss", "funnel", "diagnostic", "воронка", "потери", "как сейчас устроено"]):
            trust_delta += 2
            urgency_delta += 1
            remove_open_objections.append("I do not see why this is necessary.")
        if any(token in message_lower for token in ["buy", "must", "only today", "купите", "срочно", "только сегодня"]):
            irritation_delta += 4
            red_flags.append("Manager became pushy.")
        if any(token in message_lower for token in ["кто вы", "ваша роль", "за что отвечаете"]):
            discovered_role = profile.role
            trust_delta += 2
        if any(token in message_lower for token in ["кто принимает решение", "кто согласует", "есть ли полномочия"]):
            discovered_authority_level = profile.authority_level
            trust_delta += 1
        if any(token in message_lower for token in ["какая проблема", "что болит", "болит", "где потери", "что мешает", "проблем"]):
            discovered_pains.extend(profile.latent_pains[:1])
            known_pains.extend(profile.latent_pains[:1])
            trust_delta += 2
        if any(token in message_lower for token in ["как сейчас устроено", "процесс", "воронка"]):
            current_process.append(profile.current_business_context)
        if any(token in message_lower for token in ["по каким критериям", "что важно", "как выбираете"]):
            decision_criteria.extend(profile.decision_criteria[:2])
        if any(token in message_lower for token in ["что мешает", "какие ограничения", "риски"]):
            constraints.extend(profile.hidden_constraints[:1])

        if band in {"neutral", "warm", "hot"}:
            buying_signals.append("Client asked about scope, time, or next step.")
        if band == "cold":
            tone = "cold"
            add_open_objections.append("Still does not see enough relevance.")
        elif band == "skeptical":
            tone = "skeptical"
            add_open_objections.append("Needs more concrete proof and relevance.")
        elif band == "neutral":
            tone = "neutral"
        elif band == "warm":
            tone = "warm"
        else:
            tone = "ready_next_step"

        return StatePatch(
            tone=tone,
            trust_delta=max(-15, min(15, trust_delta)),
            irritation_delta=max(-15, min(15, irritation_delta)),
            urgency_delta=max(-15, min(15, urgency_delta)),
            add_open_objections=add_open_objections,
            remove_open_objections=remove_open_objections,
            add_known_pains=known_pains,
            add_buying_signals=buying_signals,
            add_red_flags=red_flags,
            set_discovered_role=discovered_role,
            set_discovered_authority_level=discovered_authority_level,
            add_discovered_pains=discovered_pains,
            add_discovered_decision_criteria=decision_criteria,
            add_discovered_constraints=constraints,
            add_discovered_current_process=current_process,
        )

    def _build_notes(self, delta: int, band: str, message: str) -> str:
        direction = "improved" if delta > 0 else "did not improve"
        return f"Client interest {direction}; resulting band is {band}. Manager message length={len(message)}."


Transport = Callable[[dict[str, Any]], Any]

FakeLLMClient = CleanFakeLLMClient


class YandexCompatibleLLMClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        folder_id: str,
        agent_id: str,
        timeout_seconds: int = 30,
        max_retries: int = 1,
        fallback_client: LLMClient | None = None,
        transport: Transport | None = None,
        debug_payload_logging: bool = False,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._folder_id = folder_id
        self._agent_id = agent_id
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._fallback_client = fallback_client
        self._transport = transport or self._default_transport
        self._debug_payload_logging = debug_payload_logging

    def generate_client_turn(self, payload: LLMTurnInput) -> LLMTurnResponse:
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            retry_instruction = ""
            if attempt > 0:
                retry_instruction = (
                    "\nPrevious answer was invalid. Return one JSON object only. "
                    "No markdown. No commentary."
                )
            request_payload = self._build_request_payload(payload, retry_instruction)
            metadata = _safe_request_metadata(
                provider="yandex_compatible",
                endpoint_url=self.endpoint_url,
                api_key=self._api_key,
                project_id=self._folder_id,
                prompt_id=self._agent_id,
                attempt=attempt + 1,
                request_payload=request_payload,
            )
            logger.info("yandex_llm_request %s", metadata)
            if self._debug_payload_logging:
                logger.debug("yandex_llm_request_payload %s", request_payload)
            try:
                raw_response = _response_to_payload(self._transport(request_payload))
                return parse_llm_turn_response(raw_response)
            except (LLMClientError, ValidationError, JSONDecodeError, TimeoutError) as error:
                last_error = error
                logger.warning("yandex_llm_request_failed attempt=%s error=%s", attempt + 1, error)
            except Exception as error:
                last_error = error
                status_code = getattr(error, "status_code", None)
                response = getattr(error, "response", None)
                error_body = ""
                if response is not None:
                    response_text = getattr(response, "text", None)
                    if isinstance(response_text, str):
                        error_body = response_text
                    else:
                        try:
                            error_body = json.dumps(response.json(), ensure_ascii=True)
                        except Exception:
                            error_body = repr(response)
                logger.warning(
                    "yandex_llm_http_error attempt=%s status=%s error=%s body=%s",
                    attempt + 1,
                    status_code,
                    error,
                    error_body,
                )
        if self._fallback_client is not None:
            logger.warning("yandex_llm_fallback_to_fake reason=%s", last_error)
            return self._fallback_client.generate_client_turn(payload)
        raise LLMClientError(f"Yandex LLM request failed after retries: {last_error}") from last_error

    def _build_request_payload(self, payload: LLMTurnInput, retry_instruction: str) -> dict[str, Any]:
        schema = json.loads(llm_turn_response_schema_json())
        snapshot = {
            "task": payload.task,
            "scenario": payload.scenario.model_dump(mode="json"),
            "hidden_profile": payload.hidden_profile.model_dump(mode="json"),
            "current_state": payload.current_state,
            "discovered_facts": payload.discovered_facts,
            "conversation_summary": payload.conversation_summary,
            "recent_turns": payload.recent_turns,
            "manager_message": payload.manager_message,
        }
        if retry_instruction:
            snapshot["retry_instruction"] = retry_instruction.strip()
        return {
            "prompt": {
                "id": self._agent_id,
            },
            "input": json.dumps(snapshot, ensure_ascii=False),
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "llm_turn_response",
                    "schema": schema,
                    "strict": True,
                }
            },
        }

    def _default_transport(self, request_payload: dict[str, Any]) -> Any:
        try:
            from openai import OpenAI
        except ImportError as error:
            raise LLMClientError(
                "openai package is required for yandex_compatible backend. Reinstall project dependencies."
            ) from error

        client = OpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
            project=self._folder_id,
            timeout=self._timeout_seconds,
        )
        return client.responses.create(**request_payload)

    @property
    def endpoint_url(self) -> str:
        return f"{self._base_url}/responses"


def build_llm_client(settings: Settings) -> LLMClient:
    backend = settings.llm_backend.lower().strip()
    if backend == "fake":
        return FakeLLMClient()
    if backend == "yandex_compatible":
        if not all([settings.yandex_api_key, settings.yandex_folder_id, settings.yandex_agent_id]):
            if _should_allow_fake_fallback(settings):
                logger.warning("llm_backend_incomplete_config backend=%s fallback=fake", backend)
                return FakeLLMClient()
            raise LLMProviderConfigurationError(
                "Incomplete Yandex LLM configuration and fake fallback is disabled."
            )
        return YandexCompatibleLLMClient(
            base_url=settings.yandex_base_url,
            api_key=settings.yandex_api_key,
            folder_id=settings.yandex_folder_id,
            agent_id=settings.yandex_agent_id,
            timeout_seconds=settings.llm_request_timeout_seconds,
            max_retries=1,
            fallback_client=FakeLLMClient() if _should_allow_fake_fallback(settings) else None,
            debug_payload_logging=settings.debug_llm_payload,
        )
    if _should_allow_fake_fallback(settings):
        logger.warning("llm_backend_unknown backend=%s fallback=fake", settings.llm_backend)
        return FakeLLMClient()
    raise LLMProviderConfigurationError(
        f"Unknown llm_backend '{settings.llm_backend}' and fake fallback is disabled."
    )
