#!/usr/bin/env python3
"""Block 3 / Round D7 + D6: independent Donchian breakout backtest on real
equity/ETF daily bars, plus a data-grounded horizon comparison.

Data: data/cache/asset_class_review/*_5y.csv (Date,Open,High,Low,Close,Volume)
      -- 79 symbols, ~1254 daily bars each, 2021-11-22 .. 2026-11-19.

Pre-registered rule (fixed BEFORE looking at results):
  Entry : close above the highest HIGH of the prior N days  (N = 20 and N = 55,
          both reported -- never the better one alone)
  Exit  : close below the lowest LOW of the prior M days (M = 10)
          OR time stop of 40 trading days
          OR initial stop at 2 x ATR(14) below entry
  Fill  : signal on a CLOSED bar, fill at the NEXT bar's OPEN  (no look-ahead)
  Size  : one unit per signal, equal weight, no leverage
  Costs : per-side cost charged on entry and on exit.
          US equity ETF: 5 bp/side at 1x (commission ~0 + slippage ~5bp).
          Reported at 1x and 2x.

Statistics: n, mean/median net return per trade, 95% bootstrap CI on the mean
(seed 42, 2000 resamples), annualized Sharpe (per-trade mean/std * sqrt(trades
per year), stated convention), max drawdown of the trade-sequence equity
curve, annualized vol.

Controls:
  * Walk-forward: >=5 sequential folds over the trade timeline, OOS Sharpe per
    fold, count positive. Compared honestly to the ledger's claimed +0.61.
  * Random-entry null: same symbols, same exit logic, same holding-period
    distribution, entries on random dates, >=500 shuffles. Observed result's
    percentile within the null distribution is reported.
  * Selection alpha: strategy return minus buy-and-hold of the same instrument
    over the same holding windows.

This script also emits the D6 horizon comparison from real on-disk data.
Never fabricates a price series. Prints a JSON stat block.
"""
from __future__ import annotations

import glob
import json
import math
import os
import random
import statistics
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data", "cache", "asset_class_review")
REPORTS = os.path.join(ROOT, "reports")

# ---------------------------------------------------------------- config
COST_PER_SIDE_1X = 0.0005          # 5 bp/side for US equity ETF
ATR_LEN = 14
EXIT_LOW_LOOKBACK = 10
TIME_STOP = 40
ENTRY_NS = [20, 55]
BOOT_SEED = 42
BOOT_N = 2000
NULL_SHUFFLES = 500
WF_FOLDS = 5

# liquid, listed ETF/equity universe that actually exists on disk
EQUITY_UNIVERSE = ["SPY", "QQQ", "IWM", "DIA", "XLK", "XLF", "XLV", "XLE",
                   "GLD", "TLT", "SOXX", "AAPL", "MSFT", "NVDA", "JPM"]
CRYPTO_UNIVERSE = ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD"]


def load(ticker):
    p = os.path.join(DATA_DIR, f"{ticker}_5y.csv")
    if not os.path.exists(p):
        return None
    rows = []
    with open(p) as fh:
        hdr = fh.readline().strip().split(",")
        idx = {h: i for i, h in enumerate(hdr)}
        for line in fh:
            parts = line.strip().split(",")
            if len(parts) < 5:
                continue
            try:
                rows.append({
                    "date": parts[idx["Date"]],
                    "o": float(parts[idx["Open"]]),
                    "h": float(parts[idx["High"]]),
                    "l": float(parts[idx["Low"]]),
                    "c": float(parts[idx["Close"]]),
                })
            except (KeyError, ValueError):
                continue
    return rows


def atr_series(rows, n=ATR_LEN):
    """Simple ATR (Wilder-ish via mean of true range over n) aligned to rows."""
    tr = [None] * len(rows)
    for i in range(len(rows)):
        if i == 0:
            tr[i] = rows[i]["h"] - rows[i]["l"]
        else:
            pc = rows[i - 1]["c"]
            tr[i] = max(rows[i]["h"] - rows[i]["l"],
                        abs(rows[i]["h"] - pc),
                        abs(rows[i]["l"] - pc))
    out = [None] * len(rows)
    for i in range(len(rows)):
        if i + 1 >= n:
            window = tr[i - n + 1:i + 1]
            out[i] = sum(window) / n
    return out


