#!/usr/bin/env python3
"""
Correlation pipeline integration test.

Runs correlation_engine.py and data_lag_monitor.py against public sample data
with --dry-run flag to verify the full pipeline works end-to-end.
"""

import json
import os
import sys
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
PUBLIC_DIR = os.path.join(PROJECT_ROOT, 'public')
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, 'scripts')

CORR_ENGINE = os.path.join(SCRIPTS_DIR, 'correlation_engine.py')
LAG_MONITOR = os.path.join(SCRIPTS_DIR, 'data_lag_monitor.py')
CORR_SAMPLE = os.path.join(PUBLIC_DIR, 'corr_matrix_sample.json')


def test_correlation_engine():
    """Test correlation engine with sample data."""
    print("=" * 60)
    print("TEST: correlation_engine.py --dry-run")
    print("=" * 60)

    if not os.path.exists(CORR_SAMPLE):
        print(f"FAIL: Sample file not found: {CORR_SAMPLE}")
        return False

    result = subprocess.run(
        ['python3', CORR_ENGINE, '--input', CORR_SAMPLE, '--dry-run'],
        capture_output=True, text=True
    )

    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)

    if result.returncode != 0:
        print(f"FAIL: Exit code {result.returncode}")
        return False

    # Programmatic verification
    sys.path.insert(0, SCRIPTS_DIR)
    from correlation_engine import CorrelationEngine

    engine = CorrelationEngine()
    with open(CORR_SAMPLE) as f:
        data = json.load(f)

    result_data = engine.process(data)
    assert result_data['pair_count'] > 0, "No pairs processed"
    assert len(result_data['regime']) > 0, "No regime labels"
    assert result_data['stats']['total'] > 0, "No stats computed"

    print(f"✓ Correlation engine: {result_data['pair_count']} pairs, "
          f"{result_data['stats']['high_corr']} high-corr pairs")
    return True


def test_data_lag_monitor():
    """Test data lag monitor with synthetic data."""
    print("=" * 60)
    print("TEST: data_lag_monitor.py")
    print("=" * 60)

    # Create synthetic feed data
    import tempfile
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    feeds = []
    for i in range(10):
        lag_minutes = i * 15  # 0, 15, 30, ... 135 minutes
        ts = now - timedelta(minutes=lag_minutes)
        feeds.append({
            'symbol': f'ASSET_{i}',
            'timestamp': ts.isoformat(),
            'price': 100 + i,
            'volume': 1000000 - i * 50000,
        })

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({'feeds': feeds, 'generated_at': now.isoformat()}, f)
        tmp_path = f.name

    result = subprocess.run(
        ['python3', LAG_MONITOR, '--input', tmp_path, '--dry-run'],
        capture_output=True, text=True
    )

    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)

    os.unlink(tmp_path)

    if result.returncode != 0:
        print(f"FAIL: Exit code {result.returncode}")
        return False

    # Programmatic check
    from data_lag_monitor import compute_lag_stats
    lag_data = {
        'feeds': feeds,
        'generated_at': now.isoformat(),
    }
    stats = compute_lag_stats(lag_data)
    assert stats['max_lag_minutes'] >= 135, f"Expected max lag >= 135, got {stats['max_lag_minutes']}"
    assert stats['stale_count'] > 0, "Expected some stale feeds"
    assert len(stats['flagged']) > 0, "Expected some flagged feeds"

    print(f"✓ Data lag monitor: max_lag={stats['max_lag_minutes']}min, "
          f"stale={stats['stale_count']}, flagged={len(stats['flagged'])}")
    return True


def test_schema_validation():
    """Test that sample data validates against correlation schema."""
    print("=" * 60)
    print("TEST: Schema validation")
    print("=" * 60)

    schema_path = os.path.join(PROJECT_ROOT, 'schemas', 'correlation_schema.json')
    if not os.path.exists(schema_path):
        print(f"SKIP: Schema not found: {schema_path}")
        return True

    with open(CORR_SAMPLE) as f:
        data = json.load(f)

    with open(schema_path) as f:
        schema = json.load(f)

    # Basic structural checks (no jsonschema dependency)
    required_top = schema.get('required', [])
    for field in required_top:
        assert field in data, f"Missing required field: {field}"

    if 'pairs' in data and 'pairs' in schema.get('properties', {}):
        pair_schema = schema['properties']['pairs'].get('items', {})
        pair_required = pair_schema.get('required', [])
        for pair in data['pairs']:
            for field in pair_required:
                assert field in pair, f"Missing pair field: {field}"

    print(f"✓ Schema validation passed ({len(data.get('pairs', []))} pairs)")
    return True


def main():
    all_passed = True

    tests = [
        test_schema_validation,
        test_correlation_engine,
        test_data_lag_monitor,
    ]

    for test_fn in tests:
        try:
            if not test_fn():
                all_passed = False
        except Exception as e:
            print(f"FAIL: {test_fn.__name__}: {e}")
            all_passed = False
        print()

    if all_passed:
        print("=" * 60)
        print("ALL PIPELINE TESTS PASSED ✓")
        print("=" * 60)
    else:
        print("=" * 60)
        print("SOME TESTS FAILED ✗")
        print("=" * 60)
        sys.exit(1)


if __name__ == '__main__':
    main()
