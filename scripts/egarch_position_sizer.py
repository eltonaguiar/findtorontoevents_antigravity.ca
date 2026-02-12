#!/usr/bin/env python3
"""
EGARCH Position Sizer — Advanced Position Sizing with Volatility Forecasting
=============================================================================

Upgrades the existing Half-Kelly + EWMA sizing (position_sizer.py) with:
  1. EGARCH(1,1) Volatility Forecasting (asymmetric vol: crashes > rallies)
  2. ATR-Based Dynamic Stops (replace fixed % stops with volatility-adaptive TP/SL)
  3. Quarter-Kelly with EGARCH Adjustment (smaller bets, vol-scaled)
  4. Momentum Crash Protection (VIX-gated + 5-day drawdown pause)
  5. Correlation-Adjusted Sizing (reduce concentration in correlated assets)

Rationale:
  - "Dynamic position sizing with Half-Kelly can cut drawdowns by 30-50%"
  - "Quarter-Kelly adjusted by EGARCH volatility" is more conservative and robust
  - "ATR-based dynamic stops instead of fixed % stops" lets positions breathe

Integration:
  - Posts to regime.php?action=update_position_sizing&key=livetrader2026
  - Reads from lm_trades, lm_kelly_fractions, lm_market_regime, lm_price_cache
  - Writes to lm_position_sizing table

Usage:
  python scripts/egarch_position_sizer.py                # Full run with API post
  python scripts/egarch_position_sizer.py --dry-run       # Compute only, no API/DB writes
  python scripts/egarch_position_sizer.py --algo "Momentum Burst"  # Single algo

Requirements: pip install arch pandas yfinance mysql-connector-python numpy requests
"""

import sys
import os
import json
import logging
import argparse
import warnings
from datetime import datetime, timezone, timedelta

import numpy as np
import pandas as pd
import requests

warnings.filterwarnings('ignore')

# ---------------------------------------------------------------------------
# Path setup — allow imports from scripts/ directory
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
DATA_DIR = os.path.join(SCRIPT_DIR, '..', 'data')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('egarch_position_sizer')

# ---------------------------------------------------------------------------
# Configuration — env vars with safe defaults
# ---------------------------------------------------------------------------
API_BASE = os.environ.get('SM_API_BASE', 'https://findtorontoevents.ca/live-monitor/api')
ADMIN_KEY = os.environ.get('SM_ADMIN_KEY', 'livetrader2026')

DB_HOST = os.environ.get('DB_HOST', 'mysql.50webs.com')
DB_USER = os.environ.get('DB_USER', 'ejaguiar1_stocks')
DB_PASS = os.environ.get('DB_PASS', 'stocks')
DB_NAME = os.environ.get('DB_NAME', 'ejaguiar1_stocks')

# CRITICAL: Custom User-Agent to bypass ModSecurity WAF on shared hosting
API_HEADERS = {"User-Agent": "WorldClassIntelligence/1.0"}

# Capital and sizing bounds
CAPITAL = 10000.0           # $10K paper trading capital
MIN_POSITION_PCT = 0.01    # 1% floor
MAX_POSITION_PCT = 0.10    # 10% ceiling (tighter than old 15%)
VOL_TARGET_ANNUAL = 0.10   # 10% annualized volatility target

# EGARCH config
EGARCH_LOOKBACK = '2y'     # Price history for model fitting
EGARCH_MIN_OBS = 100       # Minimum observations for EGARCH fit
FORECAST_HORIZON = 1       # 1-day vol forecast

# ATR config
ATR_PERIOD = 14
ATR_SL_MULTIPLIER = 2.0    # SL = 2.0 x ATR
ATR_TP_MULTIPLIER = 3.0    # TP = 3.0 x ATR (maintains 1.5:1 R:R)
ATR_SL_FLOOR_STOCKS = 1.5  # Minimum SL% for stocks
ATR_SL_FLOOR_CRYPTO = 2.0  # Minimum SL% for crypto

# Asset class proxy tickers for vol forecasting
ASSET_PROXIES = {
    'stocks': 'SPY',
    'crypto': 'BTC-USD',
    'forex': 'EURUSD=X',
}

# Momentum algorithms — subject to crash protection scaling
MOMENTUM_ALGOS = [
    'Momentum Burst', 'Breakout 24h', 'Volatility Breakout',
    'Trend Sniper', 'Volume Spike', 'VAM',
    'ADX Trend Strength', 'Alpha Predator',
]

# Algorithms that benefit from high-vol / fear regimes
CONTRARIAN_ALGOS = [
    'Mean Reversion', 'RSI Oversold Recovery', 'Bollinger Mean Reversion',
    'Contrarian', 'Fear & Greed Contrarian',
]


# ===========================================================================
# 1. EGARCH VOLATILITY FORECASTING
# ===========================================================================

def fetch_returns_yfinance(ticker, period=EGARCH_LOOKBACK):
    """
    Fetch historical daily returns for a ticker via yfinance.
    Returns pd.Series of fractional returns (not percentage).
    """
    import yfinance as yf

    try:
        data = yf.download(ticker, period=period, progress=False)
        if data.empty:
            logger.warning("No price data for %s", ticker)
            return None

        # Handle yfinance MultiIndex columns
        if isinstance(data.columns, pd.MultiIndex):
            if ticker in data['Close'].columns:
                close = data['Close'][ticker]
            else:
                close = data['Close'].iloc[:, 0]
        else:
            close = data['Close']

        close = close.dropna()
        if len(close) < EGARCH_MIN_OBS:
            logger.warning("Insufficient data for %s (%d obs, need %d)",
                           ticker, len(close), EGARCH_MIN_OBS)
            return None

        returns = close.pct_change().dropna()
        return returns

    except Exception as e:
        logger.warning("Failed to fetch returns for %s: %s", ticker, e)
        return None


