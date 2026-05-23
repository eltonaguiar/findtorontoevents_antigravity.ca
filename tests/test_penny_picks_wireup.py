"""Wire-up regression tests for penny_screener → JSON_PICK_SOURCES (B20, 2026-05-02).

Background: findstocks/portfolio2/data/penny_picks_latest.json is emitted fresh
(weekdays 12:00 UTC) by .github/workflows/penny-stock-picks.yml but was NOT
registered in JSON_PICK_SOURCES. This means the dashboard never read it.

Fix: register ("penny_screener", "findstocks/portfolio2/data/penny_picks_latest.json", None)
in JSON_PICK_SOURCES and teach _extract_picks() to handle the top_picks key with
direction/strategy/asset_class normalization.

These tests pin the registration + schema contract so future refactors cannot
silently re-orphan the feed.
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
PENNY_PICKS_PATH = REPO / "findstocks" / "portfolio2" / "data" / "penny_picks_latest.json"


# ── JSON_PICK_SOURCES registration ─────────────────────────────────────────


def test_penny_screener_registered_in_json_pick_sources() -> None:
    """penny_screener must appear in JSON_PICK_SOURCES so the dashboard
    loader reads it on every rebuild."""
    from audit_trail import dashboard_generator as dg

    registered = [name for name, _, _ in dg.JSON_PICK_SOURCES]
    assert "penny_screener" in registered, (
        "'penny_screener' not in JSON_PICK_SOURCES. "
        "B20 fix requires direct registration so picks surface on /audit."
    )


def test_penny_screener_path_in_json_pick_sources() -> None:
    expected_path = "findstocks/portfolio2/data/penny_picks_latest.json"
    from audit_trail import dashboard_generator as dg

    paths = [path for name, path, _ in dg.JSON_PICK_SOURCES if name == "penny_screener"]
    assert paths, "penny_screener source not found in JSON_PICK_SOURCES"
    assert paths[0] == expected_path, (
        f"Expected path '{expected_path}', got '{paths[0]}'"
    )


def test_penny_screener_no_closed_path() -> None:
    """Closed-pick path should be None — outcomes settle via universal resolver."""
    from audit_trail import dashboard_generator as dg

    entries = [(name, cp) for name, _, cp in dg.JSON_PICK_SOURCES if name == "penny_screener"]
    assert entries, "penny_screener not in JSON_PICK_SOURCES"
    _, closed_path = entries[0]
    assert closed_path is None, (
        f"Expected closed_path=None for penny_screener, got '{closed_path}'"
    )


# ── _extract_picks schema handling ────────────────────────────────────────


def test_extract_picks_handles_top_picks_key() -> None:
    """_extract_picks must return the top_picks list for penny_screener schema."""
    from audit_trail.dashboard_generator import _extract_picks

    fake_payload = {
        "date": "2026-05-02",
        "generated_at": "2026-05-02T12:00:00Z",
        "total_candidates": 50,
        "top_picks_count": 2,
        "top_picks": [
            {
                "symbol": "LCX.V",
                "name": "LYCOS ENERGY INC",
                "price": 2.28,
                "score": 77.01,
                "rating": "STRONG_BUY",
                "exchange": "TSX-V",
                "country": "CA",
                "stop_loss": 1.938,
                "take_profit": 2.964,
            },
            {
                "symbol": "TEST.T",
                "name": "TEST CORP",
                "price": 1.00,
                "score": 60.0,
                "rating": "BUY",
                "exchange": "TSX",
                "country": "CA",
                "stop_loss": 0.85,
                "take_profit": 1.30,
            },
        ],
        "all_scores": [],
    }
    extracted = _extract_picks(fake_payload)
    assert isinstance(extracted, list)
    assert len(extracted) == 2
    assert extracted[0]["symbol"] == "LCX.V"
    assert extracted[1]["symbol"] == "TEST.T"


def test_extract_picks_normalizes_direction_from_rating() -> None:
    """STRONG_BUY/BUY → LONG; SELL/STRONG_SELL → SHORT."""
    from audit_trail.dashboard_generator import _extract_picks

    payload = {
        "generated_at": "2026-05-02T12:00:00Z",
        "top_picks": [
            {"symbol": "A", "rating": "STRONG_BUY", "price": 1.0, "stop_loss": 0.85, "take_profit": 1.30},
            {"symbol": "B", "rating": "BUY", "price": 1.0, "stop_loss": 0.85, "take_profit": 1.30},
            {"symbol": "C", "rating": "SELL", "price": 1.0, "stop_loss": 1.15, "take_profit": 0.80},
            {"symbol": "D", "rating": "STRONG_SELL", "price": 1.0, "stop_loss": 1.15, "take_profit": 0.80},
        ],
    }
    picks = _extract_picks(payload)
    dirs = {p["symbol"]: p["direction"] for p in picks}
    assert dirs["A"] == "LONG"
    assert dirs["B"] == "LONG"
    assert dirs["C"] == "SHORT"
    assert dirs["D"] == "SHORT"


def test_extract_picks_sets_strategy() -> None:
    """Penny picks lack a strategy field; _extract_picks must set penny_stock_screener."""
    from audit_trail.dashboard_generator import _extract_picks

    payload = {
        "generated_at": "2026-05-02T12:00:00Z",
        "top_picks": [
            {"symbol": "X", "rating": "BUY", "price": 1.0, "stop_loss": 0.85, "take_profit": 1.30},
        ],
    }
    picks = _extract_picks(payload)
    assert picks[0].get("strategy") == "penny_stock_screener"


def test_extract_picks_sets_asset_class_equity() -> None:
    """Penny picks lack an asset_class; _extract_picks must default to EQUITY."""
    from audit_trail.dashboard_generator import _extract_picks

    payload = {
        "generated_at": "2026-05-02T12:00:00Z",
        "top_picks": [
            {"symbol": "X", "rating": "BUY", "price": 1.0, "stop_loss": 0.85, "take_profit": 1.30},
        ],
    }
    picks = _extract_picks(payload)
    assert picks[0].get("asset_class") == "EQUITY"


def test_extract_picks_propagates_parent_timestamp() -> None:
    """Individual picks don't have timestamps; parent generated_at must propagate."""
    from audit_trail.dashboard_generator import _extract_picks

    ts = "2026-05-02T12:00:00Z"
    payload = {
        "generated_at": ts,
        "top_picks": [
            {"symbol": "X", "rating": "BUY", "price": 1.0, "stop_loss": 0.85, "take_profit": 1.30},
        ],
    }
    picks = _extract_picks(payload)
    assert picks[0].get("generated_at") == ts


