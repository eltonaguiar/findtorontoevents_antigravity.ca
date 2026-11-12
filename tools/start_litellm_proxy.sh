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

# Liveness probe. MUST be /health/readiness, NOT /health: /health fans out to
# every deployment in the config and routinely exceeds a short timeout, so the
# old probe reported "not running" while the proxy was serving fine. That
# false negative is how two processes ended up competing for :4000.
proxy_healthy() {
  python3 - "$PORT" << 'PY' >/dev/null 2>&1
import sys
import urllib.request

port = sys.argv[1]
url = f"http://127.0.0.1:{port}/health/readiness"
try:
    with urllib.request.urlopen(url, timeout=1.5) as resp:
        ok = (resp.getcode() == 200)
except Exception:
    ok = False
raise SystemExit(0 if ok else 1)
PY
}

# --- serialize concurrent starts --------------------------------------------
# Two agents retrying at once BOTH pass the guards below during the 60-180s
# dynamic-discovery window (nothing is listening yet AND no litellm process
# exists yet), then both launch: the first wins :$PORT and LiteLLM silently
# rebinds the second to a random port (proxy_cli.py:1047-1048). A lock makes the
# second caller wait for the first instead of racing it. Released when this
# script exits; the long-lived child gets fd 9 closed so it cannot hold it.
LOCK_FILE="${LITELLM_START_LOCK:-/tmp/litellm_start_${PORT}.lock}"
exec 9>"$LOCK_FILE"
if command -v flock >/dev/null 2>&1; then
  if ! flock -w "${LITELLM_START_LOCK_WAIT:-300}" 9; then
    echo "[litellm-proxy] another start is still in progress after ${LITELLM_START_LOCK_WAIT:-300}s (lock: $LOCK_FILE); not starting a second instance." >&2
    exit 75
  fi
fi

port_in_use() {
  ss -ltn 2>/dev/null | awk -v p=":$1" '$4 ~ p"$" {found=1} END{exit !found}'
}

listener_port_for_pid() {
  ss -ltnp 2>/dev/null | awk -v pid="pid=$1," '$0 ~ pid {n=split($4,a,":"); print a[n]; exit}'
}

if proxy_healthy; then
  echo "[litellm-proxy] already running on port ${PORT}; skipping restart."
  exit 0
fi

# A port held by a wedged / non-responsive process is the one case where
# launching is actively harmful: LiteLLM would dodge to a random port and every
# client would keep seeing "connection refused" on $PORT. Refuse, and say why.
if port_in_use "$PORT"; then
  echo "ERROR: port ${PORT} is already bound but /health/readiness did not answer 200." >&2
  echo "       LiteLLM would silently rebind to a random port instead of failing," >&2
  echo "       so this launcher refuses to start. Inspect with:" >&2
  echo "         ss -ltnp | grep ':${PORT}'" >&2
  exit 1
fi