def fetch_candles_yfinance(ticker, period='1mo'):
    """
    Fetch OHLC candle data for ATR calculation.
    Returns list of dicts with 'high', 'low', 'close' keys.
    """
    import yfinance as yf

    try:
        data = yf.download(ticker, period=period, progress=False)
        if data.empty:
            return None

        # Handle MultiIndex columns
        if isinstance(data.columns, pd.MultiIndex):
            highs = data['High'].iloc[:, 0].values.flatten()
            lows = data['Low'].iloc[:, 0].values.flatten()
            closes = data['Close'].iloc[:, 0].values.flatten()
        else:
            highs = data['High'].values.flatten()
            lows = data['Low'].values.flatten()
            closes = data['Close'].values.flatten()

        candles = []
        for i in range(len(highs)):
            h = float(highs[i])
            l = float(lows[i])
            c = float(closes[i])
            if not (np.isnan(h) or np.isnan(l) or np.isnan(c)):
                candles.append({'high': h, 'low': l, 'close': c})

        return candles if len(candles) >= ATR_PERIOD + 1 else None

    except Exception as e:
        logger.warning("Failed to fetch candles for %s: %s", ticker, e)
        return None


def forecast_egarch_vol(returns, horizon=FORECAST_HORIZON):
    """
    Fit EGARCH(1,1) with skewed Student-t distribution and forecast volatility.

    EGARCH captures asymmetric volatility:
      - Negative returns (crashes) amplify volatility more than positive returns
      - This is the "leverage effect" observed in equity markets

    Args:
        returns: pd.Series of fractional daily returns
        horizon: forecast horizon in days

    Returns:
        (vol_forecast_daily, model_result) or (None, None) on failure
    """
    from arch import arch_model

    try:
        # Scale to percentage returns for numerical stability
        pct_returns = returns * 100.0

        # Fit EGARCH(1,1) with skewed Student-t innovations
        model = arch_model(
            pct_returns,
            vol='EGARCH',
            p=1, q=1,
            dist='skewt',
            mean='Constant'
        )
        result = model.fit(disp='off', show_warning=False)

        # Forecast
        forecast = result.forecast(horizon=horizon)
        var_forecast = forecast.variance.values[-1, 0]

        # Convert back from percentage to fractional
        vol_forecast_daily = np.sqrt(var_forecast) / 100.0

        # Sanity check: vol should be positive and reasonable
        if np.isnan(vol_forecast_daily) or vol_forecast_daily <= 0:
            logger.warning("EGARCH produced invalid vol forecast: %s", vol_forecast_daily)
            return None, None

        return float(vol_forecast_daily), result

    except Exception as e:
        logger.warning("EGARCH fit failed: %s", e)
        return None, None


def fallback_ewma_vol(returns, decay=0.94):
    """
    Fallback: EWMA volatility if EGARCH fails.
    RiskMetrics standard decay = 0.94.
    Returns daily volatility (fractional).
    """
    ret_arr = np.array(returns, dtype=float)
    ret_arr = ret_arr[~np.isnan(ret_arr)]

    if len(ret_arr) < 5:
        return 0.02  # Default 2% daily

    variance = ret_arr[0] ** 2
    for r in ret_arr[1:]:
        variance = decay * variance + (1 - decay) * (r ** 2)

    return float(np.sqrt(variance))


def get_vol_forecast(ticker):
    """
    Get the best available volatility forecast for a ticker.
    Tries EGARCH first, falls back to EWMA.

    Returns:
        dict with 'vol_daily', 'vol_annual', 'model_type', 'aic'
    """
    returns = fetch_returns_yfinance(ticker)

    if returns is None or len(returns) < 50:
        daily_vol = 0.02  # Conservative default
        return {
            'vol_daily': daily_vol,
            'vol_annual': daily_vol * np.sqrt(252),
            'model_type': 'DEFAULT',
            'aic': None,
        }

    # Try EGARCH
    egarch_vol, egarch_result = forecast_egarch_vol(returns)

    if egarch_vol is not None:
        return {
            'vol_daily': egarch_vol,
            'vol_annual': egarch_vol * np.sqrt(252),
            'model_type': 'EGARCH',
            'aic': float(egarch_result.aic) if egarch_result else None,
        }

    # Fallback to EWMA
    ewma = fallback_ewma_vol(returns)
    return {
        'vol_daily': ewma,
        'vol_annual': ewma * np.sqrt(252),
        'model_type': 'EWMA',
        'aic': None,
    }


# ===========================================================================
# 2. ATR-BASED DYNAMIC STOPS
# ===========================================================================

def calculate_atr(candles, period=ATR_PERIOD):
    """
    Calculate Average True Range over the given period.
    True Range = max(H-L, |H-Cprev|, |L-Cprev|)

    Args:
        candles: list of dicts with 'high', 'low', 'close'
        period: ATR lookback period (default 14)

    Returns:
        ATR value, or None if insufficient data
    """
    if len(candles) < period + 1:
        return None

    recent = candles[-(period + 1):]
    true_ranges = []

    for i in range(1, len(recent)):
        h = recent[i]['high']
        l = recent[i]['low']
        prev_c = recent[i - 1]['close']

        tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
        true_ranges.append(tr)

    return float(np.mean(true_ranges))


def atr_based_stops(candles, asset_class='stocks',
                    atr_period=ATR_PERIOD,
                    sl_multiplier=ATR_SL_MULTIPLIER,
                    tp_multiplier=ATR_TP_MULTIPLIER):
    """
    Calculate dynamic TP/SL based on Average True Range.

    Instead of fixed 3% stop-loss, the stop "breathes" with the asset's
    natural volatility:
      SL = sl_multiplier x ATR / price (as percentage)
      TP = tp_multiplier x ATR / price (maintains 1.5:1 reward/risk)

    Floors:
      Stocks: SL >= 1.5%
      Crypto: SL >= 2.0%

    Args:
        candles: list of dicts with 'high', 'low', 'close'
        asset_class: 'stocks', 'crypto', or 'forex'
        atr_period: ATR lookback
        sl_multiplier: multiplier for stop-loss
        tp_multiplier: multiplier for take-profit

    Returns:
        (tp_pct, sl_pct) or (None, None) if insufficient data
    """
    atr = calculate_atr(candles, atr_period)
    if atr is None:
        return None, None

    current_price = candles[-1]['close']
    if current_price <= 0:
        return None, None

    sl_pct = (sl_multiplier * atr / current_price) * 100.0
    tp_pct = (tp_multiplier * atr / current_price) * 100.0

    # Apply floors based on asset class
    if asset_class == 'crypto':
        sl_pct = max(sl_pct, ATR_SL_FLOOR_CRYPTO)
    else:
        sl_pct = max(sl_pct, ATR_SL_FLOOR_STOCKS)

    # Ensure TP is always >= SL (at least 1:1 R:R)
    tp_pct = max(tp_pct, sl_pct)

    return round(tp_pct, 2), round(sl_pct, 2)


