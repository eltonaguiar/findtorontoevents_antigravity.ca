#!/usr/bin/env python3
"""Tests for tools/etf_trend_price_refresh.py.

The behaviour that matters is the negative one: a refresh must never rewrite a bar
that is already in the cache, because the hash-chained ledger already committed to
signals computed from those bars.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "etf_refresh", ROOT / "tools" / "etf_trend_price_refresh.py")
refresh = importlib.util.module_from_spec(_spec)
sys.modules["etf_refresh"] = refresh
_spec.loader.exec_module(refresh)


def _rows(dates, close=100.0):
    return [[d, f"{close:.6f}", f"{close:.6f}", f"{close:.6f}", f"{close:.6f}", "1000"]
            for d in dates]


@pytest.fixture
def cache(tmp_path, monkeypatch):
    monkeypatch.setattr(refresh, "CACHE", tmp_path)
    return tmp_path


def test_new_rows_only_drops_revisions_and_duplicates():
    fresh = _rows(["2026-01-02", "2026-01-05", "2026-01-05", "2026-01-06"])
    got = refresh.new_rows_only(fresh, last="2026-01-05")
    assert [r[0] for r in got] == ["2026-01-06"], "an already-cached date must never be re-sent"


def test_new_rows_only_keeps_everything_when_cache_is_empty():
    fresh = _rows(["2026-01-06", "2026-01-02"])
    got = refresh.new_rows_only(fresh, last=None)
    assert [r[0] for r in got] == ["2026-01-02", "2026-01-06"], "rows must be written oldest first"


def test_refresh_appends_without_touching_existing_rows(cache):
    p = cache / "SPY_5y.csv"
    p.write_text(",".join(refresh.HEADER) + "\n" +
                 "\n".join(",".join(r) for r in _rows(["2026-01-05"], close=999.0)) + "\n")
    before = p.read_text()

    n = refresh.refresh("SPY", downloader=lambda s: _rows(["2026-01-05", "2026-01-06"], close=1.0))
    assert n == 1
    after = p.read_text()
    assert after.startswith(before), "existing bytes must be preserved exactly"
    assert after.rstrip().endswith("2026-01-06,1.000000,1.000000,1.000000,1.000000,1000")


def test_refresh_is_idempotent(cache):
    first = refresh.refresh("SPY", downloader=lambda s: _rows(["2026-01-05", "2026-01-06"]))
    assert first == 2
    batch = (cache / "SPY_5y.csv").read_text()
    second = refresh.refresh("SPY", downloader=lambda s: _rows(["2026-01-05", "2026-01-06"]))
    assert second == 0
    assert (cache / "SPY_5y.csv").read_text() == batch


def test_dry_run_writes_nothing(cache):
    n = refresh.refresh("SPY", dry_run=True, downloader=lambda s: _rows(["2026-01-05"]))
    assert n == 1
    assert not (cache / "SPY_5y.csv").exists()


def test_stale_download_cannot_roll_the_cache_back(cache):
    refresh.refresh("SPY", downloader=lambda s: _rows(["2026-01-09"]))
    n = refresh.refresh("SPY", downloader=lambda s: _rows(["2026-01-08"]))
    assert n == 0, "a download older than the cache must append nothing"
    assert refresh.last_cached_date("SPY") == "2026-01-09"


def test_download_failure_propagates_rather_than_appending_partial_data(cache):
    def boom(_sym):
        raise RuntimeError("yfinance returned no rows for SPY")
    with pytest.raises(RuntimeError):
        refresh.refresh("SPY", downloader=boom)


def test_universe_is_taken_from_the_clock_not_duplicated():
    from importlib import import_module
    clock = import_module("etf_trend_forward_clock")
    assert refresh.clock.UNIVERSE == clock.UNIVERSE
    assert len(refresh.clock.UNIVERSE) == 20
