#!/usr/bin/env bash
# ai_menu.sh — interactive launcher for the AI-development CLI tools installed on this box.
# Detects which executables are actually present, shows a status table, and launches
# the one you pick. Any extra args you type after the number are passed through to the tool.
#
# Each coding-agent CLI is launched in FULL-AUTONOMY mode by default: the tool's
# own "allow all commands without prompting" flag is auto-injected so you don't
# have to baby-sit approval prompts ("Do you want to run this command?"). Disable
# per-launch with --safe (or globally with AI_MENU_NO_YOLO=1). Flag map:
# `tools/ai_menu.sh --yolo-info`.
#
# Usage:
#   tools/ai_menu.sh             # interactive menu
#   tools/ai_menu.sh --list      # print detected tools and exit
#   tools/ai_menu.sh --yolo-info # show the auto-approve flag injected per tool
#   tools/ai_menu.sh <name>      # launch a tool directly by its menu key (e.g. ./ai_menu.sh claude)
#   tools/ai_menu.sh --safe <name>  # launch WITHOUT auto-approve (prompts restored)

set -uo pipefail

# key | command | description
TOOLS=(
  "claude|claude|Claude Code (Anthropic agentic CLI)"
  "command-code|command-code|Command-Code (Claude-Code-style agent)"
  "cursor|cursor-agent|Cursor headless agent"
  "opencode|opencode|OpenCode agentic coding CLI"
  "kilo|kilo|Kilo (OpenCode fork)"
  "codex|codex|OpenAI Codex CLI"
  "grok|grok|xAI Grok CLI"
  "gemini|gemini|Google Gemini CLI"
  "qwen|qwen|Qwen Code CLI"
  "copilot|copilot|GitHub Copilot CLI"
  "continue|continue|Continue agent CLI"
  "hermes|hermes|Hermes agent"
  "openclaude|openclaude|OpenClaude wrapper"
  "blackbox|blackbox|Blackbox AI CLI"
  "freebuff|freebuff|Freebuff agent CLI"
  "kimi|kimi|Kimi CLI"
  "agent|agent|Generic agent CLI"
  "freellm|FreeLLM|FreeLLM CLI"
  "browseruse|browser-use|Browser-Use automation agent"
  "ollama|ollama|Ollama local model runner"
)

# Repo-local commands (resolved relative to the git root, not PATH).
# key | relative-path | interpreter | description
REPO_ROOT="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel 2>/dev/null)"
PROJECT_CMDS=(
  "litellm|tools/start_litellm_proxy.sh|bash|Start LiteLLM rotating proxy (:4000)"
  "swarm|tools/swarm/swarm_run.py|python3|Multi-engine swarm fan-out"
  "consult|tools/swarm/api_consult.py|python3|Single-provider API consult"
)

# --- Full-autonomy ("YOLO") flag injection -------------------------------------
# Shared map: tools/ai_menu_yolo.inc.sh (also used by agent_run.sh).
# Opt OUT: tools/ai_menu.sh --safe claude  OR  AI_MENU_NO_YOLO=1 tools/ai_menu.sh
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=ai_menu_yolo.inc.sh
source "$SCRIPT_DIR/ai_menu_yolo.inc.sh"

C_RESET=$'\033[0m'; C_DIM=$'\033[2m'; C_GREEN=$'\033[32m'; C_RED=$'\033[31m'
C_BOLD=$'\033[1m'; C_CYAN=$'\033[36m'; C_YELLOW=$'\033[33m'

resolve() { command -v "$1" 2>/dev/null; }

print_list() {
  printf '%s%-3s %-12s %-9s %-40s %s%s\n' "$C_BOLD" "#" "KEY" "STATUS" "DESCRIPTION" "PATH" "$C_RESET"
  local i=1
  for entry in "${TOOLS[@]}"; do
    IFS='|' read -r key cmd desc <<< "$entry"
    local path; path="$(resolve "$cmd")"
    local auto=""; [[ -n "$(ai_menu_yolo_flags "$key")" ]] && auto=" ${C_YELLOW}[auto]${C_RESET}"
    if [[ -n "$path" ]]; then
      printf '%-3s %-12s %s%-9s%s %-40s%b %s%s%s\n' "$i" "$key" "$C_GREEN" "installed" "$C_RESET" "$desc" "$auto" "$C_DIM" "$path" "$C_RESET"
    else
      printf '%s%-3s %-12s %-9s %-40s (not found)%s\n' "$C_DIM" "$i" "$key" "missing" "$desc" "$C_RESET"
    fi
    ((i++))
  done
  echo "${C_DIM}-- repo commands --${C_RESET}"
  for entry in "${PROJECT_CMDS[@]}"; do
    IFS='|' read -r key rel interp desc <<< "$entry"
    local full="$REPO_ROOT/$rel"
    if [[ -n "$REPO_ROOT" && -f "$full" ]]; then
      printf '%-3s %-12s %s%-9s%s %-40s %s%s%s\n' "$i" "$key" "$C_GREEN" "available" "$C_RESET" "$desc" "$C_DIM" "$rel" "$C_RESET"
    else
      printf '%s%-3s %-12s %-9s %-40s (%s missing)%s\n' "$C_DIM" "$i" "$key" "missing" "$desc" "$rel" "$C_RESET"
    fi
    ((i++))
  done
  echo "${C_DIM}([auto] = launches in full-autonomy mode; --yolo-info for flags, --safe to disable)${C_RESET}"
}

