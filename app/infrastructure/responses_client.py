"""Shared plumbing for OpenAI-compatible LLM clients.

Holds the machinery that used to be re-implemented by each structured client:
sanitized logging helpers, response-envelope walking, and the default
``openai.OpenAI`` transport. The transport supports both the OpenAI *responses*
API (used by Yandex agents) and the de-facto ``/chat/completions`` API exposed
by OpenAI-compatible routers. Client-specific request building, retry loops,
and validation stay in the per-client modules.
"""

from __future__ import annotations

import json
import logging
from json import JSONDecodeError
import re
from typing import Any, Callable, TypeVar

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class LLMClientError(RuntimeError):
    """Raised when the external LLM client cannot produce a valid structured response."""


Transport = Callable[[dict[str, Any]], Any]


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


ModelT = TypeVar("ModelT", bound=BaseModel)


def parse_enveloped_json_output(
    raw_payload: dict[str, Any] | str,
    *,
    model: type[ModelT],
    direct_key: str,
    no_output_message: str,
    invalid_json_message: str | None = None,
) -> ModelT:
    """Parse known provider response envelopes into a strict pydantic model."""
    if isinstance(raw_payload, dict) and direct_key in raw_payload:
        return model.model_validate(raw_payload)
    if isinstance(raw_payload, dict):
        output_text = raw_payload.get("output_text")
        if isinstance(output_text, str):
            return model.model_validate_json(_extract_json_object(output_text))
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
                            return model.model_validate_json(_extract_json_object(text))
        alternatives = raw_payload.get("alternatives")
        if isinstance(alternatives, list) and alternatives:
            message = alternatives[0].get("message", {})
            text = message.get("text")
            if isinstance(text, str):
                return model.model_validate_json(_extract_json_object(text))
        chat_text = _chat_completions_text(raw_payload)
        if chat_text is not None:
            return model.model_validate_json(_extract_json_object(chat_text))
        raise LLMClientError(no_output_message)
    try:
        decoded = json.loads(raw_payload)
    except JSONDecodeError:
        if invalid_json_message is None:
            return model.model_validate_json(_extract_json_object(raw_payload))
        try:
            return model.model_validate_json(_extract_json_object(raw_payload))
        except JSONDecodeError as error:
            raise LLMClientError(invalid_json_message) from error
    return parse_enveloped_json_output(
        decoded,
        model=model,
        direct_key=direct_key,
        no_output_message=no_output_message,
        invalid_json_message=invalid_json_message,
    )


def _chat_completions_text(raw_payload: dict[str, Any]) -> str | None:
    """Extract assistant text from a ``/chat/completions``-style response payload."""
    choices = raw_payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first = choices[0]
    if not isinstance(first, dict):
        return None
    message = first.get("message")
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [chunk.get("text") for chunk in content if isinstance(chunk, dict)]
        joined = "".join(part for part in parts if isinstance(part, str))
        return joined or None
    return None


def _http_error_body(error: Exception) -> str:
    """Best-effort extraction of an HTTP error body for warning logs."""
    response = getattr(error, "response", None)
    if response is None:
        return ""
    response_text = getattr(response, "text", None)
    if isinstance(response_text, str):
        return response_text
    try:
        return json.dumps(response.json(), ensure_ascii=True)
    except Exception:
        return repr(response)


_API_STYLES = {"responses", "chat_completions"}
_RESPONSE_FORMATS = {"json_schema", "json_object", "none"}


class OpenAICompatibleClient:
    """Shared transport base for OpenAI-compatible LLM clients.

    ``api_style`` selects the wire protocol:

    - ``responses`` runs ``client.responses.create(...)`` (OpenAI responses API / Yandex agents).
    - ``chat_completions`` runs ``client.chat.completions.create(...)``, the shape exposed by
      OpenAI-compatible routers such as OpenRouter, VseGPT or a self-hosted gateway.
    """

    _openai_missing_message = (
        "openai package is required for the openai_compatible backend. Reinstall project dependencies."
    )

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str | None = None,
        folder_id: str | None = None,
        system_prompt: str | None = None,
        api_style: str = "responses",
        response_format: str = "json_schema",
        timeout_seconds: int = 30,
        max_retries: int = 1,
        transport: Transport | None = None,
        debug_payload_logging: bool = False,
    ) -> None:
        resolved_style = api_style.strip().lower()
        if resolved_style not in _API_STYLES:
            raise LLMClientError(f"Unsupported llm_api_style '{api_style}'.")
        resolved_format = response_format.strip().lower()
        if resolved_format not in _RESPONSE_FORMATS:
            raise LLMClientError(f"Unsupported llm_response_format '{response_format}'.")
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._folder_id = folder_id
        self._system_prompt = system_prompt
        self._api_style = resolved_style
        self._response_format = resolved_format
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._transport = transport or self._default_transport
        self._debug_payload_logging = debug_payload_logging

    @property
    def endpoint_url(self) -> str:
        """Return the provider endpoint used for sanitized request metadata."""
        suffix = "/chat/completions" if self._api_style == "chat_completions" else "/responses"
        return f"{self._base_url}{suffix}"

    def _default_transport(self, request_payload: dict[str, Any]) -> Any:
        """Execute the provider call through the optional OpenAI-compatible SDK."""
        try:
            from openai import OpenAI
        except ImportError as error:
            raise LLMClientError(self._openai_missing_message) from error

        if self._api_style == "chat_completions":
            client = OpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
                timeout=self._timeout_seconds,
            )
            return client.chat.completions.create(**self._chat_completions_request(request_payload))

        client = OpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
            project=self._folder_id,
            timeout=self._timeout_seconds,
        )
        return client.responses.create(**request_payload)

    def _chat_completions_request(self, request_payload: dict[str, Any]) -> dict[str, Any]:
        """Map the internal request payload onto the ``/chat/completions`` wire shape."""
        model = request_payload.get("model") or self._model
        if not model:
            raise LLMClientError("Chat-completions request requires a model name.")
        messages: list[dict[str, Any]] = []
        system_prompt = request_payload.get("system_prompt") or self._system_prompt
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        input_value = request_payload.get("input", "")
        if not isinstance(input_value, str):
            input_value = json.dumps(input_value, ensure_ascii=False)
        messages.append({"role": "user", "content": input_value})
        request: dict[str, Any] = {"model": model, "messages": messages}
        format_spec = (request_payload.get("text") or {}).get("format")
        if isinstance(format_spec, dict) and self._response_format != "none":
            if self._response_format == "json_schema":
                request["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": format_spec.get("name", "response"),
                        "schema": format_spec.get("schema", {}),
                        "strict": bool(format_spec.get("strict", True)),
                    },
                }
            else:
                request["response_format"] = {"type": "json_object"}
        return request
