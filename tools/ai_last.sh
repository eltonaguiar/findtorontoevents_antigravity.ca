#!/usr/bin/env bash
# AI_LAST helper: quick snapshot of last model activity seen by LiteLLM proxy logs.
# Usage:
#   tools/ai_last.sh
#   tools/ai_last.sh --json
#   LOG=/custom/path.log tools/ai_last.sh

set -euo pipefail

LOG_PATH="${LOG:-/tmp/litellm_proxy.log}"
OUT_JSON=0
if [[ "${1:-}" == "--json" ]]; then
  OUT_JSON=1
fi

now_est="$(TZ=America/Toronto date '+%Y-%m-%d %H:%M:%S %Z')"
today_est="$(TZ=America/Toronto date '+%Y-%m-%d')"

if [[ ! -f "$LOG_PATH" ]]; then
  if [[ $OUT_JSON -eq 1 ]]; then
    printf '{"ok":false,"error":"log-not-found","log":"%s","now_est":"%s"}\n' "$LOG_PATH" "$now_est"
  else
    echo "AI_LAST"
    echo "Now EST: $now_est"
    echo "Log: $LOG_PATH"
    echo "Status: log not found"
  fi
  exit 1
fi

model_info="$(awk '
  /model=/ {
    line=$0
    model=""
    if (match(line, /model=[^, ]+/)) {
      cand=substr(line, RSTART+6, RLENGTH-6)
      # Ignore placeholders and internals from tracebacks.
      if (cand !~ /^(self\.model|model|None|kwargs|deployment)$/ && cand !~ /^self\./) {
        model=cand
        model_line_nr=NR
        model_raw=line
        model_time=""
        if (match(line, /^[0-9][0-9]:[0-9][0-9]:[0-9][0-9]/)) {
          model_time=substr(line, RSTART, RLENGTH)
        }
      }
    }
  }
  END {
    if (model != "") {
      # Use ASCII unit-separator so empty fields survive shell splitting.
      printf "%s\034%s\034%s\034%s", model, model_time, model_line_nr, model_raw
    }
  }
' "$LOG_PATH")"

ok_time="$(awk '
  /POST \/v1\/chat\/completions HTTP\/1.1" 200 OK/ {
    line=$0
    t=""
    if (match(line, /^[0-9][0-9]:[0-9][0-9]:[0-9][0-9]/)) {
      t=substr(line, RSTART, RLENGTH)
    }
    ok=t
  }
  END { if (ok != "") print ok }
' "$LOG_PATH")"

served_hint="$(grep -oE 'served_(by|model)=\s*[^ ]+' "$HOME/.bash_history" 2>/dev/null | tail -n 1 || true)"
history_model="$(grep -Eo "['\"]model['\"]\s*:\s*['\"][^'\"]+['\"]" "$HOME/.bash_history" 2>/dev/null | tail -n 1 | sed -E "s/.*['\"]([^'\"]+)['\"]$/\1/" || true)"

model_name=""
model_time=""
model_line_nr=""
model_raw=""
if [[ -n "$model_info" ]]; then
  IFS=$'\034' read -r model_name model_time model_line_nr model_raw <<< "$model_info"
fi

# Fallback: if the proxy log has no explicit model token, use latest shell payload model.
if [[ -z "$model_name" && -n "$history_model" ]]; then
  model_name="$history_model"
  model_raw="(from bash history payload)"
fi

model_est=""
if [[ -n "$model_time" ]]; then
  model_est="$today_est $model_time EST (estimated date from current day)"
fi

if [[ $OUT_JSON -eq 1 ]]; then
  esc_raw="${model_raw//\"/\\\"}"
  esc_hint="${served_hint//\"/\\\"}"
  printf '{"ok":true,"now_est":"%s","log":"%s","last_model":"%s","last_model_log_time":"%s","last_model_est":"%s","last_model_line":%s,"last_200_log_time":"%s","last_served_hint":"%s","last_model_raw":"%s"}\n' \
    "$now_est" "$LOG_PATH" "$model_name" "$model_time" "$model_est" "${model_line_nr:-0}" "$ok_time" "$esc_hint" "$esc_raw"
  exit 0
fi

echo "AI_LAST"
echo "Now EST: $now_est"
echo "Log: $LOG_PATH"
if [[ -n "$model_name" ]]; then
  echo "Last model token seen: $model_name"
  if [[ -n "$model_time" ]]; then
    echo "Log time: $model_time"
    echo "Approx EST datetime: $model_est"
  fi
else
  echo "Last model token seen: (none found)"
fi
if [[ -n "$ok_time" ]]; then
  echo "Last successful /chat/completions (200 OK) log time: $ok_time"
fi
if [[ -n "$served_hint" ]]; then
  echo "Last served hint from shell history: $served_hint"
fi
if [[ -n "$history_model" ]]; then
  echo "Last model field in shell history payload: $history_model"
fi
