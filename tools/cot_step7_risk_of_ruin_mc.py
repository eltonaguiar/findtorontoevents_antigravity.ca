#!/usr/bin/env python3
"""COT Step 7 — Risk-of-Ruin Monte Carlo.

Bootstrap 10,000 simulated 50-trade sequences from the
`cot_positioning + CT=F` 100-pick pnl_pct distribution. For each
sequence, compute drawdown trajectory + final P&L at $5k / $10k / $25k
starter capital tiers at 1-contract sizing on a $35k notional cotton
contract ($5/tick, ~$1,200-2,000 initial margin, $1,000-1,500 maintenance).

Pass criteria (per `reports/cot_paper_pilot_testing_plan_2026-05-12.md`):
  - $10k starter: probability of margin call < 5% over 50-trade sequence
  - $25k starter: probability of margin call < 1%

NFA — research surface only. The Monte Carlo input is a HINDSIGHT
distribution (the 100 closed picks). If forward outcomes deviate from
the empirical distribution (especially the fold_1 regime outlier per Step 3),
the ruin probability is understated.

Usage:
  python tools/cot_step7_risk_of_ruin_mc.py                     # default 10k sims
  python tools/cot_step7_risk_of_ruin_mc.py --sims 100000
  python tools/cot_step7_risk_of_ruin_mc.py --seq-trades 100
"""
from __future__ import annotations

