"""
ALPHA_ENGINE -- TradingView Research Strategies Wave 3
======================================================
Advanced ML and adaptive strategies from TradingView research.

Strategies:
  1. lorentzian_classification -- k-NN with Lorentzian distance metric
                                 Most Valuable PineScript 2023, universal classifier
  2. nadaraya_watson_envelope  -- Kernel regression adaptive S/R bands
                                 Non-parametric, adapts to any volatility regime
  3. volume_delta_divergence   -- CVD vs price divergence detection
                                 Catches reversals via buy/sell pressure analysis
  4. ict_three_chain           -- ICT Sweep->MSS->FVG sequential filter
                                 3-condition chain dramatically reduces false signals

References:
  - Lorentzian: jdehorty TradingView, d(x,y) = sum(log(1 + |xi-yi|))
  - Nadaraya-Watson: LuxAlgo, rational quadratic kernel regression
  - CVD: Flux Charts, buy volume estimation via intrabar analysis
  - ICT: Inner Circle Trader methodology, automated by LuxAlgo SMC
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


# -- Helpers -----------------------------------------------------------------

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


# =====================================================================
# STRATEGY: Lorentzian Classification (k-NN)
# =====================================================================
# k-Nearest Neighbors using Lorentzian distance metric.
# Lorentzian distance: d(x,y) = sum(log(1 + |xi - yi|))
# Superior to Euclidean for financial data because it compresses
# extreme values logarithmically, making it robust to outliers and
# fat-tailed distributions.
#
# Features (5-dimensional space):
#   1. RSI(14)
#   2. ADX(20)
#   3. CCI(20) -- Commodity Channel Index
#   4. ATR ratio (current ATR / SMA of ATR) -- volatility regime
#   5. Close position in Bollinger Bands (%B)
#
# For each bar, find k=8 nearest historical neighbors using Lorentzian
# distance. Classify based on majority vote of neighbor next-bar returns.
# Only signal when confidence > 60% (5+ of 8 agree).
#
# Reference: jdehorty TradingView (Most Valuable PineScript 2023)
# =====================================================================

def _cci(high: pd.Series, low: pd.Series, close: pd.Series,
         period: int = 20) -> pd.Series:
    """Commodity Channel Index (CCI)."""
    tp = (high + low + close) / 3.0
    tp_sma = sma(tp, period)
    # Mean absolute deviation
    mad = tp.rolling(period).apply(lambda x: np.mean(np.abs(x - x.mean())), raw=True)
    mad = mad.replace(0, np.nan)
    return (tp - tp_sma) / (0.015 * mad)


def _lorentzian_distance(a: np.ndarray, b: np.ndarray) -> float:
    """Lorentzian distance: d(x,y) = sum(log(1 + |xi - yi|))."""
    return float(np.sum(np.log(1.0 + np.abs(a - b))))


def lorentzian_classification(data: dict[str, pd.DataFrame],
                              context: Optional[dict] = None) -> list[dict]:
    """
    k-NN classification using Lorentzian distance metric.

    Lookback: 500 bars subsampled every 2nd bar for performance.
    k=8 nearest neighbors. Signal when 5+ of 8 agree on direction.
    """
    signals: list[dict] = []
    k = 8
    min_bars = 200
    search_window = 500
    subsample_step = 2

    for symbol, info in CRYPTO_SYMBOLS.items():
        df = data.get(symbol)
        if df is None or len(df) < min_bars:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]

        # -- Compute 5 features across all bars --
        feat_rsi = rsi(close, 14)
        feat_adx = adx(high, low, close, 20)
        feat_cci = _cci(high, low, close, 20)
        atr_val = atr(high, low, close, 14)
        atr_sma_val = sma(atr_val, 14)
        feat_atr_ratio = atr_val / atr_sma_val.replace(0, np.nan)
        bb = bollinger_bands(close, 20, 2.0)
        feat_pctb = bb["pct_b"]

        # Stack features into a 2D array
        features = pd.DataFrame({
            "rsi": feat_rsi,
            "adx": feat_adx,
            "cci": feat_cci,
            "atr_ratio": feat_atr_ratio,
            "pct_b": feat_pctb,
        }).values  # shape (N, 5)

        # Next-bar returns for classification labels
        returns = close.pct_change().shift(-1).values  # returns[i] = return after bar i

        n = len(features)
        if n < min_bars:
            continue

        # Current bar = last bar
        current_idx = n - 1
        current_features = features[current_idx]

        # Check for NaN in current features
        if np.any(np.isnan(current_features)):
            continue

        # Search window: from bar 50 to bar[-2], subsampled
        search_start = max(50, n - search_window)
        search_end = n - 1  # exclude current bar
        candidate_indices = list(range(search_start, search_end, subsample_step))

        # Compute distances to all candidates
        distances = []
        for idx in candidate_indices:
            feat = features[idx]
            ret = returns[idx]
            if np.any(np.isnan(feat)) or np.isnan(ret):
                continue
            dist = _lorentzian_distance(current_features, feat)
            distances.append((dist, ret))

        if len(distances) < k:
            continue

        # Sort by distance, take k nearest
        distances.sort(key=lambda x: x[0])
        nearest = distances[:k]

        # Majority vote: count positive vs negative returns
        positive_count = sum(1 for _, r in nearest if r > 0)
        negative_count = k - positive_count

        confidence = max(positive_count, negative_count) / k

        # Only signal if 5+ of 8 agree (confidence > 0.6)
        if confidence < 0.625:
            continue

        if positive_count >= 5:
            direction = "BUY"
        elif negative_count >= 5:
            direction = "SELL"
        else:
            continue

        price, tp, sl = _atr_tp_sl(close, high, low, tp_mult=3.0, sl_mult=2.25)

        if direction == "SELL":
            # Invert TP/SL for shorts
            atr_val_now = float(atr(high, low, close, 14).iloc[-1])
            tp = _smart_round(price - 3.0 * atr_val_now)
            sl = _smart_round(price + 2.25 * atr_val_now)

        signals.append({
            "strategy": "lorentzian_classification",
            "symbol": symbol,
            "direction": direction,
            "entry": price,
            "tp": tp,
            "sl": sl,
            "confidence": round(confidence, 3),
            "rationale": (
                f"Lorentzian k-NN ({k} neighbors): {positive_count} bullish, "
                f"{negative_count} bearish. "
                f"RSI={feat_rsi.iloc[-1]:.1f}, ADX={feat_adx.iloc[-1]:.1f}, "
                f"CCI={feat_cci.iloc[-1]:.1f}"
            ),
            "category": _get_category(symbol),
            "timestamp": _now_iso(),
            "tags": ["ml", "knn", "lorentzian", "tv-research"],
        })

    return signals


# =====================================================================
# STRATEGY: Nadaraya-Watson Envelope
# =====================================================================
# Non-parametric kernel regression creating adaptive S/R bands.
# Uses Rational Quadratic kernel (handles multiple length scales).
#
# Kernel: K(x) = (1 + x^2 / (2 * alpha * h^2))^(-alpha)
# where h = bandwidth, alpha = relative weighting (default 8)
#
# Envelope = y_hat +/- mult * MAD
#
# BUY: price touches/crosses below lower envelope (oversold)
# SELL: price touches/crosses above upper envelope (overbought)
#
# Reference: LuxAlgo TradingView
# =====================================================================

def nadaraya_watson_envelope(data: dict[str, pd.DataFrame],
                             context: Optional[dict] = None) -> list[dict]:
    """
    Non-parametric kernel regression with Rational Quadratic kernel.
    Adaptive S/R envelope that adjusts to volatility regime.
    bandwidth=8, alpha=8.0, envelope_mult=3.0.
    """
    signals: list[dict] = []
    bandwidth = 8.0
    alpha = 8.0
    envelope_mult = 3.0
    lookback = 100
    min_bars = 120

    for symbol, info in CRYPTO_SYMBOLS.items():
        df = data.get(symbol)
        if df is None or len(df) < min_bars:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        n = len(close)

        # Use the last `lookback` bars for kernel computation
        window_start = max(0, n - lookback)
        close_window = close.iloc[window_start:].values

        if len(close_window) < 20:
            continue

        current_idx = len(close_window) - 1
        current_price = float(close_window[current_idx])

        # Compute kernel weights from current bar to all bars in window
        weights = np.zeros(len(close_window))
        for j in range(len(close_window)):
            dist = abs(current_idx - j)
            # Rational Quadratic kernel: K(x) = (1 + x^2/(2*alpha*h^2))^(-alpha)
            weights[j] = (1.0 + (dist ** 2) / (2.0 * alpha * bandwidth ** 2)) ** (-alpha)

        weight_sum = np.sum(weights)
        if weight_sum == 0:
            continue

        # Kernel estimate at current bar
        y_hat = float(np.sum(weights * close_window) / weight_sum)

        # Mean absolute deviation of price from kernel estimate across window
        # Compute kernel estimate for each bar in window for MAD calculation
        kernel_estimates = np.zeros(len(close_window))
        for i in range(len(close_window)):
            w = np.zeros(len(close_window))
            for j in range(len(close_window)):
                dist = abs(i - j)
                w[j] = (1.0 + (dist ** 2) / (2.0 * alpha * bandwidth ** 2)) ** (-alpha)
            ws = np.sum(w)
            if ws > 0:
                kernel_estimates[i] = np.sum(w * close_window) / ws
            else:
                kernel_estimates[i] = close_window[i]

        mad = float(np.mean(np.abs(close_window - kernel_estimates)))
        if mad == 0:
            continue

        upper_envelope = y_hat + envelope_mult * mad
        lower_envelope = y_hat - envelope_mult * mad

        direction = None
        distance_beyond = 0.0

        if current_price < lower_envelope:
            direction = "BUY"
            distance_beyond = (lower_envelope - current_price) / mad
        elif current_price > upper_envelope:
            direction = "SELL"
            distance_beyond = (current_price - upper_envelope) / mad

        if direction is None:
            continue

        # Confidence based on how far beyond envelope (capped at 0.95)
        confidence = min(0.95, 0.60 + distance_beyond * 0.10)

        price, tp, sl = _atr_tp_sl(close, high, low, tp_mult=3.0, sl_mult=2.25)

        if direction == "SELL":
            atr_val_now = float(atr(high, low, close, 14).iloc[-1])
            tp = _smart_round(price - 3.0 * atr_val_now)
            sl = _smart_round(price + 2.25 * atr_val_now)

        signals.append({
            "strategy": "nadaraya_watson_envelope",
            "symbol": symbol,
            "direction": direction,
            "entry": price,
            "tp": tp,
            "sl": sl,
            "confidence": round(confidence, 3),
            "rationale": (
                f"NW kernel envelope: price {'below lower' if direction == 'BUY' else 'above upper'} "
                f"band. Kernel={_smart_round(y_hat)}, "
                f"Upper={_smart_round(upper_envelope)}, "
                f"Lower={_smart_round(lower_envelope)}, "
                f"MAD={_smart_round(mad)}"
            ),
            "category": _get_category(symbol),
            "timestamp": _now_iso(),
            "tags": ["kernel-regression", "mean-reversion", "nw-envelope", "tv-research"],
        })

    return signals


# =====================================================================
# STRATEGY: Volume Delta Divergence
# =====================================================================
# Detects divergence between Cumulative Volume Delta and price.
#
# Volume Delta estimation (from candle data):
#   buy_ratio = (close - low) / max(high - low, epsilon)
#   buy_vol = volume * buy_ratio
#   sell_vol = volume * (1 - buy_ratio)
#   delta = buy_vol - sell_vol
#   CVD = rolling cumsum of delta (50-period)
#
# Divergence types:
#   Bearish: price HH but CVD LH
#   Bullish: price LL but CVD HL
#
# Reference: Flux Charts TradingView
# =====================================================================

def _find_swing_points(series: pd.Series, lookback: int = 5) -> list[tuple[int, float]]:
    """Find swing highs or lows using N-bar lookback on each side."""
    points = []
    vals = series.values
    for i in range(lookback, len(vals) - lookback):
        # Check if this is a swing high
        is_high = True
        is_low = True
        for j in range(1, lookback + 1):
            if vals[i] < vals[i - j] or vals[i] < vals[i + j]:
                is_high = False
            if vals[i] > vals[i - j] or vals[i] > vals[i + j]:
                is_low = False
        if is_high:
            points.append((i, float(vals[i]), "high"))
        elif is_low:
            points.append((i, float(vals[i]), "low"))
    return points


def volume_delta_divergence(data: dict[str, pd.DataFrame],
                            context: Optional[dict] = None) -> list[dict]:
    """
    Detect divergence between Cumulative Volume Delta and price.
    Buy/sell volume estimated from candle structure.
    Bullish divergence: price LL but CVD HL.
    Bearish divergence: price HH but CVD LH.
    """
    signals: list[dict] = []
    min_bars = 100
    cvd_period = 50
    swing_lookback = 5

    for symbol, info in CRYPTO_SYMBOLS.items():
        df = data.get(symbol)
        if df is None or len(df) < min_bars:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df.get("volume")
        if volume is None:
            continue

        # -- Estimate buy/sell volume from candle structure --
        candle_range = (high - low).replace(0, np.nan).fillna(0.0001)
        buy_ratio = (close - low) / candle_range
        buy_ratio = buy_ratio.clip(0.0, 1.0)
        buy_vol = volume * buy_ratio
        sell_vol = volume * (1.0 - buy_ratio)
        delta = buy_vol - sell_vol

        # Rolling CVD (50-period cumsum, not from beginning)
        cvd = delta.rolling(cvd_period, min_periods=cvd_period).sum()

        if cvd.isna().all():
            continue

        # -- Find swing points in price and CVD --
        # Only look at recent data (last 80 bars)
        recent_start = max(0, len(close) - 80)
        price_recent = close.iloc[recent_start:].reset_index(drop=True)
        cvd_recent = cvd.iloc[recent_start:].reset_index(drop=True)

        price_swings = _find_swing_points(price_recent, swing_lookback)
        cvd_swings = _find_swing_points(cvd_recent, swing_lookback)

        # Separate highs and lows
        price_highs = [(i, v) for i, v, t in price_swings if t == "high"]
        price_lows = [(i, v) for i, v, t in price_swings if t == "low"]
        cvd_highs = [(i, v) for i, v, t in cvd_swings if t == "high"]
        cvd_lows = [(i, v) for i, v, t in cvd_swings if t == "low"]

        direction = None
        divergence_magnitude = 0.0

        # Check bearish divergence: price HH but CVD LH
        if len(price_highs) >= 2 and len(cvd_highs) >= 2:
            ph1_idx, ph1_val = price_highs[-2]
            ph2_idx, ph2_val = price_highs[-1]
            # Find CVD highs nearest to these price highs
            ch1 = min(cvd_highs, key=lambda x: abs(x[0] - ph1_idx))
            ch2 = min(cvd_highs, key=lambda x: abs(x[0] - ph2_idx))

            if ph2_val > ph1_val and ch2[1] < ch1[1]:
                direction = "SELL"
                price_diff = (ph2_val - ph1_val) / ph1_val
                cvd_diff = (ch1[1] - ch2[1]) / max(abs(ch1[1]), 1.0)
                divergence_magnitude = price_diff + cvd_diff

        # Check bullish divergence: price LL but CVD HL
        if direction is None and len(price_lows) >= 2 and len(cvd_lows) >= 2:
            pl1_idx, pl1_val = price_lows[-2]
            pl2_idx, pl2_val = price_lows[-1]
            cl1 = min(cvd_lows, key=lambda x: abs(x[0] - pl1_idx))
            cl2 = min(cvd_lows, key=lambda x: abs(x[0] - pl2_idx))

            if pl2_val < pl1_val and cl2[1] > cl1[1]:
                direction = "BUY"
                price_diff = (pl1_val - pl2_val) / pl1_val
                cvd_diff = (cl2[1] - cl1[1]) / max(abs(cl1[1]), 1.0)
                divergence_magnitude = price_diff + cvd_diff

        if direction is None:
            continue

        # Reversal candle confirmation
        last_close = float(close.iloc[-1])
        prev_open = float(df["Open"].iloc[-1]) if "Open" in df.columns else last_close

        if direction == "BUY" and last_close < prev_open:
            # Need green candle for bullish confirmation, skip if red
            continue
        if direction == "SELL" and last_close > prev_open:
            # Need red candle for bearish confirmation, skip if green
            continue

        # Confidence based on divergence magnitude
        confidence = min(0.90, 0.55 + divergence_magnitude * 2.0)
        confidence = round(max(0.55, confidence), 3)

        price, tp, sl = _atr_tp_sl(close, high, low, tp_mult=3.0, sl_mult=2.25)

        if direction == "SELL":
            atr_val_now = float(atr(high, low, close, 14).iloc[-1])
            tp = _smart_round(price - 3.0 * atr_val_now)
            sl = _smart_round(price + 2.25 * atr_val_now)

        signals.append({
            "strategy": "volume_delta_divergence",
            "symbol": symbol,
            "direction": direction,
            "entry": price,
            "tp": tp,
            "sl": sl,
            "confidence": confidence,
            "rationale": (
                f"CVD divergence ({direction.lower()}): "
                f"price {'higher high' if direction == 'SELL' else 'lower low'} "
                f"vs CVD {'lower high' if direction == 'SELL' else 'higher low'}. "
                f"Divergence magnitude={divergence_magnitude:.4f}"
            ),
            "category": _get_category(symbol),
            "timestamp": _now_iso(),
            "tags": ["cvd", "divergence", "volume-analysis", "tv-research"],
        })

    return signals


# =====================================================================
# STRATEGY: ICT Three-Chain (Sweep -> MSS -> FVG)
# =====================================================================
# Sequential 3-condition institutional filter:
#   1. Liquidity Sweep: price wicks beyond prior swing H/L then closes back
#   2. Market Structure Shift (MSS): price breaks a prior pivot after sweep
#   3. Fair Value Gap (FVG): 3-candle imbalance zone after MSS
#
# Only signals when ALL THREE conditions occur within 10 bars.
# This dramatically reduces false signals vs individual SMC components.
#
# Reference: Inner Circle Trader methodology, LuxAlgo SMC automation
# =====================================================================

def ict_three_chain(data: dict[str, pd.DataFrame],
                    context: Optional[dict] = None) -> list[dict]:
    """
    ICT Sweep -> MSS -> FVG sequential filter.
    All 3 conditions must occur within 10 bars to generate a signal.
    Confidence fixed at 0.80 (triple-confirmed).
    """
    signals: list[dict] = []
    min_bars = 60
    swing_lookback = 5
    chain_window = 10  # all 3 events must occur within this many bars

    for symbol, info in CRYPTO_SYMBOLS.items():
        df = data.get(symbol)
        if df is None or len(df) < min_bars:
            continue

        close = df["Close"].values
        high = df["High"].values
        low = df["Low"].values
        open_arr = df["Open"].values if "Open" in df.columns else close.copy()
        n = len(close)

        # -- Step 1: Find swing points (last 40 bars) --
        swing_highs = []  # (index, price)
        swing_lows = []
        scan_start = max(swing_lookback, n - 40)
        for i in range(scan_start, n - swing_lookback):
            is_sh = all(high[i] >= high[i - j] and high[i] >= high[i + j]
                        for j in range(1, swing_lookback + 1))
            is_sl = all(low[i] <= low[i - j] and low[i] <= low[i + j]
                        for j in range(1, swing_lookback + 1))
            if is_sh:
                swing_highs.append((i, high[i]))
            if is_sl:
                swing_lows.append((i, low[i]))

        if not swing_highs and not swing_lows:
            continue

        direction = None
        sweep_bar = None
        sweep_level = None
        mss_bar = None
        fvg_bar = None
        fvg_mid = None

        # -- Check for bearish sweep (wick above swing high, close below) --
        # Then bullish MSS + bullish FVG = BUY setup
        for sh_idx, sh_price in swing_highs:
            # Look for bars after this swing high that sweep it
            for bar in range(sh_idx + 1, min(sh_idx + chain_window + 1, n)):
                if high[bar] > sh_price and close[bar] < sh_price:
                    # Bearish sweep detected at `bar`
                    # Now look for bullish MSS: price breaks above a prior swing high
                    for mss_candidate in range(bar + 1, min(bar + 6, n)):
                        # Check if close breaks above any swing high
                        for sh2_idx, sh2_price in swing_highs:
                            if sh2_idx < bar and close[mss_candidate] > sh2_price:
                                # Bullish MSS found
                                # Now look for bullish FVG after MSS
                                for fvg_candidate in range(mss_candidate, min(mss_candidate + 6, n - 0)):
                                    if fvg_candidate >= 2:
                                        # Bullish FVG: candle[i-2].high < candle[i].low
                                        if high[fvg_candidate - 2] < low[fvg_candidate]:
                                            # Check chain window
                                            if fvg_candidate - bar <= chain_window:
                                                direction = "BUY"
                                                sweep_bar = bar
                                                sweep_level = sh_price
                                                mss_bar = mss_candidate
                                                fvg_bar = fvg_candidate
                                                fvg_mid = (high[fvg_candidate - 2] + low[fvg_candidate]) / 2.0
                                                break
                                if direction:
                                    break
                        if direction:
                            break
                if direction:
                    break
            if direction:
                break

        # -- Check for bullish sweep (wick below swing low, close above) --
        # Then bearish MSS + bearish FVG = SELL setup
        if direction is None:
            for sl_idx, sl_price in swing_lows:
                for bar in range(sl_idx + 1, min(sl_idx + chain_window + 1, n)):
                    if low[bar] < sl_price and close[bar] > sl_price:
                        # Bullish sweep detected
                        # Look for bearish MSS: price breaks below a prior swing low
                        for mss_candidate in range(bar + 1, min(bar + 6, n)):
                            for sl2_idx, sl2_price in swing_lows:
                                if sl2_idx < bar and close[mss_candidate] < sl2_price:
                                    # Bearish MSS found
                                    # Look for bearish FVG: candle[i-2].low > candle[i].high
                                    for fvg_candidate in range(mss_candidate, min(mss_candidate + 6, n)):
                                        if fvg_candidate >= 2:
                                            if low[fvg_candidate - 2] > high[fvg_candidate]:
                                                if fvg_candidate - bar <= chain_window:
                                                    direction = "SELL"
                                                    sweep_bar = bar
                                                    sweep_level = sl_price
                                                    mss_bar = mss_candidate
                                                    fvg_bar = fvg_candidate
                                                    fvg_mid = (low[fvg_candidate - 2] + high[fvg_candidate]) / 2.0
                                                    break
                                    if direction:
                                        break
                            if direction:
                                break
                    if direction:
                        break
                if direction:
                    break

        if direction is None:
            continue

        # Only signal if the chain completed recently (within last 5 bars)
        if fvg_bar is not None and (n - 1 - fvg_bar) > 5:
            continue

        # Entry at FVG midpoint, or current price if FVG midpoint already passed
        entry_price = float(fvg_mid) if fvg_mid is not None else float(close[-1])
        entry_price = _smart_round(entry_price)

        # TP/SL: SL below/above sweep level, TP at 3R
        atr_val_now = float(atr(
            pd.Series(high), pd.Series(low), pd.Series(close), 14
        ).iloc[-1])

        if direction == "BUY":
            sl_price = _smart_round(float(sweep_level) - 0.5 * atr_val_now)
            risk = entry_price - sl_price
            tp_price = _smart_round(entry_price + 3.0 * max(risk, atr_val_now))
        else:
            sl_price = _smart_round(float(sweep_level) + 0.5 * atr_val_now)
            risk = sl_price - entry_price
            tp_price = _smart_round(entry_price - 3.0 * max(risk, atr_val_now))

        confidence = 0.80  # Fixed high confidence for triple-confirmed

        signals.append({
            "strategy": "ict_three_chain",
            "symbol": symbol,
            "direction": direction,
            "entry": entry_price,
            "tp": tp_price,
            "sl": sl_price,
            "confidence": confidence,
            "rationale": (
                f"ICT 3-chain: sweep at bar {sweep_bar} "
                f"(level={_smart_round(float(sweep_level))}), "
                f"MSS at bar {mss_bar}, "
                f"FVG at bar {fvg_bar} "
                f"(mid={entry_price}). "
                f"All within {chain_window}-bar window."
            ),
            "category": _get_category(symbol),
            "timestamp": _now_iso(),
            "tags": ["ict", "smc", "sweep-mss-fvg", "institutional", "tv-research"],
        })

    return signals


# =====================================================================
# Registry
# =====================================================================

TV_RESEARCH_STRATEGIES_W3: dict[str, callable] = {
    "lorentzian_classification": lorentzian_classification,
    "nadaraya_watson_envelope": nadaraya_watson_envelope,
    "volume_delta_divergence": volume_delta_divergence,
    "ict_three_chain": ict_three_chain,
}
