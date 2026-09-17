from __future__ import annotations

import json
import logging
from json import JSONDecodeError
from typing import Any, Protocol

from pydantic import ValidationError

from app.domain.errors import LLMProviderConfigurationError
from app.domain.models import LLMTurnInput, LLMTurnResponse
from app.domain.token_counter import TokenCountedResult, TokenCounterService
from app.infrastructure.config import Settings, is_fake_fallback_allowed
from app.infrastructure.fake_llm_client import FakeLLMClient
from app.prompts.schemas import llm_turn_response_schema_json, load_client_simulator_prompt
from app.infrastructure.responses_client import (
    LLMClientError,
    OpenAICompatibleClient,
    Transport,
    _http_error_body,
    _response_to_payload,
    _safe_request_metadata,
    parse_enveloped_json_output,
)

logger = logging.getLogger(__name__)


class LLMClient(Protocol):
    def generate_client_turn(self, payload: LLMTurnInput) -> TokenCountedResult[LLMTurnResponse]:
        ...


def parse_llm_turn_response(raw_payload: dict[str, Any] | str) -> LLMTurnResponse:
    return parse_enveloped_json_output(
        raw_payload,
        model=LLMTurnResponse,
        direct_key="answer",
        no_output_message="Provider response does not contain structured text output.",
        invalid_json_message="Provider response does not contain valid JSON.",
    )


class OpenAICompatibleLLMClient(OpenAICompatibleClient):
    """Dialogue client for any OpenAI-compatible router speaking responses or chat/completions."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str | None = None,
        folder_id: str | None = None,
        agent_id: str | None = None,
        system_prompt: str | None = None,
        provider: str = "openai_compatible",
        api_style: str = "chat_completions",
        response_format: str = "json_schema",
        reasoning_mode: str = "provider_default",
        timeout_seconds: int = 60,
        max_retries: int = 1,
        fallback_client: LLMClient | None = None,
        transport: Transport | None = None,
        debug_payload_logging: bool = False,
        token_counter: TokenCounterService | None = None,
    ) -> None:
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            model=model,
            folder_id=folder_id,
            system_prompt=system_prompt,
            api_style=api_style,
            response_format=response_format,
            reasoning_mode=reasoning_mode,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            transport=transport,
            debug_payload_logging=debug_payload_logging,
        )
        self._provider = provider
        self._agent_id = agent_id
        self._fallback_client = fallback_client
        self._token_counter = token_counter or TokenCounterService()

    def generate_client_turn(self, payload: LLMTurnInput) -> TokenCountedResult[LLMTurnResponse]:
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
                provider=self._provider,
                endpoint_url=self.endpoint_url,
                api_key=self._api_key,
                project_id=self._folder_id or "",
                prompt_id=self._agent_id or self._model or "",
                attempt=attempt + 1,
                request_payload=request_payload,
            )
            logger.info("llm_request %s", metadata)
            if self._debug_payload_logging:
                logger.debug("llm_request_payload %s", request_payload)
            try:
                raw_response = _response_to_payload(self._transport(request_payload))
                response = parse_llm_turn_response(raw_response)
                input_tokens = self._token_counter.count_string(request_payload.get("input", ""))
                output_tokens = self._token_counter.count_json(response.model_dump(mode="json"))
                return TokenCountedResult(value=response, input_tokens=input_tokens, output_tokens=output_tokens)
            except (LLMClientError, ValidationError, JSONDecodeError, TimeoutError) as error:
                last_error = error
                logger.warning("llm_request_failed attempt=%s error=%s", attempt + 1, error)
            except Exception as error:
                last_error = error
                status_code = getattr(error, "status_code", None)
                error_body = _http_error_body(error)
                logger.warning(
                    "llm_http_error attempt=%s status=%s error=%s body=%s",
                    attempt + 1,
                    status_code,
                    error,
                    error_body,
                )
        if self._fallback_client is not None:
            logger.warning("llm_fallback_to_fake reason=%s", last_error)
            return self._fallback_client.generate_client_turn(payload)
        raise LLMClientError(f"LLM request failed after retries: {last_error}") from last_error

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
        request_payload: dict[str, Any] = {
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
        if self._agent_id:
            request_payload["prompt"] = {"id": self._agent_id}
        elif self._model:
            request_payload["model"] = self._model
        if self._system_prompt:
            request_payload["system_prompt"] = self._system_prompt
        return request_payload


class YandexCompatibleLLMClient(OpenAICompatibleLLMClient):
    """Yandex agents responses-API flavour of the dialogue client."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        folder_id: str,
        agent_id: str,
        timeout_seconds: int = 60,
        max_retries: int = 1,
        fallback_client: LLMClient | None = None,
        transport: Transport | None = None,
        debug_payload_logging: bool = False,
        token_counter: TokenCounterService | None = None,
    ) -> None:
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            folder_id=folder_id,
            agent_id=agent_id,
            provider="yandex_compatible",
            api_style="responses",
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            fallback_client=fallback_client,
            transport=transport,
            debug_payload_logging=debug_payload_logging,
            token_counter=token_counter,
        )


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
    if backend == "openai_compatible":
        model = settings.llm_dialogue_model or settings.llm_model
        if not all([settings.llm_base_url, settings.llm_api_key, model]):
            if is_fake_fallback_allowed(settings):
                logger.warning("llm_backend_incomplete_config backend=%s fallback=fake", backend)
                return FakeLLMClient()
            raise LLMProviderConfigurationError(
                "Incomplete OpenAI-compatible LLM configuration and fake fallback is disabled."
            )
        return OpenAICompatibleLLMClient(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=model,
            system_prompt=load_client_simulator_prompt(),
            api_style=settings.llm_api_style,
            response_format=settings.llm_response_format,
            reasoning_mode=settings.llm_reasoning_mode,
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
