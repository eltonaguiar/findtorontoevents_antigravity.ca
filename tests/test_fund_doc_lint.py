"""Tests for tools/fund_doc_lint.py.

The lint exists because three defects in this report were labelling or
provenance errors rather than arithmetic errors, and none of them were
catchable by reading the table. A lint that silently stops catching them is
worse than no lint, so the failure modes are tested explicitly.
"""
import pathlib
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
LINT = REPO_ROOT / "tools" / "fund_doc_lint.py"
DOC = REPO_ROOT / "docs" / "edge_research" / "FUNDS_WHAT_TO_BUY_2026-11-23_CORRECTED.md"


def _run(*args):
    p = subprocess.run([sys.executable, str(LINT), *args],
                       capture_output=True, text=True, cwd=REPO_ROOT)
    return p.returncode, p.stdout + p.stderr


def test_real_report_has_no_unsourced_table_numbers():
    if not DOC.exists():
        pytest.skip("report not present")
    code, out = _run("--strict")
    assert code == 0, out
    assert "unsourced              : 0" in out


def test_catches_a_planted_unsourced_number(tmp_path):
    poison = tmp_path / "poison.md"
    poison.write_text("| fund | value |\n|---|---|\n| SPY | 99.99% |\n")
    code, out = _run("--doc", str(poison), "--strict")
    assert code == 1, out
    assert "99.99" in out


def test_does_not_match_at_coarser_precision(tmp_path):
    """A regression guard. 99.99 normalised to 1dp becomes 100.0, and 100.0 is
    a common portfolio weight in the payload - that produced a false pass.
    """
    poison = tmp_path / "p.md"
    poison.write_text("| fund | value |\n|---|---|\n| SPY | 99.99% |\n")
    code, _ = _run("--doc", str(poison), "--strict")
    assert code == 1, "coarser rounding let an unsourced number through"


def test_errata_sections_are_exempt(tmp_path):
    """Errata quote the WRONG figures on purpose. They must not be flagged."""
    ok = tmp_path / "ok.md"
    ok.write_text(
        "## Errata - what the original got wrong\n\n"
        "| claim | correction |\n|---|---|\n| Sharpe 0.728 | was not a Sharpe |\n"
    )
    code, out = _run("--doc", str(ok), "--strict")
    assert code == 0, out


def test_allocation_labels_are_not_treated_as_data(tmp_path):
    ok = tmp_path / "ok.md"
    ok.write_text("| mix | note |\n|---|---|\n| 60/40 | labelled only |\n")
    code, out = _run("--doc", str(ok), "--strict")
    assert code == 0, out


def test_confidence_level_and_schedule_labels_are_ignored(tmp_path):
    ok = tmp_path / "ok.md"
    ok.write_text(
        "| a | b |\n|---|---|\n"
        "| 90% CI | quarterly (63d) |\n"
        "| US Roth IRA / 401(k) | x |\n"
    )
    code, out = _run("--doc", str(ok), "--strict")
    assert code == 0, out


def test_advisory_mode_does_not_fail_the_build(tmp_path):
    poison = tmp_path / "p.md"
    poison.write_text("| fund | value |\n|---|---|\n| SPY | 99.99% |\n")
    code, out = _run("--doc", str(poison))
    assert code == 0, out
    assert "unsourced              : 1" in out
