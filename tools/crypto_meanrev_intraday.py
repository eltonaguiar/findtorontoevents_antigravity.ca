#!/usr/bin/env python3
"""Item 29 - crypto intraday mean-reversion, net of MEASURED cost.

The pre-declared rule lives in docs/edge_research/14_CRYPTO_INTRADAY_MEANREV_2026-11-22.md
section 0 and was written BEFORE this script was first run. This module implements exactly
that rule and does not tune. Rule, verbatim:

  Signal : z = (Close - SMA50) / STD50 on 4h closes (50 bars).
  Entry  : LONG when z <= -2.0, SHORT when z >= +2.0; fill at the NEXT bar's OPEN (1-bar lag).
  Exit   : reversion to mean (z crosses 0 for a long / z <= 0 for a short), evaluated at a
           bar close and filled at the NEXT bar's open; OR time stop of 12 bars (exit at that
           bar's open).
  Stop   : intrabar stop at 2.0*ATR14 from entry price, checked FIRST on every bar, before
           the reversion/time exit. Gap-aware (fill at the open if the open is already beyond
           the stop, else at the stop price).
  Overlap: one position per symbol at a time; signals while a position is open are skipped.
  Sizing : each trade = 10% of current equity notional; equity compounded at each exit.
  Costs  : 20bp per round trip base (measured 2026-11-22; taker fee 10bp/side dominates),
           40bp stress; sweep only cost, never parameters.

Data is pulled from Binance spot 4h klines (api/v3/klines), paginated at the 1,000-row cap
with first/last timestamps verified against the request. SPY daily closes come from the
programme's daily cache for the benchmark.

Nothing is fabricated: a failed pull marks the symbol BLOCKED with its error.

Usage:
  python3 tools/crypto_meanrev_intraday.py                       # full analysis at 20bp
  python3 tools/crypto_meanrev_intraday.py --cost-bp 40          # stress case
  python3 tools/crypto_meanrev_intraday.py --null-shuffles 500   # random-entry null
  python3 tools/crypto_meanrev_intraday.py --refetch             # force a fresh pull
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# ---------------------------------------------------------------------------
# Pre-declared parameters (frozen; see doc section 0)
# ---------------------------------------------------------------------------
UNIVERSE = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT",
            "ADAUSDT", "DOGEUSDT", "LINKUSDT", "AVAXUSDT", "DOTUSDT"]
BAR_MS = 4 * 60 * 60 * 1000           # 4h
INTERVAL = "4h"
Z_LOOKBACK = 50
Z_ENTER = 2.0
ATR_LEN = 14
ATR_STOP_MULT = 2.0
TIME_STOP_BARS = 12
COST_BP_PRIMARY = 20.0                # measured round trip, best venue
COST_BP_STRESS = 40.0
COST_SWEEP = [0.0, 5.0, 10.0, 20.0, 40.0, 60.0]
POSITION_FRACTION = 0.10              # 10% of equity per trade = 1/len(UNIVERSE)
RRF = 0.0432                         # US 3-month T-bill, 2026-11-20
START = "2021-11-22T00:00:00Z"
END = "2026-11-22T00:00:00Z"
SPY_CACHE = REPO_ROOT / "data/cache/asset_class_review/SPY_5y.csv"
CACHE_DIR = REPO_ROOT / "data/cache/binance_4h"

BINANCE = "https://api.binance.com/api/v3/klines"


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
def _http_json(url: str, timeout: int = 30):
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                return json.loads(r.read().decode())
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            if attempt == 4:
                raise
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError("unreachable")


def _ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def fetch_klines(symbol: str, interval: str = INTERVAL, start: str = START, end: str = END):
    """Paginated Binance klines; verifies first/last timestamps against the request."""
    start_ms, end_ms = _ms(datetime.fromisoformat(start.replace("Z", "+00:00"))), \
        _ms(datetime.fromisoformat(end.replace("Z", "+00:00")))
    rows, cursor = [], start_ms
    while cursor < end_ms:
        q = (f"{BINANCE}?symbol={symbol}&interval={interval}"
             f"&startTime={cursor}&endTime={end_ms}&limit=1000")
        chunk = _http_json(q)
        if not chunk:
            break
        rows.extend(chunk)
        nxt = int(chunk[-1][0]) + BAR_MS
        if nxt <= cursor:            # no forward progress -> guard against a silent loop
            break
        cursor = nxt
        if len(chunk) < 1000:
            break
        time.sleep(0.2)
    if not rows:
        raise RuntimeError(f"no klines returned for {symbol}")
    # verify the pull covers what we asked for
    first_ts, last_ts = int(rows[0][0]), int(rows[-1][0])
    if first_ts > start_ms + BAR_MS:
        raise RuntimeError(f"{symbol}: first bar {first_ts} is after requested start {start_ms}")
    df = pd.DataFrame(rows, columns=[
        "open_time", "open", "high", "low", "close", "volume", "close_time",
        "qav", "trades", "tbbav", "tbqav", "ignore"])
    df = df[["open_time", "open", "high", "low", "close", "volume"]].astype(
        {"open": float, "high": float, "low": float, "close": float, "volume": float})
    df["dt"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df = df.drop_duplicates("open_time").sort_values("open_time").reset_index(drop=True)
    return df, {"symbol": symbol, "bars": len(df), "requested_start_ms": start_ms,
                "first_open_ms": first_ts, "last_open_ms": last_ts,
                "last_within_end": last_ts < end_ms}


def load_symbol(symbol: str, refetch: bool = False):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = CACHE_DIR / f"{symbol}_{INTERVAL}.csv"
    if cache.exists() and not refetch:
        df = pd.read_csv(cache, parse_dates=["dt"])
        meta = {"symbol": symbol, "bars": len(df), "source": "cache",
                "requested_start_ms": _ms(datetime.fromisoformat(START.replace("Z", "+00:00"))),
                "first_open_ms": int(df["open_time"].iloc[0]),
                "last_open_ms": int(df["open_time"].iloc[-1]),
                "last_within_end": int(df["open_time"].iloc[-1]) <
                _ms(datetime.fromisoformat(END.replace("Z", "+00:00")))}
        return df, meta
    df, meta = fetch_klines(symbol)
    df.to_csv(cache, index=False)
    meta["source"] = "binance"
    return df, meta


# ---------------------------------------------------------------------------
# Indicators
# ---------------------------------------------------------------------------
def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy().reset_index(drop=True)
    c = d["close"]
    ma = c.rolling(Z_LOOKBACK).mean()
    sd = c.rolling(Z_LOOKBACK).std(ddof=0)
    d["z"] = (c - ma) / sd
    prev_close = c.shift(1)
    tr = pd.concat([(d["high"] - d["low"]),
                    (d["high"] - prev_close).abs(),
                    (d["low"] - prev_close).abs()], axis=1).max(axis=1)
    d["atr"] = tr.rolling(ATR_LEN).mean()
    return d


# ---------------------------------------------------------------------------
# Core primitive (pure, unit-testable): walk one open position bar by bar.
# STOP IS CHECKED FIRST on every bar, before the reversion/time exit.
# ---------------------------------------------------------------------------
def walk_position(direction: int, entry_price: float, stop_price: float,
                  start_bar: int, z: np.ndarray, open_: np.ndarray,
                  high: np.ndarray, low: np.ndarray, close: np.ndarray,
                  time_stop_bars: int = TIME_STOP_BARS,
                  signal_bar: int | None = None) -> dict:
    """Walk a position from `start_bar` (the entry bar) to exit.

    direction: +1 long, -1 short. `signal_bar` is the bar whose close produced the entry
    signal (used only for the time-stop reference; defaults to start_bar - 1).
    Returns dict(exit_bar, exit_price, reason).

    Conventions, in order per bar:
      1. STOP first: intrabar. If the bar OPEN is already beyond the stop -> fill at open
         (gap, worse price). Else if the bar range crosses the stop -> fill at stop_price.
      2. Then the reversion exit: if the bar CLOSE satisfies reversion, exit at the NEXT
         bar's OPEN (no look-ahead - we only know the close after the bar).
      3. Then the time stop: exit at this bar's OPEN once bars elapsed reaches the limit.
    """
    sig = signal_bar if signal_bar is not None else start_bar - 1
    n = len(z)
    for b in range(start_bar, n):
        o, h, l, c = open_[b], high[b], low[b], close[b]
        # 1) STOP FIRST (intrabar), gap-aware
        if direction == 1:
            if o <= stop_price:
                return {"exit_bar": b, "exit_price": o, "reason": "stop_gap"}
            if l <= stop_price:
                return {"exit_bar": b, "exit_price": stop_price, "reason": "stop"}
        else:
            if o >= stop_price:
                return {"exit_bar": b, "exit_price": o, "reason": "stop_gap"}
            if h >= stop_price:
                return {"exit_bar": b, "exit_price": stop_price, "reason": "stop"}
        # 2) TIME STOP: exit at this bar's open when the limit is reached
        if b - sig >= time_stop_bars:
            return {"exit_bar": b, "exit_price": o, "reason": "time"}
        # 3) REVERSION: decided on this close, filled at NEXT bar's open
        reverted = (c >= 0) if direction == 1 else (c <= 0)
        if reverted:
            nb = b + 1
            if nb >= n:
                return {"exit_bar": b, "exit_price": c, "reason": "reversion_eod"}
            return {"exit_bar": nb, "exit_price": open_[nb], "reason": "reversion"}
    return {"exit_bar": n - 1, "exit_price": close[n - 1], "reason": "eod_force"}


def generate_trades(df: pd.DataFrame, symbol: str) -> list[dict]:
    """Apply the pre-declared rule to one symbol's bars (non-overlapping)."""
    d = add_indicators(df)
    z = d["z"].to_numpy()
    o, h, l, c = (d[k].to_numpy() for k in ("open", "high", "low", "close"))
    atr = d["atr"].to_numpy()
    n = len(d)
    trades, busy_until = [], -1
    for t in range(Z_LOOKBACK, n - 1):
        if t <= busy_until or math.isnan(z[t]) or math.isnan(atr[t]):
            continue
        if z[t] <= -Z_ENTER:
            direction = 1
        elif z[t] >= Z_ENTER:
            direction = -1
        else:
            continue
        entry_bar = t + 1                       # 1-BAR LAG: fill at next open
        entry_price = o[entry_bar]
        stop = entry_price - direction * ATR_STOP_MULT * atr[t] if direction == 1 \
            else entry_price + ATR_STOP_MULT * atr[t]
        res = walk_position(direction, entry_price, stop, entry_bar, z, o, h, l, c,
                            signal_bar=t)
        eb = res["exit_bar"]
        gross = direction * (res["exit_price"] - entry_price) / entry_price
        # direction-adjusted buy&hold over the same holding period (entry->exit)
        bh = (c[eb] - entry_price) / entry_price
        sel_alpha = gross - (bh if direction == 1 else -bh)
        trades.append({
            "symbol": symbol, "direction": direction, "signal_bar": t,
            "entry_bar": entry_bar, "entry_time": str(d["dt"].iloc[entry_bar]),
            "entry_price": float(entry_price), "exit_bar": eb,
            "exit_time": str(d["dt"].iloc[eb]), "exit_price": float(res["exit_price"]),
            "reason": res["reason"], "bars_held": eb - entry_bar,
            "gross_ret": float(gross), "bh_ret": float(bh),
            "sel_alpha": float(sel_alpha), "z_entry": float(z[t]),
        })
        busy_until = eb
    return trades


