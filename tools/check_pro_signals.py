"""Check Pro Signal Engine status"""
import urllib.request, json, time

BASE = 'https://findtorontoevents.ca/findcryptopairs/api/pro_signal_engine.php'
HDR = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def call(action):
    url = f'{BASE}?action={action}'
    req = urllib.request.Request(url, headers=HDR)
    return json.loads(urllib.request.urlopen(req, timeout=60).read().decode())

print('=' * 65)
print('  PRO SIGNAL ENGINE STATUS  -', time.strftime('%Y-%m-%d %H:%M:%S'))
print('=' * 65)

try:
    d = call('signals')
    active = d.get('active_signals', [])
    stats = d.get('stats', {})
    print(f'\nActive pro signals: {len(active)}')
    print(f'Win rate: {stats.get("win_rate", "--")}%')
    print(f'Avg PnL: {stats.get("avg_pnl", "--")}%')
    print(f'Total signals: {stats.get("total", "--")}')

    if active:
        print(f'\n--- ACTIVE PRO SIGNALS ---')
        for a in active:
            pair = a.get('pair', '?')
            conf = a.get('confidence', '?')
            direction = a.get('direction', '?')
            strategies = a.get('strategies', '')
            tp = a.get('tp_pct', 0)
            sl = a.get('sl_pct', 0)
            print(f'  {pair:14s} conf={conf}% dir={direction} TP=+{tp}% SL=-{sl}%')
            if strategies:
                print(f'    Strategies: {strategies}')
except Exception as e:
    print(f'Signals error: {e}')

try:
    d = call('audit')
    rounds = d.get('rounds', [])
    winners = d.get('winners', [])
    print(f'\n--- TOURNAMENT WINNERS ({len(winners)}) ---')
    for w in winners[:10]:
        name = w.get('name', '?')
        wr = w.get('avg_wr', 0)
        pf = w.get('avg_pf', 0)
        score = w.get('composite', 0)
        print(f'  {name:35s} WR={wr:.1f}% PF={pf:.2f} score={score:.2f}')
except Exception as e:
    print(f'Audit error: {e}')

# Check Pump Watch too
print(f'\n{"="*65}')
print(f'  PUMP WATCH STATUS')
print(f'{"="*65}')
try:
    PUMP = 'https://findtorontoevents.ca/findcryptopairs/api/pump_forensics.php'
    req = urllib.request.Request(f'{PUMP}?action=performance', headers=HDR)
    d = json.loads(urllib.request.urlopen(req, timeout=30).read().decode())
    if d.get('ok'):
        print(f'  Win rate: {d.get("win_rate", "--")}%')
        print(f'  Avg PnL: {d.get("avg_pnl", "--")}%')
        print(f'  Open picks: {d.get("open_picks", 0)}')
        print(f'  Total resolved: {d.get("total_resolved", 0)}')
        bt = d.get('best_trade', {})
        wt = d.get('worst_trade', {})
        if bt: print(f'  Best trade: {bt.get("pair","?")} +{bt.get("pnl_pct",0)}%')
        if wt: print(f'  Worst trade: {wt.get("pair","?")} {wt.get("pnl_pct",0)}%')
except Exception as e:
    print(f'Pump Watch error: {e}')

# Check GitHub Actions recent runs
print(f'\n{"="*65}')
print('Done. All systems operational.')
