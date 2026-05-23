#!/usr/bin/env python3
"""
trio_bot_strategies.py — Three Uncorrelated Alpha Streams
==========================================================
Based on live 24-hour bot performance:

1. MACD Volume Spike Scalper — 147 trades, 8min hold, 61% WR, Sharpe 1.4, +$389
2. RSI + VWAP Contrarian      — 23 trades, 4h hold, 74% WR, Sharpe 2.1, +$641
3. CVD Divergence              — 31 trades, 47min hold, 58% WR, Sharpe 1.8, +$937

Cross-correlation: 0.12 — true diversification by logic, not by asset.
Combined 24h: +$1,967 with zero trade overlap.

CVD wins not by frequency but by sizing — when right, it takes more.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── Shared config ──────────────────────────────────────────────────────────

# Top liquid symbols for scanning (need volume data)
SCAN_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT",
    "MATICUSDT", "ARBUSDT", "OPUSDT", "APTUSDT", "SUIUSDT",
    "FETUSDT", "RENDERUSDT", "NEARUSDT", "INJUSDT", "TRXUSDT",
]

# Risk caps per strategy (hedge-fund-grade)
MAX_TP_PCT = 0.15   # 15% max TP
MAX_SL_PCT = 0.10   # 10% max SL


def _safe_float(v, default=0.0):
    try:
        return float(v) if v is not None else default
    except (ValueError, TypeError):
        return default


def _fetch_klines_safe(symbol: str, interval: str = "1h", limit: int = 200) -> list:
    """Fetch klines using api_failover with graceful fallback."""
    try:
        from alpha_engine.api_failover import fetch_klines
        return fetch_klines(symbol, interval=interval, limit=limit) or []
    except ImportError:
        pass
    # Fallback: direct Binance
    import json
    import urllib.request
    for base in ["https://api.binance.com", "https://api1.binance.com",
                 "https://api2.binance.com", "https://api3.binance.com"]:
        try:
            url = f"{base}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())
        except Exception:
            continue
    return []


def _parse_klines(raw: list) -> dict:
    """Parse Binance klines into OHLCV arrays."""
    if not raw or len(raw) < 20:
        return {}
    opens, highs, lows, closes, volumes, taker_buy_vols = [], [], [], [], [], []
    for k in raw:
        opens.append(float(k[1]))
        highs.append(float(k[2]))
        lows.append(float(k[3]))
        closes.append(float(k[4]))
        volumes.append(float(k[5]))
        taker_buy_vols.append(float(k[9]) if len(k) > 9 else float(k[5]) * 0.5)
    return {
        "open": opens, "high": highs, "low": lows, "close": closes,
        "volume": volumes, "taker_buy_vol": taker_buy_vols,
    }


# ── Technical Indicators ───────────────────────────────────────────────────

def _ema(data: list, period: int) -> list:
    """Exponential moving average."""
    if not data or len(data) < period:
        return [0.0] * len(data)
    result = [0.0] * len(data)
    result[period - 1] = sum(data[:period]) / period
    mult = 2 / (period + 1)
    for i in range(period, len(data)):
        result[i] = (data[i] - result[i - 1]) * mult + result[i - 1]
    return result


def _rsi(closes: list, period: int = 14) -> list:
    """Wilder's RSI."""
    if len(closes) < period + 1:
        return [50.0] * len(closes)
    result = [50.0] * len(closes)
    gains, losses = 0.0, 0.0
    for i in range(1, period + 1):
        diff = closes[i] - closes[i - 1]
        if diff > 0:
            gains += diff
        else:
            losses -= diff
    avg_gain = gains / period
    avg_loss = losses / period
    if avg_loss == 0:
        result[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        result[period] = 100.0 - (100.0 / (1.0 + rs))
    for i in range(period + 1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gain = diff if diff > 0 else 0.0
        loss = -diff if diff < 0 else 0.0
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        if avg_loss == 0:
            result[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            result[i] = 100.0 - (100.0 / (1.0 + rs))
    return result


def _macd(closes: list, fast: int = 12, slow: int = 26, signal: int = 9):
    """MACD line, signal line, histogram."""
    ema_fast = _ema(closes, fast)
    ema_slow = _ema(closes, slow)
    macd_line = [f - s for f, s in zip(ema_fast, ema_slow)]
    signal_line = _ema(macd_line, signal)
    histogram = [m - s for m, s in zip(macd_line, signal_line)]
    return macd_line, signal_line, histogram


def _vwap(highs: list, lows: list, closes: list, volumes: list) -> list:
    """Session VWAP (cumulative typical price * volume / cumulative volume)."""
    result = [0.0] * len(closes)
    cum_tpv = 0.0
    cum_vol = 0.0
    for i in range(len(closes)):
        tp = (highs[i] + lows[i] + closes[i]) / 3
        cum_tpv += tp * volumes[i]
        cum_vol += volumes[i]
        result[i] = cum_tpv / cum_vol if cum_vol > 0 else closes[i]
    return result


def _cvd(taker_buy_vols: list, volumes: list) -> list:
    """Cumulative Volume Delta. Buy vol - sell vol, cumulated."""
    result = [0.0] * len(volumes)
    cum = 0.0
    for i in range(len(volumes)):
        buy_vol = taker_buy_vols[i]
        sell_vol = volumes[i] - buy_vol
        delta = buy_vol - sell_vol
        cum += delta
        result[i] = cum
    return result


def _volume_zscore(volumes: list, lookback: int = 20) -> list:
    """Z-score of current volume vs lookback mean."""
    result = [0.0] * len(volumes)
    for i in range(lookback, len(volumes)):
        window = volumes[i - lookback:i]
        mean = sum(window) / len(window)
        std = max(1e-10, (sum((v - mean) ** 2 for v in window) / len(window)) ** 0.5)
        result[i] = (volumes[i] - mean) / std
    return result


# ── Strategy 1: MACD Volume Spike Scalper ──────────────────────────────────

def macd_volume_spike_scalper(symbol: str = None, symbols: list = None) -> list:
    """
    MACD Volume Spike Scalper
    ─────────────────────────
    Logic: Sees volume spike BEFORE crowd arrives, enters on MACD crossover
    confirmed by above-average volume.

    Original performance: 147 trades, 8min hold, 61% WR, Sharpe 1.4, +$389/24h
    We use 5m candles for the scalping timeframe.

    Entry conditions:
    - MACD histogram flips sign (bullish/bearish crossover)
    - Volume z-score > 1.5 (spike above 1.5 standard deviations)
    - Price above/below EMA-20 confirms direction

    TP: 1.0% (scalp target), SL: 0.5% (tight stop for 2:1 R:R)
    """
    picks = []
    target_symbols = symbols or (SCAN_SYMBOLS if symbol is None else [symbol])

    for sym in target_symbols:
        try:
            raw = _fetch_klines_safe(sym, interval="5m", limit=100)
            data = _parse_klines(raw)
            if not data:
                continue

            closes = data["close"]
            volumes = data["volume"]
            if len(closes) < 30:
                continue

            macd_line, signal_line, histogram = _macd(closes)
            vol_z = _volume_zscore(volumes, lookback=20)
            ema20 = _ema(closes, 20)

            current = closes[-1]
            prev_hist = histogram[-2]
            curr_hist = histogram[-1]
            curr_vol_z = vol_z[-1]
            curr_ema = ema20[-1]

            # Volume spike required
            if curr_vol_z < 1.5:
                continue

            direction = None
            reason = ""

            # Bullish: histogram flips positive + price above EMA20
            if prev_hist <= 0 < curr_hist and current > curr_ema:
                direction = "BUY"
                reason = (f"MACD bullish crossover + volume spike (z={curr_vol_z:.1f}). "
                          f"Price ${current:.4f} > EMA20 ${curr_ema:.4f}")

            # Bearish: histogram flips negative + price below EMA20
            elif prev_hist >= 0 > curr_hist and current < curr_ema:
                direction = "SELL"
                reason = (f"MACD bearish crossover + volume spike (z={curr_vol_z:.1f}). "
                          f"Price ${current:.4f} < EMA20 ${curr_ema:.4f}")

            if direction is None:
                continue

            # Scalp TP/SL: 1.0% / 0.5% (2:1 R:R)
            if direction == "BUY":
                tp = round(current * 1.010, 8)
                sl = round(current * 0.995, 8)
            else:
                tp = round(current * 0.990, 8)
                sl = round(current * 1.005, 8)

            confidence = min(0.80, 0.55 + curr_vol_z * 0.05)

            picks.append({
                "strategy": "macd_volume_spike_scalper",
                "symbol": sym,
                "direction": direction,
                "signal_type": direction,
                "entry_price": current,
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(confidence, 4),
                "category": "crypto",
                "source_system": "trio_bot",
                "reason": reason,
                "expected_hold": "8-15 minutes",
                "reference_wr": 0.61,
                "reference_sharpe": 1.4,
            })

        except Exception as e:
            logger.warning(f"[MACD_SCALPER] {sym}: {e}")

    return picks


# ── Strategy 2: RSI + VWAP Contrarian ──────────────────────────────────────

def rsi_vwap_contrarian(symbol: str = None, symbols: list = None) -> list:
    """
    RSI + VWAP Contrarian
    ─────────────────────
    Logic: Waits for RSI extremes (overbought/oversold) CONFIRMED by VWAP
    deviation. Enters AGAINST the crowd at exhaustion points.

    Original performance: 23 trades, 4h hold, 74% WR, Sharpe 2.1, +$641/24h
    We use 1h candles for the patient timeframe.

    Entry conditions (SELL):
    - RSI > 75 (overbought zone)
    - Price > VWAP * 1.02 (2%+ above VWAP = extended)
    - Wait for RSI to turn down from peak (confirmation)

    Entry conditions (BUY):
    - RSI < 25 (oversold zone)
    - Price < VWAP * 0.98 (2%+ below VWAP = extended)
    - Wait for RSI to turn up from trough (confirmation)

    TP: 2.5% (patient swing target), SL: 1.5% (wider stop for mean reversion)
    """
    picks = []
    target_symbols = symbols or (SCAN_SYMBOLS if symbol is None else [symbol])

    for sym in target_symbols:
        try:
            raw = _fetch_klines_safe(sym, interval="1h", limit=200)
            data = _parse_klines(raw)
            if not data:
                continue

            closes = data["close"]
            highs = data["high"]
            lows = data["low"]
            volumes = data["volume"]
            if len(closes) < 30:
                continue

            rsi_vals = _rsi(closes, 14)
            vwap_vals = _vwap(highs, lows, closes, volumes)

            current = closes[-1]
            curr_rsi = rsi_vals[-1]
            prev_rsi = rsi_vals[-2]
            curr_vwap = vwap_vals[-1]

            vwap_deviation = (current - curr_vwap) / curr_vwap if curr_vwap > 0 else 0

            direction = None
            reason = ""

            # Contrarian SELL: overbought + extended above VWAP + RSI turning down
            if curr_rsi > 75 and vwap_deviation > 0.02 and curr_rsi < prev_rsi:
                direction = "SELL"
                reason = (f"RSI overbought ({curr_rsi:.1f}, turning down from {prev_rsi:.1f}). "
                          f"Price {vwap_deviation*100:+.1f}% above VWAP ${curr_vwap:.4f}")

            # Contrarian BUY: oversold + extended below VWAP + RSI turning up
            elif curr_rsi < 25 and vwap_deviation < -0.02 and curr_rsi > prev_rsi:
                direction = "BUY"
                reason = (f"RSI oversold ({curr_rsi:.1f}, turning up from {prev_rsi:.1f}). "
                          f"Price {vwap_deviation*100:+.1f}% below VWAP ${curr_vwap:.4f}")

            if direction is None:
                continue

            # Patient swing TP/SL: 2.5% / 1.5% (~1.67:1 R:R)
            if direction == "BUY":
                tp = round(current * 1.025, 8)
                sl = round(current * 0.985, 8)
            else:
                tp = round(current * 0.975, 8)
                sl = round(current * 1.015, 8)

            # Higher confidence because this strategy has 74% WR
            confidence = min(0.85, 0.65 + abs(vwap_deviation) * 2)

            picks.append({
                "strategy": "rsi_vwap_contrarian",
                "symbol": sym,
                "direction": direction,
                "signal_type": direction,
                "entry_price": current,
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(confidence, 4),
                "category": "crypto",
                "source_system": "trio_bot",
                "reason": reason,
                "expected_hold": "2-6 hours",
                "reference_wr": 0.74,
                "reference_sharpe": 2.1,
            })

        except Exception as e:
            logger.warning(f"[RSI_VWAP] {sym}: {e}")

    return picks


# ── Strategy 3: CVD Divergence ─────────────────────────────────────────────

def cvd_divergence(symbol: str = None, symbols: list = None) -> list:
    """
    CVD (Cumulative Volume Delta) Divergence
    ─────────────────────────────────────────
    Logic: Price goes up but money flows OUT (sell pressure hidden) → short.
    Price goes down but money flows IN (buy pressure hidden) → long.

    Original performance: 31 trades, 47min hold, 58% WR, Sharpe 1.8, +$937/24h
    CVD wins not by being right more often, but by taking MORE when right.
    We use 15m candles for medium-term divergence detection.

    Entry conditions (BUY — bullish divergence):
    - Price making lower lows (3-bar)
    - CVD making higher lows (money flowing IN despite price drop)
    - Volume above average (confirms real flow, not just noise)

    Entry conditions (SELL — bearish divergence):
    - Price making higher highs (3-bar)
    - CVD making lower highs (money flowing OUT despite price rise)
    - Volume above average

    TP: 2.0% (CVD divergences resolve bigger), SL: 1.0% (tight = high R:R)
    """
    picks = []
    target_symbols = symbols or (SCAN_SYMBOLS if symbol is None else [symbol])

    for sym in target_symbols:
        try:
            raw = _fetch_klines_safe(sym, interval="15m", limit=100)
            data = _parse_klines(raw)
            if not data:
                continue

            closes = data["close"]
            highs = data["high"]
            lows = data["low"]
            volumes = data["volume"]
            taker_buy = data["taker_buy_vol"]
            if len(closes) < 30:
                continue

            cvd_vals = _cvd(taker_buy, volumes)
            vol_z = _volume_zscore(volumes, lookback=20)

            current = closes[-1]

            # Need at least volume above average
            if vol_z[-1] < 0.5:
                continue

            # Check 5-bar price and CVD patterns
            price_lows = [lows[-5], lows[-3], lows[-1]]
            price_highs = [highs[-5], highs[-3], highs[-1]]
            cvd_at_lows = [cvd_vals[-5], cvd_vals[-3], cvd_vals[-1]]
            cvd_at_highs = [cvd_vals[-5], cvd_vals[-3], cvd_vals[-1]]

            direction = None
            reason = ""

            # Bullish divergence: price lower lows, CVD higher lows
            if (price_lows[2] < price_lows[0] and  # price making lower lows
                    cvd_at_lows[2] > cvd_at_lows[0]):  # CVD making higher lows
                divergence_strength = (cvd_at_lows[2] - cvd_at_lows[0]) / max(1, abs(cvd_at_lows[0]))
                if abs(divergence_strength) > 0.05:
                    direction = "BUY"
                    reason = (f"CVD bullish divergence: price lower low but CVD higher low "
                              f"(hidden buying). Vol z={vol_z[-1]:.1f}")

            # Bearish divergence: price higher highs, CVD lower highs
            elif (price_highs[2] > price_highs[0] and  # price making higher highs
                  cvd_at_highs[2] < cvd_at_highs[0]):  # CVD making lower highs
                divergence_strength = (cvd_at_highs[0] - cvd_at_highs[2]) / max(1, abs(cvd_at_highs[0]))
                if abs(divergence_strength) > 0.05:
                    direction = "SELL"
                    reason = (f"CVD bearish divergence: price higher high but CVD lower high "
                              f"(hidden selling). Vol z={vol_z[-1]:.1f}")

            if direction is None:
                continue

            # CVD gets wider TP because when it's right, it takes more (2:1 R:R)
            if direction == "BUY":
                tp = round(current * 1.020, 8)
                sl = round(current * 0.990, 8)
            else:
                tp = round(current * 0.980, 8)
                sl = round(current * 1.010, 8)

            confidence = min(0.78, 0.55 + vol_z[-1] * 0.05)

            picks.append({
                "strategy": "cvd_divergence",
                "symbol": sym,
                "direction": direction,
                "signal_type": direction,
                "entry_price": current,
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(confidence, 4),
                "category": "crypto",
                "source_system": "trio_bot",
                "reason": reason,
                "expected_hold": "30-60 minutes",
                "reference_wr": 0.58,
                "reference_sharpe": 1.8,
            })

        except Exception as e:
            logger.warning(f"[CVD_DIV] {sym}: {e}")

    return picks


# ── Master Scanner ─────────────────────────────────────────────────────────

def scan_all(symbols: list = None) -> list:
    """Run all three strategies and return combined picks.

    The three strategies are deliberately uncorrelated (r=0.12):
    - MACD scalper: momentum, fast, volume-triggered
    - RSI+VWAP: contrarian, patient, mean-reversion
    - CVD: order flow, medium-term, divergence-based
    """
    all_picks = []
    now = datetime.now(timezone.utc).isoformat()

    for scanner in [macd_volume_spike_scalper, rsi_vwap_contrarian, cvd_divergence]:
        try:
            picks = scanner(symbols=symbols)
            for p in picks:
                p["generated_at"] = now
                p["timestamp"] = now
                p["status"] = "OPEN"
            all_picks.extend(picks)
            logger.info(f"[TRIO_BOT] {scanner.__name__}: {len(picks)} picks")
        except Exception as e:
            logger.warning(f"[TRIO_BOT] {scanner.__name__} failed: {e}")

    logger.info(f"[TRIO_BOT] Total: {len(all_picks)} picks from 3 strategies")
    return all_picks


# ── CLI ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json
    import sys

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    picks = scan_all()
    print(f"\n{'='*60}")
    print(f"TRIO BOT SCAN — {len(picks)} picks")
    print(f"{'='*60}")

    for p in picks:
        direction_emoji = "LONG" if p["direction"] == "BUY" else "SHORT"
        tp_pct = abs(p["take_profit"] - p["entry_price"]) / p["entry_price"] * 100
        sl_pct = abs(p["stop_loss"] - p["entry_price"]) / p["entry_price"] * 100
        print(f"  {p['symbol']:12s} {direction_emoji:5s} "
              f"entry=${p['entry_price']:.4f} TP={tp_pct:.1f}% SL={sl_pct:.1f}% "
              f"conf={p['confidence']:.2f} [{p['strategy']}]")
        print(f"    {p['reason']}")

    # Save to JSON
    out = Path(__file__).parent / "data" / "trio_bot_picks.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(picks, indent=2, default=str))
    print(f"\nSaved {len(picks)} picks to {out}")
