#!/usr/bin/env python3
"""Fresh cross-validation scan — find best entries BESIDES LINK."""
import json

def load(f):
    try:
        with open(f) as fh: return json.load(fh)
    except: return {}

tv = load('tv_fresh.json')
he = load('he_fresh.json')
ec = load('ec_fresh.json')
kimi = load('kimi_fresh.json')
lm = load('lm_fresh.json')
kraken = load('kraken_fresh.json')

def norm(pair):
    p = pair.upper()
    p = p.replace('XXBT','BTC').replace('XETH','ETH').replace('XXRP','XRP').replace('XXLM','XLM')
    p = p.replace('ZUSD','USD').replace('/USD','USD').replace('_USDT','USD')
    return p

# ══════════════════════════════════════════════════════════════
#  AGGREGATE
# ══════════════════════════════════════════════════════════════
pairs = {}

def add(pair, engine, direction, conf, detail):
    p = norm(pair)
    if not p or p == 'USD': return
    if p not in pairs:
        pairs[p] = {'engines':[], 'dirs':[], 'confs':[], 'details':[]}
    pairs[p]['engines'].append(engine)
    pairs[p]['dirs'].append(direction)
    pairs[p]['confs'].append(conf)
    pairs[p]['details'].append(engine + ': ' + str(detail)[:90])

# TV Technicals patterns
for s in tv.get('signals', []):
    add(s['pair'], 'TV-Pattern', s['direction'], s['confidence'], s['pattern'])

# TV Technicals ratings
for pair, r in tv.get('ratings', {}).items():
    rating = r.get('summary_rating', 'NEUTRAL')
    score = r.get('summary_score', 0)
    if rating in ('STRONG_BUY', 'BUY'):
        add(pair, 'TV-Rating', 'LONG', score / 2 + 50, 'Summary:' + rating + ' sc:' + str(score))
    elif rating in ('STRONG_SELL', 'SELL'):
        add(pair, 'TV-Rating', 'SHORT', abs(score) / 2 + 50, 'Summary:' + rating + ' sc:' + str(score))

# Hybrid Engine
for s in he.get('active', []):
    d = s.get('direction', 'LONG')
    add(s.get('pair', ''), 'HybridEng', d, float(s.get('confidence', 50)), s.get('strategy', ''))

# Expert Consensus
for s in ec.get('signals', []):
    d = s.get('direction', 'LONG')
    add(s.get('pair', ''), 'Expert', d, float(s.get('confidence', 50)), s.get('strategy', ''))

# Kimi Enhanced
for s in kimi.get('signals', []):
    d = s.get('direction', 'LONG')
    add(s.get('pair', ''), 'Kimi', d, float(s.get('confidence', 50)), s.get('strategy', ''))

# Live Monitor
for s in lm.get('signals', []):
    d = 'SHORT' if s.get('signal_type', '') == 'SHORT' else 'LONG'
    add(s.get('symbol', ''), 'LiveMon', d, float(s.get('signal_strength', 50)), s.get('algorithm_name', ''))

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
    range_pos = ((price - low24) / (high24 - low24) * 100) if (high24 - low24) > 0 else 50
    vwap_bias = 'ABOVE' if price > vwap24 else 'BELOW'
    kraken_data[nk] = {
        'price': price, 'vol24': vol24, 'high24': high24, 'low24': low24,
        'vwap': vwap24, 'chg24': chg24, 'range_pos': range_pos, 'vwap_bias': vwap_bias
    }

# ══════════════════════════════════════════════════════════════
#  TV INDICATORS
# ══════════════════════════════════════════════════════════════
tv_ind = {}
for pair, r in tv.get('ratings', {}).items():
    np = norm(pair)
    tv_ind[np] = r.get('indicators', {})

