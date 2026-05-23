#!/usr/bin/env python3
"""
Portfolio Signal Classification System

Reads alpha_signals.json and classifies each signal into portfolio actions:
- BUY: High conviction (confidence >= 0.7, direction = long, risk_score <= 0.5)
- SELL: High conviction (confidence >= 0.7, direction = short, risk_score <= 0.5)
- HOLD: Moderate confidence (0.3 < confidence < 0.7)
- AVOID: Low confidence (confidence <= 0.3) or high risk (risk_score > 0.5)

CLI usage:
    python signal_classifier.py --input signals.json --dry-run
    python signal_classifier.py --input signals.json --output classified.json
    python signal_classifier.py --input signals.json  # in-place with backup
"""

import json
import sys
import os
import shutil
import argparse
from datetime import datetime, timezone


# ── Classification thresholds ────────────────────────────────────────

HIGH_CONFIDENCE_THRESHOLD = 0.7
LOW_CONFIDENCE_THRESHOLD = 0.3
HIGH_RISK_THRESHOLD = 0.5
HIGH_VOLATILITY_THRESHOLD = 0.8


def load_signals(filepath: str) -> dict:
    """Load alpha signals JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def classify_signal(signal: dict) -> dict:
    """
    Classify a single signal into a portfolio action.

    Rules (evaluated in order, first match wins):
      1. AVOID if confidence <= 0.3
      2. AVOID if risk_score > 0.5
      3. BUY  if direction == long,  confidence >= 0.7, risk_score <= 0.5
      4. SELL if direction == short, confidence >= 0.7, risk_score <= 0.5
      5. HOLD for everything else
    """
    confidence = signal.get('confidence', 0.0)
    risk_score = signal.get('risk_score', 1.0)
    direction = signal.get('direction', 'long')
    asset = signal.get('asset', 'UNKNOWN')
    timeframe = signal.get('timeframe', 'unknown')
    volatility = signal.get('volatility', 0.0)

    # Rule 1: Low confidence → AVOID
    if confidence <= LOW_CONFIDENCE_THRESHOLD:
        action = 'AVOID'
        reason = f'Low confidence ({confidence:.2f})'

    # Rule 2: High risk → AVOID
    elif risk_score > HIGH_RISK_THRESHOLD:
        action = 'AVOID'
        reason = f'High risk ({risk_score:.2f})'

    # Rule 3: High confidence long → BUY
    elif direction == 'long' and confidence >= HIGH_CONFIDENCE_THRESHOLD:
        action = 'BUY'
        reason = f'Strong long signal (conf={confidence:.2f})'

    # Rule 4: High confidence short → SELL
    elif direction == 'short' and confidence >= HIGH_CONFIDENCE_THRESHOLD:
        action = 'SELL'
        reason = f'Strong short signal (conf={confidence:.2f})'

    # Rule 5: Everything else → HOLD
    else:
        action = 'HOLD'
        reason = f'Moderate confidence ({confidence:.2f}), {direction}'

    # Boost reason with volatility warning if applicable
    if volatility > HIGH_VOLATILITY_THRESHOLD and action in ('BUY', 'SELL'):
        reason += f' [WARNING: high volatility ({volatility:.2f})]'

    # Compute position sizing recommendation
    if action == 'AVOID':
        position_size = 0.0
    elif action == 'HOLD':
        position_size = 0.0
    elif risk_score <= 0.2:
        position_size = min(confidence * 1.2, 1.0)
    else:
        position_size = max(0.1, confidence * (1.0 - risk_score))

    return {
        'action': action,
        'reason': reason,
        'position_size': round(min(position_size, 1.0), 3),
        'confidence': confidence,
        'risk_score': risk_score,
        'volatility': volatility,
    }


def classify_signals(signals_data: dict) -> dict:
    """Classify all signals in the signals data structure."""
    if isinstance(signals_data, dict) and 'signals' in signals_data:
        signals = signals_data['signals']
        metadata = {k: v for k, v in signals_data.items() if k != 'signals'}
    elif isinstance(signals_data, list):
        signals = signals_data
        metadata = {}
    else:
        raise ValueError("Invalid signals format: expected list or dict with 'signals' key")

    classified = []
    summary = {'BUY': 0, 'SELL': 0, 'HOLD': 0, 'AVOID': 0}

    for signal in signals:
        classification = classify_signal(signal)
        enriched = {**signal, **classification}
        classified.append(enriched)
        summary[classification['action']] += 1

    result = {
        **metadata,
        'classified_at': datetime.now(timezone.utc).isoformat(),
        'summary': summary,
        'total_signals': len(classified),
        'signals': classified,
    }
    return result


def backup_file(filepath: str) -> str:
    """Create timestamped backup of a file."""
    backup_path = f"{filepath}.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(filepath, backup_path)
    return backup_path


def print_dry_run(classified: dict) -> None:
    """Print a human-readable dry-run summary."""
    summary = classified.get('summary', {})
    total = classified.get('total_signals', 0)

    print("=" * 60)
    print("SIGNAL CLASSIFICATION — DRY RUN")
    print("=" * 60)
    print(f"Total signals: {total}")
    print(f"  BUY:   {summary.get('BUY', 0)}")
    print(f"  SELL:  {summary.get('SELL', 0)}")
    print(f"  HOLD:  {summary.get('HOLD', 0)}")
    print(f"  AVOID: {summary.get('AVOID', 0)}")
    print("-" * 60)

    for sig in classified.get('signals', []):
        asset = sig.get('asset', '?')
        action = sig.get('action', '?')
        reason = sig.get('reason', '')
        conf = sig.get('confidence', 0)
        risk = sig.get('risk_score', 0)
        pos = sig.get('position_size', 0)
        print(f"  {action:5s} | {asset:8s} | conf={conf:.2f} risk={risk:.2f} "
              f"pos={pos:.1%} | {reason}")

    print("=" * 60)
    print("(Dry run — no files modified)")


def main():
    parser = argparse.ArgumentParser(
        description='Classify alpha signals into portfolio actions')
    parser.add_argument('--input', '-i', required=True,
                        help='Path to alpha_signals.json')
    parser.add_argument('--output', '-o',
                        help='Output path (default: overwrite input with backup)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print classification without modifying files')
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    signals_data = load_signals(args.input)
    classified = classify_signals(signals_data)

    if args.dry_run:
        print_dry_run(classified)
    else:
        output_path = args.output or args.input
        if not args.output and os.path.exists(args.input):
            backup = backup_file(args.input)
            print(f"Backup created: {backup}")

        with open(output_path, 'w') as f:
            json.dump(classified, f, indent=2)
        print(f"Classified signals written to: {output_path}")


if __name__ == '__main__':
    main()
