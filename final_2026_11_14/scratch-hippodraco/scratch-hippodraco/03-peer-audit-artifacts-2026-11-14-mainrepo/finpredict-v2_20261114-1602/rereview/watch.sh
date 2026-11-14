#!/usr/bin/env bash
# Re-review watcher for the prediction-system audit archive.
# Detects new local audit artifacts, new origin/main commits, new audit-like
# remote branches, and new GitHub Actions failures. Appends findings to
# REREVIEW_QUEUE.md. It does not modify repo source.
#
# Usage: watch.sh --once | --loop
set -uo pipefail

ROOT="/home/eaguiar2015/findtorontoevents_antigravity.ca"
ARCH="$ROOT/.kilo/worktrees/finpredict-v2/2026-11-14/finpredict-v2_20261114-1602"
RR="$ARCH/rereview"
STATE="$RR/state"
QUEUE="$RR/REREVIEW_QUEUE.md"
LOG="$RR/watch.log"
MARKER="$STATE/marker"
LAST_SHA="$STATE/last_origin_main"
LAST_BRANCHES="$STATE/last_branches.txt"
INTERVAL="${WATCH_INTERVAL:-120}"
GH_EVERY="${WATCH_GH_EVERY:-5}"

mkdir -p "$STATE"
touch "$QUEUE" "$LOG" "$MARKER"

log() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >> "$LOG"; }
queue() { printf '%s\n' "$*" >> "$QUEUE"; }

scan_remote() {
  local sha prev
  git -C "$ROOT" fetch --quiet origin main 2>/dev/null || true
  sha=$(git -C "$ROOT" rev-parse origin/main 2>/dev/null || echo unknown)
  prev=$(cat "$LAST_SHA" 2>/dev/null || echo "")
  if [ "$sha" != "$prev" ] && [ "$sha" != "unknown" ]; then
    printf '%s' "$sha" > "$LAST_SHA"
    queue ""
    queue "## [$(date -u +%Y-%m-%dT%H:%M:%SZ)] origin/main moved"
    queue '```'
    git -C "$ROOT" log --oneline "${prev:-HEAD~1}..${sha}" 2>/dev/null | head -40 >> "$QUEUE"
    queue '```'
    log "origin/main ${prev:-none} -> $sha"
  fi
}

scan_branches() {
  local nowf
  nowf="$STATE/branches.now"
  git -C "$ROOT" ls-remote --heads origin 2>/dev/null \
    | awk '{print $2}' | sed 's#refs/heads/##' \
    | grep -Ei 'audit|inspect|finpredict|deepai|hilarious|seer' | sort > "$nowf" || true
  if [ -f "$LAST_BRANCHES" ]; then
    local newb
    newb=$(comm -13 "$LAST_BRANCHES" "$nowf" 2>/dev/null || true)
    if [ -n "$newb" ]; then
      queue ""
      queue "## [$(date -u +%Y-%m-%dT%H:%M:%SZ)] new audit-like remote branches"
      printf '%s\n' "$newb" | sed 's/^/- /' >> "$QUEUE"
      log "new branches: $newb"
    fi
  fi
  mv "$nowf" "$LAST_BRANCHES"
}

scan_local() {
  local tmp
  tmp="$STATE/local.now"
  find "$ROOT" -xdev -type f -newer "$MARKER" 2>/dev/null \
    \( -path "*/2026-11-14/*" -o -path "*/audits/*" -o -path "*/updates/*" \
       -o -path "*/recommendations/*" -o -path "*/actions_deepdive/*" \) \
    ! -path "*/.git/*" ! -path "*/node_modules/*" \
    ! -path "*/bestiejob/*" ! -path "*/logs/*" ! -path "*/tmp/*" \
    ! -path "*/rereview/*" \
    | head -200 > "$tmp" || true
  touch "$MARKER"
  if [ -s "$tmp" ]; then
    queue ""
    queue "## [$(date -u +%Y-%m-%dT%H:%M:%SZ)] new/changed audit files (local)"
    sed "s#^$ROOT/##" "$tmp" | sed 's/^/- /' >> "$QUEUE"
    log "local files: $(wc -l < "$tmp")"
  fi
}

scan_actions() {
  local out
  out="$STATE/actions.now.json"
  gh run list --repo eltonaguiar/findtorontoevents_antigravity.ca --limit 30 \
    --json databaseId,workflowName,conclusion,createdAt,url > "$out" 2>/dev/null || return 0
  python3 - "$out" "$QUEUE" <<'PY' 2>/dev/null || true
import json,sys
p,q=sys.argv[1],sys.argv[2]
try: d=json.load(open(p))
except Exception: raise SystemExit
bad=[r for r in d if r.get("conclusion") in ("failure","timed_out","startup_failure","stale")]
if bad:
    with open(q,"a") as f:
        f.write("\n## [actions] new failures/cancels (last 30 runs)\n")
        for r in bad[:15]:
            f.write(f"- {r.get('createdAt')} {r.get('workflowName')} {r.get('conclusion')} {r.get('url')}\n")
PY
}

scan_once() {
  scan_remote
  scan_branches
  scan_local
  if [ "${1:-}" = "--with-gh" ]; then scan_actions; fi
}

MODE="${1:---loop}"
echo "WATCH_READY mode=$MODE root=$ROOT queue=$QUEUE"
log "watcher start mode=$MODE"

if [ "$MODE" = "--once" ]; then
  scan_once --with-gh
  log "watcher once complete"
  exit 0
fi

n=0
while true; do
  n=$((n+1))
  if [ $((n % GH_EVERY)) -eq 0 ]; then scan_once --with-gh; else scan_once; fi
  sleep "$INTERVAL"
done
