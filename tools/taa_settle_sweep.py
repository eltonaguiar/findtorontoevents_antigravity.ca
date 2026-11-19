#!/usr/bin/env python3
"""Settle the ETF tactical-allocation claim with a written spec and a real grid.

The claim under test (copilot plan 2026-11-19, sourcing
reports/TACTICAL_ROTATION_EDGE_2026-07-04.md):
    "top5-6m rotation 2007-2026 Sharpe 0.88 vs SPY 0.74, MaxDD -19% vs -51%"

This tool does not try to make the claim true or false. It pre-registers the
success criterion, sweeps the parameter space around the claim, and reports
every cell so any reader can see whether the headline sits on a plateau or on a
single lucky corner.

Success criterion (fixed before the run, see SETTLE_CRITERION below):
    at least one cell with lag=1 month and cost>=5bps reaching
    Sharpe >= 0.88 AND MaxDD >= -19% over 2007-2026.

Outputs (both under reports/):
    taa_prices_2026-11-19.json   monthly close cache (reruns are offline-cheap)
    taa_settle_2026-11-19.json   every cell + verdict + benchmark rows
    taa_settle_2026-11-19.csv    same cells, spreadsheet-friendly

Exit codes: 0 ok (regardless of verdict); 3 no price data.

Usage:
    python3 tools/taa_settle_sweep.py                # full sweep
    python3 tools/taa_settle_sweep.py --refresh      # re-download prices
    python3 tools/taa_settle_sweep.py --quick        # one universe, lag=1 only
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "reports" / "taa_prices_2026-11-19.json"
OUT_JSON = ROOT / "reports" / "taa_settle_2026-11-19.json"
OUT_CSV = ROOT / "reports" / "taa_settle_2026-11-19.csv"

# Universe definitions. SECTORS is the 11-SPDR rotation the claim's wording
# ("top5-6m rotation") matches; BROAD is the repo's own 15-ETF tactical spec.
SECTORS = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY", "XLC", "SPY"]
BROAD = ["SPY", "QQQ", "EFA", "EEM", "IWM", "VNQ", "DBC", "GLD", "TLT", "IEF",
         "HYG", "LQD", "XLE", "XLU", "XLV"]

UNIVERSES = {"sectors_11spdr": SECTORS, "broad_15etf": BROAD}
WINDOWS = [("2007-01", "2026-11"), ("2018-01", "2026-11")]

TOP_NS = [3, 5, 8]
LOOKBACKS = [3, 6, 9, 12]
LAGS = [0, 1]           # 0 = look-ahead (reproduces a naive doc), 1 = implementable
COSTS_BPS = [0, 5, 10]  # per unit of turnover
ABS_MOM = [False, True]  # True = require positive trailing return, else cash

#: The pre-registered bar. Do not edit after the first run: the whole point of
#: pre-registration is that the criterion is not chosen after seeing results.
SETTLE_CRITERION = {"lag": 1, "min_cost_bps": 5, "min_sharpe": 0.88,
                    "max_drawdown_floor_pct": -19.0, "window": "2007-01..2026-11"}


def _download(syms: list[str]) -> dict[str, list[list]]:
    """Monthly closes for every symbol. Total-return (auto_adjust) by default."""
    import yfinance as yf

    df = yf.download(sorted(set(syms)), period="max", interval="1mo",
                     auto_adjust=True, progress=False, group_by="ticker",
                     threads=True)
    out: dict[str, list[list]] = {}
    if df is None or len(df) == 0:
        return out
    multi = hasattr(df.columns, "levels") and len(df.columns.levels) > 1
    for s in sorted(set(syms)):
        try:
            sub = df[s] if multi else df
            ser = sub["Close"].dropna()
        except Exception:  # noqa: BLE001 - a missing ticker is not fatal
            continue
        if len(ser) < 24:
            continue
        out[s] = [[str(getattr(d, "strftime", lambda *_: str(d))("%Y-%m")), float(v)]
                  for d, v in ser.items()]
    return out


def load_prices(refresh: bool = False) -> dict[str, list[list]]:
    if CACHE.exists() and not refresh:
        try:
            d = json.loads(CACHE.read_text(encoding="utf-8"))
            if d:
                return d
        except Exception:  # noqa: BLE001
            pass
    data = _download(SECTORS + BROAD)
    if data:
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(data), encoding="utf-8")
    return data


def build_matrix(syms: list[str], prices: dict[str, list[list]]):
    """Aligned (T x N) monthly simple-return matrix + the month labels."""
    have = [s for s in syms if s in prices]
    if not have:
        return None, None, []
    months = sorted({m for s in have for m, _ in prices[s]})
    close = {s: dict(prices[s]) for s in have}
    prices_arr = np.full((len(months), len(have)), np.nan)
    for j, s in enumerate(have):
        for i, m in enumerate(months):
            v = close[s].get(m)
            if v is not None:
                prices_arr[i, j] = v
    rets = np.full_like(prices_arr, np.nan)
    rets[1:] = prices_arr[1:] / prices_arr[:-1] - 1.0
    return rets, months, have


def _stats(r: np.ndarray) -> dict:
    r = r[np.isfinite(r)]
    if len(r) < 12:
        return {"cagr_pct": None, "sharpe": None, "mdd_pct": None, "ann_vol_pct": None}
    cum = np.cumprod(1.0 + r)
    cagr = cum[-1] ** (12.0 / len(r)) - 1.0
    sd = float(np.std(r, ddof=1))
    sharpe = float(np.mean(r) / sd * math.sqrt(12)) if sd > 0 else None
    peak = np.maximum.accumulate(cum)
    mdd = float(np.min(cum / peak - 1.0))
    return {"cagr_pct": round(cagr * 100, 3),
            "sharpe": None if sharpe is None else round(sharpe, 3),
            "mdd_pct": round(mdd * 100, 2),
            "ann_vol_pct": round(sd * math.sqrt(12) * 100, 2)}


def rotate(rets: np.ndarray, names: list[str], top_n: int, lookback: int,
           abs_mom: bool, lag: int, cost_bps: float,
           start: str, end: str) -> dict:
    """Equal-weight top-N rotation on trailing `lookback`-month return."""
    T, N = rets.shape
    port: list[float] = []
    prev: set[int] = set()
    switches = 0
    exposure = 0
    cost = cost_bps / 10_000.0
    for t in range(T):
        # decision time is t-1 (signal) shifted back by `lag` months
        if t == 0:
            port.append(0.0)
            continue
        s = t - 1 - lag
        port.append(0.0)  # placeholder replaced below
        if s - lookback < 0:
            prev = set()
            continue
        # trailing return over the lookback window ending at s
        window = np.prod(1.0 + np.nan_to_num(rets[s - lookback + 1:s + 1], nan=0.0), axis=0)
        valid = np.isfinite(rets[s - lookback + 1:s + 1]).all(axis=0)
        score = np.where(valid, window - 1.0, -np.inf)
        if abs_mom:
            score = np.where(score > 0, score, -np.inf)
        order = np.argsort(-score)[:top_n]
        chosen = {int(j) for j in order if np.isfinite(score[j])}
        if not chosen:
            prev = set()
            continue
        exposure += 1
        r = np.nanmean(rets[t, list(chosen)])
        turnover = len(chosen.symmetric_difference(prev)) / max(1, len(chosen))
        if prev != chosen:
            switches += 1
        port[t] = float(r) - cost * turnover
        prev = chosen
    arr = np.array(port[1:])
    labels = None
    return {"port": arr, "switches": switches, "exposure_pct": round(100.0 * exposure / max(1, T - 1), 1)}


def run(universe: str, prices: dict, top_n: int, lookback: int, abs_mom: bool,
        lag: int, cost_bps: float, start: str, end: str) -> dict | None:
    rets, months, names = build_matrix(UNIVERSES[universe], prices)
    if rets is None:
        return None
    lo, hi = months.index(start) if start in months else 0, len(months)
    if end in months:
        hi = months.index(end) + 1
    sub = rets[lo:hi]
    if len(sub) < 24:
        return None
    res = rotate(sub, names, top_n, lookback, abs_mom, lag, cost_bps, start, end)
    st = _stats(res["port"])
    return {"universe": universe, "n_assets": len(names), "top_n": top_n,
            "lookback_m": lookback, "abs_mom": abs_mom, "lag": lag,
            "cost_bps": cost_bps, "window": f"{start}..{end}", **st,
            "switches": res["switches"], "exposure_pct": res["exposure_pct"]}


def benchmark(prices: dict, start: str, end: str) -> dict | None:
    rets, months, names = build_matrix(["SPY"], prices)
    if rets is None:
        return None
    lo = months.index(start) if start in months else 0
    hi = months.index(end) + 1 if end in months else len(months)
    st = _stats(rets[lo:hi, 0])
    return {"universe": "SPY_buy_hold", "window": f"{start}..{end}", **st}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()

    prices = load_prices(args.refresh)
    if not prices:
        print("no price data", file=sys.stderr)
        return 3

    universes = list(UNIVERSES) if not args.quick else ["broad_15etf"]
    lags = [1] if args.quick else LAGS
    cells: list[dict] = []
    for uni in universes:
        for start, end in WINDOWS:
            for top_n, lb, abs_mom, lag, cost in [
                (t, l, a, g, c)
                for t in TOP_NS for l in LOOKBACKS
                   for a in ABS_MOM for g in lags for c in COSTS_BPS
            ]:
                c = run(uni, prices, top_n, lb, abs_mom, lag, cost, start, end)
                if c:
                    cells.append(c)

    benches = [b for s, e in WINDOWS if (b := benchmark(prices, s, e))]

    crit = SETTLE_CRITERION
    winners = [c for c in cells
               if c["window"] == crit["window"] and c["lag"] == crit["lag"]
               and c["cost_bps"] >= crit["min_cost_bps"] and c["sharpe"] is not None
               and c["sharpe"] >= crit["min_sharpe"]
               and c["mdd_pct"] is not None
               and c["mdd_pct"] >= crit["max_drawdown_floor_pct"]]
    lag1 = [c for c in cells if c["lag"] == 1 and c["sharpe"] is not None]
    lag0 = [c for c in cells if c["lag"] == 0 and c["sharpe"] is not None]
    best = max(lag1, key=lambda c: c["sharpe"]) if lag1 else None

    payload = {
        "generated_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc).isoformat(timespec="seconds"),
        "claim": ("top5-6m rotation 2007-2026 Sharpe 0.88 vs SPY 0.74, "
                  "MaxDD -19% vs -51%"),
        "settle_criterion": crit,
        "verdict": "REPRODUCED" if winners else "NOT_REPRODUCED",
        "n_cells": len(cells),
        "n_winners": len(winners),
        "winner_cells": winners[:20],
        "best_sharpe_lag1": best,
        "max_sharpe_lag0": max((c["sharpe"] for c in lag0), default=None),
        "benchmarks": benches,
        "cells": cells,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")
    if cells:
        keys = sorted({k for c in cells for k in c})
        with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=keys)
            w.writeheader()
            for c in cells:
                w.writerow({k: c.get(k) for k in keys})

    print(f"cells={len(cells)} verdict={payload['verdict']} winners={len(winners)}")
    for b in benches:
        print(f"  SPY {b['window']}: cagr={b['cagr_pct']} sharpe={b['sharpe']} mdd={b['mdd_pct']}")
    if best:
        print(f"  best lag=1: {best['universe']} top{best['top_n']} lb{best['lookback_m']} "
              f"abs={best['abs_mom']} cost{best['cost_bps']} -> sharpe={best['sharpe']} "
              f"cagr={best['cagr_pct']} mdd={best['mdd_pct']}")
    print(f"  wrote {OUT_JSON.relative_to(ROOT)} and {OUT_CSV.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
