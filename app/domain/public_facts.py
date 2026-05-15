from __future__ import annotations

import logging
import re

from app.domain.models import RevealedFact, RevealedFactPatch

logger = logging.getLogger(__name__)


def normalize_public_fact_text(value: str) -> str:
    return " ".join(value.strip().split())


def is_probably_technical_value(value: str) -> bool:
    normalized = value.strip()
    if not normalized:
        return True
    if "_" in normalized:
        return True
    if re.fullmatch(r"[a-z][a-z0-9_]*", normalized):
        return True
    return False


def append_revealed_facts(
    existing: list[RevealedFact],
    additions: list[RevealedFactPatch],
    *,
    turn_index: int,
) -> list[RevealedFact]:
    updated = list(existing)
    seen = {
        (fact.category, normalize_public_fact_text(fact.text).casefold())
        for fact in updated
    }
    for addition in additions:
        text = normalize_public_fact_text(addition.text)
        if is_probably_technical_value(text):
            logger.info(
                "revealed_fact_rejected_technical category=%s turn_index=%s",
                addition.category,
                turn_index,
            )
            continue
        dedupe_key = (addition.category, text.casefold())
        if dedupe_key in seen:
            continue
        updated.append(
            RevealedFact(
                category=addition.category,
                text=text,
                turn_index=turn_index,
            )
        )
        seen.add(dedupe_key)
    return updated


def sanitize_revealed_fact_dicts(values: object) -> list[dict[str, object]]:
    if not isinstance(values, list):
        return []
    result: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for value in values:
        if not isinstance(value, dict):
            continue
        try:
            fact = RevealedFact.model_validate(value)
        except Exception:
            continue
        text = normalize_public_fact_text(fact.text)
        if is_probably_technical_value(text):
            continue
        dedupe_key = (fact.category, text.casefold())
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        result.append(
            RevealedFact(
                category=fact.category,
                text=text,
                turn_index=fact.turn_index,
            ).model_dump(mode="json")
        )
    return result
