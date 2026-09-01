from __future__ import annotations

from .signals import Signal
from .models import Verification


def verify(signals: list[Signal], independent_observations: int = 1) -> Verification:
    score = sum(s.weight * min(s.matches, 3) for s in signals)
    reasons = tuple(s.name for s in signals)

    # Deterministic guardrails: one page is never treated as confirmed intelligence.
    if score < 4:
        return Verification("rejected", "low", score, reasons)
    if independent_observations >= 3 and score >= 8:
        return Verification("verified", "high", score, reasons)
    if independent_observations >= 2 and score >= 6:
        return Verification("verified", "medium", score, reasons)
    return Verification("candidate", "low", score, reasons)
