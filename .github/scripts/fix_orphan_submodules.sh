#!/usr/bin/env bash
# Prevent actions/checkout post-job "git submodule foreach" exit 128 when the
# index has gitlinks (mode 160000) but .gitmodules has no URL mapping.
set -euo pipefail

git config --global submodule.recurse false

if [ -f .gitmodules ]; then
  git config -f .gitmodules --remove-section submodule.STOCKSUNIFY 2>/dev/null || true
  git config -f .gitmodules --remove-section submodule.tmp/fte_clone 2>/dev/null || true
fi

for path in openclaude openclaude-vscode; do
  if git ls-files -s "$path" 2>/dev/null | grep -q '^160000'; then
    git rm --cached -f "$path" 2>/dev/null || true
    echo "Dropped orphan submodule gitlink: $path"
  fi
done
