# ---------------------------------------------------------------------------
# tests/test_polymarket_volume_filter.py
# ---------------------------------------------------------------------------
# Unit tests for alpha_engine/polymarket_volume_filter.py
# Polymarket volume spike filter -- CRYPTO LONG entry confirmation layer.
#
# Cache isolation strategy:
#   - Module-level autouse fixture invalidates cache between tests
#   - Tests that need a specific file state call invalidate_cache() INSIDE
#     their own with-block (after patching) so the next _get_cached_signals()
#     call actually reloads, not returns stale cached data from a prior test.
# ---------------------------------------------------------------------------

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'alpha_engine'))


# ---------------------------------------------------------------------------
# Shared tmp_path for all tests (session-scoped, reused for cache isolation)
# ---------------------------------------------------------------------------

@pytest.fixture(scope='module')
def shared_pm_file(tmp_path_factory):
    cls = type('PMFileFactory', (), {
        'tmp_path': tmp_path_factory.mktemp('pm_data'),
        'make': lambda picks: _write_pm_signals(Path(cls.tmp_path) / 'data', picks),
    })
    return cls


def _write_pm_signals(tmp_path, picks):
    data_dir = tmp_path / 'data'
    data_dir.mkdir(exist_ok=True)
    f = data_dir / 'polymarket_signals.json'
    f.write_text(
        json.dumps({'picks': picks, 'updated_at': '2026-05-07T20:00:00Z'}),
        encoding='utf-8',
    )
    return f


# ---------------------------------------------------------------------------
# Setup / teardown -- invalidate cache between every test
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_cache():
    from alpha_engine.polymarket_volume_filter import invalidate_cache
    invalidate_cache()
    yield
    invalidate_cache()


# ---------------------------------------------------------------------------
# Helper: patch _POLYMARKET_SIGNALS_FILE and invalidate cache
# ---------------------------------------------------------------------------

def _use_pm_file(picks, tmp_path):
    f = _write_pm_signals(tmp_path, picks)
    from alpha_engine import polymarket_volume_filter as pmf
    original = pmf._POLYMARKET_SIGNALS_FILE
    pmf._POLYMARKET_SIGNALS_FILE = f
    pmf.invalidate_cache()
    return f


# ---------------------------------------------------------------------------
# Test: exempt symbols always pass (empty set = no-op test)
# ---------------------------------------------------------------------------

def test_exempt_symbols_pass():
    from alpha_engine.polymarket_volume_filter import _EXEMPT_SYMBOLS

    # _EXEMPT_SYMBOLS is intentionally empty — no known Polymarket coverage gaps
    # If non-empty in future, test each; for now this is a documentation test
    assert _EXEMPT_SYMBOLS == frozenset(), '_EXEMPT_SYMBOLS should be empty'


# ---------------------------------------------------------------------------
# Test: non-LONG entries pass through without Polymarket check
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('direction', ['SHORT', 'SELL', 'NEUTRAL', 'FLAT'])
def test_non_long_entries_pass(direction, tmp_path):
    from alpha_engine.polymarket_volume_filter import is_polymarket_volume_confirmed

    # Set up a file with markets so the filter WOULD fire for LONG
    _use_pm_file([{'symbol': 'XRPUSDT', 'direction': 'LONG', 'volume': 80000.0, 'probability': 0.74}], tmp_path)
    confirmed, reason = is_polymarket_volume_confirmed('XRPUSDT', direction)
    assert confirmed is True, 'direction=%s should pass: %s' % (direction, reason)
    assert 'not a CRYPTO LONG entry' in reason, 'expected non-LONG reason, got: %s' % reason


# ---------------------------------------------------------------------------
# Test: disabled env var passes everything through
# ---------------------------------------------------------------------------

def test_env_var_disabled_passes_through(monkeypatch, tmp_path):
    from alpha_engine.polymarket_volume_filter import is_polymarket_volume_confirmed

    monkeypatch.setenv('POLYMARKET_VOL_SPIKE_DISABLED', '1')
    _use_pm_file([{'symbol': 'XRPUSDT', 'direction': 'LONG', 'volume': 80000.0, 'probability': 0.74}], tmp_path)
    confirmed, reason = is_polymarket_volume_confirmed('XRPUSDT', 'LONG')
    assert confirmed is True
    assert 'disabled' in reason.lower()


# ---------------------------------------------------------------------------
# Test: no markets -> pass through
# ---------------------------------------------------------------------------

def test_no_markets_passes_through(tmp_path):
    from alpha_engine.polymarket_volume_filter import (
        is_polymarket_volume_confirmed,
        get_polymarket_volume_spike_info,
    )

    _use_pm_file([], tmp_path)
    info = get_polymarket_volume_spike_info('XRPUSDT')
    assert info['has_markets'] is False

    confirmed, reason = is_polymarket_volume_confirmed('XRPUSDT', 'LONG')
    assert confirmed is True
    assert 'no Polymarket markets found' in reason


