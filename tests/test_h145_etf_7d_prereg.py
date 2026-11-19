"""Lock the H-145 pre-registration (ETF 7-day time exit) and its Bonferroni gate.

These are guard tests, not edge tests: they fail if the entry is edited after the
fact, if the post-hoc disclosure is removed, or if the corrected alpha stops
matching the 3-class x 3-horizon family it was selected from.
"""
from __future__ import annotations

import json
from pathlib import Path
from statistics import NormalDist

import pytest

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "reports" / "hypothesis_registry.json"
EVIDENCE = ROOT / "reports" / "exit_ab_paper_2026-11-19.json"

FAMILY_K = 9
FAMILY_ALPHA = 0.05


@pytest.fixture(scope="module")
def entry():
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    hyps = data["hypotheses"] if isinstance(data, dict) else data
    hits = [h for h in hyps if h.get("id") == "H-145"]
    assert len(hits) == 1, f"expected exactly one H-145, found {len(hits)}"
    return hits[0]


def test_registered_before_any_forward_row(entry):
    assert entry["status"] == "PRE_REGISTERED"
    assert entry["registered_at"] == "2026-11-19"
    assert entry["result"]["verdict"] == "UNTESTED"


def test_post_hoc_selection_is_disclosed(entry):
    lock = entry.get("data_sample_lock", "").lower()
    assert "post-hoc" in lock or "post_hoc" in lock
    assert "2026-11-19" in entry["data_sample_lock"]
    crit = entry["acceptance_criteria"]
    assert "9" in crit.get("multiplicity_note", "")
    assert "forward" in crit["rule"].lower()


def test_bonferroni_arithmetic_matches_the_tested_family(entry):
    bonf = entry["acceptance_criteria"]["bonferroni"]
    assert bonf["family_k"] == FAMILY_K
    assert bonf["family_alpha"] == FAMILY_ALPHA
    expected = round(FAMILY_ALPHA / FAMILY_K, 6)
    assert bonf["alpha_corrected"] == pytest.approx(expected, abs=1e-6)
    # two-sided critical z for that alpha, from the normal CDF
    z = NormalDist().inv_cdf(1 - bonf["alpha_corrected"] / 2)
    assert bonf["min_abs_z"] == pytest.approx(round(z, 3), abs=2e-3)


def test_the_selecting_sample_cannot_promote_it(entry):
    # The measured ETF/7d cell is nominally positive, but it is the cell that was
    # chosen by looking at all nine, so the registry must keep it forward-only.
    rep = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    seven = [h for h in rep["horizons"] if h["horizon_days"] == 7.0][0]
    etf = seven["by_class"]["ETF"]
    assert etf["n"] >= 20 and etf["mean_delta_pct"] > 0
    assert entry["status"] != "PROVEN_T2"
    assert entry["result"]["verdict"] != "PASS"


def test_no_duplicate_ids_and_registry_still_parses():
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    hyps = data["hypotheses"] if isinstance(data, dict) else data
    ids = [h.get("id") for h in hyps]
    assert len(ids) == len(set(ids)), "duplicate hypothesis id in the registry"
    assert "H-144" in ids and "H-145" in ids
