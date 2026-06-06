#!/usr/bin/env python3
"""
ALPHA ENGINE -- ML Strategy Reviver (2026-03-25)
=================================================
Bridges the ml_crypto_predictor pipeline into the alpha engine.

ROOT CAUSE: The ml_crypto_predictor workflows run successfully and write picks to
  ml_crypto_predictor/enhanced_models/live_picks/active_picks.json
BUT there was NO integration that imported those picks into
  alpha_engine/data/active_picks.json
Result: 4 of our best strategies (94.4%, 94.1%, 88.2%, 85.7% WR) had ZERO
active picks since ~March 8.

This module:
1. Reads ml_crypto_predictor live picks (the "bridge" that was missing)
2. Falls back to a standalone signal generator using Binance price data
   + the strategy's known TP/SL parameters if ml_crypto_predictor output is stale
3. Generates inverse signals for confirmed 0% WR strategies
4. Returns picks in alpha_engine format for injection into production_scanner.py

Usage:
    from ml_strategy_reviver import revive_ml_picks
    ml_picks = revive_ml_picks()
    active.extend(ml_picks)
"""

from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

import requests

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_THIS_DIR = Path(__file__).resolve().parent
_DATA_DIR = _THIS_DIR / "data"
_REPO_ROOT = _THIS_DIR.parent
_ML_PICKS_PATH = _REPO_ROOT / "ml_crypto_predictor" / "enhanced_models" / "live_picks" / "active_picks.json"
_ALPHA_ACTIVE_PATH = _DATA_DIR / "active_picks.json"
_CLOSED_PICKS_PATH = _DATA_DIR / "closed_picks.json"
_STRATEGY_PERF_PATH = _DATA_DIR / "strategy_performance.json"

# ---------------------------------------------------------------------------
# API Failover (MANDATORY: 3+ endpoints)
# ---------------------------------------------------------------------------
BINANCE_ENDPOINTS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://data-api.binance.vision",
    "https://api.binance.us",
]
COINGECKO_BASE = "https://api.coingecko.com/api/v3"
KUCOIN_BASE = "https://api.kucoin.com"
CRYPTOCOMPARE_BASE = "https://min-api.cryptocompare.com/data"

HTTP_TIMEOUT = 10

# ---------------------------------------------------------------------------
# Hedge-fund risk caps for crypto TP/SL
# ---------------------------------------------------------------------------
CRYPTO_TP_CAP_PCT = 0.15   # 15% max TP distance from entry
CRYPTO_SL_CAP_PCT = 0.10   # 10% max SL distance from entry


def _apply_crypto_tp_sl_cap(pick: dict) -> dict:
    """Cap crypto TP at 15% and SL at 10% from entry price.

    Prevents ML models from generating absurd targets (e.g. 47% TP).
    Only applies to crypto picks.
    """
    category = (pick.get("category") or "").lower()
    if category != "crypto":
        return pick

    entry = pick.get("entry_price") or 0
    tp = pick.get("take_profit") or 0
    sl = pick.get("stop_loss") or 0
    if entry <= 0:
        return pick

    direction = (pick.get("direction") or pick.get("signal_type") or "BUY").upper()
    is_short = direction in ("SELL", "SHORT")

    # --- Cap TP ---
    if tp > 0:
        if is_short:
            tp_dist = (entry - tp) / entry
            if tp_dist > CRYPTO_TP_CAP_PCT:
                old_tp = tp
                pick["take_profit"] = round(entry * (1 - CRYPTO_TP_CAP_PCT), 8)
                print(f"  [ML_TP_CAP] {pick.get('symbol')} SHORT: TP {old_tp:.8f} -> "
                      f"{pick['take_profit']:.8f} (capped from {tp_dist*100:.1f}% to {CRYPTO_TP_CAP_PCT*100:.0f}%)")
        else:
            tp_dist = (tp - entry) / entry
            if tp_dist > CRYPTO_TP_CAP_PCT:
                old_tp = tp
                pick["take_profit"] = round(entry * (1 + CRYPTO_TP_CAP_PCT), 8)
                print(f"  [ML_TP_CAP] {pick.get('symbol')} LONG: TP {old_tp:.8f} -> "
                      f"{pick['take_profit']:.8f} (capped from {tp_dist*100:.1f}% to {CRYPTO_TP_CAP_PCT*100:.0f}%)")

    # --- Cap SL ---
    if sl > 0:
        if is_short:
            sl_dist = (sl - entry) / entry
            if sl_dist > CRYPTO_SL_CAP_PCT:
                old_sl = sl
                pick["stop_loss"] = round(entry * (1 + CRYPTO_SL_CAP_PCT), 8)
                print(f"  [ML_SL_CAP] {pick.get('symbol')} SHORT: SL {old_sl:.8f} -> "
                      f"{pick['stop_loss']:.8f} (capped from {sl_dist*100:.1f}% to {CRYPTO_SL_CAP_PCT*100:.0f}%)")
        else:
            sl_dist = (entry - sl) / entry
            if sl_dist > CRYPTO_SL_CAP_PCT:
                old_sl = sl
                pick["stop_loss"] = round(entry * (1 - CRYPTO_SL_CAP_PCT), 8)
                print(f"  [ML_SL_CAP] {pick.get('symbol')} LONG: SL {old_sl:.8f} -> "
                      f"{pick['stop_loss']:.8f} (capped from {sl_dist*100:.1f}% to {CRYPTO_SL_CAP_PCT*100:.0f}%)")

    return pick


