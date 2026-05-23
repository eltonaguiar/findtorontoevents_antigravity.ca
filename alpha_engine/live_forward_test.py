#!/usr/bin/env python3
"""
Live Forward Test Scanner -- Generates picks from proven strategies
and tracks them against live market data.

Runs against crypto (24/7 open). Forex/futures added when markets open.
"""

import json
import math
import os
import time
import urllib.request
from datetime import datetime, timezone


_BINANCE_KLINE_BASES = [
    "https://api.binance.com",
    "https://data-api.binance.vision",
    "https://api.binance.us",
]


def fetch_candles(symbol, interval="1h", limit=200):
    """Fetch OHLCV candles from Binance with endpoint failover."""
    for base in _BINANCE_KLINE_BASES:
        try:
            url = f"{base}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
            req = urllib.request.Request(url, headers={"User-Agent": "AlphaForwardTest/1.0"})
            resp = urllib.request.urlopen(req, timeout=10)
            raw = json.loads(resp.read())
            return [
                {
                    "open": float(c[1]),
                    "high": float(c[2]),
                    "low": float(c[3]),
                    "close": float(c[4]),
                    "volume": float(c[5]),
                    "time": c[0],
                }
                for c in raw
            ]
        except urllib.error.HTTPError as e:
            if e.code in (451, 403):
                continue
        except Exception:
            continue
    return []


# --- Indicator functions ---

def ema(prices, period):
    if len(prices) < 2:
        return list(prices)
    result = [0.0] * len(prices)
    k = 2 / (period + 1)
    result[0] = prices[0]
    for i in range(1, len(prices)):
        result[i] = prices[i] * k + result[i - 1] * (1 - k)
    return result


def sma(prices, period):
    result = [0.0] * len(prices)
    for i in range(len(prices)):
        start = max(0, i - period + 1)
        result[i] = sum(prices[start : i + 1]) / (i - start + 1)
    return result


def calc_atr(candles, period):
    trs = []
    for i in range(len(candles)):
        if i == 0:
            trs.append(candles[i]["high"] - candles[i]["low"])
        else:
            tr = max(
                candles[i]["high"] - candles[i]["low"],
                abs(candles[i]["high"] - candles[i - 1]["close"]),
                abs(candles[i]["low"] - candles[i - 1]["close"]),
            )
            trs.append(tr)
    return ema(trs, period)


def rsi(prices, period=14):
    if len(prices) < period + 1:
        return [50] * len(prices)
    result = [50.0] * len(prices)
    gains = [0.0] * len(prices)
    losses = [0.0] * len(prices)
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i - 1]
        gains[i] = diff if diff > 0 else 0
        losses[i] = -diff if diff < 0 else 0
    avg_gain = sum(gains[1 : period + 1]) / period
    avg_loss = sum(losses[1 : period + 1]) / period
    for i in range(period, len(prices)):
        if i > period:
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            result[i] = 100
        else:
            result[i] = 100 - 100 / (1 + avg_gain / avg_loss)
    return result


def bollinger_bands(prices, period=20, std_mult=2.0):
    sma_vals = sma(prices, period)
    upper = [0.0] * len(prices)
    lower = [0.0] * len(prices)
    for i in range(len(prices)):
        start = max(0, i - period + 1)
        window = prices[start : i + 1]
        mean = sum(window) / len(window)
        variance = sum((x - mean) ** 2 for x in window) / len(window)
        std = math.sqrt(variance)
        upper[i] = sma_vals[i] + std_mult * std
        lower[i] = sma_vals[i] - std_mult * std
    return sma_vals, upper, lower


# --- Strategy implementations ---


