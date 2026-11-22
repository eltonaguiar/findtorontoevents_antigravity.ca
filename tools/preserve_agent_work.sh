#!/usr/bin/env bash
# preserve_agent_work.sh — snapshot a worktree's uncommitted work onto a side branch.
#
# WHY THIS EXISTS
#   Several agents share this clone. When one agent checks out a different branch in
#   a worktree another agent was working in, the other agent's uncommitted edits are
#   stranded in a branch they are no longer on — and a `git checkout` that would
#   overwrite them aborts, or a subsequent stash/clean destroys them.
#
#   This script is the safe answer to "back up my work before I change branches".
#   It NEVER touches the source worktree's real index, HEAD, or current branch.
#   It reads the worktree through a TEMPORARY index file, writes the result to a
#   new commit object, and points refs/backup/<YYYYMMDD>/<label>-<stamp> at it.
#
#   Namespace note: this matches the convention kilo's
#   docs/WORK_PRESERVATION_AND_MERGE_POLICY_2026-11-19.md established
#   (refs/backup/<date>/<name>), deliberately under refs/backup/ and NOT
#   refs/heads/, so a backup can never be mistaken for a merge candidate.
#
# WITHOUT --push the snapshot stays local (instant, free, recoverable).
# WITH    --push it goes to origin, so it survives this machine.
#
# RESTORE
#   git checkout refs/backup/<day>/<label>-<stamp> -- path/to/file   # one file
#   git log -1 refs/backup/<day>/<label>-<stamp>                     # the snapshot
#   git diff <snapshot>^ <snapshot>                                  # everything
#
# USAGE
#   tools/preserve_agent_work.sh                          # current worktree, local only
#   tools/preserve_agent_work.sh --push                   # current worktree, pushed
#   tools/preserve_agent_work.sh --all --push             # every registered worktree
#   tools/preserve_agent_work.sh --worktree PATH --label kilo --push
#
# SAFETY
#   * refuses to PUSH a snapshot that matches a secret pattern (paths only, never values)
#   * refuses any snapshot larger than --max-mb (default 200) unless --allow-large
#   * never force-pushes, never rebases, never rewrites the source branch
#   * exits 0 even when individual worktrees are skipped, so it can run from cron;
#     prints a final summary you can read
set -uo pipefail

MAX_MB=200
PUSH=0
ALL=0
ALLOW_LARGE=0
LABEL=""
TARGETS=()

die() { echo "preserve: $*" >&2; exit 2; }

while [ $# -gt 0 ]; do
  case "$1" in
    --push)        PUSH=1 ;;
    --all)         ALL=1 ;;
    --allow-large) ALLOW_LARGE=1 ;;
    --label)       LABEL="${2:-}"; shift ;;
    --worktree)    TARGETS+=("${2:-}"); shift ;;
    --max-mb)      MAX_MB="${2:-200}"; shift ;;
    -h|--help)     sed -n '2,40p' "$0"; exit 0 ;;
    *)             die "unknown argument: $1 (try --help)" ;;
  esac
  shift
done

# Secret patterns. We report the FILE, never the matched value.
# Deliberately narrow enough to avoid flagging ordinary prose about passwords.
SECRET_RE='(password|passwd|pwd)[[:space:]]*[=:][[:space:]]*["'"'"'][^"'"'"']{6,}'
SECRET_RE="$SECRET_RE|AUDIT_DB_PASS[[:space:]]*=[[:space:]]*[\"'][^\"']"
SECRET_RE="$SECRET_RE|GITHUB_TOKEN[[:space:]]*=[[:space:]]*[\"']?[A-Za-z0-9_]{20,}"
SECRET_RE="$SECRET_RE|ghp_[A-Za-z0-9]{20,}|gho_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}"
SECRET_RE="$SECRET_RE|sk-[A-Za-z0-9]{20,}|sk-ant-[A-Za-z0-9_-]{20,}"
SECRET_RE="$SECRET_RE|-----BEGIN [A-Z ]*PRIVATE KEY-----"
SECRET_RE="$SECRET_RE|mysql://[^:[:space:]]+:[^@[:space:]]+@"
SECRET_RE="$SECRET_RE|amqp://[^:[:space:]]+:[^@[:space:]]+@"

