#!/usr/bin/env python3
"""
Regime Detector — HMM + Hurst + Macro Overlay for market regime classification.

Implements the hierarchical regime detection layer from the World-Class Algorithm Architecture:
  1. HMM (3 states: bull, sideways, bear) on returns + volatility
  2. Hurst Exponent (trending vs mean-reverting vs random)
  3. Macro Overlay (yield curve, VIX term structure)

Output: Composite regime score (0-100) + strategy toggles.
Posts results to PHP API for DB storage and live-monitor consumption.

Requires: pip install yfinance hmmlearn numpy pandas requests
"""
import sys
import os
import json
import logging
import numpy as np
import pandas as pd
import warnings

warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import post_to_api, call_api, safe_request, RateLimiter
from config import API_BASE, ADMIN_KEY, TRACKED_TICKERS

logger = logging.getLogger('regime_detector')


# ---------------------------------------------------------------------------
# HMM Regime Detection
# ---------------------------------------------------------------------------

class HMMRegimeDetector:
    """
    Gaussian HMM with 3 latent states on daily returns + rolling volatility.
    States are auto-labeled by mean return: bull > sideways > bear.
    """

    def __init__(self, n_states=3, lookback_days=252):
        self.n_states = n_states
        self.lookback = lookback_days
        self.model = None
        self.regime_map = {}

    def fit_predict(self, returns, volatility):
        """Fit HMM and predict current state."""
        from hmmlearn.hmm import GaussianHMM

        X = np.column_stack([returns, volatility])

        # Use last N days
        X = X[-self.lookback:]
        X = X[~np.isnan(X).any(axis=1)]

        if len(X) < 60:
            logger.warning("Not enough data for HMM (%d rows)", len(X))
            return 'sideways', 0.5, 50

        model = GaussianHMM(
            n_components=self.n_states,
            covariance_type="full",
            n_iter=200,
            random_state=42,
            tol=0.01
        )

        try:
            model.fit(X)
        except Exception as e:
            logger.error("HMM fit failed: %s", e)
            return 'sideways', 0.5, 50

        self.model = model

        # Label states by mean return (descending)
        means = model.means_[:, 0]
        state_order = np.argsort(means)[::-1]
        labels = ['bull', 'sideways', 'bear']
        self.regime_map = {state_order[i]: labels[i] for i in range(self.n_states)}

        # Predict current state
        X_recent = X[-5:]  # Use last 5 days for smoother prediction
        states = model.predict(X_recent)
        probs = model.predict_proba(X_recent)

        current_state = states[-1]
        current_prob = float(probs[-1].max())
        regime_label = self.regime_map.get(current_state, 'sideways')

        # Transition probabilities (useful for detecting regime changes)
        trans_mat = model.transmat_
        persistence = float(trans_mat[current_state, current_state])

        logger.info("HMM regime: %s (confidence=%.2f, persistence=%.2f)",
                     regime_label, current_prob, persistence)
        logger.info("HMM state means: %s", {self.regime_map[i]: round(float(means[i]) * 100, 3)
                                              for i in range(self.n_states)})

        return regime_label, current_prob, persistence


# ---------------------------------------------------------------------------
# Hurst Exponent
# ---------------------------------------------------------------------------

