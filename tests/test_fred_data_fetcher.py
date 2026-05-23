"""Tests for alpha_engine.fred_data_fetcher (network-free; Fred is mocked)."""
from __future__ import annotations

import os
import shutil
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pandas as pd

import alpha_engine.fred_data_fetcher as ff


def _synthetic(sid: str, n: int = 60, base: float = 4.0) -> pd.Series:
    end = datetime.utcnow().date()
    idx = pd.to_datetime([end - timedelta(days=n - 1 - i) for i in range(n)])
    return pd.Series([base + 0.01 * i for i in range(n)], index=idx, name=sid)


class _FakeFred:
    def __init__(self, *_, **__):
        self.calls: list[str] = []

    def get_series(self, sid, observation_start=None, observation_end=None):
        self.calls.append(sid)
        if sid == "BAMLH0A0HYM2":  # HY OAS
            return _synthetic(sid, base=3.5)
        if sid == "BAMLC0A0CM":    # IG OAS
            return _synthetic(sid, base=1.2)
        return _synthetic(sid)


class FredDataFetcherTests(unittest.TestCase):
    def setUp(self):
        self._orig_cache = ff.CACHE_DIR
        self.tmp_cache = Path(__file__).resolve().parent / "_tmp_fred_cache"
        if self.tmp_cache.exists():
            shutil.rmtree(self.tmp_cache, ignore_errors=True)
        self.tmp_cache.mkdir(parents=True, exist_ok=True)
        ff.CACHE_DIR = self.tmp_cache
        self._prev_key = os.environ.pop("FRED_API_KEY", None)

    def tearDown(self):
        ff.CACHE_DIR = self._orig_cache
        shutil.rmtree(self.tmp_cache, ignore_errors=True)
        if self._prev_key is not None:
            os.environ["FRED_API_KEY"] = self._prev_key

    def test_missing_api_key_raises_clear_error(self):
        with self.assertRaises(ff.MissingFredApiKey) as ctx:
            ff.get_treasury_curve("2024-01-01", "2024-02-01")
        self.assertIn("FRED_API_KEY", str(ctx.exception))
        self.assertIn("https://fred.stlouisfed.org", str(ctx.exception))

    def test_unknown_credit_grade_raises(self):
        os.environ["FRED_API_KEY"] = "k"
        with self.assertRaises(ValueError):
            ff.get_credit_spread(grade="NOT_A_GRADE")

    def test_get_treasury_curve_returns_canonical_columns(self):
        os.environ["FRED_API_KEY"] = "k"
        with patch.object(ff, "_build_fred_client", return_value=_FakeFred()):
            df = ff.get_treasury_curve("2024-01-01", "2024-03-01", use_cache=False)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(list(df.columns), list(ff.TREASURY_CURVE_SERIES.keys()))
        for col in df.columns:
            self.assertGreater(df[col].dropna().size, 0)
        self.assertTrue(df.index.is_monotonic_increasing)

    def test_get_credit_spread_hyg_lqd_is_difference(self):
        os.environ["FRED_API_KEY"] = "k"
        with patch.object(ff, "_build_fred_client", return_value=_FakeFred()):
            spread = ff.get_credit_spread(
                "HYG_LQD",
                date_from="2024-01-01", date_to="2024-03-01",
                use_cache=False,
            )
        # HY base 3.5, IG base 1.2 -> spread first point ~2.3.
        self.assertAlmostEqual(float(spread.iloc[0]), 2.3, places=2)
        self.assertEqual(spread.name, "HYG_LQD_spread")

    def test_get_credit_spread_hy_returns_raw(self):
        os.environ["FRED_API_KEY"] = "k"
        with patch.object(ff, "_build_fred_client", return_value=_FakeFred()):
            s = ff.get_credit_spread(
                "HY",
                date_from="2024-01-01", date_to="2024-03-01",
                use_cache=False,
            )
        self.assertEqual(s.name, "HY_OAS")
        self.assertAlmostEqual(float(s.iloc[0]), 3.5, places=2)

    def test_get_term_premium_calls_t10y2y(self):
        os.environ["FRED_API_KEY"] = "k"
        fake = _FakeFred()
        with patch.object(ff, "_build_fred_client", return_value=fake):
            s = ff.get_term_premium(use_cache=False)
        self.assertEqual(s.name, "term_premium_10y2y")
        self.assertIn("T10Y2Y", fake.calls)

    def test_get_breakeven_inflation_calls_t10yie(self):
        os.environ["FRED_API_KEY"] = "k"
        fake = _FakeFred()
        with patch.object(ff, "_build_fred_client", return_value=fake):
            s = ff.get_breakeven_inflation(use_cache=False)
        self.assertEqual(s.name, "breakeven_inflation_10y")
        self.assertIn("T10YIE", fake.calls)

    def test_cache_hit_avoids_second_network_call(self):
        os.environ["FRED_API_KEY"] = "k"
        fake = _FakeFred()
        with patch.object(ff, "_build_fred_client", return_value=fake):
            ff.get_term_premium(date_from="2024-01-01", date_to="2024-03-01")
            n1 = list(fake.calls)
            ff.get_term_premium(date_from="2024-01-01", date_to="2024-03-01")
            self.assertEqual(fake.calls, n1)
            ff.get_term_premium(date_from="2024-01-01", date_to="2024-03-01",
                                use_cache=False)
            self.assertEqual(len(fake.calls), len(n1) + 1)

    def test_date_objects_accepted(self):
        os.environ["FRED_API_KEY"] = "k"
        with patch.object(ff, "_build_fred_client", return_value=_FakeFred()):
            s = ff.get_term_premium(
                date_from=date(2024, 1, 1),
                date_to=datetime(2024, 3, 1),
                use_cache=False,
            )
        self.assertGreater(len(s), 0)


if __name__ == "__main__":
    unittest.main()
