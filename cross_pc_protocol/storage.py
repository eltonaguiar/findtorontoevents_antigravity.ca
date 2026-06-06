"""Durable event log storage used by protocol gateway and inspector."""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List


class EventStore:
    """Append-only JSONL log with simple query helpers."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def append(self, event: Dict[str, Any]) -> None:
        line = json.dumps(event, separators=(",", ":"), ensure_ascii=True)
        with self._lock:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")

    def _iter_events(self) -> Iterable[Dict[str, Any]]:
        if not self.path.exists():
            return []
        rows: List[Dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for raw in handle:
                text = raw.strip()
                if not text:
                    continue
                try:
                    rows.append(json.loads(text))
                except json.JSONDecodeError:
                    continue
        return rows

    def tail(self, limit: int = 20, topic: str = "") -> List[Dict[str, Any]]:
        rows = list(self._iter_events())
        if topic:
            rows = [row for row in rows if (row.get("envelope") or {}).get("topic") == topic]
        if limit <= 0:
            return []
        return rows[-limit:]

    def by_trace_id(self, trace_id: str, limit: int = 500) -> List[Dict[str, Any]]:
        trace = trace_id.strip()
        if not trace:
            return []
        rows = [
            row
            for row in self._iter_events()
            if (row.get("envelope") or {}).get("trace_id") == trace
        ]
        return rows[-limit:]

    def by_message_id(self, message_id: str) -> List[Dict[str, Any]]:
        needle = message_id.strip()
        if not needle:
            return []
        return [
            row
            for row in self._iter_events()
            if (row.get("envelope") or {}).get("message_id") == needle
        ]

    def recent_broadcasts(
        self, since_sec: int = 3600, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Return accepted broadcast envelopes from the last ``since_sec`` seconds.

        Used by the gateway to backfill a newly-registered peer's queue with
        broadcasts they missed (e.g. joined after a gateway restart or sent
        their first message after a to=all was already routed).

        Returns raw envelope dicts (not event wrapper dicts), newest-last,
        filtered to status=broadcasted|accepted and to="" (broadcasts only).
        """
        cutoff = time.time() - since_sec
        out: List[Dict[str, Any]] = []
        for row in self._iter_events():
            # Filter to broadcast-type events only
            if not isinstance(row, dict):
                continue
            status = row.get("status", "")
            if status not in ("broadcasted", "accepted"):
                continue
            env = row.get("envelope") or {}
            if not isinstance(env, dict):
                continue
            # Must be a broadcast (to="" or to="all")
            target = str(env.get("to") or "").strip().lower()
            if target not in ("", "all"):
                continue
            # Time filter — parse gateway_ts_utc if present, else include
            ts_str = row.get("gateway_ts_utc") or env.get("ts_utc") or ""
            if ts_str:
                try:
                    import datetime
                    dt = datetime.datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%SZ")
                    dt = dt.replace(tzinfo=datetime.timezone.utc)
                    if dt.timestamp() < cutoff:
                        continue
                except (ValueError, TypeError):
                    pass  # unknown format — include it
            out.append(env)
        return out[-limit:]