# ---------------------------------------------------------------------------
# Equity and statistics
# ---------------------------------------------------------------------------
def equity_curve(trades: list[dict], cost_bp: float) -> tuple[pd.Series, list[dict]]:
    """Compound equity at each exit in exit-time order. Returns daily equity + trade log."""
    if not trades:
        return pd.Series(dtype=float), []
    log = []
    eq = 1.0
    cost = cost_bp / 1e4
    ordered = sorted(trades, key=lambda x: (x["exit_bar"], x["entry_time"]))
    for tr in ordered:
        net = tr["gross_ret"] - cost
        pnl = POSITION_FRACTION * eq * net
        eq += pnl
        log.append({**tr, "net_ret": net, "equity_after": eq})
    exits = pd.to_datetime([x["exit_time"] for x in log], utc=True)
    ser = pd.Series([x["equity_after"] for x in log], index=exits)
    daily = ser.resample("1D").last().ffill()
    daily = pd.concat([pd.Series([1.0], index=[daily.index[0] - pd.Timedelta(days=1)]),
                       daily]).ffill()
    return daily, log


def perf_stats(daily: pd.Series) -> dict:
    if len(daily) < 3:
        return {"cagr": None, "vol": None, "sharpe": None, "maxdd": None}
    r = daily.pct_change().dropna()
    years = (daily.index[-1] - daily.index[0]).days / 365.25
    cagr = daily.iloc[-1] ** (1 / years) - 1 if years > 0 and daily.iloc[-1] > 0 else None
    vol = float(r.std() * math.sqrt(365))
    sharpe = float((r.mean() * 365 - RRF) / (r.std() * math.sqrt(365))) if r.std() > 0 else None
    dd = (daily / daily.cummax() - 1).min()
    return {"cagr": None if cagr is None else float(cagr), "vol": vol,
            "sharpe": sharpe, "maxdd": float(dd)}


