from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Signal:
    name: str
    weight: int
    matches: int


# Generic behavioural indicators only. No known group names or addresses are seeded.
PATTERNS: dict[str, tuple[int, str]] = {
    "affiliate_program": (3, r"\baffiliate(?:s| program| recruitment)?\b"),
    "ransomware_service": (4, r"\bransomware[- ]as[- ]a[- ]service\b|\braas\b"),
    "ransom_payment": (2, r"\bransom(?:ware)?\b.{0,80}\bpayment\b|\bpayment\b.{0,80}\bransom"),
    "victim_listing": (2, r"\bvictim(?:s)?\b.{0,80}\b(?:leak|encrypted|published|claimed)"),
    "extortion": (2, r"\bdouble extortion\b|\bextortion\b"),
    "partner_recruitment": (2, r"\bpartners?\b.{0,80}\bjoin|\bjoin\b.{0,80}\bpartners?\b"),
}


def detect_signals(text: str) -> list[Signal]:
    normalized = text.lower()
    results: list[Signal] = []
    for name, (weight, pattern) in PATTERNS.items():
        matches = len(re.findall(pattern, normalized, flags=re.I))
        if matches:
            results.append(Signal(name, weight, matches))
    return results
