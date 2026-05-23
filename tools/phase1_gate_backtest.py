"""Backtest the Phase 1 gates (confidence>=0.80 and TOD-block 08-11 UTC)
against the full closed-picks ledger. Shows how much loss is removed vs
how much profit is sacrificed."""
import json, sys, io, os, math
from datetime import datetime
from collections import defaultdict
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
os.chdir(r'e:/findtorontoevents_antigravity.ca')

CONF_THRESH = 0.80
TOD_BLOCK = {8, 9, 10, 11}

rows = []
for path, label in [
    ('alpha_engine/data/closed_picks.json', 'main'),
    ('alpha_engine/data/closed_picks_fast.json', 'fast'),
]:
    with open(path, encoding='utf-8') as f:
        for e in json.load(f):
            if not isinstance(e, dict): continue
            pnl = e.get('pnl_pct')
            if pnl is None: continue
            try: pnl = float(pnl)
            except: continue
            ts = e.get('closed_at') or e.get('exit_time') or e.get('exit_date') or e.get('entry_time')
            et = e.get('entry_time') or e.get('opened_at') or ts
            if not ts or not et: continue
            try:
                dt = datetime.fromisoformat(str(ts).replace('Z','+00:00').split('+')[0])
                edt = datetime.fromisoformat(str(et).replace('Z','+00:00').split('+')[0])
            except: continue
            sym = (e.get('symbol') or '').upper()
            ac = (e.get('asset_class') or '').upper()
            if not ac:
                if sym.startswith(('XAU','XAG','WTI','BRENT','GC','SI')): ac = 'COMMODITY'
                elif any(sym.endswith(q) for q in ('USDT','USDC','BUSD','DAI')) or sym in ('BTC','ETH'): ac = 'CRYPTO'
                elif len(sym)==6 and sym[:3] in ('EUR','GBP','USD','JPY','AUD','CAD','NZD','CHF'): ac = 'FOREX'
                elif sym.isalpha() and 1<=len(sym)<=5: ac = 'EQUITY'
                else: ac = 'OTHER'
            try: conf = float(e.get('confidence')) if e.get('confidence') is not None else None
            except: conf = None
            rows.append({'dt': dt, 'edt': edt, 'pnl': pnl, 'asset': ac, 'sym': sym, 'conf': conf})

seen = set(); dedup = []
for r in sorted(rows, key=lambda x: x['dt']):
    k = (r['sym'], r['dt'].isoformat())
    if k in seen: continue
    seen.add(k); dedup.append(r)
rows = dedup

def metrics(rs):
    if not rs: return None
    wins = [r['pnl'] for r in rs if r['pnl']>0]; losses = [r['pnl'] for r in rs if r['pnl']<=0]
    n = len(rs); wr = len(wins)/n*100
    gw = sum(wins); gl = abs(sum(losses))
    pf = gw/gl if gl>0 else (float('inf') if gw>0 else 0)
    total = sum(r['pnl'] for r in rs)
    avg_w = sum(wins)/len(wins) if wins else 0
    avg_l = sum(losses)/len(losses) if losses else 0
    exp = (wr/100)*avg_w + (1-wr/100)*avg_l
    return dict(n=n, wr=wr, pf=pf, total=total, exp=exp, avg_w=avg_w, avg_l=avg_l)

def pf_str(x):
    return 'inf' if x==float('inf') else f'{x:.2f}'

def show(label, rs):
    x = metrics(rs)
    if not x: return
    print(f'  {label:<45} n={x["n"]:<5} WR={x["wr"]:.1f}%  PF={pf_str(x["pf"]):<5}  '
          f'expect={x["exp"]:+.3f}%/trade  total={x["total"]:+.2f}%')

# 1. Confidence gate (crypto-only, like the code)
def conf_pass(r):
    if r['asset'] == 'CRYPTO' and r['conf'] is not None:
        return r['conf'] >= CONF_THRESH
    return True

def tod_pass(r):
    if r['asset'] == 'CRYPTO':
        return r['edt'].hour not in TOD_BLOCK
    return True

print('='*100)
print('BASELINE: all 4,762 closed picks, no Phase 1 gates')
print('='*100)
show('overall', rows)
for ac in sorted({r['asset'] for r in rows}, key=lambda a: -sum(1 for r in rows if r['asset']==a)):
    show(f'  {ac}', [r for r in rows if r['asset']==ac])

print('\n' + '='*100)
print('GATE 1 ONLY: confidence>=0.80 (crypto only)')
print('='*100)
kept = [r for r in rows if conf_pass(r)]
rej = [r for r in rows if not conf_pass(r)]
show('kept', kept)
show('rejected', rej)
# Crypto-only impact
c_kept = [r for r in kept if r['asset']=='CRYPTO']
c_rej = [r for r in rows if r['asset']=='CRYPTO' and not conf_pass(r)]
print('\n  CRYPTO-only slice:')
show('    crypto kept', c_kept)
show('    crypto rejected (saved from taking)', c_rej)

print('\n' + '='*100)
print('GATE 2 ONLY: TOD block 08-11 UTC entry (crypto only)')
print('='*100)
kept = [r for r in rows if tod_pass(r)]
rej = [r for r in rows if not tod_pass(r)]
show('kept', kept)
show('rejected', rej)

print('\n' + '='*100)
print('BOTH GATES: conf>=0.80 AND entry_hour NOT in {8,9,10,11} UTC (crypto only)')
print('='*100)
kept = [r for r in rows if conf_pass(r) and tod_pass(r)]
rej = [r for r in rows if not (conf_pass(r) and tod_pass(r))]
show('kept', kept)
show('rejected (not taken)', rej)
print('\n  Per asset class after both gates:')
for ac in sorted({r['asset'] for r in kept}, key=lambda a: -sum(1 for r in kept if r['asset']==a)):
    show(f'    {ac}', [r for r in kept if r['asset']==ac])

# Headline delta
base = metrics(rows); final = metrics(kept)
print('\n' + '='*100)
print('HEADLINE DELTA')
print('='*100)
print(f'  Picks:        {base["n"]:<6} → {final["n"]:<6}  ({(final["n"]-base["n"]):+d}, {(final["n"]-base["n"])/base["n"]*100:+.1f}%)')
print(f'  WR:           {base["wr"]:.1f}% → {final["wr"]:.1f}%  ({final["wr"]-base["wr"]:+.1f} pp)')
print(f'  PF:           {pf_str(base["pf"])} → {pf_str(final["pf"])}')
print(f'  Expectancy:   {base["exp"]:+.3f}% → {final["exp"]:+.3f}%/trade  ({final["exp"]-base["exp"]:+.3f} pp)')
print(f'  Total P/L:    {base["total"]:+.2f}% → {final["total"]:+.2f}%  ({final["total"]-base["total"]:+.2f} pp saved)')
