"""
System B: Regime Classifier for "The Regime".
XGBoost multi-class classifier for 4 market regimes:
  - trending_up: strong directional move upward
  - trending_down: strong directional move downward
  - range_bound: sideways consolidation (ADX low, vol normal)
  - high_volatility: explosive moves, wide bars, high ATR

Falls back to rule-based classification when no trained model exists.
"""
import os
import sys
import json
import numpy as np
import pandas as pd
import joblib
from typing import Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import indicators as ind

# --- Paths ---
MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
MODEL_PATH = os.path.join(MODEL_DIR, "regime_xgb.joblib")
SCALER_PATH = os.path.join(MODEL_DIR, "regime_scaler.joblib")

# --- Regime labels ---
REGIMES = ["trending_up", "trending_down", "range_bound", "high_volatility"]
REGIME_TO_INT = {r: i for i, r in enumerate(REGIMES)}
INT_TO_REGIME = {i: r for r, i in REGIME_TO_INT.items()}

# --- Feature names (16 core + 4 new = 20) ---
FEATURE_NAMES = [
    "adx",
    "plus_di",
    "minus_di",
    "ema20_slope",
    "bb_width_percentile",
    "atr_percentile",
    "hurst_exponent",
    "volume_trend",
    "fear_greed",
    "price_vs_ema50",
    "price_vs_ema200",
    "realized_vol_percentile",
    "consecutive_direction",
    "rsi_14",
    "hour_sin",
    "hour_cos",
    "rate_of_change_7",
    "cmf",
    "mfi",
    "obv_slope",
]


