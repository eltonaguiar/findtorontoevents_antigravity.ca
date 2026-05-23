import json
from collections import defaultdict

d = json.load(open('C:/findtorontoevents_antigravity.ca/audit/data/dashboard_data.json'))
perf = d.get('performance', {})
bac = perf.get('by_asset_class', {})

print('=== ASSET CLASS PERFORMANCE (ALL TIME) ===')
for k, v in sorted(bac.items()):
    pf = v.get('profit_factor')
    pnl = v.get('pnl')
    wr = v.get('win_rate', 0)
    total = v.get('wins', 0) + v.get('losses', 0)
    is_bad = (pf is not None and pf < 1) or (pnl is not None and pnl < 0)
    flag = ' ** BAD **' if is_bad else ''
    print(f"  {k:12s} WR={wr:5.1f}% PF={str(pf):>6} PnL={pnl:>9.1f}% Wins={v.get('wins',0):4d} Losses={v.get('losses',0):4d} Active={v.get('active',0):3d}{flag}")

print()
print('=== BAD ASSET CLASSES ===')
bad = [k for k, v in bac.items() if (v.get('profit_factor') or 0) < 1 or (v.get('pnl') or 0) < 0]
print(f'Asset classes with PF<1 or negative PnL: {bad}')

print()
print('=== HOURLY 24H PERFORMANCE ===')
h24 = perf.get('hourly_24h', {})
hours = h24.get('hours', [])
sum_ac = h24.get('summary_by_asset_class', {})

print('Summary by asset class (24h):')
for k, v in sorted(sum_ac.items()):
    total = v.get('total', 0)
    wr = v.get('win_rate')
    pnl = v.get('pnl')
    new_p = v.get('new', 0)
    active = v.get('active', 0)
    is_bad = total > 0 and ((wr is not None and wr < 45) or (pnl is not None and pnl < 0))
    flag = ' ** BAD **' if is_bad else ''
    print(f"  {k:12s} new={new_p:3d} active={active:3d} total={total:4d} wins={v.get('wins',0):3d} losses={v.get('losses',0):3d} WR={str(wr):>6}% PnL={pnl:>8.1f}%{flag}")

print()
print(f'Hours with activity: {sum(1 for h in hours if h.get("total",0) > 0 or h.get("new_picks",0) > 0)}/24')
for h in hours:
    if h.get('total', 0) > 0 or h.get('new_picks', 0) > 0:
        print(f"  {h.get('hour',''):20s} new={h.get('new_picks',0):3d} closed={h.get('closed_picks',0):3d} wins={h.get('wins',0):3d} losses={h.get('losses',0):3d} WR={str(h.get('win_rate')):>6}% PnL={h.get('pnl',0):>8.1f}%")

print()
print('=== TOP SYSTEMS BY ASSET CLASS ===')
systems = d.get('systems', [])
for ac in sorted(bac.keys()):
    ac_systems = [s for s in systems if ac in (s.get('asset_classes') or []) and (s.get('closed_picks', 0) + s.get('active_picks', 0)) > 0]
    ac_systems.sort(key=lambda s: s.get('total_pnl_pct', 0), reverse=True)
    if ac_systems:
        print(f'\n  {ac}:')
        for s in ac_systems[:5]:
            print(f"    {s.get('name',''):50s} active={s.get('active_picks',0):2d} closed={s.get('closed_picks',0):4d} WR={s.get('win_rate',0):5.1f}% PF={str(s.get('profit_factor')):>5} PnL={s.get('total_pnl_pct',0):>8.1f}%")
