"""Tripwire (2026-11-22 provenance repair): a quoted cost metric MUST exist in
the artifact it cites.

Why this exists
    The M1 equity-cost write-up quoted 12.07 bp round-trip while its committed
    artifact recorded ``n_symbols_with_data: 0`` / ``SKIPPED_OFFLINE_OR_NO_KEY``.
    The number was real (it reproduces exactly from yfinance 1-min bars) but the
    artifact could not support it, because a key-gated re-run overwrote the good
    run. A reader could not tell a real measurement from a fabricated one.

    This is deliberately small: one validator plus three tests. It is not a
    framework. It fails loudly on the exact shape of that defect.
"""
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
ARTIFACT = ROOT / "reports" / "equity_cost_measurement" / "equity_cost_20261122.json"
WRITEUP = ROOT / "updates" / "2026-11-22-m1-equity-cost-measurement.md"
TOL_BP = 0.01          # the write-up rounds 12.0749 -> 12.07


def assert_quoted_metric_supported(artifact: dict, quoted_bp: float,
                                   tol_bp: float = TOL_BP) -> bool:
    """A quoted spread figure is only allowed if the artifact contains it.

    Rejects: no per-symbol data, a null median, or a median that does not match
    the quoted value. Returns True when supported, raises AssertionError otherwise.
    """
    agg = artifact.get("spread_aggregate") or {}
    n = agg.get("n_symbols_with_data")
    median = agg.get("range_upper_bound_rt_bp_median")
    assert isinstance(n, int) and n > 0, (
        f"a {quoted_bp}bp figure is quoted but the artifact has "
        f"n_symbols_with_data={n!r} - no spread data to support it")
    assert median is not None, (
        f"a {quoted_bp}bp figure is quoted but the artifact median is null")
    assert abs(float(median) - float(quoted_bp)) <= tol_bp, (
        f"quoted {quoted_bp}bp but the artifact median is {float(median):.4f}bp "
        f"(tolerance {tol_bp}bp)")
    return True


@pytest.mark.skipif(not ARTIFACT.exists(), reason="M1 artifact not present")
def test_committed_artifact_contains_the_quoted_median():
    art = json.loads(ARTIFACT.read_text())
    # the value the M1 write-up quotes, rounded to 2 dp
    assert_quoted_metric_supported(art, 12.07)
    agg = art["spread_aggregate"]
    assert agg["n_symbols_with_data"] == 13
    assert len(agg["per_name_rt_bp"]) == 13
    assert agg["provenance_self_check"] == "PASS"


@pytest.mark.skipif(not WRITEUP.exists(), reason="M1 write-up not present")
def test_every_quoted_round_trip_bp_in_the_writeup_is_supported():
    art = json.loads(ARTIFACT.read_text())
    text = WRITEUP.read_text()
    # the write-up's canonical quoted RT bound
    m = re.search(r"\*\*(12\.07) bp\*\* round trip", text)
    assert m, "expected the 12.07 bp round-trip quote in the M1 write-up"
    assert_quoted_metric_supported(art, float(m.group(1)))


def test_tripwire_rejects_the_stale_artifact_shape():
    """Fail-before proof: the shape actually committed at 22:49:21Z is rejected.

    Kept inline so the regression is durable and needs no network or /tmp file.
    """
    stale = {
        "spread": {"status": "SKIPPED_OFFLINE_OR_NO_KEY"},
        "spread_aggregate": {
            "n_symbols_with_data": 0,
            "range_upper_bound_rt_bp_median": None,
        },
    }
    with pytest.raises(AssertionError, match="n_symbols_with_data"):
        assert_quoted_metric_supported(stale, 12.07)


def test_tripwire_rejects_a_real_count_but_wrong_median():
    """A non-zero count is not enough - the value must match too."""
    wrong = {"spread_aggregate": {"n_symbols_with_data": 13,
                                  "range_upper_bound_rt_bp_median": 8.31}}
    with pytest.raises(AssertionError, match="median is 8.3100bp"):
        assert_quoted_metric_supported(wrong, 12.07)
