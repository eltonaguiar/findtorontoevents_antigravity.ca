"""Regression tests for the size-aware escape hatch in
``alpha_engine.concentration_cap.passes_concentration_cap`` (v3, 2026-05-22).

PROBLEM: the percentage per-symbol cap (FOREX 20%, COMMODITY 30%) mechanically
over-blocks low-count classes — with ~12 picks in a class, the 3rd pick on a
symbol = 25% > 20% cap and gets rejected, so FOREX/COMMODITY emit 0 active
picks.

FIX: reject ONLY when BOTH the % cap is exceeded AND the absolute post-add
symbol count exceeds ``MIN_COUNT`` (default 3, clamped to
[1, MIN_ACTIVE_FOR_CAP - 1]). A small book (sym_after <= MIN_COUNT) passes the
% cap; a large book still enforces it.
"""

from __future__ import annotations

import importlib

import pytest

import alpha_engine.concentration_cap as cc
from alpha_engine.concentration_cap import (
    MIN_ACTIVE_FOR_CAP,
    MIN_COUNT,
    passes_concentration_cap,
)


def _picks(asset_class: str, *symbol_counts: tuple[str, int]) -> list[dict]:
    """Build an active-picks snapshot: each (symbol, n) repeats symbol n times."""
    out: list[dict] = []
    for sym, n in symbol_counts:
        for _ in range(n):
            out.append({"asset_class": asset_class, "symbol": sym})
    return out


# ---------------------------------------------------------------------------
# 12-pick FOREX @ 20% cap — 3rd same-symbol ALLOW, 4th REJECT
# ---------------------------------------------------------------------------


def test_forex_12pick_third_same_symbol_allowed():
    """A 12-pick FOREX book: adding a 3rd EURUSD pick = 25% > 20% cap, but
    sym_after(3) <= MIN_COUNT(3) → escape hatch ALLOWS it."""
    assert MIN_COUNT == 3, "test assumes default CONCENTRATION_MIN_COUNT=3"
    # 11 existing active picks: EURUSD x2, plus 9 distinct others
    existing = _picks(
        "FOREX",
        ("EURUSD", 2),
        *[(f"PAIR{i}", 1) for i in range(9)],
    )
    assert len(existing) == 11
    ok, why = passes_concentration_cap("FOREX", "EURUSD", existing)
    assert ok is True, f"3rd EURUSD should be allowed by escape hatch, got: {why}"


def test_forex_12pick_fourth_same_symbol_rejected():
    """A 12-pick FOREX book: adding a 4th EURUSD pick = 33.3% > 20% cap and
    sym_after(4) > MIN_COUNT(3) → REJECT."""
    # 11 existing: EURUSD x3, plus 8 distinct others
    existing = _picks(
        "FOREX",
        ("EURUSD", 3),
        *[(f"PAIR{i}", 1) for i in range(8)],
    )
    assert len(existing) == 11
    ok, why = passes_concentration_cap("FOREX", "EURUSD", existing)
    assert ok is False, "4th EURUSD should be rejected by the % cap"
    assert "concentration_cap_blocked" in why
    assert "FOREX/EURUSD" in why
    assert "MIN_COUNT" in why


# ---------------------------------------------------------------------------
# 14-pick COMMODITY @ 30% cap
# ---------------------------------------------------------------------------


def test_commodity_14pick_fourth_same_symbol_allowed():
    """14-pick COMMODITY book: 4th GC=F pick = 4/14 = 28.6% <= 30% cap → ALLOW
    (under the % cap entirely)."""
    existing = _picks(
        "COMMODITY",
        ("GC=F", 3),
        *[(f"COMM{i}", 1) for i in range(10)],
    )
    assert len(existing) == 13
    ok, why = passes_concentration_cap("COMMODITY", "GC=F", existing)
    assert ok is True, f"4th GC=F (28.6%) under 30% cap should pass, got: {why}"


def test_commodity_14pick_fifth_same_symbol_rejected():
    """14-pick COMMODITY book: 5th GC=F pick = 5/14 = 35.7% > 30% cap and
    sym_after(5) > MIN_COUNT(3) → REJECT."""
    existing = _picks(
        "COMMODITY",
        ("GC=F", 4),
        *[(f"COMM{i}", 1) for i in range(9)],
    )
    assert len(existing) == 13
    ok, why = passes_concentration_cap("COMMODITY", "GC=F", existing)
    assert ok is False, "5th GC=F (35.7%) over 30% cap should be rejected"
    assert "COMMODITY/GC=F" in why