slugify() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's|[^a-z0-9]+|-|g; s|^-+||; s|-+$||' | cut -c1-48
}

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DAY="$(date -u +%Y%m%d)"
TMPDIR_BASE="$(mktemp -d -t preserve-XXXXXX)"
trap 'rm -rf "$TMPDIR_BASE"' EXIT

# Resolve the worktree list we will act on.
if [ "$ALL" -eq 1 ] && [ "${#TARGETS[@]}" -eq 0 ]; then
  while IFS= read -r line; do
    case "$line" in
      "worktree "*) TARGETS+=("${line#worktree }") ;;
    esac
  done < <(git worktree list --porcelain 2>/dev/null)
fi
[ "${#TARGETS[@]}" -gt 0 ] || TARGETS=("$(git rev-parse --show-toplevel 2>/dev/null || pwd)")

PUSHED=0; LOCAL=0; SKIPPED=0; REFUSED=0; FAILED=0
declare -a SUMMARY=()

save_one() {
  local wt="$1" want_label="$2"
  if [ ! -d "$wt" ]; then
    SUMMARY+=("SKIP   $wt — not a directory")
    SKIPPED=$((SKIPPED+1)); return
  fi
  if ! git -C "$wt" rev-parse --git-dir >/dev/null 2>&1; then
    SUMMARY+=("SKIP   $wt — not a git worktree")
    SKIPPED=$((SKIPPED+1)); return
  fi

  local head dirty branch base_label label ref
  head="$(git -C "$wt" rev-parse HEAD 2>/dev/null)" || {
    SUMMARY+=("SKIP   $wt — no HEAD"); SKIPPED=$((SKIPPED+1)); return; }
  branch="$(git -C "$wt" branch --show-current 2>/dev/null)"
  [ -n "$branch" ] || branch="detached"
  dirty="$(git -C "$wt" status --porcelain 2>/dev/null | wc -l | tr -d ' ')"

  base_label="$want_label"
  [ -n "$base_label" ] || base_label="$(slugify "$(basename "$wt")")-$(slugify "$branch")"
  label="$(slugify "$base_label")"

  # Size guard: catch runaway data snapshots before we build the tree.
  # The `cd` matters: ls-files emits paths relative to the worktree, so du must
  # run there too or every path misses and the guard reads 0.
  local big
  big="$( (cd "$wt" && git ls-files --modified --others --exclude-standard -z 2>/dev/null \
        | xargs -0 -r du -cb 2>/dev/null | tail -1 | cut -f1) )"
  big="${big:-0}"
  case "$big" in ''|*[!0-9]*) big=0 ;; esac
  if [ "$ALLOW_LARGE" -eq 0 ] && [ "$((big / 1048576))" -gt "$MAX_MB" ]; then
    SUMMARY+=("SKIP   $wt — $((big/1048576))MB exceeds --max-mb $MAX_MB (use --allow-large)")
    SKIPPED=$((SKIPPED+1)); return
  fi

  # Build the snapshot through a throwaway index. The real index is never opened
  # for writing, so the source worktree's staged state is bit-for-bit unchanged.
  local idx tree snap
  idx="$TMPDIR_BASE/idx-$RANDOM"
  GIT_INDEX_FILE="$idx" git -C "$wt" read-tree "$head" >/dev/null 2>&1 || {
    SUMMARY+=("FAIL   $wt — read-tree failed"); FAILED=$((FAILED+1)); return; }
  GIT_INDEX_FILE="$idx" git -C "$wt" add -A >/dev/null 2>&1
  tree="$(GIT_INDEX_FILE="$idx" git -C "$wt" write-tree 2>/dev/null)"
  [ -n "$tree" ] || { SUMMARY+=("FAIL   $wt — write-tree failed"); FAILED=$((FAILED+1)); return; }

  if [ "$tree" = "$(git -C "$wt" rev-parse "$head^{tree}" 2>/dev/null)" ]; then
    SUMMARY+=("CLEAN  $wt — nothing to preserve ($branch @ ${head:0:9})")
    SKIPPED=$((SKIPPED+1)); return
  fi

  snap="$(git -C "$wt" commit-tree "$tree" -p "$head" \
          -m "chore(preserve): snapshot of $branch @ ${head:0:9}

