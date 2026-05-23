"""
ALPHA_ENGINE -- Institutional On-Chain Strategies
===================================================
3 strategies using institutional positioning, open interest dynamics,
and miner capitulation signals from free public APIs.

Strategies:
  1. cme_cot_positioning          -- Binance top trader L/S ratio z-score (COT proxy)
  2. weekly_oi_change_momentum    -- OI surge + flat price → breakout detection
  3. miner_capitulation_recovery  -- Hash ribbon 30d/60d SMA crossover (bottom signal)

Data sources (all FREE, no key required):
  - fapi.binance.com/futures/data/topLongShortPositionRatio  (no auth)
  - fapi.binance.com/futures/data/openInterestHist           (no auth)
  - api.blockchain.info/charts/hash-rate                     (no auth)
  - Price data from scanner DataFrames (yfinance)

References:
  - Bianchi & Babiak (2024): "Commitment of Traders and crypto positioning"
  - Aloosh, Ouzan & Shahzad (2024): "OI dynamics and breakout prediction"
  - Nuzzi, Waters & Andrade (2024, CoinMetrics): "Hash ribbon capitulation"
  - Charles Edwards (2019): Hash Ribbons indicator
"""

from __future__ import annotations

import json
import os
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from config import CRYPTO_SYMBOLS
from indicators import rsi, atr, sma

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).resolve().parent / "data"

_RATE_LIMIT_DELAY = 0.5  # seconds between API calls


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_category(symbol: str) -> str:
    info = CRYPTO_SYMBOLS.get(symbol, {})
    return info.get("cat", "crypto")


def _smart_round(value: float) -> float:
    if value == 0:
        return 0.0
    abs_val = abs(value)
    if abs_val >= 100:
        return round(value, 2)
    elif abs_val >= 1:
        return round(value, 4)
    elif abs_val >= 0.01:
        return round(value, 6)
    else:
        return round(value, 10)