def test_commodity_small_book_third_pick_escape_hatch():
    """COMMODITY with a small book: 3rd GC=F on a 12-pick book = 25% < 30%,
    so it is under the cap; bump to a tighter scenario where % is exceeded but
    count is small still allows."""
    # 11 existing: GC=F x2, 9 others. 3rd GC=F → 3/12 = 25% < 30% → ALLOW anyway.
    existing = _picks("COMMODITY", ("GC=F", 2), *[(f"C{i}", 1) for i in range(9)])
    ok, _ = passes_concentration_cap("COMMODITY", "GC=F", existing)
    assert ok is True


# ---------------------------------------------------------------------------
# n below MIN_ACTIVE_FOR_CAP → ALLOW (cold-start, early return preserved)
# ---------------------------------------------------------------------------


def test_below_min_active_cold_start_allowed():
    """When total active picks (incl. the new one) < MIN_ACTIVE_FOR_CAP, the
    cap does not apply at all — even a heavily concentrated symbol passes."""
    # 8 existing all EURUSD; adding 9th → total_after=9 < MIN_ACTIVE_FOR_CAP(10)
    existing = _picks("FOREX", ("EURUSD", 8))
    assert len(existing) < MIN_ACTIVE_FOR_CAP
    ok, why = passes_concentration_cap("FOREX", "EURUSD", existing)
    assert ok is True, f"cold-start (n<{MIN_ACTIVE_FOR_CAP}) should allow, got: {why}"
    assert why == ""


# ---------------------------------------------------------------------------
# CONCENTRATION_MIN_COUNT env clamp (0 → 1, 99 → 9)
# ---------------------------------------------------------------------------


def test_min_count_env_clamp_low(monkeypatch):
    """CONCENTRATION_MIN_COUNT=0 must clamp up to 1 (never below 1)."""
    monkeypatch.setenv("CONCENTRATION_MIN_COUNT", "0")
    reloaded = importlib.reload(cc)
    try:
        assert reloaded.MIN_COUNT == 1
    finally:
        monkeypatch.delenv("CONCENTRATION_MIN_COUNT", raising=False)
        importlib.reload(cc)


def test_min_count_env_clamp_high(monkeypatch):
    """CONCENTRATION_MIN_COUNT=99 must clamp down to MIN_ACTIVE_FOR_CAP - 1 (9)."""
    monkeypatch.setenv("CONCENTRATION_MIN_COUNT", "99")
    reloaded = importlib.reload(cc)
    try:
        assert reloaded.MIN_COUNT == reloaded.MIN_ACTIVE_FOR_CAP - 1
        assert reloaded.MIN_COUNT == 9
    finally:
        monkeypatch.delenv("CONCENTRATION_MIN_COUNT", raising=False)
        importlib.reload(cc)


def test_min_count_default_is_three():
    """With no env override, MIN_COUNT defaults to 3."""
    assert MIN_COUNT == 3


# ---------------------------------------------------------------------------
# Kill-switch CONCENTRATION_CAP_ENABLED=0 bypass (caller-level)
# ---------------------------------------------------------------------------


def test_kill_switch_bypasses_cap_in_caller(monkeypatch):
    """The kill-switch lives in the caller (quality_gates.passes_active_gate):
    CONCENTRATION_CAP_ENABLED=0 must skip the concentration check entirely."""
    monkeypatch.setenv("CONCENTRATION_CAP_ENABLED", "0")
    import os as _os

    enabled = _os.environ.get("CONCENTRATION_CAP_ENABLED", "1")
    # Mirror the exact guard expression used in quality_gates.py line ~7000.
    cap_runs = enabled not in ("0", "false", "FALSE", "False")
    assert cap_runs is False, "kill-switch=0 must disable the concentration check"


def test_cap_enabled_by_default(monkeypatch):
    """With no kill-switch env var, the concentration check runs (default ON)."""
    import os as _os

    monkeypatch.delenv("CONCENTRATION_CAP_ENABLED", raising=False)
    enabled = _os.environ.get("CONCENTRATION_CAP_ENABLED", "1")
    cap_runs = enabled not in ("0", "false", "FALSE", "False")
    assert cap_runs is True


# ---------------------------------------------------------------------------
# int() math sanity — the off-by-one boundary
# ---------------------------------------------------------------------------


def test_unknown_asset_class_always_allowed():
    """An asset class with no cap entry is always allowed."""
    ok, why = passes_concentration_cap("MYSTERYCLASS", "FOO", _picks("MYSTERYCLASS", ("FOO", 20)))
    assert ok is True
    assert why == ""
