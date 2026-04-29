from __future__ import annotations

from pathlib import Path
import json
from typing import Any

from pydantic import BaseModel

from app.domain.models import LLMTurnResponse

PROMPT_PATH = Path(__file__).with_name("client_simulator.md")


def load_client_simulator_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8").strip()


def build_strict_json_schema(model_class: type[BaseModel]) -> dict[str, Any]:
    return model_class.model_json_schema(mode="validation")


def llm_turn_response_schema() -> dict[str, Any]:
    return build_strict_json_schema(LLMTurnResponse)


def llm_turn_response_schema_json() -> str:
    return json.dumps(llm_turn_response_schema(), ensure_ascii=True, separators=(",", ":"))
