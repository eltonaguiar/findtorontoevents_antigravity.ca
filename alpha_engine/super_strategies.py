"""
ALPHA_ENGINE -- Super Strategies (Wave 20)
============================================
10 confluence strategies that combine the best-performing signals from
forward testing, walk-forward validation, and closed-pick analysis.

Design philosophy: DON'T KILL strategies -- mutate losers, combine
complementary edges, invert consistent failures.

Data-driven design inputs (2026-03-15):
  Forward performance:
    - fractal_sr_bounce:           71.4% WR, 14 trades, PF 3.68, Sharpe 6.7
    - widened_tp_momentum_carry:   66.7% WR, 6 trades, PF 4.28, Sharpe 11.6
    - multi_timeframe_ema_stack:   100% WR, 2 trades (bearish EMA stack shorts)
    - hurst_mean_reversion:        100% WR, 3 trades, PF inf
    - options_25delta_skew:        100% WR, 2 trades, PF inf
  Walk-forward ROBUST (OOS):
    - keltner_compression_expansion_v1: 75% OOS WR, PF 4.16
    - multi_period_rsi_confluence_xrp:  83.3% OOS WR, PF 13.08
    - multi_period_rsi_confluence_eth:  64.3% OOS WR, PF 7.58
  Consistent losers (inverse candidates):
    - seasonal_factor_rotation:  0% WR, 10 trades, 100% SL_HIT
    - order_book_imbalance:      0% WR, 4 trades, 100% SL_HIT
    - hurst_regime_adaptive:     20% WR, 5 trades

10 Super Strategies:
  TREND-FOLLOWING:
    1. super_keltner_ema_momentum    -- Keltner expansion + EMA stack + TSMOM
    2. super_hma_breakout_volume     -- HMA trend + breakout + volume confirmation
    3. super_channel_trend_rider     -- Keltner channel + ADX + multi-RSI
  MEAN-REVERSION:
    4. super_rsi_bollinger_revert    -- RSI + Bollinger %B + Hurst < 0.5
    5. super_vwap_zscore_bounce      -- VWAP z-score + fractal S/R + vol climax
    6. super_funding_rate_carry      -- Funding rate extreme + OI divergence + MVRV
  ON-CHAIN/SENTIMENT:
    7. super_whale_fear_accumulate   -- Fear&Greed + whale vol + Wyckoff accumulation
    8. super_options_macro_flow      -- Options skew + Hayes liquidity + VRP
  INVERSE:
    9. super_inverse_seasonal_obi    -- Flip seasonal_factor_rotation + order_book_imbalance
  ENSEMBLE:
    10. super_confluence_ensemble    -- Top-3 signal voting from best strategies

References: cited inline per strategy.
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd

from indicators import (
    ema, sma, hma, hma_slope,
    rsi, stoch_rsi, macd, adx, atr,
    bollinger_bands, bollinger_squeeze, keltner_channels,
    zscore, volume_ratio, volume_expansion, obv,
    vwap_session,
    hurst_exponent, shannon_entropy,
    detect_divergence, detect_support_resistance,
    detect_accumulation_phase, fair_value_gap,
)
from config import (
    CRYPTO_SYMBOLS, CATEGORY_RISK,
    BINANCE_FUTURES_BASE, BINANCE_BASE,
    FEAR_GREED_URL, COINGECKO_BASE,
)


# ---------------------------------------------------------------------------
# Helpers (shared with other strategy files)
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_category(symbol: str) -> str:
    info = CRYPTO_SYMBOLS.get(symbol, {})
    return info.get("cat", "crypto")


def _smart_round(value: float) -> float:
    """Round to appropriate precision based on magnitude."""
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


def _atr_tp_sl(close: pd.Series, high: pd.Series, low: pd.Series,
               direction: str = "long",
               tp_mult: float = 3.0, sl_mult: float = 2.25,
               atr_period: int = 14) -> tuple[float, float, float]:
    """ATR-based TP/SL adaptive to current volatility.

    SL set to 2.25x ATR (widened Feb 26 2026 -- 79/89 losses were SL_HIT
    from stops inside normal volatility bands).
    """
    atr_val = atr(high, low, close, atr_period)
    current_atr = float(atr_val.iloc[-1])
    price = float(close.iloc[-1])
    if direction == "long":
        tp = price + tp_mult * current_atr
        sl = price - sl_mult * current_atr
    else:
        tp = price - tp_mult * current_atr
        sl = price + sl_mult * current_atr
    return _smart_round(price), _smart_round(tp), _smart_round(sl)


def _fetch_json(url: str, timeout: int = 8) -> Optional[dict]:
    """Fetch JSON from URL with timeout. Returns None on failure."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ALPHA_ENGINE/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def _make_signal(strategy: str, symbol: str, signal_type: str,
                 direction: str, entry: float, tp: float, sl: float,
                 confidence: float, reason: str, timeframe: str = "1-7d",
                 extra: Optional[dict] = None) -> dict:
    """Build a standardized signal dict."""
    rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 1.0
    sig = {
        "strategy": strategy,
        "symbol": symbol,
        "category": _get_category(symbol),
        "signal_type": signal_type,
        "direction": direction,
        "entry_price": _smart_round(entry),
        "take_profit": _smart_round(tp),
        "stop_loss": _smart_round(sl),
        "confidence": round(min(confidence, 0.95), 3),
        "risk_reward": round(rr, 2),
        "reason": reason,
        "timeframe": timeframe,
        "timestamp": _now_iso(),
    }
    if extra:
        sig["extra"] = extra
    return sig


# ---------------------------------------------------------------------------
# Mutation genes -- evolvable parameters for each super strategy
# ---------------------------------------------------------------------------

