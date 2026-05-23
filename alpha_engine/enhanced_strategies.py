"""
ALPHA_ENGINE -- Enhanced Strategies (Research-Driven, March 2026)
================================================================
10 strategies derived from vectorized backtest findings + quick-win research:

Strategy 130: rsi_mean_reversion_optimized  -- RSI(14) < 30 + volume + 200 EMA trend filter
              Backtest: Sharpe 1.92, 74.6% WR across all symbols.
Strategy 131: connors_rsi2_strategy         -- Classic Connors RSI(2) < 10 with 200 SMA filter
              Academic: 75.7% WR on 200+ trades, p=6e-6 (Connors & Alvarez 2009).
Strategy 132: anti_confluence_contrarian     -- Fade 3+ strategy agreement (confluence = anti-signal)
              Empirical: Multi-Agree 3.6% WR vs Solo 33.3% WR in our dataset.
Strategy 133: keltner_chop_scalper           -- Keltner band bounce in low-ADX regimes
              Addresses choppy regime hurting LONGs; ADX < 20 filter.
Strategy 134: time_filtered_momentum         -- EMA 9/21 crossover only during 03-07 UTC
              Empirical: 62% WR in 03-07 UTC window vs <40% in worst hours.
Strategy 135: star_symbol_tracker            -- Reduced thresholds for proven winners
              RENDER 14/14, FET 11/12, BNB 9/13 in backtest.
Strategy 136: fear_greed_roc_spike           -- F&G rate-of-change >= 25 pts (massive sentiment shift)
              Contrarian: extreme swings in either direction = BUY.
Strategy 137: volatility_contraction_breakout -- ATR contraction then expansion breakout
              VCE pattern: low-vol squeeze → high-vol breakout with neutral RSI.
Strategy 138: cme_gap_fill                   -- CME BTC futures gap fill (80% fill rate)
              Trade toward gap fill on BTCUSDT when gap > 0.5%.
Strategy 139: stop_hunt_reversal             -- Smart money stop hunt sweep + reversal
              Price sweeps swing high/low with volume spike, then reverses.

References:
  - Connors & Alvarez (2009): "Short-Term Trading Strategies That Work"
  - Lo & MacKinlay (1988): Mean reversion via variance ratios
  - Our vectorized backtest (March 2026): RSI MR Sharpe 1.92, confluence anti-signal
  - CME Gap Study: ~80% of BTC gaps fill within 1 week
  - Smart Money Concepts: ICT stop hunt / liquidity sweep patterns
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional

import numpy as np
try:
    from config import CRYPTO_SYMBOLS, ALL_SYMBOLS
    from indicators import rsi, sma, ema, atr, adx, bollinger_bands, volume_ratio
except ImportError:
    CRYPTO_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "DOGEUSDT", "XRPUSDT", "AVAXUSDT", "LINKUSDT"]
    ALL_SYMBOLS = CRYPTO_SYMBOLS


# ---------------------------------------------------------------------------
# Helpers (per-module convention)
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_category(symbol: str) -> str:
    info = ALL_SYMBOLS.get(symbol, {})
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


def _compute_atr(high: pd.Series, low: pd.Series, close: pd.Series,
                 period: int = 14) -> float:
    """Return the latest ATR value."""
    atr_series = atr(high, low, close, period)
    return float(atr_series.iloc[-1])


def _keltner_channel(high: pd.Series, low: pd.Series, close: pd.Series,
                     ema_period: int = 20, atr_mult: float = 1.5,
                     atr_period: int = 14) -> dict:
    """Keltner Channel: EMA +/- ATR multiplier."""
    mid = ema(close, ema_period)
    atr_val = atr(high, low, close, atr_period)
    upper = mid + atr_mult * atr_val
    lower = mid - atr_mult * atr_val
    return {"upper": upper, "mid": mid, "lower": lower}


# Star symbols -- historically proven winners from backtest
# Maps YF-style key -> binance key for reference
STAR_SYMBOLS = {
    "RNDR-USD": {"binance": "RENDERUSDT", "wr": 1.00, "record": "14/14"},
    "FET-USD":  {"binance": "FETUSDT",    "wr": 0.917, "record": "11/12"},
    "BNB-USD":  {"binance": "BNBUSDT",    "wr": 0.692, "record": "9/13"},
}


# =========================================================================
# STRATEGY 130: RSI Mean Reversion Optimized
# =========================================================================
# Our backtest winner: Sharpe 1.92, 74.6% WR.
# Enhancement: Volume > 1.5x avg + price > 200 EMA (trend filter).
# TP: 2x ATR. SL: 1.5x ATR. R:R = 1.33:1.
# =========================================================================

def rsi_mean_reversion_optimized(data: dict[str, pd.DataFrame],
                                  context: Optional[dict] = None) -> list[dict]:
    """RSI(14) < 30 mean reversion with volume and trend confirmation.

    Only buys oversold RSI when:
    1. RSI(14) < 30 (oversold)
    2. Volume > 1.5x 20-period average (institutional participation)
    3. Price above 200 EMA (uptrend filter -- don't catch falling knives)

    Backtest: Sharpe 1.92, 74.6% WR across all symbols.
    """
    signals: list[dict] = []
    min_bars = 210  # need 200 for EMA + buffer

    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < min_bars:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            volume = df["Volume"]

            # RSI(14) for oversold detection
            rsi_14 = rsi(close, 14)
            current_rsi = float(rsi_14.iloc[-1])
            if pd.isna(current_rsi) or current_rsi >= 30:
                continue

            # Volume confirmation: > 1.5x 20-period average
            vol_avg = volume.rolling(20).mean()
            current_vol_ratio = float(volume.iloc[-1] / vol_avg.iloc[-1]) \
                if float(vol_avg.iloc[-1]) > 0 else 0.0
            if current_vol_ratio < 1.5:
                continue

            # Trend filter: price above 200 EMA
            ema_200 = ema(close, 200)
            current_price = float(close.iloc[-1])
            ema_200_val = float(ema_200.iloc[-1])
            if pd.isna(ema_200_val) or current_price <= ema_200_val:
                continue

            # ATR-based TP/SL
            current_atr = _compute_atr(high, low, close)
            tp = current_price + 2.0 * current_atr
            sl = current_price - 1.5 * current_atr

            rr = (tp - current_price) / (current_price - sl) if current_price > sl else 0
            if rr < 1.0:
                continue

            # Confidence: deeper oversold = higher confidence
            base_conf = 0.55
            rsi_bonus = min(0.15, (30 - current_rsi) / 100)
            vol_bonus = min(0.10, (current_vol_ratio - 1.5) / 10)
            trend_bonus = 0.05 if current_price > ema_200_val * 1.02 else 0.0
            confidence = round(min(0.85, base_conf + rsi_bonus + vol_bonus + trend_bonus), 2)

            signals.append({
                "strategy": "rsi_mean_reversion_optimized",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": "BUY",
                "entry_price": _smart_round(current_price),
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "confidence": confidence,
                "risk_reward": round(rr, 2),
                "reason": (f"RSI(14)={current_rsi:.1f} oversold, "
                           f"Vol={current_vol_ratio:.1f}x avg, "
                           f"Price {current_price:.2f} > 200 EMA {ema_200_val:.2f}, "
                           f"ATR-based R:R={rr:.2f}"),
                "timeframe": "1d",
                "rsi_at_entry": round(current_rsi, 1),
                "atr_at_entry": round(current_atr, 4),
                "volume_ratio": round(current_vol_ratio, 2),
                "timestamp": _now_iso(),
            })

        except Exception:
            continue

    return signals


# =========================================================================
# STRATEGY 131: Connors RSI(2) Strategy
# =========================================================================
# Classic Connors RSI(2): 75.7% WR on 200+ trades (p=6e-6).
# Reference: Connors & Alvarez (2009) "Short-Term Trading Strategies That Work"
# Rules:
#   - Price > 200 SMA (trend filter)
#   - RSI(2) < 10 = BUY (extreme oversold on fast RSI)
#   - TP when RSI(2) > 70. SL: 3x ATR (wide -- let mean reversion work).
# =========================================================================

def connors_rsi2_strategy(data: dict[str, pd.DataFrame],
                           context: Optional[dict] = None) -> list[dict]:
    """Connors RSI(2) mean reversion with 200 SMA trend filter.

    Academic: 75.7% WR on 200+ trades, p-value 6e-6.
    Ultra-fast RSI(2) catches extreme 1-2 day pullbacks in uptrends.
    """
    signals: list[dict] = []
    min_bars = 210

    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < min_bars:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]

            # Trend filter: price > 200 SMA
            sma_200 = sma(close, 200)
            current_price = float(close.iloc[-1])
            sma_200_val = float(sma_200.iloc[-1])
            if pd.isna(sma_200_val) or current_price <= sma_200_val:
                continue

            # Connors RSI(2): extreme oversold < 10
            rsi_2 = rsi(close, 2)
            current_rsi2 = float(rsi_2.iloc[-1])
            if pd.isna(current_rsi2) or current_rsi2 >= 10:
                continue

            # Additional: RSI(14) should not be extremely overbought
            rsi_14_val = float(rsi(close, 14).iloc[-1])
            if rsi_14_val > 75:
                continue

            # ATR for TP/SL -- wide SL (3x ATR) since we're mean-reverting
            current_atr = _compute_atr(high, low, close)
            # TP: when RSI(2) would normally reach 70 -- approximate as 1.5x ATR
            tp = current_price + 1.5 * current_atr
            sl = current_price - 3.0 * current_atr

            rr = (tp - current_price) / (current_price - sl) if current_price > sl else 0

            # Confidence: deeper oversold RSI(2) = higher confidence
            base_conf = 0.60
            rsi_bonus = min(0.15, (10 - current_rsi2) / 50)
            trend_strength = min(0.10, (current_price / sma_200_val - 1) * 2)
            confidence = round(min(0.85, base_conf + rsi_bonus + trend_strength), 2)

            signals.append({
                "strategy": "connors_rsi2",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": "BUY",
                "entry_price": _smart_round(current_price),
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "confidence": confidence,
                "risk_reward": round(rr, 2),
                "reason": (f"Connors RSI(2)={current_rsi2:.1f} extreme oversold, "
                           f"Price {current_price:.2f} > 200 SMA {sma_200_val:.2f}, "
                           f"RSI(14)={rsi_14_val:.1f}, academic 75.7% WR"),
                "timeframe": "1d",
                "rsi_at_entry": round(current_rsi2, 1),
                "atr_at_entry": round(current_atr, 4),
                "timestamp": _now_iso(),
            })

        except Exception:
            continue

    return signals


# =========================================================================
# STRATEGY 132: Anti-Confluence Contrarian
# =========================================================================
# Our data shows confluence is an ANTI-signal:
#   Multi-Agree picks: 3.6% WR vs Solo picks: 33.3% WR.
# When 3+ strategies agree, the move is already priced in.
# This strategy detects crowded consensus via Bollinger Band width
# (tight bands = consensus/low vol) and fades the crowd.
# TP: Mean reversion to 20 EMA. SL: 2% max.
# =========================================================================

def anti_confluence_contrarian(data: dict[str, pd.DataFrame],
                                context: Optional[dict] = None) -> list[dict]:
    """Contrarian fade when indicators converge (consensus = priced in).

    Our empirical finding: when multiple strategies agree (3+ signals),
    the actual WR drops to 3.6% vs 33.3% for solo signals. This strategy
    detects consensus conditions and fades them using mean reversion.

    In choppy regimes (BB width < threshold), consensus signals are
    especially likely to fail. We buy dips that consensus is calling
    a breakdown, and vice versa.
    """
    signals: list[dict] = []
    min_bars = 50

    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < min_bars:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]

            # Detect choppy regime via Bollinger Band width
            bb = bollinger_bands(close, period=20, std_dev=2.0)
            bb_upper = bb["upper"]
            bb_lower = bb["lower"]
            bb_mid = bb["mid"]

            current_price = float(close.iloc[-1])
            bb_width = float((bb_upper.iloc[-1] - bb_lower.iloc[-1]) / bb_mid.iloc[-1])

            # Only activate in choppy/tight regime: BB width < 6%
            if bb_width > 0.06:
                continue

            # Check ADX for chop confirmation
            adx_val = float(adx(high, low, close, 14).iloc[-1])
            if pd.isna(adx_val) or adx_val > 20:
                continue  # trending -- don't fade

            # RSI for oversold/overbought detection
            rsi_14 = float(rsi(close, 14).iloc[-1])

            # In choppy regime, buy at lower BB (consensus bearish = fade it)
            if current_price <= float(bb_lower.iloc[-1]) and rsi_14 < 40:
                current_atr = _compute_atr(high, low, close)
                ema_20_val = float(ema(close, 20).iloc[-1])

                # TP: mean reversion to 20 EMA
                tp = ema_20_val
                # SL: 2% below entry (tight -- we're in chop, not trending)
                sl = current_price * 0.98

                if tp <= current_price:
                    continue

                rr = (tp - current_price) / (current_price - sl) if current_price > sl else 0

                confidence = round(min(0.75, 0.45
                                       + min(0.10, (20 - adx_val) / 100)
                                       + min(0.10, (40 - rsi_14) / 100)
                                       + min(0.10, (0.06 - bb_width) / 0.06)), 2)

                signals.append({
                    "strategy": "anti_confluence_contrarian",
                    "symbol": symbol,
                    "category": _get_category(symbol),
                    "signal_type": "BUY",
                    "entry_price": _smart_round(current_price),
                    "take_profit": _smart_round(tp),
                    "stop_loss": _smart_round(sl),
                    "confidence": confidence,
                    "risk_reward": round(rr, 2),
                    "reason": (f"Anti-confluence fade: choppy regime (ADX={adx_val:.1f}, "
                               f"BB width={bb_width:.3f}), RSI={rsi_14:.1f}, "
                               f"price at lower BB -- consensus bearish = contrarian BUY, "
                               f"TP at 20 EMA={ema_20_val:.2f}"),
                    "timeframe": "1d",
                    "rsi_at_entry": round(rsi_14, 1),
                    "adx_at_entry": round(adx_val, 1),
                    "bb_width": round(bb_width, 4),
                    "timestamp": _now_iso(),
                })

        except Exception:
            continue

    return signals


# =========================================================================
# STRATEGY 133: Keltner Chop Scalper
# =========================================================================
# For choppy regimes where breakout strategies fail.
# Keltner Channel (20, 1.5 ATR): BUY at lower band, exit at midline.
# Only active when ADX < 20 (choppy). Tight SL at 1.5% below entry.
# =========================================================================

def keltner_chop_scalper(data: dict[str, pd.DataFrame],
                          context: Optional[dict] = None) -> list[dict]:
    """Keltner Channel mean-reversion in choppy regimes.

    Breakout strategies fail in chop (ADX < 20). Instead, buy touches
    of the lower Keltner band and take profit at the midline (EMA 20).
    Tight 1.5% SL since we're range-trading.
    """
    signals: list[dict] = []
    min_bars = 50

    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < min_bars:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]

            # ADX filter: only in choppy conditions
            adx_val = float(adx(high, low, close, 14).iloc[-1])
            if pd.isna(adx_val) or adx_val >= 20:
                continue

            # Keltner Channel
            kc = _keltner_channel(high, low, close, ema_period=20,
                                  atr_mult=1.5, atr_period=14)

            current_price = float(close.iloc[-1])
            lower_band = float(kc["lower"].iloc[-1])
            mid_band = float(kc["mid"].iloc[-1])

            # BUY signal: price at or below lower Keltner band
            if current_price > lower_band:
                continue

            # RSI sanity: not extremely oversold (avoid crashes)
            rsi_14 = float(rsi(close, 14).iloc[-1])
            if rsi_14 < 20:
                continue  # too extreme -- might be a breakdown

            # TP: EMA 20 midline
            tp = mid_band
            # SL: 1.5% below entry
            sl = current_price * 0.985

            if tp <= current_price:
                continue

            rr = (tp - current_price) / (current_price - sl) if current_price > sl else 0

            current_atr = _compute_atr(high, low, close)
            confidence = round(min(0.70, 0.45
                                   + min(0.10, (20 - adx_val) / 100)
                                   + min(0.10, (lower_band - current_price) / current_price * 20)), 2)

            signals.append({
                "strategy": "keltner_chop_scalper",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": "BUY",
                "entry_price": _smart_round(current_price),
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "confidence": confidence,
                "risk_reward": round(rr, 2),
                "reason": (f"Keltner chop scalper: ADX={adx_val:.1f} (choppy), "
                           f"price {current_price:.2f} at lower band {lower_band:.2f}, "
                           f"RSI={rsi_14:.1f}, TP at midline {mid_band:.2f}"),
                "timeframe": "1d",
                "rsi_at_entry": round(rsi_14, 1),
                "adx_at_entry": round(adx_val, 1),
                "atr_at_entry": round(current_atr, 4),
                "timestamp": _now_iso(),
            })

        except Exception:
            continue

    return signals


# =========================================================================
# STRATEGY 134: Time-Filtered Momentum
# =========================================================================
# Exploit the 03-07 UTC edge (62% WR empirically observed).
# Only generate signals during 03-07 UTC window.
# EMA 9/21 crossover as entry, extended hold (duration edge).
# =========================================================================

def time_filtered_momentum(data: dict[str, pd.DataFrame],
                            context: Optional[dict] = None) -> list[dict]:
    """EMA 9/21 crossover restricted to 03-07 UTC (62% WR window).

    Our data shows 03-07 UTC has 62% WR vs <40% in worst hours.
    Asian/early-EU session has less noise and more follow-through.
    Extended hold target (min 24h equivalent) to capture duration edge.
    """
    signals: list[dict] = []

    # Time gate: only run during 03-07 UTC
    now_utc = datetime.now(timezone.utc)
    current_hour = now_utc.hour
    if current_hour < 3 or current_hour > 7:
        return signals  # Outside optimal window

    min_bars = 50

    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < min_bars:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]

            # EMA 9/21 crossover
            ema_9 = ema(close, 9)
            ema_21 = ema(close, 21)

            current_ema9 = float(ema_9.iloc[-1])
            current_ema21 = float(ema_21.iloc[-1])
            prev_ema9 = float(ema_9.iloc[-2])
            prev_ema21 = float(ema_21.iloc[-2])

            # Bullish crossover: EMA9 crosses above EMA21
            if not (prev_ema9 <= prev_ema21 and current_ema9 > current_ema21):
                continue

            current_price = float(close.iloc[-1])

            # Volume check: above average
            volume = df["Volume"]
            vol_avg = float(volume.rolling(20).mean().iloc[-1])
            current_vol_ratio = float(volume.iloc[-1] / vol_avg) if vol_avg > 0 else 0.0
            if current_vol_ratio < 1.0:
                continue

            # Extended hold TP: 3x ATR (captures the duration edge for >3 day holds)
            current_atr = _compute_atr(high, low, close)
            tp = current_price + 3.0 * current_atr
            sl = current_price - 2.0 * current_atr

            rr = (tp - current_price) / (current_price - sl) if current_price > sl else 0
            if rr < 1.0:
                continue

            rsi_14 = float(rsi(close, 14).iloc[-1])

            confidence = round(min(0.75, 0.50
                                   + min(0.10, (current_ema9 / current_ema21 - 1) * 10)
                                   + min(0.05, (current_vol_ratio - 1.0) / 5)
                                   + 0.05), 2)  # +0.05 time window bonus

            signals.append({
                "strategy": "time_filtered_momentum",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": "BUY",
                "entry_price": _smart_round(current_price),
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "confidence": confidence,
                "risk_reward": round(rr, 2),
                "reason": (f"Time-filtered momentum: EMA9/21 bullish crossover "
                           f"during 03-07 UTC (hour={current_hour}), "
                           f"Vol={current_vol_ratio:.1f}x, RSI={rsi_14:.1f}, "
                           f"extended hold target 3x ATR"),
                "timeframe": "1d",
                "rsi_at_entry": round(rsi_14, 1),
                "atr_at_entry": round(current_atr, 4),
                "volume_ratio": round(current_vol_ratio, 2),
                "utc_hour": current_hour,
                "timestamp": _now_iso(),
            })

        except Exception:
            continue

    return signals


# =========================================================================
# STRATEGY 135: Star Symbol Tracker
# =========================================================================
# Focus on historically proven symbols:
#   RENDER (14/14 = 100% WR), FET (11/12 = 91.7%), BNB (9/13 = 69.2%)
# Lower entry threshold for these + RSI pullback timing.
# Tighter stops since these have positive expectancy.
# =========================================================================

def star_symbol_tracker(data: dict[str, pd.DataFrame],
                         context: Optional[dict] = None) -> list[dict]:
    """Preferential treatment for historically proven winners.

    RENDER, FET, BNB have the best backtest records. This strategy
    uses relaxed RSI thresholds (< 45 vs typical < 30) to catch
    more pullback entries, with tighter stops since these symbols
    have demonstrated positive expectancy.
    """
    signals: list[dict] = []
    min_bars = 60

    for yf_symbol, star_info in STAR_SYMBOLS.items():
        df = data.get(yf_symbol)
        if df is None or len(df) < min_bars:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            volume = df["Volume"]

            current_price = float(close.iloc[-1])

            # RSI pullback: relaxed threshold (< 45 for star symbols)
            rsi_14 = float(rsi(close, 14).iloc[-1])
            if pd.isna(rsi_14) or rsi_14 >= 45:
                continue

            # Must be in uptrend: price > 50 EMA
            ema_50 = ema(close, 50)
            ema_50_val = float(ema_50.iloc[-1])
            if current_price <= ema_50_val:
                continue

            # Volume: at least average
            vol_avg = float(volume.rolling(20).mean().iloc[-1])
            current_vol_ratio = float(volume.iloc[-1] / vol_avg) if vol_avg > 0 else 0.0

            # ATR-based TP/SL -- tighter for proven winners
            current_atr = _compute_atr(high, low, close)
            tp = current_price + 2.5 * current_atr  # wider TP -- let winners run
            sl = current_price - 1.2 * current_atr   # tighter SL -- positive EV

            rr = (tp - current_price) / (current_price - sl) if current_price > sl else 0
            if rr < 1.5:
                continue

            # Higher base confidence for star symbols
            base_conf = 0.55 + star_info["wr"] * 0.15  # up to 0.70 base
            rsi_bonus = min(0.10, (45 - rsi_14) / 100)
            vol_bonus = min(0.05, max(0, (current_vol_ratio - 1.0)) / 10)
            confidence = round(min(0.85, base_conf + rsi_bonus + vol_bonus), 2)

            signals.append({
                "strategy": "star_symbol_tracker",
                "symbol": yf_symbol,
                "category": _get_category(yf_symbol),
                "signal_type": "BUY",
                "entry_price": _smart_round(current_price),
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "confidence": confidence,
                "risk_reward": round(rr, 2),
                "reason": (f"Star symbol {yf_symbol} ({star_info['record']} backtest), "
                           f"RSI pullback={rsi_14:.1f}, above 50 EMA, "
                           f"Vol={current_vol_ratio:.1f}x, "
                           f"tighter SL for positive-EV symbol"),
                "timeframe": "1d",
                "rsi_at_entry": round(rsi_14, 1),
                "atr_at_entry": round(current_atr, 4),
                "volume_ratio": round(current_vol_ratio, 2),
                "star_wr": star_info["wr"],
                "star_record": star_info["record"],
                "timestamp": _now_iso(),
            })

        except Exception:
            continue

    return signals


# =========================================================================
# STRATEGY 136: Fear & Greed Rate-of-Change Spike
# =========================================================================
# The current system uses absolute F&G level. This strategy triggers on
# RATE OF CHANGE: a jump or drop of >= 25 points in a single day signals
# a massive sentiment shift. Both directions are contrarian BUY signals
# (extreme fear = buy the panic, extreme greed spike = momentum ignition).
# TP: 2x ATR. SL: 1.5x ATR. Hold 7 days minimum.
# =========================================================================

def fear_greed_roc_spike(data: dict[str, pd.DataFrame],
                          context: Optional[dict] = None) -> list[dict]:
    """Fear & Greed Index rate-of-change spike detector.

    Fetches 7-day F&G history from alternative.me (free, no auth).
    If abs(today - yesterday) >= 25 points, generate BUY signals on
    all crypto symbols. Both panic drops and euphoria spikes are
    contrarian entry points when the CHANGE is extreme.
    """
    signals: list[dict] = []

    # Fetch F&G data
    try:
        url = "https://api.alternative.me/fng/?limit=7"
        req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            fng_data = json.loads(resp.read())
        fng_list = fng_data.get("data", [])
        if len(fng_list) < 2:
            return signals
        # data[0] = today, data[1] = yesterday (newest first)
        today_fng = int(fng_list[0]["value"])
        yesterday_fng = int(fng_list[1]["value"])
    except Exception:
        return signals

    fng_roc = today_fng - yesterday_fng  # positive = greed spike, negative = fear spike
    abs_roc = abs(fng_roc)

    if abs_roc < 25:
        return signals  # Not extreme enough

    min_bars = 30

    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < min_bars:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]

            current_price = float(close.iloc[-1])
            current_atr = _compute_atr(high, low, close)

            # TP: 2x ATR, SL: 1.5x ATR
            tp = current_price + 2.0 * current_atr
            sl = current_price - 1.5 * current_atr

            rr = (tp - current_price) / (current_price - sl) if current_price > sl else 0
            if rr < 1.0:
                continue

            # Confidence: higher for bigger swings, slight bonus for fear (contrarian edge)
            base_conf = 0.50
            roc_bonus = min(0.15, (abs_roc - 25) / 100)
            fear_bonus = 0.05 if fng_roc < 0 else 0.0  # fear drops = stronger contrarian signal
            confidence = round(min(0.80, base_conf + roc_bonus + fear_bonus), 2)

            direction_label = "fear spike" if fng_roc < 0 else "greed spike"

            signals.append({
                "strategy": "fear_greed_roc_spike",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": "BUY",
                "entry_price": _smart_round(current_price),
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "confidence": confidence,
                "risk_reward": round(rr, 2),
                "reason": (f"F&G RoC {direction_label}: {yesterday_fng} -> {today_fng} "
                           f"(delta={fng_roc:+d}), massive sentiment shift = contrarian BUY, "
                           f"hold 7d min, ATR-based R:R={rr:.2f}"),
                "timeframe": "1d",
                "fng_today": today_fng,
                "fng_yesterday": yesterday_fng,
                "fng_roc": fng_roc,
                "atr_at_entry": round(current_atr, 4),
                "min_hold_days": 7,
                "timestamp": _now_iso(),
            })

        except Exception:
            continue

    return signals


# =========================================================================
# STRATEGY 137: Volatility Contraction-Expansion (VCE) Breakout
# =========================================================================
# ATR(14) / SMA(ATR(14), 20) < 0.7 = volatility contraction.
# When price breaks 10-bar high with volume > 1.5x avg AND RSI 40-60
# (neutral momentum = fresh breakout, not exhaustion): BUY.
# TP: range * 1.5. SL: range * 0.5.
# =========================================================================

def volatility_contraction_breakout(data: dict[str, pd.DataFrame],
                                      context: Optional[dict] = None) -> list[dict]:
    """Volatility contraction then expansion breakout.

    Identifies periods where ATR contracts (< 0.7x its 20-period average),
    then triggers on a breakout above 10-bar high with volume confirmation
    and neutral RSI (40-60), indicating a fresh move rather than exhaustion.
    """
    signals: list[dict] = []
    min_bars = 50

    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < min_bars:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            volume = df["Volume"]

            # Compute ATR(14) and its 20-period SMA
            atr_series = atr(high, low, close, 14)
            atr_sma_20 = sma(atr_series, 20)

            current_atr = float(atr_series.iloc[-1])
            current_atr_sma = float(atr_sma_20.iloc[-1])

            if pd.isna(current_atr_sma) or current_atr_sma == 0:
                continue

            atr_ratio = current_atr / current_atr_sma

            # Contraction detection: ATR ratio < 0.7
            if atr_ratio >= 0.7:
                continue

            current_price = float(close.iloc[-1])

            # Breakout: price breaks 10-bar high
            high_10 = float(high.iloc[-11:-1].max())  # 10 bars before current
            if current_price <= high_10:
                continue

            # Volume confirmation: > 1.5x 20-period average
            vol_avg = float(volume.rolling(20).mean().iloc[-1])
            current_vol_ratio = float(volume.iloc[-1] / vol_avg) if vol_avg > 0 else 0.0
            if current_vol_ratio < 1.5:
                continue

            # RSI filter: must be neutral (40-60) -- fresh breakout, not exhaustion
            rsi_14 = float(rsi(close, 14).iloc[-1])
            if pd.isna(rsi_14) or rsi_14 < 40 or rsi_14 > 60:
                continue

            # TP/SL based on the 10-bar range
            low_10 = float(low.iloc[-11:-1].min())
            range_10 = high_10 - low_10
            if range_10 <= 0:
                continue

            tp = current_price + range_10 * 1.5
            sl = current_price - range_10 * 0.5

            rr = (tp - current_price) / (current_price - sl) if current_price > sl else 0
            if rr < 1.0:
                continue

            # Confidence: tighter contraction + stronger volume = higher confidence
            base_conf = 0.50
            contraction_bonus = min(0.15, (0.7 - atr_ratio) / 0.7 * 0.15)
            vol_bonus = min(0.10, (current_vol_ratio - 1.5) / 5)
            confidence = round(min(0.80, base_conf + contraction_bonus + vol_bonus), 2)

            signals.append({
                "strategy": "volatility_contraction_breakout",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": "BUY",
                "entry_price": _smart_round(current_price),
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "confidence": confidence,
                "risk_reward": round(rr, 2),
                "reason": (f"VCE breakout: ATR ratio={atr_ratio:.2f} (contraction), "
                           f"broke 10-bar high {high_10:.2f}, "
                           f"Vol={current_vol_ratio:.1f}x, RSI={rsi_14:.1f} (neutral), "
                           f"range={range_10:.2f}, R:R={rr:.2f}"),
                "timeframe": "1d",
                "rsi_at_entry": round(rsi_14, 1),
                "atr_ratio": round(atr_ratio, 3),
                "atr_at_entry": round(current_atr, 4),
                "volume_ratio": round(current_vol_ratio, 2),
                "range_10bar": round(range_10, 4),
                "timestamp": _now_iso(),
            })

        except Exception:
            continue

    return signals


# =========================================================================
# STRATEGY 138: CME Gap Fill
# =========================================================================
# CME BTC futures close Friday ~21:00 UTC, reopen Sunday ~22:00 UTC.
# Gap = Monday open vs Friday close (Binance BTC price as proxy).
# If gap > 0.5%, trade toward gap fill direction.
# 80% of gaps fill within 1 week historically.
# TP: gap fill level. SL: 3% from entry. Only BTCUSDT.
# =========================================================================

def cme_gap_fill(data: dict[str, pd.DataFrame],
                  context: Optional[dict] = None) -> list[dict]:
    """CME BTC futures gap fill strategy.

    CME closes Friday 21:00 UTC, reopens Sunday 22:00 UTC. The gap between
    Friday's close and Sunday/Monday's open fills ~80% of the time within
    1 week. Uses Binance BTCUSDT daily data as proxy.

    Only runs on Monday/Sunday (day 0/6) to detect fresh gaps.
    Only trades BTCUSDT (BTC-USD in our symbol convention).
    """
    signals: list[dict] = []

    # Only check for gaps on Sunday (6) or Monday (0)
    now_utc = datetime.now(timezone.utc)
    if now_utc.weekday() not in (0, 6):
        return signals

    btc_symbol = "BTC-USD"
    df = data.get(btc_symbol)
    if df is None or len(df) < 10:
        return signals

    try:
        close = df["Close"]
        high = df["High"]
        low = df["Low"]

        current_price = float(close.iloc[-1])
        friday_close = float(close.iloc[-2])  # previous bar = Friday for Monday data

        # Calculate gap percentage
        gap_pct = (current_price - friday_close) / friday_close * 100

        if abs(gap_pct) < 0.5:
            return signals  # Gap too small

        current_atr = _compute_atr(high, low, close)

        if gap_pct > 0:
            # Price gapped UP -- gap fill means price should come DOWN
            # But we only do BUY signals, so skip gap-up
            # Actually: gap fill = price returns to friday_close
            # If gap_pct > 0: gap fill target is below current price (SHORT direction)
            # We trade the opposite: if gap_pct < 0, gap fill = price goes UP (BUY)
            return signals
        else:
            # Price gapped DOWN -- gap fill means price should go UP = BUY
            tp = friday_close  # gap fill target
            sl = current_price * 0.97  # 3% stop loss

            rr = (tp - current_price) / (current_price - sl) if current_price > sl else 0
            if rr < 0.5:
                return signals

            # Confidence: larger gaps are rarer but still fill ~80%
            base_conf = 0.55
            gap_bonus = min(0.15, abs(gap_pct) / 10)
            confidence = round(min(0.80, base_conf + gap_bonus), 2)

            signals.append({
                "strategy": "cme_gap_fill",
                "symbol": btc_symbol,
                "category": "crypto",
                "signal_type": "BUY",
                "entry_price": _smart_round(current_price),
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "confidence": confidence,
                "risk_reward": round(rr, 2),
                "reason": (f"CME gap fill: Friday close={friday_close:.2f}, "
                           f"current={current_price:.2f}, gap={gap_pct:+.2f}%, "
                           f"~80% of gaps fill within 1 week, "
                           f"TP at gap fill={friday_close:.2f}, SL=3%"),
                "timeframe": "1d",
                "friday_close": round(friday_close, 2),
                "gap_pct": round(gap_pct, 2),
                "atr_at_entry": round(current_atr, 4),
                "timestamp": _now_iso(),
            })

    except Exception:
        pass

    return signals


# =========================================================================
# STRATEGY 139: Stop Hunt Reversal (Smart Money)
# =========================================================================
# Smart money sweeps liquidity beyond swing highs/lows, then reverses.
# Steps:
#   1. Identify swing high/low (10-bar lookback)
#   2. Price sweeps 0.1-0.5% beyond the swing level
#   3. Volume spike > 2x average during sweep
#   4. Price reverses back inside the range within 2 candles
#   5. Enter in reversal direction
# SL: beyond the sweep wick. TP: opposite swing level.
# =========================================================================

def stop_hunt_reversal(data: dict[str, pd.DataFrame],
                        context: Optional[dict] = None) -> list[dict]:
    """Stop hunt / liquidity sweep reversal strategy.

    Detects when smart money sweeps stops beyond swing highs/lows,
    triggering a cascade of stop losses, then reverses. Classic
    ICT/Smart Money Concepts pattern.

    Looks for:
    - Recent swing low (10-bar lookback)
    - Price swept 0.1-0.5% below the swing low (stop hunt)
    - Volume spike > 2x average during the sweep
    - Price reversed back above swing low (reversal confirmed)
    """
    signals: list[dict] = []
    min_bars = 30
    lookback = 10

    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < min_bars:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            volume = df["Volume"]

            current_price = float(close.iloc[-1])
            current_low = float(low.iloc[-1])
            current_high = float(high.iloc[-1])
            prev_close = float(close.iloc[-2])

            # Volume spike check: current or previous bar > 2x average
            vol_avg = float(volume.rolling(20).mean().iloc[-1])
            recent_vol = max(float(volume.iloc[-1]), float(volume.iloc[-2]))
            vol_ratio = recent_vol / vol_avg if vol_avg > 0 else 0.0
            if vol_ratio < 2.0:
                continue

            # --- Bullish stop hunt (sweep below swing low, then reverse up) ---
            # Find swing low in lookback window (excluding last 2 bars)
            swing_window_low = low.iloc[-(lookback + 2):-2]
            swing_low = float(swing_window_low.min())
            swing_low_idx = swing_window_low.idxmin()

            # Find swing high for TP target
            swing_window_high = high.iloc[-(lookback + 2):-2]
            swing_high = float(swing_window_high.max())

            # Check if recent candles swept below swing low
            recent_low = float(low.iloc[-2:].min())  # last 2 bars
            sweep_depth_pct = (swing_low - recent_low) / swing_low * 100 if swing_low > 0 else 0

            # Sweep must be 0.1-0.5% beyond swing low
            if 0.1 <= sweep_depth_pct <= 0.5:
                # Reversal confirmation: current close back above swing low
                if current_price > swing_low:
                    tp = swing_high  # TP at opposite swing level
                    sl = recent_low * 0.998  # SL just beyond the sweep wick

                    if tp <= current_price or sl >= current_price:
                        continue

                    rr = (tp - current_price) / (current_price - sl) if current_price > sl else 0
                    if rr < 1.0:
                        continue

                    base_conf = 0.50
                    vol_bonus = min(0.15, (vol_ratio - 2.0) / 10)
                    reversal_bonus = min(0.10, (current_price - swing_low) / swing_low * 50)
                    confidence = round(min(0.80, base_conf + vol_bonus + reversal_bonus), 2)

                    signals.append({
                        "strategy": "stop_hunt_reversal",
                        "symbol": symbol,
                        "category": _get_category(symbol),
                        "signal_type": "BUY",
                        "entry_price": _smart_round(current_price),
                        "take_profit": _smart_round(tp),
                        "stop_loss": _smart_round(sl),
                        "confidence": confidence,
                        "risk_reward": round(rr, 2),
                        "reason": (f"Stop hunt reversal: swept {sweep_depth_pct:.2f}% "
                                   f"below swing low {swing_low:.4f}, "
                                   f"Vol spike={vol_ratio:.1f}x, "
                                   f"reversed back above -- smart money accumulation, "
                                   f"TP at swing high {swing_high:.4f}"),
                        "timeframe": "1d",
                        "swing_low": _smart_round(swing_low),
                        "swing_high": _smart_round(swing_high),
                        "sweep_depth_pct": round(sweep_depth_pct, 2),
                        "volume_ratio": round(vol_ratio, 2),
                        "timestamp": _now_iso(),
                    })

        except Exception:
            continue

    return signals


# =========================================================================
# Consecutive Loss Cooldown Filter
# =========================================================================

def should_skip_due_to_losses(symbol: str, strategy: str,
                               closed_picks: list[dict],
                               max_consecutive: int = 2) -> bool:
    """Return True if strategy has hit max consecutive losses on this symbol.

    Scans closed_picks (newest first) for the given symbol+strategy pair.
    If the last `max_consecutive` trades were all losses, returns True
    to skip generating new signals until a win resets the streak.

    Args:
        symbol: Trading pair (e.g., "BTC-USD")
        strategy: Strategy name (e.g., "fear_greed_roc_spike")
        closed_picks: List of closed pick dicts with at least
                      'symbol', 'strategy', and 'result' keys.
                      'result' should be 'win' or 'loss'.
        max_consecutive: Max consecutive losses before cooldown (default 2).

    Returns:
        True if should skip (on cooldown), False if OK to trade.
    """
    if not closed_picks or max_consecutive < 1:
        return False

    # Filter to matching symbol + strategy, sorted newest first
    matching = [
        p for p in closed_picks
        if p.get("symbol") == symbol and p.get("strategy") == strategy
    ]

    if len(matching) < max_consecutive:
        return False

    # Check if the last N trades were all losses
    recent = matching[:max_consecutive]
    return all(p.get("result") == "loss" for p in recent)


# =========================================================================
# Registry
# =========================================================================

ENHANCED_STRATEGIES: dict[str, callable] = {
    "rsi_mean_reversion_optimized": rsi_mean_reversion_optimized,
    "connors_rsi2":                 connors_rsi2_strategy,
    "anti_confluence_contrarian":   anti_confluence_contrarian,
    "keltner_chop_scalper":         keltner_chop_scalper,
    "time_filtered_momentum":       time_filtered_momentum,
    "star_symbol_tracker":          star_symbol_tracker,
    "fear_greed_roc_spike":         fear_greed_roc_spike,
    "volatility_contraction_breakout": volatility_contraction_breakout,
    "cme_gap_fill":                 cme_gap_fill,
    "stop_hunt_reversal":           stop_hunt_reversal,
}


# =========================================================================
# Self-test: fetch live BTCUSDT data and run all 6 strategies
# =========================================================================

if __name__ == "__main__":
    import sys
    import os

    # Ensure alpha_engine is on path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    print("=" * 70)
    print("ENHANCED STRATEGIES -- Live Test (BTCUSDT)")
    print("=" * 70)

    # Fetch live klines from Binance
    test_symbols = ["BTC-USD", "RNDR-USD", "FET-USD", "BNB-USD"]
    data: dict[str, pd.DataFrame] = {}

    for sym in test_symbols:
        sym_info = CRYPTO_SYMBOLS.get(sym, {})
        binance_sym = sym_info.get("binance", sym.replace("-USD", "USDT"))
        url = f"https://api.binance.com/api/v3/klines?symbol={binance_sym}&interval=1d&limit=250"
        print(f"\nFetching {binance_sym} ({sym})...")

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = json.loads(resp.read())

            if not raw:
                # Try Bybit fallback
                bybit_url = (f"https://api.bybit.com/v5/market/kline"
                             f"?category=spot&symbol={binance_sym}&interval=D&limit=250")
                req2 = urllib.request.Request(bybit_url, headers={"User-Agent": "AlphaEngine/1.0"})
                with urllib.request.urlopen(req2, timeout=15) as resp2:
                    bybit_data = json.loads(resp2.read())
                rows = bybit_data.get("result", {}).get("list", [])
                # Bybit format: [timestamp, open, high, low, close, volume, turnover]
                rows = sorted(rows, key=lambda x: int(x[0]))
                df = pd.DataFrame(rows, columns=["ts", "Open", "High", "Low", "Close", "Volume", "Turnover"])
                for col in ["Open", "High", "Low", "Close", "Volume"]:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                data[sym] = df
                print(f"  -> {len(df)} bars from Bybit")
                continue

            # Binance klines: [open_time, open, high, low, close, volume, ...]
            df = pd.DataFrame(raw, columns=[
                "open_time", "Open", "High", "Low", "Close", "Volume",
                "close_time", "quote_vol", "trades", "taker_buy_base",
                "taker_buy_quote", "ignore"
            ])
            for col in ["Open", "High", "Low", "Close", "Volume"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            data[sym] = df
            print(f"  -> {len(df)} bars from Binance")

        except Exception as e:
            print(f"  -> FAILED: {e}")
            # Try Bybit as fallback
            try:
                bybit_url = (f"https://api.bybit.com/v5/market/kline"
                             f"?category=spot&symbol={binance_sym}&interval=D&limit=250")
                req2 = urllib.request.Request(bybit_url, headers={"User-Agent": "AlphaEngine/1.0"})
                with urllib.request.urlopen(req2, timeout=15) as resp2:
                    bybit_data = json.loads(resp2.read())
                rows = bybit_data.get("result", {}).get("list", [])
                rows = sorted(rows, key=lambda x: int(x[0]))
                df = pd.DataFrame(rows, columns=["ts", "Open", "High", "Low", "Close", "Volume", "Turnover"])
                for col in ["Open", "High", "Low", "Close", "Volume"]:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                data[sym] = df
                print(f"  -> {len(df)} bars from Bybit (fallback)")
            except Exception as e2:
                print(f"  -> Bybit fallback also failed: {e2}")

    if not data:
        print("\nERROR: Could not fetch any data. Exiting.")
        sys.exit(1)

    print(f"\nLoaded data for: {list(data.keys())}")
    print(f"Current UTC hour: {datetime.now(timezone.utc).hour}")
    print()

    total_signals = 0
    for name, func in ENHANCED_STRATEGIES.items():
        print(f"--- {name} ---")
        try:
            sigs = func(data)
            if sigs:
                for s in sigs:
                    print(f"  {s['signal_type']} {s['symbol']} @ {s['entry_price']}"
                          f" | TP={s['take_profit']} SL={s['stop_loss']}"
                          f" | Conf={s['confidence']} R:R={s['risk_reward']}")
                    print(f"    {s['reason']}")
                total_signals += len(sigs)
            else:
                print("  No signals (conditions not met)")
        except Exception as e:
            print(f"  ERROR: {e}")

    print(f"\n{'=' * 70}")
    print(f"Total signals across all {len(ENHANCED_STRATEGIES)} strategies: {total_signals}")
    print(f"Strategies loaded: {len(ENHANCED_STRATEGIES)}")
    print(f"{'=' * 70}")
