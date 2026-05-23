#!/usr/bin/env python3
"""PR-F (2026-05-12) — Audit BLACKLISTED_STRATEGIES consistency.

For each entry in BLACKLISTED_STRATEGIES emit:
    strategy | active_n | historical_n | leaderboard_rank

Exits 1 if any blacklisted strategy still appears in the leaderboard top
half (i.e. render-time gate missing). Memory ref:
feedback_gate_at_execution_not_generation.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from alpha_engine.config import BLACKLISTED_STRATEGIES
except Exception as exc:  # pragma: no cover
    print(f"ERROR: cannot import BLACKLISTED_STRATEGIES: {exc}", file=sys.stderr)
    sys.exit(2)


def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _active_counts() -> dict[str, int]:
    counts: dict[str, int] = {s: 0 for s in BLACKLISTED_STRATEGIES}
    data = _load_json(ROOT / "alpha_engine/data/active_picks.json") or {}
    picks = data.get("picks") if isinstance(data, dict) else None
    if not isinstance(picks, list):
        picks = data if isinstance(data, list) else []
    for p in picks:
        nm = (p.get("strategy") or p.get("source_system") or "").strip()
        if nm in counts:
            counts[nm] += 1
    return counts


def _historical_counts() -> dict[str, int]:
    counts: dict[str, int] = {s: 0 for s in BLACKLISTED_STRATEGIES}
    data = _load_json(ROOT / "audit_dashboard/data/dashboard_data.json") or {}
    systems = data.get("systems") or {}
    if isinstance(systems, dict):
        for name, row in systems.items():
            if name in counts:
                counts[name] += int(row.get("total", row.get("trades", 0)) or 0)
    for row in data.get("recent_closed", []) or []:
        nm = (row.get("strategy") or row.get("source_system") or "").strip()
        if nm in counts:
            counts[nm] += 1
    return counts


def _leaderboard_ranks() -> tuple[dict[str, int], dict[str, bool]]:
    ranks: dict[str, int] = {s: -1 for s in BLACKLISTED_STRATEGIES}
    flagged: dict[str, bool] = {s: False for s in BLACKLISTED_STRATEGIES}
    data = _load_json(ROOT / "audit_dashboard/data/dashboard_data.json") or {}
    lb = data.get("strategy_leaderboard") or data.get("leaderboard") or []
    if not isinstance(lb, list):
        return ranks, flagged
    for i, row in enumerate(lb, start=1):
        nm = (row.get("strategy") or row.get("name") or "").strip()
        if nm in ranks and ranks[nm] == -1:
            ranks[nm] = i
            flagged[nm] = bool(row.get("is_blacklisted", False))
    return ranks, flagged


def main() -> int:
    active = _active_counts()
    hist = _historical_counts()
    ranks, flagged = _leaderboard_ranks()

    print(f"{'strategy':<32} {'active_n':>10} {'historical_n':>14} {'leaderboard_rank':>18} {'flagged':>9}")
    print("-" * 90)
    leak = False
    for s in BLACKLISTED_STRATEGIES:
        r = ranks[s]
        rdisp = "—" if r < 0 else str(r)
        fdisp = "yes" if flagged[s] else ("n/a" if r < 0 else "NO")
        print(f"{s:<32} {active[s]:>10} {hist[s]:>14} {rdisp:>18} {fdisp:>9}")
        # Leak: appears in leaderboard AND not flagged is_blacklisted
        if r > 0 and not flagged[s]:
            leak = True

    if leak:
        print("\nFAIL: blacklisted strategy in leaderboard without is_blacklisted flag.")
        return 1
    print("\nOK: every blacklisted strategy is either absent or flagged is_blacklisted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
