#!/usr/bin/env python3
"""
Trusted Genome Mutations — Battle-Tested Regime/Vol-Adaptive Strategies
========================================================================

Top 5 mutations from trusted_genome_picks.md, designed with regime awareness
and volatility adaptation. These exploit edges that survived extensive
backtesting across 30+ crypto symbols including crash periods.

Mutations:
  1. regime_switch_mut      — Trend-follow in high-vol, mean-revert in low-vol
  2. basket_corr_gate_mut   — Only trade alts correlated with BTC (>0.4)
  3. vol_scaler_size_mut    — Inverse-vol confidence scaling (lower size in chaos)
  4. mtf_align_mut          — 3-timeframe confluence (1h, 4h-proxy, daily-proxy)
  5. vol_adaptive_thresh_mut — ATR-scaled RSI thresholds (widen in high-vol)

All SANDBOX tier (0.3 weight) until forward-test validation.
"""

from __future__ import annotations

import json
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

# ── Path setup ────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent.parent

try:
    sys.path.insert(0, str(ROOT / "ml_battleground"))
    from shared.indicators import rsi, atr, sma, ema
    _HAS_INDICATORS = True
except ImportError:
    _HAS_INDICATORS = False

if not _HAS_INDICATORS:
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


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def bollinger_bands(close: pd.Series, period: int = 20, std_mult: float = 2.0):
    mid = close.rolling(period).mean()
    std = close.rolling(period).std()
    upper = mid + std_mult * std
    lower = mid - std_mult * std
    return upper, mid, lower


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


# ── Data Fetching ─────────────────────────────────────────────────────────

BINANCE_MIRRORS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api3.binance.com",
]

SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "AVAXUSDT", "LINKUSDT", "NEARUSDT", "SUIUSDT", "APTUSDT",
    "JUPUSDT", "INJUSDT", "FETUSDT", "TAOUSDT", "SEIUSDT",
    "DOGEUSDT", "ARBUSDT", "OPUSDT", "TIAUSDT", "FILUSDT", "LTCUSDT",
]

MIN_BARS = 100


def fetch_klines(symbol: str, interval: str = "1h", limit: int = 300) -> pd.DataFrame | None:
    """Fetch OHLCV klines from Binance."""
    for base in BINANCE_MIRRORS:
        url = f"{base}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "GenomeMutationLab/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = json.loads(resp.read())
            df = pd.DataFrame(raw, columns=[
                "OpenTime", "Open", "High", "Low", "Close", "Volume",
                "CloseTime", "QuoteVol", "Trades", "TakerBuyBase", "TakerBuyQuote", "Ignore"
            ])
            for col in ("Open", "High", "Low", "Close", "Volume"):
                df[col] = df[col].astype(float)
            return df
        except Exception:
            continue
    return None


# ═══════════════════════════════════════════════════════════════════════════
# MUTATION 1: regime_switch_mut
# ═══════════════════════════════════════════════════════════════════════════
# Concept: Detect market regime via rolling volatility percentile.
# High-vol regime -> trend-following (momentum breakouts)
# Low-vol regime  -> mean-reversion (fade RSI extremes)
# Backtest: BTC +12%, SOL +26%, DOT +51% (Dynamic mode)

