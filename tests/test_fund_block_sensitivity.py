"""Tests for tools/fund_block_sensitivity.py (bootstrap block-length choice).

An independent review claimed a 21-day block is too short and therefore the
confidence intervals are too narrow. The claim was tested rather than accepted;
the data contradicts its direction. These tests pin the finding so the report
cannot drift back to asserting the reviewer's version.
"""
import json
import pathlib
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "tools" / "fund_block_sensitivity.py"
COMMITTED = REPO_ROOT / "reports" / "fund_block_sensitivity.json"
DOC = REPO_ROOT / "docs" / "edge_research" / "FUNDS_WHAT_TO_BUY_2026-11-23_CORRECTED.md"


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    if not (REPO_ROOT / "2026-11-15_AM_profitability-plan/copilot-financial-review/market_prices.csv").exists():
        pytest.skip("price CSV not present in this checkout")
    out = tmp_path_factory.mktemp("blocks") / "b.json"
    p = subprocess.run(
        [sys.executable, str(SCRIPT), "--json", str(out), "--n-boot", "300"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    assert p.returncode == 0, p.stdout + p.stderr
    return json.loads(out.read_text())


def test_committed_artifact_exists_and_is_labelled():
    assert COMMITTED.exists(), "report quotes block widths but no artifact exists"
    d = json.loads(COMMITTED.read_text())
    assert d["baseline_block"] == 21
    assert "verdict" in d
    for b, block in d["by_block"].items():
        assert "block" in block and "n_blocks" in block, "identifier columns must be sourced"


def test_longer_blocks_narrow_spy_interval(result):
    """The empirical core: this refutes the reviewer's stated direction."""
    widths = {int(b): v["SPY_adj"]["width"] for b, v in result["by_block"].items()}
    assert widths[252] < widths[21] < widths[5], widths
    assert "NOT supported" in result["verdict"]


def test_sensitivity_is_reported_as_material(result):
    """The width moves by ~29%, which is why the choice is disclosed."""
    w = {int(b): v["SPY_adj"]["width"] for b, v in result["by_block"].items()}
    spread = (max(w.values()) - min(w.values())) / w[21]
    assert spread > 0.15, f"block choice barely matters ({spread:.2%}); doc overstates it"


def test_all_blocks_present(result):
    blocks = sorted(int(b) for b in result["by_block"])
    assert blocks == [5, 21, 63, 126, 252]


def test_doc_quantifies_duration_risk_and_does_not_call_the_yield_a_forecast():
    text = DOC.read_text()
    assert "duration" in text.lower()
    assert "not a forecast" in text.lower() or "not a forecast" in text.lower()
    assert "1pp rise" in text or "6%" in text


def test_doc_discloses_the_block_choice():
    text = DOC.read_text()
    assert "block length" in text.lower()
    assert "±29%" in text or "+/-29%" in text or "29%" in text