def backtest_symbol(rows, N, M=EXIT_LOW_LOOKBACK, cost_side=COST_PER_SIDE_1X,
                    random_entry=False, rng=None):
    """Return list of trade dicts. Next-bar open fills. No look-ahead."""
    if len(rows) < max(N, ATR_LEN, M) + 5:
        return []
    atr = atr_series(rows)
    trades = []
    i = max(N, ATR_LEN, M)
    while i < len(rows) - 1:
        # entry signal evaluated on closed bar i
        if random_entry:
            enter = rng.random() < 0.02       # ~2% chance per bar, same for all shuffles
        else:
            hh = max(r["h"] for r in rows[i - N:i])   # highest high of the PRIOR N days
            enter = rows[i]["c"] > hh and atr[i] is not None
        if not enter or atr[i] is None:
            i += 1
            continue
        fill_i = i + 1
        entry = rows[fill_i]["o"]
        stop = entry - 2.0 * atr[i]
        exit_i = None
        exit_price = None
        for j in range(fill_i, min(len(rows) - 1, fill_i + TIME_STOP + 1)):
            # evaluate exits on closed bar j, fill next open
            if rows[j]["l"] <= stop:
                exit_i = j + 1
                exit_price = min(rows[j + 1]["o"], stop) if j + 1 < len(rows) else stop
                break
            if j - fill_i >= TIME_STOP:
                exit_i = j + 1
                exit_price = rows[j + 1]["o"] if j + 1 < len(rows) else rows[j]["c"]
                break
            if j - M >= 0:
                low_m = min(r["l"] for r in rows[j - M:j])   # prior M bars, excl. j
                if rows[j]["c"] < low_m:
                    exit_i = j + 1
                    exit_price = rows[j + 1]["o"] if j + 1 < len(rows) else rows[j]["c"]
                    break
        if exit_i is None:
            exit_i = len(rows) - 1
            exit_price = rows[-1]["c"]
        if exit_price is None:
            i = exit_i + 1
            continue
        gross = (exit_price - entry) / entry
        net = gross - 2.0 * cost_side
        # buy-and-hold of same instrument over same window
        bh = (rows[exit_i]["c"] - entry) / entry if exit_i < len(rows) else gross
        trades.append({
            "symbol": None,
            "entry_date": rows[fill_i]["date"],
            "exit_date": rows[exit_i]["date"],
            "bars_held": exit_i - fill_i,
            "gross": gross,
            "net": net,
            "bh": bh,
            "alpha": net - bh,
        })
        i = exit_i + 1
    return trades


def run_universe(universe, N, cost_side, random_entry=False, rng=None):
    all_tr = []
    for t in universe:
        rows = load(t)
        if not rows:
            continue
        for tr in backtest_symbol(rows, N, cost_side=cost_side,
                                  random_entry=random_entry, rng=rng):
            tr["symbol"] = t
            all_tr.append(tr)
    all_tr.sort(key=lambda x: x["entry_date"])
    return all_tr


def bootstrap_ci(vals, seed=BOOT_SEED, n=BOOT_N):
    if not vals:
        return [None, None]
    rng = random.Random(seed)
    means = []
    L = len(vals)
    for _ in range(n):
        s = 0.0
        for _ in range(L):
            s += vals[rng.randrange(L)]
        means.append(s / L)
    means.sort()
    lo = means[int(0.025 * n)]
    hi = means[int(0.975 * n) - 1]
    return [lo, hi]


def sharpe_annualized(nets, avg_bars_per_trade, bars_per_year=252):
    if len(nets) < 3:
        return None
    mu = statistics.mean(nets)
    sd = statistics.pstdev(nets)
    if sd == 0 or avg_bars_per_trade <= 0:
        return None
    trades_per_year = bars_per_year / avg_bars_per_trade
    return mu / sd * math.sqrt(trades_per_year)


def equity_curve_stats(nets):
    eq = 1.0
    peak = 1.0
    maxdd = 0.0
    curve = []
    for r in nets:
        eq *= (1.0 + r)
        peak = max(peak, eq)
        dd = eq / peak - 1.0
        maxdd = min(maxdd, dd)
        curve.append(eq)
    return maxdd, curve


