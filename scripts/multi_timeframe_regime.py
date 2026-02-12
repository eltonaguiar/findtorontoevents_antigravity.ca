#!/usr/bin/env python3
"""
Multi-Timeframe Regime Detection
=================================
Extends the existing HMM regime detection (hmm_regime.py / regime_detector.py)
to cover 3 timeframes for richer regime context:

  1. Intraday (4-hour bars)  -- crypto/forex/scalp algos
  2. Daily (enhanced)        -- sector rotation + credit spread overlays
  3. Weekly (structural)     -- multi-month trends, mutual fund timing

Produces:
  - Per-timeframe HMM regime labels (bull/sideways/bear)
  - Per-asset regime across all 3 timeframes
  - Composite multi-timeframe score (0-100)
  - Strategy toggles based on cross-timeframe agreement

Stores everything in lm_market_regime (existing table):
  - composite_score       DECIMAL(6,2)
  - ticker_regimes        TEXT (JSON)
  - strategy_toggles      TEXT (JSON)
  - hmm_regime            VARCHAR(20)  (daily)
  - hmm_confidence        DECIMAL(6,4)
  - hmm_persistence       DECIMAL(6,4)
  - hurst / hurst_regime
  - ewma_vol / vol_annualized
  - vix_level / vix_regime

Requirements: pip install yfinance numpy hmmlearn mysql-connector-python
Standalone:   python scripts/multi_timeframe_regime.py
"""

import os
import sys
import json
import datetime
import warnings
import traceback

import numpy as np
import mysql.connector

warnings.filterwarnings('ignore')

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DB_HOST = os.getenv('DB_HOST', 'mysql.50webs.com')
DB_USER = os.getenv('DB_USER', 'ejaguiar1_stocks')
DB_PASS = os.getenv('DB_PASS', 'stocks')
DB_NAME = os.getenv('DB_NAME', 'ejaguiar1_stocks')

API_HEADERS = {"User-Agent": "WorldClassIntelligence/1.0"}

# Assets to compute per-asset regime for
REGIME_ASSETS = {
    'SPY':     'equity_index',
    'BTC-USD': 'crypto',
    'EURUSD=X': 'forex',
    'JPY=X':   'forex',
    'TLT':     'bonds',
}

# Sector rotation tickers
SECTOR_RISK_ON  = 'XLK'   # Technology (risk-on proxy)
SECTOR_RISK_OFF = 'XLU'   # Utilities  (risk-off proxy)

# Credit spread proxy tickers
CREDIT_HY  = 'HYG'   # High-yield corporate bonds
CREDIT_GOV = 'TLT'   # Long-term treasuries

TIMEFRAME_LABELS = {
    '4h': 'Intraday (4h)',
    '1d': 'Daily',
    '1w': 'Weekly (structural)',
}

# How many HMM states per timeframe
N_STATES = 3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log(msg, level='INFO'):
    ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{ts}] [{level}] {msg}", flush=True)


def safe_download(ticker, **kwargs):
    """Download data from yfinance with error handling and MultiIndex fix."""
    import yfinance as yf
    try:
        df = yf.download(ticker, progress=False, **kwargs)
        if df is None or len(df) == 0:
            return None
        return df
    except Exception as e:
        log(f"yfinance download failed for {ticker}: {e}", 'WARN')
        return None


def get_close_series(df):
    """Extract close prices as a flat numpy array, handling MultiIndex columns."""
    if df is None or len(df) == 0:
        return None
    closes = df['Close'].dropna()
    vals = closes.values.flatten()
    if len(vals) == 0:
        return None
    return vals


def compute_returns(prices):
    """Log returns from price array."""
    prices = np.array(prices, dtype=float)
    prices = prices[prices > 0]
    if len(prices) < 2:
        return None
    return np.diff(np.log(prices))


# ---------------------------------------------------------------------------
# HMM Regime Detection (generic, any timeframe)
# ---------------------------------------------------------------------------

