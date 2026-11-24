"""Tests for the wrapper decomposition (reports/fund_wrapper_decomp.json).

This artifact attributes the CAD-vs-US gap to MER versus withholding. The first
version of it paired ZAG.TO with BND and CASH.TO with SGOV, neither of which is
a CAD-listed version of the other, and reported the resulting exposure mismatch
as wrapper cost. These tests pin the corrected scope.
"""
import json
import pathlib

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DEC = REPO_ROOT / "reports" / "fund_wrapper_decomp.json"
DOC = REPO_ROOT / "docs" / "edge_research" / "FUNDS_WHAT_TO_BUY_2026-11-23_CORRECTED.md"


@pytest.fixture(scope="module")
def dec():
    if not DEC.exists():
        pytest.skip("no decomposition artifact")
    return json.loads(DEC.read_text())


def test_only_exposure_matched_pairs_are_included(dec):
    """The core correction: mismatched pairs must not be differenced."""
    tickers = {r["cad_listed"] for r in dec["rows"]}
    assert tickers == {"VFV.TO", "ZSP.TO", "VUN.TO"}, tickers
    assert "ZAG.TO" not in tickers
    assert "CASH.TO" not in tickers


def test_mismatched_funds_are_named_with_a_reason(dec):
    nc = dec["not_exposure_matched"]
    assert "ZAG.TO" in nc and "Canadian" in nc["ZAG.TO"]
    assert "CASH.TO" in nc and "CAD cash" in nc["CASH.TO"]


def test_sp500_wrapper_residual_matches_predicted_withholding(dec):
    """The validated finding: for the S&P 500 pair the residual is ~2bp off the
    predicted fund-level withholding."""
    by = {r["cad_listed"]: r for r in dec["rows"]}
    for t in ("VFV.TO", "ZSP.TO"):
        assert by[t]["within_tolerance"] is True, by[t]
        assert abs(by[t]["unexplained_pp"]) <= 0.05


def test_vun_is_recorded_as_unexplained_not_force_fit(dec):
    """VUN's residual is 0.156pp beyond prediction. It must stay flagged rather
    than being quietly absorbed or dropped."""
    by = {r["cad_listed"]: r for r in dec["rows"]}
    assert by["VUN.TO"]["within_tolerance"] is False
    assert dec["consistent_with_withholding"] is False
    assert any("VUN" in u for u in dec["unexplained"])


def test_artifact_disclaims_the_attribution(dec):
    assert "corroboration, not proof" in dec["caveat"]


def test_doc_records_both_the_validation_and_the_mispairing(dec):
    text = DOC.read_text()
    assert "What the wrapper actually costs" in text
    assert "cannot yet explain" in text
    assert "ZAG.TO holds" in text and "CASH.TO holds" in text