Captured by tools/preserve_agent_work.sh at $STAMP.
Source worktree: $wt
Branch at capture: $branch
Dirty paths at capture: $dirty

This commit is a BACKUP, not a change to merge. Restore individual files with:
  git checkout <this-branch> -- <path>" 2>/dev/null)"
  [ -n "$snap" ] || { SUMMARY+=("FAIL   $wt — commit-tree failed"); FAILED=$((FAILED+1)); return; }

  # Secret scan on the snapshot diff: report paths, never values.
  local hits
  hits="$(git -C "$wt" diff "$head" "$snap" 2>/dev/null | grep -nEi "$SECRET_RE" | cut -d: -f1 | head -5)"
  local hit_files=""
  if [ -n "$hits" ]; then
    hit_files="$(git -C "$wt" diff --name-only "$head" "$snap" 2>/dev/null | grep -iE 'env|secret|key|pass|config|yml|yaml|sh|py' | head -6 | tr '\n' ' ')"
  fi

  ref="refs/backup/$DAY/$label-$STAMP"
  if git -C "$wt" rev-parse --verify -q "$ref" >/dev/null 2>&1; then
    ref="$ref-$RANDOM"
  fi
  git -C "$wt" update-ref "$ref" "$snap" 2>/dev/null || {
    SUMMARY+=("FAIL   $wt — update-ref failed"); FAILED=$((FAILED+1)); return; }

  if [ -n "$hits" ]; then
    SUMMARY+=("LOCAL  $ref — $dirty dirty paths, ${snap:0:9}")
    SUMMARY+=("       REFUSED PUSH: secret pattern found in diff (paths: ${hit_files:-unknown})")
    REFUSED=$((REFUSED+1))
    return
  fi

  if [ "$PUSH" -eq 1 ]; then
    if git -C "$wt" push -q origin "$ref:$ref" 2>/dev/null; then
      SUMMARY+=("PUSHED $ref — $dirty dirty paths, ${snap:0:9}")
      PUSHED=$((PUSHED+1))
    else
      SUMMARY+=("LOCAL  $ref — push failed (offline or rejected); snapshot kept locally")
      LOCAL=$((LOCAL+1))
    fi
  else
    SUMMARY+=("LOCAL  $ref — $dirty dirty paths, ${snap:0:9}")
    LOCAL=$((LOCAL+1))
  fi
}

for wt in "${TARGETS[@]}"; do
  save_one "$wt" "$LABEL"
done

echo "preserve_agent_work — $STAMP"
echo "======================================================"
for line in "${SUMMARY[@]}"; do echo "  $line"; done
echo "------------------------------------------------------"
printf '  pushed=%d local=%d clean/skipped=%d push-refused=%d failed=%d\n' \
  "$PUSHED" "$LOCAL" "$SKIPPED" "$REFUSED" "$FAILED"
if [ "$REFUSED" -gt 0 ]; then
  echo
  echo "  A snapshot matched a secret pattern and was NOT pushed."
  echo "  Move the value to os.environ.get('...') with no default, then re-run."
fi
if [ "$PUSHED" -gt 0 ] || [ "$LOCAL" -gt 0 ]; then
  echo
  echo "  Restore any file with:  git checkout <snapshot-ref> -- <path>"
echo "  Backups live under refs/backup/ and are never branches."
fi
exit 0
