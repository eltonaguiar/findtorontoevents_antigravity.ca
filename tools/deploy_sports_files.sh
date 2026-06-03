#!/usr/bin/env bash
# deploy_sports_files.sh — sync git HEAD's sports files to FTP production.
#
# WHY: 50webs has no shell. After merging a sports PR to main, files don't
# reach production until somebody FTP-uploads them. This session lost
# production twice from forgetting that step (PR #399 squash → conflict
# markers; PR #415 merge → missing require_once). This script closes the
# gap: one command, runs smoke tests before + after deploy, refuses to
# ship if anything is red.
#
# USAGE
#   tools/deploy_sports_files.sh                        # diff + upload + verify
#   tools/deploy_sports_files.sh --dry-run              # show what would upload
#   tools/deploy_sports_files.sh --force                # skip pre-deploy smoke
#   tools/deploy_sports_files.sh --include-env --force  # refresh live-monitor/api/.env too
#
# REQUIRES
#   - git, curl, sha256sum (Git Bash on Windows ships these)
#   - python3 + pytest (for smoke run)
#   - FTP_USER + FTP_PASS in env, or sourced from
#     C:/windows_env_backup_2026-04-14.md (peer agent's known location)
set -uo pipefail

DRY_RUN=0
FORCE=0
INCLUDE_ENV=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --force) FORCE=1 ;;
    --include-env) INCLUDE_ENV=1 ;;
    *) echo "Unknown arg: $arg" >&2; exit 2 ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# --- Source FTP creds -------------------------------------------------------
if [ -z "${FTP_USER:-}" ] || [ -z "${FTP_PASS:-}" ]; then
  ENV_FILE="C:/windows_env_backup_2026-04-14.md"
  if [ -f "$ENV_FILE" ]; then
    FTP_USER="$(grep -E '^FTP_USER=' "$ENV_FILE" | head -1 | cut -d'=' -f2)"
    FTP_PASS="$(grep -E '^FTP_PASS=' "$ENV_FILE" | head -1 | cut -d'=' -f2)"
  fi
fi
if [ -z "${FTP_USER:-}" ] || [ -z "${FTP_PASS:-}" ]; then
  echo "FTP_USER + FTP_PASS not set. Export both or place them in $ENV_FILE." >&2
  exit 2
fi
FTP_HOST="${FTP_HOST:-ftps2.50webs.com}"
REMOTE_BASE="/findtorontoevents.ca"

# Files that ship via FTP. Keep in sync with .github/workflows/sports-smoke-and-e2e.yml deploy-guard.
SPORTS_FILES=(
  "live-monitor/sports-betting.html"
  "live-monitor/api/sports_picks.php"
  "live-monitor/api/sports_bets.php"
  "live-monitor/api/sports_value_analyze_lib.php"
  "live-monitor/api/sports_value_nhl_goalie_lib.php"
  "live-monitor/api/sports_steam.php"
  "live-monitor/api/sports_steam_detector.php"
  "live-monitor/api/sports_arb.php"
  "live-monitor/api/sports_arb_scanner.php"
  "live-monitor/api/sports_ml.php"
  "live-monitor/api/db_config.php"
  "config/auto_place_policy.json"
  "updates/index.html"
)

# Also auto-include any updates/*.md or updates/*.html newer than 7 days that
# git is tracking. Catches the "wrote a new dated update doc, forgot to FTP it"
# gap that hit us right after the next-steps roadmap merged.
if [ -d updates ]; then
  while IFS= read -r f; do
    [ -n "$f" ] && SPORTS_FILES+=("$f")
  done < <(find updates -maxdepth 1 -mtime -7 \( -name '*.md' -o -name '*.html' \) -type f 2>/dev/null \
            | xargs -r -I{} sh -c 'git ls-files --error-unmatch "{}" >/dev/null 2>&1 && echo "{}"')
fi

# --- Pre-deploy smoke (skip with --force) -----------------------------------
if [ "$FORCE" -eq 0 ]; then
  echo "=== Pre-deploy smoke (live production endpoints) ==="
  if ! python3 -m pytest tests/test_sports_endpoints_smoke.py -q --tb=line; then
    echo "FAIL: smoke tests red BEFORE deploy. Aborting." >&2
    echo "Pass --force to deploy anyway (e.g. emergency hotfix)." >&2
    exit 3
  fi
fi

# --- Diff git HEAD vs production via FTP ------------------------------------
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

