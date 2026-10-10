#!/usr/bin/env bash
#
# start_ai_servers.sh — idempotent bring-up of the LOCAL AI stack on the GX10.
#
# Services (each auto-skipped when already healthy):
#   vLLM        :8000   OpenAI-compatible GPU server (Qwen2.5-14B-Instruct)
#   Ollama      :11434  local + cloud model daemon
#   LiteLLM     :4000   rotating multi-provider proxy (cloud key pool)
#   Open WebUI  :3000   docker UI (opt-in, see --webui)
#
# Why this exists: the manual dance is error-prone — wrong model id, forgetting
# that vLLM's default --gpu-memory-utilization 0.85 reserves ~103 GB of the
# 121 GB unified memory (starving Ollama), forgetting the tool-call flags, and
# guessing when the server is actually ready. This script encodes all of it.
# See .claude/skills/startaiservers/SKILL.md.
#
# Usage:
#   bash tools/start_ai_servers.sh                       # start everything missing
#   bash tools/start_ai_servers.sh status                # health table only
#   bash tools/start_ai_servers.sh stop                  # stop vLLM + proxy (keep Ollama)
#   bash tools/start_ai_servers.sh restart
#   bash tools/start_ai_servers.sh --gpu-util 0.45       # more KV cache for vLLM
#   bash tools/start_ai_servers.sh --model Qwen/Qwen2.5-14B-Instruct
#   bash tools/start_ai_servers.sh --no-proxy --no-webui
#   bash tools/start_ai_servers.sh --webui               # also start Open WebUI
#   bash tools/start_ai_servers.sh --no-tools            # disable vLLM tool-calling flags
#
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VLLM_BIN="${VLLM_BIN:-$ROOT/.venv/bin/vllm}"
VLLM_MODEL="${VLLM_MODEL:-Qwen/Qwen2.5-14B-Instruct}"
VLLM_PORT="${VLLM_PORT:-8000}"
VLLM_MAXLEN="${VLLM_MAXLEN:-16384}"
# 0.3 => ~36 GB reserved, frees ~67 GB for Ollama. DO NOT use 0.85 (reserves ~103 GB).
GPU_UTIL="${GPU_UTIL:-0.3}"
VLLM_LOG="${VLLM_LOG:-/tmp/vllm_serve.log}"
OLLAMA_PORT="${OLLAMA_PORT:-11434}"
PROXY_PORT="${PROXY_PORT:-4000}"
WEBUI_PORT="${WEBUI_PORT:-3000}"

START_VLLM=1; START_OLLAMA=1; START_PROXY=1; START_WEBUI=0; USE_TOOLS=1

CMD="start"
if [[ $# -gt 0 && "$1" != -* ]]; then CMD="$1"; shift; fi
while [[ $# -gt 0 ]]; do
  case "$1" in
    --gpu-util)  GPU_UTIL="$2"; shift 2 ;;
    --model)     VLLM_MODEL="$2"; shift 2 ;;
    --max-len)   VLLM_MAXLEN="$2"; shift 2 ;;
    --port)      VLLM_PORT="$2"; shift 2 ;;
    --webui)     START_WEBUI=1; shift ;;
    --no-vllm)   START_VLLM=0; shift ;;
    --no-ollama) START_OLLAMA=0; shift ;;
    --no-proxy)  START_PROXY=0; shift ;;
    --no-tools)  USE_TOOLS=0; shift ;;
    -h|--help)   sed -n '2,32p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

# ---- health probes (fast, never block the caller) -------------------------
health_vllm()  { curl -sf -m 3 "http://127.0.0.1:${VLLM_PORT}/v1/models"   >/dev/null 2>&1; }
health_ollama(){ curl -sf -m 3 "http://127.0.0.1:${OLLAMA_PORT}/api/tags"  >/dev/null 2>&1; }
# NOTE: use /health/readiness, NOT /health — the latter runs live upstream checks
# and can hang for seconds (or timeout) when any provider is unreachable.
health_proxy() { curl -sf -m 3 "http://127.0.0.1:${PROXY_PORT}/health/readiness" >/dev/null 2>&1; }
health_webui() { curl -sf -m 3 "http://127.0.0.1:${WEBUI_PORT}/"           >/dev/null 2>&1; }

# wait_http URL [tries] — bounded readiness wait via curl retry (no `sleep`).
wait_http() {
  local url="$1" tries="${2:-60}"
  curl -s --retry "$tries" --retry-delay 3 --retry-connrefused -o /dev/null "$url" 2>/dev/null
}

