#!/usr/bin/env python3
"""Cross-validate all crypto engines and rank signals."""
import json, sys

def load(f):
    try:
        with open(f) as fh:
            return json.load(fh)
    except:
        return {}

tv = load('tv_scan.json')
kimi = load('kimi_sigs.json')
expert = load('expert_sigs.json')
proven = load('proven_active.json')
hybrid_eng = load('hybrid_eng.json')
hybrid_pred = load('hybrid_pred.json')
live = load('live_sigs.json')
kraken = load('kraken_tickers.json')

# ══════════════════════════════════════════════════════════════
#  FRESHNESS CHECK
# ══════════════════════════════════════════════════════════════
print('=' * 70)
print('  DATA FRESHNESS AUDIT')
print('=' * 70)

engines_status = {
    'TV Technicals': tv.get('ok', False),
    'Kimi Enhanced': kimi.get('ok', False),
    'Expert Consensus': expert.get('ok', False),
    'Proven Picks': proven.get('ok', False),
    'Hybrid Engine': hybrid_eng.get('ok', False),
    'Hybrid Predictor': hybrid_pred.get('ok', False),
    'Live Monitor': live.get('ok', False),
    'Kraken Tickers': 'result' in kraken,
}
live_count = sum(1 for v in engines_status.values() if v)
for name, ok in engines_status.items():
    status = 'LIVE' if ok else 'DOWN'
    print(f'  {status:4s}  {name}')
print(f'\n  {live_count}/8 engines responding')

# ══════════════════════════════════════════════════════════════
#  NORMALIZE PAIR NAMES
# ══════════════════════════════════════════════════════════════
def norm(pair):
    p = pair.upper()
    p = p.replace('XXBT','BTC').replace('XETH','ETH').replace('XXRP','XRP').replace('XXLM','XLM')
    p = p.replace('ZUSD','USD').replace('/USD','USD').replace('_USDT','USD')
    return p

# ══════════════════════════════════════════════════════════════
#  AGGREGATE SIGNALS
# ══════════════════════════════════════════════════════════════
pairs = {}

def add(pair, engine, direction, conf, detail, created=''):
    p = norm(pair)
    if not p or p == 'USD':
        return
    if p not in pairs:
        pairs[p] = {'engines': [], 'dirs': [], 'confs': [], 'details': [], 'freshest': ''}
    pairs[p]['engines'].append(engine)
    pairs[p]['dirs'].append(direction)
    pairs[p]['confs'].append(conf)
    pairs[p]['details'].append(engine + ': ' + str(detail)[:100])
    if created and created > pairs[p]['freshest']:
        pairs[p]['freshest'] = created

# 1. TV Technicals signals (pattern detections)
for s in tv.get('signals', []):
    add(s['pair'], 'TV-Pattern', s['direction'], s['confidence'], s['pattern'])

# 2. TV Technicals ratings (directional bias from 25 indicators)
for pair, r in tv.get('ratings', {}).items():
    rating = r.get('summary_rating', 'NEUTRAL')
    score = r.get('summary_score', 0)
    if rating in ('STRONG_BUY', 'BUY'):
        add(pair, 'TV-Rating', 'LONG', score / 2 + 50, 'Summary: ' + rating + ' score:' + str(score))
    elif rating in ('STRONG_SELL', 'SELL'):
        add(pair, 'TV-Rating', 'SHORT', abs(score) / 2 + 50, 'Summary: ' + rating + ' score:' + str(score))

# 3. Kimi Enhanced
for s in kimi.get('signals', []):
    d = s.get('direction', 'LONG')
    add(s.get('pair', ''), 'Kimi', d, float(s.get('confidence', 50)), s.get('strategy', ''), s.get('created_at', ''))

# 4. Expert Consensus
for s in expert.get('signals', []):
    d = s.get('direction', 'LONG')
    add(s.get('pair', ''), 'Expert', d, float(s.get('confidence', 50)), s.get('strategy', ''), s.get('created_at', ''))

# 5. Proven Picks
picks_list = proven.get('picks', proven.get('active', []))
for s in picks_list:
    d = s.get('direction', 'LONG')
    conf = float(s.get('confidence', s.get('consensus_score', 50)))
    add(s.get('pair', ''), 'Proven', d, conf, 'Proven pick', s.get('created_at', ''))

# 6. Hybrid Engine
for s in hybrid_eng.get('active', []):
    d = s.get('direction', 'LONG')
    add(s.get('pair', ''), 'HybridEng', d, float(s.get('confidence', 50)), s.get('strategy', ''), s.get('created_at', ''))

# 7. Hybrid Predictor
for pair, p in hybrid_pred.get('predictions', {}).items():
    sig = p.get('hybrid_signal', 'WAIT')
    if sig in ('LONG', 'SHORT'):
        add(pair, 'HybridPred', sig, float(p.get('confidence', 0)),
            'Score:' + str(p.get('hybrid_score', 0)) + ' Regime:' + str(p.get('regime', '?')))

