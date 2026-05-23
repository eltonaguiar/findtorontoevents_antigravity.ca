#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Top Gainer Predictor -- catches potential +10-20% daily movers BEFORE they pump.

Scans all USDT pairs on Binance for pre-pump patterns identified from empirical
analysis of today's top gainers (DUSK +21%, IQ +17%, HUMA +15%, APT +14%):

Key precursor signals found:
  1. Volume building: quote volume 2nd half > 1.5x 1st half in 3h window
  2. Whale accumulation: single 15m candle >2.5x avg volume (stealth buys)
  3. Squeeze breakout: BB width <4% (tight consolidation about to explode)
  4. Trade count surge: rising trade count = smart money splitting orders
  5. RSI oversold bounce: RSI <35 on 1H = mean reversion setup
  6. Quiet accumulation: price flat (<1.5% range) but volume rising

Scoring:
  - Each signal adds points (max 100)
  - >60 = strong pre-pump signal, >40 = moderate, >25 = watch list
  - Position size = score/100 * base allocation

Uses 5-mirror Binance failover (per API failover rule).
Stdlib only: json, datetime, math, os, urllib.request, ssl, logging, pathlib.
"""
from __future__ import annotations

import json
import logging
import math
import os
import ssl
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# Windows UTF-8 fix
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

_DIR = Path(__file__).resolve().parent
_DATA = _DIR / "data"

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger("top_gainer_predictor")

# Binance 5-mirror failover (per API failover rule)
_MIRRORS = [
    "https://data-api.binance.vision",
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]
_HDR = {"User-Agent": "AlphaEngine/TopGainerPredictor/1.0"}
_SSL_CTX = ssl.create_default_context()

# ── Score weights (empirically calibrated from today's top gainer analysis) ──
W_VOLUME_BUILDING = 20     # vol 2nd half > 1.5x 1st half in pre-pump window
W_WHALE_CANDLE = 18        # single candle >2.5x avg vol = stealth accumulation
W_SQUEEZE = 15             # BB width <4% = compression before expansion
W_TRADE_COUNT_SURGE = 12   # trade count rising = order splitting
W_RSI_OVERSOLD = 15        # RSI <35 on 1H = bounce setup
W_QUIET_ACCUMULATION = 12  # price flat but vol rising = smart money
W_MOMENTUM_IGNITION = 8    # first 3%+ move after quiet period = ignition candle

# Thresholds
MIN_24H_VOLUME_USD = 500_000    # min daily volume for liquidity
MIN_SCORE = 25                  # minimum score to report
MAX_PREDICTIONS = 20            # cap output
KLINE_15M_LIMIT = 48            # 12 hours of 15m data
KLINE_1H_LIMIT = 24             # 24 hours of 1H data


def _api_get(path: str, params: str = "") -> dict | list | None:
    """GET from Binance with 5-mirror failover."""
    for mirror in _MIRRORS:
        url = f"{mirror}{path}"
        if params:
            url += f"?{params}"
        try:
            req = urllib.request.Request(url, headers=_HDR)
            with urllib.request.urlopen(req, timeout=12, context=_SSL_CTX) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            log.debug("Mirror %s failed: %s", mirror, exc)
            continue
    log.warning("All Binance mirrors failed for %s", path)
    return None


def _calc_rsi(closes: list[float], period: int = 14) -> float:
    """Wilder RSI."""
    if len(closes) < period + 1:
        return 50.0
    gains = []
    losses = []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    avg_g = sum(gains[:period]) / period
    avg_l = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_g = (avg_g * (period - 1) + gains[i]) / period
        avg_l = (avg_l * (period - 1) + losses[i]) / period
    if avg_l == 0:
        return 100.0
    rs = avg_g / avg_l
    return 100 - (100 / (1 + rs))


def _bb_width(closes: list[float], period: int = 20) -> float:
    """Bollinger Band width as fraction of mean price."""
    if len(closes) < period:
        return 1.0  # unknown = wide
    window = closes[-period:]
    mean = sum(window) / period
    if mean <= 0:
        return 1.0
    var = sum((c - mean) ** 2 for c in window) / period
    std = math.sqrt(var)
    return (2 * std) / mean


def _get_usdt_candidates() -> list[dict]:
    """Get all USDT pairs with >MIN_24H_VOLUME_USD and moderate change."""
    tickers = _api_get("/api/v3/ticker/24hr")
    if not tickers:
        return []

    candidates = []
    for t in tickers:
        sym = t.get("symbol", "")
        if not sym.endswith("USDT"):
            continue
        # Skip stablecoins and leveraged tokens
        base = sym.replace("USDT", "")
        if base in ("USDC", "BUSD", "DAI", "TUSD", "FDUSD", "USDP"):
            continue
        if any(x in base for x in ("UP", "DOWN", "BULL", "BEAR", "3L", "3S")):
            continue

        vol_usd = float(t.get("quoteVolume", 0))
        change = float(t.get("priceChangePercent", 0))

        if vol_usd < MIN_24H_VOLUME_USD:
            continue
        # We want coins that haven't pumped yet (< +8%) but show precursors
        # Also include slightly negative coins (dip before pump)
        if change > 8.0:
            continue  # already pumped, too late

        candidates.append({
            "symbol": sym,
            "change_pct": change,
            "volume_usd": vol_usd,
            "price": float(t.get("lastPrice", 0)),
        })

    # Sort by volume descending (more liquid = more reliable signals)
    candidates.sort(key=lambda x: x["volume_usd"], reverse=True)
    # Cap at 150 to avoid API hammering
    return candidates[:150]


def _analyze_symbol(sym: str) -> dict | None:
    """Fetch 15m + 1H klines and compute pre-pump score."""
    # Get 15m klines (12 hours)
    klines_15m = _api_get(
        "/api/v3/klines",
        f"symbol={sym}&interval=15m&limit={KLINE_15M_LIMIT}"
    )
    if not klines_15m or len(klines_15m) < 20:
        return None

    # Get 1H klines (24 hours)
    klines_1h = _api_get(
        "/api/v3/klines",
        f"symbol={sym}&interval=1h&limit={KLINE_1H_LIMIT}"
    )
    if not klines_1h or len(klines_1h) < 14:
        return None

    # Parse 15m candles
    c15 = []
    for k in klines_15m:
        c15.append({
            "o": float(k[1]), "h": float(k[2]), "l": float(k[3]),
            "c": float(k[4]), "v": float(k[5]), "qv": float(k[7]),
            "trades": int(k[8]),
        })

    # Parse 1H candles
    c1h = []
    for k in klines_1h:
        c1h.append({
            "o": float(k[1]), "h": float(k[2]), "l": float(k[3]),
            "c": float(k[4]), "v": float(k[5]), "qv": float(k[7]),
            "trades": int(k[8]),
        })

    score = 0
    signals = []

    # ── Signal 1: Volume building on 15m (last 3h vs prior 3h) ──
    recent_12 = c15[-12:]  # last 3 hours
    prior_12 = c15[-24:-12] if len(c15) >= 24 else c15[:12]
    recent_vol = sum(c["qv"] for c in recent_12) / max(len(recent_12), 1)
    prior_vol = sum(c["qv"] for c in prior_12) / max(len(prior_12), 1)
    vol_building_ratio = recent_vol / prior_vol if prior_vol > 0 else 1.0

    if vol_building_ratio > 2.0:
        score += W_VOLUME_BUILDING
        signals.append(f"volume_building_{vol_building_ratio:.1f}x")
    elif vol_building_ratio > 1.5:
        score += int(W_VOLUME_BUILDING * 0.6)
        signals.append(f"volume_building_{vol_building_ratio:.1f}x")

    # ── Signal 2: Whale candle (single 15m candle >2.5x avg) ──
    avg_vol_15m = sum(c["qv"] for c in c15) / len(c15)
    whale_candles = 0
    for c in c15[-12:]:  # check last 3 hours
        if avg_vol_15m > 0 and c["qv"] > avg_vol_15m * 2.5:
            whale_candles += 1

    if whale_candles >= 2:
        score += W_WHALE_CANDLE
        signals.append(f"whale_candles_{whale_candles}")
    elif whale_candles == 1:
        score += int(W_WHALE_CANDLE * 0.6)
        signals.append("whale_candle_1")

    # ── Signal 3: Squeeze (BB width <4% on 1H) ──
    closes_1h = [c["c"] for c in c1h]
    bbw = _bb_width(closes_1h)
    if bbw < 0.03:
        score += W_SQUEEZE
        signals.append(f"tight_squeeze_{bbw*100:.1f}%")
    elif bbw < 0.04:
        score += int(W_SQUEEZE * 0.6)
        signals.append(f"squeeze_{bbw*100:.1f}%")

    # ── Signal 4: Trade count surge (last 3h vs prior) ──
    recent_trades = sum(c["trades"] for c in recent_12) / max(len(recent_12), 1)
    prior_trades = sum(c["trades"] for c in prior_12) / max(len(prior_12), 1)
    trade_ratio = recent_trades / prior_trades if prior_trades > 0 else 1.0

    if trade_ratio > 2.0:
        score += W_TRADE_COUNT_SURGE
        signals.append(f"trade_surge_{trade_ratio:.1f}x")
    elif trade_ratio > 1.5:
        score += int(W_TRADE_COUNT_SURGE * 0.6)
        signals.append(f"trade_building_{trade_ratio:.1f}x")

    # ── Signal 5: RSI oversold on 1H ──
    rsi = _calc_rsi(closes_1h)
    if rsi < 30:
        score += W_RSI_OVERSOLD
        signals.append(f"rsi_oversold_{rsi:.0f}")
    elif rsi < 35:
        score += int(W_RSI_OVERSOLD * 0.6)
        signals.append(f"rsi_low_{rsi:.0f}")

    # ── Signal 6: Quiet accumulation (price flat, volume up) ──
    recent_highs = [c["h"] for c in c15[-12:]]
    recent_lows = [c["l"] for c in c15[-12:]]
    if min(recent_lows) > 0:
        price_range = (max(recent_highs) - min(recent_lows)) / min(recent_lows)
    else:
        price_range = 1.0

    if price_range < 0.015 and vol_building_ratio > 1.3:
        score += W_QUIET_ACCUMULATION
        signals.append(f"quiet_accumulation_range={price_range*100:.1f}%")
    elif price_range < 0.025 and vol_building_ratio > 1.2:
        score += int(W_QUIET_ACCUMULATION * 0.5)
        signals.append(f"mild_accumulation_range={price_range*100:.1f}%")

    # ── Signal 7: Momentum ignition candle (first big move after quiet) ──
    # Check if the most recent 15m candle is a >1.5% move after tight range
    if len(c15) >= 2:
        last = c15[-1]
        last_move = abs(last["c"] - last["o"]) / last["o"] if last["o"] > 0 else 0
        # Check if prior 6 candles were quiet
        prior_moves = []
        for c in c15[-7:-1]:
            m = abs(c["c"] - c["o"]) / c["o"] if c["o"] > 0 else 0
            prior_moves.append(m)
        avg_prior_move = sum(prior_moves) / max(len(prior_moves), 1)

        if last_move > 0.015 and avg_prior_move < 0.005:
            score += W_MOMENTUM_IGNITION
            signals.append(f"ignition_{last_move*100:.1f}%")

    if score < MIN_SCORE:
        return None

    # ── Calculate entry/target/stop ──
    current_price = c15[-1]["c"]
    atr_vals = []
    for i in range(1, len(c1h)):
        tr = max(
            c1h[i]["h"] - c1h[i]["l"],
            abs(c1h[i]["h"] - c1h[i - 1]["c"]),
            abs(c1h[i]["l"] - c1h[i - 1]["c"]),
        )
        atr_vals.append(tr)
    atr = sum(atr_vals[-14:]) / min(len(atr_vals), 14) if atr_vals else current_price * 0.02

    # Entry = current price
    # Target = +2.5 ATR (expecting 10-20% pump)
    # Stop = -1.2 ATR (tight stop, R:R ~2:1)
    entry = current_price
    target = entry + (atr * 2.5)
    stop = entry - (atr * 1.2)
    rr_ratio = (target - entry) / (entry - stop) if entry > stop else 0

    return {
        "symbol": sym,
        "score": score,
        "signals": signals,
        "entry_price": round(entry, 8),
        "target_price": round(target, 8),
        "stop_price": round(stop, 8),
        "rr_ratio": round(rr_ratio, 2),
        "rsi_1h": round(rsi, 1),
        "bb_width_pct": round(bbw * 100, 2),
        "vol_building_ratio": round(vol_building_ratio, 2),
        "trade_count_ratio": round(trade_ratio, 2),
        "whale_candles_3h": whale_candles,
        "price_range_3h_pct": round(price_range * 100, 2),
        "avg_15m_volume_usd": round(avg_vol_15m, 2),
        "atr_1h": round(atr, 8),
    }


def run() -> list[dict]:
    """Main entry point. Scans all USDT pairs for pre-pump signals."""
    log.info("Top Gainer Predictor starting scan...")
    start = time.time()

    # Step 1: Get candidate symbols
    candidates = _get_usdt_candidates()
    log.info("Got %d USDT candidates (>$%dk vol, <+8%% change)", len(candidates), MIN_24H_VOLUME_USD // 1000)

    if not candidates:
        log.warning("No candidates found")
        return []

    # Step 2: Analyze each candidate
    predictions = []
    scanned = 0
    for cand in candidates:
        sym = cand["symbol"]
        try:
            result = _analyze_symbol(sym)
            if result:
                result["24h_change_pct"] = cand["change_pct"]
                result["24h_volume_usd"] = cand["volume_usd"]
                predictions.append(result)
        except Exception as exc:
            log.debug("Error analyzing %s: %s", sym, exc)

        scanned += 1
        # Rate limit: ~5 requests per symbol (ticker + 15m + 1h klines)
        # Binance limit ~1200/min, be conservative
        if scanned % 10 == 0:
            time.sleep(1.0)
            log.info("  scanned %d/%d, found %d signals so far", scanned, len(candidates), len(predictions))

    # Step 3: Sort by score and cap
    predictions.sort(key=lambda x: x["score"], reverse=True)
    predictions = predictions[:MAX_PREDICTIONS]

    # Step 4: Save results
    output = {
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "candidates_scanned": scanned,
        "predictions_found": len(predictions),
        "min_score_threshold": MIN_SCORE,
        "scoring_weights": {
            "volume_building": W_VOLUME_BUILDING,
            "whale_candle": W_WHALE_CANDLE,
            "squeeze": W_SQUEEZE,
            "trade_count_surge": W_TRADE_COUNT_SURGE,
            "rsi_oversold": W_RSI_OVERSOLD,
            "quiet_accumulation": W_QUIET_ACCUMULATION,
            "momentum_ignition": W_MOMENTUM_IGNITION,
        },
        "predictions": predictions,
    }

    out_path = _DATA / "top_gainer_predictions.json"
    _DATA.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    elapsed = time.time() - start
    log.info(
        "Scan complete: %d predictions from %d candidates in %.1fs",
        len(predictions), scanned, elapsed,
    )

    # Log top picks
    for p in predictions[:5]:
        log.info(
            "  %s score=%d signals=%s rsi=%.0f bbw=%.1f%% vol_build=%.1fx",
            p["symbol"], p["score"], "+".join(p["signals"]),
            p["rsi_1h"], p["bb_width_pct"], p["vol_building_ratio"],
        )

    return predictions


if __name__ == "__main__":
    run()
