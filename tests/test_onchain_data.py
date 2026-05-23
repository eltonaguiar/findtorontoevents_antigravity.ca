"""
Tests for genome.onchain_data — Real On-Chain Data Fetcher
"""

import json
import time
from unittest.mock import patch, MagicMock

import sys
import importlib.util
from pathlib import Path

import pytest

# Import directly to avoid genome.__init__ pulling in pandas/heavy deps
_spec = importlib.util.spec_from_file_location(
    "genome.onchain_data",
    Path(__file__).resolve().parent.parent / "genome" / "onchain_data.py",
)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["genome.onchain_data"] = _mod
_spec.loader.exec_module(_mod)
OnchainDataFetcher = _mod.OnchainDataFetcher
DEFAULTS = _mod.DEFAULTS


# ------------------------------------------------------------------ #
#  Fixtures
# ------------------------------------------------------------------ #

@pytest.fixture
def fetcher(tmp_path, monkeypatch):
    """Fresh fetcher with cache pointed at a temp directory."""
    cache_file = tmp_path / "onchain_cache.json"
    monkeypatch.setattr(_mod, "CACHE_PATH", cache_file)
    return OnchainDataFetcher(cache_ttl=3600)


def _mock_response(json_data, status=200):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    if status >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status}")
    return resp


# ------------------------------------------------------------------ #
#  fetch_funding_rate
# ------------------------------------------------------------------ #

class TestFetchFundingRate:
    @patch.object(_mod.requests, "get")
    def test_returns_float(self, mock_get, fetcher):
        mock_get.return_value = _mock_response([{"fundingRate": "0.00012345"}])
        result = fetcher.fetch_funding_rate("BTCUSDT")
        assert isinstance(result, float)
        assert abs(result - 0.00012345) < 1e-9

    @patch.object(_mod.requests, "get")
    def test_api_failure_returns_default(self, mock_get, fetcher):
        mock_get.side_effect = Exception("timeout")
        result = fetcher.fetch_funding_rate()
        assert result == DEFAULTS["funding_rate"]


# ------------------------------------------------------------------ #
#  fetch_fear_greed
# ------------------------------------------------------------------ #

class TestFetchFearGreed:
    @patch.object(_mod.requests, "get")
    def test_returns_int(self, mock_get, fetcher):
        mock_get.return_value = _mock_response({"data": [{"value": "25"}]})
        result = fetcher.fetch_fear_greed()
        assert result == 25
        assert isinstance(result, int)

    @patch.object(_mod.requests, "get")
    def test_api_failure_returns_default(self, mock_get, fetcher):
        mock_get.side_effect = Exception("connection error")
        result = fetcher.fetch_fear_greed()
        assert result == DEFAULTS["fear_greed"]


# ------------------------------------------------------------------ #
#  fetch_ssr
# ------------------------------------------------------------------ #

class TestFetchSSR:
    @patch.object(_mod.requests, "get")
    def test_returns_float(self, mock_get, fetcher):
        mock_get.return_value = _mock_response({
            "data": {
                "total_market_cap": {"usd": 2_500_000_000_000},
                "market_cap_percentage": {"btc": 50.0, "usdt": 4.0, "usdc": 1.5},
            }
        })
        result = fetcher.fetch_ssr()
        # BTC cap = 2.5T * 0.50 = 1.25T
        # Stablecoin cap = 2.5T * 0.055 = 137.5B
        # SSR = 1.25T / 137.5B ~ 9.09
        assert isinstance(result, float)
        assert 9.0 < result < 9.2

    @patch.object(_mod.requests, "get")
    def test_api_failure_returns_default(self, mock_get, fetcher):
        mock_get.side_effect = Exception("rate limited")
        result = fetcher.fetch_ssr()
        assert result == DEFAULTS["ssr"]


# ------------------------------------------------------------------ #
#  fetch_btc_dominance
# ------------------------------------------------------------------ #

class TestFetchBTCDominance:
    @patch.object(_mod.requests, "get")
    def test_returns_float(self, mock_get, fetcher):
        mock_get.return_value = _mock_response({
            "data": {"market_cap_percentage": {"btc": 52.3}}
        })
        result = fetcher.fetch_btc_dominance()
        assert result == 52.3

    @patch.object(_mod.requests, "get")
    def test_api_failure_returns_default(self, mock_get, fetcher):
        mock_get.side_effect = Exception("dns failure")
        result = fetcher.fetch_btc_dominance()
        assert result == DEFAULTS["btc_dominance"]


