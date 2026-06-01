"""mutation_hunt_2026-06-01.py — 3-axis mutation analysis for two dormant CRYPTO strategies.

Strategies under test:
  - justin_breakout_volume_v2  (PF 1.024, WR 64.6%, n=12,658 — asymmetric payoff)
  - keltner_bounce             (PF 0.995, WR 43.6%, n=2,661 — sub-breakeven)

Axes:
  1) Direction inversion (LONG<->SHORT)
  2) Symbol-class movement (CRYPTO -> FOREX/COMMODITY)  [DEFERRED — Binance won't serve FX/commod; reported HONESTLY]
  3) Parameter mutation (param grid)
  4) Hold-time extension (48h -> 96h -> 168h)

Output: JSON + console table. PER_AXIS WALL-TIME CAP 5 MIN.
"""
from __future__ import annotations
import json, math, time, sys, os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Callable

import numpy as np
import pandas as pd
import requests

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT", "TRXUSDT",
    "DOTUSDT", "LTCUSDT", "BCHUSDT", "ATOMUSDT", "ETCUSDT",
]
INTERVAL_MS = 60 * 60 * 1000  # 1h
BARS = 8760  # 1 year

MIRRORS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]


def fetch_klines(symbol: str, bars: int = BARS) -> Optional[pd.DataFrame]:
    """Fetch ~1yr 1h klines paginated. Cache to /tmp."""
    cache = f"/tmp/mutation_hunt_{symbol}_1h_{bars}.pkl"
    if os.path.exists(cache):
        try:
            return pd.read_pickle(cache)
        except Exception:
            pass
    end_ts = int(time.time() * 1000)
    start_ts = end_ts - bars * INTERVAL_MS
    out = []
    cur = start_ts
    while cur < end_ts:
        rows = None
        for base in MIRRORS:
            try:
                r = requests.get(
                    f"{base}/api/v3/klines",
                    params={"symbol": symbol, "interval": "1h", "startTime": cur, "limit": 1000},
                    timeout=8,
                )
                if r.status_code == 200:
                    rows = r.json()
                    break
            except Exception:
                continue
        if not rows:
            break
        out.extend(rows)
        last = rows[-1][0]
        if last <= cur:
            break
        cur = last + INTERVAL_MS
        if len(rows) < 1000:
            break
    if not out:
        return None
    df = pd.DataFrame(out, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "qav", "trades", "tbb", "tbq", "ignore",
    ])
    for c in ("open", "high", "low", "close", "volume"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df[["open_time", "open", "high", "low", "close", "volume"]].dropna().reset_index(drop=True)
    try:
        df.to_pickle(cache)
    except Exception:
        pass
    return df


# -----------------------------------------------------------------------------
# Indicators
# -----------------------------------------------------------------------------

def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def atr(high, low, close, n: int) -> pd.Series:
    pc = close.shift(1)
    tr = pd.concat([(high - low).abs(), (high - pc).abs(), (low - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def rsi(close, n: int = 14) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0).rolling(n).mean()
    dn = (-delta.clip(upper=0)).rolling(n).mean()
    rs = up / dn.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


# -----------------------------------------------------------------------------
# Trade simulator (intrabar TP/SL using next-bar OHLC, conservative)
# -----------------------------------------------------------------------------

@dataclass
class TradeResult:
    pnl_pct: float
    bars_held: int
    exit_reason: str  # TP, SL, EXPIRED


def simulate_trade(df: pd.DataFrame, i: int, direction: str, entry: float,
                   tp: float, sl: float, max_hold: int) -> TradeResult:
    """Walk forward bars i+1..i+max_hold checking OHLC for TP/SL hit.
    Conservative: if both hit in same bar, assume SL.
    Returns pnl% (signed), bars held, exit reason.
    """
    for k in range(1, max_hold + 1):
        if i + k >= len(df):
            # End of data; exit at last close
            last = df["close"].iloc[-1]
            pnl = (last - entry) / entry if direction == "LONG" else (entry - last) / entry
            return TradeResult(pnl * 100, k, "EXPIRED")
        bar = df.iloc[i + k]
        hi, lo = bar["high"], bar["low"]
        if direction == "LONG":
            hit_sl = lo <= sl
            hit_tp = hi >= tp
            if hit_sl and hit_tp:
                return TradeResult((sl - entry) / entry * 100, k, "SL")
            if hit_sl:
                return TradeResult((sl - entry) / entry * 100, k, "SL")
            if hit_tp:
                return TradeResult((tp - entry) / entry * 100, k, "TP")
        else:  # SHORT
            hit_sl = hi >= sl
            hit_tp = lo <= tp
            if hit_sl and hit_tp:
                return TradeResult((entry - sl) / entry * 100, k, "SL")
            if hit_sl:
                return TradeResult((entry - sl) / entry * 100, k, "SL")
            if hit_tp:
                return TradeResult((entry - tp) / entry * 100, k, "TP")
    # Expired at max_hold close
    last = df["close"].iloc[i + max_hold]
    pnl = (last - entry) / entry if direction == "LONG" else (entry - last) / entry
    return TradeResult(pnl * 100, max_hold, "EXPIRED")


def stats(trades: List[TradeResult]) -> Dict:
    if not trades:
        return {"n": 0, "wr": 0.0, "pf": 0.0, "avg_pnl": 0.0, "dsr": 0.0, "mean_bars": 0.0}
    n = len(trades)
    wins = [t.pnl_pct for t in trades if t.pnl_pct > 0]
    losses = [t.pnl_pct for t in trades if t.pnl_pct <= 0]
    wr = len(wins) / n
    gp = sum(wins)
    gl = abs(sum(losses)) or 1e-9
    pf = gp / gl
    pnls = np.array([t.pnl_pct for t in trades])
    mu = pnls.mean()
    sd = pnls.std(ddof=1) if n > 1 else 1.0
    # Annualized-ish Sharpe proxy on per-trade pnls -> Deflated SR approximation
    sr = (mu / sd) * math.sqrt(252) if sd > 0 else 0.0
    # DSR proxy: SR shrunk for sample size and skew/kurtosis (Bailey & Lopez de Prado lite)
    if n > 3 and sd > 0:
        skew = pd.Series(pnls).skew()
        kurt = pd.Series(pnls).kurt()
        # Variance of SR estimate
        var_sr = (1 - skew * sr + (kurt - 1) / 4 * sr * sr) / (n - 1)
        dsr = sr / math.sqrt(var_sr) if var_sr > 0 else 0.0
        # Normalize to ~SR-like scale by /sqrt(n)
        dsr = dsr / math.sqrt(n)
    else:
        dsr = 0.0
    return {
        "n": n,
        "wr": round(wr * 100, 1),
        "pf": round(pf, 3),
        "avg_pnl": round(mu, 3),
        "dsr": round(dsr, 3),
        "mean_bars": round(np.mean([t.bars_held for t in trades]), 1),
    }


# -----------------------------------------------------------------------------
# Signal generators
# -----------------------------------------------------------------------------

def justin_breakout_signals(df: pd.DataFrame, lookback: int = 20,
                              vol_mult: float = 1.3, rsi_low: float = 25,
                              rsi_high: float = 75, range_max: float = 0.15) -> List[Tuple[int, str]]:
    """Return list of (bar_idx, direction) for breakout signals.
    Mirrors justin_breakout_volume_v2 logic but vectorized across history.
    """
    sigs = []
    if len(df) < lookback + 20:
        return sigs
    close = df["close"]; high = df["high"]; low = df["low"]; vol = df["volume"]
    rsi_s = rsi(close, 14)
    # Pre-compute rolling extremes ending at bar i (uses past 'lookback' inclusive)
    rh = high.rolling(lookback).max()
    rl = low.rolling(lookback).min()
    vol_ma = vol.rolling(lookback).mean()
    prev_close = close.shift(1)
    for i in range(lookback + 5, len(df) - 1):  # need future bar
        if pd.isna(vol_ma.iloc[i]) or vol.iloc[i] < vol_ma.iloc[i] * vol_mult:
            continue
        recent_h = rh.iloc[i]; recent_l = rl.iloc[i]
        range_pct = (recent_h - recent_l) / max(recent_l, 1e-9)
        if range_pct >= range_max:
            continue
        rv = rsi_s.iloc[i]
        if pd.isna(rv):
            continue
        # LONG
        if high.iloc[i] > recent_h * 0.998 and close.iloc[i] > prev_close.iloc[i]:
            if rv < rsi_high:
                sigs.append((i, "LONG"))
        elif low.iloc[i] < recent_l * 1.002 and close.iloc[i] < prev_close.iloc[i]:
            if rv > rsi_low:
                sigs.append((i, "SHORT"))
    return sigs


def keltner_bounce_signals(df: pd.DataFrame, ema_p: int = 20, atr_p: int = 10,
                            mult: float = 2.0) -> List[Tuple[int, str]]:
    """LONG signals on lower-band bounce."""
    sigs = []
    if len(df) < max(ema_p, atr_p) + 10:
        return sigs
    mid = ema(df["close"], ema_p)
    a = atr(df["high"], df["low"], df["close"], atr_p)
    lower = mid - mult * a
    close = df["close"]
    mask = (close > lower) & (close.shift(1) <= lower.shift(1))
    for i in range(max(ema_p, atr_p) + 2, len(df) - 1):
        if bool(mask.iloc[i]):
            sigs.append((i, "LONG"))
    return sigs


# -----------------------------------------------------------------------------
# Backtests
# -----------------------------------------------------------------------------

def backtest_justin(data: Dict[str, pd.DataFrame], invert: bool = False,
                    vol_mult: float = 1.3, tp_atr: float = 2.0, sl_kind: str = "range",
                    max_hold: int = 48, tp_pct: Optional[float] = None,
                    sl_pct: Optional[float] = None) -> List[TradeResult]:
    """Run justin_breakout backtest across all symbols.
    sl_kind = 'range' uses recent_low/high (original); else uses sl_pct.
    tp_pct/sl_pct override ATR-based TP/SL if provided.
    """
    out: List[TradeResult] = []
    for sym, df in data.items():
        sigs = justin_breakout_signals(df, vol_mult=vol_mult)
        if not sigs:
            continue
        a = atr(df["high"], df["low"], df["close"], 14)
        rh = df["high"].rolling(20).max()
        rl = df["low"].rolling(20).min()
        for i, direction in sigs:
            if invert:
                direction = "SHORT" if direction == "LONG" else "LONG"
            entry = df["close"].iloc[i]
            atr_v = a.iloc[i]
            if pd.isna(atr_v):
                continue
            if tp_pct is not None and sl_pct is not None:
                if direction == "LONG":
                    tp = entry * (1 + tp_pct)
                    sl = entry * (1 - sl_pct)
                else:
                    tp = entry * (1 - tp_pct)
                    sl = entry * (1 + sl_pct)
            else:
                if direction == "LONG":
                    tp = entry + tp_atr * atr_v
                    sl = rl.iloc[i] * 0.995 if sl_kind == "range" else entry * (1 - 0.01)
                else:
                    tp = entry - tp_atr * atr_v
                    sl = rh.iloc[i] * 1.005 if sl_kind == "range" else entry * (1 + 0.01)
            out.append(simulate_trade(df, i, direction, entry, tp, sl, max_hold))
    return out


def backtest_keltner(data: Dict[str, pd.DataFrame], invert: bool = False,
                     ema_p: int = 20, atr_p: int = 10, mult: float = 2.0,
                     tp_pct: float = 0.02, sl_pct: float = 0.015,
                     max_hold: int = 48) -> List[TradeResult]:
    out: List[TradeResult] = []
    for sym, df in data.items():
        sigs = keltner_bounce_signals(df, ema_p, atr_p, mult)
        for i, direction in sigs:
            if invert:
                direction = "SHORT"
            entry = df["close"].iloc[i]
            if direction == "LONG":
                tp = entry * (1 + tp_pct); sl = entry * (1 - sl_pct)
            else:
                tp = entry * (1 - tp_pct); sl = entry * (1 + sl_pct)
            out.append(simulate_trade(df, i, direction, entry, tp, sl, max_hold))
    return out


# -----------------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------------

def load_data() -> Dict[str, pd.DataFrame]:
    data = {}
    t0 = time.time()
    for s in SYMBOLS:
        df = fetch_klines(s)
        if df is not None and len(df) > 200:
            data[s] = df
            print(f"  [{s}] {len(df)} bars  ({time.time()-t0:.1f}s elapsed)", flush=True)
    return data


def main():
    print("=" * 70, flush=True)
    print("MUTATION HUNT 2026-06-01 — justin_breakout_volume_v2 + keltner_bounce", flush=True)
    print("=" * 70, flush=True)
    print("Fetching 1yr 1h klines for 15 CRYPTO majors...", flush=True)
    data = load_data()
    print(f"Loaded {len(data)} symbols. Beginning mutation runs.\n", flush=True)
    report = {"timestamp": datetime.now(timezone.utc).isoformat(), "symbols": list(data.keys())}

    # ---------- BASELINES ----------
    print("=== BASELINES ===", flush=True)
    t = time.time()
    base_j = backtest_justin(data, invert=False)
    print(f"  justin baseline       : {stats(base_j)}  [{time.time()-t:.1f}s]", flush=True)
    t = time.time()
    base_k = backtest_keltner(data, invert=False)
    print(f"  keltner baseline      : {stats(base_k)}  [{time.time()-t:.1f}s]", flush=True)
    report["baselines"] = {"justin": stats(base_j), "keltner": stats(base_k)}

    # ---------- AXIS 1: Direction inversion ----------
    print("\n=== AXIS 1: INVERSION ===", flush=True)
    t = time.time()
    inv_j = backtest_justin(data, invert=True)
    s_inv_j = stats(inv_j)
    print(f"  justin_inverse        : {s_inv_j}  [{time.time()-t:.1f}s]", flush=True)
    t = time.time()
    inv_k = backtest_keltner(data, invert=True)
    s_inv_k = stats(inv_k)
    print(f"  keltner_inverse       : {s_inv_k}  [{time.time()-t:.1f}s]", flush=True)
    report["axis1_inversion"] = {"justin_inverse": s_inv_j, "keltner_inverse": s_inv_k}

    # ---------- AXIS 2: Symbol class movement ----------
    # Binance public klines does NOT serve FX/commodity. Be honest.
    print("\n=== AXIS 2: SYMBOL CLASS MOVEMENT ===", flush=True)
    print("  SKIPPED — Binance klines API does not serve FOREX/COMMODITY. Would need", flush=True)
    print("  yfinance or OANDA fetcher (~5+ min new code). HONEST: not done in this run.", flush=True)
    report["axis2_xasset"] = {"status": "SKIPPED", "reason": "Binance klines is CRYPTO only; cross-asset fetcher not wired in this tool."}

    # ---------- AXIS 3: Parameter grid ----------
    print("\n=== AXIS 3: PARAMETER MUTATION ===", flush=True)
    t0 = time.time()
    # Keltner grid: 5 EMA x 4 mult = 20 combos
    kelt_results = []
    for ep in [10, 14, 20, 30, 50]:
        for m in [1.5, 2.0, 2.5, 3.0]:
            if time.time() - t0 > 300:
                print("  TIME-CAP HIT for axis 3 (keltner)", flush=True); break
            s = stats(backtest_keltner(data, ema_p=ep, mult=m))
            s["params"] = {"ema_p": ep, "mult": m}
            kelt_results.append(s)
    kelt_results.sort(key=lambda r: (r["pf"], r["wr"]), reverse=True)
    print("  Top-3 keltner param combos:", flush=True)
    for r in kelt_results[:3]:
        print(f"    {r}", flush=True)

    # Justin grid: vol_mult x TP_pct x SL_pct (3 x 4 x 4 = 48 combos -> time-cap aware)
    just_results = []
    t1 = time.time()
    for vm in [1.5, 2.0, 3.0, 4.0]:
        for tp in [0.01, 0.02, 0.03, 0.04]:
            for sl in [0.005, 0.01, 0.015, 0.02]:
                if time.time() - t1 > 300:
                    break
                trades = backtest_justin(data, vol_mult=vm, tp_pct=tp, sl_pct=sl)
                s = stats(trades)
                s["params"] = {"vol_mult": vm, "tp_pct": tp, "sl_pct": sl}
                just_results.append(s)
            if time.time() - t1 > 300:
                break
        if time.time() - t1 > 300:
            print("  TIME-CAP HIT for axis 3 (justin)", flush=True); break
    just_results.sort(key=lambda r: (r["pf"], r["wr"]), reverse=True)
    print("  Top-3 justin param combos:", flush=True)
    for r in just_results[:3]:
        print(f"    {r}", flush=True)
    report["axis3_param"] = {"keltner_top3": kelt_results[:3], "justin_top3": just_results[:3],
                              "keltner_all": kelt_results, "justin_all": just_results}

    # ---------- AXIS 4: Hold-time extension ----------
    print("\n=== AXIS 4: HOLD-TIME EXTENSION ===", flush=True)
    hold_j = {}; hold_k = {}
    for h in [48, 96, 168]:
        s = stats(backtest_justin(data, max_hold=h))
        s["max_hold"] = h
        hold_j[h] = s
        print(f"  justin  h={h}h : {s}", flush=True)
    for h in [48, 96, 168]:
        s = stats(backtest_keltner(data, max_hold=h))
        s["max_hold"] = h
        hold_k[h] = s
        print(f"  keltner h={h}h : {s}", flush=True)
    report["axis4_hold"] = {"justin": hold_j, "keltner": hold_k}

    # ---------- VERDICT ----------
    def passes_t3(s):
        # Crude PF_LB: PF / (1 + 1/sqrt(n))
        n = s.get("n", 0)
        pf = s.get("pf", 0)
        if n < 50 or pf <= 0:
            return False, 0.0
        pf_lb = pf / (1 + 1 / math.sqrt(n))
        return (pf_lb > 1.0 and s.get("dsr", 0) > 0.5), pf_lb

    candidates = []
    for name, s in [("justin_inverse", s_inv_j), ("keltner_inverse", s_inv_k)]:
        ok, lb = passes_t3(s); candidates.append((name, s, ok, lb))
    for r in kelt_results[:3]:
        ok, lb = passes_t3(r); candidates.append((f"keltner_param_{r.get('params')}", r, ok, lb))
    for r in just_results[:3]:
        ok, lb = passes_t3(r); candidates.append((f"justin_param_{r.get('params')}", r, ok, lb))
    for h, s in hold_j.items():
        ok, lb = passes_t3(s); candidates.append((f"justin_hold_{h}h", s, ok, lb))
    for h, s in hold_k.items():
        ok, lb = passes_t3(s); candidates.append((f"keltner_hold_{h}h", s, ok, lb))

    print("\n=== VERDICT ===", flush=True)
    passing = [c for c in candidates if c[2]]
    if passing:
        print("  T3-PASSING MUTATIONS:", flush=True)
        for name, s, _, lb in passing:
            print(f"    {name}: pf={s['pf']}  pf_lb={lb:.3f}  wr={s['wr']}  n={s['n']}  dsr={s['dsr']}", flush=True)
    else:
        print("  NO T3-passing mutation found across all axes.", flush=True)

    report["verdict"] = {
        "passing": [{"name": n, "stats": s, "pf_lb": lb} for n, s, ok, lb in passing],
        "recommendation": ("ADD_PASSING_MUTATIONS_TO_PAPER_PILOT" if passing
                            else "BLOCK_BOTH_VIA_BLOCKED_SOURCE_SYSTEMS"),
    }
    out_path = os.path.join(REPO_ROOT, "reports", "mutation_hunt_2026-06-01.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nReport written to {out_path}", flush=True)


if __name__ == "__main__":
    main()
