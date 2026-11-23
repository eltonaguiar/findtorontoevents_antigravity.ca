#!/usr/bin/env python3
"""M1 - measure EQUITY/ETF execution cost, decomposed, and re-run the breakout
across the cost curve so BREAK-EVEN cost is directly visible.

WHY THIS FILE EXISTS
    EQUITY is the only asset class in the programme with PF > 1 on a material
    sample, and its verdict still rested on an ASSUMED cost constant
    (COST_BP_PRIMARY = 25.0 in tools/pod_equity_breakout_backtest.py). Crypto is
    measured (taker fee dominates), FX is measured as an upper bound. Equity was
    the last cheap measurement that could plausibly change a verdict.

WHAT IT MEASURES, AND WHAT IT REFUSES TO MEASURE
  * spread       - from 1-minute IEX bars (Tiingo). Two estimators with disjoint
                   information (Corwin-Schultz on high/low ranges; Roll on return
                   autocovariance) PLUS a rigorous per-bar upper bound: at any
                   instant both bid and ask lie inside the bar's [low, high], so
                   the round-trip quoted spread cannot exceed high-low. The
                   median bar range is therefore an honest UPPER BOUND on the
                   round-trip spread. It is NOT the top-of-book quote.
  * top-of-book  - attempted live. Outside US session hours IEX returns null
                   bid/ask; that is recorded as BLOCKED with the raw payload,
                   never as zero.
  * commission   - verified against repo evidence. No broker statement or
                   fill-level commission exists here -> COMMISSION_UNKNOWN
                   rather than a silent 0.
  * borrow       - the pod family is LONG-ONLY by construction (the backtest
                   skips any non-long signal), so borrow is 0 for THIS family.
                   A hypothetical short leg would need a rate that is not in
                   the repo -> BORROW_UNKNOWN.
  * impact       - ADV is computed from the cached daily bars; the family's order
                   sizes (equal weight, no leverage) are expressed as a fraction
                   of ADV so "spread plus nothing" is justified with numbers or
                   not at all.

Data source / endpoint and sample timestamps are written into the JSON so every
number is reproducible.

Read-only. No orders. Not investment advice.

Usage:
    python3 tools/equity_cost_measure.py            # measure + cost curve
    python3 tools/equity_cost_measure.py --offline  # skip network (uses cache only)
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DATA_DIR = ROOT / "data" / "cache" / "asset_class_review"
OUT = ROOT / "reports" / "equity_cost_measurement"

# the pod's actual breakout universe (tools/pod_equity_breakout_backtest.py)
POD_UNIVERSE = ["SPY", "QQQ", "XLK", "XLF", "XLE", "XLV", "XLY",
                "AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN"]
# the independent D7 universe (tools/breakout_backtest.py) - 15 liquid names
D7_UNIVERSE = ["SPY", "QQQ", "IWM", "DIA", "XLK", "XLF", "XLV", "XLE",
               "GLD", "TLT", "SOXX", "AAPL", "MSFT", "NVDA", "JPM"]
# a large-cap control set (liquid, not in the breakout universe)
LARGECAP_UNIVERSE = ["JNJ", "KO", "PG", "XOM", "JPM", "WMT", "DIS"]

# --- M3 (2026-11-22): class-level universes for the cost-triage measurement ---
# ETF: the index/sector products actually filed under ETF in the audit3 ledger,
#      plus the bond/commodity ETFs that the BOND and COMMODITY rows trade, so
#      their spread is recorded as CONTEXT for those rows (which are refused on
#      other grounds) rather than as a verdict.
ETF_UNIVERSE = ["SPY", "QQQ", "IWM", "DIA", "XLK", "XLF", "XLV", "XLE", "XLY",
                "SOXX", "GLD", "TLT", "AGG", "SHY"]
# INDEX is an ETF alias: the SAME instruments, measured once and reported under
# both labels so the alias can be seen rather than asserted.
INDEX_UNIVERSE = ["SPY", "QQQ", "IWM", "DIA"]
# MEME: the names the audit surfaces actually carry (DOGE dominates the sample).
MEME_UNIVERSE = ["DOGE-USD", "SHIB-USD", "PEPE-USD"]
# PENNY_STOCK: no penny-name series exists in this workspace's cache -> BLOCKED.
# An empty universe must stay empty; borrowing an equity number would be a lie.
PENNY_UNIVERSE = []

# --- 2026-11-23: the three classes that were UNKNOWN by ABSENCE of data ---------
# Each entry lists its symbols AND an explicit provenance for that list, because a
# universe whose origin is not written down cannot be audited later.
# BOND: the 10 bond ETFs the item-34 rule (docs/edge_research/
#   16_COMMODITY_AND_BOND_MOMENTUM_2026-11-22.md sec 0.2) trades.
BOND_UNIVERSE = ["TLT", "IEF", "SHY", "TLH", "AGG", "BND", "LQD", "TIP", "JNK", "HYG"]
BOND_UNIVERSE_SOURCE = ("ITEM 34 RULE, docs/edge_research/"
                        "16_COMMODITY_AND_BOND_MOMENTUM_2026-11-22.md sec 0.2 "
                        "(the 10 bond ETFs in data/cache/asset_class_review)")
# COMMODITY: the REAL instruments the item-33 rule trades - continuous
# front-month futures (=F), the same 7 symbols commodity_momentum.py ranks.
COMMODITY_FUTURES_UNIVERSE = ["CL=F", "GC=F", "HG=F", "NG=F", "SI=F", "ZC=F", "ZS=F"]
COMMODITY_FUTURES_UNIVERSE_SOURCE = (
    "tools/commodity_momentum.py COMMODITY_SYMBOLS (item 33 rule); the continuous "
    "front-month series cached in data/cache/asset_class_review as <SYM>_F_5y.csv")
# COMMODITY_ETF_PROXY: what an investor actually pays to get commodity exposure
# through an ETF wrapper. This is the ETF's spread, NOT the futures contract's -
# kept separate on purpose so it can never silently stand in for the futures.
COMMODITY_ETF_PROXY_UNIVERSE = ["GLD", "SLV", "USO", "DBC", "DBA", "UNG", "CPER"]
COMMODITY_ETF_PROXY_UNIVERSE_SOURCE = (
    "convenience selection of the most liquid commodity ETFs (chosen by this "
    "task, NOT read from a repo file) - see caveats; measures the ETF wrapper only")
# PENNY_STOCK: constructed here, explicitly a convenience sample of real US
# sub-$5 names that still trade. NOT point-in-time and NOT from a repo file -
# survivor selection biases any cost estimate DOWNWARD. Every name must pass the
# tick-truncation diagnostic or be excluded, because a 0.00 spread on a penny
# stock is truncation far more often than it is free trading.
PENNY_UNIVERSE_CONSTRUCTED = ["SIRI", "F", "NIO", "LCID", "PLUG", "RIG", "TELL", "GPRO"]
PENNY_UNIVERSE_SOURCE = (
    "constructed by this task (2026-11-23): a convenience sample of liquid US "
    "names trading under $5; no penny universe file exists in the repo")

COST_POINTS = [0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25]
SAMPLE_DAY = "2026-11-20"          # last completed US session before 2026-11-22
NOW = datetime.now(timezone.utc)


def _get(url: str, key: str, retries: int = 4) -> tuple[str, str]:
    """GET with backoff. Returns (body, status). Never raises."""
    last = "not attempted"
    for k in range(retries):
        try:
            req = urllib.request.Request(
                url, headers={"Content-Type": "application/json",
                              "Authorization": "Token " + key})
            return urllib.request.urlopen(req, timeout=30).read().decode(), "ok"
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code == 429:            # rate limited - long back off, then retry
                time.sleep(30 * (k + 1))
                continue
            return "", last
        except Exception as e:           # noqa: BLE001 - network, recorded not raised
            last = f"{type(e).__name__}: {e}"
            time.sleep(2)
    return "", last


# ------------------------------------------------------------------ spread
def corwin_schultz(highs, lows) -> dict:
    """Corwin & Schultz (2012) on consecutive bar pairs. Floors negatives at 0."""
    beta_terms, gamma_terms = [], []
    for i in range(len(highs) - 1):
        h1, l1, h2, l2 = highs[i], lows[i], highs[i + 1], lows[i + 1]
        if min(h1, l1, h2, l2) <= 0:
            continue
        beta_terms.append(math.log(h1 / l1) ** 2 + math.log(h2 / l2) ** 2)
        H, L = max(h1, h2), min(l1, l2)
        gamma_terms.append(math.log(H / L) ** 2)
    if not beta_terms:
        return {"n_pairs": 0, "median_bp": None, "frac_floored": None}
    beta = statistics.mean(beta_terms)
    gamma = statistics.mean(gamma_terms)
    k = 3 - 2 * math.sqrt(2)
    alpha = (math.sqrt(2 * beta) - math.sqrt(beta)) / k - math.sqrt(gamma / k)
    s = 2 * (math.exp(alpha) - 1) / (1 + math.exp(alpha))
    # per-pair values so we can report a distribution, not just the mean
    vals = []
    for b, g in zip(beta_terms, gamma_terms):
        a = (math.sqrt(2 * b) - math.sqrt(b)) / k - math.sqrt(g / k)
        v = 2 * (math.exp(a) - 1) / (1 + math.exp(a))
        vals.append(v * 1e4)
    vals.sort()
    return {"n_pairs": len(vals), "pooled_bp": max(0.0, s * 1e4),
            "median_bp": statistics.median(vals),
            "p25_bp": vals[len(vals) // 4], "p75_bp": vals[3 * len(vals) // 4],
            "frac_floored": sum(1 for v in vals if v <= 0) / len(vals)}


def roll_estimator(closes) -> dict:
    """Roll (1984): 2*sqrt(-cov(r_t, r_t-1)). Upward biased by volatility."""
    r = [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes))
         if closes[i - 1] > 0 and closes[i] > 0]
    if len(r) < 30:
        return {"n": len(r), "bp": None, "acf1": None}
    m = statistics.mean(r)
    x = [v - m for v in r]
    cov = sum(x[i] * x[i - 1] for i in range(1, len(x))) / (len(x) - 1)
    acf1 = cov / (sum(v * v for v in x) / (len(x) - 1))
    return {"n": len(r), "bp": 2 * math.sqrt(-cov) * 1e4 if cov < 0 else 0.0,
            "acf1": acf1, "structurally_valid": cov < 0}


def measure_spread(sym: str) -> dict:
    """1-min bars -> spread estimators + a rigorous upper bound + participation.

    Primary source is yfinance (Yahoo) 1-min bars, 5 trading days: it needs no
    API quota and carries VOLUME, which the spread alone does not. Tiingo IEX is
    the documented fallback (same bar schema) when its hourly allocation allows.
    """
    import warnings
    warnings.filterwarnings("ignore")
    rec = {"symbol": sym,
           "source": "yfinance period=5d interval=1m (Yahoo)",
           "fetched_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    try:
        import yfinance as yf
        d = yf.download(sym, period="5d", interval="1m", progress=False,
                        auto_adjust=False, threads=False)
    except Exception as e:                        # noqa: BLE001
        rec["fetch_status"] = f"ERROR {type(e).__name__}: {e}"
        return rec
    if d is None or len(d) == 0:
        rec["fetch_status"] = "empty"
        return rec
    if hasattr(d.columns, "get_level_values"):     # MultiIndex -> flat
        d.columns = d.columns.get_level_values(0)
    d = d.rename(columns=str.lower)
    d = d.dropna(subset=["high", "low", "close"])
    if len(d) < 60:
        rec["fetch_status"] = f"too few bars ({len(d)})"
        return rec
    highs = [float(x) for x in d["high"]]
    lows = [float(x) for x in d["low"]]
    closes = [float(x) for x in d["close"]]
    vols = [float(x) for x in d["volume"]] if "volume" in d else [0.0] * len(d)
    ranges = sorted((h - l) / c * 1e4 for h, l, c in zip(highs, lows, closes) if c > 0)
    n = len(ranges)
    per_day = {}
    for ts, v in zip(d.index, vols):
        per_day[str(ts)[:10]] = per_day.get(str(ts)[:10], 0.0) + v
    # tick-quantisation diagnostic: a cheap stock prints few distinct prices and
    # many zero-range bars, so its 0.00 median is TRUNCATION, not a zero spread.
    n_zero = sum(1 for r in ranges if r == 0)
    frac_zero = n_zero / n if n else None
    rec.update({
        "fetch_status": "ok", "n_bars": len(d),
        "first_bar": str(d.index[0]), "last_bar": str(d.index[-1]),
        "range_upper_bound_rt_bp": {
            "note": ("at any instant bid and ask both lie inside the bar's "
                     "[low, high], so RT quoted spread <= high-low. This is an "
                     "UPPER BOUND, not the NBBO."),
            "median": ranges[n // 2], "p25": ranges[n // 4],
            "p75": ranges[3 * n // 4], "p90": ranges[int(0.9 * (n - 1))],
        },
        "tick_truncation": {
            "n_distinct_high": len(set(highs)), "n_distinct_low": len(set(lows)),
            "n_zero_range_bars": n_zero, "frac_zero_range": frac_zero,
            "suspect": bool(frac_zero is not None and frac_zero > 0.5),
            "note": ("frac_zero_range > 0.5 means the quote grid is coarser than "
                      "the price moves, so this name's 0.00 bp is TRUNCATION and "
                      "must NOT be quoted as a zero spread"),
        },
        "corwin_schultz": corwin_schultz(highs, lows),
        "roll": roll_estimator(closes),
        "volume": {"shares_per_day": per_day,
                   "median_daily_shares": statistics.median(per_day.values()) if per_day else None,
                   "median_minute_volume": statistics.median(vols) if vols else None},
    })
    return rec


def top_of_book(symbols, key: str) -> dict:
    body, status = _get("https://api.tiingo.com/iex/?tickers=" + ",".join(symbols), key)
    out = {"endpoint": "https://api.tiingo.com/iex/?tickers=<universe>",
           "sampled_utc": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"),
           "fetch_status": status, "quotes": []}
    if status == "ok" and body:
        try:
            for q in json.loads(body):
                out["quotes"].append({
                    "ticker": q.get("ticker"), "bid": q.get("bidPrice"),
                    "ask": q.get("askPrice"), "bidSize": q.get("bidSize"),
                    "askSize": q.get("askSize"),
                    "quoteTimestamp": q.get("quoteTimestamp"),
                    "timestamp": q.get("timestamp")})
        except json.JSONDecodeError:
            out["fetch_status"] = "unparseable"
    live = [q for q in out["quotes"] if q["bid"] and q["ask"]]
    if not live:
        out["status"] = "BLOCKED_NO_LIVE_NBBO"
        out["reason"] = ("IEX returned null bid/ask - outside US regular session "
                         "(2026-11-22 is a Sunday) or stale. Not a zero.")
    else:
        out["status"] = "MEASURED"
        for q in live:
            mid = (q["bid"] + q["ask"]) / 2
            q["rt_spread_bp"] = (q["ask"] - q["bid"]) / mid * 1e4
    return out


# ------------------------------------------------------------------ impact
def load_daily(sym: str):
    """Cached daily bars -> (date, o, h, l, c, volume) rows."""
    p = DATA_DIR / f"{sym}_5y.csv"
    if not p.exists():
        return None
    rows = []
    with open(p) as fh:
        hdr = fh.readline().strip().split(",")
        ix = {h: i for i, h in enumerate(hdr)}
        for line in fh:
            parts = line.strip().split(",")
            if len(parts) < 5:
                continue
            try:
                rows.append({
                    "date": parts[ix["Date"]], "o": float(parts[ix["Open"]]),
                    "h": float(parts[ix["High"]]), "l": float(parts[ix["Low"]]),
                    "c": float(parts[ix["Close"]]),
                    "v": float(parts[ix["Volume"]]) if "Volume" in ix else 0.0})
            except (KeyError, ValueError):
                continue
    return rows or None


def adv_table(symbols) -> dict:
    out = {}
    for s in symbols:
        rows = load_daily(s)
        if not rows:
            out[s] = {"status": "no cached data"}
            continue
        dv = sorted(r["c"] * r["v"] for r in rows)
        med = statistics.median(dv)
        out[s] = {"median_daily_dollar_volume_usd": med,
                  "window": f"{rows[0]['date']}..{rows[-1]['date']}",
                  "n_bars": len(rows)}
    return out


# ------------------------------------------------------------------ cost curve
def summarize_curve(trades, cost_bp: float) -> dict:
    """PF + Sharpe + maxDD + net, in one place so PF is never quoted alone."""
    if not trades:
        return {"cost_bp_per_side": cost_bp, "n": 0}
    net = [t["gross"] - 2 * cost_bp / 1e4 for t in trades]
    wins = sum(x for x in net if x > 0)
    losses = -sum(x for x in net if x <= 0)
    pf = wins / losses if losses > 0 else float("inf")
    mu = statistics.mean(net)
    sd = statistics.pstdev(net) if len(net) > 1 else 0.0
    avg_bars = statistics.mean([t.get("bars", t.get("bars_held", 1)) for t in trades])
    t_stat = mu / (sd / math.sqrt(len(net))) if sd else float("nan")
    sharpe = mu / sd * math.sqrt(252.0 / avg_bars) if sd and avg_bars > 0 else float("nan")
    eq, peak, mdd = 1.0, 1.0, 0.0
    for r in net:
        eq *= (1.0 + r)
        peak = max(peak, eq)
        mdd = min(mdd, eq / peak - 1.0)
    return {"cost_bp_per_side": cost_bp, "cost_bp_round_trip": 2 * cost_bp,
            "n": len(net), "net_pct_per_trade": mu * 100,
            "total_net_pct": sum(net) * 100,
            "median_net_pct": statistics.median(net) * 100,
            "wr_pct": 100 * sum(1 for x in net if x > 0) / len(net),
            "pf": pf, "t": t_stat, "sharpe_ann": sharpe,
            "max_drawdown": mdd, "avg_bars_held": avg_bars,
            "ann_vol": sd * math.sqrt(252.0 / avg_bars) if avg_bars > 0 else None}


def breakout_curve(n: int) -> dict:
    """Re-run the pre-registered D7 Donchian rule on the cached 5y universe."""
    from tools.breakout_backtest import backtest_symbol, load
    trades = []
    for sym in D7_UNIVERSE:
        rows = load(sym)
        if not rows:
            continue
        for t in backtest_symbol(rows, n, cost_side=0.0):
            t["symbol"] = sym
            trades.append(t)
    trades.sort(key=lambda x: x["entry_date"])
    rows = [summarize_curve(trades, c) for c in COST_POINTS]
    # exposure: bars in a position / bars available, per symbol, averaged
    total_bars = 0
    held = 0
    for sym in D7_UNIVERSE:
        d = load(sym)
        if not d:
            continue
        total_bars += len(d)
    held = sum(t.get("bars", t.get("bars_held", 1)) for t in trades)
    return {"N": n, "universe": D7_UNIVERSE, "n_trades": len(trades),
            "bars_in_market": held, "bars_available": total_bars,
            "exposure_pct": 100 * held / total_bars if total_bars else None,
            "rows": rows}


def pod_curve() -> dict:
    """Re-run the ACTUAL pod strategy (VT pattern sweep) on cached 5y bars."""
    from tools.pod_equity_breakout_backtest import backtest_symbol
    from baby_strategies.vt_pattern_sweep import VTPatternSweepStrategy
    strat = VTPatternSweepStrategy()
    trades = []
    for sym in POD_UNIVERSE:
        rows = load_daily(sym)
        if not rows or len(rows) < 400:
            continue
        df = _rows_to_df(rows)
        for t in backtest_symbol(sym, strat, df, tie_break="stop"):
            t["bars"] = t["bars"]
            trades.append(t)
    trades.sort(key=lambda x: x["entry_date"])
    rows = [summarize_curve(trades, c) for c in COST_POINTS]
    return {"strategy": "POD-EQUITY-BREAKOUT / VTPatternSweepStrategy (real code)",
            "universe": POD_UNIVERSE, "n_trades": len(trades),
            "window_note": "cached 5y daily bars only (2021-11..2026-11), which is "
                           "NOT the all-history window of the published 25bp run",
            "rows": rows}


def _rows_to_df(rows):
    import pandas as pd
    df = pd.DataFrame(rows).set_index("date")
    df.index = pd.to_datetime(df.index)
    return df[["o", "h", "l", "c"]].rename(
        columns={"o": "open", "h": "high", "l": "low", "c": "close"})


def break_even(rows, key="net_pct_per_trade") -> float | None:
    prev = None
    for r in rows:
        if not r.get("n"):
            continue
        v = r[key]
        if prev and prev[1] > 0 >= v:
            return prev[0] + (r["cost_bp_per_side"] - prev[0]) * prev[1] / (prev[1] - v)
        prev = (r["cost_bp_per_side"], v)
    return None


def _pod_trades():
    """The REAL pod strategy's trades on cached 5y bars, plus the per-symbol series."""
    from tools.pod_equity_breakout_backtest import backtest_symbol
    from baby_strategies.vt_pattern_sweep import VTPatternSweepStrategy
    strat = VTPatternSweepStrategy()
    trades, series = [], {}
    for sym in POD_UNIVERSE:
        rows = load_daily(sym)
        if not rows or len(rows) < 400:
            continue
        series[sym] = rows
        for t in backtest_symbol(sym, strat, _rows_to_df(rows), tie_break="stop"):
            t["symbol"] = sym
            trades.append(t)
    trades.sort(key=lambda x: x["entry_date"])
    return trades, series


