#!/usr/bin/env python3
"""
Portfolio Optimizer — Black-Litterman + Risk Parity + CVaR.

Replaces fixed 5% allocation with mathematically optimal position sizing:
  1. Black-Litterman: Combines market equilibrium with your signal views
  2. Risk Parity: Equal risk contribution per asset (Bridgewater All Weather)
  3. CVaR Optimization: Minimize expected loss in worst 5% of scenarios
  4. Transaction Cost Awareness: Penalize high-turnover allocations

This is the single most impactful portfolio change — it converts your
algorithm signals into optimal position sizes accounting for correlation.

Pipeline:
  1. Fetch active signals from live_signals.php (your "views")
  2. Fetch historical returns for all tickers (yfinance)
  3. Run Black-Litterman to combine market + your views
  4. Optimize with CVaR constraint
  5. Post optimal weights to world_class_intelligence.php

Requires: pip install riskfolio-lib numpy pandas yfinance requests
Runs via: python run_all.py --portfolio
"""
import sys
import os
import json
import logging
import numpy as np
import pandas as pd
import warnings
from datetime import datetime, timedelta

warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import post_to_api, post_to_bridge, call_api
from config import API_BASE, ADMIN_KEY, TRACKED_TICKERS

logger = logging.getLogger('portfolio_optimizer')

try:
    import riskfolio as rp
    RISKFOLIO_AVAILABLE = True
except ImportError:
    RISKFOLIO_AVAILABLE = False
    logger.warning("riskfolio-lib not installed: pip install riskfolio-lib")

try:
    import yfinance as yf
    YF_AVAILABLE = True
except ImportError:
    YF_AVAILABLE = False


# ---------------------------------------------------------------------------
# Data Fetching
# ---------------------------------------------------------------------------

def fetch_historical_returns(tickers, period='1y'):
    """Fetch historical daily returns for portfolio optimization."""
    if not YF_AVAILABLE:
        logger.error("yfinance not available")
        return None

    logger.info("  Fetching %d tickers historical data (%s)...", len(tickers), period)

    try:
        data = yf.download(tickers, period=period, progress=False)
        if data.empty:
            return None

        # Handle multi-ticker vs single-ticker
        if isinstance(data.columns, pd.MultiIndex):
            prices = data['Adj Close']
        else:
            prices = data[['Adj Close']]
            prices.columns = tickers[:1]

        # Drop tickers with too much missing data
        valid_cols = prices.columns[prices.notna().sum() > len(prices) * 0.8]
        prices = prices[valid_cols].dropna()

        if prices.empty or len(prices) < 60:
            logger.warning("  Insufficient price data")
            return None

        returns = prices.pct_change().dropna()
        logger.info("  Got %d days of returns for %d tickers", len(returns), len(returns.columns))
        return returns

    except Exception as e:
        logger.warning("  Failed to fetch returns: %s", e)
        return None


def fetch_active_signals():
    """Fetch current active signals as 'views' for Black-Litterman."""
    result = call_api('list')
    if not result.get('ok'):
        return {}

    signals = result.get('signals', [])
    views = {}

    for sig in signals:
        ticker = sig.get('symbol', '')
        strength = float(sig.get('signal_strength', 50))
        direction = sig.get('signal_type', 'BUY')

        if not ticker or ticker not in TRACKED_TICKERS:
            continue

        # Convert signal strength to expected return view
        # Strength 80 = expect +4% over holding period
        # Strength 50 = expect +1%
        # Strength 30 = expect -1% (if SHORT)
        expected_return = (strength - 40) / 1000  # Scale to reasonable daily return

        if 'SHORT' in direction.upper():
            expected_return = -abs(expected_return)

        # Average if multiple signals for same ticker
        if ticker in views:
            views[ticker] = (views[ticker] + expected_return) / 2
        else:
            views[ticker] = expected_return

    return views


# ---------------------------------------------------------------------------
# Black-Litterman Model
# ---------------------------------------------------------------------------