def strategy_connors_rsi2(sym, candles, closes, atrs, now):
    """Connors RSI-2: proven 75.7% WR on SPY, adapted for crypto."""
    picks = []
    rsi2 = rsi(closes, 2)
    sma200 = sma(closes, min(200, len(closes) - 1))
    current = closes[-1]
    curr_atr = atrs[-1]

    if rsi2[-1] < 10 and current > sma200[-1]:
        tp = current + 1.5 * curr_atr
        sl = current - 1.0 * curr_atr
        picks.append(
            {
                "strategy": "connors_rsi2_extreme",
                "symbol": sym,
                "direction": "LONG",
                "entry_price": round(current, 6),
                "take_profit": round(tp, 6),
                "stop_loss": round(sl, 6),
                "confidence": 0.75,
                "risk_reward": 1.5,
                "reason": f"RSI(2)={rsi2[-1]:.1f} extreme oversold, above 200 SMA. Proven 75.7% WR.",
                "timestamp": now,
            }
        )
    elif rsi2[-1] > 90 and current < sma200[-1]:
        tp = current - 1.5 * curr_atr
        sl = current + 1.0 * curr_atr
        picks.append(
            {
                "strategy": "connors_rsi2_extreme",
                "symbol": sym,
                "direction": "SHORT",
                "entry_price": round(current, 6),
                "take_profit": round(tp, 6),
                "stop_loss": round(sl, 6),
                "confidence": 0.70,
                "risk_reward": 1.5,
                "reason": f"RSI(2)={rsi2[-1]:.1f} extreme overbought, below 200 SMA.",
                "timestamp": now,
            }
        )
    return picks


def strategy_keltner_compression(sym, candles, closes, atrs, now):
    """Keltner Compression Expansion: proven 72.9% WR on BTC."""
    picks = []
    current = closes[-1]
    curr_atr = atrs[-1]
    ema30 = ema(closes, 30)
    atr20 = calc_atr(candles, 20)

    upper = [ema30[i] + 1.8 * atr20[i] for i in range(len(closes))]
    lower = [ema30[i] - 1.8 * atr20[i] for i in range(len(closes))]
    widths = [
        (upper[i] - lower[i]) / ema30[i] if ema30[i] > 0 else 0
        for i in range(len(closes))
    ]

    if len(widths) > 80:
        recent_widths = sorted(widths[-80:])
        pct25 = recent_widths[20]
        compressed = widths[-1] < pct25

        if compressed and closes[-1] > ema30[-1] and closes[-2] <= ema30[-2]:
            tp = current + 2.3 * curr_atr
            sl = current - 1.3 * curr_atr
            picks.append(
                {
                    "strategy": "keltner_compression_expansion",
                    "symbol": sym,
                    "direction": "LONG",
                    "entry_price": round(current, 6),
                    "take_profit": round(tp, 6),
                    "stop_loss": round(sl, 6),
                    "confidence": 0.72,
                    "risk_reward": round(2.3 / 1.3, 2),
                    "reason": f"Keltner compressed (width={widths[-1]:.4f} < p25={pct25:.4f}), breakout above EMA30.",
                    "timestamp": now,
                }
            )
        elif compressed and closes[-1] < ema30[-1] and closes[-2] >= ema30[-2]:
            tp = current - 2.3 * curr_atr
            sl = current + 1.3 * curr_atr
            picks.append(
                {
                    "strategy": "keltner_compression_expansion",
                    "symbol": sym,
                    "direction": "SHORT",
                    "entry_price": round(current, 6),
                    "take_profit": round(tp, 6),
                    "stop_loss": round(sl, 6),
                    "confidence": 0.72,
                    "risk_reward": round(2.3 / 1.3, 2),
                    "reason": "Keltner compressed, breakdown below EMA30.",
                    "timestamp": now,
                }
            )
    return picks


