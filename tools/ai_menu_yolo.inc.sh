# Shared auto-approve ("YOLO") flags for tools/ai_menu.sh and tools/agent_run.sh.
# shellcheck shell=bash
# Usage:
#   source "$(dirname "$0")/ai_menu_yolo.inc.sh"
#   flags="$(ai_menu_yolo_flags copilot)"   # -> --allow-all
#   exec copilot $flags "$@"

if [[ -z "${AI_MENU_YOLO_FLAGS+x}" ]]; then
  declare -gA AI_MENU_YOLO_FLAGS=(
    [claude]="--dangerously-skip-permissions"
    [command-code]="--yolo --skip-onboarding --trust"
    [cursor]="--force --approve-mcps"
    [agent]="--force --approve-mcps"
    [codex]="--dangerously-bypass-approvals-and-sandbox"
    [grok]="--always-approve"
    [gemini]="--yolo"
    [qwen]="--yolo"
    [copilot]="--allow-all"
    [openclaude]="--dangerously-skip-permissions"
    [blackbox]="--yolo"
    [kimi]="--yolo"
  )
fi

ai_menu_yolo_flags() {
  local key="$1"
  if [[ "${AI_MENU_NO_YOLO:-0}" == "1" ]]; then
    return 0
  fi
  printf '%s' "${AI_MENU_YOLO_FLAGS[$key]:-}"
}

ai_menu_yolo_env() {
  local key="$1"
  case "$key" in
    copilot) export COPILOT_ALLOW_ALL=1 ;;
  esac
  export AI_MENU_LAUNCHED=1
}