"""Guard the per-class coverage caveats in the audit-review dossiers (Block 62).

The audit3 ledger is a price-covered remainder of a capped slice, so a dossier
verdict drawn from it describes the priced subset of a class, not the full
closed-pick population. ``CONTEST/ROUND_01_2026-11-23/COVERAGE_LIMITS.md``
labels that COVERAGE-LIMITED and names CRYPTO, FOREX and FUTURES as the classes
whose gate sits at ``alpha_coverage_ok = false``. Each of those three dossiers
must therefore carry a caveat that says so, in the same words, and the caveat
must rot loudly if someone deletes it.

What is asserted, per dossier:
  1. the marker ``Coverage caveat (2026-11-24)`` appears (the rot guard),
  2. ``COVERAGE_LIMITS.md`` is referenced, so the reader can follow the aggregate,
  3. the class's own coverage percentage appears as a literal,
  4. no tally string other than the canonical
     ``0 INVESTABLE / 11 NOT_INVESTABLE / 3 UNKNOWN`` is present -- a dossier edit
     must never smuggle in a second, disagreeing programme tally.

Stdlib only: no network, no DB, no third-party imports.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs" / "audit_review_2026-11-22"

# One marker string, identical in all three dossiers. Changing it here means
# changing it in every dossier in the same commit; the test is the contract.
MARKER = "Coverage caveat (2026-11-24)"

# The canonical programme tally. Dossier prose may quote it, never contradict it.
CANONICAL_TALLY = "0 INVESTABLE / 11 NOT_INVESTABLE / 3 UNKNOWN"

# class dossier -> the class's own price-coverage percentage literal.
CAVEATED = {
    "01_CRYPTO.md": "24.2",
    "04_FOREX.md": "46.8",
    "07_FUTURES.md": "83.3",
}

# A bare leading count is enough to catch a divergent tally; the full form is
# matched separately so the canonical line itself is accepted verbatim.
INVESTABLE_RE = re.compile(r"(\d+)\s+INVESTABLE")
FULL_TALLY_RE = re.compile(
    r"(\d+)\s+INVESTABLE\s*/\s*(\d+)\s+NOT_INVESTABLE\s*/\s*(\d+)\s+UNKNOWN"
)


def _text(name: str) -> str:
    path = DOCS / name
    assert path.exists(), f"{path} is missing -- the dossier set moved"
    return path.read_text(encoding="utf-8")


def test_each_caveated_dossier_is_present():
    for name in CAVEATED:
        assert (DOCS / name).is_file(), f"{name} is missing from {DOCS}"


def test_each_dossier_carries_the_same_marker():
    """The rot guard: deleting the caveat from any dossier fails here."""
    missing = [name for name in CAVEATED if MARKER not in _text(name)]
    assert not missing, (
        f"{MARKER!r} is missing from {missing}; the coverage caveat was removed "
        "or reworded without updating tests/test_dossier_coverage_caveats.py"
    )


def test_each_dossier_points_at_the_aggregate_label():
    for name in CAVEATED:
        assert "COVERAGE_LIMITS.md" in _text(name), (
            f"{name} states a coverage caveat but does not point at "
            "CONTEST/ROUND_01_2026-11-23/COVERAGE_LIMITS.md"
        )


def test_each_dossier_states_its_own_coverage_percentage():
    for name, pct in CAVEATED.items():
        caveat = [line for line in _text(name).splitlines() if MARKER in line]
        assert caveat, f"{name} has no line carrying {MARKER!r}"
        assert any(pct in line for line in caveat), (
            f"{name} carries the caveat but not its own coverage literal {pct}%"
        )


def test_no_dossier_introduces_a_divergent_tally():
    for name in CAVEATED:
        text = _text(name)
        for match in INVESTABLE_RE.finditer(text):
            assert match.group(1) == "0", (
                f"{name} contains {match.group(0)!r}: no dossier may claim a "
                f"positive INVESTABLE count (canonical: {CANONICAL_TALLY})"
            )
        for match in FULL_TALLY_RE.finditer(text):
            assert match.group(0) == CANONICAL_TALLY, (
                f"{name} contains a tally {match.group(0)!r} that differs from "
                f"the canonical {CANONICAL_TALLY!r}"
            )


def test_marker_is_defined_once_and_used_identically():
    """All three caveats must open with the same marker, not three variants."""
    for name in CAVEATED:
        lines = [line for line in _text(name).splitlines() if "Coverage caveat" in line]
        assert len(lines) == 1, f"{name} should carry exactly one caveat line, found {len(lines)}"
        assert lines[0].startswith(MARKER), (
            f"{name}'s caveat does not start with the shared marker {MARKER!r}: "
            f"{lines[0][:80]!r}"
        )
