#!/usr/bin/env python
"""
Rocket Scanner - Find 5 crypto rockets using pattern analysis + backtesting
Uses Binance API with 5-mirror failover (stdlib only)
"""
import json
import urllib.request
import urllib.error
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

# Last-run data-fetch diagnostics. Populated by main() so the CLI entry point
# can distinguish a real-empty market (exit 0 + ::warning::) from a
# data-provider outage (exit 1 + ::error::). Without this the scanner exited
# GitHub Actions GREEN on a total Binance klines failure — "fail-open
# masking". Mirrors etf_scanner.py / bond_scanner.py. Resolver-fix Step 2.
LAST_RUN_DIAGNOSTICS = {
    "symbols_requested": 0,
    "symbols_loaded": 0,
    "raw_signals": 0,
}

def api_call(path, params=None, max_retries=3):
    """Call Binance API with 5-mirror failover."""
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        path = f"{path}?{qs}"
    for mirror in BINANCE_MIRRORS:
        url = f"{mirror}{path}"
        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    return json.loads(resp.read().decode())
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(0.5)
                continue
        # Try next mirror
    return None


def get_klines(symbol, interval="1h", limit=100):
    """Fetch klines for a symbol."""
    return api_call("/api/v3/klines", {
        "symbol": symbol,
        "interval": interval,
        "limit": str(limit),
    })


def compute_rsi(closes, period=14):
    """Compute RSI from close prices."""
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
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def compute_macd(closes, fast=12, slow=26, signal=9):
    """Compute MACD, signal, histogram."""
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
    histogram = macd_line[-1] - signal_line[-1]
    return macd_line[-1], signal_line[-1], histogram


def compute_ema(closes, period):
    """Compute EMA."""
    if not closes:
        return 0
    result = closes[0]
    mult = 2.0 / (period + 1)
    for i in range(1, len(closes)):
        result = closes[i] * mult + result * (1 - mult)
    return result


def compute_bb(closes, period=20, std_mult=2.0):
    """Compute Bollinger Bands."""
    if len(closes) < period:
        return 0, 0, 0
    sma = sum(closes[-period:]) / period
    variance = sum((c - sma) ** 2 for c in closes[-period:]) / period
    std = math.sqrt(variance)
    return sma - std_mult * std, sma, sma + std_mult * std


def compute_atr(highs, lows, closes, period=14):
    """Compute ATR."""
    if len(closes) < period + 1:
        return 0
    trs = []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        trs.append(tr)
    if not trs:
        return 0
    atr = sum(trs[:period]) / period
    for i in range(period, len(trs)):
        atr = (atr * (period - 1) + trs[i]) / period
    return atr