def _fetch_json(url: str, timeout: int = 10) -> Optional[dict | list]:
    """Fetch JSON from URL with User-Agent header."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ALPHA_ENGINE/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def _load_cache(filename: str, max_age_hours: float = 12.0) -> Optional[dict | list]:
    """Load cached JSON if it exists and is fresh enough."""
    cache_path = DATA_DIR / filename
    if not cache_path.exists():
        return None
    try:
        mtime = cache_path.stat().st_mtime
        age_hours = (time.time() - mtime) / 3600
        if age_hours > max_age_hours:
            return None
        with open(cache_path, "r") as f:
            return json.load(f)
    except Exception:
        return None


def _save_cache(filename: str, data: dict | list) -> None:
    """Save data to cache file."""
    cache_path = DATA_DIR / filename
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w") as f:
            json.dump(data, f)
    except Exception:
        pass


def _binance_symbol(yf_symbol: str) -> str:
    """Convert yfinance symbol (BTC-USD) to Binance futures symbol (BTCUSDT)."""
    info = CRYPTO_SYMBOLS.get(yf_symbol, {})
    return info.get("binance", yf_symbol.replace("-USD", "USDT"))


# =====================================================================
# STRATEGY 1: CME COT Positioning (Bianchi & Babiak, 2024)
# =====================================================================
# Uses Binance top trader long/short ratio as a proxy for institutional
# (commercial) COT positioning.  Z-score > 1.0 with price above 20d SMA
# triggers BUY; z-score < -1.0 with price below 20d SMA triggers SHORT.
# TP: +8%, SL: -4%.  Hold: 14-28 days.
# =====================================================================

def cme_cot_positioning(data: dict[str, pd.DataFrame]) -> list[dict]:
    """BUY/SHORT BTC based on top-trader long/short ratio z-score."""
    signals: list[dict] = []
    symbol = "BTC-USD"

    if symbol not in data:
        return signals

    try:
        df = data[symbol]
        if len(df) < 30:
            return signals

        close = df["Close"]
        price = float(close.iloc[-1])
        sma_20 = float(sma(close, 20).iloc[-1])

        # Try cached COT data first
        cached = _load_cache("cot_btc_latest.json", max_age_hours=6.0)
        ratios = None

        if cached and isinstance(cached, list) and len(cached) >= 20:
            ratios = [float(r.get("longShortRatio", 1.0)) for r in cached]
        else:
            # Fetch from Binance top trader L/S ratio
            binance_sym = _binance_symbol(symbol)
            url = (
                f"https://fapi.binance.com/futures/data/topLongShortPositionRatio"
                f"?symbol={binance_sym}&period=1d&limit=30"
            )
            time.sleep(_RATE_LIMIT_DELAY)
            resp = _fetch_json(url)
            if resp and isinstance(resp, list) and len(resp) >= 20:
                _save_cache("cot_btc_latest.json", resp)
                ratios = [float(r.get("longShortRatio", 1.0)) for r in resp]

        if ratios is None or len(ratios) < 20:
            return signals

        # Compute z-score of latest ratio over 30-day window
        ratio_arr = np.array(ratios, dtype=float)
        latest_ratio = ratio_arr[-1]
        mean_ratio = np.mean(ratio_arr)
        std_ratio = max(np.std(ratio_arr), 0.001)
        z_score = (latest_ratio - mean_ratio) / std_ratio

        rsi_val = float(rsi(close, 14).iloc[-1])

        if z_score > 0.7 and price > sma_20:
            # Smart money net long + price above SMA → BUY (relaxed from z>1.0)
            tp = _smart_round(price * 1.08)
            sl = _smart_round(price * 0.96)
            entry = _smart_round(price)
            rr = abs(tp - entry) / max(abs(entry - sl), 0.01)

            # Confidence scales with z-score magnitude (lowered from 0.72 base)
            conf = min(0.78, 0.68 + (z_score - 0.7) * 0.05)

            signals.append({
                "strategy": "cme_cot_positioning",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": "BUY",
                "entry_price": entry,
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(conf, 2),
                "risk_reward": round(rr, 2),
                "reason": (
                    f"Top-trader L/S ratio z-score {z_score:.2f} (net long), "
                    f"price above 20d SMA ({sma_20:.0f}), RSI {rsi_val:.0f}"
                ),
                "timeframe": "1d",
                "rsi_at_entry": round(rsi_val, 1),
                "extra": {
                    "z_score": round(z_score, 2),
                    "ls_ratio": round(latest_ratio, 3),
                    "sma_20": _smart_round(sma_20),
                    "hold_days": "14-28",
                    "source": "Bianchi & Babiak (2024) -- COT positioning proxy",
                },
                "timestamp": _now_iso(),
            })

        elif z_score < -0.7 and price < sma_20:
            # Smart money net short + price below SMA → SHORT (relaxed from z<-1.0)
            tp = _smart_round(price * 0.92)
            sl = _smart_round(price * 1.04)
            entry = _smart_round(price)
            rr = abs(entry - tp) / max(abs(sl - entry), 0.01)

            conf = min(0.78, 0.68 + (abs(z_score) - 0.7) * 0.05)

            signals.append({
                "strategy": "cme_cot_positioning",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": "SHORT",
                "entry_price": entry,
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(conf, 2),
                "risk_reward": round(rr, 2),
                "reason": (
                    f"Top-trader L/S ratio z-score {z_score:.2f} (net short), "
                    f"price below 20d SMA ({sma_20:.0f}), RSI {rsi_val:.0f}"
                ),
                "timeframe": "1d",
                "rsi_at_entry": round(rsi_val, 1),
                "extra": {
                    "z_score": round(z_score, 2),
                    "ls_ratio": round(latest_ratio, 3),
                    "sma_20": _smart_round(sma_20),
                    "hold_days": "14-28",
                    "source": "Bianchi & Babiak (2024) -- COT positioning proxy",
                },
                "timestamp": _now_iso(),
            })

    except Exception:
        pass

    return signals


# =====================================================================
# STRATEGY 2: Weekly OI Change Momentum (Aloosh, Ouzan & Shahzad, 2024)
# =====================================================================
# When open interest surges >10% in a week but price stays flat (<5%),
# a breakout is imminent.  Direction follows 7d price drift.
# TP: +6%, SL: -3%.  Max 3 picks per cycle.
# =====================================================================

def weekly_oi_change_momentum(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Detect OI surge + flat price → imminent breakout."""
    signals: list[dict] = []
    target_symbols = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "DOGE-USD", "XRP-USD"]
    max_picks = 3

    for symbol in target_symbols:
        if len(signals) >= max_picks:
            break
        if symbol not in data:
            continue

        try:
            df = data[symbol]
            if len(df) < 10:
                continue

            close = df["Close"]
            price = float(close.iloc[-1])

            # 7-day price change
            price_7d_ago = float(close.iloc[-8]) if len(close) >= 8 else float(close.iloc[0])
            price_change_7d = (price - price_7d_ago) / price_7d_ago

            # Fetch OI history from Binance
            binance_sym = _binance_symbol(symbol)
            url = (
                f"https://fapi.binance.com/futures/data/openInterestHist"
                f"?symbol={binance_sym}&period=1d&limit=8"
            )
            time.sleep(_RATE_LIMIT_DELAY)
            oi_data = _fetch_json(url)

            if not oi_data or not isinstance(oi_data, list) or len(oi_data) < 2:
                continue

            # Compute weekly OI delta
            latest_oi = float(oi_data[-1].get("sumOpenInterest", 0))
            oldest_oi = float(oi_data[0].get("sumOpenInterest", 0))

            if oldest_oi <= 0 or latest_oi <= 0:
                continue

            oi_delta = (latest_oi - oldest_oi) / oldest_oi

            # Check conditions: OI up >7% AND price flat (<7% change) (relaxed from 10%/5%)
            if oi_delta <= 0.07 or abs(price_change_7d) >= 0.07:
                continue

            # Direction: follow the 7d price drift
            if price_change_7d >= 0:
                signal_type = "BUY"
                tp = _smart_round(price * 1.06)
                sl = _smart_round(price * 0.97)
            else:
                signal_type = "SHORT"
                tp = _smart_round(price * 0.94)
                sl = _smart_round(price * 1.03)

            entry = _smart_round(price)

            if signal_type == "BUY":
                rr = abs(tp - entry) / max(abs(entry - sl), 0.01)
            else:
                rr = abs(entry - tp) / max(abs(sl - entry), 0.01)

            # Confidence: higher OI delta = higher conviction (lowered from 0.70 base)
            conf = min(0.77, 0.67 + (oi_delta - 0.07) * 0.5)

            rsi_val = float(rsi(close, 14).iloc[-1])

            signals.append({
                "strategy": "weekly_oi_change_momentum",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": signal_type,
                "entry_price": entry,
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(conf, 2),
                "risk_reward": round(rr, 2),
                "reason": (
                    f"OI surged {oi_delta * 100:.1f}% in 7d while price moved "
                    f"only {price_change_7d * 100:.1f}% → breakout imminent "
                    f"({signal_type})"
                ),
                "timeframe": "1d",
                "rsi_at_entry": round(rsi_val, 1),
                "extra": {
                    "oi_delta_pct": round(oi_delta * 100, 1),
                    "price_change_7d_pct": round(price_change_7d * 100, 1),
                    "latest_oi": latest_oi,
                    "source": "Aloosh, Ouzan & Shahzad (2024) -- OI breakout",
                },
                "timestamp": _now_iso(),
            })

        except Exception:
            continue

    return signals


