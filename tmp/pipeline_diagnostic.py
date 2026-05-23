#!/usr/bin/env python3
"""Simplified pipeline diagnostic"""
import json, sys
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

if sys.platform == "win32":
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')

ROOT = Path("e:/findtorontoevents_antigravity.ca")
NOW = datetime.now(timezone.utc)

def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return None

def parse_ts(val):
    if not val:
        return None
    if isinstance(val, (int, float)):
        if val > 1e12:
            val = val / 1000
        try:
            return datetime.fromtimestamp(val, tz=timezone.utc)
        except:
            return None
    if isinstance(val, str):
        try:
            clean = val.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except:
            return None
    return None

print("=" * 80)
print("  FULL PIPELINE DIAGNOSTIC")
print("  " + NOW.strftime("%Y-%m-%d %H:%M UTC"))
print("=" * 80)

# 1. DASHBOARD PAYLOAD
print("\n=== 1. DASHBOARD PAYLOAD ===")
dp = load_json(ROOT / "audit_trail/data/dashboard_payload.json")
if dp:
    print("  Keys:", list(dp.keys()))
    print("  Generated:", dp.get("generated_at", "?"))

    # picks
    picks = dp.get("picks", [])
    print("  picks type:", type(picks).__name__)
    if isinstance(picks, dict):
        print("  picks dict keys:", list(picks.keys())[:15])
        total_picks = 0
        pick_sources = defaultdict(int)
        all_pick_dicts = []
        for sys_name, sys_picks in picks.items():
            if isinstance(sys_picks, list):
                total_picks += len(sys_picks)
                for p in sys_picks:
                    if isinstance(p, dict):
                        pick_sources[p.get("source_system", sys_name)] += 1
                        all_pick_dicts.append(p)
            elif isinstance(sys_picks, dict):
                sub_picks = sys_picks.get("picks", [])
                total_picks += len(sub_picks)
                for p in sub_picks:
                    if isinstance(p, dict):
                        pick_sources[p.get("source_system", sys_name)] += 1
                        all_pick_dicts.append(p)
        print("  Total picks across all systems:", total_picks)
        print("  By source:")
        for s, c in sorted(pick_sources.items(), key=lambda x: -x[1])[:20]:
            print("    " + s + ": " + str(c))
        
        # Freshness of dashboard picks
        dp_dates = []
        for p in all_pick_dicts:
            for key in ["entry_date", "detected_at", "created_at", "recorded_at", "timestamp"]:
                ts = parse_ts(p.get(key))
                if ts:
                    dp_dates.append(ts)
                    break
        if dp_dates:
            newest = max(dp_dates)
            oldest = min(dp_dates)
            print("  Newest dashboard pick:", newest.strftime("%Y-%m-%d %H:%M UTC"), "({:.1f}h ago)".format((NOW-newest).total_seconds()/3600))
            print("  Oldest dashboard pick:", oldest.strftime("%Y-%m-%d %H:%M UTC"))
    elif isinstance(picks, list):
        print("  picks list count:", len(picks))
        if picks:
            first = picks[0]
            print("  First pick type:", type(first).__name__)


    # systems
    systems = dp.get("systems", {})
    print("  systems type:", type(systems).__name__)
    if isinstance(systems, dict):
        snames = list(systems.keys())
        print("  System count:", len(snames))
        print("  System names:", snames[:15])
        # Sample first system
        if snames:
            first_sys = systems[snames[0]]
            if isinstance(first_sys, dict):
                print("  First system keys:", list(first_sys.keys())[:10])
                sys_picks = first_sys.get("picks", [])
                print("  First system picks count:", len(sys_picks))
                if sys_picks and isinstance(sys_picks[0], dict):
                    print("  First pick keys:", list(sys_picks[0].keys())[:10])

    # leaderboard
    lb = dp.get("leaderboard", {})
    print("  leaderboard count:", len(lb) if isinstance(lb, (dict, list)) else "?")

# 2. COPY TRADER INTEL PICKS
print("\n=== 2. COPY TRADER INTEL ACTIVE PICKS ===")
ct_data = load_json(ROOT / "copy_trader_intel/data/active_picks.json")
if ct_data:
    ct_picks = ct_data if isinstance(ct_data, list) else ct_data.get("picks", ct_data.get("active_picks", []))
    print("  Total picks:", len(ct_picks))

    # Strategy breakdown
    strats = defaultdict(int)
    for p in ct_picks:
        strats[p.get("strategy", "?")] += 1
    print("  By strategy:")
    for s, c in sorted(strats.items(), key=lambda x: -x[1])[:15]:
        print("    " + s + ": " + str(c))

    # Asset class breakdown
    cats = defaultdict(int)
    for p in ct_picks:
        cats[p.get("category", "?")] += 1
    print("  By category:")
    for c, n in sorted(cats.items(), key=lambda x: -x[1]):
        print("    " + str(c) + ": " + str(n))

    # Freshness
    dates = []
    for p in ct_picks:
        for key in ["entry_date", "detected_at", "created_at", "timestamp"]:
            ts = parse_ts(p.get(key))
            if ts:
                dates.append(ts)
                break
    if dates:
        newest = max(dates)
        oldest = min(dates)
        print("  Newest:", newest.strftime("%Y-%m-%d %H:%M UTC"))
        print("  Oldest:", oldest.strftime("%Y-%m-%d %H:%M UTC"))
        age_h = (NOW - newest).total_seconds() / 3600
        print("  Newest age: {:.1f} hours ago".format(age_h))

        buckets = {"<1h": 0, "1-6h": 0, "6-24h": 0, "1-3d": 0, "3-7d": 0, ">7d": 0}
        for ts in dates:
            h = (NOW - ts).total_seconds() / 3600
            if h < 1: buckets["<1h"] += 1
            elif h < 6: buckets["1-6h"] += 1
            elif h < 24: buckets["6-24h"] += 1
            elif h < 72: buckets["1-3d"] += 1
            elif h < 168: buckets["3-7d"] += 1
            else: buckets[">7d"] += 1
        print("  Timeframe:")
        for b, c in buckets.items():
            bar = "#" * min(c, 50)
            print("    {:>6s}: {:4d} {}".format(b, c, bar))
