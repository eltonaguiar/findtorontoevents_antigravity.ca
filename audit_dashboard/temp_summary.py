import json

with open('data/claudes_test_dashboard.json', 'r') as f:
    data = json.load(f)

lines = []
lines.append("=== PORTFOLIO PERFORMANCE ===")
for port in data.get('portfolios', []):
    name = port['name']
    wr = port['stats']['win_rate']
    pnl = port['stats']['pnl_pct']
    trades = port['stats']['total_trades']
    lines.append(f"{name} | {trades} trades | WR: {wr}% | PnL: {pnl}%")

with open('temp_summary_out.txt', 'w') as f:
    f.write('\\n'.join(lines))
