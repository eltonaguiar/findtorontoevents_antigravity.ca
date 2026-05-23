#!/usr/bin/env python3
"""Quick diagnostic: how many picks come from collect_all_picks()."""
import sys, os
sys.path.insert(0, r"e:\findtorontoevents_antigravity.ca")
os.chdir(r"e:\findtorontoevents_antigravity.ca")

from audit_trail.dashboard_generator import collect_all_picks, _is_active_pick, _has_tradeable_entry, _is_pre_score_active_candidate

active, closed, all_closed = collect_all_picks()
print(f"\n=== COLLECT_ALL_PICKS RESULTS ===")
print(f"Active: {len(active)}")
print(f"Closed: {len(closed)}")
print(f"All closed (with expired): {len(all_closed)}")

# Check filters
pre_score = [p for p in active if _is_pre_score_active_candidate(p)]
is_actually_active = [p for p in active if _is_active_pick(p)]
has_entry = [p for p in active if _has_tradeable_entry(p)]
print(f"\nActive that pass _is_pre_score_active_candidate: {len(pre_score)}")
print(f"Active that pass _is_active_pick: {len(is_actually_active)}")
print(f"Active that _has_tradeable_entry: {len(has_entry)}")

# Asset class breakdown
cats = {}
for p in active:
    ac = p.get("asset_class", "?")
    cats[ac] = cats.get(ac, 0) + 1
print(f"\nAsset class breakdown: {dict(sorted(cats.items(), key=lambda x:-x[1]))}")

# Source system breakdown
srcs = {}
for p in active:
    s = p.get("source_system", "?")
    srcs[s] = srcs.get(s, 0) + 1
print(f"\nSource system breakdown (top 15):")
for s, c in sorted(srcs.items(), key=lambda x:-x[1])[:15]:
    print(f"  {s}: {c}")

# Check what's being filtered by _is_pre_score_active_candidate
not_pre_score = [p for p in active if not _is_pre_score_active_candidate(p)]
print(f"\n{len(not_pre_score)} picks REJECTED by _is_pre_score_active_candidate:")
for p in not_pre_score[:5]:
    print(f"  strategy='{p.get('strategy')}' symbol='{p.get('symbol')}' source='{p.get('source_system')}'")
