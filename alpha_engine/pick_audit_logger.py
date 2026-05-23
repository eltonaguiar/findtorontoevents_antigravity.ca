"""Append-only Smart Picks run audit trail (bounded size)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_MAX_ENTRIES = 500
_PATH = Path(__file__).resolve().parent / "data" / "pick_audit_log.json"


def append_smart_picks_run(summary: dict[str, Any]) -> None:
    """Append one run summary; trim oldest entries beyond _MAX_ENTRIES."""
    doc: dict[str, Any] = {"version": 1, "entries": []}
    if _PATH.is_file():
        try:
            raw = json.loads(_PATH.read_text(encoding="utf-8", errors="replace"))
            if isinstance(raw, dict) and isinstance(raw.get("entries"), list):
                doc = raw
        except (json.JSONDecodeError, OSError):
            pass

    entry = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        **summary,
    }
    entries = list(doc.get("entries") or [])
    entries.append(entry)
    doc["entries"] = entries[-_MAX_ENTRIES:]
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    _PATH.write_text(json.dumps(doc, indent=2), encoding="utf-8")
