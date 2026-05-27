#!/usr/bin/env bash
#
# start_litellm_proxy.sh — boot the rotating-fallback LiteLLM proxy on :4000.
#
# Reads API keys from ~/dbpasses.txt (gitignored, outside repo), exports
# them into the LiteLLM child process env, then launches the proxy with
# litellm_config.yaml.
#
# Roo / Kilo / any OpenAI-SDK client points at:
#   base_url = http://localhost:4000
#   model    = hybrid-model
#   api_key  = anything   (LiteLLM accepts placeholder; real auth happens
#                          per-upstream from the keys we exported)
#
# Usage:
#   bash tools/start_litellm_proxy.sh                      # foreground
#   bash tools/start_litellm_proxy.sh --background         # nohup + log
#   bash tools/start_litellm_proxy.sh --port 5000          # alt port
#   ALLOW_PAID_SPILLOVER=0 bash tools/start_litellm_proxy.sh -b
#   PROXY_LOG=/tmp/litellm.log bash tools/start_litellm_proxy.sh -b
#
# Stop a backgrounded proxy: kill the PID printed at launch, or:
#   pkill -f 'litellm.*litellm_config'

set -euo pipefail

cd "$(dirname "$0")/.."

KEYS_FILE="${KEYS_FILE:-$HOME/dbpasses.txt}"
CONFIG="${CONFIG:-litellm_config.yaml}"
ALLOW_PAID_SPILLOVER="${ALLOW_PAID_SPILLOVER:-1}"
PORT="${PORT:-4000}"
BG=0
LOG="${PROXY_LOG:-/tmp/litellm_proxy.log}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --background|-b) BG=1; shift ;;
    --port)          PORT="$2"; shift 2 ;;
    --config)        CONFIG="$2"; shift 2 ;;
    --keys-file)     KEYS_FILE="$2"; shift 2 ;;
    -h|--help)
      sed -n '2,25p' "$0"
      exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ ! -f "$KEYS_FILE" ]]; then
  echo "ERROR: keys file not found: $KEYS_FILE" >&2
  exit 1
fi
if [[ ! -f "$CONFIG" ]]; then
  echo "ERROR: config not found: $CONFIG" >&2
  exit 1
fi
if [[ "$ALLOW_PAID_SPILLOVER" != "0" && "$ALLOW_PAID_SPILLOVER" != "1" ]]; then
  echo "ERROR: ALLOW_PAID_SPILLOVER must be 0 or 1 (got: $ALLOW_PAID_SPILLOVER)" >&2
  exit 2
fi

proxy_healthy() {
  python3 - "$PORT" << 'PY' >/dev/null 2>&1
import sys
import urllib.request

port = sys.argv[1]
url = f"http://127.0.0.1:{port}/health"
try:
    with urllib.request.urlopen(url, timeout=1.5) as resp:
        ok = (resp.getcode() == 200)
except Exception:
    ok = False
raise SystemExit(0 if ok else 1)
PY
}

if proxy_healthy; then
  echo "[litellm-proxy] already running on port ${PORT}; skipping restart."
  exit 0
fi

if pgrep -f "litellm --config" >/dev/null 2>&1; then
  echo "[litellm-proxy] litellm process already running; skipping restart."
  exit 0
fi

ensure_litellm_runtime() {
  if [[ -x .venv/bin/litellm ]]; then
    return 0
  fi

  echo "[litellm-proxy] runtime missing (.venv/bin/litellm). Bootstrapping..."

  if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 not found in PATH; cannot bootstrap LiteLLM runtime." >&2
    return 1
  fi

  if [[ ! -d .venv ]]; then
    echo "[litellm-proxy] creating virtualenv: .venv"
    python3 -m venv .venv
  fi

  echo "[litellm-proxy] installing litellm[proxy] into .venv (first run may take ~1-2 min)"
  .venv/bin/python -m pip install --upgrade pip >/dev/null
  .venv/bin/python -m pip install "litellm[proxy]"

  if [[ ! -x .venv/bin/litellm ]]; then
    echo "ERROR: bootstrap finished but .venv/bin/litellm still missing." >&2
    return 1
  fi

  echo "[litellm-proxy] runtime bootstrap complete."
}

