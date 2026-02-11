#!/usr/bin/env python3
"""
Signal Bundle Consolidation — Merge 23 algos into 5 orthogonal meta-bundles.

The "best" isn't 100 algos — it's 5 orthogonal signal bundles:
  1. Momentum Bundle: Breakout, ADX, Vol Spike, VAM, Alpha Predator
  2. Reversion Bundle: RSI, Bollinger, Mean Reversion Sniper, StochRSI, RSI(2)
  3. Fundamental Bundle: Insider Cluster, 13F, Earnings, Smart Money consensus
  4. Sentiment Bundle: Sentiment Divergence, Contrarian F&G, WSB, News
  5. ML Alpha Bundle: WorldQuant 101, Cross-Asset Spillover

Why consolidate:
  - RSI appears in 5+ algos = 5x correlated noise, not 5x alpha
  - Overlapping signals inflate confidence without adding information
  - Orthogonal bundles = true diversification of alpha sources

This script:
  1. Fetches recent signals from all 23 algos
  2. Computes correlation matrix between algo signals
  3. Groups into bundles (confirming/adjusting manual grouping)
  4. Calculates bundle-level signal (weighted consensus within bundle)
  5. Reports overlap statistics and bundle correlations
  6. Posts bundle assignments to PHP API

Requires: pip install numpy pandas scipy requests
"""
import sys
import os
import json
import logging
import numpy as np
import pandas as pd
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import post_to_api, call_api
from config import TRACKED_TICKERS

logger = logging.getLogger('signal_bundles')


# ---------------------------------------------------------------------------
# Bundle Definitions (manual grouping based on signal analysis)
# ---------------------------------------------------------------------------

BUNDLE_ASSIGNMENTS = {
    # MOMENTUM BUNDLE — trend-following, breakout, directional
    'momentum': {
        'algos': [
            'Momentum Burst',       # #1: candle velocity
            'Breakout 24h',         # #3: support/resistance break
            'Volatility Breakout',  # #8: ATR spike + direction
            'Trend Sniper',         # #9: 6-indicator confluence
            'Volume Spike',         # #11: whale detection
            'VAM',                  # #12: volatility-adjusted momentum
            'ADX Trend Strength',   # #14: trend power
            'Alpha Predator',       # #19: 4-factor alignment
        ],
        'weight_method': 'strength_weighted',  # Weight by signal_strength
        'regime_gate': 'trending',  # Best in trending Hurst regime
    },

    # REVERSION BUNDLE — mean-reversion, oscillator extremes
    'reversion': {
        'algos': [
            'RSI Reversal',         # #2: RSI(14) extremes
            'DCA Dip',              # #4: dip buying
            'Bollinger Squeeze',    # #5: bandwidth squeeze
            'MACD Crossover',       # #6: signal line cross
            'Dip Recovery',         # #10: multi-candle reversal
            'Mean Reversion Sniper',# #13: Bollinger+RSI+MACD convergence
            'StochRSI Crossover',   # #15: oscillator extremes
            'Awesome Oscillator',   # #16: AO zero-line (DEMOTE — low edge)
            'RSI(2) Scalp',         # #17: ultra-short MR
            'Ichimoku Cloud',       # #18: Japanese system (DEMOTE — lags)
        ],
        'weight_method': 'equal',   # Equal weight (many overlapping signals)
        'regime_gate': 'mean_reverting',  # Best in MR Hurst regime
    },

    # FUNDAMENTAL BUNDLE — smart money, insider, institutional
    'fundamental': {
        'algos': [
            'Insider Cluster Buy',  # #20: Form 4 cluster
            '13F New Position',     # #21: hedge fund opening
            'Challenger Bot',       # Smart money consensus
        ],
        'weight_method': 'conviction_weighted',  # Weight by conviction score
        'regime_gate': 'all',  # Always active (low frequency, high edge)
    },

    # SENTIMENT BUNDLE — crowd, news, social
    'sentiment': {
        'algos': [
            'Sentiment Divergence', # #22: news vs price
            'Contrarian F&G',       # #23: fear/greed extremes
        ],
        'weight_method': 'equal',
        'regime_gate': 'all',  # Always active as overlay
    },

    # ML ALPHA BUNDLE — quantitative, orthogonal to technicals
    'ml_alpha': {
        'algos': [
            'Consensus',            # #7: meta-signal (2+ algos agree)
            # WorldQuant alphas added dynamically
            # Cross-asset spillover added dynamically
        ],
        'weight_method': 'equal',
        'regime_gate': 'all',
    },
}