def trade_stats(log: list[dict]) -> dict:
    nets = np.array([x["net_ret"] for x in log], dtype=float)
    if len(nets) == 0:
        return {"n": 0}
    wins = nets[nets > 0]
    losses = nets[nets <= 0]
    pf = wins.sum() / -losses.sum() if losses.sum() < 0 else float("inf")
    gross_wins = sum(x["gross_ret"] for x in log if x["gross_ret"] > 0)
    gross_loss = -sum(x["gross_ret"] for x in log if x["gross_ret"] <= 0)
    return {
        "n": int(len(nets)),
        "win_rate": float((nets > 0).mean()),
        "mean_net_ret": float(nets.mean()),
        "median_net_ret": float(np.median(nets)),
        "pf": float(pf),
        "pf_gross_no_cost": float(gross_wins / gross_loss) if gross_loss > 0 else None,
        "mean_gross_ret": float(np.mean([x["gross_ret"] for x in log])),
        "mean_sel_alpha": float(np.mean([x["sel_alpha"] for x in log])),
        "skew": float(pd.Series(nets).skew()),
        "stdev": float(nets.std(ddof=1)),
        "worst_trade": float(nets.min()),
        "best_trade": float(nets.max()),
    }


def per_symbol(log: list[dict], total_pnl: float) -> dict:
    out = {}
    for sym in sorted({x["symbol"] for x in log}):
        sub = [x for x in log if x["symbol"] == sym]
        nets = np.array([x["net_ret"] for x in sub])
        w = nets[nets > 0].sum()
        l = -nets[nets <= 0].sum()
        out[sym] = {"n": len(sub), "sum_net_ret": float(nets.sum()),
                    "mean_net_ret": float(nets.mean()),
                    "pf": float(w / l) if l > 0 else None,
                    "share_of_pnl": float(nets.sum() / total_pnl) if total_pnl else None}
    return out