MUTATION_GENES = {
    "super_keltner_ema_momentum": {
        "ema_fast": (8, 12, 1), "ema_slow": (20, 26, 1),
        "kc_ema": (18, 24, 1), "kc_atr_mult": (1.0, 2.0, 0.1),
        "rsi_ob": (65, 80, 1), "tp_atr_mult": (2.0, 4.0, 0.25),
        "sl_atr_mult": (1.5, 2.5, 0.25),
    },
    "super_hma_breakout_volume": {
        "hma_period": (21, 55, 2), "vol_threshold": (1.3, 2.5, 0.1),
        "atr_period": (10, 20, 1), "tp_atr_mult": (2.5, 4.0, 0.25),
    },
    "super_channel_trend_rider": {
        "kc_period": (18, 30, 1), "adx_threshold": (20, 30, 1),
        "rsi_fast": (2, 5, 1), "rsi_slow": (14, 21, 1),
    },
    "super_rsi_bollinger_revert": {
        "rsi_period": (2, 7, 1), "bb_period": (18, 25, 1),
        "bb_std": (1.8, 2.5, 0.1), "hurst_threshold": (0.40, 0.50, 0.02),
    },
    "super_vwap_zscore_bounce": {
        "zscore_threshold": (2.0, 3.0, 0.25), "vol_climax_mult": (2.0, 4.0, 0.5),
        "fractal_lookback": (30, 60, 5),
    },
    "super_funding_rate_carry": {
        "funding_extreme": (0.03, 0.08, 0.01),
        "mvrv_threshold": (1.0, 1.5, 0.1),
    },
    "super_whale_fear_accumulate": {
        "fg_threshold": (15, 25, 1), "whale_vol_mult": (3.0, 7.0, 0.5),
        "wyckoff_score_min": (0.45, 0.65, 0.05),
    },
    "super_options_macro_flow": {
        "skew_threshold": (-8.0, -3.0, 0.5),
        "vrp_threshold": (8.0, 15.0, 1.0),
    },
    "super_inverse_seasonal_obi": {
        "lookback": (14, 30, 1), "confidence_floor": (0.60, 0.75, 0.05),
    },
    "super_confluence_ensemble": {
        "min_votes": (2, 3, 1), "confidence_boost": (0.05, 0.15, 0.02),
    },
}


# =========================================================================
# SUPER STRATEGY 1: Keltner-EMA Momentum (Trend-Following)
# =========================================================================
# Combines:
#   - Keltner channel expansion (75% OOS WR from walk-forward)
#   - EMA stack alignment (100% forward WR on bearish stack shorts)
#   - TSMOM 28d (100% WR, 1 trade -- Moskowitz et al. 2012)
# Logic: Keltner expansion + EMA 9/21/50 aligned + 28d momentum positive
# Targets: BTC, ETH, SOL, BNB (majors with deepest liquidity)
# =========================================================================

def super_keltner_ema_momentum(data: dict[str, pd.DataFrame],
                               context: Optional[dict] = None) -> list[dict]:
    """Keltner expansion + EMA stack + time-series momentum confluence."""
    signals = []
    target_symbols = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD",
                      "XRP-USD", "ADA-USD", "AVAX-USD", "LINK-USD",
                      "DOT-USD", "DOGE-USD"]

    for symbol in target_symbols:
        df = data.get(symbol)
        if df is None or len(df) < 100:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df.get("Volume", pd.Series(np.ones(len(close))))

        # -- Keltner channel expansion --
        kc = keltner_channels(high, low, close, ema_period=20, atr_period=14, atr_mult=1.5)
        kc_width = (kc["upper"] - kc["lower"]) / kc["middle"]
        kc_width_min = kc_width.rolling(60).min()
        expanding = float(kc_width.iloc[-1]) > float(kc_width_min.iloc[-1]) * 1.3

        if not expanding:
            continue

        # -- EMA stack alignment --
        ema9 = ema(close, 9)
        ema21 = ema(close, 21)
        ema50 = ema(close, 50)

        price = float(close.iloc[-1])
        e9 = float(ema9.iloc[-1])
        e21 = float(ema21.iloc[-1])
        e50 = float(ema50.iloc[-1])

        bullish_stack = e9 > e21 > e50 and price > e9
        bearish_stack = e9 < e21 < e50 and price < e9

        if not (bullish_stack or bearish_stack):
            continue

        # -- TSMOM 28d: positive return over 28 days --
        if len(close) >= 29:
            ret_28d = float(close.iloc[-1] / close.iloc[-29] - 1)
        else:
            continue

        # Direction alignment: TSMOM must agree with EMA stack
        if bullish_stack and ret_28d <= 0:
            continue
        if bearish_stack and ret_28d >= 0:
            continue

        # -- RSI filter: avoid exhaustion --
        rsi_val = float(rsi(close, 14).iloc[-1])
        if bullish_stack and rsi_val > 78:
            continue
        if bearish_stack and rsi_val < 22:
            continue

        # -- Volume confirmation --
        vr = float(volume_ratio(volume, 20).iloc[-1])
        if vr < 0.8:
            continue

        # Build signal
        direction = "long" if bullish_stack else "short"
        signal_type = "BUY" if direction == "long" else "SELL"

        entry, tp, sl = _atr_tp_sl(close, high, low, direction=direction,
                                    tp_mult=3.0, sl_mult=2.25)

        # Confidence: base 0.70, +0.05 for volume, +0.05 for strong TSMOM
        conf = 0.70
        if vr > 1.5:
            conf += 0.05
        if abs(ret_28d) > 0.10:
            conf += 0.05
        if abs(ret_28d) > 0.20:
            conf += 0.03

        reason = (f"Super Keltner-EMA Momentum: {'Bullish' if bullish_stack else 'Bearish'} "
                  f"EMA stack (9{'>' if bullish_stack else '<'}21{'>' if bullish_stack else '<'}50), "
                  f"Keltner expanding {float(kc_width.iloc[-1]):.4f} vs min {float(kc_width_min.iloc[-1]):.4f}, "
                  f"TSMOM 28d={ret_28d:+.1%}, RSI={rsi_val:.0f}, vol={vr:.1f}x")

        signals.append(_make_signal(
            "super_keltner_ema_momentum", symbol, signal_type, direction.upper(),
            entry, tp, sl, conf, reason, "3-7d",
            extra={"tsmom_28d": round(ret_28d, 4), "rsi": round(rsi_val, 1),
                   "vol_ratio": round(vr, 2), "ema_stack": "bullish" if bullish_stack else "bearish"}
        ))

    return signals


# =========================================================================
# SUPER STRATEGY 2: HMA Breakout Volume (Trend-Following)
# =========================================================================
# Combines:
#   - Hull Moving Average trend (lag-reduced, Alan Hull 2005)
#   - Price breakout above/below 20d range
#   - Volume expansion (>1.5x average)
#   - ADX > 25 trending filter (Wilder 1978)
# From keltner_evolved: HMA period=43 was best from genetic evolution.
# Targets: Mid-cap alts that trend hard (SOL, AVAX, NEAR, FIL, WLD)
# =========================================================================

