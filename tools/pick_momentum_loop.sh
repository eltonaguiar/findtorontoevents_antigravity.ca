#!/usr/bin/env bash
# Run pick_quality_pulse on an interval (default 20m). Logs to reports/pick_momentum_loop.log
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
INTERVAL_SEC="${INTERVAL_SEC:-1200}"
MAX_RUNS="${MAX_RUNS:-0}"
LOG="${PICK_MOMENTUM_LOG:-$ROOT/reports/pick_momentum_loop.log}"
mkdir -p "$(dirname "$LOG")"
run=0
echo "[pick_momentum_loop] start $(date -u +%Y-%m-%dT%H:%M:%SZ) interval=${INTERVAL_SEC}s" | tee -a "$LOG"
while true; do
  run=$((run + 1))
  echo "[pick_momentum_loop] tick $run $(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$LOG"
  python3 tools/pick_quality_pulse.py >>"$LOG" 2>&1 || echo "[pick_momentum_loop] pulse FAILED" | tee -a "$LOG"
  if [[ "$MAX_RUNS" -gt 0 && "$run" -ge "$MAX_RUNS" ]]; then
    break
  fi
  sleep "$INTERVAL_SEC"
done