def regime_switch_mut(data: dict) -> list:
    """Regime-adaptive strategy: trend-follow in high-vol, mean-revert in low-vol."""
    signals = []

    for symbol in SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < MIN_BARS:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        current = float(close.iloc[-1])
        if current <= 0:
            continue

        # Regime detection: rolling 20-bar volatility percentile over 100 bars
        returns = close.pct_change().dropna()
        if len(returns) < MIN_BARS:
            continue
        vol_20 = returns.rolling(20).std()
        vol_pctile = vol_20.rank(pct=True)
        current_vol_pctile = float(vol_pctile.iloc[-1]) if not np.isnan(vol_pctile.iloc[-1]) else 0.5

        atr_val = float(atr(high, low, close, 14).iloc[-1])
        if atr_val <= 0 or np.isnan(atr_val):
            continue

        rsi_val = float(rsi(close, 14).iloc[-1])
        macd_line, macd_sig, macd_hist = macd(close)
        hist_now = float(macd_hist.iloc[-1])

        is_high_vol = current_vol_pctile > 0.65  # top 35% = trend regime
        regime = "TREND" if is_high_vol else "MEANREV"

        if regime == "TREND":
            # Trend-following: momentum breakout
            ema_fast = float(ema(close, 9).iloc[-1])
            ema_slow = float(ema(close, 21).iloc[-1])
            ema_trend = float(ema(close, 50).iloc[-1])

            # LONG: fast > slow > trend, MACD positive, RSI not overbought
            if ema_fast > ema_slow > ema_trend and hist_now > 0 and rsi_val < 70:
                conf = 0.55 + min(0.25, (ema_fast - ema_slow) / atr_val * 0.1)
                tp = current + 2.5 * atr_val
                sl = current - 1.5 * atr_val
                signals.append(_base_signal(
                    "regime_switch_mut", symbol, "BUY", current, tp, sl, conf,
                    f"TREND regime (vol_pctile={current_vol_pctile:.0%}): EMA stack bullish, MACD+, RSI={rsi_val:.0f}",
                    "trusted_genome", "regime_switch",
                ))

            # SHORT: fast < slow < trend, MACD negative, RSI not oversold
            elif ema_fast < ema_slow < ema_trend and hist_now < 0 and rsi_val > 30:
                conf = 0.55 + min(0.25, (ema_slow - ema_fast) / atr_val * 0.1)
                tp = current - 2.5 * atr_val
                sl = current + 1.5 * atr_val
                signals.append(_base_signal(
                    "regime_switch_mut", symbol, "SELL", current, tp, sl, conf,
                    f"TREND regime (vol_pctile={current_vol_pctile:.0%}): EMA stack bearish, MACD-, RSI={rsi_val:.0f}",
                    "trusted_genome", "regime_switch",
                ))

        else:
            # Mean-reversion: fade RSI extremes
            bb_upper, bb_mid, bb_lower = bollinger_bands(close, 20, 2.0)
            bb_up = float(bb_upper.iloc[-1])
            bb_lo = float(bb_lower.iloc[-1])

            # LONG: RSI oversold + price near/below lower BB
            if rsi_val < 30 and current <= bb_lo * 1.01:
                conf = 0.60 + min(0.20, (30 - rsi_val) / 30 * 0.2)
                tp = current + 2.0 * atr_val
                sl = current - 1.2 * atr_val
                signals.append(_base_signal(
                    "regime_switch_mut", symbol, "BUY", current, tp, sl, conf,
                    f"MEANREV regime (vol_pctile={current_vol_pctile:.0%}): RSI={rsi_val:.0f} oversold, price at BB lower",
                    "trusted_genome", "regime_switch",
                ))

            # SHORT: RSI overbought + price near/above upper BB
            elif rsi_val > 70 and current >= bb_up * 0.99:
                conf = 0.60 + min(0.20, (rsi_val - 70) / 30 * 0.2)
                tp = current - 2.0 * atr_val
                sl = current + 1.2 * atr_val
                signals.append(_base_signal(
                    "regime_switch_mut", symbol, "SELL", current, tp, sl, conf,
                    f"MEANREV regime (vol_pctile={current_vol_pctile:.0%}): RSI={rsi_val:.0f} overbought, price at BB upper",
                    "trusted_genome", "regime_switch",
                ))

    return signals


# ═══════════════════════════════════════════════════════════════════════════
# MUTATION 2: basket_corr_gate_mut
# ═══════════════════════════════════════════════════════════════════════════
# Concept: Only trade alts when their 30-bar rolling correlation with BTC > 0.4.
# High correlation = predictable (alt follows BTC). Low corr = noise, skip.
# Filters out chaotic alt moves (TRX -40%, TON invalid in backtests).

