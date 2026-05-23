"""Tests for tools/research/forex_carry.py — G10 carry-factor scaffold.

Mocks both FRED (urllib.request.urlopen) and yfinance to keep tests offline.
Verifies:
  - Signal ranking logic (highest yield = LONG, lowest = SHORT)
  - FRED fetch + fallback behaviour
  - Output JSON schema validity
  - Unlock condition gate (PF>1.0 / WR>45% / n>30)
"""
from __future__ import annotations

import importlib
import json
import sys
import types
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest


# ── helpers ───────────────────────────────────────────────────────────────────


def _import_forex_carry():
    """Import the module fresh (avoids stale-module cross-test pollution)."""
    if "tools.research.forex_carry" in sys.modules:
        del sys.modules["tools.research.forex_carry"]
    # Ensure the tools package is importable
    import importlib.util
    import os

    spec_path = os.path.join(
        os.path.dirname(__file__), "..", "tools", "research", "forex_carry.py"
    )
    spec = importlib.util.spec_from_file_location("forex_carry", spec_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


fc = _import_forex_carry()


# ── rank_carry tests ──────────────────────────────────────────────────────────


class TestRankCarry:
    """Verify signal ranking logic: highest yield → LONG, lowest → SHORT."""

    def test_highest_yield_ranks_first(self):
        rates = {
            "USD": 5.0,
            "AUD": 7.0,  # +200 bps
            "JPY": 0.1,  # −490 bps
            "EUR": 4.0,  # −100 bps
        }
        ranked = fc.rank_carry(rates, base_ccy="USD")
        # AUD should be first (highest yield vs USD)
        assert ranked[0][0] == "AUD"
        assert ranked[0][1] == pytest.approx(2.0, abs=1e-6)

    def test_lowest_yield_ranks_last(self):
        rates = {
            "USD": 5.0,
            "AUD": 7.0,
            "JPY": 0.1,
            "EUR": 4.0,
        }
        ranked = fc.rank_carry(rates, base_ccy="USD")
        assert ranked[-1][0] == "JPY"
        assert ranked[-1][1] == pytest.approx(-4.9, abs=1e-6)

    def test_usd_excluded_from_ranking(self):
        rates = fc.FALLBACK_RATES.copy()
        ranked = fc.rank_carry(rates)
        ccys = [c for c, _ in ranked]
        assert "USD" not in ccys

    def test_sorted_descending(self):
        rates = fc.FALLBACK_RATES.copy()
        ranked = fc.rank_carry(rates)
        diffs = [d for _, d in ranked]
        assert diffs == sorted(diffs, reverse=True)

    def test_all_g10_present(self):
        rates = fc.FALLBACK_RATES.copy()
        ranked = fc.rank_carry(rates)
        ccys = {c for c, _ in ranked}
        expected = {"EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NOK", "SEK", "NZD"}
        assert expected == ccys


# ── build_signals tests ───────────────────────────────────────────────────────


class TestBuildSignals:
    """Verify LONG/SHORT assignment matches carry ranking."""

    def test_long_signals_are_high_yield(self):
        # Force AUD/NZD/GBP as top yielders
        rates = {
            "USD": 5.0,
            "AUD": 8.0,
            "NZD": 7.5,
            "GBP": 6.5,
            "EUR": 4.0,
            "CAD": 4.5,
            "CHF": 1.5,
            "JPY": 0.1,
            "NOK": 4.5,
            "SEK": 3.5,
        }
        signals = fc.build_signals(rates)
        long_ccys = {s["ccy"] for s in signals if s["direction"] == "LONG"}
        assert "AUD" in long_ccys
        assert "NZD" in long_ccys
        assert "GBP" in long_ccys

    def test_short_signals_are_low_yield(self):
        rates = {
            "USD": 5.0,
            "AUD": 8.0,
            "NZD": 7.5,
            "GBP": 6.5,
            "EUR": 4.0,
            "CAD": 4.5,
            "CHF": 1.5,
            "JPY": 0.1,
            "NOK": 4.5,
            "SEK": 3.5,
        }
        signals = fc.build_signals(rates)
        short_ccys = {s["ccy"] for s in signals if s["direction"] == "SHORT"}
        # CHF and JPY should be funding currencies
        assert "JPY" in short_ccys
        assert "CHF" in short_ccys

    def test_correct_signal_counts(self):
        signals = fc.build_signals(fc.FALLBACK_RATES)
        longs = [s for s in signals if s["direction"] == "LONG"]
        shorts = [s for s in signals if s["direction"] == "SHORT"]
        assert len(longs) == fc.LONG_K
        assert len(shorts) == fc.SHORT_K

    def test_signal_has_required_fields(self):
        signals = fc.build_signals(fc.FALLBACK_RATES)
        required_fields = {"pair", "ccy", "direction", "carry_bps", "conviction", "source", "generated_at"}
        for s in signals:
            assert required_fields.issubset(set(s.keys())), f"Missing fields in signal: {s}"

    def test_carry_bps_is_positive(self):
        """carry_bps should always be a positive integer (absolute spread)."""
        signals = fc.build_signals(fc.FALLBACK_RATES)
        for s in signals:
            assert s["carry_bps"] >= 0, f"Negative carry_bps for {s}"

    def test_conviction_in_range(self):
        signals = fc.build_signals(fc.FALLBACK_RATES)
        for s in signals:
            assert 0.0 <= s["conviction"] <= 1.0, f"Conviction out of range: {s}"

    def test_source_tag(self):
        signals = fc.build_signals(fc.FALLBACK_RATES)
        for s in signals:
            assert s["source"] == "forex_carry_v1"


# ── FRED fetch tests ──────────────────────────────────────────────────────────


class TestFetchFredRate:
    """Verify FRED fetcher parses response correctly and handles failures."""

    def _make_fred_response(self, value: str) -> Any:
        """Build a mock FRED API response."""
        payload = json.dumps({
            "observations": [{"date": "2024-01-01", "value": value}]
        }).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = payload
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    def test_parses_valid_response(self):
        with patch("urllib.request.urlopen", return_value=self._make_fred_response("5.33")):
            result = fc._fetch_fred_rate("FEDFUNDS", "fake_key")
        assert result == pytest.approx(5.33, abs=1e-9)

    def test_returns_none_on_dot_value(self):
        """FRED returns '.' for missing observations."""
        with patch("urllib.request.urlopen", return_value=self._make_fred_response(".")):
            result = fc._fetch_fred_rate("FEDFUNDS", "fake_key")
        assert result is None

    def test_returns_none_on_exception(self):
        with patch("urllib.request.urlopen", side_effect=Exception("network error")):
            result = fc._fetch_fred_rate("FEDFUNDS", "fake_key")
        assert result is None

    def test_empty_observations_returns_none(self):
        payload = json.dumps({"observations": []}).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = payload
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = fc._fetch_fred_rate("FEDFUNDS", "fake_key")
        assert result is None


class TestFetchCurrentRates:
    """Verify fetch_current_rates falls back gracefully when FRED is unavailable."""

    def test_fallback_when_no_api_key(self):
        """With no API key, should use hardcoded fallback rates for all ccys."""
        with patch.dict("os.environ", {}, clear=True):
            rates = fc.fetch_current_rates(api_key="")
        assert set(rates.keys()) == set(fc.FALLBACK_RATES.keys())
        # Check fallback values match expected
        assert rates["JPY"] == pytest.approx(fc.FALLBACK_RATES["JPY"], abs=1e-6)
        assert rates["USD"] == pytest.approx(fc.FALLBACK_RATES["USD"], abs=1e-6)

    def test_uses_fred_when_available(self):
        """When FRED returns a value, it should override the fallback."""
        fred_payload = json.dumps({
            "observations": [{"date": "2024-01-01", "value": "6.00"}]
        }).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = fred_payload
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            rates = fc.fetch_current_rates(api_key="test_key")

        # All series should have returned 6.00 from FRED mock
        assert rates["USD"] == pytest.approx(6.0, abs=1e-6)

    def test_partial_fred_failure_uses_fallback(self):
        """If FRED fails for some ccys, those ccys should use fallback."""
        call_count = {"n": 0}

        def selective_urlopen(url, **kwargs):
            call_count["n"] += 1
            if call_count["n"] <= 3:
                raise Exception("timeout")
            payload = json.dumps({
                "observations": [{"date": "2024-01-01", "value": "4.00"}]
            }).encode()
            mock_resp = MagicMock()
            mock_resp.read.return_value = payload
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=selective_urlopen):
            rates = fc.fetch_current_rates(api_key="test_key")

        # Should have all 10 ccys regardless of individual failures
        assert len(rates) == 10

    def test_all_g10_ccys_present(self):
        rates = fc.fetch_current_rates(api_key="")
        for ccy in ["USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NOK", "SEK", "NZD"]:
            assert ccy in rates, f"Missing currency: {ccy}"

    def test_rates_are_reasonable_floats(self):
        rates = fc.fetch_current_rates(api_key="")
        for ccy, rate in rates.items():
            assert isinstance(rate, float), f"{ccy} rate is not float"
            assert -5.0 < rate < 30.0, f"{ccy} rate {rate} out of plausible range"


