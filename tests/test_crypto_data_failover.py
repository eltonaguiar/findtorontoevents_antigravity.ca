"""
tests/test_crypto_data_failover.py
==================================
Tests for alpha_engine.crypto_data_failover -- the shared multi-source
failover utility (Binance mirrors -> CoinGecko -> KuCoin -> CryptoCompare).

Coverage:
  * Symbol/coin helpers
  * Per-source schema validation + normalizer correctness
  * Circuit-breaker behavior (3 failures -> open, success -> reset)
  * End-to-end fallback chain progression (mocked)

All HTTP I/O is mocked -- these tests do NOT hit live APIs.
"""
from __future__ import annotations

import os
import sys
import time
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from alpha_engine import crypto_data_failover as cdf  # noqa: E402


# ---------------------------------------------------------------------------
# Symbol helpers
# ---------------------------------------------------------------------------
class TestSymbolHelpers:
    def test_normalize_symbol_basic(self):
        assert cdf._normalize_symbol("btcusdt") == "BTCUSDT"
        assert cdf._normalize_symbol("BTC-USDT") == "BTCUSDT"
        assert cdf._normalize_symbol("BTC/USDT") == "BTCUSDT"

    def test_normalize_symbol_usd_to_usdt(self):
        assert cdf._normalize_symbol("btcusd") == "BTCUSDT"

    def test_normalize_empty(self):
        assert cdf._normalize_symbol("") == ""
        assert cdf._normalize_symbol(None or "") == ""

    def test_base_coin(self):
        assert cdf._base_coin("BTCUSDT") == "BTC"
        assert cdf._base_coin("ETH-USDT") == "ETH"
        # Already-USDT-suffixed symbol stays clean
        assert cdf._base_coin("DOGEUSDT") == "DOGE"

    def test_kucoin_symbol(self):
        assert cdf._kucoin_symbol("BTCUSDT") == "BTC-USDT"
        assert cdf._kucoin_symbol("eth/usdt") == "ETH-USDT"


# ---------------------------------------------------------------------------
# Schema validators + normalizers
# ---------------------------------------------------------------------------
class TestNormalizers:
    def test_coingecko_ticker_normalizer(self):
        cg_row = {
            "id": "bitcoin",
            "symbol": "btc",
            "current_price": 65432.10,
            "price_change_24h": 123.45,
            "price_change_percentage_24h": 0.19,
            "total_volume": 30_000_000_000,
        }
        out = cdf._normalize_coingecko_ticker(cg_row)
        assert out is not None
        assert out["symbol"] == "BTCUSDT"
        assert float(out["lastPrice"]) == 65432.10
        assert float(out["quoteVolume"]) == 30_000_000_000
        assert cdf._is_valid_ticker(out)

    def test_coingecko_ticker_rejects_zero_volume(self):
        bad = {"symbol": "btc", "current_price": 100, "total_volume": 0,
               "price_change_24h": 0, "price_change_percentage_24h": 0}
        assert cdf._normalize_coingecko_ticker(bad) is None

    def test_kucoin_ticker_normalizer(self):
        kc_row = {
            "symbol": "BTC-USDT", "last": "65432.10",
            "changePrice": "+123.45", "changeRate": "0.0019",
            "vol": "1234.56", "volValue": "80,000,000",
        }
        # KuCoin sometimes returns volValue with commas; we use a numeric one
        kc_row["volValue"] = "80000000"
        out = cdf._normalize_kucoin_ticker(kc_row)
        assert out is not None
        assert out["symbol"] == "BTCUSDT"
        assert float(out["lastPrice"]) == 65432.10
        # changeRate 0.0019 (decimal) -> 0.19% (percent)
        assert abs(float(out["priceChangePercent"]) - 0.19) < 1e-6
        assert cdf._is_valid_ticker(out)

    def test_kucoin_ticker_skips_non_usdt(self):
        bad = {"symbol": "BTC-EUR", "last": "1", "vol": "1", "volValue": "1",
               "changePrice": "0", "changeRate": "0"}
        assert cdf._normalize_kucoin_ticker(bad) is None

    def test_cryptocompare_ticker_normalizer(self):
        cc_row = {
            "CoinInfo": {"Name": "BTC"},
            "RAW": {"USD": {
                "PRICE": 65432.10,
                "CHANGE24HOUR": 123.45,
                "CHANGEPCT24HOUR": 0.19,
                "VOLUME24HOUR": 1234.56,
                "VOLUME24HOURTO": 81_000_000_000,
            }},
        }
        out = cdf._normalize_cryptocompare_ticker(cc_row)
        assert out is not None
        assert out["symbol"] == "BTCUSDT"
        assert cdf._is_valid_ticker(out)

    def test_cryptocompare_ticker_missing_raw(self):
        bad = {"CoinInfo": {"Name": "BTC"}}
        assert cdf._normalize_cryptocompare_ticker(bad) is None

    def test_kucoin_klines_normalizer_reverses_to_oldest_first(self):
        # KuCoin newest-first: [time_s, open, close, high, low, vol, turnover]
        raw = [
            ["1700000200", "100", "105", "106", "99", "10", "1050"],
            ["1700000100", "98", "100", "101", "97", "9", "900"],
        ]
        bars = cdf._normalize_kucoin_klines(raw, limit=10)
        assert len(bars) == 2
        # First bar should now be the older timestamp (1700000100)
        assert bars[0][0] == 1700000100 * 1000
        # Verify Binance schema [ts, o, h, l, c, v]
        assert bars[0][1] == "98"   # open
        assert bars[0][2] == "101"  # high
        assert bars[0][3] == "97"   # low
        assert bars[0][4] == "100"  # close
        assert bars[0][5] == "9"    # vol

    def test_coingecko_klines_normalizer_no_volume(self):
        raw = [
            [1700000100000, 98.0, 101.0, 97.0, 100.0],
            [1700000200000, 100.0, 106.0, 99.0, 105.0],
        ]
        bars = cdf._normalize_coingecko_klines(raw, limit=10)
        assert len(bars) == 2
        assert bars[0][5] == "0"   # CoinGecko has no volume
        # str() of a float is "105.0" — schema preserves str-ness, value parses back to 105.0
        assert float(bars[1][4]) == 105.0

    def test_cryptocompare_klines_normalizer_skips_zero_close(self):
        raw = [
            {"time": 1700000100, "open": 98, "high": 101, "low": 97, "close": 0,
             "volumefrom": 0, "volumeto": 0},
            {"time": 1700000200, "open": 100, "high": 106, "low": 99, "close": 105,
             "volumefrom": 9, "volumeto": 900},
        ]
        bars = cdf._normalize_cryptocompare_klines(raw, limit=10)
        assert len(bars) == 1   # zero-close row dropped
        assert float(bars[0][4]) == 105.0