def compute_regime_features(
    df: pd.DataFrame,
    fear_greed: float = 50.0,
) -> np.ndarray:
    """
    Compute the 20-dimensional feature vector for regime classification
    from an OHLCV DataFrame.

    Args:
        df: DataFrame with columns [Open, High, Low, Close, Volume]
        fear_greed: Fear & Greed index value (0-100)

    Returns:
        np.ndarray of shape (20,)
    """
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]
    open_ = df["Open"]

    # ADX, +DI, -DI
    adx_val, plus_di, minus_di = ind.adx(high, low, close, 14)
    adx_now = float(adx_val.iloc[-1]) if not np.isnan(adx_val.iloc[-1]) else 20.0
    pdi_now = float(plus_di.iloc[-1]) if not np.isnan(plus_di.iloc[-1]) else 25.0
    mdi_now = float(minus_di.iloc[-1]) if not np.isnan(minus_di.iloc[-1]) else 25.0

    # EMA(20) slope: normalized change over last 5 bars
    ema20 = ind.ema(close, 20)
    if len(ema20) >= 6 and float(ema20.iloc[-6]) != 0:
        ema20_slope = (float(ema20.iloc[-1]) - float(ema20.iloc[-6])) / float(ema20.iloc[-6])
    else:
        ema20_slope = 0.0

    # Bollinger Band width percentile (over 60 bars)
    _, _, _, bb_width, _ = ind.bollinger_bands(close, 20, 2.0)
    if len(bb_width) >= 60:
        bb_w_now = float(bb_width.iloc[-1])
        bb_w_hist = bb_width.iloc[-60:]
        bb_width_pctile = float((bb_w_hist <= bb_w_now).mean())
    else:
        bb_width_pctile = 0.5

    # ATR percentile (over 60 bars)
    atr_val = ind.atr(high, low, close, 14)
    if len(atr_val) >= 60:
        atr_now = float(atr_val.iloc[-1])
        atr_hist = atr_val.iloc[-60:]
        atr_pctile = float((atr_hist <= atr_now).mean())
    else:
        atr_pctile = 0.5

    # Hurst exponent
    hurst = ind.hurst_exponent(close, max_lag=50)

    # Volume trend: slope of 20-bar volume SMA (normalized)
    vol_sma = ind.sma(volume, 20)
    if len(vol_sma) >= 10 and float(vol_sma.iloc[-10]) > 0:
        volume_trend = (float(vol_sma.iloc[-1]) - float(vol_sma.iloc[-10])) / float(vol_sma.iloc[-10])
    else:
        volume_trend = 0.0

    # Fear & Greed normalized to 0-1
    fg_norm = float(fear_greed) / 100.0

    # Price vs EMA50 ratio
    ema50 = ind.ema(close, 50)
    price_now = float(close.iloc[-1])
    ema50_now = float(ema50.iloc[-1]) if not np.isnan(ema50.iloc[-1]) else price_now
    price_vs_ema50 = price_now / ema50_now if ema50_now > 0 else 1.0

    # Price vs EMA200 ratio
    ema200 = ind.ema(close, 200) if len(close) >= 200 else ind.sma(close, min(len(close), 200))
    ema200_now = float(ema200.iloc[-1]) if not np.isnan(ema200.iloc[-1]) else price_now
    price_vs_ema200 = price_now / ema200_now if ema200_now > 0 else 1.0

    # Realized volatility percentile (over 60 bars)
    rv = ind.realized_volatility(close, 20)
    if len(rv) >= 60:
        rv_now = float(rv.iloc[-1]) if not np.isnan(rv.iloc[-1]) else 0.0
        rv_hist = rv.dropna().iloc[-60:]
        rv_pctile = float((rv_hist <= rv_now).mean()) if len(rv_hist) > 0 else 0.5
    else:
        rv_pctile = 0.5

    # Consecutive green/red bars (positive = green, negative = red)
    consecutive = 0
    for i in range(len(close) - 1, max(0, len(close) - 11), -1):
        if float(close.iloc[i]) > float(open_.iloc[i]):
            if consecutive >= 0:
                consecutive += 1
            else:
                break
        elif float(close.iloc[i]) < float(open_.iloc[i]):
            if consecutive <= 0:
                consecutive -= 1
            else:
                break
        else:
            break

    # RSI(14)
    rsi_val = ind.rsi(close, 14)
    rsi_now = float(rsi_val.iloc[-1]) if not np.isnan(rsi_val.iloc[-1]) else 50.0

    # Hour sin/cos encoding
    if hasattr(df.index[-1], "hour"):
        hour = df.index[-1].hour
    else:
        hour = 12
    hour_sin = np.sin(2 * np.pi * hour / 24)
    hour_cos = np.cos(2 * np.pi * hour / 24)

    # Rate of change (7-bar)
    roc = ind.rate_of_change(close, 7)
    roc_val = float(roc.iloc[-1]) if not np.isnan(roc.iloc[-1]) else 0.0

    # Chaikin Money Flow
    cmf = ind.chaikin_money_flow(high, low, close, volume)
    cmf_val = float(cmf.iloc[-1]) if not np.isnan(cmf.iloc[-1]) else 0.0

    # Money Flow Index (normalized 0-1)
    mfi_series = ind.mfi(high, low, close, volume)
    mfi_val = float(mfi_series.iloc[-1]) / 100.0 if not np.isnan(mfi_series.iloc[-1]) else 0.5

    # OBV slope (20-bar)
    obv_series = ind.obv(close, volume)
    if len(obv_series) >= 20:
        obv_recent = obv_series.iloc[-20:]
        obv_slope_val = float((obv_recent.iloc[-1] - obv_recent.iloc[0]) / (abs(obv_recent.iloc[0]) + 1e-10))
    else:
        obv_slope_val = 0.0

    features = np.array([
        adx_now,
        pdi_now,
        mdi_now,
        ema20_slope,
        bb_width_pctile,
        atr_pctile,
        hurst,
        volume_trend,
        fg_norm,
        price_vs_ema50,
        price_vs_ema200,
        rv_pctile,
        float(consecutive),
        rsi_now,
        hour_sin,
        hour_cos,
        roc_val,
        cmf_val,
        mfi_val,
        obv_slope_val,
    ], dtype=np.float64)

    return features


def rule_based_label(df: pd.DataFrame) -> str:
    """
    Assign a regime label using adaptive statistical thresholds.

    Primary method: 3-state HMM-inspired statistical regime detection using
    log returns, realized volatility, and volume ratio with rolling percentile
    thresholds (adaptive to recent market conditions).

    Fallback: ADX-based rules with lowered threshold (15 instead of 25) for crypto.

    Returns one of: "trending_up", "trending_down", "range_bound", "high_volatility"
    """
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"] if "Volume" in df.columns else None

    price_now = float(close.iloc[-1])

    # --- ATR percentile (high_volatility takes priority regardless of method) ---
    atr_val = ind.atr(high, low, close, 14)
    if len(atr_val) >= 60:
        atr_now = float(atr_val.iloc[-1])
        atr_pctile = float((atr_val.iloc[-60:] <= atr_now).mean())
    else:
        atr_pctile = 0.5

    if atr_pctile > 0.80:
        return "high_volatility"

    # --- Try HMM-based statistical regime detection ---
    regime = _hmm_regime_detect(df)
    if regime is not None:
        return regime

    # --- Adaptive statistical fallback (no hmmlearn) ---
    regime = _adaptive_statistical_regime(df)
    if regime is not None:
        return regime

    # --- Last resort: ADX-based with lowered threshold (15 for crypto) ---
    return _adx_fallback_label(df)


