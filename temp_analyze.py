import json

try:
    with open('audit_dashboard/data/claudes_test_state.json') as f:
        state = json.load(f)

    trades = []
    # state is a dict of {portfolio_id: portfolio_data}
    for pid, port in state.items():
        if 'closed' in port:
            for t in port['closed']:
                t['portfolio'] = port.get('name', pid)
                trades.append(t)

    trades.sort(key=lambda x: x.get('pnl_pct', 0), reverse=True)

    print('--- TOP 10 TRADES ---')
    for t in trades[:10]:
        print(f"{t.get('symbol')}: {t.get('pnl_pct', 0):.2f}% ({t.get('portfolio')}) - Strategy: {t.get('strategy', 'N/A')}")

    print('\n--- WORST 10 TRADES ---')
    for t in trades[-10:]:
        print(f"{t.get('symbol')}: {t.get('pnl_pct', 0):.2f}% ({t.get('portfolio')}) - Strategy: {t.get('strategy', 'N/A')}")

    def get_date(x):
        return x.get('exit_time') or x.get('exit_date') or ''
    
    trades_by_date = sorted(trades, key=get_date, reverse=True)
    
    print('\n--- MOST RECENT 10 TRADES ---')
    for t in trades_by_date[:10]:
        print(f"{t.get('symbol')}: {get_date(t)} | {t.get('pnl_pct', 0):.2f}% ({t.get('portfolio')}) - Str: {t.get('strategy', 'N/A')}")

    print('\n--- SYSTEM PERFORMANCE ---')
    sys_stats = {}
    for t in trades:
        port = t.get('portfolio')
        if port not in sys_stats:
            sys_stats[port] = {'win': 0, 'loss': 0, 'pnl': 0.0}
        
        pnl = t.get('pnl_pct', 0)
        sys_stats[port]['pnl'] += pnl
        if pnl > 0:
            sys_stats[port]['win'] += 1
        elif pnl < 0:
            sys_stats[port]['loss'] += 1
            
    for port, stats in sys_stats.items():
        total = stats['win'] + stats['loss']
        if total > 0:
            wr = stats['win'] / total * 100
            avg = stats['pnl'] / total
            print(f"{port}: {total} trades | WR: {wr:.1f}% | Avg PnL: {avg:.2f}%")

except Exception as e:
    print(f"Error: {e}")
