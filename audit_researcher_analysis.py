import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

ROOT = Path("/mnt/c/findtorontoevents_antigravity.ca")

# Load dashboard payload
with open(ROOT / "audit_trail/data/dashboard_payload.json", "r") as f:
    payload = json.load(f)

# Load universal resolved picks
with open(ROOT / "audit_trail/data/universal_resolved_picks.json", "r") as f:
    resolved = json.load(f)

# Load battleground closed picks if exists
bg_closed_path = ROOT / "battleground/data/closed_picks.json"
bg_closed = []
if bg_closed_path.exists():
    with open(bg_closed_path, "r") as f:
        try:
            bg_closed = json.load(f)
        except Exception:
            pass

# Current time (use payload generated_at or now)
now = datetime.fromisoformat(payload.get("generated_at", datetime.utcnow().isoformat()))
if now.tzinfo:
    now = now.replace(tzinfo=None)

print("=" * 80)
print("AUDIT RESEARCHER FINDINGS REPORT")
print("=" * 80)
print(f"Payload generated_at: {payload.get('generated_at')}")
print(f"Total systems: {payload.get('summary', {}).get('total_systems')}")
print(f"Total active picks: {payload.get('summary', {}).get('total_active_picks')}")
print(f"Overall WR: {payload.get('summary', {}).get('overall_win_rate')}%")
print(f"Total PnL %%: {payload.get('summary', {}).get('total_pnl_pct')}")
print(f"Profit Factor: {payload.get('summary', {}).get('profit_factor')}")
print()

# ---- 1. Strategy-level forward WR analysis from resolved picks ----
print("=" * 80)
print("1. STRATEGY FORWARD WIN RATE (< 0.55)")
print("=" * 80)

strategy_stats = defaultdict(lambda: {"wins": 0, "losses": 0, "total_pnl": 0, "last_pick": None, "count": 0, "asset_classes": set()})

for pick in resolved:
    if not isinstance(pick, dict):
        continue
    strat = pick.get("strategy", "UNKNOWN")
    pnl = pick.get("pnl_pct", 0)
    ts_str = pick.get("timestamp") or pick.get("resolved_at")
    asset_class = pick.get("asset_class", "UNKNOWN")
    s = strategy_stats[strat]
    s["count"] += 1
    s["total_pnl"] += float(pnl or 0)
    s["asset_classes"].add(asset_class)
    if pnl is not None and float(pnl) > 0:
        s["wins"] += 1
    else:
        s["losses"] += 1
    if ts_str:
        try:
            # handle various timestamp formats
            ts = ts_str.replace("Z", "+00:00")
            ts_dt = datetime.fromisoformat(ts)
            if ts_dt.tzinfo:
                ts_dt = ts_dt.replace(tzinfo=None)
            if s["last_pick"] is None or ts_dt > s["last_pick"]:
                s["last_pick"] = ts_dt
        except Exception:
            pass

low_wr_strategies = []
for strat, stats in strategy_stats.items():
    total = stats["wins"] + stats["losses"]
    if total > 0:
        wr = stats["wins"] / total
        stats["wr"] = wr
    else:
        stats["wr"] = 0

    if stats["wr"] < 0.55 and stats["count"] >= 5:
        low_wr_strategies.append((strat, stats))

# Sort by count descending
low_wr_strategies.sort(key=lambda x: -x[1]["count"])
print(f"Found {len(low_wr_strategies)} strategies with forward WR < 55%% (min 5 picks)\n")
for strat, stats in low_wr_strategies[:30]:
    stale_days = (now - stats["last_pick"]).days if stats["last_pick"] else "N/A"
    print(f"  {strat:60s} | WR: {stats['wr']:.1%} | Picks: {stats['count']} | PnL: {stats['total_pnl']:.2f} | Last: {stale_days} days ago | AssetClasses: {stats['asset_classes']}")

