#!/usr/bin/env python3
"""
DNA Signal Engine Mutations — Aggressive Variants of crypto_signal_engine
=========================================================================

Parent System: crypto_signal_engine
  - Performance: 100% WR on 2 closed trades — perfect but almost never fires
  - Bottleneck: 6 strict risk guards that filter out 99%+ of potential signals
    1. MIN_CONF = 0.60 (confidence threshold)
    2. MIN_CONF_PREMIUM = 0.75 (premium confidence gate)
    3. above_200 trend guard (price must be above 200-period MA)
    4. MIN_VOL_RATIO = 1.2 (volume must be 1.2x average)
    5. Only 3 symbols scanned
    6. Momentum + mean-reversion mixed mode (conflicting filters)

Mutations:
  a. signal_engine_relaxed     — MIN_CONF 0.40, remove trend guard (above_200)
  b. signal_engine_wide_net    — 15 symbols, MIN_CONF 0.45, MIN_VOL_RATIO 0.8
  c. signal_engine_no_premium  — Remove premium gate (0.75), use flat 0.50 for all
  d. signal_engine_momentum_only — Only momentum features, skip mean-reversion

All mutations are SANDBOX tier (0.3 weight) until proven via forward testing.

Data Sources: Binance API (klines)
Output: Standard pick format consumed by forward_validator / battleground pipeline
"""

from __future__ import annotations

import json
import math
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

# ── Path setup ────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent

# Try importing indicators from ml_battleground shared
try:
    sys.path.insert(0, str(ROOT / "ml_battleground"))
    from shared.indicators import rsi, atr, sma, ema
    _HAS_INDICATORS = True
except ImportError:
    _HAS_INDICATORS = False

if not _HAS_INDICATORS:
    # Inline fallback indicators
    def sma(series: pd.Series, period: int) -> pd.Series:
        return series.rolling(period).mean()

    def ema(series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()

    def rsi(close: pd.Series, period: int = 14) -> pd.Series:
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / loss.replace(0, np.nan)
        return (100 - 100 / (1 + rs)).fillna(50.0)

    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs()
        ], axis=1).max(axis=1)
        return tr.rolling(period).mean()


# ── Helpers ───────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _smart_round(value: float) -> float:
    if value is None or not np.isfinite(value):
        return 0.0
    if abs(value) >= 1000:
        return round(value, 2)
    if abs(value) >= 1:
        return round(value, 4)
    if abs(value) >= 0.01:
        return round(value, 6)
    return round(value, 8)


def _base_signal(strategy: str, symbol: str, signal_type: str, entry: float,
                 tp: float, sl: float, confidence: float, reason: str,
                 parent_system: str, mutation_type: str, **extra) -> dict:
    """Create standardized signal dict with mutation metadata."""
    rr = 0.0
    if signal_type == "BUY" and entry > sl:
        rr = (tp - entry) / (entry - sl)
    elif signal_type == "SELL" and sl > entry:
        rr = (entry - tp) / (sl - entry)

    sig = {
        "strategy": strategy,
        "symbol": symbol,
        "signal_type": signal_type,
        "entry_price": _smart_round(entry),
        "take_profit": _smart_round(tp),
        "stop_loss": _smart_round(sl),
        "confidence": round(min(0.85, confidence), 4),
        "risk_reward": round(max(0, rr), 2),
        "reason": reason,
        "timestamp": _now_iso(),
        "category": "crypto",
        "source_system": "genome",
        "trust_tier": "SANDBOX",
        "trust_weight": 0.3,
        "parent_system": parent_system,
        "mutation_type": mutation_type,
    }
    sig.update(extra)
    return sig


# ── Data Fetching (Binance klines) ────────────────────────────────────────

BINANCE_MIRRORS = [
    "https://api.binance.com", "https://api1.binance.com",
    "https://api2.binance.com", "https://api3.binance.com",
    "https://data-api.binance.vision",
]


def fetch_binance_klines(symbol: str, interval: str = "1h", limit: int = 300) -> pd.DataFrame:
    """Fetch OHLCV from Binance with mirror rotation."""
    for base in BINANCE_MIRRORS:
        url = f"{base}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "DNASignalEngine/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            if data and isinstance(data, list) and len(data) > 20:
                df = pd.DataFrame(data, columns=[
                    "open_time", "Open", "High", "Low", "Close", "Volume",
                    "close_time", "qav", "num_trades", "taker_buy_base",
                    "taker_buy_quote", "ignore"
                ])
                for col in ["Open", "High", "Low", "Close", "Volume"]:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
                df.set_index("open_time", inplace=True)
                return df
        except Exception:
            continue
    return pd.DataFrame()


