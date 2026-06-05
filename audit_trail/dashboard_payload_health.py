#!/usr/bin/env python3
"""Shared dashboard_payload.json health logic for CI and Prometheus exporter."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class DashboardPayloadHealth:
    """Result of validating audit_trail/data/dashboard_payload.json."""

    ok: bool
    age_seconds: int
    payload_stale: bool
    generated_at: str | None
    missing_systems: list[str] = field(default_factory=list)
    bad_numeric_systems: list[str] = field(default_factory=list)
    problems: list[dict[str, str]] = field(default_factory=list)

    def summary_lines(self) -> list[str]:
        lines: list[str] = []
        if self.payload_stale and self.generated_at:
            lines.append(
                f"STALE payload generated_at={self.generated_at} age_s={self.age_seconds}"
            )
        elif self.payload_stale:
            lines.append("STALE payload (no generated_at, file old or missing)")
        if self.missing_systems:
            tail = "..." if len(self.missing_systems) > 40 else ""
            lines.append(
                f"MISSING system rows ({len(self.missing_systems)}): "
                f"{self.missing_systems[:40]}{tail}"
            )
        if self.bad_numeric_systems:
            lines.append(f"BAD numeric fields: {self.bad_numeric_systems}")
        return lines


def check_dashboard_payload(
    repo_root: Path,
    payload_path: Path,
    max_age_seconds: int = 4 * 3600,
) -> DashboardPayloadHealth:
    root_s = str(repo_root.resolve())
    if root_s not in sys.path:
        sys.path.insert(0, root_s)

    from audit_trail.dashboard_generator import JSON_PICK_SOURCES, _HIDDEN_SYSTEMS, _GHOST_SYSTEMS

    problems: list[dict[str, str]] = []
    age_seconds = -1
    payload_stale = False
    generated_at: str | None = None

    if not payload_path.is_file():
        return DashboardPayloadHealth(
            ok=False,
            age_seconds=-1,
            payload_stale=True,
            generated_at=None,
            problems=[{"system": "_payload", "reason": "missing_file"}],
        )

    try:
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return DashboardPayloadHealth(
            ok=False,
            age_seconds=-1,
            payload_stale=True,
            generated_at=None,
            problems=[{
                "system": "_payload",
                "reason": f"corrupted_json: {e.msg} at line {e.lineno} col {e.colno}",
            }],
        )
    generated_at = payload.get("generated_at")
    if generated_at:
        ts = datetime.fromisoformat(str(generated_at).replace("Z", "+00:00"))
        age_seconds = int((datetime.now(timezone.utc) - ts).total_seconds())
        if age_seconds > max_age_seconds:
            payload_stale = True
            problems.append(
                {
                    "system": "_payload",
                    "reason": f"stale_payload_{age_seconds // 3600}h",
                }
            )
    else:
        age_seconds = int(
            max(0, datetime.now(timezone.utc).timestamp() - payload_path.stat().st_mtime)
        )
        if age_seconds > max_age_seconds:
            payload_stale = True
            problems.append(
                {"system": "_payload", "reason": f"stale_file_mtime_{age_seconds // 3600}h"}
            )

    names_in_payload = {s.get("name") for s in payload.get("systems") or []}
    registered: list[str] = []
    for row in JSON_PICK_SOURCES:
        if isinstance(row, (list, tuple)) and row and isinstance(row[0], str):
            registered.append(row[0])

    missing = sorted(
        n for n in set(registered) if n not in names_in_payload and n not in _HIDDEN_SYSTEMS and n not in _GHOST_SYSTEMS
    )
    for n in missing:
        problems.append({"system": n, "reason": "missing_from_payload"})

    bad_numeric: list[str] = []
    for s in payload.get("systems") or []:
        name = s.get("name", "?")
        try:
            upnl = s.get("unrealized_pnl_pct")
            if upnl is not None and upnl != "":
                float(upnl)
            ap_raw = s.get("active_picks")
            ap = int(ap_raw) if ap_raw is not None and ap_raw != "" else 0
            if ap < 0:
                raise ValueError("active_picks < 0")
        except (TypeError, ValueError):
            bad_numeric.append(name)
            problems.append({"system": name, "reason": "invalid_numeric_fields"})

    ok = not problems
    return DashboardPayloadHealth(
        ok=ok,
        age_seconds=age_seconds,
        payload_stale=payload_stale,
        generated_at=str(generated_at) if generated_at is not None else None,
        missing_systems=missing,
        bad_numeric_systems=bad_numeric,
        problems=problems,
    )