# Algo to bundle lookup
ALGO_TO_BUNDLE = {}
for bundle, config in BUNDLE_ASSIGNMENTS.items():
    for algo in config['algos']:
        ALGO_TO_BUNDLE[algo] = bundle

# Demoted algos (lower weight within their bundle)
DEMOTED_ALGOS = {
    'Awesome Oscillator': 0.5,  # Low edge, Williams method outdated
    'Ichimoku Cloud': 0.5,      # Lagging indicator
    'RSI(2) Scalp': 0.7,        # Very short horizon, noisy
    'DCA Dip': 0.6,             # Simple, often catches falling knives
}


# ---------------------------------------------------------------------------
# Signal Correlation Analysis
# ---------------------------------------------------------------------------

def compute_signal_correlations(signals_df):
    """
    Compute pairwise correlation between algorithm signals.
    Identifies redundant pairs (>0.6 correlation).
    """
    if signals_df.empty:
        return None, []

    # Pivot: rows = (date, symbol), columns = algorithm, values = signal_strength
    pivot = signals_df.pivot_table(
        index=['signal_date', 'symbol'],
        columns='algorithm_name',
        values='signal_strength',
        aggfunc='first'
    ).fillna(0)

    if pivot.shape[1] < 2:
        return None, []

    corr_matrix = pivot.corr()

    # Find redundant pairs
    redundant = []
    for i in range(len(corr_matrix)):
        for j in range(i + 1, len(corr_matrix)):
            r = corr_matrix.iloc[i, j]
            if abs(r) > 0.6:
                redundant.append({
                    'algo_1': corr_matrix.index[i],
                    'algo_2': corr_matrix.columns[j],
                    'correlation': round(float(r), 3),
                    'action': 'MERGE' if abs(r) > 0.8 else 'REVIEW'
                })

    redundant.sort(key=lambda x: abs(x['correlation']), reverse=True)
    return corr_matrix, redundant


# ---------------------------------------------------------------------------
# Bundle Signal Aggregation
# ---------------------------------------------------------------------------

def aggregate_bundle_signal(bundle_name, bundle_signals, weight_method='equal'):
    """
    Aggregate individual algo signals within a bundle into a single signal.

    Methods:
      - equal: Simple average of signal strengths
      - strength_weighted: Weight by individual signal strength
      - conviction_weighted: Weight by conviction score (for fundamentals)
    """
    if not bundle_signals:
        return None

    directions = []
    strengths = []
    weights = []

    for sig in bundle_signals:
        direction = 1 if sig.get('signal_type', 'BUY') in ('BUY', 'STRONG_BUY', 'LONG') else -1
        strength = float(sig.get('signal_strength', 50))
        algo_name = sig.get('algorithm_name', '')

        # Apply demotion
        demotion = DEMOTED_ALGOS.get(algo_name, 1.0)
        strength *= demotion

        directions.append(direction)
        strengths.append(strength)

        if weight_method == 'strength_weighted':
            weights.append(strength)
        elif weight_method == 'conviction_weighted':
            weights.append(float(sig.get('conviction_score', strength)))
        else:
            weights.append(1.0)

    weights = np.array(weights)
    if weights.sum() == 0:
        weights = np.ones(len(weights))
    weights = weights / weights.sum()

    # Weighted direction
    weighted_dir = np.average(directions, weights=weights)

    # Weighted strength
    weighted_strength = np.average(strengths, weights=weights)

    # Agreement ratio (what fraction of signals agree on direction)
    majority_dir = 1 if weighted_dir > 0 else -1
    agreement = sum(1 for d in directions if d == majority_dir) / len(directions)

    # Bundle signal
    signal_type = 'BUY' if weighted_dir > 0 else 'SHORT'
    confidence = weighted_strength * agreement  # Scale by agreement

    return {
        'bundle': bundle_name,
        'signal_type': signal_type,
        'strength': round(confidence, 1),
        'agreement': round(agreement, 2),
        'algo_count': len(bundle_signals),
        'weighted_direction': round(weighted_dir, 3),
        'contributing_algos': [s.get('algorithm_name', '?') for s in bundle_signals]
    }


