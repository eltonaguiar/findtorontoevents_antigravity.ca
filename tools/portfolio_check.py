"""Cross-reference user's portfolio against all engine signals."""
import urllib.request, json

HDR = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def fetch(url):
    req = urllib.request.Request(url, headers=HDR)
    return json.loads(urllib.request.urlopen(req, timeout=60).read().decode())

# User's portfolio from screenshot
portfolio = [
    {'coin': 'BTC',     'pair': 'XXBTZUSD',    'qty': 0.0002383, 'avg_buy': 95578.44, 'value': 22.31},
    {'coin': 'PENGU',   'pair': 'PENGUUSD',    'qty': 1615.71,   'avg_buy': 0.01,     'value': 14.86},
    {'coin': 'DOGE',    'pair': 'XDGUSD',      'qty': 108.97,    'avg_buy': 0.1364,   'value': 14.35},
    {'coin': 'SUI',     'pair': 'SUIUSD',      'qty': 7.685,     'avg_buy': 1.29,     'value': 10.06},
    {'coin': 'DOG',     'pair': 'DOGUSD',      'qty': 7418.8,    'avg_buy': 0.01,     'value': 9.83},
    {'coin': 'POPCAT',  'pair': 'POPCATUSD',   'qty': 136.145,   'avg_buy': 0.07273,  'value': 9.53},
    {'coin': 'VIRTUAL', 'pair': 'VIRTUALUSD',  'qty': 5.7547,    'avg_buy': 0.8603,   'value': 4.83},
    {'coin': 'AZTEC',   'pair': 'AZTECUSD',    'qty': 124.69,    'avg_buy': 0.03972,  'value': 4.04},
    {'coin': 'LRC',     'pair': 'LRCUSD',      'qty': 61.74577,  'avg_buy': 0.04811,  'value': 2.89},
    {'coin': 'ZEC',     'pair': 'XZECZUSD',    'qty': 0.00503,   'avg_buy': 393.90,   'value': 1.93},
]

print('=' * 75)
print('  PORTFOLIO vs ENGINE SIGNALS CROSS-REFERENCE')
print('=' * 75)
print(f'  Total portfolio: $96.56 | Unrealized: -$2.48')
print()

# 1. Alpha Hunter signals
print('--- ALPHA HUNTER signals matching your portfolio ---')
try:
    d = fetch('https://findtorontoevents.ca/findcryptopairs/api/alpha_hunter.php?action=signals')
    ah_active = {s['pair']: s for s in d.get('active', [])}
    for p in portfolio:
        pair = p['pair']
        if pair in ah_active:
            s = ah_active[pair]
            print(f'  MATCH: {p["coin"]:8s} Score={s["fingerprint_score"]}  PnL={float(s.get("pnl_pct",0)):+.2f}%  TP=+{s["tp_pct"]}%  SL=-{s["sl_pct"]}%')
        # Also check alternate naming
        for k, s in ah_active.items():
            if p['coin'].upper() in k.upper() and pair != k:
                print(f'  MATCH: {p["coin"]:8s} (as {k}) Score={s["fingerprint_score"]}  PnL={float(s.get("pnl_pct",0)):+.2f}%')
except Exception as e:
    print(f'  Error: {e}')

# 2. Pro Signal Engine
print('\n--- PRO SIGNAL ENGINE signals matching your portfolio ---')
try:
    d = fetch('https://findtorontoevents.ca/findcryptopairs/api/pro_signal_engine.php?action=signals')
    ps_active = {s['pair']: s for s in d.get('active_signals', [])}
    for p in portfolio:
        pair = p['pair']
        if pair in ps_active:
            s = ps_active[pair]
            print(f'  MATCH: {p["coin"]:8s} conf={s.get("confidence","?")}%  dir={s.get("direction","?")}  TP=+{s.get("tp_pct","?")}%  SL=-{s.get("sl_pct","?")}%')
        for k, s in ps_active.items():
            if p['coin'].upper() in k.upper() and pair != k:
                print(f'  MATCH: {p["coin"]:8s} (as {k}) conf={s.get("confidence","?")}%  dir={s.get("direction","?")}')
