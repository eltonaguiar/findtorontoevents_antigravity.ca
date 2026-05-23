"""
DEEP AUDIT: Comprehensive reasonability check of ALL systems and picks.
Flags:
  - Systems with 0 active picks (disabled/idle?)
  - Suspicious PF (>10 or infinity-like)
  - Suspicious PnL values (>25% on single trade)
  - Systems with synthetic/backtest data mixed in
  - Systems with too few trades to be statistically significant
  - Mismatched win/loss counts vs closed picks
  - Systems with extreme max drawdown
"""
import json
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parent.parent
d = json.load(open(ROOT / "audit_trail/data/dashboard_payload.json", "r", encoding="utf-8"))

systems = d.get("systems", [])
active_picks = d["picks"]["active"]
closed_picks = d["picks"].get("closed", [])

print("=" * 80)
print("  DEEP SYSTEM AUDIT REPORT")
print("  Generated from dashboard_payload.json")
print("=" * 80)

# Build pick lookup
picks_by_sys = defaultdict(list)
closed_by_sys = defaultdict(list)
for p in active_picks:
    picks_by_sys[p.get("source_system", "?")].append(p)
for p in closed_picks:
    closed_by_sys[p.get("source_system", "?")].append(p)

# Categorize issues
critical = []
warnings = []
info = []

