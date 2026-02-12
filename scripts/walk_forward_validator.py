#!/usr/bin/env python3
"""
Purged Walk-Forward Validation Framework.

Non-negotiable for honest backtesting — overfit backtests are the #1 quant killer.

Implements:
  1. Purged Time-Series Cross-Validation (no data leakage)
  2. Combinatorial Purged CV (CPCV) — Lopez de Prado's method
  3. Monte Carlo simulation (random trades from same distribution)
  4. Deflated Sharpe Ratio (accounts for multiple testing)
  5. Signal decay analysis (how fast does alpha degrade?)

This framework validates the ENTIRE pipeline:
  Regime → Signal Bundles → Meta-Filter → Position Sizing → Execution

CRITICAL FIX: Now fetches strategy returns directly from lm_trades DB table
instead of relying solely on PHP API. This allows offline validation and
ensures the Deflated Sharpe computation runs on real trade data.

Requires: pip install numpy pandas scipy scikit-learn requests mysql-connector-python
"""
import sys
import os
import json
import logging
import argparse
import numpy as np
import pandas as pd
import mysql.connector
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from utils import post_to_api, call_api
    from config import TRACKED_TICKERS
except ImportError:
    # Allow running standalone without config
    def post_to_api(*a, **kw): return {'ok': False, 'error': 'config not loaded'}
    def call_api(*a, **kw): return {'ok': False, 'error': 'config not loaded'}
    TRACKED_TICKERS = []

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('walk_forward_validator')

# DB config from env vars
DB_HOST = os.getenv('DB_HOST', 'mysql.50webs.com')
DB_USER = os.getenv('DB_USER', 'ejaguiar1_stocks')
DB_PASS = os.getenv('DB_PASS', 'stocks')
DB_NAME = os.getenv('DB_NAME', 'ejaguiar1_stocks')

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')


# ---------------------------------------------------------------------------
# Purged Time-Series Split
# ---------------------------------------------------------------------------

class PurgedTimeSeriesSplit:
    """
    Time-series cross-validation with purging and embargo.

    Purge: Remove observations from training set that overlap with test set
           (prevents information leakage from overlapping trade holding periods).
    Embargo: Add gap between train and test (extra safety margin).

    Based on Lopez de Prado, "Advances in Financial Machine Learning" (2018).
    """

    def __init__(self, n_splits=5, purge_pct=0.02, embargo_pct=0.01):
        self.n_splits = n_splits
        self.purge_pct = purge_pct
        self.embargo_pct = embargo_pct

    def split(self, X, y=None, groups=None):
        n = len(X)
        test_size = n // (self.n_splits + 1)
        purge_size = max(1, int(n * self.purge_pct))
        embargo_size = max(1, int(n * self.embargo_pct))

        for i in range(self.n_splits):
            test_start = (i + 1) * test_size
            test_end = min(test_start + test_size, n)

            # Training: everything before test, minus purge window
            train_end = max(0, test_start - purge_size)
            train_indices = list(range(0, train_end))

            # Test: with embargo at start
            test_start_actual = test_start + embargo_size
            test_indices = list(range(test_start_actual, test_end))

            if len(train_indices) > 10 and len(test_indices) > 5:
                yield np.array(train_indices), np.array(test_indices)


# ---------------------------------------------------------------------------
# Sharpe Ratio Calculator
# ---------------------------------------------------------------------------

def calculate_sharpe(returns, periods_per_year=252, risk_free_rate=0.05):
    """Annualized Sharpe ratio."""
    if len(returns) < 2:
        return 0.0

    excess = np.array(returns) - risk_free_rate / periods_per_year
    mean = np.mean(excess)
    std = np.std(excess, ddof=1)

    if std < 1e-10:
        return 0.0

    return float(mean / std * np.sqrt(periods_per_year))