def hmm_regime_detect(returns, n_states=N_STATES, label=''):
    """
    Fit a GaussianHMM on returns and classify the current state.

    Returns: (regime_label, confidence, persistence)
      regime_label: 'bull' | 'sideways' | 'bear'
      confidence:   probability of the current state (0-1)
      persistence:  self-transition probability (0-1)
    """
    from hmmlearn.hmm import GaussianHMM

    if returns is None or len(returns) < 30:
        log(f"  [{label}] Not enough data ({0 if returns is None else len(returns)} obs), defaulting to sideways", 'WARN')
        return 'sideways', 0.33, 0.33

    X = returns.reshape(-1, 1)
    # Remove NaN/Inf
    mask = np.isfinite(X.flatten())
    X = X[mask]
    if len(X) < 30:
        return 'sideways', 0.33, 0.33

    try:
        model = GaussianHMM(
            n_components=n_states,
            covariance_type='diag',
            n_iter=300,
            random_state=42,
            tol=0.01,
        )
        model.fit(X)
    except Exception as e:
        log(f"  [{label}] HMM fit failed: {e}", 'WARN')
        return 'sideways', 0.33, 0.33

    # Label states by mean return
    means = model.means_[:, 0]
    state_order = np.argsort(means)[::-1]  # highest mean first
    labels_map = {int(state_order[0]): 'bull',
                  int(state_order[1]): 'sideways',
                  int(state_order[2]): 'bear'}

    # Predict on last 5 observations for smoothing
    X_recent = X[-min(5, len(X)):]
    states = model.predict(X_recent)
    probs = model.predict_proba(X_recent)

    current_state = int(states[-1])
    confidence = float(probs[-1][current_state])
    regime_label = labels_map.get(current_state, 'sideways')

    # Persistence = diagonal of transition matrix
    persistence = float(model.transmat_[current_state, current_state])

    return regime_label, confidence, persistence


# ---------------------------------------------------------------------------
# Timeframe-specific data fetchers
# ---------------------------------------------------------------------------

def fetch_intraday_4h(ticker):
    """
    Fetch 5 days of 1h bars, aggregate into 4h bars, return log returns.
    yfinance max for 1h interval is 7 days (or 730 days with paid).
    """
    df = safe_download(ticker, period='5d', interval='1h')
    if df is None or len(df) < 8:
        return None

    closes = get_close_series(df)
    if closes is None or len(closes) < 8:
        return None

    # Group into 4h bars by taking every 4th close
    # (market hours: 6.5h/day => ~1-2 complete 4h bars per day for stocks,
    #  but crypto/forex run 24h => 6 bars/day)
    bar_size = 4
    n_bars = len(closes) // bar_size
    if n_bars < 5:
        # Fallback: use 2h bars
        bar_size = 2
        n_bars = len(closes) // bar_size

    if n_bars < 5:
        return compute_returns(closes)

    # Take the close of each 4h block
    bar_closes = np.array([closes[(i + 1) * bar_size - 1] for i in range(n_bars)])
    return compute_returns(bar_closes)


def fetch_daily(ticker, period='1y'):
    """Fetch daily close prices, return log returns."""
    df = safe_download(ticker, period=period, interval='1d')
    if df is None:
        return None, None
    closes = get_close_series(df)
    if closes is None or len(closes) < 30:
        return None, None
    return closes, compute_returns(closes)


def fetch_weekly(ticker, period='2y'):
    """Fetch weekly close prices, return log returns."""
    df = safe_download(ticker, period=period, interval='1wk')
    if df is None:
        return None
    closes = get_close_series(df)
    if closes is None or len(closes) < 20:
        return None
    return compute_returns(closes)


# ---------------------------------------------------------------------------
# Enhanced daily signals: sector rotation + credit spread
# ---------------------------------------------------------------------------