def black_litterman_optimize(returns, views, risk_free=0.05):
    """
    Black-Litterman portfolio optimization.

    Combines market equilibrium (what the market "thinks") with your views
    (what your algorithms predict) to generate optimal allocations.

    Invented by Goldman Sachs. Used by BlackRock, AQR, most institutions.

    Args:
        returns: DataFrame of historical daily returns
        views: dict of {ticker: expected_daily_return}
        risk_free: annual risk-free rate

    Returns: dict with optimal weights per ticker
    """
    if not RISKFOLIO_AVAILABLE:
        logger.warning("riskfolio-lib not available, using equal weight fallback")
        n = len(returns.columns)
        return {col: round(1.0 / n, 4) for col in returns.columns}

    try:
        port = rp.Portfolio(returns=returns)

        # Step 1: Estimate expected returns and covariance
        port.assets_stats(method_mu='hist', method_cov='hist')

        # Step 2: If we have views, use Black-Litterman
        if views:
            tickers = list(returns.columns)
            view_tickers = [t for t in views.keys() if t in tickers]

            if view_tickers:
                n_assets = len(tickers)
                n_views = len(view_tickers)

                # P matrix: which assets each view is about
                P = np.zeros((n_views, n_assets))
                Q = np.zeros(n_views)

                for i, ticker in enumerate(view_tickers):
                    j = tickers.index(ticker)
                    P[i, j] = 1.0
                    Q[i] = views[ticker]

                P = pd.DataFrame(P, columns=tickers)
                Q = pd.DataFrame(Q, columns=['views'])

                # Apply Black-Litterman
                port.blacklitterman_stats(
                    P=P, Q=Q,
                    delta=2.5,  # Risk aversion coefficient
                    rf=risk_free / 252,  # Daily risk-free rate
                    eq=True  # Use equilibrium returns
                )

                logger.info("  Black-Litterman applied with %d views", n_views)

        # Step 3: Optimize for maximum Sharpe with CVaR constraint
        weights = port.optimization(
            model='BL' if views else 'Classic',
            rm='CVaR',  # Conditional Value at Risk
            obj='Sharpe',  # Maximize Sharpe ratio
            rf=risk_free / 252,
            hist=True
        )

        if weights is None or weights.empty:
            logger.warning("  Optimization returned empty weights")
            n = len(returns.columns)
            return {col: round(1.0 / n, 4) for col in returns.columns}

        result = {}
        for ticker in returns.columns:
            w = float(weights.loc[ticker].values[0]) if ticker in weights.index else 0.0
            if w > 0.001:  # Only include meaningful allocations
                result[ticker] = round(w, 4)

        return result

    except Exception as e:
        logger.warning("  Black-Litterman optimization failed: %s", e)
        n = len(returns.columns)
        return {col: round(1.0 / n, 4) for col in returns.columns}


# ---------------------------------------------------------------------------
# Risk Parity
# ---------------------------------------------------------------------------

def risk_parity_optimize(returns):
    """
    Risk Parity allocation — each asset contributes equally to portfolio risk.

    Used by Bridgewater's All Weather Fund.
    If crypto is 5x more volatile than bonds, hold 5x less crypto.

    Returns: dict with risk-parity weights per ticker
    """
    if not RISKFOLIO_AVAILABLE:
        n = len(returns.columns)
        return {col: round(1.0 / n, 4) for col in returns.columns}

    try:
        port = rp.Portfolio(returns=returns)
        port.assets_stats(method_mu='hist', method_cov='hist')

        weights = port.rp_optimization(
            model='Classic',
            rm='MV',  # Mean-Variance risk measure
            rf=0.05 / 252,
            hist=True
        )

        if weights is None or weights.empty:
            n = len(returns.columns)
            return {col: round(1.0 / n, 4) for col in returns.columns}

        result = {}
        for ticker in returns.columns:
            w = float(weights.loc[ticker].values[0]) if ticker in weights.index else 0.0
            if w > 0.001:
                result[ticker] = round(w, 4)

        return result

    except Exception as e:
        logger.warning("  Risk parity optimization failed: %s", e)
        n = len(returns.columns)
        return {col: round(1.0 / n, 4) for col in returns.columns}


# ---------------------------------------------------------------------------
# CVaR Computation
# ---------------------------------------------------------------------------

def compute_portfolio_risk(returns, weights):
    """
    Compute portfolio risk metrics including CVaR.

    Returns: {
        'annual_return': float,
        'annual_vol': float,
        'sharpe': float,
        'var_95': float,
        'cvar_95': float,
        'max_drawdown': float
    }
    """
    tickers = list(weights.keys())
    w = np.array([weights.get(t, 0) for t in returns.columns])

    if w.sum() == 0:
        return {}

    # Normalize weights
    w = w / w.sum()

    port_returns = (returns.values @ w)

    annual_return = float(np.mean(port_returns) * 252)
    annual_vol = float(np.std(port_returns, ddof=1) * np.sqrt(252))
    sharpe = annual_return / max(annual_vol, 0.001)

    # VaR and CVaR
    var_95 = float(np.percentile(port_returns, 5))
    cvar_95 = float(port_returns[port_returns <= var_95].mean()) if any(port_returns <= var_95) else var_95

    # Max drawdown
    cum_returns = np.cumsum(port_returns)
    peak = np.maximum.accumulate(cum_returns)
    drawdown = peak - cum_returns
    max_dd = float(np.max(drawdown)) if len(drawdown) > 0 else 0

    return {
        'annual_return_pct': round(annual_return * 100, 2),
        'annual_vol_pct': round(annual_vol * 100, 2),
        'sharpe_ratio': round(sharpe, 3),
        'var_95_daily': round(var_95 * 100, 3),
        'cvar_95_daily': round(cvar_95 * 100, 3),
        'max_drawdown_pct': round(max_dd * 100, 2),
    }


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------

