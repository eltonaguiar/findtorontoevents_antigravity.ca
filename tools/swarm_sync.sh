#!/usr/bin/env bash
# tools/swarm_sync.sh — bidirectional sync of agent state files
# Called by .github/workflows/swarm-sync-v2.yml
set -e

echo '=== STEP 1: Determine what needs merging ==='
CHANGED_FILES=()

for file in agent_shared_memory.json agent_swarm_state.json; do
  if [ ! -f $file ]; then
    echo 'SKIP: does not exist in main branch'
    continue
  fi

  echo '---' $file '---'

  # Read local last_modified (use sys.argv to avoid shell injection)
  local_updated=$(python3 -c '
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    print(d.get(\"last_modified\", d.get(\"regime_updated_at\", \"0\")))
except:
    print(\"0\")
' $file 2>/dev/null || echo '0')
  echo '  local:' $local_updated

  # Read remote last_modified
  remote_hash=$(git show main:$file 2>/dev/null | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get(\"last_modified\", d.get(\"regime_updated_at\", \"0\")))
except:
    print(\"0\")
' 2>/dev/null || echo '0')
  echo '  remote:' $remote_hash

  if [ x${local_updated:-0} != x${remote_hash:-0} ] && [ -n "$remote_hash" ] && [ "$remote_hash" != '0' ]; then
    echo '  -> remote newer, merging remote -> local'
    git show main:"$file" > "$file"
    CHANGED_FILES+=("$file")
  elif [ x${local_updated:-0} = x0 ] && [ -n "$remote_hash" ]; then
    echo '  -> local empty, restoring from remote'
    git show main:"$file" > "$file"
    CHANGED_FILES+=("$file")
  else
    echo '  -> up-to-date or no remote version'
  fi
done

echo ''
echo '=== STEP 2: Push merged changes ==='
if [ ${#CHANGED_FILES[@]} -gt 0 ]; then
  git add "${CHANGED_FILES[@]}"
  git commit -m 'chore(swarm): bidirectional sync agent state files [skip ci]'

  # Rebase to resolve concurrent pushes; abort cleanly on conflict
  if ! git pull --rebase origin main; then
    echo 'ERROR: rebase conflict — aborting sync to avoid corrupting state files'
    git rebase --abort 2>/dev/null || true
    exit 1
  fi

  # Double-check no conflict markers leaked into staged files
  if git diff --cached | grep -qE '^<<<<<<<|^=======|^>>>>>>>'; then
    echo 'ERROR: conflict markers in staged files — aborting push'
    exit 1
  fi

  git push origin main
  echo 'PUSHED OK'
else
  echo 'No files changed — nothing to push'
fi