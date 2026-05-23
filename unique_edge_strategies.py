#!/usr/bin/env python3
"""
UNIQUE EDGE STRATEGIES - Proprietary Trading Algorithms
=========================================================
5 unique strategies exploiting market microstructure edges.
All backtests use REAL data from Binance/KuCoin/OKX APIs.
"""

import json, os, time, statistics
from datetime import datetime
from urllib.request import urlopen, Request

BINANCE_MIRRORS = [
    "https://data-api.binance.vision",
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]
KUCOIN_BASE = "https://api.kucoin.com"
OKX_BASE = "https://www.okx.com"
COMMISSION = 0.001
BARS = 1500

USER_PICKS = [
    ("BINANCE", "SHIBUSDT"), ("BINANCE", "NOMUSDT"), ("KUCOIN", "PTBUSDT"),
    ("BINANCE", "DOGEUSDT"), ("BINANCE", "CHZUSDT"), ("BINANCE", "TRXUSDT"),
    ("BINANCE", "ADAUSDT"), ("OKX", "ZBCNUSDT"), ("BINANCE", "ZKUSDT"),
    ("BINANCE", "WUSDT"), ("BINANCE", "ONTUSDT"), ("KUCOIN", "QUSDT"),
    ("BINANCE", "FETUSDT"), ("BINANCE", "XRPUSDT"), ("BINANCE", "SEIUSDT"),
    ("BINANCE", "HBARUSDT"), ("BINANCE", "ARBUSDT"), ("BINANCE", "POLUSDT"),
    ("BINANCE", "STRKUSDT"), ("BINANCE", "SUIUSDT"), ("BINANCE", "OPUSDT"),
    ("BINANCE", "DYDXUSDT"), ("BINANCE", "APEUSDT"), ("BINANCE", "ALGOUSDT"),
    ("BINANCE", "TIAUSDT"), ("BINANCE", "DOTUSDT"), ("BINANCE", "JTOUSDT"),
    ("OKX", "TONUSDT"), ("BINANCE", "SOLUSDT"), ("BINANCE", "LINKUSDT"),
    ("KUCOIN", "SIRENUSDT"), ("BINANCE", "AVAXUSDT"), ("BINANCE", "ZROUSDT"),
    ("BINANCE", "INJUSDT"), ("BYBIT", "VVVUSDT"), ("BINANCE", "ETCUSDT"),
    ("BINANCE", "LTCUSDT"), ("MEXC", "RIVERUSDT"), ("BINANCE", "ETHUSDT"),
    ("OKX", "GLMUSDT"), ("BINANCE", "BNBUSDT"), ("BINANCE", "AAVEUSDT"),
    ("BINANCE", "BTCUSDT"), ("POLONIEX", "WARUSDT"), ("HTX", "ULTIMAUSDT"),
]

def fetch_binance(symbol, interval, limit=BARS):
    for base in BINANCE_MIRRORS:
        url = f"{base}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        try:
            req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
            candles = []
            for k in data:
                candles.append({"timestamp": int(k[0]), "open": float(k[1]), "high": float(k[2]),
                               "low": float(k[3]), "close": float(k[4]), "volume": float(k[5])})
            return candles
        except: continue
    return None

def fetch_kucoin(symbol, interval, limit=BARS):
    tf_map = {"15m": "15min", "1h": "1hour", "4h": "4hour"}
    kc_sym = symbol.replace("USDT", "-USDT")
    url = f"{KUCOIN_BASE}/api/v1/market/candles?type={tf_map.get(interval,'1hour')}&symbol={kc_sym}"
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        raw = json.loads(urlopen(req, timeout=15).read().decode())
        if raw.get("code") == "200000" and raw.get("data"):
            return [{"timestamp": int(k[0]), "open": float(k[1]), "close": float(k[2]),
                    "high": float(k[3]), "low": float(k[4]), "volume": float(k[5])} for k in reversed(raw["data"][:limit])]
    except: pass
    return None

