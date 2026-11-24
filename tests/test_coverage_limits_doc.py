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