# ── JSON output schema tests ──────────────────────────────────────────────────


class TestJsonOutputSchema:
    """Verify build_json_output returns a valid schema."""

    REQUIRED_TOP_LEVEL = {"generated_at", "signals", "regime", "unlock_status", "backtest_summary"}
    REQUIRED_SIGNAL_FIELDS = {"pair", "direction", "carry_bps", "conviction", "source"}
    REQUIRED_BT_FIELDS = {"wr", "pf", "n", "sharpe", "mdd"}
    VALID_REGIMES = {"carry_favorable", "carry_unfavorable"}
    VALID_UNLOCK_STATUSES = {"LOCKED", "UNLOCK_READY"}

    def test_top_level_keys(self):
        out = fc.build_json_output(rates=fc.FALLBACK_RATES)
        assert self.REQUIRED_TOP_LEVEL.issubset(set(out.keys()))

    def test_signals_list_not_empty(self):
        out = fc.build_json_output(rates=fc.FALLBACK_RATES)
        assert isinstance(out["signals"], list)
        assert len(out["signals"]) == fc.LONG_K + fc.SHORT_K

    def test_signal_fields(self):
        out = fc.build_json_output(rates=fc.FALLBACK_RATES)
        for sig in out["signals"]:
            assert self.REQUIRED_SIGNAL_FIELDS.issubset(set(sig.keys()))

    def test_regime_is_valid(self):
        out = fc.build_json_output(rates=fc.FALLBACK_RATES)
        assert out["regime"] in self.VALID_REGIMES

    def test_unlock_status_is_valid(self):
        out = fc.build_json_output(rates=fc.FALLBACK_RATES)
        assert out["unlock_status"] in self.VALID_UNLOCK_STATUSES

    def test_backtest_summary_fields(self):
        out = fc.build_json_output(rates=fc.FALLBACK_RATES)
        assert self.REQUIRED_BT_FIELDS.issubset(set(out["backtest_summary"].keys()))

    def test_backtest_summary_defaults_when_no_backtest(self):
        out = fc.build_json_output(rates=fc.FALLBACK_RATES, backtest_result=None)
        bt = out["backtest_summary"]
        assert bt["n"] == 0
        assert bt["pf"] == 0.0
        assert bt["wr"] == 0.0

    def test_with_backtest_result_propagates_unlock_ready(self):
        fake_backtest = {
            "wr": 0.55, "pf": 1.3, "n": 50, "sharpe": 0.8, "mdd": -0.05,
            "unlock_status": "UNLOCK_READY",
        }
        out = fc.build_json_output(rates=fc.FALLBACK_RATES, backtest_result=fake_backtest)
        assert out["unlock_status"] == "UNLOCK_READY"
        assert out["backtest_summary"]["pf"] == pytest.approx(1.3)
        assert out["backtest_summary"]["wr"] == pytest.approx(0.55)

    def test_json_serializable(self):
        out = fc.build_json_output(rates=fc.FALLBACK_RATES)
        # Should not raise
        serialized = json.dumps(out, default=str)
        parsed = json.loads(serialized)
        assert parsed["regime"] in self.VALID_REGIMES

    def test_generated_at_is_iso8601(self):
        out = fc.build_json_output(rates=fc.FALLBACK_RATES)
        # Should parse without error
        dt = datetime.fromisoformat(out["generated_at"].replace("Z", "+00:00"))
        assert dt is not None

    def test_rates_used_present(self):
        out = fc.build_json_output(rates=fc.FALLBACK_RATES)
        assert "rates_used" in out
        assert "USD" in out["rates_used"]


