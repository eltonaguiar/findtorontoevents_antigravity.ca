"""
Strategy Emission Monitor — daily dormancy report.

Reads closed_picks.json + active_picks.json and for each known strategy/source_system
reports: last emission date, days since last emit, status (ACTIVE / STALE / DORMANT / BLOCKED).

Usage:
    python tools/strategy_emission_monitor.py               # print report
    python tools/strategy_emission_monitor.py --days 14     # change dormancy window (default 7)
    python tools/strategy_emission_monitor.py --json        # emit JSON instead of table
    python tools/strategy_emission_monitor.py --out reports/strategy_dormancy_$(date +%Y-%m-%d).md
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
CLOSED_PATH = REPO_ROOT / "alpha_engine/data/closed_picks.json"
ACTIVE_PATH = REPO_ROOT / "alpha_engine/data/active_picks.json"
GATES_PATH = REPO_ROOT / "audit_trail/quality_gates.py"

STALE_DAYS = 7    # warning threshold
DORMANT_DAYS = 14  # dormant threshold


def _load_blocked_strategies() -> set[str]:
    """Parse BLOCKED_SOURCE_SYSTEMS and BLOCKED_STRATEGIES from quality_gates.py."""
    blocked: set[str] = set()
    if not GATES_PATH.exists():
        return blocked
    text = GATES_PATH.read_text(encoding="utf-8", errors="replace")
    in_block = False
    for line in text.splitlines():
        stripped = line.strip()
        if "BLOCKED_SOURCE_SYSTEMS" in stripped and "=" in stripped:
            in_block = True
        elif "BLOCKED_STRATEGIES" in stripped and "=" in stripped:
            in_block = True
        elif in_block:
            if stripped.startswith("}"):
                in_block = False
                continue
            if stripped.startswith('"') or stripped.startswith("'"):
                name = stripped.split('"')[1] if '"' in stripped else stripped.split("'")[1]
                if name:
                    blocked.add(name)
    return blocked


def _last_emit_date(picks: list[dict], strategy: str) -> str | None:
    """Return ISO date string of most recent emit for the strategy, or None."""
    candidates: list[str] = []
    for p in picks:
        if p.get("strategy") == strategy or p.get("source_system") == strategy:
            for field in ("timestamp", "entry_date", "created_at", "exit_date", "closed_at"):
                val = p.get(field)
                if val and isinstance(val, str) and len(val) >= 10:
                    candidates.append(val[:10])
    return max(candidates) if candidates else None


def _days_ago(iso_date: str | None) -> int | None:
    if not iso_date:
        return None
    try:
        dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).days
    except ValueError:
        return None


def build_report(stale_days: int = STALE_DAYS, dormant_days: int = DORMANT_DAYS) -> list[dict]:
    closed = json.loads(CLOSED_PATH.read_text()) if CLOSED_PATH.exists() else []
    raw_active = json.loads(ACTIVE_PATH.read_text()) if ACTIVE_PATH.exists() else []
    active: list[dict] = raw_active if isinstance(raw_active, list) else list(raw_active.values())

    all_picks = closed + active
    blocked = _load_blocked_strategies()

    # Collect distinct strategy names
    strategies: set[str] = set()
    for p in all_picks:
        s = p.get("strategy") or p.get("source_system")
        if s:
            strategies.add(s)

    # Active pick count per strategy
    active_count: dict[str, int] = defaultdict(int)
    for p in active:
        s = p.get("strategy") or p.get("source_system") or ""
        if s:
            active_count[s] += 1

    rows: list[dict] = []
    for strat in sorted(strategies):
        last_closed = _last_emit_date(closed, strat)
        last_active = _last_emit_date(active, strat)
        last_any = max(filter(None, [last_closed, last_active]), default=None)
        days = _days_ago(last_any)

        is_blocked = strat in blocked
        if is_blocked:
            status = "BLOCKED"
        elif days is None:
            status = "UNKNOWN"
        elif days <= stale_days:
            status = "ACTIVE"
        elif days <= dormant_days:
            status = "STALE"
        else:
            status = "DORMANT"

        rows.append({
            "strategy": strat,
            "last_emit": last_any or "—",
            "days_ago": days,
            "active_picks": active_count.get(strat, 0),
            "status": status,
            "blocked": is_blocked,
        })

    # Sort: DORMANT first, then STALE, ACTIVE, BLOCKED/UNKNOWN
    order = {"DORMANT": 0, "STALE": 1, "ACTIVE": 2, "UNKNOWN": 3, "BLOCKED": 4}
    rows.sort(key=lambda r: (order.get(r["status"], 9), -(r["days_ago"] or 0)))
    return rows


def _status_icon(status: str) -> str:
    return {"ACTIVE": "[OK]", "STALE": "[WARN]", "DORMANT": "[DEAD]", "BLOCKED": "[BLOCK]", "UNKNOWN": "[?]"}.get(
        status, "?"
    )


def print_table(rows: list[dict], out: Path | None = None) -> None:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [
        f"# Strategy Emission Monitor — {today}",
        "",
        f"{'Strategy':<40} {'Last Emit':<12} {'Days':<6} {'Active':<7} Status",
        "-" * 80,
    ]
    for r in rows:
        icon = _status_icon(r["status"])
        days_str = str(r["days_ago"]) if r["days_ago"] is not None else "—"
        lines.append(
            f"{r['strategy']:<40} {r['last_emit']:<12} {days_str:<6} {r['active_picks']:<7} {icon} {r['status']}"
        )

    dormant = [r for r in rows if r["status"] == "DORMANT"]
    stale = [r for r in rows if r["status"] == "STALE"]
    active = [r for r in rows if r["status"] == "ACTIVE"]
    blocked = [r for r in rows if r["status"] == "BLOCKED"]

    lines += [
        "",
        "## Summary",
        f"- DORMANT (>{DORMANT_DAYS}d silent): **{len(dormant)}**",
        f"- STALE ({STALE_DAYS}–{DORMANT_DAYS}d): **{len(stale)}**",
        f"- ACTIVE (≤{STALE_DAYS}d): **{len(active)}**",
        f"- BLOCKED: **{len(blocked)}**",
        f"- Total strategies: **{len(rows)}**",
    ]

    if dormant:
        lines.append("")
        lines.append("## Dormant strategies (action needed)")
        for r in dormant:
            lines.append(f"- `{r['strategy']}` — last emit {r['last_emit']} ({r['days_ago']}d ago)")

    text = "\n".join(lines) + "\n"
    if out:
        out.write_text(text, encoding="utf-8")
        print(f"Report written to {out}", file=sys.stderr)
    else:
        print(text)


def main() -> None:
    parser = argparse.ArgumentParser(description="Strategy emission dormancy monitor")
    parser.add_argument("--days", type=int, default=STALE_DAYS, help="Stale threshold (default 7)")
    parser.add_argument("--dormant-days", type=int, default=DORMANT_DAYS, help="Dormant threshold (default 14)")
    parser.add_argument("--json", dest="as_json", action="store_true", help="Output JSON")
    parser.add_argument("--out", type=Path, help="Write to file instead of stdout")
    args = parser.parse_args()

    rows = build_report(stale_days=args.days, dormant_days=args.dormant_days)

    if args.as_json:
        print(json.dumps(rows, indent=2))
    else:
        print_table(rows, out=args.out)


if __name__ == "__main__":
    main()
