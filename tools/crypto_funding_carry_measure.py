#!/usr/bin/env python3
"""Measure the crypto funding-rate CARRY YIELD from our own archive (plan row R2b).

Pre-registered row: R2b of notes/per-asset-class-plan-copilot-2026-11-23.

WHAT THIS MEASURES, AND WHAT IT DOES NOT
    It measures the FUNDING YIELD on a delta-neutral position: short perp +
    long spot. If funding is positive the short perp receives it, so the yield to
    the position is the funding stream itself.

    It is NOT a backtest P&L. A realised delta-neutral return also carries:
      * basis drift between spot and perp
      * four executions (open/close x 2 legs) of fees and slippage
      * liquidation/venue risk during a deleveraging event
    All three are reported or bounded here rather than assumed away.

WHY THIS FILE EXISTS
    alpha_engine/funding_rate_arb.py states in its own header:
        "Research: Funding rate arbitrage yields 5-15% monthly with very low risk."
    That is an imported magnitude of exactly the kind this programme has banned.
    The archive we already hold is enough to measure the real number.

THE HONEST FRAMING UP FRONT
    Funding carry is a SHORT-VOLATILITY trade. It pays steadily and then loses
    sharply when funding flips negative during a deleveraging. So the metric that
    decides it is NOT Sharpe -- it is the worst cumulative drawdown of the funding
    stream and the fraction of intervals spent negative. Both are printed.

Read-only. Not investment advice.

Usage:
    python3 tools/crypto_funding_carry_measure.py
"""
from __future__ import annotations

import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE = ROOT / "data" / "funding_rate_archive"
OUT = ROOT / "reports" / "crypto_funding_carry.json"

INTERVALS_PER_DAY = 3            # 8h funding
DAYS_PER_YEAR = 365
# Measured CRYPTO execution cost already in the repo (measured_cost_recost):
# carry_execution_cost.py = 10bp fee/side + 2.6bp measured slippage.
COST_BP_PER_SIDE = 12.6
LEGS_PER_ROUND_TRIP = 2          # spot leg + perp leg
SIDES_PER_TRIP = 2               # open + close
HURDLE = 0.0432


def load(sym_path: Path) -> list[dict]:
    recs = []
    for line in sym_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        fr, t = r.get("funding_rate"), r.get("funding_time_ms")
        if fr is None or t is None:
            continue
        try:
            recs.append({"t": int(t), "fr": float(fr)})
        except (TypeError, ValueError):
            continue
    recs.sort(key=lambda r: r["t"])
    return recs


def span_days(recs: list[dict]) -> float:
    if len(recs) < 2:
        return 0.0
    return (recs[-1]["t"] - recs[0]["t"]) / 86_400_000


def cumulative_dd(frs: list[float]) -> float:
    """Worst drawdown of the cumulative funding stream, in rate units."""
    cum = peak = mdd = 0.0
    for f in frs:
        cum += f
        peak = max(peak, cum)
        mdd = min(mdd, cum - peak)
    return mdd


def main() -> int:
    if not ARCHIVE.is_dir():
        print(f"::error:: no archive at {ARCHIVE}")
        return 2
    files = sorted(ARCHIVE.glob("*.jsonl"))
    if not files:
        print("::error:: archive empty")
        return 2

    per_symbol, all_pooled = [], []
    for f in files:
        recs = load(f)
        if len(recs) < 100:
            continue
        frs = [r["fr"] for r in recs]
        days = span_days(recs)
        # annualise the MEAN interval funding (x3 per day x365)
        ann = statistics.mean(frs) * INTERVALS_PER_DAY * DAYS_PER_YEAR
        per_symbol.append({
            "symbol": f.stem,
            "n_intervals": len(frs),
            "span_days": round(days, 1),
            "mean_funding_8h": statistics.mean(frs),
            "median_funding_8h": statistics.median(frs),
            "pct_positive": sum(1 for x in frs if x > 0) / len(frs),
            "p05": sorted(frs)[int(0.05 * len(frs))],
            "p95": sorted(frs)[int(0.95 * len(frs))],
            "ann_yield_gross": ann,
            "cum_funding": sum(frs),
            "cum_funding_maxdd": cumulative_dd(frs),
        })
        all_pooled.extend(frs)

    if not per_symbol:
        print("::error:: no symbol had enough intervals")
        return 1

    # equal-weight portfolio across symbols = pooled mean
    gross_ann = statistics.mean(all_pooled) * INTERVALS_PER_DAY * DAYS_PER_YEAR
    round_trip_cost = (COST_BP_PER_SIDE * LEGS_PER_ROUND_TRIP * SIDES_PER_TRIP) / 10_000
    # cost is paid once per position held ~1 year
    net_ann = gross_ann - round_trip_cost

    days_covered = max(s["span_days"] for s in per_symbol)
    pct_pos = sum(1 for x in all_pooled if x > 0) / len(all_pooled)
    worst_dd = min(s["cum_funding_maxdd"] for s in per_symbol)

    out = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "row": "R2b",
        "kind": "FUNDING_YIELD_MEASUREMENT_NOT_BACKTEST_PNL",
        "source": "data/funding_rate_archive/*.jsonl (okx), 8h funding",
        "n_symbols": len(per_symbol),
        "n_intervals_pooled": len(all_pooled),
        "span_days": round(days_covered, 1),
        "gross_ann_yield": round(gross_ann, 6),
        "round_trip_cost": round(round_trip_cost, 6),
        "net_ann_yield": round(net_ann, 6),
        "hurdle": HURDLE,
        "pct_positive_intervals": round(pct_pos, 4),
        "worst_cum_funding_drawdown": round(worst_dd, 6),
        "clears_hurdle_gross": gross_ann > HURDLE,
        "clears_hurdle_net": net_ann > HURDLE,
        "cost_basis": {
            "per_side_bp": COST_BP_PER_SIDE,
            "legs": LEGS_PER_ROUND_TRIP, "sides": SIDES_PER_TRIP,
            "source": "measured_cost_recost: 10bp fee + 2.6bp slippage",
        },
        "not_modelled": [
            "basis drift between spot and perp",
            "liquidation/venue risk during deleveraging",
            "funding is realised on notional held, so leverage scales both ways",
        ],
        "per_symbol": per_symbol,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))

    print(f"MEASURED  {len(per_symbol)} symbols, {len(all_pooled)} intervals, "
          f"{days_covered:.0f} days of 8h funding")
    print(f"{'SYM':10} {'n':>5} {'ann GROSS':>10} {'%pos':>6} {'p05':>10} "
          f"{'cum':>9} {'cumDD':>9}")
    for s in per_symbol:
        print(f"{s['symbol']:10} {s['n_intervals']:>5} {s['ann_yield_gross']:>9.2%} "
              f"{s['pct_positive']:>6.0%} {s['p05']:>10.2e} "
              f"{s['cum_funding']:>9.2%} {s['cum_funding_maxdd']:>9.2%}")
    print()
    print(f"POOLED gross annual yield : {gross_ann:>8.2%}")
    print(f"round-trip cost (2 legs x2 sides x {COST_BP_PER_SIDE}bp) : "
          f"{round_trip_cost:.2%}")
    print(f"NET annual yield         : {net_ann:>8.2%}   [hurdle {HURDLE:.2%}]")
    print(f"intervals positive       : {pct_pos:>8.1%}")
    print(f"worst cum funding DD     : {worst_dd:>8.2%}")
    print(f"clears hurdle gross={out['clears_hurdle_gross']} "
          f"net={out['clears_hurdle_net']}")
    print(f"written: {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