def compute_sector_rotation():
    """
    XLK / XLU ratio: rising = risk-on, falling = risk-off.
    Returns: signal in {'risk_on', 'neutral', 'risk_off'}, ratio value
    """
    xlk = safe_download(SECTOR_RISK_ON, period='60d', interval='1d')
    xlu = safe_download(SECTOR_RISK_OFF, period='60d', interval='1d')

    if xlk is None or xlu is None:
        return 'neutral', None

    xlk_c = get_close_series(xlk)
    xlu_c = get_close_series(xlu)
    if xlk_c is None or xlu_c is None:
        return 'neutral', None

    min_len = min(len(xlk_c), len(xlu_c))
    xlk_c = xlk_c[-min_len:]
    xlu_c = xlu_c[-min_len:]

    # Guard division by zero
    xlu_c = np.where(xlu_c == 0, 1e-10, xlu_c)
    ratio = xlk_c / xlu_c

    if len(ratio) < 20:
        return 'neutral', float(ratio[-1])

    current = ratio[-1]
    sma20 = np.mean(ratio[-20:])

    pct_diff = (current - sma20) / sma20

    if pct_diff > 0.02:
        signal = 'risk_on'
    elif pct_diff < -0.02:
        signal = 'risk_off'
    else:
        signal = 'neutral'

    log(f"  Sector rotation (XLK/XLU): ratio={current:.3f}, SMA20={sma20:.3f} -> {signal}")
    return signal, float(current)


def compute_credit_spread():
    """
    HYG / TLT ratio: rising = risk-on (credit tightening), falling = risk-off.
    Returns: signal in {'tightening', 'neutral', 'widening'}, ratio value
    """
    hyg = safe_download(CREDIT_HY, period='60d', interval='1d')
    tlt = safe_download(CREDIT_GOV, period='60d', interval='1d')

    if hyg is None or tlt is None:
        return 'neutral', None

    hyg_c = get_close_series(hyg)
    tlt_c = get_close_series(tlt)
    if hyg_c is None or tlt_c is None:
        return 'neutral', None

    min_len = min(len(hyg_c), len(tlt_c))
    hyg_c = hyg_c[-min_len:]
    tlt_c = tlt_c[-min_len:]

    tlt_c = np.where(tlt_c == 0, 1e-10, tlt_c)
    ratio = hyg_c / tlt_c

    if len(ratio) < 20:
        return 'neutral', float(ratio[-1])

    current = ratio[-1]
    sma20 = np.mean(ratio[-20:])

    pct_diff = (current - sma20) / sma20

    if pct_diff > 0.01:
        signal = 'tightening'   # Risk-on: high yield outperforming
    elif pct_diff < -0.01:
        signal = 'widening'     # Risk-off: flight to safety
    else:
        signal = 'neutral'

    log(f"  Credit spread (HYG/TLT): ratio={current:.3f}, SMA20={sma20:.3f} -> {signal}")
    return signal, float(current)


# ---------------------------------------------------------------------------
# VIX fetch
# ---------------------------------------------------------------------------

def fetch_vix():
    """Return (current_vix, vix_regime)."""
    df = safe_download('^VIX', period='30d', interval='1d')
    if df is None:
        return None, 'unknown'
    closes = get_close_series(df)
    if closes is None or len(closes) == 0:
        return None, 'unknown'

    current = float(closes[-1])
    sma20 = float(np.mean(closes[-20:])) if len(closes) >= 20 else current

    if current > 30:
        regime = 'fear'
    elif current > 20:
        regime = 'elevated'
    elif current < 13:
        regime = 'complacent'
    else:
        regime = 'normal'

    # Override with mean-reversion signals
    if current > sma20 * 1.2:
        regime = 'fear_peak'
    elif current < sma20 * 0.8:
        regime = 'complacent'

    return current, regime


# ---------------------------------------------------------------------------
# EWMA Volatility
# ---------------------------------------------------------------------------

def ewma_volatility(returns, decay=0.94):
    """EWMA vol, more responsive than rolling window."""
    returns = np.array(returns, dtype=float)
    returns = returns[np.isfinite(returns)]
    if len(returns) < 10:
        return 0.02
    variance = returns[0] ** 2
    for r in returns[1:]:
        variance = decay * variance + (1 - decay) * (r ** 2)
    return float(np.sqrt(variance))


# ---------------------------------------------------------------------------
# Hurst Exponent
# ---------------------------------------------------------------------------