def summarize(trades):
    nets = [t["net"] for t in trades]
    if not nets:
        return {"n": 0}
    avg_bars = statistics.mean([t["bars_held"] for t in trades])
    maxdd, _ = equity_curve_stats(nets)
    mu = statistics.mean(nets)
    sd = statistics.pstdev(nets) if len(nets) > 1 else 0.0
    return {
        "n_trades": len(nets),
        "mean_net": round(mu, 6),
        "median_net": round(statistics.median(nets), 6),
        "mean_gross": round(statistics.mean([t["gross"] for t in trades]), 6),
        "win_rate": round(sum(1 for x in nets if x > 0) / len(nets), 4),
        "ci95_mean": [round(x, 6) if x is not None else None
                      for x in bootstrap_ci(nets)],
        "sharpe_ann": (round(sharpe_annualized(nets, avg_bars), 4)
                       if sharpe_annualized(nets, avg_bars) is not None else None),
        "sharpe_convention": "per-trade mean/std * sqrt(trades_per_year), 252 bars/yr",
        "max_drawdown": round(maxdd, 6),
        "ann_vol": round(sd * math.sqrt(252.0 / avg_bars), 6) if avg_bars > 0 else None,
        "avg_bars_held": round(avg_bars, 2),
        "mean_selection_alpha": round(statistics.mean([t["alpha"] for t in trades]), 6),
        "alpha_ci95": [round(x, 6) if x is not None else None
                       for x in bootstrap_ci([t["alpha"] for t in trades])],
    }


def walk_forward(trades, folds=WF_FOLDS):
    if len(trades) < folds * 5:
        return {"folds": [], "n_positive": 0, "note": "too few trades"}
    size = len(trades) // folds
    out = []
    for k in range(folds):
        chunk = trades[k * size:(k + 1) * size] if k < folds - 1 else trades[k * size:]
        nets = [t["net"] for t in chunk]
        avg_bars = statistics.mean([t["bars_held"] for t in chunk])
        s = sharpe_annualized(nets, avg_bars)
        out.append({
            "fold": k + 1,
            "n": len(nets),
            "start": chunk[0]["entry_date"],
            "end": chunk[-1]["entry_date"],
            "mean_net": round(statistics.mean(nets), 6),
            "sharpe_ann": round(s, 4) if s is not None else None,
        })
    return {"folds": out,
            "n_positive": sum(1 for f in out if f["sharpe_ann"] and f["sharpe_ann"] > 0),
            "n_folds": folds}


def random_entry_null(universe, N, cost_side, observed_sharpe, shuffles=NULL_SHUFFLES):
    rng = random.Random(BOOT_SEED)
    sh = []
    means = []
    for _ in range(shuffles):
        tr = run_universe(universe, N, cost_side, random_entry=True, rng=rng)
        if len(tr) < 5:
            continue
        nets = [t["net"] for t in tr]
        avg_bars = statistics.mean([t["bars_held"] for t in tr])
        s = sharpe_annualized(nets, avg_bars)
        if s is not None:
            sh.append(s)
            means.append(statistics.mean(nets))
    if not sh:
        return {"shuffles_effective": 0}
    sh.sort()
    pct = 100.0 * sum(1 for x in sh if x < (observed_sharpe or 0)) / len(sh)
    pct_mean = 100.0 * sum(1 for x in means if x < 0) / len(means)  # placeholder
    return {
        "shuffles_effective": len(sh),
        "null_sharpe_mean": round(statistics.mean(sh), 4),
        "null_sharpe_p95": round(sh[int(0.95 * len(sh)) - 1], 4),
        "null_sharpe_max": round(max(sh), 4),
        "observed_sharpe": round(observed_sharpe, 4) if observed_sharpe is not None else None,
        "observed_percentile": round(pct, 2),
        "null_mean_net_mean": round(statistics.mean(means), 6),
    }