def _hmm_regime_detect(df: pd.DataFrame) -> Optional[str]:
    """
    3-state GaussianHMM regime detection.
    States are labeled by mean return: bull (highest), bear (lowest), range (middle).
    Returns None if hmmlearn is unavailable or insufficient data.
    """
    try:
        from hmmlearn.hmm import GaussianHMM
    except ImportError:
        return None

    close = df["Close"]
    volume = df["Volume"] if "Volume" in df.columns else None

    if len(close) < 60:
        return None

    # Features: log returns, realized vol (20d), volume ratio
    log_returns = np.log(close / close.shift(1))
    realized_vol = log_returns.rolling(20).std()

    if volume is not None and len(volume) >= 20:
        vol_sma = volume.rolling(20).mean()
        volume_ratio = volume / vol_sma.replace(0, np.nan)
    else:
        volume_ratio = pd.Series(1.0, index=close.index)

    features_df = pd.DataFrame({
        "log_returns": log_returns,
        "realized_vol": realized_vol,
        "volume_ratio": volume_ratio,
    }).dropna()

    if len(features_df) < 40:
        return None

    features = features_df.values

    try:
        model = GaussianHMM(
            n_components=3,
            covariance_type="full",
            n_iter=100,
            random_state=42,
        )
        model.fit(features)
        states = model.predict(features)

        # Label states by mean return
        state_means = {}
        for s in range(3):
            mask = states == s
            if mask.sum() > 0:
                state_means[s] = features[mask, 0].mean()  # mean of log_returns
            else:
                state_means[s] = 0.0

        sorted_states = sorted(state_means, key=state_means.get)
        # lowest = bear, middle = range, highest = bull
        label_map = {
            sorted_states[0]: "trending_down",
            sorted_states[1]: "range_bound",
            sorted_states[2]: "trending_up",
        }

        current_state = states[-1]
        return label_map[current_state]
    except Exception:
        return None


def _adaptive_statistical_regime(df: pd.DataFrame) -> Optional[str]:
    """
    Adaptive statistical regime detection using rolling percentiles.
    No fixed thresholds - everything is relative to recent history.

    Bull: returns > 0 AND vol below median AND momentum > 0 (adaptive)
    Bear: returns < 0 AND vol above median (adaptive)
    Range: everything else
    """
    close = df["Close"]
    volume = df["Volume"] if "Volume" in df.columns else None

    if len(close) < 40:
        return None

    # Compute features
    log_returns = np.log(close / close.shift(1)).dropna()
    if len(log_returns) < 30:
        return None

    # Rolling 20-bar return (smoothed direction signal)
    rolling_return = close.pct_change(20)
    # Realized vol 20d
    realized_vol = log_returns.rolling(20).std()
    # 10-bar momentum
    momentum = close.pct_change(10)

    # Get current values
    ret_now = float(rolling_return.iloc[-1]) if not np.isnan(rolling_return.iloc[-1]) else 0.0
    vol_now = float(realized_vol.iloc[-1]) if not np.isnan(realized_vol.iloc[-1]) else 0.0
    mom_now = float(momentum.iloc[-1]) if not np.isnan(momentum.iloc[-1]) else 0.0

    # Adaptive thresholds: use rolling percentiles over last 60 bars
    lookback = min(60, len(realized_vol.dropna()))
    vol_recent = realized_vol.dropna().iloc[-lookback:]
    ret_recent = rolling_return.dropna().iloc[-lookback:]

    vol_median = float(vol_recent.median()) if len(vol_recent) > 0 else vol_now
    ret_p25 = float(ret_recent.quantile(0.25)) if len(ret_recent) > 0 else -0.01
    ret_p75 = float(ret_recent.quantile(0.75)) if len(ret_recent) > 0 else 0.01

    # Volume confirmation (if available)
    vol_confirmed = True
    if volume is not None and len(volume) >= 20:
        vol_sma = volume.rolling(20).mean()
        vol_ratio = float(volume.iloc[-1]) / float(vol_sma.iloc[-1]) if float(vol_sma.iloc[-1]) > 0 else 1.0
    else:
        vol_ratio = 1.0

    # Bull: strong positive return, below-median vol, positive momentum
    if ret_now > ret_p75 and vol_now <= vol_median and mom_now > 0:
        return "trending_up"

    # Bear: strong negative return, above-median vol
    if ret_now < ret_p25 and vol_now > vol_median:
        return "trending_down"

    # Mild trending: positive return with momentum (doesn't need low vol)
    if ret_now > 0 and mom_now > 0 and vol_ratio > 0.8:
        return "trending_up"

    # Mild bearish: negative return with negative momentum
    if ret_now < 0 and mom_now < 0 and vol_ratio > 0.8:
        return "trending_down"

    return "range_bound"


