#!/usr/bin/env python3
"""Risk % sweep for selected symbol x strategy combos (uses hyro_backtest_extended.run_single)."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from hyro_backtest_extended import run_single

DEFAULT_COMBOS: list[tuple[str, str, str]] = [
    ("ETHUSDT", "volume", "ETH volume breakout"),
    ("ETHUSDT", "heikin_ashi", "ETH Heikin-Ashi"),
    ("BTCUSDT", "donchian", "BTC Donchian"),
    ("AVAXUSDT", "volume", "AVAX volume breakout"),
    ("AVAXUSDT", "donchian", "AVAX Donchian"),
    ("BNBUSDT", "connors_rsi2", "BNB Connors RSI(2)"),
    ("SOLUSDT", "connors_rsi2", "SOL Connors RSI(2)"),
    ("SOLUSDT", "volume_surge_rev", "SOL volume surge rev"),
]

DEFAULT_RISKS = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5]
DEFAULT_OUT = Path(__file__).resolve().parent.parent / "audit_dashboard" / "data" / "hyro_risk_optimization.json"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--months", type=int, default=6)
    p.add_argument("--long-only", action="store_true")
    p.add_argument("--output", type=str, default=str(DEFAULT_OUT))
    p.add_argument("--risks", type=float, nargs="+", default=DEFAULT_RISKS)
    args = p.parse_args()

    all_results: list[dict] = []
    for symbol, strat, label in DEFAULT_COMBOS:
        print(f"\n{label} ({symbol})")
        print(f"{'risk%':<8} {'status':<12} {'trades':<8} {'WR':<8} {'PF':<8} {'PnL$':<10} {'maxDD':<10}")
        for risk in args.risks:
            try:
                r = run_single(symbol, strat, months=args.months, risk_pct=risk, long_only=args.long_only)
                if r:
                    st = "PASS" if r["passed"] else ("FAIL" if r["failed"] else "INC")
                    print(
                        f"{risk:<8} {st:<12} {r['total_trades']:<8} {r['win_rate']:<8} "
                        f"{r['profit_factor']:<8} {r['total_pnl']:<10} {r['max_dd']:<10}"
                    )
                    all_results.append(r)
                else:
                    print(f"{risk:<8} NO_TRADES")
            except Exception as e:
                print(f"{risk:<8} ERR {e}")
            time.sleep(0.12)

    passed = [r for r in all_results if r["passed"]]
    passed.sort(key=lambda r: r["pnl_pct"] / (r["max_dd"] + 1.0), reverse=True)
    print(f"\nBest by pnl_pct/(max_dd+1): {len(passed)} passed configs")
    for r in passed[:15]:
        print(
            f"  {r['symbol']} x {r['strategy_name']} @ {r['risk_pct']}% "
            f"PnL%={r['pnl_pct']} maxDD={r['max_dd']} WR={r['win_rate']}"
        )

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(
            {"generated_at": datetime.now(timezone.utc).isoformat(), "results": all_results},
            f,
            indent=2,
        )
    print(f"\nSaved -> {out}")


if __name__ == "__main__":
    main()
