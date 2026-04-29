from __future__ import annotations


def clamp(value: int, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, value))


def apply_interest_delta(score: int, interest_delta: int) -> int:
    return clamp(score + interest_delta)


def interest_band(score: int) -> str:
    if score <= 20:
        return "cold"
    if score <= 40:
        return "skeptical"
    if score <= 60:
        return "neutral"
    if score <= 80:
        return "warm"
    return "hot"

