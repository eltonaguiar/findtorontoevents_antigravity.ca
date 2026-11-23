#!/usr/bin/env python3
"""Tests for tools/etf_trend_forward_clock.py (row R4b).

The behaviours that matter most are negative ones:
  * it must REFUSE to backfill a date before CLOCK_START
  * it must never use data after the as-of date (no look-ahead)
  * the on-disk record must carry its own sha256, or the chain is unverifiable
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "etf_trend_clock", ROOT / "tools" / "etf_trend_forward_clock.py")
clock = importlib.util.module_from_spec(_spec)
sys.modules["etf_trend_clock"] = clock
_spec.loader.exec_module(clock)

N = clock.LOOKBACK_DAYS + 1          # 253 entries: base at [0], latest at [-1]


def _long_series(base: float = 100.0, final: float = 110.0, n: int = N):
    """n sequential daily closes; flat at `base`, final bar at `final`."""
    d0 = date(2025, 1, 1)
    return [((d0 + timedelta(days=i)).isoformat(),
             base if i < n - 1 else final) for i in range(n)]


def _asof(ser) -> str:
    return ser[-1][0]


def _mock(monkeypatch, tmp_path, base: float = 100.0, final: float = 110.0):
    led = tmp_path / "positions.jsonl"
    monkeypatch.setattr(clock, "LEDGER", led)
    ser = _long_series(base=base, final=final)
    monkeypatch.setattr(clock, "load_closes", lambda s: ser)
    return led, _asof(ser)


# --------------------------------------------------------------- signal
def test_no_lookahead_signal_ignores_future_bars():
    ser = _long_series()
    asof = _asof(ser)
    clean = clock.signal_asof(ser, asof)
    spiked = clock.signal_asof(ser + [(date(2099, 1, 1).isoformat(), 99_999.0)], asof)
    assert clean == pytest.approx(spiked), "a future bar must not change the signal"
    assert clean == pytest.approx(0.10, abs=0.01)


def test_signal_none_when_insufficient_history():
    assert clock.signal_asof([("2026-01-02", 100.0)], "2026-01-02") is None


def test_signal_sign_and_magnitude():
    ser = _long_series(base=100.0, final=120.0)
    assert clock.signal_asof(ser, _asof(ser)) == pytest.approx(0.20, abs=0.01)


# --------------------------------------------------------- no-backfill
def test_refuses_to_backfill_before_clock_start(tmp_path, monkeypatch):
    led, asof = _mock(monkeypatch, tmp_path)
    assert asof < clock.CLOCK_START, "fixture should predate the clock"
    monkeypatch.setattr(sys, "argv", ["x", "--asof", asof])
    assert clock.main() == 3, "must refuse a pre-clock-start date"
    assert not led.exists()


def test_allow_past_requires_a_reason_and_records_it(tmp_path, monkeypatch):
    led, asof = _mock(monkeypatch, tmp_path)
    monkeypatch.setattr(sys, "argv", ["x", "--asof", asof, "--allow-past",
                                      "--reason", "unit test"])
    assert clock.main() == 0
    rec = json.loads(led.read_text().splitlines()[0])
    assert rec["backfill_reason"] == "unit test"


def test_duplicate_rebalance_date_is_refused(tmp_path, monkeypatch):
    led, asof = _mock(monkeypatch, tmp_path)
    argv = ["x", "--asof", asof, "--allow-past", "--reason", "t"]
    monkeypatch.setattr(sys, "argv", argv)
    assert clock.main() == 0
    first = led.read_text()
    monkeypatch.setattr(sys, "argv", list(argv))
    assert clock.main() == 0
    assert led.read_text() == first, "duplicate must not append or revise"


# ------------------------------------------------------------- chain
def test_record_on_disk_carries_its_own_sha256(tmp_path, monkeypatch):
    """Regression: writing canonical() stripped the hash and broke verification."""
    led, asof = _mock(monkeypatch, tmp_path)
    monkeypatch.setattr(sys, "argv", ["x", "--asof", asof, "--allow-past",
                                      "--reason", "t"])
    assert clock.main() == 0
    rec = json.loads(led.read_text().splitlines()[0])
    assert "sha256" in rec and len(rec["sha256"]) == 64


def test_chain_links_and_verifies(tmp_path, monkeypatch):
    led = tmp_path / "positions.jsonl"
    monkeypatch.setattr(clock, "LEDGER", led)
    ser = _long_series()
    monkeypatch.setattr(clock, "load_closes", lambda s: ser)
    monkeypatch.setattr(sys, "argv", ["x", "--asof", _asof(ser), "--allow-past",
                                      "--reason", "t"])
    assert clock.main() == 0
    recs = [json.loads(l) for l in led.read_text().splitlines() if l.strip()]
    assert len(recs) == 1
    assert recs[0]["prev_sha256"] == clock.GENESIS
    assert clock.stats() == 0


# ------------------------------------------------------------- selection
def test_topk_requires_positive_momentum():
    rec = clock.build_record("2026-01-02", clock.GENESIS, None)
    assert len(rec["held"]) <= clock.TOP_K
    for h in rec["held"]:
        assert rec["signals"][h] > 0


def test_frozen_parameters():
    assert len(clock.UNIVERSE) == 20
    assert clock.TOP_K == 5
    assert clock.LOOKBACK_DAYS == 252
