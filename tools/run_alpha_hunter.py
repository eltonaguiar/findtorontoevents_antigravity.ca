"""
Run the Alpha Hunter pipeline:
1. Analyze past pumps (reverse-engineer what happened before each pump)
2. Extract fingerprint (common pre-pump pattern)
3. Scan all pairs for the fingerprint NOW
"""
import urllib.request
import json
import time

BASE = 'https://findtorontoevents.ca/findcryptopairs/api/alpha_hunter.php'
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def call(action):
    url = f'{BASE}?action={action}'
    print(f'\n[{time.strftime("%H:%M:%S")}] Calling {action}...')
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        resp = urllib.request.urlopen(req, timeout=120)
        data = json.loads(resp.read().decode())
        if data.get('ok'):
            elapsed = data.get('elapsed_ms', '?')
            print(f'  OK ({elapsed}ms)')
            return data
        else:
            print(f'  ERROR: {data.get("error", "Unknown")}')
            return data
    except Exception as e:
        print(f'  EXCEPTION: {e}')
        return None

print('=' * 60)
print('ALPHA HUNTER — Reverse-Engineer Past Winners Pipeline')
print('=' * 60)

# Step 1: Analyze pump events
d = call('analyze_pumps')
if d:
    print(f'  Pump events analyzed: {d.get("pump_events_analyzed", 0)}')
    if d.get('top_pumps'):
        print(f'  Top pumps:')
        for p in d['top_pumps'][:10]:
            print(f'    {p["pair"]}: +{p["pump_pct"]}%  RSI={p.get("pre_rsi","?")} BB={p.get("pre_bb_position","?")} ADX={p.get("pre_adx","?")}')

# Step 2: Extract fingerprint
d = call('fingerprint')
if d and d.get('fingerprint'):
    fp = d['fingerprint']
    print(f'\n  === THE PRE-PUMP FINGERPRINT (from {fp["sample_size"]} pump events) ===')
    print(f'  Avg RSI before pump: {fp["avg_pre_rsi"]}')
    print(f'  Avg BB position: {fp["avg_pre_bb_position"]}')
    print(f'  Avg ADX: {fp["avg_pre_adx"]}')
    print(f'  Avg Stochastic: {fp["avg_pre_stoch"]}')
    print(f'  Avg MFI: {fp["avg_pre_mfi"]}')
    print(f'  BB Squeeze present: {fp["pct_in_squeeze"]}%')
    print(f'  Higher Lows (accumulation): {fp["pct_higher_lows"]}%')
    print(f'  Volume Accumulation: {fp["pct_vol_accumulation"]}%')
    print(f'  Near Support: {fp["pct_near_support"]}%')
    print(f'  MACD Negative before pump: {fp["pct_macd_negative"]}%')
    if fp.get('interpretation'):
        print(f'\n  Key Insights:')
        for i in fp['interpretation']:
            print(f'    - {i}')

# Step 3: Scan for matches NOW
d = call('scan')
if d:
    print(f'\n  Pairs scanned: {d.get("pairs_scanned", 0)}')
    print(f'  MATCHES FOUND: {d.get("matches_found", 0)}')
    if d.get('signals'):
        print(f'\n  === ALPHA SIGNALS ===')
        for s in d['signals']:
            print(f'\n  {s["pair"]}  Score: {s["score"]}  Price: ${s["price"]:.6f}')
            print(f'    TP: ${s["tp_price"]:.6f} (+{s["tp_pct"]:.1f}%)  SL: ${s["sl_price"]:.6f} (-{s["sl_pct"]:.1f}%)')
            print(f'    Traits ({s["trait_count"]}):')
            for t in s['traits']:
                print(f'      * {t}')
    else:
        print('  No matches — try lowering thresholds or run with more pairs')

print('\n' + '=' * 60)
print('Pipeline complete!')
print('=' * 60)
