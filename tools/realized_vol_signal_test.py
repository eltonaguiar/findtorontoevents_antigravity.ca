#!/usr/bin/env python3
"""realized_vol30 deep-dive — is the lone surviving edge candidate tradeable?

`reports/qlib_factor_research_2026-05-18.md` found `realized_vol30` the only
qlib factor with a year-stable forward-return tercile spread (+0.60%, 25+/8-).
This tests it as an actual TIMING signal, cost-adjusted, walk-forward:

  - For each ETF, weekly OHLCV.
  - realized_vol30 = stdev of the last 30 weekly returns (trailing, no look-ahead).
  - Signal: at week t, the realized_vol30 percentile within its own trailing
    104-week distribution. "High-vol" = percentile >= 0.67.
  - Strategy: hold the ETF for the next week whenever last week's signal was
    high-vol; else flat (cash). Pay COST_BPS round-trip on every position
    change.
  - Compare strategy CAGR / Sharpe / max-drawdown to buy-and-hold.
  - Year-by-year: does the strategy beat buy-hold consistently?

A real tradeable edge: cost-adjusted strategy Sharpe > buy-hold Sharpe AND
positive in a majority of years AND not carried by one regime.

    python tools/realized_vol_signal_test.py [--cost-bps 5] [--pctl 0.67]
                                             [--out report.md]
"""
from __future__ import annotations

import argparse
import math
import statistics
import sys
from pathlib import Path

UNIVERSE = ("SPY", "QQQ", "IWM", "GLD", "SLV", "XLK", "XLE", "EEM", "TLT", "HYG")
VOL_WIN = 30        # weeks for realized vol
PCTL_WIN = 104      # trailing weeks for the percentile rank
WARMUP = VOL_WIN + PCTL_WIN + 2


def fetch(ticker):
    import time
    import warnings
    warnings.filterwarnings("ignore")
    import yfinance as yf
    for _ in range(3):
        df = yf.download(ticker, period="max", interval="1wk",
                         progress=False, auto_adjust=True)
        if df is not None and len(df) >= WARMUP + 60:
            break
        time.sleep(5)
    else:
        return []
    close = df["Close"]
    if hasattr(close, "columns"):
        close = close.iloc[:, 0]
    rows = []
    for idx in close.index:
        try:
            c = float(close.loc[idx])
        except (TypeError, ValueError):
            continue
        d = idx.date() if hasattr(idx, "date") else None
        if d is not None and c > 0:
            rows.append((str(d), c))
    return rows


def _sharpe(weekly_rets):
    if len(weekly_rets) < 8:
        return 0.0
    mu = statistics.fmean(weekly_rets)
    sd = statistics.pstdev(weekly_rets)
    return 0.0 if sd == 0 else mu / sd * math.sqrt(52)


def _max_dd(equity):
    peak, mdd = equity[0], 0.0
    for v in equity:
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1.0)
    return mdd


