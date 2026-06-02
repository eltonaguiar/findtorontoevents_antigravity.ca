#!/usr/bin/env bash
# EAGLE2 operator loop — runs real refresh steps (replaces no-op AGENT_LOOP_TICK echo loop).
#
# Default: light tick every 3600s (money_ready + pulse + pilots, no LLM swarm).
# Full swarm (verify_best_picks + eagle_swarm_synthesis): EAGLE_LOOP_FULL=1
# Git pull before each tick: EAGLE_LOOP_GIT_PULL=1
#
# Usage:
#   tools/eagle2_operator_loop.sh              # loop forever
#   MAX_RUNS=1 tools/eagle2_operator_loop.sh   # one tick smoke test
#   INTERVAL_SEC=1200 EAGLE_LOOP_FULL=1 tools/eagle2_operator_loop.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
INTERVAL_SEC="${INTERVAL_SEC:-3600}"
MAX_RUNS="${MAX_RUNS:-0}"
LOG="${EAGLE_LOOP_LOG:-$ROOT/reports/eagle2_operator_loop.log}"
mkdir -p "$(dirname "$LOG")"

run=0
echo "[eagle2_operator_loop] start $(date -u +%Y-%m-%dT%H:%M:%SZ) interval=${INTERVAL_SEC}s full=${EAGLE_LOOP_FULL:-0} git_pull=${EAGLE_LOOP_GIT_PULL:-0}" | tee -a "$LOG"

while true; do
  run=$((run + 1))
  echo "[eagle2_operator_loop] tick $run $(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$LOG"

  if [[ "${EAGLE_LOOP_GIT_PULL:-0}" == "1" ]]; then
    git pull --ff-only origin main >>"$LOG" 2>&1 || echo "[eagle2_operator_loop] git pull FAILED" | tee -a "$LOG"
  fi

  suite_args=(--skip-swarm)
  if [[ "${EAGLE_LOOP_FULL:-0}" == "1" ]]; then
    suite_args=()
  fi
  if python3 tools/run_eagle_suite.py "${suite_args[@]}" >>"$LOG" 2>&1; then
    :
  else
    echo "[eagle2_operator_loop] run_eagle_suite FAILED" | tee -a "$LOG"
  fi

  if [[ "${EAGLE_LOOP_TEST_LITELLM:-0}" == "1" ]]; then
    for model in ollama-cloud-large ollama-cloud ollama-cloud-local hybrid-model; do
      echo "[eagle2_operator_loop] litellm probe $model" | tee -a "$LOG"
      python3 -c "
import urllib.request, json, sys
req = urllib.request.Request(
    'http://127.0.0.1:4000/v1/chat/completions',
    data=json.dumps({'model': sys.argv[1], 'messages': [{'role': 'user', 'content': 'ping'}], 'max_tokens': 8}).encode(),
    headers={'Content-Type': 'application/json'},
    method='POST',
)
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print('ok', r.status)
except Exception as e:
    print('fail', e)
" "$model" >>"$LOG" 2>&1 || true
    done
  fi

  if [[ "$MAX_RUNS" -gt 0 && "$run" -ge "$MAX_RUNS" ]]; then
    break
  fi
  sleep "$INTERVAL_SEC"
done