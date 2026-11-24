"""Tests for tools.per_class_cost_gate — the 3x round-trip cost rule."""
import json

import pytest

from tools import per_class_cost_gate as g


COSTS = {"CRYPTO": 0.30, "EQUITY": 0.10, "ETF": 0.10, "FOREX": 0.08, "BOND": 0.05}


def _rows(cls, pnls):
    return [{"asset_class": cls, "pnl_pct": p} for p in pnls]


# --- index construction ----------------------------------------------------
def test_class_clears_3x_cost_is_allowed():
    # EQUITY cost 0.10 -> required 0.30; mean 0.35 passes
    idx = g.build_index(_rows("EQUITY", [0.35] * 40), COSTS)
    r = idx["classes"]["EQUITY"]
    assert r["allowed"] is True
    assert r["reason"] == "passes_3x_cost"
    assert r["required_mean_pnl_pct"] == pytest.approx(0.30)
    assert r["cost_multiple"] == pytest.approx(3.5)


def test_class_below_3x_cost_is_blocked():
    # ETF cost 0.10 -> required 0.30; mean 0.04 is far below
    idx = g.build_index(_rows("ETF", [0.04] * 50), COSTS)
    r = idx["classes"]["ETF"]
    assert r["allowed"] is False
    assert r["reason"] == "below_3x_cost"
    assert r["after_cost_net_per_trade"] == pytest.approx(-0.06)


def test_thin_sample_is_blocked_but_labelled():
    idx = g.build_index(_rows("CRYPTO", [5.0] * 5), COSTS)
    r = idx["classes"]["CRYPTO"]
    assert r["allowed"] is False
    assert r["reason"] == "insufficient_sample"
    assert r["sample_sufficient"] is False


def test_unmeasured_rows_do_not_move_the_mean():
    rows = _rows("EQUITY", [0.40] * 40) + [{"asset_class": "EQUITY", "pnl_pct": None}]
    idx = g.build_index(rows, COSTS)
    assert idx["classes"]["EQUITY"]["n"] == 40
    assert idx["classes"]["EQUITY"]["mean_pnl_pct"] == pytest.approx(0.40)


def test_unknown_class_falls_back_to_default_cost():
    idx = g.build_index(_rows("MYSTERY", [0.9] * 40), COSTS)
    assert idx["classes"]["MYSTERY"]["cost_pct"] == pytest.approx(0.20)


def test_index_records_the_rule_it_was_built_with():
    idx = g.build_index(_rows("EQUITY", [1.0] * 40), COSTS)
    assert idx["required_cost_multiple"] == 3.0
    assert "3.0x" in idx["rule"]


# --- gate decisions --------------------------------------------------------
# The gate's contract changed 2026-11-19 (external review v2/v3): it used to fail
# OPEN, so a missing index or an unmeasured class emitted freely — which makes the
# gate's absence undetectable. Strict is now the default and these tests pin the
# new contract plus the explicit escape hatch.
def test_gate_blocks_unknown_class_by_default():
    idx = g.build_index(_rows("EQUITY", [0.40] * 40), COSTS)
    v = g.gate_pick({"asset_class": "MYSTERY"}, idx)
    assert v["allowed"] is False
    assert v["reason"] == "no_class_evidence_strict"
    assert v["strict"] is True


def test_gate_blocks_when_index_missing():
    v = g.gate_pick({"asset_class": "CRYPTO"}, {})
    assert v["allowed"] is False
    assert v["reason"] == "gate_index_missing_strict"


def test_strict_escape_hatch_restores_fail_open(monkeypatch):
    monkeypatch.setenv("PER_CLASS_COST_GATE_STRICT", "0")
    v = g.gate_pick({"asset_class": "MYSTERY"}, {"classes": {"EQUITY": {}}})
    assert v["allowed"] is True
    assert v["reason"] == "no_class_evidence"
    assert v["strict"] is False
    assert g.gate_pick({"asset_class": "CRYPTO"}, {})["allowed"] is True


def test_gate_blocks_when_class_blocked():
    idx = g.build_index(_rows("FOREX", [-0.15] * 40), COSTS)
    v = g.gate_pick({"asset_class": "FOREX"}, idx)
    assert v["allowed"] is False
    assert v["reason"] == "below_3x_cost"


def test_gate_allows_when_class_passes():
    idx = g.build_index(_rows("EQUITY", [0.40] * 40), COSTS)
    assert g.gate_pick({"asset_class": "EQUITY"}, idx)["allowed"] is True


# --- stamping --------------------------------------------------------------
def test_stamp_populates_after_cost_fields():
    idx = g.build_index(_rows("EQUITY", [0.40] * 40), COSTS)
    pick = {"asset_class": "EQUITY", "symbol": "SPY"}
    assert g.stamp_class_after_cost(pick, idx) is True
    assert pick["after_cost_net_per_trade"] == pytest.approx(0.30)
    assert pick["is_ac_survivor"] is True
    assert pick["class_cost_gate_reason"] == "passes_3x_cost"


def test_stamp_returns_false_for_unknown_class():
    pick = {"asset_class": "MYSTERY"}
    assert g.stamp_class_after_cost(pick, {"classes": {}}) is False
    assert "after_cost_net_per_trade" not in pick


# --- on-disk index round trip ---------------------------------------------
def test_load_index_missing_file_fails_open(tmp_path):
    assert g.load_index(str(tmp_path / "nope.json")) == {}


def test_load_index_stale_file_returns_empty_so_the_gate_blocks(tmp_path):
    """A stale index loads as {} — which now means BLOCK, not permission.

    The file layer still refuses to hand back numbers it does not trust; the
    decision moved to `gate_pick`, where an empty index is treated as "the gate
    never ran" rather than "no evidence against the pick".
    """
    p = tmp_path / "idx.json"
    p.write_text(json.dumps({
        "generated_at": "2020-01-01T00:00:00Z",
        "classes": {"CRYPTO": {"allowed": False}},
    }), encoding="utf-8")
    assert g.load_index(str(p)) == {}
    assert g.gate_pick({"asset_class": "CRYPTO"}, g.load_index(str(p)))["allowed"] is False


def test_build_then_load_round_trip(tmp_path):
    p = tmp_path / "idx.json"
    idx = g.build_index(_rows("EQUITY", [0.40] * 40), COSTS)
    p.write_text(json.dumps(idx), encoding="utf-8")
    loaded = g.load_index(str(p))
    assert loaded["classes"]["EQUITY"]["allowed"] is True
    # cache must not resurrect a stale read after the file changes
    p.write_text(json.dumps(dict(idx, generated_at="2020-01-01T00:00:00Z")), encoding="utf-8")
    assert g.load_index(str(p)) == {}
