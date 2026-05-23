"""
tests/test_production_scanner_failover.py
=========================================
Schema-validation integration tests for production_scanner.py functions
that were migrated to use alpha_engine.failover_imports.

Per Inception code review on Plan 1 (updates/2026-04-17-deferred-execution-plans.md):
silent zero-pick days are the dominant failure mode for these migrations, so
each caller is validated against:
  * required output keys
  * value types
  * non-zero/non-empty behavior on known-good mocked failover data
  * graceful handling on empty failover data

All HTTP I/O is mocked at the alpha_engine.failover_imports layer -- these
tests do NOT hit live APIs.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# production_scanner.py at module-load time redirects stdout to a log file
# unless GITHUB_ACTIONS=true. That redirect path crashes under pytest because
# `__builtins__` is a dict (not a module) when imported from a package context.
# Set the env var BEFORE importing to skip the redirect entirely.
os.environ["GITHUB_ACTIONS"] = "true"

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "alpha_engine"))


# Fixtures -------------------------------------------------------------------
def _binance_ticker(symbol: str, last: float, change_pct: float) -> dict:
    return {
        "symbol": symbol,
        "lastPrice": str(last),
        "priceChange": "0",
        "priceChangePercent": str(change_pct),
        "volume": "1000",
        "quoteVolume": "1000000",
    }


@pytest.fixture
def good_tickers():
    return [
        _binance_ticker("BTCUSDT", 65432.10, 0.19),
        _binance_ticker("ETHUSDT", 3210.50, -0.45),
        _binance_ticker("SOLUSDT", 145.22, 1.34),
        _binance_ticker("ADAUSDT", 0.4523, -0.12),
        _binance_ticker("DOGEUSDT", 0.0823, 2.10),
    ]


@pytest.fixture
def good_klines():
    # Binance shape: [ts, o, h, l, c, v, ...] -- 30 bars
    base_ts = 1700000000000
    return [
        [base_ts + i * 3600000, "100", "101", "99", "100.5", "1234"]
        for i in range(30)
    ]


# Tests ----------------------------------------------------------------------
class TestFetchBinanceTicker:
    """_fetch_binance_ticker -> {"price": float, "change_pct": float} | None"""

    def test_returns_correct_schema_for_known_symbol(self, good_tickers):
        from alpha_engine import production_scanner as ps

        with patch.object(ps, "_HAS_SHARED_FAILOVER", True), \
             patch.object(ps, "_shared_fetch_tickers_24h",
                          return_value=(good_tickers, "binance_fapi:fapi")):
            result = ps._fetch_binance_ticker("BTCUSDT")

        assert result is not None
        assert set(result.keys()) == {"price", "change_pct"}
        assert isinstance(result["price"], float)
        assert isinstance(result["change_pct"], float)
        assert result["price"] == 65432.10
        assert result["change_pct"] == 0.19

    def test_returns_none_for_missing_symbol(self, good_tickers):
        from alpha_engine import production_scanner as ps

        with patch.object(ps, "_HAS_SHARED_FAILOVER", True), \
             patch.object(ps, "_shared_fetch_tickers_24h",
                          return_value=(good_tickers, "binance_spot:api")), \
             patch("requests.get", side_effect=Exception("blocked")):
            result = ps._fetch_binance_ticker("NONEXISTENTUSDT")

        assert result is None

    def test_returns_none_when_failover_empty_and_direct_fails(self):
        from alpha_engine import production_scanner as ps

        with patch.object(ps, "_HAS_SHARED_FAILOVER", True), \
             patch.object(ps, "_shared_fetch_tickers_24h",
                          return_value=([], "none")), \
             patch("requests.get", side_effect=Exception("blocked")):
            result = ps._fetch_binance_ticker("BTCUSDT")

        assert result is None


class TestFetchAllBinancePrices:
    """_fetch_all_binance_prices -> {symbol: float}"""

    def test_returns_dict_of_symbol_to_float(self, good_tickers):
        from alpha_engine import production_scanner as ps

        with patch.object(ps, "_HAS_SHARED_FAILOVER", True), \
             patch.object(ps, "_shared_fetch_tickers_24h",
                          return_value=(good_tickers, "coingecko")):
            prices = ps._fetch_all_binance_prices()

        assert isinstance(prices, dict)
        assert len(prices) == 5
        for sym, price in prices.items():
            assert isinstance(sym, str)
            assert isinstance(price, float)
        assert prices["BTCUSDT"] == 65432.10

    def test_returns_empty_dict_on_total_failure(self):
        from alpha_engine import production_scanner as ps

        with patch.object(ps, "_HAS_SHARED_FAILOVER", True), \
             patch.object(ps, "_shared_fetch_tickers_24h",
                          return_value=([], "none")), \
             patch("requests.get", side_effect=Exception("blocked")):
            prices = ps._fetch_all_binance_prices()

        assert prices == {}

    def test_skips_malformed_ticker_rows(self):
        from alpha_engine import production_scanner as ps
        bad_then_good = [
            {"symbol": "BAD"},  # missing lastPrice
            {"symbol": "BTCUSDT", "lastPrice": "65000"},
            {"symbol": "ETHUSDT", "lastPrice": "not_a_number"},
            {"symbol": "SOLUSDT", "lastPrice": "150.0"},
        ]
        with patch.object(ps, "_HAS_SHARED_FAILOVER", True), \
             patch.object(ps, "_shared_fetch_tickers_24h",
                          return_value=(bad_then_good, "kucoin")):
            prices = ps._fetch_all_binance_prices()

        assert "BTCUSDT" in prices and prices["BTCUSDT"] == 65000.0
        assert "SOLUSDT" in prices and prices["SOLUSDT"] == 150.0
        assert "ETHUSDT" not in prices  # bad value silently skipped
        assert "BAD" not in prices  # missing key silently skipped


class TestFetchTopFunding:
    """_fetch_top_funding -> [{symbol, rate}] | None (sorted ascending by rate)"""

    def test_failover_returns_sorted_negative_rates(self):
        from alpha_engine import production_scanner as ps

        # Force direct Binance to fail so failover path is exercised
        rate_map = {
            "BTCUSDT": 0.0001,
            "ETHUSDT": -0.0005,
            "SOLUSDT": 0.0002,
            "ADAUSDT": -0.0010,
        }

        def fake_funding(sym):
            return rate_map.get(sym)

        with patch("requests.get", side_effect=Exception("blocked")), \
             patch.object(ps, "_HAS_SHARED_FAILOVER", True), \
             patch.object(ps, "_shared_fetch_funding_rate", side_effect=fake_funding), \
             patch.object(ps, "CRYPTO_SYMBOLS",
                          {"BTC-USD": {}, "ETH-USD": {}, "SOL-USD": {}, "ADA-USD": {}}):
            # CRYPTO_SYMBOLS keys aren't used directly -- function iterates over
            # universe; patch with a list-shape too:
            with patch.dict(ps.__dict__, {"CRYPTO_SYMBOLS": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT"]}):
                result = ps._fetch_top_funding(n=3)

        assert result is not None
        assert isinstance(result, list)
        assert len(result) == 3
        # Schema check
        for entry in result:
            assert set(entry.keys()) == {"symbol", "rate"}
            assert isinstance(entry["symbol"], str)
            assert isinstance(entry["rate"], float)
        # Sorted ascending: most negative first
        assert result[0]["symbol"] == "ADAUSDT"
        assert result[0]["rate"] == -0.0010

    def test_returns_none_when_all_sources_fail(self):
        from alpha_engine import production_scanner as ps

        with patch("requests.get", side_effect=Exception("blocked")), \
             patch.object(ps, "_HAS_SHARED_FAILOVER", True), \
             patch.object(ps, "_shared_fetch_funding_rate", return_value=None), \
             patch.dict(ps.__dict__, {"CRYPTO_SYMBOLS": ["BTCUSDT"]}):
            result = ps._fetch_top_funding(n=5)

        assert result is None