# ---------------------------------------------------------------------------
# Random-entry null and bootstrap CI
# ---------------------------------------------------------------------------
def random_null(per_symbol_data: dict, observed_total: float, shuffles: int,
                cost_bp: float, seed: int = 20261122) -> dict:
    """Replace each trade by a random same-direction, same-holding trade in the same symbol."""
    rng = np.random.default_rng(seed)
    # collect the real trades' direction/holding lengths to preserve the holding-period dist
    totals = []
    for _ in range(shuffles):
        tot = 0.0
        for sym, (d, trades) in per_symbol_data.items():
            o, h, l, c = d["open"].to_numpy(), d["high"].to_numpy(), d["low"].to_numpy(), d["close"].to_numpy()
            n = len(c)
            for tr in trades:
                hold = max(1, tr["bars_held"])
                direction = tr["direction"]
                # random entry bar, keeping the same holding length and direction
                best = min(n - hold - 2, n - 2)
                if best <= 1:
                    continue
                eb = int(rng.integers(1, best))
                entry_price = o[eb]
                xb = min(eb + hold, n - 1)
                exit_price = o[xb] if xb < n else c[-1]
                gross = direction * (exit_price - entry_price) / entry_price
                tot += (gross - cost_bp / 1e4)
        totals.append(tot)
    totals = np.array(totals)
    pct = float((totals < observed_total).mean() * 100)
    return {"shuffles": shuffles, "observed_total_net_ret": float(observed_total),
            "null_mean": float(totals.mean()), "null_p95": float(np.percentile(totals, 95)),
            "null_p99": float(np.percentile(totals, 99)),
            "percentile": pct,
            "beats_random_95": bool(pct >= 95)}


