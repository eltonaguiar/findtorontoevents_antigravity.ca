#!/usr/bin/env python
"""
Rocket Scanner v2 - Enhanced with wider TP targets matching actual winner moves (8-13%)
Uses 3%/5% TP targets instead of conservative 2%, and includes high-WR candidates
"""
import json
import urllib.request
import time
import math
import os
import sys
from datetime import datetime, timezone

BINANCE_MIRRORS = [
    "https://data-api.binance.vision",
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]

def api_call(path, params=None):
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        path = f"{path}?{qs}"
    for mirror in BINANCE_MIRRORS:
        url = f"{mirror}{path}"
        for attempt in range(2):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    return json.loads(resp.read().decode())
            except (urllib.error.URLError, OSError, json.JSONDecodeError):
                time.sleep(0.3)
    return None

def get_klines(symbol, interval="1h", limit=100):
    return api_call("/api/v3/klines", {"symbol": symbol, "interval": interval, "limit": str(limit)})

def compute_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    return 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))

def compute_macd(closes, fast=12, slow=26, signal=9):
    if len(closes) < slow + signal:
        return 0, 0, 0
    def ema(data, period):
        result = [data[0]]
        mult = 2.0 / (period + 1)
        for i in range(1, len(data)):
            result.append(data[i] * mult + result[-1] * (1 - mult))
        return result
    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)
    macd_line = [f - s for f, s in zip(ema_fast, ema_slow)]
    signal_line = ema(macd_line, signal)
    return macd_line[-1], signal_line[-1], macd_line[-1] - signal_line[-1]

def compute_ema(closes, period):
    if not closes: return 0
    result = closes[0]
    mult = 2.0 / (period + 1)
    for c in closes[1:]:
        result = c * mult + result * (1 - mult)
    return result

def compute_bb(closes, period=20, std_mult=2.0):
    if len(closes) < period:
        return 0, 0, 0
    sma = sum(closes[-period:]) / period
    std = math.sqrt(sum((c - sma) ** 2 for c in closes[-period:]) / period)
    return sma - std_mult * std, sma, sma + std_mult * std

def compute_atr(highs, lows, closes, period=14):
    if len(closes) < period + 1:
        return 0
    trs = []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        trs.append(tr)
    atr = sum(trs[:period]) / period
    for i in range(period, len(trs)):
        atr = (atr * (period - 1) + trs[i]) / period
    return atr