# ---- 2. Stale strategies (no picks 7+ days) ----
print("\n" + "=" * 80)
print("2. STALE STRATEGIES (no picks >= 7 days)")
print("=" * 80)
stale_strategies = []
for strat, stats in strategy_stats.items():
    if stats["last_pick"] is None:
        continue
    days_since = (now - stats["last_pick"]).days
    if days_since >= 7:
        stale_strategies.append((strat, days_since, stats["count"], stats["wr"]))

stale_strategies.sort(key=lambda x: -x[1])  # sort by days since
print(f"Found {len(stale_strategies)} strategies with no pick in 7+ days\n")
for strat, days, count, wr in stale_strategies[:30]:
    print(f"  {strat:60s} | {days:3d} days stale | Picks: {count} | WR: {wr:.1%}")

# ---- 3. Non-crypto elite score starvation ----
print("\n" + "=" * 80)
print("3. NON-CRYPTO ELITE SCORE STARVATION")
print("=" * 80)
# We look at closed picks with asset_class != CRYPTO and low win rate or very few picks
non_crypto_stats = defaultdict(lambda: {"wins": 0, "losses": 0, "count": 0, "last_pick": None})
for pick in resolved:
    if not isinstance(pick, dict):
        continue
    ac = pick.get("asset_class", "UNKNOWN")
    if ac in ("CRYPTO", "unknown", None, ""):
        continue
    strat = pick.get("strategy", "UNKNOWN")
    pnl = pick.get("pnl_pct", 0)
    s = non_crypto_stats[strat]
    s["count"] += 1
    if pnl is not None and float(pnl) > 0:
        s["wins"] += 1
    else:
        s["losses"] += 1
    ts_str = pick.get("timestamp") or pick.get("resolved_at")
    if ts_str:
        try:
            ts = ts_str.replace("Z", "+00:00")
            ts_dt = datetime.fromisoformat(ts)
            if ts_dt.tzinfo:
                ts_dt = ts_dt.replace(tzinfo=None)
            if s["last_pick"] is None or ts_dt > s["last_pick"]:
                s["last_pick"] = ts_dt
        except Exception:
            pass

starved = []
for strat, s in non_crypto_stats.items():
    total = s["wins"] + s["losses"]
    wr = s["wins"] / total if total else 0
    if s["count"] < 10 or wr < 0.55:
        starved.append((strat, s["count"], wr, s["last_pick"]))

starved.sort(key=lambda x: x[1])
print(f"Found {len(starved)} non-crypto strategies with < 10 picks or WR < 55%\n")
for strat, count, wr, last in starved[:30]:
    days = (now - last).days if last else "N/A"
    print(f"  {strat:60s} | Picks: {count:3d} | WR: {wr:.1%} | Last: {days} days")

# ---- 4. Anti-predictive weight leakage (look at systems in payload) ----
print("\n" + "=" * 80)
print("4. ANTI-PREDICTIVE WEIGHT LEAKAGE")
print("=" * 80)
# Examine systems table or payload sections to find weights assigned to poor performers
systems = payload.get("systems", [])
if not systems:
    # Try other keys
    systems = payload.get("portfolio_stats", []) or payload.get("system_performance", [])

# If still not found, look at active picks to infer systems
active_picks = payload.get("picks", {}).get("active", [])
active_system_counts = defaultdict(int)
for p in active_picks:
    if isinstance(p, dict):
        active_system_counts[p.get("source_system", p.get("system", "UNKNOWN"))] += 1

print("Active pick counts per system (top 20):")
for sys, cnt in sorted(active_system_counts.items(), key=lambda x: -x[1])[:20]:
    print(f"  {sys:40s} | {cnt} active picks")

# Check for systems with picks but known low forward WR
leakage_suspects = []
for sys_name in active_system_counts:
    # Check if any strategy from this system has low WR
    low_wr_picks = sum(1 for strat, stats in low_wr_strategies if sys_name.lower() in strat.lower())
    if low_wr_picks > 0:
        leakage_suspects.append(sys_name)

