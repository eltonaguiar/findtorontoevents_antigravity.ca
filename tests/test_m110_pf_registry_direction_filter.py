"""M-110 direction-aware pf_registry policy filter.

Previously _is_policy_excluded() only checked flat strategy/source_system sets,
so a LONG-blocked strategy's SHORT picks were also excluded from the clean view.
This hid FOREX cta_cross_asset_tsmom SHORT (n=120, WR=66%, PF=2.8, T1-grade).
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from tools.build_pf_registry import _is_policy_excluded


def _row(asset_class, strategy, direction, source_system="test"):
    return {"asset_class": asset_class, "strategy": strategy,
            "direction": direction, "source_system": source_system}


class TestDirectionAwareFilter:
    def test_commodity_cta_cross_asset_tsmom_long_excluded(self):
        """COMMODITY LONG blocked via BLOCKED_DIRECTION_TRIPLES."""
        assert _is_policy_excluded(_row("COMMODITY", "cta_cross_asset_tsmom", "LONG"))

    def test_commodity_cta_cross_asset_tsmom_short_excluded(self):
        """COMMODITY SHORT also blocked via BLOCKED_DIRECTION_TRIPLES."""
        assert _is_policy_excluded(_row("COMMODITY", "cta_cross_asset_tsmom", "SHORT"))

    def test_forex_cta_cross_asset_tsmom_long_excluded(self):
        """FOREX LONG blocked via BLOCKED_DIRECTION_TRIPLES."""
        assert _is_policy_excluded(_row("FOREX", "cta_cross_asset_tsmom", "LONG"))

    def test_forex_cta_cross_asset_tsmom_short_included(self):
        """FOREX SHORT NOT blocked — n=120, WR=66%, PF=2.8, T1-grade edge.
        This is the M-110 fix: SHORT picks must survive the policy filter.
        """
        assert not _is_policy_excluded(_row("FOREX", "cta_cross_asset_tsmom", "SHORT"))

    def test_forex_ig_contrarian_sentiment_long_excluded(self):
        """FOREX LONG blocked via BLOCKED_DIRECTION_TRIPLES."""
        assert _is_policy_excluded(_row("FOREX", "ig_contrarian_sentiment", "LONG"))

    def test_forex_ig_contrarian_sentiment_short_included(self):
        """FOREX SHORT survives — WR=60%, PF=1.95, T2-grade."""
        assert not _is_policy_excluded(_row("FOREX", "ig_contrarian_sentiment", "SHORT"))

    def test_myfxbook_both_directions_excluded(self):
        """myfxbook is in BLOCKED_ASSET_STRATEGY_PAIRS — both directions excluded."""
        assert _is_policy_excluded(_row("FOREX", "myfxbook_retail_contrarian", "LONG"))
        assert _is_policy_excluded(_row("FOREX", "myfxbook_retail_contrarian", "SHORT"))

    def test_cta_commodity_momentum_term_excluded(self):
        """Still in PF_REGISTRY_POLICY_EXCLUDED flat set."""
        assert _is_policy_excluded(_row("COMMODITY", "cta_commodity_momentum_term", "LONG"))

    def test_source_system_cta_replicator_forex_short_passes(self):
        """cta_replicator source removed from flat exclusion.
        FOREX cta_cross_asset_tsmom SHORT picks have source_system=cta_replicator.
        They must now pass the filter (T1 edge).
        """
        row = _row("FOREX", "cta_cross_asset_tsmom", "SHORT", source_system="cta_replicator")
        assert not _is_policy_excluded(row)

    def test_source_system_cta_replicator_commodity_long_still_excluded(self):
        """COMMODITY LONG blocked via direction triple even when source=cta_replicator."""
        row = _row("COMMODITY", "cta_cross_asset_tsmom", "LONG", source_system="cta_replicator")
        assert _is_policy_excluded(row)


class TestAssetClassInferenceForBlocks:
    """M-113: _is_policy_excluded must infer asset_class from symbol for records
    missing the asset_class field (e.g. mercury2/data/closed_picks.json).
    Before the fix, ac='' so BLOCKED_ASSET_STRATEGY_PAIRS never matched, allowing
    ensemble (PF=0.013, n=79) to slip through and drag CRYPTO PF from ~1.26 → 0.659.
    """

    def test_ensemble_usdt_no_asset_class_field_excluded(self):
        """ensemble BTCUSDT record with no asset_class field must be excluded."""
        row = {"strategy": "ensemble", "symbol": "BTCUSDT", "direction": "LONG"}
        assert _is_policy_excluded(row), "ensemble USDT record must be blocked even without asset_class field"

    def test_rapid_fire_usdt_no_asset_class_field_excluded(self):
        """rapid_fire DOGEUSDT record with no asset_class field must be excluded (if rapid_fire CRYPTO blocked)."""
        row = {"strategy": "rapid_fire", "symbol": "DOGEUSDT", "direction": "LONG"}
        # rapid_fire is in BLOCKED_ASSET_STRATEGY_PAIRS for CRYPTO
        result = _is_policy_excluded(row)
        # Only assert True if rapid_fire is actually blocked — check pair membership first
        from tools.build_pf_registry import _ASSET_PAIRS
        if ("CRYPTO", "rapid_fire") in _ASSET_PAIRS:
            assert result, "rapid_fire USDT without asset_class must be blocked"

    def test_unblocked_strategy_usdt_no_asset_class_passes(self):
        """An unblocked CRYPTO strategy must not be incorrectly excluded."""
        row = {"strategy": "breakout_momentum", "symbol": "SOLUSDT", "direction": "LONG"}
        assert not _is_policy_excluded(row), "Unblocked CRYPTO strategy must pass policy filter"

    def test_ensemble_equity_not_excluded_by_crypto_block(self):
        """ensemble with explicit EQUITY asset_class must not be excluded by CRYPTO block."""
        row = {"strategy": "ensemble", "asset_class": "EQUITY", "symbol": "AAPL", "direction": "LONG"}
        assert not _is_policy_excluded(row), "CRYPTO block must not affect EQUITY ensemble"