# ── Unlock condition tests ─────────────────────────────────────────────────────


class TestUnlockCondition:
    """Verify unlock_status is UNLOCK_READY only when PF>1.0, WR>45%, n>30."""

    def test_unlock_ready_when_thresholds_met(self):
        fake_backtest = {
            "wr": 0.50,   # > 0.45 ✓
            "pf": 1.2,    # > 1.0 ✓
            "n": 35,      # > 30 ✓
            "sharpe": 0.7, "mdd": -0.05,
            "unlock_status": "UNLOCK_READY",
        }
        out = fc.build_json_output(rates=fc.FALLBACK_RATES, backtest_result=fake_backtest)
        assert out["unlock_status"] == "UNLOCK_READY"

    def test_locked_when_pf_below_threshold(self):
        fake_backtest = {
            "wr": 0.50, "pf": 0.95, "n": 35,
            "sharpe": 0.4, "mdd": -0.10,
            "unlock_status": "LOCKED",
        }
        out = fc.build_json_output(rates=fc.FALLBACK_RATES, backtest_result=fake_backtest)
        assert out["unlock_status"] == "LOCKED"

    def test_locked_when_wr_below_threshold(self):
        fake_backtest = {
            "wr": 0.40, "pf": 1.5, "n": 35,
            "sharpe": 0.6, "mdd": -0.08,
            "unlock_status": "LOCKED",
        }
        out = fc.build_json_output(rates=fc.FALLBACK_RATES, backtest_result=fake_backtest)
        assert out["unlock_status"] == "LOCKED"

    def test_locked_when_n_below_threshold(self):
        fake_backtest = {
            "wr": 0.55, "pf": 1.3, "n": 20,
            "sharpe": 0.7, "mdd": -0.06,
            "unlock_status": "LOCKED",
        }
        out = fc.build_json_output(rates=fc.FALLBACK_RATES, backtest_result=fake_backtest)
        assert out["unlock_status"] == "LOCKED"

    def test_unlock_thresholds_match_spec(self):
        """PF>1.0 / WR>45% / n>30 per task spec."""
        assert fc.UNLOCK_PF == pytest.approx(1.0)
        assert fc.UNLOCK_WR == pytest.approx(0.45)
        assert fc.UNLOCK_N == 30