def backtest_aggressive(symbol, direction, klines, tp_pct=3.0, sl_pct=2.0):
    """Backtest with wider TP (matching real 8-13% winners) and reasonable SL."""
    if not klines or len(klines) < 60:
        return 0, 0, 0, 0, 0

    closes = [float(k[4]) for k in klines]
    highs = [float(k[2]) for k in klines]
    lows = [float(k[3]) for k in klines]
    volumes = [float(k[5]) for k in klines]

    trades = []
    max_favorable = []
    max_adverse = []

    for i in range(50, len(closes) - 24):
        window_closes = closes[:i+1]
        window_volumes = volumes[:i+1]

        rsi = compute_rsi(window_closes[-30:])
        _, _, macd_hist = compute_macd(window_closes[-40:])
        avg_vol = sum(window_volumes[-20:]) / 20
        vol_ratio = window_volumes[i] / max(avg_vol, 1e-10)
        recent_max_vol = max(window_volumes[max(0,i-3):i+1])
        vol_spike = recent_max_vol / max(avg_vol, 1e-10)
        ema9 = compute_ema(window_closes[-20:], 9)
        ema20 = compute_ema(window_closes[-30:], 20)

        # Check accumulation
        up_vol = sum(v for c, pc, v in zip(window_closes[-8:], window_closes[-9:-1], window_volumes[-8:]) if c > pc)
        down_vol = sum(v for c, pc, v in zip(window_closes[-8:], window_closes[-9:-1], window_volumes[-8:]) if c <= pc)

        triggered = False
        if direction == "LONG":
            # Multiple trigger conditions (any match)
            if (vol_spike > 1.8 and rsi > 45 and rsi < 78 and macd_hist > 0 and ema9 > ema20):
                triggered = True
            elif (up_vol > down_vol * 1.5 and ema9 > ema20 and rsi > 50 and rsi < 75):
                triggered = True
        else:
            if (vol_spike > 1.8 and rsi < 55 and rsi > 22 and macd_hist < 0 and ema9 < ema20):
                triggered = True
            elif (down_vol > up_vol * 1.5 and ema9 < ema20 and rsi < 50 and rsi > 25):
                triggered = True

        if not triggered:
            continue

        entry = closes[i]
        future_highs = highs[i+1:i+25]
        future_lows = lows[i+1:i+25]
        future_closes = closes[i+1:i+25]

        if direction == "LONG":
            mfe = (max(future_highs) / entry - 1) * 100
            mae = (min(future_lows) / entry - 1) * 100
            max_favorable.append(mfe)
            max_adverse.append(mae)

            # Check TP/SL hit order
            result = None
            for j in range(len(future_closes)):
                if future_highs[j] >= entry * (1 + tp_pct/100):
                    result = tp_pct
                    break
                if future_lows[j] <= entry * (1 - sl_pct/100):
                    result = -sl_pct
                    break
            if result is None:
                result = (future_closes[-1] / entry - 1) * 100 if future_closes else 0
            trades.append(result)
        else:
            mfe = (1 - min(future_lows) / entry) * 100
            mae = (max(future_highs) / entry - 1) * 100
            max_favorable.append(mfe)
            max_adverse.append(-mae)

            result = None
            for j in range(len(future_closes)):
                if future_lows[j] <= entry * (1 - tp_pct/100):
                    result = tp_pct
                    break
                if future_highs[j] >= entry * (1 + sl_pct/100):
                    result = -sl_pct
                    break
            if result is None:
                result = (1 - future_closes[-1] / entry) * 100 if future_closes else 0
            trades.append(result)

    if not trades:
        return 0, 0, 0, 0, 0

    wins = sum(1 for t in trades if t > 0)
    wr = wins / len(trades) * 100
    avg_ret = sum(trades) / len(trades)
    avg_mfe = sum(max_favorable) / len(max_favorable) if max_favorable else 0
    avg_mae = sum(max_adverse) / len(max_adverse) if max_adverse else 0

    return round(wr, 1), round(avg_ret, 3), len(trades), round(avg_mfe, 2), round(avg_mae, 2)


