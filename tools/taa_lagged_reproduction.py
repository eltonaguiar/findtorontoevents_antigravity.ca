#!/usr/bin/env python3
"""taa_lagged_reproduction — the written, lag-explicit TAA spec buffy asked for.

Peer review 2026-11-19 (buffy, COMS): "I will withdraw the TAA objection the
moment a written spec reproduces Sharpe>=0.88 at MDD<=-19% WITH a one-month
lag applied — caution: unlagged, this family prints Sharpe 2.00 in my
harness." This script IS that spec: one file, free yfinance data, every
execution convention explicit, so any agent can rerun it byte-for-byte.

Strategy under test (reports/TACTICAL_ROTATION_EDGE_2026-07-04.md):
  * Universe: 14 liquid asset-class ETFs (same list as
    tools/tactical_rotation_tracker.py).
  * Signal at month-end t: trailing L-month total-return momentum from
    month-end adjusted closes (auto_adjust=True -> dividends included).
  * Hold the top-N by momentum, equal weight 1/N; any selected slot with
    momentum <= 0 moves its weight to AGG (absolute filter).
  * Costs: 5 bp on every traded weight leg (sum |delta w| x 5bp per rebalance).

Execution conventions compared (the whole dispute is here):
  lag0   signal and entry at the SAME month-end close t. Reference only —
         borderline look-ahead (you cannot trade a close you used to rank).
  lag1d  entry at the close of the FIRST trading day of month t+1, exit at the
         close of the first trading day of month t+2. This is the convention
         the 2026-07-04 report claimed ("signal at month-end close, hold next
         month", 1-day entry-timing assumption).
  lag1m  buffy's demand: the signal from month t is not executed until the
         month-end close of t+1 (holding month t+2). A full month of signal
         decay.

Output: metric grid (CAGR, Sharpe, MaxDD, Calmar, halves) for lookbacks
{6, 9} x top-N {4, 5} x the three lags, vs SPY buy-and-hold, over 2007+ and
2018+ windows. Writes JSON next to --out-md when requested.

    python3 tools/taa_lagged_reproduction.py                 # print grid
    python3 tools/taa_lagged_reproduction.py --out-md reports/TAA_LAGGED_REPRODUCTION_2026-11-19.md
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

UNIVERSE = ["SPY", "QQQ", "IWM", "EFA", "EEM", "TLT", "IEF", "AGG", "GLD",
            "DBC", "VNQ", "LQD", "HYG", "TIP"]
CASH_ASSET = "AGG"
COST_PER_LEG = 0.0005  # 5 bp on each traded weight leg
START = "2005-01-01"   # data start; metrics windows begin 2007/2018


# ------------------------------------------------------------------ data
def fetch_monthly() -> tuple[list[str], dict[str, dict[str, float]], dict[str, dict[str, float]]]:
    """(sorted month keys, month-END closes, month-FIRST closes) per symbol.

    Adjusted daily closes from yfinance; a month key is 'YYYY-MM'. Symbols
    missing a month (pre-inception) simply lack that key.
    """
    import yfinance as yf

    px = yf.download(UNIVERSE, start=START, progress=False, auto_adjust=True)
    closes = px["Close"] if "Close" in px.columns.get_level_values(0) else px
    month_end: dict[str, dict[str, float]] = {s: {} for s in UNIVERSE}
    month_first: dict[str, dict[str, float]] = {s: {} for s in UNIVERSE}
    for ts, row in closes.iterrows():
        mk = f"{ts.year:04d}-{ts.month:02d}"
        for sym in UNIVERSE:
            try:
                v = float(row[sym])
            except (KeyError, TypeError, ValueError):
                continue
            if math.isnan(v) or v <= 0:
                continue
            month_end[sym][mk] = v             # last write in month wins
            month_first[sym].setdefault(mk, v)  # first write in month wins
    months = sorted({m for s in UNIVERSE for m in month_end[s]})
    return months, month_end, month_first


# ------------------------------------------------------------------ engine
def target_weights(months: list[str], me: dict[str, dict[str, float]],
                   i: int, lookback: int, top_n: int) -> dict[str, float] | None:
    """Equal-weight top-N by L-month momentum at month index i, abs-filtered."""
    if i - lookback < 0:
        return None
    m_now, m_then = months[i], months[i - lookback]
    scored = []
    for sym in UNIVERSE:
        p1, p0 = me[sym].get(m_now), me[sym].get(m_then)
        if p1 and p0:
            scored.append((sym, p1 / p0 - 1.0))
    if len(scored) < top_n + 1:
        return None
    scored.sort(key=lambda x: -x[1])
    w: dict[str, float] = {}
    slot = 1.0 / top_n
    for sym, mom in scored[:top_n]:
        dest = sym if mom > 0 else CASH_ASSET
        w[dest] = w.get(dest, 0.0) + slot
    return w


def asset_return(prices: dict[str, dict[str, float]], sym: str,
                 m_in: str, m_out: str) -> float | None:
    p0, p1 = prices[sym].get(m_in), prices[sym].get(m_out)
    if not p0 or not p1:
        return None
    return p1 / p0 - 1.0


def run_strategy(months: list[str], me, mf, *, lookback: int, top_n: int,
                 lag: str) -> list[tuple[str, float]]:
    """[(holding month, net portfolio return)] under one execution convention.

    lag0:  signal i -> hold me[i]   .. me[i+1]
    lag1d: signal i -> hold mf[i+1] .. mf[i+2]
    lag1m: signal i -> hold me[i+1] .. me[i+2]
    """
    out: list[tuple[str, float]] = []
    prev_w: dict[str, float] = {}
    for i in range(len(months)):
        w = target_weights(months, me, i, lookback, top_n)
        if w is None:
            continue
        if lag == "lag0":
            j_in, j_out, prices = i, i + 1, me
        elif lag == "lag1d":
            j_in, j_out, prices = i + 1, i + 2, mf
        elif lag == "lag1m":
            j_in, j_out, prices = i + 1, i + 2, me
        else:
            raise ValueError(lag)
        if j_out >= len(months):
            continue
        rets = {s: asset_return(prices, s, months[j_in], months[j_out])
                for s in w}
        if any(r is None for r in rets.values()):
            continue
        gross = sum(w[s] * rets[s] for s in w)  # type: ignore[operator]
        traded = sum(abs(w.get(s, 0.0) - prev_w.get(s, 0.0))
                     for s in set(w) | set(prev_w))
        out.append((months[j_in], gross - COST_PER_LEG * traded))
        prev_w = w
    return out


def benchmark(months: list[str], prices, sym: str,
              series: list[tuple[str, float]]) -> list[tuple[str, float]]:
    """Buy-and-hold sym over the exact months the strategy held."""
    held = [m for m, _ in series]
    out = []
    for m in held:
        i = months.index(m)
        if i + 1 >= len(months):
            continue
        r = asset_return(prices, sym, months[i], months[i + 1])
        if r is not None:
            out.append((m, r))
    return out


# ------------------------------------------------------------------ metrics
def metrics(series: list[tuple[str, float]], since: str) -> dict | None:
    rets = [r for m, r in series if m >= since]
    n = len(rets)
    if n < 24:
        return None
    mean = sum(rets) / n
    var = sum((r - mean) ** 2 for r in rets) / (n - 1)
    sd = var ** 0.5
    sharpe = (mean / sd) * math.sqrt(12) if sd else None
    equity = peak = 1.0
    maxdd = 0.0
    for r in rets:
        equity *= 1.0 + r
        peak = max(peak, equity)
        maxdd = min(maxdd, equity / peak - 1.0)
    years = n / 12.0
    cagr = equity ** (1.0 / years) - 1.0

    def half_sharpe(sub):
        if len(sub) < 12:
            return None
        m = sum(sub) / len(sub)
        v = sum((r - m) ** 2 for r in sub) / (len(sub) - 1)
        return round((m / v ** 0.5) * math.sqrt(12), 2) if v else None

    return {
        "n_months": n,
        "cagr_pct": round(cagr * 100, 2),
        "sharpe": round(sharpe, 2) if sharpe is not None else None,
        "max_dd_pct": round(maxdd * 100, 1),
        "calmar": round(cagr / abs(maxdd), 2) if maxdd else None,
        "sharpe_h1": half_sharpe(rets[: n // 2]),
        "sharpe_h2": half_sharpe(rets[n // 2:]),
    }


# ------------------------------------------------------------------ report
def build() -> dict:
    months, me, mf = fetch_monthly()
    grid: dict[str, dict] = {}
    spy_done: dict[str, dict] = {}
    for lag in ("lag0", "lag1d", "lag1m"):
        for lookback in (6, 9):
            for top_n in (4, 5):
                series = run_strategy(months, me, mf, lookback=lookback,
                                      top_n=top_n, lag=lag)
                bench_prices = mf if lag == "lag1d" else me
                spy = benchmark(months, bench_prices, "SPY", series)
                key = f"{lag}/top{top_n}-{lookback}m"
                grid[key] = {
                    "2007+": metrics(series, "2007-01"),
                    "2018+": metrics(series, "2018-01"),
                }
                if lag not in spy_done:
                    spy_done[lag] = {
                        "2007+": metrics(spy, "2007-01"),
                        "2018+": metrics(spy, "2018-01"),
                    }
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "spec": {
            "universe": UNIVERSE, "cash_asset": CASH_ASSET,
            "cost_per_leg": COST_PER_LEG,
            "momentum": "month-end adjusted close, L-month total return",
            "selection": "top-N equal weight, momentum<=0 slot -> AGG",
            "lags": {
                "lag0": "signal & entry at same month-end close (reference only)",
                "lag1d": "enter close of FIRST trading day of next month (report's claim)",
                "lag1m": "enter at month-end close one month after the signal (buffy)",
            },
        },
        "acceptance": "buffy withdraws the TAA objection if a lagged cell shows Sharpe>=0.88 and MaxDD<=-19%... means MaxDD no worse than -19% (2007+ window)",
        "spy_benchmark": spy_done,
        "grid": grid,
    }


def to_markdown(payload: dict) -> str:
    lines = [
        "# TAA lagged reproduction — written spec + results (2026-11-19)",
        "",
        f"Generated {payload['generated_at']} by `tools/taa_lagged_reproduction.py` "
        "(free yfinance data; rerun it to reproduce byte-for-byte logic).",
        "",
        "Spec: " + json.dumps(payload["spec"], indent=0).replace("\n", " "),
        "",
    ]
    for window in ("2007+", "2018+"):
        lines += [f"## Window {window}", "",
                  "| cell | CAGR% | Sharpe | MaxDD% | Calmar | Sharpe h1/h2 |",
                  "|---|---|---|---|---|---|"]
        for lag in ("lag0", "lag1d", "lag1m"):
            spy = (payload["spy_benchmark"].get(lag) or {}).get(window)
            if spy:
                lines.append(
                    f"| **SPY buy-hold ({lag} months)** | {spy['cagr_pct']} | "
                    f"{spy['sharpe']} | {spy['max_dd_pct']} | {spy['calmar']} | "
                    f"{spy['sharpe_h1']}/{spy['sharpe_h2']} |")
            for key, win in payload["grid"].items():
                if not key.startswith(lag + "/"):
                    continue
                m = win.get(window)
                if not m:
                    continue
                lines.append(
                    f"| {key} | {m['cagr_pct']} | {m['sharpe']} | "
                    f"{m['max_dd_pct']} | {m['calmar']} | "
                    f"{m['sharpe_h1']}/{m['sharpe_h2']} |")
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-md", help="write a markdown report here")
    ap.add_argument("--out-json", help="write the raw payload here")
    args = ap.parse_args(argv)
    payload = build()
    md = to_markdown(payload)
    print(md)
    if args.out_md:
        Path(args.out_md).write_text(md + "\n", encoding="utf-8")
    if args.out_json:
        Path(args.out_json).write_text(
            json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