def compute_hurst(prices, max_lag=100):
    """
    Compute Hurst exponent using rescaled range (R/S) analysis.
    H > 0.55: trending (momentum works)
    H < 0.45: mean-reverting (reversion works)
    0.45-0.55: random walk (be cautious)
    """
    prices = np.array(prices, dtype=float)
    prices = prices[~np.isnan(prices)]

    if len(prices) < 50:
        logger.warning("Not enough data for Hurst (%d points)", len(prices))
        return 0.5, 'random'

    # R/S analysis
    lags = range(10, min(max_lag, len(prices) // 4))
    rs_values = []
    lag_values = []

    for lag in lags:
        n_segments = len(prices) // lag
        if n_segments < 2:
            continue

        rs_list = []
        for seg in range(n_segments):
            segment = prices[seg * lag:(seg + 1) * lag]
            returns = np.diff(np.log(segment + 1e-10))

            if len(returns) < 2:
                continue

            mean_ret = np.mean(returns)
            deviations = np.cumsum(returns - mean_ret)
            R = np.max(deviations) - np.min(deviations)
            S = np.std(returns, ddof=1)

            if S > 1e-10:
                rs_list.append(R / S)

        if rs_list:
            rs_values.append(np.log(np.mean(rs_list)))
            lag_values.append(np.log(lag))

    if len(lag_values) < 3:
        return 0.5, 'random'

    # Linear regression: log(R/S) = H * log(n) + c
    lag_arr = np.array(lag_values)
    rs_arr = np.array(rs_values)
    H = float(np.polyfit(lag_arr, rs_arr, 1)[0])

    # Clamp to valid range
    H = max(0.0, min(1.0, H))

    if H > 0.55:
        regime = 'trending'
    elif H < 0.45:
        regime = 'mean_reverting'
    else:
        regime = 'random'

    logger.info("Hurst exponent: %.3f (%s)", H, regime)
    return H, regime


# ---------------------------------------------------------------------------
# Macro Overlay (VIX + Yield Curve)
# ---------------------------------------------------------------------------

def fetch_macro_overlay():
    """
    Fetch macro indicators for regime modulation.
    - VIX level + term structure (contango/backwardation)
    - Yield curve (10Y-2Y spread)
    - DXY strength
    """
    import yfinance as yf

    macro = {
        'vix_level': None,
        'vix_regime': 'normal',
        'yield_curve': 'normal',
        'yield_spread': None,
        'dxy_strength': 'neutral',
        'macro_score': 50  # 0-100, higher = more bullish
    }

    # VIX
    try:
        vix = yf.download('^VIX', period='30d', interval='1d', progress=False)
        if len(vix) > 0:
            current_vix = float(vix['Close'].iloc[-1])
            vix_sma20 = float(vix['Close'].rolling(20).mean().iloc[-1]) if len(vix) >= 20 else current_vix
            macro['vix_level'] = current_vix

            if current_vix > 30:
                macro['vix_regime'] = 'fear'  # High fear
            elif current_vix > 20:
                macro['vix_regime'] = 'elevated'
            elif current_vix < 13:
                macro['vix_regime'] = 'complacent'  # Watch for spike
            else:
                macro['vix_regime'] = 'normal'

            # VIX mean reversion signal
            if current_vix > vix_sma20 * 1.2:
                macro['vix_regime'] = 'fear_peak'  # Potential buy signal
            elif current_vix < vix_sma20 * 0.8:
                macro['vix_regime'] = 'complacent'

            logger.info("VIX: %.1f (regime=%s, SMA20=%.1f)", current_vix, macro['vix_regime'], vix_sma20)
    except Exception as e:
        logger.warning("VIX fetch failed: %s", e)

    # Yield Curve (10Y - 2Y treasury spread)
    try:
        tnx = yf.download('^TNX', period='5d', interval='1d', progress=False)  # 10Y
        t2y = yf.download('2YY=F', period='5d', interval='1d', progress=False)  # 2Y

        if len(tnx) > 0 and len(t2y) > 0:
            spread = float(tnx['Close'].iloc[-1]) - float(t2y['Close'].iloc[-1])
            macro['yield_spread'] = spread

            if spread < -0.5:
                macro['yield_curve'] = 'deeply_inverted'
            elif spread < 0:
                macro['yield_curve'] = 'inverted'
            elif spread < 0.5:
                macro['yield_curve'] = 'flat'
            else:
                macro['yield_curve'] = 'normal'

            logger.info("Yield curve: %.2f bps (%s)", spread * 100, macro['yield_curve'])
    except Exception as e:
        logger.warning("Yield curve fetch failed: %s", e)

    # Calculate macro score
    score = 50  # Neutral baseline

    # VIX impact
    vix_scores = {
        'fear_peak': 65,       # Contrarian buy signal
        'fear': 30,            # Risk-off
        'elevated': 40,
        'normal': 55,
        'complacent': 45       # Potential mean-revert risk
    }
    score += (vix_scores.get(macro['vix_regime'], 50) - 50)

    # Yield curve impact
    yc_scores = {
        'deeply_inverted': -15,
        'inverted': -10,
        'flat': -5,
        'normal': 5
    }
    score += yc_scores.get(macro['yield_curve'], 0)

    macro['macro_score'] = max(0, min(100, score))
    return macro


# ---------------------------------------------------------------------------
# EWMA Volatility Forecaster
# ---------------------------------------------------------------------------

def ewma_volatility(returns, decay=0.94):
    """
    Exponentially Weighted Moving Average volatility.
    More responsive than simple rolling vol, robust out-of-sample.
    Better than GARCH for our use case (no parameter instability).
    """
    returns = np.array(returns, dtype=float)
    returns = returns[~np.isnan(returns)]

    if len(returns) < 10:
        return 0.02  # Default 2% daily vol

    variance = returns[0] ** 2
    for r in returns[1:]:
        variance = decay * variance + (1 - decay) * (r ** 2)

    return float(np.sqrt(variance))


# ---------------------------------------------------------------------------
# Per-Ticker Regime Analysis
# ---------------------------------------------------------------------------

def analyze_ticker_regime(ticker, spy_data=None):
    """
    Run regime analysis for individual ticker.
    Returns: dict with hurst, vol, trend info.
    """
    import yfinance as yf

    try:
        df = yf.download(ticker, period='1y', interval='1d', progress=False)
        if len(df) < 50:
            return None
    except Exception as e:
        logger.warning("Ticker %s fetch failed: %s", ticker, e)
        return None

    closes = df['Close'].values.flatten()
    returns = np.diff(np.log(closes))

    # Hurst
    H, hurst_regime = compute_hurst(closes[-250:])

    # EWMA vol
    vol = ewma_volatility(returns[-60:])
    vol_annualized = vol * np.sqrt(252)

    # Trend strength (price vs SMA50/SMA200)
    sma50 = np.mean(closes[-50:]) if len(closes) >= 50 else closes[-1]
    sma200 = np.mean(closes[-200:]) if len(closes) >= 200 else sma50
    price = closes[-1]

    trend_score = 0
    if price > sma50:
        trend_score += 25
    if price > sma200:
        trend_score += 25
    if sma50 > sma200:
        trend_score += 25  # Golden cross
    # Momentum: above mid-point of 52w range
    high_52w = np.max(closes[-252:]) if len(closes) >= 252 else np.max(closes)
    low_52w = np.min(closes[-252:]) if len(closes) >= 252 else np.min(closes)
    mid_52w = (high_52w + low_52w) / 2
    if price > mid_52w:
        trend_score += 25

    # Strategy recommendation based on Hurst
    if hurst_regime == 'trending':
        strategies = ['momentum', 'breakout', 'trend_following']
    elif hurst_regime == 'mean_reverting':
        strategies = ['mean_reversion', 'rsi_reversal', 'bollinger']
    else:
        strategies = ['all']  # Random walk — diversify

    return {
        'ticker': ticker,
        'hurst': round(H, 4),
        'hurst_regime': hurst_regime,
        'ewma_vol': round(vol, 6),
        'vol_annualized': round(vol_annualized, 4),
        'trend_score': trend_score,
        'sma50': round(float(sma50), 2),
        'sma200': round(float(sma200), 2),
        'price': round(float(price), 2),
        'recommended_strategies': strategies
    }


# ---------------------------------------------------------------------------
# Composite Regime Score
# ---------------------------------------------------------------------------

def calculate_composite_score(hmm_regime, hmm_confidence, hurst_regime, hurst_value, macro):
    """
    Combine all regime signals into single 0-100 score.
    Higher = more bullish / momentum-friendly.
    Lower = risk-off / mean-reversion.
    """
    # HMM component (50% weight)
    hmm_scores = {
        'bull': 80,
        'sideways': 50,
        'bear': 20
    }
    hmm_base = hmm_scores.get(hmm_regime, 50)
    # Weight by confidence
    hmm_component = hmm_base * hmm_confidence + 50 * (1 - hmm_confidence)

    # Hurst component (30% weight)
    # Higher Hurst = trending = momentum-friendly
    hurst_component = hurst_value * 100  # 0.0-1.0 mapped to 0-100

    # Macro component (20% weight)
    macro_component = macro.get('macro_score', 50)

    composite = (hmm_component * 0.50) + (hurst_component * 0.30) + (macro_component * 0.20)
    return max(0, min(100, round(composite, 1)))


# ---------------------------------------------------------------------------
# Strategy Toggle Logic
# ---------------------------------------------------------------------------

def get_strategy_toggles(hmm_regime, hurst_regime, composite_score, vix_regime):
    """
    Determine which strategy bundles should be active.
    Returns dict of bundle_name -> weight (0.0 to 1.0).
    """
    toggles = {
        'momentum': 0.0,
        'reversion': 0.0,
        'fundamental': 1.0,  # Always active (low frequency, high edge)
        'sentiment': 0.5,    # Always active but modulated
        'ml_alpha': 0.5      # Always active (orthogonal)
    }

    # Momentum bundle
    if hurst_regime == 'trending':
        toggles['momentum'] = 1.0
    elif hurst_regime == 'random':
        toggles['momentum'] = 0.5
    else:
        toggles['momentum'] = 0.2  # Reduce in mean-reversion regime

    # Reversion bundle
    if hurst_regime == 'mean_reverting':
        toggles['reversion'] = 1.0
    elif hurst_regime == 'random':
        toggles['reversion'] = 0.5
    else:
        toggles['reversion'] = 0.2

    # HMM modulation
    if hmm_regime == 'bear':
        toggles['momentum'] *= 0.5  # Cut momentum in bear
        toggles['reversion'] *= 1.3  # Boost reversion
        toggles['sentiment'] = 0.8   # Sentiment more useful in bear
    elif hmm_regime == 'bull':
        toggles['momentum'] *= 1.2
        toggles['fundamental'] = 0.8  # Less alpha from fundamentals in bull

    # VIX modulation
    if vix_regime in ('fear', 'fear_peak'):
        toggles['reversion'] *= 1.2  # Volatility = reversion opportunities
        toggles['momentum'] *= 0.7   # Don't chase in fear
    elif vix_regime == 'complacent':
        toggles['momentum'] *= 0.8   # Beware of complacency spikes

    # Clamp all to [0, 1]
    for k in toggles:
        toggles[k] = round(max(0.0, min(1.0, toggles[k])), 2)

    return toggles


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------

def run_regime_detection():
    """
    Full regime detection pipeline:
    1. Fetch SPY data for market-wide HMM
    2. Fit HMM (3 states)
    3. Calculate Hurst on SPY
    4. Fetch macro overlay (VIX, yield curve)
    5. Compute composite score
    6. Analyze per-ticker regimes
    7. POST results to PHP API
    """
    import yfinance as yf

    logger.info("=" * 60)
    logger.info("REGIME DETECTOR — Starting")
    logger.info("=" * 60)

    # Step 1: Fetch SPY data
    logger.info("Fetching SPY data...")
    spy = yf.download('SPY', period='2y', interval='1d', progress=False)
    if len(spy) < 100:
        logger.error("Insufficient SPY data (%d rows)", len(spy))
        return None

    spy_closes = spy['Close'].values.flatten()
    spy_returns = np.diff(np.log(spy_closes))
    spy_vol = pd.Series(spy_returns).rolling(20).std().values

    # Remove NaNs
    valid_mask = ~np.isnan(spy_vol)
    spy_returns_clean = spy_returns[valid_mask]
    spy_vol_clean = spy_vol[valid_mask]

    # Step 2: HMM
    logger.info("Fitting HMM...")
    hmm_detector = HMMRegimeDetector(n_states=3, lookback_days=252)
    hmm_regime, hmm_confidence, hmm_persistence = hmm_detector.fit_predict(
        spy_returns_clean, spy_vol_clean
    )

    # Step 3: Hurst on SPY
    logger.info("Computing Hurst exponent...")
    hurst_value, hurst_regime = compute_hurst(spy_closes[-500:])

    # Step 4: Macro overlay
    logger.info("Fetching macro overlay...")
    macro = fetch_macro_overlay()

    # Step 5: Composite score
    composite = calculate_composite_score(
        hmm_regime, hmm_confidence, hurst_regime, hurst_value, macro
    )

    # Step 6: Strategy toggles
    strategy_toggles = get_strategy_toggles(
        hmm_regime, hurst_regime, composite, macro.get('vix_regime', 'normal')
    )

    # Step 7: Per-ticker analysis
    logger.info("Analyzing per-ticker regimes...")
    ticker_regimes = {}
    for ticker in TRACKED_TICKERS:
        result = analyze_ticker_regime(ticker)
        if result:
            ticker_regimes[ticker] = result
            logger.info("  %s: Hurst=%.3f (%s), vol=%.1f%%, trend=%d",
                         ticker, result['hurst'], result['hurst_regime'],
                         result['vol_annualized'] * 100, result['trend_score'])

    # Step 8: EWMA vol for SPY
    spy_ewma_vol = ewma_volatility(spy_returns_clean[-60:])

    # Compile result
    regime_data = {
        'market': {
            'hmm_regime': hmm_regime,
            'hmm_confidence': round(hmm_confidence, 4),
            'hmm_persistence': round(hmm_persistence, 4),
            'hurst': round(hurst_value, 4),
            'hurst_regime': hurst_regime,
            'ewma_vol': round(spy_ewma_vol, 6),
            'vol_annualized': round(spy_ewma_vol * np.sqrt(252), 4),
            'composite_score': composite,
            'strategy_toggles': strategy_toggles
        },
        'macro': {
            'vix_level': macro.get('vix_level'),
            'vix_regime': macro.get('vix_regime', 'unknown'),
            'yield_curve': macro.get('yield_curve', 'unknown'),
            'yield_spread': macro.get('yield_spread'),
            'macro_score': macro.get('macro_score', 50)
        },
        'tickers': ticker_regimes
    }

    # Print summary
    logger.info("=" * 60)
    logger.info("REGIME DETECTION RESULTS")
    logger.info("=" * 60)
    logger.info("  HMM Regime:     %s (confidence=%.1f%%, persistence=%.1f%%)",
                 hmm_regime, hmm_confidence * 100, hmm_persistence * 100)
    logger.info("  Hurst:          %.3f (%s)", hurst_value, hurst_regime)
    logger.info("  VIX:            %s (level=%s)",
                 macro.get('vix_regime', '?'), macro.get('vix_level', '?'))
    logger.info("  Yield Curve:    %s (spread=%s)",
                 macro.get('yield_curve', '?'), macro.get('yield_spread', '?'))
    logger.info("  Composite:      %.1f / 100", composite)
    logger.info("  Strategy Toggles:")
    for bundle, weight in strategy_toggles.items():
        bar = '#' * int(weight * 20)
        logger.info("    %-14s %.2f |%s|", bundle, weight, bar)
    logger.info("  Ticker Regimes: %d analyzed", len(ticker_regimes))
    logger.info("=" * 60)

    # Step 9: POST to PHP API
    logger.info("Posting regime data to API...")
    result = post_to_api('ingest_regime', regime_data)

    if result.get('ok'):
        logger.info("Regime data saved successfully")
    else:
        logger.warning("API post returned: %s", result.get('error', 'unknown'))
        # Also try saving as JSON fallback
        fallback_path = os.path.join(os.path.dirname(__file__), '..', 'temp_regime.json')
        with open(fallback_path, 'w') as f:
            json.dump(regime_data, f, indent=2, default=str)
        logger.info("Saved fallback to %s", fallback_path)

    # Also print as JSON for GitHub Actions log
    print("\n--- REGIME JSON OUTPUT ---")
    print(json.dumps(regime_data, indent=2, default=str))

    return regime_data


if __name__ == '__main__':
    run_regime_detection()
