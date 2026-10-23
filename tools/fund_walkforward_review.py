#!/usr/bin/env python3
"""Reviewer fixes for OPENCODE fund walk-forward (2026-10-23).

A) FXAIX vs SPY on an IDENTICAL window (common start 2011-05-04+),
   dividend-adjusted closes (yfinance auto_adjust=True), report annualized
   gap + block-bootstrap 95% CI. Expected: ~0.05-0.10% (the fee gap).
B) Prove/deny why mom12==mom3y and sector_rot12==sector_rot3y in the first
   run: print per-year picks under the ORIGINAL buggy 3y-CAGR condition
   (730-day lookback can never contain 700 bars -> NaN fallback fires every
   year) vs the FIXED condition (separate 1095-day window).

NFA: research only, not financial advice.
"""
import json
import os
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

RULES_BUGGY_PAIRS = ("mom12", "mom3y", "sector_rot12", "sector_rot3y")


def load(ticker: str) -> pd.Series:
    import yfinance as yf
    df = yf.download(ticker, start="2000-01-01", end="2026-10-22",
                     auto_adjust=True, progress=False, multi_level_index=False)
    return df["Close"].dropna()


def part_a() -> dict:
    fx = load("FXAIX")
    spy = load("SPY")
    start = max(fx.index[0], spy.index[0])
    end = min(fx.index[-1], spy.index[-1])
    # snap to next common trading day
    common = fx.index.intersection(spy.index)
    start, end = common[0], common[-1]
    fx_w, spy_w = fx.loc[start:end], spy.loc[start:end]
    ann_fx = float((fx_w.iloc[-1] / fx_w.iloc[0]) ** (252 / len(fx_w)) - 1)
    ann_spy = float((spy_w.iloc[-1] / spy_w.iloc[0]) ** (252 / len(spy_w)) - 1)
    # annual differences (calendar-year chains) for CI
    fx_y = fx_w.resample("YE").last()
    spy_y = spy_w.resample("YE").last()
    fx_ret = fx_y.pct_change().dropna()
    spy_ret = spy_y.pct_change().dropna()
    diff = (fx_ret - spy_ret.reindex(fx_ret.index)).dropna()
    rng = np.random.default_rng(42)
    idx = rng.integers(0, len(diff), size=(4000, len(diff)))
    chain = np.prod(1 + diff.values[idx], axis=1) ** (1 / len(diff)) - 1
    lo, hi = np.percentile(chain, [2.5, 97.5])
    fee_gap = (0.0945 - 0.015) / 100  # SPY ER - FXAIX ER
    out = {
        "start": str(start.date()), "end": str(end.date()),
        "bars": int(len(fx_w)),
        "fxaix_annualized_pct": round(ann_fx * 100, 3),
        "spy_annualized_pct": round(ann_spy * 100, 3),
        "gap_fxaix_minus_spy_pct": round((ann_fx - ann_spy) * 100, 3),
        "gap_95ci_pct": [round(float(lo) * 100, 3), round(float(hi) * 100, 3)],
        "expected_fee_gap_pct": round(fee_gap * 100, 3),
        "n_annual_diffs": int(len(diff)),
        "verdict": ("gap consistent with fee difference" if lo <= fee_gap <= hi
                    or abs((ann_fx - ann_spy) - fee_gap) < 0.001
                    else "gap NOT explained by fee alone"),
    }
    return out


def trailing_buggy(prices: pd.Series, asof) -> dict | None:
    """Original first-run logic: single 730-day window, cagr3 needs >=700 BARS
    inside that window -> impossible (~500 trading days) -> always NaN."""
    start = asof - pd.Timedelta(days=730)
    w = prices.loc[(prices.index > start) & (prices.index <= asof)]
    if len(w) < 250:
        return None
    daily = w.pct_change().dropna()
    if len(daily) < 200:
        return None
    ret12 = float(w.iloc[-1] / w.iloc[0] - 1)
    cagr3 = np.nan
    if len(w) >= 700:  # never true for a 730-day window
        cagr3 = 0.0
    sharpe = float(daily.mean() / daily.std() * np.sqrt(252)) if daily.std() > 0 else 0.0
    cum = (1 + daily).cumprod()
    mdd = float(((cum - cum.cummax()) / cum.cummax()).min())
    return {"ret12": ret12, "cagr3": cagr3, "sharpe": sharpe, "mdd": mdd}


def trailing_fixed(prices: pd.Series, asof) -> dict | None:
    st = trailing_buggy(prices, asof)
    if st is None:
        return None
    s3 = asof - pd.Timedelta(days=1095)
    w3 = prices.loc[(prices.index > s3) & (prices.index <= asof)]
    if len(w3) >= 500:
        yrs = len(w3) / 252
        st["cagr3"] = float((w3.iloc[-1] / w3.iloc[0]) ** (1 / yrs) - 1)
    return st


