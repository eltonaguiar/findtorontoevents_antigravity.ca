import json

data = json.load(open('audit_trail/data/dashboard_payload.json'))
systems = data['systems']

print('System Name'.ljust(25), 'Act Cls WR%'.ljust(10), 'PnL%'.ljust(8), 'PF'.ljust(6), 'Exp%'.ljust(6), 'Last Pick')
print('-' * 80)

for s in sorted(systems, key=lambda x: x['win_rate'], reverse=True)[:15]:
    name = s['name'][:24]
    active = s['active_picks']
    closed = s['closed_picks']
    wr = s['win_rate']
    pnl = s['total_pnl_pct']
    pf = s['profit_factor'] or 0
    exp = s['expectancy'] or 0
    last_pick = s.get('last_signal_at', '—')[:20]

    print(f'{name:25} {active:2} {closed:3} {wr:5.1f} {pnl:+6.2f} {pf:4.2f} {exp:+5.2f} {last_pick}')