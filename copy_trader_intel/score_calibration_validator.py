#!/usr/bin/env python3
"""
Copy Trader Score Calibration Validator
=======================================

Validates that copy trader score families line up with realized outcomes.
This is intentionally opinionated and focused on the local audit payload.
"""

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PAYLOAD_PATH = ROOT / "audit_trail" / "data" / "dashboard_payload.json"
VARIATION_PATH = ROOT / "copy_trader_intel" / "data" / "variation_forward_test.json"
CONSENSUS_PATH = ROOT / "copy_trader_intel" / "data" / "consensus_active_picks.json"


def safe_float(value, default=0.0):
    try:
        return float(value or default)
    except (ValueError, TypeError):
        return default


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def is_copy_pick(pick):
    source = (pick.get("source_system") or "").lower()
    strategy = (pick.get("strategy") or "").lower()
    return (
        "copy_trader" in source
        or strategy.startswith("copy_hl_")
        or strategy.startswith("clone_")
        or strategy.startswith("hs_")
    )


def bucket_name(score):
    if score >= 70:
        return "70+"
    if score >= 50:
        return "50-69"
    if score >= 30:
        return "30-49"
    return "<30"


def summarize_rows(rows):
    pnls = [safe_float(row.get("pnl_pct")) for row in rows if safe_float(row.get("pnl_pct")) != 0]
    avg_score = sum(safe_float(row.get("score")) for row in rows) / len(rows) if rows else 0
    win_rate = sum(1 for pnl in pnls if pnl > 0) / len(pnls) if pnls else 0
    avg_pnl = sum(pnls) / len(pnls) if pnls else 0
    return {
        "count": len(rows),
        "with_pnl": len(pnls),
        "avg_score": round(avg_score, 2),
        "win_rate": round(win_rate, 3),
        "avg_pnl": round(avg_pnl, 3),
    }


def main():
    if not PAYLOAD_PATH.exists():
        print(f"[ERROR] Missing payload: {PAYLOAD_PATH}")
        return 1

    payload = load_json(PAYLOAD_PATH)
    active = payload.get("picks", {}).get("active", [])
    closed = payload.get("picks", {}).get("recent_closed", [])
    copy_rows = [pick for pick in active + closed if is_copy_pick(pick)]

    print("=" * 80)
    print("  COPY TRADER SCORE CALIBRATION")
    print("  " + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
    print("=" * 80)
    print(f"  Active picks: {len(active)}")
    print(f"  Closed picks: {len(closed)}")
    print(f"  Copy trader picks: {len(copy_rows)}")

    families = {}
    for family in (
        "copy_trader_intel",
        "copy_trader_highscore",
        "copy_trader_clones",
        "copy_trader_consensus",
        "copy_trader_variations",
    ):
        family_rows = [row for row in copy_rows if (row.get("source_system") or "").lower() == family]
        if family_rows:
            families[family] = summarize_rows(family_rows)

    print("\nFamily Summary")
    for family, stats in families.items():
        print(
            f"  {family:<24} count={stats['count']:>3} "
            f"with_pnl={stats['with_pnl']:>3} avg_score={stats['avg_score']:>5.1f} "
            f"wr={stats['win_rate']*100:>5.1f}% avg_pnl={stats['avg_pnl']:>+6.2f}%"
        )

    copy_closed = [row for row in closed if is_copy_pick(row) and safe_float(row.get("pnl_pct")) != 0]
    buckets = defaultdict(list)
    for row in copy_closed:
        buckets[bucket_name(safe_float(row.get("score")))].append(row)

    print("\nCopy Trader Closed Buckets")
    for name in ("70+", "50-69", "30-49", "<30"):
        stats = summarize_rows(buckets.get(name, []))
        if stats["count"] == 0:
            continue
        print(
            f"  {name:<5} count={stats['count']:>3} with_pnl={stats['with_pnl']:>3} "
            f"wr={stats['win_rate']*100:>5.1f}% avg_pnl={stats['avg_pnl']:>+6.2f}%"
        )

    issues = []

    high_stats = summarize_rows(buckets.get("70+", []))
    low_stats = summarize_rows(buckets.get("<30", []))
    if high_stats["with_pnl"] >= 10 and low_stats["with_pnl"] >= 5:
        if high_stats["avg_pnl"] <= low_stats["avg_pnl"]:
            issues.append(
                "Copy-trader 70+ bucket is not outperforming the <30 bucket."
            )

    clone_stats = families.get("copy_trader_clones")
    if clone_stats and clone_stats["with_pnl"] >= 10 and clone_stats["win_rate"] >= 0.55:
        if clone_stats["avg_score"] < 30:
            issues.append(
                "Clone family is still under-scored (<30 avg) despite positive sample quality."
            )

    highscore_stats = families.get("copy_trader_highscore")
    if highscore_stats and highscore_stats["with_pnl"] >= 10 and highscore_stats["win_rate"] >= 0.50:
        if highscore_stats["avg_score"] < 35:
            issues.append(
                "Highscore family is still under-scored (<35 avg) despite decent realized outcomes."
            )

    consensus_stats = families.get("copy_trader_consensus")
    intel_stats = families.get("copy_trader_intel")
    if consensus_stats and intel_stats:
        if consensus_stats["avg_score"] <= intel_stats["avg_score"]:
            issues.append(
                "Consensus picks are not ranking above plain copy_trader_intel picks."
            )

    if VARIATION_PATH.exists():
        variation = load_json(VARIATION_PATH)
        summary = variation.get("summary", {})
        total_variation_trades = int(summary.get("total_trades", 0) or 0)
        if total_variation_trades == 0:
            print("\n[WARN] variation_forward_test.json has zero closed trades. Variation boosts remain disabled.")

    if CONSENSUS_PATH.exists():
        consensus_data = load_json(CONSENSUS_PATH)
        print(
            "\nConsensus Builder"
            f"\n  total_consensus_picks={consensus_data.get('total_consensus_picks', 0)}"
            f"\n  stats={consensus_data.get('stats', {})}"
        )

    print("\nResult")
    if issues:
        for issue in issues:
            print(f"  [FAIL] {issue}")
        return 1

    print("  [PASS] Copy trader score calibration looks logically consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
