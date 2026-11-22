"""Cross-document tally consistency (2026-11-22).

Why this exists
    Three edge-research documents carried three different headline tallies for
    the SAME 14-row set: doc 23 printed 9 NOT_INVESTABLE / 2 BLOCKED / 3 UNKNOWN,
    doc 15 and doc 22 printed 8 NOT_INVESTABLE / 6 UNKNOWN, and doc 23's own table
    contained 10 NOT_INVESTABLE / 2 UNKNOWN. A headline that is subtracted rather
    than counted is the same defect class as a cost figure quoted without its
    artifact, so it gets the same treatment: a machine check.

    The contract enforced here:
      1. Every one of docs 15, 22 and 23 contains exactly one line matching
         ``TALLY: <a> INVESTABLE / <b> NOT_INVESTABLE / <c> UNKNOWN (<n> rows)``.
      2. The three lines are character-identical.
      3. a + b + c == n.
      4. n equals the number of rows in doc 23's final-accounting table, counted
         from the table itself (so the total cannot drift from the list).
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DOCS = {
    "15": ROOT / "docs" / "edge_research" / "15_PROGRAMME_SCOREBOARD_2026-11-22.md",
    "22": ROOT / "docs" / "edge_research" / "22_FINAL_SYNTHESIS_2026-11-22.md",
    "23": ROOT / "docs" / "edge_research" / "23_DEFINITIVE_ANSWER_2026-11-22.md",
}

TALLY_RE = re.compile(
    r"TALLY:\s*(\d+)\s+INVESTABLE\s*/\s*(\d+)\s+NOT_INVESTABLE\s*/\s*(\d+)\s+UNKNOWN\s*"
    r"\((\d+)\s+rows\)"
)
# doc 23 final-accounting table row: "| 3 | Equity breakout | **NOT_INVESTABLE** | ... |"
ROW_RE = re.compile(r"^\|\s*(\d+)\s*\|[^|]+\|\s*\**([A-Z_]+)\**")


def _tallies(path: Path):
    return TALLY_RE.findall(path.read_text())


def _doc23_rows():
    text = DOCS["23"].read_text()
    rows = []
    for line in text.splitlines():
        m = ROW_RE.match(line)
        if m:
            rows.append((int(m.group(1)), m.group(2)))
    return rows


@pytest.mark.parametrize("key", sorted(DOCS))
def test_each_document_has_exactly_one_tally_line(key):
    found = _tallies(DOCS[key])
    assert len(found) == 1, (
        f"doc {key} should carry one TALLY line, found {len(found)}: {found}")


def test_the_three_tally_lines_are_identical():
    lines = {}
    for key, path in DOCS.items():
        text = path.read_text()
        m = TALLY_RE.search(text)
        assert m, f"doc {key} has no TALLY line"
        lines[key] = m.group(0)
    assert len(set(lines.values())) == 1, f"tally lines disagree: {lines}"


def test_tally_adds_up_to_its_row_count():
    a, b, c, n = map(int, TALLY_RE.search(DOCS["23"].read_text()).groups())
    assert a + b + c == n, f"{a}+{b}+{c} != {n}"


def test_tally_row_count_equals_the_enumerated_doc23_table():
    rows = _doc23_rows()
    assert rows, "could not parse any rows from doc 23's final-accounting table"
    # the table is numbered 1..N with no gaps and no repeats
    assert [i for i, _ in rows] == list(range(1, len(rows) + 1)), (
        f"doc 23 table numbering is not 1..N: {[i for i, _ in rows]}")
    n = int(TALLY_RE.search(DOCS["23"].read_text()).group(4))
    assert len(rows) == n, (
        f"TALLY says {n} rows but doc 23 enumerates {len(rows)}")


def test_tally_counts_equal_the_doc23_table_verdicts():
    """The counted tally must equal what the table actually says, per bucket."""
    rows = _doc23_rows()
    verdicts = [v for _, v in rows]
    assert verdicts.count("INVESTABLE") == 0, "no row may be INVESTABLE"
    expected = {
        "INVESTABLE": 0,
        "NOT_INVESTABLE": verdicts.count("NOT_INVESTABLE"),
        "UNKNOWN": verdicts.count("UNKNOWN"),
    }
    a, b, c, n = map(int, TALLY_RE.search(DOCS["23"].read_text()).groups())
    assert (a, b, c) == (expected["INVESTABLE"], expected["NOT_INVESTABLE"],
                        expected["UNKNOWN"]), (
        f"TALLY {a}/{b}/{c} disagrees with the table {expected}")


def test_commodity_rows_are_counted_once_each():
    """The commodity family may not be double-counted as blocked AND unknown."""
    rows = _doc23_rows()
    names = [line for line in DOCS["23"].read_text().splitlines()
             if ROW_RE.match(line) and "Commodity" in line]
    assert len(names) == 2, (
        f"expected exactly 2 commodity rows (momentum family + term-structure carry), "
        f"found {len(names)}: {[n[:60] for n in names]}")


# ---------------------------------------------------------------------------
# DEFECT (2026-11-22): the invariant above was enforced over a HARDCODED list of
# three documents. ``docs/EDGE_CANDIDATES_2026-11-22.md`` carried the stale
# pre-reconciliation ``0/8/6`` and nothing failed, because no test ever looked at
# it. An invariant enforced only where someone remembered to list a path is the
# same defect class as the subtracted tally: so discovery replaces the list.
#
# Historical-tally convention (the opt-out): a line that quotes an OLD tally as
# history is exempt if it
#   * carries the explicit marker ``TALLY-HISTORICAL-OK``, or
#   * is a blockquote (``> ...``) - correction notices are conventionally quoted, or
#   * contains a frozen history cue (see HISTORY_CUE_RE) *and* lives in a document
#     that also states the settled tally.
# The marker is the convention to use going forward; the other two rules exist so
# the already-written correction notes in docs 15/22/23 need no edit. The third
# rule is deliberately gated on the document already being correct, so a document
# whose ONLY figure is stale can never be excused by a cue word like "unchanged".
# ---------------------------------------------------------------------------

SETTLED = ("0", "10", "4")
# Loose claim pattern for DISCOVERY - deliberately no "(N rows)" suffix, so a
# stale figure is found even when it is not written in the canonical form.
CLAIM_RE = re.compile(
    r"(\d+)\s+INVESTABLE\s*/\s*(\d+)\s+NOT_INVESTABLE\s*/\s*(\d+)\s+UNKNOWN")
SEARCH_DIR = ROOT / "docs"
HISTORICAL_MARKER = "TALLY-HISTORICAL-OK"
HISTORY_CUE_RE = re.compile(
    r"(?i)\b(unchanged|supersedes|previously|earlier|first version|"
    r"recompute[sd]?|corrected)\b")


def _tally_documents():
    """Every markdown document under docs/ that states a tally - discovered, not listed."""
    return sorted(p for p in SEARCH_DIR.rglob("*.md")
                  if CLAIM_RE.search(p.read_text(errors="replace")))


def _claims(path: Path):
    out = []
    for no, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
        for m in CLAIM_RE.finditer(line):
            out.append((no, line, m))
    return out


def _is_historical(line: str, canonical_in_document: bool) -> bool:
    if HISTORICAL_MARKER in line:
        return True
    if line.lstrip().startswith(">"):
        return True
    return bool(canonical_in_document and HISTORY_CUE_RE.search(line))


@pytest.mark.parametrize("path", _tally_documents(),
                         ids=lambda p: str(p.relative_to(ROOT)))
def test_every_document_that_states_a_tally_states_the_settled_one(path):
    claims = _claims(path)
    canonical = [c for c in claims if c[2].groups() == SETTLED]
    assert canonical, (
        f"{path.relative_to(ROOT)} states a tally but never the settled {SETTLED}: "
        f"{[(no, line.strip()[:80]) for no, line, _ in claims]}")
    stale = [(no, line.strip()[:100]) for no, line, m in claims
             if m.groups() != SETTLED and not _is_historical(line, True)]
    assert not stale, (
        f"{path.relative_to(ROOT)} carries a stale tally outside a historical "
        f"context: {stale}")


def test_discovery_covers_the_three_settled_documents():
    """Guards against the glob silently matching nothing."""
    missing = set(DOCS.values()) - set(_tally_documents())
    assert not missing, f"discovery missed {missing}"


@pytest.mark.parametrize("line,canonical,expected", [
    ("TALLY: 0 INVESTABLE / 8 NOT_INVESTABLE / 6 UNKNOWN (14 rows)", True, False),
    ("TALLY: 0 INVESTABLE / 8 NOT_INVESTABLE / 6 UNKNOWN (14 rows) TALLY-HISTORICAL-OK", False, True),
    ("> previously printed `0 INVESTABLE / 8 NOT_INVESTABLE / 6 UNKNOWN`", False, True),
    ("Tally unchanged: 0 INVESTABLE / 8 NOT_INVESTABLE / 6 UNKNOWN", True, True),
    ("Tally unchanged: 0 INVESTABLE / 8 NOT_INVESTABLE / 6 UNKNOWN", False, False),
])
def test_historical_classifier(line, canonical, expected):
    """The opt-out must be narrow: a cue word cannot excuse a lone stale figure."""
    assert _is_historical(line, canonical) is expected