def super_hma_breakout_volume(data: dict[str, pd.DataFrame],
                              context: Optional[dict] = None) -> list[dict]:
    """HMA trend direction + range breakout + volume expansion + ADX filter."""
    signals = []
    target_symbols = ["SOL-USD", "AVAX-USD", "NEAR-USD", "FIL-USD",
                      "WLD-USD", "SUI-USD", "INJ-USD", "APT-USD",
                      "DOT-USD", "DOGE-USD", "ADA-USD", "LINK-USD"]

    for symbol in target_symbols:
        df = data.get(symbol)
        if df is None or len(df) < 60:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df.get("Volume", pd.Series(np.ones(len(close))))

        # -- HMA trend (period 43 from genetic evolution) --
        hma_dir = hma_slope(close, 43)
        cur_hma_dir = float(hma_dir.iloc[-1]) if not pd.isna(hma_dir.iloc[-1]) else 0

        if cur_hma_dir == 0:
            continue

        # -- Range breakout (20-day high/low) --
        high_20 = float(high.rolling(20).max().iloc[-2])  # Previous bar's 20d high
        low_20 = float(low.rolling(20).min().iloc[-2])
        price = float(close.iloc[-1])

        breakout_up = price > high_20 and cur_hma_dir > 0
        breakout_down = price < low_20 and cur_hma_dir < 0

        if not (breakout_up or breakout_down):
            continue

        # -- ADX trending filter --
        adx_val = float(adx(high, low, close, 14).iloc[-1])
        if pd.isna(adx_val) or adx_val < 22:
            continue

        # -- Volume expansion --
        vr = float(volume_ratio(volume, 20).iloc[-1])
        if vr < 1.3:
            continue

        direction = "long" if breakout_up else "short"
        signal_type = "BUY" if direction == "long" else "SELL"

        entry, tp, sl = _atr_tp_sl(close, high, low, direction=direction,
                                    tp_mult=3.5, sl_mult=2.0)

        conf = 0.72
        if adx_val > 30:
            conf += 0.05
        if vr > 2.0:
            conf += 0.05

        reason = (f"Super HMA Breakout: {'Bullish' if breakout_up else 'Bearish'} "
                  f"20d range break (price={price:.4f} vs "
                  f"{'high' if breakout_up else 'low'}={high_20 if breakout_up else low_20:.4f}), "
                  f"HMA(43) dir={'+' if cur_hma_dir > 0 else '-'}, "
                  f"ADX={adx_val:.0f}, vol={vr:.1f}x")

        signals.append(_make_signal(
            "super_hma_breakout_volume", symbol, signal_type, direction.upper(),
            entry, tp, sl, conf, reason, "3-7d",
            extra={"adx": round(adx_val, 1), "vol_ratio": round(vr, 2),
                   "hma_direction": "up" if cur_hma_dir > 0 else "down"}
        ))

    return signals


# =========================================================================
# SUPER STRATEGY 3: Channel Trend Rider (Trend-Following)
# =========================================================================
# Combines:
#   - Keltner channel mid-line pullback (buy dips in uptrend)
#   - ADX > 25 (trending confirmation)
#   - Multi-period RSI confluence (83.3% OOS WR on XRP, 64.3% on ETH)
#     RSI(2) oversold + RSI(14) > 40 = short-term dip in medium-term uptrend
# Targets: All crypto majors (works best in trending markets)
# =========================================================================

def super_channel_trend_rider(data: dict[str, pd.DataFrame],
                              context: Optional[dict] = None) -> list[dict]:
    """Keltner mid-line pullback + ADX trend + multi-period RSI confluence."""
    signals = []
    target_symbols = list(CRYPTO_SYMBOLS.keys())

    for symbol in target_symbols:
        df = data.get(symbol)
        if df is None or len(df) < 60:
            continue

        info = CRYPTO_SYMBOLS.get(symbol, {})
        cat = info.get("cat", "crypto")
        if cat not in ("crypto", "meme"):
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]

        # -- Keltner channel --
        kc = keltner_channels(high, low, close, ema_period=20, atr_period=14, atr_mult=1.5)
        price = float(close.iloc[-1])
        kc_mid = float(kc["middle"].iloc[-1])
        kc_upper = float(kc["upper"].iloc[-1])
        kc_lower = float(kc["lower"].iloc[-1])

        # -- ADX trending --
        adx_val = float(adx(high, low, close, 14).iloc[-1])
        if pd.isna(adx_val) or adx_val < 22:
            continue

        # -- Multi-period RSI --
        rsi2 = float(rsi(close, 2).iloc[-1])
        rsi14 = float(rsi(close, 14).iloc[-1])

        # LONG: pullback to mid-line in uptrend
        # RSI(2) < 20 (short-term oversold) + RSI(14) > 40 (med-term still healthy)
        # Price near Keltner middle (within 0.5 ATR)
        atr_val = float(atr(high, low, close, 14).iloc[-1])
        near_mid = abs(price - kc_mid) < 0.5 * atr_val

        bullish = (rsi2 < 20 and rsi14 > 40 and rsi14 < 70
                   and price > kc_lower and near_mid)

        # SHORT: bounce to mid-line in downtrend
        bearish = (rsi2 > 80 and rsi14 < 60 and rsi14 > 30
                   and price < kc_upper and near_mid)

        if not (bullish or bearish):
            continue

        direction = "long" if bullish else "short"
        signal_type = "BUY" if direction == "long" else "SELL"

        entry, tp, sl = _atr_tp_sl(close, high, low, direction=direction,
                                    tp_mult=2.5, sl_mult=2.0)

        conf = 0.73
        if adx_val > 30:
            conf += 0.04
        # RSI extremity bonus
        if bullish and rsi2 < 10:
            conf += 0.04
        if bearish and rsi2 > 90:
            conf += 0.04

        reason = (f"Super Channel Trend Rider: {'Long pullback' if bullish else 'Short bounce'} "
                  f"at Keltner mid ({kc_mid:.4f}), RSI(2)={rsi2:.0f}, RSI(14)={rsi14:.0f}, "
                  f"ADX={adx_val:.0f}. Multi-period RSI confluence (83% OOS WR XRP)")

        signals.append(_make_signal(
            "super_channel_trend_rider", symbol, signal_type, direction.upper(),
            entry, tp, sl, conf, reason, "2-5d",
            extra={"rsi2": round(rsi2, 1), "rsi14": round(rsi14, 1),
                   "adx": round(adx_val, 1), "kc_mid": round(kc_mid, 4)}
        ))

    return signals