# ---------------------------------------------------------------------------
# FailoverConfig — circuit breaker
# ---------------------------------------------------------------------------
class TestFailoverConfig:
    def setup_method(self):
        # Use a temp file so tests don't trample the real circuit state
        self.tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.tmp.close()
        self.path = Path(self.tmp.name)
        # Start clean
        self.path.unlink(missing_ok=True)
        self.cfg = cdf.FailoverConfig(
            path=self.path,
            cooldown_seconds=300,
            fail_threshold=3,
        )

    def teardown_method(self):
        self.path.unlink(missing_ok=True)

    def test_fresh_source_not_open(self):
        assert self.cfg.is_open("kucoin") is False

    def test_three_failures_open_breaker(self):
        now = time.time()
        self.cfg.record_failure("kucoin", now=now)
        self.cfg.record_failure("kucoin", now=now + 1)
        # 3rd failure (at now+2) should open the breaker.  open_until_ts is
        # set to (failure_ts + cooldown) = now + 302 with default 300s cooldown.
        opened = self.cfg.record_failure("kucoin", now=now + 2)
        assert opened is True
        assert self.cfg.is_open("kucoin", now=now + 3) is True
        assert self.cfg.is_open("kucoin", now=now + 100) is True
        # Still open just before cooldown elapses
        assert self.cfg.is_open("kucoin", now=now + 301) is True
        # Open until elapsed -- closed at now + 303
        assert self.cfg.is_open("kucoin", now=now + 303) is False

    def test_success_resets_breaker(self):
        now = time.time()
        self.cfg.record_failure("kucoin", now=now)
        self.cfg.record_failure("kucoin", now=now + 1)
        self.cfg.record_success("kucoin")
        # Need 3 fresh failures to re-open
        self.cfg.record_failure("kucoin", now=now + 10)
        self.cfg.record_failure("kucoin", now=now + 11)
        assert self.cfg.is_open("kucoin", now=now + 12) is False

    def test_failures_outside_window_reset_counter(self):
        now = time.time()
        self.cfg.record_failure("kucoin", now=now)
        # Failure 90s later — outside the 60s window, counter resets
        opened = self.cfg.record_failure("kucoin", now=now + 90)
        assert opened is False
        assert self.cfg.is_open("kucoin", now=now + 91) is False

    def test_circuit_state_persisted_to_disk(self):
        now = time.time()
        for i in range(3):
            self.cfg.record_failure("kucoin", now=now + i)
        # Reload from disk
        cfg2 = cdf.FailoverConfig(path=self.path, cooldown_seconds=300, fail_threshold=3)
        assert cfg2.is_open("kucoin", now=now + 5) is True


