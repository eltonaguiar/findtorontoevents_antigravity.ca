import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alpha_engine.hypothesis_status import (  # noqa: E402
    CANONICAL_STATES, normalize_status, summarize)


def test_every_observed_spelling_maps():
    cases = {
        "PRE_REGISTERED": "PRE_REGISTERED",
        "PRE-REGISTERED": "PRE_REGISTERED",
        "REGISTERED-UNTESTED": "PRE_REGISTERED",
        "UNTESTED": "UNTESTED",
        "UNTESTED_DATA_GAP": "BLOCKED_DATA",
        "DATA_GAP": "BLOCKED_DATA",
        "REGISTERED_BLOCKED_ON_DATA": "BLOCKED_DATA",
        "CONTROL_FAILED_PENDING_CLEAN_ENTRY": "BLOCKED_DATA",
        "FORWARD_OBSERVATION": "FORWARD",
        "FORWARD_SHADOW": "FORWARD",
        "forward-shadow": "FORWARD",
        "FORWARD_ACCRUING": "FORWARD",
        "PAPER_PILOT": "FORWARD",
        "SHADOW_IMPLEMENTATION": "FORWARD",
        "SHADOW_LIVE": "FORWARD",
        "TESTED_PASS": "SUPPORTED",
        "TESTED_PASS_BACKTEST_FORWARD_PENDING": "SUPPORTED",
        "SUPPORTED": "SUPPORTED",
        "TESTED_WEAK": "WEAK",
        "REFUTED": "REFUTED",
        "KILLED": "REFUTED",
        "TESTED_KILL": "REFUTED",
        "REJECTED": "REFUTED",
        "HARNESS_REJECTED": "REFUTED",
        "FAILED_ARCHIVED": "REFUTED",
        "NULL": "REFUTED",
        "CLOSED": "REFUTED",
    }
    for raw, want in cases.items():
        assert normalize_status(raw) == want, (raw, normalize_status(raw))


def test_untested_with_data_gap_maps_to_blocked():
    assert normalize_status(
        "UNTESTED - data-gap (free Dune cex.flows path; SOPR path needs paid Glassnode)"
    ) == "BLOCKED_DATA"


def test_free_text_prefix_variant_maps():
    assert normalize_status("REJECTED - only 0 scored windows (need 3)") == "REFUTED"


def test_unknown_is_not_guessed():
    assert normalize_status("TOTALLY_NEW_STATE") == "UNKNOWN"
    assert normalize_status(None) == "UNKNOWN"
    assert normalize_status("   ") == "UNKNOWN"


def test_every_mapped_state_is_canonical():
    for raw in ("PRE_REGISTERED", "UNTESTED", "DATA_GAP", "PAPER_PILOT",
                "SUPPORTED", "TESTED_WEAK", "KILLED"):
        assert normalize_status(raw) in CANONICAL_STATES


def test_summarize_counts_sum_to_total_and_reports_unmapped():
    reg = {"hypotheses": [
        {"id": "H-1", "status": "PRE_REGISTERED"},
        {"id": "H-2", "status": "forward-shadow"},
        {"id": "H-3", "status": "WHATEVER"},
        {"id": "H-4", "status": "REJECTED - reason"},
    ]}
    out = summarize(reg)
    assert out["total"] == 4
    assert sum(out["counts"].values()) + out["unknown"] == 4
    assert out["counts"]["PRE_REGISTERED"] == 1
    assert out["counts"]["FORWARD"] == 1
    assert out["counts"]["REFUTED"] == 1
    assert out["unknown"] == 1
    assert out["unmapped_spellings"] == {"WHATEVER": 1}


def test_iter_is_recursive_and_ignores_non_records():
    reg = {"a": {"hypotheses": [{"id": "H-9", "status": "UNTESTED"}]},
           "b": [{"not_a_hypothesis": True}]}
    out = summarize(reg)
    assert out["total"] == 1 and out["counts"]["UNTESTED"] == 1
