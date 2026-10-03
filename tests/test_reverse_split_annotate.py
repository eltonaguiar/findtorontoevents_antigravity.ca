"""Regression tests for ``_annotate_reverse_split_pick``.

2026-10-03 incident: the annotation read the registry value as if it were a
single ``(ratio, date)`` pair — ``out["reverse_split_ratio"] = info[0]`` and
``out["reverse_split_date"] = info[1]`` — but ``get_reverse_split_info()``
returns a *list* of ``(ratio, date)`` tuples, newest first.  For every symbol
with exactly one split (LODE/KULR/GSAT/GE) ``info[1]`` raised ``IndexError``,
which propagated out of ``_build_recent_closed_picks`` and crashed the whole
``audit_trail.dashboard_generator`` run.  Because the Unified Audit Dashboard
workflow builds the payload in a single step, that crash skipped the commit +
deploy steps and left findtorontoevents.ca/audit frozen on a stale snapshot
for weeks (last good deploy 2026-08-30).

These tests pin the fixed behaviour so the badge annotation can never take the
dashboard build down again.
"""

from __future__ import annotations

import pytest

from audit_trail.dashboard_generator import _annotate_reverse_split_pick
from audit_trail.reverse_split_symbols import (
    REVERSE_SPLIT_SYMBOLS,
    get_reverse_split_info,
)


def test_registry_values_are_lists_of_ratio_date_tuples():
    """The annotation depends on this contract — guard it explicitly."""
    for symbol, splits in REVERSE_SPLIT_SYMBOLS.items():
        assert isinstance(splits, list) and splits, symbol
        for entry in splits:
            assert isinstance(entry, (list, tuple)) and len(entry) == 2, (
                symbol,
                entry,
            )
            assert isinstance(entry[0], str) and isinstance(entry[1], str)


def test_single_split_symbols_do_not_raise():
    """The exact regression: single-split symbols used to raise IndexError."""
    single_split = ["LODE", "KULR", "GSAT", "GE"]
    for symbol in single_split:
        # Sanity: these really are single-entry registry rows.
        assert len(get_reverse_split_info(symbol)) == 1
        out = _annotate_reverse_split_pick({"symbol": symbol, "entry_price": 1.0})
        assert out["reverse_split_affected"] == 1
        assert out["reverse_split_ratio"] == REVERSE_SPLIT_SYMBOLS[symbol][0][0]
        assert out["reverse_split_date"] == REVERSE_SPLIT_SYMBOLS[symbol][0][1]
        assert isinstance(out["reverse_split_ratio"], str)
        assert isinstance(out["reverse_split_date"], str)


@pytest.mark.parametrize("symbol", sorted(REVERSE_SPLIT_SYMBOLS))
def test_every_registered_symbol_annotates_without_error(symbol):
    out = _annotate_reverse_split_pick({"symbol": symbol, "entry_price": 1.0})
    newest_ratio, newest_date = REVERSE_SPLIT_SYMBOLS[symbol][0]
    assert out["reverse_split_affected"] == 1
    assert out["reverse_split_ratio"] == newest_ratio
    assert out["reverse_split_date"] == newest_date
    assert out["reverse_split_note"]


def test_non_reverse_split_symbol_passes_through_untouched():
    pick = {"symbol": "AAPL", "entry_price": 100.0}
    out = _annotate_reverse_split_pick(pick)
    assert "reverse_split_affected" not in out
    assert out == pick


def test_missing_or_empty_symbol_is_safe():
    for bad in ({}, {"symbol": None}, {"symbol": ""}, {"symbol": "   "}):
        out = _annotate_reverse_split_pick(dict(bad))
        assert "reverse_split_affected" not in out


def test_lowercase_symbol_is_normalized():
    out = _annotate_reverse_split_pick({"symbol": "lode", "entry_price": 1.0})
    assert out["reverse_split_affected"] == 1
    assert out["reverse_split_ratio"] == "1-for-10"
