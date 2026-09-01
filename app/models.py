from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

MASK = "•"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()


def mask_url(url: str) -> str:
    """Display URL without protocol, preserving first 5 and last 3 characters."""
    value = re.sub(r"^[a-z][a-z0-9+.-]*://", "", url.strip(), flags=re.I)
    if len(value) <= 8:
        return value
    return value[:5] + (MASK * (len(value) - 8)) + value[-3:]


@dataclass(frozen=True)
class Observation:
    url: str
    channel: str
    observed_at: str
    title: str
    text: str
    content_hash: str
    signals: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Verification:
    status: str
    confidence: str
    score: int
    reasons: tuple[str, ...]


def validate_public_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    return True


def snapshot_path(root: Path, content_hash: str) -> Path:
    return root / f"{content_hash}.html"