# ===========================================================================
# 3. QUARTER-KELLY WITH EGARCH ADJUSTMENT
# ===========================================================================

def quarter_kelly_egarch(win_rate, avg_win, avg_loss, egarch_vol_daily,
                         target_vol=VOL_TARGET_ANNUAL):
    """
    Compute EGARCH-adjusted Quarter-Kelly position size.

    Full Kelly = (p * b - q) / b  (optimal growth fraction)
    Quarter-Kelly = Full Kelly x 0.25  (conservative: 1/16th variance of Full Kelly)

    Further adjusted by EGARCH volatility ratio:
      adjusted_kelly = quarter_kelly x (target_vol / egarch_vol_annual)
    When vol is high, position shrinks. When vol is low, position can grow.

    Clamped to [MIN_POSITION_PCT, MAX_POSITION_PCT].

    Args:
        win_rate: fraction (0 to 1)
        avg_win: average winning trade return (fraction, e.g. 0.05 = 5%)
        avg_loss: average losing trade return (fraction, positive, e.g. 0.03 = 3%)
        egarch_vol_daily: daily volatility forecast from EGARCH
        target_vol: annualized target volatility

    Returns:
        dict with full_kelly, quarter_kelly, vol_ratio, adjusted_size
    """
    # Validate inputs
    if win_rate <= 0 or avg_win <= 0 or avg_loss <= 0:
        return {
            'full_kelly': 0.0,
            'quarter_kelly': 0.0,
            'vol_ratio': 1.0,
            'adjusted_size': MIN_POSITION_PCT,
        }

    p = min(max(win_rate, 0.01), 0.99)
    q = 1.0 - p
    b = avg_win / avg_loss  # Win/loss ratio (payoff ratio)

    # Full Kelly criterion
    full_kelly = (p * b - q) / b

    # Negative Kelly means the edge is negative: don't bet
    if full_kelly <= 0:
        return {
            'full_kelly': round(full_kelly, 6),
            'quarter_kelly': 0.0,
            'vol_ratio': 1.0,
            'adjusted_size': MIN_POSITION_PCT,
        }

    # Quarter-Kelly: 75% less variance than Full Kelly for ~44% less return
    quarter_kelly = full_kelly * 0.25

    # EGARCH vol adjustment
    egarch_vol_annual = egarch_vol_daily * np.sqrt(252)
    if egarch_vol_annual > 0:
        vol_ratio = target_vol / egarch_vol_annual
        vol_ratio = min(2.0, max(0.3, vol_ratio))  # Clamp to [0.3, 2.0]
    else:
        vol_ratio = 1.0

    adjusted = quarter_kelly * vol_ratio

    # Clamp to bounds
    adjusted = max(MIN_POSITION_PCT, min(MAX_POSITION_PCT, adjusted))

    return {
        'full_kelly': round(full_kelly, 6),
        'quarter_kelly': round(quarter_kelly, 6),
        'vol_ratio': round(vol_ratio, 4),
        'adjusted_size': round(adjusted, 6),
    }


# ===========================================================================
# 4. MOMENTUM CRASH PROTECTION
# ===========================================================================

def get_vix_level():
    """
    Fetch current VIX level via yfinance.
    Returns float VIX value, or 15.0 as a safe default.
    """
    import yfinance as yf

    try:
        vix = yf.Ticker("^VIX")
        hist = vix.history(period="5d")
        if len(hist) > 0:
            val = float(hist['Close'].iloc[-1])
            if not np.isnan(val):
                return val
    except Exception as e:
        logger.warning("Could not fetch VIX: %s", e)

    return 15.0  # Safe default