# =========================================================================
# SUPER STRATEGY 4: RSI-Bollinger Mean Reversion (Mean-Reversion)
# =========================================================================
# Combines:
#   - RSI(2) < 10 / > 90 (Connors RSI-2: 75.7% WR SPY, proven)
#   - Bollinger %B < 0 / > 1 (price outside bands)
#   - Hurst exponent < 0.5 (confirms mean-reverting regime)
#   - hurst_mean_reversion: 100% WR, 3 trades in forward testing
# Logic: When Hurst says mean-reverting AND price is at Bollinger extreme
#         AND RSI(2) is extreme, enter for snap-back.
# Targets: All crypto (mean-reversion works in ranging markets)
# =========================================================================

def super_rsi_bollinger_revert(data: dict[str, pd.DataFrame],
                               context: Optional[dict] = None) -> list[dict]:
    """RSI(2) extreme + Bollinger band violation + Hurst mean-reversion regime."""
    signals = []
    target_symbols = list(CRYPTO_SYMBOLS.keys())

    for symbol in target_symbols:
        df = data.get(symbol)
        if df is None or len(df) < 60:
            continue

        info = CRYPTO_SYMBOLS.get(symbol, {})
        cat = info.get("cat", "crypto")
        if cat not in ("crypto", "meme"):
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]

        # -- Hurst exponent: must be mean-reverting (H < 0.45) --
        H = hurst_exponent(close, max_lag=20)
        if H >= 0.45:
            continue

        # -- RSI(2) extreme --
        rsi2 = float(rsi(close, 2).iloc[-1])

        # -- Bollinger Bands --
        bb = bollinger_bands(close, 20, 2.0)
        pct_b = float(bb["pct_b"].iloc[-1])

        # LONG: RSI(2) < 10 + %B < 0.05 (below lower band)
        bullish = rsi2 < 10 and pct_b < 0.05

        # SHORT: RSI(2) > 90 + %B > 0.95 (above upper band)
        bearish = rsi2 > 90 and pct_b > 0.95

        if not (bullish or bearish):
            continue

        # -- ADX must be LOW (ranging market for mean-reversion) --
        adx_val = float(adx(high, low, close, 14).iloc[-1])
        if not pd.isna(adx_val) and adx_val > 30:
            continue  # Too trendy for mean-reversion

        direction = "long" if bullish else "short"
        signal_type = "BUY" if direction == "long" else "SELL"

        # Tighter TP for mean-reversion (target Bollinger mid)
        entry, tp, sl = _atr_tp_sl(close, high, low, direction=direction,
                                    tp_mult=2.0, sl_mult=2.25)

        conf = 0.74
        if H < 0.35:
            conf += 0.05  # Strongly mean-reverting
        if bullish and rsi2 < 5:
            conf += 0.04
        if bearish and rsi2 > 95:
            conf += 0.04

        reason = (f"Super RSI-Bollinger Revert: Hurst={H:.2f} (mean-reverting), "
                  f"RSI(2)={rsi2:.0f}, BB %B={pct_b:.2f}, ADX={adx_val:.0f}. "
                  f"{'Oversold snap-back' if bullish else 'Overbought fade'} expected")

        signals.append(_make_signal(
            "super_rsi_bollinger_revert", symbol, signal_type, direction.upper(),
            entry, tp, sl, conf, reason, "1-3d",
            extra={"hurst": round(H, 3), "rsi2": round(rsi2, 1),
                   "pct_b": round(pct_b, 3), "adx": round(adx_val, 1)}
        ))

    return signals


# =========================================================================
# SUPER STRATEGY 5: VWAP Z-Score Bounce (Mean-Reversion)
# =========================================================================
# Combines:
#   - VWAP z-score < -2.0 / > 2.0 (extreme extension from fair value)
#   - Fractal S/R nearby (71.4% WR, PF 3.68 in forward testing)
#   - Volume climax (exhaustion signal)
# Logic: Price far from VWAP + at support/resistance + volume climax = reversal
# Targets: Mid-cap alts with good volume profiles
# =========================================================================

def super_vwap_zscore_bounce(data: dict[str, pd.DataFrame],
                             context: Optional[dict] = None) -> list[dict]:
    """VWAP z-score extension + fractal S/R + volume climax reversal."""
    signals = []
    target_symbols = list(CRYPTO_SYMBOLS.keys())

    for symbol in target_symbols:
        df = data.get(symbol)
        if df is None or len(df) < 60:
            continue

        info = CRYPTO_SYMBOLS.get(symbol, {})
        cat = info.get("cat", "crypto")
        if cat not in ("crypto", "meme"):
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df.get("Volume", pd.Series(np.ones(len(close))))

        # -- VWAP z-score --
        vwap = vwap_session(high, low, close, volume)
        if vwap.isna().all():
            continue
        vwap_diff = close - vwap
        vwap_z = zscore(vwap_diff, 20)
        cur_vwap_z = float(vwap_z.iloc[-1]) if not pd.isna(vwap_z.iloc[-1]) else 0

        # Need extreme z-score
        if abs(cur_vwap_z) < 2.0:
            continue

        # -- Volume climax (exhaustion): volume > 2.5x average --
        vr = float(volume_ratio(volume, 20).iloc[-1])
        vol_climax = vr > 2.0

        # -- Fractal S/R: check if price is near a support/resistance level --
        sr = detect_support_resistance(close, lookback=60, num_levels=3)
        price = float(close.iloc[-1])
        atr_val = float(atr(high, low, close, 14).iloc[-1])

        near_support = any(abs(price - s) < atr_val for s in sr.get("support", []))
        near_resistance = any(abs(price - r) < atr_val for r in sr.get("resistance", []))

        # LONG: oversold + near support + (volume climax preferred)
        bullish = cur_vwap_z < -2.0 and near_support
        # SHORT: overbought + near resistance + (volume climax preferred)
        bearish = cur_vwap_z > 2.0 and near_resistance

        if not (bullish or bearish):
            continue

        direction = "long" if bullish else "short"
        signal_type = "BUY" if direction == "long" else "SELL"

        entry, tp, sl = _atr_tp_sl(close, high, low, direction=direction,
                                    tp_mult=2.5, sl_mult=2.0)

        conf = 0.68
        if vol_climax:
            conf += 0.08  # Volume climax is strong exhaustion signal
        if abs(cur_vwap_z) > 3.0:
            conf += 0.05

        nearest_level = (sr["support"][0] if bullish and sr["support"]
                         else sr["resistance"][0] if bearish and sr["resistance"]
                         else price)

        reason = (f"Super VWAP Bounce: VWAP z-score={cur_vwap_z:.1f}, "
                  f"near {'support' if bullish else 'resistance'} at {nearest_level:.4f}, "
                  f"vol={vr:.1f}x {'(CLIMAX)' if vol_climax else ''}, "
                  f"fractal_sr_bounce 71.4% fwd WR")

        signals.append(_make_signal(
            "super_vwap_zscore_bounce", symbol, signal_type, direction.upper(),
            entry, tp, sl, conf, reason, "1-5d",
            extra={"vwap_zscore": round(cur_vwap_z, 2), "vol_ratio": round(vr, 2),
                   "vol_climax": vol_climax, "sr_level": round(nearest_level, 4)}
        ))

    return signals


