#!/usr/bin/env bash
# Daily resolver hygiene — file sources + MySQL OPEN/ACTIVE stale closes.
# Run from repo root via cron (requires AUDIT_DB_PASS or DB_PASS_STOCKS).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${ROOT}${PYTHONPATH:+:$PYTHONPATH}"
PY="${PYTHON:-python3}"
LOG_DIR="${ROOT}/logs/resolver_hygiene"
mkdir -p "$LOG_DIR"
STAMP="$(date -u +%Y%m%dT%H%MZ)"
LOG="${LOG_DIR}/run_${STAMP}.log"
{
  echo "=== resolver hygiene ${STAMP} ==="
  "$PY" audit_trail/universal_pick_resolver.py
  # Full live-set scan (OFFSET pagination; do not cap with max-batches)
  "$PY" tools/resolve_stale_open_picks.py --execute --batch-size 500
  PYTHONPATH="$ROOT" "$PY" alpha_engine/outcome_resolver.py --mysql
  "$PY" tools/check_resolver_health.py 2>&1 | tail -25
  "$PY" tools/run_verified_pilots_daily.py
} >>"$LOG" 2>&1
echo "Wrote $LOG"
