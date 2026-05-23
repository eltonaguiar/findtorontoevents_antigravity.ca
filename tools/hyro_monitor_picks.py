#!/usr/bin/env python3
"""
hyro_monitor_picks.py — Monitor top Hyro strategy signals and track performance.

Scans proven strategies from hyro_live_strategies.json against live 1h candles.
Writes a snapshot to audit_dashboard/data/hyro_signal_monitor.json.

Usage:
  python tools/hyro_monitor_picks.py              # scan + print
  python tools/hyro_monitor_picks.py --save       # scan + save JSON
  python tools/hyro_monitor_picks.py --watch 60   # rescan every 60s
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

import hyro_backtest as hb
import hyro_backtest_extended as hbe

WORKSPACE = _TOOLS.parent
MONITOR_OUT = WORKSPACE / "audit_dashboard" / "data" / "hyro_signal_monitor.json"
STRATEGIES_JSON = WORKSPACE / "audit_dashboard" / "data" / "hyro_live_strategies.json"


def calc_cci(candles: list[dict], period: int = 20) -> list:
    n = len(candles)
    result = [None] * n
    for i in range(period - 1, n):
        window = candles[i - period + 1:i + 1]
        tp = [(c["high"] + c["low"] + c["close"]) / 3 for c in window]
        sma_tp = sum(tp) / period
        mad = sum(abs(t - sma_tp) for t in tp) / period
        result[i] = (tp[-1] - sma_tp) / (0.015 * mad) if mad > 0 else 0
    return result


def calc_cmf(candles: list[dict], period: int = 20) -> list:
    n = len(candles)
    result = [None] * n
    for i in range(period - 1, n):
        window = candles[i - period + 1:i + 1]
        mf_vol = vol_sum = 0
        for c in window:
            rng = c["high"] - c["low"]
            mfm = ((c["close"] - c["low"]) - (c["high"] - c["close"])) / rng if rng > 0 else 0
            mf_vol += mfm * c["volume"]
            vol_sum += c["volume"]
        result[i] = mf_vol / vol_sum if vol_sum > 0 else 0
    return result


def evaluate_strategy(
    sym: str, strat_key: str, params: dict, candles: list[dict], idx: int
) -> dict | None:
    """Evaluate a single strategy on the bar at idx. Return signal dict or None."""
    closes = [c["close"] for c in candles]
    atr_vals = hb.calc_atr(candles, 14)
    atr = atr_vals[idx] if atr_vals[idx] else 0
    if atr == 0:
        return None
    last = candles[idx]

    if strat_key == "cci_divergence":
        cci = calc_cci(candles, params.get("cci_period", 20))
        if cci[idx] is None or cci[idx - 1] is None:
            return None
        if cci[idx] > -100 and cci[idx - 1] <= -100:
            e = last["close"]; sl = e - 1.5 * atr; tp = e + 2 * (e - sl)
            return {"direction": "LONG", "entry": round(e, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                    "trigger": f"CCI crossed above -100 ({cci[idx]:.0f})", "rr": 2.0}
        if cci[idx] < 100 and cci[idx - 1] >= 100:
            e = last["close"]; sl = e + 1.5 * atr; tp = e - 2 * (sl - e)
            return {"direction": "SHORT", "entry": round(e, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                    "trigger": f"CCI crossed below +100 ({cci[idx]:.0f})", "rr": 2.0}

    elif strat_key == "adx_vol_breakout":
        adx_v, plus_di, minus_di = hbe.calc_adx(candles, 14)
        if adx_v[idx] is None or plus_di[idx] is None:
            return None
        vol_lb = params.get("vol_lookback", 20)
        avg_vol = sum(candles[j]["volume"] for j in range(idx - vol_lb, idx)) / vol_lb if idx >= vol_lb else 0
        if adx_v[idx] >= 25 and avg_vol > 0 and last["volume"] > 1.5 * avg_vol:
            if plus_di[idx] > minus_di[idx]:
                e = last["close"]; sl = e - 1.5 * atr; tp = e + 2 * (e - sl)
                return {"direction": "LONG", "entry": round(e, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                        "trigger": f"ADX={adx_v[idx]:.0f} +DI={plus_di[idx]:.0f}>{minus_di[idx]:.0f} vol={last['volume']/avg_vol:.1f}x", "rr": 2.0}
            else:
                e = last["close"]; sl = e + 1.5 * atr; tp = e - 2 * (sl - e)
                return {"direction": "SHORT", "entry": round(e, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                        "trigger": f"ADX={adx_v[idx]:.0f} -DI={minus_di[idx]:.0f}>{plus_di[idx]:.0f} vol={last['volume']/avg_vol:.1f}x", "rr": 2.0}

    elif strat_key == "cmf_cross":
        cmf = calc_cmf(candles, params.get("cmf_period", 20))
        if cmf[idx] is None or cmf[idx - 1] is None:
            return None
        if cmf[idx] > 0.05 and cmf[idx - 1] <= 0.05:
            e = last["close"]; sl = e - 1.5 * atr; tp = e + 2 * (e - sl)
            return {"direction": "LONG", "entry": round(e, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                    "trigger": f"CMF crossed above +0.05 ({cmf[idx]:.3f})", "rr": 2.0}
        if cmf[idx] < -0.05 and cmf[idx - 1] >= -0.05:
            e = last["close"]; sl = e + 1.5 * atr; tp = e - 2 * (sl - e)
            return {"direction": "SHORT", "entry": round(e, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                    "trigger": f"CMF crossed below -0.05 ({cmf[idx]:.3f})", "rr": 2.0}

    elif strat_key in ("squeeze_breakout", "bb_squeeze"):
        sma = hb.calc_sma(candles, 20)
        std = hb.calc_std(candles, 20)
        ema50 = hbe.calc_ema(closes, 50)
        if sma[idx] is None or std[idx] is None or ema50[idx] is None or sma[idx] == 0:
            return None
        upper = sma[idx] + 2 * std[idx]
        lower = sma[idx] - 2 * std[idx]
        width = (upper - lower) / sma[idx]
        min_w = float("inf")
        for j in range(max(0, idx - 40), idx):
            if sma[j] and std[j] and sma[j] > 0:
                w = 4 * std[j] / sma[j]
                min_w = min(min_w, w)
        squeeze = width <= min_w * 1.05
        avg_vol = sum(candles[j]["volume"] for j in range(idx - 20, idx)) / 20
        vol_ok = last["volume"] >= 1.4 * avg_vol if avg_vol > 0 else False
        if squeeze and vol_ok:
            if last["close"] > upper and last["close"] > ema50[idx]:
                e = last["close"]; sl = e - 1.4 * atr; tp = e + 2.2 * (e - sl)
                return {"direction": "LONG", "entry": round(e, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                        "trigger": f"BB squeeze breakout UP w={width:.4f}", "rr": 2.2}
            if last["close"] < lower and last["close"] < ema50[idx]:
                e = last["close"]; sl = e + 1.4 * atr; tp = e - 2.2 * (sl - e)
                return {"direction": "SHORT", "entry": round(e, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                        "trigger": f"BB squeeze breakout DOWN w={width:.4f}", "rr": 2.2}

    elif strat_key == "ema_pullback_adx":
        ema21 = hbe.calc_ema(closes, 21)
        ema55 = hbe.calc_ema(closes, 55)
        adx_v, plus_di, minus_di = hbe.calc_adx(candles, 14)
        if ema21[idx] is None or ema55[idx] is None or adx_v[idx] is None:
            return None
        touch = 0.35 * atr
        bull = (ema21[idx] > ema55[idx] and last["close"] > ema55[idx]
                and plus_di[idx] > minus_di[idx] and adx_v[idx] >= 20)
        bear = (ema21[idx] < ema55[idx] and last["close"] < ema55[idx]
                and minus_di[idx] > plus_di[idx] and adx_v[idx] >= 20)
        if bull and last["low"] <= ema21[idx] + touch and last["close"] > ema21[idx]:
            e = last["close"]; sl = e - 1.4 * atr; tp = e + 2.2 * (e - sl)
            return {"direction": "LONG", "entry": round(e, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                    "trigger": f"EMA pullback to 21, ADX={adx_v[idx]:.0f}", "rr": 2.2}
        if bear and last["high"] >= ema21[idx] - touch and last["close"] < ema21[idx]:
            e = last["close"]; sl = e + 1.4 * atr; tp = e - 2.2 * (sl - e)
            return {"direction": "SHORT", "entry": round(e, 2), "sl": round(sl, 2), "tp": round(tp, 2),
                    "trigger": f"EMA pullback to 21 (bear), ADX={adx_v[idx]:.0f}", "rr": 2.2}

    return None


def get_market_context(candles: list[dict], idx: int) -> dict:
    """Compute indicator snapshot at bar idx."""
    closes = [c["close"] for c in candles]
    rsi14 = hb.calc_rsi(candles, 14)
    cci = calc_cci(candles, 20)
    cmf = calc_cmf(candles, 20)
    atr = hb.calc_atr(candles, 14)
    adx_v, plus_di, minus_di = hbe.calc_adx(candles, 14)
    ema21 = hbe.calc_ema(closes, 21)
    ema55 = hbe.calc_ema(closes, 55)
    sma200 = hb.calc_sma(candles, 200)
    vol_20avg = sum(candles[j]["volume"] for j in range(max(0, idx - 20), idx)) / 20
    return {
        "price": candles[idx]["close"],
        "rsi14": round(rsi14[idx], 1) if rsi14[idx] else None,
        "cci20": round(cci[idx], 0) if cci[idx] else None,
        "cmf20": round(cmf[idx], 3) if cmf[idx] else None,
        "atr14": round(atr[idx], 2) if atr[idx] else None,
        "adx": round(adx_v[idx], 0) if adx_v[idx] else None,
        "plus_di": round(plus_di[idx], 0) if plus_di[idx] else None,
        "minus_di": round(minus_di[idx], 0) if minus_di[idx] else None,
        "ema_trend": "BULL" if (ema21[idx] and ema55[idx] and ema21[idx] > ema55[idx]) else "BEAR" if (ema21[idx] and ema55[idx] and ema21[idx] < ema55[idx]) else "FLAT",
        "above_200sma": candles[idx]["close"] > sma200[idx] if sma200[idx] else None,
        "vol_ratio": round(candles[idx]["volume"] / vol_20avg, 1) if vol_20avg > 0 else 0,
    }


def scan_all(quiet: bool = False) -> dict:
    """Run all proven strategies. Return snapshot dict."""
    with open(STRATEGIES_JSON) as f:
        cfg = json.load(f)

    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=310)
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(now.timestamp() * 1000)

    candle_cache: dict[str, list[dict]] = {}
    all_symbols = cfg.get("symbols", ["BTCUSDT", "ETHUSDT", "SOLUSDT"])

    for sym in all_symbols:
        if sym not in candle_cache:
            raw = hb.fetch_candles(sym, "1h", start_ms, end_ms)
            candle_cache[sym] = hb.parse_candles(raw)
            time.sleep(0.15)

    signals = []
    market_ctx = {}

    for strat_cfg in cfg["strategies"]:
        tier = strat_cfg.get("tier", "unknown")
        if tier == "demoted":
            continue
        strat_key = strat_cfg["strategy"]
        strat_label = strat_cfg["label"]
        syms = strat_cfg.get("symbols", all_symbols)
        params = strat_cfg.get("params", {})

        for sym in syms:
            candles = candle_cache.get(sym, [])
            if len(candles) < 210:
                continue
            idx = len(candles) - 2

            if sym not in market_ctx:
                market_ctx[sym] = get_market_context(candles, idx)

            sig = evaluate_strategy(sym, strat_key, params, candles, idx)
            bar_time = datetime.fromtimestamp(candles[idx]["open_time"] / 1000, tz=timezone.utc).isoformat()

            entry = {
                "symbol": sym,
                "strategy": strat_key,
                "strategy_label": strat_label,
                "tier": tier,
                "bar_time": bar_time,
                "signal": sig,
            }
            signals.append(entry)

    active = [s for s in signals if s["signal"] is not None]
    waiting = [s for s in signals if s["signal"] is None]

    snapshot = {
        "scan_time": now.isoformat(),
        "summary": {
            "total_checks": len(signals),
            "active_signals": len(active),
            "waiting": len(waiting),
        },
        "market_context": market_ctx,
        "active_signals": active,
        "waiting": [{"symbol": s["symbol"], "strategy": s["strategy"], "tier": s["tier"]} for s in waiting],
    }

    if not quiet:
        print(f"\n{'='*70}")
        print(f"  HYRO SIGNAL MONITOR — {now.strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"{'='*70}")
        print(f"\n  Market Context:")
        for sym, ctx in market_ctx.items():
            trend_icon = "📈" if ctx["ema_trend"] == "BULL" else "📉" if ctx["ema_trend"] == "BEAR" else "➖"
            print(f"    {trend_icon} {sym:10s} ${ctx['price']:>10,.2f}  RSI={ctx['rsi14']}  CCI={ctx['cci20']}  ADX={ctx['adx']}  CMF={ctx['cmf20']}")

        print(f"\n  Active Signals ({len(active)}):")
        if active:
            for s in active:
                sig = s["signal"]
                icon = "🟢" if sig["direction"] == "LONG" else "🔴"
                risk = abs(sig["entry"] - sig["sl"])
                risk_pct = risk / sig["entry"] * 100
                print(f"    {icon} {s['symbol']:10s} {sig['direction']:5s}  entry=${sig['entry']:>10,.2f}  SL=${sig['sl']:>10,.2f}  TP=${sig['tp']:>10,.2f}  R:R={sig['rr']}  risk={risk_pct:.1f}%")
                print(f"       Strategy: {s['strategy_label']}")
                print(f"       Trigger:  {sig['trigger']}")
                print(f"       $25 risk → size = ${25/risk:.4f} units" if risk > 0 else "")
        else:
            print("    (no active signals — strategies waiting for trigger conditions)")

        print(f"\n  Waiting ({len(waiting)}):")
        for s in waiting:
            print(f"    ⚪ {s['symbol']:10s} {s['strategy']}")
        print()

    return snapshot


def main():
    parser = argparse.ArgumentParser(description="Hyro signal monitor")
    parser.add_argument("--save", action="store_true")
    parser.add_argument("--watch", type=int, default=0, help="Rescan interval in seconds (0=once)")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    while True:
        snapshot = scan_all(quiet=args.quiet)
        if args.save:
            MONITOR_OUT.parent.mkdir(parents=True, exist_ok=True)
            # Append to history
            history_path = MONITOR_OUT.with_name("hyro_signal_history.json")
            history = []
            if history_path.is_file():
                try:
                    history = json.loads(history_path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    pass
            history.append(snapshot)
            if len(history) > 500:
                history = history[-500:]
            history_path.write_text(json.dumps(history, indent=2), encoding="utf-8")
            MONITOR_OUT.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
            print(f"  Saved → {MONITOR_OUT}")
            print(f"  History → {history_path} ({len(history)} entries)")

        if args.watch <= 0:
            break
        print(f"\n  Next scan in {args.watch}s...")
        time.sleep(args.watch)


if __name__ == "__main__":
    main()
