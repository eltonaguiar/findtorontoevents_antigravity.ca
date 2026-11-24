"""Tests for the Canadian answer (reports/fund_cad_home.json).

The jurisdiction decision made the US-domiciled funds unusable, so this artifact
carries the actual recommendation. It reads the committed artifact only - no
network - so CI stays deterministic.
"""
import json
import pathlib

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
HOME = REPO_ROOT / "reports" / "fund_cad_home.json"
DOC = REPO_ROOT / "docs" / "edge_research" / "FUNDS_WHAT_TO_BUY_2026-11-23_CORRECTED.md"


@pytest.fixture(scope="module")
def home():
    if not HOME.exists():
        pytest.skip("no CAD-home artifact")
    return json.loads(HOME.read_text())


def test_artifact_is_provenanced(home):
    for k in ("fetched_at", "period", "cash_hurdle_pct", "source", "funds"):
        assert k in home, f"missing {k}"


def test_all_six_tsx_funds_present(home):
    for t in ("VFV.TO", "ZSP.TO", "VUN.TO", "XEQT.TO", "ZAG.TO", "CASH.TO"):
        assert t in home["funds"], f"{t} missing from the Canadian answer"


def test_core_wrapper_is_not_more_expensive_than_the_us_etf(home):
    """The finding that changes the recommendation: VFV/ZSP are cheaper than SPY."""
    wc = home["wrapper_cost"]
    assert wc["VFV.TO"]["delta_pp"] <= 0, wc["VFV.TO"]
    assert wc["ZSP.TO"]["delta_pp"] <= 0, wc["ZSP.TO"]
    # but the other sleeves do cost something, so this is not a blanket claim
    assert wc["VUN.TO"]["delta_pp"] > 0
    assert wc["ZAG.TO"]["delta_pp"] > 0


def test_cash_hurdle_is_used_and_ratios_left_undefined(home):
    assert home["funds"]["CASH.TO"]["sharpe_vs_cad_cash"] is None
    for t, m in home["funds"].items():
        if t == "CASH.TO":
            continue
        assert m["sharpe_vs_cad_cash"] is not None, t


def test_net_never_exceeds_gross(home):
    for t, m in home["funds"].items():
        assert m["net_cagr_pct"] <= m["gross_cagr_pct"] + 1e-9, t


def test_bond_sleeve_was_a_drag_in_this_window(home):
    """ZAG had negative excess return vs CAD cash, same as BND in USD."""
    assert home["funds"]["ZAG.TO"]["sharpe_vs_cad_cash"] < 0


def test_doc_states_the_two_unsettled_points():
    text = DOC.read_text()
    assert "The answer for a Canadian resident" in text
    assert "embeds USD exposure" in text
    assert "MER is not total cost" in text
