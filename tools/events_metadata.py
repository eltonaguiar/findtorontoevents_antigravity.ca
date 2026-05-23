"""Build metadata.json for the React events homepage header (no scraper deps)."""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def max_event_last_updated_iso(events: list) -> Optional[str]:
    """Best-effort max lastUpdated/last_updated across events (ISO strings)."""
    best = None
    for event in events:
        for key in ("lastUpdated", "last_updated"):
            raw = event.get(key)
            if not raw:
                continue
            s = str(raw).strip()
            if not s:
                continue
            if best is None or s > best:
                best = s
    return best


def build_events_metadata(events: list, last_updated_iso: str) -> dict:
    """Shape consumed by the live React bundle (GET /metadata.json)."""
    sources = sorted(
        {str(e.get("source") or "").strip() for e in events if str(e.get("source") or "").strip()}
    )
    return {
        "lastUpdated": last_updated_iso,
        "totalEvents": len(events),
        "sources": sources,
    }


def write_events_metadata(events: list, last_updated_iso: Optional[str] = None) -> dict:
    """Write metadata.json at site root and under next/ for the events grid header."""
    if not last_updated_iso:
        last_updated_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    metadata = build_events_metadata(events, last_updated_iso)
    # React tries Promise.any() across root, next/, data/, and TORONTOEVENTS_ANTIGRAVITY/;
    # keep every path in sync so a fast stale copy cannot win the race.
    paths = [
        PROJECT_ROOT / "metadata.json",
        PROJECT_ROOT / "next" / "metadata.json",
        PROJECT_ROOT / "data" / "metadata.json",
        PROJECT_ROOT / "TORONTOEVENTS_ANTIGRAVITY" / "metadata.json",
    ]
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        print(f"Wrote {path} (lastUpdated={metadata['lastUpdated']}, totalEvents={metadata['totalEvents']})")
    return metadata
