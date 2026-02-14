#!/usr/bin/env python3
"""
CUSUM Change-Point Detector — Statistically rigorous alpha decay detection.

Replaces the simple "consecutive losses" check with CUSUM/PELT change-point detection:
  - Detects structural breaks in algorithm PnL series
  - Catches decay days earlier than rolling averages
  - Identifies exact point where strategy started failing
  - Triggers automatic weight reduction or pause

Science: Page (1954) CUSUM, Killick et al. (2012) PELT algorithm
Library: ruptures (https://centre-borelli.github.io/ruptures-docs/)

Pipeline:
  1. Fetch trade history per algorithm from live_trade.php
  2. Run PELT change-point detection on PnL series
  3. Classify last segment: healthy / warning / decayed
  4. Post decay alerts to world_class_intelligence.php

Requires: pip install ruptures numpy requests
Runs via: python run_all.py --cusum
"""
import sys
import os
import json
import logging
import numpy as np
import warnings
from datetime import datetime

warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import post_to_api, post_to_bridge, call_api
from config import API_BASE, ADMIN_KEY

logger = logging.getLogger('cusum_detector')

try:
    import ruptures as rpt
    RUPTURES_AVAILABLE = True
except ImportError:
    RUPTURES_AVAILABLE = False
    logger.warning("ruptures not installed: pip install ruptures")


# ---------------------------------------------------------------------------
# Change-Point Detection
# ---------------------------------------------------------------------------

def detect_change_points(pnl_series, min_size=8, penalty=1.5):
    """
    Detect structural change points in a PnL series using PELT algorithm.

    Args:
        pnl_series: list/array of realized PnL percentages per trade
        min_size: minimum segment length (prevents overfitting on tiny segments)
        penalty: higher = fewer change points (less sensitive), lower = more

    Returns: {
        'change_points': list of indices where regime changed,
        'n_segments': int,
        'segments': list of {'start', 'end', 'mean', 'std', 'sharpe', 'n_trades'}
    }
    """
    signal = np.array(pnl_series, dtype=float)

    if len(signal) < min_size * 2:
        # Not enough data for meaningful detection
        return {
            'change_points': [],
            'n_segments': 1,
            'segments': [_segment_stats(signal, 0, len(signal))]
        }

    if RUPTURES_AVAILABLE:
        # PELT with RBF kernel — best for financial data (handles non-Gaussian)
        algo = rpt.Pelt(model="rbf", min_size=min_size).fit(signal)
        change_points = algo.predict(pen=penalty)
    else:
        # Fallback: simple CUSUM without ruptures
        change_points = _cusum_fallback(signal, threshold=2.0)

    # Build segment statistics
    segments = []
    prev = 0
    for cp in change_points:
        if cp > prev:
            segments.append(_segment_stats(signal, prev, cp))
        prev = cp

    return {
        'change_points': [int(cp) for cp in change_points],
        'n_segments': len(segments),
        'segments': segments
    }


def _segment_stats(signal, start, end):
    """Compute statistics for a segment of the PnL series."""
    seg = signal[start:end]
    if len(seg) == 0:
        return {'start': start, 'end': end, 'mean': 0, 'std': 0,
                'sharpe': 0, 'n_trades': 0, 'win_rate': 0}

    mean = float(np.mean(seg))
    std = float(np.std(seg, ddof=1)) if len(seg) > 1 else 0.001
    sharpe = (mean / std) * np.sqrt(252) if std > 0.0001 else 0
    win_rate = float(np.sum(seg > 0)) / len(seg)

    return {
        'start': int(start),
        'end': int(end),
        'mean': round(mean, 6),
        'std': round(std, 6),
        'sharpe': round(sharpe, 4),
        'n_trades': int(len(seg)),
        'win_rate': round(win_rate, 4),
        'total_pnl': round(float(np.sum(seg)), 4)
    }


