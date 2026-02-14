"""Run the full Pro Signal Engine pipeline: backtest -> tournament -> live scan"""
import urllib.request
import json
import time

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
BASE = 'https://findtorontoevents.ca/findcryptopairs/api/pro_signal_engine.php'

def api_call(action, params='', timeout=300):
    url = BASE + '?action=' + action
    if params:
        url += '&' + params
    req = urllib.request.Request(url, headers=HEADERS)
    resp = urllib.request.urlopen(req, timeout=timeout)
    return json.loads(resp.read())

def main():
    # Step 1: Re-run all backtests
    print('=== STEP 1: Running all 100 strategies with ATR-based TP/SL ===')
    start = time.time()
    data = api_call('run_all', 'tf=240')
    elapsed = time.time() - start
    bt_count = data.get('total_backtests', 0)
    pairs = data.get('total_pairs', 0)
    print('  Completed in %.1fs: %d backtests across %d pairs' % (elapsed, bt_count, pairs))

    # Step 2: Tournament
    print('\n=== STEP 2: Tournament elimination ===')
    data = api_call('tournament')
    rounds = data.get('rounds', [])
    for r in rounds:
        name = r.get('name', '')
        surv = r.get('survivors', r.get('total_ranked', '?'))
        elim = r.get('eliminated', '?')
        print('  Round %d: %s -> %s survived, %s eliminated' % (r['round'], name, surv, elim))

    final = data.get('final_survivors', 0)
    print('  Final survivors: %d' % final)

    top15 = data.get('top_15', [])
    print('\n=== TOP WINNERS ===')
    for i, s in enumerate(top15[:15]):
        wr = float(s['avg_wr'])
        pf = float(s['avg_pf'])
        sh = float(s['avg_sharpe'])
        ret = float(s['avg_ret'])
        dd = float(s['avg_dd'])
        sc = s['composite_score']
        print('  #%2d %-40s cat=%-12s WR=%5.1f%% PF=%6.2f Sh=%6.2f Ret=%7.2f%% DD=%5.1f%% Score=%s' % (
            i+1, s['sname'], s['scat'], wr, pf, sh, ret, dd, sc))

    # Step 3: Live scan
    print('\n=== STEP 3: Live scan with winners ===')
    data = api_call('live_scan')
    sigs = data.get('signals', [])
    print('  Pro signals found: %d' % len(sigs))
    for sig in sigs:
        pair = sig['pair']
        conf = sig['confidence']
        confl = sig['confluence']
        tp = sig['tp_pct']
        sl = sig['sl_pct']
        strats = ', '.join(sig.get('strategies', []))
        print('  >> %-15s Confidence=%d%% Confluence=%d strategies  TP=+%s%% SL=-%s%%' % (pair, conf, confl, tp, sl))
        print('     Strategies: %s' % strats)

    # Show all confluence data
    all_confl = data.get('all_confluence', {})
    active_pairs = [(p, v) for p, v in all_confl.items() if v.get('count', 0) > 0]
    active_pairs.sort(key=lambda x: x[1]['count'], reverse=True)
    print('\n=== ALL PAIR CONFLUENCE ===')
    for pair, info in active_pairs:
        ct = info['count']
        strs = ', '.join(info.get('strats', []))
        print('  %-15s %d strategies agree: %s' % (pair, ct, strs))

if __name__ == '__main__':
    main()