# 8. Live Monitor crypto signals
for s in live.get('signals', []):
    d = 'SHORT' if s.get('signal_type', '') == 'SHORT' else 'LONG'
    add(s.get('symbol', ''), 'LiveMon', d, float(s.get('signal_strength', 50)),
        s.get('algorithm_name', ''), s.get('signal_time', ''))

# ══════════════════════════════════════════════════════════════
#  KRAKEN LIVE DATA
# ══════════════════════════════════════════════════════════════
kraken_data = {}
for k, v in kraken.get('result', {}).items():
    nk = norm(k)
    price = float(v['c'][0])
    vol24 = float(v['v'][1])
    high24 = float(v['h'][1])
    low24 = float(v['l'][1])
    vwap24 = float(v['p'][1])
    open24 = float(v['o'])
    chg24 = ((price - open24) / open24 * 100) if open24 > 0 else 0
    range_pct = ((high24 - low24) / low24 * 100) if low24 > 0 else 0
    range_pos = ((price - low24) / (high24 - low24) * 100) if (high24 - low24) > 0 else 50
    vwap_bias = 'ABOVE' if price > vwap24 else 'BELOW'
    kraken_data[nk] = {
        'price': price, 'vol24': vol24, 'high24': high24, 'low24': low24,
        'vwap': vwap24, 'chg24': chg24, 'range_pct': range_pct,
        'range_pos': range_pos, 'vwap_bias': vwap_bias
    }

# ══════════════════════════════════════════════════════════════
#  CROSS-VALIDATION SCORING
# ══════════════════════════════════════════════════════════════

# Get TV technicals indicators by pair
tv_ind = {}
for pair, r in tv.get('ratings', {}).items():
    np = norm(pair)
    tv_ind[np] = r.get('indicators', {})

ranked = []
for pair, info in pairs.items():
    eng_count = len(set(info['engines']))
    longs = sum(1 for d in info['dirs'] if d == 'LONG')
    shorts = sum(1 for d in info['dirs'] if d == 'SHORT')
    total_sigs = len(info['dirs'])

    if longs > shorts:
        dominant_dir = 'LONG'
        agreement = longs / total_sigs * 100
    elif shorts > longs:
        dominant_dir = 'SHORT'
        agreement = shorts / total_sigs * 100
    else:
        dominant_dir = 'MIXED'
        agreement = 50

    avg_conf = sum(info['confs']) / len(info['confs']) if info['confs'] else 0

    # Kraken checks
    kd = kraken_data.get(pair, {})
    vwap_confirms = False
    range_confirms = False
    if kd:
        if dominant_dir == 'LONG' and kd['vwap_bias'] == 'ABOVE':
            vwap_confirms = True
        if dominant_dir == 'SHORT' and kd['vwap_bias'] == 'BELOW':
            vwap_confirms = True
        if dominant_dir == 'LONG' and kd['range_pos'] < 80:
            range_confirms = True
        if dominant_dir == 'SHORT' and kd['range_pos'] > 20:
            range_confirms = True

    # TV indicators
    ind = tv_ind.get(pair, {})
    rsi = ind.get('rsi14', 50)
    stoch = ind.get('stoch_k', 50)
    adx = ind.get('adx', 0)
    bb_width = ind.get('bb_width', 0)

    # Overbought/oversold warnings
    ob_warning = ''
    if dominant_dir == 'LONG' and rsi > 75:
        ob_warning = 'OVERBOUGHT (RSI ' + str(round(rsi, 1)) + ')'
    if dominant_dir == 'SHORT' and rsi < 25:
        ob_warning = 'OVERSOLD'

    # Composite score
    composite = (
        eng_count * 15 +
        agreement * 0.3 +
        avg_conf * 0.2 +
        (10 if vwap_confirms else 0) +
        (10 if range_confirms else 0) +
        (adx * 0.3) +
        (-20 if ob_warning else 0)
    )

    ranked.append({
        'pair': pair, 'dir': dominant_dir, 'engines': eng_count,
        'total_sigs': total_sigs, 'agreement': agreement, 'avg_conf': avg_conf,
        'composite': composite, 'details': info['details'], 'freshest': info['freshest'],
        'rsi': rsi, 'stoch': stoch, 'adx': adx, 'bb_width': bb_width,
        'vwap_confirms': vwap_confirms, 'range_confirms': range_confirms,
        'ob_warning': ob_warning, 'kd': kd,
        'engine_list': sorted(set(info['engines']))
    })

ranked.sort(key=lambda x: -x['composite'])

# ══════════════════════════════════════════════════════════════
#  DISPLAY
# ══════════════════════════════════════════════════════════════
print()
print('=' * 70)
print('  FULL CROSS-VALIDATION RANKING (ALL PAIRS)')
print('=' * 70)
print()

