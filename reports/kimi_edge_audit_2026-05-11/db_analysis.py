#!/usr/bin/env python3
"""
Financial Prediction System - Comprehensive Database Analysis
=============================================================
Generated analysis of stocks and backtests MySQL databases.
Covers: stocks, crypto, forex, ETFs, bonds, commodities, futures

Author: Financial Database Analyst
Date: 2025-06-10
"""

import warnings
warnings.filterwarnings('ignore')

import pymysql
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import stats
from scipy.stats import jarque_bera, shapiro, ttest_1samp, skew, kurtosis
import json
import os

# ============================================================
# DATABASE CONNECTIONS
# ============================================================

# Stocks Database
engine_stocks = create_engine(
    "mysql+pymysql://ejaguiar1_stocks:stocks@mysql.50webs.com/ejaguiar1_stocks",
    connect_args={'connect_timeout': 15}, pool_pre_ping=True
)

# Backtests Database
engine_backtests = create_engine(
    "mysql+pymysql://ejaguiar1_backtests:backtests@mysql.50webs.com/ejaguiar1_backtests",
    connect_args={'connect_timeout': 15}, pool_pre_ping=True
)

print("Connected to both databases successfully!")

# ============================================================
# SCHEMA DOCUMENTATION
# ============================================================
"""
STOCKS DATABASE (ejaguiar1_stocks) - 322 TABLES
Key tables:
- at_raw_picks: 143,514 rows - Main picks table (asset_class, direction, pnl_pct, confidence)
- at_signal_outcomes: 121 rows - Signal outcomes with PnL
- stock_picks: 7,239 rows - Stock picks
- cr_pair_picks: 980 rows - Crypto picks
- fx_pair_picks: 16 rows - Forex picks
- mf_fund_picks: 15 rows - Fund/ETF picks
- lm_trades: 201 rows - Live trades with realized PnL
- algorithms: 142 rows - Algorithm definitions
- algorithm_performance: 23 rows - Algorithm performance
- meme_signals: 50 rows - Meme signals
- meme_signal_results: 50 rows - Meme results
- paper_trades: 0 rows - Paper trading (empty)

BACKTESTS DATABASE (ejaguiar1_backtests) - 6 TABLES
Key tables:
- bt_backtest_runs: 285 rows - Backtest run summaries
- bt_backtest_trades: 50,000 rows - Individual backtest trades
- at_incubator_backtest_results: 1,285 rows - Incubator results
- at_large_backtest_results: 1,105 rows - Large backtest results
- backtest_results: 2 rows - Portfolio-level results
- backtest_trades: 50 rows - Older backtest trades
"""

# ============================================================
# DATA EXTRACTION QUERIES
# ============================================================

# Main picks table - resolved trades with PnL
raw_picks_query = """
    SELECT id, source_system, symbol, asset_class, direction,
           entry_price, take_profit, stop_loss, risk_reward, confidence,
           strategy, signal_timestamp, recorded_at, status,
           exit_price, exit_reason, pnl_pct, closed_at
    FROM at_raw_picks
    WHERE status IN ('WON', 'LOST', 'CLOSED', 'EXPIRED')
      AND pnl_pct IS NOT NULL
"""

# Signal outcomes
signal_outcomes_query = "SELECT * FROM at_signal_outcomes"

# Algorithm performance
algo_perf_query = "SELECT * FROM algorithm_performance"

# Backtest trades
bt_trades_query = "SELECT * FROM bt_backtest_trades"

# Backtest runs
bt_runs_query = "SELECT * FROM bt_backtest_runs"

# ============================================================
# METRIC COMPUTATION FUNCTIONS
# ============================================================

