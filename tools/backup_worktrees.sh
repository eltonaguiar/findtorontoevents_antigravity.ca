#!/usr/bin/env bash
# Read-only backup of every dirty worktree: stash-create ref + untracked tarball.
# Never touches the working tree, the index, or any branch. Backups stay local.
set -u
REPO=${1:-/home/eaguiar2015/findtorontoevents_antigravity.ca}
OUT=${2:-/tmp/kilo_backups}
DATE=$(date +%Y%m%d)
mkdir -p "$OUT"
cd "$REPO" || exit 1
for d in $(git worktree list --porcelain | awk '/^worktree /{print $2}'); do
  [ -d "$d" ] || { echo "MISSING $d (run: git worktree prune)"; continue; }
  n=$(git -C "$d" status --porcelain | wc -l)
  [ "$n" -eq 0 ] && continue
  name=$(basename "$d" | tr -c 'A-Za-z0-9._-' '_')
  sha=$(git -C "$d" stash create "kilo-backup-$DATE" 2>/dev/null)
  if [ -n "$sha" ]; then
    git -C "$d" update-ref "refs/backup/$DATE/$name" "$sha"
    echo "tracked  $name -> refs/backup/$DATE/$name ($(git -C "$d" rev-parse --short "$sha"))"
  else
    echo "tracked  $name -> SKIPPED (unmerged index or no tracked change)"
  fi
  u=$(git -C "$d" ls-files --others --exclude-standard | wc -l)
  if [ "$u" -gt 0 ]; then
    git -C "$d" ls-files --others --exclude-standard -z \
      | tar --null -T - -czf "$OUT/$name-untracked-$DATE.tgz" -C "$d" 2>/dev/null \
      && echo "untracked $name -> $OUT/$name-untracked-$DATE.tgz ($u files)"
  fi
done