def analyze_full(symbol, klines_1h):
    """Full analysis returning all metrics."""
    if not klines_1h or len(klines_1h) < 30:
        return None

    closes = [float(k[4]) for k in klines_1h]
    highs = [float(k[2]) for k in klines_1h]
    lows = [float(k[3]) for k in klines_1h]
    volumes = [float(k[5]) for k in klines_1h]

    price = closes[-1]
    if price == 0:
        return None

    rsi = compute_rsi(closes)
    _, _, macd_hist = compute_macd(closes)
    avg_vol = sum(volumes[-20:]) / max(len(volumes[-20:]), 1)
    vol_ratio = volumes[-1] / max(avg_vol, 1e-10)
    recent_max_vol = max(volumes[-4:]) if len(volumes) >= 4 else volumes[-1]
    vol_spike = recent_max_vol / max(avg_vol, 1e-10)

    ema9 = compute_ema(closes, 9)
    ema20 = compute_ema(closes, 20)
    ema50 = compute_ema(closes, 50) if len(closes) >= 50 else ema20
    ema_bull = ema9 > ema20 > ema50
    ema_bear = ema9 < ema20 < ema50

    bb_lower, bb_mid, bb_upper = compute_bb(closes)
    bb_width = (bb_upper - bb_lower) / max(bb_mid, 1e-10)
    atr = compute_atr(highs, lows, closes)
    atr_pct = atr / max(price, 1e-10) * 100

    mom_4h = (closes[-1] / closes[-5] - 1) * 100 if len(closes) >= 5 else 0
    mom_12h = (closes[-1] / closes[-13] - 1) * 100 if len(closes) >= 13 else 0
    mom_24h = (closes[-1] / closes[-25] - 1) * 100 if len(closes) >= 25 else 0

    up_vol = sum(v for c, pc, v in zip(closes[-8:], closes[-9:-1], volumes[-8:]) if c > pc)
    down_vol = sum(v for c, pc, v in zip(closes[-8:], closes[-9:-1], volumes[-8:]) if c <= pc)

    # MACD cross detection
    macd_prev = compute_macd(closes[:-1])
    prev_diff = macd_prev[0] - macd_prev[1]
    curr_diff = compute_macd(closes)[0] - compute_macd(closes)[1]
    macd_bull_cross = prev_diff < 0 and curr_diff > 0
    macd_bear_cross = prev_diff > 0 and curr_diff < 0

    # BB squeeze
    bb_widths = []
    for i in range(max(0, len(closes)-20), len(closes)):
        subset = closes[max(0,i-20):i+1]
        if len(subset) >= 10:
            bl, bm, bu = compute_bb(subset)
            if bm > 0:
                bb_widths.append((bu - bl) / bm)
    bb_squeeze = bb_width < (sum(bb_widths) / max(len(bb_widths), 1) * 0.75) if bb_widths else False

    # Score
    long_score = 0
    long_signals = []
    short_score = 0
    short_signals = []

    # LONG patterns
    if vol_spike > 2.0 and mom_4h > 1.0 and rsi > 50 and rsi < 78:
        long_score += 25
        long_signals.append(f"vol_spike_breakout(vol={vol_spike:.1f}x,mom4h=+{mom_4h:.1f}%)")
    if macd_hist > 0 and macd_bull_cross and rsi > 45 and rsi < 72:
        long_score += 25
        long_signals.append(f"macd_bullish_cross(RSI={rsi:.0f})")
    if macd_hist > 0 and ema_bull and vol_ratio > 1.3:
        long_score += 20
        long_signals.append(f"ema_macd_aligned(vol={vol_ratio:.1f}x)")
    if up_vol > down_vol * 1.5 and mom_4h > 0.5 and ema9 > ema20:
        long_score += 20
        long_signals.append(f"accumulation({up_vol/max(down_vol,1):.1f}x)")
    if bb_squeeze and closes[-1] > bb_mid and vol_ratio > 1.2:
        long_score += 20
        long_signals.append(f"bb_squeeze_break(w={bb_width:.4f})")
    if mom_4h > 2.0 and mom_12h > 3.0 and vol_ratio > 1.5 and rsi < 80:
        long_score += 15
        long_signals.append(f"momentum(4h=+{mom_4h:.1f}%,12h=+{mom_12h:.1f}%)")
    if ema_bull:
        long_score += 10
        long_signals.append("ema_stack_bull")

    # SHORT patterns
    if vol_spike > 2.0 and mom_4h < -1.0 and rsi < 50 and rsi > 22:
        short_score += 25
        short_signals.append(f"vol_breakdown(vol={vol_spike:.1f}x,mom4h={mom_4h:.1f}%)")
    if macd_hist < 0 and macd_bear_cross and rsi < 55 and rsi > 28:
        short_score += 25
        short_signals.append(f"macd_bearish_cross(RSI={rsi:.0f})")
    if macd_hist < 0 and ema_bear and vol_ratio > 1.3:
        short_score += 20
        short_signals.append(f"ema_macd_bear(vol={vol_ratio:.1f}x)")
    if down_vol > up_vol * 1.5 and mom_4h < -0.5 and ema9 < ema20:
        short_score += 20
        short_signals.append(f"distribution({down_vol/max(up_vol,1):.1f}x)")
    if bb_squeeze and closes[-1] < bb_mid and vol_ratio > 1.2:
        short_score += 20
        short_signals.append(f"bb_squeeze_down(w={bb_width:.4f})")
    if mom_4h < -2.0 and mom_12h < -3.0 and vol_ratio > 1.5 and rsi > 20:
        short_score += 15
        short_signals.append(f"sell_momentum(4h={mom_4h:.1f}%,12h={mom_12h:.1f}%)")
    if ema_bear:
        short_score += 10
        short_signals.append("ema_stack_bear")

    if long_score >= 30 and long_score > short_score:
        return {"symbol": symbol, "direction": "LONG", "score": long_score, "signals": long_signals,
                "price": price, "rsi": rsi, "macd_hist": macd_hist, "vol_ratio": vol_ratio,
                "vol_spike": vol_spike, "ema_bull": ema_bull, "bb_squeeze": bb_squeeze,
                "bb_width": bb_width, "mom_4h": mom_4h, "mom_12h": mom_12h, "mom_24h": mom_24h,
                "atr_pct": atr_pct, "up_vol_ratio": up_vol/max(down_vol,1)}
    elif short_score >= 30:
        return {"symbol": symbol, "direction": "SHORT", "score": short_score, "signals": short_signals,
                "price": price, "rsi": rsi, "macd_hist": macd_hist, "vol_ratio": vol_ratio,
                "vol_spike": vol_spike, "ema_bear": ema_bear, "bb_squeeze": bb_squeeze,
                "bb_width": bb_width, "mom_4h": mom_4h, "mom_12h": mom_12h, "mom_24h": mom_24h,
                "atr_pct": atr_pct, "down_vol_ratio": down_vol/max(up_vol,1)}
    return None