ensure_litellm_runtime

# ---------------------------------------------------------------------------
# Runtime spillover policy switch
#   ALLOW_PAID_SPILLOVER=1 (default): free groups can fall back to paid groups.
#   ALLOW_PAID_SPILLOVER=0: free groups stay free-only; when free pools exhaust,
#                           requests can fail/wait instead of spending paid keys.
# ---------------------------------------------------------------------------
ACTIVE_CONFIG="$CONFIG"
if [[ "$ALLOW_PAID_SPILLOVER" == "0" ]]; then
  ACTIVE_CONFIG="/tmp/litellm_config.nospillover.${PORT}.$$.yaml"
  cp "$CONFIG" "$ACTIVE_CONFIG"

  python3 - "$ACTIVE_CONFIG" << 'PY'
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")

replacements = [
    (r'^(\s*-\s*hybrid-model:\s*)\[[^\]]*\]', r'\1["free-mode-large", "free-mode"]'),
    (r'^(\s*-\s*free-mode:\s*)\[[^\]]*\]', r'\1["free-mode-large"]'),
    (r'^(\s*-\s*free-mode-large:\s*)\[[^\]]*\]', r'\1["free-mode"]'),
    (r'^(\s*-\s*free-mode-fast:\s*)\[[^\]]*\]', r'\1["free-mode", "free-mode-large"]'),
    (r'^(\s*-\s*free-mode-tools:\s*)\[[^\]]*\]', r'\1["free-mode-fast", "free-mode", "free-mode-large"]'),
]

for pattern, repl in replacements:
    text = re.sub(pattern, repl, text, flags=re.MULTILINE)

path.write_text(text, encoding="utf-8")
PY

  echo "[litellm-proxy] paid spillover: DISABLED (ALLOW_PAID_SPILLOVER=0)"
else
  echo "[litellm-proxy] paid spillover: ENABLED (ALLOW_PAID_SPILLOVER=1)"
fi

# ---------------------------------------------------------------------------
# Parse keys from ~/dbpasses.txt (same label→value pattern as
# tools/consult_multi.py). Each ENV name maps to a label string in the file.
# ---------------------------------------------------------------------------
parse_key() {
  # $1=label, $2=env_var_to_set
  local label="$1" env="$2"
  local val
  # Trim trailing whitespace on both label-from-file and current line so
  # entries like "NOUS API KEY (USE ONLY FREE MODELS): " (trailing space)
  # still match the bare label we pass in. Without this, parse_key silently
  # drops keys whose label line has trailing whitespace.
  # Smart-skip sub-label lines after the main label. The file has patterns like
  #   GROK:
  #   GROK_SUPER             ← header, NOT the key
  #   xai-YwdFWzx...         ← actual key
  # Rules for what counts as a "value" line:
  #   - non-empty after trim
  #   - NOT a pure-uppercase identifier (skips GROK_SUPER, ANTR, CHUTES_API_KEY_FREE)
  #   - NOT ending in ':' (skips continuation labels)
  #   - NOT a URL (skips https://hypereal.cloud/-style annotation lines)
  val="$(awk -v lbl="$label" '
    { line=$0; sub(/[[:space:]]+$/, "", line) }
    line == lbl { found=1; next }
    found && NF > 0 {
      if (line ~ /^[A-Z][A-Z0-9_]*$/) next
      if (line ~ /:$/) next
      if (line ~ /^https?:/) next
      if (line ~ /^={2,}/) next
      print line; exit
    }
  ' "$KEYS_FILE")"
  if [[ -n "$val" ]]; then
    export "$env=$val"
  fi
}

