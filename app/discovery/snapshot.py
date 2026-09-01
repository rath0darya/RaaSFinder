from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class Snapshot:
    path: Path
    sha256: str
    observed_at: str


def save_snapshot(html: str, directory: Path, name: str = "page") -> Snapshot:
    """Save a temporary UTF-8 HTML snapshot and return its evidence metadata."""
    directory.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(html.encode("utf-8")).hexdigest()
    observed_at = datetime.now(timezone.utc).isoformat()
    path = directory / f"{name}-{digest[:16]}.html"
    path.write_text(html, encoding="utf-8")
    return Snapshot(path=path, sha256=digest, observed_at=observed_at)


def delete_snapshot(snapshot: Snapshot) -> None:
    """Delete a snapshot only after its structured evidence was committed."""
    snapshot.path.unlink(missing_ok=True)
