"""Tests for the qlib Alpha158-family factors added to technical_features.py
(2026-05-17): volume ratio, price-volume correlation, realized volatility.

Pure-function, deterministic — no network / DB. Mirrors the repo CI suite.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "alpha_engine"))

from technical_features import (  # noqa: E402
    compute_all_from_klines,
    compute_price_volume_corr,
    compute_realized_vol,
    compute_technical_features,
    compute_volume_ratio,
)

_NEW_KEYS = ("vol_ratio", "pv_corr30", "realized_vol30")


class PriceVolumeCorrTests(unittest.TestCase):
    def test_rising_price_rising_volume_corr_near_plus_one(self):
        closes = [100 + i for i in range(40)]
        volumes = [1000 + i * 10 for i in range(40)]
        self.assertGreater(compute_price_volume_corr(closes, volumes), 0.95)

    def test_rising_price_falling_volume_corr_near_minus_one(self):
        closes = [100 + i for i in range(40)]
        volumes = [2000 - i * 10 for i in range(40)]
        self.assertLess(compute_price_volume_corr(closes, volumes), -0.95)

    def test_corr_bounded(self):
        closes = [100 + (i % 7) for i in range(40)]
        volumes = [500 + (i % 3) * 100 for i in range(40)]
        c = compute_price_volume_corr(closes, volumes)
        self.assertGreaterEqual(c, -1.0)
        self.assertLessEqual(c, 1.0)

    def test_insufficient_data_returns_zero(self):
        self.assertEqual(compute_price_volume_corr([1, 2, 3], [1, 2, 3]), 0.0)

    def test_flat_volume_no_div_by_zero(self):
        closes = [100 + i for i in range(40)]
        self.assertEqual(compute_price_volume_corr(closes, [500] * 40), 0.0)


class VolumeRatioTests(unittest.TestCase):
    def test_expanding_volume_positive(self):
        volumes = [1000 + i * 50 for i in range(40)]
        self.assertGreater(compute_volume_ratio(volumes), 0.0)

    def test_flat_volume_near_zero(self):
        self.assertAlmostEqual(compute_volume_ratio([1000] * 40), 0.0, places=6)

    def test_bounded(self):
        volumes = [10 ** (i % 5) for i in range(40)]
        v = compute_volume_ratio(volumes)
        self.assertGreaterEqual(v, -1.0)
        self.assertLessEqual(v, 1.0)

    def test_insufficient_data_returns_zero(self):
        self.assertEqual(compute_volume_ratio([1, 2, 3]), 0.0)


class RealizedVolTests(unittest.TestCase):
    def test_smooth_series_low_vol(self):
        closes = [100 + i * 0.1 for i in range(40)]
        self.assertLess(compute_realized_vol(closes), 0.1)

    def test_choppy_series_higher_vol(self):
        closes = [100 * (1.05 if i % 2 else 0.95) for i in range(40)]
        self.assertGreater(compute_realized_vol(closes), 0.1)

    def test_bounded_and_non_negative(self):
        closes = [100 * (3.0 if i % 2 else 0.3) for i in range(40)]
        v = compute_realized_vol(closes)
        self.assertGreaterEqual(v, 0.0)
        self.assertLessEqual(v, 1.0)

    def test_insufficient_data_returns_zero(self):
        self.assertEqual(compute_realized_vol([100, 101]), 0.0)


class IntegrationTests(unittest.TestCase):
    def test_compute_technical_features_emits_new_keys(self):
        closes = [100 + i * 0.5 for i in range(60)]
        highs = [c + 1 for c in closes]
        lows = [c - 1 for c in closes]
        volumes = [1000 + i * 20 for i in range(60)]
        feats = compute_technical_features(closes, highs, lows, volumes)
        for k in _NEW_KEYS:
            self.assertIn(k, feats)

    def test_fallback_dicts_include_new_keys(self):
        # empty + too-short inputs both hit the fallback dicts
        for bad in ([], [[0, 1, 1, 1, 1, 1]] * 5):
            feats = compute_all_from_klines(bad)
            for k in _NEW_KEYS:
                self.assertIn(k, feats, f"fallback missing {k}")

    def test_klines_path_emits_new_keys(self):
        closes = [100 + i for i in range(60)]
        volumes = [1000 + i * 5 for i in range(60)]
        klines = [[0, c, c + 1, c - 1, c, v] for c, v in zip(closes, volumes)]
        feats = compute_all_from_klines(klines)
        for k in _NEW_KEYS:
            self.assertIn(k, feats)


if __name__ == "__main__":
    unittest.main()