except Exception as e:
    print(f'  Error: {e}')

# 3. Pump Watch
print('\n--- PUMP WATCH signals matching your portfolio ---')
try:
    d = fetch('https://findtorontoevents.ca/findcryptopairs/api/pump_forensics.php?action=watchlist&min_score=30')
    if d.get('ok') and d.get('picks'):
        pw_picks = {p['pair']: p for p in d['picks']}
        for p in portfolio:
            pair = p['pair']
            if pair in pw_picks:
                s = pw_picks[pair]
                score = float(s.get('pump_score', 0))
                pnl = float(s.get('pnl_pct', 0))
                tier = s.get('tier', '?')
                print(f'  MATCH: {p["coin"]:8s} pump_score={score:.0f}  tier={tier}  PnL={pnl:+.1f}%')
            for k, s in pw_picks.items():
                if p['coin'].upper() in k.upper() and pair != k:
                    score = float(s.get('pump_score', 0))
                    tier = s.get('tier', '?')
                    print(f'  MATCH: {p["coin"]:8s} (as {k}) pump_score={score:.0f}  tier={tier}')
except Exception as e:
    print(f'  Error: {e}')

# 4. Fresh Kraken ticker for current prices
print('\n--- LIVE PRICES from Kraken ---')
try:
    pairs_str = ','.join([p['pair'] for p in portfolio])
    d = fetch(f'https://api.kraken.com/0/public/Ticker?pair={pairs_str}')
    result = d.get('result', {})
    for p in portfolio:
        for k, v in result.items():
            if p['coin'].upper() in k.upper() or p['pair'] in k:
                cur = float(v['c'][0])
                h24 = float(v['h'][1])
                l24 = float(v['l'][1])
                chg = ((cur - float(v['o'][0])) / float(v['o'][0])) * 100 if float(v['o'][0]) > 0 else 0
                ur = (cur - p['avg_buy']) / p['avg_buy'] * 100
                print(f'  {p["coin"]:8s}  Now=${cur:<12.6f}  24h: {chg:+.2f}%  UR: {ur:+.2f}%  24hRange: ${l24:.6f}-${h24:.6f}')
                break
except Exception as e:
    print(f'  Error: {e}')

# 5. Summary recommendation based on engine data
print('\n' + '=' * 75)
print('  SIGNAL SUMMARY PER COIN')
print('=' * 75)
for p in portfolio:
    coin = p['coin']
    signals = []
    pair = p['pair']

    # Check Alpha Hunter
    if pair in ah_active:
        s = ah_active[pair]
        signals.append(f'AlphaHunter(score={s["fingerprint_score"]},PnL={float(s.get("pnl_pct",0)):+.1f}%)')
    for k in ah_active:
        if coin.upper() in k.upper() and pair != k:
            s = ah_active[k]
            signals.append(f'AlphaHunter(score={s["fingerprint_score"]},PnL={float(s.get("pnl_pct",0)):+.1f}%)')

    # Check Pro Signal
    if pair in ps_active:
        s = ps_active[pair]
        signals.append(f'ProSignal(conf={s.get("confidence","?")}%,{s.get("direction","?")})')
    for k in ps_active:
        if coin.upper() in k.upper() and pair != k:
            s = ps_active[k]
            signals.append(f'ProSignal(conf={s.get("confidence","?")}%,{s.get("direction","?")})')

    engine_count = len(signals)
    verdict = 'NO ENGINE SIGNAL'
    if engine_count >= 2:
        verdict = 'STRONG HOLD -- multiple engines agree'
    elif engine_count == 1:
        verdict = 'HOLD -- engine signal active'
    else:
        verdict = 'NO SIGNAL -- watch closely'

    ur_pct = (1 - p['avg_buy'] / p['avg_buy']) if p['avg_buy'] > 0 else 0  # placeholder
    print(f'\n  {coin:8s} (${p["value"]:.2f})')
    if signals:
        for s in signals:
            print(f'    + {s}')
    print(f'    >> {verdict}')

print('\n' + '=' * 75)
print('Done.')
