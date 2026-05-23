#!/usr/bin/env python3
"""
A3 cohort-replay backtest harness for `vol_scalar_cap`.

WHY THIS EXISTS
---------------
`alpha_engine/backtest/position_sizing.py::PositionSizer.volatility_target_size`
gained an opt-in `vol_scalar_cap=(lo, hi)` param (swarm-vetted 2026-05-16) that
clamps the raw inverse-vol scalar `target_vol/annualized_vol` before the
position-pct bounds. The acceptance bar in
`reports/action_items_plan_2026-05-17.md` is "Sharpe lift >= +0.2" -- but no
harness existed to replay closed picks through the function, so the test could
not be run. This file is that harness.

WHAT IT DOES
------------
1. Loads closed picks from `alpha_engine/data/closed_picks.json`, filters to
   COMMODITY + ETF asset classes.
2. Derives `annualized_vol` per pick from available fields (daily ATR / entry
   price, annualized by sqrt(252)). When ATR is missing it falls back to a
   per-asset-class default and the pick is COUNTED as defaulted so the report
   can disclose the limitation honestly.
3. Replays each pick's realized `pnl_pct` through two sizing arms:
     NOCAP : volatility_target_size(..., vol_scalar_cap=None)
     CAP   : volatility_target_size(..., vol_scalar_cap=(0.0, 2.0))
   Each pick's realized return is weighted by that arm's own `target_weight`
   (the dataset carries no stored `target_weight`, so the sizer's output is
   used as the position weight -- this is the cohort-replay design).
4. Computes per-arm total return, Sharpe (mean/std of weighted returns), and
   max drawdown (MDD) on the equity curve.
5. Prints a NOCAP-vs-CAP table and a verdict.

READ-ONLY: this harness never writes to any input and never runs a generator.
"""
from __future__ import annotations

import json
import math
import os
import sys