ENV_UPLOAD_LOCAL=""
ENV_UPLOAD_REMOTE="live-monitor/api/.env"
if [ "$INCLUDE_ENV" -eq 1 ]; then
  if [ -f "live-monitor/api/.env" ]; then
    ENV_UPLOAD_LOCAL="$TMPDIR/live-monitor-api.env"
    cp "live-monitor/api/.env" "$ENV_UPLOAD_LOCAL"
  else
    if [ -z "${DB_STOCKS_PASSWORD:-}" ] || [ -z "${DB_SPORTS_PASSWORD:-}" ]; then
      echo "--include-env requires live-monitor/api/.env or both DB_STOCKS_PASSWORD + DB_SPORTS_PASSWORD in env." >&2
      exit 2
    fi
    ENV_UPLOAD_LOCAL="$TMPDIR/live-monitor-api.env"
    python3 - "$ENV_UPLOAD_LOCAL" "${DB_STOCKS_PASSWORD}" "${DB_SPORTS_PASSWORD}" <<'PY'
from pathlib import Path
import sys

out = Path(sys.argv[1])
stocks_pw = sys.argv[2]
sports_pw = sys.argv[3]

def q(v):
    return '"' + v.replace('\\', '\\\\').replace('"', '\\"') + '"'

out.write_text(
    "DB_STOCKS_PASSWORD=" + q(stocks_pw) + "\n" +
    "DB_SPORTS_PASSWORD=" + q(sports_pw) + "\n",
    encoding="utf-8",
)
PY
  fi
fi

CHANGED=()
for f in "${SPORTS_FILES[@]}"; do
  [ -f "$f" ] || continue
  remote_url="ftp://$FTP_HOST$REMOTE_BASE/$f"
  if ! curl --silent --max-time 30 --user "$FTP_USER:$FTP_PASS" -o "$TMPDIR/prod_$(basename "$f")" "$remote_url"; then
    echo "  miss $f (will upload as new)"
    CHANGED+=("$f")
    continue
  fi
  HASH_LOCAL=$(tr -d '\r' < "$f" | sha256sum | cut -d' ' -f1)
  HASH_PROD=$(tr -d '\r' < "$TMPDIR/prod_$(basename "$f")" | sha256sum | cut -d' ' -f1)
  if [ "$HASH_LOCAL" != "$HASH_PROD" ]; then
    echo "  DIFF $f"
    CHANGED+=("$f")
  else
    echo "  ok   $f"
  fi
done

if [ "${#CHANGED[@]}" -eq 0 ]; then
  echo "No changes to deploy. Production is in sync with git HEAD."
  exit 0
fi

echo
echo "=== Files to deploy (${#CHANGED[@]}) ==="
printf '  %s\n' "${CHANGED[@]}"
if [ "$INCLUDE_ENV" -eq 1 ]; then
  echo "  $ENV_UPLOAD_REMOTE (credential refresh)"
fi

if [ "$DRY_RUN" -eq 1 ]; then
  echo "--dry-run: skipping upload."
  exit 0
fi

# --- Upload --------------------------------------------------------------
echo
echo "=== Uploading via FTP ==="
FAILED=0
for f in "${CHANGED[@]}"; do
  if curl --silent --show-error --max-time 60 --user "$FTP_USER:$FTP_PASS" -T "$f" "ftp://$FTP_HOST$REMOTE_BASE/$f"; then
    echo "  OK $f"
  else
    echo "  FAIL $f" >&2
    FAILED=$((FAILED + 1))
  fi
done
if [ "$INCLUDE_ENV" -eq 1 ]; then
  if curl --silent --show-error --max-time 60 --user "$FTP_USER:$FTP_PASS" -T "$ENV_UPLOAD_LOCAL" "ftp://$FTP_HOST$REMOTE_BASE/$ENV_UPLOAD_REMOTE"; then
    echo "  OK $ENV_UPLOAD_REMOTE"
  else
    echo "  FAIL $ENV_UPLOAD_REMOTE" >&2
    FAILED=$((FAILED + 1))
  fi
fi
if [ "$FAILED" -gt 0 ]; then
  echo "$FAILED file(s) failed to upload." >&2
  exit 4
fi

# --- Post-deploy smoke (re-run, must still be green) ------------------------
echo
echo "=== Post-deploy smoke (live production) ==="
if ! python3 -m pytest tests/test_sports_endpoints_smoke.py -q --tb=line; then
  echo "FAIL: smoke RED after deploy. Production is broken — investigate immediately." >&2
  echo "Last-known-good FTP backups (if you took them) live at tmp/ftp_backup/." >&2
  exit 5
fi

echo
echo "=== Deploy complete. ${#CHANGED[@]} file(s) shipped, smoke green pre+post. ==="
