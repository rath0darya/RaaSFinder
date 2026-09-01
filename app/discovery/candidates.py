from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class Candidate:
    url: str
    channel: str
    reason: str


URL_PATTERN = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)


def _valid_public_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def extract_candidates(text: str, channel: str = "clearweb") -> list[Candidate]:
    """Extract unique HTTP(S) URLs from public-source text.

    This is deliberately passive: it only parses supplied text and performs
    no crawling, authentication bypass, credential collection, or exploitation.
    """
    seen: set[str] = set()
    candidates: list[Candidate] = []

    for match in URL_PATTERN.findall(text):
        url = match.rstrip(".,;:)]}")
        if not _valid_public_url(url) or url in seen:
            continue
        seen.add(url)
        candidates.append(Candidate(url=url, channel=channel, reason="public URL observed"))

    return candidates
