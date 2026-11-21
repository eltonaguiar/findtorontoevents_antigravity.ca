"""The shared population sidecar: one artifact, four required fields.

2026-11-21 review: "closed picks" was quoted at 4,618 / 1,927 / 8,769 / 16,372 /
7,942 across the three audit surfaces, and audit3's own coverage block declared
``scored_share_of_valid_pct`` "not_comparable" at 110.41%. A rate whose
denominator is unknown is not a measurement, so every input that is missing must
surface as ``null`` + a note -- never 0, never 1.
"""
from alpha_engine.denominator import SCHEMA, build, format_label

DASH = {
    "resolved_closed_picks_net": {
        "schema": "audit.canonical.v1",
        "rows_sha256": "a" * 64,
        "counts": {"kept_rows": 8769,
                   "excluded_by_reason": {"invalid_row": 7394, "mirror_duplicate": 95}},
    }
}
LEDGER = {
    "coverage": {
        "total_closed_picks": 16372,
        "valid_closed_picks": 7942,
        "scored_rows": 8769,
        "denominator": {"canonical_kept_rows": 8769,
                        "canonical_rows_sha256": "a" * 64,
                        "canonical_excluded_by_reason": {"non_performance_exit": 43}},
    }
}


def test_all_four_required_fields_are_present_and_correct():
    d = build(DASH, LEDGER)
    assert d["schema"] == SCHEMA
    assert d["canonical_sha256"] == "a" * 64
    assert d["n_canonical"] == 8769
    assert d["n_total_closed"] == 16372
    assert {r["reason"] for r in d["exclusion_reasons"]} == {
        "invalid_row", "mirror_duplicate", "non_performance_exit"}
    assert d["complete"] is True


def test_label_names_the_population_and_the_share():
    label = format_label(build(DASH, LEDGER))
    assert "8,769 of 16,372" in label
    assert "53.6%" in label
    assert "sha aaaaaaaaaaaa" in label


def test_missing_canonical_count_is_unknown_not_zero():
    d = build({}, {"coverage": {"total_closed_picks": 16372}})
    assert d["n_canonical"] is None
    assert d["complete"] is False
    assert "unknown" in d["population_label"]
    assert any("unknown, not zero" in n for n in d["notes"])


def test_falls_back_to_the_ledger_and_names_that_source():
    d = build(None, LEDGER)
    assert d["n_canonical"] == 8769
    assert d["canonical_source"] == "audit3_ledger.coverage"


def test_two_pipelines_are_noted_rather_than_silently_subtracted():
    d = build(DASH, LEDGER)
    assert d["n_unscored"] == 7603
    assert any("exclusion reasons total" in n for n in d["notes"])


def test_nothing_is_coerced_to_a_count():
    d = build({}, {})
    assert d["n_canonical"] is None and d["n_total_closed"] is None
    assert d["n_unscored"] is None
    assert d["exclusion_reasons"] == []


def test_disagreeing_snapshots_are_flagged_not_ratioed():
    ledger = {"generated_at": "2026-11-21T02:00:00Z",
              "coverage": {"total_closed_picks": 16372,
                           "denominator": {"canonical_kept_rows": 9000}}}
    d = build(DASH, ledger)
    assert d["n_canonical"] == 8769          # publisher wins
    assert any("snapshots differ" in n for n in d["notes"])
