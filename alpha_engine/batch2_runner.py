#!/usr/bin/env python3
"""
BATCH 2 SURVIVOR BACKTEST RUNNER
=================================
Runs 10 new candidate strategies through the full anti-overfitting protocol.
Imports strategies from batch2_strategies.py, testing framework from survivor_backtest.py.

Usage: py alpha_engine/batch2_runner.py
"""

import json
import sys
import time
import warnings
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from batch2_strategies import BATCH2_STRATEGIES
from survivor_backtest import (
    ALL_SYMBOLS,
    analyze_strategy,
    detect_regime,
    fetch_data,
)


def run_batch2_test(data: dict[str, pd.DataFrame]) -> dict:
    """Run batch2 strategies on all symbols with full anti-overfitting protocol."""
    results = defaultdict(
        lambda: {
            "trades": [],
            "by_symbol": defaultdict(list),
            "by_regime": defaultdict(list),
        }
    )

    for sym, df in data.items():
        close_arr = df["Close"].values.astype(float)
        n_bars = len(df)

        for strat_name, strat_info in BATCH2_STRATEGIES.items():
            func = strat_info["func"]
            try:
                trades = func(df)
            except Exception as e:
                print(f"  ERROR {strat_name} on {sym}: {e}")
                continue

            if not trades:
                continue

            for t in trades:
                regime = detect_regime(close_arr, t["entry_idx"])
                t["symbol"] = sym
                t["regime"] = regime
                t["in_sample"] = t["entry_idx"] < int(n_bars * 0.6)

                results[strat_name]["trades"].append(t)
                results[strat_name]["by_symbol"][sym].append(t)
                results[strat_name]["by_regime"][regime].append(t)

    return dict(results)


def main():
    t0 = time.time()

    print("=" * 80)
    print("  BATCH 2 SURVIVOR BACKTEST -- 10 New Candidate Strategies")
    print("  10 strategies x 24 symbols x 5 years x 8 anti-overfit checks")
    print("=" * 80)

    print(f"\n  Strategies under test:")
    for name, info in BATCH2_STRATEGIES.items():
        print(f"    - {name}: {info['desc']}")

    print(f"\n[1/3] Fetching 5 years of daily OHLCV data...")
    data = fetch_data(ALL_SYMBOLS, period="5y")

    if not data:
        print("FATAL: No data fetched")
        sys.exit(1)

    print(
        f"\n[2/3] Running walk-forward backtests on {len(BATCH2_STRATEGIES)} strategies x {len(data)} symbols..."
    )

    # Temporarily set STRATEGIES to batch2 for analyze_strategy to work
    raw_results = run_batch2_test(data)

    print(f"\n[3/3] Statistical analysis with anti-overfitting checks...")
    final = {}
    for strat_name in BATCH2_STRATEGIES:
        if strat_name in raw_results:
            analysis = analyze_strategy(strat_name, raw_results[strat_name])
            final[strat_name] = analysis

    # Sort by verdict quality
    verdict_order = {
        "SURVIVOR": 0,
        "PROMISING": 1,
        "MARGINAL": 2,
        "ELIMINATED": 3,
        "INSUFFICIENT": 4,
    }
    sorted_strats = sorted(
        final.items(),
        key=lambda x: (verdict_order.get(x[1]["verdict"], 5), -x[1].get("sharpe", 0)),
    )

    # Print report
    print("\n" + "=" * 80)
    print("  BATCH 2 RESULTS")
    print("=" * 80)

    for strat_name, analysis in sorted_strats:
        desc = BATCH2_STRATEGIES[strat_name]["desc"]
        v = analysis["verdict"]
        marker = {
            "SURVIVOR": "[***]",
            "PROMISING": "[** ]",
            "MARGINAL": "[*  ]",
            "ELIMINATED": "[   ]",
        }.get(v, "[   ]")

        print(f"\n  {marker} {strat_name} -- {v}")
        print(f"       {desc}")

        if analysis.get("total_trades", 0) < 5:
            print(f"       Insufficient trades ({analysis['total_trades']})")
            continue

        print(
            f"       Trades: {analysis['total_trades']} | WR: {analysis['win_rate_pct']}% | "
            f"Sharpe: {analysis['sharpe']} | PF: {analysis['profit_factor']} | p={analysis['p_value']}"
        )
        print(
            f"       In-sample: {analysis['in_sample_trades']}T {analysis['in_sample_wr']}% WR | "
            f"OOS: {analysis['oos_trades']}T {analysis['oos_wr']}% WR (avg {analysis['oos_avg_pnl_pct']}%)"
        )
        print(
            f"       Multi-asset: {analysis['symbols_profitable']}/{analysis['symbols_tested']} profitable | "
            f"Regimes: {analysis['regimes_profitable']}/{analysis['regimes_tested']} profitable"
        )
        print(
            f"       Consistency: 1st half {analysis['first_half_avg_pnl']}% | 2nd half {analysis['second_half_avg_pnl']}%"
        )

        # Per-symbol breakdown for survivors
        if v in ("SURVIVOR", "PROMISING"):
            print(f"       Per-symbol breakdown:")
            for sym, sr in sorted(
                analysis["symbol_results"].items(), key=lambda x: -x[1]["avg_pnl"]
            ):
                status = "+" if sr["avg_pnl"] > 0 else "-"
                print(
                    f"         {status} {sym:>10}: {sr['trades']:3d}T  WR={sr['wr']:5.1f}%  avg={sr['avg_pnl']:+.3f}%"
                )

        # Checks
        checks = analysis["checks"]
        fails = [k for k, v in checks.items() if not v]
        if fails:
            print(f"       Failed checks: {', '.join(fails)}")

    # Save results
    save_dir = Path("alpha_engine/data")
    save_dir.mkdir(parents=True, exist_ok=True)

    save_path = save_dir / "batch2_backtest_results.json"
    with open(save_path, "w") as f:
        json.dump(
            {
                "test_date": datetime.now(timezone.utc).isoformat(),
                "symbols_tested": len(data),
                "strategies_tested": len(BATCH2_STRATEGIES),
                "period": "5y",
                "anti_overfit_checks": 8,
                "results": {k: v for k, v in final.items()},
            },
            f,
            indent=2,
            default=str,
        )

    elapsed = time.time() - t0

    # Summary
    survivors = [s for s, a in final.items() if a["verdict"] == "SURVIVOR"]
    promising = [s for s, a in final.items() if a["verdict"] == "PROMISING"]
    eliminated = [
        s for s, a in final.items() if a["verdict"] in ("ELIMINATED", "MARGINAL")
    ]

    print(f"\n{'=' * 80}")
    print(f"  BATCH 2 FINAL SCORE:")
    print(
        f"    SURVIVORS (pass 7+/8 checks):  {len(survivors)} -- {', '.join(survivors) if survivors else 'NONE'}"
    )
    print(
        f"    PROMISING (pass 5-6/8 checks): {len(promising)} -- {', '.join(promising) if promising else 'NONE'}"
    )
    print(f"    ELIMINATED:                    {len(eliminated)}")
    print(f"  Completed in {elapsed:.1f}s | Saved: {save_path}")
    print(f"{'=' * 80}")

    return final


if __name__ == "__main__":
    main()
