"""Smoke tests for alpha_engine/confidence_calibrator.py.

Verifies:
  1. With CONFIDENCE_CALIBRATION_ENABLED unset, calibrate() is a no-op.
  2. With the flag set and a fitted calibrator on disk, CRYPTO confidence
     is mutated (the inversion fix is the whole point).
  3. Picks without asset_class pass through unmodified.
  4. The smart_picks_engine.py wire-up site picks up the change behind
     the same flag.
"""
from __future__ import annotations

import importlib
import os
import unittest


class CalibratorContractTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ.pop("CONFIDENCE_CALIBRATION_ENABLED", None)
        # Force fresh module state so env reads are honored
        import alpha_engine.confidence_calibrator as cc
        importlib.reload(cc)
        self.cc = cc
        self.cc.reset_cache()

    def tearDown(self) -> None:
        os.environ.pop("CONFIDENCE_CALIBRATION_ENABLED", None)
        self.cc.reset_cache()

    def test_no_op_when_flag_unset(self) -> None:
        pick = {"asset_class": "CRYPTO", "confidence": 0.85}
        self.cc.calibrate(pick)
        self.assertEqual(pick["confidence"], 0.85)
        self.assertNotIn("confidence_calibrated", pick)

    def test_passthrough_when_class_missing(self) -> None:
        os.environ["CONFIDENCE_CALIBRATION_ENABLED"] = "1"
        self.cc.reset_cache()
        pick = {"confidence": 0.5}
        self.cc.calibrate(pick)
        self.assertEqual(pick["confidence"], 0.5)
        self.assertNotIn("confidence_calibrated", pick)

    def test_passthrough_when_no_calibrator(self) -> None:
        os.environ["CONFIDENCE_CALIBRATION_ENABLED"] = "1"
        self.cc.reset_cache()
        pick = {"asset_class": "QUANTUM_DERIVATIVES", "confidence": 0.5}
        self.cc.calibrate(pick)
        self.assertEqual(pick["confidence"], 0.5)

    def test_crypto_calibration_active_when_artifact_exists(self) -> None:
        # Skip if no artifact has been fitted yet
        if not self.cc.CAL_PATH.exists():
            self.skipTest("calibrator artifact not fitted")
        os.environ["CONFIDENCE_CALIBRATION_ENABLED"] = "1"
        self.cc.reset_cache()
        pick = {"asset_class": "CRYPTO", "confidence": 0.85}
        self.cc.calibrate(pick)
        # confidence should change OR confidence_calibrated should be set
        self.assertTrue(pick.get("confidence_calibrated"))
        self.assertEqual(pick.get("confidence_raw"), 0.85)
        # Calibrated value must be in [0, 1]
        self.assertGreaterEqual(pick["confidence"], 0.0)
        self.assertLessEqual(pick["confidence"], 1.0)

    def test_isotonic_fit_can_represent_inverted_relationship(self) -> None:
        """Regression test for code-review H5: IsotonicRegression must allow
        direction flip (`increasing='auto'`) so CRYPTO/ETF inversion can
        actually be fit, not flattened by a forced increasing-monotonic."""
        # Synthetic inverted data: high X -> low Y
        x = ([0.10] * 30 + [0.20] * 30 + [0.30] * 30 + [0.40] * 30
             + [0.50] * 30 + [0.60] * 30 + [0.70] * 30 + [0.80] * 30)
        y = ([1] * 25 + [0] * 5
             + [1] * 22 + [0] * 8
             + [1] * 18 + [0] * 12
             + [1] * 15 + [0] * 15
             + [1] * 12 + [0] * 18
             + [1] * 8 + [0] * 22
             + [1] * 5 + [0] * 25
             + [1] * 2 + [0] * 28)
        table = self.cc._isotonic_fit(x, y)
        pred_at_low = self.cc._apply_isotonic(table, 0.10)
        pred_at_high = self.cc._apply_isotonic(table, 0.80)
        self.assertGreater(
            pred_at_low, pred_at_high,
            f"Isotonic fit must preserve inverted direction; got "
            f"pred(0.10)={pred_at_low:.3f} vs pred(0.80)={pred_at_high:.3f}. "
            "Likely cause: IsotonicRegression(increasing=True) default; "
            "use increasing='auto' instead."
        )


class SmartPicksWireUpTests(unittest.TestCase):
    """Ensure smart_picks_engine._compute_ml_composite calls calibrate()."""

    def test_wire_up_invokes_calibrator(self) -> None:
        os.environ.pop("CONFIDENCE_CALIBRATION_ENABLED", None)
        import alpha_engine.confidence_calibrator as cc
        importlib.reload(cc)
        import alpha_engine.smart_picks_engine as spe
        importlib.reload(spe)

        calls: list[dict] = []
        original = spe._calibrate_confidence

        def spy(pick):
            calls.append(pick)
            return original(pick)

        spe._calibrate_confidence = spy
        try:
            pick = {
                "asset_class": "CRYPTO",
                "confidence": 0.7,
                "ml_score": 0.4,
                "agreement_count": 2,
            }
            score, method = spe._compute_ml_composite(pick)
            self.assertEqual(len(calls), 1)
            self.assertIs(calls[0], pick)
            self.assertIsInstance(score, float)
            self.assertIsInstance(method, str)
        finally:
            spe._calibrate_confidence = original


if __name__ == "__main__":
    unittest.main()