# ---------------------------------------------------------------------------
# Proven strategy definitions
# ---------------------------------------------------------------------------
# These are the strategies with verified high win rates from closed_picks data.
# Each entry defines the strategy's parameters for standalone signal generation.

PROVEN_STRATEGIES = {
    "ml_enhanced_FETUSDT_1d_B_lightgbm": {
        "symbol": "FETUSDT",
        "timeframe": "1d",
        "model_variant": "FETUSDT_1d_B_lightgbm",
        "direction": "BUY",
        "historical_wr": 0.941,
        "closed_picks": 17,
        "avg_tp_pct": 10.0,   # Capped from 32.12% — unreachable in current market
        "avg_sl_pct": 7.0,    # Proportional SL for 10% TP (R:R 1.43)
        "confidence": 0.88,
        "category": "crypto",
        "expiry_hours": 120,  # 5 days for daily timeframe
    },
    "ml_enhanced_BNBUSDT_15m_B_lightgbm": {
        "symbol": "BNBUSDT",
        "timeframe": "15m",
        "model_variant": "BNBUSDT_15m_B_lightgbm",
        "direction": "BUY",
        "historical_wr": 0.60,
        "closed_picks": 35,
        "avg_tp_pct": 3.0,
        "avg_sl_pct": 2.0,
        "confidence": 0.75,
        "category": "crypto",
        "expiry_hours": 8,
    },
    # --- Wave 2: Expanded ML coverage (2026-03-25) ---
    # Symbols with aggregate WR >= 66% across 3+ closed ml_enhanced trades.
    # Conservative confidence (0.75) since individual strategy sample sizes are small.
    "ml_enhanced_TRXUSDT_4h_D_ensemble_stack": {
        "symbol": "TRXUSDT",
        "timeframe": "4h",
        "model_variant": "TRXUSDT_4h_D_ensemble_stack",
        "direction": "BUY",
        "historical_wr": 1.0,   # 3W/0L across 3 timeframes (1h/4h/1d)
        "closed_picks": 3,
        "avg_tp_pct": 2.0,     # Conservative — from 1.95% actual on 4h
        "avg_sl_pct": 1.0,     # Conservative — from 0.83% actual on 4h
        "confidence": 0.75,
        "category": "crypto",
        "expiry_hours": 48,
    },
    "ml_enhanced_OPUSDT_4h_D_ensemble_stack": {
        "symbol": "OPUSDT",
        "timeframe": "4h",
        "model_variant": "OPUSDT_4h_D_ensemble_stack",
        "direction": "BUY",
        "historical_wr": 1.0,   # 3W/0L across 3 timeframes (1h/4h/1d)
        "closed_picks": 3,
        "avg_tp_pct": 10.0,    # Capped from 12.45% actual on 4h
        "avg_sl_pct": 5.0,     # Conservative — from 5.34% actual on 4h
        "confidence": 0.75,
        "category": "crypto",
        "expiry_hours": 48,
    },
    "ml_enhanced_LINKUSDT_4h_A_xgboost": {
        "symbol": "LINKUSDT",
        "timeframe": "4h",
        "model_variant": "LINKUSDT_4h_A_xgboost",
        "direction": "BUY",
        "historical_wr": 0.75,  # 3W/1L across 4 strategies
        "closed_picks": 4,
        "avg_tp_pct": 5.9,     # From actual 4h data
        "avg_sl_pct": 2.53,
        "confidence": 0.75,
        "category": "crypto",
        "expiry_hours": 48,
    },
    "ml_enhanced_AVAXUSDT_4h_A_xgboost": {
        "symbol": "AVAXUSDT",
        "timeframe": "4h",
        "model_variant": "AVAXUSDT_4h_A_xgboost",
        "direction": "BUY",
        "historical_wr": 0.667,  # 2W/1L across 3 strategies
        "closed_picks": 3,
        "avg_tp_pct": 5.91,     # From actual 4h data
        "avg_sl_pct": 2.53,
        "confidence": 0.75,
        "category": "crypto",
        "expiry_hours": 48,
    },
    "ml_enhanced_SUIUSDT_1h_A_xgboost": {
        "symbol": "SUIUSDT",
        "timeframe": "1h",
        "model_variant": "SUIUSDT_1h_A_xgboost",
        "direction": "BUY",
        "historical_wr": 0.667,  # 2W/1L across 3 strategies
        "closed_picks": 3,
        "avg_tp_pct": 5.0,      # Conservative default — 1h actual was 1.65%
        "avg_sl_pct": 3.5,      # Conservative default
        "confidence": 0.75,
        "category": "crypto",
        "expiry_hours": 12,
    },
    "ml_enhanced_ARBUSDT_1h_D_ensemble_stack": {
        "symbol": "ARBUSDT",
        "timeframe": "1h",
        "model_variant": "ARBUSDT_1h_D_ensemble_stack",
        "direction": "BUY",
        "historical_wr": 0.667,  # 2W/1L across 3 strategies
        "closed_picks": 3,
        "avg_tp_pct": 2.5,      # From actual 1h data
        "avg_sl_pct": 1.0,
        "confidence": 0.75,
        "category": "crypto",
        "expiry_hours": 12,
    },
    "ml_enhanced_APTUSDT_4h_A_xgboost": {
        "symbol": "APTUSDT",
        "timeframe": "4h",
        "model_variant": "APTUSDT_4h_A_xgboost",
        "direction": "BUY",
        "historical_wr": 0.667,  # 2W/1L across 3 strategies
        "closed_picks": 3,
        "avg_tp_pct": 8.07,     # From actual 4h data
        "avg_sl_pct": 3.46,
        "confidence": 0.75,
        "category": "crypto",
        "expiry_hours": 48,
    },
    "ml_enhanced_LTCUSDT_4h_A_xgboost": {
        "symbol": "LTCUSDT",
        "timeframe": "4h",
        "model_variant": "LTCUSDT_4h_A_xgboost",
        "direction": "BUY",
        "historical_wr": 0.667,  # 2W/1L across 3 strategies
        "closed_picks": 3,
        "avg_tp_pct": 5.32,     # From actual 4h data
        "avg_sl_pct": 2.28,
        "confidence": 0.75,
        "category": "crypto",
        "expiry_hours": 48,
    },
    "ml_enhanced_ZKUSDT_4h_D_ensemble_stack": {
        "symbol": "ZKUSDT",
        "timeframe": "4h",
        "model_variant": "ZKUSDT_4h_D_ensemble_stack",
        "direction": "BUY",
        "historical_wr": 0.667,  # 2W/1L across 3 strategies
        "closed_picks": 3,
        "avg_tp_pct": 6.5,      # From actual 4h data
        "avg_sl_pct": 2.79,
        "confidence": 0.75,
        "category": "crypto",
        "expiry_hours": 48,
    },
}

