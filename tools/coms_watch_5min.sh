#!/bin/bash
# coms_watch_5min.sh — poll the COMS bus every 5 minutes for one hour, then self-disable.
#
# Why cron and not a sleep loop: the agent cannot block a turn waiting, so the polling has
# to be a scheduled job. START marks the first run; after 3600s the script exits without
# doing work, so it stops touching the bus on its own with no cleanup step to forget.
#
# Output: reports/coms_watch.log  (append-only; one block per tick)
set -uo pipefail

REPO=/home/eaguiar2015/findtorontoevents_antigravity.ca
LOG="$REPO/reports/coms_watch.log"
STATE="$REPO/reports/.coms_watch_state"
START_FILE="$REPO/reports/.coms_watch_start"
SEEN="$REPO/reports/.coms_watch_seen"
BROKER=192.168.2.52
TTL=3600

export PATH="$HOME/.local/bin:$PATH"

mkdir -p "$STATE" "$(dirname "$LOG")"
touch "$SEEN"

now=$(date +%s)
[ -f "$START_FILE" ] || echo "$now" > "$START_FILE"
start=$(cat "$START_FILE")

if [ $(( now - start )) -gt "$TTL" ]; then
  # one closing line, then stay silent forever after
  if [ ! -f "$REPO/reports/.coms_watch_done" ]; then
    echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ)  TTL reached (60 min) — watcher disabled ===" >> "$LOG"
    touch "$REPO/reports/.coms_watch_done"
  fi
  exit 0
fi

ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
elapsed=$(( (now - start) / 60 ))

# every retained topic on the bus
mapfile -t topics < <(mosquitto_sub -h "$BROKER" -t 'notes/#' -W 4 -F '%t' 2>/dev/null | sort -u)

new_count=0
{
  echo "--- $ts  t+${elapsed}m  topics=${#topics[@]}"
  for t in "${topics[@]}"; do
    if ! grep -qxF "$t" "$SEEN" 2>/dev/null; then
      body=$(mosquitto_sub -h "$BROKER" -i "w$$-$RANDOM" -t "$t" -W 4 --retained-only -C 1 2>/dev/null)
      bytes=$(printf %s "$body" | wc -c)
      first=$(printf %s "$body" | head -1 | cut -c1-110)
      echo "    NEW  ${t#notes/}  (${bytes}B)"
      echo "         $first"
      echo "$t" >> "$SEEN"
      new_count=$(( new_count + 1 ))
    fi
  done
  [ "$new_count" -eq 0 ] && echo "    (no new topics since last tick)"
} >> "$LOG"

exit 0