def _cusum_fallback(signal, threshold=2.0):
    """Simple CUSUM change-point detection without ruptures library."""
    n = len(signal)
    mean = np.mean(signal)
    std = np.std(signal, ddof=1)
    if std < 0.0001:
        return [n]

    # Cumulative sum of deviations from mean
    cusum_pos = np.zeros(n)
    cusum_neg = np.zeros(n)
    change_points = []

    for i in range(1, n):
        cusum_pos[i] = max(0, cusum_pos[i-1] + (signal[i] - mean) / std)
        cusum_neg[i] = max(0, cusum_neg[i-1] - (signal[i] - mean) / std)

        if cusum_pos[i] > threshold or cusum_neg[i] > threshold:
            change_points.append(i)
            cusum_pos[i] = 0
            cusum_neg[i] = 0

    change_points.append(n)
    return change_points


# ---------------------------------------------------------------------------
# Decay Classification
# ---------------------------------------------------------------------------

def classify_decay(detection_result):
    """
    Classify algorithm health based on change-point analysis.

    Returns: {
        'status': 'strong' | 'healthy' | 'warning' | 'decayed' | 'dead',
        'recommended_weight': float (0.0 to 1.5),
        'reason': str,
        'last_segment': dict
    }
    """
    segments = detection_result.get('segments', [])
    if not segments:
        return {
            'status': 'unknown',
            'recommended_weight': 0.5,
            'reason': 'No data',
            'last_segment': {}
        }

    last = segments[-1]
    last_sharpe = last.get('sharpe', 0)
    last_wr = last.get('win_rate', 0.5)
    last_mean = last.get('mean', 0)
    n_trades = last.get('n_trades', 0)

    # Compare last segment to previous segments
    if len(segments) >= 2:
        prev = segments[-2]
        sharpe_change = last_sharpe - prev.get('sharpe', 0)
        wr_change = last_wr - prev.get('win_rate', 0.5)
    else:
        sharpe_change = 0
        wr_change = 0

    # Classification logic
    if last_sharpe > 1.5 and last_wr > 0.55:
        status = 'strong'
        weight = min(1.5, 1.0 + (last_sharpe - 1.5) * 0.1)
        reason = f"Strong performance: Sharpe={last_sharpe:.2f}, WR={last_wr:.0%}"

    elif last_sharpe > 0.5 and last_wr > 0.45:
        status = 'healthy'
        weight = 1.0
        reason = f"Healthy: Sharpe={last_sharpe:.2f}, WR={last_wr:.0%}"

    elif last_sharpe > 0 and last_mean > 0:
        status = 'warning'
        weight = 0.6
        reason = f"Warning: Sharpe declining to {last_sharpe:.2f}"
        if sharpe_change < -1.0:
            reason += f" (dropped {abs(sharpe_change):.1f} from previous segment)"

    elif last_sharpe > -0.5:
        status = 'decayed'
        weight = 0.3
        reason = f"Decayed: Sharpe={last_sharpe:.2f}, WR={last_wr:.0%}"

    else:
        status = 'dead'
        weight = 0.0
        reason = f"Dead: Sharpe={last_sharpe:.2f}, losing money consistently"

    # Insufficient data penalty
    if n_trades < 15:
        weight *= 0.8
        reason += f" (low confidence: only {n_trades} trades in segment)"

    return {
        'status': status,
        'recommended_weight': round(max(0.0, min(1.5, weight)), 3),
        'reason': reason,
        'last_segment': last,
        'sharpe_change': round(sharpe_change, 4),
        'wr_change': round(wr_change, 4)
    }


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------