def gate(stat1x, stat2x, wf, null, alpha_ci):
    g1 = stat1x.get("ci95_mean") and stat1x["ci95_mean"][0] is not None \
        and stat1x["ci95_mean"][0] > 0
    g2 = stat2x.get("mean_net") is not None and stat2x["mean_net"] > 0
    g3 = wf.get("n_positive", 0) >= 3
    g4 = null.get("observed_percentile") is not None and null["observed_percentile"] >= 95.0
    g5 = alpha_ci and alpha_ci[0] is not None and alpha_ci[0] > 0
    res = {"G1_ci_mean_net_gt0_1x": bool(g1),
           "G2_mean_net_gt0_2x": bool(g2),
           "G3_three_of_five_folds_positive": bool(g3),
           "G4_above_p95_random_entry": bool(g4),
           "G5_selection_alpha_ci_lb_gt0": bool(g5)}
    if all(res.values()):
        verdict = "CANDIDATE"
    elif g1 and g4:
        verdict = "WEAK"
    else:
        verdict = "KILL"
    res["verdict"] = verdict
    return res


# ---------------------------------------------------------------- D6
def bh_stats(ticker, start=None, window_bars=None):
    rows = load(ticker)
    if not rows:
        return None
    if start is not None:
        rows = [r for r in rows if r["date"] >= start]
    if window_bars is not None:
        rows = rows[-window_bars:]
    if len(rows) < 30:
        return None
    closes = [r["c"] for r in rows]
    rets = [(closes[i] / closes[i - 1] - 1.0) for i in range(1, len(closes))]
    years = len(rows) / 252.0
    total = closes[-1] / closes[0] - 1.0
    cagr = (closes[-1] / closes[0]) ** (1.0 / years) - 1.0 if years > 0 else None
    mu = statistics.mean(rets)
    sd = statistics.pstdev(rets)
    maxdd, _ = equity_curve_stats(rets)
    return {
        "symbol": ticker,
        "start": rows[0]["date"],
        "end": rows[-1]["date"],
        "n_bars": len(rows),
        "total_return": round(total, 4),
        "cagr": round(cagr, 4) if cagr is not None else None,
        "ann_vol": round(sd * math.sqrt(252), 4),
        "sharpe_ann": round(mu / sd * math.sqrt(252), 4) if sd > 0 else None,
        "max_drawdown": round(maxdd, 4),
    }


def fx_spot_stats(pair="EURUSD"):
    p = os.path.join(ROOT, "data", "forex_rate_cache", f"{pair}.csv")
    if not os.path.exists(p):
        return None
    vals = []
    with open(p) as fh:
        fh.readline()
        for line in fh:
            parts = line.strip().split(",")
            if len(parts) >= 2:
                try:
                    vals.append((parts[0], float(parts[1])))
                except ValueError:
                    continue
    if len(vals) < 30:
        return None
    rets = [vals[i][1] / vals[i - 1][1] - 1.0 for i in range(1, len(vals))]
    sd = statistics.pstdev(rets)
    years = len(vals) / 252.0
    return {
        "pair": pair,
        "start": vals[0][0],
        "end": vals[-1][0],
        "n_bars": len(vals),
        "spot_change_total": round(vals[-1][1] / vals[0][1] - 1.0, 4),
        "ann_vol": round(sd * math.sqrt(252), 4),
        "is_investment_return": False,
        "note": "Spot FX has no carry/interest. This is price change only, "
                "NOT an investment return. Positive only with a rate differential.",
    }


def gic_breakeven():
    """Sensitivity: required risky return to beat a nominal GIC after costs
    and volatility drag. NOT a fabricated GIC series."""
    out = {}
    for gic in [0.03, 0.04, 0.05]:
        for cost in [0.0, 0.005, 0.02]:   # annual cost drag
            for vol in [0.0, 0.15, 0.30, 0.60]:
                # volatility drag: expected log growth ~ mu - vol^2/2
                drag = 0.5 * vol * vol
                req = gic + cost + drag
                out[f"gic={gic:.0%}|cost={cost:.1%}|vol={vol:.0%}"] = round(req, 4)
    return {
        "description": "Required arithmetic annualized return a risky asset must "
                       "earn to match a GIC of the given nominal rate, after annual "
                       "cost drag and volatility drag (0.5*sigma^2).",
        "grid": out,
    }


def pods_snapshot():
    p = os.path.join(ROOT, "audit_dashboard", "data", "dashboard_data.json")
    if not os.path.exists(p):
        return {"note": "dashboard_data.json not found"}
    d = json.load(open(p))
    sp = d.get("sidecar_promotion_status") or {}
    rows = {k: {"n_forward_rows": v.get("n", 0),
                "status": v.get("status"),
                "wr": v.get("wr"), "pf": v.get("pf")} for k, v in sp.items()}
    return {
        "source": "audit_dashboard/data/dashboard_data.json::sidecar_promotion_status",
        "pods": rows,
        "note": "POD-EQUITY-BREAKOUT is pre_registered but not in this map and emits "
                "zero rows; all pods here have n=0 forward rows => no measurable "
                "return. No return is invented for them.",
    }


