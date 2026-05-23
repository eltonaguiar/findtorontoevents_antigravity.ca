"""Wire-up regression + schema tests for cot_positioning → JSON_PICK_SOURCES (B7 prereq, 2026-05-02).

Background: alpha_engine/data/cot_signals.json is emitted by
alpha_engine/cot_positioning.py when run on the forex-agent cron.  The file was
NOT registered in JSON_PICK_SOURCES, and its __main__ block wrote a simplified
{pair, signal, confidence, percentile} schema incompatible with _normalize_pick.

This PR fixes:
1. cot_positioning.py __main__ now writes the full pick schema.
2. _extract_picks() has a "cot_positioning" adapter that handles both legacy and new
   format, with a content-based freshness guard (>14d → return []).
3. JSON_PICK_SOURCES is extended with the cot_positioning entry.
4. _FRESHNESS_REQUIRED_HOURS["cot_positioning"] = 14*24 as belt-and-suspenders.

These tests pin the wire-up contract and schema so future refactors cannot silently
re-orphan the feed or bypass the staleness guard.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


# ── JSON_PICK_SOURCES registration ─────────────────────────────────────────


def test_cot_registered_in_json_pick_sources() -> None:
    """cot_signals.json must appear in JSON_PICK_SOURCES."""
    from audit_trail import dashboard_generator as dg

    cot_path = "alpha_engine/data/cot_signals.json"
    registered_paths = [path for _, path, _ in dg.JSON_PICK_SOURCES]
    assert cot_path in registered_paths, (
        f"'{cot_path}' not found in JSON_PICK_SOURCES. "
        "B7 prereq fix requires direct registration."
    )


def test_cot_source_name_in_json_pick_sources() -> None:
    """The source name 'cot_positioning' must be registered."""
    from audit_trail import dashboard_generator as dg

    registered_names = [name for name, _, _ in dg.JSON_PICK_SOURCES]
    assert "cot_positioning" in registered_names, (
        "'cot_positioning' not in JSON_PICK_SOURCES. "
        "B7 prereq fix requires this registration for picks to reach the dashboard."
    )


def test_cot_closed_path_is_none() -> None:
    """COT has no separate closed-picks file; closed path must be None."""
    from audit_trail import dashboard_generator as dg

    for name, _, closed in dg.JSON_PICK_SOURCES:
        if name == "cot_positioning":
            assert closed is None, (
                "cot_positioning closed_path should be None — no separate closed file exists."
            )
            return
    pytest.fail("'cot_positioning' not found in JSON_PICK_SOURCES")


# ── Freshness guard ─────────────────────────────────────────────────────────


def test_cot_in_freshness_required_hours() -> None:
    """cot_positioning must be in _FRESHNESS_REQUIRED_HOURS so mtime-stale files are skipped."""
    from audit_trail import dashboard_generator as dg

    assert "cot_positioning" in dg._FRESHNESS_REQUIRED_HOURS, (
        "'cot_positioning' not in _FRESHNESS_REQUIRED_HOURS. "
        "Add 'cot_positioning': 14 * 24 to protect against stale CFTC data."
    )
    assert dg._FRESHNESS_REQUIRED_HOURS["cot_positioning"] >= 7 * 24, (
        "cot_positioning freshness threshold should be at least 7 days (CFTC publishes weekly)."
    )


def test_extract_picks_blocks_stale_cot_content() -> None:
    """_extract_picks must return [] when generated_at is older than 14 days."""
    from audit_trail.dashboard_generator import _extract_picks

    stale_ts = (datetime.now(timezone.utc) - timedelta(days=47)).isoformat()
    data = {
        "generated_at": stale_ts,
        "scanner": "cot_positioning",
        "picks": [
            {"pair": "GBPUSD", "signal": "SELL", "confidence": 54.6, "percentile": 92.3},
        ],
    }
    result = _extract_picks(data)
    assert result == [], (
        f"Expected [] for 47d-stale COT data, got {len(result)} picks. "
        "The freshness guard must reject cot_signals.json older than 14d."
    )


def test_extract_picks_allows_fresh_cot_content() -> None:
    """_extract_picks must return picks when generated_at is within 14 days."""
    from audit_trail.dashboard_generator import _extract_picks

    fresh_ts = datetime.now(timezone.utc).isoformat()
    data = {
        "generated_at": fresh_ts,
        "scanner": "cot_positioning",
        "picks": [
            {"pair": "GBPUSD", "signal": "SELL", "confidence": 54.6, "percentile": 92.3},
            {"pair": "AUDUSD", "signal": "BUY", "confidence": 62.3, "percentile": 3.8},
        ],
    }
    result = _extract_picks(data)
    assert len(result) == 2, f"Expected 2 picks for fresh COT data, got {len(result)}"


# ── Schema adapter (legacy format: pair/signal/confidence/percentile) ────────


def _make_fresh_cot(picks: list) -> dict:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scanner": "cot_positioning",
        "picks": picks,
    }


def test_cot_adapter_maps_pair_to_symbol() -> None:
    """Legacy 'pair' field must become 'symbol' with =X suffix."""
    from audit_trail.dashboard_generator import _extract_picks

    result = _extract_picks(_make_fresh_cot([
        {"pair": "GBPUSD", "signal": "SELL", "confidence": 54.6, "percentile": 92.3},
    ]))
    assert len(result) == 1
    assert result[0]["symbol"] == "GBPUSD=X", (
        f"Expected symbol='GBPUSD=X', got {result[0].get('symbol')!r}"
    )


def test_cot_adapter_sell_becomes_short() -> None:
    """SELL signal must map to SHORT direction."""
    from audit_trail.dashboard_generator import _extract_picks

    result = _extract_picks(_make_fresh_cot([
        {"pair": "USDJPY", "signal": "SELL", "confidence": 70.0, "percentile": 100.0},
    ]))
    assert result[0]["direction"] == "SHORT", (
        f"Expected direction='SHORT' for SELL signal, got {result[0].get('direction')!r}"
    )


def test_cot_adapter_buy_becomes_long() -> None:
    """BUY signal must map to LONG direction."""
    from audit_trail.dashboard_generator import _extract_picks

    result = _extract_picks(_make_fresh_cot([
        {"pair": "AUDUSD", "signal": "BUY", "confidence": 62.3, "percentile": 3.8},
    ]))
    assert result[0]["direction"] == "LONG", (
        f"Expected direction='LONG' for BUY signal, got {result[0].get('direction')!r}"
    )


def test_cot_adapter_sets_strategy() -> None:
    """Strategy must be 'cftc_cot_commercial_signal' for all COT picks."""
    from audit_trail.dashboard_generator import _extract_picks

    result = _extract_picks(_make_fresh_cot([
        {"pair": "USDCAD", "signal": "BUY", "confidence": 66.2, "percentile": 1.9},
    ]))
    assert result[0]["strategy"] == "cftc_cot_commercial_signal", (
        f"Expected strategy='cftc_cot_commercial_signal', got {result[0].get('strategy')!r}"
    )


def test_cot_adapter_sets_asset_class_forex() -> None:
    """Asset class must be 'FOREX' (uppercase) for all COT picks."""
    from audit_trail.dashboard_generator import _extract_picks

    result = _extract_picks(_make_fresh_cot([
        {"pair": "NZDUSD", "signal": "SELL", "confidence": 55.0, "percentile": 88.0},
    ]))
    assert result[0]["asset_class"] == "FOREX", (
        f"Expected asset_class='FOREX', got {result[0].get('asset_class')!r}"
    )


def test_cot_adapter_sets_timeframe() -> None:
    """Timeframe must be '1w' (COT data is weekly)."""
    from audit_trail.dashboard_generator import _extract_picks

    result = _extract_picks(_make_fresh_cot([
        {"pair": "USDCHF", "signal": "SELL", "confidence": 54.6, "percentile": 92.3},
    ]))
    assert result[0]["timeframe"] == "1w", (
        f"Expected timeframe='1w', got {result[0].get('timeframe')!r}"
    )


def test_cot_adapter_propagates_parent_timestamp() -> None:
    """Picks without generated_at must receive the parent generated_at."""
    from audit_trail.dashboard_generator import _extract_picks

    fresh_ts = datetime.now(timezone.utc).isoformat()
    data = {
        "generated_at": fresh_ts,
        "scanner": "cot_positioning",
        "picks": [{"pair": "GBPUSD", "signal": "SELL", "confidence": 54.6, "percentile": 92.3}],
    }
    result = _extract_picks(data)
    assert result[0].get("generated_at") == fresh_ts, (
        "Parent generated_at must be propagated to picks that lack a timestamp."
    )


def test_cot_adapter_respects_existing_symbol_in_new_format() -> None:
    """New-format picks (already have symbol) must not have symbol overwritten."""
    from audit_trail.dashboard_generator import _extract_picks

    fresh_ts = datetime.now(timezone.utc).isoformat()
    data = {
        "generated_at": fresh_ts,
        "scanner": "cot_positioning",
        "picks": [
            {
                "symbol": "GBPUSD=X",
                "direction": "SHORT",
                "strategy": "cftc_cot_commercial_signal",
                "asset_class": "FOREX",
                "timeframe": "1w",
                "confidence": 54.6,
                "generated_at": fresh_ts,
            }
        ],
    }
    result = _extract_picks(data)
    assert len(result) == 1
    assert result[0]["symbol"] == "GBPUSD=X"
    assert result[0]["direction"] == "SHORT"


# ── cot_positioning.py __main__ schema fix ─────────────────────────────────


def test_cot_positioning_module_imports() -> None:
    """alpha_engine.cot_positioning must import cleanly."""
    import importlib
    mod = importlib.import_module("alpha_engine.cot_positioning")
    assert hasattr(mod, "COT_STRATEGIES"), "COT_STRATEGIES registry missing"
    assert hasattr(mod, "cot_positioning_strategy"), "cot_positioning_strategy function missing"


def test_cot_strategies_registry_contains_cot_positioning() -> None:
    """COT_STRATEGIES must map 'cot_positioning' to the strategy function."""
    from alpha_engine.cot_positioning import COT_STRATEGIES, cot_positioning_strategy

    assert "cot_positioning" in COT_STRATEGIES
    assert COT_STRATEGIES["cot_positioning"] is cot_positioning_strategy