def fetch_okx(symbol, interval, limit=BARS):
    tf_map = {"15m": "15m", "1h": "1H", "4h": "4H"}
    okx_sym = symbol.replace("USDT", "-USDT")
    url = f"{OKX_BASE}/api/v5/market/candles?instId={okx_sym}&bar={tf_map.get(interval,'1H')}&limit={limit}"
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        raw = json.loads(urlopen(req, timeout=15).read().decode())
        if raw.get("code") == "0" and raw.get("data"):
            return [{"timestamp": int(k[0]), "open": float(k[1]), "high": float(k[2]),
                    "low": float(k[3]), "close": float(k[4]), "volume": float(k[5])} for k in raw["data"]][::-1]
    except: pass
    return None

def fetch_real_data(exchange, symbol, interval):
    exchange = exchange.upper()
    if exchange == "BINANCE":
        data = fetch_binance(symbol, interval)
        if data: return data
        data = fetch_kucoin(symbol, interval)
        if data: return data
        return fetch_okx(symbol, interval)
    elif exchange == "KUCOIN":
        data = fetch_kucoin(symbol, interval)
        if data: return data
        return fetch_binance(symbol, interval)
    elif exchange == "OKX":
        data = fetch_okx(symbol, interval)
        if data: return data
        return fetch_binance(symbol, interval)
    elif exchange in ["BYBIT", "MEXC", "POLONIEX", "HTX"]:
        return fetch_binance(symbol, interval)
    return None

def calc_rsi(closes, period=14):
    rsi = [None] * len(closes)
    if len(closes) < period + 1: return rsi
    gains = losses = 0.0
    for i in range(1, period + 1):
        delta = closes[i] - closes[i-1]
        if delta > 0: gains += delta
        else: losses -= delta
    avg_gain, avg_loss = gains / period, losses / period
    rsi[period] = 100.0 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss)
    for i in range(period + 1, len(closes)):
        delta = closes[i] - closes[i-1]
        g, l = (delta if delta > 0 else 0), (-delta if delta < 0 else 0)
        avg_gain = (avg_gain * (period - 1) + g) / period
        avg_loss = (avg_loss * (period - 1) + l) / period
        rsi[i] = 100.0 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss)
    return rsi

def calc_ema(values, period):
    ema = [None] * len(values)
    k = 2 / (period + 1)
    first = next((i for i, v in enumerate(values) if v is not None), None)
    if first is None: return ema
    ema[first] = values[first]
    for i in range(first + 1, len(values)):
        if values[i] is not None:
            ema[i] = values[i] * k + ema[i-1] * (1 - k) if ema[i-1] is not None else values[i]
    return ema

def calc_sma(values, period):
    sma = [None] * len(values)
    for i in range(period - 1, len(values)):
        window = values[i - period + 1:i + 1]
        if all(v is not None for v in window): sma[i] = sum(window) / period
    return sma

def calc_atr(candles, period=14):
    atr = [None] * len(candles)
    if len(candles) < period + 1: return atr
    trs = [max(candles[i]["high"] - candles[i]["low"], abs(candles[i]["high"] - candles[i-1]["close"]),
               abs(candles[i]["low"] - candles[i-1]["close"])) for i in range(1, len(candles))]
    if len(trs) < period: return atr
    avg = sum(trs[:period]) / period
    atr[period] = avg
    for i in range(period, len(trs)):
        avg = (avg * (period - 1) + trs[i]) / period
        atr[i + 1] = avg
    return atr

def calc_vwap(candles):
    vwap, cum_tp_vol, cum_vol = [None] * len(candles), 0.0, 0.0
    for i, c in enumerate(candles):
        tp, vol = (c["high"] + c["low"] + c["close"]) / 3, c["volume"]
        cum_tp_vol += tp * vol
        cum_vol += vol
        if cum_vol > 0: vwap[i] = cum_tp_vol / cum_vol
    return vwap

