"""
Tests for ISSUE 2 — Binance geo-block (HTTP 451) failover in the OBI fetcher.

Verifies that ml_crypto_predictor.enhanced_models.orderbook_fetcher treats
HTTP 451 from a Binance mirror as "endpoint dead -> fall through" rather than
a fatal error, and that it reaches the KuCoin fallback when every Binance
mirror is geo-blocked.
"""

import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml_crypto_predictor.enhanced_models import orderbook_fetcher as obf


class _FakeResp:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


_GOOD_OB = {"bids": [["100", "1"]], "asks": [["101", "1"]]}


def test_451_falls_through_to_next_binance_mirror():
    """First mirror returns 451; second mirror returns valid data."""
    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append(url)
        if len(calls) == 1:
            return _FakeResp(451)
        return _FakeResp(200, _GOOD_OB)

    with patch.object(obf.requests, "get", side_effect=fake_get):
        ob = obf.fetch_orderbook_snapshot("BTCUSDT", levels=20)

    assert ob["bids"] and ob["asks"], "451 should fall through, not be fatal"
    assert len(calls) >= 2, "should have tried a second mirror after 451"


def test_all_binance_451_falls_back_to_kucoin():
    """Every Binance mirror is geo-blocked -> KuCoin fallback serves data."""
    binance_calls = []

    def fake_get(url, params=None, timeout=None):
        if "binance" in url:
            binance_calls.append(url)
            return _FakeResp(451)
        if "kucoin" in url:
            return _FakeResp(200, {"data": _GOOD_OB})
        return _FakeResp(404)

    with patch.object(obf.requests, "get", side_effect=fake_get):
        ob = obf.fetch_orderbook_snapshot("BTCUSDT", levels=20)

    assert ob["bids"] and ob["asks"], "KuCoin fallback should serve data"
    assert len(binance_calls) >= 3, "should have exhausted Binance mirrors first"


def test_all_providers_down_returns_empty_not_crash():
    """Total outage returns empty bids/asks instead of raising."""
    def fake_get(url, params=None, timeout=None):
        return _FakeResp(451)

    with patch.object(obf.requests, "get", side_effect=fake_get):
        ob = obf.fetch_orderbook_snapshot("BTCUSDT", levels=20)

    assert ob == {"bids": [], "asks": []}


if __name__ == "__main__":
    test_451_falls_through_to_next_binance_mirror()
    test_all_binance_451_falls_back_to_kucoin()
    test_all_providers_down_returns_empty_not_crash()
    print("OK — all OBI failover tests passed")
