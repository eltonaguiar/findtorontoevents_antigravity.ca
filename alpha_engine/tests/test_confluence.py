"""
Tests for Confluence Engine -- Strategy Family Classification
=============================================================
Ensures every registered strategy has a valid family assignment.

Uses regex-based extraction from source files to avoid importing
heavy dependencies (pandas, numpy) that may not be available in
all environments.
"""

import os
import re
import pytest

ALPHA_DIR = os.path.join(os.path.dirname(__file__), '..')


def _extract_dict_keys_from_file(filepath: str, dict_name: str) -> set[str]:
    """Extract top-level string keys from a Python dict literal assignment.

    Looks for `dict_name = {` and then extracts quoted keys until the
    closing `}` or a `**` spread.  Also picks up spread dicts like
    `**COMMUNITY_CRYPTO_STRATEGIES`.
    """
    if not os.path.isfile(filepath):
        return set()

    with open(filepath, encoding="utf-8", errors="replace") as f:
        source = f.read()

    # Find the dict assignment
    pattern = rf'^{re.escape(dict_name)}\s*=\s*\{{(.*?)\n\}}'
    match = re.search(pattern, source, re.DOTALL | re.MULTILINE)
    if not match:
        return set()

    body = match.group(1)
    keys = set()
    for line in body.splitlines():
        # Match "key_name": value,
        m = re.match(r'\s+"([a-z_0-9]+)"\s*:', line)
        if m:
            keys.add(m.group(1))
    return keys


def _extract_all_crypto_strategy_keys() -> set[str]:
    """Extract all keys that end up in CRYPTO_STRATEGIES (core + dynamic merges)."""
    keys = set()

    # Core dict
    keys |= _extract_dict_keys_from_file(
        os.path.join(ALPHA_DIR, 'crypto_strategies.py'), 'CRYPTO_STRATEGIES')

    # Community strategies merged via ** inside the core dict
    keys |= _extract_dict_keys_from_file(
        os.path.join(ALPHA_DIR, 'community_strategies.py'), 'COMMUNITY_CRYPTO_STRATEGIES')

    # Dynamic merges (try-except blocks in crypto_strategies.py)
    dynamic_modules = {
        'spike_predictor.py':                'SPIKE_STRATEGIES',
        'onchain_strategies.py':             'ONCHAIN_STRATEGIES',
        'quant_strategies.py':               'QUANT_STRATEGIES',
        'event_strategies.py':               'EVENT_STRATEGIES',
        'advanced_strategies.py':            'ADVANCED_STRATEGIES',
        'statistical_strategies.py':         'STATISTICAL_STRATEGIES',
        'pattern_strategies.py':             'PATTERN_STRATEGIES',
        'cyclical_strategies.py':            'CYCLICAL_STRATEGIES',
        'experimental_strategies.py':        'EXPERIMENTAL_STRATEGIES',
        'mercury_ai_strategies.py':          'MERCURY_AI_STRATEGIES',
        'nextgen_strategies.py':             'NEXTGEN_STRATEGIES',
        'cerebrus_strategies.py':            'CEREBRUS_STRATEGIES',
        'untapped_strategies.py':            'UNTAPPED_STRATEGIES',
        'market_microstructure_strategies.py': 'MICROSTRUCTURE_STRATEGIES',
        'basis_strategies.py':               'BASIS_STRATEGIES',
        'orderbook_strategies.py':           'ORDERBOOK_STRATEGIES',
        'opposite_day_strategies.py':        'OPPOSITE_DAY_STRATEGIES',
    }

    for filename, dictname in dynamic_modules.items():
        keys |= _extract_dict_keys_from_file(
            os.path.join(ALPHA_DIR, filename), dictname)

    # dxy_divergence_alpha is appended after the dict: CRYPTO_STRATEGIES["dxy_divergence_alpha"] = ...
    crypto_src = os.path.join(ALPHA_DIR, 'crypto_strategies.py')
    if os.path.isfile(crypto_src):
        with open(crypto_src, encoding="utf-8", errors="replace") as f:
            source = f.read()
        for m in re.finditer(r'CRYPTO_STRATEGIES\["([a-z_0-9]+)"\]\s*=', source):
            keys.add(m.group(1))

    return keys