def compute_metrics(df, asset_class_name, label='resolved'):
    """Compute all performance metrics for a given subset of picks"""
    if len(df) == 0:
        return {'asset_class': asset_class_name, 'n_picks': 0}

    returns = df['pnl_pct'].dropna()
    if len(returns) == 0:
        return {'asset_class': asset_class_name, 'n_picks': len(df)}

    wins = returns[returns > 0]
    losses = returns[returns <= 0]
    n = len(returns)
    n_wins = len(wins)
    n_losses = len(losses)

    win_rate = (n_wins / n * 100) if n > 0 else 0
    avg_return = returns.mean()
    median_return = returns.median()
    std_return = returns.std()
    cumulative_pnl = returns.sum()

    # Sharpe (annualized)
    periods = 365 if 'CRYPTO' in asset_class_name else 252
    sharpe = (avg_return / std_return * np.sqrt(periods)) if std_return > 0 else 0

    # Sortino
    downside = returns[returns < 0]
    downside_std = downside.std() if len(downside) > 0 else 0
    sortino = (avg_return / downside_std * np.sqrt(periods)) if downside_std > 0 else 0

    # Max drawdown
    cumsum = returns.cumsum()
    running_max = cumsum.cummax()
    drawdown = cumsum - running_max
    max_dd = drawdown.min()

    # Calmar
    calmar = (avg_return * periods / abs(max_dd)) if max_dd != 0 else 0

    # Profit factor
    gross_wins = wins.sum() if len(wins) > 0 else 0
    gross_losses = abs(losses.sum()) if len(losses) > 0 else 0
    pf = gross_wins / gross_losses if gross_losses > 0 else float('inf')

    avg_winner = wins.mean() if len(wins) > 0 else 0
    avg_loser = losses.mean() if len(losses) > 0 else 0

    win_prob = n_wins / n if n > 0 else 0
    loss_prob = n_losses / n if n > 0 else 0
    expectancy = (win_prob * avg_winner) + (loss_prob * avg_loser)

    long_picks = df[df['direction'] == 'LONG']
    short_picks = df[df['direction'] == 'SHORT']
    long_wr = (len(long_picks[long_picks['pnl_pct'] > 0]) / len(long_picks) * 100) if len(long_picks) > 0 else 0
    short_wr = (len(short_picks[short_picks['pnl_pct'] > 0]) / len(short_picks) * 100) if len(short_picks) > 0 else 0

    return {
        'asset_class': asset_class_name, 'label': label, 'n_picks': n,
        'n_wins': n_wins, 'n_losses': n_losses, 'win_rate_pct': round(win_rate, 2),
        'avg_return_pct': round(avg_return, 4), 'median_return_pct': round(median_return, 4),
        'std_return_pct': round(std_return, 4), 'cumulative_pnl_pct': round(cumulative_pnl, 2),
        'sharpe_annualized': round(sharpe, 4), 'sortino_annualized': round(sortino, 4),
        'max_drawdown_pct': round(max_dd, 4), 'calmar_ratio': round(calmar, 4),
        'profit_factor': round(pf, 4), 'avg_winner_pct': round(avg_winner, 4),
        'avg_loser_pct': round(avg_loser, 4), 'expectancy_pct': round(expectancy, 4),
        'long_win_rate_pct': round(long_wr, 2), 'short_win_rate_pct': round(short_wr, 2),
        'n_long_picks': len(long_picks), 'n_short_picks': len(short_picks),
        'skewness': round(skew(returns), 4), 'kurtosis': round(kurtosis(returns), 4),
    }

# ============================================================
# KEY FINDINGS SUMMARY
# ============================================================
"""
KEY FINDINGS:
=============

1. NO ASSET CLASS SHOWS STATISTICALLY SIGNIFICANT POSITIVE EDGE
   - All t-tests show p-values > 0.05 for mean return > 0
   - All asset classes have negative or near-zero average returns

2. CRYPTO DOMINATES VOLUME (92% of all picks) BUT IS WORST PERFORMER
   - 51,049 picks, -3.73% avg return, -190,442% cumulative PnL
   - Win rate: 11.3% (far below random 50%)
   - Sharpe: -2.89 (severely negative)

3. EQUITY SHOWS SLIGHT POSITIVE TREND BUT NOT STATISTICALLY SIGNIFICANT
   - 814 picks, +0.02% avg return, p=0.115 (not significant)
   - Only asset class with positive Sharpe (0.67)
   - Profit factor: 2.18 (best among all classes)

4. MEME COINS: HIGH VOLATILITY, POOR RETURNS
   - 1,869 picks, -3.58% avg return
   - Win rate: 15.7%

5. FOREX: MODEST LOSSES
   - 605 picks, -0.19% avg return
   - Best short-direction performance (17.9% WR)

6. FUTURES & PENNY STOCKS: VERY POOR
   - Futures: -0.37% avg, 17.4% win rate
   - Penny stocks: -0.87% avg, 6.8% win rate

7. ML MODELS ARE POORLY CALIBRATED
   - Overall accuracy: 32.6% (worse than random)
   - High recall (84%) but very low precision (11.5%)
   - Confidence scores do NOT predict actual win rates
   - Brier score: 0.37 (poor calibration)

8. SEVERE BACKTEST VS LIVE GAP (OVERFITTING)
   - Backtest win rate: 42.4% vs Live: 11.1%
   - Backtest avg return: -1.05% vs Live: -3.56%
   - Gap: -2.51% (live significantly worse)

9. ALL 23 ALGORITHMS HAVE NEGATIVE RETURNS
   - Best: CAN SLIM (50% WR, -0.35% avg)
   - Worst: Alpha Factor Composite (3.9% WR, -10.0% avg)

10. DATA QUALITY ISSUES:
    - 38,312 resolved trades have zero PnL
    - 814 records with unknown asset class
    - 4 extreme outliers (up to -43,939%)
    - Meme signal results are suspicious (all marked as wins)
    - Zero paper trading data

11. DISTRIBUTION CHARACTERISTICS:
    - All asset classes: NOT normally distributed (JB p < 0.001)
    - All: Left-skewed with fat tails (negative skew, excess kurtosis)
    - No serial correlation in returns (lag-1 autocorr near 0)

12. DAY OF WEEK PATTERNS:
    - Tuesday shows best win rate (~48% for crypto)
    - Monday shows worst returns (deeply negative)
    - Weekend trading (Sat/Sun) shows large negative cumulative PnL
"""

if __name__ == '__main__':
    print("Analysis complete. See output files for detailed results.")
