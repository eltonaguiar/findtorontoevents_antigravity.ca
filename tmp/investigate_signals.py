#!/usr/bin/env python3
"""Investigate KIMI signal closure, Mercury2 status, and unrealized PNL."""
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

BASE = Path(r"e:\findtorontoevents_antigravity.ca")

# ── 1. Alpha Engine active picks analysis ──
print("=" * 80)
print("1. ALPHA ENGINE - ACTIVE PICKS ANALYSIS")
print("=" * 80)

active_path = BASE / "alpha_engine" / "data" / "active_picks.json"
with open(active_path) as f:
    active = json.load(f)

print(f"Total active (open) picks: {len(active)}")

# Group by strategy
strats = defaultdict(int)
for p in active:
    strats[p.get("strategy", "?")] += 1

print(f"Unique strategies with open picks: {len(strats)}")
print("\nTop 30 strategies by open pick count:")
for s, c in sorted(strats.items(), key=lambda x: -x[1])[:30]:
    print(f"  {s}: {c}")

# KIMI-specific
kimi_picks = [p for p in active if "kimi" in p.get("strategy", "").lower()]
print(f"\n--- KIMI open picks: {len(kimi_picks)} ---")
for p in kimi_picks:
    print(f"  {p['strategy']} | {p['symbol']} | entry={p['entry_date']} | pnl={p.get('unrealized_pnl_pct', '?')}")

# ── 2. Signal age analysis ──
print("\n" + "=" * 80)
print("2. SIGNAL AGE ANALYSIS - WHY SIGNALS STAY OPEN")
print("=" * 80)

now = datetime.utcnow()
age_buckets = {"0-2d": 0, "3-5d": 0, "6-10d": 0, "11-30d": 0, "30+d": 0}
no_tp_sl = 0
missing_tp = 0
missing_sl = 0

for p in active:
    try:
        entry = datetime.strptime(p["entry_date"], "%Y-%m-%d")
        age = (now - entry).days
    except:
        age = 999

    if age <= 2: age_buckets["0-2d"] += 1
    elif age <= 5: age_buckets["3-5d"] += 1
    elif age <= 10: age_buckets["6-10d"] += 1
    elif age <= 30: age_buckets["11-30d"] += 1
    else: age_buckets["30+d"] += 1

    if p.get("take_profit") is None:
        missing_tp += 1
    if p.get("stop_loss") is None:
        missing_sl += 1
    if p.get("take_profit") is None and p.get("stop_loss") is None:
        no_tp_sl += 1

print("Age distribution:")
for bucket, count in age_buckets.items():
    print(f"  {bucket}: {count}")

print(f"\nMissing TP: {missing_tp}")
print(f"Missing SL: {missing_sl}")
print(f"Missing BOTH TP and SL: {no_tp_sl}")

# Check max hold days config
print("\n--- Picks with NO TP and NO SL (will never auto-close via price): ---")
zombie_picks = [p for p in active if p.get("take_profit") is None and p.get("stop_loss") is None]
for p in zombie_picks[:10]:
    print(f"  {p['strategy']} | {p['symbol']} | entry={p['entry_date']} | hold={p.get('hold_days','?')}d")
if len(zombie_picks) > 10:
    print(f"  ... and {len(zombie_picks) - 10} more")

# ── 3. Unrealized PNL tracking ──
print("\n" + "=" * 80)
print("3. UNREALIZED PNL - OPEN POSITION PERFORMANCE")
print("=" * 80)

pnl_data = []
for p in active:
    pnl = p.get("unrealized_pnl_pct", 0) or 0
    pnl_data.append({
        "strategy": p.get("strategy", "?"),
        "symbol": p.get("symbol", "?"),
        "pnl": pnl,
        "entry_date": p.get("entry_date", "?"),
        "hold_days": p.get("hold_days", 0),
    })

if pnl_data:
    pnls = [d["pnl"] for d in pnl_data]
    winners = [d for d in pnl_data if d["pnl"] > 0]
    losers = [d for d in pnl_data if d["pnl"] < 0]
    flat = [d for d in pnl_data if d["pnl"] == 0]

    print(f"Total open positions: {len(pnl_data)}")
    print(f"Winners (unrealized): {len(winners)}")
    print(f"Losers (unrealized): {len(losers)}")
    print(f"Flat: {len(flat)}")
    print(f"\nTotal unrealized PNL: {sum(pnls):.4f}%")
    print(f"Average unrealized PNL: {sum(pnls)/len(pnls):.4f}%")
    print(f"Best open position: {max(pnls):.4f}%")
    print(f"Worst open position: {min(pnls):.4f}%")

    print("\nTop 10 winners (unrealized):")
    for d in sorted(pnl_data, key=lambda x: -x["pnl"])[:10]:
        print(f"  {d['strategy'][:35]:35s} | {d['symbol']:12s} | PNL: {d['pnl']:+.4f}% | {d['hold_days']}d")

    print("\nTop 10 losers (unrealized):")
    for d in sorted(pnl_data, key=lambda x: x["pnl"])[:10]:
        print(f"  {d['strategy'][:35]:35s} | {d['symbol']:12s} | PNL: {d['pnl']:+.4f}% | {d['hold_days']}d")

# ── 4. Closed picks analysis ──
print("\n" + "=" * 80)
print("4. CLOSED PICKS SUMMARY")
print("=" * 80)

closed_path = BASE / "alpha_engine" / "data" / "closed_picks.json"
with open(closed_path) as f:
    closed = json.load(f)

print(f"Total closed picks: {len(closed)}")

won = [p for p in closed if p.get("status") == "WON"]
lost = [p for p in closed if p.get("status") == "LOST"]
other = [p for p in closed if p.get("status") not in ("WON", "LOST")]

print(f"Won: {len(won)}")
print(f"Lost: {len(lost)}")
print(f"Other status: {len(other)}")
if len(won) + len(lost) > 0:
    print(f"Win rate: {len(won)/(len(won)+len(lost))*100:.1f}%")

closed_pnls = [float(p.get("pnl_pct", 0) or 0) or 0 for p in closed]
print(f"Total realized PNL: {sum(closed_pnls):.2f}%")

# ── 5. Mercury2 status ──
print("\n" + "=" * 80)
print("5. MERCURY2 SCANNER STATUS")
print("=" * 80)

m2_summary = BASE / "mercury2" / "data" / "scan_summary.json"
with open(m2_summary) as f:
    summary = json.load(f)

for k, v in summary.items():
    print(f"  {k}: {v}")

m2_active = BASE / "mercury2" / "data" / "active_picks.json"
with open(m2_active) as f:
    m2_picks = json.load(f)

print(f"\nMercury2 active picks: {len(m2_picks)}")
for p in m2_picks:
    print(f"  {p['symbol']} | {p['direction']} | entry={p['entry_price']} | pnl={p.get('unrealized_pnl_pct', '?')}%")

m2_closed = BASE / "mercury2" / "data" / "closed_picks.json"
with open(m2_closed) as f:
    m2_cl = json.load(f)
print(f"Mercury2 closed picks: {len(m2_cl)}")
m2_wins = sum(1 for p in m2_cl if p.get("status") == "WIN")
print(f"Mercury2 wins: {m2_wins}, losses: {len(m2_cl) - m2_wins}")

print("\n" + "=" * 80)
print("INVESTIGATION COMPLETE")
print("=" * 80)
