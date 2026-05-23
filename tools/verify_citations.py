#!/usr/bin/env python3
"""M-040: Hermes phantom-work guard — verify citations before swarm rounds.

Usage:
    python tools/verify_citations.py <prompt_file>

Reads a swarm prompt file and checks that every commit SHA and file path
cited in the prompt actually exists in the repo. Exits non-zero if any
citation is unresolvable (phantom work detected).

Motivation: Hermes sessions hallucinated phantom commits and files, then
ran 3+ swarm rounds on fabricated evidence. This guard must pass before
any /swarm call with 3+ rounds. See: memory project_hermes_phantom_work_2026-05-09
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


def _git_commit_exists(sha: str) -> bool:
    result = subprocess.run(
        ["git", "cat-file", "-e", sha],
        capture_output=True,
        cwd=ROOT,
    )
    return result.returncode == 0


def _extract_shas(text: str) -> list[str]:
    # Match 7-40 hex chars that look like commit SHAs (standalone words)
    return re.findall(r'\b([0-9a-f]{7,40})\b', text)


def _extract_file_paths(text: str) -> list[str]:
    # Match paths like audit_trail/foo.py, tools/bar.py, tests/test_x.py etc.
    # Require at least one directory separator to avoid matching random words
    return re.findall(
        r'\b((?:audit_trail|audit_dashboard|alpha_engine|tools|tests|reports|'
        r'scripts|docs|\.github|updates|cross_aggregation|data_pipeline)'
        r'[/\\][^\s\'"`,\)]+\.(?:py|yml|yaml|json|md|html|js|ts|sh))\b',
        text,
    )


def verify_prompt_file(prompt_path: Path) -> int:
    text = prompt_path.read_text(encoding="utf-8", errors="replace")

    errors: list[str] = []
    warnings: list[str] = []

    # 1. Check file paths
    paths_found = set(_extract_file_paths(text))
    for rel_path in sorted(paths_found):
        full = ROOT / rel_path.replace("\\", "/")
        if not full.exists():
            errors.append(f"  FILE NOT FOUND: {rel_path}")

    # 2. Check commit SHAs (only 10+ char ones to avoid false positives on short hex)
    shas_found = set(sha for sha in _extract_shas(text) if len(sha) >= 10)
    for sha in sorted(shas_found):
        if not _git_commit_exists(sha):
            errors.append(f"  COMMIT NOT FOUND: {sha}")

    # 3. Check PASSED test counts (heuristic: "N passed" in code blocks)
    passed_claims = re.findall(r'(\d+) passed', text)
    for claim in passed_claims:
        n = int(claim)
        if n > 200:
            warnings.append(f"  SUSPICIOUS test count: {n} passed — verify this is real")

    print(f"[verify_citations] Checking: {prompt_path.name}")
    print(f"  File paths found: {len(paths_found)}")
    print(f"  Commit SHAs found: {len(shas_found)}")

    if warnings:
        print("WARNINGS:")
        for w in warnings:
            print(w)

    if errors:
        print("ERRORS (phantom citations detected):")
        for e in errors:
            print(e)
        print(f"\n[verify_citations] FAIL — {len(errors)} phantom citation(s) in {prompt_path.name}")
        print("Fix the prompt before running /swarm with 3+ rounds.")
        return 1

    print(f"[verify_citations] PASS — all citations verified for {prompt_path.name}")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <prompt_file>")
        return 2

    prompt_path = Path(sys.argv[1])
    if not prompt_path.is_absolute():
        prompt_path = ROOT / prompt_path

    if not prompt_path.exists():
        print(f"[verify_citations] ERROR: prompt file not found: {prompt_path}")
        return 2

    return verify_prompt_file(prompt_path)


if __name__ == "__main__":
    sys.exit(main())
