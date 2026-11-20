"""Throwaway: does Phase A's shared predicate change any audit3 cell?

Runs build_report() twice on identical rows — once with the real
is_performance_scored_row, once with a permissive stand-in that keeps every
row the old 3-value-status deny-list would have kept. No source file is edited;
the module-level name is patched in-process only.
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from alpha_engine import audit3_tribunal as T

PICKS = "audit_dashboard/data/dashboard_data.json"


def permissive(row) -> bool:
    """Approximation of the pre-Phase-A filter: dict, has numeric pnl, not open."""
    if not isinstance(row, dict):
        return False
    if row.get("paper_trade") or row.get("expired_no_pnl") or row.get("_auto_expired"):
        return False
    pnl = row.get("pnl_pct")
    if isinstance(pnl, bool) or not isinstance(pnl, (int, float)):
        return False
    status = str(row.get("status", "") or "").upper()
    return not any(s in status for s in ("OPEN", "PENDING", "CANCELLED", "CANCELED", "INVALID"))


drops = {}
rows, generated_at = T.load_rows(PICKS, drops=drops)
print(f"rows loaded: {len(rows)}  drops: {drops}")

with open(PICKS, encoding="utf-8") as f:
    payload = json.load(f)
coverage = T.payload_coverage(payload, rows, drops)

real = T._is_scored_row
kept_real = sum(1 for r in rows if real(r))
T._is_scored_row = permissive
kept_old = sum(1 for r in rows if T._is_scored_row(r))
T._is_scored_row = real
print(f"scored rows — Phase A predicate: {kept_real}   permissive/old-style: {kept_old}")

# Cell-level comparison over the canonical rows both predicates keep.
same = 0
diffs = []
for r in rows:
    a, b = real(r), permissive(r)
    if a == b:
        same += 1
    else:
        diffs.append({"symbol": r.get("symbol"), "status": r.get("status"),
                      "exit_reason": r.get("exit_reason"), "phase_a": a, "old": b})

print(f"identical decisions: {same}/{len(rows)}   disagreements: {len(diffs)}")
for d in diffs[:15]:
    print("  DIFF", d)
json.dump({"rows": len(rows), "kept_phase_a": kept_real, "kept_old_style": kept_old,
           "disagreements": len(diffs), "sample": diffs[:200]},
          open("/tmp/phase_a_predicate_compare.json", "w"), indent=1)
print("wrote /tmp/phase_a_predicate_compare.json")
