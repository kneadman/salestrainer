from __future__ import annotations

import json
import logging
from typing import Any

import tiktoken

logger = logging.getLogger(__name__)


class TokenCounterService:
    """Provider-independent token counter using tiktoken (cl100k_base).

    Encapsulates encoding so that switching LLM providers does not affect
    billing token counts.  The counts are *estimates*; they are not guaranteed
    to match the provider's own tokenizer.
    """

    def __init__(self, encoding_name: str = "cl100k_base") -> None:
        self._encoding = tiktoken.get_encoding(encoding_name)

    def count_string(self, text: str) -> int:
        """Return token count for a plain string."""
        if not text:
            return 0
        return len(self._encoding.encode(text))

    def count_json(self, obj: Any) -> int:
        """Serialize *obj* to JSON and count tokens in the resulting string."""
        return self.count_string(json.dumps(obj, ensure_ascii=False))
