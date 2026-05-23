import json

try:
    with open('e:/findtorontoevents_antigravity.ca/audit_dashboard/data/claudes_test_dashboard.json') as f:
        d = json.load(f)
    print("Top Portfolios:")
    for r in d['ranking']:
        print(f"{r['rank']}. {r['name']}: PnL {r['pnl_pct']}% | WR {r['win_rate']}% | Sharpe {r['sharpe']} | Trades {r['trades']}")
except Exception as e:
    print(f"Error: {e}")
