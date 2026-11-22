#!/usr/bin/env python3
"""Item 7 - COST-SENSITIVITY SWEEP of POD-EQUITY-BREAKOUT.

Only the cost varies. The strategy object, entry rule, exit rule, tie-break and
universe are exactly those of tools/pod_equity_breakout_backtest.py, whose
functions are imported (not re-implemented). Data is fetched ONCE and the trade
list is produced ONCE; the sweep is then pure arithmetic on that fixed list, so
no parameter can drift between cost points.

EQUITY cost is UNMEASURED (no equity order-book access in this environment), so
this sweep reports the BREAK-EVEN cost instead - a property of the strategy that
does not depend on what we assume.

Usage: python3 tools/breakout_cost_sweep.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.pod_equity_breakout_backtest import (  # noqa: E402
    SYMBOLS, backtest_symbol, fetch_daily, summarize)
from baby_strategies.vt_pattern_sweep import VTPatternSweepStrategy  # noqa: E402

COSTS = [0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25]
OUT = ROOT / "reports" / "pod_equity_breakout"


def break_even(rows: list[dict], key: str) -> float | None:
    """Linear crossing between the last positive and first negative cost."""
    prev = None
    for r in rows:
        if r["n"] == 0:
            continue
        v = r[key]
        if prev is not None and prev[1] > 0 >= v:
            c0, v0 = prev
            c1, v1 = r["cost_bp_per_side"], v
            return c0 + (c1 - c0) * v0 / (v0 - v1)
        prev = (r["cost_bp_per_side"], v)
    return None


def main() -> int:
    strat = VTPatternSweepStrategy()
    trades = []
    per_sym = {}
    for sym in SYMBOLS:
        df = fetch_daily(sym)
        if df is None or len(df) < 300:
            per_sym[sym] = {"n": 0, "status": "no data"}
            continue
        tr = backtest_symbol(sym, strat, df, tie_break="stop")
        per_sym[sym] = {"n": len(tr),
                        "window": f"{df.index[0].date()}..{df.index[-1].date()}"}
        trades.extend(tr)
        print(f"  {sym:<6} {per_sym[sym].get('window','')} -> {len(tr):>3} trades",
              flush=True)
    if not trades:
        print("NO TRADES")
        return 2

    pre = [t for t in trades if t["entry_date"] < "2021-01-01"]
    val = [t for t in trades if t["entry_date"] >= "2021-01-01"]

    rows = []
    print(f"\n{'cost/side':>10}{'ALL net%/tr':>13}{'ALL t':>8}"
          f"{'PRE-2021 net%/tr':>18}{'PRE t':>8}{'PRE n':>7}"
          f"{'2021+ net%/tr':>15}{'2021+ t':>9}")
    for c in COSTS:
        a = summarize(trades, c, "all")
        p = summarize(pre, c, "pre")
        v = summarize(val, c, "val")
        row = {"cost_bp_per_side": c, "cost_bp_round_trip": 2 * c,
               "all": a, "pre_2021": p, "in_sample_2021plus": v}
        rows.append(row)
        print(f"{c:>10.1f}{a['net_pct']:>13.4f}{a['t']:>8.2f}"
              f"{p['net_pct']:>18.4f}{p['t']:>8.2f}{p['n']:>7}"
              f"{v['net_pct']:>15.4f}{v['t']:>9.2f}", flush=True)

    be = {"all_history": break_even(rows, None) if False else None}
    # break_even works on flattened rows
    flat_all = [{"cost_bp_per_side": r["cost_bp_per_side"], "n": r["all"]["n"],
                 "v": r["all"]["net_pct"]} for r in rows]
    flat_pre = [{"cost_bp_per_side": r["cost_bp_per_side"], "n": r["pre_2021"]["n"],
                 "v": r["pre_2021"]["net_pct"]} for r in rows]
    flat_val = [{"cost_bp_per_side": r["cost_bp_per_side"], "n": r["in_sample_2021plus"]["n"],
                 "v": r["in_sample_2021plus"]["net_pct"]} for r in rows]

    def be_of(flat):
        prev = None
        for r in flat:
            if r["n"] == 0:
                continue
            if prev and prev[1] > 0 >= r["v"]:
                return prev[0] + (r["cost_bp_per_side"] - prev[0]) * prev[1] / (prev[1] - r["v"])
            prev = (r["cost_bp_per_side"], r["v"])
        return None

    be = {"all_history": be_of(flat_all),
          "pre_2021_out_of_sample": be_of(flat_pre),
          "in_sample_2021plus": be_of(flat_val)}
    print("\n=== BREAK-EVEN COST (per side; round trip = 2x) ===")
    for k, v in be.items():
        if v is None:
            print(f"  {k:<26} no crossing in 0..25bp (stays {'positive' if flat_all[0]['v'] > 0 else 'negative'})")
        else:
            print(f"  {k:<26} {v:>6.2f}bp/side  ({2*v:.2f}bp round trip)")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "breakout_cost_sweep.json").write_text(json.dumps({
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "strategy": "POD-EQUITY-BREAKOUT / H-BABY-EQUITY-VT-PATTERN-SWEEP-001",
        "source": "tools/pod_equity_breakout_backtest.py functions imported; "
                  "baby_strategies/vt_pattern_sweep.py VTPatternSweepStrategy",
        "only_cost_varies": True, "tie_break": "stop", "fill": "next bar open",
        "symbols": SYMBOLS, "per_symbol": per_sym, "n_trades": len(trades),
        "break_even_bp_per_side": be, "rows": rows,
    }, indent=1))
    print(f"\nwrote {OUT/'breakout_cost_sweep.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