# ---------------------------------------------------------------------------
# End-to-end fallback chain (mocked HTTP)
# ---------------------------------------------------------------------------
class TestFallbackChain:
    def setup_method(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.tmp.close()
        self.path = Path(self.tmp.name)
        self.path.unlink(missing_ok=True)
        self.cfg = cdf.FailoverConfig(path=self.path)

    def teardown_method(self):
        self.path.unlink(missing_ok=True)

    def test_tickers_fallback_progresses_to_coingecko_when_binance_fails(self):
        """Binance returns None (geo-block); CoinGecko returns valid data."""
        cg_response = [
            {"symbol": "btc", "current_price": 65000, "price_change_24h": 100,
             "price_change_percentage_24h": 0.15, "total_volume": 30e9},
            {"symbol": "eth", "current_price": 3500, "price_change_24h": 5,
             "price_change_percentage_24h": 0.14, "total_volume": 15e9},
            {"symbol": "sol", "current_price": 150, "price_change_24h": 1,
             "price_change_percentage_24h": 0.5, "total_volume": 2e9},
            {"symbol": "ada", "current_price": 0.4, "price_change_24h": 0.001,
             "price_change_percentage_24h": 0.2, "total_volume": 0.5e9},
            {"symbol": "xrp", "current_price": 0.6, "price_change_24h": 0.001,
             "price_change_percentage_24h": 0.1, "total_volume": 1e9},
            {"symbol": "doge", "current_price": 0.1, "price_change_24h": 0.001,
             "price_change_percentage_24h": 0.5, "total_volume": 0.5e9},
        ]

        def fake_http(url, **_):
            if "binance" in url:
                return None  # All Binance mirrors "geo-blocked"
            if "coingecko.com" in url and "markets" in url:
                return cg_response
            return None

        with patch.object(cdf, "_http_get_json", side_effect=fake_http):
            tickers, source = cdf.fetch_tickers_24h(config=self.cfg)

        assert source == "coingecko"
        assert len(tickers) == 6
        assert all(cdf._is_valid_ticker(t) for t in tickers)
        assert tickers[0]["symbol"] == "BTCUSDT"

    def test_tickers_chain_falls_to_kucoin_when_binance_and_cg_fail(self):
        kc_response = {
            "code": "200000",
            "data": {"ticker": [
                {"symbol": "BTC-USDT", "last": "65000", "changePrice": "100",
                 "changeRate": "0.0015", "vol": "1000", "volValue": "65000000"},
                {"symbol": "ETH-USDT", "last": "3500", "changePrice": "5",
                 "changeRate": "0.0014", "vol": "1000", "volValue": "3500000"},
                {"symbol": "SOL-USDT", "last": "150", "changePrice": "1",
                 "changeRate": "0.005", "vol": "1000", "volValue": "150000"},
                {"symbol": "ADA-USDT", "last": "0.4", "changePrice": "0.001",
                 "changeRate": "0.002", "vol": "1000", "volValue": "400"},
                {"symbol": "XRP-USDT", "last": "0.6", "changePrice": "0.001",
                 "changeRate": "0.001", "vol": "1000", "volValue": "600"},
                {"symbol": "DOGE-USDT", "last": "0.1", "changePrice": "0.001",
                 "changeRate": "0.005", "vol": "1000", "volValue": "100"},
            ]},
        }

        def fake_http(url, **_):
            if "binance" in url or "coingecko.com" in url:
                return None
            if "kucoin.com" in url and "allTickers" in url:
                return kc_response
            return None

        with patch.object(cdf, "_http_get_json", side_effect=fake_http):
            tickers, source = cdf.fetch_tickers_24h(config=self.cfg)

        assert source == "kucoin"
        assert len(tickers) >= 5
        assert tickers[0]["symbol"].endswith("USDT")

    def test_klines_fallback_to_kucoin(self):
        kc_response = {
            "code": "200000",
            "data": [
                ["1700000200", "100", "105", "106", "99", "10", "1050"],
                ["1700000100", "98", "100", "101", "97", "9", "900"],
            ],
        }

        def fake_http(url, **_):
            if "binance" in url:
                return None
            if "kucoin.com" in url and "candles" in url:
                return kc_response
            return None

        with patch.object(cdf, "_http_get_json", side_effect=fake_http):
            bars = cdf.fetch_klines("BTCUSDT", "1h", limit=2, config=self.cfg)

        assert len(bars) == 2
        # Oldest first (Binance order)
        assert bars[0][0] < bars[1][0]
        # Binance shape (12 cols)
        assert len(bars[0]) >= 6

    def test_funding_rate_falls_to_okx_when_binance_and_bybit_fail(self):
        okx_response = {
            "code": "0",
            "data": [{"fundingRate": "0.00012345", "instId": "BTC-USDT-SWAP"}],
        }

        def fake_http(url, **_):
            if "binance" in url:
                return None
            if "bybit.com" in url:
                return None
            if "okx.com" in url:
                return okx_response
            return None

        with patch.object(cdf, "_http_get_json", side_effect=fake_http):
            rate = cdf.fetch_funding_rate("BTCUSDT", config=self.cfg)

        assert rate is not None
        assert abs(rate - 0.00012345) < 1e-9

    def test_all_sources_fail_returns_empty(self):
        with patch.object(cdf, "_http_get_json", return_value=None):
            tickers, source = cdf.fetch_tickers_24h(config=self.cfg)
            assert tickers == []
            assert source == "none"
            bars = cdf.fetch_klines("BTCUSDT", "1h", config=self.cfg)
            assert bars == []
            rate = cdf.fetch_funding_rate("BTCUSDT", config=self.cfg)
            assert rate is None

    def test_circuit_breaker_skips_failed_source_on_subsequent_calls(self):
        """If KuCoin failed enough to trip the breaker, subsequent fetch
        should skip it without making a network call."""
        # Trip KuCoin manually
        now = time.time()
        for _ in range(3):
            self.cfg.record_failure("kucoin", now=now)
        assert self.cfg.is_open("kucoin", now=now + 5) is True

        call_log: list[str] = []

        def fake_http(url, **_):
            call_log.append(url)
            return None

        with patch.object(cdf, "_http_get_json", side_effect=fake_http):
            cdf.fetch_tickers_24h(config=self.cfg)

        # No call should hit kucoin (it's in cooldown)
        assert all("kucoin.com" not in u for u in call_log), \
            f"Cooldown not honored; calls included KuCoin: {call_log}"


# ---------------------------------------------------------------------------
# _GEO_BLOCKED sentinel propagation
# ---------------------------------------------------------------------------
class TestGeoBlockedSentinel:
    """Verify that 451/403 geo-blocked responses propagate the _GEO_BLOCKED
    sentinel from _http_get_json through per-source fetchers to _try_source,
    which skips circuit-breaker recording so geo-blocks don't consume budget."""

    def setup_method(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.tmp.close()
        self.path = Path(self.tmp.name)
        self.path.unlink(missing_ok=True)
        self.cfg = cdf.FailoverConfig(path=self.path)

    def teardown_method(self):
        self.path.unlink(missing_ok=True)

    # -- _http_get_json returns _GEO_BLOCKED for 451/403 --

    def test_http_get_json_returns_geo_blocked_on_451(self):
        """_http_get_json returns _GEO_BLOCKED when server returns 451."""
        import urllib.error
        err = urllib.error.HTTPError(
            url="https://api.binance.com/test",
            code=451,
            msg="Unavailable For Legal Reasons",
            hdrs=None,
            fp=None,
        )
        with patch("urllib.request.urlopen", side_effect=err):
            result = cdf._http_get_json("https://api.binance.com/test")
        assert result is cdf._GEO_BLOCKED

    def test_http_get_json_returns_geo_blocked_on_403(self):
        """_http_get_json returns _GEO_BLOCKED when server returns 403."""
        import urllib.error
        err = urllib.error.HTTPError(
            url="https://api.binance.com/test",
            code=403,
            msg="Forbidden",
            hdrs=None,
            fp=None,
        )
        with patch("urllib.request.urlopen", side_effect=err):
            result = cdf._http_get_json("https://api.binance.com/test")
        assert result is cdf._GEO_BLOCKED

    def test_http_get_json_returns_none_on_500(self):
        """_http_get_json returns None (NOT _GEO_BLOCKED) for non-geo errors."""
        import urllib.error
        err = urllib.error.HTTPError(
            url="https://api.binance.com/test",
            code=500,
            msg="Internal Server Error",
            hdrs=None,
            fp=None,
        )
        with patch("urllib.request.urlopen", side_effect=err):
            result = cdf._http_get_json("https://api.binance.com/test")
        assert result is None
        assert result is not cdf._GEO_BLOCKED

    # -- Per-source fetchers propagate _GEO_BLOCKED --

    def test_binance_tickers_propagates_geo_blocked(self):
        """_fetch_binance_tickers returns _GEO_BLOCKED (not None) when
        _http_get_json returns it."""
        with patch.object(cdf, "_http_get_json", return_value=cdf._GEO_BLOCKED):
            result = cdf._fetch_binance_tickers("https://fapi.binance.com", futures=True)
        assert result is cdf._GEO_BLOCKED

    def test_coingecko_tickers_propagates_geo_blocked(self):
        with patch.object(cdf, "_http_get_json", return_value=cdf._GEO_BLOCKED):
            # Need to also throttle or patch it
            with patch.object(cdf, "_coingecko_throttle"):
                result = cdf._fetch_coingecko_tickers()
        assert result is cdf._GEO_BLOCKED

    def test_kucoin_tickers_propagates_geo_blocked(self):
        with patch.object(cdf, "_http_get_json", return_value=cdf._GEO_BLOCKED):
            result = cdf._fetch_kucoin_tickers()
        assert result is cdf._GEO_BLOCKED

    def test_cryptocompare_tickers_propagates_geo_blocked(self):
        with patch.object(cdf, "_http_get_json", return_value=cdf._GEO_BLOCKED):
            result = cdf._fetch_cryptocompare_tickers()
        assert result is cdf._GEO_BLOCKED

    def test_binance_klines_propagates_geo_blocked(self):
        with patch.object(cdf, "_http_get_json", return_value=cdf._GEO_BLOCKED):
            result = cdf._fetch_binance_klines(
                "https://fapi.binance.com", "BTCUSDT", "1h", 10, futures=True
            )
        assert result is cdf._GEO_BLOCKED

    def test_kucoin_klines_propagates_geo_blocked(self):
        with patch.object(cdf, "_http_get_json", return_value=cdf._GEO_BLOCKED):
            result = cdf._fetch_kucoin_klines("BTCUSDT", "1h", 10)
        assert result is cdf._GEO_BLOCKED

    def test_coingecko_klines_propagates_geo_blocked(self):
        with patch.object(cdf, "_http_get_json", return_value=cdf._GEO_BLOCKED):
            with patch.object(cdf, "_coingecko_throttle"):
                result = cdf._fetch_coingecko_klines("BTCUSDT", "1h", 10)
        assert result is cdf._GEO_BLOCKED

    def test_cryptocompare_klines_propagates_geo_blocked(self):
        with patch.object(cdf, "_http_get_json", return_value=cdf._GEO_BLOCKED):
            result = cdf._fetch_cryptocompare_klines("BTCUSDT", "1h", 10)
        assert result is cdf._GEO_BLOCKED

    def test_binance_funding_propagates_geo_blocked(self):
        with patch.object(cdf, "_http_get_json", return_value=cdf._GEO_BLOCKED):
            result = cdf._fetch_binance_funding("https://fapi.binance.com", "BTCUSDT")
        assert result is cdf._GEO_BLOCKED

    def test_bybit_funding_propagates_geo_blocked(self):
        with patch.object(cdf, "_http_get_json", return_value=cdf._GEO_BLOCKED):
            result = cdf._fetch_bybit_funding("BTCUSDT")
        assert result is cdf._GEO_BLOCKED

    def test_okx_funding_propagates_geo_blocked(self):
        with patch.object(cdf, "_http_get_json", return_value=cdf._GEO_BLOCKED):
            result = cdf._fetch_okx_funding("BTCUSDT")
        assert result is cdf._GEO_BLOCKED

    def test_coinglass_funding_propagates_geo_blocked(self):
        with patch.object(cdf, "_http_get_json", return_value=cdf._GEO_BLOCKED):
            with patch.dict(os.environ, {"COINGLASS_API_KEY": "test-key"}):
                result = cdf._fetch_coinglass_funding("BTCUSDT")
        assert result is cdf._GEO_BLOCKED

    # -- _try_source skips breaker recording for _GEO_BLOCKED --

    def test_try_source_does_not_record_failure_on_geo_blocked(self):
        """When a per-source fetcher returns _GEO_BLOCKED, _try_source must
        NOT call record_failure — geo-blocks are permanent and should not
        consume circuit-breaker budget."""
        source_name = "binance_fapi:fapi"
        assert self.cfg.is_open(source_name) is False

        # Simulate geo-blocked response from the fetcher
        def geo_blocked_fn():
            return cdf._GEO_BLOCKED

        result = cdf._try_source(
            self.cfg, source_name, geo_blocked_fn,
            validate=lambda v: isinstance(v, list),
        )
        # Result should be None (chain continues to next source)
        assert result is None
        # Breaker should NOT be open — no failure was recorded
        assert self.cfg.is_open(source_name) is False
        # No failure count should exist at all
        snapshot = self.cfg.snapshot()
        assert source_name not in snapshot

    def test_try_source_records_failure_on_normal_error(self):
        """When a per-source fetcher returns None (not _GEO_BLOCKED),
        _try_source DOES call record_failure — normal errors consume budget."""
        source_name = "kucoin"
        assert self.cfg.is_open(source_name) is False

        def failing_fn():
            return None  # Normal failure, not geo-blocked

        for _ in range(3):
            cdf._try_source(
                self.cfg, source_name, failing_fn,
                validate=lambda v: isinstance(v, list),
            )

        # After 3 normal failures, breaker should be open
        assert self.cfg.is_open(source_name) is True

    def test_geo_blocked_does_not_trip_breaker_but_normal_failures_still_do(self):
        """Mix of geo-blocks + normal failures: only normal failures count."""
        source_name = "binance_spot:api"
        # 3 geo-blocks — should NOT trip breaker
        for _ in range(3):
            cdf._try_source(
                self.cfg, source_name,
                lambda: cdf._GEO_BLOCKED,
                validate=lambda v: isinstance(v, list),
            )
        assert self.cfg.is_open(source_name) is False

        # Now 3 normal failures — SHOULD trip breaker
        for _ in range(3):
            cdf._try_source(
                self.cfg, source_name,
                lambda: None,
                validate=lambda v: isinstance(v, list),
            )
        assert self.cfg.is_open(source_name) is True

    # -- Full end-to-end chain: geo-blocked Binance falls through to KuCoin --

    def test_tickers_chain_succeeds_despite_geo_blocked_binance(self):
        """When ALL Binance mirrors return 451 (geo-blocked), the chain
        should still fall through to CoinGecko/KuCoin and return valid data,
        WITHOUT tripping any Binance breakers."""
        kucoin_response = {
            "code": "200000",
            "data": {"ticker": [
                {"symbol": "BTC-USDT", "last": "65000", "changePrice": "100",
                 "changeRate": "0.0015", "vol": "1000", "volValue": "65000000"},
                {"symbol": "ETH-USDT", "last": "3500", "changePrice": "5",
                 "changeRate": "0.0014", "vol": "1000", "volValue": "3500000"},
                {"symbol": "SOL-USDT", "last": "150", "changePrice": "1",
                 "changeRate": "0.005", "vol": "1000", "volValue": "150000"},
                {"symbol": "ADA-USDT", "last": "0.4", "changePrice": "0.001",
                 "changeRate": "0.002", "vol": "1000", "volValue": "400"},
                {"symbol": "XRP-USDT", "last": "0.6", "changePrice": "0.001",
                 "changeRate": "0.001", "vol": "1000", "volValue": "600"},
                {"symbol": "DOGE-USDT", "last": "0.1", "changePrice": "0.001",
                 "changeRate": "0.005", "vol": "1000", "volValue": "100"},
            ]},
        }

        call_log: list[str] = []

        def fake_http(url, **_):
            call_log.append(url)
            # All Binance + CoinGecko mirrors are geo-blocked (451)
            if "binance" in url or "coingecko" in url:
                return cdf._GEO_BLOCKED
            # KuCoin works
            if "kucoin.com" in url and "allTickers" in url:
                return kucoin_response
            return None

        with patch.object(cdf, "_http_get_json", side_effect=fake_http):
            tickers, source = cdf.fetch_tickers_24h(config=self.cfg)

        # KuCoin succeeded
        assert source == "kucoin"
        assert len(tickers) >= 5
        # Verify KuCoin was actually called
        assert any("kucoin.com" in u for u in call_log), "No KuCoin call was made"
        # No Binance/CoinGecko breaker was tripped (geo-blocks don't count)
        snap = self.cfg.snapshot()
        for key in snap:
            assert "binance" not in key, f"Binance source {key} has breaker entry despite geo-block: {snap[key]}"
            assert "coingecko" not in key, f"CoinGecko source {key} has breaker entry despite geo-block: {snap[key]}"

    def test_funding_chain_succeeds_despite_geo_blocked_binance(self):
        """When Binance funding is geo-blocked, the chain falls through
        to Bybit/OKX without tripping Binance breaker."""
        okx_response = {
            "code": "0",
            "data": [{"fundingRate": "0.00010000", "instId": "BTC-USDT-SWAP"}],
        }

        def fake_http(url, **_):
            if "binance" in url:
                return cdf._GEO_BLOCKED
            if "bybit" in url:
                return None  # Bybit down (normal failure)
            if "okx" in url:
                return okx_response
            return None

        with patch.object(cdf, "_http_get_json", side_effect=fake_http):
            rate = cdf.fetch_funding_rate("BTCUSDT", config=self.cfg)

        assert rate is not None
        assert abs(rate - 0.0001) < 1e-9
        # Binance sources should NOT have breaker entries
        snap = self.cfg.snapshot()
        for key in snap:
            assert "binance" not in key
        # Bybit (normal failure) SHOULD have a breaker entry
        assert any("bybit" in key for key in snap)


# ---------------------------------------------------------------------------
# Module-level smoke (does NOT hit network)
# ---------------------------------------------------------------------------
def test_module_default_config_singleton():
    cfg = cdf.get_default_config()
    assert isinstance(cfg, cdf.FailoverConfig)
    # Two calls return the same instance
    assert cfg is cdf.get_default_config()


# ---------------------------------------------------------------------------
# Half-open fail-fast (Design #8 from code review)
# ---------------------------------------------------------------------------
class TestHalfOpenFailFast:
    """Verify that after a breaker exits cooldown (half-open), the FIRST
    failure immediately re-opens the breaker instead of requiring 3 more
    consecutive failures. This prevents wasting HTTP round-trips on sources
    we already know are unreliable."""

    def setup_method(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.tmp.close()
        self.path = Path(self.tmp.name)
        self.path.unlink(missing_ok=True)
        self.cfg = cdf.FailoverConfig(
            path=self.path,
            cooldown_seconds=300,
            fail_threshold=3,
        )

    def teardown_method(self):
        self.path.unlink(missing_ok=True)

    def test_half_open_reopens_on_first_failure(self):
        """After cooldown expires, a single failure should re-open the breaker."""
        now = time.time()
        # Open the breaker with 3 failures
        for i in range(3):
            self.cfg.record_failure("kucoin", now=now + i)
        assert self.cfg.is_open("kucoin", now=now + 5) is True

        # Cooldown expires at now + 303
        cooldown_end = now + 303
        assert self.cfg.is_open("kucoin", now=cooldown_end) is False

        # First failure after cooldown should IMMEDIATELY re-open
        opened = self.cfg.record_failure("kucoin", now=cooldown_end + 1)
        assert opened is True
        assert self.cfg.is_open("kucoin", now=cooldown_end + 2) is True

    def test_cold_start_still_needs_three_failures(self):
        """A source that was NEVER open should still need 3 failures."""
        now = time.time()
        # First failure -- should NOT open breaker
        opened = self.cfg.record_failure("kucoin", now=now)
        assert opened is False
        assert self.cfg.is_open("kucoin", now=now + 1) is False

        # Second failure -- still not open
        opened = self.cfg.record_failure("kucoin", now=now + 1)
        assert opened is False

        # Third -- now it opens
        opened = self.cfg.record_failure("kucoin", now=now + 2)
        assert opened is True

    def test_success_resets_half_open_state(self):
        """A successful request after cooldown should fully reset the breaker."""
        now = time.time()
        for i in range(3):
            self.cfg.record_failure("kucoin", now=now + i)
        # Cooldown expires
        cooldown_end = now + 303
        assert self.cfg.is_open("kucoin", now=cooldown_end) is False
        # Success resets everything
        self.cfg.record_success("kucoin")
        # Now it should need 3 fresh failures again
        opened = self.cfg.record_failure("kucoin", now=cooldown_end + 1)
        assert opened is False  # first failure, not re-opened
        self.cfg.record_failure("kucoin", now=cooldown_end + 2)
        opened = self.cfg.record_failure("kucoin", now=cooldown_end + 3)
        assert opened is True  # 3rd failure opens it

    def test_reopened_cooldown_is_full_duration(self):
        """When half-open re-opens, the new cooldown should be the full duration."""
        now = time.time()
        for i in range(3):
            self.cfg.record_failure("kucoin", now=now + i)
        cooldown_end = now + 303
        # Re-open with a single failure
        self.cfg.record_failure("kucoin", now=cooldown_end + 1)
        # Should still be open for the full 300s from re-open
        assert self.cfg.is_open("kucoin", now=cooldown_end + 100) is True
        assert self.cfg.is_open("kucoin", now=cooldown_end + 300) is True
        assert self.cfg.is_open("kucoin", now=cooldown_end + 304) is False


# ---------------------------------------------------------------------------
# fetch_funding_entry (Design #6 from code review)
# ---------------------------------------------------------------------------
class TestFetchFundingEntry:
    """Verify that fetch_funding_entry returns both the funding rate AND
    an 8h-aligned funding timestamp instead of the inaccurate
    int(time.time()*1000) wall-clock time."""

    def setup_method(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.tmp.close()
        self.path = Path(self.tmp.name)
        self.path.unlink(missing_ok=True)
        self.cfg = cdf.FailoverConfig(path=self.path)

    def teardown_method(self):
        self.path.unlink(missing_ok=True)

    def test_fetch_funding_entry_returns_dict_with_rate_and_time(self):
        """fetch_funding_entry should return {fundingRate, fundingTime, source}."""
        bybit_response = {
            "retCode": 0,
            "result": {
                "list": [{"fundingRate": "0.00012345", "fundingRateTimestamp": "1700000000000"}],
            },
        }

        def fake_http(url, **_):
            if "binance" in url:
                return None
            if "bybit" in url:
                return bybit_response
            return None

        with patch.object(cdf, "_http_get_json", side_effect=fake_http):
            entry = cdf.fetch_funding_entry("BTCUSDT", config=self.cfg)

        assert entry is not None
        assert "fundingRate" in entry
        assert "fundingTime" in entry
        assert "source" in entry
        assert isinstance(entry["fundingRate"], float)
        assert isinstance(entry["fundingTime"], int)
        assert abs(entry["fundingRate"] - 0.00012345) < 1e-9

    def test_funding_time_is_8h_aligned(self):
        """fundingTime should be aligned to the most recent 8h boundary."""
        bybit_response = {
            "retCode": 0,
            "result": {"list": [{"fundingRate": "0.0001"}]},
        }

        def fake_http(url, **_):
            if "bybit" in url:
                return bybit_response
            return None

        with patch.object(cdf, "_http_get_json", side_effect=fake_http):
            entry = cdf.fetch_funding_entry("BTCUSDT", config=self.cfg)

        assert entry is not None
        funding_time_s = entry["fundingTime"] // 1000
        # Must be divisible by 8h (28800s) -- the 8h settlement boundary
        assert funding_time_s % (8 * 3600) == 0, \
            f"fundingTime {entry['fundingTime']} not 8h-aligned"

    def test_funding_time_not_wall_clock(self):
        """fundingTime should NOT equal int(time.time()*1000) -- that would mean
        it's using wall-clock time instead of the 8h-aligned settlement."""
        bybit_response = {
            "retCode": 0,
            "result": {"list": [{"fundingRate": "0.0001"}]},
        }

        def fake_http(url, **_):
            if "bybit" in url:
                return bybit_response
            return None

        # Record the wall-clock time during the test
        wall_clock_ms = int(time.time() * 1000)

        with patch.object(cdf, "_http_get_json", side_effect=fake_http):
            entry = cdf.fetch_funding_entry("BTCUSDT", config=self.cfg)

        assert entry is not None
        # The 8h-aligned time should be at most 8h before wall-clock
        diff_ms = wall_clock_ms - entry["fundingTime"]
        assert 0 <= diff_ms < 8 * 3600 * 1000, \
            f"fundingTime too far from wall-clock: diff={diff_ms}ms"

    def test_fetch_funding_entry_returns_none_on_all_failures(self):
        with patch.object(cdf, "_http_get_json", return_value=None):
            entry = cdf.fetch_funding_entry("BTCUSDT", config=self.cfg)
        assert entry is None

    def test_estimate_funding_time_ms_returns_8h_boundary(self):
        """_estimate_funding_time_ms should return the most recent 8h boundary."""
        result = cdf._estimate_funding_time_ms()
        result_s = result // 1000
        assert result_s % (8 * 3600) == 0
        # Should be in the past (not future)
        assert result <= int(time.time() * 1000)


def test_public_api_signatures():
    """Make sure the public API matches the documented contract."""
    assert callable(cdf.fetch_tickers_24h)
    assert callable(cdf.fetch_klines)
    assert callable(cdf.fetch_funding_rate)


# ---------------------------------------------------------------------------
# Dynamic CoinGecko id resolver (Plan 2 — fix/dynamic-coingecko-id-lookup)
# ---------------------------------------------------------------------------
class TestDynamicCoinGeckoResolver:
    """Tests for ``_resolve_coingecko_id`` — the replacement for the
    hardcoded ``_COINGECKO_IDS`` dict. Each test uses a tmpdir-isolated
    cache file and resets the in-process resolver state so they don't
    leak into one another."""

    def setup_method(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.cache_path = Path(self.tmp_dir.name) / "coingecko_id_cache.json"
        # Patch the cache path constant for the duration of the test
        self._orig_path = cdf.COINGECKO_ID_CACHE_PATH
        cdf.COINGECKO_ID_CACHE_PATH = self.cache_path
        # Reset in-memory resolver state so it re-hydrates from our tmp file
        cdf._resolve_state["ids"] = {}
        cdf._resolve_state["list_fetched_at"] = 0.0
        cdf._resolve_state["loaded_from_disk"] = False

    def teardown_method(self):
        cdf.COINGECKO_ID_CACHE_PATH = self._orig_path
        cdf._resolve_state["ids"] = {}
        cdf._resolve_state["list_fetched_at"] = 0.0
        cdf._resolve_state["loaded_from_disk"] = False
        self.tmp_dir.cleanup()

    # -- Cache hit path: seed entries resolve without network --------------

    def test_seed_entry_resolves_without_network_call(self):
        """BTC is in the seed; resolution must not trigger any HTTP call."""
        with patch.object(cdf, "_http_get_json") as mock_http, \
             patch.object(cdf, "_coingecko_throttle"):
            result = cdf._resolve_coingecko_id("BTC")
        assert result == "bitcoin"
        assert mock_http.call_count == 0, "Seed lookup should not hit network"

    def test_seed_entry_lowercase_input(self):
        """Resolution is case-insensitive via .upper() normalization."""
        with patch.object(cdf, "_http_get_json") as mock_http, \
             patch.object(cdf, "_coingecko_throttle"):
            assert cdf._resolve_coingecko_id("eth") == "ethereum"
        assert mock_http.call_count == 0

    # -- Cache miss path: /coins/list fetched, mapping persisted -----------

    def test_cache_miss_fetches_coins_list_and_resolves(self):
        """A symbol NOT in the seed (e.g. 'RLB') should trigger /coins/list
        fetch, find a unique match, persist it, and return the id."""
        coins_list = [
            {"id": "rollbit-coin", "symbol": "rlb", "name": "Rollbit Coin"},
            {"id": "bitcoin", "symbol": "btc", "name": "Bitcoin"},
            {"id": "ethereum", "symbol": "eth", "name": "Ethereum"},
        ]

        def fake_http(url, **_):
            if "coins/list" in url:
                return coins_list
            return None

        with patch.object(cdf, "_http_get_json", side_effect=fake_http), \
             patch.object(cdf, "_coingecko_throttle"):
            result = cdf._resolve_coingecko_id("RLB")

        assert result == "rollbit-coin"
        # Cache file written
        assert self.cache_path.exists()
        with open(self.cache_path, "r", encoding="utf-8") as fh:
            cached = json.load(fh)
        assert cached["ids"]["RLB"] == "rollbit-coin"
        assert cached["list_fetched_at"] > 0

    def test_ambiguous_symbol_prefers_highest_market_cap(self):
        """If multiple coins share a symbol, the resolver disambiguates
        via /coins/markets and picks the highest market_cap entry."""
        coins_list = [
            # Two distinct coins both reporting symbol 'gas'
            {"id": "gas-coin", "symbol": "gas", "name": "Gas Token"},
            {"id": "gas-real", "symbol": "gas", "name": "Real Gas"},
            {"id": "bitcoin", "symbol": "btc", "name": "Bitcoin"},
        ]
        markets_response = [
            {"id": "gas-coin", "market_cap": 1_000_000},
            {"id": "gas-real", "market_cap": 500_000_000},  # bigger -> winner
        ]

        def fake_http(url, **_):
            if "coins/list" in url:
                return coins_list
            if "coins/markets" in url and "ids=" in url:
                return markets_response
            return None

        with patch.object(cdf, "_http_get_json", side_effect=fake_http), \
             patch.object(cdf, "_coingecko_throttle"):
            result = cdf._resolve_coingecko_id("GAS")

        assert result == "gas-real"

    def test_unknown_symbol_returns_none_and_caches_negative(self):
        """A symbol with NO matching entry in /coins/list should return
        None AND record a negative-cache sentinel so we don't keep
        retrying the remote fetch for the same dud symbol."""
        coins_list = [
            {"id": "bitcoin", "symbol": "btc", "name": "Bitcoin"},
        ]
        call_log: list[str] = []

        def fake_http(url, **_):
            call_log.append(url)
            if "coins/list" in url:
                return coins_list
            return None

        with patch.object(cdf, "_http_get_json", side_effect=fake_http), \
             patch.object(cdf, "_coingecko_throttle"):
            assert cdf._resolve_coingecko_id("ZZZNONEXIST") is None
            # Second call: should NOT re-fetch /coins/list
            assert cdf._resolve_coingecko_id("ZZZNONEXIST") is None

        list_fetches = [u for u in call_log if "coins/list" in u]
        assert len(list_fetches) == 1, \
            f"Negative cache should suppress repeat /coins/list fetches; got {list_fetches}"

    # -- Persistence: cache survives a fresh resolver state ----------------

    def test_cache_persists_to_disk_and_rehydrates(self):
        """Resolve once -> cache file written -> reset in-mem state ->
        next resolve reads from disk without any HTTP call."""
        coins_list = [
            {"id": "memecoin-meme", "symbol": "meme", "name": "Meme Coin"},
        ]

        def fake_http(url, **_):
            if "coins/list" in url:
                return coins_list
            return None

        with patch.object(cdf, "_http_get_json", side_effect=fake_http), \
             patch.object(cdf, "_coingecko_throttle"):
            first = cdf._resolve_coingecko_id("MEME")
        assert first == "memecoin-meme"
        assert self.cache_path.exists()

        # Now wipe in-memory state — simulate fresh process
        cdf._resolve_state["ids"] = {}
        cdf._resolve_state["list_fetched_at"] = 0.0
        cdf._resolve_state["loaded_from_disk"] = False

        # Bump the timestamp on disk so the TTL check thinks the snapshot
        # is fresh — the resolver should NOT refetch /coins/list.
        with open(self.cache_path, "r", encoding="utf-8") as fh:
            disk = json.load(fh)
        disk["list_fetched_at"] = time.time()
        with open(self.cache_path, "w", encoding="utf-8") as fh:
            json.dump(disk, fh)

        with patch.object(cdf, "_http_get_json") as mock_http, \
             patch.object(cdf, "_coingecko_throttle"):
            second = cdf._resolve_coingecko_id("MEME")

        assert second == "memecoin-meme"
        assert mock_http.call_count == 0, \
            "Re-resolution after disk rehydration should be HTTP-free"

    # -- Geo-block on /coins/list falls back to seed only ------------------

    def test_geo_blocked_coins_list_falls_back_to_seed(self):
        """If CoinGecko /coins/list is geo-blocked, seeded entries still
        resolve and unknown symbols return None (no crash)."""
        with patch.object(cdf, "_http_get_json", return_value=cdf._GEO_BLOCKED), \
             patch.object(cdf, "_coingecko_throttle"):
            # Seed entry still resolves
            assert cdf._resolve_coingecko_id("BTC") == "bitcoin"
            # Unknown symbol — fetch returns None, resolver returns None
            assert cdf._resolve_coingecko_id("ZZZUNKNOWN") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