import argparse
import json
import os
import random
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import pymysql
except ImportError:
    print("ERROR: pymysql not installed", file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent

# Contract spec — matches alpha_engine/strategies/cot_paper_pilot.py
CONTRACT_NOTIONAL_LBS = 50_000
TICK_USD = 5.0
ROUND_TRIP_COST_USD = 10.0  # commission + slippage per round trip
BASE_PRICE_USD_PER_LB = 0.70  # ~$35k notional
NOTIONAL_USD = BASE_PRICE_USD_PER_LB * CONTRACT_NOTIONAL_LBS

# Maintenance margin (broker-dependent, conservative end)
MAINTENANCE_MARGIN_USD = 1500.0

TIERS = [5_000, 10_000, 25_000, 50_000]


def connect():
    return pymysql.connect(
        host=os.environ.get("DB_STOCKS_HOST", "mysql.50webs.com"),
        user=os.environ.get("DB_STOCKS_USER", "ejaguiar1_stocks"),
        password=os.environ.get("DB_STOCKS_PASSWORD", "stocks"),
        database=os.environ.get("DB_STOCKS_NAME", "ejaguiar1_stocks"),
        port=int(os.environ.get("DB_STOCKS_PORT", "3306")),
        connect_timeout=30,
        read_timeout=60,
    )


def fetch_pnls():
    """Pull pnl_pct for the 100 closed cot_positioning + CT=F picks."""
    c = connect()
    cur = c.cursor()
    cur.execute("""
        SELECT pnl_pct FROM trading_picks
         WHERE strategy='cot_positioning' AND symbol='CT=F'
           AND status IN ('WON','LOST','WIN','LOSS','TP_HIT','SL_HIT')
           AND pnl_pct IS NOT NULL
        """)
    pnls = [float(r[0]) for r in cur.fetchall() if r[0] is not None]
    c.close()
    return pnls


def simulate(pnls_pct: list[float], starter: float, seq_trades: int,
             sims: int, seed: int = 1234) -> dict:
    """Bootstrap `sims` × `seq_trades` from `pnls_pct`. Convert each pnl_pct
    to USD via 1-contract notional, subtract round-trip cost, apply to
    equity. Track margin-call and final equity.
    """
    rng = random.Random(seed)
    margin_calls = 0
    finals = []
    drawdowns = []
    for _ in range(sims):
        equity = starter
        peak = starter
        max_dd = 0.0
        called = False
        for _ in range(seq_trades):
            pnl_pct = rng.choice(pnls_pct)
            pnl_usd_gross = pnl_pct / 100.0 * NOTIONAL_USD
            pnl_usd_net = pnl_usd_gross - ROUND_TRIP_COST_USD
            equity += pnl_usd_net
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd
            if equity < MAINTENANCE_MARGIN_USD:
                called = True
                break
        if called:
            margin_calls += 1
        finals.append(equity)
        drawdowns.append(max_dd)
    finals_sorted = sorted(finals)
    return {
        "starter": starter,
        "sims": sims,
        "seq_trades": seq_trades,
        "margin_call_count": margin_calls,
        "margin_call_pct": round(margin_calls * 100.0 / sims, 4),
        "final_equity_mean": round(statistics.mean(finals), 2),
        "final_equity_p05": round(finals_sorted[int(sims * 0.05)], 2),
        "final_equity_p50": round(finals_sorted[int(sims * 0.50)], 2),
        "final_equity_p95": round(finals_sorted[int(sims * 0.95)], 2),
        "max_drawdown_mean_pct": round(statistics.mean(drawdowns) * 100, 3),
        "max_drawdown_p95_pct": round(sorted(drawdowns)[int(sims * 0.95)] * 100, 3),
    }


def verdict_for_tier(t: dict, target_pct: float) -> str:
    return "PASS" if t["margin_call_pct"] < target_pct else "FAIL"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sims", type=int, default=10000)
    p.add_argument("--seq-trades", type=int, default=50)
    p.add_argument("--seed", type=int, default=1234)
    p.add_argument("--out", default="audit_dashboard/data/cot_step7_ror_mc.json")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    print(f"# COT Step 7 Risk-of-Ruin MC — sims={args.sims} "
          f"seq_trades={args.seq_trades} seed={args.seed}", file=sys.stderr)

    try:
        pnls = fetch_pnls()
    except Exception as e:
        print(f"DB connect failed: {e}", file=sys.stderr)
        sys.exit(1)

    if len(pnls) < 50:
        print(f"# WARN: n={len(pnls)} pnls too few for stable MC", file=sys.stderr)

    pnl_summary = {
        "n": len(pnls),
        "mean_pct": round(statistics.mean(pnls), 4),
        "stdev_pct": round(statistics.stdev(pnls), 4) if len(pnls) > 1 else 0,
        "min_pct": round(min(pnls), 4),
        "max_pct": round(max(pnls), 4),
        "wins": sum(1 for p in pnls if p > 0),
        "losses": sum(1 for p in pnls if p < 0),
    }
    print(f"# pnl_summary: {pnl_summary}", file=sys.stderr)

    tiers_results = {}
    for starter in TIERS:
        r = simulate(pnls, starter, args.seq_trades, args.sims, args.seed)
        tiers_results[f"${starter}"] = r
        print(f"#   ${starter}: margin_call_pct={r['margin_call_pct']:.3f}% "
              f"final_p05=${r['final_equity_p05']} "
              f"final_p50=${r['final_equity_p50']} "
              f"max_dd_p95={r['max_drawdown_p95_pct']:.2f}%", file=sys.stderr)

    # Pass/fail per plan
    pass_5k  = verdict_for_tier(tiers_results["$5000"],  10.0)   # plan didn't spec $5k; using 10%
    pass_10k = verdict_for_tier(tiers_results["$10000"], 5.0)    # plan: <5%
    pass_25k = verdict_for_tier(tiers_results["$25000"], 1.0)    # plan: <1%

    overall = "PASS" if (pass_10k == "PASS" and pass_25k == "PASS") else "FAIL"

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "strategy": "cot_positioning",
        "symbol": "CT=F",
        "method": "bootstrap " + str(args.sims) + " sequences of " +
                  str(args.seq_trades) + " trades each, sampled with "
                  "replacement from the 100-pick realized pnl_pct distribution. "
                  "Per-trade USD = pnl_pct/100 × $35k notional − $10 round-trip cost.",
        "contract_spec": {
            "size_lbs": CONTRACT_NOTIONAL_LBS,
            "tick_usd": TICK_USD,
            "round_trip_cost_usd": ROUND_TRIP_COST_USD,
            "base_price_usd_per_lb": BASE_PRICE_USD_PER_LB,
            "notional_usd": NOTIONAL_USD,
            "maintenance_margin_usd": MAINTENANCE_MARGIN_USD,
        },
        "pnl_distribution": pnl_summary,
        "tiers": tiers_results,
        "verdicts": {
            "$5k_at_<10pct": pass_5k,
            "$10k_at_<5pct (plan target)": pass_10k,
            "$25k_at_<1pct (plan target)": pass_25k,
            "overall": overall,
        },
        "caveat": "Hindsight MC. Empirical pnl distribution carries the "
                  "fold_1 regime outlier from Step 3 (worst-fold 10% WR). "
                  "If forward regime reverts to that state, true ror is "
                  "higher than this MC reports. Pair with regime-gate add "
                  "before sizing.",
        "nfa": "Research surface only. No real-money sizing without (1) "
               "regime-gate addition, (2) Step 6 paper-pilot clear, (3) "
               "this Step 7 PASS, (4) explicit user greenlight.",
    }

    if args.dry_run:
        print(json.dumps(payload, indent=2))
        return

    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    size = out_path.stat().st_size
    print(f"# wrote {out_path} ({size:,} bytes)", file=sys.stderr)
    print(f"# OVERALL: {overall} ($10k {pass_10k} <5% target; "
          f"$25k {pass_25k} <1% target)", file=sys.stderr)


if __name__ == "__main__":
    main()
