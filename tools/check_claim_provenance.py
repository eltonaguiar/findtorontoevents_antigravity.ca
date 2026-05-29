#!/usr/bin/env python3
"""
check_claim_provenance.py — flag UNSOURCED evidence claims in PR bodies, diffs,
docs, or code comments, so a change cannot justify itself with fabricated or
unverifiable evidence.

provenance-checker: ignore-file
(^ this file describes the patterns, so it opts itself out. Two opt-outs exist:
a file-level "provenance-checker: ignore-file" marker, and a per-line
"provenance-allow" directive. Fenced ``` code blocks are skipped automatically.)

Motivated by the 2026-05-29 swarm PR review, which found 5 open PRs asserting
evidence that does not exist:
  - #30  "3 of 23 models" coverage metric — verifiably false
  - #11  "Kwas et al. (2024) ECB" — no DOI / link / paper id anywhere
  - #13  "Ring-2.6-1T recommended this exact approach" — no swarm_runs/ output
  - #21  "QW-2 ETF threshold" / BTC death-zone hours "peer-agent verified" — no data file

This is the machine version of the metric-honesty-tiers.json ⛔ DISPUTED rule:
a quantitative or authority claim is trustworthy only if a reproducer / source
sits next to it. Three claim classes are detected:

  ACADEMIC    "<Name> et al. (20XX)", "<paper/study/ECB/journal> ..."   -> needs DOI/arXiv/URL
  ENDORSEMENT "recommended/verified/confirmed by <swarm|peer|model>"    -> needs swarm_runs//reports/ path or command
  PERFORMANCE "PF/WR/Sharpe/win-rate <number>"                          -> needs source .json/.md / reproducer / SQL

For each match we scan a +/-window for a PROVENANCE token (http(s)://, doi.org,
arxiv, reports/, swarm_runs/, *.json, *.md, "reproducer", "SELECT ", "python ").
No token in range -> UNSOURCED.

Usage:
    python tools/check_claim_provenance.py <file> [<file> ...]
    python tools/check_claim_provenance.py --pr 11           # gh pr view+diff
    python tools/check_claim_provenance.py --text "Ring-2.6-1T recommended X"
    python tools/check_claim_provenance.py --json <file>
    python tools/check_claim_provenance.py --fail-on endorsement,academic <file>   # exit 1 if those classes are unsourced

Exit code is 1 when any class named in --fail-on (default: academic,endorsement)
has at least one UNSOURCED hit — suitable for a CI / pre-PR gate.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

WINDOW = 300  # chars on each side to search for provenance

PROVENANCE = re.compile(
    r"(https?://|doi\.org|arxiv|10\.\d{4,}/|reports/|swarm_runs/|updates/|"
    r"\b[\w/().-]+\.(?:json|md|csv|parquet)\b|reproducer|repro:|"
    r"\bSELECT\b|\bpython[03]?\b|pf_registry|money_ready_verdict)",
    re.IGNORECASE,
)

CLAIM_PATTERNS = {
    # Author-year academic citations and study/paper/institution references.
    "academic": re.compile(
        r"(\b[A-Z][a-zA-Z]+(?:\s+(?:&|and|et\s+al\.?))[^.\n]{0,40}\(?(?:19|20)\d{2}\)?"
        r"|\b(?:per|cite[sd]?|according to)\s+[^.\n]{0,60}\b(?:paper|study|research|journal|ECB|Fed|working paper)\b"
        r"|\bKwas\b[^.\n]{0,40})",
    ),
    # Authority / endorsement: "recommended/verified by <swarm|peer|named model>".
    "endorsement": re.compile(
        r"((?:recommended|verified|confirmed|endorsed|suggested|validated|approved|blessed)\s+by\s+[^.\n]{0,50}"
        r"|peer[- ]agent[- ]?verified"
        r"|swarm[- ](?:verified|confirmed|recommended|consensus)"
        r"|\b(?:Ring|Grok|Claude|Gemini|Kimi|Qwen|DeepSeek|Mercury|GPT|Llama|Nemotron|Mimo)[\w.\-]*\s+"
        r"(?:recommended|verified|confirmed|suggested|says|advises|endorses)\b)",
        re.IGNORECASE,
    ),
    # Performance assertions with a number attached.
    "performance": re.compile(
        r"\b(?:PF|profit[- ]?factor|WR|win[- ]?rate|Sharpe|Sortino|MDD|max[- ]?drawdown|CAGR)\b"
        r"[^.\n]{0,15}?\d[\d.,]*\s*%?",
        re.IGNORECASE,
    ),
}

SEVERITY = {"academic": "high", "endorsement": "high", "performance": "medium"}


@dataclass
class Finding:
    source: str
    line: int
    claim_class: str
    severity: str
    snippet: str
    sourced: bool


def _line_of(text: str, idx: int) -> int:
    return text.count("\n", 0, idx) + 1


# Files that describe/quote the patterns (audit reports, this checker itself) are not
# making claims — they discuss them. Opt out with a file-level marker, blank out fenced
# code blocks, and honor a per-line directive. This kills the self-referential
# false-positives (a consensus report quoting "Ring-2.6-1T recommended", the checker's
# own regex examples) without weakening detection on real PR bodies / code.
IGNORE_FILE_MARKER = "provenance-checker: ignore-file"
ALLOW_LINE_MARKER = "provenance-allow"
_FENCE = re.compile(r"```.*?```", re.S)


def _blank_fences(text: str) -> str:
    # replace fenced code blocks with same-length newline-preserving blanks (keeps line numbers)
    return _FENCE.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)


def scan_text(text: str, source: str) -> list[Finding]:
    if IGNORE_FILE_MARKER in text:
        return []
    lines = text.splitlines()
    scanned = _blank_fences(text)
    out: list[Finding] = []
    for cls, pat in CLAIM_PATTERNS.items():
        for m in pat.finditer(scanned):
            s, e = m.start(), m.end()
            ln = _line_of(text, s)
            if ALLOW_LINE_MARKER in (lines[ln - 1] if 0 < ln <= len(lines) else ""):
                continue
            window = text[max(0, s - WINDOW): e + WINDOW]
            sourced = bool(PROVENANCE.search(window))
            snippet = re.sub(r"\s+", " ", m.group(0)).strip()[:120]
            out.append(Finding(source, ln, cls, SEVERITY[cls], snippet, sourced))
    return out


def gather_pr_text(pr: str) -> tuple[str, str]:
    body = subprocess.run(
        ["gh", "pr", "view", pr, "--json", "title,body", "-q", ".title + \"\\n\" + .body"],
        capture_output=True, text=True,
    ).stdout
    diff = subprocess.run(["gh", "pr", "diff", pr], capture_output=True, text=True).stdout
    # only consider added lines + the body for diffs
    added = "\n".join(l[1:] for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++"))
    return body, added


def main() -> None:
    ap = argparse.ArgumentParser(description="Flag unsourced evidence claims.")
    ap.add_argument("files", nargs="*", help="files to scan")
    ap.add_argument("--pr", help="GitHub PR number (scans title+body+added diff lines)")
    ap.add_argument("--text", help="scan a literal string")
    ap.add_argument("--json", dest="as_json", action="store_true")
    ap.add_argument("--fail-on", default="academic,endorsement",
                    help="comma list of classes that exit 1 when unsourced (default academic,endorsement)")
    ap.add_argument("--show-sourced", action="store_true", help="also list claims that DO have provenance")
    args = ap.parse_args()

    findings: list[Finding] = []
    if args.text:
        findings += scan_text(args.text, "<text>")
    if args.pr:
        body, added = gather_pr_text(args.pr)
        findings += scan_text(body, f"PR#{args.pr}:body")
        findings += scan_text(added, f"PR#{args.pr}:diff+")
    for f in args.files:
        p = Path(f)
        if not p.is_file():
            print(f"[warn] not a file: {f}", file=sys.stderr)
            continue
        findings += scan_text(p.read_text(encoding="utf-8", errors="replace"), f)

    unsourced = [f for f in findings if not f.sourced]
    fail_classes = {c.strip() for c in args.fail_on.split(",") if c.strip()}
    fail_hits = [f for f in unsourced if f.claim_class in fail_classes]

    if args.as_json:
        print(json.dumps({
            "n_claims": len(findings),
            "n_unsourced": len(unsourced),
            "fail": bool(fail_hits),
            "findings": [asdict(f) for f in (findings if args.show_sourced else unsourced)],
        }, indent=2))
    else:
        shown = findings if args.show_sourced else unsourced
        if not shown:
            print("✓ no unsourced claims found")
        for f in sorted(shown, key=lambda x: (not x.sourced, x.severity != "high", x.source, x.line)):
            tag = "SOURCED  " if f.sourced else "UNSOURCED"
            print(f"  [{tag}] {f.severity:<6} {f.claim_class:<11} {f.source}:{f.line}  «{f.snippet}»")
        print(f"\n{len(findings)} claims, {len(unsourced)} unsourced "
              f"({len(fail_hits)} in fail classes: {sorted(fail_classes)})")

    sys.exit(1 if fail_hits else 0)


if __name__ == "__main__":
    main()