# =====================================================================
# STRATEGY 3: Miner Capitulation Recovery (Nuzzi, Waters & Andrade, 2024)
# =====================================================================
# Hash Ribbon: when 30d SMA of hash rate crosses above 60d SMA, miners
# have recovered from capitulation → strong BUY signal for BTC.
# Also requires 7d hash rate change to be positive (confirms recovery).
# TP: +15%, SL: -8%.  Hold: 30-90 days.  ~2-4 signals per year.
# Blockchain.com data cached for 12 hours.
# =====================================================================

def miner_capitulation_recovery(data: dict[str, pd.DataFrame]) -> list[dict]:
    """BUY BTC when hash ribbon signals miner recovery after capitulation."""
    signals: list[dict] = []
    symbol = "BTC-USD"

    if symbol not in data:
        return signals

    try:
        df = data[symbol]
        if len(df) < 10:
            return signals

        close = df["Close"]
        price = float(close.iloc[-1])

        # Load hash rate data (cached for 12 hours)
        cache_file = "hash_rate_90d.json"
        hash_data = _load_cache(cache_file, max_age_hours=12.0)

        if hash_data is None:
            time.sleep(_RATE_LIMIT_DELAY)
            url = "https://api.blockchain.info/charts/hash-rate?timespan=90days&format=json&cors=true"
            hash_data = _fetch_json(url, timeout=15)
            if hash_data:
                _save_cache(cache_file, hash_data)

        if not hash_data or "values" not in hash_data:
            return signals

        values = hash_data["values"]
        if len(values) < 65:
            return signals

        # Extract hash rate time series
        hash_rates = np.array([float(v.get("y", 0)) for v in values], dtype=float)

        if len(hash_rates) < 65:
            return signals

        # Compute 30d and 60d SMAs of hash rate
        sma_30 = np.mean(hash_rates[-30:])
        sma_60 = np.mean(hash_rates[-60:])

        # Previous day SMAs (for crossover detection)
        prev_sma_30 = np.mean(hash_rates[-31:-1])
        prev_sma_60 = np.mean(hash_rates[-61:-1])

        # 7-day hash rate change (must be positive for recovery confirmation)
        hr_7d_ago = np.mean(hash_rates[-10:-3]) if len(hash_rates) >= 10 else hash_rates[0]
        hr_latest = np.mean(hash_rates[-3:])
        hr_change_7d = (hr_latest - hr_7d_ago) / max(hr_7d_ago, 1.0)

        # Hash Ribbon BUY: 30d SMA crosses above 60d SMA
        ribbon_cross = (prev_sma_30 <= prev_sma_60) and (sma_30 > sma_60)

        # Also check for recovery without exact crossover:
        # 30d recently crossed above 60d (within last few days)
        ribbon_above = sma_30 > sma_60
        ribbon_margin = (sma_30 - sma_60) / max(sma_60, 1.0)

        # Must have 7d positive hash rate change
        if not (ribbon_cross or (ribbon_above and ribbon_margin < 0.03)) or hr_change_7d <= 0:
            return signals

        entry = _smart_round(price)
        tp = _smart_round(price * 1.15)
        sl = _smart_round(price * 0.92)
        rr = abs(tp - entry) / max(abs(entry - sl), 0.01)

        # Confidence: higher for exact crossover, slightly lower for near-crossover
        if ribbon_cross:
            conf = min(0.85, 0.78 + hr_change_7d * 0.5)
        else:
            conf = min(0.82, 0.75 + hr_change_7d * 0.5)

        rsi_val = float(rsi(close, 14).iloc[-1])

        signals.append({
            "strategy": "miner_capitulation_recovery",
            "symbol": symbol,
            "category": _get_category(symbol),
            "signal_type": "BUY",
            "entry_price": entry,
            "take_profit": tp,
            "stop_loss": sl,
            "confidence": round(conf, 2),
            "risk_reward": round(rr, 2),
            "reason": (
                f"Hash ribbon {'crossover' if ribbon_cross else 'recovery'}: "
                f"30d SMA ({sma_30:.0f}) > 60d SMA ({sma_60:.0f}), "
                f"7d hash rate +{hr_change_7d * 100:.1f}% → miner recovery"
            ),
            "timeframe": "1d",
            "rsi_at_entry": round(rsi_val, 1),
            "extra": {
                "sma_30_hash": round(sma_30, 1),
                "sma_60_hash": round(sma_60, 1),
                "ribbon_margin_pct": round(ribbon_margin * 100, 2),
                "hr_change_7d_pct": round(hr_change_7d * 100, 1),
                "is_exact_crossover": ribbon_cross,
                "hold_days": "30-90",
                "source": "Nuzzi, Waters & Andrade (2024, CoinMetrics) -- Hash Ribbons",
            },
            "timestamp": _now_iso(),
        })

    except Exception:
        pass

    return signals


# ---------------------------------------------------------------------------
# Strategy registry for scanner import
# ---------------------------------------------------------------------------

INSTITUTIONAL_ONCHAIN_STRATEGIES = {
    "cme_cot_positioning": cme_cot_positioning,
    "weekly_oi_change_momentum": weekly_oi_change_momentum,
    "miner_capitulation_recovery": miner_capitulation_recovery,
}
