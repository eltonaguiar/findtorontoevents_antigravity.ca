#!/usr/bin/env python3
"""Lint the audit-review dossiers: fixed 8-heading shape + a source marker for every number.

The contract (plans/2026-11-22-audit-review-and-gha-qa-program.md §2a):
  1. every number is covered by a source marker `[SRC: <path>:<line>]`, `[SRC: manifest:<key>]`,
     `[SRC: <url>]`, or the literal token `UNMEASURED`;
  2. a `## Provenance` footer names model, prompt file, snapshot id;
  3. the 8 section headings appear verbatim so documents diff against each other;
  4. the dossier answers "name the single number least likely to survive re-measurement".

Coverage rule (documented, not implicit): a marker opens a region that extends to the next marker
or the next heading. Every number inside a region is attributed to that region's marker. Because a
region never crosses a heading, each section must open its claims with its own marker: a section
whose numbers appear before its first marker fails. That is what makes "zero bare numbers"
meaningful per section rather than per file.

Exit code 0 = clean, 1 = violations.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HEADINGS = [
    "## 1 Identity",
    "## 2 What the class is",
    "## 3 Measured state",
    "## 4 Contradictions",
    "## 5 Data integrity",
    "## 6 Cost reality",
    "## 7 What would change the verdict",
    "## 8 Blunt answer",
    "## Provenance",
]

UNMEASURED = "UNMEASURED"
DOSSIER_NAME_RE = re.compile(r"^\d{2}_[A-Z_]+\.md$")
# shared documents that are not dossiers (no fixed 8-section shape expected)
NON_DOSSIER_NAMES = {"00_SURFACE_BASELINE.md", "README.md", "REJECTED.md", "BLOCKERS.md"}

SRC_RE = re.compile(r"\[SRC:\s*[^\]]+\]")
NUM_RE = re.compile(r"(?<![\w./-])\d[\d,]*(?:\.\d+)?(?:[eE][+-]?\d+)?%?")
CODE_SPAN_RE = re.compile(r"`[^`]*`")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2})?)?")
HEX_RE = re.compile(r"\b[0-9a-f]{7,64}\b")
HTML_ENTITY_RE = re.compile(r"&#?\w+;")
MD_STRUCT_RE = [
    re.compile(r"^\s{0,3}#{1,6}\s"),
    re.compile(r"^\s*\d+\.\s"),
    re.compile(r"^\s*\|?\s*:?-{2,}"),
    re.compile(r"^\s*\[\^?\d+\]:"),
]
NAME_TOKENS = {
    "audit2", "audit3", "q1", "q2", "q3", "q4", "q5", "q6", "q7", "q8", "q9", "q10",
    "r1", "r2", "r3", "r4", "r5", "r6", "r7", "r8", "r9", "r10", "r11", "r12",
    "p0", "p1", "p2", "s1", "s2", "t2", "m1b", "btc4h", "4h", "1h", "1d", "24h", "30d", "90d",
    "sha256", "utf8", "utf-8", "h1", "h2", "v1", "v2",
}


def _strip_non_claims(line: str) -> str:
    s = CODE_SPAN_RE.sub(" ", line)
    s = SRC_RE.sub(" ", s)
    s = DATE_RE.sub(" ", s)
    s = HTML_ENTITY_RE.sub(" ", s)
    s = HEX_RE.sub(" ", s)
    return s


def _numbers_in(line: str) -> list[str]:
    out = []
    for m in NUM_RE.finditer(_strip_non_claims(line)):
        tok = m.group(0)
        core = tok.rstrip("%").replace(",", "").lower()
        if core in NAME_TOKENS:
            continue
        if re.fullmatch(r"\d{4}", core) and 1900 <= int(core) <= 2100:
            continue
        out.append(tok)
    return out


def bare_numbers(lines: list[str]) -> list[tuple[int, str]]:
    """(lineno, token) for every number that no preceding marker in its section covers."""
    out: list[tuple[int, str]] = []
    in_fence = False
    marker_seen = False
    for i, line in enumerate(lines, 1):
        stripped = line.rstrip("\n")
        if stripped.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if stripped.startswith("#"):
            marker_seen = False  # a region never crosses a heading
            continue
        if SRC_RE.search(stripped) or UNMEASURED in stripped:
            marker_seen = True
            continue
        if any(p.match(stripped) for p in MD_STRUCT_RE):
            continue
        if marker_seen:
            continue
        for tok in _numbers_in(stripped):
            out.append((i, tok))
    return out


def check_headings(text: str) -> list[str]:
    present = [ln.strip() for ln in text.splitlines() if ln.strip().startswith("## ")]
    errs = []
    for h in HEADINGS:
        if not any(p == h or p.startswith(h + " ") for p in present):
            errs.append(f"missing heading: {h!r}")
    return errs


def check_provenance(text: str) -> list[str]:
    m = re.search(r"## Provenance(.*)\Z", text, re.S)
    if not m:
        return ["no ## Provenance footer"]
    body = m.group(1)
    return [f"Provenance footer missing {f!r}" for f in ("model", "prompt", "snapshot")
            if not re.search(rf"\b{f}\b", body, re.I)]


def check_least_survivable(text: str) -> list[str]:
    if not re.search(r"least (likely to )?surviv", text, re.I):
        return ["does not answer 'least survivable number' (required before publish)"]
    return []


def lint_text(text: str, name: str = "<text>", require_least_survivable: bool = True) -> list[str]:
    errs = check_headings(text)
    errs += check_provenance(text)
    if require_least_survivable:
        errs += check_least_survivable(text)
    for lineno, tok in bare_numbers(text.splitlines()):
        errs.append(f"{name}:{lineno}: bare number {tok!r} before any [SRC: ...] marker "
                    f"in its section, and not UNMEASURED")
    return errs


def lint_dir(path: Path, require_least_survivable: bool = True) -> dict[str, list[str]]:
    results: dict[str, list[str]] = {}
    files = ([path] if path.is_file()
             else sorted(p for p in path.glob("*.md")
                         if DOSSIER_NAME_RE.match(p.name) and p.name not in NON_DOSSIER_NAMES))
    for f in files:
        results[str(f)] = lint_text(f.read_text(), f.name, require_least_survivable)
    return results


def main(argv: list[str]) -> int:
    target = Path(argv[1]) if len(argv) > 1 else Path("docs/audit_review_2026-11-22")
    results = lint_dir(target)
    bad = 0
    for name, errs in results.items():
        if errs:
            bad += 1
            print(f"FAIL {name}")
            for e in errs:
                print("  -", e)
        else:
            print(f"ok   {name}")
    print(f"\n{len(results) - bad}/{len(results)} clean")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
