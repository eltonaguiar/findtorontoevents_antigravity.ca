#!/usr/bin/env bash
set -uo pipefail
STATE="/home/eaguiar2015/findtorontoevents_antigravity.ca/.coms_review_state"
COUNT=0
if [[ -f "$STATE" ]]; then COUNT=$(cat "$STATE" 2>/dev/null || echo 0); fi
COUNT=$((COUNT + 1))
echo "$COUNT" > "$STATE"
LOG="/home/eaguiar2015/findtorontoevents_antigravity.ca/.coms_review_log"
echo "=== run $COUNT/50 at $(date -u +%Y-%m-%dT%H:%MZ) ===" >> "$LOG"
/home/eaguiar2015/AGENT_FOLDERFRAMEWORK/COMMUNICATION/coms check --agent opencode --wait 5 >> "$LOG" 2>&1
MSG="COMS check run $COUNT/50 (remaining work sprint). CREDENTIAL FIX DONE: 13 files had wrong password 'stocks' -> 'stocks1234560'. DB connection verified. Remaining: R2 (ML recalibration), R5 (ETF pilot), R10-R20 (hygiene), R21-R24 (Sprint 4). GitHub: 29 commits. Money-ready: ETF TAA + mutual fund passive core."
/home/eaguiar2015/AGENT_FOLDERFRAMEWORK/COMMUNICATION/coms send "audit/review-2026-11-19" "$MSG" >> "$LOG" 2>&1
if [[ "$COUNT" -ge 50 ]]; then
  (crontab -l 2>/dev/null | grep -v "coms_check_reply.sh") | crontab -
  echo "self-disabled after 50 runs" >> "$LOG"
fi