# ---------------------------------------------------------------------------
# Test: no spike -> soft warning, passes through (not blocked)
# ---------------------------------------------------------------------------

def test_no_spike_passes_with_warning(tmp_path):
    from alpha_engine.polymarket_volume_filter import (
        is_polymarket_volume_confirmed,
        get_polymarket_volume_spike_info,
    )

    # Two markets: 5000 and 6000 -> median=5000, max=6000, ratio=1.2x (no spike)
    _use_pm_file([
        {'symbol': 'XRPUSDT', 'direction': 'LONG', 'volume': 5000.0, 'probability': 0.72},
        {'symbol': 'XRPUSDT', 'direction': 'LONG', 'volume': 6000.0, 'probability': 0.70},
    ], tmp_path)

    info = get_polymarket_volume_spike_info('XRPUSDT')
    assert info['has_markets'] is True
    assert info['volume_spike'] is False
    # Lower-middle of [5000, 6000] -> index 0 -> median = 5000
    assert info['median_volume'] == 5000.0

    confirmed, reason = is_polymarket_volume_confirmed('XRPUSDT', 'LONG')
    assert confirmed is True  # PASSES through, not blocked
    assert 'no-spike' in reason


# ---------------------------------------------------------------------------
# Test: volume spike present -> pass + spike detected
# ---------------------------------------------------------------------------

def test_volume_spike_detected(tmp_path):
    from alpha_engine.polymarket_volume_filter import (
        get_polymarket_volume_spike_info,
        is_polymarket_volume_confirmed,
    )

    # Two markets: 50000 and 8000 -> sorted=[8000, 50000], median=8000, ratio=6.25x
    _use_pm_file([
        {'symbol': 'XRPUSDT', 'direction': 'LONG', 'volume': 50000.0, 'probability': 0.74},
        {'symbol': 'XRPUSDT', 'direction': 'LONG', 'volume': 8000.0, 'probability': 0.70},
    ], tmp_path)

    info = get_polymarket_volume_spike_info('XRPUSDT')
    assert info['has_markets'] is True
    assert info['current_volume'] == 50000.0
    assert info['median_volume'] == 8000.0, 'Expected 8000.0, got %s' % info['median_volume']
    assert info['spike_ratio'] >= 2.0, 'Spike ratio %.3f should be >= 2.0' % info['spike_ratio']
    assert info['volume_spike'] is True

    confirmed, reason = is_polymarket_volume_confirmed('XRPUSDT', 'LONG')
    assert confirmed is True
    assert 'VOLUME SPIKE' in reason


# ---------------------------------------------------------------------------
# Test: confidence boost applied when spike is present
# ---------------------------------------------------------------------------

def test_confidence_boost_on_spike(tmp_path):
    from alpha_engine.polymarket_volume_filter import (
        apply_confidence_boost,
        get_polymarket_volume_spike_info,
    )

    # Two markets: 8000 (low) and 80000 (high) -> median=8000, max=80000, ratio=10x
    _use_pm_file([
        {'symbol': 'XRPUSDT', 'direction': 'LONG', 'volume': 8000.0, 'probability': 0.70},
        {'symbol': 'XRPUSDT', 'direction': 'LONG', 'volume': 80000.0, 'probability': 0.75},
    ], tmp_path)

    # Sanity-check: spike should be detected
    info = get_polymarket_volume_spike_info('XRPUSDT')
    assert info['volume_spike'] is True, 'spike should be detected: %s' % info['reason']

    # Now test the boost
    pick = {'symbol': 'XRPUSDT', 'direction': 'LONG', 'confidence': 0.70}
    new_conf, reason = apply_confidence_boost(pick, 0.70)
    # Boost = min(0.05, 0.20 - 0.70) = 0.05 -> new_conf = 0.75
    assert new_conf == 0.75, 'expected 0.75, got %s (reason: %s)' % (new_conf, reason)
    assert 'pm_vol_spike' in reason


# ---------------------------------------------------------------------------
# Test: no confidence boost when no spike
# ---------------------------------------------------------------------------

def test_no_boost_without_spike(tmp_path):
    from alpha_engine.polymarket_volume_filter import apply_confidence_boost

    # Single market below spike threshold
    _use_pm_file([
        {'symbol': 'XRPUSDT', 'direction': 'LONG', 'volume': 3000.0, 'probability': 0.68},
    ], tmp_path)

    pick = {'symbol': 'XRPUSDT', 'direction': 'LONG', 'confidence': 0.70}
    new_conf, reason = apply_confidence_boost(pick, 0.70)
    assert new_conf == 0.70, 'no boost expected without spike, got %s' % new_conf


# ---------------------------------------------------------------------------
# Test: cache invalidation and refresh
# ---------------------------------------------------------------------------