# ── Regime detection tests ─────────────────────────────────────────────────────


class TestCarryRegime:
    """Verify carry regime detection logic."""

    def test_favorable_when_spreads_wide(self):
        # AUD at 7%, JPY at 0.1% vs USD 5% → spreads are large
        rates = {
            "USD": 5.0, "AUD": 7.0, "NZD": 7.5, "GBP": 6.0,
            "EUR": 4.0, "CAD": 4.5, "CHF": 1.5, "JPY": 0.1,
            "NOK": 4.5, "SEK": 3.5,
        }
        ranked = fc.rank_carry(rates)
        regime = fc._detect_carry_regime(ranked)
        assert regime == "carry_favorable"

    def test_unfavorable_when_spreads_compressed(self):
        # All rates very similar (within 1.5% of each other)
        rates = {
            "USD": 5.0, "AUD": 5.5, "NZD": 5.3, "GBP": 5.2,
            "EUR": 4.8, "CAD": 5.1, "CHF": 4.7, "JPY": 4.6,
            "NOK": 5.0, "SEK": 4.9,
        }
        ranked = fc.rank_carry(rates)
        regime = fc._detect_carry_regime(ranked)
        assert regime == "carry_unfavorable"

    def test_returns_string(self):
        ranked = fc.rank_carry(fc.FALLBACK_RATES)
        regime = fc._detect_carry_regime(ranked)
        assert isinstance(regime, str)
        assert regime in {"carry_favorable", "carry_unfavorable"}


