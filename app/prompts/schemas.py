from __future__ import annotations

from pathlib import Path
import json

LLM_TURN_RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["answer", "interest_delta", "state_patch", "stage", "internal_notes"],
    "properties": {
        "answer": {"type": "string"},
        "interest_delta": {"type": "integer", "minimum": -15, "maximum": 15},
        "stage": {"type": "string"},
        "internal_notes": {"type": "string"},
        "state_patch": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "tone": {
                    "type": ["string", "null"],
                    "enum": ["cold", "skeptical", "neutral", "interested", "warm", "ready_next_step", None],
                },
                "trust_delta": {"type": "integer", "minimum": -15, "maximum": 15},
                "irritation_delta": {"type": "integer", "minimum": -15, "maximum": 15},
                "urgency_delta": {"type": "integer", "minimum": -15, "maximum": 15},
                "add_open_objections": {"type": "array", "items": {"type": "string"}},
                "remove_open_objections": {"type": "array", "items": {"type": "string"}},
                "add_known_pains": {"type": "array", "items": {"type": "string"}},
                "add_buying_signals": {"type": "array", "items": {"type": "string"}},
                "add_red_flags": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
}


PROMPT_PATH = Path(__file__).with_name("client_simulator.md")


def load_client_simulator_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8").strip()


def llm_turn_response_schema_json() -> str:
    return json.dumps(LLM_TURN_RESPONSE_SCHEMA, ensure_ascii=True, separators=(",", ":"))
