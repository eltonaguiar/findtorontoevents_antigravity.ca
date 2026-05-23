"""
ML Context Filter for System A.
Scores each raw signal as "take" (1) or "skip" (0).
Falls back to heuristic when no trained model available.
"""
import os
import sys
import numpy as np
import joblib
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import indicators as ind
from shared.sr_engine import nearest_support, nearest_resistance

MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "filter_xgb.joblib")
SCALER_PATH = os.path.join(os.path.dirname(__file__), "models", "filter_scaler.joblib")
CALIBRATION_PATH = os.path.join(os.path.dirname(__file__), "models", "filter_xgb_calibration.joblib")

# ── Integration: Cross-Sectional Momentum (Liu et al. 2022 JFE) ─────
# Expected improvement: +0.3–0.5 Sharpe when added as LightGBM/XGBoost features.
#
# To integrate (separate step — requires model retraining):
#   1. Add these 4 names to FEATURE_NAMES below:
#        "momentum_7d_rank",
#        "momentum_30d_rank",
#        "momentum_7d_zscore",
#        "relative_strength_vs_btc",
#
#   2. In compute_filter_features(), import and compute:
#        from battleground.features.cross_sectional_momentum import (
#            compute_cross_sectional_momentum,
#        )
#        cs_mom = compute_cross_sectional_momentum(signal.get("symbol", "BTCUSDT"))
#        cs_features = cs_mom.to_list()
#
#   3. Append cs_features to the feature vector:
#        features = [...existing...] + strat_features + [close_ffd_val] + cs_features
#
#   4. Retrain filter_xgb.joblib with the expanded 42-feature set.
# ─────────────────────────────────────────────────────────────────────

FEATURE_NAMES = [
    "dist_to_support_pct",
    "dist_to_resistance_pct",
    "sr_support_strength",
    "sr_resistance_strength",
    "sr_spread_pct",
    "volume_ratio_20",
    "rsi_14",
    "atr_percentile",
    "fear_greed",
    "funding_rate",
    "hour_sin",
    "hour_cos",
    "btc_correlation",
    "btc_return_1h",
    "consecutive_green",
    "bollinger_pctb",
    "macd_histogram",
    "obv_slope",
    "volume_climax_ratio",
    "realized_vol_20",
    "rate_of_change_7",
    "price_vs_ema200",
    "chaikin_mf",
    "mfi_14",
    "linear_reg_slope",
    "hurst",
    "strategy_supertrend",
    "strategy_connors",
    "strategy_squeeze",
    "strategy_rsi_macd",
    "strategy_ema_stack",
    "strategy_volume_climax",
    "strategy_sfp",
    "strategy_ou",
    "strategy_rsi_bb_macd",
    "strategy_supertrend_vol",
    "strategy_funding_extreme",
    # Fractional differentiation — Lopez de Prado, AFML Ch.5
    "close_ffd",
]


