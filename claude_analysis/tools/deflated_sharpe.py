#!/usr/bin/env python3
"""
GOLDMINE_CURSOR — Deflated Sharpe Ratio (DSR) Calculator

The Deflated Sharpe Ratio adjusts for multiple hypothesis testing.
When you test 50+ algorithms, some will look good by random chance.
DSR corrects for this by accounting for:
  - Number of strategies tested (N)
  - Skewness of returns
  - Kurtosis of returns
  - Length of track record

Reference: Bailey & Lopez de Prado (2014)
"The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting,
 and Non-Normality"

Usage:
  python deflated_sharpe.py --db-host mysql.50webs.com --db-user X --db-pass X --db-name X
  python deflated_sharpe.py --help
"""

import argparse
import math
import sys

try:
    from scipy import stats as sp_stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


def compute_dsr(observed_sharpe, num_strategies, track_length, skewness=0, kurtosis=3):
    """
    Compute the Deflated Sharpe Ratio.

    Parameters:
    -----------
    observed_sharpe : float
        The Sharpe ratio of the strategy being evaluated
    num_strategies : int
        Total number of strategies tested (including this one)
    track_length : int
        Number of return observations (e.g., number of trades)
    skewness : float
        Skewness of returns (0 = normal)
    kurtosis : float
        Kurtosis of returns (3 = normal)

    Returns:
    --------
    dict with:
        - dsr: Deflated Sharpe Ratio (probability that true Sharpe > 0)
        - expected_max_sharpe: Expected maximum Sharpe from N random strategies
        - haircut: Percentage reduction from observed to deflated
        - pass: Boolean — True if DSR > 0.95 (strategy likely has real alpha)
    """

    if track_length < 2 or num_strategies < 1:
        return {'dsr': 0, 'expected_max_sharpe': 0, 'haircut': 100, 'pass': False,
                'error': 'Insufficient data'}

    # Expected maximum Sharpe ratio from N independent trials
    # E[max(SR)] ≈ (1 - γ) * Φ^{-1}(1 - 1/N) + γ * Φ^{-1}(1 - 1/(N*e))
    # where γ ≈ 0.5772 (Euler-Mascheroni constant)
    gamma = 0.5772156649

    if HAS_SCIPY:
        z1 = sp_stats.norm.ppf(1.0 - 1.0 / num_strategies) if num_strategies > 1 else 0
        z2 = sp_stats.norm.ppf(1.0 - 1.0 / (num_strategies * math.e)) if num_strategies > 1 else 0
    else:
        # Approximate inverse normal using rational approximation
        def approx_ppf(p):
            if p <= 0 or p >= 1:
                return 0
            t = math.sqrt(-2 * math.log(min(p, 1 - p)))
            c0, c1, c2 = 2.515517, 0.802853, 0.010328
            d1, d2, d3 = 1.432788, 0.189269, 0.001308
            result = t - (c0 + c1 * t + c2 * t * t) / (1 + d1 * t + d2 * t * t + d3 * t * t * t)
            return result if p > 0.5 else -result

        z1 = approx_ppf(1.0 - 1.0 / num_strategies) if num_strategies > 1 else 0
        z2 = approx_ppf(1.0 - 1.0 / (num_strategies * math.e)) if num_strategies > 1 else 0

    expected_max_sr = (1 - gamma) * z1 + gamma * z2

    # Standard error of the Sharpe ratio (adjusted for non-normality)
    se_sr = math.sqrt(
        (1 - skewness * observed_sharpe + (kurtosis - 1) / 4.0 * observed_sharpe ** 2)
        / (track_length - 1)
    )

    if se_sr == 0:
        return {'dsr': 0, 'expected_max_sharpe': expected_max_sr, 'haircut': 100, 'pass': False,
                'error': 'Zero standard error'}

    # DSR test statistic
    test_stat = (observed_sharpe - expected_max_sr) / se_sr

    # Convert to probability (one-sided test)
    if HAS_SCIPY:
        dsr_prob = sp_stats.norm.cdf(test_stat)
    else:
        # Approximate CDF
        def approx_cdf(x):
            if x < -8:
                return 0
            if x > 8:
                return 1
            k = 1.0 / (1.0 + 0.2316419 * abs(x))
            poly = k * (0.319381530 + k * (-0.356563782 + k * (1.781477937 + k * (-1.821255978 + k * 1.330274429))))
            cdf = 1.0 - (1.0 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * x * x) * poly
            return cdf if x >= 0 else 1 - cdf

        dsr_prob = approx_cdf(test_stat)

    haircut = max(0, (1 - dsr_prob / max(0.01, 1.0)) * 100) if observed_sharpe > 0 else 100

    return {
        'dsr': round(dsr_prob, 4),
        'expected_max_sharpe': round(expected_max_sr, 4),
        'test_statistic': round(test_stat, 4),
        'se_sharpe': round(se_sr, 4),
        'haircut_pct': round(haircut, 1),
        'pass': dsr_prob > 0.95,
        'interpretation': (
            'STRONG — Strategy likely has genuine alpha (DSR > 95%)'
            if dsr_prob > 0.95 else
            'MARGINAL — Cannot rule out luck (DSR 50-95%)'
            if dsr_prob > 0.50 else
            'WEAK — Strategy likely benefited from multiple testing (DSR < 50%)'
        )
    }