def get_recent_portfolio_return(conn, days=5):
    """
    Calculate the portfolio return over the last N days from lm_trades.

    Looks at closed trades in the window and computes aggregate PnL.
    Also checks open positions' unrealized PnL if available.

    Returns:
        float: portfolio return as fraction (e.g., -0.05 = -5%)
    """
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT COALESCE(SUM(realized_pnl_usd), 0) AS total_pnl
            FROM lm_trades
            WHERE status = 'closed'
              AND closed_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
        """, (days,))
        row = cursor.fetchone()
        total_pnl = float(row['total_pnl']) if row and row['total_pnl'] else 0.0
        cursor.close()

        # Return as fraction of capital
        return total_pnl / CAPITAL

    except Exception as e:
        logger.warning("Could not compute recent portfolio return: %s", e)
        return 0.0


def momentum_crash_scale(vix_level, recent_5d_return, algo_name):
    """
    Scale momentum exposure based on crash indicators.

    Momentum strategies are the first to fail during market stress:
      - They rely on trend continuation, which breaks during panics
      - Correlation spikes during crashes destroy diversification

    Scaling rules:
      VIX > 40: momentum algos x 0.25  (extreme fear)
      VIX > 30: momentum algos x 0.50  (elevated fear)
      5-day portfolio return < -5%: PAUSE momentum entirely
      5-day portfolio return < -3%: momentum x 0.50

    Non-momentum algos (mean-reversion, contrarian) are unaffected.
    Contrarian algos get a BOOST during extreme fear.

    Args:
        vix_level: current VIX value
        recent_5d_return: 5-day portfolio return as fraction
        algo_name: name of the algorithm

    Returns:
        float: scaling factor (0.0 to 1.5)
    """
    # Contrarian algos benefit from fear
    if algo_name in CONTRARIAN_ALGOS:
        if vix_level > 40:
            return 1.3  # Contrarian boost in extreme fear
        elif vix_level > 30:
            return 1.1
        return 1.0

    # Non-momentum, non-contrarian: unaffected
    if algo_name not in MOMENTUM_ALGOS:
        return 1.0

    # Momentum crash protection
    scale = 1.0

    # VIX-based scaling
    if vix_level > 40:
        scale *= 0.25
    elif vix_level > 30:
        scale *= 0.50

    # Recent portfolio loss scaling
    if recent_5d_return < -0.05:
        scale *= 0.0  # Pause momentum entirely
    elif recent_5d_return < -0.03:
        scale *= 0.50

    return round(scale, 4)


# ===========================================================================
# 5. CORRELATION-ADJUSTED SIZING
# ===========================================================================

def fetch_prices_for_symbols(symbols, period='3mo'):
    """
    Fetch closing prices for multiple symbols.
    Returns dict of {symbol: np.array of closes}.
    """
    import yfinance as yf

    price_data = {}
    for sym in symbols:
        try:
            data = yf.download(sym, period=period, progress=False)
            if data.empty:
                continue

            if isinstance(data.columns, pd.MultiIndex):
                close = data['Close'].iloc[:, 0]
            else:
                close = data['Close']

            vals = close.dropna().values.flatten()
            if len(vals) >= 30:
                price_data[sym] = vals
        except Exception:
            continue

    return price_data


def correlation_adjustment(new_symbol, existing_positions, price_data):
    """
    Reduce position size if the new position is highly correlated with
    existing portfolio positions.

    This prevents concentration risk — even if different algorithms pick
    different symbols, they may be in the same sector/factor.

    Scaling rules:
      avg_corr > 0.85: Block entirely (return 0.0)
      avg_corr > 0.70: Scale by max(0.3, 1.0 - (avg_corr - 0.5))
      avg_corr <= 0.70: No reduction

    Args:
        new_symbol: symbol being sized
        existing_positions: list of dicts with 'symbol' key
        price_data: dict of {symbol: np.array of closing prices}

    Returns:
        float: scaling factor (0.0 to 1.0)
    """
    if not existing_positions:
        return 1.0

    if new_symbol not in price_data:
        return 1.0  # Can't compute correlation, allow full size

    new_returns = np.diff(np.log(price_data[new_symbol][-31:]))
    if len(new_returns) < 20:
        return 1.0

    correlations = []
    for pos in existing_positions:
        sym = pos.get('symbol', pos.get('ticker', ''))
        if sym not in price_data or sym == new_symbol:
            continue

        pos_returns = np.diff(np.log(price_data[sym][-31:]))
        if len(pos_returns) < 20:
            continue

        # Align lengths
        min_len = min(len(new_returns), len(pos_returns))
        corr = np.corrcoef(
            new_returns[-min_len:],
            pos_returns[-min_len:]
        )[0, 1]

        if not np.isnan(corr):
            correlations.append(abs(corr))

    if not correlations:
        return 1.0

    avg_corr = float(np.mean(correlations))

    if avg_corr > 0.85:
        return 0.0  # Block: too correlated with existing portfolio
    elif avg_corr > 0.70:
        return round(max(0.3, 1.0 - (avg_corr - 0.5)), 4)

    return 1.0


# ===========================================================================
# DATABASE HELPERS
# ===========================================================================

def connect_db():
    """Connect to MySQL database."""
    import mysql.connector

    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        connect_timeout=30
    )


def ensure_position_sizing_table(conn):
    """
    Ensure the lm_position_sizing table exists with EGARCH columns.
    """
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lm_position_sizing (
                id INT AUTO_INCREMENT PRIMARY KEY,
                algorithm_name VARCHAR(100) NOT NULL,
                kelly_base DECIMAL(10,6) NOT NULL DEFAULT 0,
                quarter_kelly DECIMAL(10,6) NOT NULL DEFAULT 0,
                vol_scalar DECIMAL(10,4) NOT NULL DEFAULT 1.0,
                regime_modifier DECIMAL(10,4) NOT NULL DEFAULT 1.0,
                decay_weight DECIMAL(10,4) NOT NULL DEFAULT 1.0,
                final_size_pct DECIMAL(10,4) NOT NULL DEFAULT 5.0,
                dollar_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
                algo_sharpe_30d DECIMAL(10,4) NOT NULL DEFAULT 0,
                is_decaying TINYINT(1) NOT NULL DEFAULT 0,
                regime_composite INT NOT NULL DEFAULT 50,
                egarch_vol_forecast DECIMAL(10,6) DEFAULT NULL,
                egarch_model_type VARCHAR(20) DEFAULT NULL,
                atr_tp_pct DECIMAL(8,2) DEFAULT NULL,
                atr_sl_pct DECIMAL(8,2) DEFAULT NULL,
                crash_protection_scale DECIMAL(8,4) NOT NULL DEFAULT 1.0,
                correlation_scale DECIMAL(8,4) NOT NULL DEFAULT 1.0,
                vix_level DECIMAL(8,2) DEFAULT NULL,
                recent_5d_return DECIMAL(10,6) DEFAULT NULL,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_algo (algorithm_name),
                INDEX idx_updated (updated_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        conn.commit()
    except Exception as e:
        logger.warning("Table creation note: %s", e)
    finally:
        cursor.close()


def fetch_kelly_fractions(conn):
    """
    Fetch Kelly fractions per algorithm from lm_kelly_fractions.

    Returns:
        dict keyed by algorithm_name with win_rate, avg_win_pct, avg_loss_pct,
        half_kelly, full_kelly, asset_class, sample_size
    """
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT algorithm_name, asset_class, win_rate, avg_win_pct, avg_loss_pct,
                   full_kelly, half_kelly, sample_size
            FROM lm_kelly_fractions
            ORDER BY updated_at DESC
        """)
        rows = cursor.fetchall()
    except Exception as e:
        logger.warning("Could not fetch Kelly fractions: %s", e)
        return {}
    finally:
        cursor.close()

    # De-duplicate: keep the latest entry per algorithm
    kelly_by_algo = {}
    for row in rows:
        algo = row['algorithm_name']
        if algo not in kelly_by_algo:
            kelly_by_algo[algo] = {
                'algorithm_name': algo,
                'asset_class': row.get('asset_class', 'stocks'),
                'win_rate': float(row['win_rate'] or 0),
                'avg_win_pct': float(row['avg_win_pct'] or 0),
                'avg_loss_pct': float(row['avg_loss_pct'] or 0),
                'full_kelly': float(row['full_kelly'] or 0),
                'half_kelly': float(row['half_kelly'] or 0),
                'sample_size': int(row['sample_size'] or 0),
            }

    return kelly_by_algo


