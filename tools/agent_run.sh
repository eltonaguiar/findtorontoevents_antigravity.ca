#!/usr/bin/env bash
# tools/agent_run.sh — Non-interactive CLI wrapper for AI agents.
# Runs any repo tool without human intervention (auto-yes, auto-confirm).
#
# Usage:
#   tools/agent_run.sh <tool_key> [args...]     # launch by ai_menu key
#   tools/agent_run.sh python3 tools/script.py   # run any command
#   tools/agent_run.sh deploy                    # deploy audit files
#   tools/agent_run.sh litellm                   # start LiteLLM proxy
#   tools/agent_run.sh gateway                   # start cross-PC gateway
#   tools/agent_run.sh swarm <prompt>            # run swarm fan-out
#   tools/agent_run.sh consult <prompt>          # single API consult
#   tools/agent_run.sh verify                    # run all verification
#   tools/agent_run.sh backtest <strategy>       # run backtest
#   tools/agent_run.sh monitor                   # run quant monitor
#   tools/agent_run.sh mutation                  # run mutation scan
#
# This wrapper:
#   - Passes --yes / --non-interactive to any tool that supports it
#   - Sets DEBIAN_FRONTEND=noninteractive for apt
#   - Pipes 'yes' to any remaining interactive prompts
#   - Logs all commands to /tmp/agent_run.log

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG="/tmp/agent_run.log"
TIMESTAMP="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"

# Force non-interactive everywhere
export DEBIAN_FRONTEND=noninteractive
export GIT_TERMINAL_PROMPT=0
export GCM_INTERACTIVE=never
export HOMEBREW_NO_AUTO_UPDATE=1

log() { echo "[$TIMESTAMP] $*" >> "$LOG"; }

# Auto-inject --yes into commands that support it
auto_yes() {
  local cmd="$*"
  # Add --yes if command contains a known flag pattern and doesn't already have it
  if [[ "$cmd" =~ (cleanup_ghost_rows|audit_won_picks|deploy_audit|deploy_sports) ]] && [[ ! "$cmd" =~ (--yes|--dry-run) ]]; then
    cmd="$cmd --yes"
  fi
  echo "$cmd"
}

run_cmd() {
  local cmd="$1"
  shift
  log "RUN: $cmd $*"
  
  case "$cmd" in
    # --- AI Menu keys ---
    claude|cursor|opencode|kilo|codex|grok|gemini|qwen|copilot|hermes|blackbox|freebuff|kimi)
      exec "$cmd" "$@"
      ;;
    
    # --- Project commands ---
    litellm)
      cd "$REPO_ROOT"
      exec bash tools/start_litellm_proxy.sh --background "$@"
      ;;
    
    gateway)
      echo "Gateway is managed on the desktop (192.168.2.32:8788). Cannot start from peer."
      echo "Check health: curl -s http://192.168.2.32:8788/health"
      exit 1
      ;;
    
    swarm)
      cd "$REPO_ROOT"
      exec python3 tools/swarm/swarm_run.py "$@"
      ;;
    
    consult)
      cd "$REPO_ROOT"
      exec python3 tools/swarm/api_consult.py "$@"
      ;;
    
    deploy)
      cd "$REPO_ROOT"
      local real_cmd
      real_cmd=$(auto_yes "python3 tools/deploy_audit_files.py")
      exec $real_cmd "$@"
      ;;
    
    deploy-sports)
      cd "$REPO_ROOT"
      local real_cmd
      real_cmd=$(auto_yes "bash tools/deploy_sports_files.sh")
      exec $real_cmd "$@"
      ;;
    
    verify)
      cd "$REPO_ROOT"
      echo "=== Running verification pipeline ==="
      python3 verified_strategies/verification_runner.py "$@"
      echo "=== Running quant monitor ==="
      python3 verified_strategies/quant_monitor.py "$@"
      echo "=== Done ==="
      ;;
    
    backtest)
      cd "$REPO_ROOT"
      if [[ -z "${1:-}" ]]; then
        echo "Usage: agent_run.sh backtest <strategy_name>"
        exit 1
      fi
      python3 verified_strategies/verification_runner.py --strategy "$1" "${@:2}"
      ;;
    
    monitor)
      cd "$REPO_ROOT"
      exec python3 verified_strategies/quant_monitor.py "$@"
      ;;
    
    mutation)
      cd "$REPO_ROOT"
      exec python3 -c "
import json
from collections import defaultdict
from verified_strategies.mutation_framework import run_full_mutation_scan
with open('audit_dashboard/data/dashboard_data.json') as f:
    data = json.load(f)
closed = data['picks']['recent_closed']
trades_by_strat = defaultdict(list)
for p in closed:
    trades_by_strat[p.get('strategy', 'unknown')].append(p)
results = run_full_mutation_scan(trades_by_strat)
for r in results[:10]:
    print(f'{r.strategy_name:35s} {r.axis.value:20s} PF {r.original_pf:.2f} -> {r.mutated_pf:.2f} {r.verdict}')
"
      ;;
    
    eagle)
      cd "$REPO_ROOT"
      exec python3 tools/run_eagle_suite.py "$@"
      ;;
    
    freshness)
      cd "$REPO_ROOT"
      exec python3 tools/db_freshness_check.py "$@"
      ;;
    
    resolver)
      cd "$REPO_ROOT"
      exec python3 tools/check_resolver_health.py "$@"
      ;;
    
    money-ready)
      cd "$REPO_ROOT"
      exec python3 tools/money_ready_snapshot.py "$@"
      ;;
    
    # --- Direct command pass-through ---
    python3|python|bash|sh|node|npm|npx|git|curl|pip)
      log "DIRECT: $cmd $*"
      exec "$cmd" "$@"
      ;;
    
    # --- Try as Python script ---
    *.py)
      cd "$REPO_ROOT"
      local real_cmd
      real_cmd=$(auto_yes "python3 $cmd")
      exec $real_cmd "$@"
      ;;
    
    # --- Try as shell script ---
    *.sh)
      cd "$REPO_ROOT"
      local real_cmd
      real_cmd=$(auto_yes "bash $cmd")
      exec $real_cmd "$@"
      ;;
    
    *)
      echo "Unknown command: $cmd"
      echo "Available keys: claude, cursor, opencode, kilo, codex, grok, gemini, qwen, copilot, hermes, blackbox, freebuff, kimi"
      echo "Available cmds: litellm, gateway, swarm, consult, deploy, deploy-sports, verify, backtest, monitor, mutation, eagle, freshness, resolver, money-ready"
      echo "Or run directly: agent_run.sh python3 tools/script.py"
      exit 1
      ;;
  esac
}

# --- Main ---
if [[ $# -eq 0 ]]; then
  echo "Usage: tools/agent_run.sh <command> [args...]"
  echo ""
  echo "Quick commands:"
  echo "  verify          Run verification pipeline + quant monitor"
  echo "  monitor         Run quant health checks"
  echo "  mutation        Run mutation scan on failing strategies"
  echo "  deploy          Deploy audit files to production"
  echo "  eagle           Run EAGLE daily suite"
  echo "  litellm         Start LiteLLM proxy"
  echo "  swarm <prompt>  Run multi-engine swarm"
  echo "  consult <prompt> Single API consult"
  echo ""
  echo "AI agents: claude, cursor, opencode, kilo, codex, grok, gemini, qwen, copilot, hermes"
  echo ""
  echo "Any command: tools/agent_run.sh python3 tools/script.py --flag arg"
  exit 0
fi

CMD="$1"
shift
run_cmd "$CMD" "$@"