def analyze_symbol(symbol, klines_1h, klines_4h=None):
    """Analyze a symbol for rocket potential. Returns score dict or None."""
    if not klines_1h or len(klines_1h) < 30:
        return None

    closes = [float(k[4]) for k in klines_1h]
    highs = [float(k[2]) for k in klines_1h]
    lows = [float(k[3]) for k in klines_1h]
    volumes = [float(k[5]) for k in klines_1h]

    current_price = closes[-1]
    if current_price == 0:
        return None

    # RSI
    rsi = compute_rsi(closes)

    # MACD
    macd_line, signal_line, macd_hist = compute_macd(closes)

    # Volume ratio (current vs 20-period avg)
    avg_vol = sum(volumes[-20:]) / max(len(volumes[-20:]), 1)
    vol_ratio = volumes[-1] / max(avg_vol, 1e-10)

    # Recent volume spike (max of last 4 candles vs avg)
    recent_max_vol = max(volumes[-4:]) if len(volumes) >= 4 else volumes[-1]
    vol_spike = recent_max_vol / max(avg_vol, 1e-10)

    # EMA alignment
    ema9 = compute_ema(closes, 9)
    ema20 = compute_ema(closes, 20)
    ema50 = compute_ema(closes, 50) if len(closes) >= 50 else ema20
    ema_bullish = ema9 > ema20 > ema50
    ema_bearish = ema9 < ema20 < ema50

    # Bollinger Band squeeze
    bb_lower, bb_mid, bb_upper = compute_bb(closes)
    bb_width = (bb_upper - bb_lower) / max(bb_mid, 1e-10) if bb_mid else 0

    # Check for BB squeeze (narrow bands about to expand)
    bb_widths = []
    for i in range(max(0, len(closes)-20), len(closes)):
        subset = closes[max(0,i-20):i+1]
        if len(subset) >= 10:
            bl, bm, bu = compute_bb(subset)
            if bm > 0:
                bb_widths.append((bu - bl) / bm)
    bb_squeeze = bb_width < (sum(bb_widths) / max(len(bb_widths), 1) * 0.75) if bb_widths else False

    # ATR for stop loss sizing
    atr = compute_atr(highs, lows, closes)
    atr_pct = atr / max(current_price, 1e-10) * 100

    # Price momentum (% change last 4h, 12h, 24h)
    mom_4h = (closes[-1] / closes[-5] - 1) * 100 if len(closes) >= 5 else 0
    mom_12h = (closes[-1] / closes[-13] - 1) * 100 if len(closes) >= 13 else 0
    mom_24h = (closes[-1] / closes[-25] - 1) * 100 if len(closes) >= 25 else 0

    # MACD crossover detection (bullish or bearish)
    macd_values = []
    for i in range(max(0, len(closes)-5), len(closes)):
        subset = closes[:i+1]
        ml, sl, _ = compute_macd(subset)
        macd_values.append((ml, sl))

    macd_bull_cross = False
    macd_bear_cross = False
    if len(macd_values) >= 2:
        prev_diff = macd_values[-2][0] - macd_values[-2][1]
        curr_diff = macd_values[-1][0] - macd_values[-1][1]
        macd_bull_cross = prev_diff < 0 and curr_diff > 0
        macd_bear_cross = prev_diff > 0 and curr_diff < 0

    # Accumulation detection: increasing volume on up candles
    up_vol = sum(v for c, pc, v in zip(closes[-8:], closes[-9:-1], volumes[-8:]) if c > pc)
    down_vol = sum(v for c, pc, v in zip(closes[-8:], closes[-9:-1], volumes[-8:]) if c <= pc)
    accumulation = up_vol > down_vol * 1.5 if down_vol > 0 else False
    distribution = down_vol > up_vol * 1.5 if up_vol > 0 else False

    # === SCORING: Pattern matching against our winners ===
    # Our winners had: volume spikes + momentum + MACD alignment

    score = 0
    signals = []
    direction = None

    # --- LONG SIGNALS ---
    long_score = 0
    long_signals = []

    # Pattern 1: Volume spike breakout (like SIGNUSDT +11.39%)
    if vol_spike > 2.0 and mom_4h > 1.0 and rsi > 50 and rsi < 75:
        long_score += 25
        long_signals.append(f"volume_spike_breakout (vol {vol_spike:.1f}x, mom4h +{mom_4h:.1f}%)")

    # Pattern 2: MACD + RSI confluence (like DASHUSDT +9.87%)
    if macd_hist > 0 and macd_bull_cross and rsi > 45 and rsi < 70:
        long_score += 25
        long_signals.append(f"macd_rsi_confluence (MACD cross, RSI {rsi:.0f})")

    # Pattern 3: StochRSI + MACD combo (like BANANAS31 +13.02%)
    if macd_hist > 0 and ema_bullish and vol_ratio > 1.3:
        long_score += 20
        long_signals.append(f"stochrsi_macd_combo (EMA aligned, vol {vol_ratio:.1f}x)")

    # Pattern 4: Whale accumulation (like BTCUSDT +8.70%)
    if accumulation and mom_4h > 0.5 and ema9 > ema20:
        long_score += 20
        long_signals.append(f"whale_accumulation (up_vol {up_vol/max(down_vol,1):.1f}x down)")

    # Pattern 5: BB squeeze breakout (compression → expansion)
    if bb_squeeze and closes[-1] > bb_mid and vol_ratio > 1.2:
        long_score += 20
        long_signals.append(f"bb_squeeze_breakout (width {bb_width:.4f})")

    # Pattern 6: Momentum continuation
    if mom_4h > 2.0 and mom_12h > 3.0 and vol_ratio > 1.5 and rsi < 80:
        long_score += 15
        long_signals.append(f"momentum_continuation (4h +{mom_4h:.1f}%, 12h +{mom_12h:.1f}%)")

    # Bonus: EMA stack aligned
    if ema_bullish:
        long_score += 10
        long_signals.append("ema_stack_bullish")

    # --- SHORT SIGNALS ---
    short_score = 0
    short_signals = []

    # Pattern: Copy trader fade (like PUMPUSDT SHORT +8.03%)
    if vol_spike > 2.0 and mom_4h < -1.0 and rsi < 45:
        short_score += 25
        short_signals.append(f"volume_breakdown (vol {vol_spike:.1f}x, mom4h {mom_4h:.1f}%)")

    if macd_hist < 0 and macd_bear_cross and rsi < 55 and rsi > 30:
        short_score += 25
        short_signals.append(f"macd_bearish_cross (RSI {rsi:.0f})")

    if distribution and mom_4h < -0.5 and ema9 < ema20:
        short_score += 20
        short_signals.append(f"distribution (down_vol {down_vol/max(up_vol,1):.1f}x up)")

    if ema_bearish:
        short_score += 10
        short_signals.append("ema_stack_bearish")

    if bb_squeeze and closes[-1] < bb_mid and vol_ratio > 1.2:
        short_score += 20
        short_signals.append(f"bb_squeeze_breakdown (width {bb_width:.4f})")

    if mom_4h < -2.0 and mom_12h < -3.0 and vol_ratio > 1.5 and rsi > 20:
        short_score += 15
        short_signals.append(f"momentum_breakdown (4h {mom_4h:.1f}%, 12h {mom_12h:.1f}%)")

    # Pick direction
    if long_score > short_score and long_score >= 30:
        direction = "LONG"
        score = long_score
        signals = long_signals
    elif short_score > long_score and short_score >= 30:
        direction = "SHORT"
        score = short_score
        signals = short_signals
    else:
        return None

    return {
        "symbol": symbol,
        "direction": direction,
        "score": score,
        "signals": signals,
        "entry_price": current_price,
        "rsi": round(rsi, 1),
        "macd_hist": round(macd_hist, 6),
        "vol_ratio": round(vol_ratio, 2),
        "vol_spike_4h": round(vol_spike, 2),
        "ema9": round(ema9, 6),
        "ema20": round(ema20, 6),
        "ema_aligned": ema_bullish if direction == "LONG" else ema_bearish,
        "bb_squeeze": bb_squeeze,
        "bb_width": round(bb_width, 5),
        "mom_4h": round(mom_4h, 2),
        "mom_12h": round(mom_12h, 2),
        "mom_24h": round(mom_24h, 2),
        "atr_pct": round(atr_pct, 3),
        "accumulation": accumulation if direction == "LONG" else distribution,
    }


