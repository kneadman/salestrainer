from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.application.summary_compressor import FakeSummaryCompressor, SummaryCompressor
from app.domain.errors import LLMProviderConfigurationError
from app.domain.models import TrainingSessionState, Turn
from app.infrastructure.config import Settings, is_fake_fallback_allowed
from app.infrastructure.responses_client import (
    LLMClientError,
    OpenAICompatibleClient,
    Transport,
    _chat_completions_text,
    _http_error_body,
    _response_to_payload,
    _safe_request_metadata,
)

logger = logging.getLogger(__name__)

SUMMARY_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "summary_compressor.md"


def load_summary_prompt() -> str:
    return SUMMARY_PROMPT_PATH.read_text(encoding="utf-8").strip()


def parse_summary_text(raw_payload: dict[str, Any] | str) -> str:
    if isinstance(raw_payload, dict):
        output_text = raw_payload.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()[:1000]
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
                        if isinstance(text, str) and text.strip():
                            return text.strip()[:1000]
        chat_text = _chat_completions_text(raw_payload)
        if chat_text is not None and chat_text.strip():
            return chat_text.strip()[:1000]
        raise LLMClientError("Summary response does not contain output_text.")
    try:
        decoded = json.loads(raw_payload)
    except json.JSONDecodeError:
        decoded = None
    if isinstance(decoded, dict):
        return parse_summary_text(decoded)
    text = raw_payload.strip()
    if not text:
        raise LLMClientError("Summary response is empty.")
    return text[:1000]


class OpenAICompatibleSummaryCompressor(OpenAICompatibleClient):
    """Summary compressor for any OpenAI-compatible router."""

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
        response_format: str = "none",
        reasoning_mode: str = "provider_default",
        timeout_seconds: int = 30,
        max_retries: int = 1,
        fallback_compressor: SummaryCompressor | None = None,
        transport: Transport | None = None,
        debug_payload_logging: bool = False,
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
        self._fallback_compressor = fallback_compressor

    def compress(
        self,
        *,
        existing_summary: str,
        overflow_turns: list[Turn],
        session: TrainingSessionState,
        latest_internal_notes: str,
    ) -> str:
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            retry_instruction = ""
            if attempt > 0:
                retry_instruction = "\nPrevious answer was invalid. Return plain text summary only."
            request_payload = self._build_request_payload(
                existing_summary=existing_summary,
                overflow_turns=overflow_turns,
                session=session,
                latest_internal_notes=latest_internal_notes,
                retry_instruction=retry_instruction,
            )
            metadata = _safe_request_metadata(
                provider=self._provider,
                endpoint_url=self.endpoint_url,
                api_key=self._api_key,
                project_id=self._folder_id or "",
                prompt_id=self._agent_id or self._model or "",
                attempt=attempt + 1,
                request_payload=request_payload,
            )
            logger.info("summary_compression_request %s", metadata)
            if self._debug_payload_logging:
                logger.debug("summary_compression_request_payload %s", request_payload)
            try:
                raw_response = _response_to_payload(self._transport(request_payload))
                return parse_summary_text(raw_response)
            except (LLMClientError, TimeoutError) as error:
                last_error = error
                logger.warning("summary_compression_failed attempt=%s error=%s", attempt + 1, error)
            except Exception as error:
                last_error = error
                status_code = getattr(error, "status_code", None)
                error_body = _http_error_body(error)
                logger.warning(
                    "summary_compression_http_error attempt=%s status=%s error=%s body=%s",
                    attempt + 1,
                    status_code,
                    error,
                    error_body,
                )
        if self._fallback_compressor is None:
            raise LLMClientError(f"Summary compression failed after retries: {last_error}") from last_error
        logger.warning("summary_compression_fallback reason=%s", last_error)
        return self._fallback_compressor.compress(
            existing_summary=existing_summary,
            overflow_turns=overflow_turns,
            session=session,
            latest_internal_notes=latest_internal_notes,
        )

    def _build_request_payload(
        self,
        *,
        existing_summary: str,
        overflow_turns: list[Turn],
        session: TrainingSessionState,
        latest_internal_notes: str,
        retry_instruction: str,
    ) -> dict[str, Any]:
        turns_payload = [
            {
                "index": turn.index,
                "manager_message": turn.manager_message,
                "client_answer": turn.client_answer,
                "interest_before": turn.interest_before,
                "interest_after": turn.interest_after,
                "stage_before": turn.stage_before,
                "stage_after": turn.stage_after,
            }
            for turn in overflow_turns
        ]
        input_text = (
            f"{load_summary_prompt()}\n\n"
            f"{retry_instruction}\n\n"
            f"Existing summary:\n{existing_summary}\n\n"
            f"Overflow turns:\n{json.dumps(turns_payload, ensure_ascii=True, indent=2)}\n\n"
            f"Latest notes:\n{latest_internal_notes}\n\n"
            f"Current session state:\n"
            f"{json.dumps({'interest_score': session.interest_score, 'stage': session.stage, 'client_state': session.client_state.model_dump(mode='json')}, ensure_ascii=True, indent=2)}"
        )
        request_payload: dict[str, Any] = {"input": input_text}
        if self._agent_id:
            request_payload["prompt"] = {"id": self._agent_id}
        elif self._model:
            request_payload["model"] = self._model
        return request_payload


