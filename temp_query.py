import json
with open(r'e:\findtorontoevents_antigravity.ca\audit_dashboard\data\claudes_test_state.json', 'r') as f:
    data = json.load(f)
portfolios = {}
for key, value in data.items():
    if isinstance(value, dict) and 'equity' in value:
        portfolios[key] = {
            'equity': value['equity'],
            'wins': value.get('wins', 0),
            'losses': value.get('losses', 0),
            'max_drawdown_pct': value.get('max_drawdown_pct', 0)
        }
print('Portfolio performances:')
for name, stats in portfolios.items():
    initial = 10000
    pnl_pct = (stats['equity'] - initial) / initial * 100
    win_rate = stats['wins'] / (stats['wins'] + stats['losses']) * 100 if stats['wins'] + stats['losses'] > 0 else 0
    print(f'{name}: Equity ${stats["equity"]:.2f}, PnL {pnl_pct:.2f}%, Win Rate {win_rate:.1f}%, Max DD {stats["max_drawdown_pct"]*100:.2f}%')