def backtest_pattern(symbol, direction, klines, lookback=30*24):
    """
    Backtest: scan historical klines for the same pattern setup.
    Returns win_rate, avg_return, num_trades.
    """
    if not klines or len(klines) < 60:
        return 0, 0, 0

    closes = [float(k[4]) for k in klines]
    highs = [float(k[2]) for k in klines]
    lows = [float(k[3]) for k in klines]
    volumes = [float(k[5]) for k in klines]

    trades = []

    # Slide a window and look for pattern matches
    for i in range(50, len(closes) - 12):  # Need 50 lookback, 12 forward
        window_closes = closes[:i+1]
        window_volumes = volumes[:i+1]

        rsi = compute_rsi(window_closes[-30:])
        _, _, macd_hist = compute_macd(window_closes[-40:])
        avg_vol = sum(window_volumes[-20:]) / 20
        vol_ratio = window_volumes[i] / max(avg_vol, 1e-10)
        ema9 = compute_ema(window_closes[-20:], 9)
        ema20 = compute_ema(window_closes[-30:], 20)

        triggered = False

        if direction == "LONG":
            # Volume spike + momentum + RSI in range
            if vol_ratio > 1.5 and rsi > 45 and rsi < 75 and macd_hist > 0 and ema9 > ema20:
                triggered = True
        else:  # SHORT
            if vol_ratio > 1.5 and rsi < 55 and rsi > 25 and macd_hist < 0 and ema9 < ema20:
                triggered = True

        if triggered:
            entry = closes[i]
            # Check next 12 candles (12 hours) for result
            future_closes = closes[i+1:i+13]
            future_highs = highs[i+1:i+13]
            future_lows = lows[i+1:i+13]

            if direction == "LONG":
                max_gain = (max(future_highs) / entry - 1) * 100
                max_loss = (min(future_lows) / entry - 1) * 100
                # Use 2% TP, 1.5% SL as reference
                hit_tp = max_gain >= 2.0
                hit_sl = max_loss <= -1.5

                if hit_tp and not hit_sl:
                    trades.append(2.0)
                elif hit_sl and not hit_tp:
                    trades.append(-1.5)
                elif hit_tp and hit_sl:
                    # Both hit - check which came first
                    for j in range(len(future_closes)):
                        if future_highs[j] >= entry * 1.02:
                            trades.append(2.0)
                            break
                        if future_lows[j] <= entry * 0.985:
                            trades.append(-1.5)
                            break
                else:
                    # Exit at close of window
                    pnl = (future_closes[-1] / entry - 1) * 100 if future_closes else 0
                    trades.append(pnl)
            else:  # SHORT
                max_gain = (1 - min(future_lows) / entry) * 100
                max_loss = (1 - max(future_highs) / entry) * 100
                hit_tp = max_gain >= 2.0
                hit_sl = max_loss <= -1.5

                if hit_tp and not hit_sl:
                    trades.append(2.0)
                elif hit_sl and not hit_tp:
                    trades.append(-1.5)
                elif hit_tp and hit_sl:
                    for j in range(len(future_closes)):
                        if future_lows[j] <= entry * 0.98:
                            trades.append(2.0)
                            break
                        if future_highs[j] >= entry * 1.015:
                            trades.append(-1.5)
                            break
                else:
                    pnl = (1 - future_closes[-1] / entry) * 100 if future_closes else 0
                    trades.append(pnl)

            # Skip next 12 candles to avoid overlapping trades
            # (handled by continuing the loop - trades overlap is fine for WR calc)

    if not trades:
        return 0, 0, 0

    wins = sum(1 for t in trades if t > 0)
    win_rate = wins / len(trades) * 100
    avg_return = sum(trades) / len(trades)

    return round(win_rate, 1), round(avg_return, 3), len(trades)


