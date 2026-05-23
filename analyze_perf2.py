import json
from collections import defaultdict

d = json.load(open('C:/findtorontoevents_antigravity.ca/audit/data/dashboard_data.json'))

print('=== DATA FRESHNESS ===')
print(f"Generated at: {d.get('generated_at', 'N/A')}")
print(f"Summary total_closed_picks: {d.get('summary', {}).get('total_closed_picks', 'N/A')}")
print(f"Summary total_active_picks: {d.get('summary', {}).get('total_active_picks', 'N/A')}")

print()
print('=== CLOSED PICK TIMESTAMPS ===')
recent_closed = d.get('picks', {}).get('recent_closed', [])
print(f"Recent closed picks count: {len(recent_closed)}")

closed_at_times = defaultdict(int)
created_times = defaultdict(int)
for p in recent_closed:
    ca = p.get('closed_at', 'none')
    if ca:
        h = ca[:13]  # YYYY-MM-DDTHH
        closed_at_times[h] += 1
    ts = p.get('timestamp', 'none')
    if ts:
        h = ts[:13]
        created_times[h] += 1

print(f"\nClosed picks by hour (closed_at, top 10):")
for k in sorted(closed_at_times.keys(), reverse=True)[:10]:
    print(f"  {k}:00Z  {closed_at_times[k]}")

print(f"\nClosed picks by hour (timestamp, top 10):")
for k in sorted(created_times.keys(), reverse=True)[:10]:
    print(f"  {k}:00Z  {created_times[k]}")

print()
print('=== ACTIVE PICK TIMESTAMPS ===')
active = d.get('picks', {}).get('active', [])
print(f"Active picks count: {len(active)}")
created_times_a = defaultdict(int)
for p in active:
    ts = p.get('created_at') or p.get('timestamp', 'none')
    if ts:
        h = ts[:13]
        created_times_a[h] += 1

print(f"\nActive picks by hour (created_at, top 10):")
for k in sorted(created_times_a.keys(), reverse=True)[:10]:
    print(f"  {k}:00Z  {created_times_a[k]}")

print()
print('=== SYSTEM-LEVEL DEEP DIVE (BAD ASSET CLASSES) ===')
systems = d.get('systems', [])

bad_acs = ['CRYPTO', 'EQUITY', 'FOREX', 'ETF', 'FUTURES']
for ac in bad_acs:
    ac_systems = [s for s in systems if ac in (s.get('asset_classes') or [])]
    if not ac_systems:
        continue
    print(f"\n  {ac}:")
    # Show ALL systems, sorted by total_pnl
    ac_systems.sort(key=lambda s: s.get('total_pnl_pct', 0))
    for s in ac_systems:
        name = s.get('name', '')
        ap = s.get('active_picks', 0)
        cp = s.get('closed_picks', 0)
        wr = s.get('win_rate', 0)
        pf = s.get('profit_factor')
        pnl = s.get('total_pnl_pct', 0)
        avg = s.get('avg_pnl_pct', 0)
        wins = s.get('wins', 0)
        losses = s.get('losses', 0)
        status = s.get('status', '')
        print(f"    {name:50s} status={status:12s} active={ap:3d} closed={cp:4d} WR={wr:5.1f}% PF={str(pf):>6} PnL={pnl:>9.1f}% avg={avg:>6.2f}% wins={wins:4d} losses={losses:4d}")

print()
print('=== ROOT CAUSE: STRATEGY-LEVEL PERFORMANCE ===')
print("Looking for the worst-performing strategies across all asset classes...")

all_strats = []
for s in systems:
    cp = s.get('closed_picks', 0)
    if cp < 5:
        continue
    wr = s.get('win_rate', 0)
    pf = s.get('profit_factor')
    pnl = s.get('total_pnl_pct', 0)
    acs = s.get('asset_classes', [])
    status = s.get('status', '')
    # Flag if: WR<40% with PF<0.8, OR huge negative PnL
    is_bad = (wr < 40 and pf is not None and pf < 0.8) or (pnl < -50 and cp > 10)
    if is_bad:
        all_strats.append((pnl, wr, pf, cp, name, acs, status))

all_strats.sort()
print(f"\nWorst strategies (WR<40% + PF<0.8 OR PnL<-50% with 10+ trades):")
for pnl, wr, pf, cp, name, acs, status in all_strats[:20]:
    print(f"  {name:50s} {str(acs):20s} WR={wr:5.1f}% PF={str(pf):>6} PnL={pnl:>9.1f}% n={cp}")

print()
print('=== PNL CONCENTRATION ANALYSIS ===')
perf = d.get('performance', {})
bac = perf.get('by_asset_class', {})
for ac, v in sorted(bac.items()):
    if v.get('losses', 0) == 0:
        continue
    win_pnl_est = v.get('avg_win', 0) * v.get('wins', 0)
    loss_pnl_est = v.get('avg_loss', 0) * v.get('losses', 0)
    total_trades = v.get('wins', 0) + v.get('losses', 0)
    print(f"  {ac:12s} wins={v.get('wins',0):4d} (avg_win={v.get('avg_win',0):.2f}%) losses={v.get('losses',0):4d} (avg_loss={v.get('avg_loss',0):.2f}%) total_pnl={v.get('pnl',0):.2f}%")
