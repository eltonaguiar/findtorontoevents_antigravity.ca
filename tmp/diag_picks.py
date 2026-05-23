#!/usr/bin/env python3
"""Diagnose pick counts across all source files."""
import json, os, datetime

ROOT = r"e:\findtorontoevents_antigravity.ca"

sources = {
    "alpha_engine/data/active_picks.json": None,
    "audit_trail/data/dashboard_payload.json": lambda d: d.get("picks", {}).get("active", []),
    "audit_trail/data/universal_resolved_picks.json": None,
    "copy_trader_intel/data/active_picks.json": None,
    "predictions/data/active_predictions.json": None,
    "rapid_fire_data/active_picks.json": None,
    "quan_engine/data/active_signals.json": None,
    "regime_terminal/data/regime_picks.json": None,
    "copy_trader_intel/data/forex_copytrader_picks.json": None,
    "alpha_engine/data/smart_picks.json": lambda d: d.get("picks", []),
}

for rel_path, extractor in sources.items():
    full = os.path.join(ROOT, rel_path)
    if not os.path.isfile(full):
        print(f"  NOT FOUND: {rel_path}")
        continue
    try:
        with open(full, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if extractor:
            picks = extractor(raw)
        elif isinstance(raw, list):
            picks = raw
        elif isinstance(raw, dict):
            picks = raw.get("picks", raw.get("active", raw.get("signals", raw.get("predictions", []))))
        else:
            picks = []
        
        cats = {}
        for p in picks:
            if isinstance(p, dict):
                ac = p.get("asset_class", p.get("category", "?"))
                cats[ac] = cats.get(ac, 0) + 1
        
        mtime = os.path.getmtime(full)
        age_m = (datetime.datetime.now().timestamp() - mtime) / 60
        
        print(f"  {rel_path}: {len(picks)} picks (age: {age_m:.0f}m) {dict(cats)}")
    except Exception as e:
        print(f"  ERROR reading {rel_path}: {e}")

print("\n--- Dashboard Payload Detail ---")
dp_path = os.path.join(ROOT, "audit_trail", "data", "dashboard_payload.json")
if os.path.isfile(dp_path):
    with open(dp_path, "r", encoding="utf-8") as f:
        dp = json.load(f)
    picks = dp.get("picks", {})
    print(f"  active: {len(picks.get('active', []))}")
    print(f"  closed: {len(picks.get('closed', []))}")
    smart = dp.get("smart_picks_feed", {})
    print(f"  smart_picks_feed picks: {len(smart.get('picks', []))}")
    size_kb = os.path.getsize(dp_path) / 1024
    print(f"  payload size: {size_kb:.0f} KB")
    
    active = picks.get("active", [])
    if active:
        scores = [p.get("score", 0) for p in active if isinstance(p, dict)]
        print(f"  score range: {min(scores):.1f} - {max(scores):.1f}")
        print(f"  avg score: {sum(scores)/len(scores):.1f}")