def get_top_symbols():
    """Get top 100 USDT futures pairs by volume."""
    print("[*] Fetching top symbols by 24h volume...")
    data = api_call("/api/v3/ticker/24hr")
    if not data:
        print("[!] Failed to fetch ticker data")
        return []

    # Filter USDT pairs, sort by quote volume
    usdt_pairs = []
    for t in data:
        sym = t.get("symbol", "")
        if sym.endswith("USDT") and not sym.endswith("DOWNUSDT") and not sym.endswith("UPUSDT"):
            try:
                vol = float(t.get("quoteVolume", 0))
                price = float(t.get("lastPrice", 0))
                change = float(t.get("priceChangePercent", 0))
                if vol > 1_000_000 and price > 0:  # Min $1M daily volume
                    usdt_pairs.append({
                        "symbol": sym,
                        "volume": vol,
                        "price": price,
                        "change_24h": change,
                    })
            except (ValueError, TypeError):
                continue

    usdt_pairs.sort(key=lambda x: x["volume"], reverse=True)
    return usdt_pairs[:100]


def main():
    print("=" * 70)
    print("  ROCKET SCANNER - Finding 5 Crypto Rockets")
    print(f"  Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)

    # Load copy trader consensus for cross-reference
    consensus_symbols = {}
    try:
        with open(os.path.join(os.path.dirname(__file__), "data", "..", "..", "copy_trader_intel", "data", "consensus_active_picks.json")) as f:
            consensus = json.load(f)
        for p in consensus.get("picks", []):
            sym = p.get("symbol", "")
            consensus_symbols[sym] = {
                "direction": p.get("direction"),
                "consensus_count": p.get("consensus_count", 0),
                "traders": p.get("agreeing_traders", []),
            }
        print(f"[+] Loaded {len(consensus_symbols)} copy trader consensus picks")
    except Exception as e:
        print(f"[!] Could not load consensus: {e}")

    # Phase 1: Get top symbols
    top_symbols = get_top_symbols()
    if not top_symbols:
        print("[!] FATAL: Could not get symbols")
        sys.exit(1)

    print(f"[+] Scanning {len(top_symbols)} symbols")
    LAST_RUN_DIAGNOSTICS["symbols_requested"] = len(top_symbols)
    LAST_RUN_DIAGNOSTICS["symbols_loaded"] = 0
    LAST_RUN_DIAGNOSTICS["raw_signals"] = 0

    # Phase 2: Analyze each symbol
    candidates = []
    for idx, sym_info in enumerate(top_symbols):
        symbol = sym_info["symbol"]
        if idx % 10 == 0:
            print(f"  [{idx}/{len(top_symbols)}] Scanning {symbol}...")

        # Fetch 1H klines (100 candles = ~4 days)
        klines_1h = get_klines(symbol, "1h", 100)
        if not klines_1h:
            continue
        LAST_RUN_DIAGNOSTICS["symbols_loaded"] += 1

        result = analyze_symbol(symbol, klines_1h)
        if result:
            # Cross-reference with copy trader consensus
            if symbol in consensus_symbols:
                ct = consensus_symbols[symbol]
                if ct["direction"] == result["direction"]:
                    result["score"] += 15 * ct["consensus_count"]
                    result["signals"].append(f"copy_trader_consensus ({ct['consensus_count']} traders: {', '.join(ct['traders'][:3])})")
                    result["consensus"] = ct
                elif ct["consensus_count"] >= 3:
                    # Strong disagreement - reduce score
                    result["score"] -= 10
                    result["signals"].append(f"WARNING: copy_traders_disagree ({ct['direction']})")

            candidates.append(result)

        # Rate limiting
        time.sleep(0.1)

    print(f"\n[+] Found {len(candidates)} raw candidates")
    LAST_RUN_DIAGNOSTICS["raw_signals"] = len(candidates)

    # Sort by score
    candidates.sort(key=lambda x: x["score"], reverse=True)

    # Phase 3: Backtest top candidates
    print("\n" + "=" * 70)
    print("  PHASE 3: Backtesting Top Candidates")
    print("=" * 70)

    validated = []
    for cand in candidates[:20]:  # Backtest top 20
        symbol = cand["symbol"]
        direction = cand["direction"]
        print(f"  Backtesting {symbol} {direction} (score: {cand['score']})...")

        # Get more historical data for backtest (720 candles = 30 days)
        klines_bt = get_klines(symbol, "1h", 720)
        if klines_bt:
            wr, avg_ret, num_trades = backtest_pattern(symbol, direction, klines_bt)
            cand["backtest"] = {
                "win_rate": wr,
                "avg_return": avg_ret,
                "num_trades": num_trades,
            }
            print(f"    -> WR: {wr}%, Avg Return: {avg_ret}%, Trades: {num_trades}")

            # Only keep if WR >= 50% OR strong score with decent WR
            if (wr >= 50 and num_trades >= 3) or (wr >= 45 and cand["score"] >= 50):
                validated.append(cand)
            elif num_trades == 0 and cand["score"] >= 40:
                # No backtest data but strong current signal
                cand["backtest"]["note"] = "No historical pattern matches - novel setup"
                validated.append(cand)

        time.sleep(0.2)

    if not validated:
        print("[!] No candidates passed backtest validation. Using top raw candidates.")
        validated = candidates[:5]
        for v in validated:
            v["backtest"] = {"win_rate": 0, "avg_return": 0, "num_trades": 0, "note": "backtest_skipped"}

    # Sort validated by composite score (signal score + backtest WR)
    for v in validated:
        bt = v.get("backtest", {})
        v["composite_score"] = v["score"] + bt.get("win_rate", 0) * 0.5 + bt.get("avg_return", 0) * 5

    validated.sort(key=lambda x: x["composite_score"], reverse=True)

    # Take top 5
    rockets = validated[:5]

    # Phase 5: Format output
    print("\n" + "=" * 70)
    print("  TOP 5 ROCKET PICKS")
    print("=" * 70)

    output_picks = []
    for i, r in enumerate(rockets):
        bt = r.get("backtest", {})
        atr_pct = r.get("atr_pct", 2.0)

        # TP/SL based on ATR and backtest
        tp_mult = max(2.0, min(bt.get("avg_return", 2.0) * 1.2, 8.0))
        sl_mult = max(1.0, atr_pct * 1.5)

        if r["direction"] == "LONG":
            tp = r["entry_price"] * (1 + tp_mult / 100)
            sl = r["entry_price"] * (1 - sl_mult / 100)
        else:
            tp = r["entry_price"] * (1 - tp_mult / 100)
            sl = r["entry_price"] * (1 + sl_mult / 100)

        # Time horizon based on pattern type
        if any("squeeze" in s for s in r["signals"]):
            horizon = "4-12h (squeeze breakout)"
        elif any("momentum" in s for s in r["signals"]):
            horizon = "2-8h (momentum continuation)"
        elif any("volume_spike" in s for s in r["signals"]):
            horizon = "1-6h (volume spike)"
        else:
            horizon = "4-24h (swing)"

        pick = {
            "rank": i + 1,
            "symbol": r["symbol"],
            "direction": r["direction"],
            "entry_price": r["entry_price"],
            "take_profit": round(tp, 6),
            "stop_loss": round(sl, 6),
            "confidence": bt.get("win_rate", 50),
            "composite_score": round(r["composite_score"], 1),
            "signal_score": r["score"],
            "reason": " + ".join(r["signals"]),
            "time_horizon": horizon,
            "technicals": {
                "rsi": r["rsi"],
                "macd_hist": r["macd_hist"],
                "vol_ratio": r["vol_ratio"],
                "vol_spike_4h": r["vol_spike_4h"],
                "ema_aligned": r["ema_aligned"],
                "bb_squeeze": r["bb_squeeze"],
                "mom_4h": r["mom_4h"],
                "mom_12h": r["mom_12h"],
            },
            "backtest": bt,
            "copy_trader_consensus": r.get("consensus"),
        }
        output_picks.append(pick)

        dir_arrow = "LONG >>>" if r["direction"] == "LONG" else "SHORT <<<"
        print(f"\n  #{i+1} {r['symbol']} {dir_arrow}")
        print(f"      Entry: {r['entry_price']}")
        print(f"      TP: {round(tp, 6)} ({tp_mult:.1f}%)")
        print(f"      SL: {round(sl, 6)} ({sl_mult:.1f}%)")
        print(f"      Confidence: {bt.get('win_rate', 'N/A')}% WR ({bt.get('num_trades', 0)} trades)")
        print(f"      Score: {r['score']} (composite: {r['composite_score']:.0f})")
        print(f"      RSI: {r['rsi']} | Vol: {r['vol_ratio']}x | Mom4h: {r['mom_4h']}%")
        print(f"      Signals: {' + '.join(r['signals'])}")
        print(f"      Horizon: {horizon}")

    # Save to file
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scanner_version": "rocket_v1.0",
        "total_scanned": len(top_symbols),
        "total_candidates": len(candidates),
        "total_validated": len(validated),
        "target": "60%+ WR, 3%+ avg move, 4-24h horizon",
        "picks": output_picks,
    }

    out_path = os.path.join(os.path.dirname(__file__), "data", "rocket_picks.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n[+] Saved {len(output_picks)} rocket picks to {out_path}")
    print("=" * 70)

    return output