def _sharpe(nets, bars):
    if len(nets) < 3:
        return float("nan")
    mu = statistics.mean(nets)
    sd = statistics.pstdev(nets)
    avg = statistics.mean(bars)
    return mu / sd * math.sqrt(252.0 / avg) if sd and avg > 0 else float("nan")


def proof_bar(cost_bp: float, n_shuffles: int = 500, n_boot: int = 10000) -> dict:
    """Step 4: null, bootstrap CI on excess CAGR vs SPY, hurdle, at a given cost."""
    import random
    trades, series = _pod_trades()
    if not trades:
        return {"status": "no trades"}
    net = [t["gross"] - 2 * cost_bp / 1e4 for t in trades]
    bars = [t["bars"] for t in trades]
    obs_sharpe = _sharpe(net, bars)

    # --- random-entry null: same symbol mix, same holding-period distribution,
    # same exit geometry (hold `bars` from a random entry), timing destroyed.
    rng = random.Random(42)
    null = []
    for _ in range(n_shuffles):
        nn, bb = [], []
        for t in trades:
            rows = series[t["symbol"]]
            h = t["bars"]
            if h >= len(rows) - 3:
                continue
            i = rng.randrange(1, len(rows) - h - 1)
            e, x = rows[i]["o"], rows[i + h]["c"]
            if e <= 0:
                continue
            nn.append((x - e) / e - 2 * cost_bp / 1e4)
            bb.append(h)
        if len(nn) > 5:
            null.append(_sharpe(nn, bb))
    null = [v for v in null if v == v]
    null.sort()
    pct = 100.0 * sum(1 for v in null if v < obs_sharpe) / len(null) if null else None

    # --- bootstrap CI on excess CAGR vs SPY, >=10k resamples
    span0 = trades[0]["entry_date"]
    span1 = trades[-1]["exit_date"]
    years = max(1e-9, (datetime.fromisoformat(span1) - datetime.fromisoformat(span0)).days / 365.25)

    def cagr(sample):
        eq = 1.0
        for r in sample:
            eq *= (1.0 + r)
        return eq ** (1.0 / years) - 1.0

    spy_rows = [r for r in (load_daily("SPY") or []) if span0 <= r["date"] <= span1]
    spy_cagr = ((spy_rows[-1]["c"] / spy_rows[0]["c"]) ** (1.0 / years) - 1.0
                if len(spy_rows) > 2 else None)
    obs_cagr = cagr(net)
    b = random.Random(7)
    boot = []
    L = len(net)
    for _ in range(n_boot):
        s = [net[b.randrange(L)] for _ in range(L)]
        boot.append(cagr(s) - (spy_cagr or 0.0))
    boot.sort()
    ci = [float(boot[int(0.025 * n_boot)]), float(boot[int(0.975 * n_boot) - 1])]

    # --- the honest hurdle: rf + hurdleSharpe * vol
    rf, hurdle = 0.0432, 1.114
    ann_vol = statistics.pstdev(net) * math.sqrt(252.0 / statistics.mean(bars))
    required = rf + hurdle * ann_vol

    return {
        "cost_bp_per_side": cost_bp, "n_trades": len(net),
        "window": f"{span0}..{span1}", "years": round(years, 2),
        "observed_sharpe_ann": obs_sharpe,
        "null": {"shuffles": len(null), "mean_sharpe": statistics.mean(null) if null else None,
                 "p95_sharpe": null[int(0.95 * len(null)) - 1] if null else None,
                 "observed_percentile": pct, "gate_95": (pct is not None and pct >= 95)},
        "cagr": obs_cagr, "spy_cagr_same_window": spy_cagr,
        "excess_cagr_point": (obs_cagr - spy_cagr) if spy_cagr is not None else None,
        "excess_cagr_boot_ci95": ci, "boot_resamples": n_boot,
        "hurdle": {"rf": rf, "hurdle_sharpe": hurdle, "ann_vol": ann_vol,
                    "required_return": required,
                    "beats_hurdle": obs_cagr > required},
        "verdict": ("NOT_INVESTABLE" if not (
            pct is not None and pct >= 95 and ci[0] > 0 and obs_cagr > required)
            else "CANDIDATE_FOR_FORWARD_GATE"),
    }


