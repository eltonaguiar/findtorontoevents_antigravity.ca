#!/usr/bin/env python3
"""
equity_reversal_backtest.py — is short-horizon equity reversal a REAL edge?
===========================================================================

The 2026-06-13 money-ready research fleet converged on one forward-looking,
literature-grounded, immediately-testable hypothesis: short-horizon equity
RETURN-REVERSAL (Lehmann 1990 / Jegadeesh 1990). Our own data says why it should
work — current LONG pick entries chase tops (hourly MFE median +0.5% vs MAE +3.8%),
so FADING short-term extremes is the structural cure.

This backtests it END-TO-END on `stock_ohlcv` (hourly RTH bars, 214 symbols,
~2026-03..2026-06) — no dependency on the contaminated pick book. The design is a
CROSS-SECTIONAL LONG-SHORT, which is MARKET-NEUTRAL BY CONSTRUCTION: it longs the
biggest recent losers and shorts the biggest recent winners in equal weight, so a
pure market move (beta) cancels. That is the built-in beta control this project
keeps needing — if the only "edge" is that the market fell, a long-short collapses
to ~0.

Method:
  1. Build daily bars per symbol from the hourly RTH bars (open=first, close=last,
     high=max, low=min, per calendar date).
  2. Exclude non-equity rows that share this table (`=X` FX, `=F` futures).
  3. Signal on day T = trailing close-to-close return r_T = close_T/close_{T-1}-1.
  4. Each day, cross-sectionally rank the symbols with a valid signal; LONG the
     bottom `pct` fraction (losers), SHORT the top `pct` fraction (winners).
  5. Hold one session. Two exit modes:
       intraday : enter T+1 open, exit T+1 close   (no overnight gap)
       c2c      : enter T close,  exit T+1 close    (close-to-close, incl. overnight)
  6. Net of cost: subtract a round-trip `2*per_side_bps` from EVERY leg.
  7. Daily long-short net return = mean(long legs) - mean(short legs).
  8. Report: gross/net daily mean, %positive days, daily-return PF, annualized
     Sharpe, cumulative; IS/OOS by distinct date halves; per-leg (long vs short);
     and a beta regression of the long-short series on SPY (alpha vs beta).

A real edge = net-positive in BOTH IS and OOS halves, beta ~ 0 (market-neutral),
and not driven by a single leg in a single fortnight.

Read-only. Usage:
  DB_PASS_STOCKS=... python3 tools/equity_reversal_backtest.py
  DB_PASS_STOCKS=... python3 tools/equity_reversal_backtest.py --pct 0.2 --exit c2c --per-side-bps 3
  python3 tools/equity_reversal_backtest.py --self-test

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _daily_from_hourly(rows):
    """rows: list of dicts (timestamp ms, open, high, low, close) ascending.
    Returns dict date_str -> {open, high, low, close} aggregated per RTH date."""
    by_date = {}
    for r in rows:
        d = datetime.fromtimestamp(r["timestamp"] / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        o, h, l, c = float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"])
        if d not in by_date:
            by_date[d] = {"open": o, "high": h, "low": l, "close": c}
        else:
            bd = by_date[d]
            bd["high"] = max(bd["high"], h)
            bd["low"] = min(bd["low"], l)
            bd["close"] = c  # last bar's close
    return by_date


def _stats(returns):
    n = len(returns)
    if n == 0:
        return {"n": 0, "mean": 0.0, "pos_pct": 0.0, "pf": 0.0, "sharpe": 0.0, "cum": 0.0}
    mean = sum(returns) / n
    gains = sum(r for r in returns if r > 0)
    losses = -sum(r for r in returns if r < 0)
    pf = gains / losses if losses > 0 else (float("inf") if gains > 0 else 0.0)
    var = sum((r - mean) ** 2 for r in returns) / n
    sd = var ** 0.5
    sharpe = (mean / sd * (252 ** 0.5)) if sd > 0 else 0.0   # daily -> annualized
    cum = 1.0
    for r in returns:
        cum *= (1 + r)
    return {"n": n, "mean": mean, "pos_pct": sum(1 for r in returns if r > 0) / n,
            "pf": pf, "sharpe": sharpe, "cum": cum - 1.0}


def _ols_beta(y, x):
    """Return (alpha_daily, beta) of y ~ alpha + beta*x. Lists aligned."""
    n = len(y)
    if n < 3 or len(x) != n:
        return 0.0, 0.0
    mx = sum(x) / n
    my = sum(y) / n
    sxx = sum((xi - mx) ** 2 for xi in x)
    sxy = sum((x[i] - mx) * (y[i] - my) for i in range(n))
    beta = sxy / sxx if sxx > 0 else 0.0
    alpha = my - beta * mx
    return alpha, beta


def run_backtest(daily_by_sym, dates, pct, exit_mode, per_side_bps, bench="SPY"):
    """daily_by_sym: {symbol: {date: bar}}. dates: sorted list of common-ish dates."""
    rt_cost = 2 * per_side_bps / 10000.0  # round-trip per leg, in fraction
    ls_daily = []            # net long-short daily returns
    ls_gross = []
    long_daily, short_daily = [], []
    ls_dates = []
    per_day_counts = []

    for i in range(1, len(dates) - 1):
        d_prev, d_sig, d_hold = dates[i - 1], dates[i], dates[i + 1]
        # signal = close_sig / close_prev - 1, for symbols having all needed bars
        sigs = []
        for sym, dd in daily_by_sym.items():
            if d_prev in dd and d_sig in dd and d_hold in dd:
                cp = dd[d_prev]["close"]
                cs = dd[d_sig]["close"]
                if cp > 0:
                    sigs.append((sym, cs / cp - 1.0))
        if len(sigs) < 10:
            continue
        sigs.sort(key=lambda t: t[1])
        k = max(1, int(len(sigs) * pct))
        losers = [s for s, _ in sigs[:k]]      # LONG these (reversal: they bounce)
        winners = [s for s, _ in sigs[-k:]]    # SHORT these (they revert down)

        def leg_ret(sym, is_long):
            dd = daily_by_sym[sym]
            if exit_mode == "intraday":
                entry = dd[d_hold]["open"]
                exit_ = dd[d_hold]["close"]
            else:  # c2c
                entry = dd[d_sig]["close"]
                exit_ = dd[d_hold]["close"]
            if entry <= 0:
                return None
            r = (exit_ / entry - 1.0) if is_long else (entry / exit_ - 1.0)
            return r - rt_cost

        lr = [r for r in (leg_ret(s, True) for s in losers) if r is not None]
        sr = [r for r in (leg_ret(s, False) for s in winners) if r is not None]
        if not lr or not sr:
            continue
        lmean = sum(lr) / len(lr)
        smean = sum(sr) / len(sr)
        ls = (lmean + smean) / 2.0  # equal capital long & short; each already net of cost
        gross_ls = ls + rt_cost     # approx add back one leg's cost for gross view
        ls_daily.append(ls)
        ls_gross.append(gross_ls)
        long_daily.append(lmean)
        short_daily.append(smean)
        ls_dates.append(d_hold)
        per_day_counts.append(k)

    # benchmark daily returns aligned to ls_dates (intraday or c2c SPY)
    bench_rets = []
    bsym = daily_by_sym.get(bench)
    if bsym:
        for j, d_hold in enumerate(ls_dates):
            # find d_sig = the date before d_hold in `dates`
            idx = dates.index(d_hold)
            d_sig = dates[idx - 1]
            if exit_mode == "intraday":
                e, x = bsym.get(d_hold, {}).get("open"), bsym.get(d_hold, {}).get("close")
            else:
                e, x = bsym.get(d_sig, {}).get("close"), bsym.get(d_hold, {}).get("close")
            bench_rets.append((x / e - 1.0) if (e and x) else 0.0)

    return {"ls_daily": ls_daily, "ls_gross": ls_gross, "long_daily": long_daily,
            "short_daily": short_daily, "ls_dates": ls_dates, "bench_rets": bench_rets,
            "avg_names_per_side": (sum(per_day_counts) / len(per_day_counts)) if per_day_counts else 0}


def _self_test():
    # two symbols, 4 days; loser bounces, winner reverts -> long-short positive
    base = 1700000000000
    hour = 3600000
    def mk(prices):
        # one bar/day, open=close=high=low=price for simplicity
        return [{"timestamp": base + i * 24 * hour, "open": p, "high": p, "low": p, "close": p}
                for i, p in enumerate(prices)]
    # A: down then up (loser->bounce); B: up then down (winner->revert)
    daily = {"A": _daily_from_hourly(mk([100, 90, 99, 99])),
             "B": _daily_from_hourly(mk([100, 110, 101, 101]))}
    dates = sorted(set(daily["A"]) | set(daily["B"]))
    # not enough symbols (need >=10) -> just exercise helpers
    s = _stats([0.01, -0.005, 0.02, 0.0])
    assert s["n"] == 4 and abs(s["mean"] - 0.00625) < 1e-9, s
    a, b = _ols_beta([2, 4, 6], [1, 2, 3])
    assert abs(b - 2.0) < 1e-9 and abs(a) < 1e-9, (a, b)
    bd = _daily_from_hourly([
        {"timestamp": base, "open": 10, "high": 12, "low": 9, "close": 11},
        {"timestamp": base + hour, "open": 11, "high": 13, "low": 10, "close": 12.5},
    ])
    d0 = list(bd.values())[0]
    assert d0["open"] == 10 and d0["close"] == 12.5 and d0["high"] == 13 and d0["low"] == 9, d0
    print("[self-test] all assertions passed")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--pct", type=float, default=0.2, help="fraction per side (0.2 = quintile L/S).")
    ap.add_argument("--exit", choices=["intraday", "c2c"], default="c2c")
    ap.add_argument("--per-side-bps", type=float, default=3.0)
    ap.add_argument("--min-days", type=int, default=20, help="min daily bars for a symbol to be included.")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()

    import pymysql
    from tools.db_env import get_stocks_creds
    conn = pymysql.connect(**get_stocks_creds(), cursorclass=pymysql.cursors.DictCursor)
    cur = conn.cursor()

    cur.execute("SELECT DISTINCT symbol FROM stock_ohlcv")
    syms = [r["symbol"] for r in cur.fetchall()
            if "=X" not in r["symbol"] and "=F" not in r["symbol"]]
    daily_by_sym = {}
    for sym in syms:
        cur.execute("SELECT timestamp,open,high,low,close FROM stock_ohlcv WHERE symbol=%s ORDER BY timestamp ASC", (sym,))
        rows = cur.fetchall()
        dd = _daily_from_hourly(rows)
        if len(dd) >= args.min_days:
            daily_by_sym[sym] = dd
    conn.close()

    all_dates = sorted({d for dd in daily_by_sym.values() for d in dd})
    print(f"\n=== EQUITY SHORT-HORIZON REVERSAL BACKTEST ===")
    print(f"universe={len(daily_by_sym)} symbols (=X/=F excluded), trading days={len(all_dates)}")
    print(f"signal=prev close-to-close return; LONG bottom {args.pct:.0%} / SHORT top {args.pct:.0%}; "
          f"exit={args.exit}; cost={args.per_side_bps}bp/side\n")

    res = run_backtest(daily_by_sym, all_dates, args.pct, args.exit, args.per_side_bps)
    ls = res["ls_daily"]
    if not ls:
        print("no tradable days"); return 0

    full = _stats(ls)
    half = len(ls) // 2
    is_s = _stats(ls[:half]); oos_s = _stats(ls[half:])
    long_s = _stats(res["long_daily"]); short_s = _stats(res["short_daily"])
    gross = _stats(res["ls_gross"])
    alpha, beta = _ols_beta(ls, res["bench_rets"]) if res["bench_rets"] else (0.0, 0.0)

    def line(tag, s):
        print(f"  {tag:14s} n={s['n']:3d}  mean/day {s['mean']*100:+.3f}%  pos {s['pos_pct']*100:.0f}%  "
              f"PF {s['pf']:.2f}  Sharpe(ann) {s['sharpe']:.2f}  cum {s['cum']*100:+.1f}%")
    print("── Long-short (market-neutral) daily return series ──")
    line("GROSS LS", gross)
    line("NET LS", full)
    line("  IS half", is_s)
    line("  OOS half", oos_s)
    print("── Per-leg (net) ──")
    line("LONG losers", long_s)
    line("SHORT winners", short_s)
    print("── Beta control (NET LS regressed on SPY) ──")
    print(f"  alpha/day {alpha*100:+.3f}%   beta {beta:+.2f}   (beta~0 => genuinely market-neutral; alpha>0 net => real edge)")
    print(f"  avg names/side: {res['avg_names_per_side']:.0f}")

    money_ready = (full["mean"] > 0 and is_s["mean"] > 0 and oos_s["mean"] > 0
                   and abs(beta) < 0.3 and full["pf"] >= 1.3)
    print(f"\n  REVERSAL EDGE (net+ in BOTH halves, |beta|<0.3, PF>=1.3): {'YES ✅' if money_ready else 'NO'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