# ══════════════════════════════════════════════════════════════
#  RANK (exclude LINK since user already has it)
# ══════════════════════════════════════════════════════════════
ranked = []
for pair, info in pairs.items():
    if 'LINK' in pair:
        continue  # Already have LINK

    eng_count = len(set(info['engines']))
    longs = sum(1 for d in info['dirs'] if d == 'LONG')
    shorts = sum(1 for d in info['dirs'] if d == 'SHORT')
    total = len(info['dirs'])

    if longs > shorts:
        dom_dir = 'LONG'
        agreement = longs / total * 100
    elif shorts > longs:
        dom_dir = 'SHORT'
        agreement = shorts / total * 100
    else:
        dom_dir = 'MIXED'
        agreement = 50

    avg_conf = sum(info['confs']) / len(info['confs']) if info['confs'] else 0

    kd = kraken_data.get(pair, {})
    ind = tv_ind.get(pair, {})
    rsi = ind.get('rsi14', 50)
    stoch = ind.get('stoch_k', 50)
    adx = ind.get('adx', 0)
    bb_width = ind.get('bb_width', 0)
    atr = ind.get('atr', 0)
    ema20 = ind.get('ema20', 0)
    ema50 = ind.get('ema50', 0)
    sma200 = ind.get('sma200', 0)
    price = kd.get('price', ind.get('price', 0))

    # Extra checks
    vwap_ok = False
    range_ok = False
    if kd:
        if dom_dir == 'LONG' and kd['vwap_bias'] == 'ABOVE': vwap_ok = True
        if dom_dir == 'SHORT' and kd['vwap_bias'] == 'BELOW': vwap_ok = True
        if dom_dir == 'LONG' and kd['range_pos'] < 85: range_ok = True
        if dom_dir == 'SHORT' and kd['range_pos'] > 15: range_ok = True

    ob = ''
    if dom_dir == 'LONG' and rsi > 75: ob = 'OVERBOUGHT RSI %.0f' % rsi
    if dom_dir == 'SHORT' and rsi < 25: ob = 'OVERSOLD RSI %.0f' % rsi

    # MA alignment check
    ma_aligned = False
    if dom_dir == 'LONG' and price > 0 and ema20 > 0 and ema50 > 0:
        if price > ema20 > ema50: ma_aligned = True
    if dom_dir == 'SHORT' and price > 0 and ema20 > 0 and ema50 > 0:
        if price < ema20 < ema50: ma_aligned = True

    composite = (
        eng_count * 15 +
        agreement * 0.3 +
        avg_conf * 0.2 +
        (10 if vwap_ok else 0) +
        (8 if range_ok else 0) +
        (adx * 0.3) +
        (10 if ma_aligned else 0) +
        (-20 if ob else 0)
    )

    # TP/SL calculation using ATR
    if atr > 0 and price > 0:
        if dom_dir == 'LONG':
            tp = price + (atr * 2.0)
            sl = price - (atr * 1.2)
        else:
            tp = price - (atr * 2.0)
            sl = price + (atr * 1.2)
        tp_pct = abs(tp - price) / price * 100
        sl_pct = abs(sl - price) / price * 100
        rr = tp_pct / sl_pct if sl_pct > 0 else 0
    else:
        tp = sl = tp_pct = sl_pct = rr = 0

    ranked.append({
        'pair': pair, 'dir': dom_dir, 'engines': eng_count, 'agreement': agreement,
        'avg_conf': avg_conf, 'composite': composite, 'rsi': rsi, 'stoch': stoch,
        'adx': adx, 'bb_width': bb_width, 'ob': ob, 'vwap_ok': vwap_ok,
        'range_ok': range_ok, 'ma_aligned': ma_aligned, 'kd': kd,
        'price': price, 'tp': tp, 'sl': sl, 'tp_pct': tp_pct, 'sl_pct': sl_pct,
        'rr': rr, 'atr': atr, 'ema20': ema20, 'ema50': ema50,
        'engine_list': sorted(set(info['engines'])), 'details': info['details']
    })

ranked.sort(key=lambda x: -x['composite'])

