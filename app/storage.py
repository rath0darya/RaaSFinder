from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def append_observation(path: Path, item: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    records = []
    if path.exists():
        try:
            records = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            records = []
    records.append(item)
    path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