def calc_bollinger(closes, period=20, mult=2.0):
    upper = middle = lower = [None] * len(closes)
    for i in range(period - 1, len(closes)):
        window = closes[i - period + 1:i + 1]
        if all(v is not None for v in window):
            mid, std = sum(window) / period, statistics.stdev(window)
            middle[i], upper[i], lower[i] = mid, mid + mult * std, mid - mult * std
    return upper, middle, lower

def strategy_liquidity_sweep(candles):
    signals = []
    if len(candles) < 50: return signals
    closes = [c["close"] for c in candles]
    highs, lows, volumes = [c["high"] for c in candles], [c["low"] for c in candles], [c["volume"] for c in candles]
    atr, rsi = calc_atr(candles, 14), calc_rsi(closes, 14)
    vol_sma20 = calc_sma(volumes, 20)
    for i in range(25, len(candles) - 1):
        if atr[i] is None or rsi[i] is None or vol_sma20[i] is None: continue
        lookback, recent_lows, recent_highs = 10, lows[i-lookback:i], highs[i-lookback:i]
        swing_low, swing_high = min(recent_lows), max(recent_highs)
        if lows[i-1] < swing_low * 0.998 and closes[i-1] > swing_low:
            if closes[i] > closes[i-1] and volumes[i] > vol_sma20[i] * 1.2 and 30 < rsi[i] < 55:
                entry, sl = closes[i], swing_low - atr[i] * 0.5
                signals.append({"type": "LONG", "index": i, "entry": entry, "sl": sl, "tp": entry + (entry - sl) * 2.0, "rr": 2.0,
                               "reason": f"Liquidity sweep below {swing_low:.4f}, vol {volumes[i]/vol_sma20[i]:.1f}x"})
        elif highs[i-1] > swing_high * 1.002 and closes[i-1] < swing_high:
            if closes[i] < closes[i-1] and volumes[i] > vol_sma20[i] * 1.2 and 45 < rsi[i] < 70:
                entry, sl = closes[i], swing_high + atr[i] * 0.5
                signals.append({"type": "SHORT", "index": i, "entry": entry, "sl": sl, "tp": entry - (sl - entry) * 2.0, "rr": 2.0,
                               "reason": f"Liquidity sweep above {swing_high:.4f}, vol {volumes[i]/vol_sma20[i]:.1f}x"})
    return signals

def strategy_order_block(candles):
    signals = []
    if len(candles) < 50: return signals
    closes = [c["close"] for c in candles]
    highs, lows, opens, volumes = [c["high"] for c in candles], [c["low"] for c in candles], [c["open"] for c in candles], [c["volume"] for c in candles]
    atr, rsi, ema50 = calc_atr(candles, 14), calc_rsi(closes, 14), calc_ema(closes, 50)
    order_blocks = []
    for i in range(5, len(candles) - 5):
        if atr[i] is None: continue
        candle_range, body = highs[i] - lows[i], abs(closes[i] - opens[i])
        if closes[i] > opens[i] and body > candle_range * 0.6 and closes[i+1] > highs[i] and closes[i+2] > closes[i+1]:
            strength = volumes[i] / statistics.mean(volumes[max(0,i-10):i]) if i > 10 else 1.0
            order_blocks.append((i, highs[i], lows[i], "BULLISH", strength))
        elif closes[i] < opens[i] and body > candle_range * 0.6 and closes[i+1] < lows[i] and closes[i+2] < closes[i+1]:
            strength = volumes[i] / statistics.mean(volumes[max(0,i-10):i]) if i > 10 else 1.0
            order_blocks.append((i, highs[i], lows[i], "BEARISH", strength))
    order_blocks = sorted(order_blocks, key=lambda x: x[4], reverse=True)[:10]
    for i in range(20, len(candles) - 1):
        if rsi[i] is None or ema50[i] is None: continue
        for block_idx, block_high, block_low, block_type, strength in order_blocks:
            if block_idx > i - 5 or block_idx < i - 100: continue
            if block_type == "BULLISH" and block_low <= lows[i] <= block_high and closes[i] > opens[i] and rsi[i] > 40 and closes[i] > ema50[i]:
                entry, sl = closes[i], block_low - atr[i] * 0.3
                signals.append({"type": "LONG", "index": i, "entry": entry, "sl": sl, "tp": entry + (entry - sl) * 1.5, "rr": 1.5,
                               "reason": f"Bullish OB retest @ {block_low:.4f}-{block_high:.4f}"})
            elif block_type == "BEARISH" and block_low <= highs[i] <= block_high and closes[i] < opens[i] and rsi[i] < 60 and closes[i] < ema50[i]:
                entry, sl = closes[i], block_high + atr[i] * 0.3
                signals.append({"type": "SHORT", "index": i, "entry": entry, "sl": sl, "tp": entry - (sl - entry) * 1.5, "rr": 1.5,
                               "reason": f"Bearish OB retest @ {block_low:.4f}-{block_high:.4f}"})
    return signals

