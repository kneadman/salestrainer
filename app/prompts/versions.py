"""Repository-owned prompt revisions.

Master prompts live in ``app/prompts/*.md`` and are shipped inside the backend
image. They are the single source of truth for every LLM backend; provider-hosted
agent prompts are deprecated.

The revision is derived from the file content, so a prompt edit changes the
revision automatically and nobody has to remember to bump a hand-written label.
Durable history columns (``training_sessions.persona_prompt_version`` and friends)
keep their stable contract labels for backwards compatibility; the content
revision below is recorded in logs and token-usage metadata so a report can be
traced back to the exact prompt text that produced it.
"""

from __future__ import annotations

from functools import lru_cache
import hashlib
from pathlib import Path

_PROMPT_DIR = Path(__file__).parent

DIALOGUE_PROMPT_FILE = _PROMPT_DIR / "client_simulator.md"
PERSONA_PROMPT_FILE = _PROMPT_DIR / "persona_generator.md"
JUDGE_PROMPT_FILE = _PROMPT_DIR / "judge_agent.md"
SUMMARY_PROMPT_FILE = _PROMPT_DIR / "summary_compressor.md"
PERSONA_SEED_TEMPLATE_FILE = _PROMPT_DIR / "persona_seed_template.md"


def _revision_of(path: Path) -> str:
    """Return a short, stable content hash for one prompt file."""
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"{path.stem}-{digest[:12]}"


@lru_cache(maxsize=1)
def prompt_revisions() -> dict[str, str]:
    """Return the content revision for every runtime prompt, keyed by role."""
    return {
        "dialogue": _revision_of(DIALOGUE_PROMPT_FILE),
        "persona": _revision_of(PERSONA_PROMPT_FILE),
        "persona_seed": _revision_of(PERSONA_SEED_TEMPLATE_FILE),
        "judge": _revision_of(JUDGE_PROMPT_FILE),
        "summary": _revision_of(SUMMARY_PROMPT_FILE),
    }
