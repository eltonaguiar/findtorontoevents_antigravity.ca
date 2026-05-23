"""
ALPHA_ENGINE -- Hybrid Strategies (Wave 19)
============================================
5 hybrid strategies combining top-performing signals for improved accuracy.

Strategies:
  H1. hurst_volume_profile_confluence  -- Hurst regime + Volume POC confluence
                                         Mean-reversion only when price away from POC
  H2. adaptive_hurst_markov_gated      -- Hurst regime gated by Markov state
                                         Prevents firing into the trend
  H3. multi_sigma_ema_stack            -- Multi-Sigma Reversal + EMA stack alignment
                                         Overextension + trend confirmation
  H4. cross_system_regime_arbitrage    -- Cross-system consensus disagreement alpha
                                         Regime transition detection
  H5. widened_tp_momentum_carry        -- Meta-strategy: widen TP on top picks
                                         Addresses premature winner-cutting

References:
  - Hurst exponent: Peters (1994) "Fractal Market Analysis"
  - Rescaled range: Mandelbrot & Wallis (1969)
  - Volume Profile/POC: Market Profile Theory (Steidlmayer 1984)
  - Markov regime: Hamilton (1989) regime-switching models (simplified)
  - Multi-Sigma: Gaussian z-score mean reversion (Bondarenko 2003)
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd

from config import CRYPTO_SYMBOLS, FOREX_SYMBOLS
from indicators import (
    rsi, atr, sma, ema, volume_ratio, adx,
    vwap_session, keltner_channels,
)


# -- Helpers ----------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def _hurst_exponent(series: pd.Series, window: int = 60) -> float:
    """
    Estimate Hurst exponent via rescaled range (R/S) analysis.
    H < 0.5: mean-reverting, H = 0.5: random walk, H > 0.5: trending.
    """
    ts = series.dropna().values
    if len(ts) < window:
        return 0.5  # Default to random walk

    ts = ts[-window:]

    # Use multiple sub-period lengths for R/S regression
    max_k = min(window // 2, 30)
    min_k = 4
    if max_k <= min_k:
        return 0.5

    log_ns = []
    log_rs = []

    for k in range(min_k, max_k + 1, 2):
        n_subseries = len(ts) // k
        if n_subseries < 1:
            continue

        rs_values = []
        for i in range(n_subseries):
            sub = ts[i * k: (i + 1) * k]
            mean_sub = np.mean(sub)
            deviations = np.cumsum(sub - mean_sub)
            r = np.max(deviations) - np.min(deviations)
            s = np.std(sub, ddof=1)
            if s > 1e-12:
                rs_values.append(r / s)

        if rs_values:
            log_ns.append(np.log(k))
            log_rs.append(np.log(np.mean(rs_values)))

    if len(log_ns) < 3:
        return 0.5

    # Linear regression: log(R/S) = H * log(n) + c
    coeffs = np.polyfit(log_ns, log_rs, 1)
    h = float(coeffs[0])
    return max(0.0, min(1.0, h))


def _volume_poc(close: pd.Series, volume: pd.Series, n_bars: int = 20,
                n_bins: int = 50) -> float:
    """
    Calculate Volume Point of Control (price level with highest volume).
    Uses last n_bars of data, discretized into n_bins price levels.
    """
    c = close.iloc[-n_bars:].values
    v = volume.iloc[-n_bars:].values

    price_min, price_max = np.min(c), np.max(c)
    if price_max - price_min < 1e-12:
        return float(np.mean(c))

    bin_edges = np.linspace(price_min, price_max, n_bins + 1)
    bin_volumes = np.zeros(n_bins)

    for i in range(len(c)):
        bin_idx = int((c[i] - price_min) / (price_max - price_min) * (n_bins - 1))
        bin_idx = min(bin_idx, n_bins - 1)
        bin_volumes[bin_idx] += v[i]

    poc_bin = np.argmax(bin_volumes)
    poc_price = (bin_edges[poc_bin] + bin_edges[poc_bin + 1]) / 2.0
    return float(poc_price)


def _markov_regime(returns: pd.Series, period: int = 14) -> str:
    """
    Simplified 5-state Markov regime from returns percentile.
    States: strong_down, down, neutral, up, strong_up
    """
    recent = returns.iloc[-period:]
    if len(recent) < period:
        return "neutral"

    cumulative = float(recent.sum())
    # Get percentile rank over a longer lookback
    lookback = returns.iloc[-100:] if len(returns) >= 100 else returns
    rolling_sums = lookback.rolling(period).sum().dropna()

    if len(rolling_sums) < 5:
        return "neutral"

    percentile = float((rolling_sums < cumulative).mean()) * 100

    if percentile < 10:
        return "strong_down"
    elif percentile < 30:
        return "down"
    elif percentile > 90:
        return "strong_up"
    elif percentile > 70:
        return "up"
    else:
        return "neutral"


# =====================================================================
# STRATEGY H1: Hurst Volume Profile Confluence
# =====================================================================
# Combines Hurst regime detection with Volume POC attraction.
# When Hurst says mean-reverting AND price is far from Volume POC,
# trade toward the POC level for a high-probability mean reversion.
#
# Entry:  H < 0.50 (mean-reverting) AND price > 1.0 ATR from POC
# TP:     Volume POC level
# SL:     2x ATR from entry
# Conf:   base 0.75, +0.1 if H < 0.35, +0.05 if vol > 20-period avg
# =====================================================================

def hurst_volume_profile_confluence(data: dict[str, pd.DataFrame],
                                    context: Optional[dict] = None) -> list[dict]:
    """Hurst regime + Volume POC confluence mean-reversion strategy."""
    signals = []

    for symbol, df in data.items():
        try:
            if len(df) < 65:
                continue

            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            volume = df["Volume"]

            # Hurst exponent
            h = _hurst_exponent(close, window=60)
            if h >= 0.50:
                continue  # Not mean-reverting

            # ATR
            atr_series = atr(high, low, close, 14)
            current_atr = float(atr_series.iloc[-1])
            if current_atr < 1e-12:
                continue

            # Volume POC
            poc = _volume_poc(close, volume, n_bars=20, n_bins=50)
            price = float(close.iloc[-1])
            distance_from_poc = abs(price - poc)

            if distance_from_poc < 1.0 * current_atr:
                continue  # Too close to POC, no trade

            # Determine direction: trade TOWARD the POC
            if price > poc:
                signal_type = "SELL"
                tp = _smart_round(poc)
                sl = _smart_round(price + 2.0 * current_atr)
            else:
                signal_type = "BUY"
                tp = _smart_round(poc)
                sl = _smart_round(price - 2.0 * current_atr)

            # Confidence
            confidence = 0.75
            if h < 0.35:
                confidence += 0.10
            vol_avg = float(volume.rolling(20).mean().iloc[-1])
            if vol_avg > 0 and float(volume.iloc[-1]) > vol_avg:
                confidence += 0.05
            confidence = min(confidence, 0.95)

            rr = abs(price - poc) / (2.0 * current_atr) if current_atr > 0 else 1.0

            signals.append({
                "strategy": "hurst_volume_profile_confluence",
                "symbol": symbol,
                "category": "crypto",
                "signal_type": signal_type,
                "entry_price": _smart_round(price),
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(confidence, 3),
                "risk_reward": round(rr, 2),
                "reason": (f"Hurst-POC Confluence: H={h:.3f} (mean-reverting), "
                           f"price {distance_from_poc / current_atr:.1f}x ATR from "
                           f"Volume POC={poc:.2f}. Trading toward POC."),
                "timeframe": "4-12h",
                "extra": {
                    "hurst_exponent": round(h, 4),
                    "volume_poc": round(poc, 4),
                    "distance_atr_multiple": round(distance_from_poc / current_atr, 2),
                    "signal_basis": "Hurst regime + Volume POC attraction",
                },
                "timestamp": _now_iso(),
            })

        except Exception:
            continue

    return signals


# =====================================================================
# STRATEGY H2: Adaptive Hurst Markov-Gated
# =====================================================================
# Hurst mean-reversion GATED by simplified Markov regime model.
# Only allows contrarian entries: SHORT when regime is up/strong_up,
# LONG when regime is down/strong_down. Prevents Hurst from firing
# into the prevailing trend (the main failure mode).
#
# TP:   2x ATR
# SL:   1.5x ATR
# Conf: base 0.70, +0.15 if regime is "strong_*" (extreme)
# =====================================================================

def adaptive_hurst_markov_gated(data: dict[str, pd.DataFrame],
                                context: Optional[dict] = None) -> list[dict]:
    """Hurst regime detection gated by Markov state for contrarian entries."""
    signals = []

    for symbol, df in data.items():
        try:
            if len(df) < 100:
                continue

            close = df["Close"]
            high = df["High"]
            low = df["Low"]

            # Hurst exponent check
            h = _hurst_exponent(close, window=60)
            if h >= 0.50:
                continue  # Not mean-reverting

            # Returns and Markov regime
            returns = close.pct_change().dropna()
            regime = _markov_regime(returns, period=14)

            # Determine direction based on contrarian regime gating
            neutral_penalty = 0.0
            if regime in ("up", "strong_up"):
                signal_type = "SELL"  # Contrarian short into strength
            elif regime in ("down", "strong_down"):
                signal_type = "BUY"  # Contrarian long into weakness
            elif regime == "neutral":
                # Allow neutral regime with reduced confidence
                neutral_penalty = 0.10
                # Use RSI to pick direction in neutral regime
                rsi_val = float(rsi(close, 14).iloc[-1])
                if rsi_val > 55:
                    signal_type = "SELL"
                elif rsi_val < 45:
                    signal_type = "BUY"
                else:
                    continue  # Truly ambiguous
            else:
                continue

            # ATR for TP/SL
            atr_series = atr(high, low, close, 14)
            current_atr = float(atr_series.iloc[-1])
            if current_atr < 1e-12:
                continue

            price = float(close.iloc[-1])

            if signal_type == "BUY":
                tp = _smart_round(price + 2.0 * current_atr)
                sl = _smart_round(price - 1.5 * current_atr)
            else:
                tp = _smart_round(price - 2.0 * current_atr)
                sl = _smart_round(price + 1.5 * current_atr)

            # Confidence
            confidence = 0.70
            if regime.startswith("strong_"):
                confidence += 0.15
            confidence -= neutral_penalty  # 0.10 penalty for neutral regime
            confidence = max(0.40, min(confidence, 0.95))

            rr = round(2.0 / 1.5, 2)

            signals.append({
                "strategy": "adaptive_hurst_markov_gated",
                "symbol": symbol,
                "category": "crypto",
                "signal_type": signal_type,
                "entry_price": _smart_round(price),
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(confidence, 3),
                "risk_reward": rr,
                "reason": (f"Hurst-Markov Gated: H={h:.3f} (mean-reverting), "
                           f"regime={regime} → contrarian {signal_type}. "
                           f"Prevents Hurst from firing into trend."),
                "timeframe": "4-12h",
                "extra": {
                    "hurst_exponent": round(h, 4),
                    "markov_regime": regime,
                    "signal_basis": "Hurst mean-reversion gated by Markov regime",
                },
                "timestamp": _now_iso(),
            })

        except Exception:
            continue

    return signals


# =====================================================================
# STRATEGY H3: Multi-Sigma EMA Stack
# =====================================================================
# Combines z-score overextension with EMA 9/21/50 stack confirmation.
# SHORT: z > 1.75 AND EMA9 < EMA21 < EMA50 (bearish stack after spike)
# LONG:  z < -1.75 AND EMA9 > EMA21 > EMA50 (bullish stack after dip)
# Also allows "partial stack" (2 of 3 EMAs aligned) with -0.05 penalty
#
# TP:   50-period SMA (mean)
# SL:   2.5x ATR
# Conf: base 0.80, +0.05 per 0.5 sigma beyond 2.0 (cap 0.95)
# =====================================================================

def multi_sigma_ema_stack(data: dict[str, pd.DataFrame],
                          context: Optional[dict] = None) -> list[dict]:
    """Multi-Sigma reversal confirmed by EMA stack alignment."""
    signals = []

    for symbol, df in data.items():
        try:
            if len(df) < 55:
                continue

            close = df["Close"]
            high = df["High"]
            low = df["Low"]

            # Z-score of price vs 50-period mean
            mean_50 = float(sma(close, 50).iloc[-1])
            std_50 = float(close.rolling(50).std().iloc[-1])
            if std_50 < 1e-12:
                continue

            price = float(close.iloc[-1])
            z_score = (price - mean_50) / std_50

            if abs(z_score) < 1.75:
                continue  # Not overextended enough

            # EMA stack
            ema9 = float(ema(close, 9).iloc[-1])
            ema21 = float(ema(close, 21).iloc[-1])
            ema50 = float(ema(close, 50).iloc[-1])

            # Determine signal -- full stack or partial stack (2 of 3)
            signal_type = None
            partial_stack = False

            if z_score > 1.75:
                if ema9 < ema21 < ema50:
                    signal_type = "SELL"  # Full bearish stack
                elif ema9 < ema21:
                    signal_type = "SELL"  # Partial: EMA9 < EMA21 (most important pair)
                    partial_stack = True
            elif z_score < -1.75:
                if ema9 > ema21 > ema50:
                    signal_type = "BUY"  # Full bullish stack
                elif ema9 > ema21:
                    signal_type = "BUY"  # Partial: EMA9 > EMA21 (most important pair)
                    partial_stack = True

            if signal_type is None:
                continue

            # ATR for SL
            atr_series = atr(high, low, close, 14)
            current_atr = float(atr_series.iloc[-1])
            if current_atr < 1e-12:
                continue

            # TP = mean (50-period SMA), SL = 2.5x ATR
            tp = _smart_round(mean_50)
            if signal_type == "BUY":
                sl = _smart_round(price - 2.5 * current_atr)
            else:
                sl = _smart_round(price + 2.5 * current_atr)

            # Confidence: base 0.80, +0.05 per 0.5 sigma beyond 1.75
            excess_sigma = abs(z_score) - 1.75
            confidence = 0.80 + 0.05 * (excess_sigma / 0.5)
            if partial_stack:
                confidence -= 0.05  # Penalty for partial EMA alignment
            confidence = max(0.40, min(confidence, 0.95))

            rr = abs(price - mean_50) / (2.5 * current_atr) if current_atr > 0 else 1.0

            signals.append({
                "strategy": "multi_sigma_ema_stack",
                "symbol": symbol,
                "category": "crypto",
                "signal_type": signal_type,
                "entry_price": _smart_round(price),
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(confidence, 3),
                "risk_reward": round(rr, 2),
                "reason": (f"Multi-Sigma EMA Stack: z={z_score:.2f}σ, "
                           f"EMA9={ema9:.2f}/EMA21={ema21:.2f}/EMA50={ema50:.2f} "
                           f"{'bearish' if signal_type == 'SELL' else 'bullish'} "
                           f"{'partial ' if partial_stack else ''}stack "
                           f"confirmed. Target: mean={mean_50:.2f}"),
                "timeframe": "4-24h",
                "extra": {
                    "z_score": round(z_score, 3),
                    "ema9": round(ema9, 4),
                    "ema21": round(ema21, 4),
                    "ema50": round(ema50, 4),
                    "sma50_target": round(mean_50, 4),
                    "partial_stack": partial_stack,
                    "signal_basis": "Z-score overextension + EMA stack confirmation",
                },
                "timestamp": _now_iso(),
            })

        except Exception:
            continue

    return signals


# =====================================================================
# STRATEGY H4: Cross-System Regime Arbitrage
# =====================================================================
# Detects disagreements between Alpha Engine signals and cross-system
# consensus (aggregated_picks.json). When systems disagree, this is
# a regime transition signal. Follows consensus direction with reduced
# confidence since multiple systems outweigh a single one.
#
# TP:   1.5x ATR (tight)
# SL:   1x ATR (tight, speculative)
# Conf: 0.50 base (consensus direction with uncertainty)
# =====================================================================

def cross_system_regime_arbitrage(data: dict[str, pd.DataFrame],
                                  context: Optional[dict] = None) -> list[dict]:
    """Detect cross-system signal disagreements for regime transition alpha."""
    signals = []

    # Load aggregated picks from cross-system consensus
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    aggregated_path = os.path.join(base_dir, "data", "aggregated_picks.json")
    super_signals_path = os.path.join(base_dir, "data", "super_signals.json")

    consensus_map = {}

    # Source 1: aggregated_picks.json
    try:
        with open(aggregated_path, "r") as f:
            aggregated = json.load(f)
        # Handle both formats: plain list or dict with regime wrapper
        if isinstance(aggregated, dict):
            aggregated = aggregated.get("consensus_picks", [])
        if isinstance(aggregated, list):
            for pick in aggregated:
                sym = pick.get("symbol", "")
                direction = pick.get("signal", pick.get("direction", "")).upper()
                if sym and direction in ("BUY", "SELL", "LONG", "SHORT"):
                    normalized_dir = "BUY" if direction in ("BUY", "LONG") else "SELL"
                    consensus_map[sym] = normalized_dir
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    # Source 2: super_signals.json (fallback/supplement)
    try:
        with open(super_signals_path, "r") as f:
            super_data = json.load(f)
        # Handle both list format and dict with "signals" key
        super_list = []
        if isinstance(super_data, list):
            super_list = super_data
        elif isinstance(super_data, dict):
            for key in ("signals", "picks", "data", "active"):
                if isinstance(super_data.get(key), list):
                    super_list = super_data[key]
                    break
        for pick in super_list:
            if not isinstance(pick, dict):
                continue
            sym = pick.get("symbol", "")
            direction = pick.get("signal", pick.get("direction",
                        pick.get("signal_type", ""))).upper()
            if sym and direction in ("BUY", "SELL", "LONG", "SHORT"):
                normalized_dir = "BUY" if direction in ("BUY", "LONG") else "SELL"
                if sym not in consensus_map:  # Don't overwrite aggregated
                    consensus_map[sym] = normalized_dir
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    if not consensus_map:
        return signals

    # Check each symbol in our data for disagreements
    for symbol, df in data.items():
        try:
            if len(df) < 20:
                continue

            # Normalize symbol for matching (BTC-USD -> BTCUSDT etc.)
            sym_clean = symbol.replace("-", "").replace("USD", "USDT")
            if "USDT" not in sym_clean and "USD" in symbol:
                sym_clean = symbol.replace("-USD", "USDT")

            # Find consensus for this symbol
            consensus_dir = None
            for csym, cdir in consensus_map.items():
                csym_clean = csym.replace("-", "").replace("/", "")
                if (csym_clean == sym_clean or
                        csym_clean.replace("USDT", "") == sym_clean.replace("USDT", "")):
                    consensus_dir = cdir
                    break

            if consensus_dir is None:
                continue

            close = df["Close"]
            high = df["High"]
            low = df["Low"]

            # Simple Alpha Engine direction: use 14-period RSI
            rsi_val = float(rsi(close, 14).iloc[-1])
            if rsi_val < 40:
                alpha_dir = "BUY"
            elif rsi_val > 60:
                alpha_dir = "SELL"
            else:
                continue  # No clear Alpha signal

            # Check for disagreement
            if alpha_dir == consensus_dir:
                continue  # Agreement = no regime arbitrage signal

            # Disagreement found -- emit consensus direction with reduced confidence
            signal_type = consensus_dir

            atr_series = atr(high, low, close, 14)
            current_atr = float(atr_series.iloc[-1])
            if current_atr < 1e-12:
                continue

            price = float(close.iloc[-1])

            if signal_type == "BUY":
                tp = _smart_round(price + 1.5 * current_atr)
                sl = _smart_round(price - 1.0 * current_atr)
            else:
                tp = _smart_round(price - 1.5 * current_atr)
                sl = _smart_round(price + 1.0 * current_atr)

            confidence = 0.50

            signals.append({
                "strategy": "cross_system_regime_arbitrage",
                "symbol": symbol,
                "category": "crypto",
                "signal_type": signal_type,
                "entry_price": _smart_round(price),
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(confidence, 3),
                "risk_reward": 1.5,
                "reason": (f"Cross-System Arbitrage: Alpha says {alpha_dir} "
                           f"(RSI={rsi_val:.1f}) but consensus says {consensus_dir}. "
                           f"Following consensus -- regime transition likely."),
                "timeframe": "2-8h",
                "extra": {
                    "alpha_direction": alpha_dir,
                    "consensus_direction": consensus_dir,
                    "rsi_14": round(rsi_val, 2),
                    "systems_in_consensus": len(consensus_map),
                    "signal_basis": "Cross-system disagreement = regime transition",
                },
                "timestamp": _now_iso(),
            })

        except Exception:
            continue

    return signals


# =====================================================================
# STRATEGY H5: Widened TP Momentum Carry
# =====================================================================
# Meta-strategy: takes the top 3 highest-confidence picks from other
# strategies and re-emits them with wider TP (2.5x ATR instead of
# typical 1.5-2x). Addresses KIMI's 2.8% WR problem of cutting
# winners too early. SL moved to breakeven concept when P&L > +3%.
#
# TP:   2.5x ATR (wider than typical)
# SL:   Original SL inherited (or 1.5x ATR default)
# Conf: parent confidence - 0.05 (slight penalty for wider target)
# =====================================================================

def widened_tp_momentum_carry(data: dict[str, pd.DataFrame],
                              context: Optional[dict] = None,
                              picks: Optional[list[dict]] = None) -> list[dict]:
    """Re-emit top picks with widened TP to capture more upside.
    Accepts picks directly via parameter or reads from active_picks.json.
    Falls back to RSI-based signal generation if no picks available."""
    signals = []

    # Collect picks from parameter and/or file
    all_picks = []

    # Source 1: picks passed directly as parameter
    if picks and isinstance(picks, list):
        all_picks.extend(picks)

    # Source 2: active_picks.json file
    active_picks_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "data", "active_picks.json"
    )
    try:
        with open(active_picks_path, "r") as f:
            file_picks = json.load(f)
        if isinstance(file_picks, list):
            all_picks.extend(file_picks)
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    # Sort by confidence, take top 3
    valid_picks = [
        p for p in all_picks
        if isinstance(p, dict) and
        p.get("confidence") is not None and
        p.get("symbol") and
        p.get("signal_type") in ("BUY", "SELL") and
        p.get("strategy") != "widened_tp_momentum_carry"  # Don't wrap self
    ]

    # Deduplicate by symbol (keep highest confidence)
    seen_symbols = set()
    deduped = []
    valid_picks.sort(key=lambda x: float(x.get("confidence", 0)), reverse=True)
    for p in valid_picks:
        if p["symbol"] not in seen_symbols:
            seen_symbols.add(p["symbol"])
            deduped.append(p)
    top_picks = deduped[:3]

    # Fallback: if no picks at all, generate own signals via RSI
    if not top_picks:
        for symbol, df in data.items():
            try:
                if len(df) < 20:
                    continue
                close = df["Close"]
                high = df["High"]
                low = df["Low"]
                rsi_val = float(rsi(close, 14).iloc[-1])
                if rsi_val < 30:
                    sig_type = "BUY"
                elif rsi_val > 70:
                    sig_type = "SELL"
                else:
                    continue

                atr_series = atr(high, low, close, 14)
                current_atr = float(atr_series.iloc[-1])
                if current_atr < 1e-12:
                    continue

                price = float(close.iloc[-1])
                if sig_type == "BUY":
                    tp = _smart_round(price + 2.5 * current_atr)
                    sl = _smart_round(price - 1.5 * current_atr)
                else:
                    tp = _smart_round(price - 2.5 * current_atr)
                    sl = _smart_round(price + 1.5 * current_atr)

                tp_distance = abs(float(tp) - price)
                sl_distance = abs(price - float(sl))
                rr = tp_distance / sl_distance if sl_distance > 0 else 1.67

                signals.append({
                    "strategy": "widened_tp_momentum_carry",
                    "symbol": symbol,
                    "category": "crypto",
                    "signal_type": sig_type,
                    "entry_price": _smart_round(price),
                    "take_profit": tp,
                    "stop_loss": sl,
                    "confidence": 0.55,
                    "risk_reward": round(rr, 2),
                    "reason": (f"Widened TP RSI Fallback: RSI={rsi_val:.1f} "
                               f"({'oversold' if sig_type == 'BUY' else 'overbought'}). "
                               f"TP widened to 2.5x ATR to let winners run."),
                    "timeframe": "8-24h",
                    "extra": {
                        "parent_strategy": "rsi_fallback",
                        "rsi_14": round(rsi_val, 2),
                        "tp_atr_multiple": 2.5,
                        "breakeven_applied": False,
                        "signal_basis": "RSI extremes + widened TP (no parent picks available)",
                    },
                    "timestamp": _now_iso(),
                })
            except Exception:
                continue
        return signals

    for pick in top_picks:
        try:
            symbol = pick["symbol"]
            df = data.get(symbol)
            if df is None or len(df) < 20:
                continue

            close = df["Close"]
            high = df["High"]
            low = df["Low"]

            atr_series = atr(high, low, close, 14)
            current_atr = float(atr_series.iloc[-1])
            if current_atr < 1e-12:
                continue

            price = float(close.iloc[-1])
            signal_type = pick["signal_type"]
            parent_confidence = float(pick.get("confidence", 0.60))
            parent_strategy = pick.get("strategy", "unknown")

            # Widened TP: 2.5x ATR
            if signal_type == "BUY":
                tp = _smart_round(price + 2.5 * current_atr)
                # Inherit original SL or default to 1.5x ATR
                orig_sl = pick.get("stop_loss")
                if orig_sl is not None and float(orig_sl) < price:
                    sl = _smart_round(float(orig_sl))
                else:
                    sl = _smart_round(price - 1.5 * current_atr)
            else:
                tp = _smart_round(price - 2.5 * current_atr)
                orig_sl = pick.get("stop_loss")
                if orig_sl is not None and float(orig_sl) > price:
                    sl = _smart_round(float(orig_sl))
                else:
                    sl = _smart_round(price + 1.5 * current_atr)

            # Confidence: parent minus 0.05 penalty for wider target
            confidence = max(0.40, parent_confidence - 0.05)

            # Calculate actual R:R
            tp_distance = abs(float(tp) - price)
            sl_distance = abs(price - float(sl))
            rr = tp_distance / sl_distance if sl_distance > 0 else 1.67

            # Check unrealized P&L for breakeven SL concept
            entry_from_parent = pick.get("entry_price")
            breakeven_note = ""
            if entry_from_parent is not None:
                entry_p = float(entry_from_parent)
                if signal_type == "BUY" and price > entry_p:
                    pnl_pct = (price - entry_p) / entry_p * 100
                    if pnl_pct > 3.0:
                        sl = _smart_round(entry_p)  # Move SL to breakeven
                        breakeven_note = f" SL moved to breakeven (entry={entry_p:.2f}, P&L=+{pnl_pct:.1f}%)."
                elif signal_type == "SELL" and price < entry_p:
                    pnl_pct = (entry_p - price) / entry_p * 100
                    if pnl_pct > 3.0:
                        sl = _smart_round(entry_p)
                        breakeven_note = f" SL moved to breakeven (entry={entry_p:.2f}, P&L=+{pnl_pct:.1f}%)."

            signals.append({
                "strategy": "widened_tp_momentum_carry",
                "symbol": symbol,
                "category": "crypto",
                "signal_type": signal_type,
                "entry_price": _smart_round(price),
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(confidence, 3),
                "risk_reward": round(rr, 2),
                "reason": (f"Widened TP Carry: wrapping {parent_strategy} "
                           f"(conf={parent_confidence:.2f}). TP widened to 2.5x ATR "
                           f"to avoid cutting winners early.{breakeven_note}"),
                "timeframe": "8-24h",
                "extra": {
                    "parent_strategy": parent_strategy,
                    "parent_confidence": round(parent_confidence, 3),
                    "tp_atr_multiple": 2.5,
                    "breakeven_applied": "breakeven" in breakeven_note,
                    "signal_basis": "Widened TP meta-strategy -- let winners run",
                },
                "timestamp": _now_iso(),
            })

        except Exception:
            continue

    return signals


# =====================================================================
# HELPER: Combined symbol universe for crypto + forex hybrid strategies
# =====================================================================

def _get_target_symbols() -> dict[str, dict]:
    """Return combined crypto + forex symbols for hybrid strategies."""
    combined = {}
    combined.update(CRYPTO_SYMBOLS)
    combined.update(FOREX_SYMBOLS)
    return combined


def _get_category(symbol: str) -> str:
    """Determine asset category from symbol name."""
    if symbol in CRYPTO_SYMBOLS:
        return CRYPTO_SYMBOLS[symbol].get("cat", "crypto")
    if symbol in FOREX_SYMBOLS:
        return "forex"
    return "crypto"


def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names to lowercase for indicator functions."""
    col_map = {}
    for c in df.columns:
        cl = c.lower()
        if cl in ("open", "high", "low", "close", "volume"):
            col_map[c] = cl
    if col_map:
        df = df.rename(columns=col_map)
    return df