# ---------------------------------------------------------------------------
# De-duplication Report
# ---------------------------------------------------------------------------

def generate_dedup_report(signals_df, corr_matrix, redundant_pairs):
    """
    Generate a report on signal redundancy and recommendations.
    """
    report = {
        'total_algos': 0,
        'redundant_pairs': len(redundant_pairs),
        'highly_redundant': sum(1 for r in redundant_pairs if abs(r['correlation']) > 0.8),
        'bundle_stats': {},
        'recommendations': []
    }

    if corr_matrix is not None:
        report['total_algos'] = len(corr_matrix)

    # Bundle statistics
    for bundle_name, config in BUNDLE_ASSIGNMENTS.items():
        algo_list = config['algos']
        in_data = [a for a in algo_list if a in (signals_df['algorithm_name'].unique() if not signals_df.empty else [])]

        report['bundle_stats'][bundle_name] = {
            'defined_algos': len(algo_list),
            'active_algos': len(in_data),
            'algos': algo_list
        }

    # Recommendations based on redundancy
    for pair in redundant_pairs[:10]:
        if pair['correlation'] > 0.8:
            report['recommendations'].append(
                "MERGE: %s and %s (r=%.2f) — keep the one with higher Sharpe" %
                (pair['algo_1'], pair['algo_2'], pair['correlation'])
            )
        else:
            report['recommendations'].append(
                "REVIEW: %s and %s (r=%.2f) — consider reducing weight of one" %
                (pair['algo_1'], pair['algo_2'], pair['correlation'])
            )

    return report


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------

