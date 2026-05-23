"""
tests/test_kimi_inverse_scanner_failover.py
===========================================
Schema-validation integration tests for kimi_inverse_scanner.fetch_binance_prices
post-migration to alpha_engine.failover_imports.

Per Inception code review on Plan 1: silent zero-pick days are the dominant
failure mode. Test covers required keys + types + edge cases (missing symbols,
total source failure).
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "alpha_engine"))


@pytest.fixture
def good_tickers():
    return [
        {"symbol": "BTCUSDT", "lastPrice": "65432.10",
         "priceChange": "0", "priceChangePercent": "0.19",
         "volume": "1000", "quoteVolume": "1000000"},
        {"symbol": "ETHUSDT", "lastPrice": "3210.50",
         "priceChange": "0", "priceChangePercent": "-0.45",
         "volume": "1000", "quoteVolume": "1000000"},
        {"symbol": "SOLUSDT", "lastPrice": "145.22",
         "priceChange": "0", "priceChangePercent": "1.34",
         "volume": "1000", "quoteVolume": "1000000"},
        {"symbol": "DOGEUSDT", "lastPrice": "0.0823",
         "priceChange": "0", "priceChangePercent": "2.10",
         "volume": "1000", "quoteVolume": "1000000"},
        {"symbol": "ADAUSDT", "lastPrice": "0.4523",
         "priceChange": "0", "priceChangePercent": "-0.12",
         "volume": "1000", "quoteVolume": "1000000"},
    ]


class TestFetchBinancePrices:
    """fetch_binance_prices(symbols) -> {requested_sym: float}"""

    def test_returns_correct_schema_for_dash_usd_symbols(self, good_tickers):
        from alpha_engine import kimi_inverse_scanner as kis

        with patch.object(kis, "_HAS_SHARED_FAILOVER", True), \
             patch.object(kis, "_shared_fetch_tickers_24h",
                          return_value=(good_tickers, "binance_fapi:fapi")):
            prices = kis.fetch_binance_prices(["BTC-USD", "ETH-USD", "SOL-USD"])

        assert isinstance(prices, dict)
        assert set(prices.keys()) == {"BTC-USD", "ETH-USD", "SOL-USD"}
        for sym, price in prices.items():
            assert isinstance(sym, str)
            assert isinstance(price, float)
            assert price > 0
        assert prices["BTC-USD"] == 65432.10

    def test_handles_already_normalized_symbols(self, good_tickers):
        from alpha_engine import kimi_inverse_scanner as kis

        with patch.object(kis, "_HAS_SHARED_FAILOVER", True), \
             patch.object(kis, "_shared_fetch_tickers_24h",
                          return_value=(good_tickers, "coingecko")):
            prices = kis.fetch_binance_prices(["BTCUSDT"])

        assert "BTCUSDT" in prices
        assert isinstance(prices["BTCUSDT"], float)

    def test_returns_empty_when_failover_empty_and_direct_fails(self):
        from alpha_engine import kimi_inverse_scanner as kis

        with patch.object(kis, "_HAS_SHARED_FAILOVER", True), \
             patch.object(kis, "_shared_fetch_tickers_24h",
                          return_value=([], "none")):
            # Also block urllib.request fallback
            import urllib.request
            with patch.object(urllib.request, "urlopen",
                              side_effect=Exception("blocked")):
                prices = kis.fetch_binance_prices(["BTC-USD"])

        assert prices == {}

    def test_skips_unknown_requested_symbols(self, good_tickers):
        from alpha_engine import kimi_inverse_scanner as kis

        with patch.object(kis, "_HAS_SHARED_FAILOVER", True), \
             patch.object(kis, "_shared_fetch_tickers_24h",
                          return_value=(good_tickers, "kucoin")):
            prices = kis.fetch_binance_prices(["BTC-USD", "NONEXISTENT-USD"])

        assert "BTC-USD" in prices
        assert "NONEXISTENT-USD" not in prices

    def test_skips_malformed_lastprice_values(self):
        from alpha_engine import kimi_inverse_scanner as kis
        bad_tickers = [
            {"symbol": "BTCUSDT", "lastPrice": "65000"},
            {"symbol": "ETHUSDT", "lastPrice": "garbage"},
        ]
        with patch.object(kis, "_HAS_SHARED_FAILOVER", True), \
             patch.object(kis, "_shared_fetch_tickers_24h",
                          return_value=(bad_tickers, "kucoin")):
            prices = kis.fetch_binance_prices(["BTC-USD", "ETH-USD"])

        assert "BTC-USD" in prices
        assert prices["BTC-USD"] == 65000.0
        assert "ETH-USD" not in prices  # malformed value silently dropped