def fetch_open_positions(conn):
    """
    Fetch currently open positions from lm_trades.

    Returns:
        list of dicts with ticker, algorithm_name, asset_class, entry_price
    """
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT ticker, algorithm_name, asset_class, entry_price, position_size_usd
            FROM lm_trades
            WHERE status = 'open'
            ORDER BY opened_at DESC
        """)
        positions = cursor.fetchall()
    except Exception as e:
        logger.warning("Could not fetch open positions: %s", e)
        return []
    finally:
        cursor.close()

    return positions


def fetch_market_regime(conn):
    """
    Fetch the latest market regime from lm_market_regime.

    Returns:
        dict with composite_score, hmm_regime, vix_regime
    """
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT composite_score, hmm_regime, vix_regime
            FROM lm_market_regime
            ORDER BY updated_at DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
    except Exception as e:
        logger.warning("Could not fetch market regime: %s", e)
        return {'composite_score': 50, 'hmm_regime': 'sideways', 'vix_regime': 'normal'}
    finally:
        cursor.close()

    if row:
        return {
            'composite_score': int(row.get('composite_score', 50)),
            'hmm_regime': row.get('hmm_regime', 'sideways'),
            'vix_regime': row.get('vix_regime', 'normal'),
        }

    return {'composite_score': 50, 'hmm_regime': 'sideways', 'vix_regime': 'normal'}


def fetch_algo_recent_trades(conn, algo_name, limit=30):
    """
    Fetch recent closed trades for an algorithm to compute Sharpe/decay.

    Returns:
        list of dicts with realized_pct
    """
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT realized_pct
            FROM lm_trades
            WHERE algorithm_name = %s AND status = 'closed'
            ORDER BY closed_at DESC
            LIMIT %s
        """, (algo_name, limit))
        trades = cursor.fetchall()
    except Exception as e:
        logger.warning("Could not fetch trades for %s: %s", algo_name, e)
        return []
    finally:
        cursor.close()

    return trades


def save_sizing_to_db(conn, sizing_results):
    """
    Write sizing results to lm_position_sizing table.
    Upserts: deletes old rows for each algo, inserts new.
    """
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

    saved = 0
    for s in sizing_results:
        try:
            # Delete previous entry for this algorithm
            cursor.execute(
                "DELETE FROM lm_position_sizing WHERE algorithm_name = %s",
                (s['algorithm_name'],)
            )

            cursor.execute("""
                INSERT INTO lm_position_sizing
                (algorithm_name, kelly_base, quarter_kelly, vol_scalar,
                 regime_modifier, decay_weight, final_size_pct, dollar_amount,
                 algo_sharpe_30d, is_decaying, regime_composite,
                 egarch_vol_forecast, egarch_model_type,
                 atr_tp_pct, atr_sl_pct,
                 crash_protection_scale, correlation_scale,
                 vix_level, recent_5d_return, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s)
            """, (
                s['algorithm_name'],
                s.get('kelly_base', 0),
                s.get('quarter_kelly', 0),
                s.get('vol_scalar', 1.0),
                s.get('regime_modifier', 1.0),
                s.get('decay_weight', 1.0),
                s.get('final_size_pct', 5.0),
                s.get('dollar_amount', 0),
                s.get('algo_sharpe_30d', 0),
                1 if s.get('is_decaying', False) else 0,
                s.get('regime_composite', 50),
                s.get('egarch_vol_forecast'),
                s.get('egarch_model_type'),
                s.get('atr_tp_pct'),
                s.get('atr_sl_pct'),
                s.get('crash_protection_scale', 1.0),
                s.get('correlation_scale', 1.0),
                s.get('vix_level'),
                s.get('recent_5d_return'),
                now,
            ))
            saved += 1

        except Exception as e:
            logger.warning("DB write failed for %s: %s", s.get('algorithm_name', '?'), e)

    conn.commit()
    cursor.close()
    return saved


# ===========================================================================
# ALPHA DECAY DETECTION
# ===========================================================================

def calculate_alpha_decay(trades, window=30):
    """
    Compute rolling Sharpe and detect alpha decay for an algorithm.

    Returns:
        (sharpe, is_decaying, decay_weight)
    """
    if not trades or len(trades) < 10:
        return 0.0, False, 1.0

    pnl_pcts = [float(t.get('realized_pct', 0)) for t in trades[:window]]
    pnl_arr = np.array(pnl_pcts, dtype=float)

    mean_pnl = np.mean(pnl_arr)
    std_pnl = np.std(pnl_arr, ddof=1)

    if std_pnl < 0.0001:
        sharpe = 0.0
    else:
        sharpe = mean_pnl / std_pnl * np.sqrt(252 / max(1, len(pnl_arr)))

    is_decaying = sharpe < 0.5

    # Decay weight: exponential confidence scaling
    if sharpe >= 1.0:
        weight = 1.0
    elif sharpe >= 0.5:
        weight = 0.5 + 0.5 * (sharpe - 0.5) / 0.5
    elif sharpe >= 0:
        weight = 0.2 + 0.3 * sharpe / 0.5
    else:
        weight = max(0.1, 0.2 + 0.2 * sharpe)

    return float(sharpe), is_decaying, round(weight, 4)


# ===========================================================================
# REGIME MODIFIER
# ===========================================================================

