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
    OpenAICompatibleResponsesClient,
    Transport,
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


class YandexSummaryCompressor(OpenAICompatibleResponsesClient):
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
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            transport=transport,
            debug_payload_logging=debug_payload_logging,
        )
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
                provider="yandex_summary_compressor",
                endpoint_url=self.endpoint_url,
                api_key=self._api_key,
                project_id=self._folder_id,
                prompt_id=self._agent_id,
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
        return {
            "prompt": {"id": self._agent_id},
            "input": input_text,
        }


def build_summary_compressor(settings: Settings) -> SummaryCompressor:
    backend = settings.llm_backend.lower().strip()
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