def run_bundle_analysis():
    """
    Full bundle consolidation pipeline:
    1. Fetch recent signals
    2. Compute correlations
    3. Aggregate into bundles
    4. Generate de-dup report
    5. Post results
    """
    logger.info("=" * 60)
    logger.info("SIGNAL BUNDLE CONSOLIDATION — Starting")
    logger.info("=" * 60)

    # Fetch recent signals (last 30 days)
    result = call_api('signals', 'days=30&limit=5000')
    signals = result.get('signals', []) if result.get('ok') else []

    if not signals:
        logger.warning("No signals data available. Using bundle definitions only.")
        signals_df = pd.DataFrame()
    else:
        signals_df = pd.DataFrame(signals)
        if 'signal_time' in signals_df.columns:
            signals_df['signal_date'] = pd.to_datetime(signals_df['signal_time']).dt.date
        logger.info("Loaded %d signals", len(signals_df))

    # Step 1: Correlation analysis
    logger.info("Computing signal correlations...")
    corr_matrix, redundant_pairs = compute_signal_correlations(signals_df)

    if redundant_pairs:
        logger.info("Found %d redundant pairs:", len(redundant_pairs))
        for pair in redundant_pairs[:10]:
            logger.info("  %s <-> %s: r=%.3f (%s)",
                         pair['algo_1'], pair['algo_2'],
                         pair['correlation'], pair['action'])

    # Step 2: Aggregate into bundles
    logger.info("Aggregating into %d bundles...", len(BUNDLE_ASSIGNMENTS))
    bundle_signals_map = defaultdict(list)

    if not signals_df.empty:
        for _, sig in signals_df.iterrows():
            algo = sig.get('algorithm_name', '')
            bundle = ALGO_TO_BUNDLE.get(algo, 'ml_alpha')  # Default to ml_alpha
            bundle_signals_map[bundle].append(sig.to_dict())

    bundle_results = {}
    for bundle_name, config in BUNDLE_ASSIGNMENTS.items():
        bundle_sigs = bundle_signals_map.get(bundle_name, [])
        if bundle_sigs:
            agg = aggregate_bundle_signal(
                bundle_name, bundle_sigs, config['weight_method']
            )
            bundle_results[bundle_name] = agg
            logger.info("  %-14s: %s strength=%.0f agreement=%.0f%% (%d algos)",
                         bundle_name,
                         agg['signal_type'],
                         agg['strength'],
                         agg['agreement'] * 100,
                         agg['algo_count'])
        else:
            bundle_results[bundle_name] = {
                'bundle': bundle_name,
                'signal_type': 'NEUTRAL',
                'strength': 0,
                'agreement': 0,
                'algo_count': 0,
                'contributing_algos': []
            }
            logger.info("  %-14s: NO SIGNALS", bundle_name)

    # Step 3: De-dup report
    dedup_report = generate_dedup_report(signals_df, corr_matrix, redundant_pairs)

    # Step 4: Bundle correlation (between bundles, not within)
    bundle_corr = {}
    if corr_matrix is not None:
        for b1 in BUNDLE_ASSIGNMENTS:
            for b2 in BUNDLE_ASSIGNMENTS:
                if b1 >= b2:
                    continue
                algos_1 = [a for a in BUNDLE_ASSIGNMENTS[b1]['algos'] if a in corr_matrix.columns]
                algos_2 = [a for a in BUNDLE_ASSIGNMENTS[b2]['algos'] if a in corr_matrix.columns]

                if algos_1 and algos_2:
                    cross_corrs = corr_matrix.loc[algos_1, algos_2].values.flatten()
                    avg_corr = float(np.nanmean(cross_corrs))
                    bundle_corr[f"{b1}_vs_{b2}"] = round(avg_corr, 3)

    # Compile output
    output = {
        'bundles': bundle_results,
        'bundle_assignments': {k: v['algos'] for k, v in BUNDLE_ASSIGNMENTS.items()},
        'algo_to_bundle': ALGO_TO_BUNDLE,
        'demoted_algos': DEMOTED_ALGOS,
        'dedup_report': dedup_report,
        'bundle_correlations': bundle_corr,
        'signal_count': len(signals_df)
    }

    # Print summary
    logger.info("=" * 60)
    logger.info("BUNDLE CONSOLIDATION SUMMARY")
    logger.info("  Total algos: %d mapped to %d bundles", len(ALGO_TO_BUNDLE), len(BUNDLE_ASSIGNMENTS))
    logger.info("  Redundant pairs: %d (highly redundant: %d)",
                 dedup_report['redundant_pairs'], dedup_report['highly_redundant'])
    if bundle_corr:
        logger.info("  Bundle cross-correlations:")
        for pair, corr in sorted(bundle_corr.items(), key=lambda x: abs(x[1]), reverse=True):
            status = "OK" if abs(corr) < 0.3 else "HIGH"
            logger.info("    %-30s r=%.3f [%s]", pair, corr, status)
    for rec in dedup_report.get('recommendations', [])[:5]:
        logger.info("  REC: %s", rec)
    logger.info("=" * 60)

    # Post to API
    post_result = post_to_api('update_bundles', output)
    if post_result.get('ok'):
        logger.info("Bundle data saved")
    else:
        logger.warning("API post: %s", post_result.get('error', 'unknown'))

    # Print JSON
    print("\n--- BUNDLE JSON OUTPUT ---")
    print(json.dumps(output, indent=2, default=str))

    return output


if __name__ == '__main__':
    run_bundle_analysis()