# Guard on an actual LISTENING litellm socket, not on `pgrep -f "litellm --config"`.
# That pattern matches any shell whose command line merely MENTIONS the string --
# including the very command used to start the proxy -- so the launcher told itself
# "already running" and exited 0 without starting anything. Observed 2026-11-12:
# systemd ExecStart exited SUCCESS in 103ms with nothing listening on :4000.
if ss -ltnp 2>/dev/null | grep -q 'users:(("litellm"'; then
  echo "[litellm-proxy] a litellm listener already exists; skipping restart:"
  ss -ltnp 2>/dev/null | grep 'users:(("litellm"' | sed 's/^/    /' >&2
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
  # Trim BOTH leading and trailing whitespace so labels under sections like
  # "==PAID_APIS==" (which are indented with 2 spaces: "  XIAOMI_MIMO_TOKEN_PLAN",
  # "  ANTROPHIC") still match the bare labels passed to parse_key.
  # Also handles trailing spaces on labels like "NOUS API KEY ...: ".
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
    { line=$0; gsub(/^[ \t]+|[ \t]+$/, "", line) }
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
# Label FIXED 2026-11-12: dbpasses spells this "OPEN ROUTER API KEY (OPENROUTER)" and
# parse_key() matches whole lines, so the old "OPEN ROUTER API KEY" never matched. The
# result was silent: OPENROUTER_API_KEY was never exported, and every openrouter/*:free
# deployment returned 401 "No cookie auth credentials found" (seen as
# ULTRA_FREE_CLOUD_TOOLS failing its whole group). Keep the parenthetical.
parse_key "OPEN ROUTER API KEY (OPENROUTER)"                                          OPENROUTER_API_KEY
parse_key "OFOX_API_KEY"                                                             OFOX_AI_KEY
parse_key "GROK:"                                                                    XAI_API_KEY      # = GROK NEW (first under GROK:)
parse_key "GROK NEW2:"                                                               XAI_API_KEY_ALT  # second xAI key
parse_key "GROQ_API_KEY"                                                             GROQ_API_KEY_ALT # second Groq key (no-colon label, line 138)
parse_key "OLLAMA_CLOUD_KEY"                                                         OLLAMA_CLOUD_KEY
parse_key "ANTROPHIC"                                                                ANTHROPIC_API_KEY
parse_key "ANTR_MAY2026"                                                             ANTHROPIC_API_KEY_ALT
parse_key "DEEPSEEK_API"                                                             DEEPSEEK_API_KEY
parse_key "XIAOMI_MIMO_TOKEN_PLAN"                                                   XIAOMI_MIMO_TOKEN_PLAN
parse_key "KIMI_MOONSHOT_APIKEY"                                                     MOONSHOT_API_KEY
parse_key "KIMI_MOONSHOT_APIKEY2"                                                    MOONSHOT_API_KEY_ALT
parse_key "SAMBANOVA_API_KEY:"                                                       SAMBANOVA_API_KEY
parse_key "OPENAI_KEY"                                                               OPENAI_API_KEY
parse_key "QWEN_API_KEY_PRO"                                                         QWEN_API_KEY
parse_key "CHUTES"                                                                   CHUTES_API_KEY
parse_key "LLM7_API_KEY_FREE"                                                        LLM7_API_KEY
parse_key "NOVITA API KEY:"                                                         NOVITA_API_KEY
parse_key "CURSOR_API_KEY"                                                           CURSOR_API_KEY
parse_key "KILOCODE_API_KEY"                                                         KILOCODE_API_KEY
parse_key "OPENCODE_API_KEY"                                                         OPENCODE_API_KEY
# The 'OPENCODE_API_KEY' label above holds a DEAD key (api_key_expired, verified
# 2026-11-12). The live OpenCode Zen credential is filed under
# OPENCODE_OPENAI_KEY_NOV112026 — it was previously mislabelled as an OpenAI key,
# which is why it looked like an OpenAI credential. parse_key() matches whole
# lines, so this does not collide with "OPENAI_KEY". Added AFTER the stale line
# so it wins.
parse_key "OPENCODE_OPENAI_KEY_NOV112026"                                            OPENCODE_API_KEY
# Backup OpenCode Zen credential. Same account tier as the primary: /models 200,
# free ids 429 FreeUsageLimit, paid ids 402. Wired so it is picked up the moment
# either account is funded or the free gate lifts.
parse_key "OPENCODE_API_KEY_ALT"                                                     OPENCODE_API_KEY_ALT
parse_key "BLUESMIND API KEY"                                                        BLUESMIND_API_KEY
parse_key "DEEPINFRA API KEY_BEST:"                                                   DEEPINFRA_API_KEY_BEST
parse_key "KIMI AI API KEY part of PROJECT:"                                          KIMI_PLATFORM_API_KEY
parse_key "OLLAMA_ALT"                                                                OLLAMA_CLOUD_TOKEN

