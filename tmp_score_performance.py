"""Analyze top-score AND low-score pick performance — does score correlate with edge?"""
import json
from collections import defaultdict

with open('e:/findtorontoevents_antigravity.ca/tmp_live7.json', encoding='utf-8') as f:
    data = json.load(f)

active = data.get('picks', {}).get('active', [])
closed = data.get('picks', {}).get('recent_closed', [])

# Score bucket closed picks to check if score predicts edge
print("=" * 90)
print("CLOSED PICK PERFORMANCE BY SCORE BUCKET")
print("=" * 90)
buckets = [
    ("0 (unscored)", 0, 0.01),
    ("1-20",        1, 21),
    ("20-40",       20, 41),
    ("40-60",       40, 61),
    ("60-70",       60, 71),
    ("70-80",       70, 81),
    ("80-90",       80, 91),
    ("90+",         90, 10000),
]

bucket_stats = {}
for name, lo, hi in buckets:
    picks = [p for p in closed if lo <= (p.get('score') or 0) < hi]
    wins = sum(1 for p in picks if float(p.get('pnl_pct') or 0) > 0)
    losses = sum(1 for p in picks if float(p.get('pnl_pct') or 0) < 0)
    total = len(picks)
    resolved = wins + losses
    if total == 0:
        continue
    total_pnl = sum(float(p.get('pnl_pct') or 0) for p in picks)
    # cap extreme outliers
    capped_pnl = sum(max(-500, min(500, float(p.get('pnl_pct') or 0))) for p in picks)
    wr = wins / resolved * 100 if resolved else 0
    avg = capped_pnl / total
    wins_sum = sum(max(0, float(p.get('pnl_pct') or 0)) for p in picks)
    losses_abs = abs(sum(min(0, float(p.get('pnl_pct') or 0)) for p in picks))
    pf = wins_sum / losses_abs if losses_abs > 0 else 999
    bucket_stats[name] = {"n": total, "wr": wr, "avg": avg, "pf": pf, "pnl": capped_pnl}

print(f"{'Score':<14}{'N':>5}{'WR%':>7}{'Avg/Trd':>10}{'PF':>7}{'Total PnL':>12}{'Verdict':>16}")
print("-" * 80)
for name, s in bucket_stats.items():
    verdict = "STRONG" if s['wr'] >= 55 and s['pf'] >= 1.3 else "OK" if s['wr'] >= 50 and s['pf'] >= 1.1 else "WEAK"
    print(f"{name:<14}{s['n']:>5}{s['wr']:>6.1f}%{s['avg']:>+9.3f}%{s['pf']:>7.2f}{s['pnl']:>+11.2f}%{verdict:>16}")

# Current active picks — top 15 + bottom 15 by score
print("\n" + "=" * 90)
print("TOP 15 CURRENT ACTIVE PICKS BY SCORE")
print("=" * 90)
active_sorted = sorted(active, key=lambda x: -(x.get('score') or 0))
print(f"{'Symbol':<15}{'Dir':<7}{'Score':<7}{'Strategy':<35}{'Src':<22}{'PnL%':>8}")
print("-" * 95)
for p in active_sorted[:15]:
    pnl = p.get('pnl_pct') or p.get('unrealized_pnl_pct') or 0
    try:
        pnl = float(pnl)
    except (TypeError, ValueError):
        pnl = 0
    print(f"{(p.get('symbol') or '?')[:13]:<15}{(p.get('direction') or '?')[:6]:<7}{(p.get('score') or 0):<7}{(p.get('strategy') or '?')[:33]:<35}{(p.get('source_system') or '?')[:20]:<22}{pnl:>+7.2f}%")

print("\n" + "=" * 90)
print("BOTTOM 15 ACTIVE PICKS BY SCORE")
print("=" * 90)
print(f"{'Symbol':<15}{'Dir':<7}{'Score':<7}{'Strategy':<35}{'Src':<22}{'PnL%':>8}")
print("-" * 95)
for p in active_sorted[-15:]:
    pnl = p.get('pnl_pct') or p.get('unrealized_pnl_pct') or 0
    try:
        pnl = float(pnl)
    except (TypeError, ValueError):
        pnl = 0
    print(f"{(p.get('symbol') or '?')[:13]:<15}{(p.get('direction') or '?')[:6]:<7}{(p.get('score') or 0):<7}{(p.get('strategy') or '?')[:33]:<35}{(p.get('source_system') or '?')[:20]:<22}{pnl:>+7.2f}%")

# Unrealized PnL of top-15 vs bottom-15
top15 = active_sorted[:15]
bot15 = active_sorted[-15:]
top_pnl = sum(float(p.get('pnl_pct') or p.get('unrealized_pnl_pct') or 0) for p in top15)
bot_pnl = sum(float(p.get('pnl_pct') or p.get('unrealized_pnl_pct') or 0) for p in bot15)
print(f"\n{'='*50}")
print(f"UNREALIZED PNL COMPARISON:")
print(f"  TOP 15 picks (score {top15[-1].get('score')}-{top15[0].get('score')}): total {top_pnl:+.2f}% / avg {top_pnl/15:+.2f}%")
print(f"  BOT 15 picks (score {bot15[0].get('score')}-{bot15[-1].get('score')}): total {bot_pnl:+.2f}% / avg {bot_pnl/15:+.2f}%")
print(f"  EDGE: {(top_pnl - bot_pnl):+.2f}%")

# Also check by source_system — which systems drive top-score picks?
print("\n" + "=" * 90)
print("TOP 15 ACTIVE PICKS — SOURCE DISTRIBUTION")
print("=" * 90)
from collections import Counter
top_sources = Counter(p.get('source_system') for p in top15)
bot_sources = Counter(p.get('source_system') for p in bot15)
print("Top 15 sources:", dict(top_sources))
print("Bot 15 sources:", dict(bot_sources))