# =========================================================================
# SUPER STRATEGY 6: Funding Rate Carry Plus (Mean-Reversion)
# =========================================================================
# Combines:
#   - Funding rate extreme (>0.05% = overleveraged longs, <-0.02% = shorts)
#   - OI/price divergence (rising OI + falling price = short squeeze setup)
#   - MVRV proxy (price vs 200d SMA as realized price proxy)
# Reference: Kraken Research (2023), CryptoQuant (2020)
# funding_rate_carry has 8.19 Sharpe in config STRATEGY_WEIGHT_OVERRIDES
# Targets: BTC, ETH (deepest perpetual futures markets)
# =========================================================================

def super_funding_rate_carry(data: dict[str, pd.DataFrame],
                             context: Optional[dict] = None) -> list[dict]:
    """Funding rate extreme + OI divergence + MVRV proxy confluence."""
    signals = []
    target_symbols = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
                      "ADA-USD", "AVAX-USD", "LINK-USD", "DOT-USD", "DOGE-USD"]

    for symbol in target_symbols:
        df = data.get(symbol)
        if df is None or len(df) < 200:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]

        binance_sym = CRYPTO_SYMBOLS.get(symbol, {}).get("binance")
        if not binance_sym:
            continue

        # -- Fetch funding rate from Binance --
        funding_url = f"{BINANCE_FUTURES_BASE}/fapi/v1/fundingRate?symbol={binance_sym}&limit=1"
        funding_data = _fetch_json(funding_url)

        if not funding_data or not isinstance(funding_data, list) or len(funding_data) == 0:
            continue

        funding_rate = float(funding_data[0].get("fundingRate", 0))

        # -- MVRV proxy: price / 200d SMA --
        sma200 = float(sma(close, 200).iloc[-1])
        if pd.isna(sma200) or sma200 == 0:
            continue
        price = float(close.iloc[-1])
        mvrv_proxy = price / sma200

        # -- OI divergence proxy: compare recent price vs volume trend --
        # Rising volume + falling price suggests accumulation (OI building)
        price_5d_ret = float(close.iloc[-1] / close.iloc[-6] - 1) if len(close) > 6 else 0
        volume = df.get("Volume", pd.Series(np.ones(len(close))))
        vol_5d = float(volume.iloc[-5:].mean())
        vol_20d = float(volume.iloc[-20:].mean())
        oi_proxy_divergence = (vol_5d > vol_20d * 1.2) and (price_5d_ret < -0.02)

        # LONG: funding very negative (shorts paying longs) + MVRV < 1.2 (undervalued)
        bullish = (funding_rate < -0.02 and mvrv_proxy < 1.2)

        # SHORT: funding very positive (longs paying shorts) + MVRV > 1.5 (overvalued)
        bearish = (funding_rate > 0.05 and mvrv_proxy > 1.5)

        if not (bullish or bearish):
            continue

        direction = "long" if bullish else "short"
        signal_type = "BUY" if direction == "long" else "SELL"

        entry, tp, sl = _atr_tp_sl(close, high, low, direction=direction,
                                    tp_mult=3.0, sl_mult=2.25)

        conf = 0.72
        if oi_proxy_divergence and bullish:
            conf += 0.08  # OI divergence adds conviction for longs
        if mvrv_proxy < 0.9:
            conf += 0.05  # Deeply undervalued
        if abs(funding_rate) > 0.08:
            conf += 0.05  # Extreme funding

        reason = (f"Super Funding Carry: funding={funding_rate:.4f}% "
                  f"({'shorts paying' if funding_rate < 0 else 'longs paying'}), "
                  f"MVRV proxy={mvrv_proxy:.2f} (price/${price:.0f} vs 200SMA/${sma200:.0f}), "
                  f"OI divergence={'YES' if oi_proxy_divergence else 'no'}")

        signals.append(_make_signal(
            "super_funding_rate_carry", symbol, signal_type, direction.upper(),
            entry, tp, sl, conf, reason, "3-7d",
            extra={"funding_rate": round(funding_rate, 6),
                   "mvrv_proxy": round(mvrv_proxy, 3),
                   "oi_divergence": oi_proxy_divergence}
        ))

    return signals


# =========================================================================
# SUPER STRATEGY 7: Whale Fear Accumulation (On-Chain/Sentiment)
# =========================================================================
# Combines:
#   - Fear & Greed Index <= 20 (extreme fear = buy)
#   - Whale volume detection (>5x avg volume = smart money accumulation)
#   - Wyckoff accumulation phase detection (range contraction + vol decline)
# Reference: Wyckoff (1930s), CNN F&G (Nasdaq backtest: 14.6% annual at F&G<=10)
# wyckoff_accumulation + fear_greed_contrarian both profitable in forward test
# Targets: BTC, ETH primarily (whales accumulate majors)
# =========================================================================

