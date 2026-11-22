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


# ------------------------------------------------------------------ main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="skip network calls")
    a = ap.parse_args()
    key = os.environ.get("TIINGO_API_KEY", "")
    OUT.mkdir(parents=True, exist_ok=True)

    out = {
        "generated_utc": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "task": "M1 - EQUITY/ETF cost measurement",
        "sources": {
            "intraday_bars": "Tiingo IEX 1-min bars: "
                             "https://api.tiingo.com/iex/<SYM>/prices"
                             "?startDate=<day>&endDate=<day>&resampleFreq=1min",
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

    if not a.offline and key:
        print("measuring 1-min bar spread upper bounds...", flush=True)
        for sym in sorted(set(POD_UNIVERSE) | set(LARGECAP_UNIVERSE)):
            rec = measure_spread(sym)
            out["spread"][sym] = rec
            u = rec.get("range_upper_bound_rt_bp", {}).get("median")
            print(f"  {sym:<6} {rec.get('fetch_status', '?'):<12} "
                  f"range_ub_rt={u if u is None else round(u, 2)}bp", flush=True)
        out["top_of_book"] = top_of_book(sorted(set(POD_UNIVERSE) | set(LARGECAP_UNIVERSE)), key)
    else:
        out["spread"] = {"status": "SKIPPED_OFFLINE_OR_NO_KEY"}
        out["top_of_book"] = {"status": "SKIPPED_OFFLINE_OR_NO_KEY"}

    # aggregate the spread bound across the breakout universe only
    ub = [r["range_upper_bound_rt_bp"]["median"] for s, r in out["spread"].items()
          if isinstance(r, dict) and r.get("range_upper_bound_rt_bp") and s in POD_UNIVERSE]
    cs = [r["corwin_schultz"]["median_bp"] for s, r in out["spread"].items()
          if isinstance(r, dict) and r.get("corwin_schultz") and r["corwin_schultz"].get("median_bp") is not None
          and s in POD_UNIVERSE]
    out["spread_aggregate"] = {
        "universe": "POD_UNIVERSE",
        "n_symbols_with_data": len(ub),
        "range_upper_bound_rt_bp_median": statistics.median(ub) if ub else None,
        "corwin_schultz_rt_bp_median": statistics.median(cs) if cs else None,
        "measured_cost_per_side_used_bp": (statistics.median(ub) / 2) if ub else None,
        "basis": ("half the median 1-min bar range = a rigorous UPPER bound on "
                  "per-side spread; the true NBBO is tighter but was not "
                  "measurable with markets closed"),
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