# ── Symbol lists ──────────────────────────────────────────────────────────

# Original signal engine only scans 3 symbols — way too narrow
SIGNAL_ENGINE_ORIGINAL_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

# Expanded universe for wide_net mutation
SIGNAL_ENGINE_WIDE_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "ADAUSDT", "AVAXUSDT", "LINKUSDT", "NEARUSDT", "DOTUSDT",
    "SUIUSDT", "APTUSDT", "INJUSDT", "SEIUSDT", "ATOMUSDT",
]


# ═══════════════════════════════════════════════════════════════════════════
# Signal Engine Feature Computation (proxy for XGBoost model features)
# ═══════════════════════════════════════════════════════════════════════════

def _compute_signal_features(df: pd.DataFrame) -> Optional[dict]:
    """
    Compute the features that crypto_signal_engine's XGBoost model uses.
    Returns a dict of feature values, or None if insufficient data.

    Features modeled:
      - rsi_14: RSI(14)
      - rsi_7: RSI(7) — fast RSI
      - macd_hist: MACD histogram
      - bb_position: Where price is in Bollinger Bands (0=lower, 1=upper)
      - vol_ratio: Volume / 20-period avg
      - mom_3d: 3-bar momentum (pct change)
      - mom_7d: 7-bar momentum
      - above_200: Price above 200-period SMA (1/0)
      - atr_pct: ATR as % of price
      - ema_cross: EMA(9) > EMA(21) crossover signal
    """
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    if len(close) < 200:
        # For shorter data, compute what we can
        pass

    current = float(close.iloc[-1])
    if current <= 0:
        return None

    # RSI
    rsi_14 = float(rsi(close, 14).iloc[-1])
    rsi_7 = float(rsi(close, 7).iloc[-1]) if len(close) > 10 else 50.0
    if pd.isna(rsi_14):
        return None

    # MACD
    ema_12 = ema(close, 12)
    ema_26 = ema(close, 26)
    macd_line = ema_12 - ema_26
    signal_line = ema(macd_line, 9)
    histogram = macd_line - signal_line
    macd_hist = float(histogram.iloc[-1]) if not pd.isna(histogram.iloc[-1]) else 0.0

    # Bollinger Band position
    bb_mid = sma(close, 20)
    bb_std = close.rolling(20).std()
    bb_upper = bb_mid + 2 * bb_std
    bb_lower = bb_mid - 2 * bb_std
    bb_range = float(bb_upper.iloc[-1] - bb_lower.iloc[-1])
    if bb_range > 0:
        bb_position = (current - float(bb_lower.iloc[-1])) / bb_range
    else:
        bb_position = 0.5

    # Volume ratio
    vol_avg = float(volume.rolling(20).mean().iloc[-1])
    vol_ratio = float(volume.iloc[-1]) / vol_avg if vol_avg > 0 else 1.0

    # Momentum
    mom_3d = float(close.pct_change(3).iloc[-1]) if len(close) > 3 else 0
    mom_7d = float(close.pct_change(7).iloc[-1]) if len(close) > 7 else 0

    # Trend: above 200 SMA
    sma_200 = float(sma(close, 200).iloc[-1]) if len(close) >= 200 else float(sma(close, min(len(close), 50)).iloc[-1])
    above_200 = 1 if current > sma_200 else 0

    # ATR as % of price
    atr_val = float(atr(high, low, close).iloc[-1])
    atr_pct = atr_val / current if current > 0 else 0

    # EMA cross
    ema_9 = float(ema(close, 9).iloc[-1])
    ema_21 = float(ema(close, 21).iloc[-1])
    ema_cross = 1 if ema_9 > ema_21 else 0

    return {
        "current": current,
        "rsi_14": rsi_14,
        "rsi_7": rsi_7,
        "macd_hist": macd_hist,
        "bb_position": bb_position,
        "vol_ratio": vol_ratio,
        "mom_3d": mom_3d,
        "mom_7d": mom_7d,
        "above_200": above_200,
        "atr_pct": atr_pct,
        "atr_val": atr_val,
        "ema_cross": ema_cross,
        "ema_9": ema_9,
        "ema_21": ema_21,
        "sma_200": sma_200,
    }


