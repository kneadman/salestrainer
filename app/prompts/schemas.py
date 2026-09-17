from __future__ import annotations

from pathlib import Path
import json
from typing import Any

from pydantic import BaseModel

from app.domain.models import LLMTurnResponse

PROMPT_PATH = Path(__file__).with_name("client_simulator.md")
JUDGE_PROMPT_PATH = Path(__file__).with_name("judge_agent.md")
PERSONA_PROMPT_PATH = Path(__file__).with_name("persona_generator.md")


def load_client_simulator_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8").strip()


def load_judge_prompt() -> str:
    """Load the reference judge instructions for providers without hosted agents."""
    return JUDGE_PROMPT_PATH.read_text(encoding="utf-8").strip()


def load_persona_generator_prompt() -> str:
    """Load the reference persona-generator instructions for providers without hosted agents."""
    return PERSONA_PROMPT_PATH.read_text(encoding="utf-8").strip()


def build_strict_json_schema(model_class: type[BaseModel]) -> dict[str, Any]:
    """Build a provider-safe strict JSON schema from a Pydantic model.

    Pydantic omits fields that carry a default from ``required``. OpenAI-style
    strict validators reject such schemas outright with
    ``'required' is required to be supplied and to be an array including every
    key in properties``, which used to break every GPT-class model on the router.

    The fix is mechanical and applies to the whole tree: every object node lists
    all of its properties in ``required`` and sets ``additionalProperties`` to
    ``false``. Fields that are optional for the caller stay optional in the
    Pydantic model - the prompt is responsible for filling them with a sensible
    value, and a missing field still validates because defaults are applied
    during model construction, not during JSON-schema validation.
    """
    return make_strict_json_schema(model_class)


def make_strict_json_schema(schema: dict[str, Any] | type[BaseModel]) -> dict[str, Any]:
    """Return a copy of ``schema`` where every object node is strict-validatable.

    Accepts either a raw JSON schema dict or a Pydantic model class.
    """
    raw = schema.model_json_schema(mode="validation") if isinstance(schema, type) else schema
    strict_schema = json.loads(json.dumps(raw))
    _strictify(strict_schema)
    return strict_schema


def _strictify(node: Any) -> None:
    """Recursively force ``required`` completeness and ``additionalProperties: false``."""
    if isinstance(node, dict):
        properties = node.get("properties")
        if isinstance(properties, dict) and properties:
            node["required"] = sorted(properties.keys())
            node["additionalProperties"] = False
        for value in node.values():
            _strictify(value)
        return
    if isinstance(node, list):
        for item in node:
            _strictify(item)


def llm_turn_response_schema() -> dict[str, Any]:
    return build_strict_json_schema(LLMTurnResponse)


def llm_turn_response_schema_json() -> str:
    return json.dumps(llm_turn_response_schema(), ensure_ascii=True, separators=(",", ":"))