def strategy_rsi_whale_volume(sym, candles, closes, atrs, now):
    """RSI + Whale Volume Confluence: 67.9% WR forward-tested."""
    picks = []
    current = closes[-1]
    curr_atr = atrs[-1]
    rsi14 = rsi(closes, 14)
    volumes = [c["volume"] for c in candles]
    avg_vol = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else sum(volumes) / len(volumes)
    vol_ratio = volumes[-1] / avg_vol if avg_vol > 0 else 1

    if rsi14[-1] < 30 and vol_ratio > 2.0:
        tp = current + 2.0 * curr_atr
        sl = current - 1.2 * curr_atr
        picks.append(
            {
                "strategy": "rsi_whale_volume_confluence",
                "symbol": sym,
                "direction": "LONG",
                "entry_price": round(current, 6),
                "take_profit": round(tp, 6),
                "stop_loss": round(sl, 6),
                "confidence": 0.68,
                "risk_reward": round(2.0 / 1.2, 2),
                "reason": f"RSI(14)={rsi14[-1]:.1f} oversold + whale volume {vol_ratio:.1f}x avg.",
                "timestamp": now,
            }
        )
    elif rsi14[-1] > 70 and vol_ratio > 2.0:
        tp = current - 2.0 * curr_atr
        sl = current + 1.2 * curr_atr
        picks.append(
            {
                "strategy": "rsi_whale_volume_confluence",
                "symbol": sym,
                "direction": "SHORT",
                "entry_price": round(current, 6),
                "take_profit": round(tp, 6),
                "stop_loss": round(sl, 6),
                "confidence": 0.65,
                "risk_reward": round(2.0 / 1.2, 2),
                "reason": f"RSI(14)={rsi14[-1]:.1f} overbought + whale volume {vol_ratio:.1f}x avg.",
                "timestamp": now,
            }
        )
    return picks


def strategy_bollinger_reversion(sym, candles, closes, atrs, now):
    """Bollinger Band Mean Reversion: target SMA20 from extremes."""
    picks = []
    current = closes[-1]
    curr_atr = atrs[-1]
    rsi14 = rsi(closes, 14)
    sma20, bb_upper, bb_lower = bollinger_bands(closes, 20, 2.0)

    if current < bb_lower[-1] and rsi14[-1] < 35:
        tp = sma20[-1]
        sl = current - 1.5 * curr_atr
        dist_tp = abs(tp - current)
        dist_sl = abs(current - sl)
        rr = dist_tp / dist_sl if dist_sl > 0 else 0
        if rr > 1.0:
            picks.append(
                {
                    "strategy": "bollinger_mean_reversion",
                    "symbol": sym,
                    "direction": "LONG",
                    "entry_price": round(current, 6),
                    "take_profit": round(tp, 6),
                    "stop_loss": round(sl, 6),
                    "confidence": 0.62,
                    "risk_reward": round(rr, 2),
                    "reason": f"Price below lower BB + RSI(14)={rsi14[-1]:.1f}, target SMA20 mean.",
                    "timestamp": now,
                }
            )
    elif current > bb_upper[-1] and rsi14[-1] > 65:
        tp = sma20[-1]
        sl = current + 1.5 * curr_atr
        dist_tp = abs(current - tp)
        dist_sl = abs(sl - current)
        rr = dist_tp / dist_sl if dist_sl > 0 else 0
        if rr > 1.0:
            picks.append(
                {
                    "strategy": "bollinger_mean_reversion",
                    "symbol": sym,
                    "direction": "SHORT",
                    "entry_price": round(current, 6),
                    "take_profit": round(tp, 6),
                    "stop_loss": round(sl, 6),
                    "confidence": 0.60,
                    "risk_reward": round(rr, 2),
                    "reason": f"Price above upper BB + RSI(14)={rsi14[-1]:.1f}, target SMA20 mean.",
                    "timestamp": now,
                }
            )
    return picks