def _confidence_score(features: dict, mode: str = "full") -> float:
    """
    Compute a confidence score that proxies the XGBoost model output.
    This is a rule-based approximation of the ML model's decision boundaries.

    Modes:
      - "full": All features (original model)
      - "momentum": Only momentum features
      - "mean_reversion": Only mean-reversion features
    """
    score = 0.0

    if mode in ("full", "momentum"):
        # Momentum features
        if features["macd_hist"] > 0:
            score += 0.12
        if features["ema_cross"] == 1:
            score += 0.10
        if features["mom_3d"] > 0.01:
            score += 0.08
        if features["mom_7d"] > 0.02:
            score += 0.08
        if features["rsi_7"] > 50 and features["rsi_7"] < 70:
            score += 0.06

    if mode in ("full", "mean_reversion"):
        # Mean-reversion features
        if features["rsi_14"] < 35:
            score += 0.12
        if features["bb_position"] < 0.2:
            score += 0.10
        if features["rsi_14"] < 25:
            score += 0.08
        if features["bb_position"] < 0.1:
            score += 0.06

    # Common features (always used)
    if features["vol_ratio"] > 1.2:
        score += 0.08
    if features["vol_ratio"] > 1.8:
        score += 0.05
    if features["atr_pct"] > 0.01 and features["atr_pct"] < 0.05:
        score += 0.05  # healthy volatility

    return score


# ═══════════════════════════════════════════════════════════════════════════
# MUTATION A: signal_engine_relaxed
# Lower MIN_CONF from 0.60 to 0.40, remove trend guard (above_200)
# ═══════════════════════════════════════════════════════════════════════════

def signal_engine_relaxed(data: dict) -> list[dict]:
    """
    Mutation of crypto_signal_engine: Relaxed confidence + no trend filter.

    Original: MIN_CONF = 0.60, requires price above 200 SMA
    Relaxed:  MIN_CONF = 0.40, trend guard removed

    The above_200 filter kills signals during corrections — which is exactly
    when mean-reversion signals are most valuable. Removing it while keeping
    a lower confidence bar should generate 5-10x more signals.

    Expected: ~8x more picks, WR drops from 100% -> ~55-65%
    """
    signals = []

    for symbol in SIGNAL_ENGINE_ORIGINAL_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 50:
            continue

        features = _compute_signal_features(df)
        if features is None:
            continue

        current = features["current"]
        conf_score = _confidence_score(features, mode="full")

        # Relaxed threshold: 0.40 (original was 0.60)
        if conf_score < 0.40:
            continue

        # NO trend guard (above_200 removed)

        atr_val = features["atr_val"]
        if atr_val <= 0:
            continue

        tp = current + 2.0 * atr_val
        sl = current - 1.5 * atr_val

        conf = min(0.80, 0.45 + conf_score * 0.5)

        signals.append(_base_signal(
            "signal_engine_relaxed_mut", symbol, "BUY", current, tp, sl, conf,
            f"Signal engine relaxed: conf_score={conf_score:.2f} (>= 0.40), "
            f"RSI={features['rsi_14']:.1f}, MACD={features['macd_hist']:.6f}, "
            f"BB_pos={features['bb_position']:.2f} — no trend filter",
            parent_system="crypto_signal_engine",
            mutation_type="conservative",
            conf_score=round(conf_score, 3),
            rsi_14=round(features["rsi_14"], 1),
            bb_position=round(features["bb_position"], 3),
            volume_ratio=round(features["vol_ratio"], 2),
            above_200=features["above_200"],
            timeframe="1h",
        ))

    return signals


# ═══════════════════════════════════════════════════════════════════════════
# MUTATION B: signal_engine_wide_net
# Expand from 3 to 15 symbols, MIN_CONF 0.45, MIN_VOL_RATIO 0.8
# ═══════════════════════════════════════════════════════════════════════════

