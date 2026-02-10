#!/usr/bin/env python3
"""
GOLDMINE_CURSOR — Algorithm Correlation Matrix

Measures how independent the 50+ algorithms truly are.
If 10 algorithms all pick the same stocks, "consensus" is illusory.

Metrics:
  1. Ticker Overlap % — What fraction of picks are identical tickers?
  2. Return Correlation — Pearson correlation of per-trade returns
  3. Directional Agreement — How often do they agree on direction?

A truly diversified ensemble has low correlation (< 0.3) between algos.
High correlation (> 0.7) means the algos are essentially clones.

Usage:
  python algo_correlation.py --demo
"""

import argparse
import json
import math
import sys


def compute_overlap(picks_a, picks_b):
    """
    Compute ticker overlap between two algorithms' pick lists.

    Parameters:
        picks_a: list of ticker strings
        picks_b: list of ticker strings

    Returns: overlap percentage (0-100)
    """
    if not picks_a or not picks_b:
        return 0

    set_a = set(picks_a)
    set_b = set(picks_b)
    intersection = set_a & set_b
    union = set_a | set_b

    if not union:
        return 0

    return round(len(intersection) / len(union) * 100, 2)


def pearson_correlation(returns_a, returns_b):
    """
    Compute Pearson correlation between two return series.

    Returns: correlation coefficient (-1 to +1), or None if insufficient data
    """
    n = min(len(returns_a), len(returns_b))
    if n < 3:
        return None

    a = returns_a[:n]
    b = returns_b[:n]

    mean_a = sum(a) / n
    mean_b = sum(b) / n

    cov = sum((a[i] - mean_a) * (b[i] - mean_b) for i in range(n)) / n
    std_a = math.sqrt(sum((x - mean_a) ** 2 for x in a) / n)
    std_b = math.sqrt(sum((x - mean_b) ** 2 for x in b) / n)

    if std_a == 0 or std_b == 0:
        return None

    return round(cov / (std_a * std_b), 4)


def build_correlation_matrix(algo_data):
    """
    Build a full correlation matrix from algorithm data.

    Parameters:
        algo_data: dict of { algo_name: { 'tickers': [...], 'returns': [...] } }

    Returns:
        list of { algo_a, algo_b, ticker_overlap, return_correlation, assessment }
    """
    names = sorted(algo_data.keys())
    matrix = []

    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a = names[i]
            b = names[j]

            overlap = compute_overlap(
                algo_data[a].get('tickers', []),
                algo_data[b].get('tickers', [])
            )

            corr = pearson_correlation(
                algo_data[a].get('returns', []),
                algo_data[b].get('returns', [])
            )

            # Assessment
            assessment = 'independent'
            if overlap > 70 or (corr is not None and corr > 0.7):
                assessment = 'clone'
            elif overlap > 40 or (corr is not None and corr > 0.4):
                assessment = 'similar'
            elif overlap > 20 or (corr is not None and corr > 0.2):
                assessment = 'moderate'

            matrix.append({
                'algo_a': a,
                'algo_b': b,
                'ticker_overlap_pct': overlap,
                'return_correlation': corr,
                'assessment': assessment
            })

    return matrix


def demo():
    """Run demo with synthetic algorithm data."""
    print("=== GOLDMINE_CURSOR — Algorithm Correlation Matrix Demo ===\n")

    # Simulate 5 algorithms with varying overlap
    algo_data = {
        'Blue Chip Growth': {
            'tickers': ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'JPM'],
            'returns': [2.1, -0.5, 3.8, 1.2, -1.1, 2.5, 0.8]
        },
        'Technical Momentum': {
            'tickers': ['NVDA', 'TSLA', 'AMD', 'SMCI', 'PLTR', 'AAPL', 'COIN'],
            'returns': [4.2, -2.1, 5.5, -3.2, 6.1, 1.8, -1.5]
        },
        'CAN SLIM': {
            'tickers': ['AAPL', 'NVDA', 'MSFT', 'GOOGL', 'META', 'AMZN', 'LLY'],
            'returns': [1.9, 3.5, -0.3, 1.0, 2.2, -0.8, 1.5]
        },
        'Penny Sniper': {
            'tickers': ['MULN', 'BBIG', 'SNDL', 'CLOV', 'SOFI', 'PLTR', 'OPEN'],
            'returns': [15.0, -8.0, -5.0, 22.0, 3.0, -12.0, -7.0]
        },
        'Sector Rotation': {
            'tickers': ['XLE', 'XLF', 'XLK', 'XLV', 'XLI', 'XLU', 'XLRE'],
            'returns': [1.2, 0.8, 2.1, -0.5, 1.5, -0.3, 0.2]
        }
    }

    matrix = build_correlation_matrix(algo_data)

    # Print results
    print("  {:25s} {:25s} {:>10s} {:>10s} {:>12s}".format(
        'Algorithm A', 'Algorithm B', 'Overlap%', 'Corr', 'Assessment'))
    print("  " + "-" * 85)

    for row in matrix:
        corr_str = "{:.4f}".format(row['return_correlation']) if row['return_correlation'] is not None else 'N/A'
        print("  {:25s} {:25s} {:>9.1f}% {:>10s} {:>12s}".format(
            row['algo_a'], row['algo_b'],
            row['ticker_overlap_pct'], corr_str, row['assessment'].upper()))

    # Summary
    clones = [r for r in matrix if r['assessment'] == 'clone']
    similar = [r for r in matrix if r['assessment'] == 'similar']
    print("\n  Summary:")
    print("    Total pairs: {}".format(len(matrix)))
    print("    Clones (>70% overlap): {}".format(len(clones)))
    print("    Similar (40-70%): {}".format(len(similar)))
    print("    Independent (<20%): {}".format(len([r for r in matrix if r['assessment'] == 'independent'])))

    if clones:
        print("\n    WARNING: These algorithm pairs are essentially clones:")
        for c in clones:
            print("      {} <-> {} ({}% overlap)".format(c['algo_a'], c['algo_b'], c['ticker_overlap_pct']))


def main():
    parser = argparse.ArgumentParser(description='GOLDMINE_CURSOR — Algorithm Correlation Matrix')
    parser.add_argument('--demo', action='store_true', help='Run demo with sample data')
    parser.add_argument('--json', action='store_true', help='Output as JSON')

    args = parser.parse_args()

    if args.demo:
        demo()
    else:
        parser.print_help()
        print("\nRun with --demo to see example output.")
        print("To use with live data, integrate via the harvest API which populates goldmine_cursor_correlation_matrix.")


if __name__ == '__main__':
    main()