# --- Free-tier credentials present in dbpasses.txt but never exported (added 2026-11-12) ---
# parse_key() matches the label as a WHOLE LINE, so exact spelling matters,
# including the trailing spaces inside some labels below.
parse_key "SILICONFLOW.com API KEY:"                                            SILICONFLOW_API_KEY
parse_key "PUBLIC AI KEY"                                                       PUBLICAI_API_KEY
parse_key "HYPERBOLIC API KEY :"                                                HYPERBOLIC_API_KEY
parse_key "MODELSCOPE API KEY :"                                                MODELSCOPE_API_KEY
parse_key "FEATHER API KEY:"                                                    FEATHERLESS_API_KEY
parse_key "ORCAROUTER.AI"                                                       ORCAROUTER_API_KEY
parse_key "ORCAROUTER.AI alterative key (november 2026)"                        ORCAROUTER_API_KEY_ALT
parse_key "REQUESTY API KEY (200 free requests a day)"                          REQUESTY_API_KEY
parse_key "ZAI_API_KEY"                                                          ZAI_API_KEY
parse_key "ZAI_API_KEY2:"                                                        ZAI_API_KEY2
parse_key "ZAI_API_KEY3_NOV2026:"                                                ZAI_API_KEY3
parse_key "WAFER_API_KEY:"                                                       WAFER_API_KEY
parse_key "VERCEL AI API KEY:"                                                   VERCEL_AI_API_KEY
parse_key "INFRON API KEY(FREE 1000 requests a day ):"                           INFRON_API_KEY
parse_key "INFRON API KEY ALT:"                                                  INFRON_API_KEY_ALT
parse_key "UPSTAGE.AI API KEY"                                                   UPSTAGE_API_KEY
parse_key "UPSTAGE.AI ALT API KEY"                                               UPSTAGE_API_KEY_ALT
parse_key "EXA API KEY for serach"                                               EXA_API_KEY
parse_key "EXA_API_KEY"                                                          EXA_API_KEY_ALT
parse_key "FIRECRAWL API KEY"                                                    FIRECRAWL_API_KEY
parse_key "AIONLABS API KEY:"                                                    AIONLABS_API_KEY
parse_key "OPENCODE.AI API KEY test (try Big Pickle or other free models)"        OPENCODE_API_KEY_ALT

# Assemble the full per-account Cloudflare Workers AI URL once so the litellm
# config can reference $CF_API_BASE (litellm's per-provider `account_id` param
# doesn't accept os.environ/... interpolation on the cloudflare provider).
if [[ -n "${CF_ACCOUNT_ID:-}" ]]; then
  export CF_API_BASE="https://api.cloudflare.com/client/v4/accounts/${CF_ACCOUNT_ID}/ai/v1"
  export CLOUDFLARE_ACCOUNT_ID="${CF_ACCOUNT_ID}"   # litellm cloudflare/ provider reads this name
fi

