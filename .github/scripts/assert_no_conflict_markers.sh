#!/bin/bash
# assert_no_conflict_markers.sh — Fail fast if staged files contain unresolved
# git conflict markers. Invoke this just before `git commit` in any auto-commit
# workflow to prevent the bug documented in issue #141 (stash-pop leaving
# <<<<<<< / ======= / >>>>>>> markers in JSON/data files that then get pushed
# straight to main).
#
# Usage (inside a workflow `run: |` block):
#     bash .github/scripts/assert_no_conflict_markers.sh \
#       || { echo "Aborting auto-commit"; exit 1; }
#
# Exits 0 if clean, 1 if any staged file contains conflict markers. On failure
# it unstages everything (`git reset HEAD`) so the caller can handle cleanup.

set -uo pipefail

PATTERN='^(<<<<<<<|=======$|>>>>>>>)'
_hits=""

while IFS= read -r f; do
    [ -z "$f" ] && continue
    [ -f "$f" ] || continue
    if git check-attr binary -- "$f" 2>/dev/null | grep -q 'binary: set'; then
        continue
    fi
    if grep -lE "$PATTERN" -- "$f" >/dev/null 2>&1; then
        _hits="${_hits}${f}\n"
    fi
done < <(git diff --cached --name-only --diff-filter=ACM 2>/dev/null)

if [ -n "$_hits" ]; then
    echo "::error::Refusing to commit — unresolved git conflict markers detected in:"
    printf "%b" "$_hits" | sed 's/^/::error::  /'
    echo "::error::See issue #141 for background. Unstaging and aborting."
    git reset HEAD -- . 2>/dev/null || true
    exit 1
fi

exit 0