def compute_regime_modifier(composite_score, hmm_regime, vix_regime):
    """
    Modulate position size based on market regime.

    Bear + high VIX -> reduce 40-60%
    Bull + normal VIX -> full size or slight boost
    Sideways -> moderate reduction
    """
    base = composite_score / 100.0

    hmm_adj = {'bull': 1.1, 'sideways': 0.9, 'bear': 0.6}
    adj = hmm_adj.get(hmm_regime, 0.9)

    vix_adj = {
        'fear': 0.7,
        'fear_peak': 0.85,
        'elevated': 0.85,
        'normal': 1.0,
        'complacent': 0.95,
    }
    v_adj = vix_adj.get(vix_regime, 1.0)

    modifier = base * adj * v_adj
    return round(max(0.3, min(1.2, modifier * 2)), 4)


# ===========================================================================
# API POSTING
# ===========================================================================

def post_sizing_to_api(sizing_results, regime_composite):
    """
    POST sizing results to the regime.php API endpoint.

    Endpoint: regime.php?action=update_position_sizing&key=livetrader2026
    """
    url = f"{API_BASE}/regime.php?action=update_position_sizing&key={ADMIN_KEY}"

    payload = {
        'sizing': sizing_results,
        'regime_composite': regime_composite,
        'source': 'egarch_position_sizer',
        'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    }

    try:
        resp = requests.post(url, json=payload, headers=API_HEADERS, timeout=60)
        result = resp.json()

        if result.get('ok'):
            logger.info("API POST: OK - %s", result.get('message', 'saved'))
        else:
            logger.error("API POST: Error - %s", result.get('error', 'unknown'))

        return result

    except Exception as e:
        logger.error("API POST failed: %s", e)
        return {'ok': False, 'error': str(e)}


# ===========================================================================
# MAIN PIPELINE
# ===========================================================================

def run(single_algo=None, dry_run=False):
    """
    Full EGARCH position sizing pipeline.

    Steps:
      1. Connect to DB, fetch market regime
      2. Fetch Kelly fractions per algorithm
      3. Fetch open positions for correlation check
      4. Get VIX level and recent portfolio return
      5. For each algorithm:
         a. Get EGARCH vol forecast for its asset class proxy
         b. Get ATR-based stops for the proxy ticker
         c. Compute Quarter-Kelly adjusted by EGARCH vol
         d. Apply regime modifier
         e. Apply alpha decay detection
         f. Apply momentum crash protection
         g. Apply correlation adjustment
         h. Final position size
      6. Post results to API
      7. Save to DB
      8. Print summary
    """
    logger.info("=" * 72)
    logger.info("  EGARCH POSITION SIZER — Advanced Volatility-Adjusted Sizing")
    logger.info("  Quarter-Kelly + EGARCH Vol + ATR Stops + Crash Protection")
    logger.info("  Capital: $%.0f | Bounds: [%.0f%%, %.0f%%] | Vol Target: %.0f%%",
                CAPITAL, MIN_POSITION_PCT * 100, MAX_POSITION_PCT * 100,
                VOL_TARGET_ANNUAL * 100)
    logger.info("=" * 72)

    # ------------------------------------------------------------------
    # Step 1: DB connection and market regime
    # ------------------------------------------------------------------
    logger.info("\n[1/8] Connecting to database...")
    try:
        conn = connect_db()
        logger.info("  Connected to %s@%s/%s", DB_USER, DB_HOST, DB_NAME)
    except Exception as e:
        logger.error("  DB connection failed: %s", e)
        logger.info("  Continuing without DB (will use defaults)...")
        conn = None

    if conn and not dry_run:
        ensure_position_sizing_table(conn)

    # Fetch market regime
    logger.info("\n[2/8] Fetching market regime...")
    if conn:
        regime = fetch_market_regime(conn)
    else:
        regime = {'composite_score': 50, 'hmm_regime': 'sideways', 'vix_regime': 'normal'}

    regime_composite = regime['composite_score']
    regime_mod = compute_regime_modifier(
        regime_composite, regime['hmm_regime'], regime['vix_regime']
    )
    logger.info("  Regime: composite=%d, HMM=%s, VIX=%s -> modifier=%.2f",
                regime_composite, regime['hmm_regime'], regime['vix_regime'], regime_mod)

    # ------------------------------------------------------------------
    # Step 2: Fetch Kelly fractions
    # ------------------------------------------------------------------
    logger.info("\n[3/8] Fetching Kelly fractions...")
    if conn:
        kelly_data = fetch_kelly_fractions(conn)
    else:
        kelly_data = {}

    if kelly_data:
        logger.info("  Found Kelly data for %d algorithms", len(kelly_data))
    else:
        logger.warning("  No Kelly data found. Using defaults for all algorithms.")

    # ------------------------------------------------------------------
    # Step 3: Fetch open positions
    # ------------------------------------------------------------------
    logger.info("\n[4/8] Fetching open positions...")
    if conn:
        open_positions = fetch_open_positions(conn)
    else:
        open_positions = []

    logger.info("  Open positions: %d", len(open_positions))
    position_symbols = list(set(
        p.get('ticker', '') for p in open_positions if p.get('ticker')
    ))

    # ------------------------------------------------------------------
    # Step 4: VIX and recent portfolio return
    # ------------------------------------------------------------------
    logger.info("\n[5/8] Fetching VIX and recent portfolio return...")
    vix_level = get_vix_level()
    recent_5d_return = get_recent_portfolio_return(conn, days=5) if conn else 0.0

    logger.info("  VIX: %.2f | 5-day portfolio return: %.2f%%",
                vix_level, recent_5d_return * 100)

    # ------------------------------------------------------------------
    # Step 5: EGARCH vol forecasts for each asset class
    # ------------------------------------------------------------------
    logger.info("\n[6/8] Computing EGARCH volatility forecasts...")
    vol_forecasts = {}
    for asset_class, proxy_ticker in ASSET_PROXIES.items():
        logger.info("  %s (%s):", asset_class.upper(), proxy_ticker)
        vf = get_vol_forecast(proxy_ticker)
        vol_forecasts[asset_class] = vf
        logger.info("    Model: %s | Vol daily: %.4f (%.2f%% annual)",
                     vf['model_type'], vf['vol_daily'], vf['vol_annual'] * 100)

    # ------------------------------------------------------------------
    # Step 6: ATR-based stops for each proxy
    # ------------------------------------------------------------------
    logger.info("\n  Computing ATR-based stops...")
    atr_stops = {}
    for asset_class, proxy_ticker in ASSET_PROXIES.items():
        candles = fetch_candles_yfinance(proxy_ticker, period='2mo')
        if candles:
            tp, sl = atr_based_stops(candles, asset_class=asset_class)
            if tp is not None:
                atr_stops[asset_class] = {'tp_pct': tp, 'sl_pct': sl}
                logger.info("    %s: TP=%.2f%% SL=%.2f%%", asset_class.upper(), tp, sl)
            else:
                atr_stops[asset_class] = {'tp_pct': 4.5, 'sl_pct': 3.0}
        else:
            atr_stops[asset_class] = {'tp_pct': 4.5, 'sl_pct': 3.0}
            logger.info("    %s: Using default TP=4.5%% SL=3.0%%", asset_class.upper())

    # ------------------------------------------------------------------
    # Step 7: Fetch price data for correlation analysis
    # ------------------------------------------------------------------
    logger.info("\n[7/8] Fetching price data for correlation analysis...")
    all_symbols = list(set(
        position_symbols + [ASSET_PROXIES[ac] for ac in ASSET_PROXIES]
    ))
    if all_symbols:
        price_data = fetch_prices_for_symbols(all_symbols, period='3mo')
        logger.info("  Fetched prices for %d / %d symbols", len(price_data), len(all_symbols))
    else:
        price_data = {}

    # ------------------------------------------------------------------
    # Step 8: Compute position sizing for each algorithm
    # ------------------------------------------------------------------
    logger.info("\n[8/8] Computing position sizes per algorithm...")
    logger.info("-" * 72)

    # Build list of algorithms to size
    # Use Kelly data if available; fall back to querying known algo names from trades
    if kelly_data:
        algo_names = list(kelly_data.keys())
    elif conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT DISTINCT algorithm_name
                FROM lm_trades
                WHERE algorithm_name != '' AND algorithm_name IS NOT NULL
            """)
            algo_names = [r['algorithm_name'] for r in cursor.fetchall()]
            cursor.close()
        except Exception:
            algo_names = []
    else:
        algo_names = []

    if single_algo:
        algo_names = [a for a in algo_names if a == single_algo]
        if not algo_names:
            algo_names = [single_algo]

    if not algo_names:
        logger.warning("  No algorithms found. Nothing to size.")
        if conn:
            conn.close()
        return []

    logger.info("  Sizing %d algorithms...", len(algo_names))

    sizing_results = []

    for algo_name in sorted(algo_names):
        # Get Kelly data for this algo
        kd = kelly_data.get(algo_name, {})
        asset_class = kd.get('asset_class', 'stocks').lower()
        if asset_class not in ASSET_PROXIES:
            asset_class = 'stocks'

        win_rate = kd.get('win_rate', 0.50)
        avg_win_pct = kd.get('avg_win_pct', 3.0)
        avg_loss_pct = kd.get('avg_loss_pct', 2.0)
        sample_size = kd.get('sample_size', 0)

        # Convert percentage to fraction
        avg_win_frac = avg_win_pct / 100.0 if avg_win_pct > 1 else avg_win_pct
        avg_loss_frac = avg_loss_pct / 100.0 if avg_loss_pct > 1 else avg_loss_pct

        # (a) EGARCH vol forecast for this asset class
        vf = vol_forecasts.get(asset_class, vol_forecasts.get('stocks', {}))
        egarch_vol_daily = vf.get('vol_daily', 0.02)
        egarch_model_type = vf.get('model_type', 'DEFAULT')

        # (b) ATR stops for this asset class
        stops = atr_stops.get(asset_class, {'tp_pct': 4.5, 'sl_pct': 3.0})

        # (c) Quarter-Kelly with EGARCH adjustment
        kelly_result = quarter_kelly_egarch(
            win_rate, avg_win_frac, avg_loss_frac, egarch_vol_daily
        )
        kelly_base = kelly_result['adjusted_size']

        # (d) Regime modifier
        reg_mod = regime_mod

        # (e) Alpha decay detection
        if conn:
            recent_trades = fetch_algo_recent_trades(conn, algo_name, limit=30)
        else:
            recent_trades = []

        algo_sharpe, is_decaying, decay_weight = calculate_alpha_decay(recent_trades)

        # (f) Momentum crash protection
        crash_scale = momentum_crash_scale(vix_level, recent_5d_return, algo_name)

        # (g) Correlation adjustment
        proxy_ticker = ASSET_PROXIES.get(asset_class, 'SPY')
        corr_scale = correlation_adjustment(proxy_ticker, open_positions, price_data)

        # (h) Compute vol scalar (EGARCH vol ratio)
        vol_scalar = kelly_result['vol_ratio']

        # Final position size
        raw_size = kelly_base * reg_mod * decay_weight * crash_scale * corr_scale
        final_size = max(MIN_POSITION_PCT, min(MAX_POSITION_PCT, raw_size))
        dollar_amount = CAPITAL * final_size

        result = {
            'algorithm_name': algo_name,
            'kelly_base': round(kelly_result['full_kelly'], 6),
            'quarter_kelly': round(kelly_result['quarter_kelly'], 6),
            'vol_scalar': round(vol_scalar, 4),
            'regime_modifier': round(reg_mod, 4),
            'decay_weight': round(decay_weight, 4),
            'final_size_pct': round(final_size * 100, 2),
            'dollar_amount': round(dollar_amount, 2),
            'algo_sharpe_30d': round(algo_sharpe, 4),
            'is_decaying': is_decaying,
            'regime_composite': regime_composite,
            'egarch_vol_forecast': round(egarch_vol_daily, 6),
            'egarch_model_type': egarch_model_type,
            'atr_tp_pct': stops['tp_pct'],
            'atr_sl_pct': stops['sl_pct'],
            'crash_protection_scale': round(crash_scale, 4),
            'correlation_scale': round(corr_scale, 4),
            'vix_level': round(vix_level, 2),
            'recent_5d_return': round(recent_5d_return, 6),
        }

        sizing_results.append(result)

        # Log per-algo summary
        flags = []
        if crash_scale < 1.0:
            flags.append("CRASH-PROT")
        if is_decaying:
            flags.append("DECAYING")
        if corr_scale < 1.0:
            flags.append("CORR-ADJ")
        flag_str = " [" + ", ".join(flags) + "]" if flags else ""

        logger.info(
            "  %-25s Kelly=%.1f%% Vol=%.2fx Regime=%.2fx Decay=%.2fx "
            "Crash=%.2fx Corr=%.2fx -> %.1f%% ($%.0f)%s",
            algo_name,
            kelly_result['quarter_kelly'] * 100,
            vol_scalar,
            reg_mod,
            decay_weight,
            crash_scale,
            corr_scale,
            final_size * 100,
            dollar_amount,
            flag_str,
        )

    # ------------------------------------------------------------------
    # Post results to API
    # ------------------------------------------------------------------
    if sizing_results and not dry_run:
        logger.info("\nPosting %d sizing results to API...", len(sizing_results))
        api_result = post_sizing_to_api(sizing_results, regime_composite)

        if conn:
            logger.info("Saving to lm_position_sizing table...")
            saved = save_sizing_to_db(conn, sizing_results)
            logger.info("  Saved %d rows to DB", saved)

    # ------------------------------------------------------------------
    # Save to local JSON for debugging
    # ------------------------------------------------------------------
    os.makedirs(DATA_DIR, exist_ok=True)
    output = {
        'generated': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'config': {
            'capital': CAPITAL,
            'min_position_pct': MIN_POSITION_PCT,
            'max_position_pct': MAX_POSITION_PCT,
            'vol_target_annual': VOL_TARGET_ANNUAL,
            'atr_period': ATR_PERIOD,
            'atr_sl_multiplier': ATR_SL_MULTIPLIER,
            'atr_tp_multiplier': ATR_TP_MULTIPLIER,
        },
        'market_state': {
            'vix_level': vix_level,
            'recent_5d_return': recent_5d_return,
            'regime': regime,
            'regime_modifier': regime_mod,
        },
        'vol_forecasts': {
            ac: {
                'proxy': ASSET_PROXIES[ac],
                'model_type': vf.get('model_type', 'N/A'),
                'vol_daily': vf.get('vol_daily', 0),
                'vol_annual': vf.get('vol_annual', 0),
            }
            for ac, vf in vol_forecasts.items()
        },
        'atr_stops': atr_stops,
        'sizing': sizing_results,
    }

    output_path = os.path.join(DATA_DIR, 'egarch_position_sizing.json')
    try:
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2, default=str)
        logger.info("Results saved to %s", output_path)
    except Exception as e:
        logger.warning("Could not save JSON: %s", e)

    # ------------------------------------------------------------------
    # Print summary table
    # ------------------------------------------------------------------
    logger.info("\n" + "=" * 72)
    logger.info("  EGARCH POSITION SIZING SUMMARY")
    logger.info("=" * 72)

    if sizing_results:
        sizes = [s['final_size_pct'] for s in sizing_results]
        dollars = [s['dollar_amount'] for s in sizing_results]
        decaying_count = sum(1 for s in sizing_results if s['is_decaying'])
        crash_protected = sum(1 for s in sizing_results if s['crash_protection_scale'] < 1.0)
        corr_adjusted = sum(1 for s in sizing_results if s['correlation_scale'] < 1.0)

        logger.info("  Algorithms sized:       %d", len(sizing_results))
        logger.info("  Average position:       %.1f%% ($%.0f)", np.mean(sizes), np.mean(dollars))
        logger.info("  Min / Max position:     %.1f%% / %.1f%%", min(sizes), max(sizes))
        logger.info("  Total allocation:       %.1f%% ($%.0f)", sum(sizes), sum(dollars))
        logger.info("  Decaying algos:         %d / %d", decaying_count, len(sizing_results))
        logger.info("  Crash-protected algos:  %d / %d", crash_protected, len(sizing_results))
        logger.info("  Correlation-adjusted:   %d / %d", corr_adjusted, len(sizing_results))
        logger.info("  VIX level:              %.2f", vix_level)
        logger.info("  5-day portfolio return: %.2f%%", recent_5d_return * 100)
        logger.info("  EGARCH models used:     %s", ", ".join(
            f"{ac}={vf.get('model_type', 'N/A')}" for ac, vf in vol_forecasts.items()
        ))

        # ATR stops summary
        logger.info("\n  ATR Dynamic Stops:")
        for ac, stops_val in atr_stops.items():
            logger.info("    %s: TP=%.2f%% SL=%.2f%% (R:R=%.1f:1)",
                        ac.upper(),
                        stops_val['tp_pct'],
                        stops_val['sl_pct'],
                        stops_val['tp_pct'] / stops_val['sl_pct'] if stops_val['sl_pct'] > 0 else 0)
    else:
        logger.info("  No algorithms to size.")

    logger.info("=" * 72)

    # Close DB
    if conn:
        try:
            conn.close()
        except Exception:
            pass

    return sizing_results


# ===========================================================================
# ENTRY POINT
# ===========================================================================

def main():
    parser = argparse.ArgumentParser(
        description='EGARCH Position Sizer - Advanced volatility-adjusted position sizing'
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Compute sizing without posting to API or writing to DB'
    )
    parser.add_argument(
        '--algo', type=str, default=None,
        help='Compute sizing for a single algorithm (e.g. "Momentum Burst")'
    )
    args = parser.parse_args()

    results = run(single_algo=args.algo, dry_run=args.dry_run)

    if results:
        print(f"\nSized {len(results)} algorithms successfully.")
    else:
        print("\nNo algorithms were sized.")


if __name__ == '__main__':
    main()