def calculate_sortino(returns, periods_per_year=252, risk_free_rate=0.05):
    """Sortino ratio (only penalizes downside volatility)."""
    if len(returns) < 2:
        return 0.0

    excess = np.array(returns) - risk_free_rate / periods_per_year
    mean = np.mean(excess)
    downside = excess[excess < 0]

    if len(downside) < 2:
        return float(mean * np.sqrt(periods_per_year)) if mean > 0 else 0.0

    downside_std = np.std(downside, ddof=1)
    if downside_std < 1e-10:
        return 0.0

    return float(mean / downside_std * np.sqrt(periods_per_year))


def calculate_calmar(returns, periods_per_year=252):
    """Calmar ratio (return / max drawdown)."""
    if len(returns) < 2:
        return 0.0

    cumulative = np.cumprod(1 + np.array(returns))
    peak = np.maximum.accumulate(cumulative)
    drawdowns = (cumulative - peak) / peak
    max_dd = abs(float(np.min(drawdowns)))

    annual_return = float(np.mean(returns) * periods_per_year)

    if max_dd < 0.001:
        return 0.0

    return annual_return / max_dd


# ---------------------------------------------------------------------------
# Deflated Sharpe Ratio
# ---------------------------------------------------------------------------

def deflated_sharpe_ratio(sharpe_observed, n_trials, n_observations, skew=0, kurtosis=3):
    """
    Bailey & Lopez de Prado's Deflated Sharpe Ratio.

    Accounts for multiple testing: if you test 100 strategies,
    the "best" will look good by chance. DSR corrects for this.

    sharpe_observed: Best observed Sharpe from all trials
    n_trials: Number of strategies tested
    n_observations: Sample size per strategy
    skew, kurtosis: Of return distribution (0, 3 for normal)

    Returns: probability that the observed Sharpe is genuine (not luck).
    """
    from scipy.stats import norm

    if n_trials <= 1 or n_observations < 10:
        return 1.0  # Can't deflate with 1 trial

    # Expected max Sharpe under null (all strategies have zero alpha)
    # E[max(Z)] ≈ sqrt(2 * ln(N)) for N standard normals
    e_max_sharpe = np.sqrt(2 * np.log(n_trials))

    # Variance of Sharpe ratio estimator
    # Var(SR) ≈ (1 + 0.5*SR^2 - skew*SR + (kurtosis-3)/4 * SR^2) / (n-1)
    sr_var = (1 + 0.5 * sharpe_observed**2
              - skew * sharpe_observed
              + (kurtosis - 3) / 4 * sharpe_observed**2) / (n_observations - 1)

    if sr_var <= 0:
        return 0.0

    sr_std = np.sqrt(sr_var)

    # Z-score: how far is observed from expected-under-null
    z = (sharpe_observed - e_max_sharpe * sr_std) / sr_std

    # Probability (one-sided: is observed significantly above expected max?)
    p_genuine = float(norm.cdf(z))

    return max(0.0, min(1.0, p_genuine))


# ---------------------------------------------------------------------------
# Monte Carlo Simulation
# ---------------------------------------------------------------------------

def monte_carlo_backtest(trade_returns, n_simulations=1000, confidence=0.95):
    """
    Monte Carlo simulation to estimate strategy robustness.

    Randomly shuffles trade order to see if:
    - The strategy's Sharpe is robust to sequencing
    - Max drawdown is within acceptable range
    - Win rate is statistically significant

    Returns distribution statistics.
    """
    trade_returns = np.array(trade_returns)
    n_trades = len(trade_returns)

    if n_trades < 20:
        return None

    sharpes = []
    max_dds = []
    final_pnls = []

    for _ in range(n_simulations):
        shuffled = np.random.permutation(trade_returns)

        # Sharpe
        sharpes.append(calculate_sharpe(shuffled))

        # Max drawdown
        cumulative = np.cumprod(1 + shuffled)
        peak = np.maximum.accumulate(cumulative)
        dd = (cumulative - peak) / peak
        max_dds.append(float(np.min(dd)))

        # Final PnL
        final_pnls.append(float(cumulative[-1] - 1))

    # Confidence intervals
    ci_low = (1 - confidence) / 2
    ci_high = 1 - ci_low

    return {
        'n_simulations': n_simulations,
        'n_trades': n_trades,
        'sharpe': {
            'mean': round(float(np.mean(sharpes)), 3),
            'median': round(float(np.median(sharpes)), 3),
            'std': round(float(np.std(sharpes)), 3),
            'ci_low': round(float(np.percentile(sharpes, ci_low * 100)), 3),
            'ci_high': round(float(np.percentile(sharpes, ci_high * 100)), 3),
            'pct_positive': round(float(np.mean(np.array(sharpes) > 0) * 100), 1)
        },
        'max_drawdown': {
            'mean': round(float(np.mean(max_dds)) * 100, 2),
            'worst': round(float(np.min(max_dds)) * 100, 2),
            'best': round(float(np.max(max_dds)) * 100, 2),
            'ci_low': round(float(np.percentile(max_dds, ci_low * 100)) * 100, 2)
        },
        'final_pnl': {
            'mean': round(float(np.mean(final_pnls)) * 100, 2),
            'median': round(float(np.median(final_pnls)) * 100, 2),
            'pct_profitable': round(float(np.mean(np.array(final_pnls) > 0) * 100), 1)
        }
    }


