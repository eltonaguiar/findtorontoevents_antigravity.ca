"""Run Mercury3's EXACT commodity rule under my CI-LB gate.

He posted the weight logic (COMS notes/reply-mercury3-to-buffy-commodity-code-2026-11-22,
from /tmp/p6/r2_regime.py lines 50-62). It is not per-member SMA — it is a single scalar
whole-book binary on the EQUAL-WEIGHT BASKET LEVEL:

    lvl = px / px.iloc[0]
    i   = t - 2                        # everything known by t
    if i >= 10:
        new = 1.0 if lvl.iloc[i] > lvl.iloc[i-10:i].mean() else 0.0
    cost = abs(diff(pos)) * 20bp

He then WITHDREW the +3.59% claim himself, on the grounds that the rule is a 43%-duty-cycle
overlay over one secular bear and that it does not survive moving the SMA from the basket to
the members. This tool verifies both halves of that withdrawal under my own gate, because a
withdrawal is still a claim and it should be measured like one:

  1. reproduce his specification (basket level, lag=2, 20bp) and get his duty cycle
  2. run the SAME data through the per-member formulation (what I registered) for contrast
  3. apply the CI-LB gate that every other cell in this repo was judged by, to monthly
     EXCESS return over the T-bill leg, at 1x and 2x cost, plus both halves

Usage
  python3 tools/commodity_basket_timing_check.py --out reports/commodity_basket_timing_2026-11-22.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from commodity_tsmom_check import (CASH_PROXY, UNIVERSE, boot_lb,  # noqa: E402
                                   load_daily, max_drawdown, monthly_last)

SMA_MONTHS = 10
COST_BPS = 20.0


def build_panel() -> tuple[list[str], dict[str, float], dict[str, float]]:
    """Common monthly window, EW basket level, and the T-bill rate per month."""
    member_monthly = {}
    for sym in UNIVERSE:
        try:
            member_monthly[sym] = monthly_last(load_daily(sym))
        except Exception as e:  # noqa: BLE001
            print(f"  drop {sym}: {type(e).__name__}: {e}", file=sys.stderr)
    if not member_monthly:
        raise SystemExit("no members loaded")
    start = max(min(m) for m in member_monthly.values())
    end = min(max(m) for m in member_monthly.values())
    months = sorted({m for mm in member_monthly.values() for m in mm if start <= m <= end})
    months = [m for m in months if all(m in mm for mm in member_monthly.values())]

    levels, basket = {}, []
    for sym, mm in member_monthly.items():
        base = mm[months[0]]
        levels[sym] = [mm[m] / base for m in months]
    for i in range(len(months)):
        basket.append(sum(levels[s][i] for s in levels) / len(levels))

    cash = monthly_last(load_daily(CASH_PROXY))
    cash_pct = {m: cash.get(m, 0.0) for m in months}
    return months, {"BASKET": basket}, cash_pct


def position_path(months, lvl, lag):
    """His rule, transcribed: whole-book binary on the basket level, i = t - lag."""
    path, switches, pos = [], 0, 0.0
    for t in range(len(months)):
        i = t - lag
        if i >= SMA_MONTHS:
            new = 1.0 if lvl[i] > sum(lvl[i - SMA_MONTHS:i]) / SMA_MONTHS else 0.0
            if new != pos:
                switches += 1
            pos = new
        path.append(pos)
    return path, switches


def simulate(months, series, cash_pct, lag, cost_bps):
    """Whole-book binary on `series` (dict of one or more members), monthly."""
    keys = list(series)
    lvl = [sum(series[k][i] for k in keys) / len(keys) for i in range(len(months))]
    pos_path, switches = position_path(months, lvl, lag)
    port = []
    for t in range(len(months)):
        r = lvl[t] / lvl[t - 1] - 1.0 if t else 0.0
        c = cash_pct[months[t]] / 12.0 / 100.0
        prev = pos_path[t - 1] if t else 0.0
        cost = abs(pos_path[t] - prev) * cost_bps / 1e4
        port.append(pos_path[t] * r + (1 - pos_path[t]) * c - cost)
    eq = [1.0]
    for x in port:
        eq.append(eq[-1] * (1.0 + x))
    n = len(months)
    excess = [port[t] - cash_pct[months[t]] / 12.0 / 100.0 for t in range(n)]
    lo, _hi = boot_lb(excess[1:])
    mu = sum(excess[1:]) / max(1, n - 1)
    var = sum((x - mu) ** 2 for x in excess[1:]) / max(1, n - 2)
    sd = math.sqrt(var)
    half = n // 2
    return {
        "months": n,
        "cagr_pct": round(((eq[-1] / eq[0]) ** (12.0 / n) - 1.0) * 100, 3),
        "sharpe_excess": round(mu / sd * math.sqrt(12) if sd else 0.0, 3),
        "mdd_pct": round(max_drawdown(eq) * 100, 2),
        "invested_share": round(sum(pos_path) / n, 3),
        "switches": switches,
        "excess_bps_month": round(mu * 1e4, 2),
        "ci_lb_bps_month": round(lo * 1e4, 2),
        "halves_bps": [
            round(sum(excess[1:half]) / max(1, len(excess[1:half])) * 1e4, 2),
            round(sum(excess[half:]) / max(1, len(excess) - half) * 1e4, 2),
        ],
        "verdict": "CI_LB_POSITIVE" if lo > 0 else "CI_LB_NEGATIVE",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="reports/commodity_basket_timing_2026-11-22.json")
    args = ap.parse_args()
    print("loading 11 members + ^IRX (cached where possible)...")
    months, series, cash_pct = build_panel()
    basket = series["BASKET"]
    # buy-and-hold self-check against the value already registered in V3 (-0.81%/yr)
    eq = [1.0]
    for t in range(1, len(months)):
        eq.append(eq[-1] * (basket[t] / basket[t - 1]))
    bh = (eq[-1] / eq[0]) ** (12.0 / len(months)) - 1.0

    out = {
        "generated_by": "tools/commodity_basket_timing_check.py",
        "spec_source": "mercury3 COMS reply-mercury3-to-buffy-commodity-code-2026-11-22 (r2_regime.py 50-62)",
        "window": [months[0], months[-1]], "months": len(months), "members": len(UNIVERSE),
        "buy_and_hold_cagr_pct": round(bh * 100, 3),
        "bh_selfcheck_vs_v3_pct": round(bh * 100 + 0.81, 3),
        "cells": {},
    }
    for lag in (2, 1):
        for cost in (20.0, 40.0):
            out["cells"][f"basket_lag{lag}_cost{cost:.0f}"] = simulate(months, series, cash_pct, lag, cost)
    out["note_on_per_member"] = ("per-member result is in reports/commodity_tsmom_v3_2026-11-22.json "
                                 "(-2.16%/yr, invested 86%); this cell exists only to show the same "
                                 "data under the other specification")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2) + "\n")

    print(f"window {months[0]}..{months[-1]}  {len(months)} months  {len(UNIVERSE)} members")
    print(f"BH self-check: my basket {bh*100:+.2f}%/yr vs V3 registered -0.81 -> delta {bh*100+0.81:+.3f}pp")
    for k, v in out["cells"].items():
        print(f"  {k:24s} CAGR {v['cagr_pct']:+6.2f}%  Sharpe {v['sharpe_excess']:+.3f}  "
              f"MDD {v['mdd_pct']:+6.2f}%  invested {v['invested_share']*100:4.0f}%  "
              f"excess {v['excess_bps_month']:+7.2f} bp/mo  CI-LB {v['ci_lb_bps_month']:+7.2f}  "
              f"halves {v['halves_bps']}  {v['verdict']}")
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
