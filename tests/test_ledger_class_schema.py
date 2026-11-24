import json
from pathlib import Path

import pytest

LEDGER = (Path(__file__).resolve().parent.parent / "docs"
          / "audit_review_2026-11-22" / "_raw" / "audit3_audit3_ledger.json")

pytestmark = pytest.mark.skipif(not LEDGER.exists(),
                                reason="committed ledger not present")

REQUIRED = ["asset_class", "n", "pf", "pf_basis", "net_ci_pct",
            "net_ci_pct_2x", "stress_2x_ok", "split_half",
            "top_symbol_share", "verdict", "alpha_gate"]


@pytest.fixture(scope="module")
def classes():
    return json.loads(LEDGER.read_text(encoding="utf-8"))["classes"]


def test_classes_is_a_non_empty_list(classes):
    assert isinstance(classes, list) and classes


def test_every_class_row_has_the_fields_we_rely_on(classes):
    for row in classes:
        missing = [k for k in REQUIRED if k not in row]
        assert not missing, f"{row.get('asset_class')} missing {missing}"


def test_pf_basis_is_net_so_pf_is_comparable(classes):
    # If pf_basis ever becomes 'gross', the ladder's PF test silently changes
    # meaning. Fail loudly instead.
    for row in classes:
        assert row["pf_basis"] == "net", row.get("asset_class")


def test_split_half_uses_first_second_half_mean(classes):
    # split_half may be null (too few rows to split). When it is present it
    # must carry the two means the ladder reads; null is treated as unstable.
    for row in classes:
        sh = row["split_half"]
        if sh is None:
            continue
        assert "first_half_mean" in sh and "second_half_mean" in sh


def test_alpha_gate_carries_a_coverage_flag(classes):
    for row in classes:
        assert "alpha_coverage_ok" in row["alpha_gate"], row.get("asset_class")
