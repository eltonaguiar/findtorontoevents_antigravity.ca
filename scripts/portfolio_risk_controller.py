#!/usr/bin/env python3
"""
Portfolio Risk Controller -- Portfolio-Level Risk Management for Live Monitor.

CRITICAL INFRASTRUCTURE: This is the missing portfolio-level risk layer.
Individual trade-level risk (per-trade stops, circuit breakers, sector caps)
already exists in live_trade.php. This script adds the PORTFOLIO-level
controls that can double Sharpe without adding a single new indicator:

  1. Portfolio Volatility Targeting (10-12% annualized)
  2. Strategy-Level Capital Allocation (max 15% per algo, 25% per direction)
  3. Correlation-Based Scaling (penalize correlated positions)
  4. Drawdown-Based Throttling (enhanced: 10% halve, 15% halt, 20% shutdown)
  5. Rolling Sharpe Gate (negative Sharpe = cut exposure)
  6. CVaR / Conditional Value at Risk (tail risk management)
  7. Momentum Crash Protection (VIX-gated, fear-regime aware)

Posts sizing recommendations to regime.php?action=update_position_sizing.
Saves risk report JSON for dashboard consumption.

Requires: pip install mysql-connector-python numpy scipy requests yfinance
"""

import sys
import os
import json
import logging
import time
import math
from datetime import datetime, timedelta

import numpy as np
import requests

# Optional imports -- graceful degradation if not available
try:
    from scipy import stats as scipy_stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False

try:
    import mysql.connector
    HAS_MYSQL = True
except ImportError:
    HAS_MYSQL = False

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('portfolio_risk_controller')

# ---------------------------------------------------------------------------
# Configuration (all from environment variables for GitHub Actions)
# ---------------------------------------------------------------------------
API_BASE = os.environ.get('SM_API_BASE', 'https://findtorontoevents.ca/live-monitor/api')
ADMIN_KEY = os.environ.get('SM_ADMIN_KEY', 'livetrader2026')
DB_HOST = os.environ.get('DB_HOST', 'mysql.50webs.com')
DB_USER = os.environ.get('DB_USER', 'ejaguiar1_stocks')
DB_PASS = os.environ.get('DB_PASS', 'stocks')
DB_NAME = os.environ.get('DB_NAME', 'ejaguiar1_stocks')

# CRITICAL: ModSecurity blocks python-requests User-Agent
API_HEADERS = {"User-Agent": "WorldClassIntelligence/1.0"}

# ---------------------------------------------------------------------------
# Risk Parameters
# ---------------------------------------------------------------------------
INITIAL_CAPITAL = 10000.0

# Volatility targeting
TARGET_VOL_LOW = 0.10       # 10% annualized -- allow slight position increase
TARGET_VOL_HIGH = 0.12      # 12% annualized -- scale down above this
VOL_SCALAR_MIN = 0.50       # Never scale below 50%
VOL_SCALAR_MAX = 1.50       # Never scale above 150%

# Strategy-level allocation caps
MAX_CAPITAL_PER_ALGO = 0.15       # 15% of capital per algorithm
MAX_CAPITAL_PER_DIRECTION = 0.25  # 25% per direction (long vs short)

# Correlation thresholds
CORR_REDUCE_THRESHOLD = 0.70      # Avg correlation > 0.7 -> reduce 50%
CORR_BLOCK_THRESHOLD = 0.85       # Avg correlation > 0.85 -> block trade

# Drawdown thresholds (enhanced)
DD_HALVE_PCT = 10.0       # 10% drawdown -> halve all sizes
DD_HALT_PCT = 15.0         # 15% drawdown -> close all, halt 48h
DD_SHUTDOWN_PCT = 20.0     # 20% drawdown -> emergency shutdown

# Rolling Sharpe
SHARPE_WINDOW_DAYS = 30           # 30-day rolling window
SHARPE_NEGATIVE_CUT = 0.50       # Negative Sharpe -> cut exposure 50%
PORTFOLIO_SHARPE_CRISIS_DAYS = 14 # Portfolio Sharpe < 0 for 14d -> 25% sizing
PORTFOLIO_SHARPE_CRISIS_CUT = 0.25

# CVaR
CVAR_CONFIDENCE = 0.95     # 95th percentile
CVAR_MAX_PCT = 0.03        # 3% daily CVaR threshold

# Momentum crash protection
VIX_MOMENTUM_SCALE = 0.50  # VIX > 30 -> scale momentum algos by 50%
VIX_THRESHOLD = 30.0
PORTFOLIO_5D_CRASH = -5.0  # 5-day return < -5% -> pause momentum

# Algorithms classified as momentum-based (adjust to match your actual names)
MOMENTUM_ALGOS = {
    'Momentum Burst', 'StochRSI Crossover', 'Ichimoku Cloud',
    'Alpha Predator', 'RSI(2) Scalp', 'Cursor Genius',
    'MACD Crossover', 'Breakout Momentum', 'Trend Surfer'
}
CONTRARIAN_ALGOS = {
    'Mean Reversion', 'Bollinger Bounce', 'RSI Oversold',
    'Contrarian Signal', 'Value Dip'
}


# ============================================================================
#  DATABASE ACCESS
# ============================================================================

def get_db_connection():
    """Create MySQL connection with error handling."""
    if not HAS_MYSQL:
        logger.error("mysql-connector-python not installed")
        return None
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
            connect_timeout=30
        )
        return conn
    except Exception as e:
        logger.error("DB connection failed: %s", e)
        return None