def compute_filter_features(
    signal: dict,
    sr_levels: list,
    df,
    fear_greed: int = 50,
    funding_rate: float = 0.0,
    btc_return_1h: float = 0.0,
) -> np.ndarray:
    """Compute feature vector for the ML filter."""
    price = signal["entry_price"]
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    # S/R features
    sup = nearest_support(sr_levels, price)
    res = nearest_resistance(sr_levels, price)
    dist_sup = (price - sup.price) / price if sup else 0.05
    dist_res = (res.price - price) / price if res else 0.05
    sup_strength = sup.strength if sup else 0.0
    res_strength = res.strength if res else 0.0
    sr_spread = dist_sup + dist_res

    # Technical features
    vol_ratio = float(volume.iloc[-1] / volume.rolling(20).mean().iloc[-1]) if volume.rolling(20).mean().iloc[-1] > 0 else 1.0
    rsi_val = float(ind.rsi(close).iloc[-1])
    atr_val = ind.atr(high, low, close)
    atr_pctile = float((atr_val.iloc[-1] <= atr_val.tail(60)).mean()) if len(atr_val) >= 60 else 0.5
    _, _, _, _, pctb = ind.bollinger_bands(close)
    pctb_val = float(pctb.iloc[-1]) if not np.isnan(pctb.iloc[-1]) else 0.5

    # Time features
    hour = df.index[-1].hour if hasattr(df.index[-1], 'hour') else 12
    hour_sin = np.sin(2 * np.pi * hour / 24)
    hour_cos = np.cos(2 * np.pi * hour / 24)

    # BTC correlation — compute from actual price data when available
    btc_corr = 0.5  # default fallback
    if len(close) >= 20:
        try:
            import yfinance as yf
            btc = yf.download("BTC-USD", period="60d", interval="1h",
                              progress=False, auto_adjust=True)
            if btc is not None and len(btc) >= 20:
                # Align lengths and compute rolling correlation
                n = min(len(close), len(btc["Close"]))
                if n >= 20:
                    btc_returns = btc["Close"].pct_change().dropna().tail(n - 1)
                    asset_returns = close.pct_change().dropna().tail(n - 1)
                    min_len = min(len(btc_returns), len(asset_returns))
                    if min_len >= 20:
                        corr = float(np.corrcoef(
                            btc_returns.values[-min_len:],
                            asset_returns.values[-min_len:]
                        )[0, 1])
                        if not np.isnan(corr):
                            btc_corr = corr
        except Exception:
            pass  # keep fallback 0.5

    # Consecutive green candles
    greens = 0
    for i in range(len(close) - 1, max(0, len(close) - 11), -1):
        if close.iloc[i] > df["Open"].iloc[i]:
            greens += 1
        else:
            break

    # MACD histogram (normalized by price)
    _, _, macd_hist = ind.macd(close)
    macd_hist_val = float(macd_hist.iloc[-1]) / price if price > 0 else 0.0

    # OBV slope (20-bar normalized)
    obv_series = ind.obv(close, volume)
    if len(obv_series) >= 20:
        obv_recent = obv_series.iloc[-20:]
        obv_slope = float((obv_recent.iloc[-1] - obv_recent.iloc[0]) / (abs(obv_recent.iloc[0]) + 1e-10))
    else:
        obv_slope = 0.0

    # Volume climax ratio (current bar vs 60-bar max)
    vol_max_60 = float(volume.tail(60).max()) if len(volume) >= 60 else float(volume.max())
    vol_climax = float(volume.iloc[-1]) / vol_max_60 if vol_max_60 > 0 else 0.0

    # Realized volatility (20-bar, annualized)
    rv = ind.realized_volatility(close, 20)
    rv_val = float(rv.iloc[-1]) if not np.isnan(rv.iloc[-1]) else 0.0

    # Rate of change (7-bar momentum)
    roc = ind.rate_of_change(close, 7)
    roc_val = float(roc.iloc[-1]) if not np.isnan(roc.iloc[-1]) else 0.0

    # Price vs EMA(200)
    ema200 = ind.ema(close, 200) if len(close) >= 200 else ind.sma(close, min(len(close), 200))
    ema200_val = float(ema200.iloc[-1]) if not np.isnan(ema200.iloc[-1]) else price
    price_vs_ema200 = price / ema200_val if ema200_val > 0 else 1.0

    # Chaikin Money Flow
    cmf = ind.chaikin_money_flow(high, low, close, volume)
    cmf_val = float(cmf.iloc[-1]) if not np.isnan(cmf.iloc[-1]) else 0.0

    # Money Flow Index
    mfi_series = ind.mfi(high, low, close, volume)
    mfi_val = float(mfi_series.iloc[-1]) / 100.0 if not np.isnan(mfi_series.iloc[-1]) else 0.5

    # Linear regression slope
    lr_slope = ind.linear_regression_slope(close, 20)
    lr_slope_val = float(lr_slope.iloc[-1]) if not np.isnan(lr_slope.iloc[-1]) else 0.0

    # Hurst exponent
    hurst_val = ind.hurst_exponent(close)

    # Fractional differentiation — Lopez de Prado, AFML Ch.5
    # FFD with d=0.4: preserves memory while achieving stationarity
    close_ffd_val = 0.0
    try:
        from crypto_ml_edge.features.fracdiff import frac_diff_ffd
        ffd_series = frac_diff_ffd(close, d=0.4)
        last_val = ffd_series.iloc[-1]
        if not np.isnan(last_val):
            close_ffd_val = float(last_val)
    except Exception:
        try:
            from cross_aggregation.frac_diff import frac_diff_ffd as _frac_diff_ffd
            ffd_series = _frac_diff_ffd(close, d=0.4)
            last_val = ffd_series.iloc[-1]
            if not np.isnan(last_val):
                close_ffd_val = float(last_val)
        except Exception:
            pass  # graceful fallback — feature stays 0.0

    # Strategy one-hot
    strat = signal.get("strategy", "")
    strat_features = [
        1.0 if "supertrend" in strat and "volume" not in strat else 0.0,
        1.0 if "connors" in strat else 0.0,
        1.0 if "squeeze" in strat else 0.0,
        1.0 if "rsi_macd" in strat and "bb" not in strat else 0.0,
        1.0 if "ema_stack" in strat else 0.0,
        1.0 if "volume_climax" in strat else 0.0,
        1.0 if "swing_failure" in strat or "sfp" in strat else 0.0,
        1.0 if "ornstein" in strat or "ou" in strat else 0.0,
        1.0 if "rsi_bb_macd" in strat else 0.0,
        1.0 if "supertrend_volume" in strat else 0.0,
        1.0 if "funding_rate" in strat else 0.0,
    ]

    features = [
        dist_sup, dist_res, sup_strength, res_strength, sr_spread,
        vol_ratio, rsi_val, atr_pctile, fear_greed / 100.0, funding_rate,
        hour_sin, hour_cos, btc_corr, btc_return_1h, float(greens), pctb_val,
        macd_hist_val, obv_slope, vol_climax, rv_val, roc_val,
        price_vs_ema200, cmf_val, mfi_val, lr_slope_val, hurst_val,
    ] + strat_features + [close_ffd_val]

    return np.array(features, dtype=np.float64)