def strategy_vwap_deviation(candles):
    signals = []
    if len(candles) < 50: return signals
    closes = [c["close"] for c in candles]
    highs, lows, volumes = [c["high"] for c in candles], [c["low"] for c in candles], [c["volume"] for c in candles]
    vwap, rsi, atr = calc_vwap(candles), calc_rsi(closes, 14), calc_atr(candles, 14)
    vwap_stds = []
    for i in range(20, len(candles)):
        if vwap[i] is not None:
            deviations = [(closes[j] - vwap[j]) / vwap[j] for j in range(i-20, i+1) if vwap[j] and vwap[j] > 0]
            vwap_stds.append(statistics.stdev(deviations) if len(deviations) > 1 else 0)
        else: vwap_stds.append(0)
    for i in range(20, len(candles) - 1):
        if vwap[i] is None or rsi[i] is None or atr[i] is None: continue
        deviation = (closes[i] - vwap[i]) / vwap[i]
        avg_vol = statistics.mean(volumes[max(0,i-20):i])
        vol_ratio = volumes[i] / avg_vol if avg_vol > 0 else 1.0
        std = vwap_stds[i-20] if i >= 20 else 0.01
        if deviation < -0.015 and deviation < -2.5 * std and rsi[i] < 35 and vol_ratio > 1.3:
            entry, sl, tp = closes[i], lows[i] - atr[i] * 0.5, vwap[i]
            if tp > entry:
                rr = (tp - entry) / (entry - sl) if (entry - sl) > 0 else 1.0
                signals.append({"type": "LONG", "index": i, "entry": entry, "sl": sl, "tp": tp, "rr": rr,
                               "reason": f"VWAP dev -{abs(deviation)*100:.1f}%, RSI {rsi[i]:.0f}, vol {vol_ratio:.1f}x"})
        elif deviation > 0.015 and deviation > 2.5 * std and rsi[i] > 65 and vol_ratio > 1.3:
            entry, sl, tp = closes[i], highs[i] + atr[i] * 0.5, vwap[i]
            if tp < entry:
                rr = (entry - tp) / (sl - entry) if (sl - entry) > 0 else 1.0
                signals.append({"type": "SHORT", "index": i, "entry": entry, "sl": sl, "tp": tp, "rr": rr,
                               "reason": f"VWAP dev +{deviation*100:.1f}%, RSI {rsi[i]:.0f}, vol {vol_ratio:.1f}x"})
    return signals