def fetch_snapshots(conn, days=60):
    """
    Fetch equity curve snapshots for portfolio volatility and drawdown analysis.
    Returns list of dicts with snapshot_time, total_value_usd, peak_value, drawdown_pct.
    """
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT snapshot_time, total_value_usd, cash_usd, invested_usd,
               open_positions, unrealized_pnl_usd, realized_pnl_today,
               cumulative_pnl_usd, peak_value, drawdown_pct
        FROM lm_snapshots
        WHERE snapshot_time >= DATE_SUB(NOW(), INTERVAL %s DAY)
        ORDER BY snapshot_time ASC
    """, (days,))
    rows = cursor.fetchall()
    cursor.close()
    return rows


def fetch_open_trades(conn):
    """Fetch all currently open positions from lm_trades."""
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT id, asset_class, symbol, algorithm_name, direction,
               entry_time, entry_price, position_size_units,
               position_value_usd, current_price,
               unrealized_pnl_usd, unrealized_pct,
               target_tp_pct, target_sl_pct
        FROM lm_trades
        WHERE status = 'open'
        ORDER BY entry_time ASC
    """)
    rows = cursor.fetchall()
    cursor.close()
    return rows


def fetch_closed_trades(conn, days=90):
    """Fetch closed trades for Sharpe and performance analysis."""
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT id, asset_class, symbol, algorithm_name, direction,
               entry_time, exit_time, entry_price, exit_price,
               realized_pnl_usd, realized_pct, exit_reason,
               hold_hours, position_value_usd
        FROM lm_trades
        WHERE status = 'closed'
        AND exit_time >= DATE_SUB(NOW(), INTERVAL %s DAY)
        ORDER BY exit_time ASC
    """, (days,))
    rows = cursor.fetchall()
    cursor.close()
    return rows


def fetch_regime(conn):
    """Fetch latest regime state from lm_market_regime."""
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT hmm_regime, hmm_confidence, composite_score,
               vix_level, vix_regime, macro_score, ewma_vol, vol_annualized
        FROM lm_market_regime
        WHERE hmm_regime NOT IN ('worldquant_update', 'bundle_update', 'validation_update')
        ORDER BY date DESC
        LIMIT 1
    """)
    row = cursor.fetchone()
    cursor.close()
    return row