def strategy_ema_stack(sym, candles, closes, atrs, now):
    """EMA Stack Momentum: 9>21>50 alignment, 65-72% WR."""
    picks = []
    if len(closes) < 54:
        return picks
    current = closes[-1]
    curr_atr = atrs[-1]
    ema9 = ema(closes, 9)
    ema21 = ema(closes, 21)
    ema50 = ema(closes, 50)

    bullish_now = ema9[-1] > ema21[-1] > ema50[-1] and current > ema9[-1]
    bearish_now = ema9[-1] < ema21[-1] < ema50[-1] and current < ema9[-1]
    was_bullish = ema9[-4] > ema21[-4] > ema50[-4]
    was_bearish = ema9[-4] < ema21[-4] < ema50[-4]

    if bullish_now and not was_bullish:
        tp = current + 2.0 * curr_atr
        sl = current - 1.0 * curr_atr
        picks.append(
            {
                "strategy": "ema_stack_momentum",
                "symbol": sym,
                "direction": "LONG",
                "entry_price": round(current, 6),
                "take_profit": round(tp, 6),
                "stop_loss": round(sl, 6),
                "confidence": 0.65,
                "risk_reward": 2.0,
                "reason": f"EMA 9>{ema9[-1]:.1f} > 21>{ema21[-1]:.1f} > 50>{ema50[-1]:.1f} bullish stack just formed.",
                "timestamp": now,
            }
        )
    elif bearish_now and not was_bearish:
        tp = current - 2.0 * curr_atr
        sl = current + 1.0 * curr_atr
        picks.append(
            {
                "strategy": "ema_stack_momentum",
                "symbol": sym,
                "direction": "SHORT",
                "entry_price": round(current, 6),
                "take_profit": round(tp, 6),
                "stop_loss": round(sl, 6),
                "confidence": 0.65,
                "risk_reward": 2.0,
                "reason": "EMA 9<21<50 bearish stack just formed.",
                "timestamp": now,
            }
        )
    return picks


def strategy_funding_sentiment(sym, now):
    """Binance Futures Sentiment contrarian: L/S ratio extremes."""
    picks = []
    try:
        # Fetch L/S ratio (with fapi failover)
        data = None
        for _fbase in ["https://fapi.binance.com", "https://fapi1.binance.com", "https://fapi2.binance.com"]:
            try:
                _url = f"{_fbase}/futures/data/topLongShortAccountRatio?symbol={sym}&period=4h&limit=1"
                _req = urllib.request.Request(_url, headers={"User-Agent": "AlphaForwardTest/1.0"})
                _resp = urllib.request.urlopen(_req, timeout=5)
                data = json.loads(_resp.read())
                if data:
                    break
            except Exception:
                continue
        if not data:
            return picks
        ls_ratio = float(data[0]["longShortRatio"])

        # Fetch current price (with spot failover)
        current = None
        for _sbase in _BINANCE_KLINE_BASES:
            try:
                _url2 = f"{_sbase}/api/v3/ticker/price?symbol={sym}"
                _req2 = urllib.request.Request(_url2, headers={"User-Agent": "AlphaForwardTest/1.0"})
                _resp2 = urllib.request.urlopen(_req2, timeout=5)
                price_data = json.loads(_resp2.read())
                current = float(price_data["price"])
                break
            except Exception:
                continue
        if current is None:
            return picks

        # Fetch taker ratio (with fapi failover)
        taker_data = None
        for _fbase in ["https://fapi.binance.com", "https://fapi1.binance.com", "https://fapi2.binance.com"]:
            try:
                _url3 = f"{_fbase}/futures/data/takerlongshortRatio?symbol={sym}&period=4h&limit=1"
                _req3 = urllib.request.Request(_url3, headers={"User-Agent": "AlphaForwardTest/1.0"})
                _resp3 = urllib.request.urlopen(_req3, timeout=5)
                taker_data = json.loads(_resp3.read())
                if taker_data:
                    break
            except Exception:
                continue
        taker_ratio = float(taker_data[0]["buySellRatio"]) if taker_data else 1.0

        # Contrarian: when crowd is extremely long, go short (and vice versa)
        if ls_ratio > 2.0 and taker_ratio < 0.45:
            # Crowd extremely long + sellers dominant = SHORT
            atr_est = current * 0.015  # estimate 1.5% ATR
            tp = current - 1.5 * atr_est
            sl = current + 1.0 * atr_est
            picks.append(
                {
                    "strategy": "funding_sentiment_contrarian",
                    "symbol": sym,
                    "direction": "SHORT",
                    "entry_price": round(current, 6),
                    "take_profit": round(tp, 6),
                    "stop_loss": round(sl, 6),
                    "confidence": 0.60,
                    "risk_reward": 1.5,
                    "reason": f"Contrarian: L/S ratio {ls_ratio:.2f} (crowd long) + taker sell ratio {1-taker_ratio:.1%}.",
                    "timestamp": now,
                }
            )
        elif ls_ratio < 0.5 and taker_ratio > 0.55:
            # Crowd extremely short + buyers dominant = LONG
            atr_est = current * 0.015
            tp = current + 1.5 * atr_est
            sl = current - 1.0 * atr_est
            picks.append(
                {
                    "strategy": "funding_sentiment_contrarian",
                    "symbol": sym,
                    "direction": "LONG",
                    "entry_price": round(current, 6),
                    "take_profit": round(tp, 6),
                    "stop_loss": round(sl, 6),
                    "confidence": 0.60,
                    "risk_reward": 1.5,
                    "reason": f"Contrarian: L/S ratio {ls_ratio:.2f} (crowd short) + taker buy ratio {taker_ratio:.1%}.",
                    "timestamp": now,
                }
            )
    except Exception:
        pass
    return picks


