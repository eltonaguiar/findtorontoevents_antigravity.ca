"""Quick script to run just fingerprint + scan on already-analyzed data."""
import urllib.request, json, time

BASE = 'https://findtorontoevents.ca/findcryptopairs/api/alpha_hunter.php'
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def call(action):
    url = f'{BASE}?action={action}'
    print(f'[{time.strftime("%H:%M:%S")}] Calling {action}...')
    req = urllib.request.Request(url, headers=HEADERS)
    resp = urllib.request.urlopen(req, timeout=120)
    return json.loads(resp.read().decode())

# Fingerprint
d = call('fingerprint')
if d.get('ok'):
    fp = d['fingerprint']
    print(f'\nFINGERPRINT from {fp["sample_size"]} pump events:')
    print(f'  Avg RSI: {fp["avg_pre_rsi"]}')
    print(f'  Avg BB Pos: {fp["avg_pre_bb_position"]}')
    print(f'  Avg ADX: {fp["avg_pre_adx"]}')
    print(f'  BB Squeeze: {fp["pct_in_squeeze"]}%')
    print(f'  Higher Lows: {fp["pct_higher_lows"]}%')
    print(f'  Vol Accum: {fp["pct_vol_accumulation"]}%')
    print(f'  Near Support: {fp["pct_near_support"]}%')
    print(f'  MACD Neg: {fp["pct_macd_negative"]}%')
    for i in fp.get('interpretation', []):
        print(f'  >> {i}')

# Scan
print('\n' + '='*60)
d = call('scan')
if d.get('ok'):
    print(f'Pairs scanned: {d["pairs_scanned"]}')
    print(f'MATCHES: {d["matches_found"]}')
    for s in d.get('signals', []):
        print(f'\n  {s["pair"]}  Score={s["score"]}  Price=${s["price"]:.6f}')
        print(f'    TP=${s["tp_price"]:.6f} (+{s["tp_pct"]:.1f}%)  SL=${s["sl_price"]:.6f} (-{s["sl_pct"]:.1f}%)')
        print(f'    Traits ({s["trait_count"]}):')
        for t in s['traits']:
            print(f'      - {t}')
print('\nDone!')
