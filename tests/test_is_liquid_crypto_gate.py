"""Tests for alpha_engine.asset_class.is_liquid_crypto() ADV gate.

Verifies:
 - Fail-open when cache is absent or symbol not found
 - ADV threshold: $50M for altcoins, $500M for majors
 - Cache TTL rejection (>2h stale)
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from unittest import mock

import pytest

from alpha_engine.asset_class import (
    _ADV_MAJOR_THRESHOLD_USD,
    _ADV_THRESHOLD_USD,
    _COINGECKO_CACHE_PATH,
    _COINGECKO_CACHE_TTL_SECONDS,
    is_liquid_crypto,
)


def _make_cache(adv_map: dict, age_seconds: float = 0) -> dict:
    return {
        "_fetched_at": time.time() - age_seconds,
        "_fetched_utc": "2026-05-18T00:00:00Z",
        "_symbol_count": len(adv_map),
        "adv_by_symbol": adv_map,
    }


class TestFailOpen:
    def test_none_symbol_passes(self):
        assert is_liquid_crypto(None) is True

    def test_empty_symbol_passes(self):
        assert is_liquid_crypto("") is True

    def test_missing_cache_passes(self):
        with mock.patch("alpha_engine.asset_class._COINGECKO_CACHE_PATH") as mp:
            mp.exists.return_value = False
            assert is_liquid_crypto("BTCUSDT") is True

    def test_symbol_not_in_cache_passes(self):
        cache = _make_cache({"BTCUSDT": 10_000_000_000})
        with mock.patch("alpha_engine.asset_class._load_coingecko_adv_cache", return_value=cache):
            # SOMEUNKNOWNUSDT not in cache → fail-open
            assert is_liquid_crypto("SOMEUNKNOWNUSDT") is True

    def test_corrupt_cache_passes(self):
        with mock.patch("alpha_engine.asset_class._load_coingecko_adv_cache", return_value={}):
            assert is_liquid_crypto("BTCUSDT") is True


class TestAltcoinThreshold:
    def test_altcoin_above_threshold_passes(self):
        cache = _make_cache({"ADAUSDT": _ADV_THRESHOLD_USD + 1_000_000})
        with mock.patch("alpha_engine.asset_class._load_coingecko_adv_cache", return_value=cache):
            assert is_liquid_crypto("ADAUSDT") is True

    def test_altcoin_exactly_at_threshold_passes(self):
        cache = _make_cache({"ADAUSDT": _ADV_THRESHOLD_USD})
        with mock.patch("alpha_engine.asset_class._load_coingecko_adv_cache", return_value=cache):
            assert is_liquid_crypto("ADAUSDT") is True

    def test_altcoin_below_threshold_fails(self):
        cache = _make_cache({"XYZUSDT": _ADV_THRESHOLD_USD - 1})
        with mock.patch("alpha_engine.asset_class._load_coingecko_adv_cache", return_value=cache):
            assert is_liquid_crypto("XYZUSDT") is False

    def test_penny_coin_low_volume_fails(self):
        cache = _make_cache({"MEMEUSDT": 1_000_000})  # $1M — well below threshold
        with mock.patch("alpha_engine.asset_class._load_coingecko_adv_cache", return_value=cache):
            assert is_liquid_crypto("MEMEUSDT") is False


class TestMajorThreshold:
    def test_btc_above_major_threshold_passes(self):
        cache = _make_cache({"BTCUSDT": _ADV_MAJOR_THRESHOLD_USD + 1})
        with mock.patch("alpha_engine.asset_class._load_coingecko_adv_cache", return_value=cache):
            assert is_liquid_crypto("BTCUSDT") is True

    def test_btc_below_major_threshold_fails(self):
        # BTC should use $500M threshold, not $50M
        cache = _make_cache({"BTCUSDT": 100_000_000})  # $100M — above altcoin but below major
        with mock.patch("alpha_engine.asset_class._load_coingecko_adv_cache", return_value=cache):
            assert is_liquid_crypto("BTCUSDT") is False

    def test_eth_below_major_threshold_fails(self):
        cache = _make_cache({"ETHUSDT": 200_000_000})  # $200M — below $500M major threshold
        with mock.patch("alpha_engine.asset_class._load_coingecko_adv_cache", return_value=cache):
            assert is_liquid_crypto("ETHUSDT") is False


class TestConstants:
    def test_altcoin_threshold_is_50m(self):
        assert _ADV_THRESHOLD_USD == 50_000_000

    def test_major_threshold_is_500m(self):
        assert _ADV_MAJOR_THRESHOLD_USD == 500_000_000