def strategy_volatility_regime(candles):
    signals = []
    if len(candles) < 50: return signals
    closes = [c["close"] for c in candles]
    highs, lows, volumes = [c["high"] for c in candles], [c["low"] for c in candles], [c["volume"] for c in candles]
    bb_upper, bb_middle, bb_lower = calc_bollinger(closes, 20, 2.0)
    rsi, atr, ema50 = calc_rsi(closes, 14), calc_atr(candles, 14), calc_ema(closes, 50)
    squeeze_active, squeeze_bars = False, 0
    for i in range(25, len(candles) - 1):
        if bb_upper[i] is None or bb_lower[i] is None or rsi[i] is None: continue
        bb_width = (bb_upper[i] - bb_lower[i]) / bb_middle[i] if bb_middle[i] else 0
        recent_widths = [(bb_upper[j] - bb_lower[j]) / bb_middle[j] for j in range(max(0, i-20), i) if bb_middle[j] and bb_middle[j] > 0]
        avg_width = statistics.mean(recent_widths) if recent_widths else bb_width
        is_squeezed = bb_width < avg_width * 0.5 if avg_width > 0 else False
        if is_squeezed:
            squeeze_active, squeeze_bars = True, squeeze_bars + 1
        elif squeeze_active and squeeze_bars >= 5:
            squeeze_active = False
            avg_vol = statistics.mean(volumes[max(0,i-20):i])
            vol_ratio = volumes[i] / avg_vol if avg_vol > 0 else 1.0
            if closes[i] > bb_upper[i] and closes[i-1] <= bb_upper[i-1] and vol_ratio > 1.5 and rsi[i] > 50 and ema50[i] and closes[i] > ema50[i]:
                entry, sl = closes[i], bb_middle[i]
                signals.append({"type": "LONG", "index": i, "entry": entry, "sl": sl, "tp": entry + (entry - sl) * 2.0, "rr": 2.0,
                               "reason": f"BB squeeze release LONG, vol {vol_ratio:.1f}x, {squeeze_bars} bars"})
            elif closes[i] < bb_lower[i] and closes[i-1] >= bb_lower[i-1] and vol_ratio > 1.5 and rsi[i] < 50 and ema50[i] and closes[i] < ema50[i]:
                entry, sl = closes[i], bb_middle[i]
                signals.append({"type": "SHORT", "index": i, "entry": entry, "sl": sl, "tp": entry - (sl - entry) * 2.0, "rr": 2.0,
                               "reason": f"BB squeeze release SHORT, vol {vol_ratio:.1f}x, {squeeze_bars} bars"})
            squeeze_bars = 0
        else:
            squeeze_active, squeeze_bars = False, 0
    return signals

def strategy_smart_money_confluence(candles_15m, candles_1h, candles_4h):
    signals = []
    if not candles_15m or len(candles_15m) < 50: return signals
    candles = candles_1h
    closes = [c["close"] for c in candles]
    highs, lows, volumes = [c["high"] for c in candles], [c["low"] for c in candles], [c["volume"] for c in candles]
    ema9, ema21, rsi, atr = calc_ema(closes, 9), calc_ema(closes, 21), calc_rsi(closes, 14), calc_atr(candles, 14)
    for i in range(30, len(candles) - 1):
        if ema9[i] is None or ema21[i] is None or rsi[i] is None: continue
        trend_1h_bull = ema9[i] > ema21[i] and closes[i] > ema9[i]
        trend_1h_bear = ema9[i] < ema21[i] and closes[i] < ema9[i]
        alignment_score, reasons = 0, []
        if trend_1h_bull: alignment_score, reasons = alignment_score + 25, reasons + ["1h_trend_up"]
        elif trend_1h_bear: alignment_score, reasons = alignment_score + 25, reasons + ["1h_trend_down"]
        if rsi[i] > 50 and trend_1h_bull: alignment_score, reasons = alignment_score + 25, reasons + ["mom_bull"]
        elif rsi[i] < 50 and trend_1h_bear: alignment_score, reasons = alignment_score + 25, reasons + ["mom_bear"]
        avg_vol = statistics.mean(volumes[max(0,i-20):i]) if i >= 20 else volumes[i]
        if volumes[i] > avg_vol * 1.2: alignment_score, reasons = alignment_score + 25, reasons + ["vol_confirm"]
        if alignment_score >= 75 and atr[i] is not None:
            if trend_1h_bull and rsi[i] < 70:
                entry = closes[i]
                sl = entry - atr[i] * 1.5
                signals.append({"type": "LONG", "index": i, "entry": entry, "sl": sl, "tp": entry + atr[i] * 3.0, "rr": 2.0,
                               "reason": f"SMC {alignment_score}/100: {', '.join(reasons)}"})
            elif trend_1h_bear and rsi[i] > 30:
                entry = closes[i]
                sl = entry + atr[i] * 1.5
                signals.append({"type": "SHORT", "index": i, "entry": entry, "sl": sl, "tp": entry - atr[i] * 3.0, "rr": 2.0,
                               "reason": f"SMC {alignment_score}/100: {', '.join(reasons)}"})
    return signals

