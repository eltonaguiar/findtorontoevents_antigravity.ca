"""Quick check: simulate NEW scoring to compare before/after."""
import json, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
d = json.load(open(ROOT / "audit_trail/data/dashboard_payload.json", "r", encoding="utf-8"))
picks = d["picks"]["active"]
systems = d.get("systems", [])

def simulate_score_new(p, systems):
    """Replicate the FIXED JS computeScore function."""
    breakdown = {}
    
    # 1. Strategy Performance (25%)
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
    
    # 3. Freshness (15%)
    age = p.get("age_hours") or 999
    if age <= 1: freshness = 100
    elif age <= 4: freshness = 85
    elif age <= 12: freshness = 65
    elif age <= 24: freshness = 45
    elif age <= 48: freshness = 25
    else: freshness = 10
    breakdown["freshness"] = freshness
    
    # 4. Forward Performance (15%)
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
    
    # 5. Consensus (15%)
    agree = p.get("agreement_count") or 0
    breakdown["consensus"] = min(100, agree * 35)
    
    # 6. No-conflict (10%) — NOW: conflicted = 30, not 0
    breakdown["noConflict"] = 30 if p.get("has_conflict") else 100
    
    # Raw total — NEW weights
    raw_total = round(
        breakdown["strategy"] * 0.25 +
        breakdown["signal"] * 0.20 +
        breakdown["freshness"] * 0.15 +
        breakdown["forward"] * 0.15 +
        breakdown["consensus"] * 0.15 +
        breakdown["noConflict"] * 0.10
    )
    
    # Trust tier — NEW logic with auto-trust
    trust_tier, trust_w = get_trust_new(p, systems)
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
    
    # NO separate conflict penalty — REMOVED
    adjusted = round(after_decay * entry_drift)
    final = max(0, min(100, adjusted))
    
    return final, {
        "raw_total": raw_total,
        "trust_tier": trust_tier,
        "trust_w": trust_w,
        "after_trust": after_trust,
        "time_decay": time_decay,
        "after_decay": after_decay,
        "entry_drift": entry_drift,
        "final": final,
        **breakdown
    }

# PROVEN systems mapping (from template.html)
PROVEN_SYSTEMS = {
    'battleground': 1.0,
    'alpha_engine': 0.85,
    'luxalgo_filters': 0.95,
    'claude_gainer': 0.75,
    'claude_gainer_ml_perf': 0.75,
    'crypto_ml_edge': 0.70,
    'ml_bg_system_f': 0.70,
    'ml_claws_of_doom': 0.70,
}

PROBATION = ['baby_strats_forward', 'ml_bg_system_c', 'mercury2_fast', 'ml_crypto_predictor', 
             'ml_filter_a', 'paper_trading', 'multi_asset_institutional', 'rapid_fire']

def get_trust_new(p, systems):
    """Replicate new getTrustTier with auto-trust."""
    sys_name = (p.get("source_system") or "").lower()
    
    # Check probation first
    for prob in PROBATION:
        if prob in sys_name:
            return "PROBATION", 0.1
    
    # Check proven systems
    for name, w in PROVEN_SYSTEMS.items():
        if name in sys_name:
            return "PROVEN", w
    
    # Auto-trust from system data
    for s in systems:
        if s.get("name") == p.get("source_system"):
            closed = s.get("closed_picks") or 0
            if closed >= 5:
                wr = s.get("win_rate") or 0
                pf = s.get("profit_factor") or 0
                if wr >= 60 and pf >= 2.0: return "RELIABLE", 0.90
                if wr >= 55 and pf >= 1.5: return "RELIABLE", 0.80
                if wr >= 50: return "WATCH", 0.70
                if wr >= 45: return "WATCH", 0.55
                return "SANDBOX", 0.40
    
    return "SANDBOX", 0.35

# Score all picks
scored = [(simulate_score_new(p, systems)[0], p, simulate_score_new(p, systems)[1]) for p in picks]
scored.sort(key=lambda x: x[0], reverse=True)

print("=" * 70)
print("  NEW SCORING — TOP 20 PICKS")
print("=" * 70)
for i, (score, p, bd) in enumerate(scored[:20]):
    conflict = "CONF" if p.get("has_conflict") else "    "
    print(f"[{i+1:>2}] SCORE={score:>3}  {conflict} {p.get('symbol'):<14} {p.get('direction'):<6}  sys={p.get('source_system')}")
    print(f"     strat={bd['strategy']:>3} sig={bd['signal']:>3} fresh={bd['freshness']:>3} fwd={bd['forward']:>3} cons={bd['consensus']:>3} noConf={bd['noConflict']:>3}")
    print(f"     raw={bd['raw_total']:>3}  trust={bd['trust_tier']}(x{bd['trust_w']})  decay=x{bd['time_decay']}  drift=x{bd['entry_drift']}")
    print()

# Distribution
buckets = collections.Counter()
for s, p, _ in scored:
    if s >= 80: buckets["80-100 (excellent)"] += 1
    elif s >= 60: buckets["60-79 (good)"] += 1
    elif s >= 40: buckets["40-59 (mediocre)"] += 1
    elif s >= 20: buckets["20-39 (poor)"] += 1
    else: buckets["0-19 (terrible)"] += 1

print("=" * 70)
print("  SCORE DISTRIBUTION (NEW vs OLD)")
print("=" * 70)
for bucket in sorted(buckets.keys(), reverse=True):
    print(f"  {bucket}: {buckets[bucket]} picks")

print(f"\n  Total picks: {len(scored)}")
print(f"  Conflicted: {sum(1 for _, p, _ in scored if p.get('has_conflict'))}")
print(f"  Trust: PROVEN={sum(1 for _, _, b in scored if b['trust_tier']=='PROVEN')} "
      f"RELIABLE={sum(1 for _, _, b in scored if b['trust_tier']=='RELIABLE')} "
      f"WATCH={sum(1 for _, _, b in scored if b['trust_tier']=='WATCH')} "
      f"SANDBOX={sum(1 for _, _, b in scored if b['trust_tier']=='SANDBOX')} "
      f"PROBATION={sum(1 for _, _, b in scored if b['trust_tier']=='PROBATION')}")
