"""Tests for the top-3 pick tracker. No network: prices are injected."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import top3_pick_tracker as t  # noqa: E402


def _pick(**kw):
    base = {"symbol": "SPY", "rank": 1, "tier": "BENCHMARK", "entry_price": 100.0}
    base.update(kw)
    return base


def test_return_is_computed_against_frozen_entry():
    rows = t.mark_to_market([_pick()], {"SPY": 110.0})
    assert rows[0]["return_pct"] == 10.0
    assert rows[0]["state"] == "OPEN"


def test_missing_entry_price_is_no_price_not_dropped():
    rows = t.mark_to_market([_pick(entry_price=None)], {"SPY": 110.0})
    assert len(rows) == 1
    assert rows[0]["state"] == "NO_PRICE"
    assert rows[0]["return_pct"] is None


def test_missing_market_data_is_no_data_and_kept_in_denominator():
    rows = t.mark_to_market([_pick(symbol="NOPE")], {"SPY": 110.0})
    assert rows[0]["state"] == "NO_DATA"


def test_zero_entry_price_does_not_divide_by_zero():
    rows = t.mark_to_market([_pick(entry_price=0)], {"SPY": 110.0})
    assert rows[0]["state"] == "NO_PRICE"


def test_all_picks_flattens_with_asset_class_and_preserves_rank():
    reg = {"classes": [
        {"asset_class": "EQUITY", "picks": [_pick(rank=1), _pick(symbol="QQQ", rank=2)]},
        {"asset_class": "BOND", "picks": [_pick(symbol="AGG", rank=1)]},
    ]}
    picks = t.all_picks(reg)
    assert [p["symbol"] for p in picks] == ["SPY", "QQQ", "AGG"]
    assert [p["rank"] for p in picks] == [1, 2, 1]
    assert picks[2]["asset_class"] == "BOND"
