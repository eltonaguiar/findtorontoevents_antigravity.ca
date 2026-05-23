#!/usr/bin/env python3
"""
DNA Winner Mutations — Aggressive Variants of Proven Winning Systems
=====================================================================

These are MUTATED versions of 4 winning trading systems that have gone stale
(0 active picks despite strong win rates). Each mutation relaxes the entry
thresholds to generate MORE FREQUENT picks while preserving the core edge.

Parent Systems (from audit dashboard):
  1. claude_gainer_ml_perf  — 70% WR, 10 trades, last pick Mar 6
  2. kimi_signal_tracking   — 64% WR, 1028 trades, last pick Mar 1
  3. claude_gainer          — 56.2% WR, 32 trades, last pick Mar 4
  4. battleground           — 61.6% WR, 380 trades, last pick Mar 9

Mutation Philosophy:
  - Conservative: ~20% relaxation of key thresholds
  - Moderate: ~40% relaxation + expanded symbol universe
  - Aggressive: ~60% relaxation + faster timeframes + removed secondary filters
  - Inverse: Flip proven BUY logic to SELL (contrarian variant)

All mutations are SANDBOX tier (0.3 weight) until proven via forward testing.

Data Sources: Binance API (klines), yfinance (daily OHLCV), CoinGecko (F&G)
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


def _zscore(series: pd.Series, window: int) -> pd.Series:
    m = series.rolling(window).mean()
    s = series.rolling(window).std()
    return (series - m) / s.replace(0, np.nan)


def _vwma(close: pd.Series, volume: pd.Series, window: int) -> pd.Series:
    return (close * volume).rolling(window).sum() / volume.rolling(window).sum()


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
            req = urllib.request.Request(url, headers={"User-Agent": "DNAMutations/1.0"})
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


def fetch_fear_greed() -> Optional[int]:
    """Fetch current Fear & Greed index."""
    try:
        url = "https://api.alternative.me/fng/?limit=1"
        req = urllib.request.Request(url, headers={"User-Agent": "DNAMutations/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        return int(data["data"][0]["value"])
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════════════
# SYSTEM 1: CLAUDE GAINER ML PERF — 70% WR, 10 trades
# Parent: claude_gainer_ml/live_scanner.py
# Bottleneck: pump_probability threshold 0.65 (BUY) + BTC bearish filter
# ═══════════════════════════════════════════════════════════════════════════

# --- Mutation 1A: Conservative — Lower probability threshold ---
# Original: BUY threshold = 0.55 + 0.10 boost = 0.65
# Mutation: BUY threshold = 0.55 (remove boost), accept MEDIUM confidence

CLAUDE_ML_CONSERVATIVE_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "ADAUSDT", "AVAXUSDT", "DOGEUSDT", "LINKUSDT", "NEARUSDT",
]


def claude_ml_conservative(data: dict) -> list[dict]:
    """
    Mutation of claude_gainer_ml_perf: Lower pump probability threshold.

    Original thresholds:
      - BUY needs prob >= 0.65 (0.55 base + 0.10 buy boost)
      - BTC bearish -> prob >= 0.70
    Relaxed:
      - BUY needs prob >= 0.50 (remove buy boost entirely)
      - Ignore BTC trend filter
    Expected: ~3x more picks, WR drops from 70% -> ~58-62%
    """
    signals = []

    for symbol in CLAUDE_ML_CONSERVATIVE_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 50:
            continue

        close = df["Close"]
        volume = df["Volume"]
        current = float(close.iloc[-1])
        if current <= 0:
            continue

        # Compute simple ML proxy features (pump probability estimate)
        rsi_14 = float(rsi(close, 14).iloc[-1])
        if pd.isna(rsi_14):
            continue

        # Volume acceleration
        vol_avg = float(volume.rolling(20).mean().iloc[-1])
        vol_now = float(volume.iloc[-1])
        vol_ratio = vol_now / vol_avg if vol_avg > 0 else 1.0

        # Momentum features
        mom_1d = float(close.pct_change(1).iloc[-1]) if len(close) > 1 else 0
        mom_3d = float(close.pct_change(3).iloc[-1]) if len(close) > 3 else 0

        # Compression detection
        high_low_range = float((df["High"].iloc[-1] - df["Low"].iloc[-1]) / current)
        bb_width = float((close.rolling(20).std().iloc[-1] / close.rolling(20).mean().iloc[-1]))
        compression = bb_width < 0.02

        # Simple pump probability proxy
        pump_score = 0.3  # base
        if rsi_14 < 35:
            pump_score += 0.15  # oversold bounce setup
        if vol_ratio > 1.5:
            pump_score += 0.10  # volume interest
        if mom_1d > 0.01:
            pump_score += 0.05  # positive momentum
        if compression:
            pump_score += 0.10  # about to break out
        if mom_3d < -0.03 and rsi_14 < 40:
            pump_score += 0.10  # mean reversion after pullback

        # Relaxed threshold: 0.50 (original was 0.65)
        if pump_score < 0.50:
            continue

        atr_val = float(atr(df["High"], df["Low"], close).iloc[-1])
        if atr_val <= 0:
            continue

        tp = current + 2.5 * atr_val
        sl = current - 1.5 * atr_val

        conf = min(0.80, 0.50 + pump_score * 0.3)

        signals.append(_base_signal(
            "claude_ml_conservative_mut", symbol, "BUY", current, tp, sl, conf,
            f"Claude ML conservative: pump_score={pump_score:.2f} (threshold>=0.50), "
            f"RSI={rsi_14:.1f}, vol={vol_ratio:.1f}x, bb_width={bb_width:.4f}",
            parent_system="claude_gainer_ml_perf",
            mutation_type="conservative",
            rsi_14=round(rsi_14, 1),
            volume_ratio=round(vol_ratio, 2),
            pump_score=round(pump_score, 3),
            timeframe="1h",
        ))

    return signals


# --- Mutation 1B: Moderate — Expanded universe + relaxed features ---

CLAUDE_ML_MODERATE_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "ADAUSDT", "AVAXUSDT", "DOGEUSDT", "LINKUSDT", "NEARUSDT",
    # Expanded universe — mid-cap alts the original scanner doesn't cover
    "SUIUSDT", "APTUSDT", "INJUSDT", "TIAUSDT", "SEIUSDT",
    "JUPUSDT", "WUSDT", "STXUSDT", "IMXUSDT", "OPUSDT",
]


def claude_ml_moderate(data: dict) -> list[dict]:
    """
    Mutation of claude_gainer_ml_perf: Expanded universe + lower threshold.

    Changes vs original:
      - 20 symbols (was ~10-15 top gainers dynamically selected)
      - Pump threshold 0.45 (was 0.65)
      - No BTC trend filter
      - Accept lower RSI range (was implicit RSI < 30 for OVERSOLD tag)
    Expected: ~5x more picks, WR ~55-58%
    """
    signals = []

    for symbol in CLAUDE_ML_MODERATE_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 50:
            continue

        close = df["Close"]
        volume = df["Volume"]
        current = float(close.iloc[-1])
        if current <= 0:
            continue

        rsi_14 = float(rsi(close, 14).iloc[-1])
        if pd.isna(rsi_14):
            continue

        vol_avg = float(volume.rolling(20).mean().iloc[-1])
        vol_ratio = float(volume.iloc[-1]) / vol_avg if vol_avg > 0 else 1.0

        mom_1d = float(close.pct_change(1).iloc[-1]) if len(close) > 1 else 0
        mom_3d = float(close.pct_change(3).iloc[-1]) if len(close) > 3 else 0
        mom_7d = float(close.pct_change(7).iloc[-1]) if len(close) > 7 else 0

        bb_width = float((close.rolling(20).std().iloc[-1] / close.rolling(20).mean().iloc[-1]))

        # Enhanced pump score with more features
        pump_score = 0.25
        if rsi_14 < 40:
            pump_score += 0.12
        if rsi_14 < 30:
            pump_score += 0.08  # deeper oversold bonus
        if vol_ratio > 1.3:
            pump_score += 0.08
        if vol_ratio > 2.0:
            pump_score += 0.07  # extreme volume bonus
        if mom_1d > 0.005:
            pump_score += 0.05
        if bb_width < 0.025:
            pump_score += 0.08  # compression
        if mom_3d < -0.02 and rsi_14 < 45:
            pump_score += 0.08  # mean reversion setup
        if mom_7d > 0.05 and mom_1d < -0.01:
            pump_score += 0.07  # pullback in uptrend

        # Even more relaxed: 0.45
        if pump_score < 0.45:
            continue

        atr_val = float(atr(df["High"], df["Low"], close).iloc[-1])
        if atr_val <= 0:
            continue

        tp = current + 2.0 * atr_val
        sl = current - 1.5 * atr_val

        conf = min(0.78, 0.48 + pump_score * 0.3)

        signals.append(_base_signal(
            "claude_ml_moderate_mut", symbol, "BUY", current, tp, sl, conf,
            f"Claude ML moderate: pump_score={pump_score:.2f} (threshold>=0.45), "
            f"RSI={rsi_14:.1f}, vol={vol_ratio:.1f}x, mom7d={mom_7d:.2%}",
            parent_system="claude_gainer_ml_perf",
            mutation_type="moderate",
            rsi_14=round(rsi_14, 1),
            volume_ratio=round(vol_ratio, 2),
            pump_score=round(pump_score, 3),
            timeframe="1h",
        ))

    return signals


# --- Mutation 1C: Aggressive — Yesterday-gainer momentum chase ---

def claude_ml_aggressive(data: dict) -> list[dict]:
    """
    Mutation of claude_gainer_ml_perf: Momentum chase on recent gainers.

    The original scanner's best feature was 'is_yesterday_gainer' (+3% boost).
    This mutation ONLY triggers on coins showing recent momentum, ignoring
    the ML ensemble entirely. Pure momentum with RSI guard.

    Entry: 1d return > +2% AND RSI < 70 AND volume > 1.5x avg
    Expected: Very high frequency, WR ~50-55% (momentum is real but noisy)
    """
    signals = []

    all_symbols = [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
        "ADAUSDT", "AVAXUSDT", "DOGEUSDT", "LINKUSDT", "NEARUSDT",
        "SUIUSDT", "APTUSDT", "INJUSDT", "TIAUSDT", "SEIUSDT",
        "LTCUSDT", "DOTUSDT", "MATICUSDT", "ATOMUSDT",
    ]

    for symbol in all_symbols:
        df = data.get(symbol)
        if df is None or len(df) < 30:
            continue

        close = df["Close"]
        volume = df["Volume"]
        current = float(close.iloc[-1])
        if current <= 0:
            continue

        # Momentum check: 1-day return > +2%
        mom_1d = float(close.pct_change(1).iloc[-1]) if len(close) > 1 else 0
        if mom_1d < 0.02:
            continue

        # RSI guard: not overbought
        rsi_14 = float(rsi(close, 14).iloc[-1])
        if pd.isna(rsi_14) or rsi_14 > 70:
            continue

        # Volume confirmation
        vol_avg = float(volume.rolling(20).mean().iloc[-1])
        vol_ratio = float(volume.iloc[-1]) / vol_avg if vol_avg > 0 else 1.0
        if vol_ratio < 1.5:
            continue

        atr_val = float(atr(df["High"], df["Low"], close).iloc[-1])
        if atr_val <= 0:
            continue

        # Tighter TP/SL for momentum trades
        tp = current + 1.5 * atr_val
        sl = current - 1.2 * atr_val

        conf = min(0.72, 0.50 + mom_1d * 2 + (vol_ratio - 1.5) * 0.05)

        signals.append(_base_signal(
            "claude_ml_aggressive_mut", symbol, "BUY", current, tp, sl, conf,
            f"Claude ML aggressive: momentum +{mom_1d:.1%} today, "
            f"RSI={rsi_14:.1f}, vol={vol_ratio:.1f}x — chase mode",
            parent_system="claude_gainer_ml_perf",
            mutation_type="aggressive",
            rsi_14=round(rsi_14, 1),
            volume_ratio=round(vol_ratio, 2),
            momentum_1d=round(mom_1d, 4),
            timeframe="1h",
        ))

    return signals


# ═══════════════════════════════════════════════════════════════════════════
# SYSTEM 2: KIMI SIGNAL TRACKING — 64% WR, 1028 trades
# Parent: KIMI_RISEOFTHECLAW/live_scanner.py
# Bottleneck: z-score < -2.0 (funding arb), RSI < 25 (flash crash),
#             beta < 0.8 (BAB), volume > 2x (bollinger). All very strict.
# ═══════════════════════════════════════════════════════════════════════════

# --- Mutation 2A: Conservative — Relax z-score & RSI thresholds ---

KIMI_TIER1_SYMBOLS_CRYPTO = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "MATICUSDT",
    "LTCUSDT", "TRXUSDT", "ATOMUSDT", "NEARUSDT",
]


def kimi_funding_arb_relaxed(data: dict) -> list[dict]:
    """
    Mutation of KIMI FundingRateArbitrage: Relaxed z-score threshold.

    Original: VWMA basis z-score < -2.0 (deeply below fair value)
    Relaxed: z-score < -1.5 (moderately below fair value)
    Expected: ~2.5x more signals, WR drops from ~64% -> ~56-60%
    """
    signals = []

    for symbol in KIMI_TIER1_SYMBOLS_CRYPTO:
        df = data.get(symbol)
        if df is None or len(df) < 100:
            continue

        close = df["Close"]
        volume = df["Volume"]
        current = float(close.iloc[-1])
        if current <= 0:
            continue

        # VWMA basis z-score (same calculation as KIMI live_scanner)
        vwma_val = _vwma(close, volume, 20)
        basis = (close - vwma_val) / vwma_val
        z = _zscore(basis, 60)
        z_val = float(z.iloc[-1])

        if pd.isna(z_val):
            continue

        # Relaxed threshold: -1.5 (was -2.0)
        if z_val >= -1.5:
            continue

        atr_val = float(atr(df["High"], df["Low"], close).iloc[-1])
        if atr_val <= 0:
            continue

        # Depth-based confidence: deeper z-score = higher confidence
        depth_bonus = min(abs(z_val) - 1.5, 1.0) * 0.1
        conf = min(0.80, 0.55 + depth_bonus)

        tp = current + 2.0 * atr_val
        sl = current - 1.5 * atr_val

        signals.append(_base_signal(
            "kimi_funding_arb_relaxed_mut", symbol, "BUY", current, tp, sl, conf,
            f"KIMI Funding Arb relaxed: VWMA z-score={z_val:.2f} (threshold<-1.5), "
            f"price deeply below volume-weighted fair value",
            parent_system="kimi_signal_tracking",
            mutation_type="conservative",
            z_score=round(z_val, 3),
            timeframe="1d",
        ))

    return signals


# --- Mutation 2B: Moderate — Flash crash with relaxed conditions ---

KIMI_FLASH_CRASH_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "ADAUSDT",
    "LINKUSDT", "DOTUSDT", "NEARUSDT", "ATOMUSDT",
    "DOGEUSDT", "SHIBUSDT",
    # Extended: high-beta alts that crash often
    "SUIUSDT", "APTUSDT", "INJUSDT", "TIAUSDT", "SEIUSDT",
]


def kimi_flash_crash_relaxed(data: dict) -> list[dict]:
    """
    Mutation of KIMI FlashCrashReversal: Relaxed drawdown + RSI + volume.

    Original: drawdown > 5% AND RSI(6) < 25 AND volume > 2x avg
    Relaxed:  drawdown > 3% AND RSI(6) < 35 AND volume > 1.3x avg
    Expected: ~4x more signals, WR ~55-60%
    """
    signals = []

    for symbol in KIMI_FLASH_CRASH_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 30:
            continue

        close = df["Close"]
        volume = df["Volume"]
        current = float(close.iloc[-1])
        if current <= 0:
            continue

        # Drawdown from 20-bar high (relaxed: 3% instead of 5%)
        rolling_high = float(close.rolling(20).max().iloc[-1])
        dd = (current - rolling_high) / rolling_high
        if dd > -0.03:
            continue

        # RSI(6) relaxed: < 35 instead of < 25
        rsi_6 = float(rsi(close, 6).iloc[-1])
        if pd.isna(rsi_6) or rsi_6 >= 35:
            continue

        # Volume relaxed: > 1.3x instead of > 2x
        vol_avg = float(volume.iloc[-21:-1].mean()) if len(volume) > 21 else float(volume.mean())
        vol_ratio = float(volume.iloc[-1]) / vol_avg if vol_avg > 0 else 0
        if vol_ratio < 1.3:
            continue

        atr_val = float(atr(df["High"], df["Low"], close).iloc[-1])
        if atr_val <= 0:
            continue

        # Confidence: deeper crash = higher confidence
        dd_depth = min(abs(dd) / 0.10, 1.0)
        rsi_depth = (35 - rsi_6) / 35
        conf = min(0.82, 0.52 + 0.15 * dd_depth + 0.10 * rsi_depth)

        tp = current + 2.5 * atr_val
        sl = current - 1.5 * atr_val

        signals.append(_base_signal(
            "kimi_flash_crash_relaxed_mut", symbol, "BUY", current, tp, sl, conf,
            f"KIMI Flash Crash relaxed: {dd*100:.1f}% drawdown (>=3%), "
            f"RSI(6)={rsi_6:.1f} (<35), vol={vol_ratio:.1f}x (>=1.3x)",
            parent_system="kimi_signal_tracking",
            mutation_type="moderate",
            drawdown_pct=round(dd * 100, 2),
            rsi_6=round(rsi_6, 1),
            volume_ratio=round(vol_ratio, 2),
            timeframe="1d",
        ))

    return signals


# --- Mutation 2C: Aggressive — Bollinger mean-rev without pump protection ---

def kimi_bollinger_aggressive(data: dict) -> list[dict]:
    """
    Mutation of KIMI BollingerMeanReversion: Remove pump protection + relax.

    Original: price <= lower BB AND RSI < 30 AND vol > 2x AND no recent pump
    Relaxed:  price within 0.5% of lower BB AND RSI < 40 AND vol > 1.2x
              Pump protection REMOVED (was blocking valid entries)
    Expected: ~5x more signals, WR ~50-55%
    """
    signals = []

    all_symbols = [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
        "DOGEUSDT", "SHIBUSDT", "NEARUSDT", "AVAXUSDT", "LINKUSDT",
        "ADAUSDT", "SUIUSDT", "APTUSDT", "INJUSDT",
    ]

    for symbol in all_symbols:
        df = data.get(symbol)
        if df is None or len(df) < 50:
            continue

        close = df["Close"]
        volume = df["Volume"]
        current = float(close.iloc[-1])
        if current <= 0:
            continue

        # Bollinger Bands (20, 2)
        sma_20 = float(close.rolling(20).mean().iloc[-1])
        std_20 = float(close.rolling(20).std().iloc[-1])
        if pd.isna(sma_20) or pd.isna(std_20) or std_20 <= 0:
            continue
        bb_lower = sma_20 - 2 * std_20

        # Relaxed: within 0.5% of lower band (not necessarily below it)
        if current > bb_lower * 1.005:
            continue

        # RSI relaxed: < 40 (was < 30)
        rsi_14 = float(rsi(close, 14).iloc[-1])
        if pd.isna(rsi_14) or rsi_14 >= 40:
            continue

        # Volume relaxed: > 1.2x (was > 2x)
        vol_avg = float(volume.rolling(20).mean().iloc[-1])
        vol_ratio = float(volume.iloc[-1]) / vol_avg if vol_avg > 0 else 0
        if vol_ratio < 1.2:
            continue

        # Trend guard: not in extreme downtrend (below 50d SMA by > 20%)
        if len(close) > 50:
            sma_50 = float(close.rolling(50).mean().iloc[-1])
            if current < sma_50 * 0.80:
                continue

        atr_val = float(atr(df["High"], df["Low"], close).iloc[-1])
        if atr_val <= 0:
            continue

        # Target: revert to SMA(20) or 2x ATR
        tp_sma = sma_20
        tp_atr = current + 2.0 * atr_val
        tp = min(tp_sma, tp_atr) if tp_sma > current else tp_atr
        sl = current - 1.5 * atr_val

        bb_pct = (current - bb_lower) / (2 * std_20 * 2) if std_20 > 0 else 0
        conf = min(0.78, 0.52 + (40 - rsi_14) / 100 + (vol_ratio - 1.2) * 0.05)

        signals.append(_base_signal(
            "kimi_bollinger_aggressive_mut", symbol, "BUY", current, tp, sl, conf,
            f"KIMI Bollinger aggressive: price near lower BB ({bb_pct:.1%}), "
            f"RSI={rsi_14:.1f} (<40), vol={vol_ratio:.1f}x, no pump filter",
            parent_system="kimi_signal_tracking",
            mutation_type="aggressive",
            rsi_14=round(rsi_14, 1),
            volume_ratio=round(vol_ratio, 2),
            bb_percentb=round(bb_pct, 3),
            timeframe="1d",
        ))

    return signals


# --- Mutation 2D: KIMI Drought-Adaptive (uses the v11 drought parameter) ---

def kimi_drought_adaptive(data: dict) -> list[dict]:
    """
    Mutation of KIMI's drought-adaptive system: Pre-apply drought=3 levels.

    KIMI v11+ has adaptive thresholds that relax during signal droughts.
    This mutation permanently operates at drought=3 (moderate drought),
    which relaxes z-scores by -0.45, RSI thresholds by +9, and
    volume thresholds by -0.6.

    Combined with mean-reversion z-score + RSI divergence logic.
    """
    signals = []
    drought = 3  # Permanent drought=3 relaxation

    all_symbols = [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
        "ADAUSDT", "AVAXUSDT", "LINKUSDT", "NEARUSDT", "DOTUSDT",
        "LTCUSDT", "ATOMUSDT", "SUIUSDT", "APTUSDT",
    ]

    for symbol in all_symbols:
        df = data.get(symbol)
        if df is None or len(df) < 50:
            continue

        close = df["Close"]
        volume = df["Volume"]
        current = float(close.iloc[-1])
        if current <= 0:
            continue

        # Z-score mean reversion (drought-adjusted threshold)
        mean20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        if pd.isna(mean20.iloc[-1]) or pd.isna(std20.iloc[-1]) or float(std20.iloc[-1]) <= 0:
            continue

        z_score = (current - float(mean20.iloc[-1])) / float(std20.iloc[-1])
        z_threshold = -2.0 - drought * 0.15  # = -2.45 with drought=3

        # RSI check (drought-adjusted)
        rsi_14 = float(rsi(close, 14).iloc[-1])
        if pd.isna(rsi_14):
            continue
        rsi_threshold = 32 + drought * 3  # = 41 with drought=3

        # Volume check (drought-adjusted)
        vol_avg = float(volume.rolling(20).mean().iloc[-1])
        vol_ratio = float(volume.iloc[-1]) / vol_avg if vol_avg > 0 else 1.0
        vol_threshold = max(1.5 - drought * 0.1, 1.0)  # = 1.2 with drought=3

        # Combined entry: z-score below threshold + RSI oversold + volume interest
        if z_score > z_threshold or rsi_14 > rsi_threshold or vol_ratio < vol_threshold:
            continue

        atr_val = float(atr(df["High"], df["Low"], close).iloc[-1])
        if atr_val <= 0:
            continue

        tp = current + 2.0 * atr_val
        sl = current - 1.5 * atr_val

        z_depth = min(abs(z_score) / 3.0, 1.0)
        rsi_depth = (rsi_threshold - rsi_14) / rsi_threshold
        conf = min(0.80, 0.50 + 0.15 * z_depth + 0.10 * rsi_depth)

        signals.append(_base_signal(
            "kimi_drought_adaptive_mut", symbol, "BUY", current, tp, sl, conf,
            f"KIMI drought-adaptive: z={z_score:.2f} (<{z_threshold:.1f}), "
            f"RSI={rsi_14:.1f} (<{rsi_threshold}), vol={vol_ratio:.1f}x (>={vol_threshold:.1f}x) "
            f"[drought_level=3]",
            parent_system="kimi_signal_tracking",
            mutation_type="drought_adaptive",
            z_score=round(z_score, 3),
            rsi_14=round(rsi_14, 1),
            volume_ratio=round(vol_ratio, 2),
            drought_level=drought,
            timeframe="1d",
        ))

    return signals


# ═══════════════════════════════════════════════════════════════════════════
# SYSTEM 3: CLAUDE GAINER — 56.2% WR, 32 trades
# Parent: claude_gainer_ml/live_scanner.py (non-ML variant)
# Bottleneck: Same as System 1 but uses simpler signals (momentum_ignition,
#             vol_spike, compression_breakout). Threshold 0.55.
# ═══════════════════════════════════════════════════════════════════════════

# --- Mutation 3A: Conservative — Compression breakout only ---

def gainer_compression_relaxed(data: dict) -> list[dict]:
    """
    Mutation of claude_gainer: Focus on compression breakout signal.

    Original: needed pump_probability >= 0.55 from full ML ensemble
    Mutation: Just needs Bollinger Band width < 3% (compression) +
              RSI between 40-60 (neutral) + volume starting to pick up
    This is the most reliable signal from the claude_gainer feature set.
    """
    signals = []

    all_symbols = [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
        "ADAUSDT", "AVAXUSDT", "DOGEUSDT", "LINKUSDT", "NEARUSDT",
        "LTCUSDT", "DOTUSDT", "MATICUSDT",
    ]

    for symbol in all_symbols:
        df = data.get(symbol)
        if df is None or len(df) < 50:
            continue

        close = df["Close"]
        volume = df["Volume"]
        current = float(close.iloc[-1])
        if current <= 0:
            continue

        # Bollinger Band width (compression indicator)
        sma_20 = close.rolling(20).mean()
        std_20 = close.rolling(20).std()
        bb_width = float(std_20.iloc[-1] / sma_20.iloc[-1]) if float(sma_20.iloc[-1]) > 0 else 1.0

        # Relaxed compression: < 3% (original implicit threshold was ~2%)
        if bb_width >= 0.03:
            continue

        # RSI in neutral zone (about to break either way, but we bet on continuation)
        rsi_14 = float(rsi(close, 14).iloc[-1])
        if pd.isna(rsi_14) or rsi_14 < 35 or rsi_14 > 65:
            continue

        # Volume starting to pick up (> 0.8x avg — not even 1x required)
        vol_avg = float(volume.rolling(20).mean().iloc[-1])
        vol_ratio = float(volume.iloc[-1]) / vol_avg if vol_avg > 0 else 1.0
        if vol_ratio < 0.8:
            continue

        # Trend direction: use 10-bar momentum to determine BUY vs SELL
        mom_10 = float(close.pct_change(10).iloc[-1]) if len(close) > 10 else 0
        sig_type = "BUY" if mom_10 >= 0 else "SELL"

        atr_val = float(atr(df["High"], df["Low"], close).iloc[-1])
        if atr_val <= 0:
            continue

        if sig_type == "BUY":
            tp = current + 2.0 * atr_val
            sl = current - 1.2 * atr_val
        else:
            tp = current - 2.0 * atr_val
            sl = current + 1.2 * atr_val

        conf = min(0.72, 0.50 + (0.03 - bb_width) * 10 + abs(mom_10) * 2)

        signals.append(_base_signal(
            "gainer_compression_relaxed_mut", symbol, sig_type, current, tp, sl, conf,
            f"Gainer compression: BB width={bb_width:.3f} (<3%), "
            f"RSI={rsi_14:.1f}, vol={vol_ratio:.1f}x, 10-bar mom={mom_10:.2%}",
            parent_system="claude_gainer",
            mutation_type="conservative",
            bb_width=round(bb_width, 4),
            rsi_14=round(rsi_14, 1),
            volume_ratio=round(vol_ratio, 2),
            timeframe="1h",
        ))

    return signals


# --- Mutation 3B: Moderate — OBV divergence + volume spike ---

def gainer_obv_divergence(data: dict) -> list[dict]:
    """
    Mutation of claude_gainer: OBV divergence with relaxed conditions.

    Original: OBV divergence was 1 of 10+ features feeding ML model.
    Mutation: Use OBV divergence as standalone signal with volume spike.
              OBV rising while price falling = accumulation (bullish).
    """
    signals = []

    all_symbols = [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
        "ADAUSDT", "AVAXUSDT", "DOGEUSDT", "LINKUSDT", "NEARUSDT",
        "SUIUSDT", "APTUSDT",
    ]

    for symbol in all_symbols:
        df = data.get(symbol)
        if df is None or len(df) < 30:
            continue

        close = df["Close"]
        volume = df["Volume"]
        current = float(close.iloc[-1])
        if current <= 0:
            continue

        # On Balance Volume
        obv = (volume * np.where(close.diff() > 0, 1, -1)).cumsum()

        # OBV divergence: price down over 5 bars but OBV up
        price_5d = float(close.pct_change(5).iloc[-1]) if len(close) > 5 else 0
        obv_5d = float(obv.iloc[-1] - obv.iloc[-6]) if len(obv) > 6 else 0

        # Price must be falling but OBV rising (accumulation)
        if price_5d >= 0 or obv_5d <= 0:
            continue

        # RSI not extreme
        rsi_14 = float(rsi(close, 14).iloc[-1])
        if pd.isna(rsi_14) or rsi_14 > 55 or rsi_14 < 20:
            continue

        # Volume interest
        vol_avg = float(volume.rolling(20).mean().iloc[-1])
        vol_ratio = float(volume.iloc[-1]) / vol_avg if vol_avg > 0 else 1.0
        if vol_ratio < 1.0:
            continue

        atr_val = float(atr(df["High"], df["Low"], close).iloc[-1])
        if atr_val <= 0:
            continue

        tp = current + 2.0 * atr_val
        sl = current - 1.5 * atr_val

        divergence_strength = abs(price_5d) + abs(obv_5d / (vol_avg * 5 + 1))
        conf = min(0.75, 0.50 + divergence_strength * 0.5 + (55 - rsi_14) / 100)

        signals.append(_base_signal(
            "gainer_obv_divergence_mut", symbol, "BUY", current, tp, sl, conf,
            f"Gainer OBV divergence: price {price_5d:.1%} (5d) but OBV rising, "
            f"RSI={rsi_14:.1f}, vol={vol_ratio:.1f}x — accumulation signal",
            parent_system="claude_gainer",
            mutation_type="moderate",
            price_5d_pct=round(price_5d, 4),
            rsi_14=round(rsi_14, 1),
            volume_ratio=round(vol_ratio, 2),
            timeframe="1h",
        ))

    return signals


# --- Mutation 3C: Aggressive — Multi-day gainer + green streak ---

def gainer_momentum_streak(data: dict) -> list[dict]:
    """
    Mutation of claude_gainer: Multi-day momentum streak hunter.

    Original: 'consecutive_green' and 'multi_day_gainer' were features.
    Mutation: Standalone trigger on 3+ green bars + accelerating volume.
    This catches the early phase of a multi-day pump.
    """
    signals = []

    all_symbols = [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
        "ADAUSDT", "AVAXUSDT", "DOGEUSDT", "LINKUSDT", "NEARUSDT",
        "SUIUSDT", "APTUSDT", "INJUSDT", "SEIUSDT",
    ]

    for symbol in all_symbols:
        df = data.get(symbol)
        if df is None or len(df) < 10:
            continue

        close = df["Close"]
        volume = df["Volume"]
        current = float(close.iloc[-1])
        if current <= 0:
            continue

        # Count consecutive green bars
        changes = close.diff()
        green_count = 0
        for i in range(len(changes) - 1, max(0, len(changes) - 8), -1):
            if float(changes.iloc[i]) > 0:
                green_count += 1
            else:
                break

        # Need at least 3 consecutive green bars (relaxed from implicit 4+)
        if green_count < 3:
            continue

        # RSI guard: not too overbought (allow up to 72)
        rsi_14 = float(rsi(close, 14).iloc[-1])
        if pd.isna(rsi_14) or rsi_14 > 72:
            continue

        # Volume acceleration: last bar volume > previous bar volume
        if len(volume) < 3:
            continue
        vol_accel = float(volume.iloc[-1]) > float(volume.iloc[-2])
        if not vol_accel:
            continue

        atr_val = float(atr(df["High"], df["Low"], close).iloc[-1])
        if atr_val <= 0:
            continue

        # Tight TP/SL for momentum continuation
        tp = current + 1.5 * atr_val
        sl = current - 1.0 * atr_val

        conf = min(0.70, 0.48 + green_count * 0.04 + (rsi_14 - 50) / 200)

        signals.append(_base_signal(
            "gainer_momentum_streak_mut", symbol, "BUY", current, tp, sl, conf,
            f"Gainer momentum streak: {green_count} consecutive green bars, "
            f"RSI={rsi_14:.1f}, volume accelerating — early pump phase",
            parent_system="claude_gainer",
            mutation_type="aggressive",
            green_streak=green_count,
            rsi_14=round(rsi_14, 1),
            timeframe="1h",
        ))

    return signals


# ═══════════════════════════════════════════════════════════════════════════
# SYSTEM 4: BATTLEGROUND — 61.6% WR, 380 trades
# Parent: ml_battleground/system_a_filter/scanner.py
# Bottleneck: ML filter score >= 0.65 (FILTER_THRESHOLD), plus
#             adaptive_threshold from cost model, plus regime filters
# ═══════════════════════════════════════════════════════════════════════════

# --- Mutation 4A: Conservative — Lower ML filter threshold ---

def battleground_ml_relaxed(data: dict) -> list[dict]:
    """
    Mutation of battleground System A: Lower ML filter threshold.

    Original: ML score >= 0.65 (BUY), 0.55 (SELL)
    Relaxed:  score >= 0.45 (BUY), 0.40 (SELL)
    We recreate the key signals without the actual ML model,
    using the underlying technical indicators that the ML was trained on.
    """
    signals = []

    all_symbols = [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
        "ADAUSDT", "AVAXUSDT", "LINKUSDT", "NEARUSDT", "DOTUSDT",
        "LTCUSDT", "MATICUSDT", "ATOMUSDT",
    ]

    for symbol in all_symbols:
        df = data.get(symbol)
        if df is None or len(df) < 100:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]
        current = float(close.iloc[-1])
        if current <= 0:
            continue

        # Feature composite (proxy for ML score)
        rsi_14 = float(rsi(close, 14).iloc[-1])
        rsi_50 = float(rsi(close, 50).iloc[-1]) if len(close) > 55 else 50.0
        if pd.isna(rsi_14):
            continue

        # VWAP deviation
        typical = (high + low + close) / 3
        vol_sum = volume.rolling(48).sum()
        vwap = (typical * volume).rolling(48).sum() / vol_sum
        vwap_dev = (current - float(vwap.iloc[-1])) / float(vwap.iloc[-1]) if not pd.isna(vwap.iloc[-1]) and float(vwap.iloc[-1]) > 0 else 0

        # Volume ratio
        vol_avg = float(volume.rolling(20).mean().iloc[-1])
        vol_ratio = float(volume.iloc[-1]) / vol_avg if vol_avg > 0 else 1.0

        # Drawdown from 50-bar high
        high_50 = float(high.rolling(50).max().iloc[-1]) if len(high) > 50 else float(high.max())
        dd_pct = (current - high_50) / high_50

        # Composite "ML proxy" score
        score = 0.30  # base
        if rsi_14 < 35:
            score += 0.10
        if rsi_14 < 25:
            score += 0.08
        if rsi_50 < 40:
            score += 0.07
        if vwap_dev < -0.01:
            score += 0.08
        if vwap_dev < -0.02:
            score += 0.07
        if vol_ratio > 1.5:
            score += 0.06
        if dd_pct < -0.05:
            score += 0.08
        if dd_pct < -0.10:
            score += 0.06

        # Relaxed threshold: 0.45 (original ML was 0.65)
        if score < 0.45:
            continue

        atr_val = float(atr(high, low, close).iloc[-1])
        if atr_val <= 0:
            continue

        tp = current + 2.0 * atr_val
        sl = current - 1.5 * atr_val

        conf = min(0.78, 0.45 + score * 0.4)

        signals.append(_base_signal(
            "battleground_ml_relaxed_mut", symbol, "BUY", current, tp, sl, conf,
            f"Battleground ML relaxed: composite score={score:.2f} (threshold>=0.45), "
            f"RSI14={rsi_14:.1f}, RSI50={rsi_50:.1f}, VWAP dev={vwap_dev:.2%}, "
            f"DD={dd_pct:.1%}, vol={vol_ratio:.1f}x",
            parent_system="battleground",
            mutation_type="conservative",
            ml_proxy_score=round(score, 3),
            rsi_14=round(rsi_14, 1),
            vwap_deviation=round(vwap_dev, 4),
            drawdown_pct=round(dd_pct, 4),
            volume_ratio=round(vol_ratio, 2),
            timeframe="4h",
        ))

    return signals


# --- Mutation 4B: Moderate — Multi-period RSI without regime filter ---

def battleground_rsi_no_regime(data: dict) -> list[dict]:
    """
    Mutation of battleground multi_period_rsi_confluence: Remove regime gate.

    Original: RSI(14) < 35 AND RSI(50) < 40, plus ML filter >= 0.65,
              plus regime detection gate
    Relaxed: RSI(14) < 42 AND RSI(50) < 48, no ML filter, no regime gate
    Expected: ~4x more signals
    """
    signals = []

    all_symbols = [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
        "ADAUSDT", "AVAXUSDT", "LINKUSDT", "NEARUSDT", "DOTUSDT",
        "LTCUSDT", "SUIUSDT", "APTUSDT",
    ]

    for symbol in all_symbols:
        df = data.get(symbol)
        if df is None or len(df) < 60:
            continue

        close = df["Close"]
        current = float(close.iloc[-1])
        if current <= 0:
            continue

        rsi_14 = float(rsi(close, 14).iloc[-1])
        rsi_50 = float(rsi(close, 50).iloc[-1]) if len(close) > 55 else 50.0

        if pd.isna(rsi_14) or pd.isna(rsi_50):
            continue

        # Relaxed dual RSI thresholds
        if rsi_14 >= 42 or rsi_50 >= 48:
            continue

        # RSI(14) must be turning up (momentum reversal confirmation)
        if len(close) > 2:
            prev_rsi = float(rsi(close, 14).iloc[-2])
            if rsi_14 <= prev_rsi:
                continue

        atr_val = float(atr(df["High"], df["Low"], close).iloc[-1])
        if atr_val <= 0:
            continue

        tp = current + 2.0 * atr_val
        sl = current - 1.5 * atr_val

        rsi14_depth = (42 - rsi_14) / 42
        rsi50_depth = (48 - rsi_50) / 48
        conf = min(0.78, 0.52 + 0.12 * rsi14_depth + 0.10 * rsi50_depth)

        signals.append(_base_signal(
            "battleground_rsi_no_regime_mut", symbol, "BUY", current, tp, sl, conf,
            f"Battleground RSI no-regime: RSI14={rsi_14:.1f} (<42, rising), "
            f"RSI50={rsi_50:.1f} (<48) — dual RSI oversold, no regime gate",
            parent_system="battleground",
            mutation_type="moderate",
            rsi_14=round(rsi_14, 1),
            rsi_50=round(rsi_50, 1),
            timeframe="4h",
        ))

    return signals


# --- Mutation 4C: Aggressive — VWAP reversion on 1h timeframe ---

def battleground_vwap_1h(data: dict) -> list[dict]:
    """
    Mutation of battleground VWAP deviation reversion: Faster timeframe.

    Original: VWAP 2-sigma deviation on 4h bars, Hurst < 0.60
    Relaxed: VWAP 1.2-sigma deviation on 1h bars, no Hurst gate
    Much higher frequency but noisier. Trades the institutional
    VWAP magnet effect on shorter timeframes.
    """
    signals = []

    all_symbols = [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
        "ADAUSDT", "AVAXUSDT", "LINKUSDT", "NEARUSDT",
        "DOGEUSDT", "SUIUSDT", "APTUSDT",
    ]

    for symbol in all_symbols:
        df = data.get(symbol)
        if df is None or len(df) < 60:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]
        current = float(close.iloc[-1])
        if current <= 0:
            continue

        # Rolling VWAP (24-bar for 1h = ~1 day)
        lookback = 24
        typical = (high + low + close) / 3
        cum_tp_vol = (typical * volume).rolling(lookback).sum()
        cum_vol = volume.rolling(lookback).sum()
        vwap = cum_tp_vol / cum_vol

        if pd.isna(vwap.iloc[-1]) or float(vwap.iloc[-1]) == 0:
            continue

        current_vwap = float(vwap.iloc[-1])
        vwap_dev = (current - current_vwap) / current_vwap

        # 1.2-sigma deviation bands (very relaxed from 2.0-sigma)
        deviation = typical - vwap
        std_dev = deviation.rolling(lookback).std()
        if pd.isna(std_dev.iloc[-1]):
            continue
        lower_band = current_vwap - 1.2 * float(std_dev.iloc[-1])

        # Must be below lower band
        if current >= lower_band:
            continue

        # Min deviation 0.3% (relaxed from 0.5-0.8%)
        if abs(vwap_dev) < 0.003:
            continue

        atr_val = float(atr(high, low, close).iloc[-1])
        if atr_val <= 0:
            continue

        # Target: revert to VWAP
        tp = current_vwap
        sl = current - 1.5 * atr_val

        # Ensure minimum R:R
        if tp <= current or (current - sl) <= 0:
            continue
        rr = (tp - current) / (current - sl)
        if rr < 1.0:
            tp = current + (current - sl) * 1.0

        dev_depth = min(abs(vwap_dev) / 0.02, 1.0)
        conf = min(0.75, 0.50 + 0.15 * dev_depth)

        signals.append(_base_signal(
            "battleground_vwap_1h_mut", symbol, "BUY", current, tp, sl, conf,
            f"Battleground VWAP 1h: {vwap_dev:.2%} below VWAP, "
            f"1.2-sigma band breach — institutional magnet effect",
            parent_system="battleground",
            mutation_type="aggressive",
            vwap_deviation=round(vwap_dev, 4),
            vwap_price=round(current_vwap, 4),
            timeframe="1h",
        ))

    return signals


# --- Mutation 4D: Battleground contrarian SELL ---

def battleground_contrarian_sell(data: dict) -> list[dict]:
    """
    Mutation of battleground: Invert winning BUY logic to SELL.

    The battleground system is 61.6% WR on BUY signals.
    This variant triggers SELL when the OPPOSITE conditions occur:
    RSI(14) > 65 AND RSI(50) > 60 AND VWAP deviation > +1.5%

    Contrarian assumption: if oversold bounces work 61.6% of the time,
    overbought fades might work at a similar rate.
    """
    signals = []

    all_symbols = [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
        "ADAUSDT", "AVAXUSDT", "DOGEUSDT",
    ]

    for symbol in all_symbols:
        df = data.get(symbol)
        if df is None or len(df) < 60:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]
        current = float(close.iloc[-1])
        if current <= 0:
            continue

        rsi_14 = float(rsi(close, 14).iloc[-1])
        rsi_50 = float(rsi(close, 50).iloc[-1]) if len(close) > 55 else 50.0

        if pd.isna(rsi_14) or pd.isna(rsi_50):
            continue

        # Overbought conditions (inverse of oversold BUY)
        if rsi_14 < 65 or rsi_50 < 60:
            continue

        # RSI must be turning down
        if len(close) > 2:
            prev_rsi = float(rsi(close, 14).iloc[-2])
            if rsi_14 >= prev_rsi:
                continue

        # VWAP above (price extended above fair value)
        typical = (high + low + close) / 3
        vol_sum = volume.rolling(24).sum()
        vwap = (typical * volume).rolling(24).sum() / vol_sum
        if pd.isna(vwap.iloc[-1]) or float(vwap.iloc[-1]) == 0:
            continue
        vwap_dev = (current - float(vwap.iloc[-1])) / float(vwap.iloc[-1])
        if vwap_dev < 0.015:
            continue

        atr_val = float(atr(high, low, close).iloc[-1])
        if atr_val <= 0:
            continue

        tp = current - 2.0 * atr_val
        sl = current + 1.5 * atr_val

        conf = min(0.72, 0.50 + (rsi_14 - 65) / 100 + vwap_dev * 5)

        signals.append(_base_signal(
            "battleground_contrarian_sell_mut", symbol, "SELL", current, tp, sl, conf,
            f"Battleground contrarian SELL: RSI14={rsi_14:.1f} (>65, falling), "
            f"RSI50={rsi_50:.1f} (>60), VWAP dev=+{vwap_dev:.2%} — overbought fade",
            parent_system="battleground",
            mutation_type="contrarian",
            rsi_14=round(rsi_14, 1),
            rsi_50=round(rsi_50, 1),
            vwap_deviation=round(vwap_dev, 4),
            timeframe="4h",
        ))

    return signals


# ═══════════════════════════════════════════════════════════════════════════
# System 5: Justin Breakout Volume v2 — THE GREAT PURGE RESURRECTION
# ═══════════════════════════════════════════════════════════════════════════
#
# Parent: justin_breakout_volume_v2 (alpha_engine/justin_bravo_strategies_v2.py)
# Core logic: 20-bar range breakout + 1.3x volume + RSI filter + ATR TP/SL
# NOT in any mutation pipeline until now — unanimous AI consensus to add it.

JUSTIN_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "ADAUSDT", "AVAXUSDT", "DOGEUSDT", "NEARUSDT", "MATICUSDT",
]


def _justin_core(data: dict, lookback: int, vol_thresh: float,
                 range_max: float, rsi_cap: int, rsi_floor: int,
                 atr_mult: float, mutation_label: str) -> list[dict]:
    """Shared core for justin breakout mutations."""
    signals = []

    for symbol in JUSTIN_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < lookback + 5:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]

        current = float(close.iloc[-1])
        prev_close = float(close.iloc[-2])
        curr_high = float(high.iloc[-1])
        curr_low = float(low.iloc[-1])
        if current <= 0:
            continue

        recent_high = float(high.iloc[-lookback-1:-1].max())
        recent_low = float(low.iloc[-lookback-1:-1].min())

        # Consolidation check
        if recent_low <= 0:
            continue
        range_pct = (recent_high - recent_low) / recent_low
        if range_pct >= range_max:
            continue

        # Volume confirmation
        vol_ma = float(volume.iloc[-lookback:].mean())
        curr_vol = float(volume.iloc[-1])
        if vol_ma <= 0:
            continue
        vol_ratio = curr_vol / vol_ma

        if vol_ratio < vol_thresh:
            continue

        rsi_val = float(rsi(close, 14).iloc[-1])
        if pd.isna(rsi_val):
            continue

        atr_val = float(atr(high, low, close).iloc[-1])
        if atr_val <= 0:
            continue

        direction = None
        tp = sl = 0

        # LONG breakout
        if curr_high > recent_high * 0.998 and current > prev_close and rsi_val < rsi_cap:
            direction = "BUY"
            tp = current + atr_mult * atr_val
            sl = recent_low * 0.995

        # SHORT breakdown
        elif curr_low < recent_low * 1.002 and current < prev_close and rsi_val > rsi_floor:
            direction = "SELL"
            tp = current - atr_mult * atr_val
            sl = recent_high * 1.005

        if direction is None:
            continue

        conf = min(0.72, 0.55 + (vol_ratio - vol_thresh) * 0.1)

        signals.append(_base_signal(
            f"justin_{mutation_label}_mut", symbol, direction, current, tp, sl, conf,
            f"Justin {mutation_label}: {lookback}-bar breakout, vol={vol_ratio:.2f}x, "
            f"RSI={rsi_val:.1f}, range={range_pct:.2%}, ATR_mult={atr_mult}",
            parent_system="justin_breakout_volume_v2",
            mutation_type=mutation_label,
            volume_ratio=round(vol_ratio, 2),
            rsi_14=round(rsi_val, 1),
            range_pct=round(range_pct, 4),
            timeframe="4h",
        ))

    return signals


# --- Mutation 5A: Conservative — tighter range, same volume ---
def justin_conservative(data: dict) -> list[dict]:
    """Conservative: 15-bar lookback, tighter consolidation (10%), 1.5x volume."""
    return _justin_core(data, lookback=15, vol_thresh=1.5, range_max=0.10,
                        rsi_cap=70, rsi_floor=30, atr_mult=2.0,
                        mutation_label="conservative")


# --- Mutation 5B: Moderate — relaxed volume, wider range ---
def justin_moderate(data: dict) -> list[dict]:
    """Moderate: 20-bar (original), lower volume bar (1.1x), wider range (18%)."""
    return _justin_core(data, lookback=20, vol_thresh=1.1, range_max=0.18,
                        rsi_cap=78, rsi_floor=22, atr_mult=2.5,
                        mutation_label="moderate")


# --- Mutation 5C: Aggressive — short lookback, minimal filters ---
def justin_aggressive(data: dict) -> list[dict]:
    """Aggressive: 10-bar micro breakout, low volume bar (1.0x), wide range (20%), 3x ATR TP."""
    return _justin_core(data, lookback=10, vol_thresh=1.0, range_max=0.20,
                        rsi_cap=80, rsi_floor=20, atr_mult=3.0,
                        mutation_label="aggressive")


# --- Mutation 5D: Scalper — very short lookback, tight TP ---
def justin_scalper(data: dict) -> list[dict]:
    """Scalper: 8-bar micro breakout, 1.2x volume, tight 1.2x ATR TP for quick captures."""
    return _justin_core(data, lookback=8, vol_thresh=1.2, range_max=0.08,
                        rsi_cap=72, rsi_floor=28, atr_mult=1.2,
                        mutation_label="scalper")


# ═══════════════════════════════════════════════════════════════════════════
# REGISTRY — All DNA Winner Mutations
# ═══════════════════════════════════════════════════════════════════════════

DNA_WINNER_MUTATIONS = {
    # System 1: Claude Gainer ML Perf (70% WR) — 3 mutations
    "claude_ml_conservative_mut": {
        "fn": claude_ml_conservative,
        "parent": "claude_gainer_ml_perf",
        "mutation": "conservative",
        "trust_weight": 0.3,
        "description": "Lower pump probability threshold (0.50 vs 0.65)",
    },
    "claude_ml_moderate_mut": {
        "fn": claude_ml_moderate,
        "parent": "claude_gainer_ml_perf",
        "mutation": "moderate",
        "trust_weight": 0.3,
        "description": "Expanded universe + lower threshold (0.45)",
    },
    "claude_ml_aggressive_mut": {
        "fn": claude_ml_aggressive,
        "parent": "claude_gainer_ml_perf",
        "mutation": "aggressive",
        "trust_weight": 0.3,
        "description": "Momentum chase on recent gainers (no ML)",
    },

    # System 2: KIMI Signal Tracking (64% WR) — 4 mutations
    "kimi_funding_arb_relaxed_mut": {
        "fn": kimi_funding_arb_relaxed,
        "parent": "kimi_signal_tracking",
        "mutation": "conservative",
        "trust_weight": 0.3,
        "description": "VWMA z-score < -1.5 (was -2.0)",
    },
    "kimi_flash_crash_relaxed_mut": {
        "fn": kimi_flash_crash_relaxed,
        "parent": "kimi_signal_tracking",
        "mutation": "moderate",
        "trust_weight": 0.3,
        "description": "Flash crash: 3% DD + RSI<35 + vol>1.3x (all relaxed)",
    },
    "kimi_bollinger_aggressive_mut": {
        "fn": kimi_bollinger_aggressive,
        "parent": "kimi_signal_tracking",
        "mutation": "aggressive",
        "trust_weight": 0.3,
        "description": "Bollinger mean-rev without pump protection",
    },
    "kimi_drought_adaptive_mut": {
        "fn": kimi_drought_adaptive,
        "parent": "kimi_signal_tracking",
        "mutation": "drought_adaptive",
        "trust_weight": 0.3,
        "description": "Permanent drought=3 level (pre-relaxed thresholds)",
    },

    # System 3: Claude Gainer (56.2% WR) — 3 mutations
    "gainer_compression_relaxed_mut": {
        "fn": gainer_compression_relaxed,
        "parent": "claude_gainer",
        "mutation": "conservative",
        "trust_weight": 0.3,
        "description": "Compression breakout only (BB width < 3%)",
    },
    "gainer_obv_divergence_mut": {
        "fn": gainer_obv_divergence,
        "parent": "claude_gainer",
        "mutation": "moderate",
        "trust_weight": 0.3,
        "description": "OBV divergence as standalone signal",
    },
    "gainer_momentum_streak_mut": {
        "fn": gainer_momentum_streak,
        "parent": "claude_gainer",
        "mutation": "aggressive",
        "trust_weight": 0.3,
        "description": "3+ green bars + volume acceleration",
    },

    # System 4: Battleground (61.6% WR) — 4 mutations
    "battleground_ml_relaxed_mut": {
        "fn": battleground_ml_relaxed,
        "parent": "battleground",
        "mutation": "conservative",
        "trust_weight": 0.3,
        "description": "ML proxy score >= 0.45 (was 0.65)",
    },
    "battleground_rsi_no_regime_mut": {
        "fn": battleground_rsi_no_regime,
        "parent": "battleground",
        "mutation": "moderate",
        "trust_weight": 0.3,
        "description": "Dual RSI without regime gate",
    },
    "battleground_vwap_1h_mut": {
        "fn": battleground_vwap_1h,
        "parent": "battleground",
        "mutation": "aggressive",
        "trust_weight": 0.3,
        "description": "VWAP reversion on 1h (1.2-sigma, no Hurst gate)",
    },
    "battleground_contrarian_sell_mut": {
        "fn": battleground_contrarian_sell,
        "parent": "battleground",
        "mutation": "contrarian",
        "trust_weight": 0.3,
        "description": "Inverted BUY logic for SELL signals",
    },

    # System 5: Justin Breakout Volume v2 (alpha engine) — 4 mutations
    # THE GREAT PURGE RESURRECTION: all AIs agreed to add this to mutation pipeline
    "justin_conservative_mut": {
        "fn": justin_conservative,
        "parent": "justin_breakout_volume_v2",
        "mutation": "conservative",
        "trust_weight": 0.3,
        "description": "15-bar lookback, tighter consolidation (10%), 1.5x volume",
    },
    "justin_moderate_mut": {
        "fn": justin_moderate,
        "parent": "justin_breakout_volume_v2",
        "mutation": "moderate",
        "trust_weight": 0.3,
        "description": "Original 20-bar, lower volume bar (1.1x), wider range (18%)",
    },
    "justin_aggressive_mut": {
        "fn": justin_aggressive,
        "parent": "justin_breakout_volume_v2",
        "mutation": "aggressive",
        "trust_weight": 0.3,
        "description": "10-bar micro breakout, minimal filters, 3x ATR TP",
    },
    "justin_scalper_mut": {
        "fn": justin_scalper,
        "parent": "justin_breakout_volume_v2",
        "mutation": "scalper",
        "trust_weight": 0.3,
        "description": "8-bar micro breakout for quick captures (1.2x ATR TP)",
    },
}

# Total: 18 mutations across 5 winning systems


# ═══════════════════════════════════════════════════════════════════════════
# RUNNER — Fetch data & execute all mutations
# ═══════════════════════════════════════════════════════════════════════════

# All unique symbols across all mutations
ALL_SCAN_SYMBOLS = sorted(set(
    CLAUDE_ML_CONSERVATIVE_SYMBOLS +
    CLAUDE_ML_MODERATE_SYMBOLS +
    KIMI_TIER1_SYMBOLS_CRYPTO +
    KIMI_FLASH_CRASH_SYMBOLS +
    ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
     "ADAUSDT", "AVAXUSDT", "DOGEUSDT", "LINKUSDT", "NEARUSDT",
     "SUIUSDT", "APTUSDT", "INJUSDT", "TIAUSDT", "SEIUSDT",
     "LTCUSDT", "DOTUSDT", "MATICUSDT", "ATOMUSDT", "SHIBUSDT",
     "JUPUSDT", "WUSDT", "STXUSDT", "IMXUSDT", "OPUSDT",
     ]
))


def run_all_mutations(interval: str = "1h", limit: int = 300) -> dict:
    """
    Fetch market data and run all 14 DNA winner mutations.

    Returns:
        {
            "metadata": {...},
            "picks": [...],
            "mutations_triggered": [...],
            "mutations_silent": [...]
        }
    """
    print(f"\n{'='*70}")
    print(f"DNA WINNER MUTATIONS — {len(DNA_WINNER_MUTATIONS)} strategies")
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

    for name, info in DNA_WINNER_MUTATIONS.items():
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
            "total_mutations": len(DNA_WINNER_MUTATIONS),
            "total_picks": len(all_picks),
            "mutations_triggered": len(triggered),
            "mutations_silent": len(silent),
            "symbols_scanned": len(data),
            "interval": interval,
            "system": "dna_winner_mutations",
        },
        "picks": all_picks,
        "mutations_triggered": triggered,
        "mutations_silent": silent,
    }

    print(f"\n{'='*70}")
    print(f"RESULTS: {len(all_picks)} picks from {len(triggered)}/{len(DNA_WINNER_MUTATIONS)} mutations")
    print(f"{'='*70}\n")

    return result


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="DNA Winner Mutations Scanner")
    parser.add_argument("--interval", default="1h", choices=["1h", "4h", "1d"],
                        help="Kline interval (default: 1h)")
    parser.add_argument("--limit", type=int, default=300,
                        help="Number of bars to fetch (default: 300)")
    parser.add_argument("--output", default=None,
                        help="Output JSON path (default: genome/data/dna_winner_picks.json)")
    args = parser.parse_args()

    output_path = args.output or str(ROOT / "genome" / "data" / "dna_winner_picks.json")

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