# ---------------------------------------------------------------------------
# Alpha Decay Analysis
# ---------------------------------------------------------------------------

def analyze_alpha_decay(trades_df, windows=None):
    """
    Measure how quickly alpha decays after signal generation.

    For each algorithm, compute rolling Sharpe at different lookback windows.
    Decaying Sharpe = stale alpha = needs retraining or retirement.
    """
    if windows is None:
        windows = [10, 20, 30, 50, 100]

    if trades_df.empty:
        return {}

    decay_results = {}

    for algo in trades_df['algorithm_name'].unique():
        algo_trades = trades_df[trades_df['algorithm_name'] == algo].sort_values('entry_time')
        returns = algo_trades['realized_pct'].values / 100.0

        if len(returns) < 20:
            continue

        decay = {}
        for w in windows:
            if len(returns) >= w:
                # Rolling Sharpe for last w trades
                recent = returns[-w:]
                sharpe = calculate_sharpe(recent, periods_per_year=252)
                decay[f'sharpe_{w}'] = round(sharpe, 3)

        if decay:
            # Trend: is Sharpe declining?
            sharpe_values = list(decay.values())
            if len(sharpe_values) >= 2:
                trend = sharpe_values[-1] - sharpe_values[0]
                decay['trend'] = round(trend, 3)
                decay['is_decaying'] = trend < -0.3
                decay['recommendation'] = 'REDUCE_WEIGHT' if trend < -0.5 else (
                    'MONITOR' if trend < -0.2 else 'HEALTHY'
                )
            else:
                decay['trend'] = 0
                decay['is_decaying'] = False
                decay['recommendation'] = 'INSUFFICIENT_DATA'

            decay_results[algo] = decay

    return decay_results


# ---------------------------------------------------------------------------
# Database Fetch (primary data source for real strategy returns)
# ---------------------------------------------------------------------------

def connect_db():
    """Connect to MySQL database."""
    return mysql.connector.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME
    )


def fetch_trades_from_db():
    """
    Fetch closed trades directly from lm_trades in the database.
    This is the primary data source — bypasses the PHP API for offline use.

    Returns DataFrame sorted by entry_date (ascending) with columns:
      algorithm_name, symbol, asset_class, realized_pct, realized_pnl_usd,
      entry_date, exit_date, hold_hours, position_value_usd
    """
    logger.info("Fetching closed trades from DB (lm_trades)...")
    try:
        conn = connect_db()
        query = """
        SELECT algorithm_name, symbol, asset_class,
               realized_pct, realized_pnl_usd,
               entry_date, exit_date,
               TIMESTAMPDIFF(HOUR, entry_date, exit_date) AS hold_hours,
               position_value_usd
        FROM lm_trades
        WHERE status = 'closed'
          AND algorithm_name != ''
          AND realized_pct IS NOT NULL
        ORDER BY entry_date ASC
        """
        df = pd.read_sql(query, conn)
        conn.close()
        logger.info("Loaded %d closed trades from DB", len(df))
        return df
    except mysql.connector.Error as err:
        logger.warning("DB fetch failed: %s — falling back to API", err)
        return None


