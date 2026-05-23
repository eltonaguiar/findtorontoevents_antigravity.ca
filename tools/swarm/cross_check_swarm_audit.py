"""Cross-check swarm consensus picks against /audit active set.

Reproducer for reports/swarm_vs_audit_cross_check_2026-05-13.md.
Same numbers each run as long as the source files have not changed:

  - Total swarm picks (open vs resolved)
  - /audit active count + unique symbol count
  - Intersection (symbol match, normalized)
  - Direction-aligned vs direction-conflict subset
  - Swarm-only set (excluding /audit recent_closed)
  - /audit-only set
  - Swarm tier distribution

Usage:
    python tools/swarm/cross_check_swarm_audit.py
    python tools/swarm/cross_check_swarm_audit.py --json   # machine output
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SWARM_PATH = ROOT / "audit_dashboard" / "data" / "swarm_picks.json"
AUDIT_PATH = ROOT / "audit_dashboard" / "data" / "dashboard_data.json"


def normalize_symbol(s: str) -> str:
    """Strip exchange prefix + futures/perp suffix to a bare ticker."""
    s = s or ""
    if ":" in s:
        s = s.split(":", 1)[1]
    s = re.sub(r"1!$|\.P$|\.PA$|\.MEM$", "", s)
    return s.upper()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = ap.parse_args()

    if not SWARM_PATH.exists():
        print(f"ERROR: {SWARM_PATH} missing", file=sys.stderr)
        return 1
    if not AUDIT_PATH.exists():
        print(f"ERROR: {AUDIT_PATH} missing", file=sys.stderr)
        return 1

    sp = json.loads(SWARM_PATH.read_text(encoding="utf-8"))
    dd = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))

    active = (dd.get("picks") or {}).get("active") or []
    recent = (dd.get("picks") or {}).get("recent_closed") or []

    swarm_open = [p for p in sp if not (p.get("outcome") or {}).get("exit_reason")]
    swarm_closed = [p for p in sp if (p.get("outcome") or {}).get("exit_reason")]

    audit_active_by_sym: dict[str, list[dict]] = {}
    for p in active:
        s = normalize_symbol(p.get("symbol", ""))
        if s:
            audit_active_by_sym.setdefault(s, []).append(p)
    audit_recent_syms = {normalize_symbol(p.get("symbol", "")) for p in recent if p.get("symbol")}

    overlap_aligned: list[dict] = []
    overlap_conflict: list[dict] = []
    swarm_only_strict: list[dict] = []  # not in active AND not in recent_closed
    for p in swarm_open:
        sym = normalize_symbol(p["symbol"])
        if sym in audit_active_by_sym:
            audit_dirs = {ap.get("direction", "").upper() for ap in audit_active_by_sym[sym]}
            if p["direction"].upper() in audit_dirs:
                overlap_aligned.append({"symbol": sym, "tier": p["consensus_tier"],
                                        "swarm_dir": p["direction"], "audit_dirs": sorted(audit_dirs)})
            else:
                overlap_conflict.append({"symbol": sym, "tier": p["consensus_tier"],
                                         "swarm_dir": p["direction"], "audit_dirs": sorted(audit_dirs),
                                         "asset_class": p["asset_class"]})
        elif sym not in audit_recent_syms:
            swarm_only_strict.append({"symbol": sym, "tier": p["consensus_tier"],
                                      "swarm_dir": p["direction"],
                                      "asset_class": p["asset_class"]})

    swarm_active_syms = {normalize_symbol(p["symbol"]) for p in swarm_open}
    audit_only = sorted(set(audit_active_by_sym.keys()) - swarm_active_syms)

    tier_counter = Counter(p["consensus_tier"] for p in swarm_open)

    payload = {
        "swarm_total": len(sp),
        "swarm_open": len(swarm_open),
        "swarm_resolved": len(swarm_closed),
        "audit_active_total": len(active),
        "audit_active_unique_symbols": len(audit_active_by_sym),
        "audit_recent_closed_total": len(recent),
        "audit_recent_closed_unique_symbols": len(audit_recent_syms),
        "intersection_count": len(overlap_aligned) + len(overlap_conflict),
        "direction_aligned_count": len(overlap_aligned),
        "direction_conflict_count": len(overlap_conflict),
        "direction_conflicts": overlap_conflict,
        "swarm_only_strict_count": len(swarm_only_strict),
        "swarm_only_strict": swarm_only_strict,
        "audit_only_count": len(audit_only),
        "audit_only_sample": audit_only[:20],
        "swarm_tier_dist": dict(tier_counter),
    }

    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    print(f"swarm picks: total={payload['swarm_total']}  open={payload['swarm_open']}  resolved={payload['swarm_resolved']}")
    print(f"/audit active: {payload['audit_active_total']}  unique symbols: {payload['audit_active_unique_symbols']}")
    print(f"/audit recent_closed: {payload['audit_recent_closed_total']}  unique symbols: {payload['audit_recent_closed_unique_symbols']}")
    print(f"intersection (by symbol): {payload['intersection_count']}")
    print(f"  direction-aligned: {payload['direction_aligned_count']}")
    print(f"  direction-conflict: {payload['direction_conflict_count']}")
    for c in overlap_conflict:
        print(f"    [CONFLICT] {c['symbol']} ({c['asset_class']}): swarm {c['swarm_dir']} ({c['tier']}) | /audit {c['audit_dirs']}")
    print(f"swarm-only (no active AND no recent_closed): {payload['swarm_only_strict_count']}")
    for r in swarm_only_strict:
        print(f"  {r['symbol']:14s} {r['asset_class']:8s} swarm {r['swarm_dir']} ({r['tier']})")
    print(f"/audit-only (no swarm vote): {payload['audit_only_count']}")
    print(f"swarm tier dist (open picks): {payload['swarm_tier_dist']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
