"""Synthetic-row tests for ``summarize_excluded_rows`` (Block 58).

The summariser exists to make the dashboard's excluded cohorts measurable
per asset class and per reason. These tests feed it hand-built rows only --
no MySQL, no generator run -- and pin the three properties that matter:

* overlapping cohorts are counted in every cohort they belong to,
* a row with no asset class lands in an explicit ``"UNKNOWN"`` bucket rather
  than being silently dropped,
* ``by_reason`` reuses ``summarize_excluded`` so reason detail cannot drift
  between the two functions.

Stdlib only.
"""
from __future__ import annotations

import pytest

from audit_trail.excluded_cohorts import summarize_excluded, summarize_excluded_rows

REASONS = ("invalid_row", "mirror_duplicate", "non_performance_exit",
           "resolver_breakeven_fallback")


def _row(asset_class="CRYPTO", reason="invalid_row", symbol="BTCUSDT", pnl=1.0):
    return {"asset_class": asset_class, "exclude_reason": reason,
            "symbol": symbol, "pnl_pct": pnl, "direction": "LONG"}


def test_empty_and_none_are_safe():
    for empty in (None, {}, {"integrity": []}):
        out = summarize_excluded_rows(empty)
        assert out["total"] == 0
        assert out["by_class"] == {}
        assert set(out["by_reason"]) == set(REASONS)


def test_overlapping_cohorts_count_the_row_twice_in_reason_but_once_in_total():
    """A row dropped by both integrity and auto-expiry is ONE missing row."""
    shared = _row("EQUITY", "non_performance_exit")
    out = summarize_excluded_rows({
        "integrity": [shared, _row("CRYPTO", "invalid_row")],
        "auto_expired": [shared],
    })
    assert out["total"] == 2, "the shared row must not inflate the row total"
    assert out["by_reason"]["non_performance_exit"] == 1
    assert out["by_reason"]["invalid_row"] == 1
    assert out["by_class"]["EQUITY"] == 1
    assert out["by_class"]["CRYPTO"] == 1
    assert out["overlap"] is True
    assert any("overlap" in note for note in out["notes"])


def test_single_cohort_is_not_flagged_as_overlapping():
    out = summarize_excluded_rows({"canonical": [_row(), _row()]})
    assert out["overlap"] is False
    assert out["by_class"] == {"CRYPTO": 2}


def test_row_without_class_lands_in_the_unknown_bucket_not_dropped():
    out = summarize_excluded_rows({
        "canonical": [_row(asset_class=""), {"exclude_reason": "invalid_row"},
                      {"asset_class": None, "exclude_reason": "invalid_row"},
                      _row("CRYPTO")],
    })
    assert out["total"] == 4, "classless rows must still be counted"
    assert out["by_class"]["UNKNOWN"] == 3
    assert out["by_class"]["CRYPTO"] == 1
    assert out["by_class_and_reason"]["UNKNOWN"]["invalid_row"] == 3
    assert sum(out["by_class"].values()) == out["total"]


def test_non_mapping_rows_are_skipped():
    out = summarize_excluded_rows({"canonical": [_row(), "not a row", None, 42]})
    assert out["total"] == 1


def test_by_reason_reuses_summarize_excluded():
    rows = [_row("CRYPTO", "invalid_row", pnl=2.0),
            _row("CRYPTO", "mislabeled", pnl=-1.0)]
    out = summarize_excluded_rows({"canonical": rows})
    direct = summarize_excluded(rows)
    assert out["reason_detail"] == direct["by_reason"]
    assert out["by_reason"]["mislabeled"] == 1
    assert out["reason_detail"]["invalid_row"]["mean_pnl_pct"] == pytest.approx(2.0)


def test_reason_falls_back_to_private_key_then_unknown():
    out = summarize_excluded_rows({
        "canonical": [{"asset_class": "ETF", "_exclude_reason": "mirror_duplicate"},
                      {"asset_class": "ETF"}],
    })
    assert out["by_class_and_reason"]["ETF"]["mirror_duplicate"] == 1
    assert out["by_class_and_reason"]["ETF"]["unknown"] == 1


def test_by_class_and_reason_partitions_by_class():
    out = summarize_excluded_rows({
        "canonical": [_row("CRYPTO", "invalid_row"), _row("CRYPTO", "mirror_duplicate"),
                      _row("EQUITY", "invalid_row")],
    })
    assert out["by_class_and_reason"] == {
        "CRYPTO": {"invalid_row": 1, "mirror_duplicate": 1},
        "EQUITY": {"invalid_row": 1},
    }
    for cls, per in out["by_class_and_reason"].items():
        assert sum(per.values()) == out["by_class"][cls]
