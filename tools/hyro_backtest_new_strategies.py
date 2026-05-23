#!/usr/bin/env python3
"""
Backtest the 5 new trend-following strategies added April 2026.

Runs IS/OOS split (70% / 15% / 15%) per TESTING_PROTOCOL.MD Layer 2.
Fetches 2 years of 1h candles from Binance, tests across 15 symbols,
reports per-split metrics and drift flags.

Usage:
  python tools/hyro_backtest_new_strategies.py
  python tools/hyro_backtest_new_strategies.py --months 24 --save
  python tools/hyro_backtest_new_strategies.py --strategy triple_ema_trend --symbol BTCUSDT
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

import hyro_backtest as hb

fetch_candles = hb.fetch_candles
parse_candles = hb.parse_candles
calc_sma = hb.calc_sma
calc_std = hb.calc_std
calc_rsi = hb.calc_rsi
calc_atr = hb.calc_atr
HyroSimulator = hb.HyroSimulator
HYRO = hb.HYRO

WORKSPACE = _TOOLS.parent
DEFAULT_OUTPUT = WORKSPACE / "audit_dashboard" / "data" / "hyro_backtest_new_strategies.json"

ALL_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "XRPUSDT",
    "BNBUSDT", "DOGEUSDT", "LINKUSDT", "ADAUSDT", "DOTUSDT",
    "NEARUSDT", "SUIUSDT", "ARBUSDT", "APTUSDT", "PEPEUSDT",
]


# ── Indicator helpers ───────────────────────────────────────────────────────

def calc_ema(values: list[float], period: int) -> list:
    n = len(values)
    out = [None] * n
    if n < period:
        return out
    k = 2 / (period + 1)
    out[period - 1] = sum(values[:period]) / period
    for i in range(period, n):
        out[i] = values[i] * k + out[i - 1] * (1 - k)
    return out


def calc_adx(candles: list[dict], period: int = 14):
    n = len(candles)
    adx = [None] * n
    plus_di = [None] * n
    minus_di = [None] * n
    if n < period * 3:
        return adx, plus_di, minus_di
    tr, p_dm, m_dm = [], [], []
    for i in range(1, n):
        h, l = candles[i]["high"], candles[i]["low"]
        pc = candles[i - 1]["close"]
        h1, l1 = candles[i - 1]["high"], candles[i - 1]["low"]
        tr.append(max(h - l, abs(h - pc), abs(l - pc)))
        up = h - h1
        dn = l1 - l
        p_dm.append(up if up > dn and up > 0 else 0.0)
        m_dm.append(dn if dn > up and dn > 0 else 0.0)
    dx_vals, dx_idx = [], []
    for i in range(period - 1, len(tr)):
        i_c = i + 1
        tr_m = sum(tr[i - period + 1: i + 1]) / period
        p_m = sum(p_dm[i - period + 1: i + 1]) / period
        m_m = sum(m_dm[i - period + 1: i + 1]) / period
        if tr_m <= 0:
            continue
        pp = 100.0 * p_m / tr_m
        mm = 100.0 * m_m / tr_m
        plus_di[i_c] = pp
        minus_di[i_c] = mm
        tot = pp + mm
        dx_vals.append(100.0 * abs(pp - mm) / tot if tot > 0 else 0.0)
        dx_idx.append(i_c)
    for j in range(period - 1, len(dx_vals)):
        adx_i = dx_idx[j]
        adx[adx_i] = sum(dx_vals[j - period + 1: j + 1]) / period
    return adx, plus_di, minus_di


# ── Strategy implementations (mirror JS in hyro_live_signals.js) ────────────

def strategy_triple_ema_trend(candles: list[dict], params: dict | None = None) -> list[dict]:
    """Triple EMA Trend — enters on EMA 9/21/55 alignment + pullback to EMA21."""
    p = params or {}
    fast, mid, slow = p.get("fast", 9), p.get("mid", 21), p.get("slow", 55)
    atr_p = p.get("atr_period", 14)
    tp_r = p.get("tp_r", 2.0)
    closes = [c["close"] for c in candles]
    ema_f = calc_ema(closes, fast)
    ema_m = calc_ema(closes, mid)
    ema_s = calc_ema(closes, slow)
    rsi = calc_rsi(candles, 14)
    atr = calc_atr(candles, atr_p)
    signals = []
    for i in range(slow + 10, len(candles)):
        if any(v is None for v in [ema_f[i], ema_m[i], ema_s[i], atr[i], rsi[i]]):
            continue
        c = candles[i]
        dist = abs(c["close"] - ema_m[i]) / ema_m[i]
        if ema_f[i] > ema_m[i] and ema_m[i] > ema_s[i] and 40 < rsi[i] < 70 and dist < 0.015:
            entry = c["close"]
            sl = ema_s[i] - 0.5 * atr[i]
            risk = entry - sl
            if risk > 0:
                tp = entry + tp_r * risk
                signals.append({"index": i, "time": c["open_time"], "direction": "LONG",
                                "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                                "rr": round(tp_r, 2), "strategy": "triple_ema_trend"})
        if ema_f[i] < ema_m[i] and ema_m[i] < ema_s[i] and 30 < rsi[i] < 60 and dist < 0.015:
            entry = c["close"]
            sl = ema_s[i] + 0.5 * atr[i]
            risk = sl - entry
            if risk > 0:
                tp = entry - tp_r * risk
                signals.append({"index": i, "time": c["open_time"], "direction": "SHORT",
                                "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                                "rr": round(tp_r, 2), "strategy": "triple_ema_trend"})
    return signals


def strategy_adx_slope_momentum(candles: list[dict], params: dict | None = None) -> list[dict]:
    """ADX Slope Momentum — enters when ADX is rising + EMA slope confirms."""
    p = params or {}
    atr_p = p.get("atr_period", 14)
    adx_p = p.get("adx_period", 14)
    tp_r = p.get("tp_r", 2.5)
    sl_atr = p.get("sl_atr", 1.0)
    slope_back = p.get("slope_lookback", 5)
    closes = [c["close"] for c in candles]
    adx, plus_di, minus_di = calc_adx(candles, adx_p)
    ema9 = calc_ema(closes, 9)
    ema21 = calc_ema(closes, 21)
    atr = calc_atr(candles, atr_p)
    signals = []
    for i in range(adx_p * 3 + slope_back, len(candles)):
        if any(v is None for v in [adx[i], adx[i - slope_back], ema9[i], ema9[i - 3],
                                    ema21[i], atr[i], plus_di[i], minus_di[i]]):
            continue
        adx_slope = adx[i] - adx[i - slope_back]
        if adx_slope <= 0 or adx[i] < 15:
            continue
        ema_slope = (ema9[i] - ema9[i - 3]) / ema9[i - 3] * 100
        c = candles[i]
        if ema9[i] > ema21[i] and ema_slope > 0.1 and plus_di[i] > minus_di[i]:
            entry = c["close"]
            sl = entry - sl_atr * atr[i]
            risk = entry - sl
            if risk > 0:
                tp = entry + tp_r * risk
                signals.append({"index": i, "time": c["open_time"], "direction": "LONG",
                                "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                                "rr": round(tp_r, 2), "strategy": "adx_slope_momentum"})
        if ema9[i] < ema21[i] and ema_slope < -0.1 and minus_di[i] > plus_di[i]:
            entry = c["close"]
            sl = entry + sl_atr * atr[i]
            risk = sl - entry
            if risk > 0:
                tp = entry - tp_r * risk
                signals.append({"index": i, "time": c["open_time"], "direction": "SHORT",
                                "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                                "rr": round(tp_r, 2), "strategy": "adx_slope_momentum"})
    return signals


def strategy_consolidation_breakout(candles: list[dict], params: dict | None = None) -> list[dict]:
    """Consolidation Breakout — ATR compression then range break."""
    p = params or {}
    atr_p = p.get("atr_period", 14)
    comp_mult = p.get("compression_mult", 0.75)
    lookback = p.get("lookback", 20)
    med_lookback = p.get("median_lookback", 100)
    tp_r = p.get("tp_r", 2.0)
    closes = [c["close"] for c in candles]
    atr = calc_atr(candles, atr_p)
    ema9 = calc_ema(closes, 9)
    ema21 = calc_ema(closes, 21)
    signals = []
    for i in range(med_lookback + 10, len(candles)):
        if any(v is None for v in [atr[i], ema9[i], ema21[i]]):
            continue
        # Median ATR
        atr_win = [atr[j] for j in range(i - med_lookback + 1, i + 1) if atr[j] is not None]
        if len(atr_win) < 20:
            continue
        atr_win.sort()
        median_atr = atr_win[len(atr_win) // 2]
        if atr[i] >= median_atr * comp_mult:
            continue
        # Range
        range_high = max(candles[j]["high"] for j in range(i - lookback + 1, i + 1))
        range_low = min(candles[j]["low"] for j in range(i - lookback + 1, i + 1))
        c = candles[i]
        if c["close"] > range_high and ema9[i] > ema21[i]:
            entry = c["close"]
            sl = range_low - 0.5 * atr[i]
            risk = entry - sl
            if risk > 0:
                tp = entry + tp_r * risk
                signals.append({"index": i, "time": c["open_time"], "direction": "LONG",
                                "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                                "rr": round(tp_r, 2), "strategy": "consolidation_breakout"})
        if c["close"] < range_low and ema9[i] < ema21[i]:
            entry = c["close"]
            sl = range_high + 0.5 * atr[i]
            risk = sl - entry
            if risk > 0:
                tp = entry - tp_r * risk
                signals.append({"index": i, "time": c["open_time"], "direction": "SHORT",
                                "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                                "rr": round(tp_r, 2), "strategy": "consolidation_breakout"})
    return signals


def strategy_rsi_pullback(candles: list[dict], params: dict | None = None) -> list[dict]:
    """RSI Pullback in Trend — enters on RSI 42-55 pullback in EMA-aligned trend."""
    p = params or {}
    atr_p = p.get("atr_period", 14)
    tp_r = p.get("tp_r", 2.0)
    rsi_period = p.get("rsi_period", 14)
    ema_slow = p.get("ema_slow", 50)
    closes = [c["close"] for c in candles]
    rsi = calc_rsi(candles, rsi_period)
    ema9 = calc_ema(closes, 9)
    ema21 = calc_ema(closes, 21)
    ema50 = calc_ema(closes, ema_slow)
    atr = calc_atr(candles, atr_p)
    signals = []
    for i in range(ema_slow + 10, len(candles)):
        if any(v is None for v in [rsi[i], ema9[i], ema21[i], ema50[i], atr[i]]):
            continue
        # Check recent RSI history
        was_high = any(rsi[j] is not None and rsi[j] > 60 for j in range(max(0, i - 5), i))
        was_low = any(rsi[j] is not None and rsi[j] < 40 for j in range(max(0, i - 5), i))
        c = candles[i]
        # LONG
        if (ema9[i] > ema21[i] and ema21[i] > ema50[i] and was_high
                and 42 <= rsi[i] <= 55 and c["close"] > ema21[i]):
            entry = c["close"]
            sl = ema50[i] - 0.5 * atr[i]
            risk = entry - sl
            if risk > 0:
                tp = entry + tp_r * risk
                signals.append({"index": i, "time": c["open_time"], "direction": "LONG",
                                "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                                "rr": round(tp_r, 2), "strategy": "rsi_pullback"})
        # SHORT
        if (ema9[i] < ema21[i] and ema21[i] < ema50[i] and was_low
                and 45 <= rsi[i] <= 58 and c["close"] < ema21[i]):
            entry = c["close"]
            sl = ema50[i] + 0.5 * atr[i]
            risk = sl - entry
            if risk > 0:
                tp = entry - tp_r * risk
                signals.append({"index": i, "time": c["open_time"], "direction": "SHORT",
                                "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                                "rr": round(tp_r, 2), "strategy": "rsi_pullback"})
    return signals


def strategy_vwap_trend(candles: list[dict], params: dict | None = None) -> list[dict]:
    """VWAP Trend Continuation — pullback to rolling VWAP in EMA-confirmed trend."""
    p = params or {}
    vwap_period = p.get("vwap_period", 20)
    atr_p = p.get("atr_period", 14)
    tp_r = p.get("tp_r", 2.0)
    sl_atr = p.get("sl_atr", 1.2)
    closes = [c["close"] for c in candles]
    atr = calc_atr(candles, atr_p)
    ema21 = calc_ema(closes, 21)
    ema50 = calc_ema(closes, 50)
    signals = []
    for i in range(vwap_period + 30, len(candles)):
        if any(v is None for v in [atr[i], ema21[i], ema50[i]]):
            continue
        # Rolling VWAP
        cum_vol, cum_pv = 0.0, 0.0
        for j in range(i - vwap_period + 1, i + 1):
            vol = candles[j]["volume"] or 1
            cum_vol += vol
            cum_pv += candles[j]["close"] * vol
        vwap = cum_pv / cum_vol
        c = candles[i]
        vwap_dist = (c["close"] - vwap) / vwap
        # LONG
        if ema21[i] > ema50[i] and -0.01 <= vwap_dist <= 0.005:
            entry = c["close"]
            sl = entry - sl_atr * atr[i]
            risk = entry - sl
            if risk > 0:
                tp = entry + tp_r * risk
                signals.append({"index": i, "time": c["open_time"], "direction": "LONG",
                                "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                                "rr": round(tp_r, 2), "strategy": "vwap_trend"})
        # SHORT
        if ema21[i] < ema50[i] and -0.005 <= vwap_dist <= 0.01:
            entry = c["close"]
            sl = entry + sl_atr * atr[i]
            risk = sl - entry
            if risk > 0:
                tp = entry - tp_r * risk
                signals.append({"index": i, "time": c["open_time"], "direction": "SHORT",
                                "entry": round(entry, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                                "rr": round(tp_r, 2), "strategy": "vwap_trend"})
    return signals


# ── Strategy registry ──────────────────────────────────────────────────────

NEW_STRATEGIES: dict[str, tuple[str, object]] = {
    "triple_ema_trend": ("Triple EMA Trend", strategy_triple_ema_trend),
    "adx_slope_momentum": ("ADX Slope Momentum", strategy_adx_slope_momentum),
    "consolidation_breakout": ("Consolidation Breakout", strategy_consolidation_breakout),
    "rsi_pullback": ("RSI Pullback in Trend", strategy_rsi_pullback),
    "vwap_trend": ("VWAP Trend Continuation", strategy_vwap_trend),
}


# ── IS/OOS split runner ───────────────────────────────────────────────────

def sim_on_signals(signals: list[dict], candles: list[dict], risk_pct: float = 0.75) -> dict:
    """Run HyroSimulator on a list of pre-generated signals."""
    if not signals:
        return {"total_trades": 0}
    acct = float(HYRO["account_size"])
    sim = HyroSimulator(account_size=acct, risk_pct=risk_pct)
    last_exit = -1
    for sig in sorted(signals, key=lambda s: s["index"]):
        if sig["index"] <= last_exit:
            continue
        if sim.failed:
            break
        if sim.daily_profit >= sim._consistency_cap():
            continue
        result = sim.simulate_trade(sig, candles)
        if result:
            last_exit = sig["index"] + result.get("bars_held", 0)
    wins = [t for t in sim.trades if t["pnl"] > 0]
    losses = [t for t in sim.trades if t["pnl"] <= 0]
    total = len(sim.trades)
    if total == 0:
        return {"total_trades": 0}
    total_profit = sum(t["pnl"] for t in wins)
    total_loss = sum(t["pnl"] for t in losses)
    return {
        "total_trades": total,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / total * 100, 1),
        "profit_factor": round(abs(total_profit / total_loss), 2) if total_loss != 0 else 999.0,
        "total_pnl": round(sim.total_pnl, 2),
        "pnl_pct": round(sim.total_pnl / acct * 100, 1),
        "max_dd": round(sim.max_drawdown_from_peak, 2),
        "avg_win": round(total_profit / len(wins), 2) if wins else 0.0,
        "avg_loss": round(total_loss / len(losses), 2) if losses else 0.0,
        "passed": sim.passed,
        "failed": sim.failed,
        "fail_reason": sim.fail_reason,
    }


def run_with_split(
    symbol: str,
    strategy_key: str,
    months: int = 24,
    risk_pct: float = 0.75,
    strategy_params: dict | None = None,
) -> dict | None:
    """Fetch candles, generate signals, split IS (70%) / OOS-val (15%) / OOS-holdout (15%)."""
    name, fn = NEW_STRATEGIES[strategy_key]
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=months * 30)
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(now.timestamp() * 1000)
    raw = fetch_candles(symbol, "1h", start_ms, end_ms)
    candles = parse_candles(raw)
    if len(candles) < 200:
        return None

    # Generate ALL signals on full dataset
    all_signals = fn(candles, strategy_params or {})
    if not all_signals:
        return None

    n = len(candles)
    is_end = int(n * 0.70)
    oos_val_end = int(n * 0.85)

    # Split signals by index
    is_sigs = [s for s in all_signals if s["index"] < is_end]
    oos_val_sigs = [s for s in all_signals if is_end <= s["index"] < oos_val_end]
    oos_hold_sigs = [s for s in all_signals if s["index"] >= oos_val_end]

    is_metrics = sim_on_signals(is_sigs, candles, risk_pct)
    oos_val_metrics = sim_on_signals(oos_val_sigs, candles, risk_pct)
    oos_hold_metrics = sim_on_signals(oos_hold_sigs, candles, risk_pct)

    # Drift detection
    is_wr = is_metrics.get("win_rate", 0)
    oos_wr = oos_val_metrics.get("win_rate", 0)
    hold_wr = oos_hold_metrics.get("win_rate", 0)
    is_pf = is_metrics.get("profit_factor", 0)
    oos_pf = oos_val_metrics.get("profit_factor", 0)

    wr_drift_val = abs(is_wr - oos_wr) if is_wr and oos_wr else None
    wr_drift_hold = abs(is_wr - hold_wr) if is_wr and hold_wr else None
    pf_drift = abs(is_pf - oos_pf) if is_pf and oos_pf else None

    # Drift flags per TESTING_PROTOCOL Layer 2
    drift_flags = []
    if wr_drift_val is not None and wr_drift_val > 15:
        drift_flags.append(f"WR drift IS→OOS-val: {wr_drift_val:.1f}pp")
    if wr_drift_hold is not None and wr_drift_hold > 15:
        drift_flags.append(f"WR drift IS→holdout: {wr_drift_hold:.1f}pp")
    if pf_drift is not None and pf_drift > 1.0:
        drift_flags.append(f"PF drift IS→OOS-val: {pf_drift:.2f}")
    if is_metrics.get("total_trades", 0) < 5:
        drift_flags.append("IS trades < 5 (insufficient)")
    if oos_val_metrics.get("total_trades", 0) < 3:
        drift_flags.append("OOS-val trades < 3 (insufficient)")

    # Verdict
    oos_pass = (
        oos_val_metrics.get("total_trades", 0) >= 3
        and oos_val_metrics.get("win_rate", 0) >= 40
        and oos_val_metrics.get("profit_factor", 0) >= 1.0
        and len(drift_flags) == 0
    )

    # Date ranges for reporting
    is_start_dt = datetime.utcfromtimestamp(candles[0]["open_time"] / 1000).strftime("%Y-%m-%d")
    is_end_dt = datetime.utcfromtimestamp(candles[is_end - 1]["open_time"] / 1000).strftime("%Y-%m-%d")
    oos_val_end_dt = datetime.utcfromtimestamp(candles[oos_val_end - 1]["open_time"] / 1000).strftime("%Y-%m-%d")
    holdout_end_dt = datetime.utcfromtimestamp(candles[-1]["open_time"] / 1000).strftime("%Y-%m-%d")

    return {
        "symbol": symbol,
        "strategy": strategy_key,
        "strategy_name": name,
        "months": months,
        "candles": n,
        "total_signals": len(all_signals),
        "splits": {
            "is": {
                "period": f"{is_start_dt} to {is_end_dt}",
                "candles": is_end,
                "signals": len(is_sigs),
                **is_metrics,
            },
            "oos_validation": {
                "period": f"{is_end_dt} to {oos_val_end_dt}",
                "candles": oos_val_end - is_end,
                "signals": len(oos_val_sigs),
                **oos_val_metrics,
            },
            "oos_holdout": {
                "period": f"{oos_val_end_dt} to {holdout_end_dt}",
                "candles": n - oos_val_end,
                "signals": len(oos_hold_sigs),
                **oos_hold_metrics,
            },
        },
        "drift": {
            "wr_is_vs_oos_val": round(wr_drift_val, 1) if wr_drift_val is not None else None,
            "wr_is_vs_holdout": round(wr_drift_hold, 1) if wr_drift_hold is not None else None,
            "pf_is_vs_oos_val": round(pf_drift, 2) if pf_drift is not None else None,
            "flags": drift_flags,
        },
        "oos_pass": oos_pass,
    }


# ── Main ───────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest 5 new trend-following strategies with IS/OOS split")
    parser.add_argument("--symbols", nargs="+", default=ALL_SYMBOLS)
    parser.add_argument("--months", type=int, default=24)
    parser.add_argument("--risk", type=float, default=0.75)
    parser.add_argument("--strategy", default=None, help="Single strategy key")
    parser.add_argument("--symbol", default=None, help="Single symbol (overrides --symbols)")
    parser.add_argument("--save", action="store_true")
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    symbols = [args.symbol] if args.symbol else args.symbols
    strats = [args.strategy] if args.strategy else list(NEW_STRATEGIES.keys())
    all_results: list[dict] = []

    total_combos = len(symbols) * len(strats)
    done = 0
    for symbol in symbols:
        for strat_key in strats:
            name = NEW_STRATEGIES[strat_key][0]
            done += 1
            print(f"\n{'=' * 70}")
            print(f" [{done}/{total_combos}] {symbol} × {name}")
            print(f"{'=' * 70}")
            try:
                result = run_with_split(symbol, strat_key, args.months, args.risk)
                if result:
                    all_results.append(result)
                    sp = result["splits"]
                    is_m = sp["is"]
                    oos_m = sp["oos_validation"]
                    ho_m = sp["oos_holdout"]
                    verdict = "✓ OOS-PASS" if result["oos_pass"] else "✗ OOS-FAIL"
                    flags = ", ".join(result["drift"]["flags"]) if result["drift"]["flags"] else "none"
                    print(f" IN-SAMPLE  : trades={is_m.get('total_trades',0):>3}  WR={is_m.get('win_rate',0):>5}%  PF={is_m.get('profit_factor',0):>6}  PnL=${is_m.get('total_pnl',0):>8}")
                    print(f" OOS-VAL    : trades={oos_m.get('total_trades',0):>3}  WR={oos_m.get('win_rate',0):>5}%  PF={oos_m.get('profit_factor',0):>6}  PnL=${oos_m.get('total_pnl',0):>8}")
                    print(f" HOLDOUT    : trades={ho_m.get('total_trades',0):>3}  WR={ho_m.get('win_rate',0):>5}%  PF={ho_m.get('profit_factor',0):>6}  PnL=${ho_m.get('total_pnl',0):>8}")
                    print(f" {verdict}  |  Drift flags: {flags}")
                else:
                    print(" No signals generated")
            except Exception as e:
                print(f" ERROR: {e}")
            time.sleep(0.15)

    # ── Summary table ──────────────────────────────────────────────────────
    print(f"\n{'=' * 120}")
    print(f" SUMMARY — {len(all_results)} results across {len(symbols)} symbols × {len(strats)} strategies ({args.months} months)")
    print(f"{'=' * 120}")

    # Group by strategy for aggregate view
    by_strat: dict[str, list] = {}
    for r in all_results:
        by_strat.setdefault(r["strategy"], []).append(r)

    print(f"\n {'Strategy':<25} {'Symbols':>7} {'Signals':>8} {'IS WR':>6} {'OOS WR':>7} {'Hold WR':>8} {'IS PF':>6} {'OOS PF':>7} {'OOS-Pass':>9} {'Drift':>6}")
    print(f" {'-'*25} {'-'*7} {'-'*8} {'-'*6} {'-'*7} {'-'*8} {'-'*6} {'-'*7} {'-'*9} {'-'*6}")
    for sk, runs in sorted(by_strat.items()):
        n_sym = len(runs)
        total_sigs = sum(r["total_signals"] for r in runs)
        is_wrs = [r["splits"]["is"]["win_rate"] for r in runs if r["splits"]["is"].get("total_trades", 0) > 0]
        oos_wrs = [r["splits"]["oos_validation"]["win_rate"] for r in runs if r["splits"]["oos_validation"].get("total_trades", 0) > 0]
        ho_wrs = [r["splits"]["oos_holdout"]["win_rate"] for r in runs if r["splits"]["oos_holdout"].get("total_trades", 0) > 0]
        is_pfs = [r["splits"]["is"]["profit_factor"] for r in runs if r["splits"]["is"].get("total_trades", 0) > 0]
        oos_pfs = [r["splits"]["oos_validation"]["profit_factor"] for r in runs if r["splits"]["oos_validation"].get("total_trades", 0) > 0]
        n_pass = sum(1 for r in runs if r["oos_pass"])
        n_drift = sum(1 for r in runs if r["drift"]["flags"])

        avg_is_wr = round(sum(is_wrs) / len(is_wrs), 1) if is_wrs else 0
        avg_oos_wr = round(sum(oos_wrs) / len(oos_wrs), 1) if oos_wrs else 0
        avg_ho_wr = round(sum(ho_wrs) / len(ho_wrs), 1) if ho_wrs else 0
        avg_is_pf = round(sum(is_pfs) / len(is_pfs), 2) if is_pfs else 0
        avg_oos_pf = round(sum(oos_pfs) / len(oos_pfs), 2) if oos_pfs else 0

        print(f" {sk:<25} {n_sym:>7} {total_sigs:>8} {avg_is_wr:>5.1f}% {avg_oos_wr:>6.1f}% {avg_ho_wr:>7.1f}% {avg_is_pf:>6.2f} {avg_oos_pf:>7.2f} {n_pass:>4}/{n_sym:<4} {n_drift:>5}")

    # Best/worst per-symbol results
    oos_pass_results = [r for r in all_results if r["oos_pass"]]
    oos_fail_results = [r for r in all_results if not r["oos_pass"]]
    print(f"\n OOS-PASS: {len(oos_pass_results)} / {len(all_results)} combos")
    if oos_pass_results:
        print(f"\n Top 10 OOS-passing combos (by OOS-val PnL):")
        top = sorted(oos_pass_results, key=lambda r: r["splits"]["oos_validation"].get("total_pnl", 0), reverse=True)[:10]
        for r in top:
            oos = r["splits"]["oos_validation"]
            print(f"   {r['symbol']:<10} {r['strategy']:<25} OOS: WR={oos.get('win_rate',0)}% PF={oos.get('profit_factor',0)} PnL=${oos.get('total_pnl',0)}")

    if args.save and all_results:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "months": args.months,
                "symbols": symbols,
                "strategies": strats,
                "testing_protocol": {
                    "split": "IS 70% / OOS-val 15% / OOS-holdout 15%",
                    "oos_pass_criteria": "trades >= 3, WR >= 40%, PF >= 1.0, no drift flags",
                    "drift_thresholds": "WR drift > 15pp, PF drift > 1.0",
                },
                "summary": {
                    sk: {
                        "symbols_tested": len(runs),
                        "oos_pass_count": sum(1 for r in runs if r["oos_pass"]),
                        "avg_is_wr": round(sum(r["splits"]["is"].get("win_rate", 0) for r in runs if r["splits"]["is"].get("total_trades", 0) > 0) / max(1, sum(1 for r in runs if r["splits"]["is"].get("total_trades", 0) > 0)), 1),
                        "avg_oos_wr": round(sum(r["splits"]["oos_validation"].get("win_rate", 0) for r in runs if r["splits"]["oos_validation"].get("total_trades", 0) > 0) / max(1, sum(1 for r in runs if r["splits"]["oos_validation"].get("total_trades", 0) > 0)), 1),
                    }
                    for sk, runs in by_strat.items()
                },
                "results": all_results,
            }, f, indent=2)
        print(f"\n Results saved to {out_path}")


if __name__ == "__main__":
    main()