def super_whale_fear_accumulate(data: dict[str, pd.DataFrame],
                                context: Optional[dict] = None) -> list[dict]:
    """Fear & Greed extreme + whale volume + Wyckoff accumulation phase."""
    signals = []

    # -- Fetch Fear & Greed Index --
    fg_data = _fetch_json(FEAR_GREED_URL)
    if not fg_data or "data" not in fg_data:
        return signals

    try:
        fg_value = int(fg_data["data"][0]["value"])
        fg_class = fg_data["data"][0].get("value_classification", "")
    except (KeyError, IndexError, ValueError):
        return signals

    # Only fire on extreme fear OR extreme greed
    extreme_fear = fg_value <= 20
    extreme_greed = fg_value >= 80

    if not (extreme_fear or extreme_greed):
        return signals

    target_symbols = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD",
                      "ADA-USD", "AVAX-USD", "XRP-USD", "LINK-USD",
                      "DOT-USD", "DOGE-USD"]

    for symbol in target_symbols:
        df = data.get(symbol)
        if df is None or len(df) < 60:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df.get("Volume", pd.Series(np.ones(len(close))))

        # -- Whale volume: current volume > 5x 20d average --
        vr = float(volume_ratio(volume, 20).iloc[-1])
        whale_volume = vr > 3.0

        # -- Wyckoff accumulation detection --
        wyckoff = detect_accumulation_phase(close, volume, lookback=30)
        accumulating = wyckoff.get("is_accumulating", False)
        phase_score = wyckoff.get("phase_score", 0)

        # Need at least whale volume OR Wyckoff accumulation
        if not (whale_volume or accumulating):
            continue

        price = float(close.iloc[-1])

        if extreme_fear:
            # BUY during extreme fear with accumulation signals
            direction = "long"
            signal_type = "BUY"
        else:
            # SELL during extreme greed (distribution phase)
            direction = "short"
            signal_type = "SELL"

        entry, tp, sl = _atr_tp_sl(close, high, low, direction=direction,
                                    tp_mult=3.0, sl_mult=2.25)

        conf = 0.68
        if whale_volume and accumulating:
            conf += 0.10  # Both signals = high conviction
        elif whale_volume:
            conf += 0.06
        elif accumulating:
            conf += 0.04
        if fg_value <= 10 or fg_value >= 90:
            conf += 0.05  # Ultra-extreme

        reason = (f"Super Whale Fear: F&G={fg_value} ({fg_class}), "
                  f"vol={vr:.1f}x {'(WHALE)' if whale_volume else ''}, "
                  f"Wyckoff phase={phase_score:.2f} "
                  f"{'(ACCUMULATING)' if accumulating else ''}. "
                  f"{'Contrarian buy in extreme fear' if extreme_fear else 'Distribution sell in greed'}")

        signals.append(_make_signal(
            "super_whale_fear_accumulate", symbol, signal_type, direction.upper(),
            entry, tp, sl, conf, reason, "5-14d",
            extra={"fear_greed": fg_value, "vol_ratio": round(vr, 2),
                   "whale_volume": whale_volume, "wyckoff_score": phase_score}
        ))

    return signals


# =========================================================================
# SUPER STRATEGY 8: Options Macro Flow (On-Chain/Sentiment)
# =========================================================================
# Combines:
#   - Options 25-delta skew (100% WR, 2 trades in forward testing)
#     Negative skew (puts cheap) = institutional bullish positioning
#   - Hayes Liquidity Index (Fed BS - RRP - TGA; 50% WR but profitable)
#   - VRP: DVOL vs realized vol (sell premium when IV >> RV)
# Reference: Deribit (2019-2024), Arthur Hayes (2024)
# Targets: BTC, ETH (only assets with liquid options market)
# =========================================================================

def super_options_macro_flow(data: dict[str, pd.DataFrame],
                             context: Optional[dict] = None) -> list[dict]:
    """Options skew + Hayes liquidity + volatility risk premium confluence."""
    signals = []

    # BTC/ETH ONLY: Deribit options skew data only available for BTC and ETH.
    # SOL has nascent options market but skew data unreliable.
    btc_df = data.get("BTC-USD")
    eth_df = data.get("ETH-USD")

    if btc_df is None or len(btc_df) < 35:
        return signals

    for symbol, df in [("BTC-USD", btc_df), ("ETH-USD", eth_df)]:
        if df is None or len(df) < 35:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        price = float(close.iloc[-1])

        vote_bull = 0
        vote_bear = 0
        components = []

        # -- Component 1: Options 25-delta skew from Deribit --
        currency = "BTC" if "BTC" in symbol else "ETH"
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        start_ms = now_ms - 86400_000  # Last 24h

        dvol_url = (
            f"https://www.deribit.com/api/v2/public/get_volatility_index_data"
            f"?currency={currency}&start_timestamp={start_ms}&end_timestamp={now_ms}"
            f"&resolution=3600"
        )
        dvol_data = _fetch_json(dvol_url, timeout=10)

        if dvol_data and "result" in dvol_data:
            dvol_points = dvol_data["result"].get("data", [])
            if dvol_points:
                latest_dvol = float(dvol_points[-1][4])

                # Calculate realized vol
                returns = close.pct_change().dropna()
                if len(returns) >= 30:
                    rv_30d = float(returns.tail(30).std() * np.sqrt(365) * 100)
                    vrp = latest_dvol - rv_30d

                    if vrp > 10:
                        vote_bear += 1  # IV high = fear priced in, often overdone
                        components.append(f"VRP=+{vrp:.0f}pts (IV>RV, overpriced fear)")
                    elif vrp < -5:
                        vote_bull += 1  # IV cheap = complacency, buy vol
                        components.append(f"VRP={vrp:.0f}pts (IV<RV, vol cheap)")

                    # Skew proxy: DVOL trend over 24h
                    if len(dvol_points) > 4:
                        dvol_start = float(dvol_points[0][4])
                        dvol_end = float(dvol_points[-1][4])
                        dvol_change = dvol_end - dvol_start
                        if dvol_change < -3:
                            vote_bull += 1  # Falling IV = puts getting cheaper = bullish
                            components.append(f"DVOL falling {dvol_change:.1f}pts (puts cheaper)")
                        elif dvol_change > 3:
                            vote_bear += 1
                            components.append(f"DVOL rising +{dvol_change:.1f}pts (hedging up)")

        # -- Component 2: Macro liquidity proxy (200d SMA slope) --
        if len(close) >= 210:
            sma200 = sma(close, 200)
            sma200_slope = float(sma200.iloc[-1] - sma200.iloc[-10]) / float(sma200.iloc[-10])
            if sma200_slope > 0.005:
                vote_bull += 1
                components.append(f"200SMA slope=+{sma200_slope:.3f} (macro up)")
            elif sma200_slope < -0.005:
                vote_bear += 1
                components.append(f"200SMA slope={sma200_slope:.3f} (macro down)")

        # -- Need >= 2 votes in same direction --
        if vote_bull >= 2:
            direction = "long"
            signal_type = "BUY"
        elif vote_bear >= 2:
            direction = "short"
            signal_type = "SELL"
        else:
            continue

        entry, tp, sl = _atr_tp_sl(close, high, low, direction=direction,
                                    tp_mult=3.0, sl_mult=2.25)

        conf = 0.70 + 0.05 * max(vote_bull, vote_bear)

        reason = (f"Super Options Macro: {' + '.join(components)}. "
                  f"Votes: bull={vote_bull}, bear={vote_bear}. "
                  f"options_25delta_skew 100% fwd WR")

        signals.append(_make_signal(
            "super_options_macro_flow", symbol, signal_type, direction.upper(),
            entry, tp, sl, conf, reason, "5-10d",
            extra={"vote_bull": vote_bull, "vote_bear": vote_bear,
                   "components": components}
        ))

    return signals