def main():
    print("=" * 70)
    print("  ROCKET SCANNER v2 - Aggressive Mode")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)

    # Load consensus
    consensus = {}
    try:
        cp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "copy_trader_intel", "data", "consensus_active_picks.json")
        with open(cp) as f:
            data = json.load(f)
        for p in data.get("picks", []):
            s = p.get("symbol", "")
            consensus[s] = {"dir": p.get("direction"), "count": p.get("consensus_count", 0),
                           "traders": p.get("agreeing_traders", [])}
        print(f"[+] {len(consensus)} consensus picks loaded")
    except (IOError, json.JSONDecodeError, KeyError) as exc:
        print(f"[!] Consensus load failed: {exc}")

    # Get top symbols
    print("[*] Fetching top 100 USDT pairs...")
    tickers = api_call("/api/v3/ticker/24hr")
    if not tickers:
        print("[!] Failed to get tickers")
        return

    pairs = []
    for t in tickers:
        s = t.get("symbol", "")
        if s.endswith("USDT") and "DOWN" not in s and "UP" not in s:
            try:
                v = float(t.get("quoteVolume", 0))
                p = float(t.get("lastPrice", 0))
                ch = float(t.get("priceChangePercent", 0))
                if v > 1_000_000 and p > 0:
                    pairs.append({"symbol": s, "vol": v, "price": p, "chg24": ch})
            except (ValueError, KeyError):
                pass
    pairs.sort(key=lambda x: x["vol"], reverse=True)
    pairs = pairs[:120]  # Scan more
    print(f"[+] {len(pairs)} pairs to scan")

    # Scan
    candidates = []
    for idx, pi in enumerate(pairs):
        sym = pi["symbol"]
        if idx % 20 == 0:
            print(f"  [{idx}/{len(pairs)}] {sym}...")
        klines = get_klines(sym, "1h", 100)
        if not klines:
            continue
        result = analyze_full(sym, klines)
        if result:
            # Consensus bonus
            if sym in consensus:
                ct = consensus[sym]
                if ct["dir"] == result["direction"]:
                    result["score"] += 15 * ct["count"]
                    result["signals"].append(f"WHALE_CONSENSUS({ct['count']}traders)")
                    result["consensus"] = ct
            candidates.append(result)
        time.sleep(0.08)

    print(f"\n[+] {len(candidates)} candidates found")
    candidates.sort(key=lambda x: x["score"], reverse=True)

    # Backtest top 25 with AGGRESSIVE targets (3% TP, 2% SL)
    print("\n[*] Backtesting with 3% TP / 2% SL targets...")
    validated = []
    for c in candidates[:25]:
        sym = c["symbol"]
        d = c["direction"]
        klines_bt = get_klines(sym, "1h", 720)
        if not klines_bt:
            continue
        wr, avg_ret, n_trades, avg_mfe, avg_mae = backtest_aggressive(sym, d, klines_bt, tp_pct=3.0, sl_pct=2.0)
        c["bt_3pct"] = {"wr": wr, "avg_ret": avg_ret, "trades": n_trades, "avg_mfe": avg_mfe, "avg_mae": avg_mae}
        print(f"  {sym} {d}: WR={wr}% ret={avg_ret}% mfe={avg_mfe}% mae={avg_mae}% ({n_trades}t)")

        # Also test 5% TP for swing plays
        wr5, ret5, n5, mfe5, mae5 = backtest_aggressive(sym, d, klines_bt, tp_pct=5.0, sl_pct=3.0)
        c["bt_5pct"] = {"wr": wr5, "avg_ret": ret5, "trades": n5, "avg_mfe": mfe5, "avg_mae": mae5}

        # Composite: best of the two backtest configs
        best_wr = max(wr, wr5)
        best_ret = max(avg_ret, ret5)
        c["best_wr"] = best_wr
        c["best_ret"] = best_ret
        c["best_config"] = "3%TP/2%SL" if avg_ret >= ret5 else "5%TP/3%SL"

        if best_wr >= 45 and n_trades >= 3:
            validated.append(c)

        time.sleep(0.15)

    if not validated:
        validated = candidates[:5]
        for v in validated:
            v["best_wr"] = 0
            v["best_ret"] = 0
            v["best_config"] = "no_backtest"

    # Final ranking: composite of signal score, WR, and avg return
    for v in validated:
        v["final_score"] = v["score"] + v.get("best_wr", 0) * 0.8 + v.get("best_ret", 0) * 10

    validated.sort(key=lambda x: x["final_score"], reverse=True)
    rockets = validated[:5]

    # Build output
    print("\n" + "=" * 70)
    print("  FINAL 5 ROCKET PICKS")
    print("=" * 70)

    picks = []
    for i, r in enumerate(rockets):
        bt = r.get("bt_3pct", {})
        bt5 = r.get("bt_5pct", {})
        best = r.get("best_config", "3%TP/2%SL")

        if best == "5%TP/3%SL":
            tp_pct, sl_pct = 5.0, 3.0
            use_bt = bt5
        else:
            tp_pct, sl_pct = 3.0, 2.0
            use_bt = bt

        # Adjust TP/SL using actual MFE/MAE data
        avg_mfe = use_bt.get("avg_mfe", tp_pct)
        avg_mae = abs(use_bt.get("avg_mae", sl_pct))
        actual_tp = min(max(avg_mfe * 0.7, tp_pct), 10.0)  # 70% of avg max favorable
        actual_sl = min(max(avg_mae * 0.8, sl_pct), 5.0)    # 80% of avg max adverse

        if r["direction"] == "LONG":
            tp_price = r["price"] * (1 + actual_tp / 100)
            sl_price = r["price"] * (1 - actual_sl / 100)
        else:
            tp_price = r["price"] * (1 - actual_tp / 100)
            sl_price = r["price"] * (1 + actual_sl / 100)

        horizon = "2-8h" if any("momentum" in s or "spike" in s for s in r["signals"]) else "4-24h"

        pick = {
            "rank": i + 1,
            "symbol": r["symbol"],
            "direction": r["direction"],
            "entry_price": r["price"],
            "take_profit": round(tp_price, 8),
            "stop_loss": round(sl_price, 8),
            "tp_pct": round(actual_tp, 2),
            "sl_pct": round(actual_sl, 2),
            "confidence_wr": r.get("best_wr", 0),
            "signal_score": r["score"],
            "final_score": round(r["final_score"], 1),
            "best_backtest_config": best,
            "signals": r["signals"],
            "reason": " | ".join(r["signals"]),
            "time_horizon": horizon,
            "technicals": {
                "rsi": round(r["rsi"], 1),
                "macd_hist": round(r["macd_hist"], 8),
                "vol_ratio": round(r["vol_ratio"], 2),
                "vol_spike_4h": round(r["vol_spike"], 2),
                "mom_4h_pct": round(r["mom_4h"], 2),
                "mom_12h_pct": round(r["mom_12h"], 2),
                "bb_squeeze": r["bb_squeeze"],
            },
            "backtest_3pct": r.get("bt_3pct"),
            "backtest_5pct": r.get("bt_5pct"),
            "copy_trader_consensus": r.get("consensus"),
        }
        picks.append(pick)

        print(f"\n  #{i+1} {r['symbol']} {r['direction']}")
        print(f"      Entry: ${r['price']}")
        print(f"      TP: ${round(tp_price, 8)} (+{actual_tp:.1f}%)")
        print(f"      SL: ${round(sl_price, 8)} (-{actual_sl:.1f}%)")
        print(f"      Backtest WR: {r.get('best_wr',0)}% ({best})")
        print(f"      Avg MFE: {use_bt.get('avg_mfe',0)}% | Avg MAE: {use_bt.get('avg_mae',0)}%")
        print(f"      Signal Score: {r['score']} | Final: {r['final_score']:.0f}")
        print(f"      RSI: {r['rsi']:.0f} | Vol: {r['vol_ratio']:.1f}x | Mom4h: {r['mom_4h']:.1f}%")
        print(f"      Pattern: {' + '.join(r['signals'][:3])}")
        if r.get("consensus"):
            print(f"      WHALE CONSENSUS: {r['consensus']['count']} traders agree!")

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scanner": "rocket_v2_aggressive",
        "scanned": len(pairs),
        "candidates": len(candidates),
        "validated": len(validated),
        "picks": picks,
    }
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "rocket_picks.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\n[+] Saved to {path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