class YandexSummaryCompressor(OpenAICompatibleSummaryCompressor):
    """Yandex agents responses-API flavour of the summary compressor."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        folder_id: str,
        agent_id: str,
        timeout_seconds: int = 30,
        max_retries: int = 1,
        fallback_compressor: SummaryCompressor | None = None,
        transport: Transport | None = None,
        debug_payload_logging: bool = False,
    ) -> None:
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            folder_id=folder_id,
            agent_id=agent_id,
            provider="yandex_summary_compressor",
            api_style="responses",
            response_format="none",
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            fallback_compressor=fallback_compressor,
            transport=transport,
            debug_payload_logging=debug_payload_logging,
        )


def build_summary_compressor(settings: Settings) -> SummaryCompressor:
    backend = settings.llm_backend.lower().strip()
    if backend == "openai_compatible":
        model = settings.llm_summary_model or settings.llm_model
        if not all([settings.llm_base_url, settings.llm_api_key, model]):
            if is_fake_fallback_allowed(settings):
                logger.warning("summary_compressor_incomplete_config fallback=fake")
                return FakeSummaryCompressor()
            raise LLMProviderConfigurationError(
                "Incomplete summary compressor configuration and fake fallback is disabled."
            )
        return OpenAICompatibleSummaryCompressor(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=model,
            system_prompt=load_summary_prompt(),
            api_style=settings.llm_api_style,
            response_format="none",
            reasoning_mode=settings.llm_reasoning_mode,
            timeout_seconds=settings.llm_request_timeout_seconds,
            max_retries=1,
            fallback_compressor=FakeSummaryCompressor() if is_fake_fallback_allowed(settings) else None,
            debug_payload_logging=settings.debug_llm_payload,
        )
    if backend != "yandex_compatible":
        return FakeSummaryCompressor()
    if not all([settings.yandex_api_key, settings.yandex_folder_id, settings.yandex_agent_id]):
        if is_fake_fallback_allowed(settings):
            logger.warning("summary_compressor_incomplete_config fallback=fake")
            return FakeSummaryCompressor()
        raise LLMProviderConfigurationError(
            "Incomplete summary compressor configuration and fake fallback is disabled."
        )
    return YandexSummaryCompressor(
        base_url=settings.yandex_base_url,
        api_key=settings.yandex_api_key,
        folder_id=settings.yandex_folder_id,
        agent_id=settings.yandex_agent_id,
        timeout_seconds=settings.llm_request_timeout_seconds,
        max_retries=1,
        fallback_compressor=FakeSummaryCompressor() if is_fake_fallback_allowed(settings) else None,
        debug_payload_logging=settings.debug_llm_payload,
    )
