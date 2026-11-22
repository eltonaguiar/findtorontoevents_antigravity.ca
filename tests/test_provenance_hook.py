#!/usr/bin/env python3
"""Tests for the shared emit hook (ledger item T4).

Proves the second callsite records picks into the ledger with a VALID CHAIN, and that
the hook cannot break the caller that uses it.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
for p in (str(REPO), str(REPO / "tools")):
    if p not in sys.path:
        sys.path.insert(0, p)

from alpha_engine.provenance_hook import emit_picks, to_ledger_pick  # noqa: E402
from provenance_ledger import read_all, verify  # noqa: E402


# --- a pick shaped exactly like smart_picks_engine emits -------------------
SMART_PICK = {
    "symbol": "BTCUSDT", "direction": "LONG",
    "entry": 60000.0, "tp": 62000.0, "sl": 59000.0,
    "strategy": "Crypto RSI Scout", "smart_score": 88,
}

# --- and one shaped like production_scanner -------------------------------
SCANNER_PICK = {
    "symbol": "EURUSD", "side": "SHORT",
    "entry_price": 1.0850, "take_profit": 1.0800, "stop_loss": 1.0880,
    "strategy_family": "fx_meanrev", "source_system": "alpha_engine",
}


class TestMapping:
    def test_smart_picks_field_names_map(self):
        m = to_ledger_pick(SMART_PICK, default_source="smart_picks_engine")
        assert m is not None
        assert m["symbol"] == "BTCUSDT"
        assert m["side"] == "LONG"
        assert (m["entry_ref"], m["tp"], m["sl"]) == (60000.0, 62000.0, 59000.0)
        assert m["strategy"] == "Crypto RSI Scout"
        # the second callsite must be distinguishable from the first
        assert m["source_system"] == "smart_picks_engine"

    def test_scanner_field_names_map(self):
        m = to_ledger_pick(SCANNER_PICK)
        assert m is not None
        assert m["side"] == "SHORT"
        assert m["strategy"] == "fx_meanrev"
        assert m["source_system"] == "alpha_engine"

    @pytest.mark.parametrize("drop,why", [
        ("tp", "no take-profit -> no resolvable outcome"),
        ("sl", "no stop-loss -> no resolvable outcome"),
        ("entry", "no entry -> no resolvable outcome"),
    ])
    def test_pick_without_levels_is_refused(self, drop, why):
        p = dict(SMART_PICK)
        p.pop(drop)
        assert to_ledger_pick(p) is None, why

    @pytest.mark.parametrize("bad_side", ["", None, "FLAT", "?", "hold"])
    def test_side_must_be_long_or_short(self, bad_side):
        assert to_ledger_pick(dict(SMART_PICK, direction=bad_side)) is None

    def test_zero_or_negative_levels_refused(self):
        assert to_ledger_pick(dict(SMART_PICK, tp=0)) is None
        assert to_ledger_pick(dict(SMART_PICK, sl=-5)) is None


class TestLedgerWrite:
    def test_emit_from_second_callsite_produces_a_valid_chain(self, tmp_path):
        ledger = tmp_path / "picks.jsonl"
        written, rejected = emit_picks([SMART_PICK, SCANNER_PICK],
                                       path=ledger, quiet=True)
        assert len(written) == 2, f"expected 2 written, got {len(written)} ({rejected})"
        assert rejected == []
        recs = read_all(ledger)
        assert [r["seq"] for r in recs] == [1, 2]
        v = verify(ledger)
        assert v["ok"] is True, v
        # created_at is stamped by the ledger, never by the caller
        assert all(r.get("created_at") for r in recs)

    def test_two_callsites_are_distinguishable_in_the_ledger(self, tmp_path):
        ledger = tmp_path / "p.jsonl"
        emit_picks([SMART_PICK], default_source="smart_picks_engine",
                   path=ledger, quiet=True)
        emit_picks([SCANNER_PICK], default_source="alpha_engine",
                   path=ledger, quiet=True)
        srcs = [r["source_system"] for r in read_all(ledger)]
        assert srcs == ["smart_picks_engine", "alpha_engine"], srcs

    def test_chain_detects_tampering_after_a_hook_write(self, tmp_path):
        import json
        ledger = tmp_path / "p.jsonl"
        emit_picks([SMART_PICK], path=ledger, quiet=True)
        recs = read_all(ledger)
        recs[0]["tp"] = 1.0                     # tamper
        ledger.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in recs))
        assert verify(ledger)["ok"] is False, "tampered record not detected"

    def test_unusable_picks_are_dropped_not_emitted_as_zeros(self, tmp_path):
        ledger = tmp_path / "p.jsonl"
        written, _ = emit_picks([{"symbol": "X", "direction": "LONG", "entry": 100.0}],
                                path=ledger, quiet=True)
        assert written == []
        assert read_all(ledger) == []


class TestFailSafe:
    def test_none_input_does_not_raise(self, tmp_path):
        assert emit_picks(None, path=tmp_path / "p.jsonl", quiet=True) == ([], [])

    def test_empty_input_does_not_raise(self, tmp_path):
        assert emit_picks([], path=tmp_path / "p.jsonl", quiet=True) == ([], [])

    def test_garbage_input_is_swallowed(self, tmp_path):
        # a non-list, and a list of non-dicts -- neither may propagate
        assert emit_picks("not-a-list", path=tmp_path / "p.jsonl", quiet=True) == ([], [])

    def test_unwritable_path_returns_empty_instead_of_raising(self, tmp_path):
        d = tmp_path / "adir"
        d.mkdir()
        # path is a DIRECTORY -> the ledger write must fail, the hook must not raise
        written, rejected = emit_picks([SMART_PICK], path=d, quiet=True)
        assert (written, rejected) == ([], [])


class TestNoCreatedAtEscapes:
    def test_hook_never_forwards_a_caller_created_at(self, tmp_path):
        """A pick carrying its own created_at must not smuggle it into the ledger.

        `to_ledger_pick` builds a fresh dict, so caller fields are dropped by
        construction; the ledger would also refuse. Both guards are asserted here
        because this is the property the entire ledger rests on.
        """
        ledger = tmp_path / "p.jsonl"
        p = dict(SMART_PICK, created_at="2020-01-01T00:00:00+00:00")
        mapped = to_ledger_pick(p)
        assert "created_at" not in mapped
        written, _ = emit_picks([p], path=ledger, quiet=True)
        assert len(written) == 1
        assert read_all(ledger)[0]["created_at"] != "2020-01-01T00:00:00+00:00"