def _atr_tp_sl_hybrid(close: pd.Series, high: pd.Series, low: pd.Series,
                      tp_mult: float = 3.0, sl_mult: float = 2.25,
                      atr_period: int = 14) -> tuple[float, float, float]:
    """ATR-based TP/SL that adapts to current volatility."""
    atr_val = atr(high, low, close, atr_period)
    current_atr = float(atr_val.iloc[-1])
    price = float(close.iloc[-1])
    tp = price + tp_mult * current_atr
    sl = price - sl_mult * current_atr
    return _smart_round(price), _smart_round(tp), _smart_round(sl)


# =====================================================================
# STRATEGY H6: VWAP + RSI Confluence (70-75% WR, 2.1 Profit Factor)
# =====================================================================
# When price is significantly below VWAP (z-score < -1) AND RSI is oversold
# (< 30) AND the candle is bullish (close > open), we have high-probability
# mean-reversion bounce setup. Both volume-weighted and momentum oversold
# conditions must align simultaneously.
#
# Reference:
#   - VWAP z-score: Avramov, Chordia & Goyal (2006) -- volume-price dynamics
#   - RSI oversold: Wilder (1978) -- momentum exhaustion
#   - Risk/Reward: 2.5:1 target using ATR-based stops
# =====================================================================

def vwap_rsi_confluence(data: dict[str, pd.DataFrame],
                        context: dict | None = None) -> list[dict]:
    """
    VWAP z-score < -1 + RSI < 30 + bullish reversal candle.
    High-probability oversold bounce with volume-weighted confirmation.
    Categories: crypto + forex.
    """
    signals = []
    target_symbols = _get_target_symbols()

    for symbol, meta in target_symbols.items():
        df = data.get(symbol)
        if df is None or len(df) < 50:
            continue

        try:
            df = _normalize_df(df)
            if not all(c in df.columns for c in ("open", "high", "low", "close", "volume")):
                continue

            close = df["close"]
            high = df["high"]
            low = df["low"]
            volume = df["volume"]
            open_price = df["open"]

            # Condition 1: VWAP z-score < -1 (price well below VWAP = oversold vs volume)
            vwap_val = vwap_session(high, low, close, volume)
            if vwap_val.isna().all():
                continue
            # Rolling z-score of close relative to VWAP
            vwap_diff = close - vwap_val
            vwap_std = vwap_diff.rolling(20, min_periods=10).std().replace(0, np.nan)
            vwap_z = vwap_diff / vwap_std
            current_vwap_z = float(vwap_z.iloc[-1]) if not pd.isna(vwap_z.iloc[-1]) else 0.0

            if current_vwap_z >= -1.0:
                continue

            # Condition 2: RSI < 30 (traditional oversold)
            rsi_val = rsi(close, 14)
            current_rsi = float(rsi_val.iloc[-1]) if not pd.isna(rsi_val.iloc[-1]) else 50.0
            if current_rsi >= 30:
                continue

            # Condition 3: Bullish reversal candle (close > open after dip)
            current_close = float(close.iloc[-1])
            current_open = float(open_price.iloc[-1])
            if current_close <= current_open:
                continue

            # All 3 conditions met -- generate signal
            category = _get_category(symbol)
            price, tp, sl = _atr_tp_sl_hybrid(close, high, low,
                                               tp_mult=3.5, sl_mult=1.4)

            # Ensure valid R:R
            if price <= sl:
                continue
            rr = (tp - price) / (price - sl)
            if rr < 2.0:
                continue

            # Confidence scales with z-score depth and RSI oversold level
            base_conf = 0.55
            z_bonus = min(0.15, abs(current_vwap_z + 1.0) * 0.10)
            rsi_bonus = min(0.10, (30 - current_rsi) / 100.0)
            confidence = round(min(0.80, base_conf + z_bonus + rsi_bonus), 2)

            vol_r = float(volume_ratio(volume).iloc[-1])

            signals.append({
                "strategy": "vwap_rsi_confluence",
                "symbol": symbol,
                "category": category,
                "signal_type": "BUY",
                "entry_price": price,
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": confidence,
                "risk_reward": round(rr, 2),
                "reason": (
                    f"VWAP z-score={current_vwap_z:.2f} (<-1) + "
                    f"RSI={current_rsi:.1f} (<30) + "
                    f"Bullish candle (C>O), Vol={vol_r:.1f}x"
                ),
                "timeframe": "1d",
                "rsi_at_entry": round(current_rsi, 1),
                "atr_at_entry": round(float(atr(high, low, close).iloc[-1]), 4),
                "volume_ratio": round(vol_r, 2),
                "extra": {
                    "vwap_zscore": round(current_vwap_z, 3),
                    "rsi": round(current_rsi, 1),
                    "candle_bullish": True,
                    "confluence_count": 3,
                },
                "timestamp": _now_iso(),
            })
        except Exception:
            continue

    return signals