STRATEGIES = [
    ("connors_rsi2_extreme", strategy_connors_rsi2),
    ("keltner_compression_expansion", strategy_keltner_compression),
    ("rsi_whale_volume_confluence", strategy_rsi_whale_volume),
    ("bollinger_mean_reversion", strategy_bollinger_reversion),
    ("ema_stack_momentum", strategy_ema_stack),
]

SYMBOLS = [
    "BTCUSDT", "SOLUSDT", "ETHUSDT", "BNBUSDT",
    "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "XRPUSDT",
    "ADAUSDT", "NEARUSDT", "SUIUSDT", "APTUSDT",
]


def run_scan():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    all_picks = []

    print("=" * 70)
    print("  LIVE FORWARD TEST SCANNER")
    print(f"  {now}")
    print("=" * 70)

    # Fetch candles
    candle_data = {}
    for sym in SYMBOLS:
        try:
            candles = fetch_candles(sym, "1h", 200)
            candle_data[sym] = candles
            print(f"  {sym}: {len(candles)} candles, last={candles[-1]['close']}")
        except Exception as e:
            print(f"  {sym}: FAILED - {e}")

    print(f"\nScanning {len(candle_data)} symbols x {len(STRATEGIES) + 1} strategies...")
    print("-" * 70)

    # Run TA strategies
    for sym, candles in candle_data.items():
        closes = [c["close"] for c in candles]
        atrs = calc_atr(candles, 14)

        for name, func in STRATEGIES:
            picks = func(sym, candles, closes, atrs, now)
            all_picks.extend(picks)

    # Run sentiment strategy (futures data, separate API)
    for sym in ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]:
        picks = strategy_funding_sentiment(sym, now)
        all_picks.extend(picks)

    # Print results
    print(f"\n{'=' * 70}")
    print(f"  RESULTS: {len(all_picks)} picks generated")
    print(f"{'=' * 70}")

    if all_picks:
        for p in all_picks:
            d = "L" if p["direction"] == "LONG" else "S"
            print(
                f"  {d} {p['symbol']:10s} @ {p['entry_price']:>12.6f}  "
                f"TP:{p['take_profit']:>12.6f}  SL:{p['stop_loss']:>12.6f}  "
                f"R:R {p['risk_reward']}  [{p['strategy']}]"
            )
            print(f"    {p['reason']}")
    else:
        print("  No signals triggered. Strategies waiting for setup conditions.")
        print("  This is CORRECT - being selective, not forcing trades.")

    # Save
    output = {
        "generated_at": now,
        "market": "crypto",
        "market_status": "OPEN",
        "total_picks": len(all_picks),
        "strategies_scanned": [n for n, _ in STRATEGIES] + ["funding_sentiment_contrarian"],
        "symbols_scanned": list(candle_data.keys()),
        "picks": all_picks,
    }

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "live_forward_test_picks.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nSaved to {out_path}")
    return all_picks


if __name__ == "__main__":
    run_scan()