def _adx_fallback_label(df: pd.DataFrame) -> str:
    """
    ADX-based regime detection with lowered threshold (15) for crypto markets.
    Original used 25 which was too strict - crypto ADX often sits at 15-20 during
    clear trends due to higher baseline volatility.
    """
    close = df["Close"]
    high = df["High"]
    low = df["Low"]

    # ADX
    adx_val, _, _ = ind.adx(high, low, close, 14)
    adx_now = float(adx_val.iloc[-1]) if not np.isnan(adx_val.iloc[-1]) else 20.0

    # EMA50
    ema50 = ind.ema(close, 50)
    ema50_now = float(ema50.iloc[-1]) if not np.isnan(ema50.iloc[-1]) else float(close.iloc[-1])
    price_now = float(close.iloc[-1])

    # Higher highs / lower lows over last 5 bars
    if len(high) >= 6:
        curr_high = float(high.iloc[-1])
        prev_max_high = float(high.iloc[-6:-1].max())
        curr_low = float(low.iloc[-1])
        prev_min_low = float(low.iloc[-6:-1].min())
        higher_highs = curr_high > prev_max_high
        lower_lows = curr_low < prev_min_low
    else:
        higher_highs = False
        lower_lows = False

    # Lowered ADX threshold from 25 to 15 for crypto
    if adx_now > 15 and price_now > ema50_now and higher_highs:
        return "trending_up"

    if adx_now > 15 and price_now < ema50_now and lower_lows:
        return "trending_down"

    return "range_bound"


def label_series(df: pd.DataFrame, lookback_min: int = 60) -> pd.Series:
    """
    Label each bar in the DataFrame with a regime using rule_based_label.
    Returns a pd.Series of regime strings aligned with df.index.

    Bars before lookback_min are labeled NaN (insufficient data).
    """
    labels = pd.Series(index=df.index, dtype="object")

    for i in range(lookback_min, len(df)):
        slice_df = df.iloc[:i + 1]
        try:
            labels.iloc[i] = rule_based_label(slice_df)
        except Exception:
            labels.iloc[i] = "range_bound"

    return labels


def classify(
    df: pd.DataFrame,
    fear_greed: float = 50.0,
) -> Tuple[str, float, int]:
    """
    Classify the current market regime with transition smoothing.

    Returns:
        (regime_name, confidence, regime_duration) where:
        - confidence is 0.0 - 1.0
        - regime_duration is how many consecutive bars in this regime
    Falls back to rule-based classification when no trained model exists.
    """
    # EXTREME FEAR MODE (Feb 26 2026 fix):
    # OLD: F&G<15 forced trending_down at 90% conf, which blocked ALL BUYs via
    # regime directional filter. Combined with health gate blocking all SELLs,
    # this produced ZERO picks — a total deadlock.
    # NEW: F&G<15 still classifies as trending_down but with LOWER confidence (55%)
    # so the directional filter (which requires >=70% conf) won't block BUYs.
    # This lets the health gate decide (it allows BUYs >=0.55 conf at 50% size).
    # Historically, extreme fear IS the best time to buy (contrarian edge).
    if fear_greed < 15:
        print(f"  [Regime] F&G={fear_greed} < 15: trending_down (RELAXED conf=55%, extreme fear mode)")
        return "trending_down", 0.55, 0
    if fear_greed > 85:
        print(f"  [Regime] F&G={fear_greed} > 85: FORCED trending_up (override)")
        return "trending_up", 0.90, 0

    # Try ML model first
    if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
        try:
            model = joblib.load(MODEL_PATH)
            scaler = joblib.load(SCALER_PATH)

            features = compute_regime_features(df, fear_greed)
            X = scaler.transform(features.reshape(1, -1))
            probs = model.predict_proba(X)[0]
            predicted_class = int(np.argmax(probs))
            confidence = float(probs[predicted_class])

            regime = INT_TO_REGIME.get(predicted_class, "range_bound")
            return smooth_regime(regime, confidence)
        except Exception as e:
            print(f"[Regime] ML model failed, falling back to rules: {e}")

    # Rule-based fallback
    regime = rule_based_label(df)
    confidence = _rule_based_confidence(df, regime)

    return smooth_regime(regime, confidence)


