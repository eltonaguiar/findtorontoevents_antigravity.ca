"""
Strategy block expiry audit tool.

Reads BLOCKED_ASSET_STRATEGY_PAIRS from quality_gates.py comments and flags
pairs that have been blocked for > 90 days without a review date.

Per swarm recommendation (deepseek 2026-05-18): blocked strategies that remain
inactive for 90+ days should be reviewed and either:
  - Re-verified still broken (reset timer)
  - Promoted to ARCHIVED_FAILURES (never comes back)
  - Unblocked with a mutation plan

Usage:
    python tools/research/strategy_block_expiry_audit.py
    python tools/research/strategy_block_expiry_audit.py --expiry-days 60
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
QUALITY_GATES_PATH = REPO_ROOT / "audit_trail" / "quality_gates.py"
EXPIRY_DAYS = 90

# Known block dates from inline comments (YYYY-MM-DD)
_KNOWN_DATES: dict[str, str] = {
    "myfxbook_retail_contrarian": "2026-05-11",
    "goldmine_1x_consensus": "2026-04-18",
    "goldmine_2x_consensus": "2026-04-18",
    "goldmine_3x_consensus": "2026-04-18",
    "goldmine_4x_consensus": "2026-04-18",
    "ml_enhanced_APEUSDT_1d_D_ensemble_stack": "2026-04-22",
    "quan_engine_scalp": "2026-04-22",
    "penny_deep_oversold": "2026-04-18",
    "forex_carry_momentum": "2026-05-02",
    "forex_carry_g10": "2026-05-17",
    "MomentumEMA": "2026-01-01",       # no date in code — use conservative estimate
    "volume_spike_breakout": "2026-01-01",
    "ML Ranker": "2026-04-01",
    "cta_replicator": "2026-05-17",
    "futures_momentum": "2026-05-17",
    "multi_asset_copytrader": "2026-05-17",
}


def parse_blocked_pairs() -> list[tuple[str, str]]:
    """Extract (asset_class, strategy) tuples from BLOCKED_ASSET_STRATEGY_PAIRS in quality_gates.py."""
    if not QUALITY_GATES_PATH.exists():
        return []

    text = QUALITY_GATES_PATH.read_text(encoding="utf-8", errors="replace")
    # Find the BLOCKED_ASSET_STRATEGY_PAIRS block
    m = re.search(r"BLOCKED_ASSET_STRATEGY_PAIRS\s*=\s*\{(.*?)\}", text, re.DOTALL)
    if not m:
        return []

    block = m.group(1)
    # Extract ("CLASS", "strategy") tuples
    pattern = re.compile(r'\(\s*"([^"]+)"\s*,\s*"([^"]+)"\s*\)')
    pairs = pattern.findall(block)
    return [(ac, strat) for ac, strat in pairs]


def audit_blocks(expiry_days: int = EXPIRY_DAYS) -> list[dict]:
    """
    For each blocked pair, determine if it's past the expiry threshold.

    Returns list of audit records, sorted by days_blocked descending.
    """
    pairs = parse_blocked_pairs()
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=expiry_days)

    records = []
    for ac, strat in pairs:
        blocked_date_str = _KNOWN_DATES.get(strat, "2026-01-01")
        try:
            blocked_dt = datetime.strptime(blocked_date_str, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            blocked_dt = cutoff  # conservative: treat as expired

        days_blocked = (now - blocked_dt).days
        expired = blocked_dt <= cutoff
        status = "EXPIRED" if expired else "ACTIVE"

        records.append({
            "asset_class": ac,
            "strategy": strat,
            "blocked_since": blocked_date_str,
            "days_blocked": days_blocked,
            "status": status,
            "recommendation": (
                "REVIEW: re-verify or archive" if expired else "OK"
            ),
        })

    records.sort(key=lambda r: r["days_blocked"], reverse=True)
    return records


def print_audit(records: list[dict], expiry_days: int = EXPIRY_DAYS) -> None:
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    expired = [r for r in records if r["status"] == "EXPIRED"]
    active = [r for r in records if r["status"] == "ACTIVE"]

    print(f"\n{'='*68}")
    print(f"Strategy Block Expiry Audit — {now_str} (expiry={expiry_days}d)")
    print(f"{'='*68}")

    if expired:
        print(f"\n EXPIRED (>{expiry_days}d without review) — {len(expired)} pairs:")
        print(f"  {'Asset Class':<12} {'Strategy':<45} {'Days':>5}")
        print(f"  {'-'*65}")
        for r in expired:
            print(f"  {r['asset_class']:<12} {r['strategy']:<45} {r['days_blocked']:>5}d")

    if active:
        print(f"\n ACTIVE (<{expiry_days}d) — {len(active)} pairs:")
        print(f"  {'Asset Class':<12} {'Strategy':<45} {'Days':>5}")
        print(f"  {'-'*65}")
        for r in active:
            print(f"  {r['asset_class']:<12} {r['strategy']:<45} {r['days_blocked']:>5}d")

    print(f"\nSummary: {len(expired)} expired / {len(active)} active / {len(records)} total")
    if expired:
        print("\nAction: Run strategy investigation per docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md")
        print("        then either reset the block date or move to ARCHIVED_FAILURES.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Strategy block expiry audit")
    parser.add_argument("--expiry-days", type=int, default=EXPIRY_DAYS)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    records = audit_blocks(args.expiry_days)

    out = REPO_ROOT / "reports" / "strategy_block_expiry_audit.json"
    out.write_text(json.dumps(records, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(records, indent=2))
    else:
        print_audit(records, args.expiry_days)
        print(f"\nJSON: {out}")


if __name__ == "__main__":
    main()
