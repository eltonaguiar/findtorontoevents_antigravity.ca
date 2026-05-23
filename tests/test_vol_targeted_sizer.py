"""Unit tests for alpha_engine.vol_targeted_sizer (U-1)."""
import math
import os
import unittest

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alpha_engine.vol_targeted_sizer import (
    DEFAULT_CAP,
    DEFAULT_FLOOR,
    DEFAULT_TARGET_ANNUAL_VOL,
    SizingDecision,
    realized_vol_from_closes,
    realized_vol_from_returns,
    size_from_closes,
    size_position,
)


class _ClearEnv:
    _vars = ("VOL_TARGET_ENABLED", "VOL_TARGET_SHADOW")

    def __enter__(self):
        self._saved = {k: os.environ.pop(k, None) for k in self._vars}
        return self

    def __exit__(self, *exc):
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


class VolTargetedSizerTests(unittest.TestCase):
    def test_high_vol_gets_downsized(self):
        with _ClearEnv():
            d = size_position(1.0, realized_vol_ann=0.60, target_vol_ann=0.15)
            self.assertLess(d.multiplier, 1.0)
            self.assertTrue(d.applied)
            # 0.15 / 0.60 = 0.25 = floor exactly
            self.assertAlmostEqual(d.multiplier, 0.25, places=3)

    def test_low_vol_is_capped(self):
        """Without the cap, σ=0.05 → 0.15/0.05=3.0× oversizing. Cap at 1.5×."""
        with _ClearEnv():
            d = size_position(1.0, realized_vol_ann=0.05, target_vol_ann=0.15)
            self.assertEqual(d.multiplier, DEFAULT_CAP)
            self.assertAlmostEqual(d.sized, DEFAULT_CAP, places=6)

    def test_floor_prevents_zero_sizing(self):
        """Vol spike → σ→∞ → multiplier clamps at floor, not 0."""
        with _ClearEnv():
            d = size_position(1.0, realized_vol_ann=10.0)
            self.assertEqual(d.multiplier, DEFAULT_FLOOR)

    def test_flat_fallback_when_vol_missing(self):
        with _ClearEnv():
            d = size_position(0.02, realized_vol_ann=None)
            self.assertFalse(d.applied)
            self.assertAlmostEqual(d.sized, 0.02, places=6)
            self.assertEqual(d.multiplier, 1.0)
            self.assertIn("no finite", d.reason)

    def test_non_finite_realized_vol_falls_back_flat(self):
        with _ClearEnv():
            d = size_position(0.02, realized_vol_ann=float("nan"))
            self.assertFalse(d.applied)

    def test_zero_or_negative_vol_falls_back_flat(self):
        with _ClearEnv():
            self.assertFalse(size_position(0.02, realized_vol_ann=0.0).applied)
            self.assertFalse(size_position(0.02, realized_vol_ann=-0.1).applied)

    def test_env_disable_is_flat(self):
        with _ClearEnv():
            os.environ["VOL_TARGET_ENABLED"] = "0"
            d = size_position(0.5, realized_vol_ann=0.30)
            self.assertFalse(d.applied)
            self.assertAlmostEqual(d.sized, 0.5)
            self.assertIn("disabled", d.reason)

    def test_shadow_mode_returns_base_but_reports_multiplier(self):
        with _ClearEnv():
            os.environ["VOL_TARGET_SHADOW"] = "1"
            d = size_position(1.0, realized_vol_ann=0.30, target_vol_ann=0.15)
            self.assertFalse(d.applied)
            self.assertAlmostEqual(d.sized, 1.0)  # unchanged
            self.assertAlmostEqual(d.multiplier, 0.5, places=3)
            self.assertIn("SHADOW", d.reason)

    def test_kelly_ceiling_caps_final_size(self):
        """Kelly ceiling must apply AFTER vol-targeting, not multiply."""
        with _ClearEnv():
            # σ = 0.075 → raw = 0.15/0.075 = 2 → clipped to cap 1.5
            # → sized = 1.0 × 1.5 = 1.5; kelly_ceiling=0.6 clamps to 0.6.
            d = size_position(
                1.0, realized_vol_ann=0.075, kelly_ceiling=0.6
            )
            self.assertAlmostEqual(d.multiplier, 1.5, places=3)
            self.assertAlmostEqual(d.sized, 0.6, places=6)

    def test_kelly_ceiling_does_not_multiply_into_base(self):
        """Sanity check against the σ³ stacking bug the critique warned about:
        if Kelly were erroneously *multiplied* in, sized would be
        1.0 × 1.5 × 0.6 = 0.9. We want the *min*, which is 0.6."""
        with _ClearEnv():
            d = size_position(1.0, realized_vol_ann=0.075, kelly_ceiling=0.6)
            self.assertNotAlmostEqual(d.sized, 0.9, places=2)
            self.assertAlmostEqual(d.sized, 0.6, places=6)

    def test_realized_vol_from_returns(self):
        # Flat returns → tiny realized vol
        self.assertLess(realized_vol_from_returns([0.0] * 50), 1e-9)
        # Noise
        rng = [0.01, -0.015, 0.02, -0.005, 0.012, -0.018, 0.009, -0.007]
        rv = realized_vol_from_returns(rng)
        self.assertGreater(rv, 0.0)
        self.assertTrue(math.isfinite(rv))

    def test_realized_vol_from_returns_small_sample(self):
        self.assertTrue(math.isnan(realized_vol_from_returns([0.01])))

    def test_realized_vol_from_closes(self):
        closes = [100.0, 100.5, 99.8, 100.2, 100.7, 100.3, 100.1, 100.9, 101.2,
                  100.8, 101.5, 101.1, 101.9, 102.0, 101.5, 102.3, 102.1, 102.6,
                  102.2, 102.8, 102.5, 103.1, 102.9, 103.4]
        rv = realized_vol_from_closes(closes, lookback=20)
        self.assertGreater(rv, 0)
        self.assertTrue(math.isfinite(rv))

    def test_size_from_closes_convenience(self):
        closes = [100.0 + 0.3 * i + (0.5 if i % 3 else -0.4) for i in range(60)]
        with _ClearEnv():
            d = size_from_closes(1.0, closes, bar_period="1h", lookback=20)
            self.assertIsInstance(d, SizingDecision)
            self.assertTrue(math.isfinite(d.realized_vol_ann or 0))

    def test_dataclass_shape(self):
        d = SizingDecision(
            multiplier=1.0, base_size=1.0, sized=1.0,
            realized_vol_ann=0.2, reason="ok", applied=True,
        )
        for attr in ("multiplier", "base_size", "sized", "realized_vol_ann", "reason", "applied"):
            self.assertTrue(hasattr(d, attr))


if __name__ == "__main__":
    unittest.main(verbosity=2)
