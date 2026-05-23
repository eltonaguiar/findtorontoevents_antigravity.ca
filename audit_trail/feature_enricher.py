#!/usr/bin/env python3
"""
Feature Enricher — Computes RSI and Volume Ratio for picks missing them.

This module fetches Binance kline data and computes technical indicators
for pick sources that don't provide them (copy_trader_intel, PM signals, etc.)

Usage:
    from audit_trail.feature_enricher import enrich_pick_with_features
    enriched_pick = enrich_pick_with_features(pick)
"""

import json
import logging
import urllib.request
from typing import Optional

log = logging.getLogger("feature_enricher")

# Cache for computed features to avoid redundant API calls
_feature_cache = {}


def _fetch_klines(symbol: str, interval: str = "1h", limit: int = 30) -> Optional[list]:
    """Fetch Binance kline (candlestick) data.
    
    Returns list of [timestamp, open, high, low, close, volume, ...]
    """
    symbol = symbol.upper().replace("-", "").replace("/", "")
    if not symbol.endswith("USDT"):
        symbol += "USDT"
    
    # Try multiple Binance endpoints
    endpoints = [
        f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}",
        f"https://api1.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}",
        f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}",
    ]
    
    for url in endpoints:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "FeatureEnricher/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                if data and len(data) >= 15:  # Need at least 15 candles for RSI
                    return data
        except Exception as e:
            log.debug("Klines fetch failed for %s: %s", url, e)
            continue
    
    return None


def _compute_rsi(closes: list, period: int = 14) -> Optional[float]:
    """Compute RSI from closing prices."""
    if len(closes) < period + 1:
        return None
    
    gains = []
    losses = []
    
    for i in range(1, len(closes)):
        change = closes[i] - closes[i-1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))
    
    if len(gains) < period:
        return None
    
    # Calculate initial averages
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    # Calculate smoothed RSI
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi, 2)


def _compute_volume_ratio(volumes: list, period: int = 20) -> Optional[float]:
    """Compute current volume vs average ratio."""
    if len(volumes) < period + 1:
        return None
    
    current_vol = volumes[-1]
    avg_vol = sum(volumes[-(period+1):-1]) / period
    
    if avg_vol == 0:
        return 1.0
    
    ratio = current_vol / avg_vol
    return round(ratio, 2)


def enrich_pick_with_features(pick: dict) -> dict:
    """Enrich a pick with RSI and volume_ratio if missing.
    
    Args:
        pick: Pick dictionary with at least 'symbol' key
        
    Returns:
        Enriched pick with rsi_at_entry and volume_ratio added if missing
    """
    symbol = pick.get("symbol", "")
    if not symbol:
        return pick
    
    # Check if already has features
    has_rsi = pick.get("rsi_at_entry") is not None or pick.get("rsi") is not None or pick.get("rsi_14") is not None
    has_vol = pick.get("volume_ratio") is not None or pick.get("vol_ratio") is not None
    
    if has_rsi and has_vol:
        return pick  # Nothing to do
    
    # Check cache
    cache_key = symbol.upper().replace("-", "").replace("/", "")
    if cache_key in _feature_cache:
        cached = _feature_cache[cache_key]
        if not has_rsi and "rsi" in cached:
            pick["rsi_at_entry"] = cached["rsi"]
        if not has_vol and "volume_ratio" in cached:
            pick["volume_ratio"] = cached["volume_ratio"]
        return pick
    
    # Fetch klines and compute
    klines = _fetch_klines(symbol)
    if not klines:
        return pick
    
    try:
        closes = [float(k[4]) for k in klines]  # Index 4 = close
        volumes = [float(k[5]) for k in klines]  # Index 5 = volume
        
        cache_entry = {}
        
        if not has_rsi:
            rsi = _compute_rsi(closes)
            if rsi is not None:
                pick["rsi_at_entry"] = rsi
                cache_entry["rsi"] = rsi
                log.debug("Computed RSI %.2f for %s", rsi, symbol)
        
        if not has_vol:
            vol_ratio = _compute_volume_ratio(volumes)
            if vol_ratio is not None:
                pick["volume_ratio"] = vol_ratio
                cache_entry["volume_ratio"] = vol_ratio
                log.debug("Computed volume ratio %.2fx for %s", vol_ratio, symbol)
        
        # Cache results
        if cache_entry:
            _feature_cache[cache_key] = cache_entry
            
    except Exception as e:
        log.warning("Feature computation failed for %s: %s", symbol, e)
    
    return pick


def enrich_picks_batch(picks: list) -> list:
    """Enrich a batch of picks with features.
    
    Args:
        picks: List of pick dictionaries
        
    Returns:
        List of enriched picks
    """
    enriched = []
    for pick in picks:
        try:
            enriched.append(enrich_pick_with_features(pick))
        except Exception as e:
            log.warning("Failed to enrich pick %s: %s", pick.get("symbol", "?"), e)
            enriched.append(pick)
    return enriched


if __name__ == "__main__":
    # Test
    logging.basicConfig(level=logging.INFO)
    test_pick = {"symbol": "BTCUSDT", "direction": "LONG"}
    enriched = enrich_pick_with_features(test_pick)
    print(f"Enriched: {enriched}")
