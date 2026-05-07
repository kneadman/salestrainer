from __future__ import annotations

import re


_MULTISPACE_RE = re.compile(r"[^\S\r\n]+")
_BLANK_LINES_RE = re.compile(r"\n{3,}")


def normalize_transcribed_text(text: str, *, mode: str) -> tuple[str, bool]:
    """Apply a light non-semantic cleanup pass to transcribed text."""
    if mode != "light":
        return text.strip(), False

    normalized = text.strip().replace("\r\n", "\n").replace("\r", "\n")
    normalized = "\n".join(_MULTISPACE_RE.sub(" ", line).strip() for line in normalized.split("\n"))
    normalized = _BLANK_LINES_RE.sub("\n\n", normalized)
    normalized = normalized.strip()
    normalized = _capitalize_first_letter(normalized)
    return normalized, True


def _capitalize_first_letter(text: str) -> str:
    """Uppercase only the first letter-like character when it is lowercase."""
    if not text:
        return text
    first_character = text[0]
    if first_character.isalpha() and first_character.islower():
        return first_character.upper() + text[1:]
    return text