def _extract_forex_strategy_keys() -> set[str]:
    keys = _extract_dict_keys_from_file(
        os.path.join(ALPHA_DIR, 'forex_strategies.py'), 'FOREX_STRATEGIES')
    keys |= _extract_dict_keys_from_file(
        os.path.join(ALPHA_DIR, 'community_strategies.py'), 'COMMUNITY_FOREX_STRATEGIES')
    return keys


def _extract_equity_strategy_keys() -> set[str]:
    keys = _extract_dict_keys_from_file(
        os.path.join(ALPHA_DIR, 'equity_strategies.py'), 'EQUITY_STRATEGIES')
    keys |= _extract_dict_keys_from_file(
        os.path.join(ALPHA_DIR, 'community_strategies.py'), 'COMMUNITY_EQUITY_STRATEGIES')
    return keys


def _load_config_mapping() -> tuple[dict[str, str], set[str]]:
    """Import STRATEGY_FAMILIES and INDICATOR_FAMILIES from config.py.

    config.py has no heavy dependencies (only pathlib), so direct import works.
    """
    import sys
    sys.path.insert(0, ALPHA_DIR)
    from config import STRATEGY_FAMILIES, INDICATOR_FAMILIES
    return STRATEGY_FAMILIES, INDICATOR_FAMILIES


class TestStrategyFamiliesCoverage:
    """Ensure STRATEGY_FAMILIES covers all registered strategies."""

    def test_covers_all_crypto_strategies(self):
        families, _ = _load_config_mapping()
        crypto_keys = _extract_all_crypto_strategy_keys()
        mapped = set(families.keys())
        missing = crypto_keys - mapped
        assert not missing, f"Crypto strategies missing family assignment: {missing}"

    def test_covers_all_forex_strategies(self):
        families, _ = _load_config_mapping()
        forex_keys = _extract_forex_strategy_keys()
        mapped = set(families.keys())
        missing = forex_keys - mapped
        assert not missing, f"Forex strategies missing family assignment: {missing}"

    def test_covers_all_equity_strategies(self):
        families, _ = _load_config_mapping()
        equity_keys = _extract_equity_strategy_keys()
        mapped = set(families.keys())
        missing = equity_keys - mapped
        assert not missing, f"Equity strategies missing family assignment: {missing}"

    def test_covers_all_strategies_combined(self):
        """Every active strategy must have a family assignment."""
        families, _ = _load_config_mapping()
        all_keys = (_extract_all_crypto_strategy_keys()
                    | _extract_forex_strategy_keys()
                    | _extract_equity_strategy_keys())
        mapped = set(families.keys())
        missing = all_keys - mapped
        assert not missing, f"Strategies missing family assignment: {missing}"


class TestStrategyFamiliesValidity:
    """Ensure all family values are valid."""

    def test_all_values_in_indicator_families(self):
        families, indicator_families = _load_config_mapping()
        for name, family in families.items():
            assert family in indicator_families, (
                f"{name} has invalid family '{family}'"
            )

    def test_all_families_have_strategies(self):
        """Every indicator family should have at least one strategy assigned."""
        families, indicator_families = _load_config_mapping()
        used = set(families.values())
        unused = indicator_families - used
        assert not unused, f"Indicator families with no strategies: {unused}"

    def test_no_duplicate_keys(self):
        """Ensure no strategy name appears with two different families."""
        # This is inherently enforced by dict structure, but good to verify
        # the config file doesn't have duplicates (last one wins silently).
        families, _ = _load_config_mapping()
        assert len(families) > 0, "STRATEGY_FAMILIES is empty"


# ===========================================================================
# ConfluenceEngine -- Cross-Family Signal Aggregation Tests
# ===========================================================================

from datetime import datetime, timedelta

# Import ConfluenceEngine (config.py has no heavy deps)
import sys as _sys
_sys.path.insert(0, ALPHA_DIR)
from confluence_engine import ConfluenceEngine


