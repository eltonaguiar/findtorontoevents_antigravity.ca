#!/usr/bin/env python3
"""
GARCH Volatility Forecasting & Kelly Adjustment Engine
========================================================
Multi-model volatility forecasting for position sizing optimization.

Models:
  1. GARCH(1,1)  — Standard symmetric volatility model
  2. EGARCH(1,1) — Asymmetric (leverage effect: bad news = more vol)
  3. GJR-GARCH   — Threshold GARCH (another asymmetric variant)

Features:
  - Per-ticker vol forecast for top traded symbols
  - Per-asset-class vol using proxies (SPY, BTC-USD, EURUSD=X)
  - Kelly fraction adjustment: scale position size by vol_target / vol_forecast
  - Historical vol forecast storage for tracking
  - Integration with lm_kelly_fractions table
  - Fallback: if GARCH fails, use realized vol (20-day rolling std)

Usage:
  python scripts/garch_vol.py                  # Full run with DB update
  python scripts/garch_vol.py --dry-run        # Forecast only, no DB write
  python scripts/garch_vol.py --ticker SPY     # Single ticker forecast

Requirements: pip install arch pandas yfinance mysql-connector-python numpy
"""
import os
import sys
import json
import math
import logging
import argparse
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import yfinance as yf
from arch import arch_model

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('garch_vol')

# DB config
DB_HOST = os.getenv('DB_HOST', 'mysql.50webs.com')
DB_USER = os.getenv('DB_USER', 'ejaguiar1_stocks')
DB_PASS = os.getenv('DB_PASS', 'stocks')
DB_NAME = os.getenv('DB_NAME', 'ejaguiar1_stocks')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, '..', 'data')

# Asset class proxy tickers for vol forecasting
ASSET_PROXIES = {
    'stocks': 'SPY',       # S&P 500 ETF
    'crypto': 'BTC-USD',   # Bitcoin
    'forex':  'EURUSD=X',  # EUR/USD
}

# Vol targeting config
VOL_TARGET_DAILY_PCT = 2.0    # 2% daily vol target for Kelly adjustment
KELLY_FLOOR = 0.01            # Minimum Kelly fraction (1%)
KELLY_CEILING = 0.25          # Maximum Kelly fraction (25%)
LOOKBACK_PERIOD = '2y'        # How far back to fetch price data
FORECAST_HORIZON = 5          # Forecast horizon in days


def connect_db():
    import mysql.connector
    return mysql.connector.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME
    )


def fetch_returns(ticker, period=LOOKBACK_PERIOD):
    """Fetch historical returns for a ticker via yfinance."""
    try:
        data = yf.download(ticker, period=period, progress=False)
        if data.empty:
            logger.warning("No data for %s", ticker)
            return None
        # Handle multi-level columns from yfinance
        if isinstance(data.columns, pd.MultiIndex):
            close = data['Close'][ticker] if ticker in data['Close'].columns else data['Close'].iloc[:, 0]
        else:
            close = data['Close']
        returns = 100.0 * close.pct_change().dropna()
        return returns
    except Exception as e:
        logger.warning("Failed to fetch %s: %s", ticker, e)
        return None


def fit_garch(returns, model_type='GARCH'):
    """
    Fit a GARCH-family model and return the volatility forecast.

    Args:
        returns: pd.Series of percentage returns
        model_type: 'GARCH', 'EGARCH', or 'GJR'

    Returns:
        dict with model results, or None on failure
    """
    try:
        if model_type == 'EGARCH':
            am = arch_model(returns, vol='EGARCH', p=1, o=1, q=1, dist='normal')
        elif model_type == 'GJR':
            am = arch_model(returns, vol='GARCH', p=1, o=1, q=1, dist='normal')
        else:
            am = arch_model(returns, vol='GARCH', p=1, q=1, dist='normal')

        res = am.fit(disp='off', show_warning=False)

        # Forecast
        fc = res.forecast(horizon=FORECAST_HORIZON)
        # Variance forecast for each horizon day
        var_forecast = fc.variance.iloc[-1].values

        # Annualized vol from 1-day forecast
        vol_1d = float(np.sqrt(var_forecast[0]))
        vol_5d = float(np.sqrt(np.mean(var_forecast)))
        vol_ann = vol_1d * np.sqrt(252)

        # Current realized vol (last 20 days)
        realized_vol_20d = float(returns.iloc[-20:].std()) if len(returns) >= 20 else float(returns.std())

        # Model quality metrics
        aic = float(res.aic)
        bic = float(res.bic)
        log_lik = float(res.loglikelihood)

        return {
            'model_type': model_type,
            'vol_1d_pct': round(vol_1d, 4),
            'vol_5d_avg_pct': round(vol_5d, 4),
            'vol_annualized_pct': round(vol_ann, 4),
            'realized_vol_20d_pct': round(realized_vol_20d, 4),
            'aic': round(aic, 2),
            'bic': round(bic, 2),
            'log_likelihood': round(log_lik, 2),
            'n_observations': len(returns),
        }
    except Exception as e:
        logger.warning("  %s model failed: %s", model_type, e)
        return None