# ══════════════════════════════════════════════════════════════
#  DISPLAY
# ══════════════════════════════════════════════════════════════
print('=' * 72)
print('  FRESH SCAN — TOP SIGNALS (excluding LINK)')
print('  Timestamp: NOW | 7 engines queried | Kraken live prices')
print('=' * 72)

for i, r in enumerate(ranked[:15]):
    kd = r['kd']
    chg = '%+.1f%%' % kd['chg24'] if kd else '?'
    rng = '%.0f%%' % kd['range_pos'] if kd else '?'

    # Tier
    tier = 'INFO'
    if r['engines'] >= 3 and r['agreement'] >= 70 and not r['ob']:
        tier = 'ACT'
    elif r['engines'] >= 2 and r['agreement'] >= 60 and not r['ob']:
        tier = 'WATCH'
    elif r['ob']:
        tier = 'CAUT'

    checks = []
    if r['vwap_ok']: checks.append('VWAP')
    if r['range_ok']: checks.append('Range')
    if r['ma_aligned']: checks.append('MA-Stack')
    checks_str = ','.join(checks) if checks else 'none'

    print()
    print('%2d. [%5s] %-10s %-5s | Score:%.0f | %d engines, %.0f%% agree' % (
        i+1, tier, r['pair'], r['dir'], r['composite'], r['engines'], r['agreement']))

    if r['ob']:
        print('    !! %s — wait for pullback' % r['ob'])

    print('    Price: $%.4f  24h:%s  RangePos:%s' % (r['price'], chg, rng))
    print('    RSI:%.0f  Stoch:%.0f  ADX:%.0f  BB:%.1f%%  Confirms:[%s]' % (
        r['rsi'], r['stoch'], r['adx'], r['bb_width'], checks_str))

    if r['tp'] > 0:
        print('    TP: $%.4f (%+.1f%%)  SL: $%.4f (%.1f%%)  R:R = 1:%.1f' % (
            r['tp'], r['tp_pct'], r['sl'], r['sl_pct'], r['rr']))
        if r['price'] > 0:
            tp_cad = r['tp'] * 1.36
            sl_cad = r['sl'] * 1.36
            price_cad = r['price'] * 1.36
            print('    CAD: Entry ~$%.2f  TP ~$%.2f  SL ~$%.2f' % (price_cad, tp_cad, sl_cad))

    print('    EMA20:$%.4f  EMA50:$%.4f  ATR:$%.6f' % (r['ema20'], r['ema50'], r['atr']))
    print('    Engines: %s' % ' + '.join(r['engine_list']))
    for d in r['details'][:3]:
        print('      -> %s' % d[:105])

# ══════════════════════════════════════════════════════════════
#  SUMMARY TABLE
# ══════════════════════════════════════════════════════════════
print()
print('=' * 72)
print('  QUICK SUMMARY')
print('=' * 72)
print()
print('%-12s %-5s %3s %5s %5s %5s %5s %5s %8s %8s %5s' % (
    'PAIR', 'DIR', 'ENG', 'AGREE', 'RSI', 'ADX', 'VWAP', 'MA', 'TP%', 'SL%', 'R:R'))
print('-' * 72)
for r in ranked[:12]:
    if r['ob']:
        pair_str = r['pair'] + '*'
    else:
        pair_str = r['pair']
    print('%-12s %-5s %3d %4.0f%% %5.0f %5.0f %5s %5s %7.1f%% %7.1f%% %4.1f' % (
        pair_str, r['dir'], r['engines'], r['agreement'], r['rsi'], r['adx'],
        'Y' if r['vwap_ok'] else 'N',
        'Y' if r['ma_aligned'] else 'N',
        r['tp_pct'], r['sl_pct'], r['rr']))
print()
print('* = OVERBOUGHT warning — engines say buy but RSI says stretched')
print('R:R = Risk/Reward ratio (higher = better, want > 1.0)')
