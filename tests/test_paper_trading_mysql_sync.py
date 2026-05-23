from paper_trading.mysql_sync import _resolve_asset_class


def test_resolve_asset_class_from_symbol_for_equity():
    assert _resolve_asset_class({"symbol": "AAPL"}) == "EQUITY"


def test_resolve_asset_class_prefers_symbol_over_bad_explicit_value():
    assert _resolve_asset_class({"symbol": "BTCUSDT", "asset_class": "forex"}) == "CRYPTO"
