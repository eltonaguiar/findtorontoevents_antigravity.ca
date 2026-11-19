#!/bin/bash
# agent_worktree_snapshot.sh — push a WIP snapshot to a side branch WITHOUT
# touching HEAD, the index, or the working tree.
#
# Why (fleet agreement 2026-11-19): agents kept losing uncommitted work when
# switching branches (a copilot session clobbered its own doc edits with a
# `git checkout <branch> -- <file>` the same day), and peer work stranded on
# local branches is invisible to the fleet. This gives every agent a one-command
# backup that cannot interfere with anything: the snapshot is built in a
# TEMPORARY index and pushed as `backup/<agent>/<utc-stamp>`.
#
#   tools/agent_worktree_snapshot.sh <agent-name> [remote]
#
# Properties:
#   * read-only for your checkout: HEAD, index, working tree all untouched
#   * includes EVERYTHING git would add with `git add -A` (respects .gitignore,
#     so secrets files like dbpasses stay out — but run `COMS guard` on anything
#     you are unsure about first)
#   * parent = current HEAD, so the branch shows exactly what the WIP changes
#   * never force-pushes; each run makes a new timestamped branch
#   * prune old ones with: git push <remote> --delete backup/<agent>/<stamp>
set -euo pipefail

AGENT="${1:?usage: agent_worktree_snapshot.sh <agent-name> [remote]}"
REMOTE="${2:-origin}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
# slugify the agent name so it is a valid ref component
AGENT_SLUG="$(echo "$AGENT" | tr 'A-Z' 'a-z' | tr -cs 'a-z0-9._-' '-' | sed 's/^-//;s/-$//')"
BRANCH="backup/${AGENT_SLUG}/${STAMP}"

HEAD_SHA="$(git rev-parse HEAD)"
TMPIDX="$(mktemp)"
trap 'rm -f "$TMPIDX"' EXIT

# Build the snapshot in a temporary index: current HEAD + every tracked and
# untracked (non-ignored) change, exactly like `git add -A` would stage.
GIT_INDEX_FILE="$TMPIDX" git read-tree "$HEAD_SHA"
GIT_INDEX_FILE="$TMPIDX" git add -A
TREE="$(GIT_INDEX_FILE="$TMPIDX" git write-tree)"

if [ "$TREE" = "$(git rev-parse "$HEAD_SHA^{tree}")" ]; then
  echo "nothing to back up: working tree matches HEAD ($HEAD_SHA)"
  echo "pushing a ref to HEAD anyway so the branch records the checkpoint"
  COMMIT="$HEAD_SHA"
else
  COMMIT="$(git commit-tree "$TREE" -p "$HEAD_SHA" \
    -m "backup(${AGENT_SLUG}): WIP snapshot ${STAMP}

Automated worktree snapshot (tools/agent_worktree_snapshot.sh).
Parent is the HEAD the agent was working on; diff this commit against
its parent to see exactly what was in flight. Not for direct merge.")"
fi

git push "$REMOTE" "${COMMIT}:refs/heads/${BRANCH}"
echo "backed up -> ${REMOTE}/${BRANCH} (commit ${COMMIT:0:12}, parent ${HEAD_SHA:0:12})"
echo "restore into a scratch worktree with:"
echo "  git worktree add /tmp/restore-${AGENT_SLUG} ${BRANCH}"
