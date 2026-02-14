"""Check Alpha Hunter status — signals, monitor, fingerprint"""
import urllib.request, json, time

BASE = 'https://findtorontoevents.ca/findcryptopairs/api/alpha_hunter.php'
HDR = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def call(action):
    url = f'{BASE}?action={action}'
    req = urllib.request.Request(url, headers=HDR)
    return json.loads(urllib.request.urlopen(req, timeout=60).read().decode())

print('=' * 65)
print('  ALPHA HUNTER STATUS CHECK  -', time.strftime('%Y-%m-%d %H:%M:%S'))
print('=' * 65)

# 1. Monitor first (updates prices)
try:
    m = call('monitor')
    print(f'\nMonitor: checked={m.get("checked",0)} resolved={m.get("resolved",0)}')
    if m.get('message'):
        print(f'  {m["message"]}')
except Exception as e:
    print(f'Monitor error: {e}')

# 2. Get signals
try:
    d = call('signals')
    active = d.get('active', [])
    hist = d.get('history', [])
    wins = sum(1 for h in hist if float(h.get('pnl_pct', 0)) > 0)
    losses = len(hist) - wins
    wr = (wins / len(hist) * 100) if hist else 0

    print(f'\n--- SIGNAL SUMMARY ---')
    print(f'Active signals: {len(active)}')
    print(f'Resolved: {len(hist)} ({wins}W / {losses}L = {wr:.1f}% WR)')

    if active:
        print(f'\n--- ACTIVE SIGNALS ---')
        for a in active:
            pair = a['pair']
            score = a['fingerprint_score']
            entry = float(a['price'])
            cur = float(a.get('current_price', 0))
            pnl = float(a.get('pnl_pct', 0))
            tp = float(a.get('tp_pct', 0))
            sl = float(a.get('sl_pct', 0))
            created = a.get('created_at', '?')
            pnl_s = f'{pnl:+.2f}%' if cur > 0 else '--'
            cur_s = f'${cur:.6f}' if cur > 0 else 'not yet'
            print(f'  {pair:14s} Score={score:>4s}  Entry=${entry:.6f}  Now={cur_s}  PnL={pnl_s}  TP=+{tp:.1f}% SL=-{sl:.1f}%  ({created})')

    if hist:
        print(f'\n--- RESOLVED SIGNALS (recent) ---')
        for h in hist[:15]:
            pair = h['pair']
            pnl = float(h.get('pnl_pct', 0))
            reason = h.get('exit_reason', '--')
            score = h.get('fingerprint_score', '?')
            icon = 'WIN' if pnl > 0 else 'LOSS'
            print(f'  {icon:4s} {pair:14s} Score={score:>4s}  PnL={pnl:+.2f}%  Exit={reason}')

except Exception as e:
    print(f'Signals error: {e}')

# 3. Quick re-scan to find new matches
print(f'\n--- RUNNING QUICK SCAN ---')
try:
    s = call('scan')
    print(f'Pairs scanned: {s.get("pairs_scanned", 0)}')
    print(f'New matches: {s.get("matches_found", 0)}')
    for sig in s.get('signals', []):
        pair = sig['pair']
        score = sig['score']
        price = sig['price']
        traits = sig['trait_count']
        tp = sig['tp_pct']
        sl = sig['sl_pct']
        print(f'  {pair:14s} Score={score:3d}  ${price:.6f}  TP=+{tp:.1f}% SL=-{sl:.1f}%  ({traits} traits)')
        for t in sig.get('traits', []):
            print(f'    - {t}')
except Exception as e:
    print(f'Scan error: {e}')

# 4. Fingerprint summary
try:
    f = call('fingerprint')
    fp = f.get('fingerprint', {})
    print(f'\n--- FINGERPRINT ({fp.get("sample_size",0)} pump events) ---')
    print(f'  Avg RSI: {fp.get("avg_pre_rsi")}  |  BB Pos: {fp.get("avg_pre_bb_position")}  |  ADX: {fp.get("avg_pre_adx")}')
    print(f'  Squeeze: {fp.get("pct_in_squeeze")}%  |  Higher Lows: {fp.get("pct_higher_lows")}%  |  Near Support: {fp.get("pct_near_support")}%')
except Exception as e:
    print(f'Fingerprint error: {e}')

print(f'\n' + '=' * 65)
print('Done.')