# wait_down PROBE_FN [tries] — bounded wait until a service actually STOPS answering.
# Needed because right after `pkill` the dying process can still accept one more
# request, which would make a following start() think it's "already up".
# (The short sleep is shutdown synchronization, not idle polling.)
wait_down() {
  local fn="$1" tries="${2:-40}" i=0
  while (( i < tries )); do
    "$fn" || return 0
    sleep 0.5; i=$((i + 1))
  done
  return 1
}

# wait_pids_gone PATTERN [tries] — wait for matching processes to fully exit.
wait_pids_gone() {
  local pat="$1" tries="${2:-40}" i=0
  while (( i < tries )); do
    pgrep -f "$pat" >/dev/null 2>&1 || return 0
    sleep 0.5; i=$((i + 1))
  done
  return 1
}

vllm_pids() { pgrep -f "vllm serve" 2>/dev/null || true; }

# ---- starters -------------------------------------------------------------
start_vllm() {
  if health_vllm; then echo "  vLLM      :${VLLM_PORT}  already up"; return 0; fi
  if [[ -n "$(vllm_pids)" ]]; then
    echo "  vLLM      :${VLLM_PORT}  process running, waiting for readiness..."
    wait_http "http://127.0.0.1:${VLLM_PORT}/v1/models" 60 \
      && { echo "  vLLM      :${VLLM_PORT}  OK"; return 0; } \
      || { echo "  vLLM      still not ready — tail $VLLM_LOG" >&2; return 1; }
  fi
  [[ -x "$VLLM_BIN" ]] || { echo "  ERROR: vLLM binary not found: $VLLM_BIN" >&2; return 1; }

  local common=("$VLLM_BIN" serve "$VLLM_MODEL" --port "$VLLM_PORT" \
                --max-model-len "$VLLM_MAXLEN" --gpu-memory-utilization "$GPU_UTIL")
  local tool_flags=()
  if [[ "$USE_TOOLS" == "1" ]]; then
    # Qwen2/Qwen2.5 use the hermes tool-call parser in vLLM.
    tool_flags=(--enable-auto-tool-choice --tool-call-parser hermes)
  fi

  echo "  vLLM      :${VLLM_PORT}  starting ${VLLM_MODEL}"
  echo "            gpu-util=${GPU_UTIL} max-len=${VLLM_MAXLEN} tools=$USE_TOOLS log=${VLLM_LOG}"
  nohup "${common[@]}" "${tool_flags[@]}" > "$VLLM_LOG" 2>&1 &
  if wait_http "http://127.0.0.1:${VLLM_PORT}/v1/models" 100; then
    echo "  vLLM      :${VLLM_PORT}  OK"
    return 0
  fi
  # Tool flags can be unsupported on some model/parser combos — retry plain.
  if [[ "$USE_TOOLS" == "1" ]]; then
    echo "  vLLM      tool-call flags failed — retrying without them" >&2
    pkill -f "vllm serve" >/dev/null 2>&1 || true
    nohup "${common[@]}" > "$VLLM_LOG" 2>&1 &
    wait_http "http://127.0.0.1:${VLLM_PORT}/v1/models" 100 \
      && { echo "  vLLM      :${VLLM_PORT}  OK (no tool-calling)"; return 0; }
  fi
  echo "  vLLM      FAILED — inspect $VLLM_LOG" >&2
  return 1
}

start_ollama() {
  if health_ollama; then echo "  Ollama    :${OLLAMA_PORT}  already up"; return 0; fi
  command -v ollama >/dev/null 2>&1 || { echo "  Ollama    not installed — skipped" >&2; return 0; }
  echo "  Ollama    :${OLLAMA_PORT}  starting daemon"
  nohup ollama serve > /tmp/ollama_serve.log 2>&1 &
  wait_http "http://127.0.0.1:${OLLAMA_PORT}/api/tags" 15 \
    && echo "  Ollama    :${OLLAMA_PORT}  OK" \
    || echo "  Ollama    not ready — tail /tmp/ollama_serve.log" >&2
}

