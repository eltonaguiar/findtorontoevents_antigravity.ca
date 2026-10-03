"""Tests for the per-asset-class visibility floor (2026-10-03).

Background: the admission gate stack in ``audit_trail.quality_gates`` can zero
out an entire asset class. On 2026-10-03 CRYPTO/FOREX/COMMODITY/FUTURES each
published 0 active picks while EQUITY/ETF/BOND published fine. The floor
surfaces the top-scoring candidates of any under-covered class WITHOUT relaxing
any gate (they are tagged ``_below_gate`` / ``_gate_passed=False``).
"""

from __future__ import annotations

import importlib

from audit_trail.dashboard_generator import (
    _PER_CLASS_FLOOR_CLASSES,
    _apply_per_class_visibility_floor,
)


def _pick(symbol: str, asset_class: str, score: float) -> dict:
    return {"symbol": symbol, "asset_class": asset_class, "score": score}


def test_covers_every_class_when_none_published():
    candidates = [
        _pick("BTCUSDT", "CRYPTO", 80),
        _pick("BTCUSDT", "CRYPTO", 60),
        _pick("EURUSD=X", "FOREX", 55),
        _pick("GC=F", "COMMODITY", 50),
        _pick("ES=F", "FUTURES", 45),
    ]
    out = _apply_per_class_visibility_floor([], candidates)
    counts = {}
    for p in out:
        counts[p["asset_class"]] = counts.get(p["asset_class"], 0) + 1
    # Every covered class that HAS candidates gets the floor count (default 2).
    assert counts.get("CRYPTO") == 2
    assert counts.get("FOREX") == 1  # only one candidate available
    assert counts.get("COMMODITY") == 1
    assert counts.get("FUTURES") == 1
    # No candidates for EQUITY/ETF/BOND -> nothing invented.
    assert counts.get("EQUITY", 0) == 0


def test_does_not_reduce_or_duplicate_existing_picks():
    published = [_pick("AAPL", "EQUITY", 70), _pick("MSFT", "EQUITY", 65)]
    candidates = [_pick("AAPL", "EQUITY", 70), _pick("BTCUSDT", "CRYPTO", 80)]
    out = _apply_per_class_visibility_floor(published, candidates)
    # Existing published picks retained unchanged.
    assert published[0] in out and published[1] in out
    # AAPL is not re-added (identity already seen).
    assert sum(1 for p in out if p.get("symbol") == "AAPL") == 1


def test_floored_picks_are_tagged_below_gate():
    candidates = [_pick("BTCUSDT", "CRYPTO", 80)]
    out = _apply_per_class_visibility_floor([], candidates)
    added = [p for p in out if p.get("_visibility_floor") == "per_class"]
    assert len(added) == 1
    p = added[0]
    assert p["_below_gate"] is True
    assert p["_gate_passed"] is False


def test_ranks_by_score_descending():
    candidates = [
        _pick("A", "CRYPTO", 10),
        _pick("B", "CRYPTO", 90),
        _pick("C", "CRYPTO", 50),
    ]
    out = _apply_per_class_visibility_floor([], candidates)
    syms = [p["symbol"] for p in out if p["asset_class"] == "CRYPTO"]
    assert syms == ["B", "C"]  # top-2 by score, not insertion order


def test_satisfied_class_is_untouched():
    published = [_pick("A", "CRYPTO", 1), _pick("B", "CRYPTO", 2)]
    out = _apply_per_class_visibility_floor(published, [_pick("C", "CRYPTO", 99)])
    assert len(out) == 2
    assert all(p.get("_visibility_floor") is None for p in out)


def test_kill_switch_disables_floor(monkeypatch):
    monkeypatch.setenv("PER_CLASS_ACTIVE_FLOOR", "0")
    out = _apply_per_class_visibility_floor([], [_pick("BTCUSDT", "CRYPTO", 80)])
    assert out == []


def test_floor_n_env_override(monkeypatch):
    monkeypatch.setenv("PER_CLASS_ACTIVE_FLOOR_N", "3")
    candidates = [_pick(s, "CRYPTO", 10 * i) for i, s in enumerate(["A", "B", "C", "D"])]
    out = _apply_per_class_visibility_floor([], candidates)
    assert sum(1 for p in out if p["asset_class"] == "CRYPTO") == 3


def test_covered_classes_constant():
    for ac in ("CRYPTO", "EQUITY", "ETF", "FOREX", "COMMODITY", "FUTURES", "BOND"):
        assert ac in _PER_CLASS_FLOOR_CLASSES


def test_handles_none_and_garbage_inputs():
    assert _apply_per_class_visibility_floor(None, None) == []
    out = _apply_per_class_visibility_floor([], [None, 5, {"symbol": "X"}])
    assert out == []