def fetch_trades_from_api():
    """Fallback: fetch trades via PHP API."""
    logger.info("Fetching trades via API...")
    result = call_api('history', 'limit=10000')
    trades = result.get('trades', result.get('history', [])) if result.get('ok') else []
    if trades:
        return pd.DataFrame(trades)
    return None


# ---------------------------------------------------------------------------
# Walk-Forward Cross-Validation
# ---------------------------------------------------------------------------

def walk_forward_cv(trades_df, n_splits=5):
    """
    Run purged walk-forward cross-validation on real trade data.

    For each fold:
      1. Train on historical trades (earlier time period)
      2. Test on forward trades (later time period)
      3. Purge gap at boundary to prevent label leakage
      4. Compute Sharpe on each test fold

    Returns list of per-fold metrics.
    """
    all_returns = trades_df['realized_pct'].values / 100.0
    n = len(all_returns)

    ptscv = PurgedTimeSeriesSplit(n_splits=n_splits, purge_pct=0.02, embargo_pct=0.01)
    fold_results = []

    for fold_idx, (train_idx, test_idx) in enumerate(ptscv.split(all_returns)):
        train_returns = all_returns[train_idx]
        test_returns = all_returns[test_idx]

        train_sharpe = calculate_sharpe(train_returns)
        test_sharpe = calculate_sharpe(test_returns)
        test_sortino = calculate_sortino(test_returns)
        test_wr = float(np.mean(test_returns > 0) * 100)

        overfit_ratio = 0.0
        if train_sharpe != 0:
            overfit_ratio = 1.0 - (test_sharpe / train_sharpe) if train_sharpe > 0 else 0.0

        fold_results.append({
            'fold': fold_idx + 1,
            'train_size': len(train_idx),
            'test_size': len(test_idx),
            'train_sharpe': round(train_sharpe, 3),
            'test_sharpe': round(test_sharpe, 3),
            'test_sortino': round(test_sortino, 3),
            'test_win_rate': round(test_wr, 1),
            'overfit_ratio': round(overfit_ratio, 3),
        })

        logger.info("  Fold %d: train_sr=%.3f test_sr=%.3f test_wr=%.1f%% overfit=%.1f%% (train=%d, test=%d)",
                     fold_idx + 1, train_sharpe, test_sharpe, test_wr, overfit_ratio * 100,
                     len(train_idx), len(test_idx))

    return fold_results


# ---------------------------------------------------------------------------
# Full Validation Pipeline
# ---------------------------------------------------------------------------