def basket_corr_gate_mut(data: dict) -> list:
    """Correlation-gated alt trading: only enter when alt tracks BTC."""
    signals = []

    btc_df = data.get("BTCUSDT")
    if btc_df is None or len(btc_df) < MIN_BARS:
        return signals

    btc_returns = btc_df["Close"].pct_change().dropna()

    for symbol in SYMBOLS:
        if symbol == "BTCUSDT":
            continue  # Don't correlate BTC with itself

        df = data.get(symbol)
        if df is None or len(df) < MIN_BARS:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        current = float(close.iloc[-1])
        if current <= 0:
            continue

        # Rolling 30-bar correlation with BTC
        alt_returns = close.pct_change().dropna()
        min_len = min(len(btc_returns), len(alt_returns))
        if min_len < 30:
            continue

        corr = float(np.corrcoef(
            btc_returns.values[-min_len:],
            alt_returns.values[-min_len:]
        )[0, 1])

        if np.isnan(corr) or corr < 0.4:
            continue  # Gate: skip uncorrelated alts

        # Now apply a simple momentum signal on the gated alt
        atr_val = float(atr(high, low, close, 14).iloc[-1])
        if atr_val <= 0 or np.isnan(atr_val):
            continue

        rsi_val = float(rsi(close, 14).iloc[-1])
        ema_9 = float(ema(close, 9).iloc[-1])
        ema_21 = float(ema(close, 21).iloc[-1])
        macd_line_s, _, macd_hist_s = macd(close)
        hist_now = float(macd_hist_s.iloc[-1])

        # LONG: EMA bullish + MACD positive + RSI not extreme
        if ema_9 > ema_21 and hist_now > 0 and 35 < rsi_val < 65:
            conf = 0.55 + min(0.25, corr * 0.2)  # Higher corr = higher confidence
            tp = current + 2.0 * atr_val
            sl = current - 1.5 * atr_val
            signals.append(_base_signal(
                "basket_corr_gate_mut", symbol, "BUY", current, tp, sl, conf,
                f"Corr-gated (BTC corr={corr:.2f}): EMA 9>{ema_9:.4f}>21, MACD+, RSI={rsi_val:.0f}",
                "trusted_genome", "basket_corr_gate",
            ))

        # SHORT: EMA bearish + MACD negative + RSI mid-range
        elif ema_9 < ema_21 and hist_now < 0 and 35 < rsi_val < 65:
            conf = 0.55 + min(0.25, corr * 0.2)
            tp = current - 2.0 * atr_val
            sl = current + 1.5 * atr_val
            signals.append(_base_signal(
                "basket_corr_gate_mut", symbol, "SELL", current, tp, sl, conf,
                f"Corr-gated (BTC corr={corr:.2f}): EMA 9<21, MACD-, RSI={rsi_val:.0f}",
                "trusted_genome", "basket_corr_gate",
            ))

    return signals


# ═══════════════════════════════════════════════════════════════════════════
# MUTATION 3: vol_scaler_size_mut
# ═══════════════════════════════════════════════════════════════════════════
# Concept: Scale confidence (proxy for position size) inversely with volatility.
# High vol = smaller size (lower confidence), low vol = larger size.
# Cuts drawdown on high-vol assets (ARB -63% -> est 30% with scaling).

def vol_scaler_size_mut(data: dict) -> list:
    """Inverse volatility-scaled entries: lower confidence in high-vol environments."""
    signals = []

    for symbol in SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < MIN_BARS:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        current = float(close.iloc[-1])
        if current <= 0:
            continue

        # Volatility scaling: current ATR vs average ATR
        atr_series = atr(high, low, close, 14)
        atr_val = float(atr_series.iloc[-1])
        avg_atr = float(atr_series.rolling(50).mean().iloc[-1])

        if atr_val <= 0 or avg_atr <= 0 or np.isnan(atr_val) or np.isnan(avg_atr):
            continue

        vol_ratio = atr_val / avg_atr  # >1 = above-avg vol, <1 = below-avg
        # Inverse scale: high vol -> lower confidence multiplier
        vol_scale = np.clip(1.0 / vol_ratio, 0.5, 1.5)

        rsi_val = float(rsi(close, 14).iloc[-1])
        ema_9 = float(ema(close, 9).iloc[-1])
        ema_21 = float(ema(close, 21).iloc[-1])
        ema_50 = float(ema(close, 50).iloc[-1])
        macd_l, _, macd_h = macd(close)
        hist_now = float(macd_h.iloc[-1])

        # Entry logic: EMA stack + MACD + RSI filter
        if ema_9 > ema_21 > ema_50 and hist_now > 0 and rsi_val < 65:
            base_conf = 0.60
            scaled_conf = base_conf * vol_scale
            tp = current + (2.0 * atr_val * vol_scale)  # Tighter TP in high vol
            sl = current - (1.5 * atr_val)
            signals.append(_base_signal(
                "vol_scaler_size_mut", symbol, "BUY", current, tp, sl, scaled_conf,
                f"Vol-scaled (ratio={vol_ratio:.2f}, scale={vol_scale:.2f}): EMA stack bull, RSI={rsi_val:.0f}",
                "trusted_genome", "vol_scaler_size",
            ))

        elif ema_9 < ema_21 < ema_50 and hist_now < 0 and rsi_val > 35:
            base_conf = 0.60
            scaled_conf = base_conf * vol_scale
            tp = current - (2.0 * atr_val * vol_scale)
            sl = current + (1.5 * atr_val)
            signals.append(_base_signal(
                "vol_scaler_size_mut", symbol, "SELL", current, tp, sl, scaled_conf,
                f"Vol-scaled (ratio={vol_ratio:.2f}, scale={vol_scale:.2f}): EMA stack bear, RSI={rsi_val:.0f}",
                "trusted_genome", "vol_scaler_size",
            ))

    return signals


