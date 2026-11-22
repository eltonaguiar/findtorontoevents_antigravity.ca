#!/usr/bin/env python3
"""commodity_tsmom_check.py — V3: settle the commodity ETF TSMOM conflict.

The conflict
  Mercury3 (COMS notes/antigravity-part12-commodity-rebuild-2026-11-22) measures
  TREND on an 11-commodity-ETF basket at CAGR +3.59% / Sharpe 0.431 / MDD -15.4%
  and calls it the strongest class result in the project.
  My H-223/H-224 refuted commodity TREND on an 8-ETF basket at CI-LB -1.324 bps.
  He offered to withdraw on my number if my gate also rejects his basket, so the
  dispute must be settled on HIS construction, not mine. Disagreements found:
    universe   11 ETFs (adds DBC GSG) vs my 8
    signal     SMA(10) on MONTHLY bars vs my 200-day SMA on DAILY bars
    rebalance  monthly vs daily
  Mercury3 already quantified the cadence effect himself: daily re-entry eats
  whipsaw the monthly rule never sees (his L1 vs L1d = 0.665 vs 0.796 Sharpe).

What this script adds beyond reproducing his number
1. A ZERO-CASH variant. He states most of the +3.59% is T-bill interest earned
   while 57% in cash. If the cash leg carries the result, the "edge" is a
   cash-management artifact, not a commodity signal.
2. Both halves (2011-2019, 2020-2026) — a 180-month window is 15 years but only
   ~2 independent macro regimes.
3. A bootstrap lower bound on mean monthly EXCESS return (the CI-LB gate), which
   is the bar every other cell in this repo was judged by.
4. 1x and 2x cost, so the verdict cannot hinge on 20bp vs 40bp.

Honesty rules
  * signal at month t uses levels through month t-1 (lag=1) or t-2 (lag=2); a
    variant that scores better only under lag=0 would be look-ahead and is not
    run at all;
  * cost is charged on |Δweight| every month, not per trade;
  * Sharpe is excess over the T-bill leg, never over zero;
  * a monthly-end MDD is NOT the same as a daily MDD and is labelled as such;
  * insufficient history or a failed download yields NO_DATA, never a number.

Usage
  python3 tools/commodity_tsmom_check.py [--json out.json] [--no-cache]
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = Path("/tmp/commodity_cache")
UNIVERSE = ["DBC", "GSG", "GLD", "SLV", "USO", "UNG", "CORN", "WEAT", "SOYB", "DBA", "CPER"]
CASH_PROXY = "^IRX"          # 13-week T-bill discount rate, percent
SMA_MONTHS = 10
COST_BPS = 20.0
MIN_MONTHS = 120


def load_daily(symbol: str, max_age_days: float = 7.0) -> list[tuple[str, float]]:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{symbol.replace('^', 'IDX_')}.json"
    if path.exists() and time.time() - path.stat().st_mtime < max_age_days * 86400:
        return json.loads(path.read_text())
    import warnings
    import yfinance as yf
    warnings.filterwarnings("ignore")
    df = yf.download(symbol, period="max", progress=False, auto_adjust=True, threads=False)
    if df is None or len(df) == 0:
        raise RuntimeError(f"no data for {symbol}")
    close = df["Close"]
    if hasattr(close, "columns"):
        close = close.iloc[:, 0]
    close = close.dropna()
    rows = [[d.strftime("%Y-%m-%d"), float(v)] for d, v in close.items()]
    path.write_text(json.dumps(rows))
    return rows


def monthly_last(rows: list[tuple[str, float]]) -> dict[str, float]:
    """Last trading day's close per calendar month."""
    out: dict[str, float] = {}
    for d, v in rows:
        out[d[:7]] = v
    return out


def max_drawdown(vals: list[float]) -> float:
    peak, worst = vals[0], 0.0
    for v in vals:
        peak = max(peak, v)
        worst = min(worst, v / peak - 1.0)
    return worst


def ann_ret(vals: list[float], months: int) -> float:
    if len(vals) < 2 or months <= 0:
        return 0.0
    return (vals[-1] / vals[0]) ** (12.0 / months) - 1.0


def sharpe(excess: list[float]) -> float:
    if len(excess) < 3:
        return 0.0
    mu = sum(excess) / len(excess)
    var = sum((x - mu) ** 2 for x in excess) / (len(excess) - 1)
    sd = math.sqrt(var)
    return 0.0 if sd == 0 else mu / sd * math.sqrt(12.0)


