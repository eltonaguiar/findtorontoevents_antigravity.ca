"""
Weekly Elite Pick Filter — outputs recommended picks for real-money consideration.

Backed by OOS-validated edge filters in audit_trail/edge_filters.py
(5000-pick dataset, chronological 70/30 IS/OOS split, 500-iter bootstrap CI).

Usage:
    python tools/weekly_filter_picks.py
    python tools/weekly_filter_picks.py --output reports/weekly_picks_2026-05-16.json
    python tools/weekly_filter_picks.py --class COMMODITY
    python tools/weekly_filter_picks.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

# Systems with proven Tier 2+ performance (n≥10, PF≥1.5, WR≥50%)
# Source: reports/statistical_edge_analysis_2026-05-16.md
ELITE_SYSTEMS: dict[str, dict] = {
    "aggregated_picks": {"pf": 5.35, "wr": 76.3, "mdd": 88.05, "classes": ["EQUITY", "CRYPTO", "COMMODITY"]},
    "multi_asset_copytrader": {"pf": 3.14, "wr": 66.0, "mdd": 85.88, "classes": ["EQUITY", "COMMODITY", "FUTURES", "FOREX"]},
    "multi_asset_cot": {"pf": 4.72, "wr": 79.4, "mdd": 79.97, "classes": ["COMMODITY"]},
    "signal_validation": {"pf": 4.70, "wr": 59.5, "mdd": 8.14, "classes": ["CRYPTO", "FOREX"]},
    "kimi_signal_tracking": {"pf": 5.43, "wr": 75.0, "mdd": 4.0, "classes": ["CRYPTO", "FOREX"]},
    "ml_crypto_pred_v12": {"pf": 2.53, "wr": 55.6, "mdd": 11.0, "classes": ["CRYPTO"]},
    "claude_gainer": {"pf": 2.23, "wr": 56.2, "mdd": 33.48, "classes": ["CRYPTO"]},
    "mega_mutation": {"pf": 2.43, "wr": 58.8, "mdd": 44.59, "classes": ["CRYPTO"]},
}

# Elite strategies WITHIN aggregated_picks — OOS verified (5,000-pick pre-registered split)
# Source: reports/peer_notes/minimax_corrected_VERIFIED_2026-05-16.md
ELITE_STRATEGIES: dict[str, dict] = {
    "AuditEnsemble_LONG":              {"n": 104, "wr": 94.2, "pf": 37.79},
    "Multi-Timeframe Trend Alignment": {"n": 76,  "wr": 90.8, "pf": 21.2},
    "VWAP Deviation Scalp":            {"n": 35,  "wr": 97.1, "pf": 119.0},
    "RSI Divergence Scalp":            {"n": 24,  "wr": 83.3, "pf": 9.86},
}

# Strategies to block regardless of source_system passing
# Source: HC filter OOS backtest 2026-05-16 (below 50% WR floor)
BLOCKED_STRATEGIES: set[str] = {
    "Bollinger Band Squeeze Breakout",   # WR=42.1%, PF=1.31 — below floor
    "enhanced_ml_A_xgboost",            # WR=35.9% within alpha_engine cluster
}

# Systems confirmed sub-floor — exclude from weekly filter
SUB_FLOOR_SYSTEMS = {
    "alpha_engine_fast",
    "rapid_fire",
    "super_signals",
    "multi_asset",
    "mutation_lab",
    "dna_rapid_fire_mutations",
    "paper_trading",
    "fast_stocks_competition",
    "goldmine_stocks",
}

# Asset classes cleared for real-money allocation
REAL_MONEY_CLASSES = {"EQUITY", "COMMODITY"}

# Building classes — small allocation only (n<100 on all elite systems)
BUILDING_CLASSES = {"CRYPTO"}

# Blocked classes
BLOCKED_CLASSES = {"FOREX", "BOND", "FUTURES", "ETF"}

# Per-class max allocation (fraction of portfolio, Quarter-Kelly)
MAX_ALLOC: dict[str, float] = {
    "COMMODITY": 0.02,   # 2%
    "EQUITY": 0.015,     # 1.5%
    "CRYPTO": 0.005,     # 0.5% (building)
    "ETF": 0.005,
    "FOREX": 0.0,        # blocked
    "BOND": 0.0,
    "FUTURES": 0.0,
}

# Quality gates
MIN_CONFIDENCE = 0.65
MIN_RR = 2.0
MIN_CONFIDENCE_CRYPTO = 0.70  # tighter for crypto (more noise)


def load_picks(data_dir: Path) -> list[dict[str, Any]]:
    # Primary: active_picks.json (live, has source_system + asset_class)
    candidates = [
        data_dir / "active_picks.json",
        data_dir / "active_picks_fast.json",
        data_dir / "live_forward_test_picks.json",
        data_dir / "live_scan_now.json",
        data_dir / "last_scan.json",
    ]
    for path in candidates:
        if path.exists():
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                return raw
            picks = raw.get("picks", raw.get("active_picks", raw.get("raw_signals", [])))
            if picks:
                return picks
    return []


def get_spy_return() -> float | None:
    spy_file = ROOT / "alpha_engine" / "data" / "spy_20d_return.json"
    if not spy_file.exists():
        return None
    try:
        data = json.loads(spy_file.read_text(encoding="utf-8"))
        return float(data.get("spy_20d_return_pct", 0))
    except (ValueError, KeyError, TypeError):
        return None


def score_pick(pick: dict[str, Any], spy_return: float | None) -> dict[str, Any] | None:
    source = pick.get("source_system", pick.get("system", pick.get("strategy", "")))
    symbol = pick.get("symbol", "")
    asset_class = pick.get("asset_class", pick.get("category", "UNKNOWN")).upper()
    direction = pick.get("direction", "LONG").upper()
    confidence = float(pick.get("confidence", 0) or 0)
    rr = float(pick.get("risk_reward", 0) or 0)

    # Blocked class
    if asset_class in BLOCKED_CLASSES:
        return None

    # Sub-floor system
    if source in SUB_FLOOR_SYSTEMS:
        return None

    # Elite system gate
    if source not in ELITE_SYSTEMS:
        return None

    # Blocked strategy gate (even if source_system passes)
    strategy = pick.get("strategy", "")
    if strategy in BLOCKED_STRATEGIES:
        return None

    # Strategy-level boost for aggregated_picks: prefer elite strategies
    # (non-elite strategies from aggregated_picks still pass but get lower alloc)
    is_elite_strategy = source == "aggregated_picks" and strategy in ELITE_STRATEGIES

    # CRYPTO SHORT block: OOS shows WR=30.3%, PF=0.90 — net negative after costs
    if asset_class == "CRYPTO" and direction == "SHORT":
        return None

    # Confidence gate (tighter for CRYPTO)
    min_conf = MIN_CONFIDENCE_CRYPTO if asset_class == "CRYPTO" else MIN_CONFIDENCE
    if confidence < min_conf:
        return None

    # Confidence anti-overfit gate: 0.80-0.90 is the actual danger zone (OOS PF=0.96)
    if 0.80 <= confidence <= 0.90:
        return None

    # RR gate
    if rr < MIN_RR:
        return None

    # ETF regime gate: only LONG when SPY 20d > 0
    if asset_class == "ETF" and direction == "LONG" and spy_return is not None and spy_return <= 0:
        return None

    # Compute allocation size
    max_alloc = MAX_ALLOC.get(asset_class, 0.0)
    if max_alloc == 0.0:
        return None

    system_info = ELITE_SYSTEMS[source]
    # Reduce size for high-MDD systems
    mdd = system_info.get("mdd", 50.0)
    size_adj = 1.0
    if mdd > 40:
        size_adj = 0.33
    elif mdd > 20:
        size_adj = 0.5
    # Boost for elite strategies within aggregated_picks (WR 90-97%)
    if is_elite_strategy:
        size_adj = min(size_adj * 1.5, 1.0)

    alloc_pct = max_alloc * size_adj

    strat_info = ELITE_STRATEGIES.get(strategy, {})
    return {
        "symbol": symbol,
        "asset_class": asset_class,
        "direction": direction,
        "source_system": source,
        "strategy": strategy,
        "is_elite_strategy": is_elite_strategy,
        "confidence": confidence,
        "risk_reward": rr,
        "entry_price": pick.get("entry_price"),
        "take_profit": pick.get("take_profit"),
        "stop_loss": pick.get("stop_loss"),
        "alloc_pct": round(alloc_pct * 100, 3),
        "system_pf": system_info["pf"],
        "system_wr": system_info["wr"],
        "system_mdd": mdd,
        "strategy_wr": strat_info.get("wr"),
        "strategy_pf": strat_info.get("pf"),
        "real_money_class": asset_class in REAL_MONEY_CLASSES,
        "timestamp": pick.get("timestamp", pick.get("signal_timestamp")),
    }


def run_filter(
    asset_class_filter: str | None = None,
    dry_run: bool = False,
    output_path: str | None = None,
) -> dict[str, Any]:
    data_dir = ROOT / "alpha_engine" / "data"
    picks = load_picks(data_dir)
    spy_return = get_spy_return()

    results: list[dict] = []
    skipped = 0
    for pick in picks:
        scored = score_pick(pick, spy_return)
        if scored is None:
            skipped += 1
            continue
        if asset_class_filter and scored["asset_class"] != asset_class_filter.upper():
            continue
        results.append(scored)

    # Sort by confidence * system_pf (composite score)
    results.sort(key=lambda x: -(x["confidence"] * x["system_pf"]))

    # De-dup by (symbol, entry_price, take_profit, stop_loss) triplet first — prevents
    # re-emission artifacts (same position emitted on update ticks) from inflating WR/PF.
    # Then de-dup by symbol+direction keeping highest-scored to limit concentration.
    triplet_seen: set[tuple] = set()
    triplet_deduped: list[dict] = []
    for r in results:
        triplet = (r["symbol"], r.get("entry_price"), r.get("take_profit"), r.get("stop_loss"))
        if triplet not in triplet_seen:
            triplet_seen.add(triplet)
            triplet_deduped.append(r)

    seen: set[str] = set()
    deduped: list[dict] = []
    for r in triplet_deduped:
        key = f"{r['symbol']}_{r['direction']}"
        if key not in seen:
            seen.add(key)
            deduped.append(r)

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "spy_20d_return_pct": spy_return,
        "total_raw_picks": len(picks),
        "passed_filter": len(deduped),
        "skipped": skipped,
        "filter_config": {
            "elite_systems": list(ELITE_SYSTEMS.keys()),
            "sub_floor_excluded": list(SUB_FLOOR_SYSTEMS),
            "min_confidence": MIN_CONFIDENCE,
            "min_rr": MIN_RR,
            "real_money_classes": list(REAL_MONEY_CLASSES),
        },
        "picks": deduped,
    }

    if not dry_run and output_path:
        Path(output_path).write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        print(f"Wrote {len(deduped)} elite picks to {output_path}")

    return out


def main() -> None:
    p = argparse.ArgumentParser(description="Weekly elite pick filter for real-money consideration")
    p.add_argument("--output", "-o", help="JSON output path")
    p.add_argument("--class", dest="asset_class", help="Filter to specific asset class (EQUITY, COMMODITY, CRYPTO...)")
    p.add_argument("--dry-run", action="store_true", help="Print results but do not write file")
    args = p.parse_args()

    result = run_filter(
        asset_class_filter=args.asset_class,
        dry_run=args.dry_run,
        output_path=args.output,
    )

    picks = result["picks"]
    print(f"\n{'='*60}")
    print(f"WEEKLY ELITE PICKS — {result['generated_at'][:10]}")
    print(f"{'='*60}")
    print(f"Input picks: {result['total_raw_picks']} | Passed filter: {result['passed_filter']} | Skipped: {result['skipped']}")
    print(f"SPY 20d return: {result['spy_20d_return_pct']}%\n")

    if not picks:
        print("No picks passed the elite filter this week.")
        print("Check if alpha_engine data files are fresh (run `python alpha_engine/production_scanner.py`)")
        return

    real_money = [x for x in picks if x["real_money_class"]]
    building = [x for x in picks if not x["real_money_class"]]

    if real_money:
        print("REAL-MONEY PICKS (EQUITY / COMMODITY):")
        print(f"{'Symbol':12s} {'Class':12s} {'Dir':6s} {'Conf':6s} {'RR':5s} {'Alloc':7s} {'System'}")
        print("-" * 75)
        for pk in real_money:
            print(f"{pk['symbol']:12s} {pk['asset_class']:12s} {pk['direction']:6s} "
                  f"{pk['confidence']:.2f}   {pk['risk_reward']:.1f}   "
                  f"{pk['alloc_pct']:.2f}%   {pk['source_system']} (PF={pk['system_pf']})")

    if building:
        print(f"\nBUILDING PICKS (CRYPTO — small allocation only):")
        print(f"{'Symbol':12s} {'Dir':6s} {'Conf':6s} {'RR':5s} {'Alloc':7s} {'System'}")
        print("-" * 65)
        for pk in building:
            print(f"{pk['symbol']:12s} {pk['direction']:6s} {pk['confidence']:.2f}   "
                  f"{pk['risk_reward']:.1f}   {pk['alloc_pct']:.2f}%   "
                  f"{pk['source_system']} (PF={pk['system_pf']})")

    print(f"\n{'='*60}")
    print("ALLOCATION RULES:")
    print("  • Real-money picks: size as shown (fraction of portfolio)")
    print("  • Building picks: half the shown allocation until n≥100")
    print("  • Drawdown halt: stop all new picks if portfolio DD > 30%")
    print("  • Stop-loss: hard stop at signal_validation SL price")
    print("  • NOT FINANCIAL ADVICE — research surface only")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