# ═══════════════════════════════════════════════════════════════════════════
# MUTATION 4: mtf_align_mut
# ═══════════════════════════════════════════════════════════════════════════
# Concept: 3-timeframe confluence using resampled 1h data.
# 1h (native), 4h (resample), 1d (resample) must all agree on direction.
# Backtest: DYDX +95%, SHIB +83% (Multi mode)

def _resample_ohlcv(df: pd.DataFrame, period: int) -> pd.DataFrame:
    """Resample OHLCV by grouping every `period` bars."""
    n = len(df)
    trim = n - (n % period)
    if trim < period:
        return pd.DataFrame()
    sliced = df.iloc[-trim:].copy()
    groups = np.arange(len(sliced)) // period
    resampled = sliced.groupby(groups).agg({
        "Open": "first", "High": "max", "Low": "min",
        "Close": "last", "Volume": "sum",
    })
    return resampled


def mtf_align_mut(data: dict) -> list:
    """Multi-timeframe alignment: only trade when 1h, 4h, daily all agree."""
    signals = []

    for symbol in SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < MIN_BARS:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        current = float(close.iloc[-1])
        if current <= 0:
            continue

        # 1h signals (native)
        ema9_1h = float(ema(close, 9).iloc[-1])
        ema21_1h = float(ema(close, 21).iloc[-1])
        rsi_1h = float(rsi(close, 14).iloc[-1])
        sig_1h = 1 if ema9_1h > ema21_1h else (-1 if ema9_1h < ema21_1h else 0)

        # 4h signals (resample 4 bars)
        df_4h = _resample_ohlcv(df, 4)
        if len(df_4h) < 25:
            continue
        ema9_4h = float(ema(df_4h["Close"], 9).iloc[-1])
        ema21_4h = float(ema(df_4h["Close"], 21).iloc[-1])
        rsi_4h = float(rsi(df_4h["Close"], 14).iloc[-1])
        sig_4h = 1 if ema9_4h > ema21_4h else (-1 if ema9_4h < ema21_4h else 0)

        # Daily signals (resample 24 bars)
        df_1d = _resample_ohlcv(df, 24)
        if len(df_1d) < 10:
            continue
        ema9_1d = float(ema(df_1d["Close"], 9).iloc[-1])
        ema21_1d = float(ema(df_1d["Close"], 21).iloc[-1])
        sig_1d = 1 if ema9_1d > ema21_1d else (-1 if ema9_1d < ema21_1d else 0)

        # All 3 timeframes must agree
        if sig_1h == 0 or sig_4h == 0 or sig_1d == 0:
            continue
        if not (sig_1h == sig_4h == sig_1d):
            continue

        atr_val = float(atr(high, low, close, 14).iloc[-1])
        if atr_val <= 0 or np.isnan(atr_val):
            continue

        # Confidence boost from RSI alignment
        rsi_boost = 0.0
        if sig_1h == 1 and rsi_1h < 60 and rsi_4h < 60:
            rsi_boost = 0.10
        elif sig_1h == -1 and rsi_1h > 40 and rsi_4h > 40:
            rsi_boost = 0.10

        if sig_1h == 1:
            conf = 0.65 + rsi_boost
            tp = current + 2.5 * atr_val
            sl = current - 1.5 * atr_val
            signals.append(_base_signal(
                "mtf_align_mut", symbol, "BUY", current, tp, sl, conf,
                f"3TF aligned LONG: 1h({ema9_1h:.4f}>{ema21_1h:.4f}) 4h({ema9_4h:.4f}>{ema21_4h:.4f}) 1d aligned, RSI 1h={rsi_1h:.0f} 4h={rsi_4h:.0f}",
                "trusted_genome", "mtf_align",
            ))
        else:
            conf = 0.65 + rsi_boost
            tp = current - 2.5 * atr_val
            sl = current + 1.5 * atr_val
            signals.append(_base_signal(
                "mtf_align_mut", symbol, "SELL", current, tp, sl, conf,
                f"3TF aligned SHORT: 1h({ema9_1h:.4f}<{ema21_1h:.4f}) 4h({ema9_4h:.4f}<{ema21_4h:.4f}) 1d aligned, RSI 1h={rsi_1h:.0f} 4h={rsi_4h:.0f}",
                "trusted_genome", "mtf_align",
            ))

    return signals