def main():
    parser = argparse.ArgumentParser(description='GOLDMINE_CURSOR — Deflated Sharpe Ratio Calculator')
    parser.add_argument('--sharpe', type=float, help='Observed Sharpe ratio')
    parser.add_argument('--strategies', type=int, default=50, help='Number of strategies tested (default: 50)')
    parser.add_argument('--trades', type=int, help='Number of trades / return observations')
    parser.add_argument('--skewness', type=float, default=0, help='Return skewness (default: 0)')
    parser.add_argument('--kurtosis', type=float, default=3, help='Return kurtosis (default: 3)')
    parser.add_argument('--demo', action='store_true', help='Run demo with sample data')

    args = parser.parse_args()

    if args.demo:
        print("=== GOLDMINE_CURSOR — Deflated Sharpe Ratio Demo ===\n")
        examples = [
            {'name': 'Strong Alpha (SR=2.5, 200 trades, 50 algos)', 'sr': 2.5, 'n': 50, 't': 200},
            {'name': 'Moderate (SR=1.2, 100 trades, 50 algos)', 'sr': 1.2, 'n': 50, 't': 100},
            {'name': 'Lucky (SR=1.0, 30 trades, 50 algos)', 'sr': 1.0, 'n': 50, 't': 30},
            {'name': 'Weak (SR=0.5, 50 trades, 50 algos)', 'sr': 0.5, 'n': 50, 't': 50},
            {'name': 'Few strategies (SR=1.2, 100 trades, 5 algos)', 'sr': 1.2, 'n': 5, 't': 100},
        ]
        for ex in examples:
            result = compute_dsr(ex['sr'], ex['n'], ex['t'])
            print(f"  {ex['name']}")
            print(f"    DSR: {result['dsr']:.4f}  |  Pass: {result['pass']}  |  {result['interpretation']}")
            print(f"    Expected Max SR from {ex['n']} random strategies: {result['expected_max_sharpe']:.4f}")
            print()
        return

    if args.sharpe is None or args.trades is None:
        parser.print_help()
        print("\nExample: python deflated_sharpe.py --sharpe 1.5 --trades 100 --strategies 50")
        sys.exit(1)

    result = compute_dsr(args.sharpe, args.strategies, args.trades, args.skewness, args.kurtosis)

    print("=== Deflated Sharpe Ratio Result ===")
    for k, v in result.items():
        print(f"  {k}: {v}")


if __name__ == '__main__':
    main()
