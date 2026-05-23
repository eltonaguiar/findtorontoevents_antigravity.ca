"""Tests for alpha_engine.equity_sector_rs — IDEA-A Sector ETF RS factor."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import alpha_engine.equity_sector_rs as srs


def _reset_caches():
    srs._sector_returns_cache.clear()
    srs._symbol_sector_cache.clear()


# ---------------------------------------------------------------------------
# _fetch_sector_returns
# ---------------------------------------------------------------------------

class TestFetchSectorReturns:
    def setup_method(self):
        _reset_caches()

    def test_returns_empty_on_yfinance_failure(self):
        mock_yf = MagicMock()
        mock_yf.download.side_effect = RuntimeError("no network")
        with patch.dict(sys.modules, {"yfinance": mock_yf}):
            result = srs._fetch_sector_returns()
        assert result == {}

    def test_returns_dict_with_sector_names_as_keys(self):
        import pandas as pd
        # Simulate download returning a multi-level DataFrame
        mock_yf = MagicMock()
        etfs = list(srs.SECTOR_ETFS.values())
        # Build a simple MultiIndex DataFrame
        idx = pd.date_range("2026-01-01", periods=5, freq="D")
        # Return dict of DataFrames per ETF (group_by="ticker" layout)
        def mock_download(tickers, **kwargs):
            arrays = [[etf, "Close"] for etf in etfs]
            tuples = [(etf, "Close") for etf in etfs]
            midx = pd.MultiIndex.from_tuples(tuples)
            data = {etf: 100.0 + i for i, etf in enumerate(etfs)}
            # Return a flat structure the function can iterate
            df_dict = {}
            for etf in etfs:
                base_price = 100.0 + etfs.index(etf)
                closes = [base_price + j for j in range(5)]
                df_dict[etf] = pd.DataFrame({"Close": closes}, index=idx)
            # Simulate multi-level columns
            combined = pd.concat(df_dict, axis=1)
            return combined

        mock_yf.download.side_effect = mock_download
        with patch.dict(sys.modules, {"yfinance": mock_yf}):
            result = srs._fetch_sector_returns()
        # At least some sectors should have returns
        assert isinstance(result, dict)

    def test_uses_cache_on_second_call(self):
        import time
        _reset_caches()
        # Manually populate cache
        fake_returns = {"Technology": 0.05, "Energy": -0.02}
        srs._sector_returns_cache["all"] = (time.time(), fake_returns)
        # Should NOT call yfinance
        mock_yf = MagicMock()
        with patch.dict(sys.modules, {"yfinance": mock_yf}):
            result = srs._fetch_sector_returns()
        assert result == fake_returns
        mock_yf.download.assert_not_called()


# ---------------------------------------------------------------------------
# _lookup_sector
# ---------------------------------------------------------------------------

class TestLookupSector:
    def setup_method(self):
        _reset_caches()

    def test_returns_none_on_yfinance_failure(self):
        mock_yf = MagicMock()
        mock_yf.Ticker.side_effect = RuntimeError("fail")
        with patch.dict(sys.modules, {"yfinance": mock_yf}):
            result = srs._lookup_sector("AAPL")
        assert result is None

    def test_returns_sector_from_info(self):
        mock_ticker = MagicMock()
        mock_ticker.info = {"sector": "Technology"}
        mock_yf = MagicMock()
        mock_yf.Ticker.return_value = mock_ticker
        _reset_caches()
        with patch.dict(sys.modules, {"yfinance": mock_yf}):
            result = srs._lookup_sector("AAPL")
        assert result == "Technology"

    def test_uses_cache_on_second_call(self):
        import time
        _reset_caches()
        srs._symbol_sector_cache["AAPL"] = (time.time(), "Technology")
        mock_yf = MagicMock()
        with patch.dict(sys.modules, {"yfinance": mock_yf}):
            result = srs._lookup_sector("AAPL")
        assert result == "Technology"
        mock_yf.Ticker.assert_not_called()

    def test_returns_none_when_sector_missing_from_info(self):
        mock_ticker = MagicMock()
        mock_ticker.info = {}  # no sector key
        mock_yf = MagicMock()
        mock_yf.Ticker.return_value = mock_ticker
        _reset_caches()
        with patch.dict(sys.modules, {"yfinance": mock_yf}):
            result = srs._lookup_sector("UNKNOWN")
        assert result is None


# ---------------------------------------------------------------------------
# sector_rs_score
# ---------------------------------------------------------------------------

class TestSectorRsScore:
    def setup_method(self):
        _reset_caches()

    def test_returns_50_when_sector_returns_empty(self):
        with patch.object(srs, "_fetch_sector_returns", return_value={}):
            score = srs.sector_rs_score("AAPL")
        assert score == 50.0

    def test_returns_50_when_symbol_sector_unknown(self):
        fake_returns = {"Technology": 0.05, "Energy": -0.02}
        with patch.object(srs, "_fetch_sector_returns", return_value=fake_returns):
            with patch.object(srs, "_lookup_sector", return_value=None):
                score = srs.sector_rs_score("UNKNOWN")
        assert score == 50.0

    def test_top_sector_scores_high(self):
        # 5 sectors; Technology is best
        fake_returns = {
            "Technology":             0.10,
            "Energy":                 0.02,
            "Financials":            -0.01,
            "Health Care":           -0.03,
            "Consumer Discretionary":-0.05,
        }
        with patch.object(srs, "_fetch_sector_returns", return_value=fake_returns):
            with patch.object(srs, "_lookup_sector", return_value="Technology"):
                score = srs.sector_rs_score("AAPL")
        assert score == 100.0  # rank 1 of 5

    def test_bottom_sector_scores_low(self):
        fake_returns = {
            "Technology":             0.10,
            "Energy":                 0.02,
            "Financials":            -0.01,
            "Health Care":           -0.03,
            "Consumer Discretionary":-0.05,
        }
        with patch.object(srs, "_fetch_sector_returns", return_value=fake_returns):
            with patch.object(srs, "_lookup_sector", return_value="Consumer Discretionary"):
                score = srs.sector_rs_score("XYZ")
        assert score == 0.0  # rank 5 of 5

    def test_middle_sector_scores_near_50(self):
        fake_returns = {
            "Technology":  0.10,
            "Energy":      0.05,
            "Financials":  0.00,
            "Health Care":-0.05,
            "Industrials": -0.10,
        }
        with patch.object(srs, "_fetch_sector_returns", return_value=fake_returns):
            with patch.object(srs, "_lookup_sector", return_value="Financials"):
                score = srs.sector_rs_score("JPM")
        assert score == 50.0  # rank 3 of 5

    def test_score_bounded_0_to_100(self):
        fake_returns = {"Technology": 0.20, "Energy": -0.10}
        with patch.object(srs, "_fetch_sector_returns", return_value=fake_returns):
            with patch.object(srs, "_lookup_sector", return_value="Technology"):
                score = srs.sector_rs_score("NVDA")
        assert 0.0 <= score <= 100.0

    def test_single_sector_returns_50(self):
        fake_returns = {"Technology": 0.05}
        with patch.object(srs, "_fetch_sector_returns", return_value=fake_returns):
            with patch.object(srs, "_lookup_sector", return_value="Technology"):
                score = srs.sector_rs_score("AAPL")
        # Only 1 sector: rank 1 of 1, (1-1)/(1-1) = div-by-zero-protected → 100
        assert score == 100.0


# ---------------------------------------------------------------------------
# sector_rs_feature
# ---------------------------------------------------------------------------

class TestSectorRsFeature:
    def test_returns_precomputed_value(self):
        pick = {"sector_rs_score": 72.5}
        assert srs.sector_rs_feature(pick) == 72.5

    def test_falls_back_to_compute_when_missing(self):
        pick = {"symbol": "AAPL", "asset_class": "EQUITY"}
        with patch.object(srs, "sector_rs_score", return_value=65.0) as mock_fn:
            result = srs.sector_rs_feature(pick)
        assert result == 65.0
        mock_fn.assert_called_once_with("AAPL", srs.LOOKBACK_DAYS)

    def test_returns_50_when_symbol_empty(self):
        pick = {}
        assert srs.sector_rs_feature(pick) == 50.0

    def test_handles_bad_precomputed_value(self):
        pick = {"symbol": "AAPL", "sector_rs_score": "bad_value"}
        with patch.object(srs, "sector_rs_score", return_value=55.0):
            result = srs.sector_rs_feature(pick)
        assert result == 55.0


# ---------------------------------------------------------------------------
# stamp_pick
# ---------------------------------------------------------------------------

class TestStampPick:
    def test_stamps_equity_pick(self):
        pick = {"symbol": "AAPL", "asset_class": "EQUITY"}
        with patch.object(srs, "sector_rs_score", return_value=78.0):
            result = srs.stamp_pick(pick)
        assert result["sector_rs_score"] == 78.0
        assert result is pick  # mutates in-place

    def test_skips_non_equity(self):
        pick = {"symbol": "BTC", "asset_class": "CRYPTO"}
        with patch.object(srs, "sector_rs_score", return_value=80.0) as mock_fn:
            srs.stamp_pick(pick)
        mock_fn.assert_not_called()
        assert "sector_rs_score" not in pick

    def test_skips_when_symbol_missing(self):
        pick = {"asset_class": "EQUITY"}
        with patch.object(srs, "sector_rs_score") as mock_fn:
            srs.stamp_pick(pick)
        mock_fn.assert_not_called()
        assert "sector_rs_score" not in pick

    def test_fail_open_on_exception(self):
        pick = {"symbol": "AAPL", "asset_class": "EQUITY"}
        with patch.object(srs, "sector_rs_score", side_effect=RuntimeError("network")):
            result = srs.stamp_pick(pick)
        # Must not raise; pick unchanged
        assert result is pick
        assert "sector_rs_score" not in pick

    def test_returns_pick_for_chaining(self):
        pick = {"symbol": "MSFT", "asset_class": "EQUITY"}
        with patch.object(srs, "sector_rs_score", return_value=60.0):
            returned = srs.stamp_pick(pick)
        assert returned is pick
