#!/usr/bin/env python3
"""
Test script for signal_classifier.py

Uses public/alpha_signals_sample.json with --dry-run to verify classification.
"""

import json
import os
import sys
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
SAMPLE_FILE = os.path.join(PROJECT_ROOT, 'public', 'alpha_signals_sample.json')
CLASSIFIER = os.path.join(PROJECT_ROOT, 'scripts', 'signal_classifier.py')


def main():
    if not os.path.exists(SAMPLE_FILE):
        print(f"Sample file not found: {SAMPLE_FILE}", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(CLASSIFIER):
        print(f"Classifier script not found: {CLASSIFIER}", file=sys.stderr)
        sys.exit(1)

    print("Running signal_classifier.py --dry-run ...")
    result = subprocess.run(
        ['python3', CLASSIFIER, '--input', SAMPLE_FILE, '--dry-run'],
        capture_output=True, text=True
    )

    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)

    if result.returncode != 0:
        print(f"FAILED: exit code {result.returncode}")
        sys.exit(1)

    # Also verify programmatic classification
    from signal_classifier import classify_signals, load_signals
    data = load_signals(SAMPLE_FILE)
    classified = classify_signals(data)
    summary = classified.get('summary', {})

    assert classified['total_signals'] > 0, "No signals classified"
    assert sum(summary.values()) == classified['total_signals'], "Summary count mismatch"
    for action in ('BUY', 'SELL', 'HOLD', 'AVOID'):
        assert action in summary, f"Missing action: {action}"

    # Verify each signal has required fields
    for sig in classified['signals']:
        for field in ('action', 'reason', 'position_size', 'confidence', 'risk_score'):
            assert field in sig, f"Missing field {field} in signal {sig.get('asset', '?')}"

    print("\n✓ All assertions passed")
    print(f"  Total signals: {classified['total_signals']}")
    print(f"  Summary: {summary}")


if __name__ == '__main__':
    main()