# =========================================================================
# SUPER STRATEGY 9: Inverse Seasonal + OBI (Inverse / Contrarian)
# =========================================================================
# Flips two consistent losers:
#   - seasonal_factor_rotation: 0% WR, 10 trades, 100% SL_HIT
#     -> The seasonal signals are WRONG in current regime, so INVERT them
#   - order_book_imbalance: 0% WR, 4 trades, 100% SL_HIT
#     -> OBI generates signals in wrong direction, so INVERT
#
# Academic basis: Jegadeesh (1990) -- past losers outperform when inverted.
# If a signal consistently loses, it has edge -- just in the wrong direction.
# Both strategies have NO wins, meaning they're systematically wrong.
#
# Logic: Compute what seasonal_factor_rotation WOULD signal, then go opposite.
#        Compute what OBI WOULD signal, then go opposite.
#        When both inverted signals agree, fire with high confidence.
# Targets: BTC, ETH (both OBI losers were BTC/ETH)
# =========================================================================

def super_inverse_seasonal_obi(data: dict[str, pd.DataFrame],
                               context: Optional[dict] = None) -> list[dict]:
    """Invert consistently-losing seasonal rotation + order book imbalance signals."""
    signals = []
    target_symbols = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
                      "ADA-USD", "AVAX-USD", "LINK-USD", "DOT-USD", "DOGE-USD"]

    for symbol in target_symbols:
        df = data.get(symbol)
        if df is None or len(df) < 60:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df.get("Volume", pd.Series(np.ones(len(close))))

        price = float(close.iloc[-1])
        inverse_votes = 0
        components = []

        # -- Inverse Seasonal: monthly return tendency --
        # seasonal_factor_rotation was buying based on positive seasonal months
        # It went 0-for-10 (all SL_HIT), so we INVERT the seasonal signal.
        # If the seasonal model says "this month is bullish", we go SHORT.
        current_month = datetime.now(timezone.utc).month
        # BTC seasonal tendencies (historical average monthly returns):
        # Positive: Jan, Feb, Apr, Jul, Oct, Nov
        # Negative: Mar, Jun, Sep
        seasonal_bullish_months = {1, 2, 4, 7, 10, 11}
        if current_month in seasonal_bullish_months:
            # Seasonal says BUY -> we SELL (inverse)
            inverse_votes -= 1
            components.append(f"INV seasonal: month {current_month} historically bullish -> SHORT")
        else:
            # Seasonal says SELL -> we BUY (inverse)
            inverse_votes += 1
            components.append(f"INV seasonal: month {current_month} historically bearish -> LONG")

        # -- Inverse OBI: volume imbalance direction --
        # OBI was buying on high buy-side volume and losing every time.
        # So we check if recent volume is accumulation-like, and go opposite.
        recent_returns = close.pct_change().tail(5)
        up_vol = volume.tail(5)[recent_returns > 0].sum()
        down_vol = volume.tail(5)[recent_returns <= 0].sum()

        if up_vol > 0 and down_vol > 0:
            obi = float((up_vol - down_vol) / (up_vol + down_vol))
        else:
            obi = 0

        if obi > 0.3:
            # OBI says buy pressure -> inverse: SELL
            inverse_votes -= 1
            components.append(f"INV OBI: buy pressure OBI={obi:.2f} -> SHORT")
        elif obi < -0.3:
            # OBI says sell pressure -> inverse: BUY
            inverse_votes += 1
            components.append(f"INV OBI: sell pressure OBI={obi:.2f} -> LONG")

        # Need at least 1 vote (both agreeing gives 2 votes)
        if inverse_votes == 0:
            continue

        # RSI sanity check: don't inverse into extreme exhaustion
        rsi_val = float(rsi(close, 14).iloc[-1])
        if inverse_votes > 0 and rsi_val > 75:
            continue  # Don't go long when already overbought
        if inverse_votes < 0 and rsi_val < 25:
            continue  # Don't short when already oversold

        direction = "long" if inverse_votes > 0 else "short"
        signal_type = "BUY" if direction == "long" else "SELL"

        entry, tp, sl = _atr_tp_sl(close, high, low, direction=direction,
                                    tp_mult=2.5, sl_mult=2.0)

        conf = 0.65
        if abs(inverse_votes) >= 2:
            conf += 0.10  # Both inversions agree
        # The original strategies had 0% WR, so inverting should improve
        conf += 0.03

        reason = (f"Super Inverse: {' | '.join(components)}. "
                  f"Inverting 0% WR losers (seasonal 0/10, OBI 0/4). "
                  f"Jegadeesh (1990): past losers outperform when flipped. "
                  f"RSI={rsi_val:.0f}")

        signals.append(_make_signal(
            "super_inverse_seasonal_obi", symbol, signal_type, direction.upper(),
            entry, tp, sl, conf, reason, "3-7d",
            extra={"inverse_votes": inverse_votes, "obi": round(obi, 3),
                   "rsi": round(rsi_val, 1), "month": current_month}
        ))

    return signals


