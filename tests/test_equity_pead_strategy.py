"""Tests for H-002: PEAD equity earnings drift shadow scanner.

All tests use mocks — no yfinance network calls.
Gate: EQUITY_PEAD_ENABLED (default OFF).
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from alpha_engine.equity_pead_strategy import equity_pead_signals, _PEAD_UNIVERSE


class TestPEADGate:

    def test_gate_off_by_default(self, monkeypatch):
        monkeypatch.delenv("EQUITY_PEAD_ENABLED", raising=False)
        assert equity_pead_signals() == []

    def test_gate_off_explicit_zero(self, monkeypatch):
        monkeypatch.setenv("EQUITY_PEAD_ENABLED", "0")
        assert equity_pead_signals() == []

    def test_gate_on_returns_list(self, monkeypatch):
        monkeypatch.setenv("EQUITY_PEAD_ENABLED", "1")
        # With empty universe, returns empty list without network
        result = equity_pead_signals(symbols=[])
        assert isinstance(result, list)


class TestPEADSignals:

    def _make_earnings_df(self, surprise: float):
        """Build a minimal DataFrame mimicking yfinance get_earnings_dates output."""
        import pandas as pd
        from datetime import datetime, timezone, timedelta

        est = 1.00
        actual = est * (1 + surprise / 100)
        idx = pd.DatetimeIndex(
            [datetime.now(timezone.utc) - timedelta(days=1)],
            tz="UTC",
        )
        return pd.DataFrame(
            {"Reported EPS": [actual], "EPS Estimate": [est]},
            index=idx,
        )

    def test_positive_surprise_generates_signal(self, monkeypatch):
        monkeypatch.setenv("EQUITY_PEAD_ENABLED", "1")

        mock_ticker = MagicMock()
        mock_ticker.get_earnings_dates.return_value = self._make_earnings_df(10.0)
        mock_ticker.fast_info.last_price = 150.0

        with patch("alpha_engine.equity_pead_strategy.yf", create=True) as mock_yf, \
             patch("alpha_engine.equity_pead_strategy._HAS_YFINANCE", True), \
             patch("alpha_engine.equity_pead_strategy._load_cache", return_value={}), \
             patch("alpha_engine.equity_pead_strategy._save_cache"):
            mock_yf.Ticker.return_value = mock_ticker
            result = equity_pead_signals(symbols=["AAPL"])

        assert len(result) == 1
        sig = result[0]
        assert sig["symbol"] == "AAPL"
        assert sig["strategy"] == "equity_pead"
        assert sig["signal_type"] == "BUY"
        assert sig["direction"] == "LONG"
        assert sig["asset_class"] == "EQUITY"
        assert sig["earnings_surprise_pct"] == 10.0
        assert sig["confidence"] >= 0.60
        assert sig["risk_reward"] >= 1.5
        assert sig["_pead_signal"] is True
        assert sig["_h002_shadow"] is True

    def test_sub_threshold_surprise_no_signal(self, monkeypatch):
        monkeypatch.setenv("EQUITY_PEAD_ENABLED", "1")

        mock_ticker = MagicMock()
        mock_ticker.get_earnings_dates.return_value = self._make_earnings_df(3.0)
        mock_ticker.fast_info.last_price = 150.0

        with patch("alpha_engine.equity_pead_strategy.yf", create=True) as mock_yf, \
             patch("alpha_engine.equity_pead_strategy._HAS_YFINANCE", True), \
             patch("alpha_engine.equity_pead_strategy._load_cache", return_value={}), \
             patch("alpha_engine.equity_pead_strategy._save_cache"):
            mock_yf.Ticker.return_value = mock_ticker
            result = equity_pead_signals(symbols=["AAPL"])

        assert result == []

    def test_negative_surprise_no_signal(self, monkeypatch):
        monkeypatch.setenv("EQUITY_PEAD_ENABLED", "1")

        mock_ticker = MagicMock()
        mock_ticker.get_earnings_dates.return_value = self._make_earnings_df(-8.0)
        mock_ticker.fast_info.last_price = 150.0

        with patch("alpha_engine.equity_pead_strategy.yf", create=True) as mock_yf, \
             patch("alpha_engine.equity_pead_strategy._HAS_YFINANCE", True), \
             patch("alpha_engine.equity_pead_strategy._load_cache", return_value={}), \
             patch("alpha_engine.equity_pead_strategy._save_cache"):
            mock_yf.Ticker.return_value = mock_ticker
            result = equity_pead_signals(symbols=["AAPL"])

        assert result == []

    def test_no_earnings_data_returns_empty(self, monkeypatch):
        monkeypatch.setenv("EQUITY_PEAD_ENABLED", "1")

        mock_ticker = MagicMock()
        mock_ticker.get_earnings_dates.return_value = None
        mock_ticker.fast_info.last_price = 150.0

        with patch("alpha_engine.equity_pead_strategy.yf", create=True) as mock_yf, \
             patch("alpha_engine.equity_pead_strategy._HAS_YFINANCE", True), \
             patch("alpha_engine.equity_pead_strategy._load_cache", return_value={}), \
             patch("alpha_engine.equity_pead_strategy._save_cache"):
            mock_yf.Ticker.return_value = mock_ticker
            result = equity_pead_signals(symbols=["AAPL"])

        assert result == []

    def test_yfinance_error_is_fail_open(self, monkeypatch):
        monkeypatch.setenv("EQUITY_PEAD_ENABLED", "1")

        with patch("alpha_engine.equity_pead_strategy.yf", create=True) as mock_yf, \
             patch("alpha_engine.equity_pead_strategy._HAS_YFINANCE", True), \
             patch("alpha_engine.equity_pead_strategy._load_cache", return_value={}), \
             patch("alpha_engine.equity_pead_strategy._save_cache"):
            mock_yf.Ticker.side_effect = RuntimeError("network error")
            result = equity_pead_signals(symbols=["AAPL"])

        assert result == []

    def test_stale_earnings_beyond_3_days_skipped(self, monkeypatch):
        """Earnings more than 3 days ago → skip (PEAD entry window closed)."""
        import pandas as pd
        from datetime import datetime, timezone, timedelta

        monkeypatch.setenv("EQUITY_PEAD_ENABLED", "1")

        # Set earnings date to 10 days ago — outside 3-day entry window
        mock_ticker = MagicMock()
        idx = pd.DatetimeIndex(
            [datetime.now(timezone.utc) - timedelta(days=10)],
            tz="UTC",
        )
        mock_ticker.get_earnings_dates.return_value = pd.DataFrame(
            {"Reported EPS": [1.10], "EPS Estimate": [1.00]},
            index=idx,
        )
        mock_ticker.fast_info.last_price = 150.0

        with patch("alpha_engine.equity_pead_strategy.yf", create=True) as mock_yf, \
             patch("alpha_engine.equity_pead_strategy._HAS_YFINANCE", True), \
             patch("alpha_engine.equity_pead_strategy._load_cache", return_value={}), \
             patch("alpha_engine.equity_pead_strategy._save_cache"):
            mock_yf.Ticker.return_value = mock_ticker
            result = equity_pead_signals(symbols=["AAPL"])

        assert result == []

    def test_confidence_scales_with_surprise(self, monkeypatch):
        monkeypatch.setenv("EQUITY_PEAD_ENABLED", "1")

        def make_ticker(surprise: float):
            mock_ticker = MagicMock()
            mock_ticker.get_earnings_dates.return_value = self._make_earnings_df(surprise)
            mock_ticker.fast_info.last_price = 150.0
            return mock_ticker

        confidences = []
        for surprise in [5.0, 10.0, 15.0]:
            with patch("alpha_engine.equity_pead_strategy.yf", create=True) as mock_yf, \
                 patch("alpha_engine.equity_pead_strategy._load_cache", return_value={}), \
                 patch("alpha_engine.equity_pead_strategy._save_cache"):
                mock_yf.Ticker.return_value = make_ticker(surprise)
                result = equity_pead_signals(symbols=["AAPL"])
                if result:
                    confidences.append(result[0]["confidence"])

        assert len(confidences) == 3
        assert confidences[0] <= confidences[1] <= confidences[2]
        assert all(0.60 <= c <= 0.75 for c in confidences)

    def test_universe_constants(self):
        assert len(_PEAD_UNIVERSE) >= 40
        assert "AAPL" in _PEAD_UNIVERSE
        assert "MSFT" in _PEAD_UNIVERSE
        assert "NVDA" in _PEAD_UNIVERSE