for i, r in enumerate(ranked[:20]):
    kd = r['kd']
    price_str = '$' + str(kd['price']) if kd else '?'
    chg_str = '%+.1f%%' % kd['chg24'] if kd else '?'
    vwap_str = 'VWAP:YES' if r['vwap_confirms'] else 'VWAP:NO'
    range_str = 'RangeOK:YES' if r['range_confirms'] else 'RangeOK:NO'
    ob_str = ' !! ' + r['ob_warning'] if r['ob_warning'] else ''

    tier = 'INFO'
    if r['engines'] >= 3 and r['agreement'] >= 70 and not r['ob_warning']:
        tier = 'ACT'
    elif r['engines'] >= 2 and r['agreement'] >= 60:
        tier = 'WATCH'

    print('%2d. [%5s] %-12s %-5s  Composite:%.0f  Engines:%d  Agree:%.0f%%  AvgConf:%.0f%%%s' % (
        i + 1, tier, r['pair'], r['dir'], r['composite'], r['engines'], r['agreement'], r['avg_conf'], ob_str))
    if kd:
        print('    Price:%-12s 24h:%s  RSI:%.0f  Stoch:%.0f  ADX:%.0f  BB:%.1f%%  %s  %s' % (
            price_str, chg_str, r['rsi'], r['stoch'], r['adx'], r['bb_width'], vwap_str, range_str))
        print('    Range Pos: %.0f%% (0=24h low, 100=24h high)  Vol24h: %s' % (
            kd['range_pos'], '{:,.0f}'.format(kd['vol24'])))
    print('    Engines: %s' % ' + '.join(r['engine_list']))
    for d in r['details'][:4]:
        print('      -> %s' % d[:110])
    if len(r['details']) > 4:
        print('      -> ... and %d more signals' % (len(r['details']) - 4))
    print()

# ══════════════════════════════════════════════════════════════
#  FINAL TIERS
# ══════════════════════════════════════════════════════════════
print('=' * 70)
print('  FINAL SIGNAL TIERS')
print('=' * 70)

act = [r for r in ranked if r['engines'] >= 3 and r['agreement'] >= 70 and not r['ob_warning']]
watch = [r for r in ranked if r not in act and r['engines'] >= 2 and r['agreement'] >= 60 and not r['ob_warning']]
caution = [r for r in ranked if r['ob_warning'] and r['engines'] >= 2]

print()
print('TIER 1 - ACT (3+ engines agree, 70%+ agreement, no overbought warning):')
if act:
    for r in act[:8]:
        kd = r['kd']
        p = '$' + str(kd['price']) if kd else '?'
        c = '%+.1f%%' % kd['chg24'] if kd else '?'
        print('  %-12s %-5s | %d engines, %.0f%% agree | RSI:%.0f ADX:%.0f | %s %s | %s' % (
            r['pair'], r['dir'], r['engines'], r['agreement'], r['rsi'], r['adx'],
            'VWAP:Y' if r['vwap_confirms'] else 'VWAP:N',
            'Range:Y' if r['range_confirms'] else 'Range:N',
            ' + '.join(r['engine_list'])))
else:
    print('  (none meet strict criteria right now)')

print()
print('TIER 2 - WATCH (2+ engines, 60%+ agreement, no overbought):')
for r in watch[:8]:
    kd = r['kd']
    print('  %-12s %-5s | %d engines, %.0f%% agree | RSI:%.0f ADX:%.0f | %s' % (
        r['pair'], r['dir'], r['engines'], r['agreement'], r['rsi'], r['adx'],
        ' + '.join(r['engine_list'])))

print()
print('TIER 3 - CAUTION (engines say GO but indicators say OVERBOUGHT):')
for r in caution[:8]:
    kd = r['kd']
    print('  %-12s %-5s | %d engines BUT %s | Wait for pullback before entry' % (
        r['pair'], r['dir'], r['engines'], r['ob_warning']))

print()
print('=' * 70)
print('  YOUR PORTFOLIO HOLDINGS - STATUS CHECK')
print('=' * 70)
holdings = ['BTCUSD', 'DOGEUSD', 'SUIUSD']
for h in holdings:
    found = [r for r in ranked if r['pair'] == h]
    if found:
        r = found[0]
        kd = r['kd']
        status = 'OVERBOUGHT - consider taking profit' if r['ob_warning'] else 'OK - hold'
        if r['dir'] == 'SHORT' and r['engines'] >= 2:
            status = 'WARNING: engines lean SHORT'
        print('  %-12s %s | %d engines, dir:%s, RSI:%.0f, Stoch:%.0f' % (
            h, status, r['engines'], r['dir'], r['rsi'], r['stoch']))
    else:
        print('  %-12s Not tracked by engines' % h)