start_proxy() {
  if health_proxy; then echo "  LiteLLM   :${PROXY_PORT}  already up"; return 0; fi
  [[ -f "$ROOT/tools/start_litellm_proxy.sh" ]] || { echo "  LiteLLM   launcher missing — skipped" >&2; return 0; }
  echo "  LiteLLM   :${PROXY_PORT}  starting rotating proxy"
  bash "$ROOT/tools/start_litellm_proxy.sh" --background >/tmp/litellm_start.out 2>&1
  wait_http "http://127.0.0.1:${PROXY_PORT}/health/readiness" 40 \
    && echo "  LiteLLM   :${PROXY_PORT}  OK" \
    || echo "  LiteLLM   not ready — see /tmp/litellm_proxy.log" >&2
}

start_webui() {
  if health_webui; then echo "  OpenWebUI :${WEBUI_PORT}  already up"; return 0; fi
  if command -v docker >/dev/null 2>&1 && docker ps -a --format '{{.Names}}' 2>/dev/null | grep -qx 'open-webui'; then
    echo "  OpenWebUI :${WEBUI_PORT}  starting container"
    docker start open-webui >/dev/null 2>&1 || true
    wait_http "http://127.0.0.1:${WEBUI_PORT}/" 30 \
      && echo "  OpenWebUI :${WEBUI_PORT}  OK" \
      || echo "  OpenWebUI not ready" >&2
  else
    echo "  OpenWebUI container 'open-webui' not found — skipped" >&2
  fi
}

# ---- status / stop --------------------------------------------------------
show_status() {
  echo "LOCAL AI STACK — $(date '+%Y-%m-%d %H:%M:%S')"
  if health_vllm; then
    local m; m=$(curl -s -m 3 "http://127.0.0.1:${VLLM_PORT}/v1/models" \
      | python3 -c "import sys,json;print(','.join(d['id'] for d in json.load(sys.stdin)['data']))" 2>/dev/null)
    printf "  vLLM       :%s  UP    %s\n" "$VLLM_PORT" "${m:-?}"
  else
    printf "  vLLM       :%s  DOWN\n" "$VLLM_PORT"
  fi
  if health_ollama; then
    local n; n=$(curl -s -m 3 "http://127.0.0.1:${OLLAMA_PORT}/api/tags" \
      | python3 -c "import sys,json;print(len(json.load(sys.stdin).get('models',[])))" 2>/dev/null)
    printf "  Ollama     :%s  UP    %s models\n" "$OLLAMA_PORT" "${n:-?}"
  else
    printf "  Ollama     :%s  DOWN\n" "$OLLAMA_PORT"
  fi
  health_proxy && printf "  LiteLLM    :%s  UP\n" "$PROXY_PORT" || printf "  LiteLLM    :%s  DOWN\n" "$PROXY_PORT"
  health_webui && printf "  OpenWebUI  :%s  UP\n" "$WEBUI_PORT" || printf "  OpenWebUI  :%s  DOWN\n" "$WEBUI_PORT"
}

stop_all() {
  if [[ -n "$(vllm_pids)" ]]; then
    pkill -f "vllm serve" && echo "  stopping vLLM..."
    wait_down health_vllm 80 && wait_pids_gone "vllm serve" 40 || true
    echo "  stopped vLLM"
  else
    echo "  vLLM not running"
  fi
  if pgrep -f 'litellm.*litellm_config' >/dev/null 2>&1; then
    pkill -f 'litellm.*litellm_config' && echo "  stopping LiteLLM proxy..."
    wait_down health_proxy 60 || true
    echo "  stopped LiteLLM proxy"
  else echo "  LiteLLM not running"; fi
  echo "  (Ollama left running — stop with: sudo systemctl stop ollama)"
}

echo "=== Local AI stack: $CMD ==="
case "$CMD" in
  start)
    [[ "$START_OLLAMA" == "1" ]] && start_ollama
    [[ "$START_VLLM"   == "1" ]] && start_vllm
    [[ "$START_PROXY"  == "1" ]] && start_proxy
    [[ "$START_WEBUI"  == "1" ]] && start_webui
    echo; show_status
    ;;
  status)  show_status ;;
  stop)    stop_all ;;
  restart)
    stop_all; echo "--- restarting ---"
    [[ "$START_OLLAMA" == "1" ]] && start_ollama
    [[ "$START_VLLM"   == "1" ]] && start_vllm
    [[ "$START_PROXY"  == "1" ]] && start_proxy
    echo; show_status
    ;;
  *) echo "unknown command: $CMD (use start|stop|status|restart)" >&2; exit 2 ;;
esac
