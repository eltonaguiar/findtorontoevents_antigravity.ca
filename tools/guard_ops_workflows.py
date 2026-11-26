#!/usr/bin/env python3
"""Fail CI when an automated commit deletes protected ops workflows.

Why this exists: commit 26dd4f9d ("Alpha Engine FAST ... [AUTO] [skip ci]", authored by
github-actions[bot]) deleted 573 files because it committed a stale index with
`git add -A`. Anything written between its checkout and its push - including the
`.github/workflows/ops-*` files that carry the SSH/runner operations - was silently
reverted. Nothing noticed until a human went looking.

This guard inspects a commit range with plain `git` (no API, so the 300-file cap on the
compare endpoint cannot hide a deletion) and exits 1 when

  * at least one protected file was deleted in the range, and
  * at least one commit in the range looks automated.

A human deleting the same file only produces a warning: that is a deliberate act.

Usage:
    python3 tools/guard_ops_workflows.py --before <sha> --after <sha> [--dry-run]
    python3 tools/guard_ops_workflows.py --before 26dd4f9df832^ --after 26dd4f9df832
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

WORKFLOW_DIR = ".github/workflows"
DEFAULT_PREFIX = "ops-"
PROTECTED_SUFFIXES = (".yml", ".yaml")

# Names/emails that identify an automation identity rather than a person.
BOT_NAME_SUFFIXES = ("[bot]",)
BOT_NAME_EXACT = {
    "github-actions",
    "github-actions-bot",
    "dependabot",
    "renovate",
    "codebuff",
    "copilot-swe-agent",
    "chatgpt-codex-connector",
}
BOT_EMAIL_MARKERS = ("[bot]@", "bot@users.noreply.github.com", "github-actions@github.com")
# Markers automation puts in its own commit subject.
AUTO_SUBJECT_MARKERS = ("[auto]", "[skip ci]", "[bot]", "automated")


def is_automated(name: str, email: str, subject: str) -> bool:
    """True when this commit looks machine-authored.

    Deliberately generous: a false positive only turns a silent revert into a red
    check, while a false negative is the bug this guard exists to catch.
    """
    name = (name or "").strip().lower()
    email = (email or "").strip().lower()
    subject = (subject or "").strip().lower()

    if name in BOT_NAME_EXACT:
        return True
    if any(name.endswith(suffix) for suffix in BOT_NAME_SUFFIXES):
        return True
    if any(marker in email for marker in BOT_EMAIL_MARKERS):
        return True
    if any(marker in subject for marker in AUTO_SUBJECT_MARKERS):
        return True
    return False


def is_protected(path: str, prefix: str = DEFAULT_PREFIX) -> bool:
    """True for `.github/workflows/<prefix>*.yml|yaml`, at the top level only."""
    path = path.strip()
    if not path.startswith(WORKFLOW_DIR + "/"):
        return False
    rest = path[len(WORKFLOW_DIR) + 1 :]
    if "/" in rest:
        return False
    return rest.startswith(prefix) and rest.endswith(PROTECTED_SUFFIXES)


def filter_protected(paths, prefix: str = DEFAULT_PREFIX):
    return sorted({p for p in paths if is_protected(p, prefix)})


def protected_deletions(before: str, after: str, prefix: str = DEFAULT_PREFIX, cwd=None):
    """Files removed between two commits (renames report the destination, not as D)."""
    out = _git(
        ["diff", "--diff-filter=D", "--name-only", "-z", before, after, "--", WORKFLOW_DIR],
        cwd=cwd,
    )
    return filter_protected([p for p in out.split("\0") if p], prefix)


def commits_in_range(before: str, after: str, cwd=None):
    """(sha, name, email, subject) for every commit in before..after."""
    out = _git(["log", "--format=%H%x1f%an%x1f%ae%x1f%s%x1e", f"{before}..{after}"], cwd=cwd)
    commits = []
    for record in out.split("\x1e"):
        record = record.strip("\n")
        if not record.strip():
            continue
        sha, name, email, subject = (record.split("\x1f") + ["", "", ""])[:4]
        commits.append((sha.strip(), name, email, subject))
    return commits


def automated_commits(commits):
    return [c for c in commits if is_automated(c[1], c[2], c[3])]


def _git(args, cwd=None) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def evaluate(before: str, after: str, prefix: str = DEFAULT_PREFIX, cwd=None):
    """Return (exit_code, lines) without printing - kept pure for the tests."""
    try:
        deletions = protected_deletions(before, after, prefix, cwd=cwd)
        commits = commits_in_range(before, after, cwd=cwd)
    except RuntimeError as exc:
        return 0, [f"::warning::guard-ops-workflows could not inspect {before}..{after}: {exc}"]

    if not deletions:
        return 0, [f"ok: no protected workflow deleted in {before}..{after}"]

    automated = automated_commits(commits)
    listing = "\n".join(f"  - {p}" for p in deletions)
    if not automated:
        return 0, [
            f"::warning::deleted protected workflow(s) in a human-authored range:\n{listing}",
        ]

    who = "\n".join(f"  - {sha[:12]} {name} <{email}>: {subject}" for sha, name, email, subject in automated)
    return 1, [
        f"::error::{len(deletions)} protected workflow(s) deleted by an automated commit:",
        listing,
        "automated commit(s) in range:",
        who,
        "This is the silent-revert pattern (a bot committing a stale index with `git add -A`).",
        "Restore the file(s) and fix the job so it commits only its own outputs.",
    ]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Fail when an automated commit deletes ops workflows.")
    parser.add_argument("--before", required=True, help="range start (exclusive)")
    parser.add_argument("--after", required=True, help="range end (inclusive)")
    parser.add_argument(
        "--prefix",
        default=DEFAULT_PREFIX,
        help=f"filename prefix protected under {WORKFLOW_DIR}/ (default: {DEFAULT_PREFIX})",
    )
    parser.add_argument("--dry-run", action="store_true", help="report but always exit 0")
    args = parser.parse_args(argv)

    if set(args.before) == {"0"}:
        print("ok: first push on this ref (before is all-zeroes) - nothing to compare")
        return 0

    code, lines = evaluate(args.before, args.after, args.prefix)
    for line in lines:
        print(line)
    if code != 0 and args.dry_run:
        print("dry-run: would have failed this run")
        return 0
    return code


if __name__ == "__main__":
    sys.exit(main())