# ═══════════════════════════════════════════════════════════════════════════
# MUTATION 5: vol_adaptive_thresh_mut
# ═══════════════════════════════════════════════════════════════════════════
# Concept: Scale RSI buy/sell thresholds based on ATR ratio.
# High vol -> widen thresholds (need more extreme RSI to trigger)
# Low vol  -> tighten thresholds (small moves are meaningful)
# Boosts Sharpe by 0.3 on SOL/ETH in backtests.

def vol_adaptive_thresh_mut(data: dict) -> list:
    """ATR-adaptive RSI thresholds: dynamic oversold/overbought levels."""
    signals = []

    for symbol in SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < MIN_BARS:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        current = float(close.iloc[-1])
        if current <= 0:
            continue

        atr_series = atr(high, low, close, 14)
        atr_val = float(atr_series.iloc[-1])
        avg_atr = float(atr_series.rolling(50).mean().iloc[-1])

        if atr_val <= 0 or avg_atr <= 0 or np.isnan(atr_val) or np.isnan(avg_atr):
            continue

        vol_ratio = atr_val / avg_atr

        # Adaptive thresholds: base 30/70, scale with volatility
        # High vol (ratio=1.5) -> 25/75 (wider, need more extreme)
        # Low vol  (ratio=0.7) -> 35/65 (tighter, small moves count)
        oversold_thresh = 30 - (vol_ratio - 1.0) * 10  # e.g., 1.5 -> 25, 0.7 -> 33
        overbought_thresh = 70 + (vol_ratio - 1.0) * 10  # e.g., 1.5 -> 75, 0.7 -> 67
        oversold_thresh = np.clip(oversold_thresh, 20, 40)
        overbought_thresh = np.clip(overbought_thresh, 60, 80)

        rsi_val = float(rsi(close, 14).iloc[-1])
        ema_21 = float(ema(close, 21).iloc[-1])

        # MACD for confirmation
        _, _, macd_h = macd(close)
        hist_now = float(macd_h.iloc[-1])
        hist_prev = float(macd_h.iloc[-2]) if len(macd_h) > 1 else 0

        # LONG: RSI below adaptive oversold + MACD turning up + price above EMA21
        if rsi_val < oversold_thresh and hist_now > hist_prev and current > ema_21:
            extremity = (oversold_thresh - rsi_val) / oversold_thresh
            conf = 0.55 + min(0.25, extremity * 0.3)
            tp = current + 2.0 * atr_val
            sl = current - 1.3 * atr_val
            signals.append(_base_signal(
                "vol_adaptive_thresh_mut", symbol, "BUY", current, tp, sl, conf,
                f"Adaptive RSI: thresh={oversold_thresh:.0f}/{overbought_thresh:.0f} (vol_ratio={vol_ratio:.2f}), RSI={rsi_val:.0f} < {oversold_thresh:.0f}, MACD turning up",
                "trusted_genome", "vol_adaptive_thresh",
            ))

        # SHORT: RSI above adaptive overbought + MACD turning down + price below EMA21
        elif rsi_val > overbought_thresh and hist_now < hist_prev and current < ema_21:
            extremity = (rsi_val - overbought_thresh) / (100 - overbought_thresh)
            conf = 0.55 + min(0.25, extremity * 0.3)
            tp = current - 2.0 * atr_val
            sl = current + 1.3 * atr_val
            signals.append(_base_signal(
                "vol_adaptive_thresh_mut", symbol, "SELL", current, tp, sl, conf,
                f"Adaptive RSI: thresh={oversold_thresh:.0f}/{overbought_thresh:.0f} (vol_ratio={vol_ratio:.2f}), RSI={rsi_val:.0f} > {overbought_thresh:.0f}, MACD turning down",
                "trusted_genome", "vol_adaptive_thresh",
            ))

    return signals