def test_symbol(rows, cost_bps: float, pctl: float) -> dict | None:
    closes = [c for _, c in rows]
    dates = [d for d, _ in rows]
    rets = [0.0] + [closes[i] / closes[i - 1] - 1.0 for i in range(1, len(closes))]
    cost = cost_bps / 10000.0
    strat_r, bh_r, strat_years = [], [], {}
    prev_pos = 0
    for t in range(WARMUP, len(closes) - 1):
        win_rets = rets[t - VOL_WIN:t]
        rv = statistics.pstdev(win_rets)
        hist = []
        for u in range(t - PCTL_WIN, t):
            hist.append(statistics.pstdev(rets[u - VOL_WIN:u]))
        rank = sum(1 for h in hist if h <= rv) / len(hist)
        pos = 1 if rank >= pctl else 0          # decided at t, applied to t->t+1
        fwd = rets[t + 1]
        sr = pos * fwd - (cost if pos != prev_pos else 0.0)
        prev_pos = pos
        strat_r.append(sr)
        bh_r.append(fwd)
        strat_years.setdefault(dates[t][:4], []).append((sr, fwd))
    if len(strat_r) < 52:
        return None
    eq_s, eq_b = [1.0], [1.0]
    for s, b in zip(strat_r, bh_r):
        eq_s.append(eq_s[-1] * (1 + s))
        eq_b.append(eq_b[-1] * (1 + b))
    yrs = len(strat_r) / 52.0
    return {
        "n_weeks": len(strat_r),
        "strat_cagr": eq_s[-1] ** (1 / yrs) - 1,
        "bh_cagr": eq_b[-1] ** (1 / yrs) - 1,
        "strat_sharpe": _sharpe(strat_r),
        "bh_sharpe": _sharpe(bh_r),
        "strat_mdd": _max_dd(eq_s),
        "bh_mdd": _max_dd(eq_b),
        "time_in_market": sum(1 for s, b in zip(strat_r, bh_r) if s != 0) / len(strat_r),
        "by_year": {y: (sum(s for s, _ in v), sum(b for _, b in v))
                    for y, v in strat_years.items()},
    }


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cost-bps", type=float, default=5.0)
    ap.add_argument("--pctl", type=float, default=0.67)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    out = [f"# realized_vol30 — cost-adjusted timing-signal deep-dive",
           "",
           f"Signal: hold the ETF next week when realized_vol30 is in the top "
           f"{(1-args.pctl)*100:.0f}% of its trailing {PCTL_WIN}-week distribution; "
           f"else cash. Round-trip cost {args.cost_bps:.0f} bps. No look-ahead.",
           "", "| ETF | strat Sharpe | B&H Sharpe | strat CAGR | B&H CAGR | "
           "strat MDD | B&H MDD | time in mkt |", "|---|---|---|---|---|---|---|---|"]
    beat_sharpe = years_pos = years_tot = 0
    pooled_years: dict[str, list] = {}
    n_sym = 0
    for sym in UNIVERSE:
        rows = fetch(sym)
        r = test_symbol(rows, args.cost_bps, args.pctl) if rows else None
        if not r:
            out.append(f"| {sym} | — | — | — | — | — | — | skipped |")
            continue
        n_sym += 1
        beat = r["strat_sharpe"] > r["bh_sharpe"]
        beat_sharpe += beat
        out.append(f"| {sym} | {r['strat_sharpe']:.2f}{'*' if beat else ''} | "
                   f"{r['bh_sharpe']:.2f} | {r['strat_cagr']*100:+.1f}% | "
                   f"{r['bh_cagr']*100:+.1f}% | {r['strat_mdd']*100:.0f}% | "
                   f"{r['bh_mdd']*100:.0f}% | {r['time_in_market']*100:.0f}% |")
        for y, (s, b) in r["by_year"].items():
            pooled_years.setdefault(y, [0.0, 0.0])
            pooled_years[y][0] += s
            pooled_years[y][1] += b
    out += ["", f"`*` = strategy Sharpe beats buy-and-hold. "
            f"**{beat_sharpe}/{n_sym} ETFs**, cost-adjusted.", ""]
    out += ["## Pooled by year — strategy vs buy-hold (summed weekly returns)", "",
            "| year | strat | B&H | strat wins? |", "|---|---|---|---|"]
    for y in sorted(pooled_years):
        s, b = pooled_years[y]
        win = s > b
        years_tot += 1
        years_pos += win
        out.append(f"| {y} | {s*100:+.1f}% | {b*100:+.1f}% | {'yes' if win else 'no'} |")
    edge = beat_sharpe >= 0.6 * max(n_sym, 1) and years_pos >= 0.6 * max(years_tot, 1)
    out += ["",
            f"**Verdict: {'TRADEABLE EDGE candidate — ' if edge else 'NOT a tradeable edge — '}"
            f"strategy beats buy-hold Sharpe on {beat_sharpe}/{n_sym} ETFs and wins "
            f"{years_pos}/{years_tot} pooled years (cost {args.cost_bps:.0f}bps).**"]
    if not edge:
        out.append("realized_vol30 timing does not beat passive holding once costs "
                    "are paid — it is the 7th candidate to fail. The in-house edge "
                    "search is exhausted; next move is new signal sources.")
    report = "\n".join(out)
    if args.out:
        args.out.write_text(report, encoding="utf-8")
        print(f"# wrote {args.out}", file=sys.stderr)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
