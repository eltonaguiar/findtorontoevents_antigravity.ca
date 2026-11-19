"""audit3's PROVEN_T2 must need forward evidence, not just re-scored history."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alpha_engine.audit3_tribunal import build_report, forward_gate_block  # noqa: E402

MANIFEST = {"path": "m.json", "available": True,
            "pods": [{"id": "POD-A", "status": "pre_registered",
                      "hypothesis_id": "H-TEST-1", "registered_at": "2026-11-20",
                      "strategies": ["cellA"], "asset_classes": ["CRYPTO"],
                      "directions": ["LONG"]}]}


def _rows(n=150):
    symbols = ("AAAUSDT", "BBBUSDT", "CCCUSDT", "DDDUSDT")
    sources = ("src_a", "src_b")
    rows = []
    for i in range(n):
        win = i % 3 != 0
        rows.append({
            "id": f"r{i}", "asset_class": "CRYPTO", "strategy": "cellA",
            "symbol": symbols[i % 4], "direction": "LONG",
            "source_system": sources[i % 2],
            "pnl_pct": 3.0 if win else -0.6,
            "status": "WON" if win else "LOST",
            "closed_at": f"2026-01-{(i % 28) + 1:02d}T00:00:00Z",
        })
    return rows


def _fwd_row(i: int, hid="H-TEST-1", closed="2026-12-01T00:00:00+00:00"):
    """Ledger-shaped row. +3% / -1% keeps dispersion non-zero so IR is defined."""
    return {
        "id": f"fwd_{hid}_{i}", "hypothesis_id": hid,
        "opened_at": "2026-11-25T00:00:00+00:00", "closed_at": closed,
        "symbol": f"S{i % 5}USDT", "asset_class": "CRYPTO", "side": "LONG",
        "entry_px": 1.0, "exit_px": 1.03 if i % 4 else 0.99, "qty": 1.0,
        "fees": 0.0, "funding": 0.0, "slippage_bps": 16.0,
        "resolver_version": "test.v1", "intrabar_first_touch": True,
        "benchmark_leg_ret": 0.001, "regime_ok": True,
        "created_at": "2026-12-01T00:00:00+00:00",
    }


# ─────────────────────────────────────────────────────── the gate itself ──
def test_pod_with_no_forward_rows_cannot_hold_proven():
    forward = {"enforced": True, "pods": {"POD-A": {
        "eligible": False, "n_forward": 0, "min_n": 100,
        "reasons": ["no forward rows — nothing can promote"]}}}
    rep = build_report(_rows(), "x.json", None, confirmatory=MANIFEST, forward=forward)
    cell = rep["cells"][0]
    assert cell["namespace"] == "confirmatory"
    assert cell["verdict"] == "CANDIDATE"
    assert any("forward gate" in r for r in cell["reasons"])
    assert cell["forward_gate"]["eligible"] is False
    assert cell["forward_gate"]["n_forward"] == 0
    assert rep["summary"]["n_proven"] == 0
    assert rep["forward_gate"]["enforced"] is True


def test_pod_with_forward_rows_that_clear_the_rule_stays_proven():
    forward = {"enforced": True, "pods": {"POD-A": {
        "eligible": True, "n_forward": 100, "min_n": 100,
        "pf_ci_lb": 1.4, "ir": 0.9, "reasons": [],
        "hypothesis_id": "H-TEST-1", "since": "2026-11-20"}}}
    rep = build_report(_rows(), "x.json", None, confirmatory=MANIFEST, forward=forward)
    cell = rep["cells"][0]
    assert cell["verdict"] == "PROVEN_T2"
    assert cell["forward_gate"]["pf_ci_lb"] == 1.4
    assert rep["summary"]["n_proven"] == 1


def test_library_callers_without_a_forward_block_are_unchanged():
    # Explicitly pinned: the gate is a data-driven demotion, so a caller that never
    # supplies forward evidence (unit tests, notebooks) keeps the pre-gate verdict.
    rep = build_report(_rows(), "x.json", None, confirmatory=MANIFEST)
    assert rep["cells"][0]["verdict"] == "PROVEN_T2"
    assert rep["forward_gate"]["enforced"] is False
    assert "no forward ledger supplied" in rep["forward_gate"]["why"]


def test_non_proven_cells_are_not_touched_by_the_gate():
    rows = []
    for i in range(120):
        rows.append({"id": f"k{i}", "asset_class": "CRYPTO", "strategy": "bleeder",
                     "symbol": f"B{i % 6}USDT", "direction": "LONG",
                     "source_system": f"s{i % 3}", "pnl_pct": -1.0,
                     "closed_at": f"2026-01-{(i % 28) + 1:02d}T00:00:00Z"})
    forward = {"enforced": True, "pods": {"POD-A": {"eligible": False, "n_forward": 0}}}
    rep = build_report(rows, "x.json", None, confirmatory=MANIFEST, forward=forward)
    cell = rep["cells"][0]
    assert cell["verdict"] != "PROVEN_T2"
    assert "forward_gate" not in cell


# ─────────────────────────────────────────────────── gate data construction ──
def _write_ledger(tmp_path, rows):
    p = tmp_path / "forward_observations.jsonl"
    p.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return str(p)


def test_gate_counts_only_rows_closed_after_the_pod_registered(tmp_path):
    rows = [_fwd_row(i, closed="2026-11-01T00:00:00+00:00") for i in range(120)]
    rows += [_fwd_row(i, closed="2026-12-01T00:00:00+00:00") for i in range(3)]
    block = forward_gate_block(MANIFEST, _write_ledger(tmp_path, rows))
    pod = block["pods"]["POD-A"]
    assert pod["n_forward"] == 3          # the 120 pre-registration rows are history
    assert pod["eligible"] is False
    assert pod["since"] == "2026-11-20"


def test_gate_ignores_other_hypotheses(tmp_path):
    rows = [_fwd_row(i, hid="H-OTHER") for i in range(120)]
    block = forward_gate_block(MANIFEST, _write_ledger(tmp_path, rows))
    assert block["pods"]["POD-A"]["n_forward"] == 0
    assert block["hypotheses"]["H-OTHER"]["n_forward"] == 120


def test_gate_promotes_only_when_the_pod_own_rows_clear_the_rule(tmp_path):
    rows = [_fwd_row(i) for i in range(120)]
    block = forward_gate_block(MANIFEST, _write_ledger(tmp_path, rows))
    assert block["pods"]["POD-A"]["eligible"] is True, block["pods"]["POD-A"]["reasons"]


def test_missing_ledger_is_zero_rows_not_an_error(tmp_path):
    block = forward_gate_block(MANIFEST, str(tmp_path / "nope.jsonl"))
    assert block["n_rows"] == 0
    assert block["fingerprint"] == "absent"
    assert block["pods"]["POD-A"]["eligible"] is False


def test_post_hoc_pods_get_no_gate_entry(tmp_path):
    manifest = {"pods": [{"id": "POD-PH", "status": "post_hoc",
                          "hypothesis_id": "H-TEST-1", "registered_at": "2026-11-20"}]}
    block = forward_gate_block(manifest, _write_ledger(tmp_path, [_fwd_row(0)]))
    assert block["pods"] == {}


# ───────────────────────────────────── observe pods: visible but inert ──
def test_observe_pod_is_shown_but_cannot_promote(tmp_path):
    ledger = tmp_path / "fwd.jsonl"
    ledger.write_text("\n".join(json.dumps(_fwd_row(i)) for i in range(120)) + "\n",
                      encoding="utf-8")
    blk = forward_gate_block({"available": True, "pods": [
        {"id": "POD-OBS", "status": "observe", "hypothesis_id": "H-TEST-1",
         "registered_at": "2026-11-20"}]}, ledger=str(ledger))
    pod = blk["pods"]["POD-OBS"]
    assert pod["status"] == "observe"
    assert pod["eligible"] is False
    assert pod["n_forward"] >= 100
    assert any("observe" in r for r in pod["reasons"])


def test_declined_pods_stay_hidden(tmp_path):
    ledger = tmp_path / "fwd.jsonl"
    ledger.write_text("", encoding="utf-8")
    blk = forward_gate_block({"available": True, "pods": [
        {"id": "POD-X", "status": "declined", "hypothesis_id": "H-TEST-1"}]},
        ledger=str(ledger))
    assert "POD-X" not in blk["pods"]