# ------------------------------------------------------------------ #
#  Cache behaviour
# ------------------------------------------------------------------ #

class TestCache:
    @patch.object(_mod.requests, "get")
    def test_cache_prevents_duplicate_calls(self, mock_get, fetcher):
        mock_get.return_value = _mock_response({"data": [{"value": "30"}]})
        fetcher.fetch_fear_greed()
        fetcher.fetch_fear_greed()
        # Only one HTTP call should have been made
        assert mock_get.call_count == 1

    @patch.object(_mod.requests, "get")
    def test_expired_cache_refetches(self, mock_get, fetcher):
        fetcher.cache_ttl = 0  # expire immediately
        mock_get.return_value = _mock_response({"data": [{"value": "30"}]})
        fetcher.fetch_fear_greed()
        fetcher.fetch_fear_greed()
        assert mock_get.call_count == 2


# ------------------------------------------------------------------ #
#  get_all_genes
# ------------------------------------------------------------------ #

class TestGetAllGenes:
    @patch.object(_mod.requests, "get")
    def test_returns_complete_dict(self, mock_get, fetcher):
        def side_effect(url, **kwargs):
            if "fundingRate" in url or "fapi" in url:
                return _mock_response([{"fundingRate": "0.0001"}])
            if "alternative.me" in url:
                return _mock_response({"data": [{"value": "45"}]})
            if "coingecko" in url:
                return _mock_response({
                    "data": {
                        "total_market_cap": {"usd": 2_000_000_000_000},
                        "market_cap_percentage": {"btc": 48.0, "usdt": 4.0, "usdc": 1.5},
                    }
                })
            return _mock_response({})

        mock_get.side_effect = side_effect
        genes = fetcher.get_all_genes("BTCUSDT")

        assert "funding_rate" in genes
        assert "fear_greed" in genes
        assert "ssr" in genes
        assert "btc_dominance" in genes
        assert genes["fear_greed"] == 45


# ------------------------------------------------------------------ #
#  get_mutation_bias
# ------------------------------------------------------------------ #

class TestGetMutationBias:
    def test_extreme_fear(self):
        genes = {"fear_greed": 10, "funding_rate": 0.0, "ssr": 10.0}
        bias = OnchainDataFetcher.get_mutation_bias(genes)
        assert bias["entry_direction"] == "long"
        assert bias["tp_mult_range"] == (2.0, 5.0)

    def test_extreme_greed(self):
        genes = {"fear_greed": 90, "funding_rate": 0.0, "ssr": 10.0}
        bias = OnchainDataFetcher.get_mutation_bias(genes)
        assert bias["entry_direction"] == "short"

    def test_high_funding_rate(self):
        genes = {"fear_greed": 50, "funding_rate": 0.0005, "ssr": 10.0}
        bias = OnchainDataFetcher.get_mutation_bias(genes)
        assert bias["entry_direction"] == "short"

    def test_negative_funding_rate(self):
        genes = {"fear_greed": 50, "funding_rate": -0.0005, "ssr": 10.0}
        bias = OnchainDataFetcher.get_mutation_bias(genes)
        assert bias["entry_direction"] == "long"

    def test_low_ssr(self):
        genes = {"fear_greed": 50, "funding_rate": 0.0, "ssr": 5.0}
        bias = OnchainDataFetcher.get_mutation_bias(genes)
        assert bias["position_size_range"] == (0.05, 0.15)

    def test_neutral_returns_empty(self):
        genes = {"fear_greed": 50, "funding_rate": 0.0, "ssr": 12.0}
        bias = OnchainDataFetcher.get_mutation_bias(genes)
        assert bias == {}

    def test_funding_overrides_fear_greed(self):
        """When F&G says long but funding says short, funding wins (applied last)."""
        genes = {"fear_greed": 15, "funding_rate": 0.0005, "ssr": 10.0}
        bias = OnchainDataFetcher.get_mutation_bias(genes)
        # Funding rate check runs after F&G, so it overwrites entry_direction
        assert bias["entry_direction"] == "short"