def forecast_ticker(ticker, returns=None):
    """
    Run all three GARCH variants on a ticker and pick the best (lowest AIC).
    Returns best model results dict.
    """
    if returns is None:
        returns = fetch_returns(ticker)
    if returns is None or len(returns) < 50:
        logger.warning("  Insufficient data for %s (%s obs)", ticker,
                        len(returns) if returns is not None else 0)
        return None

    logger.info("  Fitting GARCH models for %s (%d obs)...", ticker, len(returns))

    results = []
    for mt in ['GARCH', 'EGARCH', 'GJR']:
        r = fit_garch(returns, mt)
        if r:
            r['ticker'] = ticker
            results.append(r)
            logger.info("    %s: vol_1d=%.3f%% vol_ann=%.2f%% AIC=%.1f",
                         mt, r['vol_1d_pct'], r['vol_annualized_pct'], r['aic'])

    if not results:
        # Fallback to simple realized vol
        realized = float(returns.std())
        logger.info("    All GARCH models failed — using realized vol: %.3f%%", realized)
        return {
            'ticker': ticker,
            'model_type': 'REALIZED',
            'vol_1d_pct': round(realized, 4),
            'vol_5d_avg_pct': round(realized, 4),
            'vol_annualized_pct': round(realized * np.sqrt(252), 4),
            'realized_vol_20d_pct': round(realized, 4),
            'aic': 0, 'bic': 0, 'log_likelihood': 0,
            'n_observations': len(returns),
        }

    # Pick best model (lowest AIC)
    best = min(results, key=lambda x: x['aic'])
    logger.info("    Best model: %s (AIC=%.1f)", best['model_type'], best['aic'])
    best['all_models'] = results
    return best


def adjust_kelly(kelly_fraction, vol_forecast_pct, vol_target_pct=VOL_TARGET_DAILY_PCT):
    """
    Adjust Kelly fraction based on volatility forecast.

    When vol is high (above target), reduce position size.
    When vol is low (below target), can increase (up to ceiling).

    Formula: adjusted_kelly = kelly * (vol_target / vol_forecast)
    Clamped to [KELLY_FLOOR, KELLY_CEILING]
    """
    if vol_forecast_pct <= 0:
        return kelly_fraction

    adjustment_ratio = vol_target_pct / max(vol_forecast_pct, 0.001)
    adjusted = kelly_fraction * adjustment_ratio
    clamped = max(KELLY_FLOOR, min(KELLY_CEILING, adjusted))

    return round(clamped, 4)


def update_kelly_fractions(conn, vol_forecasts, dry_run=False):
    """
    Update lm_kelly_fractions with vol-adjusted Kelly for each algo.

    Schema: lm_kelly_fractions has columns:
      algorithm_name, asset_class, win_rate, avg_win_pct, avg_loss_pct,
      full_kelly, half_kelly, sample_size, updated_at
    """
    cursor = conn.cursor(dictionary=True)

    # Ensure vol_adjusted_kelly column exists
    if not dry_run:
        try:
            cursor.execute("""
                ALTER TABLE lm_kelly_fractions
                ADD COLUMN vol_adjusted_kelly DECIMAL(8,6) NOT NULL DEFAULT 0
            """)
            conn.commit()
            logger.info("  Added vol_adjusted_kelly column to lm_kelly_fractions")
        except Exception:
            pass  # Column already exists

    # Get current Kelly fractions
    cursor.execute("SELECT DISTINCT algorithm_name, asset_class FROM lm_kelly_fractions")
    algos = cursor.fetchall()

    if not algos:
        logger.info("  No Kelly fractions found in DB — skipping Kelly adjustment")
        return []

    adjustments = []
    for row in algos:
        algo = row['algorithm_name']
        ac = row.get('asset_class', 'ALL').lower()
        if ac == 'all':
            ac = 'stocks'
        proxy = ASSET_PROXIES.get(ac, 'SPY')

        # Get vol forecast for this asset class
        vf = vol_forecasts.get(proxy)
        if not vf:
            continue

        # Get current Kelly (use half_kelly as the conservative default)
        cursor.execute(
            "SELECT half_kelly, full_kelly FROM lm_kelly_fractions "
            "WHERE algorithm_name = %s ORDER BY updated_at DESC LIMIT 1",
            (algo,)
        )
        krow = cursor.fetchone()
        if not krow:
            continue

        kelly = float(krow['half_kelly'])
        if kelly <= 0:
            kelly = float(krow['full_kelly']) * 0.5  # Use half of full Kelly

        vol_1d = vf['vol_1d_pct']
        adjusted = adjust_kelly(kelly, vol_1d)

        adjustments.append({
            'algo': algo,
            'asset_class': ac,
            'original_kelly': round(kelly, 4),
            'vol_1d_pct': vol_1d,
            'adjustment_ratio': round(VOL_TARGET_DAILY_PCT / max(vol_1d, 0.001), 3),
            'adjusted_kelly': adjusted,
        })

        if not dry_run:
            try:
                cursor.execute("""
                    UPDATE lm_kelly_fractions
                    SET vol_adjusted_kelly = %s
                    WHERE algorithm_name = %s
                    ORDER BY updated_at DESC LIMIT 1
                """, (adjusted, algo))
            except Exception as e:
                logger.warning("  Could not update vol_adjusted_kelly for %s: %s", algo, e)

    if not dry_run:
        conn.commit()

    return adjustments


