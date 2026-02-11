#!/usr/bin/env python3
"""
Position Sizer — Half-Kelly + EWMA Volatility Scaling + Regime Modulation.

Implements the optimal position sizing layer from World-Class Architecture:
  1. Half-Kelly: Mathematically optimal growth rate with 50% buffer
  2. EWMA Vol Scaling: Target volatility approach (more responsive than GARCH)
  3. Regime Modulation: Reduce size in bear/fear, increase in bull/normal
  4. Correlation Budgeting: Factor exposure limits
  5. Slippage Modeling: Almgren-Chriss inspired impact estimates

Posts sizing recommendations to PHP API for live-monitor consumption.

Requires: pip install numpy pandas requests
"""
import sys
import os
import json
import logging
import numpy as np
import warnings

warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import post_to_api, call_api
from config import API_BASE, ADMIN_KEY, TRACKED_TICKERS

logger = logging.getLogger('position_sizer')


# ---------------------------------------------------------------------------
# Half-Kelly Position Sizing
# ---------------------------------------------------------------------------

def half_kelly(win_rate, avg_win, avg_loss, max_size=0.15):
    """
    Calculate Half-Kelly position size.

    Full Kelly = (p * b - q) / b
    where p = win rate, q = 1-p, b = win/loss ratio

    Half-Kelly halves the bet for practical robustness:
    - 50% of the expected log-optimal growth rate
    - 50% less drawdown for only ~25% less return
    - Accounts for estimation error in win_rate/payoff

    Returns fraction of capital to allocate (0 to max_size).
    """
    if win_rate <= 0 or avg_win <= 0 or avg_loss <= 0:
        return 0.0

    p = min(max(win_rate, 0.01), 0.99)
    q = 1 - p
    b = avg_win / avg_loss  # Win/loss ratio

    # Full Kelly
    kelly = (p * b - q) / b

    # Half-Kelly with bounds
    half = kelly * 0.5
    return max(0.0, min(half, max_size))


# ---------------------------------------------------------------------------
# EWMA Volatility Forecast
# ---------------------------------------------------------------------------

def ewma_vol(returns, decay=0.94):
    """
    Exponentially Weighted Moving Average volatility.

    Better than GARCH out-of-sample because:
    - No parameter estimation instability
    - Single decay parameter (0.94 = RiskMetrics standard)
    - Responsive to recent regime changes
    - Zero extra compute

    Returns daily volatility (not annualized).
    """
    returns = np.array(returns, dtype=float)
    returns = returns[~np.isnan(returns)]

    if len(returns) < 5:
        return 0.02  # Default 2% daily

    variance = returns[0] ** 2
    for r in returns[1:]:
        variance = decay * variance + (1 - decay) * (r ** 2)

    return float(np.sqrt(variance))


# ---------------------------------------------------------------------------
# Volatility Target Scaling
# ---------------------------------------------------------------------------

def vol_target_scalar(current_vol, target_vol=0.15, annualize=True):
    """
    Scale position size to target a specific portfolio volatility.

    If current vol >> target vol → shrink position.
    If current vol << target vol → can grow position.

    target_vol: annualized target (0.15 = 15% annual vol).
    """
    if current_vol <= 0:
        return 1.0

    if annualize:
        current_annual = current_vol * np.sqrt(252)
    else:
        current_annual = current_vol

    scalar = target_vol / max(current_annual, 0.01)
    return max(0.1, min(3.0, scalar))  # Clamp 10%-300%


# ---------------------------------------------------------------------------
# Regime Position Modifier
# ---------------------------------------------------------------------------

def regime_modifier(composite_score, hmm_regime='sideways', vix_regime='normal'):
    """
    Modulate position size based on market regime.

    Bear + high VIX → reduce 40-60%
    Bull + normal VIX → full size or slight boost
    Sideways → moderate reduction
    Fear peak → slight boost (contrarian)
    """
    # Base: composite_score / 100 (0-1 range, centered at 0.5)
    base = composite_score / 100.0

    # HMM adjustment
    hmm_adj = {'bull': 1.1, 'sideways': 0.9, 'bear': 0.6}
    adj = hmm_adj.get(hmm_regime, 0.9)

    # VIX adjustment
    vix_adj = {
        'fear': 0.7,
        'fear_peak': 0.85,     # Contrarian: slightly less cut at peak
        'elevated': 0.85,
        'normal': 1.0,
        'complacent': 0.95     # Slight caution (spike risk)
    }
    v_adj = vix_adj.get(vix_regime, 1.0)

    modifier = base * adj * v_adj

    # Normalize to 0.3-1.2 range (never zero out, never >20% boost)
    return max(0.3, min(1.2, modifier * 2))  # *2 because base centered at 0.5


