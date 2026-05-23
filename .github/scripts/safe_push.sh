#!/bin/bash
# safe_push.sh — Push-only exponential backoff (for workflows that already add+commit)
# Usage: bash .github/scripts/safe_push.sh [remote_url]
#
# If remote_url is provided, pushes to that URL instead of "origin main".
# Handles: pull --rebase before push, exponential backoff on failure
# Designed for GitHub Actions where many workflows push to main concurrently.
# For full add+commit+push, use safe_commit_push.sh instead.

set -uo pipefail

# Cancellation fix 2026-05-06: Many workflows were cancelled because
# safe_push.sh's git operations hung past the runner timeout, causing GHA to
# kill the job AFTER all work was done (commit succeeded, just push hung).
# Key fixes:
#   1. GIT_NET_TIMEOUT reduced to 90s — fail faster, let retries work
#   2. Deepen fetch capped at 90s — exit early if it stalls (don't burn clock)
#   3. Fail-fast if deepen times out — shallow repos can't rebase anyway
#   4. Reduce MAX_RETRIES to 8 — the old 15 was burning too many runner minutes
MAX_RETRIES=8
INITIAL_BACKOFF=3  # seconds
MAX_BACKOFF_SLEEP=60  # cap per sleep so one run does not wait many minutes idle
GIT_NET_TIMEOUT=90   # seconds — kill hanging git pull/push so we retry instead of
                     # burning the job's timeout-minutes waiting on one stuck call.
DEEPEN_TIMEOUT=90    # seconds — git fetch --deepen=N must not burn the whole run

REMOTE_URL="${1:-}"

# --- Early exit: nothing to push ---
LOCAL_HEAD=$(git rev-parse HEAD 2>/dev/null || echo "")
REMOTE_HEAD=$(git rev-parse origin/main 2>/dev/null || echo "")
if [ -n "$LOCAL_HEAD" ] && [ "$LOCAL_HEAD" = "$REMOTE_HEAD" ]; then
    echo "Nothing to push — local HEAD matches origin/main"
    exit 0
fi

# --- Auth token injection ---
# Auto-inject PAT into origin URL if available (fixes 403 for workflows without explicit token)
_TOKEN="${TOKEN_FOR_PUSH:-${GH_PAT:-}}"
if [ -z "$REMOTE_URL" ] && [ -n "$_TOKEN" ] && [ -n "${GITHUB_REPOSITORY:-}" ]; then
    git remote set-url origin "https://x-access-token:${_TOKEN}@github.com/${GITHUB_REPOSITORY}.git" 2>/dev/null || true
    echo "  (remote URL updated with push token)"
fi

