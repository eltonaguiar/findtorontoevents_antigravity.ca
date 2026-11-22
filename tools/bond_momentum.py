#!/usr/bin/env python3
"""Item 34 -- bond / rate momentum, on tradeable instruments, pre-registered.

PRE-DECLARED RULE (fixed before any run; copied verbatim from
docs/edge_research/16_COMMODITY_AND_BOND_MOMENTUM_2026-11-22.md section 0.2):

  Tradeable-instrument tests on the 10 bond ETFs in data/cache/asset_class_review
  (TLT, IEF, SHY, TLH, AGG, BND, LQD, TIP, JNK, HYG) over their common window.
  Formation = 12-1 month return (months t-12..t-2, skipping t-1).
  B1 (primary, time-series): each month-end hold equal weight every ETF whose 12-1
  return > 0, else cash at 4.32%. Sign-skip = flat, no shorting (shorting bonds
  costs financing above rf and is impractical for this capital base; the cash leg
  pays rf).
  B2 (cross-sectional, diagnostic): long top 3 / short bottom 3 by 12-1 return.
  B3 (duration timing, mapped): long TLT when the FRED DGS10 month-end yield is
  below its level 3 months earlier, else cash. B3 is an UNTRADEABLE signal (a yield
  cannot be traded); it is mapped through TLT, so its cost is TLT's ETF cost and its
  P&L is TLT's P&L, not the yield's.
  Cost sweep 2/5/10/20 bp per side, base 5 bp/side.
  INSUFFICIENT if the window lacks a sustained rising-rate period or has < 24
  rebalances.

COST BASIS: ETF bp/side is an ASSUMPTION (bond/ETF cost is UNMEASURED here). It is
plausible-to-generous for liquid treasury ETFs (TLT/IEF/SHY ~1-2bp) and optimistic
for HYG/LQD/JNK in stress; the sweep covers that range.

DATA CAVEAT: the cached ETF `Close` behaves as a dividend-adjusted series (proven
for SHY in doc 16: short duration, rates up ~4%, yet +10.4% over 5 years is only
possible with coupons reinvested). The exact adjustment method is UNMEASURED, so
absolute CAGRs are marked as such while relative comparisons stay valid.

PRE-DECLARED SAMPLE CHECK: the window 2021-11 -> 2026-11 spans the 2022-23
rate-hike bear market, so a rising-rate period IS present. But it also contains
only ONE big bond bear; a single episode cannot distinguish a robust rule from a
lucky one -- this limitation is reported, not hidden.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

if __package__ in (None, ""):
    _ROOT = Path(__file__).resolve().parent.parent
    if str(_ROOT) not in sys.path:
        sys.path.insert(0, str(_ROOT))

from tools.momentum_core import (
    BASE_COST_BP, COST_SWEEP_BP, DATA_DIR, N_BOOT, N_NULL, REPO_ROOT, RF_ANNUAL, SEED,
    bootstrap_excess_cagr, load_close_series, load_panel, mom_12_1_by_period,
    month_end_index, monthly_returns, profit_factor, sanitize, summarize,
)

REPORTS_DIR = REPO_ROOT / "reports"
RATES_DIR = REPO_ROOT / "data" / "rates_cache"

BOND_ETFS = ["TLT", "IEF", "SHY", "TLH", "AGG", "BND", "LQD", "TIP", "JNK", "HYG"]


# --------------------------------------------------------------------------- #
# Yield series (for B3)
# --------------------------------------------------------------------------- #
def load_yield(symbol: str, rates_dir: Path = RATES_DIR) -> pd.Series:
    """Daily Treasury constant-maturity yield from a cached FRED CSV."""
    path = rates_dir / f"{symbol}.csv"
    df = pd.read_csv(path, parse_dates=["observation_date"])
    col = df.columns[1]
    df[col] = pd.to_numeric(df[col], errors="coerce")  # FRED uses "." for holidays
    df = df.dropna().drop_duplicates(subset=["observation_date"]).sort_values("observation_date")
    return df.set_index("observation_date")[col].astype(float)


# --------------------------------------------------------------------------- #
# Generic monthly backtest over weights
# --------------------------------------------------------------------------- #
def run_weights(mrets: pd.DataFrame, weight_fn, cost_bp_per_side: float,
                rf_annual: float = RF_ANNUAL, collect_rows: bool = True) -> Dict:
    """Apply per-period weights to forward monthly returns, charging cost on turnover."""
    cost = cost_bp_per_side / 10_000.0
    rf_m = rf_annual / 12.0
    prev_w: Dict[str, float] = {}
    nets, rows = [], []
    for t in mrets.index:
        w, cash_w = weight_fn(t)
        gross = sum(abs(v) for v in w.values()) + cash_w
        gross = gross if gross > 0 else 1.0
        w = {k: v / gross for k, v in w.items()}
        cash_w = cash_w / gross
        turnover = sum(abs(w.get(s, 0.0) - prev_w.get(s, 0.0))
                       for s in set(w) | set(prev_w))
        gross_ret = sum(wt * float(mrets.loc[t, s]) for s, wt in w.items())
        net = gross_ret + cash_w * rf_m - cost * turnover
        nets.append(net)
        if collect_rows:
            rows.append({"period_start": t.strftime("%Y-%m-%d"), "net_return": net,
                         "gross_return": gross_ret, "turnover": turnover,
                         "cost_drag": cost * turnover, "cash_weight": cash_w,
                         "weights": {k: round(v, 6) for k, v in sorted(w.items())}})
        prev_w = w
    return {"monthly": np.array(nets), "rows": rows, "n_periods": len(nets)}


# --------------------------------------------------------------------------- #
# B1 / B2 weight functions
# --------------------------------------------------------------------------- #
def _monthly(prices: pd.DataFrame) -> pd.DataFrame:
    """Resample a daily panel to month-ends (the grid 12-1 formation requires)."""
    return prices.loc[month_end_index(prices)]


def b1_time_series(prices: pd.DataFrame, periods: Sequence[pd.Timestamp]):
    """Hold equal weight every ETF with 12-1 return > 0; remainder in cash."""
    scores = mom_12_1_by_period(_monthly(prices), periods)

    def fn(t: pd.Timestamp):
        pos = [s for s, v in scores.get(t, {}).items() if v > 0]
        if not pos:
            return {}, 1.0
        return {s: 1.0 / len(pos) for s in pos}, 0.0
    return fn


def b2_cross_sectional(prices: pd.DataFrame, periods: Sequence[pd.Timestamp], k: int = 3):
    """Long top-k / short bottom-k by 12-1 return, equal weight."""
    scores = mom_12_1_by_period(_monthly(prices), periods)

    def fn(t: pd.Timestamp):
        sc = {s: v for s, v in scores.get(t, {}).items() if np.isfinite(v)}
        if len(sc) < 2 * k:
            return {}, 1.0
        ranked = sorted(sc.items(), key=lambda kv: kv[1], reverse=True)
        w = {}
        for s, _ in ranked[:k]:
            w[s] = w.get(s, 0.0) + 1.0 / k
        for s, _ in ranked[-k:]:
            w[s] = w.get(s, 0.0) - 1.0 / k
        return w, 0.0
    return fn


def b3_duration_timing(y10: pd.Series):
    """Long TLT when the DGS10 month-end yield is below its level 3 months earlier.

    The comparison uses the last yield month-end <= t (as-of, no lookahead), so a
    holiday mismatch between the yield and ETF calendars cannot leak future data.
    """
    y_me = y10.loc[month_end_index(y10.to_frame("y"))]

    def fn(t: pd.Timestamp):
        past = y_me[y_me.index <= t]
        if len(past) < 4:
            return {}, 1.0
        return ({"TLT": 1.0}, 0.0) if past.iloc[-1] < past.iloc[-4] else ({}, 1.0)
    return fn


# --------------------------------------------------------------------------- #
# Null: shuffle which ETFs are held, keep count and hold period
# --------------------------------------------------------------------------- #
def null_time_series(prices: pd.DataFrame, mrets: pd.DataFrame, cost_bp: float,
                     n_shuffles: int = N_NULL, seed: int = SEED) -> Dict:
    """Null for B1: each month hold the same NUMBER of names, chosen at random."""
    rng = np.random.default_rng(seed)
    real_rows = run_weights(mrets, b1_time_series(prices, list(mrets.index)), cost_bp)["rows"]
    real = summarize(np.array([r["net_return"] for r in real_rows]))
    # Same number of names per month as the real rule (including all-cash months).
    counts = [len(r["weights"]) for r in real_rows]
    syms = list(prices.columns)
    null = []
    for _ in range(n_shuffles):
        chosen = {t: list(rng.choice(syms, size=counts[i], replace=False))
                  for i, t in enumerate(mrets.index)}

        def fn(t, c=chosen):
            if not c[t]:
                return {}, 1.0
            return {s: 1.0 / len(c[t]) for s in c[t]}, 0.0
        null.append(summarize(run_weights(mrets, fn, cost_bp, collect_rows=False)["monthly"])["sharpe_vs_rf"])
    null = np.array([x for x in null if np.isfinite(x)])
    pct = float((null < real["sharpe_vs_rf"]).mean() * 100) if len(null) else float("nan")
    return {"n_shuffles": n_shuffles, "real_sharpe": real["sharpe_vs_rf"],
            "null_sharpe_mean": float(null.mean()) if len(null) else float("nan"),
            "null_sharpe_p95": float(np.percentile(null, 95)) if len(null) else float("nan"),
            "percentile": pct, "beats_random_95": bool(pct >= 95) if np.isfinite(pct) else False}


# --------------------------------------------------------------------------- #
# Break-even
# --------------------------------------------------------------------------- #
def breakeven_bp(stat_fn, hi: float = 500.0) -> Optional[float]:
    """Cost (bp/side) at which Sharpe-vs-rf hits zero, by bisection on cost alone."""
    if stat_fn(0.0) <= 0:
        return 0.0
    if stat_fn(hi) > 0:
        return None
    lo = 0.0
    for _ in range(50):
        mid = (lo + hi) / 2
        if stat_fn(mid) > 0:
            lo = mid
        else:
            hi = mid
    return float((lo + hi) / 2)


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #
def run(data_dir: Path = DATA_DIR, rates_dir: Path = RATES_DIR,
        n_null: int = N_NULL, n_boot: int = N_BOOT) -> Dict:
    prices = load_panel(BOND_ETFS, data_dir)
    me_all = month_end_index(prices)
    # A period starting at month-end k decides at k+1 using 12 months back to k-11,
    # so k >= 11 is the first period with a complete formation window. Warm-up
    # months are dropped rather than padded with cash (which would deflate vol).
    me = me_all[11:]
    mrets = monthly_returns(prices, me)

    spy = load_close_series("SPY", data_dir).to_frame()
    spy_me = [t for t in month_end_index(spy) if me[0] <= t <= me[-1]]
    spy_m = monthly_returns(spy, spy_me).iloc[:, 0].to_numpy()

    y10 = load_yield("DGS10", rates_dir)
    tlt = prices["TLT"]

    inventory = {
        "bond_etfs": BOND_ETFS, "n_etfs": len(BOND_ETFS),
        "etf_rows": int(len(prices)),
        "etf_first_date": prices.index[0].strftime("%Y-%m-%d"),
        "etf_last_date": prices.index[-1].strftime("%Y-%m-%d"),
        "yield_series": {s: {"file": f"data/rates_cache/{s}.csv",
                             "first": str(load_yield(s, rates_dir).index[0].date()),
                             "last": str(load_yield(s, rates_dir).index[-1].date()),
                             "last_value_pct": float(load_yield(s, rates_dir).iloc[-1])}
                         for s in ("DGS2", "DGS5", "DGS10")},
        "etf_close_note": ("Close behaves as dividend-adjusted (proven for SHY); "
                           "adjustment method UNMEASURED"),
    }

    dgs10_window = y10[(y10.index >= me[0]) & (y10.index <= me[-1])]
    sample_check = {
        "window": [me[0].strftime("%Y-%m-%d"), me[-1].strftime("%Y-%m-%d")],
        "n_rebalances": len(mrets),
        "dgs10_start_pct": float(dgs10_window.iloc[0]),
        "dgs10_end_pct": float(dgs10_window.iloc[-1]),
        "dgs10_min_pct": float(dgs10_window.min()),
        "dgs10_max_pct": float(dgs10_window.max()),
        "rising_rate_period_present": bool(dgs10_window.iloc[0] < dgs10_window.max()),
        "n_rate_cycles": "one dominant bear (2022-23); cannot separate skill from luck",
    }

    tests: Dict[str, Dict] = {}

    # ---- B1 time-series ----
    periods = list(mrets.index)
    b1_fn = b1_time_series(prices, periods)
    b1 = run_weights(mrets, b1_fn, BASE_COST_BP)
    b1_sweep = {}
    for bp in COST_SWEEP_BP:
        st = summarize(run_weights(mrets, b1_fn, bp, collect_rows=False)["monthly"])
        b1_sweep[f"{bp:g}bp"] = {"cost_basis": f"{bp:g} bp/side ASSUMED", "cagr": st["cagr"],
                                "sharpe_vs_rf": st["sharpe_vs_rf"], "maxdd": st["maxdd"],
                                "pf": profit_factor(run_weights(mrets, b1_fn, bp, collect_rows=False)["monthly"])}
    tests["B1_time_series_long_only"] = {
        "description": "equal-weight every ETF with 12-1 return > 0, else cash at rf",
        "n_rebalances": b1["n_periods"], "cost_basis": f"base {BASE_COST_BP:g} bp/side ASSUMED",
        "metrics": summarize(b1["monthly"]), "pf_base": profit_factor(b1["monthly"]),
        "cost_sweep": b1_sweep,
        "breakeven_bp_per_side_sharpe_zero": breakeven_bp(
            lambda c: summarize(run_weights(mrets, b1_fn, c, collect_rows=False)["monthly"])["sharpe_vs_rf"]),
        "null": null_time_series(prices, mrets, BASE_COST_BP, n_shuffles=n_null),
        "bootstrap_excess_vs_spy": bootstrap_excess_cagr(b1["monthly"], spy_m, n_boot=n_boot),
        "avg_time_in_market": float(np.mean([1 - r["cash_weight"] for r in b1["rows"]])),
        "per_etf_exposure": {s: round(float(np.mean([r["weights"].get(s, 0.0) for r in b1["rows"]])), 5)
                             for s in BOND_ETFS},
        "monthly_detail": [{"period": r["period_start"], "net": round(r["net_return"], 6),
                            "in_market": round(1 - r["cash_weight"], 4)} for r in b1["rows"]],
    }

    # ---- B2 cross-sectional ----
    b2_fn = b2_cross_sectional(prices, periods, k=3)
    b2 = run_weights(mrets, b2_fn, BASE_COST_BP)
    b2_sweep = {}
    for bp in COST_SWEEP_BP:
        st = summarize(run_weights(mrets, b2_fn, bp, collect_rows=False)["monthly"])
        b2_sweep[f"{bp:g}bp"] = {"cost_basis": f"{bp:g} bp/side ASSUMED", "cagr": st["cagr"],
                                "sharpe_vs_rf": st["sharpe_vs_rf"], "maxdd": st["maxdd"]}
    tests["B2_cross_sectional_long_short"] = {
        "description": "long top-3 / short bottom-3 by 12-1 return (diagnostic)",
        "n_rebalances": b2["n_periods"], "cost_basis": f"base {BASE_COST_BP:g} bp/side ASSUMED",
        "metrics": summarize(b2["monthly"]), "pf_base": profit_factor(b2["monthly"]),
        "cost_sweep": b2_sweep,
        "breakeven_bp_per_side_sharpe_zero": breakeven_bp(
            lambda c: summarize(run_weights(mrets, b2_fn, c, collect_rows=False)["monthly"])["sharpe_vs_rf"]),
        "bootstrap_excess_vs_spy": bootstrap_excess_cagr(b2["monthly"], spy_m, n_boot=n_boot),
        "per_etf_exposure": {s: round(float(np.mean([r["weights"].get(s, 0.0) for r in b2["rows"]])), 5)
                             for s in BOND_ETFS},
    }

    # ---- B3 yield signal mapped through TLT ----
    tlt_frame = tlt.to_frame()
    tlt_me = month_end_index(tlt_frame)[11:]
    tlt_mrets = monthly_returns(tlt_frame, tlt_me)
    b3_fn = b3_duration_timing(y10)
    # align the yield rule to TLT's return calendar
    b3 = run_weights(tlt_mrets, b3_fn, BASE_COST_BP)
    b3_sweep = {}
    for bp in COST_SWEEP_BP:
        st = summarize(run_weights(tlt_mrets, b3_fn, bp, collect_rows=False)["monthly"])
        b3_sweep[f"{bp:g}bp"] = {"cost_basis": f"{bp:g} bp/side ASSUMED", "cagr": st["cagr"],
                                "sharpe_vs_rf": st["sharpe_vs_rf"], "maxdd": st["maxdd"]}
    tlt_bh = summarize(tlt_mrets["TLT"].to_numpy())
    tests["B3_duration_timing_mapped_to_TLT"] = {
        "description": ("long TLT when DGS10 month-end yield < its level 3 months earlier, "
                        "else cash -- UNTRADEABLE yield signal mapped to TLT"),
        "n_rebalances": b3["n_periods"], "cost_basis": f"base {BASE_COST_BP:g} bp/side ASSUMED",
        "metrics": summarize(b3["monthly"]), "pf_base": profit_factor(b3["monthly"]),
        "cost_sweep": b3_sweep,
        "breakeven_bp_per_side_sharpe_zero": breakeven_bp(
            lambda c: summarize(run_weights(tlt_mrets, b3_fn, c, collect_rows=False)["monthly"])["sharpe_vs_rf"]),
        "bootstrap_excess_vs_spy": bootstrap_excess_cagr(b3["monthly"], spy_m, n_boot=n_boot),
        "tlt_buy_hold": {"cost_basis": "zero (buy-and-hold)",
                         "cagr": tlt_bh["cagr"], "sharpe_vs_rf": tlt_bh["sharpe_vs_rf"],
                         "maxdd": tlt_bh["maxdd"], "n_periods": tlt_bh["n"]},
        "avg_time_in_market": float(np.mean([1 - r["cash_weight"] for r in b3["rows"]])),
        "mapping_caveat": ("A yield cannot be traded. This is the yield rule's timing "
                           "decision applied to TLT's price return: the P&L and the cost "
                           "belong to TLT, not to the yield signal."),
    }

    # ---- buy-and-hold references ----
    bh = {}
    for s in BOND_ETFS:
        st = summarize(mrets[s].to_numpy())
        bh[s] = {"cost_basis": "zero (buy-and-hold benchmark)", "cagr": st["cagr"],
                 "sharpe_vs_rf": st["sharpe_vs_rf"], "maxdd": st["maxdd"], "skew": st["skew"]}

    # ---- verdicts ----
    for name, r in tests.items():
        sh10 = r["cost_sweep"]["10bp"]["sharpe_vs_rf"]
        if r["n_rebalances"] < 24:
            verdict = "INSUFFICIENT"
        elif np.isfinite(sh10) and sh10 >= 0.5 and r["bootstrap_excess_vs_spy"]["ci95"][0] > 0:
            verdict = "EDGE"
        elif np.isfinite(sh10) and sh10 >= 0.5:
            verdict = "MARGINAL"
        else:
            verdict = "KILL"
        r["verdict"] = verdict
        r["verdict_conditional_on"] = ("ETF cost assumption (UNMEASURED); dividend "
                                       "adjustment method (UNMEASURED); single 5-year "
                                       "window containing one bond bear")
    if tests["B1_time_series_long_only"]["null"]["percentile"] < 95:
        tests["B1_time_series_long_only"]["verdict"] = "KILL"
        tests["B1_time_series_long_only"]["verdict_note"] = (
            "null percentile < 95: does not beat random selection -- stopping there")

    return sanitize({
        "item": 34, "title": "Bond / rate momentum (tradeable instruments)",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "data_inventory": inventory, "risk_free_annual": RF_ANNUAL,
        "sample_check": sample_check,
        "spy_buy_hold": {"cagr": summarize(spy_m)["cagr"],
                         "sharpe_vs_rf": summarize(spy_m)["sharpe_vs_rf"],
                         "n_periods": len(spy_m)},
        "bond_buy_hold": bh,
        "tests": tests,
    })


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--null", type=int, default=N_NULL)
    ap.add_argument("--boot", type=int, default=N_BOOT)
    ap.add_argument("--out", type=Path, default=REPORTS_DIR / "bond_momentum_20261122.json")
    args = ap.parse_args(argv)
    res = run(n_null=args.null, n_boot=args.boot)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(res, indent=2))
    for name, r in res["tests"].items():
        m = r["metrics"]
        ci = r["bootstrap_excess_vs_spy"]["ci95"]
        print(f"{name}: n={r['n_rebalances']} CAGR={m['cagr']:.4f} Sharpe={m['sharpe_vs_rf']:.3f} "
              f"maxDD={m['maxdd']:.3f} skew={m['skew']:.3f} "
              f"excessCI=[{ci[0]:.4f},{ci[1]:.4f}] BE_bp={r['breakeven_bp_per_side_sharpe_zero']} "
              f"verdict={r['verdict']}")
    print(f"written: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
