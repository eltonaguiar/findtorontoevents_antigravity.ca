#!/usr/bin/env bash
# preserve_peer_worktrees.sh — snapshot parallel agent worktrees before they are deleted.
#
# The audit review split across several .kilo/worktrees/* checkouts. Their work is
# sometimes uncommitted (diffs + untracked files) and will be lost on deletion.
# This script writes a dated snapshot of each worktree's branch state, diff, and
# untracked files into reports/peer_snapshots/<UTC timestamp>/ so nothing useful
# disappears. It never modifies a worktree.
#
# Usage: tools/preserve_peer_worktrees.sh [worktree-root]
# Default root: <repo>/.kilo/worktrees
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# In a linked worktree, .kilo/worktrees lives under the MAIN checkout, not here.
COMMON_DIR="$(git -C "$REPO_ROOT" rev-parse --git-common-dir 2>/dev/null || echo "$REPO_ROOT/.git")"
MAIN_ROOT="$(cd "$COMMON_DIR/.." && pwd)"
WT_ROOT="${1:-$MAIN_ROOT/.kilo/worktrees}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$REPO_ROOT/reports/peer_snapshots/$STAMP"

WORKTREES=(
  universal-pisces
  witty-fight
  lapis-chronometer
  vanilla-handsaw
  audit2-page-tunable-variables
  audit2-page-forward-path
  audit2-page-implementation-status
)

mkdir -p "$OUT"
{
  echo "# Peer worktree snapshot $STAMP"
  echo
  echo "root: $WT_ROOT"
} > "$OUT/INDEX.md"

for name in "${WORKTREES[@]}"; do
  wt="$WT_ROOT/$name"
  [ -d "$wt" ] || { echo "- $name: MISSING" >> "$OUT/INDEX.md"; continue; }
  mkdir -p "$OUT/$name"

  branch="$(git -C "$wt" branch --show-current 2>/dev/null || echo detached)"
  head="$(git -C "$wt" rev-parse --short HEAD 2>/dev/null || echo '?')"
  ahead="$(git -C "$wt" rev-list --count origin/main..HEAD 2>/dev/null || echo '?')"
  dirty="$(git -C "$wt" status --porcelain 2>/dev/null | wc -l | tr -d ' ')"

  git -C "$wt" status --porcelain > "$OUT/$name/status.txt" 2>&1 || true
  git -C "$wt" log --oneline -15 > "$OUT/$name/log.txt" 2>&1 || true
  # Code diffs only (skip large data payloads that churn every run).
  git -C "$wt" diff -- . \
    ':(exclude)*.json' ':(exclude)*.jsonl' ':(exclude)*.pkl' ':(exclude)logs/*' \
    ':(exclude)*.html' > "$OUT/$name/code.patch" 2>/dev/null || true
  # Full status names for anything we filtered out of the patch.
  git -C "$wt" diff --name-only > "$OUT/$name/changed_files.txt" 2>&1 || true

  # Copy small untracked text files (docs, scripts, tests) — not binaries/data.
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    case "$f" in
      *.md|*.py|*.sh|*.yml|*.yaml|*.txt|*.html|*.js) ;;
      *) continue ;;
    esac
    size="$(stat -c%s "$wt/$f" 2>/dev/null || echo 0)"
    [ "$size" -le 262144 ] || continue
    mkdir -p "$OUT/$name/untracked/$(dirname "$f")"
    cp "$wt/$f" "$OUT/$name/untracked/$f" 2>/dev/null || true
  done < <(git -C "$wt" ls-files --others --exclude-standard 2>/dev/null || true)

  # Handoff / COMS notes, if any.
  grep -rIl -E 'COMS|AGENT_BUS|handoff|taking over|next steps' \
    "$wt"/docs "$wt"/updates "$wt"/*.md 2>/dev/null \
    | head -20 > "$OUT/$name/handoff_candidates.txt" || true

  printf -- '- %s: branch=%s head=%s ahead=%s dirty=%s\n' \
    "$name" "$branch" "$head" "$ahead" "$dirty" >> "$OUT/INDEX.md"
done

echo
echo "Snapshot written to: $OUT"
echo "Commit it with: git add reports/peer_snapshots && git commit -m 'chore: peer worktree snapshot $STAMP'"