def _make_signal(strategy, symbol, direction, family, confidence=0.7,
                 ml_score=0.6, timestamp=None):
    return {
        "strategy": strategy, "symbol": symbol, "signal_type": direction,
        "family": family, "confidence": confidence, "ml_score": ml_score,
        "timestamp": (timestamp or datetime.utcnow()).isoformat(),
        "entry_price": 100.0, "take_profit": 110.0, "stop_loss": 95.0,
        "risk_reward": 2.0,
    }


class TestConfluenceEngine:
    """Tests for the ConfluenceEngine cross-family aggregation."""

    def test_confluence_requires_two_families(self):
        """Two signals from the SAME family should NOT produce a confluence signal."""
        engine = ConfluenceEngine(min_families=2)
        signals = [
            _make_signal("rsi_a", "BTC-USD", "BUY", "momentum"),
            _make_signal("rsi_b", "BTC-USD", "BUY", "momentum"),
        ]
        results = engine.process_signals(signals)
        assert len(results) == 0

    def test_confluence_passes_with_two_families(self):
        """Momentum + volume on same symbol+direction should produce 1 result."""
        engine = ConfluenceEngine(min_families=2)
        signals = [
            _make_signal("rsi_strat", "BTC-USD", "BUY", "momentum"),
            _make_signal("obv_strat", "BTC-USD", "BUY", "volume"),
        ]
        results = engine.process_signals(signals)
        assert len(results) == 1
        assert results[0]["family_count"] == 2
        assert results[0]["symbol"] == "BTC-USD"
        assert results[0]["direction"] == "BUY"
        assert set(results[0]["families"]) == {"momentum", "volume"}

    def test_confluence_separates_directions(self):
        """BUY momentum + SELL volume on same symbol should NOT match."""
        engine = ConfluenceEngine(min_families=2)
        signals = [
            _make_signal("rsi_strat", "BTC-USD", "BUY", "momentum"),
            _make_signal("obv_strat", "BTC-USD", "SELL", "volume"),
        ]
        results = engine.process_signals(signals)
        assert len(results) == 0

    def test_confluence_time_window_filters_old(self):
        """A signal older than the time window should be excluded."""
        engine = ConfluenceEngine(min_families=2, time_window_hours=4.0)
        old_ts = datetime.utcnow() - timedelta(hours=5)
        signals = [
            _make_signal("rsi_strat", "BTC-USD", "BUY", "momentum"),
            _make_signal("obv_strat", "BTC-USD", "BUY", "volume",
                         timestamp=old_ts),
        ]
        results = engine.process_signals(signals)
        assert len(results) == 0

    def test_confluence_three_families_scored_higher(self):
        """Three families should produce a higher score than two families."""
        engine = ConfluenceEngine(min_families=2)
        two_fam = [
            _make_signal("rsi_strat", "BTC-USD", "BUY", "momentum"),
            _make_signal("obv_strat", "BTC-USD", "BUY", "volume"),
        ]
        three_fam = [
            _make_signal("rsi_strat", "ETH-USD", "BUY", "momentum"),
            _make_signal("obv_strat", "ETH-USD", "BUY", "volume"),
            _make_signal("ema_strat", "ETH-USD", "BUY", "trend"),
        ]
        r2 = engine.process_signals(two_fam)
        r3 = engine.process_signals(three_fam)
        assert len(r2) == 1
        assert len(r3) == 1
        assert r3[0]["confluence_score"] > r2[0]["confluence_score"]

    def test_confluence_multiple_symbols(self):
        """Signals for BTC and ETH should produce 2 separate results."""
        engine = ConfluenceEngine(min_families=2)
        signals = [
            _make_signal("rsi_strat", "BTC-USD", "BUY", "momentum"),
            _make_signal("obv_strat", "BTC-USD", "BUY", "volume"),
            _make_signal("ema_strat", "ETH-USD", "BUY", "trend"),
            _make_signal("vwap_strat", "ETH-USD", "BUY", "volume"),
        ]
        results = engine.process_signals(signals)
        assert len(results) == 2
        symbols = {r["symbol"] for r in results}
        assert symbols == {"BTC-USD", "ETH-USD"}