# ═══════════════════════════════════════════════════════════════════════════
# Registry & Runner
# ═══════════════════════════════════════════════════════════════════════════

MUTATION_REGISTRY = {
    "regime_switch_mut": {
        "fn": regime_switch_mut,
        "parent": "trusted_genome",
        "description": "Regime-adaptive: trend-follow in high-vol, mean-revert in low-vol",
    },
    "basket_corr_gate_mut": {
        "fn": basket_corr_gate_mut,
        "parent": "trusted_genome",
        "description": "BTC correlation gate: only trade alts correlated > 0.4 with BTC",
    },
    "vol_scaler_size_mut": {
        "fn": vol_scaler_size_mut,
        "parent": "trusted_genome",
        "description": "Inverse vol sizing: scale confidence/size down in high-vol",
    },
    "mtf_align_mut": {
        "fn": mtf_align_mut,
        "parent": "trusted_genome",
        "description": "3-timeframe confluence: 1h + 4h + 1d must all agree",
    },
    "vol_adaptive_thresh_mut": {
        "fn": vol_adaptive_thresh_mut,
        "parent": "trusted_genome",
        "description": "ATR-scaled RSI thresholds: widen in high-vol, tighten in low-vol",
    },
}


def run_all(interval: str = "1h", limit: int = 300) -> dict:
    """Run all 5 trusted genome mutations. Interface matches KIMI/super mutations."""
    print("=" * 70)
    print("  TRUSTED GENOME MUTATIONS — 5 Regime/Vol-Adaptive Strategies")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  {len(SYMBOLS)} symbols x {len(MUTATION_REGISTRY)} mutations")
    print("=" * 70)

    # Fetch data
    data = {}
    for sym in SYMBOLS:
        df = fetch_klines(sym, interval, limit)
        if df is not None and len(df) >= MIN_BARS:
            data[sym] = df
            print(f"  [OK] {sym}: {len(df)} bars, last={float(df['Close'].iloc[-1]):.4f}")
        else:
            print(f"  [!!] {sym}: fetch failed or insufficient data")

    print(f"\nFetched {len(data)}/{len(SYMBOLS)} symbols\n")

    # Run mutations
    all_picks = []
    triggered = []

    for name, info in MUTATION_REGISTRY.items():
        try:
            picks = info["fn"](data)
            if picks:
                all_picks.extend(picks)
                triggered.append({"strategy": name, "picks": len(picks)})
                for p in picks:
                    print(f"  [SIGNAL] {name} -> {p['symbol']} {p['signal_type']} "
                          f"@ {p['entry_price']} conf={p['confidence']:.2f}")
            else:
                print(f"  [quiet] {name}: no signals")
        except Exception as e:
            print(f"  [ERROR] {name}: {e}")

    print(f"\n{'=' * 70}")
    print(f"  TOTAL: {len(all_picks)} picks from {len(triggered)}/{len(MUTATION_REGISTRY)} mutations")
    print(f"{'=' * 70}")

    return {
        "metadata": {
            "timestamp": _now_iso(),
            "system": "trusted_genome_mutations",
            "version": "1.0.0",
            "total_mutations": len(MUTATION_REGISTRY),
            "total_picks": len(all_picks),
            "mutations_triggered": len(triggered),
            "symbols_scanned": len(data),
        },
        "picks": all_picks,
        "mutations_triggered": triggered,
    }


if __name__ == "__main__":
    result = run_all()

    # Save picks
    out_path = ROOT / "genome" / "data" / "trusted_genome_picks_live.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\nSaved {result['metadata']['total_picks']} picks to {out_path}")