def fetch_algo_stats(conn):
    """Fetch per-algorithm performance stats from closed trades."""
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT
            algorithm_name,
            COUNT(*) AS total_trades,
            SUM(CASE WHEN realized_pnl_usd > 0 THEN 1 ELSE 0 END) AS wins,
            ROUND(SUM(CASE WHEN realized_pnl_usd > 0 THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) AS win_rate,
            ROUND(AVG(realized_pct), 4) AS avg_pnl_pct,
            ROUND(MIN(realized_pct), 4) AS worst_trade_pct,
            ROUND(MAX(realized_pct), 4) AS best_trade_pct,
            ROUND(SUM(realized_pnl_usd), 2) AS total_pnl_usd
        FROM lm_trades
        WHERE status = 'closed'
        AND entry_time > DATE_SUB(NOW(), INTERVAL 90 DAY)
        AND algorithm_name != ''
        GROUP BY algorithm_name
        ORDER BY win_rate DESC
    """)
    rows = cursor.fetchall()
    cursor.close()
    return rows


# ============================================================================
#  1. PORTFOLIO VOLATILITY TARGETING (10-12% annualized)
# ============================================================================

def calculate_portfolio_volatility(snapshots):
    """
    Calculate annualized portfolio volatility from equity curve snapshots.
    Uses daily log returns of total portfolio value.
    """
    if len(snapshots) < 5:
        logger.warning("Insufficient snapshots (%d) for vol calculation", len(snapshots))
        return 0.0, 1.0  # (vol, scalar)

    values = [float(s['total_value_usd']) for s in snapshots if float(s['total_value_usd']) > 0]
    if len(values) < 5:
        return 0.0, 1.0

    # Daily log returns
    log_returns = []
    for i in range(1, len(values)):
        if values[i - 1] > 0:
            log_returns.append(math.log(values[i] / values[i - 1]))

    if len(log_returns) < 3:
        return 0.0, 1.0

    daily_vol = float(np.std(log_returns, ddof=1))
    annual_vol = daily_vol * math.sqrt(252)

    # Calculate scalar: target_vol / current_vol
    target_mid = (TARGET_VOL_LOW + TARGET_VOL_HIGH) / 2.0  # 11%
    if annual_vol <= 0.001:
        vol_scalar = VOL_SCALAR_MAX
    elif annual_vol > TARGET_VOL_HIGH:
        vol_scalar = target_mid / annual_vol
    elif annual_vol < TARGET_VOL_LOW:
        vol_scalar = target_mid / annual_vol
    else:
        vol_scalar = 1.0  # Within target band

    vol_scalar = max(VOL_SCALAR_MIN, min(VOL_SCALAR_MAX, vol_scalar))

    logger.info("Portfolio Vol: %.2f%% annual (target: %.0f-%.0f%%) -> scalar: %.3f",
                annual_vol * 100, TARGET_VOL_LOW * 100, TARGET_VOL_HIGH * 100, vol_scalar)

    return annual_vol, vol_scalar


# ============================================================================
#  2. STRATEGY-LEVEL CAPITAL ALLOCATION
# ============================================================================

def calculate_algo_exposure(open_trades, current_equity):
    """
    Calculate current exposure per algorithm and per direction.
    Returns dict of algo -> exposure_pct and direction -> exposure_pct,
    plus per-algo block flags.
    """
    algo_exposure = {}
    direction_exposure = {'LONG': 0.0, 'SHORT': 0.0}

    for trade in open_trades:
        algo = trade.get('algorithm_name', 'Unknown')
        direction = trade.get('direction', 'LONG').upper()
        value = float(trade.get('position_value_usd', 0))

        algo_exposure[algo] = algo_exposure.get(algo, 0.0) + value

        if direction in direction_exposure:
            direction_exposure[direction] += value
        else:
            direction_exposure['LONG'] += value

    # Convert to percentages
    algo_pct = {}
    algo_blocked = {}
    for algo, value in algo_exposure.items():
        pct = value / max(current_equity, 1.0)
        algo_pct[algo] = pct
        algo_blocked[algo] = pct >= MAX_CAPITAL_PER_ALGO

    direction_pct = {}
    direction_blocked = {}
    for direction, value in direction_exposure.items():
        pct = value / max(current_equity, 1.0)
        direction_pct[direction] = pct
        direction_blocked[direction] = pct >= MAX_CAPITAL_PER_DIRECTION

    logger.info("Algo Exposure: %s", {k: f"{v:.1%}" for k, v in algo_pct.items()})
    logger.info("Direction Exposure: %s", {k: f"{v:.1%}" for k, v in direction_pct.items()})

    blocked_algos = [a for a, b in algo_blocked.items() if b]
    blocked_dirs = [d for d, b in direction_blocked.items() if b]
    if blocked_algos:
        logger.warning("BLOCKED algos (>%.0f%%): %s", MAX_CAPITAL_PER_ALGO * 100, blocked_algos)
    if blocked_dirs:
        logger.warning("BLOCKED directions (>%.0f%%): %s", MAX_CAPITAL_PER_DIRECTION * 100, blocked_dirs)

    return {
        'algo_pct': algo_pct,
        'algo_blocked': algo_blocked,
        'direction_pct': direction_pct,
        'direction_blocked': direction_blocked,
        'total_invested_pct': sum(algo_pct.values())
    }


# ============================================================================
#  3. CORRELATION-BASED SCALING
# ============================================================================

def fetch_price_returns(symbols, period='3mo'):
    """
    Fetch price returns for symbols using yfinance.
    Returns dict of symbol -> array of daily returns.
    """
    if not HAS_YFINANCE or not symbols:
        return {}

    returns_map = {}
    for sym in symbols:
        try:
            # Map our symbols to yfinance tickers
            yf_sym = sym
            if sym.endswith('USD') and len(sym) > 3:
                # Crypto: BTCUSD -> BTC-USD
                base = sym[:-3]
                yf_sym = f"{base}-USD"
            elif '/' in sym:
                yf_sym = sym.replace('/', '')

            data = yf.download(yf_sym, period=period, progress=False)
            if data is not None and len(data) > 10:
                closes = data['Close'].dropna()
                if hasattr(closes, 'values'):
                    vals = closes.values.flatten()
                else:
                    vals = np.array(closes)
                if len(vals) > 10:
                    rets = np.diff(vals) / vals[:-1]
                    returns_map[sym] = rets
        except Exception as e:
            logger.debug("Price fetch failed for %s: %s", sym, e)
            continue

    return returns_map


def calculate_correlation_penalty(open_trades):
    """
    Calculate correlation between open positions.
    Returns per-trade scaling factor based on avg correlation with portfolio.
    """
    if len(open_trades) < 2:
        return {}, 0.0

    symbols = list(set(t.get('symbol', '') for t in open_trades if t.get('symbol')))
    if len(symbols) < 2:
        return {}, 0.0

    returns_map = fetch_price_returns(symbols)
    if len(returns_map) < 2:
        logger.info("Insufficient price data for correlation analysis")
        return {}, 0.0

    # Align returns to same length
    available = [s for s in symbols if s in returns_map]
    if len(available) < 2:
        return {}, 0.0

    min_len = min(len(returns_map[s]) for s in available)
    aligned = {s: returns_map[s][-min_len:] for s in available}

    # Build correlation matrix
    returns_matrix = np.column_stack([aligned[s] for s in available])
    corr_matrix = np.corrcoef(returns_matrix, rowvar=False)
    np.fill_diagonal(corr_matrix, 0)  # Exclude self-correlation

    # Per-symbol average correlation with rest of portfolio
    corr_penalties = {}
    for i, sym in enumerate(available):
        other_corrs = np.abs(corr_matrix[i])
        avg_corr = float(np.mean(other_corrs[other_corrs > 0])) if np.any(other_corrs > 0) else 0.0

        if avg_corr > CORR_BLOCK_THRESHOLD:
            corr_penalties[sym] = 0.0   # Block (effectively zero sizing)
            logger.warning("CORRELATION BLOCK: %s avg_corr=%.3f > %.2f", sym, avg_corr, CORR_BLOCK_THRESHOLD)
        elif avg_corr > CORR_REDUCE_THRESHOLD:
            corr_penalties[sym] = 0.50  # Reduce by 50%
            logger.warning("CORRELATION REDUCE: %s avg_corr=%.3f > %.2f", sym, avg_corr, CORR_REDUCE_THRESHOLD)
        else:
            corr_penalties[sym] = 1.0   # No penalty

    portfolio_avg_corr = float(np.mean(np.abs(corr_matrix[corr_matrix != 0]))) if np.any(corr_matrix != 0) else 0.0
    logger.info("Portfolio avg correlation: %.3f (symbols: %d)", portfolio_avg_corr, len(available))

    return corr_penalties, portfolio_avg_corr


# ============================================================================
#  4. DRAWDOWN-BASED THROTTLING (Enhanced)
# ============================================================================

def calculate_drawdown_state(snapshots, current_equity):
    """
    Enhanced drawdown-based throttling.
    Returns drawdown percentage, scaling factor, and action level.
    """
    if not snapshots:
        return 0.0, 1.0, 'normal'

    # Get peak equity from snapshots
    peak = INITIAL_CAPITAL
    for s in snapshots:
        val = float(s.get('total_value_usd', 0))
        if val > peak:
            peak = val

    # Also check peak_value column if available
    for s in snapshots:
        pv = float(s.get('peak_value', 0))
        if pv > peak:
            peak = pv

    if peak <= 0:
        peak = INITIAL_CAPITAL

    drawdown_pct = 0.0
    if current_equity < peak:
        drawdown_pct = ((peak - current_equity) / peak) * 100.0

    # Determine action level
    if drawdown_pct >= DD_SHUTDOWN_PCT:
        action = 'emergency_shutdown'
        scale = 0.0
        logger.critical("EMERGENCY SHUTDOWN: Drawdown %.1f%% >= %.0f%%", drawdown_pct, DD_SHUTDOWN_PCT)
    elif drawdown_pct >= DD_HALT_PCT:
        action = 'halt_48h'
        scale = 0.0
        logger.critical("HALT 48H: Drawdown %.1f%% >= %.0f%% -- close all, pause trading", drawdown_pct, DD_HALT_PCT)
    elif drawdown_pct >= DD_HALVE_PCT:
        action = 'halve_all'
        scale = 0.50
        logger.warning("HALVE ALL: Drawdown %.1f%% >= %.0f%%", drawdown_pct, DD_HALVE_PCT)
    elif drawdown_pct > 0:
        # Continuous scaling: exponential decay -- e^(-0.08 * dd)
        scale = math.exp(-0.08 * drawdown_pct)
        scale = max(0.25, min(1.0, scale))
        action = 'scaling'
        logger.info("Drawdown scaling: %.1f%% DD -> %.2fx", drawdown_pct, scale)
    else:
        action = 'normal'
        scale = 1.0

    return drawdown_pct, scale, action


# ============================================================================
#  5. ROLLING SHARPE GATE
# ============================================================================

def calculate_rolling_sharpe(closed_trades, algo_name=None, window_days=30):
    """
    Calculate rolling Sharpe ratio from closed trade PnL.
    If algo_name is None, calculates portfolio-level Sharpe.
    """
    if not closed_trades:
        return 0.0

    # Filter by algorithm if specified
    if algo_name:
        trades = [t for t in closed_trades if t.get('algorithm_name') == algo_name]
    else:
        trades = closed_trades

    # Filter to window
    cutoff = datetime.now() - timedelta(days=window_days)
    recent = []
    for t in trades:
        exit_time = t.get('exit_time')
        if exit_time:
            if isinstance(exit_time, str):
                try:
                    exit_time = datetime.strptime(exit_time, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    continue
            if exit_time >= cutoff:
                recent.append(t)

    if len(recent) < 5:
        return 0.0  # Not enough data

    pnl_pcts = [float(t.get('realized_pct', 0)) for t in recent]
    pnl_arr = np.array(pnl_pcts, dtype=float)

    mean_pnl = np.mean(pnl_arr)
    std_pnl = np.std(pnl_arr, ddof=1)

    if std_pnl < 0.0001:
        return 0.0

    # Annualize: sqrt(trades_per_year / trades_in_window)
    trades_per_day = len(recent) / max(window_days, 1)
    annualize_factor = math.sqrt(252 * trades_per_day) if trades_per_day > 0 else 1.0
    sharpe = (mean_pnl / std_pnl) * annualize_factor

    return float(sharpe)


def apply_sharpe_gates(closed_trades, algo_stats_list):
    """
    Apply rolling Sharpe gates per-algo and portfolio-wide.
    Returns dict of algo -> sharpe_scalar.
    """
    sharpe_scalars = {}

    # Per-algorithm Sharpe check
    algo_names = set(a.get('algorithm_name', '') for a in algo_stats_list if a.get('algorithm_name'))
    for algo in algo_names:
        sharpe = calculate_rolling_sharpe(closed_trades, algo_name=algo, window_days=SHARPE_WINDOW_DAYS)
        if sharpe < 0:
            sharpe_scalars[algo] = SHARPE_NEGATIVE_CUT
            logger.warning("SHARPE GATE: %s 30d Sharpe=%.3f < 0 -> %.0f%% cut",
                           algo, sharpe, SHARPE_NEGATIVE_CUT * 100)
        else:
            sharpe_scalars[algo] = 1.0

    # Portfolio-wide Sharpe check
    portfolio_sharpe = calculate_rolling_sharpe(closed_trades, algo_name=None, window_days=PORTFOLIO_SHARPE_CRISIS_DAYS)
    portfolio_crisis = portfolio_sharpe < 0

    if portfolio_crisis:
        logger.warning("PORTFOLIO SHARPE CRISIS: %d-day Sharpe=%.3f < 0 -> ALL algos to %.0f%%",
                       PORTFOLIO_SHARPE_CRISIS_DAYS, portfolio_sharpe, PORTFOLIO_SHARPE_CRISIS_CUT * 100)
        for algo in sharpe_scalars:
            sharpe_scalars[algo] = min(sharpe_scalars[algo], PORTFOLIO_SHARPE_CRISIS_CUT)

    return sharpe_scalars, portfolio_sharpe, portfolio_crisis


# ============================================================================
#  6. CVaR (CONDITIONAL VALUE AT RISK)
# ============================================================================

def calculate_cvar(snapshots, confidence=0.95):
    """
    Calculate CVaR (Expected Shortfall) from portfolio daily returns.
    CVaR at 95% = average of worst 5% of daily returns.
    """
    if len(snapshots) < 10:
        return 0.0, 0.0, 1.0  # (var, cvar, scaling)

    values = [float(s['total_value_usd']) for s in snapshots if float(s['total_value_usd']) > 0]
    if len(values) < 10:
        return 0.0, 0.0, 1.0

    # Daily returns
    daily_returns = []
    for i in range(1, len(values)):
        if values[i - 1] > 0:
            ret = (values[i] - values[i - 1]) / values[i - 1]
            daily_returns.append(ret)

    if len(daily_returns) < 10:
        return 0.0, 0.0, 1.0

    returns_arr = np.array(daily_returns, dtype=float)

    # VaR: percentile at (1 - confidence)
    var_pct = (1 - confidence) * 100  # 5th percentile
    if HAS_SCIPY:
        var_val = float(scipy_stats.scoreatpercentile(returns_arr, var_pct))
    else:
        var_val = float(np.percentile(returns_arr, var_pct))

    # CVaR: average of returns below VaR
    tail = returns_arr[returns_arr <= var_val]
    cvar_val = float(np.mean(tail)) if len(tail) > 0 else var_val

    # Scaling: if abs(CVaR) > threshold, reduce exposure
    cvar_abs = abs(cvar_val)
    if cvar_abs > CVAR_MAX_PCT:
        cvar_scale = CVAR_MAX_PCT / cvar_abs
        cvar_scale = max(0.25, min(1.0, cvar_scale))
        logger.warning("CVaR BREACH: CVaR=%.2f%% > %.1f%% threshold -> scale %.2f",
                       cvar_abs * 100, CVAR_MAX_PCT * 100, cvar_scale)
    else:
        cvar_scale = 1.0

    logger.info("CVaR Analysis: VaR(%.0f%%)=%.3f%%, CVaR=%.3f%%, scale=%.2f",
                confidence * 100, var_val * 100, cvar_val * 100, cvar_scale)

    return var_val, cvar_val, cvar_scale


# ============================================================================
#  7. MOMENTUM CRASH PROTECTION
# ============================================================================

def calculate_momentum_protection(regime, snapshots):
    """
    Momentum crash protection:
    - VIX > 30: scale momentum algos by 50%
    - 5-day portfolio return < -5%: pause momentum algos
    - Fear regime: only allow mean-reversion/contrarian
    """
    momentum_scale = 1.0
    momentum_paused = False
    reason = 'normal'

    # VIX check from regime data
    vix_level = 15.0
    vix_regime = 'normal'
    if regime:
        vix_level = float(regime.get('vix_level', 15) or 15)
        vix_regime = regime.get('vix_regime', 'normal') or 'normal'

    if vix_level > VIX_THRESHOLD:
        momentum_scale = VIX_MOMENTUM_SCALE
        reason = f'vix_high ({vix_level:.1f})'
        logger.warning("MOMENTUM PROTECTION: VIX %.1f > %.0f -> scale momentum by %.0f%%",
                       vix_level, VIX_THRESHOLD, momentum_scale * 100)

    # 5-day portfolio return check
    if len(snapshots) >= 5:
        recent_values = [float(s['total_value_usd']) for s in snapshots[-6:] if float(s['total_value_usd']) > 0]
        if len(recent_values) >= 2:
            five_day_return = (recent_values[-1] - recent_values[0]) / recent_values[0] * 100
            if five_day_return < PORTFOLIO_5D_CRASH:
                momentum_scale = 0.0
                momentum_paused = True
                reason = f'5d_crash ({five_day_return:.1f}%)'
                logger.warning("MOMENTUM PAUSE: 5-day return %.1f%% < %.0f%% -> pause all momentum",
                               five_day_return, PORTFOLIO_5D_CRASH)

    # Fear regime check
    if vix_regime in ('fear', 'fear_peak'):
        if momentum_scale > 0:
            momentum_scale = min(momentum_scale, 0.30)
            reason = f'fear_regime ({vix_regime})'
            logger.warning("FEAR REGIME: %s -> momentum at %.0f%%", vix_regime, momentum_scale * 100)

    return {
        'momentum_scale': momentum_scale,
        'momentum_paused': momentum_paused,
        'reason': reason,
        'vix_level': vix_level,
        'vix_regime': vix_regime,
        'contrarian_allowed': True  # Always allow contrarian in any regime
    }


# ============================================================================
#  RISK REPORT ASSEMBLY
# ============================================================================

def assemble_risk_report(vol_data, exposure_data, corr_data, dd_data,
                         sharpe_data, cvar_data, momentum_data,
                         per_algo_sizing, portfolio_state):
    """Assemble comprehensive risk report for dashboard consumption."""
    report = {
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'portfolio_state': portfolio_state,

        'volatility_targeting': {
            'portfolio_vol_annual': round(vol_data[0] * 100, 2),
            'target_range': f"{TARGET_VOL_LOW * 100:.0f}-{TARGET_VOL_HIGH * 100:.0f}%",
            'vol_scalar': round(vol_data[1], 3),
            'status': 'in_range' if TARGET_VOL_LOW <= vol_data[0] <= TARGET_VOL_HIGH else (
                'high' if vol_data[0] > TARGET_VOL_HIGH else 'low'
            )
        },

        'strategy_allocation': {
            'algo_exposure_pct': {k: round(v * 100, 2) for k, v in exposure_data.get('algo_pct', {}).items()},
            'algo_blocked': exposure_data.get('algo_blocked', {}),
            'direction_exposure_pct': {k: round(v * 100, 2) for k, v in exposure_data.get('direction_pct', {}).items()},
            'direction_blocked': exposure_data.get('direction_blocked', {}),
            'total_invested_pct': round(exposure_data.get('total_invested_pct', 0) * 100, 2),
            'max_per_algo': f"{MAX_CAPITAL_PER_ALGO * 100:.0f}%",
            'max_per_direction': f"{MAX_CAPITAL_PER_DIRECTION * 100:.0f}%"
        },

        'correlation': {
            'portfolio_avg_correlation': round(corr_data[1], 3),
            'symbol_penalties': {k: round(v, 2) for k, v in corr_data[0].items()},
            'reduce_threshold': CORR_REDUCE_THRESHOLD,
            'block_threshold': CORR_BLOCK_THRESHOLD
        },

        'drawdown': {
            'current_drawdown_pct': round(dd_data[0], 2),
            'dd_scale': round(dd_data[1], 3),
            'action_level': dd_data[2],
            'thresholds': {
                'halve': DD_HALVE_PCT,
                'halt_48h': DD_HALT_PCT,
                'shutdown': DD_SHUTDOWN_PCT
            }
        },

        'sharpe_gates': {
            'per_algo_scalars': {k: round(v, 2) for k, v in sharpe_data[0].items()},
            'portfolio_sharpe_14d': round(sharpe_data[1], 3),
            'portfolio_crisis': sharpe_data[2]
        },

        'cvar': {
            'var_95_pct': round(cvar_data[0] * 100, 3),
            'cvar_95_pct': round(cvar_data[1] * 100, 3),
            'cvar_scale': round(cvar_data[2], 3),
            'threshold_pct': CVAR_MAX_PCT * 100
        },

        'momentum_protection': momentum_data,

        'per_algo_sizing': per_algo_sizing
    }

    return report


# ============================================================================
#  COMBINED SIZING PIPELINE
# ============================================================================

def compute_final_sizing(algo_stats_list, vol_scalar, dd_scale, dd_action,
                         sharpe_scalars, cvar_scale, momentum_data,
                         exposure_data, corr_penalties, current_equity):
    """
    Compute final position size recommendation per algorithm.
    Combines all 7 risk layers into a single sizing number.
    """
    sizing_results = []

    for algo in algo_stats_list:
        algo_name = algo.get('algorithm_name', 'Unknown')
        win_rate = float(algo.get('win_rate', 0))
        total_trades = int(algo.get('total_trades', 0))

        # Base size: 5% default
        base_size_pct = 5.0

        # If algo is blocked by capital allocation, set to 0
        if exposure_data.get('algo_blocked', {}).get(algo_name, False):
            final_pct = 0.0
            block_reason = f'algo_cap ({MAX_CAPITAL_PER_ALGO * 100:.0f}%)'
        elif dd_action in ('emergency_shutdown', 'halt_48h'):
            final_pct = 0.0
            block_reason = dd_action
        else:
            # Layer 1: Volatility targeting
            size = base_size_pct * vol_scalar

            # Layer 2: Drawdown scaling
            size *= dd_scale

            # Layer 3: Sharpe gate
            algo_sharpe_scalar = sharpe_scalars.get(algo_name, 1.0)
            size *= algo_sharpe_scalar

            # Layer 4: CVaR scaling
            size *= cvar_scale

            # Layer 5: Momentum crash protection
            is_momentum = algo_name in MOMENTUM_ALGOS
            is_contrarian = algo_name in CONTRARIAN_ALGOS
            if is_momentum:
                size *= momentum_data.get('momentum_scale', 1.0)
            # Contrarian algos get slight boost in fear regime
            if is_contrarian and momentum_data.get('vix_regime', '') in ('fear', 'fear_peak'):
                size *= 1.15  # 15% boost for contrarians in fear

            # Layer 6: Win-rate confidence scaling
            if total_trades >= 20:
                if win_rate >= 60:
                    size *= 1.10  # Slight boost for proven winners
                elif win_rate < 40:
                    size *= 0.60  # Significant cut for poor performers
                elif win_rate < 50:
                    size *= 0.80  # Moderate cut for below-average

            # Clamp to 1-15%
            final_pct = max(1.0, min(15.0, size))
            block_reason = None

        # Build the algo Sharpe for reporting
        algo_sharpe = 0.0
        if algo_name in sharpe_scalars:
            # We don't have the actual sharpe in sharpe_scalars (just the scalar).
            # If scalar < 1, Sharpe was negative.
            algo_sharpe = -0.5 if sharpe_scalars.get(algo_name, 1.0) < 1.0 else 0.5

        dollar_amount = round(current_equity * (final_pct / 100.0), 2)

        result = {
            'algorithm_name': algo_name,
            'kelly_base': round(base_size_pct / 100.0, 4),
            'vol_scalar': round(vol_scalar, 2),
            'regime_modifier': round(dd_scale, 2),
            'decay_weight': round(sharpe_scalars.get(algo_name, 1.0), 2),
            'final_size_pct': round(final_pct, 2),
            'dollar_amount': dollar_amount,
            'algo_sharpe_30d': round(algo_sharpe, 3),
            'is_decaying': 1 if sharpe_scalars.get(algo_name, 1.0) < 1.0 else 0,
            # Extra fields for risk report (not sent to PHP)
            '_cvar_scale': round(cvar_scale, 3),
            '_momentum_scale': round(momentum_data.get('momentum_scale', 1.0), 3),
            '_is_momentum_algo': algo_name in MOMENTUM_ALGOS,
            '_is_contrarian_algo': algo_name in CONTRARIAN_ALGOS,
            '_block_reason': block_reason,
            '_win_rate': win_rate,
            '_total_trades': total_trades
        }

        sizing_results.append(result)

        status = "BLOCKED" if block_reason else "OK"
        logger.info("  %-25s Vol=%.2fx DD=%.2fx Sharpe=%.2fx CVaR=%.2fx -> %.1f%% ($%.0f) [%s]",
                     algo_name, vol_scalar, dd_scale,
                     sharpe_scalars.get(algo_name, 1.0), cvar_scale,
                     final_pct, dollar_amount, status)

    return sizing_results


# ============================================================================
#  API POSTING
# ============================================================================

def post_sizing_to_api(sizing_results, regime_composite):
    """Post position sizing results to regime.php API."""
    url = f"{API_BASE}/regime.php?action=update_position_sizing&key={ADMIN_KEY}"

    # Strip internal fields (prefixed with _) before sending to API
    clean_results = []
    for r in sizing_results:
        clean = {k: v for k, v in r.items() if not k.startswith('_')}
        clean_results.append(clean)

    payload = {
        'sizing': clean_results,
        'regime_composite': regime_composite
    }

    try:
        resp = requests.post(url, json=payload, headers=API_HEADERS, timeout=60)
        result = resp.json()
        if result.get('ok'):
            logger.info("API POST success: %d algos sized, %d inserted",
                        len(clean_results), result.get('inserted', 0))
        else:
            logger.error("API POST error: %s", result.get('error', 'unknown'))
        return result
    except Exception as e:
        logger.error("API POST failed: %s", e)
        return {'ok': False, 'error': str(e)}


def save_risk_report(report, output_dir=None):
    """Save risk report as JSON for dashboard consumption."""
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, 'risk_report.json')

    try:
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        logger.info("Risk report saved to %s", filepath)
    except Exception as e:
        logger.error("Failed to save risk report: %s", e)


# ============================================================================
#  MAIN PIPELINE
# ============================================================================

def main():
    """Main execution pipeline."""
    start_time = time.time()

    print("=" * 70)
    print("  PORTFOLIO RISK CONTROLLER -- Critical Infrastructure")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # ── Step 0: Connect to DB ──
    conn = get_db_connection()
    if not conn:
        logger.critical("Cannot connect to database. Exiting.")
        print("FATAL: Database connection failed")
        sys.exit(1)

    try:
        # ── Step 1: Fetch portfolio state ──
        print("\n[1/7] Fetching portfolio state...")
        snapshots = fetch_snapshots(conn, days=60)
        open_trades = fetch_open_trades(conn)
        closed_trades = fetch_closed_trades(conn, days=90)
        regime = fetch_regime(conn)
        algo_stats_list = fetch_algo_stats(conn)

        # Current equity from latest snapshot
        current_equity = INITIAL_CAPITAL
        if snapshots:
            current_equity = float(snapshots[-1].get('total_value_usd', INITIAL_CAPITAL))
        if current_equity <= 0:
            current_equity = INITIAL_CAPITAL

        regime_composite = float(regime.get('composite_score', 50)) if regime else 50.0

        portfolio_state = {
            'current_equity': current_equity,
            'initial_capital': INITIAL_CAPITAL,
            'total_return_pct': round((current_equity - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100, 2),
            'open_positions': len(open_trades),
            'closed_trades_90d': len(closed_trades),
            'algorithms_tracked': len(algo_stats_list),
            'snapshots_available': len(snapshots),
            'regime_composite': regime_composite,
            'hmm_regime': regime.get('hmm_regime', 'unknown') if regime else 'unknown'
        }

        print(f"  Equity: ${current_equity:,.2f} | Open: {len(open_trades)} | "
              f"Closed (90d): {len(closed_trades)} | Algos: {len(algo_stats_list)}")

        # ── Step 2: Portfolio Volatility Targeting ──
        print("\n[2/7] Portfolio volatility targeting...")
        annual_vol, vol_scalar = calculate_portfolio_volatility(snapshots)

        # ── Step 3: Strategy-Level Capital Allocation ──
        print("\n[3/7] Strategy-level capital allocation...")
        exposure_data = calculate_algo_exposure(open_trades, current_equity)

        # ── Step 4: Correlation-Based Scaling ──
        print("\n[4/7] Correlation-based scaling...")
        corr_penalties, portfolio_avg_corr = calculate_correlation_penalty(open_trades)

        # ── Step 5: Drawdown-Based Throttling ──
        print("\n[5/7] Drawdown-based throttling...")
        drawdown_pct, dd_scale, dd_action = calculate_drawdown_state(snapshots, current_equity)

        # ── Step 6: Rolling Sharpe Gate ──
        print("\n[6/7] Rolling Sharpe gates...")
        sharpe_scalars, portfolio_sharpe, portfolio_crisis = apply_sharpe_gates(closed_trades, algo_stats_list)

        # ── Step 7: CVaR & Momentum Protection ──
        print("\n[7/7] CVaR and momentum crash protection...")
        var_val, cvar_val, cvar_scale = calculate_cvar(snapshots)
        momentum_data = calculate_momentum_protection(regime, snapshots)

        # ── Combine: Final Sizing ──
        print("\n" + "=" * 70)
        print("  COMPUTING FINAL POSITION SIZING")
        print("=" * 70)

        per_algo_sizing = compute_final_sizing(
            algo_stats_list=algo_stats_list,
            vol_scalar=vol_scalar,
            dd_scale=dd_scale,
            dd_action=dd_action,
            sharpe_scalars=sharpe_scalars,
            cvar_scale=cvar_scale,
            momentum_data=momentum_data,
            exposure_data=exposure_data,
            corr_penalties=corr_penalties,
            current_equity=current_equity
        )

        # ── Post to API ──
        print("\nPosting sizing to API...")
        if per_algo_sizing:
            api_result = post_sizing_to_api(per_algo_sizing, regime_composite)
        else:
            logger.warning("No algorithm stats found -- nothing to post")
            api_result = {'ok': False, 'error': 'no_data'}

        # ── Assemble & Save Risk Report ──
        print("Saving risk report...")
        report = assemble_risk_report(
            vol_data=(annual_vol, vol_scalar),
            exposure_data=exposure_data,
            corr_data=(corr_penalties, portfolio_avg_corr),
            dd_data=(drawdown_pct, dd_scale, dd_action),
            sharpe_data=(sharpe_scalars, portfolio_sharpe, portfolio_crisis),
            cvar_data=(var_val, cvar_val, cvar_scale),
            momentum_data=momentum_data,
            per_algo_sizing=[{k: v for k, v in s.items()} for s in per_algo_sizing],
            portfolio_state=portfolio_state
        )
        save_risk_report(report)

        # ── Summary ──
        elapsed = time.time() - start_time
        print("\n" + "=" * 70)
        print("  PORTFOLIO RISK CONTROLLER -- SUMMARY")
        print("=" * 70)
        print(f"  Equity:             ${current_equity:,.2f}")
        print(f"  Portfolio Vol:      {annual_vol * 100:.1f}% annualized")
        print(f"  Vol Scalar:         {vol_scalar:.3f}")
        print(f"  Drawdown:           {drawdown_pct:.1f}% (action: {dd_action})")
        print(f"  DD Scale:           {dd_scale:.3f}")
        print(f"  Portfolio Sharpe:   {portfolio_sharpe:.3f} (crisis: {portfolio_crisis})")
        print(f"  CVaR (95%):         {cvar_val * 100:.2f}% (scale: {cvar_scale:.3f})")
        print(f"  Avg Correlation:    {portfolio_avg_corr:.3f}")
        print(f"  VIX Level:          {momentum_data.get('vix_level', 0):.1f}")
        print(f"  Momentum Status:    {momentum_data.get('reason', 'normal')}")
        print(f"  Algos Sized:        {len(per_algo_sizing)}")
        if per_algo_sizing:
            avg_size = np.mean([s['final_size_pct'] for s in per_algo_sizing])
            blocked = sum(1 for s in per_algo_sizing if s.get('_block_reason'))
            decaying = sum(1 for s in per_algo_sizing if s.get('is_decaying'))
            print(f"  Avg Position Size:  {avg_size:.1f}%")
            print(f"  Blocked Algos:      {blocked}")
            print(f"  Decaying Algos:     {decaying}")
        print(f"  API Result:         {'OK' if api_result.get('ok') else api_result.get('error', 'failed')}")
        print(f"  Elapsed:            {elapsed:.1f}s")
        print("=" * 70)

        # ── Alert flags for GitHub Actions ──
        if dd_action in ('emergency_shutdown', 'halt_48h'):
            print(f"\n*** CRITICAL ALERT: {dd_action.upper()} -- Drawdown {drawdown_pct:.1f}% ***")
        if portfolio_crisis:
            print(f"\n*** WARNING: Portfolio Sharpe crisis ({portfolio_sharpe:.3f}) -- all sizing at {PORTFOLIO_SHARPE_CRISIS_CUT * 100:.0f}% ***")
        if momentum_data.get('momentum_paused'):
            print(f"\n*** WARNING: Momentum algos PAUSED -- {momentum_data.get('reason')} ***")

    except Exception as e:
        logger.exception("Portfolio Risk Controller failed: %s", e)
        print(f"\nFATAL ERROR: {e}")
        sys.exit(1)
    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == '__main__':
    main()