def run_walkforward(px: dict, trailing_fn) -> dict:
    panel = pd.DataFrame(px).sort_index().ffill(limit=10)
    sectors = ["XLF", "XLK", "XLV", "XLE", "XLI", "XLY", "XLP", "XLU", "XLB"]
    picks = {r: {} for r in RULES_BUGGY_PAIRS}
    for y in range(2006, 2025):
        rd = pd.Timestamp(f"{y}-12-31")
        cand = panel.index[panel.index <= rd]
        if not len(cand):
            continue
        d = cand[-1]
        elig = []
        for t in panel.columns:
            s = panel[t].dropna()
            if len(s) < 100 or s.index[0] > d - pd.DateOffset(years=2):
                continue
            st = trailing_fn(s, d)
            if st is None or np.isnan(st["ret12"]):
                continue
            elig.append({"t": t, **st})
        if len(elig) < 10:
            continue
        e = pd.DataFrame(elig)
        e3 = e.dropna(subset=["cagr3"])
        sec = e[e["t"].isin(sectors)]
        mom12 = e.sort_values("ret12", ascending=False).iloc[0]["t"]
        picks["mom12"][y] = mom12
        picks["mom3y"][y] = (e3.sort_values("cagr3", ascending=False).iloc[0]["t"]
                             if len(e3) else mom12)  # NaN fallback -> identical
        if len(sec):
            s12 = sec.sort_values("ret12", ascending=False).iloc[0]["t"]
            picks["sector_rot12"][y] = s12
            sec3 = sec.dropna(subset=["cagr3"])
            picks["sector_rot3y"][y] = (sec3.sort_values("cagr3", ascending=False).iloc[0]["t"]
                                        if len(sec3) else s12)  # NaN fallback
        else:
            picks["sector_rot12"][y] = picks["sector_rot3y"][y] = "N/A"
    return picks


def part_b() -> dict:
    tickers = ["VFINX", "FCNTX", "FOCPX", "AIVSX", "CWGIX", "PRGFX", "SPY", "QQQ",
               "DIA", "IWM", "XLF", "XLK", "XLV", "XLE", "XLI", "XLY", "XLP", "XLU",
               "XLB", "IVV", "VTSAX", "VTI", "TLT", "AGG", "VGT", "VNQ", "GLD", "VIG",
               "DJP", "BND", "VOO", "VXUS", "FXAIX", "FSKAX", "SCHD", "VFV.TO",
               "XAW.TO", "XLRE", "VBAL.TO", "VGRO.TO", "XLC", "ZGRO.TO", "XEQT.TO"]
    px = {}
    import yfinance as yf
    for t in tickers:
        df = yf.download(t, start="2000-01-01", end="2026-10-22",
                         auto_adjust=True, progress=False, multi_level_index=False)
        if df is not None and len(df) >= 500:
            px[t] = df["Close"].dropna()
    buggy = run_walkforward(px, trailing_buggy)
    fixed = run_walkforward(px, trailing_fixed)
    return {"buggy_picks": buggy, "fixed_picks": fixed}


def main() -> None:
    a = part_a()
    print("PART A — FXAIX vs SPY, identical window, dividend-adjusted:")
    for k, v in a.items():
        print(f"  {k}: {v}")
    b = part_b()
    print("\nPART B — per-year picks (buggy first-run logic vs fixed):")
    for pair in (("mom12", "mom3y"), ("sector_rot12", "sector_rot3y")):
        r1, r2 = pair
        same_buggy = b["buggy_picks"][r1] == b["buggy_picks"][r2]
        same_fixed = b["fixed_picks"][r1] == b["fixed_picks"][r2]
        print(f"\n  {r1} vs {r2}:")
        print(f"    identical under BUGGY logic: {same_buggy}")
        print(f"    identical under FIXED logic: {same_fixed}")
        print(f"    {'year':>6} {r1:<16} {r2:<16} {'buggy_eq':>8} {'fixed_eq':>8}")
        for y in sorted(set(b["buggy_picks"][r1]) | set(b["buggy_picks"][r2])):
            b1 = b["buggy_picks"][r1].get(y, "-")
            b2 = b["buggy_picks"][r2].get(y, "-")
            f1 = b["fixed_picks"][r1].get(y, "-")
            f2 = b["fixed_picks"][r2].get(y, "-")
            print(f"    {y:>6} {b1:<16} {b2:<16} {str(b1 == b2):>8} {str(f1 == f2):>8}")
        print(f"    FIXED picks {r1}: {b['fixed_picks'][r1]}")
        print(f"    FIXED picks {r2}: {b['fixed_picks'][r2]}")
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "audit_dashboard", "data")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "fund_walkforward_review.json")
    with open(path, "w") as f:
        json.dump({"part_a_fxaix_vs_spy": a, "part_b_identical_pairs": b}, f, indent=2, default=str)
    print(f"\nSaved {path}")


if __name__ == "__main__":
    sys.exit(main())
