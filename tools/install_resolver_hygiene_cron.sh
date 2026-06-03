#!/usr/bin/env bash
# Install daily resolver hygiene crontab line (idempotent check).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# Set AUDIT_DB_PASS in user crontab or ~/.profile; line below passes through if exported.
LINE="15 6 * * * cd ${ROOT} && export AUDIT_DB_PASS=\${AUDIT_DB_PASS:-\${DB_PASS_STOCKS:-stocks}} PYTHONPATH=${ROOT} && ./tools/run_daily_resolver_hygiene.sh >> ${ROOT}/logs/resolver_hygiene/cron.log 2>&1"
MARKER="# findtorontoevents resolver hygiene"

if [[ "${1:-}" == "--print" ]]; then
  echo "$LINE"
  exit 0
fi

mkdir -p "${ROOT}/logs/resolver_hygiene"
EXISTING="$(crontab -l 2>/dev/null || true)"
if echo "$EXISTING" | grep -Fq "$MARKER"; then
  echo "Cron already installed ($MARKER)"
  exit 0
fi
{
  echo "$EXISTING"
  echo ""
  echo "$MARKER"
  echo "$LINE"
} | crontab -
echo "Installed daily resolver hygiene cron (06:15 UTC)"
