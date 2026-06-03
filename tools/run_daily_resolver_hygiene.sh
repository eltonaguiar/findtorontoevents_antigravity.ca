#!/usr/bin/env bash
# Daily resolver hygiene — file sources + MySQL OPEN/ACTIVE stale closes.
# Run from repo root via cron. DB pass: AUDIT_DB_PASS / DB_PASS_STOCKS env, else ~/dbpasses.txt.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${ROOT}${PYTHONPATH:+:$PYTHONPATH}"
PY="${PYTHON:-python3}"

# Cron has no shell profile — load stocks password when env unset.
if [[ -z "${AUDIT_DB_PASS:-}" && -z "${DB_PASS_STOCKS:-}" ]]; then
  _pw="$("$PY" -c "
from pathlib import Path
p = Path.home() / 'dbpasses.txt'
if not p.exists():
    raise SystemExit(0)
lines = p.read_text().splitlines()
for i, line in enumerate(lines):
    if line.strip() == 'ejaguiar1_stocks' and i + 1 < len(lines):
        print(lines[i + 1].strip())
        break
else:
    if lines:
        print(lines[0].strip())
" 2>/dev/null || true)"
  if [[ -n "${_pw:-}" ]]; then
    export AUDIT_DB_PASS="$_pw" DB_PASS_STOCKS="$_pw"
  fi
fi
LOG_DIR="${ROOT}/logs/resolver_hygiene"
mkdir -p "$LOG_DIR"
STAMP="$(date -u +%Y%m%dT%H%MZ)"
LOG="${LOG_DIR}/run_${STAMP}.log"
{
  echo "=== resolver hygiene ${STAMP} ==="
  "$PY" audit_trail/universal_pick_resolver.py
  # Full live-set scan (OFFSET pagination; do not cap with max-batches)
  "$PY" tools/resolve_stale_open_picks.py --execute --batch-size 500 --max-batches 30
  PYTHONPATH="$ROOT" "$PY" alpha_engine/outcome_resolver.py --mysql
  "$PY" tools/check_resolver_health.py 2>&1 | tail -25
  "$PY" tools/run_verified_pilots_daily.py
} >>"$LOG" 2>&1
echo "Wrote $LOG"