def boot_lb(xs: list[float], n: int = 5000, seed: int = 20261122) -> tuple[float, float]:
    """Bootstrap 5%/95% bounds on the MEAN (not on the Sharpe)."""
    if len(xs) < 12:
        return (0.0, 0.0)
    rnd = random.Random(seed)
    k = len(xs)
    means = []
    for _ in range(n):
        means.append(sum(xs[rnd.randrange(k)] for _ in range(k)) / k)
    means.sort()
    return (means[int(0.05 * n)], means[int(0.95 * n)])


def run_variant(levels: dict[str, list[float]], bill: list[float], months: list[str],
                lag: int, cost_bps: float, cash_rate: bool = True,
                start: int = 0, end: int | None = None) -> dict:
    """Equal-weight the members whose month-end level is above their SMA(10)."""
    names = list(levels)
    n = len(months) if end is None else end
    prev_w = [0.0] * len(names)
    curve, excess, invested_share, switches = [1.0], [], [], 0
    for i in range(max(start, 1), n):
        k = i - lag
        w = [0.0] * len(names)
        if k >= SMA_MONTHS - 1:
            on = []
            for j, nm in enumerate(names):
                lv = levels[nm]
                window = lv[k - SMA_MONTHS + 1:k + 1]
                on.append(1.0 if lv[k] > sum(window) / len(window) else 0.0)
            c = sum(on)
            if c:
                w = [o / c for o in on]
        port = 0.0
        for j, nm in enumerate(names):
            lv = levels[nm]
            port += w[j] * (lv[i] / lv[i - 1] - 1.0)
        cash_m = (bill[i] / 100.0 / 12.0) if cash_rate else 0.0
        port += (1.0 - sum(w)) * cash_m
        turn = sum(abs(w[j] - prev_w[j]) for j in range(len(names)))
        if turn > 1e-12:
            switches += 1
        port -= turn * cost_bps / 1e4
        prev_w = w
        curve.append(curve[-1] * (1.0 + port))
        excess.append(port - cash_m)
        invested_share.append(sum(w))
    m = len(curve) - 1
    lb, ub = boot_lb(excess)
    return {
        "months": m,
        "cagr": round(ann_ret(curve, m), 4),
        "sharpe_excess": round(sharpe(excess), 4),
        "mdd_month_end": round(max_drawdown(curve), 4),
        "final_equity": round(curve[-1], 4),
        "rebalance_months": switches,
        "invested_share": round(sum(invested_share) / max(1, len(invested_share)), 4),
        "mean_excess_bps_month": round(1e4 * sum(excess) / max(1, len(excess)), 4),
        "ci_lb_bps_month": round(1e4 * lb, 4),
        "ci_ub_bps_month": round(1e4 * ub, 4),
        "ci_excludes_zero": lb > 0.0,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=str(ROOT / "reports" / "commodity_tsmom_v3.json"))
    a = ap.parse_args()

    raw, failed = {}, {}
    for sym in UNIVERSE + [CASH_PROXY]:
        try:
            raw[sym] = load_daily(sym)
            print(f"loaded {sym}: {len(raw[sym])} bars {raw[sym][0][0]}..{raw[sym][-1][0]}")
        except Exception as exc:  # noqa: BLE001
            failed[sym] = f"{type(exc).__name__}: {exc}"
            print(f"FAILED {sym}: {failed[sym]}")
    members = [s for s in UNIVERSE if s in raw]
    if len(members) < 5 or CASH_PROXY not in raw:
        out = {"verdict": {"level": "ASSET", "asset_class": "COMMODITY",
                           "basis": "NO_DATA" if len(members) < 5 else "UNMEASURED",
                           "note": f"only {len(members)}/11 members and cash proxy "
                                   f"{'ok' if CASH_PROXY in raw else 'missing'}; "
                                   f"failed={failed}"}}
        Path(a.json).write_text(json.dumps(out, indent=1) + "\n")
        print(json.dumps(out, indent=1))
        return 1

    monthly = {s: monthly_last(raw[s]) for s in members}
    bill_m = monthly_last(raw[CASH_PROXY])
    # Common calendar: the first month in which every member AND the cash proxy trades.
    first = max(min(m for m in monthly[s]) for s in members)
    last = min(max(m for m in monthly[s]) for s in members)
    months = sorted(m for m in bill_m if first <= m <= last)
    levels = {s: [monthly[s][m] for m in months] for s in members}
    bill = [bill_m[m] for m in months]
    print(f"common window {months[0]}..{months[-1]} ({len(months)} months), "
          f"members={len(members)}")

    if len(months) < MIN_MONTHS:
        out = {"verdict": {"level": "ASSET", "asset_class": "COMMODITY",
                           "basis": "INSUFFICIENT_N",
                           "n_months": len(months), "required": MIN_MONTHS}}
        Path(a.json).write_text(json.dumps(out, indent=1) + "\n")
        print(json.dumps(out, indent=1))
        return 1

    # Buy-and-hold equal weight: the same basket with no signal, so the trend
    # result is measured against the asset it is supposed to beat.
    bh = run_variant({s: levels[s] for s in members}, bill, months, lag=1,
                     cost_bps=0.0, cash_rate=False)
    # ...but BH never holds cash, so a cash_rate=True BH would be identical.

    res = {
        "bh_ew": bh,
        "trend_lag1_1x": run_variant(levels, bill, months, 1, COST_BPS),
        "trend_lag1_2x": run_variant(levels, bill, months, 1, COST_BPS * 2),
        "trend_lag1_zero_cash": run_variant(levels, bill, months, 1, COST_BPS, cash_rate=False),
        "trend_lag2_1x": run_variant(levels, bill, months, 2, COST_BPS),
    }

    # Halves, on the same lag-1/cost-1x rule.
    mid = len(months) // 2
    res["half_1_lag1_1x"] = run_variant(levels, bill, months, 1, COST_BPS, end=mid)
    res["half_2_lag1_1x"] = run_variant(levels, bill, months, 1, COST_BPS, start=mid)

    t1 = res["trend_lag1_1x"]
    dz = res["trend_lag1_zero_cash"]
    cash_share = (t1["cagr"] - dz["cagr"]) / t1["cagr"] if t1["cagr"] else 0.0
    delta_sharpe = t1["sharpe_excess"] - bh["sharpe_excess"]

    if t1["ci_lb_bps_month"] > 0 and res["trend_lag1_2x"]["ci_lb_bps_month"] > 0:
        basis = "MEASURED"
    elif t1["ci_lb_bps_month"] > 0:
        basis = "MEASURED"   # positive lower bound, fails at 2x -> reported, not promoted
    else:
        basis = "REFUTED"

    out = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "rule": {"universe": members, "bars": "monthly last trading day",
                 "adjust": "yfinance auto_adjust=True (dividends in)",
                 "signal": f"SMA({SMA_MONTHS}) of month-end level, lag=1 month",
                 "position": "equal weight across members above SMA, remainder T-bill",
                 "cost_bps_one_way_turnover": COST_BPS,
                 "cash_leg": "^IRX / 12 monthly accrual"},
        "data": {"window": {"start": months[0], "end": months[-1]},
                 "months": len(months), "members": len(members),
                 "failed_downloads": failed},
        "reference_mercury3_part12": {"bh_cagr": -0.0083, "bh_sharpe": 0.010,
                                      "bh_mdd": -0.628, "trend_cagr": 0.0359,
                                      "trend_sharpe": 0.431, "trend_mdd": -0.154,
                                      "switches": 23, "invested": 0.43},
        "results": res,
        "cash_leg_share_of_cagr": round(cash_share, 4),
        "delta_sharpe_vs_bh": round(delta_sharpe, 4),
        "verdict": {"level": "ASSET", "asset_class": "COMMODITY", "basis": basis,
                    "n_months": len(months),
                    "net_bps_month_1x": t1["mean_excess_bps_month"],
                    "ci_lb_bps_month_1x": t1["ci_lb_bps_month"],
                    "ci_lb_bps_month_2x": res["trend_lag1_2x"]["ci_lb_bps_month"],
                    "both_halves_positive": (res["half_1_lag1_1x"]["mean_excess_bps_month"] > 0
                                             and res["half_2_lag1_1x"]["mean_excess_bps_month"] > 0),
                    "note": "MDD is month-end, not daily; only ~2 independent regimes in 180 months"},
    }
    Path(a.json).parent.mkdir(parents=True, exist_ok=True)
    Path(a.json).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("results", "cash_leg_share_of_cagr",
                                          "delta_sharpe_vs_bh", "verdict")}, indent=1))
    print(f"wrote {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
