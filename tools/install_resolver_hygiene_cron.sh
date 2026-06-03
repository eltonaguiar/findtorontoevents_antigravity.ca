#!/usr/bin/env bash
# Install daily resolver hygiene crontab line (idempotent; --force replaces existing).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MARKER="# findtorontoevents resolver hygiene"
LINE="15 6 * * * cd ${ROOT} && ./tools/run_daily_resolver_hygiene.sh >> ${ROOT}/logs/resolver_hygiene/cron.log 2>&1"

if [[ "${1:-}" == "--print" ]]; then
  echo "$MARKER"
  echo "$LINE"
  exit 0
fi

mkdir -p "${ROOT}/logs/resolver_hygiene"
EXISTING="$(crontab -l 2>/dev/null || true)"

if echo "$EXISTING" | grep -Fq "$MARKER"; then
  if [[ "${1:-}" != "--force" ]]; then
    echo "Cron already installed ($MARKER). Use --force to replace."
    exit 0
  fi
  EXISTING="$(echo "$EXISTING" | awk -v m="$MARKER" '
    $0 == m { skip=1; next }
    skip && /^[0-9*]/ { skip=0 }
    skip && $0 ~ /^[0-9*]/ { skip=0 }
    skip && $0 == "" { skip=0; next }
    skip { next }
    { print }
  ')"
fi

{
  echo "$EXISTING"
  echo ""
  echo "$MARKER"
  echo "$LINE"
} | crontab -
echo "Installed daily resolver hygiene cron (06:15 UTC)"
echo "DB password: loaded inside run_daily_resolver_hygiene.sh from ~/dbpasses.txt if env unset"