else:
    print("  [MISSING]")

# 3. ALPHA ENGINE PICKS
print("\n=== 3. ALPHA ENGINE ACTIVE PICKS ===")
ae = load_json(ROOT / "alpha_engine/data/active_picks.json")
if ae:
    ae_picks = ae if isinstance(ae, list) else ae.get("picks", ae.get("active_picks", []))
    print("  Total picks:", len(ae_picks))
    ae_src = defaultdict(int)
    for p in ae_picks:
        if isinstance(p, dict):
            ae_src[p.get("source_system", p.get("strategy", "?"))] += 1
    for s, c in sorted(ae_src.items(), key=lambda x: -x[1])[:10]:
        print("    " + s + ": " + str(c))
else:
    print("  [MISSING]")

# 4. CTI DATABASE
print("\n=== 4. COPYTRADER DATABASE ===")
cdb = load_json(ROOT / "copy_trader_intel/data/copytrader_database.json")
if cdb:
    print("  Version:", cdb.get("version", "?"))
    print("  Total:", cdb.get("total_unique", "?"))
    print("  Crypto:", cdb.get("crypto_total", "?"))
    print("  Forex:", cdb.get("forex_total", "?"))
    print("  Quality dist:", cdb.get("quality_distribution", "?"))
    for p, v in list(cdb.get("by_platform", {}).items())[:10]:
        print("    " + p + ": " + str(v))
else:
    print("  [MISSING]")

# 5. QUALITY BACKTEST
print("\n=== 5. QUALITY BACKTEST RESULTS ===")
qbr = load_json(ROOT / "copy_trader_intel/data/quality_backtest_results.json")
if qbr:
    print("  Traders analyzed:", qbr.get("total_traders_analyzed", "?"))
    for code, q in qbr.get("quality_reports", {}).items():
        name = qbr.get("backtest_results", {}).get(code, {}).get("trader_name", code[:12])
        m = q["metrics"]
        print("  [{}] {} WR:{}% PF:{} PnL:${:,.0f} DD:{:.0f}%".format(
            q["quality_grade"], name, m["win_rate"], m["profit_factor"], m["total_pnl_usd"], m["max_drawdown_pct"]))
else:
    print("  [MISSING]")

# 6. WIRING CHECK
print("\n=== 6. WIRING: dashboard_generator.py ===")
dg_path = ROOT / "audit_trail/dashboard_generator.py"
if dg_path.exists():
    with open(dg_path, "r", encoding="utf-8", errors="replace") as f:
        dg = f.read()
    for kw in ["copy_trader", "active_picks", "at_raw_picks", "at_consensus", "source_system", "copy_trader_intel"]:
        count = dg.count(kw)
        if count > 0:
            print("  '{}': {} refs".format(kw, count))
        else:
            print("  '{}': NOT FOUND".format(kw))
else:
    print("  [MISSING]")

# Forex futures picks
print("\n=== 7. FOREX/FUTURES PICKS ===")
ffp = load_json(ROOT / "audit_dashboard/data/forex_futures_picks.json")
if ffp:
    if isinstance(ffp, list):
        print("  Type: list, count:", len(ffp))
    elif isinstance(ffp, dict):
        plist = ffp.get("picks", [])
        print("  Count:", len(plist))
        ff_src = defaultdict(int)
        for p in plist:
            if isinstance(p, dict):
                ff_src[p.get("source_system", "?")] += 1
        for s, c in sorted(ff_src.items(), key=lambda x: -x[1])[:10]:
            print("    " + s + ": " + str(c))
else:
    print("  [MISSING]")

# Health report
print("\n=== 8. HEALTH REPORT ===")
hr = load_json(ROOT / "copy_trader_intel/data/health_report.json")
if hr:
    print("  Generated:", hr.get("generated_at", "?"))
    print("  Total picks:", hr.get("total_active_picks", "?"))
    print("  Status:", hr.get("overall_status", "?"))
    issues = hr.get("issues", [])
    print("  Issues:", len(issues))
    for i in issues[:5]:
        print("    -", str(i)[:100])
else:
    print("  [MISSING]")

print("\n" + "=" * 80)
print("  DIAGNOSTIC COMPLETE")
print("=" * 80)