# --- Token auth validation (fail-fast if token is invalid/expired) ---
# Without this, an invalid token causes git push to hang indefinitely waiting for
# auth instead of failing fast. Validates in ~15s max (curl --max-time).
# Skipped when REMOTE_URL is provided (custom URL may use different credentials).
_AUTH_TMP=$(mktemp 2>/dev/null || echo "/tmp/auth_check_$$.json")
chmod 600 "$_AUTH_TMP" 2>/dev/null || true
if [ -z "$REMOTE_URL" ] && [ -n "$_TOKEN" ] && [ -n "${GITHUB_REPOSITORY:-}" ]; then
    _auth_check=$(curl -s --max-time 15 -o "$_AUTH_TMP" -w "%{http_code}" \
        -H "Authorization: Bearer $_TOKEN" \
        -H "Accept: application/vnd.github+json" \
        "https://api.github.com/repos/${GITHUB_REPOSITORY}" 2>/dev/null || echo "000")
    if [ "$_auth_check" != "200" ]; then
        _err_msg=$(cat "$_AUTH_TMP" 2>/dev/null | python3 -c "
import json, sys, os
code=os.environ.get('_auth_check','?')
try:
    d=json.load(sys.stdin)
    msg=d.get('message', d.get('error', 'unknown error'))
    print(f'Token validation failed (HTTP {code}): {msg}')
except:
    print(f'Token validation failed (HTTP {code})')
" 2>/dev/null || echo "Token validation failed (HTTP $_auth_check)")
        echo "ERROR: $_err_msg"
        echo "  → Check that GH_PAT secret is set and the token has 'repo' scope (full push access)."
        echo "  → If using github.token directly, verify the workflow has 'permissions: contents: write'."
        echo "  → A 401/403 means the token is invalid or expired. A 404 means the repo path is wrong."
        rm -f "$_AUTH_TMP" 2>/dev/null || true
        exit 1
    fi
    echo "  (token auth validated OK)"
fi
rm -f "$_AUTH_TMP" 2>/dev/null || true

# Avoid submodule recursion (broken .gitmodules entries break pull in post-checkout too)
git config pull.recurseSubmodules false 2>/dev/null || true
git config fetch.recurseSubmodules false 2>/dev/null || true

# Helper: sanitize output to prevent token leakage in logs
_sanitize() {
    if [ -n "$_TOKEN" ]; then
        sed "s/${_TOKEN}/***TOKEN***/g"
    else
        cat
    fi
}

# Shallow checkouts make pull --rebase flaky on high-churn main; deepen once.
# FIX 2026-05-06: Use DEEPEN_TIMEOUT and fail fast — don't burn runner clock.
# If deepen times out, exit the script immediately so the workflow fails cleanly
# (conclusion=failure) rather than getting cancelled (conclusion=cancelled) by GHA.
_SHALLOW_FILE="$(git rev-parse --git-dir 2>/dev/null)/shallow"
if [ -f "$_SHALLOW_FILE" ]; then
    echo "  (shallow repo — deepening history for pull/rebase)"
    if ! timeout "${DEEPEN_TIMEOUT}" git fetch --no-recurse-submodules --deepen=150 origin main 2>&1 | _sanitize; then
        echo "  FATAL: deepen fetch timed out after ${DEEPEN_TIMEOUT}s — shallow repo cannot rebase"
        echo "  Falling back to merge strategy (preserves commit, no rebase needed)"
        git config pull.rebase false 2>/dev/null || true
    fi
fi

backoff=$INITIAL_BACKOFF
for attempt in $(seq 1 $MAX_RETRIES); do
    echo "=== Push attempt $attempt/$MAX_RETRIES ==="

    # Remember our commit before pull so we can detect if rebase dropped it
    PRE_PULL_HEAD=$(git rev-parse HEAD 2>/dev/null)

    # BUG FIX 2026-04-05: stash unstaged/untracked before rebase, pop after.
    # Without this, rebase fails with "cannot pull with rebase: You have unstaged
    # changes" when generators leave working-tree modifications. Observed in
    # enhanced-ml-crypto.yml run 24001259151 (all 7 push attempts failed).
    STASHED=false
    if ! git diff --quiet HEAD 2>/dev/null || [ -n "$(git ls-files --others --exclude-standard 2>/dev/null)" ]; then
        if git stash push --include-untracked --quiet -m "safe_push-pre-rebase-$$" 2>/dev/null; then
            STASHED=true
        fi
    fi

    # Pull latest before push — rebase keeps history linear.
    # Bounded by GIT_NET_TIMEOUT so a hung network call cannot burn the whole
    # workflow timeout-minutes (root cause of chronic "cancelled" runs).
    pull_ok=true
    # -X theirs: during rebase, "theirs" = the commits being replayed (our local
    # commit with generated data). Auto-resolves conflicts in our favor instead of
    # stopping the rebase. This is the key fix for the race condition — when
    # multiple workflows push to main concurrently, rebase conflicts on data files
    # are now auto-resolved instead of requiring manual resolution that often fails.
    timeout "${GIT_NET_TIMEOUT}" git pull --rebase --no-recurse-submodules -X theirs origin main 2>&1 | _sanitize || {
        pull_ok=false
        echo "Rebase failed or timed out, aborting rebase and trying merge strategy..."
        git rebase --abort 2>/dev/null || true
        # Merge fallback: -X ours prefers our local branch (our generated data).
        # In merge semantics (unlike rebase), "ours" = local HEAD = our commit.
        if ! timeout "${GIT_NET_TIMEOUT}" git pull --no-rebase --no-recurse-submodules -X ours origin main 2>&1 | _sanitize; then
            echo "WARNING: Merge pull also failed on attempt $attempt"
        fi
    }

    # Restore stashed working-tree changes (best-effort — if pop conflicts, drop
    # since this script only ships the committed HEAD, not working-tree state).
    # NOTE: a failed `git stash pop` leaves merge-conflict markers in the
    # working tree even after `git stash drop` (drop only removes the stash
    # entry). On the next iteration `git pull --rebase` then aborts with
    # "needs merge / unmerged files" and every subsequent retry fails the same
    # way. Reset the index+worktree to HEAD when pop fails so retries can
    # proceed cleanly.
    if [ "$STASHED" = true ]; then
        if ! git stash pop --quiet 2>/dev/null; then
            git stash drop --quiet 2>/dev/null || true
            git reset --hard HEAD --quiet 2>/dev/null || true
            git clean -fd --quiet 2>/dev/null || true
        fi
    fi

    # After git pull --rebase, replayed commits get new SHAs, so PRE_PULL_HEAD is usually NOT an
    # ancestor of HEAD even though nothing was lost. The old merge-base check falsely triggered
    # reset --hard and an infinite retry loop. Only exit early if we truly have nothing to push.
    POST_PULL_HEAD=$(git rev-parse HEAD 2>/dev/null)
    if [ "$pull_ok" = true ] && [ "$PRE_PULL_HEAD" != "$POST_PULL_HEAD" ]; then
        CURRENT_REMOTE_HEAD=$(git rev-parse origin/main 2>/dev/null || echo "")
        if [ -n "$CURRENT_REMOTE_HEAD" ] && [ "$POST_PULL_HEAD" = "$CURRENT_REMOTE_HEAD" ]; then
            echo "Commit already present on remote — push successful"
            exit 0
        fi
        AHEAD=$(git rev-list --count origin/main..HEAD 2>/dev/null || echo 0)
        if ! git merge-base --is-ancestor "$PRE_PULL_HEAD" HEAD 2>/dev/null; then
            if [ "${AHEAD:-0}" -eq 0 ]; then
                echo "Rebase left no commits ahead of origin — changes likely upstream already"
                exit 0
            fi
        fi
    fi

    # Check again if there's anything to push after pull
    LOCAL_HEAD=$(git rev-parse HEAD 2>/dev/null || echo "")
    REMOTE_HEAD=$(git rev-parse origin/main 2>/dev/null || echo "")
    if [ -n "$LOCAL_HEAD" ] && [ "$LOCAL_HEAD" = "$REMOTE_HEAD" ]; then
        echo "Already up to date after pull — nothing to push"
        exit 0
    fi

    # Attempt push — sanitize output to avoid leaking tokens
    push_output=""
    push_rc=0
    if [ -n "$REMOTE_URL" ]; then
        push_output=$(timeout "${GIT_NET_TIMEOUT}" git push "$REMOTE_URL" HEAD:main 2>&1) || push_rc=$?
    else
        push_output=$(timeout "${GIT_NET_TIMEOUT}" git push origin main 2>&1) || push_rc=$?
    fi

    echo "$push_output" | _sanitize

    if [ $push_rc -eq 0 ]; then
        echo "Pushed successfully on attempt $attempt"
        exit 0
    fi

    # Detect transient ref-lock race conditions (concurrent push from another
    # workflow). These MUST be retried with a fresh pull+rebase — they are
    # NOT auth failures. Previously these caused false-positive exits via the
    # auth check below on the "rejected" substring.
    if echo "$push_output" | grep -qiE "cannot lock ref|remote rejected.*(is at|non-fast-forward|fetch first)"; then
        # Longer jitter to reduce thundering herd on concurrent retries
        jitter=$((RANDOM % 8 + 5))
        wait_time=$((backoff + jitter))
        if [ "$wait_time" -gt "$MAX_BACKOFF_SLEEP" ]; then
            wait_time=$MAX_BACKOFF_SLEEP
        fi
        echo "Push failed on attempt $attempt (ref-lock race), extended backoff ${wait_time}s..."
        sleep $wait_time
        backoff=$((backoff * 2))
        continue
    fi

    # Detect fatal auth errors — no point retrying these
    # NOTE: restrict to true credential/permission errors. Do NOT match bare
    # "403" or "401" which can appear in commit messages or unrelated output.
    if echo "$push_output" | grep -qiE "HTTP 403|HTTP 401|Authentication failed|Permission denied|could not read Username|invalid credentials|bad credentials"; then
        echo "ERROR: Authentication/permission failure — aborting (no retry)"
        exit 1
    fi

    # Detect permanent server-side rejection (pre-receive hook / branch protection /
    # GitHub error codes GH001 large-file, GH006 protected branch, GH007 signed-commit
    # required, etc). Retrying produces identical rejection but burns runner clock,
    # so fail fast.
    if echo "$push_output" | grep -qiE "pre-receive hook declined|push declined due to|protected branch|GH[0-9]{3}|refusing to (allow|update)"; then
        echo "ERROR: Push permanently rejected by remote (pre-receive hook / branch protection)"
        echo "$push_output" | tail -10
        exit 1
    fi

    # Add jitter (0-3s random) to backoff to reduce thundering herd
    jitter=$((RANDOM % 4))
    wait_time=$((backoff + jitter))
    if [ "$wait_time" -gt "$MAX_BACKOFF_SLEEP" ]; then
        wait_time=$MAX_BACKOFF_SLEEP
    fi
    echo "Push failed on attempt $attempt, backing off ${wait_time}s..."
    sleep $wait_time
    backoff=$((backoff * 2))
done

echo "ERROR: All $MAX_RETRIES push attempts failed"
exit 1