parse_key "NVIDIA:"                                                                  NVIDIA_API_KEY
parse_key "NVIDIA ALT KEY:"                                                          NVIDIA_API_KEY_ALT
parse_key "GROQ FREE KEY:"                                                           GROQ_API_KEY
parse_key "GOOGLE GEMINI API KEY:"                                                   GEMINI_API_KEY
parse_key "GOOGLE GEMIINI API KEY ALT:"                                              GEMINI_API_KEY_ALT
parse_key "GOOGLE GEMINI API KEY ALT2:"                                              GEMINI_API_KEY_ALT2
parse_key "GITHUB MODELS API KEY:"                                                   GITHUB_MODELS_KEY
parse_key "TOGETHER AI API KEY:"                                                     TOGETHER_API_KEY
parse_key "CEREBRAS_FREE_API_KEY:"                                                   CEREBRAS_API_KEY
parse_key "COHERE_TRIAL_API_KEY"                                                    COHERE_API_KEY
parse_key "HUGGING_FACE_TOKEN"                                                       HF_API_TOKEN
parse_key "FIREWORKS FREE API KEY:"                                                  FIREWORKS_API_KEY
parse_key "DEEPINFRA API KEY:"                                                       DEEPINFRA_API_KEY
parse_key "DEEPINFRA API KEY ALT:"                                                   DEEPINFRA_API_KEY_ALT
parse_key "NOUS API KEY (USE ONLY FREE MODELS):"                                     NOUS_API_KEY
parse_key "MISTRAL API KEY:"                                                         MISTRAL_API_KEY
parse_key "AIMLAPI.COM"                                                              AIMLAPI_FREE_KEY
parse_key "HYPEREAL CLOUD API KEY:"                                                  HYPEREAL_API_KEY
parse_key "Cloudflare account iD:"                                                   CF_ACCOUNT_ID
parse_key "Cloudflare API key:"                                                      CF_API_TOKEN

# --- Alt keys (extra rotation slots for already-wired providers) ---
parse_key "GITHUB MODELS API KEY2:"                                                  GITHUB_MODELS_KEY2
parse_key "TOGETHER AI API KEY ALT:"                                                 TOGETHER_API_KEY_ALT
parse_key "FIREWORKS FREE API KEY ALT:"                                              FIREWORKS_API_KEY_ALT
parse_key "NOUS API KEY ALT USE ONLY FREE MODELS:"                                   NOUS_API_KEY_ALT
parse_key "MISTRAL API KEY ALT:"                                                     MISTRAL_API_KEY_ALT
parse_key "MISTRAL API KEY ALT2:"                                                    MISTRAL_API_KEY_ALT2
parse_key "AIMLAPIKEY PAID (\$20 limit):"                                            AIMLAPI_PAID_KEY
parse_key "HYPEREAL CLOUD API KEY 2:"                                                HYPEREAL_API_KEY_ALT
parse_key "HUGGING_FACE_TOKEN ALT(TRIED FINE GRAIN AND SETTING BUNCH OF CHECKBOXES):" HF_API_TOKEN_ALT
parse_key "HUGGINF_FACE TOKEN ALT2(READ):"                                           HF_API_TOKEN_READ

# --- New providers (file uses no-colon header style here) ---
parse_key "OPEN ROUTER API KEY"                                                      OPENROUTER_API_KEY
parse_key "OFOX_API_KEY"                                                             OFOX_AI_KEY
parse_key "GROK:"                                                                    XAI_API_KEY      # = GROK NEW (first under GROK:)
parse_key "GROK NEW2:"                                                               XAI_API_KEY_ALT  # second xAI key
parse_key "GROQ_API_KEY"                                                             GROQ_API_KEY_ALT # second Groq key (no-colon label, line 138)
parse_key "OLLAMA_CLOUD_KEY"                                                         OLLAMA_CLOUD_KEY
parse_key "ANTROPHIC"                                                                ANTHROPIC_API_KEY
parse_key "ANTR_MAY2026"                                                             ANTHROPIC_API_KEY_ALT
parse_key "DEEPSEEK_API"                                                             DEEPSEEK_API_KEY
parse_key "KIMI_MOONSHOT_APIKEY"                                                     MOONSHOT_API_KEY
parse_key "KIMI_MOONSHOT_APIKEY2"                                                    MOONSHOT_API_KEY_ALT
parse_key "SAMBANOVA_API_KEY:"                                                       SAMBANOVA_API_KEY
parse_key "OPENAI_KEY"                                                               OPENAI_API_KEY
parse_key "QWEN_API_KEY_PRO"                                                         QWEN_API_KEY
parse_key "CHUTES"                                                                   CHUTES_API_KEY
parse_key "LLM7_API_KEY_FREE"                                                        LLM7_API_KEY
parse_key "INCEPTION_AI_KEY"                                                         INCEPTION_API_KEY
parse_key "NOVITA API KEY:"                                                         NOVITA_API_KEY
parse_key "CURSOR_API_KEY"                                                           CURSOR_API_KEY
parse_key "KILOCODE_API_KEY"                                                         KILOCODE_API_KEY
parse_key "OPENCODE_API_KEY"                                                         OPENCODE_API_KEY
parse_key "BLUESMIND API KEY"                                                        BLUESMIND_API_KEY