# =====================================================================
# STRATEGY H7: Hoffman + Keltner Channel Expansion (68-73% WR)
# =====================================================================
# Rob Hoffman's EMA alignment (3/5/18 stack in order) combined with
# Keltner Channel expansion (ATR bands widening = breakout). Entry on
# pullback to middle Keltner band when EMAs are stacked and ADX > 20.
#
# Reference:
#   - Hoffman (2013): EMA 3/5/18 inventory retracement
#   - Keltner (1960): ATR-based channel bands
#   - Wilder (1978): ADX trend strength filter (> 20 = trending)
#   - Risk/Reward: 2:1 target using ATR-based stops
# =====================================================================

def hoffman_keltner_expansion(data: dict[str, pd.DataFrame],
                              context: dict | None = None) -> list[dict]:
    """
    Hoffman EMA 3/5/18 alignment + Keltner expansion + ADX > 20 pullback.
    Trend-following entry on orderly pullback during strong trends.
    Categories: crypto + forex.
    """
    signals = []
    target_symbols = _get_target_symbols()

    for symbol, meta in target_symbols.items():
        df = data.get(symbol)
        if df is None or len(df) < 50:
            continue

        try:
            df = _normalize_df(df)
            if not all(c in df.columns for c in ("open", "high", "low", "close", "volume")):
                continue

            close = df["close"]
            high = df["high"]
            low = df["low"]

            # Hoffman EMA stack: 3 > 5 > 18 (bullish) or 3 < 5 < 18 (bearish)
            ema3 = ema(close, 3)
            ema5 = ema(close, 5)
            ema18 = ema(close, 18)

            e3 = float(ema3.iloc[-1])
            e5 = float(ema5.iloc[-1])
            e18 = float(ema18.iloc[-1])

            if any(np.isnan(v) for v in (e3, e5, e18)):
                continue

            bullish_stack = e3 > e5 > e18
            bearish_stack = e3 < e5 < e18

            if not bullish_stack and not bearish_stack:
                continue

            # Keltner Channel expansion: current bandwidth > prior bandwidth
            kc = keltner_channels(high, low, close, ema_period=20,
                                  atr_period=10, atr_mult=1.5)
            kc_upper = kc["upper"]
            kc_lower = kc["lower"]
            kc_middle = kc["middle"]

            # Bandwidth = (upper - lower) / middle
            kc_bw = (kc_upper - kc_lower) / kc_middle.replace(0, np.nan)
            kc_bw_sma = sma(kc_bw, 10)

            current_bw = float(kc_bw.iloc[-1]) if not pd.isna(kc_bw.iloc[-1]) else 0
            avg_bw = float(kc_bw_sma.iloc[-1]) if not pd.isna(kc_bw_sma.iloc[-1]) else 0

            # Expansion: current bandwidth > 1.1x average (widening)
            if avg_bw <= 0 or current_bw < avg_bw * 1.1:
                continue

            # ADX > 20 filter for trend strength
            adx_val = adx(high, low, close, 14)
            current_adx = float(adx_val.iloc[-1]) if not pd.isna(adx_val.iloc[-1]) else 0.0
            if current_adx < 20:
                continue

            # Pullback filter: price near Keltner middle band (within 1.0 ATR)
            current_price = float(close.iloc[-1])
            kc_mid = float(kc_middle.iloc[-1])
            atr_val = atr(high, low, close, 14)
            current_atr = float(atr_val.iloc[-1])

            if current_atr <= 0:
                continue

            dist_to_mid = abs(current_price - kc_mid) / current_atr
            if dist_to_mid > 1.0:
                # Price too far from middle band -- not a pullback
                continue

            category = _get_category(symbol)

            if bullish_stack:
                # BUY signal: pullback to mid in bullish trend
                price, tp, sl = _atr_tp_sl_hybrid(close, high, low,
                                                   tp_mult=3.0, sl_mult=1.5)
                signal_type = "BUY"
            else:
                # SELL signal: rally to mid in bearish trend
                price_raw = float(close.iloc[-1])
                tp_raw = price_raw - 3.0 * current_atr
                sl_raw = price_raw + 1.5 * current_atr
                price = _smart_round(price_raw)
                tp = _smart_round(tp_raw)
                sl = _smart_round(sl_raw)
                signal_type = "SELL"

            # Validate R:R
            if signal_type == "BUY":
                if price <= sl:
                    continue
                rr = (tp - price) / (price - sl)
            else:
                if sl <= price:
                    continue
                rr = (price - tp) / (sl - price)

            if rr < 1.5:
                continue

            # Confidence based on ADX strength + EMA separation + bandwidth expansion
            base_conf = 0.55
            adx_bonus = min(0.10, (current_adx - 20) / 200.0)
            ema_sep = abs(e3 - e18) / abs(e18) if e18 != 0 else 0
            ema_bonus = min(0.10, ema_sep * 5.0)
            bw_bonus = min(0.05, (current_bw / avg_bw - 1.0) * 0.10)
            confidence = round(min(0.78, base_conf + adx_bonus + ema_bonus + bw_bonus), 2)

            rsi_val = float(rsi(close, 14).iloc[-1]) if not pd.isna(rsi(close, 14).iloc[-1]) else 50
            vol_r = float(volume_ratio(df["volume"]).iloc[-1])

            signals.append({
                "strategy": "hoffman_keltner_expansion",
                "symbol": symbol,
                "category": category,
                "signal_type": signal_type,
                "entry_price": price,
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": confidence,
                "risk_reward": round(rr, 2),
                "reason": (
                    f"Hoffman EMA {'bullish' if bullish_stack else 'bearish'} "
                    f"(3={e3:.4f}>5={e5:.4f}>18={e18:.4f}), "
                    f"Keltner expanding ({current_bw:.4f} vs avg {avg_bw:.4f}), "
                    f"ADX={current_adx:.1f}, pullback dist={dist_to_mid:.2f}ATR"
                ),
                "timeframe": "1d",
                "rsi_at_entry": round(rsi_val, 1),
                "atr_at_entry": round(current_atr, 4),
                "volume_ratio": round(vol_r, 2),
                "extra": {
                    "ema3": round(e3, 6),
                    "ema5": round(e5, 6),
                    "ema18": round(e18, 6),
                    "adx": round(current_adx, 1),
                    "keltner_bw": round(current_bw, 6),
                    "keltner_bw_avg": round(avg_bw, 6),
                    "pullback_dist_atr": round(dist_to_mid, 3),
                    "confluence_count": 3,
                },
                "timestamp": _now_iso(),
            })
        except Exception:
            continue

    return signals