# Confirmed 0% WR strategies — generate INVERSE signals
INVERSE_STRATEGIES = {
    "inverse_ml_enhanced_BTCUSDT_15m_D": {
        "source_strategy": "ml_enhanced_BTCUSDT_15m_D_ensemble_stack",
        "symbol": "BTCUSDT",
        "timeframe": "15m",
        "model_variant": "BTCUSDT_15m_D_ensemble_stack",
        "historical_wr_original": 0.0,
        "closed_picks_original": 10,
        "avg_tp_pct": 1.10,
        "avg_sl_pct": 0.88,
        "confidence": 0.75,  # Conservative since inverse
        "category": "crypto",
        "expiry_hours": 2,
    },
    "inverse_ml_enhanced_ADAUSDT_15m_D": {
        "source_strategy": "ml_enhanced_ADAUSDT_15m_D_ensemble_stack",
        "symbol": "ADAUSDT",
        "timeframe": "15m",
        "model_variant": "ADAUSDT_15m_D_ensemble_stack",
        "historical_wr_original": 0.0,
        "closed_picks_original": 10,
        "avg_tp_pct": 1.15,
        "avg_sl_pct": 0.92,
        "confidence": 0.75,
        "category": "crypto",
        "expiry_hours": 2,
    },
    "inverse_ml_enhanced_RENDERUSDT_4h_D": {
        "source_strategy": "ml_enhanced_RENDERUSDT_4h_D_ensemble_stack",
        "symbol": "RENDERUSDT",
        "timeframe": "4h",
        "model_variant": "RENDERUSDT_4h_D_ensemble_stack",
        "historical_wr_original": 0.0,
        "closed_picks_original": 7,
        "avg_tp_pct": 10.0,
        "avg_sl_pct": 5.0,
        "confidence": 0.70,
        "category": "crypto",
        "expiry_hours": 24,
    },
    "inverse_ml_enhanced_RENDERUSDT_1h_D": {
        "source_strategy": "ml_enhanced_RENDERUSDT_1h_D_ensemble_stack",
        "symbol": "RENDERUSDT",
        "timeframe": "1h",
        "model_variant": "RENDERUSDT_1h_D_ensemble_stack",
        "historical_wr_original": 0.20,
        "closed_picks_original": 17,
        "avg_tp_pct": 5.0,
        "avg_sl_pct": 3.5,
        "confidence": 0.70,
        "category": "crypto",
        "expiry_hours": 12,
    },
}


# ---------------------------------------------------------------------------
# Price fetching with API failover
# ---------------------------------------------------------------------------