def predict(features: np.ndarray) -> tuple[float, str]:
    """
    Predict whether to take a signal.
    Returns (score 0-1, method "ml"|"heuristic"|"bootstrap").

    During bootstrap phase (< MIN_CLOSED_FOR_ML closed picks), uses heuristic
    scoring to allow signals through for forward-testing data collection.
    Once enough closed picks exist, the ML model is retrained on real outcomes
    and used for filtering.
    """
    # Check if we have enough closed picks to trust the ML model
    min_closed = int(os.environ.get("SYSTEM_A_MIN_CLOSED_FOR_ML", "15"))
    closed_path = os.path.join(os.path.dirname(__file__), "data", "closed_picks.json")
    n_closed = 0
    if os.path.exists(closed_path):
        try:
            import json
            with open(closed_path) as f:
                n_closed = len(json.load(f))
        except Exception:
            pass

    # Bootstrap phase: use heuristic (generous) to collect forward-test data
    if n_closed < min_closed:
        heuristic = _heuristic_score(features)
        return heuristic, "bootstrap"

    # Production phase: use trained ML model if available
    if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
        try:
            from shared.model_calibration import CalibratedModelWrapper
            scaler = joblib.load(SCALER_PATH)
            X = scaler.transform(features.reshape(1, -1))
            wrapper = CalibratedModelWrapper.load(MODEL_PATH, CALIBRATION_PATH)
            prob = float(wrapper.predict_proba(X)[0][1])
            method = "ml_calibrated" if wrapper.is_calibrated else "ml"
            return prob, method
        except Exception:
            pass

    # Final fallback
    return _heuristic_score(features), "heuristic"


def _heuristic_score(features: np.ndarray) -> float:
    """Rule-based scoring when no ML model available.
    Raised baseline and harder penalties to stop garbage picks."""
    score = 0.60  # raised from 0.55 — must earn passage through bonuses

    dist_sup = features[0]
    dist_res = features[1]
    sup_strength = features[2]
    rsi_val = features[6]
    vol_ratio = features[5]
    atr_pctile = features[7]

    # Close to strong support = good for BUY
    if dist_sup < 0.03 and sup_strength >= 2:
        score += 0.12
    # Good R:R (far resistance, close support)
    if dist_res > 1.5 * dist_sup and dist_sup > 0:
        score += 0.08
    # Oversold RSI (bullish bias)
    if rsi_val < 40:
        score += 0.08
    # Overbought RSI (bearish bias — still valid for SELL signals)
    if rsi_val > 60:
        score += 0.05
    # Volume confirmation
    if vol_ratio > 1.2:
        score += 0.05
    # Volume below median — harder penalty (was 0.05, now 0.10)
    if vol_ratio < 1.0:
        score -= 0.10
    # ATR below 20th percentile (low volatility) — no movement to profit from
    if atr_pctile < 0.20:
        score -= 0.08
    # S/R levels exist (any strength)
    if sup_strength > 0 or features[3] > 0:
        score += 0.03
    # F&G awareness (context-dependent, NOT a blanket penalty)
    # Old bug: penalized BUY -0.15 in extreme fear, contradicting the scanner's
    # contrarian BUY bias (+0.10). Net effect was random. Now: the scanner handles
    # directionality (F&G < 15 = BUY only, F&G > 80 = SELL only). The heuristic
    # should NOT second-guess the scanner's directional filter — just reward
    # strong conviction and penalize lukewarm signals.
    fg = features[8]  # fear_greed / 100.0
    if fg < 0.15 or fg > 0.85:
        # Extreme conditions: only high-quality signals should pass (scanner already
        # filtered direction). Reward strong technical setup, penalize weak ones.
        if vol_ratio > 1.5 and (rsi_val < 30 or rsi_val > 70):
            score += 0.08  # Strong reversal setup in extreme conditions
        elif vol_ratio < 0.8:
            score -= 0.10  # Weak volume in extreme conditions = noise

    return max(0.0, min(1.0, score))
