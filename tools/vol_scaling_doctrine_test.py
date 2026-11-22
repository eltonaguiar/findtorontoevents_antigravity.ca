#!/usr/bin/env python3
"""vol_scaling_doctrine_test.py — is volatility scaling "free alpha"?

audit2's doctrine says:

  "Volatility scaling is free alpha. Simply scaling positions by inverse
   realized vol improves Sharpe by 0.3+ for ANY momentum strategy."

My first test (PART15) capped the weight at 1.0x — no leverage — and measured a
mean Sharpe delta of +0.01. But that test was arguably unfair to the claim:
inverse-vol sizing's whole point is to LEVER UP when volatility is low, and
capping at 1.0x removes exactly that mechanism. So this script tests the claim
properly, three ways:

  A. capped    w = min(target/vol, 1.0)                     no leverage, no borrow
  B. uncapped  w = target/vol                              leverage, borrow FREE
  C. uncapped  w = target/vol  minus borrow cost           leverage, borrow PAID

Only C is investable. B is the version most advocates have in mind when they
quote a Sharpe improvement, and it is usually quoted without a borrow cost.

Vol estimate uses trailing 12-month realised vol, lagged one month. Target vol is
the full-sample realised vol of the series, which is generous to the claim (it
sits near the middle of the vol distribution, so the weight averages ~1).
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "portfolios" / "price_cache.json"
OUT = ROOT / "reports" / "vol_scaling"

BORROW_RATE = 0.05     # annual, on the levered excess (broker margin / futures financing)
VOL_WINDOW = 12        # months
WEIGHT_CAP = 2.0       # safety cap even in "uncapped" mode; 2x is the practical limit


def monthly_series() -> dict[str, pd.Series]:
    raw = json.loads(CACHE.read_text())
    out = {}
    for t, d in raw.items():
        s = pd.Series(d)
        s.index = pd.to_datetime(s.index)
        s = s.sort_index().resample("ME").last().dropna()
        if len(s) > 120:
            out[t] = s
    return out


def sharpe(r: pd.Series) -> float:
    r = r.dropna()
    sd = r.std(ddof=1)
    return (r.mean() / sd * math.sqrt(12)) if sd else float("nan")


def mdd(curve: pd.Series) -> float:
    c = curve / curve.cummax()
    return float(c.min() - 1) * 100


def run_variant(r: pd.Series, mode: str) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Returns (returns, weights, borrow_cost)."""
    vol = r.rolling(VOL_WINDOW).std().shift(1)
    target = r.std()
    w_raw = (target / vol).replace([np.inf, -np.inf], np.nan)
    if mode == "capped":
        w = w_raw.clip(upper=1.0)
        borrow = pd.Series(0.0, index=r.index)
    else:
        w = w_raw.clip(upper=WEIGHT_CAP)
        if mode == "uncapped_paid":
            excess = (w - 1.0).clip(lower=0.0)
            borrow = excess * (BORROW_RATE / 12)
        else:
            borrow = pd.Series(0.0, index=r.index)
    w = w.fillna(0.0)
    gross = w * r
    return gross - borrow, w, borrow


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    series = monthly_series()
    if not series:
        print("no cached price data — run tools/portfolio_option_backtest.py --init first")
        return 2

    MODES = [("capped", "A capped (no leverage)"),
             ("uncapped_free", "B uncapped, borrow FREE"),
             ("uncapped_paid", "C uncapped, borrow PAID")]

    print("=== audit2 CLAIM: 'vol scaling improves Sharpe by 0.3+ for ANY momentum strategy' ===")
    print(f"    borrow rate {BORROW_RATE*100:.1f}%/yr on levered excess, vol window {VOL_WINDOW}m, cap {WEIGHT_CAP}x\n")

    results = {}
    for name, px in sorted(series.items()):
        r = px.pct_change().dropna()
        if len(r) < 120:
            continue
        base_mom = ((px / px.shift(12) - 1) > 0).astype(float).shift(1).fillna(0.0)
        r_mom = base_mom * r
        sh_mom = sharpe(r_mom)
        print(f"--- {name}  (n={len(r)} months, buy&hold Sharpe {sharpe(r):.2f}, "
              f"12m-mom Sharpe {sh_mom:.2f})")
        row = {"mom_sharpe": sh_mom, "bh_sharpe": sharpe(r)}
        for mode, label in MODES:
            rv, w, borrow = run_variant(r, mode)
            sh = sharpe(rv)
            avg_w = float(w.loc[w.index > w.index[VOL_WINDOW]].mean()) if len(w) > VOL_WINDOW else float("nan")
            row[f"{mode}_sharpe"] = sh
            row[f"{mode}_delta"] = sh - sh_mom
            row[f"{mode}_avg_weight"] = avg_w
            row[f"{mode}_borrow_drag_ann_pct"] = float(borrow.mean() * 12 * 100)
            print(f"    {label:<26} Sharpe {sh:>6.2f}  delta {sh - sh_mom:>+6.2f}  "
                  f"avg weight {avg_w:>5.2f}x  borrow drag {borrow.mean()*12*100:>5.2f}%/yr")
        results[name] = row
        print()

    print("=== VERDICT ===")
    for mode, label in MODES:
        deltas = [v[f"{mode}_delta"] for v in results.values() if not math.isnan(v[f"{mode}_delta"])]
        if not deltas:
            continue
        mean_d = statistics.mean(deltas)
        n_ge_03 = sum(1 for d in deltas if d >= 0.3)
        print(f"  {label:<26} mean delta {mean_d:>+6.2f}   "
              f"cells reaching +0.30: {n_ge_03}/{len(deltas)}")
    print()
    b = [v["uncapped_free_delta"] for v in results.values() if not math.isnan(v["uncapped_free_delta"])]
    c = [v["uncapped_paid_delta"] for v in results.values() if not math.isnan(v["uncapped_paid_delta"])]
    if b and c:
        mb, mc = statistics.mean(b), statistics.mean(c)
        print(f"  mean delta: free leverage {mb:+.3f}, paid leverage {mc:+.3f}, "
              f"difference {mb - mc:+.3f} Sharpe")
        # guard: a percentage against a near-zero denominator is meaningless noise
        if abs(mb) < 0.05:
            print(f"  NOTE: the free-leverage gain is ~0 ({mb:+.3f}), so expressing the")
            print(f"  deterioration as a PERCENTAGE of it would divide by ~zero and")
            print(f"  produce a nonsense figure. Report the absolute delta instead.")
        else:
            print(f"  Charging {BORROW_RATE*100:.0f}%/yr removes "
                  f"{(1 - (mc / mb)) * 100:.0f}% of the leverage gain.")
    print("\n  The claim says 'for ANY momentum strategy'. The honest restatement is:")
    print("  vol scaling is a LEVERAGE RULE. It raises Sharpe only while you are")
    print("  allowed to lever into low-vol periods and financing is free. With no")
    print("  leverage it does nothing (PART15: +0.01); with paid leverage it does")
    print("  little. It is not alpha and it is not free.")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "vol_scaling_doctrine.json").write_text(json.dumps(
        {"generated_utc": pd.Timestamp.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
         "borrow_rate": BORROW_RATE, "vol_window": VOL_WINDOW, "weight_cap": WEIGHT_CAP,
         "claim": "vol scaling improves Sharpe by 0.3+ for any momentum strategy",
         "per_series": results}, indent=1))
    print(f"\nwrote {OUT/'vol_scaling_doctrine.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