def _rule_based_confidence(df: pd.DataFrame, regime: str) -> float:
    """
    Estimate confidence for rule-based regime classification.
    Higher confidence when indicators strongly agree.
    """
    close = df["Close"]
    high = df["High"]
    low = df["Low"]

    adx_val, plus_di, minus_di = ind.adx(high, low, close, 14)
    adx_now = float(adx_val.iloc[-1]) if not np.isnan(adx_val.iloc[-1]) else 20.0

    atr_val = ind.atr(high, low, close, 14)
    if len(atr_val) >= 60:
        atr_now = float(atr_val.iloc[-1])
        atr_pctile = float((atr_val.iloc[-60:] <= atr_now).mean())
    else:
        atr_pctile = 0.5

    if regime == "trending_up":
        # Confidence scales with ADX strength and DI spread (lowered threshold to 15)
        pdi = float(plus_di.iloc[-1]) if not np.isnan(plus_di.iloc[-1]) else 25
        mdi = float(minus_di.iloc[-1]) if not np.isnan(minus_di.iloc[-1]) else 25
        di_spread = max(0, pdi - mdi)
        confidence = min(0.90, 0.50 + (adx_now - 15) * 0.01 + di_spread * 0.005)
    elif regime == "trending_down":
        pdi = float(plus_di.iloc[-1]) if not np.isnan(plus_di.iloc[-1]) else 25
        mdi = float(minus_di.iloc[-1]) if not np.isnan(minus_di.iloc[-1]) else 25
        di_spread = max(0, mdi - pdi)
        confidence = min(0.90, 0.50 + (adx_now - 15) * 0.01 + di_spread * 0.005)
    elif regime == "high_volatility":
        # Confidence scales with how extreme ATR percentile is
        confidence = min(0.90, 0.50 + (atr_pctile - 0.80) * 2.0)
    else:
        # range_bound: confidence higher when ADX is low and vol is normal
        adx_factor = max(0, 20 - adx_now) * 0.015
        vol_factor = max(0, 0.50 - abs(atr_pctile - 0.50)) * 0.5
        confidence = min(0.85, 0.45 + adx_factor + vol_factor)

    return max(0.30, confidence)


# --- Regime Persistence / Smoothing ---
_REGIME_HISTORY_PATH = os.path.join(os.path.dirname(__file__), "data", "regime_history.json")


def _load_regime_history() -> list:
    """Load recent regime classifications for smoothing."""
    if os.path.exists(_REGIME_HISTORY_PATH):
        try:
            with open(_REGIME_HISTORY_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_regime_history(history: list):
    """Save regime history (keep last 20 entries)."""
    os.makedirs(os.path.dirname(_REGIME_HISTORY_PATH), exist_ok=True)
    with open(_REGIME_HISTORY_PATH, "w") as f:
        json.dump(history[-20:], f)


def smooth_regime(raw_regime: str, confidence: float, min_persistence: int = 3) -> tuple:
    """
    Prevent regime whipsaws by requiring min_persistence consecutive
    bars of a new regime before switching.

    Returns (smoothed_regime, smoothed_confidence, regime_duration)
    """
    history = _load_regime_history()

    # Add current reading
    history.append({"regime": raw_regime, "confidence": confidence})
    _save_regime_history(history)

    if len(history) < min_persistence:
        return raw_regime, confidence, len(history)

    # Check if last N readings all agree on a different regime than the previous stable one
    recent = [h["regime"] for h in history[-min_persistence:]]

    if len(set(recent)) == 1:
        # All recent readings agree -- this is the current regime
        current_regime = recent[0]
        avg_conf = np.mean([h["confidence"] for h in history[-min_persistence:]])

        # Count consecutive bars of this regime for duration
        duration = 0
        for h in reversed(history):
            if h["regime"] == current_regime:
                duration += 1
            else:
                break

        return current_regime, float(avg_conf), duration
    else:
        # No consensus -- stick with the most recent stable regime
        # Find the last regime that persisted for >= min_persistence
        for i in range(len(history) - min_persistence, -1, -1):
            window = [h["regime"] for h in history[i:i + min_persistence]]
            if len(set(window)) == 1:
                stable_regime = window[0]
                return stable_regime, confidence * 0.8, 0  # lower confidence during transition

        # No stable regime found -- use current reading
        return raw_regime, confidence * 0.7, 0
