"""Tests for the withholding estimate and the jurisdiction decision.

The jurisdiction call (Canadian resident, decided 2026-11-24) gates the whole
recommendation, and the withholding figure is the cost it hinges on. Both are
pinned so a later edit cannot quietly revert to "unresolved" or turn an
unverified tax treatment into a stated fact.
"""
import json
import pathlib

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
WH = REPO_ROOT / "reports" / "fund_withholding.json"
DECISION = REPO_ROOT / "docs" / "edge_research" / "JURISDICTION_DECISION_2026-11-24.md"
DOC = REPO_ROOT / "docs" / "edge_research" / "FUNDS_WHAT_TO_BUY_2026-11-23_CORRECTED.md"


@pytest.fixture(scope="module")
def wh():
    if not WH.exists():
        pytest.skip("no withholding artifact")
    return json.loads(WH.read_text())


def test_withholding_artifact_is_provenanced(wh):
    for k in ("fetched_at", "fee_edge_pp", "statutory_rate_pct",
              "treaty_rate_pct", "rows", "caveat"):
        assert k in wh, f"missing {k}"
    # the tax treatment must stay flagged, not silently upgraded to fact
    assert wh["tax_treatment_verified"] is False


def test_interest_is_not_withheld_but_dividends_are(wh):
    """A bond fund yields 4% yet contributes zero drag. This is the nuance that
    makes a single blended withholding number wrong."""
    by = {r["ticker"]: r for r in wh["rows"]}
    assert by["BND"]["withholdable"] is False
    assert by["BND"]["tfsa_or_taxable_drag_pp_treaty"] == 0.0
    assert by["BND"]["distribution_yield_pct"] > 3.0
    assert by["SPY"]["withholdable"] is True
    assert by["SPY"]["tfsa_or_taxable_drag_pp_treaty"] > 0.0


def test_withholding_exceeds_the_fee_edge(wh):
    """If this ever flips, the report's ranking of priorities is wrong."""
    assert wh["max_multiple_of_fee_edge"] > 1.0
    lo, hi = wh["equity_drag_range_pp"]
    assert lo > wh["fee_edge_pp"], (lo, wh["fee_edge_pp"])
    assert hi > lo


def test_rrsp_is_modelled_as_zero_drag(wh):
    for r in wh["rows"]:
        assert r["rrsp_drag_pp"] == 0.0


def test_decision_document_exists_and_states_the_call():
    assert DECISION.exists(), "jurisdiction was delegated; the decision must be written down"
    text = DECISION.read_text()
    assert "Canadian resident" in text
    assert "Reasoning" in text
    # consequences-if-wrong must be stated, not omitted
    assert "Consequences if wrong" in text


def test_report_no_longer_says_jurisdiction_is_unresolved():
    text = DOC.read_text()
    assert "Jurisdiction decided" in text
    assert "has not been confirmed by the operator" not in text
    assert "E3–E6: DECIDED" in text or "DECIDED 2026-11-24" in text