# --- locate repo root + import the sizer -----------------------------------
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(THIS_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from alpha_engine.backtest.position_sizing import PositionSizer  # noqa: E402

CLOSED_PICKS = os.path.join(REPO_ROOT, "alpha_engine", "data", "closed_picks.json")

TARGET_CLASSES = {"COMMODITY", "ETF"}
TRADING_DAYS = 252

# Per-asset-class fallback annualized vol, used ONLY when ATR is unavailable.
# COMMODITY: futures realized vol typically 25-45% annualized -> 0.35 midpoint.
# ETF: broad-ETF realized vol typically 12-20% annualized -> 0.16 midpoint.
DEFAULT_ANN_VOL = {"COMMODITY": 0.35, "ETF": 0.16}

# vol_scalar_cap arm under test (recommended (0.0, 2.0) per the docstring guard).
CAP_BOUNDS = (0.0, 2.0)


def make_sizer() -> PositionSizer:
    """
    Build a PositionSizer WITHOUT touching the broken `config.MAX_POSITION_PCT`
    path. `PositionSizer.__init__` imports `.. import config` and reads
    attributes that may not exist; we bypass __init__ entirely and set the
    attributes `volatility_target_size` actually needs.
    """
    sizer = PositionSizer.__new__(PositionSizer)
    sizer.portfolio_value = 100_000.0
    sizer.min_position_pct = 0.01
    sizer.max_position_pct = 0.25
    return sizer


def derive_annualized_vol(pick: dict) -> tuple[float, bool]:
    """
    Return (annualized_vol, was_defaulted).

    Preference order:
      1. daily ATR (`extra.atr`) / entry_price, annualized by sqrt(252).
      2. per-asset-class default (flagged was_defaulted=True).
    """
    extra = pick.get("extra") or {}
    atr = extra.get("atr")
    entry = pick.get("entry_price")
    if isinstance(atr, (int, float)) and isinstance(entry, (int, float)) and atr > 0 and entry > 0:
        daily_vol = atr / entry
        ann_vol = daily_vol * math.sqrt(TRADING_DAYS)
        # clamp to a sane band so a bad ATR row cannot poison the replay
        ann_vol = min(max(ann_vol, 0.05), 1.50)
        return ann_vol, False
    ac = pick.get("asset_class", "COMMODITY")
    return DEFAULT_ANN_VOL.get(ac, 0.35), True


def equity_curve_mdd(weighted_returns: list[float]) -> float:
    """Max drawdown of the cumulative (compounded) equity curve."""
    equity = 1.0
    peak = 1.0
    mdd = 0.0
    for r in weighted_returns:
        equity *= (1.0 + r)
        peak = max(peak, equity)
        if peak > 0:
            dd = (peak - equity) / peak
            mdd = max(mdd, dd)
    return mdd


def sharpe(weighted_returns: list[float]) -> float:
    """Per-trade Sharpe = mean / std of the weighted return series."""
    n = len(weighted_returns)
    if n < 2:
        return 0.0
    mean = sum(weighted_returns) / n
    var = sum((r - mean) ** 2 for r in weighted_returns) / (n - 1)
    std = math.sqrt(var)
    if std <= 0:
        return 0.0
    return mean / std


def replay(picks: list[dict], sizer: PositionSizer, cap):
    """
    Replay every pick through one sizing arm.

    Returns (weighted_returns, total_return, sharpe, mdd, weights).
    `cap` is None for the NOCAP arm or (lo, hi) for the CAP arm.
    """
    weighted_returns: list[float] = []
    weights: list[float] = []
    for p in picks:
        pnl = p["pnl_pct"]
        ann_vol = p["_ann_vol"]
        entry = p.get("entry_price") or 1.0
        res = sizer.volatility_target_size(
            price=entry,
            annualized_vol=ann_vol,
            target_vol=0.15,
            vol_scalar_cap=cap,
        )
        w = res.target_weight
        weights.append(w)
        weighted_returns.append(w * pnl)
    total_return = sum(weighted_returns)
    return weighted_returns, total_return, sharpe(weighted_returns), equity_curve_mdd(weighted_returns), weights


def main() -> int:
    with open(CLOSED_PICKS, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    picks = [
        p for p in data
        if p.get("asset_class") in TARGET_CLASSES
        and isinstance(p.get("pnl_pct"), (int, float))
    ]

    # derive annualized_vol per pick + track defaulting
    defaulted = 0
    by_class: dict[str, int] = {}
    for p in picks:
        ann_vol, was_default = derive_annualized_vol(p)
        p["_ann_vol"] = ann_vol
        p["_vol_defaulted"] = was_default
        if was_default:
            defaulted += 1
        ac = p.get("asset_class", "?")
        by_class[ac] = by_class.get(ac, 0) + 1

    n = len(picks)
    print("=" * 70)
    print("A3 COHORT-REPLAY BACKTEST  --  vol_scalar_cap acceptance test")
    print("=" * 70)
    print(f"Closed picks file : {CLOSED_PICKS}")
    print(f"Cohort            : COMMODITY + ETF")
    print(f"Picks replayed    : {n}")
    for ac, c in sorted(by_class.items()):
        print(f"  - {ac:<10}: {c}")
    print(f"annualized_vol src: ATR-derived for {n - defaulted}/{n}, "
          f"per-class default for {defaulted}/{n}")
    if n == 0:
        print("\nNO PICKS IN COHORT -- cannot run. Verdict: INCONCLUSIVE")
        return 0

    sizer = make_sizer()

    nc_wr, nc_total, nc_sharpe, nc_mdd, nc_w = replay(picks, sizer, None)
    cp_wr, cp_total, cp_sharpe, cp_mdd, cp_w = replay(picks, sizer, CAP_BOUNDS)

    avg_nc_w = sum(nc_w) / len(nc_w)
    avg_cp_w = sum(cp_w) / len(cp_w)

    sharpe_lift = cp_sharpe - nc_sharpe

    print()
    print("-" * 70)
    print(f"{'metric':<22}{'NOCAP':>16}{'CAP(0.0,2.0)':>18}{'delta':>14}")
    print("-" * 70)
    print(f"{'total return':<22}{nc_total*100:>15.3f}%{cp_total*100:>17.3f}%"
          f"{(cp_total-nc_total)*100:>13.3f}%")
    print(f"{'Sharpe (per-trade)':<22}{nc_sharpe:>16.4f}{cp_sharpe:>18.4f}"
          f"{sharpe_lift:>+14.4f}")
    print(f"{'max drawdown':<22}{nc_mdd*100:>15.3f}%{cp_mdd*100:>17.3f}%"
          f"{(cp_mdd-nc_mdd)*100:>+13.3f}%")
    print(f"{'avg position weight':<22}{avg_nc_w*100:>15.3f}%{avg_cp_w*100:>17.3f}%"
          f"{(avg_cp_w-avg_nc_w)*100:>+13.3f}%")
    print("-" * 70)

    # verdict: CAP passes iff Sharpe lift >= +0.2 AND MDD does not worsen
    passes_sharpe = sharpe_lift >= 0.2
    mdd_ok = cp_mdd <= nc_mdd + 1e-9
    if passes_sharpe and mdd_ok:
        verdict = "CAP PASSES"
    elif not passes_sharpe and abs(sharpe_lift) < 1e-6 and abs(cp_mdd - nc_mdd) < 1e-9:
        verdict = "INCONCLUSIVE (cap never bound -- arms identical on this cohort)"
    else:
        verdict = "CAP FAILS"

    print()
    print(f"Sharpe lift       : {sharpe_lift:+.4f}  (bar: >= +0.2  -> "
          f"{'PASS' if passes_sharpe else 'FAIL'})")
    print(f"MDD vs NOCAP      : {'<= NOCAP (ok)' if mdd_ok else '> NOCAP (worse)'}")
    print(f"VERDICT           : {verdict}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