def survivorship_check() -> dict:
    from tools.pit_universe import build_pit_universe
    syms = sorted({p.stem.replace("_5y", "") for p in DATA_DIR.glob("*_5y.csv")})
    first = min(_first_date(s) for s in syms if _first_date(s))
    last = max(_last_date(s) for s in syms if _last_date(s))
    a = set(build_pit_universe(first, str(DATA_DIR), syms))
    b = set(build_pit_universe(last, str(DATA_DIR), syms))
    return {"tool": "tools/pit_universe.py",
            "n_symbols_on_disk": len(syms),
            "universe_at_start": len(a), "universe_at_end": len(b),
            "symbols_lost": sorted(b - a)[:20],
            "note": ("first/last close censoring only; it cannot remove "
                     "delisting-with-poor-returns bias, so a zero gap is a "
                     "LOWER BOUND on survivorship, not evidence of none")}


def _first_date(sym):
    r = load_daily(sym)
    return r[0]["date"] if r else None


def _last_date(sym):
    r = load_daily(sym)
    return r[-1]["date"] if r else None


# ------------------------------------------------- M3 class measurement
def measure_class(name: str, universe) -> dict:
    """Per-name spread distribution for one asset class.

    An AVERAGE across a universe that mixes liquid and illiquid names hides the
    only number that matters, so this returns the FULL per-name distribution
    (min / p25 / median / p75 / max / p90) plus every name's own record, and it
    never collapses the class to a single figure without the spread of it.
    A name that cannot be fetched is listed as blocked, not dropped and not set
    to zero.
    """
    rec = {"asset_class": name, "universe": list(universe),
           "source": "yfinance period=5d interval=1m (Yahoo); Tiingo IEX is the "
                     "documented fallback and returned HTTP 429 this run",
           "fetched_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "per_name": {}, "blocked": [], "aggregate": None}
    if not universe:
        rec["blocked"].append({"reason": "NO_INSTRUMENT_IN_REPO",
                                "detail": "an empty universe stays empty; no number "
                                          "is borrowed from another class"})
        return rec
    ubs, css = [], []
    for sym in universe:
        r = measure_spread(sym)
        rec["per_name"][sym] = r
        if r.get("range_upper_bound_rt_bp"):
            ubs.append((sym, r["range_upper_bound_rt_bp"]["median"]))
            cs = r.get("corwin_schultz", {}).get("median_bp")
            if cs is not None:
                css.append(cs)
        else:
            rec["blocked"].append({"symbol": sym,
                                    "reason": r.get("fetch_status", "unknown")})
    if ubs:
        vals = sorted(v for _, v in ubs)
        n = len(vals)
        rec["aggregate"] = {
            "n_names_with_data": n,
            "range_ub_rt_bp": {"min": vals[0], "p25": vals[n // 4],
                                "median": statistics.median(vals),
                                "p75": vals[3 * n // 4],
                                "p90": vals[int(0.9 * (n - 1))], "max": vals[-1]},
            "per_name_rt_bp": dict(ubs),
            "corwin_schultz_rt_bp_median": statistics.median(css) if css else None,
            "ratio_max_to_min": (vals[-1] / vals[0]) if vals[0] > 0 else None,
            "basis": ("median 1-min bar range = rigorous UPPER bound on round-trip "
                       "quoted spread (bid and ask both lie inside [low, high]); "
                       "NOT the NBBO"),
        }
    return rec


def classes_main() -> int:
    """M3: measure ETF (and its INDEX alias) and MEME per-name distributions.

    Writes a SEPARATE artifact so the M1 artifact is not silently rewritten.
    BOND/COMMODITY ETFs are measured as CONTEXT only - their strategy rows are
    refused on break-even grounds, so no verdict is inferred from these numbers.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    out = {"generated_utc": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"),
           "task": "M3 - cost triage: class cost distributions for COST_ADDRESSABLE rows",
           "sources": {"intraday_bars": "yfinance 1-min, period=5d (Yahoo)",
                        "top_of_book": "Tiingo IEX https://api.tiingo.com/iex/?tickers=<u>",
                        "session_note": "2026-11-22 is a Sunday; US session closed.",
                        "tiingo_state_this_run": "HTTP 429 (hourly allocation exhausted)"},
           "classes": {}}
    for name, uni in (("ETF", ETF_UNIVERSE), ("INDEX_alias_of_ETF", INDEX_UNIVERSE),
                      ("MEME", MEME_UNIVERSE), ("PENNY_STOCK", PENNY_UNIVERSE)):
        print(f"measuring {name} ({len(uni)} names)...", flush=True)
        c = measure_class(name, uni)
        out["classes"][name] = c
        agg = c.get("aggregate")
        if agg:
            print(f"  {name}: n={agg['n_names_with_data']} median_rt="
                  f"{agg['range_ub_rt_bp']['median']:.2f}bp "
                  f"max/min={agg['ratio_max_to_min']}", flush=True)
        else:
            print(f"  {name}: no data - {c['blocked']}", flush=True)
    # top-of-book attempted once, honestly blocked rather than zeroed
    key = os.environ.get("TIINGO_API_KEY", "")
    out["top_of_book"] = (top_of_book(sorted(set(ETF_UNIVERSE) | set(MEME_UNIVERSE)), key)
                          if key else {"status": "SKIPPED_NO_KEY"})
    out["commission"] = {"status": "COMMISSION_UNKNOWN",
                          "why": "no broker statement or fill data in repo; the 10bp "
                                 "constant in transaction_costs.json is an unsourced "
                                 "assumption and is not propagated as measured"}
    path = OUT / "class_cost_20261122.json"
    path.write_text(json.dumps(out, indent=1, default=str))
    print(f"\nwrote {path}")
    return 0


# ------------------------------------------------- 2026-11-23 new classes
OUT_NEW = ROOT / "reports" / "cost_measurement_new_classes"


def _sample_freshness(rec: dict) -> str:
    """Is this name's 1-min sample from today (live) or an earlier session?"""
    lb = (rec or {}).get("last_bar")
    if not lb:
        return "NO_BARS"
    return ("SAME_UTC_DAY" if str(lb)[:10] == NOW.strftime("%Y-%m-%d")
            else "LAST_SESSION")


def _aggregate_excl_truncated(c: dict) -> dict:
    """Median over names whose tick-truncation diagnostic is NOT suspect.

    measure_class() reports the full distribution (and, deliberately, includes
    every fetched name in its median - the MEME median includes SHIB's 0.0). We
    do not change that. Here we ADD a truncation-aware view: a name with
    frac_zero_range > 0.5 has a 0.00 bp that is TRUNCATION, not a zero spread, so
    it is excluded from the median and listed with its reason instead.
    """
    rows = []
    for sym, r in (c.get("per_name") or {}).items():
        ub = (r or {}).get("range_upper_bound_rt_bp") or {}
        tt = (r or {}).get("tick_truncation") or {}
        if ub.get("median") is None:
            continue
        rows.append((sym, ub["median"], bool(tt.get("suspect")),
                     tt.get("frac_zero_range"), _sample_freshness(r)))
    clean = sorted(v for _, v, sus, _, _ in rows if not sus)
    excl = [{"symbol": s, "range_ub_rt_bp": round(v, 6),
             "frac_zero_range": f,
             "reason": "TRUNCATION (frac_zero_range > 0.5): 0.00bp is not a zero spread"}
            for s, v, sus, f, _ in rows if sus]
    if not clean:
        return {"n_names_clean": 0, "median_rt_bp": None, "excluded_truncated": excl}
    n = len(clean)
    return {
        "n_names_clean": n,
        "median_rt_bp": statistics.median(clean),
        "min": clean[0], "p25": clean[n // 4], "p75": clean[3 * n // 4],
        "max": clean[-1],
        "per_name_rt_bp_clean": {s: v for s, v, sus, _, _ in rows if not sus},
        "excluded_truncated": excl,
        "freshness_by_name": {s: f for s, _, _, _, f in rows},
    }


def _measure_new_class(name, universe, universe_source, caveats,
                       proxy_of=None, always_status=None) -> dict:
    """measure_class() + provenance + truncation-aware aggregate + status."""
    c = measure_class(name, universe)
    c["universe_source"] = universe_source
    if proxy_of:
        c["proxy_of"] = proxy_of
    c["measured_at_utc"] = NOW.strftime("%Y-%m-%dT%H:%M:%SZ")
    c["caveats"] = list(caveats)
    agg = _aggregate_excl_truncated(c)
    c["aggregate_excl_truncated"] = agg
    fresh = list((agg.get("freshness_by_name") or {}).values())
    c["freshness"] = ("LIVE_SESSION" if fresh and
                      sum(1 for f in fresh if f == "SAME_UTC_DAY") * 2 >= len(fresh)
                      else "LAST_SESSION" if fresh else "NO_SAMPLE")
    if always_status:
        status = always_status
    elif not agg.get("n_names_clean"):
        status = "INSUFFICIENT_DATA"
    elif c["freshness"] == "LIVE_SESSION":
        status = "MEASURED_UPPER_BOUND"
    else:
        status = "MEASURED_FROM_LAST_SESSION"
    c["status"] = status
    c["measurement_kind"] = "UPPER_BOUND_ON_RT_QUOTED_SPREAD" if agg.get("median_rt_bp") else None
    return c


def classes_new_main() -> int:
    """2026-11-23: BOND, COMMODITY (futures + ETF proxy) and PENNY_STOCK.

    Writes a SEPARATE artifact; the M3 artifact for the existing classes is not
    touched. Commodity FUTURES are measured as their own class because =F
    instruments trade ~24/5 (so a Sunday-night sample is live), while the ETF
    proxy is kept apart so it can never silently stand in for the futures.
    """
    OUT_NEW.mkdir(parents=True, exist_ok=True)
    sunday = ("US bond ETFs, equities and penny stocks do not trade on Sunday "
              "night: a sample taken now is the LAST session's, and a zero-range "
              "bar there is truncation, not a zero spread. =F futures trade "
              "~24/5 and may be live.")
    classes = {}
    classes["BOND"] = _measure_new_class(
        "BOND", BOND_UNIVERSE, BOND_UNIVERSE_SOURCE,
        caveats=[
            "A bond-ETF spread is the cost of ETF exposure - NOT the cost of trading "
            "Treasuries directly nor of a bond mutual fund.",
            "Sampled Sunday night: these are Friday's bars (MEASURED_FROM_LAST_SESSION), "
            "not a live NBBO.",
            "The figure is an UPPER bound from 1-min bar ranges; the true NBBO is tighter.",
            "Does NOT change the item-34 verdict: bond momentum has a 0bp/side "
            "break-even, so any cost > 0bp makes net worse, not better.",
        ])
    classes["COMMODITY_FUTURES"] = _measure_new_class(
        "COMMODITY_FUTURES", COMMODITY_FUTURES_UNIVERSE,
        COMMODITY_FUTURES_UNIVERSE_SOURCE,
        caveats=[
            "Continuous front-month (=F) series: a roll-adjusted continuous curve is "
            "NOT available in the repo, so this is the front-month contract's spread, "
            "not the roll cost.",
            "=F trades ~24/5, so a Sunday-night sample may be live - see freshness.",
            "Does NOT change the item-33 verdict: commodity momentum has a 0bp/side "
            "break-even, so any cost > 0bp cannot rescue it.",
        ])
    classes["COMMODITY_ETF_PROXY"] = _measure_new_class(
        "COMMODITY_ETF_PROXY", COMMODITY_ETF_PROXY_UNIVERSE,
        COMMODITY_ETF_PROXY_UNIVERSE_SOURCE, proxy_of="COMMODITY_FUTURES",
        always_status="ETF_PROXY_ONLY",
        caveats=[
            "Measures the ETF WRAPPER's spread only. It is NOT the futures contract's "
            "spread and does NOT include roll cost.",
            "It answers 'what would commodity exposure via an ETF cost', not 'what "
            "does the futures momentum strategy pay'.",
            "Do not let this number unblock the commodity momentum verdict.",
            "Universe is a convenience selection by this task, not a repo file.",
        ])
    classes["PENNY_STOCK"] = _measure_new_class(
        "PENNY_STOCK", PENNY_UNIVERSE_CONSTRUCTED, PENNY_UNIVERSE_SOURCE,
        caveats=[
            "Convenience sample, NOT point-in-time; survivor selection biases the "
            "cost estimate DOWNWARD.",
            "No penny universe file exists in the repo; the list was constructed here.",
            "Sampled Sunday night: last-session bars, not a live NBBO.",
            "Names flagged suspect by the truncation diagnostic are excluded from the "
            "median - a 0.00bp penny spread is truncation far more often than free trading.",
        ])
    out = {
        "generated_utc": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "measured_at_utc": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "task": "2026-11-23 - cost measurement for classes UNKNOWN by absence of data",
        "session_note": sunday,
        "sources": {"intraday_bars": "yfinance 1-min, period=5d (Yahoo)",
                     "top_of_book": "Tiingo IEX (needs key; not attempted here)",
                     "daily_cache": "data/cache/asset_class_review/*_5y.csv"},
        "basis_note": ("Every bp figure is the median 1-min bar range = a rigorous "
                        "UPPER bound on the round-trip quoted spread (bid and ask both "
                        "lie inside [low, high]); it is NOT the NBBO."),
        "classes": classes,
    }
    for name, c in classes.items():
        a = c["aggregate_excl_truncated"]
        print(f"{name:<20} status={c['status']:<28} freshness={c['freshness']:<13} "
              f"n={a['n_names_clean']} median_rt={a['median_rt_bp']}", flush=True)
        for x in a["excluded_truncated"]:
            print(f"    excluded {x['symbol']} (frac_zero={x['frac_zero_range']})", flush=True)
    path = OUT_NEW / "class_cost_new_20261123.json"
    path.write_text(json.dumps(out, indent=1, default=str))
    print(f"\nwrote {path}")
    return 0


# ------------------------------------------------------------------ main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="skip network calls")
    ap.add_argument("--classes-measure", action="store_true",
                    help="M3: measure ETF/INDEX-alias/MEME per-name spread "
                         "distributions into class_cost_20261122.json")
    ap.add_argument("--classes-measure-new", action="store_true",
                    help="2026-11-23: measure BOND/COMMODITY(futures+ETF proxy)/"
                         "PENNY_STOCK into class_cost_new_20261123.json")
    a = ap.parse_args()
    if a.classes_measure:
        return classes_main()
    if a.classes_measure_new:
        return classes_new_main()
    key = os.environ.get("TIINGO_API_KEY", "")
    OUT.mkdir(parents=True, exist_ok=True)

    out = {
        "generated_utc": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "task": "M1 - EQUITY/ETF cost measurement",
        "sources": {
            "intraday_bars": "yfinance 1-min bars, period=5d (Yahoo) - PRIMARY, "
                             "needs no API key; Tiingo IEX 1-min is the documented "
                             "fallback (https://api.tiingo.com/iex/<SYM>/prices"
                             "?startDate=<day>&endDate=<day>&resampleFreq=1min)",
            "top_of_book": "Tiingo IEX: https://api.tiingo.com/iex/?tickers=<universe>",
            "daily_bars": "data/cache/asset_class_review/*_5y.csv "
                          "(2021-11-22..2026-11-19)",
            "sample_day": SAMPLE_DAY,
            "session_note": "2026-11-22 is a Sunday; the US regular session is closed.",
        },
        "spread": {}, "top_of_book": None, "commission": None,
        "borrow": None, "impact": None, "cost_curve": {},
        "survivorship": None,
    }

    # FIX (provenance repair): the spread loop uses yfinance (Yahoo) and needs NO
    # API key, so it must not be gated on TIINGO_API_KEY. Gating it there silently
    # overwrote a good run with SKIPPED_OFFLINE_OR_NO_KEY, which made a real 12.07 bp
    # unquotable from its own artifact. Only --offline may skip the spread.
    if not a.offline:
        print("measuring 1-min bar spread upper bounds (yfinance)...", flush=True)
        for sym in sorted(set(POD_UNIVERSE) | set(LARGECAP_UNIVERSE)):
            rec = measure_spread(sym)
            out["spread"][sym] = rec
            u = rec.get("range_upper_bound_rt_bp", {}).get("median")
            print(f"  {sym:<6} {rec.get('fetch_status', '?'):<12} "
                  f"range_ub_rt={u if u is None else round(u, 2)}bp", flush=True)
        # top-of-book still needs Tiingo; blocked (never zeroed) when no key exists
        out["top_of_book"] = (top_of_book(sorted(set(POD_UNIVERSE) | set(LARGECAP_UNIVERSE)), key)
                              if key else {"status": "SKIPPED_NO_KEY"})
    else:
        out["spread"] = {"status": "SKIPPED_OFFLINE"}
        out["top_of_book"] = {"status": "SKIPPED_OFFLINE"}

    # aggregate the spread bound across the breakout universe only
    ub = [r["range_upper_bound_rt_bp"]["median"] for s, r in out["spread"].items()
          if isinstance(r, dict) and r.get("range_upper_bound_rt_bp") and s in POD_UNIVERSE]
    cs = [r["corwin_schultz"]["median_bp"] for s, r in out["spread"].items()
          if isinstance(r, dict) and r.get("corwin_schultz") and r["corwin_schultz"].get("median_bp") is not None
          and s in POD_UNIVERSE]
    out["spread_aggregate"] = {
        "universe": "POD_UNIVERSE",
        "universe_symbols": list(POD_UNIVERSE),
        "n_symbols_with_data": len(ub),
        "per_name_rt_bp": {s: r["range_upper_bound_rt_bp"]["median"]
                           for s, r in out["spread"].items()
                           if isinstance(r, dict) and r.get("range_upper_bound_rt_bp")
                           and s in POD_UNIVERSE},
        "range_upper_bound_rt_bp_median": statistics.median(ub) if ub else None,
        "corwin_schultz_rt_bp_median": statistics.median(cs) if cs else None,
        "measured_cost_per_side_used_bp": (statistics.median(ub) / 2) if ub else None,
        "bar_interval": "1m", "window": "2026-11-16..2026-11-20 (last 5 sessions, period=5d)",
        "basis": ("half the median 1-min bar range = a rigorous UPPER bound on "
                  "per-side spread; the true NBBO is tighter but was not "
                  "measurable with markets closed"),
        "provenance_self_check": ("PASS" if (ub and statistics.median(ub) is not None)
                                  else "FAIL_NO_SPREAD_DATA - a quoted bp figure "
                                       "must NOT be sourced from this artifact"),
    }

    out["commission"] = {
        "status": "COMMISSION_UNKNOWN",
        "evidence_searched": [
            "tools/data/transaction_costs.json (EQUITY note: 'commission-free "
            "broker + typical bid-ask spread' - an unsourced ASSUMPTION, 10bp RT)",
            "no broker statement, no fill-level commission field in the repo",
        ],
        "why_not_zero": ("a zero-commission claim needs a broker confirmation or "
                          "fill data; neither exists here, and PFOF fill quality "
                          "is exactly where a 'zero' commission hides"),
    }
    out["borrow"] = {
        "status": "ZERO_FOR_THIS_FAMILY",
        "reason": ("the pod family is LONG-ONLY by construction: "
                    "backtest_symbol() skips any signal whose direction is not "
                    "LONG/BUY, so no short leg and no borrow"),
        "hypothetical_short_leg": "BORROW_UNKNOWN - no borrow rate is in the repo",
    }
    adv = adv_table(sorted(set(POD_UNIVERSE) | set(LARGECAP_UNIVERSE)))
    out["impact"] = {
        "adv": adv,
        "order_sizing": ("one unit per signal, equal weight, no leverage; a "
                          "$100k book over 13 names is ~$7.7k/name"),
        "order_to_adv": {s: (7700.0 / v["median_daily_dollar_volume_usd"]
                            if v.get("median_daily_dollar_volume_usd") else None)
                         for s, v in adv.items()},
        "note": ("if order/ADV is ~1e-5 or smaller, market impact is negligible "
                  "and 'spread plus nothing' is justified with numbers"),
    }

    print("re-running the breakout cost curve (D7 rule, cached 5y)...", flush=True)
    for n in (20, 55):
        c = breakout_curve(n)
        c["break_even_bp_per_side"] = break_even(c["rows"])
        out["cost_curve"][f"d7_donchian_N{n}"] = c
        print(f"  N={n}: n={c['n_trades']} exposure={c['exposure_pct']}% "
              f"break_even={c['break_even_bp_per_side']}", flush=True)
    pc = pod_curve()
    pc["break_even_bp_per_side"] = break_even(pc["rows"])
    out["cost_curve"]["pod_vt_pattern_sweep"] = pc
    print(f"  pod: n={pc['n_trades']} break_even={pc['break_even_bp_per_side']}", flush=True)

    out["survivorship"] = survivorship_check()

    # Step 4: the full proof bar on the measured-cost survivor. Run at measured
    # cost, at the D7 family's 5bp, and at the pod's 25bp assumption.
    measured_side = out.get("spread_aggregate", {}).get("measured_cost_per_side_used_bp")
    out["proof_bar"] = {}
    for label, c in (("measured", measured_side), ("5bp", 5.0), ("25bp", 25.0)):
        if c is None:
            out["proof_bar"][label] = {"status": "no measured cost available"}
            continue
        print(f"proof bar at {label} ({c:.2f}bp/side): null 500, bootstrap 10000...", flush=True)
        pb = proof_bar(c)
        out["proof_bar"][label] = pb
        if pb.get("null"):
            print(f"  null pct {pb['null']['observed_percentile']} | excess CAGR "
                  f"{pb['excess_cagr_point']} CI {pb['excess_cagr_boot_ci95']} | "
                  f"CAGR {pb['cagr']} vs hurdle {pb['hurdle']['required_return']:.4f} "
                  f"-> {pb['verdict']}", flush=True)

    path = OUT / "equity_cost_20261122.json"
    path.write_text(json.dumps(out, indent=1, default=str))
    print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
