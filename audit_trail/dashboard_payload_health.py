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
    optional_missing: list[str] = field(default_factory=list)
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
        if self.optional_missing:
            lines.append(
                f"OPTIONAL sources with no rows yet (warning, not failure): {self.optional_missing}"
            )
        if self.bad_numeric_systems:
            lines.append(f"BAD numeric fields: {self.bad_numeric_systems}")
        return lines


# Sources that are registered so the dashboard can display them, but whose
# producers are best-effort (network / API-key dependent, run with `|| echo
# warning` in audit-dashboard.yml). A registered source that has produced zero
# rows yet cannot emit a payload row, so its absence is a WARNING, not a broken
# feed. Do NOT add healthy sources here — this exists so the Feed Health gate
# fails only on real wiring regressions. Review after 7 consecutive days of rows.
_OPTIONAL_SYSTEMS: set[str] = {
    "pm_kalshi_re_signals",      # alpha_engine/kalshi_signals.py
    "pm_polymarket_re_signals",  # alpha_engine/polymarket_signals.py
    # Dead-by-design / ephemeral prediction-market sources. These are in
    # dashboard_generator._GHOST_SYSTEMS (pm_momentum_signals) or produced only
    # inside the audit-dashboard job and never committed (pm_whale_signals /
    # pm_kalshi_signals, gitignored `**/data/*_signals.json`), so they cannot
    # emit a payload row on most runs. Requiring them failed Feed Health every
    # hour (MISSING system rows ['pm_momentum_signals'], run 19:39Z 2026-11-16).
    "pm_momentum_signals",       # prediction_market_agents/momentum_signals.json (GHOST)
    "pm_whale_signals",          # prediction_market_agents/whale_signals.json (ephemeral)
    "pm_kalshi_signals",         # prediction_market_agents/kalshi_signals.json (ephemeral)
}


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

    missing: list[str] = []
    optional_missing: list[str] = []
    for n in sorted(set(registered)):
        if n in names_in_payload or n in _HIDDEN_SYSTEMS or n in _GHOST_SYSTEMS:
            continue
        if n in _OPTIONAL_SYSTEMS:
            optional_missing.append(n)
            continue
        missing.append(n)
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
        optional_missing=optional_missing,
        bad_numeric_systems=bad_numeric,
        problems=problems,
    )