# ---------------------------------------------------------------------------
# Dynamic free-model discovery (run on every start)
#
# Hardcoded model IDs rot: `nvidia_nim/meta/llama-3.1-8b-instruct` was retired
# 2026-08-26 and returned HTTP 410 for months while the config still listed it.
# Gateway catalogs (Kilo, OpenCode) are always current, so we re-read them at
# boot and merge the free ones into ULTRA_FREE_KILO / ULTRA_FREE_OPENCODE.
# Fail-open: if discovery fails, we start from the static config unchanged.
#   LITELLM_DYNAMIC_MODELS=0   disable entirely
#   LITELLM_DYNAMIC_PROVIDERS= kilo,opencode,gemini (default)
#   OPENROUTER_FREE_RPM=       weight for the ULTRA_FREE_OPENROUTER group (default 2)
#
# OpenRouter note: its free pool is metered PER ACCOUNT, not per model —
# 50 req/day with no credit, 1000 req/day once any credit is bought. It is a
# shared budget, so ULTRA_FREE_OPENROUTER is kept at a low rpm weight and is only
# reached as a fallback. Check remaining quota: GET /api/v1/key ->
# free_model_daily_requests.
# ---------------------------------------------------------------------------
if [[ "${LITELLM_DYNAMIC_MODELS:-1}" == "1" ]]; then
  PY_BIN=".venv/bin/python"
  [[ -x "$PY_BIN" ]] || PY_BIN="python3"
  # IMPORTANT: the merged config must live in the repo root, not /tmp. LiteLLM
  # resolves `callbacks: tools.xxx.yyy` relative to the CONFIG FILE's directory,
  # so a /tmp config makes the callback import fail and the proxy exits.
  DYNAMIC_OUT="$PWD/litellm_config.runtime.yaml"
  # Keep discovery output OUT of $LOG: litellm opens $LOG with `>` moments later
  # and truncates it, so every "why was provider X skipped" line vanished.
  DYNAMIC_LOG="${DYNAMIC_LOG:-/tmp/litellm_dynamic.log}"
  # Belt and braces for the same resolution path.
  export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
  if "$PY_BIN" tools/litellm_dynamic_models.py \
        --base "$ACTIVE_CONFIG" \
        --out "$DYNAMIC_OUT" \
        --providers "${LITELLM_DYNAMIC_PROVIDERS:-kilo,opencode,gemini,pins,openrouter}" \
        >>"$DYNAMIC_LOG" 2>&1; then
    ACTIVE_CONFIG="$DYNAMIC_OUT"
    echo "[litellm-proxy] dynamic models: merged (+free gateway models) — log: $DYNAMIC_LOG"
  else
    echo "[litellm-proxy] dynamic models: skipped (kept static config) — log: $DYNAMIC_LOG"
  fi
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
         NOVITA_API_KEY CURSOR_API_KEY KILOCODE_API_KEY OPENCODE_API_KEY \
         BLUESMIND_API_KEY XAI_API_KEY_ALT GROQ_API_KEY_ALT \
         DEEPINFRA_API_KEY_BEST KIMI_PLATFORM_API_KEY OLLAMA_CLOUD_TOKEN; do
  total=$((total+1))
  # `-v` tests whether the variable named by $v is set. The old `${!v:-}` form is
  # rejected by bash ("invalid variable name") because indirect expansion cannot
  # be combined with a default value — and under `set -e` it aborted the launch.
  if [[ -v $v ]]; then loaded=$((loaded+1)); fi
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
  # 9>&- closes the start lock in the child. Without it the long-lived proxy
  # inherits fd 9 and holds the lock forever, so no future start could acquire it.
  nohup .venv/bin/litellm --config "$ACTIVE_CONFIG" --port "$PORT" --num_workers 1 \
    > "$LOG" 2>&1 9>&- &
  PID=$!
  record_restart "$PID"
  echo "[litellm-proxy] PID: $PID  (kill with: kill $PID)"
  echo "[litellm-proxy] tail -f $LOG  to watch"

  # A live PID does NOT mean the port is up: LiteLLM silently picks a random free
  # port when $PORT is busy (proxy_cli.py:1047-1048). Wait for the listener, then
  # assert it is actually on $PORT — a random-port ghost fails loudly HERE instead
  # of surfacing later as a mystery "connection refused".
  if [[ "${VERIFY_BOUND_PORT:-1}" == "1" ]]; then
    _bound=""
    for _ in $(seq 1 "${VERIFY_BOUND_PORT_TIMEOUT:-240}"); do
      kill -0 "$PID" 2>/dev/null || break
      _bound="$(listener_port_for_pid "$PID")"
      [[ -n "$_bound" ]] && break
      sleep 1
    done
    if [[ -z "$_bound" ]]; then
      echo "ERROR: pid $PID never opened a listening port (see $LOG)" >&2
      kill "$PID" 2>/dev/null || true
      exit 1
    fi
    if [[ "$_bound" != "$PORT" ]]; then
      echo "ERROR: LiteLLM bound port ${_bound}, not ${PORT}." >&2
      echo "       That is LiteLLM's random-port dodge (proxy_cli.py:1047): something" >&2
      echo "       held ${PORT} at launch time. Killing pid $PID so no ghost is left behind." >&2
      kill "$PID" 2>/dev/null || true
      exit 1
    fi
    echo "[litellm-proxy] bound ${PORT} as expected (pid $PID)"
  fi
  # Preload the latency-first local group so its first request is not a cold
  # model load (3-23s measured). Non-fatal and detached: ollama may be absent.
  if [[ "${WARM_LOCAL_FAST:-1}" == "1" && -f tools/warm_litellm_local_fast.sh ]]; then
    nohup bash tools/warm_litellm_local_fast.sh --config "$ACTIVE_CONFIG" \
      > /tmp/litellm_warm.log 2>&1 9>&- &
  fi
else
  record_restart "$$"
  # 9>&- drops the start lock before exec, otherwise the exec'd proxy would hold
  # it for its entire lifetime and block every future start.
  exec .venv/bin/litellm --config "$ACTIVE_CONFIG" --port "$PORT" --num_workers 1 9>&-
fi