def backtest_strategy(signals, candles, strategy_name, symbol, timeframe):
    trades = []
    for sig in signals:
        idx, entry_price, sl_price, tp_price, direction = sig["index"], sig["entry"], sig["sl"], sig["tp"], sig["type"]
        entry_time = candles[idx]["timestamp"]
        exit_price = exit_time = exit_reason = None
        for j in range(idx + 1, len(candles)):
            high, low = candles[j]["high"], candles[j]["low"]
            if direction == "LONG":
                if low <= sl_price: exit_price, exit_time, exit_reason = sl_price, candles[j]["timestamp"], "STOP_LOSS"; break
                elif high >= tp_price: exit_price, exit_time, exit_reason = tp_price, candles[j]["timestamp"], "TAKE_PROFIT"; break
            elif direction == "SHORT":
                if high >= sl_price: exit_price, exit_time, exit_reason = sl_price, candles[j]["timestamp"], "STOP_LOSS"; break
                elif low <= tp_price: exit_price, exit_time, exit_reason = tp_price, candles[j]["timestamp"], "TAKE_PROFIT"; break
        if exit_price is None and idx < len(candles) - 1:
            exit_price, exit_time, exit_reason = candles[-1]["close"], candles[-1]["timestamp"], "END_OF_DATA"
        if exit_price:
            pnl_pct = (exit_price - entry_price) / entry_price - COMMISSION * 2 if direction == "LONG" else (entry_price - exit_price) / entry_price - COMMISSION * 2
            trades.append({"entry_time": entry_time, "exit_time": exit_time, "direction": direction, "entry": entry_price,
                          "exit": exit_price, "sl": sl_price, "tp": tp_price, "pnl_pct": pnl_pct, "exit_reason": exit_reason, "reason": sig.get("reason", "")})
    if not trades:
        return {"symbol": symbol, "timeframe": timeframe, "strategy": strategy_name, "trades": 0, "win_rate": 0, "avg_pnl": 0, "total_pnl": 0, "profit_factor": 0, "sharpe": 0}
    wins, losses = [t for t in trades if t["pnl_pct"] > 0], [t for t in trades if t["pnl_pct"] <= 0]
    win_rate = len(wins) / len(trades) if trades else 0
    avg_pnl = statistics.mean([t["pnl_pct"] for t in trades]) if trades else 0
    total_pnl = sum([t["pnl_pct"] for t in trades])
    gross_profit = sum([t["pnl_pct"] for t in wins]) if wins else 0
    gross_loss = abs(sum([t["pnl_pct"] for t in losses])) if losses else 0.0001
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
    if len(trades) > 1:
        returns = [t["pnl_pct"] for t in trades]
        sharpe = statistics.mean(returns) / (statistics.stdev(returns) + 0.0001) * (252 ** 0.5) if statistics.stdev(returns) > 0 else 0
    else: sharpe = 0
    return {"symbol": symbol, "timeframe": timeframe, "strategy": strategy_name, "trades": len(trades), "win_rate": round(win_rate * 100, 1),
            "avg_pnl": round(avg_pnl * 100, 2), "total_pnl": round(total_pnl * 100, 2), "profit_factor": round(profit_factor, 2), "sharpe": round(sharpe, 2), "trade_details": trades}

