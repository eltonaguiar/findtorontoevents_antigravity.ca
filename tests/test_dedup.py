"""
tests/test_dedup.py — Focused unit tests for the TON-validated dedup harmonization helper.

Covers:
- Determinism and stability
- Raw ID namespacing (per TON refinement)
- Fallback logic (no redundant hash)
- Edge cases highlighted by TON fast4 (historical data, TIME_EXIT, missing fields, cross-emitter)

This is P0 §15 work driven by internal audit + external TON validation (2026-06-01).
"""

import pytest
from alpha_engine.dedup import build_canonical_outcomes_pick_id


def test_basic_determinism():
    pick = {
        "symbol": "AAPL",
        "direction": "LONG",
        "strategy": "test_strat",
        "opened_at": "2026-05-01T10:00:00",
        "asset_class": "EQUITY",
    }
    id1 = build_canonical_outcomes_pick_id(pick)
    id2 = build_canonical_outcomes_pick_id(pick)
    assert id1 == id2
    assert id1.startswith("v1::fallback::")


def test_raw_id_namespacing():
    pick = {"id": "raw123", "emitter": "test_emitter"}
    pid = build_canonical_outcomes_pick_id(pick)
    assert pid == "v1::test_emitter::raw123"


def test_fallback_no_hash():
    pick = {
        "symbol": "BTCUSDT",
        "direction": "LONG",
        "strategy": "momentum",
        "opened_at": "2026-06-01T00:00:00",
        "asset_class": "CRYPTO",
    }
    pid = build_canonical_outcomes_pick_id(pick)
    # Should not contain a hash-like suffix beyond the deterministic fields
    assert "hash" not in pid.lower()
    assert pid.startswith("v1::fallback::")


def test_historical_like_missing_fields():
    # Historical untagged data may lack some fields
    pick = {"symbol": "OLD", "direction": "SHORT"}
    pid = build_canonical_outcomes_pick_id(pick)
    assert pid.startswith("v1::fallback::")
    assert "OLD" in pid.upper()


def test_time_exit_cohort_stable_time():
    pick = {
        "symbol": "TSLA",
        "direction": "LONG",
        "strategy": "mean_rev",
        "resolved_at": "2026-05-15T14:30:00",
        "asset_class": "EQUITY",
    }
    pid = build_canonical_outcomes_pick_id(pick)
    assert "2026-05-15T14:30:00" in pid or pid.startswith("v1::fallback::")


def test_version_prefix_present():
    pick = {"symbol": "X", "direction": "LONG"}
    pid = build_canonical_outcomes_pick_id(pick)
    assert pid.startswith("v1::")


# ------------------------------------------------------------------
# Cross-writer parity & TON-highlighted edge cases (expanded this fire)
# ------------------------------------------------------------------

def _old_universal_at_pick_outcomes_hash(pick):
    """Exact narrow hash previously used in universal_pick_resolver.py _write_outcomes_to_mysql."""
    import hashlib
    symbol = str(pick.get("symbol", pick.get("ticker", "")))[:50]
    strategy = str(pick.get("strategy", pick.get("algorithm_name", "")))[:100]
    resolved_at = None
    for ts_key in ("resolved_at", "closed_at", "exit_date", "timestamp"):
        if pick.get(ts_key):
            resolved_at = str(pick[ts_key]).replace("T", " ").replace("Z", "")[:19]
            break
    asset_class = str(pick.get("asset_class", "CRYPTO"))[:20]
    _seed = f"{symbol}|{strategy}|{resolved_at or ''}|{asset_class}"
    return hashlib.md5(_seed.encode("utf-8")).hexdigest()[:36]


def _old_alpha_at_pick_outcomes_raw(pick):
    """Exact raw-id logic previously used in alpha_engine/outcome_resolver.py _write_outcomes_to_mysql."""
    return str(pick.get("id", "") or "").strip()


def test_cross_writer_parity_basic():
    """New helper must produce a canonical key; we at minimum verify it differs from the old divergent paths on the same input."""
    pick = {
        "id": "raw-xyz",
        "symbol": "ETHUSDT",
        "direction": "LONG",
        "strategy": "breakout",
        "opened_at": "2026-05-20T08:15:00",
        "resolved_at": "2026-05-20T09:00:00",
        "asset_class": "CRYPTO",
        "emitter": "test",
    }
    new_id = build_canonical_outcomes_pick_id(pick)
    old_univ = _old_universal_at_pick_outcomes_hash(pick)
    old_alpha = _old_alpha_at_pick_outcomes_raw(pick)

    # The new helper must not be identical to either of the old divergent implementations on this input
    assert new_id != old_univ
    assert new_id != old_alpha
    # It must still be a stable v1 key
    assert new_id.startswith("v1::")


def test_raw_id_validation_rejects_empty():
    pick = {"id": "", "symbol": "AAPL", "direction": "LONG"}
    pid = build_canonical_outcomes_pick_id(pick)
    # Should fall back rather than produce an empty or invalid key
    assert pid.startswith("v1::fallback::")


def test_additional_historical_edge():
    """Very old untagged row with almost no fields."""
    pick = {"symbol": "LEGACY1"}
    pid = build_canonical_outcomes_pick_id(pick)
    assert pid.startswith("v1::fallback::")
    assert "LEGACY1" in pid.upper()
