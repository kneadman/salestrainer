from __future__ import annotations

from enum import StrEnum


class UsageEventType(StrEnum):
    SESSION_STARTED = "session_started"
    TURN_PROCESSED = "turn_processed"
    SESSION_FINISHED = "session_finished"
    REPORT_GENERATED = "report_generated"
    SESSION_RESUMED = "session_resumed"
    SESSION_VIEWED = "session_viewed"
    HISTORY_VIEWED = "history_viewed"