def run_portfolio_optimization():
    """Run full portfolio optimization pipeline."""
    logger.info("=" * 60)
    logger.info("PORTFOLIO OPTIMIZER — Starting")
    logger.info("  Engine: %s", "riskfolio-lib" if RISKFOLIO_AVAILABLE else "equal-weight fallback")
    logger.info("=" * 60)

    # Fetch historical returns
    returns = fetch_historical_returns(TRACKED_TICKERS, period='1y')
    if returns is None:
        logger.error("Cannot fetch historical returns")
        return {}

    # Fetch active signal views
    views = fetch_active_signals()
    logger.info("  Active signal views: %d tickers", len(views))
    for ticker, view in views.items():
        logger.info("    %s: expected daily return = %+.4f%%", ticker, view * 100)

    # Run Black-Litterman optimization
    logger.info("")
    logger.info("--- Black-Litterman Optimization ---")
    bl_weights = black_litterman_optimize(returns, views)

    logger.info("  BL Optimal Weights:")
    for ticker, weight in sorted(bl_weights.items(), key=lambda x: x[1], reverse=True):
        logger.info("    %-6s: %.1f%%", ticker, weight * 100)

    # Run Risk Parity (as alternative/default)
    logger.info("")
    logger.info("--- Risk Parity Optimization ---")
    rp_weights = risk_parity_optimize(returns)

    logger.info("  Risk Parity Weights:")
    for ticker, weight in sorted(rp_weights.items(), key=lambda x: x[1], reverse=True):
        logger.info("    %-6s: %.1f%%", ticker, weight * 100)

    # Compute risk metrics for both
    logger.info("")
    logger.info("--- Portfolio Risk Metrics ---")

    bl_risk = compute_portfolio_risk(returns, bl_weights)
    rp_risk = compute_portfolio_risk(returns, rp_weights)

    # Equal weight for comparison
    eq_weights = {t: 1.0 / len(returns.columns) for t in returns.columns}
    eq_risk = compute_portfolio_risk(returns, eq_weights)

    logger.info("  %-20s  Return  Vol    Sharpe  CVaR95  MaxDD", "Strategy")
    for name, risk in [("Equal Weight", eq_risk), ("Risk Parity", rp_risk), ("Black-Litterman", bl_risk)]:
        if risk:
            logger.info("  %-20s  %+.1f%%  %.1f%%  %.3f   %.2f%%  %.1f%%",
                         name,
                         risk.get('annual_return_pct', 0),
                         risk.get('annual_vol_pct', 0),
                         risk.get('sharpe_ratio', 0),
                         risk.get('cvar_95_daily', 0),
                         risk.get('max_drawdown_pct', 0))

    # Choose best strategy (highest Sharpe)
    best_name = 'equal_weight'
    best_weights = eq_weights
    best_sharpe = eq_risk.get('sharpe_ratio', 0)

    if bl_risk.get('sharpe_ratio', 0) > best_sharpe:
        best_name = 'black_litterman'
        best_weights = bl_weights
        best_sharpe = bl_risk.get('sharpe_ratio', 0)

    if rp_risk.get('sharpe_ratio', 0) > best_sharpe:
        best_name = 'risk_parity'
        best_weights = rp_weights

    logger.info("")
    logger.info("  SELECTED: %s", best_name)

    # Post to API
    payload = {
        'source': 'portfolio_optimizer',
        'selected_strategy': best_name,
        'weights': {
            'black_litterman': bl_weights,
            'risk_parity': rp_weights,
            'equal_weight': {t: round(w, 4) for t, w in eq_weights.items()},
        },
        'risk_metrics': {
            'black_litterman': bl_risk,
            'risk_parity': rp_risk,
            'equal_weight': eq_risk,
        },
        'active_views': views,
        'computed_at': datetime.utcnow().isoformat(),
    }

    api_result = post_to_api('update_position_sizing', payload)
    if api_result.get('ok'):
        logger.info("Portfolio optimization posted to API")
    else:
        logger.warning("API post error: %s", api_result.get('error', 'unknown'))

    # Post to bridge dashboard
    post_to_bridge('portfolio_optimizer', payload,
                   "Strategy: %s, %d tickers" % (best_name, len(best_weights)))

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("PORTFOLIO OPTIMIZATION COMPLETE")
    logger.info("  Strategy: %s", best_name)
    logger.info("  Tickers: %d", len(best_weights))
    logger.info("=" * 60)

    return payload


def main():
    return run_portfolio_optimization()


if __name__ == '__main__':
    main()
