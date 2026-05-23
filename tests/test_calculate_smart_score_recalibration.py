"""Tests for Phase B recalibration of calculate_smart_score base term.

Strategy: Since calculate_smart_score adds many bonuses besides the base term,
we test via DIFFERENCES between picks that are identical except for the field
affecting the base term. The delta in output equals the delta in base.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from audit_trail.quality_gates import calculate_smart_score  # noqa: E402


def _base_pick(score, **overrides):
    """Return a pick with valid trade geometry. Defaults avoid copy-pick logic."""
    pick = {
        "symbol": "XYZUSDT",
        "direction": "LONG",
        "entry_price": 100.0,
        "take_profit": 105.0,  # RR tiny to minimize RR bonus influence (still bonus fires)
        "stop_loss": 95.0,
        "score": score,
        "strategy": "non_copy_strategy",
        "asset_class": "CRYPTO",
        "confidence": 0.5,  # outside all bonus bands
    }
    pick.update(overrides)
    return pick


class TestPiecewiseBaseTerm(unittest.TestCase):
    """Verify piecewise base values by diffing against raw=0 (base=0) reference."""

    def _base_component(self, pick):
        """Extract the base-term contribution by diffing vs score=0 pick."""
        zero_pick = dict(pick)
        zero_pick["score"] = 0
        return calculate_smart_score(pick) - calculate_smart_score(zero_pick)

    def test_low_raw_score_30(self):
        # raw <= 40: base = raw * 0.10 => 30 * 0.10 = 3.0
        self.assertAlmostEqual(self._base_component(_base_pick(30)), 3.0, places=6)

    def test_middle_raw_score_55(self):
        # 40 < raw <= 70: base = raw * 0.20 => 55 * 0.20 = 11.0
        self.assertAlmostEqual(self._base_component(_base_pick(55)), 11.0, places=6)

    def test_high_raw_score_85(self):
        # raw > 70: base = min(raw*0.30, 30.0) => 85 * 0.30 = 25.5
        self.assertAlmostEqual(self._base_component(_base_pick(85)), 25.5, places=6)

    def test_very_high_raw_score_100_capped(self):
        # raw > 70: capped at 30.0 (100 * 0.30 = 30.0 -> cap)
        self.assertAlmostEqual(self._base_component(_base_pick(100)), 30.0, places=6)

    def test_very_high_raw_score_above_cap(self):
        # raw = 150 -> 45 -> capped to 30.0
        self.assertAlmostEqual(self._base_component(_base_pick(150)), 30.0, places=6)

    def test_zero_or_negative_raw_score(self):
        self.assertAlmostEqual(self._base_component(_base_pick(0)), 0.0, places=6)


class TestCopyTraderCap(unittest.TestCase):
    """Verify 0.8x cap on copy-trader picks for non-BTC-majors only."""

    def _base_component_with_zero_ref(self, pick):
        zero_pick = dict(pick)
        zero_pick["score"] = 0
        return calculate_smart_score(pick) - calculate_smart_score(zero_pick)

    def test_copy_trader_non_btc_major_gets_0_8x(self):
        # Non-copy raw=85 -> base=25.5; copy-pick on DOGE -> 25.5 * 0.8 = 20.4
        pick = _base_pick(85, symbol="DOGEUSDT", _is_copy_pick=True)
        self.assertAlmostEqual(
            self._base_component_with_zero_ref(pick), 25.5 * 0.8, places=6
        )

    def test_copy_trader_via_strategy_prefix(self):
        # Detection also via strategy name matching copy_hl_*
        pick = _base_pick(55, symbol="ADAUSDT", strategy="copy_hl_whale1")
        self.assertAlmostEqual(
            self._base_component_with_zero_ref(pick), 11.0 * 0.8, places=6
        )

    def test_copy_trader_on_btc_major_no_cap(self):
        # BTC major: cap does NOT apply
        pick = _base_pick(85, symbol="BTCUSDT", _is_copy_pick=True)
        self.assertAlmostEqual(
            self._base_component_with_zero_ref(pick), 25.5, places=6
        )

    def test_copy_trader_on_eth_major_no_cap(self):
        pick = _base_pick(55, symbol="ETH", strategy="copy_hl_trader")
        self.assertAlmostEqual(
            self._base_component_with_zero_ref(pick), 11.0, places=6
        )

    def test_copy_trader_on_sol_major_no_cap(self):
        pick = _base_pick(100, symbol="SOL-USD", _is_copy_pick=True)
        self.assertAlmostEqual(
            self._base_component_with_zero_ref(pick), 30.0, places=6
        )

    def test_non_copy_pick_gets_full_base(self):
        # Plain pick on altcoin, no copy flags
        pick = _base_pick(55, symbol="ADAUSDT")
        self.assertAlmostEqual(
            self._base_component_with_zero_ref(pick), 11.0, places=6
        )


if __name__ == "__main__":
    unittest.main()