# Assemble the full per-account Cloudflare Workers AI URL once so the litellm
# config can reference $CF_API_BASE (litellm's per-provider `account_id` param
# doesn't accept os.environ/... interpolation on the cloudflare provider).
if [[ -n "${CF_ACCOUNT_ID:-}" ]]; then
  export CF_API_BASE="https://api.cloudflare.com/client/v4/accounts/${CF_ACCOUNT_ID}/ai/v1"
fi

# Pre-flight: which keys did we successfully load?
loaded=0; total=0
for v in NVIDIA_API_KEY NVIDIA_API_KEY_ALT GROQ_API_KEY GEMINI_API_KEY GEMINI_API_KEY_ALT GEMINI_API_KEY_ALT2 \
         GITHUB_MODELS_KEY GITHUB_MODELS_KEY2 TOGETHER_API_KEY TOGETHER_API_KEY_ALT \
         CEREBRAS_API_KEY COHERE_API_KEY HF_API_TOKEN HF_API_TOKEN_ALT HF_API_TOKEN_READ \
         FIREWORKS_API_KEY FIREWORKS_API_KEY_ALT DEEPINFRA_API_KEY DEEPINFRA_API_KEY_ALT \
         NOUS_API_KEY NOUS_API_KEY_ALT MISTRAL_API_KEY MISTRAL_API_KEY_ALT MISTRAL_API_KEY_ALT2 \
         AIMLAPI_FREE_KEY AIMLAPI_PAID_KEY HYPEREAL_API_KEY HYPEREAL_API_KEY_ALT \
         CF_ACCOUNT_ID CF_API_TOKEN OPENROUTER_API_KEY OFOX_AI_KEY XAI_API_KEY \
         OLLAMA_CLOUD_KEY ANTHROPIC_API_KEY ANTHROPIC_API_KEY_ALT DEEPSEEK_API_KEY \
         MOONSHOT_API_KEY MOONSHOT_API_KEY_ALT OPENAI_API_KEY QWEN_API_KEY CHUTES_API_KEY LLM7_API_KEY \
         INCEPTION_API_KEY NOVITA_API_KEY CURSOR_API_KEY KILOCODE_API_KEY OPENCODE_API_KEY \
         BLUESMIND_API_KEY XAI_API_KEY_ALT GROQ_API_KEY_ALT; do
  total=$((total+1))
  if [[ -n "${!v:-}" ]]; then loaded=$((loaded+1)); fi
done
echo "[litellm-proxy] keys loaded: $loaded / $total"
echo "[litellm-proxy] config: $ACTIVE_CONFIG"
echo "[litellm-proxy] port:   $PORT"

# Record this restart in a history file so the monitor can correctly classify
# Roo "Connection error" diagnostics that coincide with restart windows.
RESTART_HISTORY="${RESTART_HISTORY:-/tmp/litellm_restart_history.jsonl}"
record_restart() {
  python3 -c "
import json, datetime
with open('$RESTART_HISTORY', 'a') as fh:
    fh.write(json.dumps({
        'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'pid': $1,
        'config': '$ACTIVE_CONFIG',
        'port': '$PORT',
    }) + '\n')
"
}

if [[ $BG -eq 1 ]]; then
  echo "[litellm-proxy] starting in background, log → $LOG"
  nohup .venv/bin/litellm --config "$ACTIVE_CONFIG" --port "$PORT" --num_workers 1 \
    > "$LOG" 2>&1 &
  PID=$!
  record_restart "$PID"
  echo "[litellm-proxy] PID: $PID  (kill with: kill $PID)"
  echo "[litellm-proxy] tail -f $LOG  to watch"
else
  record_restart "$$"
  exec .venv/bin/litellm --config "$ACTIVE_CONFIG" --port "$PORT" --num_workers 1
fi
