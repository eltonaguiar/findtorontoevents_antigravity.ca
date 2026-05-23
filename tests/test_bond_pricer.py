"""Tests for alpha_engine.bond_pricer (network-free, synthetic curves)."""
from __future__ import annotations

import math
import random
import unittest

import pandas as pd

from alpha_engine.bond_pricer import (
    credit_spread_zscore,
    krd_profile,
    price_treasury,
)


def _flat_curve(rate_pct: float = 4.0) -> pd.DataFrame:
    cols = ["DGS1MO", "DGS3MO", "DGS6MO", "DGS1", "DGS2", "DGS3",
            "DGS5", "DGS7", "DGS10", "DGS20", "DGS30"]
    return pd.DataFrame(
        [[rate_pct] * len(cols)],
        index=pd.to_datetime(["2026-04-28"]), columns=cols,
    )


class PriceTreasuryTests(unittest.TestCase):
    def test_4pct_coupon_on_4pct_flat_curve_is_par(self):
        out = price_treasury(coupon=0.04, maturity=10.0, curve_df=_flat_curve(4.0))
        self.assertAlmostEqual(out["price"], 100.0, places=2)
        self.assertAlmostEqual(out["ytm"], 0.04, places=4)
        # 10Y 4% par bond modified duration ~ 8.17 years (semiannual).
        self.assertGreater(out["dur"], 7.5)
        self.assertLess(out["dur"], 8.6)
        self.assertAlmostEqual(out["dv01"], out["dur"] * out["price"] * 1e-4,
                               places=6)

    def test_premium_when_coupon_above_curve(self):
        out = price_treasury(coupon=0.05, maturity=5.0, curve_df=_flat_curve(2.0))
        self.assertGreater(out["price"], 100.0)
        self.assertLess(out["ytm"], 0.05)

    def test_discount_when_coupon_below_curve(self):
        out = price_treasury(coupon=0.02, maturity=5.0, curve_df=_flat_curve(6.0))
        self.assertLess(out["price"], 100.0)
        self.assertGreater(out["ytm"], 0.02)

    def test_empty_curve_raises(self):
        with self.assertRaises(ValueError):
            price_treasury(coupon=0.04, maturity=10.0, curve_df=pd.DataFrame())


class KrdProfileTests(unittest.TestCase):
    def test_default_buckets_present(self):
        prof = krd_profile({"coupon": 0.04, "maturity": 10.0}, _flat_curve(4.0))
        for k in ("2Y", "5Y", "10Y", "30Y"):
            self.assertIn(k, prof)
            self.assertTrue(math.isfinite(prof[k]))

    def test_krd_sum_approximates_total_duration(self):
        # Single-knot bumps + linear interp -> approximate, not algebraically
        # identical to a parallel shift. Allow ±50% slack.
        prof = krd_profile(
            {"coupon": 0.04, "maturity": 10.0}, _flat_curve(4.0),
            key_tenors=("1M", "3M", "6M", "1Y", "2Y", "3Y", "5Y",
                        "7Y", "10Y", "20Y", "30Y"),
        )
        total = prof["_total_dur"]
        bucket_sum = sum(v for k, v in prof.items() if not k.startswith("_"))
        self.assertGreater(total, 0)
        self.assertGreater(bucket_sum, 0.5 * total)
        self.assertLess(bucket_sum, 1.5 * total)

    def test_unknown_tenor_skipped(self):
        prof = krd_profile(
            {"coupon": 0.04, "maturity": 10.0}, _flat_curve(4.0),
            key_tenors=("10Y", "BOGUS"),
        )
        self.assertIn("10Y", prof)
        self.assertNotIn("BOGUS", prof)


class CreditSpreadZScoreTests(unittest.TestCase):
    def test_zscore_zero_variance_is_nan(self):
        s = pd.Series([2.5] * 61)
        self.assertTrue(math.isnan(credit_spread_zscore(s, lookback=60)))

    def test_zscore_high_when_latest_above_window(self):
        random.seed(0)
        window = [2.5 + random.uniform(-0.05, 0.05) for _ in range(60)]
        z = credit_spread_zscore(pd.Series(window + [3.5]), lookback=60)
        self.assertGreater(z, 5.0)

    def test_zscore_low_when_latest_below_window(self):
        random.seed(0)
        window = [2.5 + random.uniform(-0.05, 0.05) for _ in range(60)]
        z = credit_spread_zscore(pd.Series(window + [1.5]), lookback=60)
        self.assertLess(z, -5.0)

    def test_insufficient_data_returns_nan(self):
        z = credit_spread_zscore(pd.Series([1.0, 2.0, 3.0]), lookback=60)
        self.assertTrue(math.isnan(z))


if __name__ == "__main__":
    unittest.main()
