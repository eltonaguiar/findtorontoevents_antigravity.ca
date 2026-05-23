"""Tests for audit_trail.guide_band_activation (Phase 5 Wilson-LB gate)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from audit_trail.guide_band_activation import (  # noqa: E402
    should_activate_guide_band,
    wilson_lower_bound,
)


class WilsonLowerBoundTests(unittest.TestCase):
    def test_zero_n_returns_zero(self):
        self.assertEqual(wilson_lower_bound(0, 0), 0.0)

    def test_50_of_100_is_about_0_40(self):
        # Well-known textbook value: Wilson 95% LB for 0.5 on n=100 ≈ 0.4038
        lb = wilson_lower_bound(50, 100)
        self.assertAlmostEqual(lb, 0.4038, places=3)

    def test_higher_z_tightens_bound(self):
        # 99% LB should be strictly lower than 95% LB.
        self.assertLess(
            wilson_lower_bound(30, 50, z=2.576),
            wilson_lower_bound(30, 50, z=1.96),
        )

    def test_wins_gt_n_raises(self):
        with self.assertRaises(ValueError):
            wilson_lower_bound(11, 10)

    def test_negative_inputs_raise(self):
        with self.assertRaises(ValueError):
            wilson_lower_bound(-1, 10)
        with self.assertRaises(ValueError):
            wilson_lower_bound(1, -1)


class ShouldActivateGuideBandTests(unittest.TestCase):
    def test_small_n_never_activates(self):
        # 19 wins / 20 = WR 0.95 but n < 50 → must stay False.
        self.assertFalse(
            should_activate_guide_band(19, 20, currently_active=False)
        )
        # Even when currently_active, n < min_n forces False.
        self.assertFalse(
            should_activate_guide_band(19, 20, currently_active=True)
        )

    def test_activation_above_threshold(self):
        # 40/60 = 0.667, Wilson LB ≈ 0.542 → clears 0.52.
        self.assertTrue(
            should_activate_guide_band(40, 60, currently_active=False)
        )

    def test_hysteresis_stays_active_between_bands(self):
        # Deactivate gap widened 2026-04-20 to ~0.07 (≈1 SE at n=50).
        # Find n,wins with wilson_lb in [0.45, 0.52): try 36/60 -> LB ≈ 0.476.
        lb = wilson_lower_bound(36, 60)
        self.assertGreaterEqual(lb, 0.45)
        self.assertLess(lb, 0.52)
        # currently_active → stays on
        self.assertTrue(
            should_activate_guide_band(36, 60, currently_active=True)
        )
        # not active → does not flip on
        self.assertFalse(
            should_activate_guide_band(36, 60, currently_active=False)
        )

    def test_below_deactivate_flips_off(self):
        # 27/60 -> LB ≈ 0.327, below 0.45 → even if currently_active, must flip off.
        self.assertFalse(
            should_activate_guide_band(27, 60, currently_active=True)
        )

    def test_bonferroni_raises_the_bar(self):
        # Pick wins,n that pass at k=1 but fail at k=4.
        # 40/60 -> 95% LB ≈ 0.542 (passes 0.52). With k=4 the effective
        # confidence is 98.75% → z ≈ 2.498, LB ≈ 0.497 → fails 0.52.
        self.assertTrue(
            should_activate_guide_band(40, 60, currently_active=False, k=1)
        )
        self.assertFalse(
            should_activate_guide_band(40, 60, currently_active=False, k=4)
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