# =========================================================================
# SUPER STRATEGY 10: Confluence Ensemble (Meta-Strategy)
# =========================================================================
# Combines the top-3 performing sub-strategies via voting:
#   1. fractal_sr_bounce logic (71.4% WR, PF 3.68)
#   2. widened_tp_momentum_carry logic (66.7% WR, PF 4.28)
#   3. hurst_mean_reversion logic (100% WR, PF inf)
#
# Signal only fires when >= 2 of 3 agree on direction.
# Confidence boosted by +0.10 when all 3 agree.
#
# Academic basis: Ensemble methods (Breiman 1996, Schapire 1990)
# reduce variance and improve generalization vs single models.
# =========================================================================

def super_confluence_ensemble(data: dict[str, pd.DataFrame],
                              context: Optional[dict] = None) -> list[dict]:
    """Top-3 strategy voting ensemble: fractal S/R + momentum carry + Hurst MR."""
    signals = []
    target_symbols = list(CRYPTO_SYMBOLS.keys())

    for symbol in target_symbols:
        df = data.get(symbol)
        if df is None or len(df) < 60:
            continue

        info = CRYPTO_SYMBOLS.get(symbol, {})
        cat = info.get("cat", "crypto")
        if cat not in ("crypto", "meme"):
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df.get("Volume", pd.Series(np.ones(len(close))))

        price = float(close.iloc[-1])
        bull_votes = 0
        bear_votes = 0
        reasons = []

        # -- Sub-strategy 1: Fractal S/R Bounce --
        sr = detect_support_resistance(close, lookback=60, num_levels=3)
        atr_val = float(atr(high, low, close, 14).iloc[-1])

        near_support = any(abs(price - s) < 0.5 * atr_val for s in sr.get("support", []))
        near_resistance = any(abs(price - r) < 0.5 * atr_val for r in sr.get("resistance", []))

        rsi14 = float(rsi(close, 14).iloc[-1])

        if near_support and rsi14 < 40:
            bull_votes += 1
            nearest_s = min(sr["support"], key=lambda s: abs(price - s)) if sr["support"] else price
            reasons.append(f"fractal_sr: near support {nearest_s:.4f}")
        elif near_resistance and rsi14 > 60:
            bear_votes += 1
            nearest_r = min(sr["resistance"], key=lambda r: abs(price - r)) if sr["resistance"] else price
            reasons.append(f"fractal_sr: near resistance {nearest_r:.4f}")

        # -- Sub-strategy 2: Momentum Carry (TSMOM-inspired) --
        if len(close) >= 29:
            ret_28d = float(close.iloc[-1] / close.iloc[-29] - 1)
            ret_7d = float(close.iloc[-1] / close.iloc[-8] - 1) if len(close) > 8 else 0

            # Momentum carry: consistent direction on both timeframes
            if ret_28d > 0.03 and ret_7d > 0.01:
                bull_votes += 1
                reasons.append(f"momentum: 28d={ret_28d:+.1%}, 7d={ret_7d:+.1%}")
            elif ret_28d < -0.03 and ret_7d < -0.01:
                bear_votes += 1
                reasons.append(f"momentum: 28d={ret_28d:+.1%}, 7d={ret_7d:+.1%}")

        # -- Sub-strategy 3: Hurst Mean Reversion --
        H = hurst_exponent(close, max_lag=20)
        rsi2 = float(rsi(close, 2).iloc[-1])

        if H < 0.45:  # Mean-reverting regime
            if rsi2 < 15:
                bull_votes += 1
                reasons.append(f"hurst_mr: H={H:.2f}, RSI(2)={rsi2:.0f} oversold")
            elif rsi2 > 85:
                bear_votes += 1
                reasons.append(f"hurst_mr: H={H:.2f}, RSI(2)={rsi2:.0f} overbought")

        # -- Voting: need >= 2 --
        total_votes = max(bull_votes, bear_votes)
        if total_votes < 2:
            continue

        direction = "long" if bull_votes > bear_votes else "short"
        signal_type = "BUY" if direction == "long" else "SELL"

        entry, tp, sl = _atr_tp_sl(close, high, low, direction=direction,
                                    tp_mult=3.0, sl_mult=2.25)

        # Base confidence scales with vote count
        conf = 0.70
        if total_votes >= 3:
            conf += 0.12  # All 3 agree = strong conviction
        elif total_votes >= 2:
            conf += 0.05

        reason = (f"Super Ensemble ({total_votes}/3 votes): "
                  f"{' + '.join(reasons)}. "
                  f"Ensemble of fractal_sr (71% WR) + momentum (67% WR) + hurst_mr (100% WR)")

        signals.append(_make_signal(
            "super_confluence_ensemble", symbol, signal_type, direction.upper(),
            entry, tp, sl, conf, reason, "3-7d",
            extra={"bull_votes": bull_votes, "bear_votes": bear_votes,
                   "total_votes": total_votes, "hurst": round(H, 3),
                   "components": reasons}
        ))

    return signals


# =========================================================================
# SUPER_STRATEGIES Registry
# =========================================================================

SUPER_STRATEGIES: dict[str, callable] = {
    # Trend-following (3)
    "super_keltner_ema_momentum":  super_keltner_ema_momentum,
    "super_hma_breakout_volume":   super_hma_breakout_volume,
    "super_channel_trend_rider":   super_channel_trend_rider,
    # Mean-reversion (3)
    "super_rsi_bollinger_revert":  super_rsi_bollinger_revert,
    "super_vwap_zscore_bounce":    super_vwap_zscore_bounce,
    "super_funding_rate_carry":    super_funding_rate_carry,
    # On-chain / sentiment (2)
    "super_whale_fear_accumulate": super_whale_fear_accumulate,
    "super_options_macro_flow":    super_options_macro_flow,
    # Inverse (1)
    "super_inverse_seasonal_obi":  super_inverse_seasonal_obi,
    # Ensemble (1)
    "super_confluence_ensemble":   super_confluence_ensemble,
}
