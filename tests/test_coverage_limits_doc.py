"""Guard the COVERAGE-LIMITED label against silent drift (Block 57).

The label lives in two places that must not disagree: the prose of
``CONTEST/ROUND_01_2026-11-23/COVERAGE_LIMITS.md`` and the ``## Machine-readable``
json block at its end. This test parses the block and checks it against itself
(integer consistency, recomputed rates) and against the prose (every surface the
json claims to apply to is actually named in the body).

Stdlib + json only: no network, no DB, no third-party imports.
"""
from __future__ import annotations

import json
import re

import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "CONTEST" / "ROUND_01_2026-11-23" / "COVERAGE_LIMITS.md"

HEADING = "## Machine-readable"
BLOCK_RE = re.compile(
    r"^## Machine-readable\s*$\n+```json\n(.*?)\n```", re.MULTILINE | re.DOTALL
)


def _text() -> str:
    assert DOC.exists(), f"{DOC} is missing"
    return DOC.read_text(encoding="utf-8")


def _block() -> dict:
    m = BLOCK_RE.search(_text())
    assert m, f"{DOC} has no parseable '{HEADING}' fenced json block"
    return json.loads(m.group(1))


def _body_without_block() -> str:
    return BLOCK_RE.sub("", _text())


def test_doc_exists_with_parseable_machine_readable_block():
    data = _block()
    assert isinstance(data, dict) and data, "the json block must be a non-empty object"


def test_label_is_coverage_limited():
    assert _block()["label"] == "COVERAGE-LIMITED"


def test_coverage_integers_are_positive_and_consistent():
    c = _block()["coverage"]
    for key in ("covered", "universe", "scored_rows", "total_closed_picks"):
        assert isinstance(c[key], int) and c[key] > 0, f"coverage.{key} must be a positive integer"
    assert c["covered"] <= c["universe"], "covered cannot exceed the display universe"
    assert c["covered"] <= c["scored_rows"], "covered cannot exceed the scoreable rows"
    assert c["scored_rows"] <= c["total_closed_picks"], "scoreable cannot exceed all closed picks"


def test_rates_match_recomputed_values_to_three_decimals():
    data = _block()
    c, r = data["coverage"], data["rates"]
    expected = {
        "covered_of_universe": c["covered"] / c["universe"],
        "scored_of_closed": c["scored_rows"] / c["total_closed_picks"],
        "covered_of_scored": c["covered"] / c["scored_rows"],
        "covered_of_closed": c["covered"] / c["total_closed_picks"],
    }
    for key, value in expected.items():
        assert abs(r[key] - value) <= 0.0005, (
            f"rates.{key} = {r[key]} does not match the recomputed {value:.6f} "
            "to 3 decimal places"
        )


def test_applies_to_entries_are_named_in_the_body_text():
    data = _block()
    entries = data["applies_to"]
    assert entries, "applies_to must not be empty"
    body = _body_without_block()
    for entry in entries:
        assert entry in body, (
            f"applies_to entry {entry!r} is in the json but not in the document body, "
            "so the label and the prose have drifted apart"
        )


def _excluded_class_entry() -> str:
    entries = [e for e in _block()["unmeasured"]
               if e.startswith("class composition of the 6,111 unscoreable rows")]
    assert len(entries) == 1, (
        "exactly one 'class composition' entry must stay in unmeasured so the "
        "INSTRUMENTED marker has a single home"
    )
    return entries[0]


def test_excluded_class_composition_is_marked_instrumented():
    """Block 59 wired the path; the marker must survive any doc edit."""
    entry = _excluded_class_entry()
    assert "INSTRUMENTED" in entry, (
        "the excluded-row class composition is now instrumented "
        "(coverage.excluded_summary); the entry must say so rather than "
        "claiming it is still unmeasured"
    )


def test_excluded_class_entry_carries_no_invented_integer():
    """The marker must not smuggle in a count the next live build has to match.

    The only integers allowed are the ones already in the shared phrase
    '6,111 unscoreable rows' and the dated marker '2026-11-24'; a 'total: N'
    would be a fabricated measurement.
    """
    entry = _excluded_class_entry()
    stripped = entry.replace("6,111", "").replace("2026-11-24", "")
    assert not re.search(r"\d", stripped), (
        f"no invented integer may appear in the INSTRUMENTED entry: {entry!r}"
    )
    assert "total" not in entry.lower(), (
        "the entry must not assert a total count before the live build produces one"
    )


def test_observation_log_records_the_zero_total_trap():
    """Block 61: the pre-wiring observation must stay on the record.

    ``total: 0`` looks the same whether the summary is un-wired or genuinely
    empty, so the doc has to keep saying so -- otherwise the next reader
    concludes "no excluded rows exist" from a payload that never carried any.
    """
    text = _text()
    assert "## Observation log" in text, (
        "the dated observation log must not be deleted from COVERAGE_LIMITS.md"
    )
    assert "indistinguishable from the un-wired default" in text, (
        "the observation log must keep the 'total: 0 is indistinguishable from "
        "the un-wired default' warning so the Block 59/60 trap cannot be "
        "forgotten"
    )


LEDGER = ROOT / "audit_dashboard" / "data" / "audit3_ledger.json"


def test_snapshot_stamp_exists_and_names_the_limitation():
    """Block 63: the json must say WHEN it was captured and that it is not live.

    The integers above are a point-in-time read of a table that refreshes
    hourly. Without a stamp a reader cannot tell a snapshot from live state --
    and an earlier claim that this block 'cannot drift' was exactly that error.
    """
    snap = _block()["snapshot"]
    assert snap.get("captured_at_ref"), "snapshot.captured_at_ref must name the ref"
    assert snap.get("ledger_generated_at"), (
        "snapshot.ledger_generated_at must name the ledger timestamp"
    )
    note = snap.get("note", "")
    assert ("hourly" in note or "not live" in note), (
        "snapshot.note must say the figures are not live / refresh hourly"
    )
    assert "check_excluded_summary.py" in note, (
        "snapshot.note must point at the live-state checker"
    )


def test_prose_states_the_figures_are_a_snapshot_not_live():
    assert "snapshot, not live" in _text().lower(), (
        "the prose must call the figures a snapshot, not live, so they cannot "
        "be mistaken for current state"
    )


@pytest.mark.skipif(not LEDGER.exists(), reason="audit3 ledger not present in this checkout")
def test_snapshot_is_within_tolerance_of_the_current_ledger():
    """A snapshot may be stale; wild drift means the finding changed.

    Tolerance is 5% of the live ``covered`` count: the metric moves by tens as
    the display universe refills, so a 2% band would be noise, but a collapse
    or doubling means the COVERAGE-LIMITED story needs a fresh read.
    """
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    live = data.get("selection_alpha", {}).get("covered")
    if not isinstance(live, int) or live <= 0:
        pytest.skip("ledger carries no usable selection_alpha.covered")
    snap = _block()["coverage"]["covered"]
    assert abs(snap - live) / live <= 0.05, (
        f"snapshot covered={snap} is more than 5% from the live ledger "
        f"covered={live}; re-read the ledger and update the snapshot (and its "
        "captured_at_ref) in the same commit"
    )