def run_extensive_backtests():
    all_results = []
    print("=" * 80)
    print("UNIQUE EDGE STRATEGIES - EXTENSIVE BACKTEST")
    print("Using REAL data from Binance, KuCoin, OKX")
    print("=" * 80)
    strategies = [("LSR", strategy_liquidity_sweep), ("OBB", strategy_order_block), ("VDR", strategy_vwap_deviation), ("VRM", strategy_volatility_regime)]
    for exchange, symbol in USER_PICKS:
        print(f"\n[{exchange}] {symbol}")
        print("-" * 40)
        data_1h, data_4h, data_15m = fetch_real_data(exchange, symbol, "1h"), fetch_real_data(exchange, symbol, "4h"), fetch_real_data(exchange, symbol, "15m")
        if not data_1h:
            print(f"  [ERR] No data available")
            continue
        print(f"  [OK] 1h: {len(data_1h)} bars | 4h: {len(data_4h) if data_4h else 0} bars | 15m: {len(data_15m) if data_15m else 0} bars")
        for strat_name, strat_func in strategies:
            try:
                signals = strat_func(data_1h)
                if signals:
                    result = backtest_strategy(signals, data_1h, strat_name, symbol, "1h")
                    all_results.append(result)
                    status = "[WIN]" if result["win_rate"] > 50 and result["profit_factor"] > 1.0 else "[-]"
                    print(f"  {status} {strat_name}: {result['trades']} trades, {result['win_rate']:.0f}% WR, PF {result['profit_factor']:.2f}, Sharpe {result['sharpe']:.2f}")
            except Exception as e: print(f"  [ERR] {strat_name}: Error - {e}")
        if data_15m and data_1h and data_4h:
            try:
                signals = strategy_smart_money_confluence(data_15m, data_1h, data_4h)
                if signals:
                    result = backtest_strategy(signals, data_1h, "SMC", symbol, "MTF")
                    all_results.append(result)
                    status = "[WIN]" if result["win_rate"] > 50 and result["profit_factor"] > 1.0 else "[-]"
                    print(f"  {status} SMC: {result['trades']} trades, {result['win_rate']:.0f}% WR, PF {result['profit_factor']:.2f}")
            except Exception as e: print(f"  [ERR] SMC: Error - {e}")
        time.sleep(0.5)
    summary = {"run_date": datetime.now().isoformat(), "total_results": len(all_results), "strategies_tested": ["LSR", "OBB", "VDR", "VRM", "SMC"],
               "symbols_tested": len(USER_PICKS), "results": all_results,
               "aggregate": {"avg_win_rate": round(statistics.mean([r["win_rate"] for r in all_results]), 1) if all_results else 0,
                            "avg_profit_factor": round(statistics.mean([r["profit_factor"] for r in all_results]), 2) if all_results else 0,
                            "total_trades": sum([r["trades"] for r in all_results]),
                            "best_strategy": max(all_results, key=lambda x: x["sharpe"])["strategy"] if all_results else None,
                            "best_symbol": max(all_results, key=lambda x: x["profit_factor"])["symbol"] if all_results else None}}
    _repo = __file__.replace("\\", "/").rsplit("/", 1)[0]
    output_path = os.path.join(_repo, "alpha_engine", "data", "unique_edge_backtest_results.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print("\n" + "=" * 80)
    print("BACKTEST COMPLETE")
    print("=" * 80)
    print(f"Total results: {summary['total_results']}")
    print(f"Total trades: {summary['aggregate']['total_trades']}")
    print(f"Avg Win Rate: {summary['aggregate']['avg_win_rate']:.1f}%")
    print(f"Avg Profit Factor: {summary['aggregate']['avg_profit_factor']:.2f}")
    print(f"\nBest Strategy: {summary['aggregate']['best_strategy']}")
    print(f"Best Symbol: {summary['aggregate']['best_symbol']}")
    print(f"\nResults saved to: {output_path}")
    return summary

if __name__ == "__main__":
    results = run_extensive_backtests()