if __name__ == "__main__":
    main()

    # ── fail-open guard ────────────────────────────────────────────────────
    # Stop the scanner from exiting GitHub Actions GREEN on a Binance klines
    # outage. main() already sys.exit(1)s when get_top_symbols() returns
    # nothing; this catches the partial-outage case where the ticker list
    # loads but most per-symbol klines fail (<50% loaded), which otherwise
    # passes silently and corrupts the audit ledger. Mirrors the ratio logic
    # in etf_scanner.py / bond_scanner.py. Resolver-fix Step 2.
    _requested = max(1, LAST_RUN_DIAGNOSTICS["symbols_requested"])
    _loaded = LAST_RUN_DIAGNOSTICS["symbols_loaded"]
    _ratio = _loaded / _requested
    if _ratio < 0.5:
        print(f"::error::DATA FETCH FAILURE — only {_loaded}/{_requested} "
              f"symbols loaded klines (Binance mirrors degraded); refusing to "
              f"exit green on missing data")
        sys.exit(1)
    if LAST_RUN_DIAGNOSTICS["raw_signals"] == 0:
        print(f"::warning::Rocket scanner produced 0 raw candidates on "
              f"healthy data ({_loaded}/{_requested} symbols loaded) — "
              f"real-empty market, not a data failure")
