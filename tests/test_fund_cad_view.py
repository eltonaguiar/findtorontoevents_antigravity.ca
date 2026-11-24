"""Tests for the CAD-investor view (reports/fund_cad_view.json).

Reads the committed artifact only - no network - so CI stays deterministic.
The FX series is fetched by tools/fund_cad_view.py on demand and committed with
provenance; these tests check the claims derived from it.
"""
import json
import pathlib

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
CAD = REPO_ROOT / "reports" / "fund_cad_view.json"
DOC = REPO_ROOT / "docs" / "edge_research" / "FUNDS_WHAT_TO_BUY_2026-11-23_CORRECTED.md"


@pytest.fixture(scope="module")
def cad():
    if not CAD.exists():
        pytest.skip("no CAD artifact committed")
    return json.loads(CAD.read_text())


def test_artifact_carries_provenance(cad):
    """A currency number with no pair/period provenance is untraceable."""
    for key in ("fetched_at", "period", "fx_pair", "usdcad_first", "usdcad_last",
                "fx_cagr_pct", "rf_cad_pct", "hedge_carry_pct_assumed"):
        assert key in cad, f"CAD artifact missing {key}"
    assert "CAD=X" in cad["fx_pair"]


def test_hedging_is_declared_as_an_assumption(cad):
    """Carry is a parameter, not a measurement. It must say so in the payload."""
    assert cad["hedge_carry_pct_assumed"] is not None
    for m in cad["funds"].values():
        assert "hedged_approx_net_cagr_pct" in m


def test_fx_effect_matches_the_compounding_identity(cad):
    """cad = (1+usd)(1+fx)-1 must agree with the reported FX effect to rounding."""
    fx = cad["fx_cagr_pct"] / 100.0
    for name, m in cad["funds"].items():
        usd = m["usd_net_cagr_pct"] / 100.0
        expected = ((1 + usd) * (1 + fx) - 1) * 100.0
        assert expected == pytest.approx(m["cad_net_cagr_pct"], abs=0.05), name


def test_currency_dwarfs_the_fee_edge(cad):
    """The whole point of the section: this is not a rounding effect."""
    assert cad["currency_vs_fee_ratio"] > 10
    assert abs(cad["fx_cagr_pct"]) > 1.0


def test_cash_ratios_are_left_undefined(cad):
    m = cad["funds"]["SGOV_adj"]
    assert m["cad_sharpe"] is None
    assert m["ratio_note"] if "ratio_note" in m else True


def test_doc_states_the_caveats():
    """Reporting an FX windfall without the reversal caveat would be misleading."""
    text = DOC.read_text()
    assert "If you spend in CAD" in text
    assert "not a forecast" in text.lower()
    # the benchmark moves with the asset, which is why Sharpe barely changes
    assert "hurdle rose" in text.lower() or "6.50%" in text
    assert "approximated, not measured" in text.lower() or "approximate" in text.lower()
