"""Tests for non-crypto bucket inference (aligned with audit dashboard template)."""

import pytest

from audit_trail.dashboard_generator import nc_asset_category_for_pick


@pytest.mark.parametrize(
    "pick,expected",
    [
        ({"symbol": "EURUSD=X", "asset_class": ""}, "FOREX"),
        ({"symbol": "GC=F", "category": ""}, "FUTURES"),
        ({"symbol": "AAPL", "asset_class": ""}, "EQUITY"),
        ({"symbol": "XAUUSD"}, "COMMODITY"),
        ({"symbol": "XAUwhatever"}, "COMMODITY"),
        ({"symbol": "XAGUSD"}, "COMMODITY"),
        ({"asset_class": "FX"}, "FOREX"),
        ({"category": "STOCKS"}, "STOCK"),
        ({"asset_class": "ETF"}, "ETF"),
    ],
)
def test_nc_asset_category_for_pick(pick: dict, expected: str | None) -> None:
    assert nc_asset_category_for_pick(pick) == expected
