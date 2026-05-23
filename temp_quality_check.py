import json, os, sys

# Load active picks JSON
with open('alpha_engine/data/active_picks.json') as f:
    data = json.load(f)

# Filter only crypto picks (category contains 'crypto' or empty) and open status
crypto_picks = [p for p in data if p.get('category') == 'crypto' or p.get('category') == '' and p.get('status') == 'OPEN']

# Compute basic stats
total = len(crypto_picks)
if total == 0:
    print('No crypto picks found')
    sys.exit()

confidences = [p.get('confidence', 0) for p in crypto_picks]
avg_conf = sum(confidences) / total

# Compute unrealized P&L percent stats
pnl = [p.get('unrealized_pnl_pct', 0) for p in crypto_picks]
avg_pnl = sum(pnl) / total
# Win rate proxy: count of positive P&L
win_rate = sum(1 for x in pnl if x > 0) / total

# Show top 5 picks by confidence
sorted_by_conf = sorted(crypto_picks, key=lambda p: p.get('confidence',0), reverse=True)[:5]

print(f'Total crypto active picks: {total}')
print(f'Average confidence: {avg_conf:.2f}')
print(f'Average unrealized P&L %: {avg_pnl:.2%}')
print(f'Proxy win rate (positive P&L): {win_rate:.2%}')
print('\nTop 5 picks by confidence:')
for p in sorted_by_conf:
    print(f"- {p.get('symbol')} {p.get('signal_type')} conf={p.get('confidence')} pnl={p.get('unrealized_pnl_pct'):.2%}")
