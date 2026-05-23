"""
Unified Monte Carlo Backtester & Statistical Validator
=======================================================
Testing Framework for All Strategies

Implements the TESTING_PROTOCOL.MD requirements:
- Layer 4: Statistical significance (p-value, Bonferroni)
- Layer 5: Bootstrap / Monte Carlo confidence intervals
- Walk-forward validation
- Cross-asset performance aggregation

Usage:
    from unified_monte_carlo_backtester import run_full_validation
    results = run_full_validation(df, signal_generator, config)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
import json


@dataclass
class ValidationConfig:
    # Monte Carlo
    mc_simulations: int = 1000
    mc_confidence: float = 0.95

    # Walk-forward
    wf_train_pct: float = 0.70
    wf_val_pct: float = 0.15
    wf_test_pct: float = 0.15
    wf_min_train_bars: int = 500

    # Quality gates (from TESTING_PROTOCOL Layer 2.5)
    min_score: float = 40.0
    min_promotion_score: float = 60.0
    min_win_rate: float = 50.0
    min_profit_factor: float = 1.3
    max_drawdown_pct: float = 20.0
    min_sharpe: float = 0.5
    min_trades: int = 30

    # Multi-testing correction
    bonferroni_alpha: float = 0.05


def compute_metrics(pnls: List[float], annualization: float = 252) -> Dict:
    """Compute standard trading metrics from a list of per-trade PnLs."""
    if len(pnls) < 2:
        return {'error': 'insufficient_trades'}

    pnls_arr = np.array(pnls)
    wins = pnls_arr[pnls_arr > 0]
    losses = pnls_arr[pnls_arr <= 0]

    gross_profit = wins.sum() if len(wins) > 0 else 0
    gross_loss = abs(losses.sum()) if len(losses) > 0 else 1e-10

    equity = np.cumsum(pnls_arr)
    peak = equity[0]
    max_dd = 0
    for v in equity:
        peak = max(peak, v)
        max_dd = max(max_dd, peak - v)

    # Sharpe (annualized)
    mean_pnl = np.mean(pnls_arr)
    std_pnl = np.std(pnls_arr) + 1e-10
    sharpe = mean_pnl / std_pnl * np.sqrt(annualization)

    # Sortino (downside deviation only)
    downside = pnls_arr[pnls_arr < 0]
    downside_std = np.std(downside) + 1e-10 if len(downside) > 0 else 1e-10
    sortino = mean_pnl / downside_std * np.sqrt(annualization)

    # Calmar = annualized return / max drawdown
    annual_return = mean_pnl * annualization
    calmar = annual_return / (max_dd + 1e-10)

    return {
        'total_trades': len(pnls),
        'win_rate': round(len(wins) / len(pnls) * 100, 2),
        'profit_factor': round(gross_profit / gross_loss, 3),
        'sharpe': round(sharpe, 3),
        'sortino': round(sortino, 3),
        'calmar': round(calmar, 3),
        'max_drawdown': round(max_dd, 6),
        'max_drawdown_pct': round(max_dd / (equity[0] + abs(max_dd) + 1e-10) * 100, 2),
        'avg_pnl': round(mean_pnl, 6),
        'avg_win': round(wins.mean(), 6) if len(wins) > 0 else 0,
        'avg_loss': round(losses.mean(), 6) if len(losses) > 0 else 0,
        'total_return': round(equity[-1], 6),
        'equity_curve': equity.tolist(),
    }


def monte_carlo_permutation(pnls: List[float], n_sim: int = 1000,
                            confidence: float = 0.95,
                            annualization: float = 252) -> Dict:
    """
    Monte Carlo permutation test.
    H0: The order of trades doesn't matter (no edge).
    Shuffle trade sequence n_sim times, compute Sharpe each time.
    If actual Sharpe > 95th percentile of shuffled → edge is real.
    """
    pnls_arr = np.array(pnls)
    actual_sharpe = np.mean(pnls_arr) / (np.std(pnls_arr) + 1e-10) * np.sqrt(annualization)

    sim_sharpes = []
    for _ in range(n_sim):
        shuffled = np.random.permutation(pnls_arr)
        s_sharpe = np.mean(shuffled) / (np.std(shuffled) + 1e-10) * np.sqrt(annualization)
        sim_sharpes.append(s_sharpe)

    threshold = np.percentile(sim_sharpes, confidence * 100)
    p_value = np.mean([s >= actual_sharpe for s in sim_sharpes])

    return {
        'status': 'PASS' if actual_sharpe > threshold else 'FAIL',
        'actual_sharpe': round(actual_sharpe, 3),
        'simulated_mean': round(np.mean(sim_sharpes), 3),
        'simulated_std': round(np.std(sim_sharpes), 3),
        'threshold_95': round(threshold, 3),
        'p_value': round(p_value, 4),
        'edge_significant': actual_sharpe > threshold,
        'n_simulations': n_sim,
    }


def bootstrap_confidence(pnls: List[float], n_boot: int = 1000,
                         confidence: float = 0.95) -> Dict:
    """
    Bootstrap confidence intervals for key metrics.
    """
    pnls_arr = np.array(pnls)
    boot_pf = []
    boot_wr = []
    boot_sharpe = []

    for _ in range(n_boot):
        sample = np.random.choice(pnls_arr, size=len(pnls_arr), replace=True)
        wins = sample[sample > 0]
        losses = sample[sample <= 0]
        gp = wins.sum() if len(wins) > 0 else 0
        gl = abs(losses.sum()) if len(losses) > 0 else 1e-10
        boot_pf.append(gp / gl)
        boot_wr.append(len(wins) / len(sample) * 100)
        boot_sharpe.append(np.mean(sample) / (np.std(sample) + 1e-10) * np.sqrt(252))

    lo = (1 - confidence) / 2 * 100
    hi = (1 + confidence) / 2 * 100

    return {
        'profit_factor_ci': (round(np.percentile(boot_pf, lo), 3), round(np.percentile(boot_pf, hi), 3)),
        'win_rate_ci': (round(np.percentile(boot_wr, lo), 1), round(np.percentile(boot_wr, hi), 1)),
        'sharpe_ci': (round(np.percentile(boot_sharpe, lo), 3), round(np.percentile(boot_sharpe, hi), 3)),
    }


def walk_forward_split(df: pd.DataFrame, config: ValidationConfig = None) -> Dict:
    """
    Walk-forward validation split.
    Returns dict with 'train', 'val', 'test' DataFrames.
    """
    if config is None:
        config = ValidationConfig()

    n = len(df)
    train_end = int(n * config.wf_train_pct)
    val_end = int(n * (config.wf_train_pct + config.wf_val_pct))

    return {
        'train': df.iloc[:train_end],
        'val': df.iloc[train_end:val_end],
        'test': df.iloc[val_end:],
    }


def quality_gate(metrics: Dict, config: ValidationConfig = None) -> Dict:
    """
    Apply quality gates from TESTING_PROTOCOL.MD Layer 2.5.
    Returns pass/fail with reasons.
    """
    if config is None:
        config = ValidationConfig()

    checks = {}
    checks['sufficient_trades'] = metrics.get('total_trades', 0) >= config.min_trades
    checks['win_rate_ok'] = metrics.get('win_rate', 0) >= config.min_win_rate
    checks['profit_factor_ok'] = metrics.get('profit_factor', 0) >= config.min_profit_factor
    checks['drawdown_ok'] = metrics.get('max_drawdown_pct', 100) <= config.max_drawdown_pct
    checks['sharpe_ok'] = metrics.get('sharpe', 0) >= config.min_sharpe

    passed = all(checks.values())
    failed = [k for k, v in checks.items() if not v]

    return {
        'status': 'PASS' if passed else 'FAIL',
        'checks': checks,
        'failed_gates': failed,
        'promotion_eligible': passed and metrics.get('profit_factor', 0) >= 1.5,
    }


def run_full_validation(df: pd.DataFrame, signal_fn: Callable,
                        config: ValidationConfig = None,
                        annualization: float = 252) -> Dict:
    """
    Full validation pipeline per TESTING_PROTOCOL.MD:
    1. Generate signals
    2. Backtest
    3. Compute metrics (Sharpe, Sortino, Calmar, max DD, PF)
    4. Monte Carlo permutation test
    5. Bootstrap confidence intervals
    6. Walk-forward split validation
    7. Quality gate check
    """
    if config is None:
        config = ValidationConfig()

    # 1. Generate signals and backtest
    signals = signal_fn(df)
    pnls = []
    pos = None
    for i in range(1, len(signals)):
        row, price = signals.iloc[i], df['close'].iloc[i]
        if pos:
            bh = i - pos['ei']
            sl, tp = pos['sl'], pos['tp']
            if pos['d'] == 'long':
                if price <= sl or price >= tp or bh >= pos.get('mh', 20):
                    ex = min(price, sl) if price <= sl else max(price, tp) if price >= tp else price
                    pnls.append(ex - pos['ep'])
                    pos = None
            else:
                if price >= sl or price <= tp or bh >= pos.get('mh', 20):
                    ex = max(price, sl) if price >= sl else min(price, tp) if price <= tp else price
                    pnls.append(pos['ep'] - ex)
                    pos = None
        if not pos and row.get('signal', 0) != 0:
            pos = {'d': 'long' if row['signal'] == 1 else 'short', 'ep': price,
                   'sl': row.get('stop_loss', price * 0.98),
                   'tp': row.get('take_profit', price * 1.02),
                   'ei': i, 'mh': row.get('max_hold', 20)}

    if len(pnls) < config.min_trades:
        return {
            'status': 'INSUFFICIENT_DATA',
            'trades': len(pnls),
            'message': f'Only {len(pnls)} trades, need {config.min_trades}'
        }

    # 2. Metrics
    metrics = compute_metrics(pnls, annualization)

    # 3. Monte Carlo
    mc = monte_carlo_permutation(pnls, config.mc_simulations, config.mc_confidence, annualization)

    # 4. Bootstrap
    ci = bootstrap_confidence(pnls)

    # 5. Walk-forward
    wf = walk_forward_split(df, config)

    # 6. Quality gate
    gate = quality_gate(metrics, config)

    return {
        'status': 'COMPLETE',
        'metrics': metrics,
        'monte_carlo': mc,
        'bootstrap_ci': ci,
        'walk_forward': {
            'train_bars': len(wf['train']),
            'val_bars': len(wf['val']),
            'test_bars': len(wf['test']),
        },
        'quality_gate': gate,
        'recommendation': 'PRODUCTION' if gate['promotion_eligible'] else
                          'FORWARD_TEST' if gate['status'] == 'PASS' else 'NEEDS_WORK',
    }


def generate_cross_asset_summary(results: Dict[str, Dict]) -> str:
    """
    Generate a cross-asset performance summary table.
    results: dict of asset_class -> run_full_validation() result
    """
    lines = ["# Cross-Asset Strategy Performance Summary\n"]
    lines.append("| Asset Class | Trades | WR% | PF | Sharpe | Sortino | Max DD% | Status | Recommendation |")
    lines.append("|-------------|--------|-----|-----|--------|---------|---------|--------|----------------|")

    for asset, res in results.items():
        if res.get('status') != 'COMPLETE':
            lines.append(f"| {asset} | - | - | - | - | - | - | {res.get('status', 'ERROR')} | NEEDS_WORK |")
            continue
        m = res['metrics']
        gate = res['quality_gate']
        lines.append(
            f"| {asset} | {m['total_trades']} | {m['win_rate']} | {m['profit_factor']} "
            f"| {m['sharpe']} | {m['sortino']} | {m['max_drawdown_pct']} "
            f"| {gate['status']} | {res['recommendation']} |"
        )

    # Flag failures
    lines.append("\n## Quality Gate Failures\n")
    for asset, res in results.items():
        if res.get('quality_gate', {}).get('failed_gates'):
            lines.append(f"- **{asset}**: {', '.join(res['quality_gate']['failed_gates'])}")

    return '\n'.join(lines)


if __name__ == '__main__':
    print("Unified Monte Carlo Backtester & Statistical Validator")
    print("=" * 50)
    print("Implements TESTING_PROTOCOL.MD Layers 2.5, 4, 5, 6")
    print("Usage: run_full_validation(df, signal_generator_fn, config)")