def compute_hurst(prices, max_lag=100):
    """
    R/S Hurst exponent.
    H > 0.55: trending  |  H < 0.45: mean-reverting  |  0.45-0.55: random walk
    """
    prices = np.array(prices, dtype=float)
    prices = prices[np.isfinite(prices)]
    if len(prices) < 50:
        return 0.5, 'random'

    lags = range(10, min(max_lag, len(prices) // 4))
    rs_values, lag_values = [], []

    for lag in lags:
        n_segments = len(prices) // lag
        if n_segments < 2:
            continue
        rs_list = []
        for seg in range(n_segments):
            segment = prices[seg * lag:(seg + 1) * lag]
            rets = np.diff(np.log(segment + 1e-10))
            if len(rets) < 2:
                continue
            mean_r = np.mean(rets)
            devs = np.cumsum(rets - mean_r)
            R = np.max(devs) - np.min(devs)
            S = np.std(rets, ddof=1)
            if S > 1e-10:
                rs_list.append(R / S)
        if rs_list:
            rs_values.append(np.log(np.mean(rs_list)))
            lag_values.append(np.log(lag))

    if len(lag_values) < 3:
        return 0.5, 'random'

    H = float(np.polyfit(np.array(lag_values), np.array(rs_values), 1)[0])
    H = max(0.0, min(1.0, H))

    if H > 0.55:
        regime = 'trending'
    elif H < 0.45:
        regime = 'mean_reverting'
    else:
        regime = 'random'
    return H, regime


# ---------------------------------------------------------------------------
# Per-Asset Multi-Timeframe Regime
# ---------------------------------------------------------------------------

def compute_asset_regime(ticker, asset_class):
    """
    Run HMM regime detection across 3 timeframes for a single asset.
    Returns dict like: {"4h": "bull", "1d": "sideways", "1w": "bear", "agreement": 0.67}
    """
    result = {}

    # --- 4h intraday ---
    log(f"  {ticker} [4h] fetching intraday...")
    rets_4h = fetch_intraday_4h(ticker)
    regime_4h, conf_4h, _ = hmm_regime_detect(rets_4h, label=f'{ticker}-4h')
    result['4h'] = regime_4h
    result['4h_confidence'] = round(conf_4h, 4)

    # --- 1d daily ---
    log(f"  {ticker} [1d] fetching daily...")
    daily_closes, rets_1d = fetch_daily(ticker, period='1y')
    regime_1d, conf_1d, persist_1d = hmm_regime_detect(rets_1d, label=f'{ticker}-1d')
    result['1d'] = regime_1d
    result['1d_confidence'] = round(conf_1d, 4)

    # --- 1w weekly ---
    log(f"  {ticker} [1w] fetching weekly...")
    rets_1w = fetch_weekly(ticker, period='2y')
    regime_1w, conf_1w, _ = hmm_regime_detect(rets_1w, label=f'{ticker}-1w')
    result['1w'] = regime_1w
    result['1w_confidence'] = round(conf_1w, 4)

    # Agreement: how many of the 3 timeframes agree
    regimes = [regime_4h, regime_1d, regime_1w]
    from collections import Counter
    counts = Counter(regimes)
    most_common_regime, most_common_count = counts.most_common(1)[0]
    result['consensus'] = most_common_regime
    result['agreement'] = round(most_common_count / 3.0, 2)

    # Extra daily stats if we have closes
    if daily_closes is not None and len(daily_closes) >= 50:
        sma50 = float(np.mean(daily_closes[-50:]))
        sma200 = float(np.mean(daily_closes[-200:])) if len(daily_closes) >= 200 else sma50
        result['sma50'] = round(sma50, 2)
        result['sma200'] = round(sma200, 2)
        result['price'] = round(float(daily_closes[-1]), 2)

    result['asset_class'] = asset_class
    return result


# ---------------------------------------------------------------------------
# Composite Multi-Timeframe Score
# ---------------------------------------------------------------------------

def compute_composite_score(spy_regimes, all_asset_regimes, sector_signal, credit_signal,
                            vix_regime, hurst_value):
    """
    Combine all 3 SPY timeframes + overlays into a single 0-100 score.

    Weighting:
      - Weekly regime:  25%  (structural direction)
      - Daily regime:   35%  (primary operating timeframe)
      - 4h regime:      15%  (near-term momentum)
      - Sector rotation: 10%
      - Credit spread:   10%
      - Hurst modifier:   5%

    All-agree bonus: if all 3 timeframes are the same, add 10 pts (or subtract 10 if bear).
    """
    regime_scores = {'bull': 80, 'sideways': 50, 'bear': 20}

    # SPY timeframe scores (weighted by confidence)
    def weighted_regime(regime_info, timeframe):
        label = regime_info.get(timeframe, 'sideways')
        conf = regime_info.get(f'{timeframe}_confidence', 0.5)
        base = regime_scores.get(label, 50)
        return base * conf + 50 * (1 - conf)

    score_1w = weighted_regime(spy_regimes, '1w')
    score_1d = weighted_regime(spy_regimes, '1d')
    score_4h = weighted_regime(spy_regimes, '4h')

    # Sector rotation score
    sector_scores = {'risk_on': 70, 'neutral': 50, 'risk_off': 30}
    score_sector = sector_scores.get(sector_signal, 50)

    # Credit spread score
    credit_scores = {'tightening': 70, 'neutral': 50, 'widening': 30}
    score_credit = credit_scores.get(credit_signal, 50)

    # Hurst modifier (trending = momentum-friendly = bullish bias)
    score_hurst = hurst_value * 100  # 0-1 mapped to 0-100

    composite = (
        score_1w * 0.25 +
        score_1d * 0.35 +
        score_4h * 0.15 +
        score_sector * 0.10 +
        score_credit * 0.10 +
        score_hurst * 0.05
    )

    # Agreement bonus/penalty
    agreement = spy_regimes.get('agreement', 0.33)
    consensus = spy_regimes.get('consensus', 'sideways')
    if agreement >= 1.0:
        # All 3 timeframes agree
        if consensus == 'bull':
            composite += 10
        elif consensus == 'bear':
            composite -= 10
        # sideways full agreement: no extra bonus
    elif agreement <= 0.33:
        # Complete disagreement: pull toward neutral
        composite = composite * 0.8 + 50 * 0.2

    return max(0.0, min(100.0, round(composite, 1)))


# ---------------------------------------------------------------------------
# Strategy Toggles
# ---------------------------------------------------------------------------

def generate_strategy_toggles(spy_regimes, composite_score, vix_regime,
                              hurst_regime, sector_signal, credit_signal):
    """
    Decide which strategy families to enable based on multi-TF regime.

    Returns JSON-ready dict with boolean + weight toggles.
    """
    weekly = spy_regimes.get('1w', 'sideways')
    daily = spy_regimes.get('1d', 'sideways')
    intra = spy_regimes.get('4h', 'sideways')
    agreement = spy_regimes.get('agreement', 0.33)

    toggles = {}

    # -- Momentum: enable in bull + sideways, reduce in bear
    mom_score = 0.5
    if daily in ('bull',):
        mom_score += 0.2
    if weekly in ('bull',):
        mom_score += 0.15
    if intra in ('bull',):
        mom_score += 0.1
    if daily == 'bear':
        mom_score -= 0.3
    if hurst_regime == 'trending':
        mom_score += 0.1
    if vix_regime in ('fear', 'fear_peak'):
        mom_score -= 0.15
    toggles['momentum'] = mom_score > 0.4

    # -- Mean Reversion: enable in sideways, also useful in volatile bear
    rev_score = 0.5
    if daily == 'sideways':
        rev_score += 0.25
    if hurst_regime == 'mean_reverting':
        rev_score += 0.2
    if vix_regime in ('fear', 'elevated'):
        rev_score += 0.1
    if daily == 'bull' and weekly == 'bull':
        rev_score -= 0.2  # Less useful in strong uptrend
    toggles['mean_reversion'] = rev_score > 0.4

    # -- Trend Following: enable in strong directional regimes
    trend_score = 0.5
    if agreement >= 0.67:  # At least 2/3 agree on direction
        trend_score += 0.25
    if hurst_regime == 'trending':
        trend_score += 0.15
    if daily == 'sideways' and weekly == 'sideways':
        trend_score -= 0.3  # No trend to follow
    toggles['trend'] = trend_score > 0.45

    # -- Scalp: disable in high-vol bear (whipsaws), good in calm markets
    scalp_score = 0.5
    if vix_regime in ('fear', 'fear_peak'):
        scalp_score -= 0.35  # Whipsaw risk
    if daily == 'bear' and intra == 'bear':
        scalp_score -= 0.2
    if vix_regime in ('normal', 'complacent'):
        scalp_score += 0.15
    toggles['scalp'] = scalp_score > 0.4

    # -- Mutual Fund Buy: enable only when weekly = bull (structural uptrend)
    toggles['mutual_fund_buy'] = weekly == 'bull'

    # -- Crypto: enable when both BTC is not in weekly bear and vol is manageable
    toggles['crypto_long'] = not (vix_regime == 'fear' and daily == 'bear')

    # -- Forex: almost always active, reduce in extreme regimes
    toggles['forex'] = not (vix_regime == 'fear_peak' and agreement >= 1.0 and
                            spy_regimes.get('consensus') == 'bear')

    # -- Confidence weights (0.0 to 1.0) for position sizing
    toggles['_weights'] = {
        'momentum':      round(max(0.0, min(1.0, mom_score)), 2),
        'mean_reversion': round(max(0.0, min(1.0, rev_score)), 2),
        'trend':         round(max(0.0, min(1.0, trend_score)), 2),
        'scalp':         round(max(0.0, min(1.0, scalp_score)), 2),
    }

    return toggles


# ---------------------------------------------------------------------------
# Database: save to lm_market_regime
# ---------------------------------------------------------------------------

def save_to_database(regime_data):
    """
    Update the existing lm_market_regime row with multi-TF results.
    Creates a new row if none exists.
    """
    try:
        conn = mysql.connector.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME,
            connect_timeout=15
        )
    except Exception as e:
        log(f"DB connection failed: {e}", 'ERROR')
        return False

    cursor = conn.cursor()
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Extract fields
    spy = regime_data.get('spy', {})
    hmm_regime    = spy.get('1d', 'sideways')
    hmm_conf      = spy.get('1d_confidence', 0.5)
    hmm_persist   = spy.get('1d_persistence', 0.5)
    hurst_val     = regime_data.get('hurst', 0.5)
    hurst_regime  = regime_data.get('hurst_regime', 'random')
    ewma_vol      = regime_data.get('ewma_vol', 0.02)
    vol_ann       = regime_data.get('vol_annualized', 0.3)
    composite     = regime_data.get('composite_score', 50.0)
    vix_level     = regime_data.get('vix_level')
    vix_regime    = regime_data.get('vix_regime', 'unknown')

    # JSON fields
    ticker_regimes_json = json.dumps(regime_data.get('ticker_regimes', {}), default=str)
    strategy_toggles_json = json.dumps(regime_data.get('strategy_toggles', {}), default=str)

    try:
        # Check if a row exists
        cursor.execute("SELECT id FROM lm_market_regime ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()

        if row:
            cursor.execute("""
                UPDATE lm_market_regime
                SET hmm_regime = %s,
                    hmm_confidence = %s,
                    hmm_persistence = %s,
                    hurst = %s,
                    hurst_regime = %s,
                    ewma_vol = %s,
                    vol_annualized = %s,
                    composite_score = %s,
                    strategy_toggles = %s,
                    vix_level = %s,
                    vix_regime = %s,
                    ticker_regimes = %s,
                    created_at = %s
                WHERE id = %s
            """, (
                hmm_regime, hmm_conf, hmm_persist,
                hurst_val, hurst_regime,
                ewma_vol, vol_ann,
                composite,
                strategy_toggles_json,
                vix_level, vix_regime,
                ticker_regimes_json,
                now, row[0]
            ))
            log(f"Updated lm_market_regime row id={row[0]}")
        else:
            cursor.execute("""
                INSERT INTO lm_market_regime
                    (date, hmm_regime, hmm_confidence, hmm_persistence,
                     hurst, hurst_regime, ewma_vol, vol_annualized,
                     composite_score, strategy_toggles,
                     vix_level, vix_regime, ticker_regimes, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                now, hmm_regime, hmm_conf, hmm_persist,
                hurst_val, hurst_regime, ewma_vol, vol_ann,
                composite, strategy_toggles_json,
                vix_level, vix_regime, ticker_regimes_json, now
            ))
            log("Inserted new lm_market_regime row")

        conn.commit()
        success = True
    except Exception as e:
        log(f"DB write failed: {e}", 'ERROR')
        success = False
    finally:
        cursor.close()
        conn.close()

    return success


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------

def run():
    """
    Full multi-timeframe regime detection pipeline.

    Steps:
      1. Fetch VIX
      2. Enhanced daily overlays (sector rotation, credit spread)
      3. Per-asset multi-TF regime (SPY, BTC-USD, EURUSD=X, JPY=X, TLT)
      4. SPY Hurst exponent + EWMA vol
      5. Composite score
      6. Strategy toggles
      7. Save to DB
    """
    log("=" * 70)
    log("MULTI-TIMEFRAME REGIME DETECTION — Starting")
    log("=" * 70)

    # ------------------------------------------------------------------
    # Step 1: VIX
    # ------------------------------------------------------------------
    log("[Step 1/7] Fetching VIX...")
    vix_level, vix_regime = fetch_vix()
    log(f"  VIX: {vix_level} ({vix_regime})")

    # ------------------------------------------------------------------
    # Step 2: Enhanced daily overlays
    # ------------------------------------------------------------------
    log("[Step 2/7] Computing sector rotation + credit spread overlays...")
    sector_signal, sector_ratio = compute_sector_rotation()
    credit_signal, credit_ratio = compute_credit_spread()

    # ------------------------------------------------------------------
    # Step 3: Per-asset multi-TF regime
    # ------------------------------------------------------------------
    log("[Step 3/7] Computing per-asset multi-timeframe regimes...")
    ticker_regimes = {}
    spy_regimes = None

    for ticker, asset_class in REGIME_ASSETS.items():
        log(f"  --- {ticker} ({asset_class}) ---")
        try:
            asset_regime = compute_asset_regime(ticker, asset_class)
            ticker_regimes[ticker] = asset_regime
            if ticker == 'SPY':
                spy_regimes = asset_regime
            log(f"  {ticker}: 4h={asset_regime['4h']} | 1d={asset_regime['1d']} | "
                f"1w={asset_regime['1w']} | consensus={asset_regime['consensus']} "
                f"(agreement={asset_regime['agreement']})")
        except Exception as e:
            log(f"  {ticker} failed: {e}", 'WARN')
            traceback.print_exc()

    # Fallback if SPY failed entirely
    if spy_regimes is None:
        log("SPY regime detection failed, using defaults", 'WARN')
        spy_regimes = {
            '4h': 'sideways', '4h_confidence': 0.33,
            '1d': 'sideways', '1d_confidence': 0.33,
            '1w': 'sideways', '1w_confidence': 0.33,
            'consensus': 'sideways', 'agreement': 0.33,
        }

    # ------------------------------------------------------------------
    # Step 4: SPY Hurst + EWMA vol (from daily data)
    # ------------------------------------------------------------------
    log("[Step 4/7] Computing Hurst exponent + EWMA volatility for SPY...")
    spy_daily_closes, spy_daily_rets = fetch_daily('SPY', period='2y')

    hurst_value, hurst_regime = 0.5, 'random'
    ewma_vol_val, vol_ann = 0.02, 0.3

    if spy_daily_closes is not None:
        hurst_value, hurst_regime = compute_hurst(spy_daily_closes[-500:])
        log(f"  Hurst: {hurst_value:.4f} ({hurst_regime})")

    if spy_daily_rets is not None:
        ewma_vol_val = ewma_volatility(spy_daily_rets[-60:])
        vol_ann = round(ewma_vol_val * np.sqrt(252), 4)
        log(f"  EWMA vol: {ewma_vol_val:.6f} (annualized: {vol_ann:.4f})")

    # Also store persistence from the daily HMM in spy_regimes
    # (already computed inside compute_asset_regime via hmm_regime_detect)
    # We re-run a standalone daily HMM here to also get persistence for the DB
    if spy_daily_rets is not None:
        _, _, daily_persistence = hmm_regime_detect(spy_daily_rets, label='SPY-1d-persistence')
        spy_regimes['1d_persistence'] = round(daily_persistence, 4)

    # ------------------------------------------------------------------
    # Step 5: Composite multi-TF score
    # ------------------------------------------------------------------
    log("[Step 5/7] Computing composite multi-timeframe score...")
    composite_score = compute_composite_score(
        spy_regimes, ticker_regimes,
        sector_signal, credit_signal,
        vix_regime, hurst_value
    )
    log(f"  Composite score: {composite_score}/100")

    # ------------------------------------------------------------------
    # Step 6: Strategy toggles
    # ------------------------------------------------------------------
    log("[Step 6/7] Generating strategy toggles...")
    strategy_toggles = generate_strategy_toggles(
        spy_regimes, composite_score, vix_regime,
        hurst_regime, sector_signal, credit_signal
    )
    for k, v in strategy_toggles.items():
        if k == '_weights':
            continue
        log(f"  {k:20s} = {v}")
    if '_weights' in strategy_toggles:
        log(f"  Position sizing weights: {strategy_toggles['_weights']}")

    # ------------------------------------------------------------------
    # Step 7: Save to DB
    # ------------------------------------------------------------------
    log("[Step 7/7] Saving to database...")

    # Add enhanced overlay info into ticker_regimes for storage
    ticker_regimes['_overlays'] = {
        'sector_rotation': sector_signal,
        'sector_ratio': sector_ratio,
        'credit_spread': credit_signal,
        'credit_ratio': credit_ratio,
    }

    regime_data = {
        'spy': spy_regimes,
        'ticker_regimes': ticker_regimes,
        'composite_score': composite_score,
        'strategy_toggles': strategy_toggles,
        'hurst': hurst_value,
        'hurst_regime': hurst_regime,
        'ewma_vol': ewma_vol_val,
        'vol_annualized': vol_ann,
        'vix_level': vix_level,
        'vix_regime': vix_regime,
    }

    db_ok = save_to_database(regime_data)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    log("=" * 70)
    log("MULTI-TIMEFRAME REGIME RESULTS")
    log("=" * 70)
    log(f"  SPY 4h:        {spy_regimes.get('4h', '?'):10s} (conf={spy_regimes.get('4h_confidence', 0):.1%})")
    log(f"  SPY Daily:     {spy_regimes.get('1d', '?'):10s} (conf={spy_regimes.get('1d_confidence', 0):.1%})")
    log(f"  SPY Weekly:    {spy_regimes.get('1w', '?'):10s} (conf={spy_regimes.get('1w_confidence', 0):.1%})")
    log(f"  Agreement:     {spy_regimes.get('agreement', 0):.0%} ({spy_regimes.get('consensus', '?')})")
    log(f"  Sector Rot:    {sector_signal}")
    log(f"  Credit Spread: {credit_signal}")
    log(f"  VIX:           {vix_level} ({vix_regime})")
    log(f"  Hurst:         {hurst_value:.4f} ({hurst_regime})")
    log(f"  EWMA Vol:      {ewma_vol_val:.6f} (ann={vol_ann:.4f})")
    log(f"  Composite:     {composite_score}/100")
    log(f"  DB saved:      {'YES' if db_ok else 'FAILED'}")
    log("")
    log("  Per-asset regimes:")
    for tk, info in ticker_regimes.items():
        if tk.startswith('_'):
            continue
        log(f"    {tk:10s}  4h={info.get('4h','?'):10s}  1d={info.get('1d','?'):10s}  "
            f"1w={info.get('1w','?'):10s}  consensus={info.get('consensus','?')}")
    log("")
    log("  Strategy toggles:")
    for k, v in strategy_toggles.items():
        if k == '_weights':
            for wk, wv in v.items():
                bar = '#' * int(wv * 20)
                log(f"    {wk:20s} weight={wv:.2f} |{bar}|")
        else:
            log(f"    {k:20s} = {v}")
    log("=" * 70)

    # JSON output for GitHub Actions / downstream consumers
    print("\n--- MULTI-TF REGIME JSON OUTPUT ---")
    print(json.dumps(regime_data, indent=2, default=str))

    return regime_data


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    try:
        result = run()
        if result:
            log("Multi-timeframe regime detection completed successfully.")
            sys.exit(0)
        else:
            log("Multi-timeframe regime detection returned no result.", 'ERROR')
            sys.exit(1)
    except Exception as e:
        log(f"Fatal error: {e}", 'ERROR')
        traceback.print_exc()
        sys.exit(1)