def signal_engine_wide_net(data: dict) -> list[dict]:
    """
    Mutation of crypto_signal_engine: 5x symbol expansion + relaxed filters.

    Original: 3 symbols (BTC, ETH, SOL), MIN_CONF=0.60, MIN_VOL_RATIO=1.2
    Relaxed:  15 symbols, MIN_CONF=0.45, MIN_VOL_RATIO=0.8

    The original engine only watches 3 coins. Many alt-coins have the same
    technical patterns but are completely ignored. This mutation casts a wide
    net while keeping the core signal logic.

    Expected: ~15-20x more opportunities, WR ~50-60%
    """
    signals = []

    for symbol in SIGNAL_ENGINE_WIDE_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 50:
            continue

        features = _compute_signal_features(df)
        if features is None:
            continue

        current = features["current"]
        conf_score = _confidence_score(features, mode="full")

        # Relaxed confidence: 0.45 (was 0.60)
        if conf_score < 0.45:
            continue

        # Relaxed volume: 0.8x (was 1.2x)
        if features["vol_ratio"] < 0.8:
            continue

        atr_val = features["atr_val"]
        if atr_val <= 0:
            continue

        tp = current + 2.0 * atr_val
        sl = current - 1.5 * atr_val

        conf = min(0.78, 0.42 + conf_score * 0.5)

        signals.append(_base_signal(
            "signal_engine_wide_net_mut", symbol, "BUY", current, tp, sl, conf,
            f"Signal engine wide net: conf_score={conf_score:.2f} (>= 0.45), "
            f"RSI={features['rsi_14']:.1f}, vol={features['vol_ratio']:.1f}x (>= 0.8), "
            f"15-symbol scan",
            parent_system="crypto_signal_engine",
            mutation_type="moderate",
            conf_score=round(conf_score, 3),
            rsi_14=round(features["rsi_14"], 1),
            volume_ratio=round(features["vol_ratio"], 2),
            bb_position=round(features["bb_position"], 3),
            momentum_3d=round(features["mom_3d"], 4),
            timeframe="1h",
        ))

    return signals


# ═══════════════════════════════════════════════════════════════════════════
# MUTATION C: signal_engine_no_premium
# Remove premium confidence gate (0.75), use flat 0.50 for all
# ═══════════════════════════════════════════════════════════════════════════

def signal_engine_no_premium(data: dict) -> list[dict]:
    """
    Mutation of crypto_signal_engine: Remove premium tier confidence gate.

    Original: MIN_CONF_PREMIUM = 0.75 for "high conviction" signals,
              MIN_CONF = 0.60 for standard signals
    Relaxed:  Flat 0.50 for ALL signals — no premium/standard split

    The premium gate was designed to separate "A+" from "A" signals, but
    with only 2 closed trades, there's no statistical basis for this split.
    Using a flat 0.50 treats all moderately confident signals equally.

    Expected: ~4x more signals, WR ~55-65%
    """
    signals = []

    for symbol in SIGNAL_ENGINE_ORIGINAL_SYMBOLS + ["BNBUSDT", "XRPUSDT", "ADAUSDT"]:
        df = data.get(symbol)
        if df is None or len(df) < 50:
            continue

        features = _compute_signal_features(df)
        if features is None:
            continue

        current = features["current"]
        conf_score = _confidence_score(features, mode="full")

        # Flat threshold: 0.50 for ALL (no premium gate)
        if conf_score < 0.50:
            continue

        # Keep trend guard as a soft bonus (not a hard filter)
        trend_bonus = 0.03 if features["above_200"] else 0.0

        atr_val = features["atr_val"]
        if atr_val <= 0:
            continue

        tp = current + 2.0 * atr_val
        sl = current - 1.5 * atr_val

        conf = min(0.82, 0.48 + conf_score * 0.4 + trend_bonus)

        signals.append(_base_signal(
            "signal_engine_no_premium_mut", symbol, "BUY", current, tp, sl, conf,
            f"Signal engine no-premium: conf_score={conf_score:.2f} (flat >= 0.50), "
            f"RSI={features['rsi_14']:.1f}, trend={'UP' if features['above_200'] else 'DOWN'} "
            f"(soft bonus, not filter)",
            parent_system="crypto_signal_engine",
            mutation_type="moderate",
            conf_score=round(conf_score, 3),
            rsi_14=round(features["rsi_14"], 1),
            above_200=features["above_200"],
            volume_ratio=round(features["vol_ratio"], 2),
            timeframe="1h",
        ))

    return signals


