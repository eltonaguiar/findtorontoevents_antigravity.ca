#!/usr/bin/env python3
"""
Correlation Engine — Computes asset pair correlations from price series.

Reads price data (JSON or CSV) and computes Pearson correlation coefficients
for all asset pairs using a configurable sliding window.

Usage:
    python correlation_engine.py --input prices.json --dry-run
    python correlation_engine.py --input prices.csv --format csv --window 20
"""

import json
import sys
import os
import csv
import math
import argparse
from datetime import datetime, timezone


def pearson_correlation(x, y):
    """Compute Pearson correlation coefficient between two lists."""
    n = len(x)
    if n < 3:
        return 0.0

    mean_x = sum(x) / n
    mean_y = sum(y) / n

    cov = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    std_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x))
    std_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y))

    if std_x == 0 or std_y == 0:
        return 0.0

    return round(cov / (std_x * std_y), 6)


class CorrelationEngine:
    """Engine for computing asset correlations from price data."""

    def __init__(self, window=20, high_corr_threshold=0.7):
        self.window = window
        self.high_corr_threshold = high_corr_threshold

    def _get_regime(self, corr):
        """Classify correlation into regime."""
        abs_corr = abs(corr)
        if abs_corr >= 0.8:
            return 'strong_positive' if corr > 0 else 'strong_negative'
        elif abs_corr >= 0.5:
            return 'moderate_positive' if corr > 0 else 'moderate_negative'
        elif abs_corr >= 0.2:
            return 'weak_positive' if corr > 0 else 'weak_negative'
        else:
            return 'no_correlation'

    def _extract_price_series(self, data):
        """Extract per-asset price series from input data."""
        prices = data.get('prices', data.get('price_series', {}))
        if isinstance(prices, dict):
            return {k: [float(p) for p in v] for k, v in prices.items()}

        # If pairs are given directly, return None (use pair data as-is)
        return None

    def process(self, data):
        """
        Process price/correlation data and compute pair statistics.

        Accepts either:
        - Raw price series: {'assets': [...], 'prices': {asset: [values...]}}
        - Pre-computed pairs: {'pairs': [{asset_a, asset_b, correlation, ...}]}

        Returns dict with pair_count, regime labels, stats.
        """
        pairs_input = data.get('pairs', [])
        assets = data.get('assets', [])
        window = data.get('window', self.window)

        # Mode 1: Pre-computed pairs provided
        if pairs_input:
            regimes = {}
            high_corr_count = 0
            processed_pairs = []

            for pair in pairs_input:
                corr = pair.get('correlation', 0.0)
                regime = self._get_regime(corr)
                regimes[regime] = regimes.get(regime, 0) + 1

                if abs(corr) >= self.high_corr_threshold:
                    high_corr_count += 1

                processed_pairs.append({
                    **pair,
                    'regime': regime,
                })

            regime_labels = list(regimes.keys())

            return {
                'assets': assets,
                'pair_count': len(processed_pairs),
                'regime': regime_labels,
                'regime_counts': regimes,
                'pairs': processed_pairs,
                'stats': {
                    'total': len(processed_pairs),
                    'high_corr': high_corr_count,
                    'low_corr': len(processed_pairs) - high_corr_count,
                },
                'window': window,
                'generated_at': datetime.now(timezone.utc).isoformat(),
            }

        # Mode 2: Raw price series
        price_series = self._extract_price_series(data)
        if price_series is None:
            # No usable data
            return {
                'assets': assets,
                'pair_count': 0,
                'regime': [],
                'stats': {'total': 0, 'high_corr': 0, 'low_corr': 0},
                'window': window,
                'generated_at': datetime.now(timezone.utc).isoformat(),
            }

        asset_names = list(price_series.keys())
        pairs = []
        regimes = {}
        high_corr_count = 0

        for i in range(len(asset_names)):
            for j in range(i + 1, len(asset_names)):
                a, b = asset_names[i], asset_names[j]
                series_a = price_series[a][-window:]
                series_b = price_series[b][-window:]
                min_len = min(len(series_a), len(series_b))

                if min_len < 3:
                    continue

                corr = pearson_correlation(series_a[:min_len], series_b[:min_len])
                regime = self._get_regime(corr)
                regimes[regime] = regimes.get(regime, 0) + 1

                if abs(corr) >= self.high_corr_threshold:
                    high_corr_count += 1

                pairs.append({
                    'asset_a': a,
                    'asset_b': b,
                    'correlation': corr,
                    'regime': regime,
                    'window': min_len,
                })

        regime_labels = list(regimes.keys())

        return {
            'assets': asset_names,
            'pair_count': len(pairs),
            'regime': regime_labels,
            'regime_counts': regimes,
            'pairs': pairs,
            'stats': {
                'total': len(pairs),
                'high_corr': high_corr_count,
                'low_corr': len(pairs) - high_corr_count,
            },
            'window': window,
            'generated_at': datetime.now(timezone.utc).isoformat(),
        }


def load_json(filepath):
    with open(filepath, 'r') as f:
        return json.load(f)


def load_csv(filepath):
    """Load CSV and convert to price series dict."""
    series = {}
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            for key, val in row.items():
                if key not in series:
                    series[key] = []
                try:
                    series[key].append(float(val))
                except (ValueError, TypeError):
                    pass
    return {'assets': list(series.keys()), 'prices': series}


def main():
    parser = argparse.ArgumentParser(description='Compute asset correlations')
    parser.add_argument('--input', '-i', required=True,
                        help='Path to input file (JSON or CSV)')
    parser.add_argument('--format', choices=['json', 'csv'], default='json')
    parser.add_argument('--window', type=int, default=20,
                        help='Sliding window size (default: 20)')
    parser.add_argument('--output', '-o',
                        help='Output path for correlation matrix JSON')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print results without writing files')
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    if args.format == 'csv':
        data = load_csv(args.input)
    else:
        data = load_json(args.input)

    engine = CorrelationEngine(window=args.window)
    result = engine.process(data)

    if args.dry_run:
        print("=" * 55)
        print("CORRELATION ENGINE — DRY RUN")
        print("=" * 55)
        print(f"  Assets: {', '.join(result['assets'])}")
        print(f"  Pairs:  {result['pair_count']}")
        print(f"  Window: {result['window']}")
        print(f"  Regimes: {', '.join(result['regime'])}")
        print(f"  High corr: {result['stats']['high_corr']}")
        print("-" * 55)
        for pair in result['pairs'][:15]:
            print(f"  {pair['asset_a']:6s} <-> {pair['asset_b']:6s}  "
                  f"r={pair['correlation']:+.4f}  [{pair['regime']}]")
        print("=" * 55)
    else:
        output_path = args.output or 'corr_matrix.json'
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"Correlation matrix written to: {output_path}")


if __name__ == '__main__':
    main()