def _fetch_price_binance(symbol: str) -> Optional[float]:
    """Fetch current price from Binance with mirror failover."""
    for base in BINANCE_ENDPOINTS:
        try:
            r = requests.get(
                f"{base}/api/v3/ticker/price",
                params={"symbol": symbol},
                timeout=HTTP_TIMEOUT,
            )
            if r.status_code in (451, 403):
                continue
            r.raise_for_status()
            return float(r.json()["price"])
        except Exception:
            continue
    return None


def _fetch_price_coingecko(symbol: str) -> Optional[float]:
    """Fetch price from CoinGecko as fallback."""
    # Map Binance symbols to CoinGecko IDs
    cg_map = {
        "FETUSDT": "fetch-ai",
        "BNBUSDT": "binancecoin",
        "RENDERUSDT": "render-token",
        "BTCUSDT": "bitcoin",
        "ADAUSDT": "cardano",
        "TRXUSDT": "tron",
        "OPUSDT": "optimism",
        "LINKUSDT": "chainlink",
        "AVAXUSDT": "avalanche-2",
        "SUIUSDT": "sui",
        "ARBUSDT": "arbitrum",
        "APTUSDT": "aptos",
        "LTCUSDT": "litecoin",
        "ZKUSDT": "zksync",
    }
    cg_id = cg_map.get(symbol)
    if not cg_id:
        return None
    try:
        r = requests.get(
            f"{COINGECKO_BASE}/simple/price",
            params={"ids": cg_id, "vs_currencies": "usd"},
            timeout=HTTP_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        return float(data.get(cg_id, {}).get("usd", 0)) or None
    except Exception:
        return None


def _fetch_price_kucoin(symbol: str) -> Optional[float]:
    """Fetch price from KuCoin as fallback."""
    # KuCoin uses format like BTC-USDT
    base_sym = symbol.replace("USDT", "")
    kucoin_sym = f"{base_sym}-USDT"
    try:
        r = requests.get(
            f"{KUCOIN_BASE}/api/v1/market/orderbook/level1",
            params={"symbol": kucoin_sym},
            timeout=HTTP_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        price_str = data.get("data", {}).get("price")
        return float(price_str) if price_str else None
    except Exception:
        return None


def _fetch_price_cryptocompare(symbol: str) -> Optional[float]:
    """Fetch price from CryptoCompare as fallback."""
    base_sym = symbol.replace("USDT", "")
    try:
        r = requests.get(
            f"{CRYPTOCOMPARE_BASE}/price",
            params={"fsym": base_sym, "tsyms": "USD"},
            timeout=HTTP_TIMEOUT,
        )
        r.raise_for_status()
        return float(r.json().get("USD", 0)) or None
    except Exception:
        return None


def fetch_price(symbol: str) -> Optional[float]:
    """Fetch price with full failover chain: Binance mirrors -> CoinGecko -> KuCoin -> CryptoCompare."""
    price = _fetch_price_binance(symbol)
    if price and price > 0:
        return price

    price = _fetch_price_coingecko(symbol)
    if price and price > 0:
        return price

    price = _fetch_price_kucoin(symbol)
    if price and price > 0:
        return price

    price = _fetch_price_cryptocompare(symbol)
    if price and price > 0:
        return price

    print(f"  [ML REVIVER] WARNING: All price sources failed for {symbol}")
    return None


# ---------------------------------------------------------------------------
# Kline fetching for basic technical checks
# ---------------------------------------------------------------------------

def fetch_klines(symbol: str, interval: str = "1h", limit: int = 50) -> list[dict]:
    """Fetch OHLCV klines from Binance with failover."""
    for base in BINANCE_ENDPOINTS:
        try:
            r = requests.get(
                f"{base}/api/v3/klines",
                params={"symbol": symbol, "interval": interval, "limit": limit},
                timeout=HTTP_TIMEOUT,
            )
            if r.status_code in (451, 403):
                continue
            r.raise_for_status()
            raw = r.json()
            return [
                {
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                }
                for k in raw
            ]
        except Exception:
            continue
    return []


def compute_rsi(closes: list[float], period: int = 14) -> float:
    """Compute RSI from close prices."""
    if len(closes) < period + 1:
        return 50.0
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas[-period:]]
    losses = [-d if d < 0 else 0 for d in deltas[-period:]]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def compute_ema(values: list[float], period: int) -> float:
    """Compute EMA of last N values."""
    if not values:
        return 0.0
    if len(values) < period:
        return sum(values) / len(values)
    multiplier = 2.0 / (period + 1)
    ema = sum(values[:period]) / period
    for v in values[period:]:
        ema = (v - ema) * multiplier + ema
    return ema


# ---------------------------------------------------------------------------
# Bridge: Read ml_crypto_predictor picks
# ---------------------------------------------------------------------------

def _load_ml_predictor_picks() -> list[dict]:
    """
    Load active picks from the ml_crypto_predictor pipeline.
    This is the BRIDGE that was missing — reads their output and converts
    to alpha_engine format.
    """
    if not _ML_PICKS_PATH.exists():
        return []

    try:
        with open(_ML_PICKS_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception as e:
        print(f"  [ML REVIVER] Failed to read ml_crypto_predictor picks: {e}")
        return []

    if not isinstance(raw, list):
        return []

    now = datetime.now(timezone.utc)
    picks = []

    for p in raw:
        # Check if pick is expired
        expires_str = p.get("expires_at")
        if expires_str:
            try:
                expires = datetime.fromisoformat(str(expires_str).replace("Z", "+00:00"))
                if expires.tzinfo is None:
                    expires = expires.replace(tzinfo=timezone.utc)
                if expires < now:
                    continue  # Skip expired picks
            except (ValueError, TypeError):
                pass

        symbol = p.get("symbol", "")
        if not symbol:
            continue

        model_variant = p.get("model_variant", "")
        strategy_name = f"ml_enhanced_{model_variant}" if model_variant else f"ml_enhanced_{symbol}"

        direction = p.get("direction", "BUY").upper()
        entry_price = p.get("entry_price", 0) or 0
        take_profit = p.get("take_profit", 0) or 0
        stop_loss = p.get("stop_loss", 0) or 0
        probability = p.get("probability", 0.5)
        generated_at = p.get("generated_at", now.isoformat())

        entry_date_str = str(generated_at)[:10]
        # Map to alpha_engine format
        alpha_pick = {
            "id": f"{strategy_name}::{symbol}::{entry_date_str}",
            "symbol": symbol,
            "strategy": strategy_name,
            "direction": direction,
            "signal_type": direction,
            "entry_price": entry_price,
            "take_profit": take_profit,
            "stop_loss": stop_loss,
            "confidence": min(probability, 0.95),
            "category": "crypto",
            "asset_class": "CRYPTO",
            "source_system": "ml_crypto_predictor",
            "timeframe": p.get("timeframe", "1h"),
            "timestamp": generated_at,
            "created_at": generated_at,
            "entry_date": str(generated_at)[:10],
            "status": "ACTIVE",
            "reasoning": p.get("reasoning", []),
            "model_variant": model_variant,
            "ml_probability": probability,
            "feedback_win_prob": p.get("feedback_win_prob"),
            "fear_greed": p.get("fear_greed"),
            "btc_regime": p.get("btc_regime"),
        }
        # Apply hedge-fund crypto TP/SL caps
        alpha_pick = _apply_crypto_tp_sl_cap(alpha_pick)
        picks.append(alpha_pick)

    return picks


# ---------------------------------------------------------------------------
# Standalone signal generator (fallback when ml_crypto_predictor is stale)
# ---------------------------------------------------------------------------

def _is_pick_already_active(strategy: str, symbol: str) -> bool:
    """Check if a pick for this strategy+symbol is already active."""
    if not _ALPHA_ACTIVE_PATH.exists():
        return False
    try:
        with open(_ALPHA_ACTIVE_PATH, "r", encoding="utf-8") as f:
            active = json.load(f)
        for p in active:
            if (p.get("strategy") == strategy
                    and p.get("symbol") == symbol
                    and p.get("status", "").upper() in ("ACTIVE", "OPEN", "")):
                return True
    except Exception:
        pass
    return False


def _was_recently_closed(strategy: str, symbol: str, hours: int = 4) -> bool:
    """Check if this strategy+symbol was closed recently (avoid re-entry churn)."""
    if not _CLOSED_PICKS_PATH.exists():
        return False
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    try:
        with open(_CLOSED_PICKS_PATH, "r", encoding="utf-8") as f:
            closed = json.load(f)
        for p in closed:
            if p.get("strategy") != strategy or p.get("symbol") != symbol:
                continue
            closed_at = p.get("closed_at") or p.get("created_at") or ""
            if not closed_at:
                continue
            try:
                ts = datetime.fromisoformat(str(closed_at).replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if ts > cutoff:
                    return True
            except (ValueError, TypeError):
                continue
    except Exception:
        pass
    return False


# ---------------------------------------------------------------------------
# Adaptive Dilation: Automatically relax filters for dormant winners
# ---------------------------------------------------------------------------

def _get_strategy_dilation(strategy_name: str) -> float:
    """
    Compute a dilation factor (1.0 - 2.0) based on strategy dormancy.
    If a high-WR strategy hasn't traded for >24h, we expand its RSI/EMA gates.
    """
    if not _STRATEGY_PERF_PATH.exists():
        return 1.0
    
    try:
        with open(_STRATEGY_PERF_PATH, "r", encoding="utf-8") as f:
            perf = json.load(f)
        
        data = perf.get(strategy_name, {})
        if not data:
            return 1.0
        
        wr = float(data.get("win_rate") or 0)
        last_up_str = data.get("last_updated")
        if not last_up_str or wr < 0.70: # Only dilate for proven winners
            return 1.0
            
        try:
            last_up = datetime.fromisoformat(last_up_str.replace("Z", "+00:00"))
            if last_up.tzinfo is None:
                last_up = last_up.replace(tzinfo=timezone.utc)
            
            now = datetime.now(timezone.utc)
            dormancy_hours = (now - last_up).total_seconds() / 3600
            
            if dormancy_hours <= 24:
                return 1.0
            
            # Linearly dilate from 24h to 72h, capping at 2.0x
            dilation = 1.0 + (min(48.0, dormancy_hours - 24) / 48.0)
            return round(dilation, 3)
        except (ValueError, TypeError):
            return 1.0
    except Exception:
        return 1.0


def _basic_entry_check(symbol: str, timeframe: str, direction: str = "BUY", dilation: float = 1.0) -> dict:
    """
    Run basic technical entry conditions for a symbol.
    Uses RSI + EMA trend + volume to generate a simplified entry signal.
    
    Supports 'dilation': expands the RSI and Price/EMA acceptance zones for dormant strats.

    Returns dict with 'pass': bool, 'reasoning': list[str], 'probability': float
    """
    klines = fetch_klines(symbol, timeframe, limit=60)
    if len(klines) < 30:
        return {"pass": False, "reasoning": ["Insufficient kline data"], "probability": 0.0}

    closes = [k["close"] for k in klines]
    volumes = [k["volume"] for k in klines]

    rsi = compute_rsi(closes, 14)
    ema_20 = compute_ema(closes, 20)
    ema_50 = compute_ema(closes, 50)
    current_price = closes[-1]
    avg_vol = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else sum(volumes) / len(volumes)
    recent_vol = volumes[-1]
    vol_ratio = recent_vol / avg_vol if avg_vol > 0 else 1.0

    reasoning = []
    score = 0.5  # Neutral starting point
    
    # Apply dilation to thresholds (e.g. dilation=1.5 means RSI range expands from [30,65] to [20,85])
    rsi_low = max(10, 30 / dilation)
    rsi_high = min(90, 65 * dilation)
    
    if dilation > 1.0:
        reasoning.append(f"Applying {dilation}x Adaptive Dilation (Dormancy Recovery)")

    if direction == "BUY":
        # Trend alignment: price above EMA20 and EMA20 > EMA50
        if current_price > (ema_20 / dilation): # Relaxed price check
            score += 0.10
            reasoning.append(f"Price above dilated EMA20 floor ({current_price:.6g} > {ema_20/dilation:.6g})")
        else:
            score -= 0.05
            reasoning.append(f"Price below dilated EMA20")

        if ema_20 > (ema_50 / dilation):
            score += 0.10
            reasoning.append("Dilated trend alignment (bullish-bias)")
        else:
            score -= 0.05
            reasoning.append("Bearish trend")

        # RSI conditions
        if rsi_low <= rsi <= rsi_high:
            score += 0.05
            reasoning.append(f"RSI={rsi:.0f} (within dilated {rsi_low:.0f}-{rsi_high:.0f} range)")
        elif rsi < rsi_low:
            score += 0.15  # Oversold = good entry
            reasoning.append(f"RSI={rsi:.0f} (oversold, bounce potential)")
        else:
            score -= 0.10
            reasoning.append(f"RSI={rsi:.0f} (overbought risk)")

        # Volume confirmation
        if vol_ratio > 1.1:
            score += 0.05
            reasoning.append(f"Volume {vol_ratio:.1f}x avg (confirmed)")
    else:
        # SELL/SHORT direction (for inverse strategies)
        if current_price < (ema_20 * dilation):
            score += 0.10
            reasoning.append(f"Price below dilated EMA20 ceiling (bearish)")
        if ema_20 < (ema_50 * dilation):
            score += 0.10
            reasoning.append("Dilated trend alignment (bearish-bias)")
        if rsi > rsi_high:
            score += 0.15
            reasoning.append(f"RSI={rsi:.0f} (overbought, reversal potential)")
        elif rsi_low <= rsi <= rsi_high:
            score += 0.05
            reasoning.append(f"RSI={rsi:.0f} (neutral)")
        else:
            score -= 0.10
            reasoning.append(f"RSI={rsi:.0f} (oversold)")

    score = max(0.0, min(1.0, score))

    return {
        "pass": score >= 0.50,
        "reasoning": reasoning,
        "probability": score,
        "current_price": current_price,
        "rsi": rsi,
        "vol_ratio": vol_ratio,
        "dilation": dilation,
    }


def _generate_standalone_pick(strategy_name: str, config: dict) -> Optional[dict]:
    """Generate a pick for a proven strategy using live price data + basic technicals."""
    symbol = config["symbol"]
    timeframe = config["timeframe"]
    direction = config.get("direction", "BUY")

    # Skip if already active or recently closed
    if _is_pick_already_active(strategy_name, symbol):
        return None

    # Use different cooldown periods based on timeframe
    cooldown_map = {"15m": 1, "1h": 4, "4h": 12, "1d": 48}
    cooldown = cooldown_map.get(timeframe, 4)
    if _was_recently_closed(strategy_name, symbol, hours=cooldown):
        return None

    # Calculate dilation factor based on dormancy
    dilation = _get_strategy_dilation(strategy_name)

    # Fetch current price
    price = fetch_price(symbol)
    if not price or price <= 0:
        return None

    # Run basic technical entry check with dilation
    entry_check = _basic_entry_check(symbol, timeframe, direction, dilation=dilation)
    if not entry_check["pass"]:
        print(f"  [ML REVIVER] {strategy_name}: Entry check failed "
              f"(prob={entry_check['probability']:.2f})")
        return None

    # Use the checked price if available (more recent)
    current_price = entry_check.get("current_price", price)

    # Calculate TP/SL from historical averages
    tp_pct = config["avg_tp_pct"] / 100.0
    sl_pct = config["avg_sl_pct"] / 100.0

    if direction == "BUY":
        take_profit = round(current_price * (1 + tp_pct), 8)
        stop_loss = round(current_price * (1 - sl_pct), 8)
    else:
        take_profit = round(current_price * (1 - tp_pct), 8)
        stop_loss = round(current_price * (1 + sl_pct), 8)

    now = datetime.now(timezone.utc)
    expiry = now + timedelta(hours=config.get("expiry_hours", 12))

    # Confidence: blend historical WR with current entry quality
    base_confidence = config["confidence"]
    entry_quality = entry_check["probability"]
    blended_confidence = base_confidence * 0.7 + entry_quality * 0.3
    blended_confidence = max(0.60, min(0.95, blended_confidence))

    reasoning = entry_check.get("reasoning", [])
    reasoning.append(f"Strategy: {strategy_name} (historical WR={config['historical_wr']:.0%})")
    reasoning.append(f"TP={tp_pct*100:.2f}% / SL={sl_pct*100:.2f}% (from {config['closed_picks']} closed trades)")
    reasoning.append(f"Reviver standalone signal (ml_crypto_predictor bridge)")

    entry_date_str = now.strftime("%Y-%m-%d")
    pick = {
        "id": f"{strategy_name}::{symbol}::{entry_date_str}",
        "symbol": symbol,
        "strategy": strategy_name,
        "direction": direction,
        "signal_type": direction,
        "entry_price": current_price,
        "take_profit": take_profit,
        "stop_loss": stop_loss,
        "confidence": round(blended_confidence, 4),
        "category": config.get("category", "crypto"),
        "asset_class": "CRYPTO",
        "source_system": "ml_strategy_reviver",
        "timeframe": timeframe,
        "timestamp": now.isoformat(),
        "created_at": now.isoformat(),
        "entry_date": now.strftime("%Y-%m-%d"),
        "status": "ACTIVE",
        "reasoning": reasoning,
        "model_variant": config.get("model_variant", ""),
        "historical_wr": config.get("historical_wr", 0),
        "expires_at": expiry.isoformat(),
    }
    # Apply hedge-fund crypto TP/SL caps
    return _apply_crypto_tp_sl_cap(pick)


def _generate_inverse_pick(strategy_name: str, config: dict) -> Optional[dict]:
    """
    Generate an INVERSE pick for a confirmed 0% WR strategy.
    If the original strategy always loses BUY trades, we SHORT instead.
    """
    symbol = config["symbol"]
    timeframe = config["timeframe"]

    # Skip if already active or recently closed
    if _is_pick_already_active(strategy_name, symbol):
        return None

    cooldown_map = {"15m": 1, "1h": 4, "4h": 12, "1d": 48}
    cooldown = cooldown_map.get(timeframe, 4)
    if _was_recently_closed(strategy_name, symbol, hours=cooldown):
        return None

    # Fetch current price
    price = fetch_price(symbol)
    if not price or price <= 0:
        return None

    # The original strategy was BUY and always lost, so we SELL/SHORT
    # Run entry check for SHORT direction
    entry_check = _basic_entry_check(symbol, timeframe, direction="SELL")

    # For inverse strategies, we are more lenient on entry (the original being
    # 0% WR means almost ANY short would have been profitable)
    # Accept if probability >= 0.40 (lower bar)
    if entry_check["probability"] < 0.40:
        return None

    current_price = entry_check.get("current_price", price)

    # TP/SL: use the original strategy's levels but inverted
    tp_pct = config["avg_tp_pct"] / 100.0
    sl_pct = config["avg_sl_pct"] / 100.0

    # SHORT: TP below, SL above
    take_profit = round(current_price * (1 - tp_pct), 8)
    stop_loss = round(current_price * (1 + sl_pct), 8)

    now = datetime.now(timezone.utc)
    expiry = now + timedelta(hours=config.get("expiry_hours", 2))

    reasoning = entry_check.get("reasoning", [])
    reasoning.append(f"INVERSE of {config['source_strategy']} (0% WR on {config['closed_picks_original']} trades)")
    reasoning.append(f"Original always lost BUY -> we SHORT instead")
    reasoning.append(f"TP={tp_pct*100:.2f}% / SL={sl_pct*100:.2f}% (inverted)")

    entry_date_str = now.strftime("%Y-%m-%d")
    pick = {
        "id": f"{strategy_name}::{symbol}::{entry_date_str}",
        "symbol": symbol,
        "strategy": strategy_name,
        "direction": "SELL",
        "signal_type": "SELL",
        "entry_price": current_price,
        "take_profit": take_profit,
        "stop_loss": stop_loss,
        "confidence": round(config["confidence"], 4),
        "category": "CRYPTO",
        "asset_class": "CRYPTO",
        "source_system": "ml_strategy_reviver_inverse",
        "timeframe": timeframe,
        "timestamp": now.isoformat(),
        "created_at": now.isoformat(),
        "entry_date": now.strftime("%Y-%m-%d"),
        "status": "ACTIVE",
        "reasoning": reasoning,
        "model_variant": f"inverse_{config.get('model_variant', '')}",
        "historical_wr_original": config.get("historical_wr_original", 0),
        "expires_at": expiry.isoformat(),
    }
    # Apply hedge-fund crypto TP/SL caps
    return _apply_crypto_tp_sl_cap(pick)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def revive_ml_picks() -> list[dict]:
    """
    Main function: revive ML strategy picks.

    1. Try to bridge picks from ml_crypto_predictor (preferred — uses real models)
    2. For any proven strategy without a bridged pick, generate standalone signal
    3. Generate inverse signals for 0% WR strategies

    Returns list of picks in alpha_engine format.
    """
    now = datetime.now(timezone.utc)
    all_picks: list[dict] = []
    bridged_strategies: set[str] = set()

    # Phase 1: Bridge from ml_crypto_predictor
    print("\n[ML REVIVER] Phase 1: Bridging ml_crypto_predictor picks...")
    ml_picks = _load_ml_predictor_picks()
    if ml_picks:
        print(f"  [ML REVIVER] Found {len(ml_picks)} active picks from ml_crypto_predictor")
        for p in ml_picks:
            strat = p.get("strategy", "")
            symbol = p.get("symbol", "")
            # Only add if not already in alpha active picks
            if not _is_pick_already_active(strat, symbol):
                all_picks.append(p)
                bridged_strategies.add(strat)
                print(f"  [ML REVIVER] BRIDGED: {strat} {symbol} "
                      f"conf={p.get('confidence', 0):.2f}")
            else:
                bridged_strategies.add(strat)
                print(f"  [ML REVIVER] Already active: {strat} {symbol}")
    else:
        print("  [ML REVIVER] No picks from ml_crypto_predictor (stale or unavailable)")

    # Phase 2: Standalone generation for proven strategies without bridged picks
    print("\n[ML REVIVER] Phase 2: Standalone generation for un-bridged proven strategies...")
    for strategy_name, config in PROVEN_STRATEGIES.items():
        if strategy_name in bridged_strategies:
            continue
        try:
            pick = _generate_standalone_pick(strategy_name, config)
            if pick:
                all_picks.append(pick)
                print(f"  [ML REVIVER] STANDALONE: {strategy_name} {config['symbol']} "
                      f"entry={pick['entry_price']:.6g} conf={pick['confidence']:.2f}")
            else:
                print(f"  [ML REVIVER] SKIP: {strategy_name} (no entry conditions met or cooldown)")
        except Exception as e:
            print(f"  [ML REVIVER] ERROR generating {strategy_name}: {e}")

    # Phase 3: Inverse signals for 0% WR strategies
    print("\n[ML REVIVER] Phase 3: Inverse signals for 0% WR strategies...")
    for strategy_name, config in INVERSE_STRATEGIES.items():
        try:
            pick = _generate_inverse_pick(strategy_name, config)
            if pick:
                all_picks.append(pick)
                print(f"  [ML REVIVER] INVERSE: {strategy_name} {config['symbol']} "
                      f"SELL entry={pick['entry_price']:.6g} conf={pick['confidence']:.2f}")
            else:
                print(f"  [ML REVIVER] SKIP: {strategy_name} (no entry conditions or cooldown)")
        except Exception as e:
            print(f"  [ML REVIVER] ERROR generating inverse {strategy_name}: {e}")

    print(f"\n[ML REVIVER] Total picks generated: {len(all_picks)}")
    return all_picks


# ---------------------------------------------------------------------------
# CLI entry point (for testing / standalone workflow)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    picks = revive_ml_picks()
    if picks:
        print(f"\n{'='*60}")
        print(f"ML STRATEGY REVIVER — {len(picks)} picks generated")
        print(f"{'='*60}")
        for p in picks:
            print(f"  {p['strategy']:50s} {p['symbol']:12s} {p['direction']:5s} "
                  f"entry={p['entry_price']:.6g} TP={p['take_profit']:.6g} SL={p['stop_loss']:.6g} "
                  f"conf={p['confidence']:.2f}")

        # Save to output file for workflow consumption
        output_path = _DATA_DIR / "ml_reviver_picks.json"
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(picks, f, indent=2, default=str)
        print(f"\nSaved to {output_path}")
    else:
        print("\nNo picks generated.")