# ═══════════════════════════════════════════════════════════════════════════
# MUTATION D: signal_engine_momentum_only
# Only momentum features from XGBoost, skip mean-reversion signals
# ═══════════════════════════════════════════════════════════════════════════

def signal_engine_momentum_only(data: dict) -> list[dict]:
    """
    Mutation of crypto_signal_engine: Momentum-only mode.

    The original XGBoost model mixes momentum and mean-reversion features.
    These can conflict: momentum says "buy the breakout" while mean-reversion
    says "wait for RSI < 30". This mutation ONLY uses momentum features:
      - MACD histogram positive
      - EMA(9) > EMA(21) cross
      - 3d/7d momentum positive
      - RSI in 50-70 range (momentum sweet spot)

    Skip: RSI oversold, BB lower band, drawdown recovery (mean-reversion)
    Expected: Cleaner directional signals — ~52-58% WR
    """
    signals = []

    for symbol in SIGNAL_ENGINE_WIDE_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 50:
            continue

        features = _compute_signal_features(df)
        if features is None:
            continue

        current = features["current"]

        # Momentum-only score (no mean-reversion features)
        mom_score = _confidence_score(features, mode="momentum")

        # Need meaningful momentum score
        if mom_score < 0.30:
            continue

        # Hard momentum filters
        if features["macd_hist"] <= 0:
            continue  # Must have positive MACD

        if features["ema_cross"] != 1:
            continue  # EMA(9) must be above EMA(21)

        # RSI must be in momentum sweet spot (not oversold, not overbought)
        if features["rsi_14"] < 45 or features["rsi_14"] > 72:
            continue

        # Positive short-term momentum
        if features["mom_3d"] < 0:
            continue

        atr_val = features["atr_val"]
        if atr_val <= 0:
            continue

        # Momentum trades: slightly tighter TP/SL
        tp = current + 1.8 * atr_val
        sl = current - 1.3 * atr_val

        conf = min(0.78, 0.48 + mom_score * 0.6 + features["mom_3d"] * 2)

        signals.append(_base_signal(
            "signal_engine_momentum_mut", symbol, "BUY", current, tp, sl, conf,
            f"Signal engine momentum-only: MACD>0, EMA9>21, "
            f"RSI={features['rsi_14']:.1f}, mom3d=+{features['mom_3d']:.1%}, "
            f"mom7d=+{features['mom_7d']:.1%} — pure trend follow",
            parent_system="crypto_signal_engine",
            mutation_type="aggressive",
            momentum_score=round(mom_score, 3),
            rsi_14=round(features["rsi_14"], 1),
            macd_hist=round(features["macd_hist"], 8),
            ema_cross=features["ema_cross"],
            momentum_3d=round(features["mom_3d"], 4),
            momentum_7d=round(features["mom_7d"], 4),
            timeframe="1h",
        ))

    return signals


# ═══════════════════════════════════════════════════════════════════════════
# REGISTRY — All Signal Engine Mutations
# ═══════════════════════════════════════════════════════════════════════════

DNA_SIGNAL_ENGINE_MUTATIONS = {
    "signal_engine_relaxed_mut": {
        "fn": signal_engine_relaxed,
        "parent": "crypto_signal_engine",
        "mutation": "conservative",
        "trust_weight": 0.3,
        "description": "MIN_CONF 0.40 (was 0.60), remove above_200 trend guard",
    },
    "signal_engine_wide_net_mut": {
        "fn": signal_engine_wide_net,
        "parent": "crypto_signal_engine",
        "mutation": "moderate",
        "trust_weight": 0.3,
        "description": "15 symbols (was 3), MIN_CONF 0.45, MIN_VOL_RATIO 0.8",
    },
    "signal_engine_no_premium_mut": {
        "fn": signal_engine_no_premium,
        "parent": "crypto_signal_engine",
        "mutation": "moderate",
        "trust_weight": 0.3,
        "description": "Remove premium gate (0.75), flat 0.50 for all signals",
    },
    "signal_engine_momentum_mut": {
        "fn": signal_engine_momentum_only,
        "parent": "crypto_signal_engine",
        "mutation": "aggressive",
        "trust_weight": 0.3,
        "description": "Momentum features only, skip mean-reversion signals",
    },
}

# Total: 4 mutations of crypto_signal_engine


