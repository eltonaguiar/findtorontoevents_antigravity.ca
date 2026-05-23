import csv, json, statistics, re
from collections import defaultdict, Counter

def load_csv(path):
    with open(path, 'r', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

closed = load_csv(r'C:\Users\zerou\Downloads\antigravity_closed_picks_2026-03-27 (6).csv')
active = load_csv(r'C:\Users\zerou\Downloads\antigravity_active_picks_2026-03-27 (7).csv')

def parse_float(val):
    if not val or val.strip() in ('', 'None', 'N/A', '??', '?'):
        return None
    try:
        # Strip % signs
        return float(val.replace('%','').strip())
    except:
        return None

def parse_str(val):
    if not val:
        return ''
    return val.strip()

# ========================================================================
# FOCUS: CRYPTO CLOSED PICKS ONLY (they have resolved PnL)
# ========================================================================
crypto_closed = [r for r in closed if parse_str(r.get('Asset Class','')).upper() in ('CRYPTO','CRYPTOCURRENCY','')]
# Also filter by symbol patterns
crypto_symbols = ['BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'DOGE', 'ADA', 'LINK', 'AVAX', 'DOT', 
                  'MATIC', 'FET', 'RENDER', 'NEAR', 'SUI', 'APT', 'ARB', 'OP', 'INJ', 'TIA',
                  'PEPE', 'WIF', 'BONK', 'JUP', 'AAVE', 'UNI', 'MKR', 'USDT', 'TAO', 'KAT',
                  'KITE', 'TRX', 'HBAR', 'SEI', 'STX', 'ALGO', 'FIL', 'GRT', 'ATOM']
crypto_closed = [r for r in closed if any(s in (r.get('Symbol','') or '').upper() for s in crypto_symbols) 
                 or parse_str(r.get('Asset Class','')).upper() in ('CRYPTO','CRYPTOCURRENCY')]

print(f"Total closed: {len(closed)} | Crypto closed: {len(crypto_closed)}")

# Parse PnL
for r in crypto_closed:
    r['_pnl'] = parse_float(r.get('PnL%'))
    r['_score'] = parse_float(r.get('Score'))
    r['_trust'] = parse_float(r.get('Trust Score (0-10)'))
    r['_fwd_wr'] = parse_float(r.get('Forward WR'))
    r['_fwd_trades'] = parse_float(r.get('Forward Trades'))
    r['_confluence'] = parse_float(r.get('Confluence Count'))
    r['_direction'] = parse_str(r.get('Direction','')).upper()
    r['_strategy'] = parse_str(r.get('Strategy',''))
    r['_system'] = parse_str(r.get('System',''))
    r['_grade'] = parse_str(r.get('Grade',''))
    r['_trust_tier'] = parse_str(r.get('Trust Tier',''))
    r['_exit'] = parse_str(r.get('Exit Reason',''))
    r['_symbol'] = parse_str(r.get('Symbol',''))
    r['_asset'] = parse_str(r.get('Asset Class',''))
    
    # Parse HTF from Score Breakdown
    breakdown = r.get('Score Breakdown (English)', '') or ''
    r['_breakdown'] = breakdown
    
    # Try to find HTF/regime info from Direction Reason
    dir_reason = r.get('Direction Reason', '') or ''
    r['_dir_reason'] = dir_reason
    
    # Extract regime from direction reason
    regime_match = re.search(r'(BULLISH|BEARISH|CHOPPY|TRENDING|VOLATILE|NEUTRAL)', dir_reason.upper())
    r['_regime'] = regime_match.group(1) if regime_match else ''
    
    # Systems agreement count from direction reason
    agree_match = re.search(r'(\d+)\s+(?:independent\s+)?systems?\s+(?:all\s+)?agree', dir_reason)
    r['_agree_count'] = int(agree_match.group(1)) if agree_match else 0
    
    # Check for 'viable' in strategy/reason
    all_text = (r['_strategy'] + ' ' + dir_reason + ' ' + breakdown).lower()
    r['_has_viable'] = 'viable' in all_text or 'a-viable' in all_text
    r['_has_multi_agree'] = 'multi' in all_text and 'agree' in all_text
    
    # Parse score breakdown for details
    # Look for: "Strategy: XX/100 (fwd WR=YY%"
    strat_score_match = re.search(r'Strategy:\s*(\d+)/100\s*\(fwd WR=([\d.]+)%', breakdown)
    r['_strat_subscore'] = float(strat_score_match.group(1)) if strat_score_match else None
    r['_strat_fwd_wr_from_breakdown'] = float(strat_score_match.group(2)) if strat_score_match else None
    
    # Signal subscore
    signal_match = re.search(r'Signal:\s*(\d+)/100\s*\(confidence=(\d+)%,\s*R:R=([\d.]+)', breakdown)
    r['_signal_subscore'] = float(signal_match.group(1)) if signal_match else None
    r['_confidence_from_bd'] = float(signal_match.group(2)) if signal_match else None
    r['_rr_from_bd'] = float(signal_match.group(3)) if signal_match else None
    
    # Freshness subscore
    fresh_match = re.search(r'Freshness:\s*(\d+)/100', breakdown)
    r['_freshness'] = float(fresh_match.group(1)) if fresh_match else None
    
    # Track record from breakdown
    track_match = re.search(r'Track:\s*(\d+)/100', breakdown)
    r['_track_subscore'] = float(track_match.group(1)) if track_match else None
    
    # Consensus from breakdown
    consensus_match = re.search(r'Consensus(?:\s*mult)?:\s*(\d+)%', breakdown)
    r['_consensus_mult'] = float(consensus_match.group(1)) if consensus_match else None

# Only picks with resolved PnL
resolved = [r for r in crypto_closed if r['_pnl'] is not None]
winners = [r for r in resolved if r['_pnl'] > 0]
losers = [r for r in resolved if r['_pnl'] < 0]

print(f"Resolved PnL: {len(resolved)} | Winners: {len(winners)} | Losers: {len(losers)}")
if resolved:
    pnls = [r['_pnl'] for r in resolved]
    print(f"Overall: Avg PnL={statistics.mean(pnls):+.3f}%, WR={len(winners)/len(resolved)*100:.1f}%, Med={statistics.median(pnls):+.3f}%")

# ========================================================================
# CORRELATION ANALYSIS  
# ========================================================================
def corr(xs, ys):
    n = len(xs)
    if n < 5: return (0, n)
    mx, my = statistics.mean(xs), statistics.mean(ys)
    sx = statistics.stdev(xs) if n > 1 else 1
    sy = statistics.stdev(ys) if n > 1 else 1
    if sx < 0.0001 or sy < 0.0001: return (0, n)
    return (sum((x-mx)*(y-my) for x,y in zip(xs,ys)) / ((n-1)*sx*sy), n)

print("\n" + "="*80)
print("PEARSON CORRELATIONS TO PnL%")
print("="*80)

metrics = [
    ('Score', '_score'),
    ('Trust Score', '_trust'),
    ('Forward WR', '_fwd_wr'),
    ('Forward Trades', '_fwd_trades'),
    ('Confluence Count', '_confluence'),
    ('Agreement Count', '_agree_count'),
    ('Strategy Subscore', '_strat_subscore'),
    ('Signal Subscore', '_signal_subscore'),
    ('Confidence', '_confidence_from_bd'),
    ('R:R Ratio', '_rr_from_bd'),
    ('Freshness', '_freshness'),
    ('Track Subscore', '_track_subscore'),
    ('Consensus Mult', '_consensus_mult'),
    ('Strat FWD WR (breakdown)', '_strat_fwd_wr_from_breakdown'),
]

all_corrs = []
for label, field in metrics:
    pairs = [(r[field], r['_pnl']) for r in resolved if r[field] is not None and r['_pnl'] is not None]
    if len(pairs) >= 5:
        xs, ys = zip(*pairs)
        c, n = corr(list(xs), list(ys))
        strength = "🟢 STRONG" if abs(c) > 0.15 else "🟡 MODERATE" if abs(c) > 0.08 else "⚪ WEAK"
        all_corrs.append((label, c, n, strength))

all_corrs.sort(key=lambda x: abs(x[1]), reverse=True)
print(f"\n{'Metric':35s} | {'Corr':>8s} | {'N':>6s} | Strength")
print("-" * 75)
for label, c, n, strength in all_corrs:
    print(f"  {label:33s} | {c:+8.4f} | {n:6d} | {strength}")

# ========================================================================
# SCORE BUCKETS
# ========================================================================
print("\n" + "="*80)
print("SCORE BUCKETS vs PnL%")
print("="*80)

buckets = defaultdict(list)
for r in resolved:
    s = r['_score']
    if s is None: 
        buckets['no_score'].append(r['_pnl'])
        continue
    if s < 30: bucket = "0-29"
    elif s < 40: bucket = "30-39"
    elif s < 50: bucket = "40-49"
    elif s < 60: bucket = "50-59"
    elif s < 70: bucket = "60-69"
    elif s < 80: bucket = "70-79"
    elif s < 90: bucket = "80-89"
    else: bucket = "90-100"
    buckets[bucket].append(r['_pnl'])

print(f"\n{'Score':12s} | {'N':>5s} | {'Avg PnL%':>9s} | {'WR':>7s} | {'Med PnL%':>9s} | {'Avg Win':>9s} | {'Avg Loss':>9s}")
print("-" * 80)
for b in sorted(buckets.keys()):
    pnls = buckets[b]
    if not pnls: continue
    avg = statistics.mean(pnls)
    w = sum(1 for p in pnls if p > 0)
    wr = w/len(pnls)*100
    med = statistics.median(pnls)
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    avg_win = statistics.mean(wins) if wins else 0
    avg_loss = statistics.mean(losses) if losses else 0
    print(f"  {b:10s} | {len(pnls):5d} | {avg:+9.3f} | {wr:6.1f}% | {med:+9.3f} | {avg_win:+9.3f} | {avg_loss:+9.3f}")

# ========================================================================
# FORWARD WR BUCKETS  
# ========================================================================
print("\n" + "="*80)
print("FORWARD WR (Track%) BUCKETS vs PnL%")
print("="*80)

buckets = defaultdict(list)
for r in resolved:
    fw = r['_fwd_wr']
    if fw is None:
        buckets['no_track'].append(r['_pnl'])
        continue
    if fw < 30: bucket = "0-29%"
    elif fw < 40: bucket = "30-39%"
    elif fw < 50: bucket = "40-49%"
    elif fw < 55: bucket = "50-54%"
    elif fw < 60: bucket = "55-59%"
    elif fw < 65: bucket = "60-64%"
    elif fw < 70: bucket = "65-69%"
    elif fw < 80: bucket = "70-79%"
    else: bucket = "80-100%"
    buckets[bucket].append(r['_pnl'])

print(f"\n{'Track WR%':12s} | {'N':>5s} | {'Avg PnL%':>9s} | {'WR':>7s} | {'Med PnL%':>9s}")
print("-" * 60)
for b in sorted(buckets.keys()):
    pnls = buckets[b]
    if not pnls: continue
    avg = statistics.mean(pnls)
    w = sum(1 for p in pnls if p > 0)
    wr = w/len(pnls)*100
    med = statistics.median(pnls)
    print(f"  {b:10s} | {len(pnls):5d} | {avg:+9.3f} | {wr:6.1f}% | {med:+9.3f}")

# ========================================================================
# HTF / REGIME MATCHING
# ========================================================================
print("\n" + "="*80)
print("REGIME AT ENTRY vs PnL%")
print("="*80)

regime_results = defaultdict(list)
for r in resolved:
    regime = r['_regime']
    if regime:
        regime_results[regime].append(r['_pnl'])

for reg in sorted(regime_results.keys()):
    pnls = regime_results[reg]
    if len(pnls) >= 3:
        avg = statistics.mean(pnls)
        wr = sum(1 for p in pnls if p > 0)/len(pnls)*100
        print(f"  {reg:15s}: {len(pnls):4d} picks | Avg: {avg:+8.3f} | WR: {wr:5.1f}%")

# ========================================================================
# AGREEMENT COUNT
# ========================================================================
print("\n" + "="*80)
print("SYSTEM AGREEMENT COUNT vs PnL%")
print("="*80)

agree_results = defaultdict(list)
for r in resolved:
    ac = r['_agree_count']
    agree_results[ac].append(r['_pnl'])

print(f"\n{'Agree':8s} | {'N':>5s} | {'Avg PnL%':>9s} | {'WR':>7s} | {'Med PnL%':>9s}")
print("-" * 50)
for ac in sorted(agree_results.keys()):
    pnls = agree_results[ac]
    if len(pnls) < 3: continue
    avg = statistics.mean(pnls)
    wr = sum(1 for p in pnls if p > 0)/len(pnls)*100
    med = statistics.median(pnls)
    print(f"  {ac:6d} | {len(pnls):5d} | {avg:+9.3f} | {wr:6.1f}% | {med:+9.3f}")

# ========================================================================
# GRADE
# ========================================================================
print("\n" + "="*80)
print("GRADE vs PnL%")
print("="*80)

grade_results = defaultdict(list)
for r in resolved:
    g = r['_grade']
    if g:
        grade_results[g].append(r['_pnl'])

for g in sorted(grade_results.keys()):
    pnls = grade_results[g]
    if len(pnls) >= 3:
        avg = statistics.mean(pnls)
        wr = sum(1 for p in pnls if p > 0)/len(pnls)*100
        print(f"  Grade {g:3s}: {len(pnls):4d} picks | Avg: {avg:+8.3f} | WR: {wr:5.1f}% | Med: {statistics.median(pnls):+8.3f}")

# ========================================================================
# TRUST TIER
# ========================================================================
print("\n" + "="*80)
print("TRUST TIER vs PnL%")
print("="*80)

tier_results = defaultdict(list)
for r in resolved:
    t = r['_trust_tier']
    if t:
        tier_results[t].append(r['_pnl'])

for t in sorted(tier_results.keys()):
    pnls = tier_results[t]
    if len(pnls) >= 3:
        avg = statistics.mean(pnls)
        wr = sum(1 for p in pnls if p > 0)/len(pnls)*100
        print(f"  {t:20s}: {len(pnls):4d} picks | Avg: {avg:+8.3f} | WR: {wr:5.1f}% | Med: {statistics.median(pnls):+8.3f}")

# ========================================================================
# STRATEGY DEEP DIVE (A-viable and multi-agree)
# ========================================================================
print("\n" + "="*80)
print("STRATEGY TAGS: A-viable and multi-agree")
print("="*80)

viable_picks = [r for r in resolved if r['_has_viable']]
multi_agree_picks = [r for r in resolved if r['_has_multi_agree']]

if viable_picks:
    pnls = [r['_pnl'] for r in viable_picks]
    wr = sum(1 for p in pnls if p > 0)/len(pnls)*100
    print(f"\n  A-viable tagged: {len(viable_picks)} picks | Avg: {statistics.mean(pnls):+.3f} | WR: {wr:.1f}%")
else:
    print("\n  A-viable: NOT FOUND in closed picks")

if multi_agree_picks:
    pnls = [r['_pnl'] for r in multi_agree_picks]
    wr = sum(1 for p in pnls if p > 0)/len(pnls)*100
    print(f"  Multi-agree tagged: {len(multi_agree_picks)} picks | Avg: {statistics.mean(pnls):+.3f} | WR: {wr:.1f}%")
else:
    print("  Multi-agree: NOT FOUND in closed picks")

# Also check strategies containing these
viable_strats = [r for r in resolved if 'viable' in r['_strategy'].lower()]
print(f"\n  Strategies with 'viable' in name: {len(viable_strats)}")
multi_strats = [r for r in resolved if 'multi' in r['_strategy'].lower()]
print(f"  Strategies with 'multi' in name: {len(multi_strats)}")

# ========================================================================
# SOURCE SYSTEM RANKING
# ========================================================================
print("\n" + "="*80)
print("SOURCE SYSTEM RANKING (by Avg PnL)")
print("="*80)

sys_results = defaultdict(list)
for r in resolved:
    s = r['_system']
    if s:
        sys_results[s].append(r['_pnl'])

print(f"\n{'System':45s} | {'N':>5s} | {'Avg PnL%':>9s} | {'WR':>7s} | {'Med':>8s}")
print("-" * 85)
for s in sorted(sys_results.keys(), key=lambda x: statistics.mean(sys_results[x]), reverse=True):
    pnls = sys_results[s]
    if len(pnls) < 3: continue
    avg = statistics.mean(pnls)
    wr = sum(1 for p in pnls if p > 0)/len(pnls)*100
    med = statistics.median(pnls)
    print(f"  {s:43s} | {len(pnls):5d} | {avg:+9.3f} | {wr:6.1f}% | {med:+8.3f}")

# ========================================================================
# STRATEGY RANKING  
# ========================================================================
print("\n" + "="*80)
print("TOP 30 STRATEGIES (by Win Rate, min 5 picks)")
print("="*80)

strat_results = defaultdict(list)
for r in resolved:
    s = r['_strategy']
    if s:
        strat_results[s].append(r['_pnl'])

strat_ranked = []
for s, pnls in strat_results.items():
    if len(pnls) < 5: continue
    avg = statistics.mean(pnls)
    wr = sum(1 for p in pnls if p > 0)/len(pnls)*100
    med = statistics.median(pnls)
    strat_ranked.append((s, len(pnls), avg, wr, med))

strat_ranked.sort(key=lambda x: x[3], reverse=True)
print(f"\n{'Strategy':50s} | {'N':>5s} | {'Avg PnL%':>9s} | {'WR':>7s} | {'Med':>8s}")
print("-" * 90)
for s, n, avg, wr, med in strat_ranked[:30]:
    print(f"  {s:48s} | {n:5d} | {avg:+9.3f} | {wr:6.1f}% | {med:+8.3f}")

# ========================================================================
# GOLDEN CRITERIA COMBINATIONS
# ========================================================================
print("\n" + "="*80)
print("🏆 GOLDEN CRITERIA COMBINATIONS")
print("="*80)

combos = []

# Baseline
bl_pnls = [r['_pnl'] for r in resolved]
bl_wr = sum(1 for p in bl_pnls if p > 0)/len(bl_pnls)*100
combos.append(("**BASELINE**", len(bl_pnls), statistics.mean(bl_pnls), bl_wr, statistics.median(bl_pnls)))

# Combo definitions
def eval_combo(name, picks):
    pnls = [r['_pnl'] for r in picks]
    if not pnls: return
    wr = sum(1 for p in pnls if p > 0)/len(pnls)*100
    combos.append((name, len(pnls), statistics.mean(pnls), wr, statistics.median(pnls)))

# 1. Score >= 70
eval_combo("Score ≥ 70", [r for r in resolved if (r['_score'] or 0) >= 70])

# 2. Score >= 80
eval_combo("Score ≥ 80", [r for r in resolved if (r['_score'] or 0) >= 80])

# 3. Track WR >= 60%
eval_combo("Track WR ≥ 60%", [r for r in resolved if (r['_fwd_wr'] or 0) >= 60])

# 4. Track WR >= 70%
eval_combo("Track WR ≥ 70%", [r for r in resolved if (r['_fwd_wr'] or 0) >= 70])

# 5. Agreement >= 5
eval_combo("Agreement ≥ 5", [r for r in resolved if r['_agree_count'] >= 5])

# 6. Agreement >= 10
eval_combo("Agreement ≥ 10", [r for r in resolved if r['_agree_count'] >= 10])

# 7. Grade A only
eval_combo("Grade A", [r for r in resolved if r['_grade'] == 'A'])

# 8. Trust >= 7
eval_combo("Trust Score ≥ 7", [r for r in resolved if (r['_trust'] or 0) >= 7])

# 9. Confidence >= 80%
eval_combo("Confidence ≥ 80%", [r for r in resolved if (r['_confidence_from_bd'] or 0) >= 80])

# 10. R:R >= 2.0
eval_combo("R:R ≥ 2.0", [r for r in resolved if (r['_rr_from_bd'] or 0) >= 2.0])

# 11. Track subscore >= 50
eval_combo("Track Subscore ≥ 50", [r for r in resolved if (r['_track_subscore'] or 0) >= 50])

# 12. Strat FWD WR >= 65%
eval_combo("Strat FWD WR ≥ 65%", [r for r in resolved if (r['_strat_fwd_wr_from_breakdown'] or 0) >= 65])

# COMBOS
# 13. Score >= 70 + Track WR >= 60
eval_combo("Score≥70 + TrackWR≥60", [r for r in resolved if (r['_score'] or 0) >= 70 and (r['_fwd_wr'] or 0) >= 60])

# 14. Score >= 60 + Agreement >= 5
eval_combo("Score≥60 + Agree≥5", [r for r in resolved if (r['_score'] or 0) >= 60 and r['_agree_count'] >= 5])

# 15. Track WR >= 60 + Agreement >= 5
eval_combo("TrackWR≥60 + Agree≥5", [r for r in resolved if (r['_fwd_wr'] or 0) >= 60 and r['_agree_count'] >= 5])

# 16. Score >= 65 + Track WR >= 60 + Agree >= 3
eval_combo("Score≥65 + WR≥60 + Agree≥3", [r for r in resolved if (r['_score'] or 0) >= 65 and (r['_fwd_wr'] or 0) >= 60 and r['_agree_count'] >= 3])

# 17. Grade A + Track WR >= 60
eval_combo("Grade A + TrackWR≥60", [r for r in resolved if r['_grade'] == 'A' and (r['_fwd_wr'] or 0) >= 60])

# 18. Trust >= 6 + Score >= 60 + Track >= 55
eval_combo("Trust≥6 + Score≥60 + Track≥55", [r for r in resolved if (r['_trust'] or 0) >= 6 and (r['_score'] or 0) >= 60 and (r['_fwd_wr'] or 0) >= 55])

# 19. Confidence >= 75 + R:R >= 1.5 + Track >= 55
eval_combo("Conf≥75 + RR≥1.5 + Track≥55", [r for r in resolved if (r['_confidence_from_bd'] or 0) >= 75 and (r['_rr_from_bd'] or 0) >= 1.5 and (r['_fwd_wr'] or 0) >= 55])

# 20. CHOPPY regime excluded (non-choppy)
eval_combo("Non-CHOPPY regime", [r for r in resolved if r['_regime'] and r['_regime'] != 'CHOPPY'])

# 21. Track >= 65 + Strat FWD WR >= 60
eval_combo("Track≥65 + StratWR≥60", [r for r in resolved if (r['_fwd_wr'] or 0) >= 65 and (r['_strat_fwd_wr_from_breakdown'] or 0) >= 60])

# 22. GOLDEN: Score≥65 + TrackWR≥60 + Agree≥3 + Trust≥5
eval_combo("GOLDEN: S65+T60+A3+Tr5", [r for r in resolved if (r['_score'] or 0) >= 65 and (r['_fwd_wr'] or 0) >= 60 and r['_agree_count'] >= 3 and (r['_trust'] or 0) >= 5])

# 23. PLATINUM: All high
eval_combo("PLATINUM: S70+T65+A5+Tr6+Conf75", [r for r in resolved if (r['_score'] or 0) >= 70 and (r['_fwd_wr'] or 0) >= 65 and r['_agree_count'] >= 5 and (r['_trust'] or 0) >= 6 and (r['_confidence_from_bd'] or 0) >= 75])

print(f"\n{'Criteria':45s} | {'N':>5s} | {'Avg PnL%':>9s} | {'WR':>7s} | {'Med PnL%':>9s}")
print("-" * 85)
for name, n, avg, wr, med in combos:
    emoji = "🏆" if wr > bl_wr + 10 and n >= 10 else "✨" if wr > bl_wr + 5 else "  "
    print(f"{emoji}{name:43s} | {n:5d} | {avg:+9.3f} | {wr:6.1f}% | {med:+9.3f}")

# ========================================================================
# WINNER PATTERNS
# ========================================================================
print("\n" + "="*80)
print("TOP 25 WINNERS - COMMON PATTERNS")
print("="*80)

top_w = sorted(winners, key=lambda r: r['_pnl'], reverse=True)[:25]
print(f"\n{'#':>3s} {'Symbol':12s} {'PnL%':>8s} {'Dir':5s} {'Score':>6s} {'Grade':6s} {'TrackWR':>8s} {'Trust':>6s} {'Agree':>6s} {'Strategy':40s}")
print("-" * 110)
for i, r in enumerate(top_w, 1):
    print(f"{i:3d} {r['_symbol']:12s} {r['_pnl']:+8.2f} {r['_direction']:5s} {str(r['_score'] or '??'):>6s} {r['_grade']:6s} {str(r['_fwd_wr'] or '??'):>8s} {str(r['_trust'] or '??'):>6s} {str(r['_agree_count']):>6s} {r['_strategy'][:40]:40s}")

# Common traits of top winners
print("\nCommon traits of top 25 winners:")
w_scores = [r['_score'] for r in top_w if r['_score']]
w_tracks = [r['_fwd_wr'] for r in top_w if r['_fwd_wr']]
w_agrees = [r['_agree_count'] for r in top_w]
w_grades = Counter(r['_grade'] for r in top_w if r['_grade'])
w_dirs = Counter(r['_direction'] for r in top_w)
w_systems = Counter(r['_system'] for r in top_w)
w_strats = Counter(r['_strategy'] for r in top_w)
w_tiers = Counter(r['_trust_tier'] for r in top_w)
w_regimes = Counter(r['_regime'] for r in top_w if r['_regime'])

if w_scores: print(f"  Avg Score: {statistics.mean(w_scores):.1f} (Med: {statistics.median(w_scores):.1f})")
if w_tracks: print(f"  Avg Track WR: {statistics.mean(w_tracks):.1f}% (Med: {statistics.median(w_tracks):.1f}%)")
print(f"  Avg Agreement: {statistics.mean(w_agrees):.1f}")
print(f"  Grades: {dict(w_grades)}")
print(f"  Directions: {dict(w_dirs)}")
print(f"  Top Systems: {w_systems.most_common(5)}")
print(f"  Top Strats: {w_strats.most_common(5)}")
print(f"  Trust Tiers: {dict(w_tiers)}")
print(f"  Regimes: {dict(w_regimes)}")

# ========================================================================
# LOSER PATTERNS (what to AVOID)
# ========================================================================
print("\n" + "="*80)
print("TOP 25 LOSERS - COMMON PATTERNS (what to AVOID)")
print("="*80)

top_l = sorted(losers, key=lambda r: r['_pnl'])[:25]
print(f"\n{'#':>3s} {'Symbol':12s} {'PnL%':>8s} {'Dir':5s} {'Score':>6s} {'Grade':6s} {'TrackWR':>8s} {'Trust':>6s} {'Agree':>6s} {'Strategy':40s}")
print("-" * 110)
for i, r in enumerate(top_l, 1):
    print(f"{i:3d} {r['_symbol']:12s} {r['_pnl']:+8.2f} {r['_direction']:5s} {str(r['_score'] or '??'):>6s} {r['_grade']:6s} {str(r['_fwd_wr'] or '??'):>8s} {str(r['_trust'] or '??'):>6s} {str(r['_agree_count']):>6s} {r['_strategy'][:40]:40s}")

# Common traits of top losers
l_scores = [r['_score'] for r in top_l if r['_score']]
l_tracks = [r['_fwd_wr'] for r in top_l if r['_fwd_wr']]
l_agrees = [r['_agree_count'] for r in top_l]
l_grades = Counter(r['_grade'] for r in top_l if r['_grade'])
l_systems = Counter(r['_system'] for r in top_l)
l_strats = Counter(r['_strategy'] for r in top_l)
l_tiers = Counter(r['_trust_tier'] for r in top_l)

print("\nCommon traits of top 25 losers:")
if l_scores: print(f"  Avg Score: {statistics.mean(l_scores):.1f} (Med: {statistics.median(l_scores):.1f})")
if l_tracks: print(f"  Avg Track WR: {statistics.mean(l_tracks):.1f}% (Med: {statistics.median(l_tracks):.1f}%)")
print(f"  Avg Agreement: {statistics.mean(l_agrees):.1f}")
print(f"  Grades: {dict(l_grades)}")
print(f"  Top Systems: {l_systems.most_common(5)}")
print(f"  Top Strats: {l_strats.most_common(5)}")
print(f"  Trust Tiers: {dict(l_tiers)}")

# ========================================================================
# MISSING METADATA  
# ========================================================================
print("\n" + "="*80)
print("METADATA GAPS")
print("="*80)

fields_to_check = {
    'Score': '_score',
    'Forward WR': '_fwd_wr',
    'Trust Score': '_trust',
    'Confidence': '_confidence_from_bd',
    'R:R': '_rr_from_bd',
    'Track Subscore': '_track_subscore',
    'Strat FWD WR': '_strat_fwd_wr_from_breakdown',
    'Regime': '_regime',
}

for label, field in fields_to_check.items():
    missing = sum(1 for r in resolved if r[field] is None or r[field] == '' or r[field] == 0)
    pct = missing/len(resolved)*100
    flag = "⚠️ " if pct > 30 else "  "
    print(f"{flag}{label:25s}: {missing:4d}/{len(resolved)} missing ({pct:.1f}%)")
