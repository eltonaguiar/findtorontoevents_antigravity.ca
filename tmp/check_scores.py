"""Quick check of active picks data to understand scoring inputs."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
d = json.load(open(ROOT / "audit_trail/data/dashboard_payload.json", "r", encoding="utf-8"))
picks = d["picks"]["active"]
print(f"Total active picks: {len(picks)}")
print()

# Show first 15 picks by most recent
picks_sorted = sorted(picks, key=lambda p: p.get("timestamp", ""), reverse=True)[:15]

for i, p in enumerate(picks_sorted):
    sym = p.get("symbol", "?")
    dr = p.get("direction", "?")
    sys = p.get("source_system", "?")
    strat = p.get("strategy", "?")[:40]
    conf = p.get("confidence")
    fwd_wr = p.get("strat_fwd_wr")
    fwd_trades = p.get("strat_fwd_trades", 0)
    fwd_pf = p.get("strat_fwd_pf")
    trust = p.get("trust_tier", "?")
    agree = p.get("agreement_count", 0)
    health = p.get("strat_health", "?")
    age = p.get("age_hours")
    pnl = p.get("pnl_pct")
    conflict = p.get("has_conflict", False)
    
    print(f"[{i+1}] {sym} {dr}")
    print(f"    sys={sys}  strat={strat}")
    print(f"    conf={conf}  fwd_wr={fwd_wr}  fwd_trades={fwd_trades}  fwd_pf={fwd_pf}")
    print(f"    trust={trust}  agreement={agree}  health={health}")
    print(f"    age_h={age}  pnl%={pnl}  conflict={conflict}")
    print()

# Show system stats
print("=" * 60)
print("SYSTEM STATS (for scoring)")
systems = d.get("systems", [])
for s in sorted(systems, key=lambda x: x.get("win_rate", 0), reverse=True)[:15]:
    n = s.get("name", "?")
    wr = s.get("win_rate", 0)
    closed = s.get("closed_picks", 0)
    total = s.get("total_trades", 0)
    pf = s.get("profit_factor")
    exp = s.get("expectancy")
    print(f"  {n}: WR={wr}%  closed={closed}  total={total}  PF={pf}  exp={exp}")

# Simulate scoring for top picks
print()
print("=" * 60)
print("SIMULATED SCORE BREAKDOWN (replicating JS computeScore)")
print()

def simulate_score(p, systems):
    """Replicate the JS computeScore function."""
    breakdown = {}
    
    # 1. Strategy Performance (20%)
    fwd_wr = p.get("strat_fwd_wr") or 0
    fwd_pf = p.get("strat_fwd_pf") or 0
    health = p.get("strat_health")
    perf_base = min(100, (fwd_wr * 0.6) + (min(fwd_pf, 3) / 3 * 100 * 0.4))
    health_mult = 1.0 if health == "healthy" else 0.75 if health == "watch" else 0.4 if health == "degraded" else 0.5
    breakdown["strategy"] = round(perf_base * health_mult)
    
    # 2. Signal Quality (20%)
    conf = (p.get("confidence") or 0) * 100
    entry = float(p.get("entry_price") or 0)
    tp = float(p.get("take_profit") or 0)
    sl = float(p.get("stop_loss") or 0)
    rr_score = 50
    if entry and tp and sl:
        rr = abs(tp - entry) / (abs(entry - sl) or 1)
        rr_score = min(100, rr * 40)
    breakdown["signal"] = round(conf * 0.6 + rr_score * 0.4)
    
    # 3. Freshness (20%)
    age = p.get("age_hours") or 999
    if age <= 1: freshness = 100
    elif age <= 4: freshness = 85
    elif age <= 12: freshness = 65
    elif age <= 24: freshness = 45
    elif age <= 48: freshness = 25
    else: freshness = 10
    breakdown["freshness"] = freshness
    
    # 4. Forward Performance (10%)
    fwd_score = 50
    sys_data = None
    for s in systems:
        if s.get("name") == p.get("source_system"):
            sys_data = s
            break
    if sys_data and (sys_data.get("closed_picks") or 0) >= 5:
        wr_score = min(100, (sys_data.get("win_rate") or 0) * 1.2)
        pf_score = min(100, ((sys_data.get("profit_factor") or 0) - 0.5) * 100)
        exp_val = sys_data.get("expectancy") or 0
        exp_score = min(100, max(0, (exp_val + 5) * 10))
        fwd_score = round(wr_score * 0.5 + pf_score * 0.3 + exp_score * 0.2)
    breakdown["forward"] = max(0, min(100, fwd_score))
    
    # 5. Consensus (10%)
    agree = p.get("agreement_count") or 0
    breakdown["consensus"] = min(100, agree * 35)
    
    # 6. No-conflict (20%)
    breakdown["noConflict"] = 0 if p.get("has_conflict") else 100
    
    # Raw total
    raw_total = round(
        breakdown["strategy"] * 0.20 +
        breakdown["signal"] * 0.20 +
        breakdown["freshness"] * 0.20 +
        breakdown["forward"] * 0.10 +
        breakdown["consensus"] * 0.10 +
        breakdown["noConflict"] * 0.20
    )
    
    # Trust tier (simplified — just use from data)
    trust_tier = p.get("trust_tier", "SANDBOX")
    trust_w = {"PROVEN": 1.0, "PROBATION": 0.7, "SANDBOX": 0.65, "DEMOTED": 0.3}.get(trust_tier, 0.65)
    after_trust = round(raw_total * trust_w)
    
    # Time decay
    decay_age = p.get("age_hours") or 999
    if decay_age <= 2: time_decay = 1.0
    elif decay_age <= 6: time_decay = 0.95
    elif decay_age <= 12: time_decay = 0.85
    elif decay_age <= 24: time_decay = 0.70
    elif decay_age <= 36: time_decay = 0.55
    elif decay_age <= 48: time_decay = 0.40
    else: time_decay = 0.25
    after_decay = round(after_trust * time_decay)
    
    # Entry drift
    pnl = p.get("pnl_pct") or 0
    if pnl < -3: entry_drift = 0.3
    elif pnl < -2: entry_drift = 0.5
    elif pnl < -1: entry_drift = 0.7
    elif pnl > 8: entry_drift = 0.4
    elif pnl > 5: entry_drift = 0.6
    elif pnl > 3: entry_drift = 0.85
    else: entry_drift = 1.0
    
    # Conflict penalty
    conflict_penalty = 0.7 if p.get("has_conflict") else 1.0
    
    adjusted = round(after_decay * entry_drift * conflict_penalty)
    final = max(0, min(100, adjusted))
    
    return final, {
        "raw_total": raw_total,
        "trust_tier": trust_tier,
        "trust_w": trust_w,
        "after_trust": after_trust,
        "time_decay": time_decay,
        "after_decay": after_decay,
        "entry_drift": entry_drift,
        "conflict_penalty": conflict_penalty,
        "final": final,
        **breakdown
    }


# Score all picks and show top 10
scored = []
for p in picks:
    score, bd = simulate_score(p, systems)
    scored.append((score, p, bd))

scored.sort(key=lambda x: x[0], reverse=True)

for i, (score, p, bd) in enumerate(scored[:15]):
    print(f"[{i+1}] SCORE={score}  {p.get('symbol')} {p.get('direction')}  sys={p.get('source_system')}")
    print(f"    strategy={bd['strategy']} signal={bd['signal']} freshness={bd['freshness']} forward={bd['forward']} consensus={bd['consensus']} noConflict={bd['noConflict']}")
    print(f"    raw_total={bd['raw_total']} trust={bd['trust_tier']}(x{bd['trust_w']}) after_trust={bd['after_trust']}")
    print(f"    time_decay=x{bd['time_decay']} after_decay={bd['after_decay']} entry_drift=x{bd['entry_drift']} conflict=x{bd['conflict_penalty']}")
    print()

# Show distribution
import collections
buckets = collections.Counter()
for s, p, _ in scored:
    if s >= 70: buckets["70-100 (excellent)"] += 1
    elif s >= 50: buckets["50-69 (good)"] += 1
    elif s >= 30: buckets["30-49 (mediocre)"] += 1
    else: buckets["0-29 (poor)"] += 1

print("=" * 60)
print("SCORE DISTRIBUTION")
for bucket in sorted(buckets.keys(), reverse=True):
    print(f"  {bucket}: {buckets[bucket]} picks")

# Key insights
print()
print("=" * 60)
print("KEY ISSUES AFFECTING SCORES")
no_health = sum(1 for _, p, _ in scored if not p.get("strat_health"))
no_fwd_wr = sum(1 for _, p, _ in scored if not p.get("strat_fwd_wr"))
no_conf = sum(1 for _, p, _ in scored if not p.get("confidence"))
all_conflict = sum(1 for _, p, _ in scored if p.get("has_conflict"))
sandbox = sum(1 for _, p, _ in scored if p.get("trust_tier") == "SANDBOX")
demoted = sum(1 for _, p, _ in scored if p.get("trust_tier") == "DEMOTED")
probation = sum(1 for _, p, _ in scored if p.get("trust_tier") == "PROBATION")
proven = sum(1 for _, p, _ in scored if p.get("trust_tier") == "PROVEN")
old_24h = sum(1 for _, p, _ in scored if (p.get("age_hours") or 0) > 24)
old_48h = sum(1 for _, p, _ in scored if (p.get("age_hours") or 0) > 48)
print(f"  Missing strat_health: {no_health}/{len(scored)}")
print(f"  Missing strat_fwd_wr: {no_fwd_wr}/{len(scored)}")
print(f"  Missing confidence: {no_conf}/{len(scored)}")
print(f"  Has conflict: {all_conflict}/{len(scored)}")
print(f"  Trust tiers: PROVEN={proven} PROBATION={probation} SANDBOX={sandbox} DEMOTED={demoted}")
print(f"  Age >24h: {old_24h}  Age >48h: {old_48h}")