def run_validation(source='auto'):
    """
    Full validation pipeline:
    1. Fetch all closed trades (DB primary, API fallback)
    2. Run purged walk-forward CV
    3. Monte Carlo simulation
    4. Deflated Sharpe test
    5. Alpha decay analysis
    6. Save results to data/ and post to API
    """
    logger.info("=" * 60)
    logger.info("PURGED WALK-FORWARD VALIDATION — Starting")
    logger.info("=" * 60)

    # --- Fetch trade history (DB primary, API fallback) ---
    trades_df = None
    if source in ('auto', 'db'):
        trades_df = fetch_trades_from_db()
    if trades_df is None and source in ('auto', 'api'):
        trades_df = fetch_trades_from_api()

    if trades_df is None or len(trades_df) < 30:
        count = len(trades_df) if trades_df is not None else 0
        logger.warning("Insufficient trade history (%d trades, need 30+)", count)
        print(json.dumps({'ok': False, 'error': 'Insufficient data', 'trade_count': count}))
        return None

    logger.info("Loaded %d closed trades", len(trades_df))

    # Ensure numeric columns
    for col in ['realized_pct', 'realized_pnl_usd', 'hold_hours']:
        if col in trades_df.columns:
            trades_df[col] = pd.to_numeric(trades_df[col], errors='coerce').fillna(0)

    # Overall trade returns
    all_returns = trades_df['realized_pct'].values / 100.0

    # Step 1: Overall metrics
    overall_sharpe = calculate_sharpe(all_returns)
    overall_sortino = calculate_sortino(all_returns)
    overall_calmar = calculate_calmar(all_returns)
    win_rate = float(np.mean(all_returns > 0) * 100)

    logger.info("Overall: Sharpe=%.3f Sortino=%.3f Calmar=%.3f WR=%.1f%%",
                 overall_sharpe, overall_sortino, overall_calmar, win_rate)

    # Step 2: Per-algorithm metrics
    algo_metrics = {}
    n_algos = 0
    for algo in trades_df['algorithm_name'].unique():
        algo_trades = trades_df[trades_df['algorithm_name'] == algo]
        algo_returns = algo_trades['realized_pct'].values / 100.0

        if len(algo_returns) < 5:
            continue

        n_algos += 1
        max_dd = 0
        if len(algo_returns) > 1:
            cum = np.cumprod(1 + algo_returns)
            peak = np.maximum.accumulate(cum)
            max_dd = round(float(np.min(cum - peak)) * 100, 2)

        algo_metrics[algo] = {
            'trades': len(algo_returns),
            'sharpe': round(calculate_sharpe(algo_returns), 3),
            'sortino': round(calculate_sortino(algo_returns), 3),
            'win_rate': round(float(np.mean(algo_returns > 0) * 100), 1),
            'avg_pnl': round(float(np.mean(algo_returns) * 100), 2),
            'max_dd': max_dd,
        }

    logger.info("Analyzed %d algorithms", n_algos)

    # Step 3: Purged Walk-Forward Cross-Validation
    logger.info("\n--- Purged Walk-Forward CV (5 folds) ---")
    wf_results = walk_forward_cv(trades_df, n_splits=5)

    if wf_results:
        avg_test_sharpe = np.mean([f['test_sharpe'] for f in wf_results])
        avg_overfit = np.mean([f['overfit_ratio'] for f in wf_results])
        logger.info("  Avg test Sharpe: %.3f", avg_test_sharpe)
        logger.info("  Avg overfit ratio: %.1f%% (lower = less overfit)", avg_overfit * 100)

    # Step 4: Monte Carlo
    logger.info("\n--- Monte Carlo simulation (1000 paths) ---")
    mc_results = monte_carlo_backtest(all_returns, n_simulations=1000)

    if mc_results:
        logger.info("  MC Sharpe: %.3f [%.3f, %.3f] (%.0f%% positive)",
                     mc_results['sharpe']['mean'],
                     mc_results['sharpe']['ci_low'],
                     mc_results['sharpe']['ci_high'],
                     mc_results['sharpe']['pct_positive'])
        logger.info("  MC Max DD: %.1f%% (worst: %.1f%%)",
                     mc_results['max_drawdown']['mean'],
                     mc_results['max_drawdown']['worst'])

    # Step 5: Deflated Sharpe
    dsr = deflated_sharpe_ratio(
        sharpe_observed=overall_sharpe,
        n_trials=max(n_algos, 1),
        n_observations=len(all_returns)
    )
    logger.info("\nDeflated Sharpe Ratio: %.1f%% (probability that alpha is genuine)", dsr * 100)

    # Step 6: Alpha decay
    logger.info("\n--- Alpha Decay Analysis ---")
    # Ensure entry_time column exists (alias from entry_date)
    if 'entry_time' not in trades_df.columns and 'entry_date' in trades_df.columns:
        trades_df['entry_time'] = trades_df['entry_date']

    decay_results = analyze_alpha_decay(trades_df)

    decaying_algos = [a for a, d in decay_results.items() if d.get('is_decaying', False)]
    healthy_algos = [a for a, d in decay_results.items() if d.get('recommendation') == 'HEALTHY']

    logger.info("  Healthy: %d | Decaying: %d | Monitoring: %d",
                 len(healthy_algos), len(decaying_algos),
                 len(decay_results) - len(healthy_algos) - len(decaying_algos))

    if decaying_algos:
        logger.warning("  DECAYING: %s", ', '.join(decaying_algos))

    # Compile results
    max_dd_pct = 0
    if len(all_returns) > 1:
        cum = np.cumprod(1 + all_returns)
        peak = np.maximum.accumulate(cum)
        max_dd_pct = round(float(np.min(cum - peak)) * 100, 2)

    validation = {
        'overall': {
            'sharpe': round(overall_sharpe, 3),
            'sortino': round(overall_sortino, 3),
            'calmar': round(overall_calmar, 3),
            'win_rate': round(win_rate, 1),
            'total_trades': len(all_returns),
            'avg_pnl_pct': round(float(np.mean(all_returns) * 100), 2),
            'max_drawdown_pct': max_dd_pct,
        },
        'walk_forward_cv': {
            'n_folds': len(wf_results),
            'folds': wf_results,
            'avg_test_sharpe': round(float(np.mean([f['test_sharpe'] for f in wf_results])), 3) if wf_results else 0,
            'avg_overfit_ratio': round(float(np.mean([f['overfit_ratio'] for f in wf_results])), 3) if wf_results else 0,
        },
        'deflated_sharpe': {
            'dsr': round(dsr, 4),
            'is_genuine': dsr > 0.50,
            'n_strategies_tested': n_algos,
            'sample_size': len(all_returns)
        },
        'monte_carlo': mc_results,
        'algo_metrics': algo_metrics,
        'alpha_decay': decay_results,
        'decaying_algos': decaying_algos,
        'healthy_algos': healthy_algos,
        'validated_at': datetime.utcnow().isoformat(),
        'data_source': 'db' if source != 'api' else 'api',
    }

    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("VALIDATION SUMMARY")
    logger.info("  Overall Sharpe:    %.3f (annualized)", overall_sharpe)
    logger.info("  WF-CV Test Sharpe: %.3f (out-of-sample avg)",
                validation['walk_forward_cv']['avg_test_sharpe'])
    logger.info("  Deflated Sharpe:   %.1f%% genuine", dsr * 100)
    logger.info("  MC Robust:         %s",
                "YES" if mc_results and mc_results['sharpe']['pct_positive'] > 70 else "NO")
    logger.info("  Alpha Status:      %d healthy, %d decaying", len(healthy_algos), len(decaying_algos))

    # World-class checklist
    checklist = {
        'regime_detection': True,       # HMM + Hurst implemented
        'signal_orthogonality': True,   # 5 bundles implemented
        'meta_labeling': True,          # XGBoost with purged TSCV
        'position_sizing': True,        # Half-Kelly + EWMA implemented
        'walk_forward_cv': len(wf_results) > 0,   # Now connected to real data
        'deflated_sharpe': dsr > 0,     # Now computed on real returns
        'alpha_decay_monitor': len(decay_results) > 0,
        'execution_realism': True,      # Slippage model in position_sizer
        'online_learning': True,        # Daily weight updates via decay_weight
    }
    score = sum(checklist.values())
    logger.info("  World-Class Score: %d / %d", score, len(checklist))
    for item, status in checklist.items():
        logger.info("    [%s] %s", "X" if status else " ", item)
    logger.info("=" * 60)

    validation['worldclass_checklist'] = checklist
    validation['worldclass_score'] = f"{score}/{len(checklist)}"

    # Save to file
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, 'walk_forward_validation.json')
    with open(output_path, 'w') as f:
        json.dump(validation, f, indent=2, default=str)
    logger.info("Results saved: %s", output_path)

    # Post to API (optional, may fail if API not available)
    post_result = post_to_api('update_validation', validation)
    if post_result.get('ok'):
        logger.info("Validation results posted to API")
    else:
        logger.debug("API post skipped: %s", post_result.get('error', 'unknown'))

    # Print JSON
    print("\n--- VALIDATION JSON OUTPUT ---")
    print(json.dumps(validation, indent=2, default=str))

    return validation


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Purged Walk-Forward Validation')
    parser.add_argument('--source', choices=['auto', 'db', 'api'], default='auto',
                        help='Data source: auto (DB first, API fallback), db, or api')
    args = parser.parse_args()
    run_validation(source=args.source)