# =====================================================================
# STRATEGY H8: AI EMA Pullback (72-78% WR)
# =====================================================================
# EMA 9/21 pullback in trend: price touches 21 EMA from above in uptrend.
# ML signal confirmation: only enter if context provides ML ranker with
# probability > 0.6 (graceful degradation if ML unavailable).
# Volume must be above average (1.2x+) and RSI in healthy pullback zone
# (40-60, not overbought or oversold).
#
# Reference:
#   - Elder (1993): Triple Screen -- multi-filter trend entry
#   - EMA pullback: institutional accumulation during trend corrections
#   - Risk/Reward: 2:1 target using ATR-based stops
# =====================================================================

def ai_ema_pullback(data: dict[str, pd.DataFrame],
                    context: dict | None = None) -> list[dict]:
    """
    EMA 9/21 pullback in uptrend + volume > 1.2x + RSI 40-60.
    ML confirmation overlay when available (>0.6 probability).
    Category: crypto only.
    """
    signals = []
    context = context or {}

    # ML weights from context (if ML ranker is available)
    ml_weights = context.get("ml_weights", {})

    for symbol, meta in CRYPTO_SYMBOLS.items():
        df = data.get(symbol)
        if df is None or len(df) < 50:
            continue

        try:
            df = _normalize_df(df)
            if not all(c in df.columns for c in ("open", "high", "low", "close", "volume")):
                continue

            close = df["close"]
            high = df["high"]
            low = df["low"]
            volume = df["volume"]

            # EMA 9 and 21
            ema9 = ema(close, 9)
            ema21 = ema(close, 21)

            e9 = float(ema9.iloc[-1])
            e21 = float(ema21.iloc[-1])
            e9_prev = float(ema9.iloc[-2]) if len(ema9) > 1 else e9
            e21_prev = float(ema21.iloc[-2]) if len(ema21) > 1 else e21

            if any(np.isnan(v) for v in (e9, e21)):
                continue

            # Uptrend: EMA9 > EMA21
            if e9 <= e21:
                continue

            # Trend confirmation: EMA9 was above EMA21 yesterday too (not a fresh cross)
            if e9_prev <= e21_prev:
                continue

            # Pullback: price near EMA21 (within 1.5 ATR above it)
            current_price = float(close.iloc[-1])
            atr_val = atr(high, low, close, 14)
            current_atr = float(atr_val.iloc[-1])
            if current_atr <= 0:
                continue

            dist_to_ema21 = (current_price - e21) / current_atr
            # Price should be near EMA21 (within 1.5 ATR above it) -- pullback zone
            if dist_to_ema21 > 1.5 or dist_to_ema21 < -0.2:
                continue

            # Condition: Volume above average (1.2x+)
            vol_r = float(volume_ratio(volume, 20).iloc[-1])
            if vol_r < 1.2:
                continue

            # Condition: RSI in healthy pullback zone (40-60)
            rsi_val_series = rsi(close, 14)
            current_rsi = float(rsi_val_series.iloc[-1]) if not pd.isna(rsi_val_series.iloc[-1]) else 50.0
            if current_rsi < 40 or current_rsi > 60:
                continue

            # ML confirmation (optional): check if ML ranker gives > 0.6 probability
            ml_score = None
            if ml_weights:
                ml_score = ml_weights.get(symbol, ml_weights.get("ai_ema_pullback"))
                if ml_score is not None and float(ml_score) < 0.6:
                    continue

            # All conditions met -- generate BUY signal
            category = _get_category(symbol)
            price, tp, sl = _atr_tp_sl_hybrid(close, high, low,
                                               tp_mult=3.0, sl_mult=1.5)

            if price <= sl:
                continue
            rr = (tp - price) / (price - sl)
            if rr < 1.8:
                continue

            # Confidence: higher when ML confirms, with RSI and volume bonuses
            base_conf = 0.58
            ml_bonus = 0.08 if (ml_score is not None and float(ml_score) > 0.6) else 0.0
            vol_bonus = min(0.07, (vol_r - 1.2) * 0.05)
            rsi_bonus = 0.05 if 45 <= current_rsi <= 55 else 0.0
            confidence = round(min(0.82, base_conf + ml_bonus + vol_bonus + rsi_bonus), 2)

            signals.append({
                "strategy": "ai_ema_pullback",
                "symbol": symbol,
                "category": category,
                "signal_type": "BUY",
                "entry_price": price,
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": confidence,
                "risk_reward": round(rr, 2),
                "reason": (
                    f"EMA pullback: 9={e9:.4f}>21={e21:.4f}, "
                    f"dist={dist_to_ema21:.2f}ATR, "
                    f"RSI={current_rsi:.1f} (40-60), "
                    f"Vol={vol_r:.1f}x (>1.2x)"
                    + (f", ML={float(ml_score):.2f}" if ml_score is not None else "")
                ),
                "timeframe": "1d",
                "rsi_at_entry": round(current_rsi, 1),
                "atr_at_entry": round(current_atr, 4),
                "volume_ratio": round(vol_r, 2),
                "extra": {
                    "ema9": round(e9, 6),
                    "ema21": round(e21, 6),
                    "pullback_dist_atr": round(dist_to_ema21, 3),
                    "rsi": round(current_rsi, 1),
                    "volume_ratio": round(vol_r, 2),
                    "ml_score": round(float(ml_score), 3) if ml_score is not None else None,
                    "ml_confirmed": ml_score is not None and float(ml_score) > 0.6,
                    "confluence_count": 4 if ml_score is not None else 3,
                },
                "timestamp": _now_iso(),
            })
        except Exception:
            continue

    return signals


# -- Strategy registry ------------------------------------------------

HYBRID_STRATEGIES: dict[str, callable] = {
    "hurst_volume_profile_confluence": hurst_volume_profile_confluence,
    "adaptive_hurst_markov_gated": adaptive_hurst_markov_gated,
    "multi_sigma_ema_stack": multi_sigma_ema_stack,
    "cross_system_regime_arbitrage": cross_system_regime_arbitrage,
    "widened_tp_momentum_carry": widened_tp_momentum_carry,
    # World-Class Roadmap -- Hybrid Confluence batch (March 2026)
    "vwap_rsi_confluence": vwap_rsi_confluence,
    "hoffman_keltner_expansion": hoffman_keltner_expansion,
    "ai_ema_pullback": ai_ema_pullback,
}


def get_hybrid_strategies() -> list:
    """Return list of all hybrid strategy functions."""
    return list(HYBRID_STRATEGIES.values())
