from __future__ import annotations

import json
import logging
from json import JSONDecodeError
import re
from typing import Any, Callable, Protocol

from pydantic import ValidationError

from app.domain.errors import LLMProviderConfigurationError
from app.domain.models import LLMTurnInput, LLMTurnResponse
from app.infrastructure.config import Settings, is_fake_fallback_allowed
from app.infrastructure.fake_llm_client import FakeLLMClient
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


Transport = Callable[[dict[str, Any]], Any]


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
        folder_id = settings.yandex_dialogue_folder_id or settings.yandex_folder_id
        agent_id = settings.yandex_dialogue_agent_id or settings.yandex_agent_id
        if not all([settings.yandex_api_key, folder_id, agent_id]):
            if is_fake_fallback_allowed(settings):
                logger.warning("llm_backend_incomplete_config backend=%s fallback=fake", backend)
                return FakeLLMClient()
            raise LLMProviderConfigurationError(
                "Incomplete Yandex LLM configuration and fake fallback is disabled."
            )
        return YandexCompatibleLLMClient(
            base_url=settings.yandex_base_url,
            api_key=settings.yandex_api_key,
            folder_id=folder_id,
            agent_id=agent_id,
            timeout_seconds=settings.llm_request_timeout_seconds,
            max_retries=1,
            fallback_client=FakeLLMClient() if is_fake_fallback_allowed(settings) else None,
            debug_payload_logging=settings.debug_llm_payload,
        )
    if is_fake_fallback_allowed(settings):
        logger.warning("llm_backend_unknown backend=%s fallback=fake", settings.llm_backend)
        return FakeLLMClient()
    raise LLMProviderConfigurationError(
        f"Unknown llm_backend '{settings.llm_backend}' and fake fallback is disabled."
    )
