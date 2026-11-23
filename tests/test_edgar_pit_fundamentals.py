#!/usr/bin/env python3
"""Tests for tools/edgar_pit_fundamentals.py (register item PIT-2a).

The two things that must never break:
  * as_of() must never return a fact filed AFTER the as-of date (look-ahead)
  * a restated period must resolve to its EARLIEST filed value, not the latest
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "edgar_pit", ROOT / "tools" / "edgar_pit_fundamentals.py")
pit = importlib.util.module_from_spec(_spec)
sys.modules["edgar_pit"] = pit
_spec.loader.exec_module(pit)


def _cf(periods):
    """Build a minimal companyfacts payload: [(end, filed, val), ...]."""
    return {"facts": {"us-gaap": {"StockholdersEquity": {"units": {"USD": [
        {"end": e, "filed": f, "val": v, "form": "10-K"} for e, f, v in periods
    ]}}}}}


# ---------------------------------------------------------------- earliest
def test_restatement_resolves_to_earliest_filed_value():
    """Same period_end filed twice: the FIRST public value must win."""
    cf = _cf([
        ("2024-12-31", "2025-02-10", 100.0),   # original
        ("2024-12-31", "2025-08-01", 90.0),    # restated later
    ])
    h = pit.pit_history(cf)
    assert len(h) == 1
    assert h[0]["value"] == 100.0, "must use the first-filed value, not the restatement"
    assert h[0]["filed"] == "2025-02-10"


def test_lag_is_filed_minus_period_end():
    h = pit.pit_history(_cf([("2025-09-30", "2025-11-07", 1.0)]))
    assert h[0]["lag_days"] == 38


# ---------------------------------------------------------------- artefacts
def test_xbrl_adoption_lag_is_flagged_not_used():
    """A 2007 period first filed in 2010 is an artefact, not a late filing."""
    h = pit.pit_history(_cf([("2007-06-30", "2010-08-30", 5.0)]))
    assert h[0]["lag_days"] == 1157
    assert h[0]["usable_for_pit"] is False


def test_normal_lag_is_usable():
    h = pit.pit_history(_cf([("2025-09-30", "2025-11-07", 1.0)]))
    assert h[0]["usable_for_pit"] is True


# ---------------------------------------------------------------- look-ahead
def test_as_of_never_returns_a_future_filed_fact(tmp_path, monkeypatch):
    monkeypatch.setattr(pit, "STORE", tmp_path)
    hist = pit.pit_history(_cf([
        ("2024-12-31", "2025-02-10", 100.0),
        ("2025-12-31", "2026-02-10", 200.0),
    ]))
    (tmp_path / "TEST.json").write_text(json.dumps({"ticker": "TEST", "history": hist}))
    # one day before the second filing -> must return the FIRST period only
    r = pit.as_of("TEST", "2026-02-09")
    assert r is not None and r["value"] == 100.0
    # on/after the filing date -> second period becomes visible
    r2 = pit.as_of("TEST", "2026-02-10")
    assert r2 is not None and r2["value"] == 200.0


def test_as_of_returns_none_before_any_filing(tmp_path, monkeypatch):
    monkeypatch.setattr(pit, "STORE", tmp_path)
    hist = pit.pit_history(_cf([("2025-12-31", "2026-02-10", 200.0)]))
    (tmp_path / "TEST.json").write_text(json.dumps({"ticker": "TEST", "history": hist}))
    assert pit.as_of("TEST", "2025-01-01") is None


def test_as_of_skips_artefacts(tmp_path, monkeypatch):
    """An artefact must not become visible even when its filed date has passed."""
    monkeypatch.setattr(pit, "STORE", tmp_path)
    hist = pit.pit_history(_cf([("2007-06-30", "2010-08-30", 5.0)]))
    (tmp_path / "TEST.json").write_text(json.dumps({"ticker": "TEST", "history": hist}))
    assert pit.as_of("TEST", "2011-01-01") is None


def test_as_of_unknown_ticker_is_none(tmp_path, monkeypatch):
    monkeypatch.setattr(pit, "STORE", tmp_path)
    assert pit.as_of("NOPE", "2026-01-01") is None
