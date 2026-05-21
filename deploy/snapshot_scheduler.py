#!/usr/bin/env python3
"""Simple foreground scheduler: run snapshot-token-usage daily at 00:00 MSK.

Intended for Docker Compose — sleeps until next midnight MSK, then triggers
the CLI command and sleeps again. No cron daemon or host setup required.
"""
from __future__ import annotations

import os
import subprocess
import time


def _seconds_until_midnight_msk() -> int:
    """Return seconds from now to next 00:00 Europe/Moscow."""
    os.environ["TZ"] = "Europe/Moscow"
    time.tzset()
    now = time.time()
    t = time.localtime(now)
    # seconds elapsed today
    elapsed = t.tm_hour * 3600 + t.tm_min * 60 + t.tm_sec
    return 24 * 3600 - elapsed


def main() -> None:
    while True:
        sleep_sec = _seconds_until_midnight_msk()
        print(f"[snapshot-scheduler] Sleeping {sleep_sec}s until 00:00 MSK")
        time.sleep(sleep_sec)

        print("[snapshot-scheduler] Triggering snapshot-token-usage")
        result = subprocess.run(
            ["python", "-m", "app.admin.cli", "snapshot-token-usage"],
            capture_output=True,
            text=True,
        )
        print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=__import__("sys").stderr)

        # Small safety pause to avoid double-run within the same minute
        time.sleep(60)


if __name__ == "__main__":
    main()