for s in sorted(systems, key=lambda x: x.get("name", "")):
    name = s.get("name", "?")
    wr = s.get("win_rate") or 0
    pf = s.get("profit_factor")
    exp = s.get("expectancy") or 0
    dd = s.get("max_drawdown") or 0
    closed = s.get("closed_picks") or 0
    active = s.get("active_picks") or 0
    wins = s.get("wins") or 0
    losses = s.get("losses") or 0
    avg_win = s.get("avg_win") or 0
    avg_loss = s.get("avg_loss") or 0
    
    # 1. Zero active picks with proven-tier performance
    if active == 0 and closed >= 5 and wr >= 50:
        critical.append(f"[IDLE] {name}: 0 active picks but WR={wr:.1f}% ({closed} closed). Why is this system not generating picks?")
    
    # 2. Suspicious profit factor
    if pf is not None and pf > 10 and closed < 20:
        warnings.append(f"[HIGH PF] {name}: PF={pf:.2f} but only {closed} trades. Likely small sample / lucky streak, not statistically significant.")
    
    # 3. PF of 0 or None with trades
    if closed >= 5 and (pf is None or pf == 0):
        warnings.append(f"[MISSING PF] {name}: {closed} closed trades but PF=None/0. Win/loss accounting may be broken.")
    
    # 4. Win/loss count mismatch
    if closed > 0 and wins + losses > 0:
        expected_wr = (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0
        if abs(expected_wr - wr) > 2:
            warnings.append(f"[WR MISMATCH] {name}: reported WR={wr:.1f}% but wins/losses={wins}/{losses} => {expected_wr:.1f}%")
    
    # 5. Extreme drawdown (>100% means position sizing is wrong)
    if dd > 100:
        critical.append(f"[EXTREME DD] {name}: max_drawdown={dd:.1f}% (>100%!). This suggests position sizing errors or cumulative tracking bug.")
    
    # 6. Too few trades to trust
    if closed > 0 and closed < 5 and wr >= 60:
        info.append(f"[SAMPLE] {name}: WR={wr:.1f}% looks impressive but only {closed} trades. Not statistically reliable.")
    
    # 7. Negative expectancy systems that are still active
    if exp < -1 and active > 0:
        warnings.append(f"[LOSING] {name}: expectancy={exp:.2f}% but still has {active} active picks. Should this be disabled?")
    
    # 8. Zero closed + zero active = ghost system
    if closed == 0 and active == 0:
        info.append(f"[GHOST] {name}: 0 closed, 0 active. System never produced picks or all data lost.")

# Check individual picks for suspicious PnL
print("\n--- SUSPICIOUS INDIVIDUAL PICKS ---")
sus_picks = []
for p in closed_picks:
    pnl = p.get("pnl_pct") or 0
    if abs(pnl) > 25:
        sus_picks.append(p)

for p in active_picks:
    pnl = p.get("pnl_pct") or 0
    if abs(pnl) > 25:
        sus_picks.append(p)

print(f"Picks with |PnL| > 25%: {len(sus_picks)}")
for p in sorted(sus_picks, key=lambda x: abs(x.get("pnl_pct",0) or 0), reverse=True)[:20]:
    pnl = p.get("pnl_pct") or 0
    print(f"  {p.get('symbol')} {p.get('direction')} PnL={pnl:.1f}% sys={p.get('source_system')} strat={p.get('strategy','')[:40]}")

# Check for potential synthetic/backtest data
print("\n--- POTENTIAL SYNTHETIC DATA CHECK ---")
for s in systems:
    name = s.get("name", "")
    # Systems with "backtest" or "simulated" in name
    if any(kw in name.lower() for kw in ["backtest", "simulated", "synthetic", "paper"]):
        print(f"  [SYNTHETIC?] {name}: WR={s.get('win_rate',0):.1f}% closed={s.get('closed_picks',0)} - NAME suggests non-live data")
    # Systems with suspiciously perfect records
    if s.get("win_rate",0) == 100 and (s.get("closed_picks",0) or 0) >= 5:
        print(f"  [PERFECT?] {name}: 100% WR on {s.get('closed_picks',0)} trades - verify these are real forward tests")

# Check baby_strats_forward specifically (920 closed, 47.6% WR)
print("\n--- HIGH-VOLUME SYSTEMS CHECK ---")
for s in systems:
    if (s.get("closed_picks") or 0) >= 100:
        name = s.get("name","")
        print(f"  {name}: {s.get('closed_picks')} closed, WR={s.get('win_rate',0):.1f}%, PF={s.get('profit_factor','?')}, DD={s.get('max_drawdown',0):.1f}%")
        # Check if this could be forward or backtest
        actual_closed = closed_by_sys.get(name, [])
        if len(actual_closed) > 0:
            # Check date range
            dates = [p.get("closed_at") or p.get("timestamp","") for p in actual_closed]
            dates = [d for d in dates if d]
            if dates:
                print(f"    Date range: {min(dates)[:10]} to {max(dates)[:10]}")

# Print findings
print("\n" + "=" * 80)
print(f"  CRITICAL ISSUES: {len(critical)}")
print("=" * 80)
for c in critical:
    print(f"  {c}")

print("\n" + "=" * 80)
print(f"  WARNINGS: {len(warnings)}")
print("=" * 80)
for w in warnings:
    print(f"  {w}")

print("\n" + "=" * 80)
print(f"  INFO: {len(info)}")
print("=" * 80)
for i in info[:30]:
    print(f"  {i}")
if len(info) > 30:
    print(f"  ... and {len(info)-30} more")

# Specific deep-dive: why claude_gainer_ml_perf has 0 active
print("\n" + "=" * 80)
print("  DEEP DIVE: Systems with data but 0 active picks")
print("=" * 80)
for s in systems:
    name = s.get("name","")
    if (s.get("closed_picks") or 0) >= 5 and (s.get("active_picks") or 0) == 0:
        actual_picks = picks_by_sys.get(name, [])
        actual_closed = closed_by_sys.get(name, [])
        print(f"\n  {name}:")
        print(f"    Reported: closed={s.get('closed_picks')}, active={s.get('active_picks')}")
        print(f"    Actual in payload: active={len(actual_picks)}, closed={len(actual_closed)}")
        print(f"    WR={s.get('win_rate',0):.1f}% PF={s.get('profit_factor','?')} exp={s.get('expectancy',0)}")
        print(f"    Last signal: {s.get('last_signal_at','unknown')}")
        # Is the scanner even running?
        status = s.get("status", "unknown")
        print(f"    Status: {status}")

# Summary
print("\n" + "=" * 80)
print("  REASONABILITY SUMMARY")
print("=" * 80)
systems_with_data = [s for s in systems if (s.get("closed_picks") or 0) > 0]
proven = [s for s in systems_with_data if s.get("win_rate",0) >= 50 and (s.get("closed_picks",0) or 0) >= 10]
losing = [s for s in systems_with_data if s.get("win_rate",0) < 45 and (s.get("closed_picks",0) or 0) >= 10]
print(f"  Total systems: {len(systems)}")
print(f"  Systems with closed trades: {len(systems_with_data)}")
print(f"  Winning systems (WR>=50%, 10+ trades): {len(proven)}")
for p in sorted(proven, key=lambda x: x.get("win_rate",0), reverse=True):
    print(f"    {p.get('name')}: WR={p.get('win_rate',0):.1f}% PF={p.get('profit_factor','?')} ({p.get('closed_picks',0)} trades)")
print(f"  Losing systems (WR<45%, 10+ trades): {len(losing)}")
for l in sorted(losing, key=lambda x: x.get("win_rate",0)):
    print(f"    {l.get('name')}: WR={l.get('win_rate',0):.1f}% PF={l.get('profit_factor','?')} ({l.get('closed_picks',0)} trades)")
