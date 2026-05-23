#!/usr/bin/env python3
"""
Audit analysis script — reads dashboard_data.json and produces a structured
performance report for all asset classes and source systems.
"""
import json, sys

with open('audit_dashboard/data/dashboard_data.json') as f:
    data = json.load(f)

# ── Asset class health ────────────────────────────────────────────────────────
print("=" * 70)
print("ASSET CLASS HEALTH (post-resolver-v2)")
print("=" * 70)
ach = data['performance'].get('asset_class_health', {})
by_ac = data['performance'].get('by_asset_class', {})
CHARTER = {'T1': {'pf': 2.0, 'wr': 55.0, 'mdd': 10.0},
           'T2': {'pf': 1.5, 'wr': 50.0, 'mdd': 20.0},
           'FLOOR': {'pf': 1.0, 'wr': 45.0}}

for cls in ['CRYPTO', 'EQUITY', 'COMMODITY', 'FOREX', 'ETF', 'BOND', 'FUTURES', 'UNKNOWN']:
    raw = by_ac.get(cls, {})
    health = ach.get(cls, {})
    pf = raw.get('profit_factor') or health.get('profit_factor') or health.get('pf')
    wr = raw.get('win_rate') or health.get('win_rate') or health.get('wr')
    closed = raw.get('closed', 0)
    wins = raw.get('wins', 0)
    losses = raw.get('losses', 0)
    pnl = raw.get('pnl', 0)
    avg_win = raw.get('avg_win', 0)
    avg_loss = raw.get('avg_loss', 0)
    exp = raw.get('expectancy', 0)
    active = raw.get('active', 0)

    tier = "SUB-FLOOR"
    if pf and wr:
        if pf >= 2.0 and wr >= 55.0:
            tier = "T1 (Renaissance)"
        elif pf >= 1.5 and wr >= 50.0:
            tier = "T2 (Institutional)"
        elif pf >= 1.0:
            tier = "T3 (Marginal)"

    print(f"\n{cls}")
    print(f"  Tier       : {tier}")
    print(f"  PF         : {pf}")
    print(f"  Win Rate   : {wr}%")
    print(f"  Closed     : {closed}  (Active: {active})")
    print(f"  Wins/Losses: {wins}/{losses}")
    print(f"  Avg Win    : {avg_win}%  Avg Loss: {avg_loss}%")
    print(f"  Expectancy : {exp}%")
    print(f"  Total PnL  : {pnl}")

# ── Systems ranked by PF ──────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("SOURCE SYSTEMS RANKED BY PROFIT FACTOR")
print("=" * 70)
systems = data.get('systems', [])
ranked = []
for s in systems:
    if isinstance(s, dict):
        name = s.get('name', 'unknown')
        pf = s.get('profit_factor', 0) or 0
        wr = s.get('win_rate', 0) or 0
        n = s.get('closed_picks', s.get('count', 0)) or 0
        pnl = s.get('total_pnl', s.get('pnl', 0)) or 0
        ranked.append({'name': name, 'pf': pf, 'wr': wr, 'n': n, 'pnl': pnl})

ranked.sort(key=lambda x: x['pf'], reverse=True)
print(f"\n{'System':<45} {'PF':>6} {'WR':>7} {'Closed':>8} {'PnL':>10}")
print("-" * 80)
for s in ranked:
    print(f"  {s['name']:<43} {s['pf']:>6.2f} {s['wr']:>6.1f}% {s['n']:>8} {s['pnl']:>10.2f}")

# ── Tier-2 proven strategies ──────────────────────────────────────────────────
print("\n" + "=" * 70)
print("TIER-2 PROVEN STRATEGIES")
print("=" * 70)
t2 = data.get('tier2_proven_strategies', [])
if isinstance(t2, list):
    for s in t2[:20]:
        print(f"  {json.dumps(s)[:120]}")
elif isinstance(t2, dict):
    for k, v in list(t2.items())[:20]:
        print(f"  {k}: {json.dumps(v)[:100]}")

# ── Shadow / probation ────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("SHADOW PROBATION (failing strategies)")
print("=" * 70)
shadow = data.get('shadow_probation', [])
if isinstance(shadow, list):
    for s in shadow[:30]:
        print(f"  {json.dumps(s)[:140]}")
elif isinstance(shadow, dict):
    for k, v in list(shadow.items())[:30]:
        print(f"  {k}: {json.dumps(v)[:100]}")

# ── HF decay watchlist ────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("HF DECAY WATCHLIST")
print("=" * 70)
hf_decay = data.get('hf_decay_watchlist', [])
if isinstance(hf_decay, list):
    for s in hf_decay[:20]:
        print(f"  {json.dumps(s)[:140]}")

# ── Backtest vs Forward ───────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("BACKTEST VS FORWARD VALIDATION")
print("=" * 70)
bvf = data.get('backtest_vs_forward', {})
if isinstance(bvf, dict):
    for k, v in list(bvf.items())[:10]:
        print(f"  {k}: {json.dumps(v)[:200]}")

# ── Performance alerts ────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("PERFORMANCE ALERTS")
print("=" * 70)
alerts = data.get('performance_alerts', [])
if isinstance(alerts, list):
    for a in alerts[:20]:
        print(f"  {json.dumps(a)[:200]}")

# ── ML health ─────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("ML HEALTH")
print("=" * 70)
ml = data.get('ml_health', {})
print(f"  {json.dumps(ml)[:500]}")

print("\n=== ANALYSIS COMPLETE ===")