def load_spy_daily() -> pd.Series:
    df = pd.read_csv(SPY_CACHE, parse_dates=["Date"]).set_index("Date").sort_index()
    return df["Close"]


def _date_index(ser: pd.Series) -> pd.Series:
    """Normalise to tz-naive calendar dates so tz-aware and tz-naive series can align."""
    if isinstance(ser.index, pd.DatetimeIndex) and ser.index.tz is not None:
        ser = ser.copy()
        ser.index = ser.index.tz_convert("UTC").tz_localize(None).normalize()
    else:
        ser = ser.copy()
        ser.index = pd.DatetimeIndex(ser.index).normalize()
    return ser.groupby(level=0).last()


def bootstrap_excess_cagr(daily: pd.Series, spy: pd.Series, n_boot: int = 10000,
                         block_days: int = 5, seed: int = 20261122) -> dict:
    s = _date_index(daily.resample("1D").last().ffill().dropna())
    spy = _date_index(spy.resample("1D").last().ffill())
    idx = s.index.intersection(spy.index)
    if len(idx) < 60:
        raise RuntimeError("strategy and SPY series do not overlap; refusing to report a CI")
    s = s.loc[idx]
    spy = spy.loc[idx]
    rs = s.pct_change(fill_method=None).fillna(0).to_numpy()
    rb = spy.pct_change(fill_method=None).fillna(0).to_numpy()
    n = len(rs)
    if n < 60:
        return {"point_excess_cagr": None, "ci_low": None, "ci_high": None,
                "n_resamples": 0, "note": "series too short"}
    block = max(1, block_days)
    nblocks = int(math.ceil(n / block))
    starts = np.arange(0, n - block + 1) if n - block + 1 > 0 else np.array([0])
    years = (idx[-1] - idx[0]).days / 365.25
    rng = np.random.default_rng(seed)

    def cagr(path_r):
        eq = np.cumprod(1 + path_r)
        return eq[-1] ** (1 / years) - 1 if eq[-1] > 0 else -1.0

    point = cagr(rs) - cagr(rb)
    diffs = []
    for _ in range(n_boot):
        picks = rng.choice(starts, size=nblocks, replace=True)
        pi = np.concatenate([np.arange(p, p + block) for p in picks])[:n]
        diffs.append(cagr(rs[pi]) - cagr(rb[pi]))
    diffs = np.array(diffs)
    return {"point_excess_cagr": float(point),
            "ci_low": float(np.percentile(diffs, 2.5)),
            "ci_high": float(np.percentile(diffs, 97.5)),
            "n_resamples": n_boot, "window_days": int(n),
            "spy_cagr_over_window": float(cagr(rb))}