print_yolo_info() {
  echo "${C_BOLD}Auto-approve (\"YOLO\") flags injected per tool:${C_RESET}"
  echo "${C_DIM}(disable for one launch with --safe, or globally with AI_MENU_NO_YOLO=1)${C_RESET}"
  local k
  for k in $(printf '%s\n' "${!AI_MENU_YOLO_FLAGS[@]}" | sort); do
    printf '  %-12s %s%s%s\n' "$k" "$C_GREEN" "${AI_MENU_YOLO_FLAGS[$k]}" "$C_RESET"
  done
  echo "${C_DIM}  opencode/kilo  (config-based: ~/.config/{opencode,kilo}/*.jsonc, set to allow)${C_RESET}"
}

run_project_cmd() {
  local entry="$1"; shift
  IFS='|' read -r key rel interp desc <<< "$entry"
  local full="$REPO_ROOT/$rel"
  if [[ -z "$REPO_ROOT" || ! -f "$full" ]]; then
    echo "${C_RED}'$rel' not found under repo root.${C_RESET}" >&2; return 1
  fi
  echo "${C_CYAN}Launching ${C_BOLD}$desc${C_RESET}${C_CYAN} -> $interp $rel $*${C_RESET}"
  exec "$interp" "$full" "$@"
}

launch_by_index() {
  local idx="$1"; shift
  local ntools=${#TOOLS[@]} nproj=${#PROJECT_CMDS[@]}
  if ! [[ "$idx" =~ ^[0-9]+$ ]] || (( idx < 1 || idx > ntools + nproj )); then
    echo "${C_RED}Invalid selection: $idx${C_RESET}" >&2; return 1
  fi
  if (( idx <= ntools )); then
    local entry="${TOOLS[$((idx-1))]}"
    IFS='|' read -r key cmd desc <<< "$entry"
    launch_cmd "$key" "$cmd" "$desc" "$@"
  else
    run_project_cmd "${PROJECT_CMDS[$((idx-ntools-1))]}" "$@"
  fi
}

launch_by_key() {
  local want="$1"; shift
  for entry in "${TOOLS[@]}"; do
    IFS='|' read -r key cmd desc <<< "$entry"
    if [[ "$key" == "$want" ]]; then
      launch_cmd "$key" "$cmd" "$desc" "$@"; return $?
    fi
  done
  for entry in "${PROJECT_CMDS[@]}"; do
    IFS='|' read -r key rel interp desc <<< "$entry"
    if [[ "$key" == "$want" ]]; then
      run_project_cmd "$entry" "$@"; return $?
    fi
  done
  echo "${C_RED}Unknown tool key: $want${C_RESET}" >&2; return 1
}

launch_cmd() {
  local key="$1" cmd="$2" desc="$3"; shift 3
  local path; path="$(resolve "$cmd")"
  if [[ -z "$path" ]]; then
    echo "${C_RED}'$cmd' is not installed on this machine.${C_RESET}" >&2; return 1
  fi
  local yolo; yolo="$(ai_menu_yolo_flags "$key")"
  if [[ -n "$yolo" ]]; then
    ai_menu_yolo_env "$key"
    echo "${C_YELLOW}auto-approve: injecting '${yolo}' (use --safe to disable)${C_RESET}"
    [[ "$key" == copilot && -n "${COPILOT_ALLOW_ALL:-}" ]] && \
      echo "${C_DIM}  COPILOT_ALLOW_ALL=1${C_RESET}"
  fi
  echo "${C_CYAN}Launching ${C_BOLD}$desc${C_RESET}${C_CYAN} -> $cmd $yolo $*${C_RESET}"
  # shellcheck disable=SC2086  # $yolo is intentionally word-split into separate flags
  exec "$cmd" $yolo "$@"
}

# --- entrypoint ---
# Consume a leading --safe / --no-yolo to disable auto-approve injection.
while [[ "${1:-}" == "--safe" || "${1:-}" == "--no-yolo" ]]; do
  AI_MENU_NO_YOLO=1
  shift
  echo "${C_DIM}(--safe: auto-approve injection disabled for this launch)${C_RESET}" >&2
done

case "${1:-}" in
  --list|-l) print_list; exit 0 ;;
  --yolo-info|--yolo) print_yolo_info; exit 0 ;;
  --help|-h) sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
  "" ) : ;;  # fall through to interactive menu
  * )
    # direct launch by key: ai_menu.sh claude --resume
    key="$1"; shift
    launch_by_key "$key" "$@"; exit $?
    ;;
esac

while true; do
  echo
  echo "${C_BOLD}${C_CYAN}=== AI Development CLI Launcher ===${C_RESET}"
  print_list
  echo
  read -r -p "${C_YELLOW}Select # to launch (extra args allowed), or q to quit: ${C_RESET}" choice rest || { echo; exit 0; }
  case "$choice" in
    q|Q|quit|exit|"") echo "Bye."; exit 0 ;;
    *) launch_by_index "$choice" $rest ;;  # exec replaces process on success
  esac
done