if leakage_suspects:
    print("\nSuspected weight leakage (active systems with known low-WR strategies):")
    for s in leakage_suspects:
        print(f"  {s}")
else:
    print("\nNo obvious weight leakage suspects from quick scan.")

# ---- 5. Retired strategies still emitting (from active picks) ----
print("\n" + "=" * 80)
print("5. RETIRED STRATEGIES STILL EMITTING")
print("=" * 80)
# We need a retired list. Check kill_list.json if it exists.
retired = set()
kill_list_path = ROOT / "kill_list.json"
if kill_list_path.exists():
    with open(kill_list_path, "r") as f:
        try:
            kl = json.load(f)
            if isinstance(kl, list):
                retired = set(str(x) for x in kl)
            elif isinstance(kl, dict):
                retired = set(str(k) for k in kl.keys())
        except Exception:
            pass

# Also try strategies with names suggesting retired
retired_names = {"retired", "deprecated", "old", "legacy", "killed", "dead"}
for strat in strategy_stats:
    if any(r in strat.lower() for r in retired_names):
        retired.add(strat)

still_emitting = []
for p in active_picks:
    if not isinstance(p, dict):
        continue
    strat = p.get("strategy", "")
    sys = p.get("source_system", "")
    if strat in retired or sys in retired:
        still_emitting.append((strat, sys, p.get("symbol")))

if still_emitting:
    print(f"Found {len(still_emitting)} active picks from retired strategies/systems\n")
    for strat, sys, sym in still_emitting[:30]:
        print(f"  Strategy: {strat} | System: {sys} | Symbol: {sym}")
else:
    print("No retired strategies found emitting in active picks (based on available retire lists).")

# ---- Summary stats on battleground data ----
print("\n" + "=" * 80)
print("6. BATTLEGROUND DATA OVERVIEW")
print("=" * 80)
if bg_closed:
    bg_stats = defaultdict(lambda: {"wins":0, "losses":0})
    for p in bg_closed:
        if not isinstance(p, dict):
            continue
        strat = p.get("strategy", "UNKNOWN")
        pnl = p.get("pnl_pct", 0)
        if pnl is not None and float(pnl) > 0:
            bg_stats[strat]["wins"] += 1
        else:
            bg_stats[strat]["losses"] += 1
    low_bg = [(s, st["wins"]/(st["wins"]+st["losses"]) if (st["wins"]+st["losses"]) else 0) for s, st in bg_stats.items() if (st["wins"]+st["losses"])>0 and st["wins"]/(st["wins"]+st["losses"]) < 0.55]
    low_bg.sort(key=lambda x: x[1])
    print(f"Battleground closed picks: {len(bg_closed)}")
    print(f"Battleground strategies with WR < 55%: {len(low_bg)}")
    for s, wr in low_bg[:10]:
        print(f"  {s:50s} WR: {wr:.1%}")
else:
    print("No battleground closed picks loaded.")

# ---- TOP 3 ACTION ITEMS ----
print("\n" + "=" * 80)
print("TOP 3 ACTION ITEMS")
print("=" * 80)
print("""
1. CULL LOW-FORWARD-WR STRATEGIES
   - {} strategies have forward WR < 55% with >=5 picks.
   - Consider demoting or blocking these from active/strong feeds.
   - Highest impact culls: top volume low-WR strategies above.

2. INVESTIGATE STALE & STARVED NON-CRYPTO SYSTEMS
   - {} strategies have no pick in 7+ days.
   - {} non-crypto strategies are starved (<10 picks or WR<55%).
   - Non-crypto coverage is weak; either retire or reactivate with proven signals.

3. HARDEN ANTI-PREDICTIVE WEIGHTS & RETIRED STRATEGY GATES
   - Active system counts suggest some low-WR systems may still receive consensus weight.
   - Add gate: if a strategy/system's 30-day forward WR < 50%, weight = 0 until recovery.
   - Validate retired list against active pick feed to prevent zombie signals.
""".format(len(low_wr_strategies), len(stale_strategies), len(starved)))