def run(single_ticker=None, dry_run=False):
    """Main execution: forecast vol for all proxies + top tickers, adjust Kelly."""
    logger.info("=" * 70)
    logger.info("  GARCH Volatility Forecasting Engine")
    logger.info("  Models: GARCH(1,1), EGARCH(1,1), GJR-GARCH(1,1,1)")
    logger.info("  Vol target: %.1f%% daily | Forecast horizon: %d days",
                VOL_TARGET_DAILY_PCT, FORECAST_HORIZON)
    logger.info("=" * 70)

    vol_forecasts = {}

    if single_ticker:
        # Single ticker mode
        result = forecast_ticker(single_ticker)
        if result:
            vol_forecasts[single_ticker] = result
    else:
        # Forecast for asset class proxies
        logger.info("\n[1/3] Asset Class Proxy Forecasts:")
        for ac, ticker in ASSET_PROXIES.items():
            logger.info("  %s (%s):", ac.upper(), ticker)
            result = forecast_ticker(ticker)
            if result:
                vol_forecasts[ticker] = result
                result['asset_class'] = ac

        # Also fetch top traded tickers from DB for individual vol
        logger.info("\n[2/3] Top Traded Ticker Forecasts:")
        try:
            conn = connect_db()
            cur = conn.cursor(dictionary=True)
            cur.execute("""
                SELECT ticker, COUNT(*) as cnt
                FROM stock_picks
                GROUP BY ticker
                ORDER BY cnt DESC
                LIMIT 10
            """)
            top_tickers = [r['ticker'] for r in cur.fetchall()]
            conn.close()
        except Exception:
            top_tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']

        for tk in top_tickers:
            if tk in vol_forecasts:
                continue
            result = forecast_ticker(tk)
            if result:
                vol_forecasts[tk] = result

    # Print summary
    logger.info("\n" + "=" * 70)
    logger.info("  VOLATILITY FORECAST SUMMARY")
    logger.info("=" * 70)
    logger.info("  %-12s | %-8s | %8s | %8s | %8s | %8s",
                "Ticker", "Model", "Vol 1D", "Vol 5D", "Vol Ann", "Rlzd 20D")
    logger.info("  " + "-" * 65)
    for tk, vf in sorted(vol_forecasts.items()):
        logger.info("  %-12s | %-8s | %7.3f%% | %7.3f%% | %7.2f%% | %7.3f%%",
                     tk, vf['model_type'],
                     vf['vol_1d_pct'], vf['vol_5d_avg_pct'],
                     vf['vol_annualized_pct'], vf['realized_vol_20d_pct'])

    # Adjust Kelly fractions
    logger.info("\n[3/3] Kelly Fraction Adjustments:")
    try:
        conn = connect_db()
        adjustments = update_kelly_fractions(conn, vol_forecasts, dry_run=dry_run)
        conn.close()

        if adjustments:
            logger.info("  %-25s | %8s | %8s | %8s | %8s",
                         "Algorithm", "Kelly", "Vol 1D", "Ratio", "Adjusted")
            logger.info("  " + "-" * 70)
            for adj in adjustments:
                logger.info("  %-25s | %7.2f%% | %7.3f%% | %7.3f | %7.2f%%",
                             adj['algo'], adj['original_kelly'] * 100,
                             adj['vol_1d_pct'], adj['adjustment_ratio'],
                             adj['adjusted_kelly'] * 100)
        else:
            logger.info("  No Kelly fractions to adjust (lm_kelly_fractions may be empty)")
    except Exception as e:
        logger.warning("  Kelly adjustment skipped: %s", e)
        adjustments = []

    # Save results to JSON
    os.makedirs(DATA_DIR, exist_ok=True)
    output = {
        'generated': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'config': {
            'vol_target_daily_pct': VOL_TARGET_DAILY_PCT,
            'kelly_floor': KELLY_FLOOR,
            'kelly_ceiling': KELLY_CEILING,
            'forecast_horizon_days': FORECAST_HORIZON,
        },
        'vol_forecasts': {
            tk: {k: v for k, v in vf.items() if k != 'all_models'}
            for tk, vf in vol_forecasts.items()
        },
        'kelly_adjustments': adjustments,
    }
    output_path = os.path.join(DATA_DIR, 'garch_vol_forecast.json')
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    logger.info("\nResults saved: %s", output_path)

    return vol_forecasts, adjustments


def main():
    parser = argparse.ArgumentParser(description='GARCH Volatility Forecasting')
    parser.add_argument('--ticker', help='Single ticker to forecast')
    parser.add_argument('--dry-run', action='store_true', help='Forecast only, no DB writes')
    args = parser.parse_args()

    run(single_ticker=args.ticker, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