def main():
    os.makedirs(REPORTS, exist_ok=True)
    out = {"generated_at": datetime.now(timezone.utc).isoformat(),
           "data_source": "data/cache/asset_class_review/*_5y.csv",
           "rule": {
               "entry": "close > highest high of prior N days (N=20 and 55)",
               "exit": "close < lowest low prior 10d OR 40 bar time stop OR 2*ATR14 stop",
               "fill": "NEXT bar open (no look-ahead)",
               "cost_per_side_1x": COST_PER_SIDE_1X,
               "cost_per_side_2x": COST_PER_SIDE_1X * 2,
           },
           "d7": {}}

    for N in ENTRY_NS:
        tr1 = run_universe(EQUITY_UNIVERSE, N, COST_PER_SIDE_1X)
        tr2 = run_universe(EQUITY_UNIVERSE, N, COST_PER_SIDE_1X * 2)
        s1 = summarize(tr1)
        s2 = summarize(tr2)
        wf = walk_forward(tr1)
        null = random_entry_null(EQUITY_UNIVERSE, N, COST_PER_SIDE_1X,
                                 s1.get("sharpe_ann"))
        g = gate(s1, s2, wf, null, s1.get("alpha_ci95"))
        out["d7"][f"N={N}"] = {"1x": s1, "2x": s2, "walk_forward": wf,
                              "random_entry_null": null, "gates": g}

    # D6 horizon comparison
    d6 = {"equities": {}, "crypto": {}, "fx": {}, "pods": pods_snapshot(),
          "gic_breakeven": gic_breakeven()}
    for t in ["SPY", "QQQ", "IWM", "BTC-USD", "GLD", "TLT"]:
        st = bh_stats(t)
        if st:
            key = "crypto" if t.endswith("-USD") else "equities"
            d6[key][t] = st
    d6["fx"]["EURUSD"] = fx_spot_stats("EURUSD")
    d6["fx"]["USDJPY"] = fx_spot_stats("USDJPY")
    out["d6"] = d6

    # Horizon comparison on the SAME window as the equity data (start of the
    # equity cache) so vehicles are comparable; plus short/medium/long slices.
    common_start = "2021-11-22"
    horizons = {"short_1y": 252, "medium_3y": 756, "long_full": None}
    d6h = {"common_start": common_start,
           "common_window_note": "All vehicles aligned to the equity cache start "
                                 "(2021-11-22) so returns are comparable.",
           "vehicles": ["SPY", "QQQ", "IWM", "GLD", "TLT", "BTC-USD"],
           "horizons": {}}
    for hname, bars in horizons.items():
        d6h["horizons"][hname] = {}
        for t in d6h["vehicles"]:
            st = bh_stats(t, start=common_start, window_bars=bars)
            if st:
                d6h["horizons"][hname][t] = st
    d6h["fx"] = {"EURUSD": fx_spot_stats("EURUSD"), "USDJPY": fx_spot_stats("USDJPY")}
    d6h["fx_note"] = ("Spot FX price change is NOT an investment return: no carry, "
                      "no interest, no dividend. Not comparable to an ETF/GIC without "
                      "a rate differential. Shown for price behaviour only.")
    d6h["pods"] = d6["pods"]
    d6h["gic_breakeven"] = d6["gic_breakeven"]
    d6h["gic_note"] = ("No GIC/savings market series exists in the repo. A GIC/HISA is "
                       "a known nominal rate with ~zero vol and CDIC-type protection. "
                       "The break-even grid is a SENSITIVITY, not a data series; no GIC "
                       "return series was fabricated.")

    path = os.path.join(REPORTS, "breakout_backtest_20261122.json")
    with open(path, "w") as fh:
        json.dump(out, fh, indent=2)
    hpath = os.path.join(REPORTS, "horizon_comparison_20261122.json")
    with open(hpath, "w") as fh:
        json.dump(d6h, fh, indent=2)
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
