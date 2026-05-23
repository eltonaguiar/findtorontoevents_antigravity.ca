#!/bin/bash
# safe_commit_push.sh — Robust commit + push with exponential backoff
# Usage: safe_commit_push.sh "commit message" [files_to_add...]
#
# Handles: pull conflicts, push race conditions, exponential backoff
# Designed for GitHub Actions where many workflows push to main concurrently.

set -euo pipefail

MAX_RETRIES=5
INITIAL_BACKOFF=3  # seconds
GIT_NET_TIMEOUT=60  # seconds — kill hanging git network ops (pull/push) so we actually retry
                     # instead of burning the job's timeout-minutes waiting on one hung call.

commit_msg="$1"
shift
files_to_add=("$@")

if [ ${#files_to_add[@]} -eq 0 ]; then
    echo "ERROR: No files specified to commit"
    exit 1
fi

git config user.name "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"

# Auto-inject PAT into origin URL if available (fixes 403 for workflows without explicit token)
_TOKEN="${TOKEN_FOR_PUSH:-${GH_PAT:-}}"
if [ -n "$_TOKEN" ] && [ -n "${GITHUB_REPOSITORY:-}" ]; then
    git remote set-url origin "https://x-access-token:${_TOKEN}@github.com/${GITHUB_REPOSITORY}.git" 2>/dev/null || true
fi

# Helper: sanitize output to prevent token leakage in logs
_sanitize() {
    if [ -n "$_TOKEN" ]; then
        sed "s/${_TOKEN}/***TOKEN***/g"
    else
        cat
    fi
}

# Stage files
for f in "${files_to_add[@]}"; do
    git add "$f" 2>/dev/null || true
done

# Check if anything to commit
if git diff --cached --quiet; then
    echo "No changes to commit"
    exit 0
fi

# Stash staged changes so we can pull cleanly
git stash 2>/dev/null || true

backoff=$INITIAL_BACKOFF
for attempt in $(seq 1 $MAX_RETRIES); do
    echo "=== Push attempt $attempt/$MAX_RETRIES ==="

    # Fresh pull before each attempt (bounded by GIT_NET_TIMEOUT to avoid hangs)
    timeout "${GIT_NET_TIMEOUT}" git pull --rebase --no-recurse-submodules origin main 2>&1 | _sanitize || {
        echo "Rebase failed or timed out, trying merge strategy..."
        git rebase --abort 2>/dev/null || true
        timeout "${GIT_NET_TIMEOUT}" git pull --no-rebase --no-recurse-submodules -X ours origin main 2>&1 | _sanitize || true
    }

    # Restore our stashed changes
    if [ "$attempt" -eq 1 ]; then
        git stash pop 2>/dev/null || {
            echo "Stash pop conflict — keeping our generated files"
            # BUG FIX 2026-04-05 (mirrors 108b99aa85, 597fb2f17a): the caller-supplied
            # files_to_add[@] are the workflow's freshly-generated outputs. We MUST take
            # --ours (the stashed = locally generated version), NOT --theirs (origin's
            # stale pre-run version). Pre-fix this silently reverted every caller's
            # generator output on any stash-pop conflict. Remaining conflicts (files we
            # did NOT generate) still use --theirs as a safe default for shared data.
            for f in "${files_to_add[@]}"; do
                git checkout --ours -- "$f" 2>/dev/null || git checkout --theirs -- "$f" 2>/dev/null || true
            done
            git diff --name-only --diff-filter=U 2>/dev/null | xargs -r git checkout --theirs -- 2>/dev/null || true
            git diff --name-only --diff-filter=U 2>/dev/null | xargs -r git add 2>/dev/null || true
            git stash drop 2>/dev/null || true
        }
    fi

    # Re-stage our target files and commit
    for f in "${files_to_add[@]}"; do
        git add "$f" 2>/dev/null || true
    done

    if git diff --cached --quiet; then
        echo "No changes after pull — already up to date"
        exit 0
    fi

    # BUG FIX (issue #141): refuse to commit if any staged file contains unresolved
    # git conflict markers. The stash-pop recovery path above can leave <<<<<<< / =======
    # / >>>>>>> markers inside JSON/data files (e.g. ai_challenge_summary.json,
    # stock_prices.json, swarm_weights.json) and the auto-commit would push broken data
    # straight to main. If markers are found, unstage, drop the stash, and exit non-zero
    # so the workflow fails loudly instead of silently corrupting the default branch.
    _marker_hits=""
    while IFS= read -r _staged; do
        [ -z "$_staged" ] && continue
        [ -f "$_staged" ] || continue
        if git check-attr binary -- "$_staged" 2>/dev/null | grep -q 'binary: set'; then
            continue
        fi
        if grep -lE '^(<<<<<<<|=======$|>>>>>>>)' -- "$_staged" >/dev/null 2>&1; then
            _marker_hits="${_marker_hits}${_staged}\n"
        fi
    done < <(git diff --cached --name-only --diff-filter=ACM 2>/dev/null)
    if [ -n "$_marker_hits" ]; then
        echo "::error::Refusing to commit — unresolved git conflict markers detected:"
        printf "%b" "$_marker_hits" | sed 's/^/::error::  /'
        git reset HEAD -- . 2>/dev/null || true
        git stash drop 2>/dev/null || true
        exit 1
    fi

    # Only commit if HEAD doesn't already have our message (avoid duplicate commits)
    git diff --cached --quiet || git commit -m "$commit_msg" 2>/dev/null || true

    # Push — capture exit code for retry logic (bounded so hangs don't burn job time)
    push_output=$(timeout "${GIT_NET_TIMEOUT}" git push origin main 2>&1) && push_rc=0 || push_rc=$?
    echo "$push_output" | _sanitize

    if [ $push_rc -eq 0 ]; then
        echo "Pushed successfully on attempt $attempt"
        exit 0
    fi

    # Detect fatal auth errors — no point retrying
    if echo "$push_output" | grep -qiE "403|401|Authentication|Permission denied"; then
        echo "ERROR: Authentication/permission failure — aborting (no retry)"
        exit 1
    fi

    echo "Push failed on attempt $attempt, backing off ${backoff}s..."
    sleep $backoff
    backoff=$((backoff * 2))  # exponential backoff: 3, 6, 12, 24, 48
done

echo "ERROR: All $MAX_RETRIES push attempts failed"
exit 1
