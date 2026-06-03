#!/usr/bin/env bash
# Restart pick_momentum + eagle2 operator loops when they exit (e.g. IDE max_runtime ~10h).
# Run on the desktop in tmux — not inside a short-lived agent harness:
#   tmux new -s ops
#   cd /path/to/repo && tools/operator_loops_supervisor.sh
#
# Env:
#   PICK_INTERVAL_SEC=1200   pick_quality_pulse cadence
#   EAGLE_INTERVAL_SEC=3600  run_eagle_suite light cadence
#   EAGLE_LOOP_FULL=1        passed to eagle2_operator_loop.sh
#   SUPERVISOR_SLEEP_SEC=30  delay between restart checks
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
LOG="${OPERATOR_SUPERVISOR_LOG:-$ROOT/reports/operator_loops_supervisor.log}"
mkdir -p "$(dirname "$LOG")"
PICK_INTERVAL_SEC="${PICK_INTERVAL_SEC:-1200}"
EAGLE_INTERVAL_SEC="${EAGLE_INTERVAL_SEC:-3600}"
SLEEP_SEC="${SUPERVISOR_SLEEP_SEC:-30}"

log() { echo "[operator_supervisor] $(date -u +%Y-%m-%dT%H:%M:%SZ) $*" | tee -a "$LOG"; }

start_pick() {
  INTERVAL_SEC="$PICK_INTERVAL_SEC" nohup "$ROOT/tools/pick_momentum_loop.sh" \
    >>"${PICK_MOMENTUM_LOG:-$ROOT/reports/pick_momentum_loop.log}" 2>&1 &
  echo $! >"$ROOT/reports/.pick_momentum_loop.pid"
  log "started pick_momentum_loop pid=$(cat "$ROOT/reports/.pick_momentum_loop.pid")"
}

start_eagle() {
  export INTERVAL_SEC="$EAGLE_INTERVAL_SEC"
  export EAGLE_LOOP_FULL="${EAGLE_LOOP_FULL:-0}"
  export EAGLE_LOOP_GIT_PULL="${EAGLE_LOOP_GIT_PULL:-0}"
  nohup "$ROOT/tools/eagle2_operator_loop.sh" \
    >>"${EAGLE_LOOP_LOG:-$ROOT/reports/eagle2_operator_loop.log}" 2>&1 &
  echo $! >"$ROOT/reports/.eagle2_operator_loop.pid"
  log "started eagle2_operator_loop pid=$(cat "$ROOT/reports/.eagle2_operator_loop.pid") full=${EAGLE_LOOP_FULL}"
}

alive() {
  local pidfile="$1"
  [[ -f "$pidfile" ]] || return 1
  local pid; pid="$(cat "$pidfile" 2>/dev/null)" || return 1
  kill -0 "$pid" 2>/dev/null
}

log "supervisor start pick=${PICK_INTERVAL_SEC}s eagle=${EAGLE_INTERVAL_SEC}s"
start_pick
start_eagle

while true; do
  if ! alive "$ROOT/reports/.pick_momentum_loop.pid"; then
    log "pick_momentum_loop not running — restarting"
    start_pick
  fi
  if ! alive "$ROOT/reports/.eagle2_operator_loop.pid"; then
    log "eagle2_operator_loop not running — restarting"
    start_eagle
  fi
  sleep "$SLEEP_SEC"
done