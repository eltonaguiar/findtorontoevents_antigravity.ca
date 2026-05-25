#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "FAIL: not in a git repo"; exit 1; }

pass=0; fail=0
ok()   { echo "  [PASS] $1"; pass=$((pass+1)); }
bad()  { echo "  [FAIL] $1   (expected: $2)"; fail=$((fail+1)); }

echo "=== Git history rewrite recovery validator (2026-05-25) ==="
echo

git fetch origin main --quiet 2>/dev/null || true

test -f docs/GIT_HISTORY_REWRITE_2026-05-25.md \
  && ok "recovery doc present" \
  || bad "recovery doc missing" "docs/GIT_HISTORY_REWRITE_2026-05-25.md should exist on main"

LOCAL="$(git rev-parse HEAD 2>/dev/null || echo '')"
REMOTE="$(git rev-parse origin/main 2>/dev/null || echo '')"
[ -n "${LOCAL}" ] && [ "${LOCAL}" = "${REMOTE}" ] \
  && ok "HEAD matches origin/main (${LOCAL})" \
  || bad "HEAD diverges from origin/main" "local=${LOCAL}  remote=${REMOTE}"

fsck_out="$(git fsck --no-progress 2>&1 | grep -iE 'missing blob|missing tree|missing commit' | head -3 || true)"
[ -z "${fsck_out:-}" ] \
  && ok "fsck clean (no missing blobs/trees)" \
  || bad "fsck reports missing objects" "${fsck_out}"

matches="$(git log --oneline 2>/dev/null | grep -cE 'gitignore v4|gitignore regenerable bloat|gitignore v3' || true)"
[ "${matches:-0}" -ge 3 ] \
  && ok "post-rewrite gitignore commits present (${matches} found, expected >=3)" \
  || bad "post-rewrite gitignore commits missing" "expected gitignore v3/v4/regenerable bloat commits"

leaked="$(git ls-files \
  | grep -cE '(^|/)ml_crypto_predictor/production_models/.*\.pkl$|(^|/)ml_crypto_predictor/enhanced_models/models/.*\.joblib$|^audit/data/dashboard_data\.json$|^events\.json$|^next/events\.json$|^data/live_picks\.db$|^alpha_engine/data/closed_picks\.json$|^alpha_engine/data/closed_picks_enriched\.json$|^alpha_engine/data/closed_picks\.archive\.jsonl$|^tools/data/audit_edge_review_live\.json$|^tools/data/snapshots/dashboard_data_.*\.json$' || true)"
[ "${leaked:-0}" -eq 0 ] \
  && ok "no scrubbed bloat paths tracked in index" \
  || bad "${leaked} bloat path(s) still tracked" "git ls-files | grep production_models"

if [ ! -f .gitignore ]; then
  bad ".gitignore missing entirely" ".gitignore file must exist"
else
  gi_lines="$(grep -cE '^ml_crypto_predictor/production_models/\*\.pkl|^ml_crypto_predictor/enhanced_models/models/\*\.joblib|^audit/data/dashboard_data\.json' .gitignore || true)"
  [ "${gi_lines:-0}" -ge 3 ] \
    && ok "gitignore covers the scrubbed paths" \
    || bad "gitignore missing scrub-path entries" "expected >=3 of the bloat patterns in .gitignore"
fi

conflicts="$(git ls-files --unmerged 2>/dev/null | wc -l)"
[ "${conflicts:-0}" -eq 0 ] \
  && ok "no unresolved merge conflicts" \
  || bad "${conflicts} unmerged path(s)" "resolve with git status / git mergetool"

if git merge-base --is-ancestor HEAD origin/main 2>/dev/null; then
  ok "git pull --ff-only origin main would succeed (no divergence)"
else
  bad "git pull --ff-only origin main would fail" "your local main diverged"
fi

echo
total=$((pass+fail))
if [ "${fail}" -eq 0 ]; then
  echo "RESULT: ALL ${total} CHECKS PASSED -- recovery complete"
  exit 0
else
  echo "RESULT: ${fail}/${total} CHECKS FAILED -- see fixes above"
  exit 1
fi