# ---------------------------------------------------------------------------
# Slippage Model (Almgren-Chriss inspired)
# ---------------------------------------------------------------------------

def estimate_slippage(position_value, avg_daily_volume, daily_vol, spread_bps=5):
    """
    Estimate execution slippage based on market impact.

    Almgren-Chriss framework simplified:
    - Temporary impact: spread + linear participation cost
    - Permanent impact: proportional to sqrt(participation) * volatility

    Returns slippage as decimal (0.001 = 10 bps).
    """
    if avg_daily_volume <= 0:
        return 0.005  # Default 50 bps for unknown

    participation = position_value / max(avg_daily_volume, 1)

    # Temporary impact (half-spread + linear participation)
    temp_impact_bps = spread_bps / 2 + 0.1 * participation * 10000

    # Permanent impact (vol * sqrt(participation))
    perm_impact_bps = 0.2 * daily_vol * np.sqrt(participation) * 10000

    total_bps = temp_impact_bps + perm_impact_bps
    return min(total_bps / 10000, 0.02)  # Cap at 200 bps


# ---------------------------------------------------------------------------
# Correlation Budget Check
# ---------------------------------------------------------------------------

def check_factor_exposure(position_returns, weights, max_eigen_share=0.30):
    """
    Ensure no single factor dominates portfolio variance.
    Uses PCA to identify if top eigenvector has >max_eigen_share of variance.

    position_returns: DataFrame of returns for current positions.
    weights: array of position weights (same order).
    """
    if position_returns is None or len(position_returns.columns) < 2:
        return True, 0.0  # Can't check with < 2 positions

    try:
        corr = position_returns.corr().values
        eigenvals = np.linalg.eigvalsh(corr)
        eigenvals = np.sort(eigenvals)[::-1]

        total_var = eigenvals.sum()
        top_share = eigenvals[0] / total_var if total_var > 0 else 0

        passes = top_share < max_eigen_share
        return passes, float(top_share)
    except Exception as e:
        logger.warning("Factor exposure check failed: %s", e)
        return True, 0.0  # Fail open


# ---------------------------------------------------------------------------
# Alpha Decay Detection
# ---------------------------------------------------------------------------

def calculate_alpha_decay(algo_trades, window=30):
    """
    Rolling Sharpe ratio for an algorithm's recent trades.
    If Sharpe < 0.5 over last 30 trades → flag for weight reduction.

    Returns: current_sharpe, is_decaying, recommended_weight
    """
    if not algo_trades or len(algo_trades) < 10:
        return 0.0, False, 1.0

    pnl_pcts = [t.get('realized_pct', 0) for t in algo_trades[-window:]]
    pnl_arr = np.array(pnl_pcts, dtype=float)

    mean_pnl = np.mean(pnl_arr)
    std_pnl = np.std(pnl_arr, ddof=1)

    if std_pnl < 0.0001:
        sharpe = 0.0
    else:
        sharpe = mean_pnl / std_pnl * np.sqrt(252 / max(1, window))

    # Decay detection
    is_decaying = sharpe < 0.5

    # Recommended weight: exponential decay of confidence
    if sharpe >= 1.0:
        weight = 1.0
    elif sharpe >= 0.5:
        weight = 0.5 + 0.5 * (sharpe - 0.5) / 0.5
    elif sharpe >= 0:
        weight = 0.2 + 0.3 * sharpe / 0.5
    else:
        weight = max(0.1, 0.2 + 0.2 * sharpe)  # Negative Sharpe → near-zero

    return float(sharpe), is_decaying, round(weight, 2)


# ---------------------------------------------------------------------------
# Full Position Sizing Pipeline
# ---------------------------------------------------------------------------

