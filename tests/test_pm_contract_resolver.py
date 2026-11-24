"""Tests for audit_trail.pm_contract_resolver."""

from datetime import datetime, timezone

import pytest

from audit_trail.pm_contract_resolver import (
    classify_pick_kind,
    contract_side,
    index_outcomes,
    is_contract_pick,
    normalize_outcome,
    pnl_pct_for,
    resolve_contract_pick,
)

NOW = datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc)


def test_spot_derived_pm_pick_is_not_a_contract():
    # Live /audit shape: XRPUSDT LONG from polymarket_signals, no market id.
    pick = {
        "symbol": "XRPUSDT",
        "source_system": "polymarket_signals",
        "strategy": "copy_pm_pm_06dc5182",
        "entry_price": 0.949,
        "take_profit": 0.972725,
        "stop_loss": 0.934765,
        "direction": "LONG",
    }
    assert is_contract_pick(pick) is False
    assert classify_pick_kind(pick) == "spot_derived"


def test_contract_pick_requires_market_id_and_side():
    assert is_contract_pick({"market_id": "KXBTC-25", "contract_side": "YES"}) is True
    assert is_contract_pick({"market_id": "KXBTC-25"}) is False
    assert is_contract_pick({"asset_class": "PREDICTION_MARKET", "direction": "LONG"}) is True


def test_contract_side_maps_direction():
    assert contract_side({"direction": "LONG"}) == "YES"
    assert contract_side({"direction": "SHORT"}) == "NO"
    assert contract_side({"contract_side": "no"}) == "NO"
    assert contract_side({}) is None


def test_payout_math_is_binary_not_price_geometry():
    assert pnl_pct_for(0.30, 1.0) == pytest.approx(233.3333, abs=1e-3)
    assert pnl_pct_for(0.30, 0.0) == pytest.approx(-100.0)
    # entry > 1 is not a probability -> no P&L claim
    assert pnl_pct_for(1795.36, 1.0) is None
    assert pnl_pct_for(0.0, 1.0) is None


def test_resolve_winning_contract():
    pick = {"market_id": "M1", "contract_side": "YES", "entry_price": 0.40}
    out = resolve_contract_pick(pick, {"M1": {"outcome": "YES"}}, now=NOW)
    assert out["status"] == "WON"
    assert out["exit_price"] == 1.0
    assert out["pnl_pct"] == pytest.approx(150.0)
    assert out["exit_reason"] == "CONTRACT_RESOLVED"


def test_resolve_losing_contract():
    pick = {"market_id": "M1", "contract_side": "NO", "entry_price": 0.40}
    out = resolve_contract_pick(pick, {"M1": {"outcome": "YES"}}, now=NOW)
    assert out["status"] == "LOST"
    assert out["exit_price"] == 0.0
    assert out["pnl_pct"] == pytest.approx(-100.0)


def test_expired_without_outcome_never_fabricates_pnl():
    pick = {
        "market_id": "M2",
        "contract_side": "YES",
        "entry_price": 0.55,
        "end_date": "2026-11-10T00:00:00Z",
    }
    out = resolve_contract_pick(pick, {}, now=NOW)
    assert out["status"] == "EXPIRED"
    assert out["pnl_pct"] is None
    assert out["pm_resolution_status"] == "awaiting_outcome"
    assert out["exit_reason"] == "CONTRACT_UNRESOLVED"


def test_live_market_stays_open():
    pick = {
        "market_id": "M3",
        "contract_side": "YES",
        "entry_price": 0.55,
        "end_date": "2026-12-01T00:00:00Z",
    }
    out = resolve_contract_pick(pick, {}, now=NOW)
    assert out["status"] == "OPEN"
    assert out["pm_resolution_status"] == "open"


def test_outcome_index_accepts_platform_records():
    records = [
        {"ticker": "KXBTC-25", "result": "yes", "platform": "kalshi"},
        {"id": "0xabc", "resolved_outcome": "NO", "source": "polymarket"},
        {"ticker": "UNSETTLED"},
    ]
    index = index_outcomes(records)
    assert index["KXBTC-25"]["outcome"] == "YES"
    assert index["0xabc"]["outcome"] == "NO"
    assert "UNSETTLED" not in index


def test_normalize_outcome_values():
    assert normalize_outcome("YES") == "YES"
    assert normalize_outcome(True) == "YES"
    assert normalize_outcome("no") == "NO"
    assert normalize_outcome(0) == "NO"
    assert normalize_outcome("pending") is None


def test_loader_indexes_a_local_outcome_feed(tmp_path):
    from audit_trail.pm_contract_resolver import load_market_outcomes

    feed = tmp_path / "pm_market_outcomes.json"
    feed.write_text(
        '{"markets": [{"ticker": "KXFED-26", "outcome": "yes", '
        '"end_date": "2026-11-01T00:00:00Z"}]}',
        encoding="utf-8",
    )
    index = load_market_outcomes((str(feed),))
    assert index["KXFED-26"]["outcome"] == "YES"