# ---------------------------------------------------------------------------
# Break-even cost
# ---------------------------------------------------------------------------
def breakeven_cost(trades: list[dict], lo: float = 0.0, hi: float = 200.0) -> float:
    """Round-trip bp at which mean net return per trade is exactly zero (bisection)."""
    def mean_net(c):
        return np.mean([t["gross_ret"] for t in trades]) - c / 1e4
    if mean_net(lo) <= 0:
        return float(lo)
    if mean_net(hi) >= 0:
        return float(hi)
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if mean_net(mid) > 0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Item 29 crypto intraday mean-reversion")
    ap.add_argument("--cost-bp", type=float, default=COST_BP_PRIMARY)
    ap.add_argument("--null-shuffles", type=int, default=500)
    ap.add_argument("--boot", type=int, default=10000)
    ap.add_argument("--refetch", action="store_true")
    ap.add_argument("--out", default=str(REPO_ROOT / "reports/crypto_meanrev_intraday_20261122.json"))
    args = ap.parse_args(argv)

    data, meta, blocked = {}, {}, {}
    for sym in UNIVERSE:
        try:
            df, m = load_symbol(sym, refetch=args.refetch)
            data[sym] = df
            meta[sym] = m
        except Exception as exc:  # noqa: BLE001 - mark BLOCKED honestly
            blocked[sym] = f"{type(exc).__name__}: {exc}"
    if not data:
        print(json.dumps({"verdict": "BLOCKED_DATA", "blocked": blocked}, indent=2))
        return 2

    per_sym_trades = {sym: generate_trades(df, sym) for sym, df in data.items()}
    all_trades = [t for ts in per_sym_trades.values() for t in ts]

    # base case
    daily, log = equity_curve(all_trades, args.cost_bp)
    tstats = trade_stats(log)
    pstats = perf_stats(daily)
    total_net = float(sum(t["net_ret"] for t in log)) if log else 0.0
    psym = per_symbol(log, total_net)

    # cost sweep (ONLY cost varies)
    sweep = {}
    for c in COST_SWEEP:
        _, lg = equity_curve(all_trades, c)
        st = trade_stats(lg)
        sweep[f"{c:g}bp"] = {"n": st.get("n"), "mean_net_ret": st.get("mean_net_ret"),
                            "pf": st.get("pf"), "win_rate": st.get("win_rate")}
    be = breakeven_cost(all_trades)

    # per-symbol frames for the null
    null_data = {sym: (data[sym], per_sym_trades[sym]) for sym in per_sym_trades}
    null = random_null(null_data, total_net if log else 0.0, args.null_shuffles, args.cost_bp)

    # bootstrap CI vs SPY
    spy = load_spy_daily()
    boot = bootstrap_excess_cagr(daily, spy, n_boot=args.boot) if len(daily) else {}

    # worst period: worst 30-day rolling return on the daily equity curve
    worst_period = None
    if len(daily) > 30:
        roll = daily.pct_change(30).min()
        worst_period = {"worst_30d_ret": float(roll),
                        "at": str(daily.pct_change(30).idxmin().date())}

    # verdict under the pre-declared kill criteria
    if tstats.get("n", 0) < 30:
        verdict = "INSUFFICIENT_MEASUREMENT"
    elif null["percentile"] < 95:
        verdict = "KILL"
    elif be < 20:
        verdict = "KILL"
    elif tstats.get("mean_net_ret", 0) <= 0:
        verdict = "KILL"
    elif (null["percentile"] >= 95 and be >= 40
          and boot.get("ci_low") is not None and boot["ci_low"] > 0):
        verdict = "INVESTABLE"
    else:
        verdict = "MARGINAL"

    top_sym = max(psym, key=lambda k: abs(psym[k]["sum_net_ret"])) if psym else None
    conc = psym[top_sym]["share_of_pnl"] if top_sym else None

    result = {
        "item": 29, "name": "crypto intraday mean-reversion", "generated_utc": datetime.now(timezone.utc).isoformat(),
        "cost_bp_base": args.cost_bp, "cost_bp_stress": COST_BP_STRESS,
        "resolution": INTERVAL, "universe": list(data.keys()), "blocked": blocked,
        "data_meta": meta,
        "predeclared": {"z_lookback": Z_LOOKBACK, "z_enter": Z_ENTER, "atr_len": ATR_LEN,
                        "atr_stop_mult": ATR_STOP_MULT, "time_stop_bars": TIME_STOP_BARS,
                        "entry_fill": "next bar open (1-bar lag)", "overlap": "one per symbol"},
        "base_case": {"cost_bp": args.cost_bp, "trade_stats": tstats, "perf_stats": pstats,
                      "worst_period": worst_period},
        "cost_sweep": sweep, "breakeven_cost_bp": be,
        "random_null": null, "bootstrap_vs_spy": boot,
        "per_symbol": psym, "top_symbol_by_abs_pnl": top_sym,
        "top_symbol_pnl_share": conc,
        "verdict": verdict,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, indent=2))
    print(json.dumps({k: result[k] for k in
                      ("verdict", "resolution", "breakeven_cost_bp", "random_null",
                       "bootstrap_vs_spy", "base_case")}, indent=2))
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
