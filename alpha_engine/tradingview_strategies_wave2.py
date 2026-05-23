"""
ALPHA_ENGINE -- TradingView Research Strategies Wave 2
======================================================
Advanced confirmation-based strategies from TradingView research.

Strategies:
  1. qqe_mod              -- QQE MOD (Mihkel00): dual QQE + Bollinger Band triple confirmation
                            Dramatically reduces false signals vs single-RSI approaches
  2. ttm_squeeze          -- TTM Squeeze (John Carter/LazyBear): BB inside Keltner Channel
                            Predicts breakouts BEFORE they happen via volatility compression
  3. stochastic_momentum_index -- SMI (Ergodic): refined stochastic, better than StochRSI
                            57% WR, 1.8 PF, 20% better risk/reward than MACD
  4. smc_confluence_score -- Smart Money Confluence: weighted composite score
                            Unifies OB + FVG + BOS + volume into 0-100 institutional score

References:
  - QQE MOD: Mihkel00 TradingView, RSI(6) + EMA(5) + ATR bands + BB filter
  - TTM Squeeze: John Carter, Bollinger(20,2) vs Keltner(20,1.5)
  - SMI: William Blau, midpoint distance stochastic
  - SMC Confluence: PhenLabs SMFI weighting (25-20-20-20-15)
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd

from config import CRYPTO_SYMBOLS, BINANCE_BASE, COINGECKO_BASE
from indicators import rsi, ema, sma, atr, bollinger_bands, volume_ratio, macd, adx


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


def _atr_tp_sl(close: pd.Series, high: pd.Series, low: pd.Series,
               tp_mult: float = 3.0, sl_mult: float = 2.25,
               atr_period: int = 14) -> tuple[float, float, float]:
    """Compute entry price, take-profit, and stop-loss from ATR."""
    atr_val = atr(high, low, close, atr_period)
    current_atr = float(atr_val.iloc[-1])
    price = float(close.iloc[-1])
    tp = price + tp_mult * current_atr
    sl = price - sl_mult * current_atr
    return _smart_round(price), _smart_round(tp), _smart_round(sl)


def _fetch_json(url: str, timeout: int = 8):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ALPHA_ENGINE/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


# =========================================================================
# 1. QQE MOD -- Mihkel00 TradingView
#    Dual QQE (RSI-6 Wilders + QQE factor 4.236 primary, 1.61 secondary)
#    plus Bollinger Band filter on RSI. Triple confirmation = high quality.
# =========================================================================

def qqe_mod(data: dict[str, pd.DataFrame],
            context: Optional[dict] = None) -> list[dict]:
    """
    QQE MOD: dual QQE + Bollinger Band triple confirmation.
    BUY: primary trend == 1 AND rsi_smooth > bb_upper AND secondary cross up.
    SELL: primary trend == -1 AND rsi_smooth < bb_lower AND secondary cross down.
    Requires 100+ bars.
    """
    signals: list[dict] = []
    QQE_FACTOR_PRIMARY = 4.236
    QQE_FACTOR_SECONDARY = 1.61
    RSI_PERIOD = 6
    RSI_SMOOTH_PERIOD = 5
    WILDERS_PERIOD = 27
    BB_RSI_PERIOD = 50
    BB_DEV_MULT = 0.35

    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 120:
            continue

        close = df["Close"]
        high, low = df["High"], df["Low"]
        vol = df.get("Volume")

        # --- Primary QQE ---
        rsi_val = rsi(close, RSI_PERIOD)
        rsi_smooth = ema(rsi_val, RSI_SMOOTH_PERIOD)

        # ATR of RSI (Wilders smoothing)
        rsi_diff = (rsi_smooth - rsi_smooth.shift(1)).abs()
        atr_rsi = ema(rsi_diff, WILDERS_PERIOD)
        dar_primary = atr_rsi * QQE_FACTOR_PRIMARY

        # Build dynamic bands with ratchet logic
        longband = rsi_smooth - dar_primary
        shortband = rsi_smooth + dar_primary

        # Ratchet bands iteratively
        longband_arr = longband.values.copy()
        shortband_arr = shortband.values.copy()
        rsi_smooth_arr = rsi_smooth.values.copy()
        trend_arr = np.zeros(len(close), dtype=int)

        for i in range(1, len(close)):
            # Ratchet longband up
            if rsi_smooth_arr[i] > longband_arr[i - 1]:
                longband_arr[i] = max(longband_arr[i], longband_arr[i - 1])
            # Ratchet shortband down
            if rsi_smooth_arr[i] < shortband_arr[i - 1]:
                shortband_arr[i] = min(shortband_arr[i], shortband_arr[i - 1])

            # Determine trend
            if rsi_smooth_arr[i] > shortband_arr[i - 1]:
                trend_arr[i] = 1
            elif rsi_smooth_arr[i] < longband_arr[i - 1]:
                trend_arr[i] = -1
            else:
                trend_arr[i] = trend_arr[i - 1]

        # --- Bollinger Band filter on RSI ---
        bb_rsi = rsi(close, RSI_PERIOD)
        bb_basis = sma(bb_rsi, BB_RSI_PERIOD)
        bb_std = bb_rsi.rolling(BB_RSI_PERIOD).std()
        bb_upper = bb_basis + BB_DEV_MULT * bb_std
        bb_lower = bb_basis - BB_DEV_MULT * bb_std

        # --- Secondary QQE (factor 1.61) ---
        dar_secondary = atr_rsi * QQE_FACTOR_SECONDARY
        longband2 = rsi_smooth - dar_secondary
        shortband2 = rsi_smooth + dar_secondary

        longband2_arr = longband2.values.copy()
        shortband2_arr = shortband2.values.copy()
        trend2_arr = np.zeros(len(close), dtype=int)

        for i in range(1, len(close)):
            if rsi_smooth_arr[i] > longband2_arr[i - 1]:
                longband2_arr[i] = max(longband2_arr[i], longband2_arr[i - 1])
            if rsi_smooth_arr[i] < shortband2_arr[i - 1]:
                shortband2_arr[i] = min(shortband2_arr[i], shortband2_arr[i - 1])

            if rsi_smooth_arr[i] > shortband2_arr[i - 1]:
                trend2_arr[i] = 1
            elif rsi_smooth_arr[i] < longband2_arr[i - 1]:
                trend2_arr[i] = -1
            else:
                trend2_arr[i] = trend2_arr[i - 1]

        # --- Generate signals on latest bar ---
        idx = len(close) - 1
        if idx < 2:
            continue

        cur_trend = trend_arr[idx]
        cur_rsi_smooth = rsi_smooth_arr[idx]
        cur_bb_upper = float(bb_upper.iloc[idx]) if not np.isnan(bb_upper.iloc[idx]) else 999
        cur_bb_lower = float(bb_lower.iloc[idx]) if not np.isnan(bb_lower.iloc[idx]) else -999

        # Secondary cross detection
        sec_cross_up = trend2_arr[idx] == 1 and trend2_arr[idx - 1] != 1
        sec_cross_down = trend2_arr[idx] == -1 and trend2_arr[idx - 1] != -1

        price_val = float(close.iloc[-1])
        atr_val = float(atr(high, low, close, 14).iloc[-1])
        vol_r = float(volume_ratio(vol).iloc[-1]) if vol is not None and len(vol) > 20 else 1.0

        # Count how many confirmations are strong
        buy_confirms = 0
        sell_confirms = 0

        if cur_trend == 1:
            buy_confirms += 1
        if cur_rsi_smooth > cur_bb_upper:
            buy_confirms += 1
        if sec_cross_up:
            buy_confirms += 1

        if cur_trend == -1:
            sell_confirms += 1
        if cur_rsi_smooth < cur_bb_lower:
            sell_confirms += 1
        if sec_cross_down:
            sell_confirms += 1

        # BUY: all three must align
        if buy_confirms == 3:
            tp = price_val + 3.0 * atr_val
            sl = price_val - 2.25 * atr_val
            rr = (tp - price_val) / (price_val - sl) if price_val > sl else 0
            if rr < 1.0:
                continue
            confidence = round(min(0.85, 0.55 + 0.10 * buy_confirms), 2)
            signals.append({
                "strategy": "qqe_mod",
                "symbol": symbol,
                "direction": "BUY",
                "entry": _smart_round(price_val),
                "tp": _smart_round(tp),
                "sl": _smart_round(sl),
                "confidence": confidence,
                "rationale": (
                    f"QQE MOD triple confirm: primary trend UP, "
                    f"RSI smooth {cur_rsi_smooth:.1f} > BB upper {cur_bb_upper:.1f}, "
                    f"secondary cross UP"
                ),
                "category": _get_category(symbol),
                "timestamp": _now_iso(),
                "tags": ["qqe", "triple_confirm", "tradingview"],
                "signal_type": "BUY",
                "entry_price": _smart_round(price_val),
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "risk_reward": round(rr, 2),
                "reason": f"QQE MOD: trend=1, RSI>{cur_bb_upper:.0f} BB, sec cross UP",
                "timeframe": "1d",
                "rsi_at_entry": round(cur_rsi_smooth, 1),
                "volume_ratio": round(vol_r, 2),
                "atr_at_entry": round(atr_val, 6),
            })

        # SELL: all three must align
        elif sell_confirms == 3:
            tp = price_val - 3.0 * atr_val
            sl = price_val + 2.25 * atr_val
            rr = (price_val - tp) / (sl - price_val) if sl > price_val else 0
            if rr < 1.0:
                continue
            confidence = round(min(0.85, 0.55 + 0.10 * sell_confirms), 2)
            signals.append({
                "strategy": "qqe_mod",
                "symbol": symbol,
                "direction": "SELL",
                "entry": _smart_round(price_val),
                "tp": _smart_round(tp),
                "sl": _smart_round(sl),
                "confidence": confidence,
                "rationale": (
                    f"QQE MOD triple confirm: primary trend DOWN, "
                    f"RSI smooth {cur_rsi_smooth:.1f} < BB lower {cur_bb_lower:.1f}, "
                    f"secondary cross DOWN"
                ),
                "category": _get_category(symbol),
                "timestamp": _now_iso(),
                "tags": ["qqe", "triple_confirm", "tradingview"],
                "signal_type": "SELL",
                "entry_price": _smart_round(price_val),
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "risk_reward": round(rr, 2),
                "reason": f"QQE MOD: trend=-1, RSI<{cur_bb_lower:.0f} BB, sec cross DOWN",
                "timeframe": "1d",
                "rsi_at_entry": round(cur_rsi_smooth, 1),
                "volume_ratio": round(vol_r, 2),
                "atr_at_entry": round(atr_val, 6),
            })

    return signals


# =========================================================================
# 2. TTM Squeeze -- John Carter / LazyBear
#    Bollinger Bands inside Keltner Channels = volatility compression.
#    When squeeze fires (BB exits KC), momentum direction predicts breakout.
# =========================================================================

def ttm_squeeze(data: dict[str, pd.DataFrame],
                context: Optional[dict] = None) -> list[dict]:
    """
    TTM Squeeze: BB inside KC = squeeze ON. When squeeze fires OFF after 6+ bars,
    trade momentum direction. Longer squeeze = higher confidence.
    """
    signals: list[dict] = []
    SQUEEZE_MIN_BARS = 6
    KC_MULT = 1.5
    BB_PERIOD = 20
    BB_STD = 2.0

    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 60:
            continue

        close = df["Close"]
        high, low = df["High"], df["Low"]
        vol = df.get("Volume")

        # Bollinger Bands
        bb = bollinger_bands(close, BB_PERIOD, BB_STD)
        bb_upper = bb["upper"]
        bb_lower = bb["lower"]

        # Keltner Channels
        kc_middle = sma(close, BB_PERIOD)
        kc_range = atr(high, low, close, BB_PERIOD)
        kc_upper = kc_middle + KC_MULT * kc_range
        kc_lower = kc_middle - KC_MULT * kc_range

        # Squeeze detection: BB inside KC
        squeeze_on = (bb_lower > kc_lower) & (bb_upper < kc_upper)

        # Momentum: close minus midline of Donchian + SMA, smoothed
        highest_high = high.rolling(BB_PERIOD).max()
        lowest_low = low.rolling(BB_PERIOD).min()
        midline = (highest_high + lowest_low) / 2
        sma_close = sma(close, BB_PERIOD)
        mom = close - (midline + sma_close) / 2

        # Check squeeze state at latest bars
        idx = len(close) - 1
        if idx < SQUEEZE_MIN_BARS + 5:
            continue

        # Count consecutive squeeze bars ending at idx-1
        # (squeeze was ON, now check if it turned OFF at idx)
        cur_squeeze = bool(squeeze_on.iloc[idx])
        prev_squeeze = bool(squeeze_on.iloc[idx - 1])

        # Squeeze just fired: was ON, now OFF
        if prev_squeeze and not cur_squeeze:
            # Count how many bars squeeze was on
            squeeze_count = 0
            for j in range(idx - 1, -1, -1):
                if squeeze_on.iloc[j]:
                    squeeze_count += 1
                else:
                    break

            if squeeze_count < SQUEEZE_MIN_BARS:
                continue

            # Momentum direction
            mom_cur = float(mom.iloc[idx])
            mom_prev = float(mom.iloc[idx - 1])
            mom_rising = mom_cur > mom_prev

            price_val = float(close.iloc[-1])
            atr_val = float(atr(high, low, close, 14).iloc[-1])
            vol_r = float(volume_ratio(vol).iloc[-1]) if vol is not None and len(vol) > 20 else 1.0

            # Volume expansion check
            vol_expanding = vol_r > 1.2 if vol is not None else True

            # Confidence scales with squeeze duration and volume
            base_conf = min(0.80, 0.45 + squeeze_count * 0.03)
            if vol_expanding:
                base_conf = min(0.85, base_conf + 0.05)

            if mom_cur > 0 and mom_rising:
                # Bullish breakout
                tp = price_val + 3.0 * atr_val
                sl = price_val - 2.0 * atr_val
                rr = (tp - price_val) / (price_val - sl) if price_val > sl else 0
                if rr < 1.0:
                    continue
                signals.append({
                    "strategy": "ttm_squeeze",
                    "symbol": symbol,
                    "direction": "BUY",
                    "entry": _smart_round(price_val),
                    "tp": _smart_round(tp),
                    "sl": _smart_round(sl),
                    "confidence": round(base_conf, 2),
                    "rationale": (
                        f"TTM Squeeze fired after {squeeze_count} bars compression, "
                        f"momentum positive & rising ({mom_cur:.2f}), "
                        f"vol_ratio={vol_r:.1f}"
                    ),
                    "category": _get_category(symbol),
                    "timestamp": _now_iso(),
                    "tags": ["ttm_squeeze", "volatility_breakout", "tradingview"],
                    "signal_type": "BUY",
                    "entry_price": _smart_round(price_val),
                    "take_profit": _smart_round(tp),
                    "stop_loss": _smart_round(sl),
                    "risk_reward": round(rr, 2),
                    "reason": f"TTM Squeeze: {squeeze_count}-bar compression, mom>0 rising",
                    "timeframe": "1d",
                    "volume_ratio": round(vol_r, 2),
                    "atr_at_entry": round(atr_val, 6),
                    "squeeze_bars": squeeze_count,
                })

            elif mom_cur < 0 and not mom_rising:
                # Bearish breakout
                tp = price_val - 3.0 * atr_val
                sl = price_val + 2.0 * atr_val
                rr = (price_val - tp) / (sl - price_val) if sl > price_val else 0
                if rr < 1.0:
                    continue
                signals.append({
                    "strategy": "ttm_squeeze",
                    "symbol": symbol,
                    "direction": "SELL",
                    "entry": _smart_round(price_val),
                    "tp": _smart_round(tp),
                    "sl": _smart_round(sl),
                    "confidence": round(base_conf, 2),
                    "rationale": (
                        f"TTM Squeeze fired after {squeeze_count} bars compression, "
                        f"momentum negative & falling ({mom_cur:.2f}), "
                        f"vol_ratio={vol_r:.1f}"
                    ),
                    "category": _get_category(symbol),
                    "timestamp": _now_iso(),
                    "tags": ["ttm_squeeze", "volatility_breakout", "tradingview"],
                    "signal_type": "SELL",
                    "entry_price": _smart_round(price_val),
                    "take_profit": _smart_round(tp),
                    "stop_loss": _smart_round(sl),
                    "risk_reward": round(rr, 2),
                    "reason": f"TTM Squeeze: {squeeze_count}-bar compression, mom<0 falling",
                    "timeframe": "1d",
                    "volume_ratio": round(vol_r, 2),
                    "atr_at_entry": round(atr_val, 6),
                    "squeeze_bars": squeeze_count,
                })

    return signals


# =========================================================================
# 3. Stochastic Momentum Index (SMI) -- William Blau
#    Measures distance from midpoint of high/low range, double-smoothed.
#    Better than StochRSI: smoother, fewer whipsaws. 57% WR, 1.8 PF.
# =========================================================================

def stochastic_momentum_index(data: dict[str, pd.DataFrame],
                              context: Optional[dict] = None) -> list[dict]:
    """
    SMI Ergodic: double-smoothed midpoint distance stochastic.
    BUY: SMI crosses above signal AND smi < -40 (oversold).
    SELL: SMI crosses below signal AND smi > 40 (overbought).
    """
    signals: list[dict] = []
    K_PERIOD = 10
    D_PERIOD = 3
    OVERSOLD = -40
    OVERBOUGHT = 40

    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 40:
            continue

        close = df["Close"]
        high, low = df["High"], df["Low"]
        vol = df.get("Volume")

        # Highest high and lowest low over K period
        highest_high = high.rolling(K_PERIOD).max()
        lowest_low = low.rolling(K_PERIOD).min()

        # Distance from midpoint (key difference from regular Stochastic)
        midpoint = (highest_high + lowest_low) / 2
        distance = close - midpoint
        half_range = (highest_high - lowest_low) / 2

        # Double smoothing
        smooth_distance = ema(ema(distance, D_PERIOD), D_PERIOD)
        smooth_range = ema(ema(half_range, D_PERIOD), D_PERIOD)

        # SMI calculation -- handle division by zero
        safe_range = smooth_range.replace(0, np.nan)
        smi = 100.0 * smooth_distance / safe_range
        smi = smi.fillna(0.0)
        signal_line = ema(smi, D_PERIOD)

        idx = len(close) - 1
        if idx < 2:
            continue

        smi_cur = float(smi.iloc[idx])
        smi_prev = float(smi.iloc[idx - 1])
        sig_cur = float(signal_line.iloc[idx])
        sig_prev = float(signal_line.iloc[idx - 1])

        if np.isnan(smi_cur) or np.isnan(sig_cur) or np.isnan(smi_prev) or np.isnan(sig_prev):
            continue

        price_val = float(close.iloc[-1])
        atr_val = float(atr(high, low, close, 14).iloc[-1])
        vol_r = float(volume_ratio(vol).iloc[-1]) if vol is not None and len(vol) > 20 else 1.0

        # Cross detection
        cross_up = smi_prev <= sig_prev and smi_cur > sig_cur
        cross_down = smi_prev >= sig_prev and smi_cur < sig_cur

        # Confidence based on depth into oversold/overbought zone
        def _smi_confidence(smi_val: float, threshold: float) -> float:
            depth = abs(smi_val) - abs(threshold)
            base = 0.50
            bonus = min(0.30, depth / 100.0) if depth > 0 else 0.0
            return round(min(0.85, base + bonus), 2)

        # BUY: SMI crosses above signal from oversold
        if cross_up and smi_cur < OVERSOLD:
            tp = price_val + 2.5 * atr_val
            sl = price_val - 1.5 * atr_val
            rr = (tp - price_val) / (price_val - sl) if price_val > sl else 0
            if rr < 1.0:
                continue
            signals.append({
                "strategy": "stochastic_momentum_index",
                "symbol": symbol,
                "direction": "BUY",
                "entry": _smart_round(price_val),
                "tp": _smart_round(tp),
                "sl": _smart_round(sl),
                "confidence": _smi_confidence(smi_cur, OVERSOLD),
                "rationale": (
                    f"SMI cross UP from oversold: SMI={smi_cur:.1f} (signal={sig_cur:.1f}), "
                    f"depth={abs(smi_cur):.0f}"
                ),
                "category": _get_category(symbol),
                "timestamp": _now_iso(),
                "tags": ["smi", "oversold_reversal", "tradingview"],
                "signal_type": "BUY",
                "entry_price": _smart_round(price_val),
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "risk_reward": round(rr, 2),
                "reason": f"SMI oversold cross UP: SMI={smi_cur:.0f}, signal={sig_cur:.0f}",
                "timeframe": "1d",
                "volume_ratio": round(vol_r, 2),
                "atr_at_entry": round(atr_val, 6),
                "smi_value": round(smi_cur, 1),
                "smi_signal": round(sig_cur, 1),
            })

        # SELL: SMI crosses below signal from overbought
        elif cross_down and smi_cur > OVERBOUGHT:
            tp = price_val - 2.5 * atr_val
            sl = price_val + 1.5 * atr_val
            rr = (price_val - tp) / (sl - price_val) if sl > price_val else 0
            if rr < 1.0:
                continue
            signals.append({
                "strategy": "stochastic_momentum_index",
                "symbol": symbol,
                "direction": "SELL",
                "entry": _smart_round(price_val),
                "tp": _smart_round(tp),
                "sl": _smart_round(sl),
                "confidence": _smi_confidence(smi_cur, OVERBOUGHT),
                "rationale": (
                    f"SMI cross DOWN from overbought: SMI={smi_cur:.1f} (signal={sig_cur:.1f}), "
                    f"depth={abs(smi_cur):.0f}"
                ),
                "category": _get_category(symbol),
                "timestamp": _now_iso(),
                "tags": ["smi", "overbought_reversal", "tradingview"],
                "signal_type": "SELL",
                "entry_price": _smart_round(price_val),
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "risk_reward": round(rr, 2),
                "reason": f"SMI overbought cross DOWN: SMI={smi_cur:.0f}, signal={sig_cur:.0f}",
                "timeframe": "1d",
                "volume_ratio": round(vol_r, 2),
                "atr_at_entry": round(atr_val, 6),
                "smi_value": round(smi_cur, 1),
                "smi_signal": round(sig_cur, 1),
            })

    return signals


# =========================================================================
# 4. SMC Confluence Score -- Smart Money Confluence
#    Weighted composite from OB + FVG + Liquidity + BOS + MTF alignment.
#    Score 0-100. Signal when score > 70.
#    Weights: OB 25%, FVG 20%, Liquidity 20%, BOS 20%, MTF 15%
# =========================================================================

def smc_confluence_score(data: dict[str, pd.DataFrame],
                         context: Optional[dict] = None) -> list[dict]:
    """
    Smart Money Confluence: weighted composite score from 5 SMC components.
    - Order Block strength (volume-validated): 25%
    - Fair Value Gap (size and recency): 20%
    - Liquidity zone proximity (sweep detection): 20%
    - Market structure alignment (BOS/CHoCH): 20%
    - Multi-timeframe trend alignment (EMA stack): 15%

    Score 0-100. BUY when score > 70 and direction is bullish.
    """
    signals: list[dict] = []
    SCORE_THRESHOLD = 70
    OB_LOOKBACK = 20
    FVG_LOOKBACK = 10
    BOS_LOOKBACK = 5
    SWING_LOOKBACK = 20

    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 60:
            continue

        close = df["Close"]
        high, low = df["High"], df["Low"]
        vol = df.get("Volume")
        price_val = float(close.iloc[-1])
        atr_val = float(atr(high, low, close, 14).iloc[-1])
        vol_r = float(volume_ratio(vol).iloc[-1]) if vol is not None and len(vol) > 20 else 1.0

        # Determine directional bias from EMA stack
        ema9 = ema(close, 9)
        ema21 = ema(close, 21)
        ema50 = ema(close, 50)

        e9 = float(ema9.iloc[-1])
        e21 = float(ema21.iloc[-1])
        e50 = float(ema50.iloc[-1])

        bullish_bias = e9 > e21 > e50
        bearish_bias = e9 < e21 < e50

        if not bullish_bias and not bearish_bias:
            # No clear directional bias -- skip or partial score
            pass

        # -----------------------------------------------------------
        # Component 1: Order Block Score (25%)
        # Find recent swing highs/lows with high volume
        # -----------------------------------------------------------
        ob_score = 0.0
        if vol is not None and len(vol) > OB_LOOKBACK:
            avg_vol = float(vol.iloc[-OB_LOOKBACK:].mean())
            # Look for swing lows (bullish OB) or swing highs (bearish OB)
            for j in range(max(2, len(close) - OB_LOOKBACK), len(close) - 2):
                is_swing_low = (float(low.iloc[j]) <= float(low.iloc[j - 1]) and
                                float(low.iloc[j]) <= float(low.iloc[j + 1]))
                is_swing_high = (float(high.iloc[j]) >= float(high.iloc[j - 1]) and
                                 float(high.iloc[j]) >= float(high.iloc[j + 1]))

                vol_at_swing = float(vol.iloc[j])
                vol_mult = vol_at_swing / avg_vol if avg_vol > 0 else 0

                if bullish_bias and is_swing_low:
                    # Price near the OB zone?
                    ob_level = float(low.iloc[j])
                    distance_pct = abs(price_val - ob_level) / price_val if price_val > 0 else 999
                    if distance_pct < 0.03 and vol_mult > 2.0:
                        ob_score = min(100, 60 + vol_mult * 10)
                    elif distance_pct < 0.05 and vol_mult > 1.5:
                        ob_score = max(ob_score, min(80, 40 + vol_mult * 10))

                elif bearish_bias and is_swing_high:
                    ob_level = float(high.iloc[j])
                    distance_pct = abs(price_val - ob_level) / price_val if price_val > 0 else 999
                    if distance_pct < 0.03 and vol_mult > 2.0:
                        ob_score = min(100, 60 + vol_mult * 10)
                    elif distance_pct < 0.05 and vol_mult > 1.5:
                        ob_score = max(ob_score, min(80, 40 + vol_mult * 10))

        # -----------------------------------------------------------
        # Component 2: Fair Value Gap Score (20%)
        # 3-candle FVG pattern in last N bars
        # -----------------------------------------------------------
        fvg_score = 0.0
        for j in range(max(2, len(close) - FVG_LOOKBACK), len(close)):
            if bullish_bias:
                # Bullish FVG: candle[j] low > candle[j-2] high
                gap = float(low.iloc[j]) - float(high.iloc[j - 2])
                if gap > 0:
                    gap_pct = gap / float(high.iloc[j - 2]) if float(high.iloc[j - 2]) > 0 else 0
                    recency = 1.0 - (len(close) - 1 - j) / FVG_LOOKBACK
                    fvg_score = max(fvg_score, min(100, (gap_pct / atr_val * price_val) * 50 * recency))
            elif bearish_bias:
                # Bearish FVG: candle[j] high < candle[j-2] low
                gap = float(low.iloc[j - 2]) - float(high.iloc[j])
                if gap > 0:
                    gap_pct = gap / float(low.iloc[j - 2]) if float(low.iloc[j - 2]) > 0 else 0
                    recency = 1.0 - (len(close) - 1 - j) / FVG_LOOKBACK
                    fvg_score = max(fvg_score, min(100, (gap_pct / atr_val * price_val) * 50 * recency))

        # -----------------------------------------------------------
        # Component 3: Liquidity Score (20%)
        # Check if price swept a prior swing high/low (wick beyond, close inside)
        # -----------------------------------------------------------
        liq_score = 0.0
        # Find swing highs/lows in prior SWING_LOOKBACK bars
        swing_highs = []
        swing_lows = []
        lookback_start = max(2, len(close) - SWING_LOOKBACK - 5)
        lookback_end = max(2, len(close) - 3)

        for j in range(lookback_start, lookback_end):
            if (float(high.iloc[j]) >= float(high.iloc[j - 1]) and
                    float(high.iloc[j]) >= float(high.iloc[j + 1])):
                swing_highs.append(float(high.iloc[j]))
            if (float(low.iloc[j]) <= float(low.iloc[j - 1]) and
                    float(low.iloc[j]) <= float(low.iloc[j + 1])):
                swing_lows.append(float(low.iloc[j]))

        # Check latest bar for liquidity sweep
        cur_high = float(high.iloc[-1])
        cur_low = float(low.iloc[-1])
        cur_close = float(close.iloc[-1])

        if bullish_bias and swing_lows:
            for sl_level in swing_lows:
                # Wick swept below swing low but closed above it
                if cur_low < sl_level and cur_close > sl_level:
                    sweep_depth = (sl_level - cur_low) / atr_val if atr_val > 0 else 0
                    liq_score = max(liq_score, min(100, 50 + sweep_depth * 50))

        elif bearish_bias and swing_highs:
            for sh_level in swing_highs:
                # Wick swept above swing high but closed below it
                if cur_high > sh_level and cur_close < sh_level:
                    sweep_depth = (cur_high - sh_level) / atr_val if atr_val > 0 else 0
                    liq_score = max(liq_score, min(100, 50 + sweep_depth * 50))

        # -----------------------------------------------------------
        # Component 4: Break of Structure Score (20%)
        # Check if price broke prior pivot in last BOS_LOOKBACK bars
        # -----------------------------------------------------------
        bos_score = 0.0
        # Find pivots further back
        pivot_highs = []
        pivot_lows = []
        pivot_start = max(2, len(close) - BOS_LOOKBACK - 10)
        pivot_end = max(2, len(close) - BOS_LOOKBACK)

        for j in range(pivot_start, pivot_end):
            if j + 1 < len(high):
                if (float(high.iloc[j]) >= float(high.iloc[j - 1]) and
                        float(high.iloc[j]) >= float(high.iloc[j + 1])):
                    pivot_highs.append(float(high.iloc[j]))
                if (float(low.iloc[j]) <= float(low.iloc[j - 1]) and
                        float(low.iloc[j]) <= float(low.iloc[j + 1])):
                    pivot_lows.append(float(low.iloc[j]))

        # Check recent bars for BOS
        for j in range(max(1, len(close) - BOS_LOOKBACK), len(close)):
            cur_c = float(close.iloc[j])
            cur_v = float(vol.iloc[j]) if vol is not None else 0
            avg_v = float(vol.iloc[max(0, j - 20):j].mean()) if vol is not None and j > 1 else 1

            if bullish_bias and pivot_highs:
                for ph in pivot_highs:
                    if cur_c > ph:
                        vol_conviction = cur_v / avg_v if avg_v > 0 else 1
                        bos_score = max(bos_score, min(100, 50 + vol_conviction * 15))

            elif bearish_bias and pivot_lows:
                for pl in pivot_lows:
                    if cur_c < pl:
                        vol_conviction = cur_v / avg_v if avg_v > 0 else 1
                        bos_score = max(bos_score, min(100, 50 + vol_conviction * 15))

        # -----------------------------------------------------------
        # Component 5: Multi-Timeframe Trend Score (15%)
        # EMA(9) > EMA(21) > EMA(50) alignment
        # -----------------------------------------------------------
        mtf_score = 0.0
        if bullish_bias:
            # Full alignment = 100%
            alignment_count = 0
            if e9 > e21:
                alignment_count += 1
            if e21 > e50:
                alignment_count += 1
            if price_val > e9:
                alignment_count += 1
            mtf_score = (alignment_count / 3.0) * 100

        elif bearish_bias:
            alignment_count = 0
            if e9 < e21:
                alignment_count += 1
            if e21 < e50:
                alignment_count += 1
            if price_val < e9:
                alignment_count += 1
            mtf_score = (alignment_count / 3.0) * 100

        # -----------------------------------------------------------
        # Composite Score
        # -----------------------------------------------------------
        composite = (
            ob_score * 0.25 +
            fvg_score * 0.20 +
            liq_score * 0.20 +
            bos_score * 0.20 +
            mtf_score * 0.15
        )

        if composite < SCORE_THRESHOLD:
            continue

        confidence = round(min(0.90, composite / 100.0), 2)

        if bullish_bias:
            tp = price_val + 3.0 * atr_val
            sl = price_val - 2.0 * atr_val
            rr = (tp - price_val) / (price_val - sl) if price_val > sl else 0
            if rr < 1.0:
                continue
            signals.append({
                "strategy": "smc_confluence_score",
                "symbol": symbol,
                "direction": "BUY",
                "entry": _smart_round(price_val),
                "tp": _smart_round(tp),
                "sl": _smart_round(sl),
                "confidence": confidence,
                "rationale": (
                    f"SMC Confluence {composite:.0f}/100: "
                    f"OB={ob_score:.0f} FVG={fvg_score:.0f} LIQ={liq_score:.0f} "
                    f"BOS={bos_score:.0f} MTF={mtf_score:.0f}"
                ),
                "category": _get_category(symbol),
                "timestamp": _now_iso(),
                "tags": ["smc", "confluence", "institutional", "tradingview"],
                "signal_type": "BUY",
                "entry_price": _smart_round(price_val),
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "risk_reward": round(rr, 2),
                "reason": f"SMC score {composite:.0f}/100 bullish (OB+FVG+LIQ+BOS+MTF)",
                "timeframe": "1d",
                "volume_ratio": round(vol_r, 2),
                "atr_at_entry": round(atr_val, 6),
                "smc_score": round(composite, 1),
                "smc_ob": round(ob_score, 1),
                "smc_fvg": round(fvg_score, 1),
                "smc_liq": round(liq_score, 1),
                "smc_bos": round(bos_score, 1),
                "smc_mtf": round(mtf_score, 1),
            })

        elif bearish_bias:
            tp = price_val - 3.0 * atr_val
            sl = price_val + 2.0 * atr_val
            rr = (price_val - tp) / (sl - price_val) if sl > price_val else 0
            if rr < 1.0:
                continue
            signals.append({
                "strategy": "smc_confluence_score",
                "symbol": symbol,
                "direction": "SELL",
                "entry": _smart_round(price_val),
                "tp": _smart_round(tp),
                "sl": _smart_round(sl),
                "confidence": confidence,
                "rationale": (
                    f"SMC Confluence {composite:.0f}/100: "
                    f"OB={ob_score:.0f} FVG={fvg_score:.0f} LIQ={liq_score:.0f} "
                    f"BOS={bos_score:.0f} MTF={mtf_score:.0f}"
                ),
                "category": _get_category(symbol),
                "timestamp": _now_iso(),
                "tags": ["smc", "confluence", "institutional", "tradingview"],
                "signal_type": "SELL",
                "entry_price": _smart_round(price_val),
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "risk_reward": round(rr, 2),
                "reason": f"SMC score {composite:.0f}/100 bearish (OB+FVG+LIQ+BOS+MTF)",
                "timeframe": "1d",
                "volume_ratio": round(vol_r, 2),
                "atr_at_entry": round(atr_val, 6),
                "smc_score": round(composite, 1),
                "smc_ob": round(ob_score, 1),
                "smc_fvg": round(fvg_score, 1),
                "smc_liq": round(liq_score, 1),
                "smc_bos": round(bos_score, 1),
                "smc_mtf": round(mtf_score, 1),
            })

    return signals


# =========================================================================
# Strategy Registry
# =========================================================================

TV_RESEARCH_STRATEGIES_W2: dict[str, callable] = {
    "qqe_mod": qqe_mod,
    "ttm_squeeze": ttm_squeeze,
    "stochastic_momentum_index": stochastic_momentum_index,
    "smc_confluence_score": smc_confluence_score,
}