def test_extract_picks_preserves_existing_direction() -> None:
    """If a pick already has direction set, don't overwrite it."""
    from audit_trail.dashboard_generator import _extract_picks

    payload = {
        "generated_at": "2026-05-02T12:00:00Z",
        "top_picks": [
            {
                "symbol": "X",
                "rating": "BUY",
                "direction": "SHORT",  # explicitly set; should be preserved
                "price": 1.0,
                "stop_loss": 0.85,
                "take_profit": 1.30,
            },
        ],
    }
    picks = _extract_picks(payload)
    assert picks[0]["direction"] == "SHORT"


def test_extract_picks_does_not_affect_picks_key_format() -> None:
    """Adding top_picks handling must not break the existing picks key path."""
    from audit_trail.dashboard_generator import _extract_picks

    payload = {
        "generated_at": "2026-05-02T12:00:00Z",
        "picks": [
            {"symbol": "Y", "direction": "LONG", "strategy": "test_strat"},
        ],
    }
    picks = _extract_picks(payload)
    assert len(picks) == 1
    assert picks[0]["symbol"] == "Y"


# ── Live file schema compatibility ────────────────────────────────────────


@pytest.mark.skipif(
    not PENNY_PICKS_PATH.exists(),
    reason="penny_picks_latest.json not present (workflow hasn't run yet)"
)
def test_live_penny_picks_file_extractable() -> None:
    """The live file must yield at least 1 pick via _extract_picks."""
    import json
    from audit_trail.dashboard_generator import _extract_picks

    data = json.loads(PENNY_PICKS_PATH.read_text())
    picks = _extract_picks(data)
    assert isinstance(picks, list)
    assert len(picks) >= 1, (
        f"Expected >=1 pick from {PENNY_PICKS_PATH}, got {len(picks)}. "
        "Check if the file is using a different top-level key."
    )
    first = picks[0]
    assert first.get("symbol"), "First pick must have a symbol"
    assert first.get("direction") in ("LONG", "SHORT"), (
        f"First pick direction must be LONG or SHORT, got {first.get('direction')!r}"
    )
    assert first.get("strategy") == "penny_stock_screener"
    assert first.get("asset_class") == "EQUITY"
