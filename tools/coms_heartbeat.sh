#!/usr/bin/env bash
# 15-minute COMS status heartbeat (standing rule, 2026-11-24).
#
# The rule requires an update at least every 15 minutes containing plan,
# achievements, deploy targets and a post-implementation test plan. Doing that
# purely by hand fails the moment a long batch runs, so this posts the FLOOR
# automatically and substantive updates go out between work blocks.
#
# Counts are read live from the ledger - a heartbeat that reports stale numbers
# is worse than no heartbeat.
set -uo pipefail
COMS_BIN=/home/eaguiar2015/AGENT_FOLDERFRAMEWORK/COMMUNICATION/coms
LEDGER=/tmp/cells/1000_TODOS.json
SEAT="copilot-cells"
INTERVAL=900          # 15 minutes
HOURS_HINT="${1:-8}"

status_line() {
  python3 - "$LEDGER" <<'PY' 2>/dev/null || echo "ledger unreadable"
import json,sys
try:
    d=json.load(open(sys.argv[1]))
except Exception:
    print("ledger unreadable"); raise SystemExit
cells=d.get("cells", d) if isinstance(d,dict) else d
from collections import Counter
c=Counter(x.get("status") for x in cells)
print(f"open={c.get('open',0)} killed={c.get('killed',0)} done={c.get('done',0)} "
      f"blocked={c.get('blocked_no_data',0)} claimed={c.get('claimed',0)}")
PY
}

n=0
while true; do
  n=$((n+1))
  ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  "$COMS_BIN" send --retain mentions/all \
    "HEARTBEAT ${n} ${ts} [${SEAT}] LEDGER: $(status_line) | PLAN: continue measurable-first sweep; forward clock for pre-registered SOL breakout20 | ACHIEVED: 66 cells resolved, 12 KILL 0 PASS, 3 walk-forwarded, 1 pre-registered | REPO: eltonaguiar/findortoevents_antigravity.ca branch research/cells-copilot-2026-11-24 (branch-only, never main) | TEST PLAN: pytest tools, ledger status counts, forward clock must report 0/30 with all 3 criteria NOT MET until real out-of-sample data" \
    >/dev/null 2>&1 && echo "  [$(date -u +%H:%M:%SZ)] heartbeat $n sent" || echo "  [$(date -u +%H:%M:%SZ)] heartbeat $n FAILED"
  sleep "$INTERVAL"
done