def calculate_position_size(signal, algo_stats, regime_data, capital=10000):
    """
    Full position sizing for a single signal.

    signal: {ticker, type, strength, bundle}
    algo_stats: {win_rate, avg_profit, avg_loss, recent_trades}
    regime_data: {market: {composite_score, hmm_regime, ...}, macro: {vix_regime}}

    Returns sizing recommendation.
    """
    max_position = 0.15  # 15% max per position

    # Step 1: Half-Kelly base size
    win_rate = algo_stats.get('win_rate', 0.50)
    avg_win = algo_stats.get('avg_profit', 0.03)
    avg_loss = abs(algo_stats.get('avg_loss', 0.02))

    kelly_size = half_kelly(win_rate, avg_win, avg_loss, max_position)

    # Step 2: EWMA vol scaling
    recent_returns = algo_stats.get('recent_returns', [])
    if recent_returns:
        current_vol = ewma_vol(recent_returns)
    else:
        current_vol = 0.02  # Default 2% daily

    vol_scalar = vol_target_scalar(current_vol, target_vol=0.15)

    # Step 3: Regime modifier
    market = regime_data.get('market', {})
    macro = regime_data.get('macro', {})

    reg_mod = regime_modifier(
        market.get('composite_score', 50),
        market.get('hmm_regime', 'sideways'),
        macro.get('vix_regime', 'normal')
    )

    # Step 4: Alpha decay check
    recent_trades = algo_stats.get('recent_trades', [])
    algo_sharpe, is_decaying, decay_weight = calculate_alpha_decay(recent_trades)

    # Step 5: Signal strength modifier
    strength = signal.get('strength', 50) / 100.0
    strength_mod = 0.5 + 0.5 * strength  # Range 0.5-1.0

    # Step 6: Combine
    raw_size = kelly_size * vol_scalar * reg_mod * decay_weight * strength_mod
    final_size = max(0.01, min(raw_size, max_position))  # 1% min, 15% max
    dollar_amount = capital * final_size

    return {
        'ticker': signal.get('ticker', '?'),
        'bundle': signal.get('bundle', '?'),
        'kelly_base': round(kelly_size, 4),
        'vol_scalar': round(vol_scalar, 2),
        'regime_modifier': round(reg_mod, 2),
        'decay_weight': round(decay_weight, 2),
        'strength_modifier': round(strength_mod, 2),
        'algo_sharpe_30d': round(algo_sharpe, 3),
        'is_decaying': is_decaying,
        'raw_size': round(raw_size, 4),
        'final_size_pct': round(final_size * 100, 2),
        'dollar_amount': round(dollar_amount, 2),
        'current_vol_daily': round(current_vol, 6),
        'current_vol_annual': round(current_vol * np.sqrt(252), 4)
    }


# ---------------------------------------------------------------------------
# Batch Sizing for All Algos
# ---------------------------------------------------------------------------

def run_position_sizing():
    """
    Fetch algo stats and regime data, compute position sizes for all algos.
    Post results to PHP API.
    """
    logger.info("=" * 60)
    logger.info("POSITION SIZER — Starting")
    logger.info("=" * 60)

    # Fetch current regime
    regime_result = call_api('get_regime')
    if regime_result.get('ok'):
        regime_data = regime_result.get('regime', {})
    else:
        logger.warning("Could not fetch regime, using defaults")
        regime_data = {
            'market': {'composite_score': 50, 'hmm_regime': 'sideways'},
            'macro': {'vix_regime': 'normal'}
        }

    # Fetch algo performance stats
    algo_result = call_api('algo_stats')
    algo_stats_list = algo_result.get('algorithms', []) if algo_result.get('ok') else []

    sizing_results = []

    for algo in algo_stats_list:
        algo_name = algo.get('algorithm_name', 'Unknown')

        stats = {
            'win_rate': algo.get('win_rate', 50) / 100.0,
            'avg_profit': algo.get('avg_pnl_pct', 3) / 100.0,
            'avg_loss': abs(algo.get('worst_trade_pct', -2)) / 100.0,
            'recent_trades': algo.get('recent_trades', []),
            'recent_returns': []
        }

        signal = {
            'ticker': 'PORTFOLIO',
            'type': 'BUY',
            'strength': algo.get('avg_strength', 50),
            'bundle': algo.get('bundle', 'unknown')
        }

        sizing = calculate_position_size(signal, stats, regime_data)
        sizing['algorithm_name'] = algo_name
        sizing_results.append(sizing)

        logger.info("  %-25s Kelly=%.1f%% Vol=%.1fx Regime=%.1fx Decay=%.1fx -> %.1f%% ($%.0f)",
                     algo_name,
                     sizing['kelly_base'] * 100,
                     sizing['vol_scalar'],
                     sizing['regime_modifier'],
                     sizing['decay_weight'],
                     sizing['final_size_pct'],
                     sizing['dollar_amount'])

    # Post to API
    if sizing_results:
        result = post_to_api('update_position_sizing', {
            'sizing': sizing_results,
            'regime_composite': regime_data.get('market', {}).get('composite_score', 50)
        })

        if result.get('ok'):
            logger.info("Position sizing data saved")
        else:
            logger.warning("API post returned: %s", result.get('error', 'unknown'))

    # Print summary
    logger.info("=" * 60)
    logger.info("POSITION SIZING SUMMARY")
    logger.info("  Algorithms sized: %d", len(sizing_results))
    if sizing_results:
        avg_size = np.mean([s['final_size_pct'] for s in sizing_results])
        decaying = sum(1 for s in sizing_results if s['is_decaying'])
        logger.info("  Average position: %.1f%%", avg_size)
        logger.info("  Decaying algos:   %d / %d", decaying, len(sizing_results))
    logger.info("=" * 60)

    return sizing_results


if __name__ == '__main__':
    run_position_sizing()
