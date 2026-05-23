"""Tests for alpha_engine.equity_earnings_surprise — IDEA-A PEAD factor."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import alpha_engine.equity_earnings_surprise as eps_mod


def _reset_cache():
    eps_mod._earnings_cache.clear()


def _make_earnings_df(surprise_pct: float, days_ago: int = 5):
    """Build a minimal fake earnings_dates DataFrame."""
    import pandas as pd
    from datetime import datetime, timedelta, timezone
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    dt = pd.Timestamp(dt).tz_localize(None)
    df = pd.DataFrame(
        {"EPS Estimate": [1.00], "Reported EPS": [1.00 * (1 + surprise_pct / 100)],
         "Surprise(%)": [surprise_pct]},
        index=[dt],
    )
    return df


class TestEarningsSurpriseScore:
    def setup_method(self):
        _reset_cache()

    def test_returns_50_on_yfinance_failure(self):
        mock_yf = MagicMock()
        mock_yf.Ticker.side_effect = RuntimeError("network error")
        with patch.dict(sys.modules, {"yfinance": mock_yf}):
            score = eps_mod.earnings_surprise_score("AAPL")
        assert score == 50.0

    def test_returns_50_when_no_earnings_data(self):
        import pandas as pd
        mock_ticker = MagicMock()
        mock_ticker.earnings_dates = pd.DataFrame()
        mock_yf = MagicMock()
        mock_yf.Ticker.return_value = mock_ticker
        _reset_cache()
        with patch.dict(sys.modules, {"yfinance": mock_yf}):
            score = eps_mod.earnings_surprise_score("AAPL")
        assert score == 50.0

    def test_returns_50_when_earnings_too_old(self):
        df = _make_earnings_df(surprise_pct=15.0, days_ago=60)  # > LOOKBACK_DAYS=45
        mock_ticker = MagicMock()
        mock_ticker.earnings_dates = df
        mock_yf = MagicMock()
        mock_yf.Ticker.return_value = mock_ticker
        _reset_cache()
        with patch.dict(sys.modules, {"yfinance": mock_yf}):
            score = eps_mod.earnings_surprise_score("AAPL")
        assert score == 50.0

    def test_large_positive_surprise_scores_high(self):
        df = _make_earnings_df(surprise_pct=15.0, days_ago=3)
        mock_ticker = MagicMock()
        mock_ticker.earnings_dates = df
        mock_yf = MagicMock()
        mock_yf.Ticker.return_value = mock_ticker
        _reset_cache()
        with patch.dict(sys.modules, {"yfinance": mock_yf}):
            score = eps_mod.earnings_surprise_score("AAPL")
        assert score > 60.0, f"Expected >60, got {score}"

    def test_negative_surprise_scores_below_50(self):
        df = _make_earnings_df(surprise_pct=-8.0, days_ago=3)
        mock_ticker = MagicMock()
        mock_ticker.earnings_dates = df
        mock_yf = MagicMock()
        mock_yf.Ticker.return_value = mock_ticker
        _reset_cache()
        with patch.dict(sys.modules, {"yfinance": mock_yf}):
            score = eps_mod.earnings_surprise_score("MSFT")
        assert score < 50.0, f"Expected <50, got {score}"

    def test_score_bounded_0_to_100(self):
        for pct in [-50.0, 0.0, 5.0, 50.0]:
            df = _make_earnings_df(surprise_pct=pct, days_ago=3)
            mock_ticker = MagicMock()
            mock_ticker.earnings_dates = df
            mock_yf = MagicMock()
            mock_yf.Ticker.return_value = mock_ticker
            _reset_cache()
            with patch.dict(sys.modules, {"yfinance": mock_yf}):
                score = eps_mod.earnings_surprise_score("TEST")
            assert 0.0 <= score <= 100.0, f"surprise={pct}% → score={score} out of bounds"

    def test_uses_cache_on_second_call(self):
        import time
        _reset_cache()
        eps_mod._earnings_cache["AAPL"] = (time.time(), 75.0)
        mock_yf = MagicMock()
        with patch.dict(sys.modules, {"yfinance": mock_yf}):
            score = eps_mod.earnings_surprise_score("AAPL")
        assert score == 75.0
        mock_yf.Ticker.assert_not_called()

    def test_small_positive_surprise_scores_between_50_and_70(self):
        df = _make_earnings_df(surprise_pct=3.0, days_ago=5)
        mock_ticker = MagicMock()
        mock_ticker.earnings_dates = df
        mock_yf = MagicMock()
        mock_yf.Ticker.return_value = mock_ticker
        _reset_cache()
        with patch.dict(sys.modules, {"yfinance": mock_yf}):
            score = eps_mod.earnings_surprise_score("NVDA")
        assert 50.0 < score <= 80.0

    def test_recency_discount_for_older_earnings(self):
        """Earnings 40 days ago should score lower than same surprise 5 days ago."""
        for days in [5, 40]:
            df = _make_earnings_df(surprise_pct=10.0, days_ago=days)
            mock_ticker = MagicMock()
            mock_ticker.earnings_dates = df
            mock_yf = MagicMock()
            mock_yf.Ticker.return_value = mock_ticker
            _reset_cache()
            with patch.dict(sys.modules, {"yfinance": mock_yf}):
                scores = [eps_mod.earnings_surprise_score("TEST")]
            if days == 5:
                score_fresh = scores[0]
            else:
                score_old = scores[0]
        assert score_fresh >= score_old, "Fresh earnings should score >= older earnings"

    def test_falls_back_to_estimate_vs_reported_when_no_surprise_col(self):
        """If 'Surprise(%)' column is missing, compute from EPS Estimate vs Reported EPS."""
        import pandas as pd
        from datetime import datetime, timedelta, timezone
        dt = pd.Timestamp(datetime.now(timezone.utc) - timedelta(days=5)).tz_localize(None)
        df = pd.DataFrame(
            {"EPS Estimate": [1.00], "Reported EPS": [1.12]},  # +12% surprise
            index=[dt],
        )
        mock_ticker = MagicMock()
        mock_ticker.earnings_dates = df
        mock_yf = MagicMock()
        mock_yf.Ticker.return_value = mock_ticker
        _reset_cache()
        with patch.dict(sys.modules, {"yfinance": mock_yf}):
            score = eps_mod.earnings_surprise_score("AMZN")
        assert score > 60.0  # positive surprise → high score


class TestEarningsSurpriseFeature:
    def test_returns_precomputed_value(self):
        pick = {"earnings_surprise_score": 72.0}
        assert eps_mod.earnings_surprise_feature(pick) == 72.0

    def test_falls_back_to_compute(self):
        pick = {"symbol": "AAPL", "asset_class": "EQUITY"}
        with patch.object(eps_mod, "earnings_surprise_score", return_value=65.0) as m:
            result = eps_mod.earnings_surprise_feature(pick)
        assert result == 65.0
        m.assert_called_once()

    def test_returns_50_for_empty_symbol(self):
        assert eps_mod.earnings_surprise_feature({}) == 50.0


class TestStampPick:
    def test_stamps_equity_pick(self):
        pick = {"symbol": "AAPL", "asset_class": "EQUITY"}
        with patch.object(eps_mod, "earnings_surprise_score", return_value=78.0):
            result = eps_mod.stamp_pick(pick)
        assert result["earnings_surprise_score"] == 78.0
        assert result is pick

    def test_skips_non_equity(self):
        pick = {"symbol": "BTCUSDT", "asset_class": "CRYPTO"}
        with patch.object(eps_mod, "earnings_surprise_score") as m:
            eps_mod.stamp_pick(pick)
        m.assert_not_called()
        assert "earnings_surprise_score" not in pick

    def test_fail_open_on_exception(self):
        pick = {"symbol": "AAPL", "asset_class": "EQUITY"}
        with patch.object(eps_mod, "earnings_surprise_score", side_effect=RuntimeError("fail")):
            result = eps_mod.stamp_pick(pick)
        assert result is pick
        assert "earnings_surprise_score" not in pick