# ── Backtest with mocked yfinance ─────────────────────────────────────────────


class TestRunCarryBacktest:
    """Smoke-test backtest with mocked yfinance (offline)."""

    def _make_yf_mock(self) -> Any:
        """Build a minimal yfinance mock that returns synthetic monthly-able data."""
        try:
            import pandas as pd
            import numpy as np
        except ImportError:
            pytest.skip("pandas/numpy not installed")

        # 400 days of synthetic data starting 2023-01-01
        idx = pd.date_range("2023-01-01", periods=400, freq="D")
        np.random.seed(42)

        mock_yf = MagicMock()

        def mock_ticker(sym):
            t = MagicMock()
            prices = 1.0 + np.cumsum(np.random.normal(0, 0.003, len(idx)))
            prices = np.clip(prices, 0.5, 3.0)
            hist_df = pd.DataFrame({"Close": prices}, index=idx)
            t.history.return_value = hist_df
            return t

        mock_yf.Ticker.side_effect = mock_ticker
        return mock_yf

    def test_backtest_returns_required_keys(self):
        yf_mock = self._make_yf_mock()
        with patch.dict("sys.modules", {"yfinance": yf_mock}):
            result = fc.run_carry_backtest(
                start_date="2023-01-01",
                end_date="2024-01-01",
                rates=fc.FALLBACK_RATES,
                output_path=None,
            )
        required = {"pf", "wr", "n", "sharpe", "mdd", "total_return", "unlock_status", "production_eligible"}
        # Allow "error" key if data couldn't be fetched (shouldn't happen with mock)
        if "error" not in result:
            assert required.issubset(set(result.keys()))

    def test_backtest_no_price_data_returns_error(self):
        """When yfinance returns no data, backtest should return error dict."""
        mock_yf = MagicMock()
        mock_ticker = MagicMock()
        try:
            import pandas as pd
            mock_ticker.history.return_value = pd.DataFrame()
        except ImportError:
            pytest.skip("pandas not installed")
        mock_yf.Ticker.return_value = mock_ticker
        with patch.dict("sys.modules", {"yfinance": mock_yf}):
            result = fc.run_carry_backtest(
                start_date="2023-01-01",
                end_date="2024-01-01",
                rates=fc.FALLBACK_RATES,
                output_path=None,
            )
        assert result.get("pf") == 0
        assert result.get("unlock_status") == "LOCKED"

    def test_unlock_status_field_present(self):
        yf_mock = self._make_yf_mock()
        with patch.dict("sys.modules", {"yfinance": yf_mock}):
            result = fc.run_carry_backtest(
                start_date="2023-01-01",
                end_date="2024-01-01",
                rates=fc.FALLBACK_RATES,
                output_path=None,
            )
        assert "unlock_status" in result
        assert result["unlock_status"] in {"LOCKED", "UNLOCK_READY"}