def test_cache_invalidation(tmp_path):
    from alpha_engine.polymarket_volume_filter import (
        _get_cached_signals,
        invalidate_cache,
    )

    f = _use_pm_file([{'symbol': 'XRPUSDT', 'volume': 5000.0}], tmp_path)
    first = _get_cached_signals()
    assert len(first) == 1

    # Overwrite file with MORE picks but DON'T invalidate cache
    _write_pm_signals(tmp_path, [
        {'symbol': 'XRPUSDT', 'volume': 5000.0},
        {'symbol': 'SOLUSDT', 'volume': 10000.0},
    ])
    cached = _get_cached_signals()
    assert len(cached) == 1, 'cache should still be stale (1 entry)'

    # Now invalidate and re-read
    invalidate_cache()
    refreshed = _get_cached_signals()
    assert len(refreshed) == 2, 'cache should refresh after invalidate (2 entries)'


# ---------------------------------------------------------------------------
# Test: SHORT entries are not gated regardless of volume
# ---------------------------------------------------------------------------

def test_short_not_gated_regardless_of_volume(tmp_path):
    from alpha_engine.polymarket_volume_filter import is_polymarket_volume_confirmed

    # High volume spike, but direction is SHORT — should still pass
    _use_pm_file([{'symbol': 'XRPUSDT', 'direction': 'SHORT', 'volume': 100000.0}], tmp_path)
    confirmed, reason = is_polymarket_volume_confirmed('XRPUSDT', 'SHORT')
    assert confirmed is True, 'SHORT should never be gated: %s' % reason
    assert 'not a CRYPTO LONG entry' in reason


# ---------------------------------------------------------------------------
# Test: volume below MIN_MARKET_VOLUME_USD is filtered out
# ---------------------------------------------------------------------------

def test_low_volume_markets_ignored(tmp_path):
    from alpha_engine.polymarket_volume_filter import get_polymarket_volume_spike_info

    # Both volumes < 1000 USD minimum threshold
    _use_pm_file([
        {'symbol': 'XRPUSDT', 'direction': 'LONG', 'volume': 200.0},
        {'symbol': 'XRPUSDT', 'direction': 'LONG', 'volume': 300.0},
    ], tmp_path)

    info = get_polymarket_volume_spike_info('XRPUSDT')
    assert info['has_markets'] is False, 'all volumes < 1000 USD min threshold'
    assert 'below min volume threshold' in info['reason']


# ---------------------------------------------------------------------------
# Test: top_direction majority is computed correctly
# ---------------------------------------------------------------------------

def test_top_direction_majority_long(tmp_path):
    from alpha_engine.polymarket_volume_filter import get_polymarket_volume_spike_info

    _use_pm_file([
        {'symbol': 'XRPUSDT', 'direction': 'LONG', 'volume': 10000.0, 'probability': 0.72},
        {'symbol': 'XRPUSDT', 'direction': 'LONG', 'volume': 10000.0, 'probability': 0.70},
        {'symbol': 'XRPUSDT', 'direction': 'SHORT', 'volume': 10000.0, 'probability': 0.35},
    ], tmp_path)

    info = get_polymarket_volume_spike_info('XRPUSDT')
    assert info['top_direction'] == 'LONG'


# ---------------------------------------------------------------------------
# Test: feed_hygiene integration -- LONG without markets passes (not blocked)
# ---------------------------------------------------------------------------

def test_feed_hygiene_long_no_markets_passes(tmp_path):
    from alpha_engine.feed_hygiene import sanitize_active_picks

    _use_pm_file([], tmp_path)  # empty = no markets
    picks = [
        {
            'strategy': 'rsi_bounce_v1',
            'symbol': 'XRPUSDT',
            'direction': 'LONG',
            'entry_price': 2.50,
            'status': 'OPEN',
            'confidence': 0.65,
            'source_system': 'test',
        },
    ]
    result = sanitize_active_picks(picks, 'test')
    assert len(result) == 1, 'LONG pick should pass when no Polymarket markets'


# ---------------------------------------------------------------------------
# Test: feed_hygiene integration -- spike pick gets confidence boost
# ---------------------------------------------------------------------------

def test_feed_hygiene_spike_boost(tmp_path):
    from alpha_engine.feed_hygiene import sanitize_active_picks

    # Two markets: low=8000, high=80000 -> spike_ratio=10x
    _use_pm_file([
        {'symbol': 'XRPUSDT', 'direction': 'LONG', 'volume': 8000.0, 'probability': 0.70},
        {'symbol': 'XRPUSDT', 'direction': 'LONG', 'volume': 80000.0, 'probability': 0.74},
    ], tmp_path)

    picks = [
        {
            'strategy': 'rsi_bounce_v1',
            'symbol': 'XRPUSDT',
            'direction': 'LONG',
            'entry_price': 2.50,
            'status': 'OPEN',
            'confidence': 0.70,
            'source_system': 'test',
        },
    ]
    result = sanitize_active_picks(picks, 'test')
    assert len(result) == 1
    got_conf = result[0].get('confidence')
    assert got_conf == 0.75, 'Expected 0.75, got %s' % got_conf
    assert '_pm_vol_spike_boost' in result[0]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])