def run_cusum_detection():
    """
    Fetch trade history, run CUSUM on each algorithm, post results.
    """
    logger.info("=" * 60)
    logger.info("CUSUM CHANGE-POINT DETECTOR — Starting")
    logger.info("  Library: %s", "ruptures (PELT)" if RUPTURES_AVAILABLE else "fallback CUSUM")
    logger.info("=" * 60)

    # Fetch trade history
    result = call_api('history', 'limit=5000')
    if not result.get('ok'):
        logger.error("Cannot fetch trade history: %s", result.get('error'))
        return []

    trades = result.get('trades', [])
    if len(trades) < 20:
        logger.warning("Insufficient trade history (%d trades, need 20+)", len(trades))
        return []

    logger.info("Fetched %d closed trades", len(trades))

    # Group trades by algorithm
    algo_trades = {}
    for trade in trades:
        algo = trade.get('algorithm_name', 'Unknown')
        pnl = trade.get('realized_pct', 0)
        try:
            pnl = float(pnl)
        except (ValueError, TypeError):
            continue
        if algo not in algo_trades:
            algo_trades[algo] = []
        algo_trades[algo].append(pnl)

    # Run detection per algorithm
    health_results = []

    for algo_name, pnl_series in sorted(algo_trades.items()):
        if len(pnl_series) < 10:
            logger.info("  %-25s SKIP (only %d trades)", algo_name, len(pnl_series))
            continue

        # Detect change points
        detection = detect_change_points(pnl_series)

        # Classify decay
        classification = classify_decay(detection)

        health = {
            'algorithm_name': algo_name,
            'total_trades': len(pnl_series),
            'change_points_detected': len(detection['change_points']),
            'n_segments': detection['n_segments'],
            'decay_status': classification['status'],
            'recommended_weight': classification['recommended_weight'],
            'reason': classification['reason'],
            'last_segment_sharpe': classification['last_segment'].get('sharpe', 0),
            'last_segment_wr': classification['last_segment'].get('win_rate', 0),
            'last_segment_trades': classification['last_segment'].get('n_trades', 0),
            'detected_at': datetime.utcnow().isoformat()
        }

        health_results.append(health)

        # Log with status emoji
        emoji = {
            'strong': '+', 'healthy': '=', 'warning': '!',
            'decayed': 'X', 'dead': 'XX', 'unknown': '?'
        }
        logger.info("  [%2s] %-25s weight=%.2f sharpe=%.2f wr=%.0f%% (%d trades, %d segments)",
                     emoji.get(classification['status'], '?'),
                     algo_name,
                     classification['recommended_weight'],
                     classification['last_segment'].get('sharpe', 0),
                     classification['last_segment'].get('win_rate', 0) * 100,
                     len(pnl_series),
                     detection['n_segments'])

    # Post to API
    if health_results:
        api_result = post_to_api('ingest_regime', {
            'source': 'cusum_detector',
            'algo_health': health_results,
            'computed_at': datetime.utcnow().isoformat(),
            'method': 'PELT' if RUPTURES_AVAILABLE else 'CUSUM_fallback',
            'total_algorithms': len(health_results)
        })

        if api_result.get('ok'):
            logger.info("CUSUM results posted to API")
        else:
            logger.warning("API post error: %s", api_result.get('error', 'unknown'))

    # Post to bridge dashboard
    if health_results:
        healthy = sum(1 for h in health_results if h['decay_status'] in ('strong', 'healthy'))
        summary = "%d algos: %d healthy, %d warning/decayed" % (
            len(health_results), healthy, len(health_results) - healthy)
        post_to_bridge('cusum_detector', {'algo_health': health_results}, summary)

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("CUSUM DETECTION SUMMARY")
    logger.info("  Algorithms analyzed: %d", len(health_results))

    for status in ['strong', 'healthy', 'warning', 'decayed', 'dead']:
        count = sum(1 for h in health_results if h['decay_status'] == status)
        if count > 0:
            names = [h['algorithm_name'] for h in health_results if h['decay_status'] == status]
            logger.info("  %s (%d): %s", status.upper(), count, ', '.join(names))

    logger.info("=" * 60)

    return health_results


def main():
    return run_cusum_detection()


if __name__ == '__main__':
    main()