# ═══════════════════════════════════════════════════════════════════════════
# RUNNER — Fetch data & execute all mutations
# ═══════════════════════════════════════════════════════════════════════════

ALL_SCAN_SYMBOLS = sorted(set(
    SIGNAL_ENGINE_ORIGINAL_SYMBOLS +
    SIGNAL_ENGINE_WIDE_SYMBOLS +
    ["BNBUSDT", "XRPUSDT", "ADAUSDT"]
))


def run_all_mutations(interval: str = "1h", limit: int = 300) -> dict:
    """
    Fetch market data and run all 4 Signal Engine DNA mutations.

    Returns:
        {
            "metadata": {...},
            "picks": [...],
            "mutations_triggered": [...],
            "mutations_silent": [...]
        }
    """
    print(f"\n{'='*70}")
    print(f"DNA SIGNAL ENGINE MUTATIONS — {len(DNA_SIGNAL_ENGINE_MUTATIONS)} strategies")
    print(f"Scanning {len(ALL_SCAN_SYMBOLS)} symbols on {interval}")
    print(f"{'='*70}\n")

    # Fetch data for all symbols
    data = {}
    for symbol in ALL_SCAN_SYMBOLS:
        df = fetch_binance_klines(symbol, interval=interval, limit=limit)
        if not df.empty and len(df) > 20:
            data[symbol] = df
            print(f"  [OK] {symbol}: {len(df)} bars")
        else:
            print(f"  [--] {symbol}: no data")

    print(f"\nFetched data for {len(data)}/{len(ALL_SCAN_SYMBOLS)} symbols\n")

    # Run all mutations
    all_picks = []
    triggered = []
    silent = []

    for name, info in DNA_SIGNAL_ENGINE_MUTATIONS.items():
        try:
            picks = info["fn"](data)
            if picks:
                for p in picks:
                    p["timeframe"] = p.get("timeframe", interval)
                all_picks.extend(picks)
                triggered.append({
                    "strategy": name,
                    "parent": info["parent"],
                    "mutation": info["mutation"],
                    "picks": len(picks),
                })
                print(f"  [SIGNAL] {name}: {len(picks)} picks")
            else:
                silent.append(name)
                print(f"  [quiet] {name}: 0 picks")
        except Exception as e:
            silent.append(name)
            print(f"  [ERROR] {name}: {e}")

    # Sort by confidence
    all_picks.sort(key=lambda x: x.get("confidence", 0), reverse=True)

    result = {
        "metadata": {
            "timestamp": _now_iso(),
            "total_mutations": len(DNA_SIGNAL_ENGINE_MUTATIONS),
            "total_picks": len(all_picks),
            "mutations_triggered": len(triggered),
            "mutations_silent": len(silent),
            "symbols_scanned": len(data),
            "interval": interval,
            "system": "dna_signal_engine_mutations",
        },
        "picks": all_picks,
        "mutations_triggered": triggered,
        "mutations_silent": silent,
    }

    print(f"\n{'='*70}")
    print(f"RESULTS: {len(all_picks)} picks from {len(triggered)}/{len(DNA_SIGNAL_ENGINE_MUTATIONS)} mutations")
    print(f"{'='*70}\n")

    return result


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="DNA Signal Engine Mutations Scanner")
    parser.add_argument("--interval", default="1h", choices=["1h", "4h", "1d"],
                        help="Kline interval (default: 1h)")
    parser.add_argument("--limit", type=int, default=300,
                        help="Number of bars to fetch (default: 300)")
    parser.add_argument("--output", default=None,
                        help="Output JSON path (default: genome/data/signal_engine_mutation_picks.json)")
    args = parser.parse_args()

    output_path = args.output or str(ROOT / "genome" / "data" / "signal_engine_mutation_picks.json")

    result = run_all_mutations(interval=args.interval, limit=args.limit)

    # Save results
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2, default=str)

    print(f"Saved {result['metadata']['total_picks']} picks to {output_path}")

    # Summary
    if result["picks"]:
        print("\nTop 5 picks by confidence:")
        for i, p in enumerate(result["picks"][:5], 1):
            print(f"  {i}. {p['symbol']} {p['signal_type']} | "
                  f"conf={p['confidence']:.2f} | "
                  f"R:R={p['risk_reward']:.1f} | "
                  f"{p['strategy']} ({p['mutation_type']})")
