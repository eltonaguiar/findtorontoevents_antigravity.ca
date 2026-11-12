#!/usr/bin/env bash
# hermes_web.sh — talk to the Hermes agent's OpenAI-compatible web server.
# Endpoint defaults to the LAN peer (Windows host 192.168.2.32:8642); override
# with HERMES_ENDPOINT. Key resolution order: $HERMES_API_KEY, then
# API_SERVER_KEY= in ~/.hermes/.env (or $HERMES_ENV_FILE). The key is never printed.
#
# Usage:
#   tools/hermes_web.sh                # status probe (is the gateway listening?)
#   tools/hermes_web.sh models         # same probe, prints /v1/models
#   tools/hermes_web.sh ask "prompt"   # one-shot question, prints the reply
set -uo pipefail

BASE="${HERMES_ENDPOINT:-http://192.168.2.32:8642}"
MODEL="${HERMES_MODEL:-hermes-agent}"
ENVF="${HERMES_ENV_FILE:-$HOME/.hermes/.env}"
TMP="$(mktemp -t hermes_models.XXXXXX)"

die() { echo "hermes-web: $*" >&2; exit 1; }
cleanup() { rm -f "$TMP"; }
trap cleanup EXIT

load_key() {
  if [[ -n "${HERMES_API_KEY:-}" ]]; then printf '%s' "$HERMES_API_KEY"; return 0; fi
  [[ -r "$ENVF" ]] || return 1
  local k
  k=$(sed -n 's/^[[:space:]]*API_SERVER_KEY[[:space:]]*=[[:space:]]*//p' "$ENVF" | head -1 | tr -d '\r' | sed 's/^"//; s/"$//')
  [[ -n "$k" ]] || return 1
  printf '%s' "$k"
}

probe() {
  echo "endpoint : $BASE"
  echo "model    : $MODEL"
  local code
  code=$(curl -sS -m 6 -o "$TMP" -w '%{http_code}' "$BASE/v1/models" 2>/dev/null) || code=000
  case "$code" in
    200)
      echo "reachable: YES (http 200)"
      python3 -c 'import json,sys
try:
    d=json.load(open(sys.argv[1]))
    ids=[m.get("id") for m in d.get("data",[])]
    print("models   : " + (", ".join(ids) if ids else "(none listed)"))
except Exception:
    pass' "$TMP" 2>/dev/null
      ;;
    401|403) echo "reachable: YES (http $code — server is up, key missing or rejected)" ;;
    000)     echo "reachable: NO (connection failed — Windows host down, or 8642 not LAN-reachable)" ;;
    *)       echo "reachable: UNKNOWN (http $code)"; head -c 200 "$TMP" 2>/dev/null; echo ;;
  esac
}

ask() {
  local prompt="$1" key payload
  key=$(load_key) || die "no API key — set HERMES_API_KEY, or add API_SERVER_KEY=... to $ENVF"
  payload=$(printf '%s' "$prompt" | python3 -c 'import json,sys; print(json.dumps({"model": sys.argv[1], "messages":[{"role":"user","content": sys.stdin.read()}]}))' "$MODEL")
  curl -sS -m "${HERMES_TIMEOUT:-180}" -X POST "$BASE/v1/chat/completions" \
    -H "Authorization: Bearer $key" -H 'Content-Type: application/json' \
    -d "$payload" \
  | python3 -c 'import json,sys
raw=sys.stdin.read()
try: d=json.loads(raw)
except Exception: print(raw[:800], file=sys.stderr); sys.exit(1)
if "error" in d: print("error: %s" % json.dumps(d["error"])[:400], file=sys.stderr); sys.exit(1)
try: print(d["choices"][0]["message"].get("content",""))
except Exception: print(raw[:800], file=sys.stderr); sys.exit(1)'
}

case "${1:-status}" in
  status|probe|models) probe ;;
  ask) shift; [[ $# -ge 1 ]] || die 'usage: hermes_web.sh ask "<prompt>"'; ask "$*" ;;
  -h|--help) sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//' ;;
  *) die "unknown command: $1 (try: status | models | ask \"<prompt>\")" ;;
esac
