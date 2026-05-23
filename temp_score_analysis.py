import json, statistics

with open('alpha_engine/data/active_picks.json') as f:
    picks = json.load(f)

# Filter crypto picks open
crypto = [p for p in picks if (p.get('category') == 'crypto' or p.get('category') == '') and p.get('status') == 'OPEN']

# Compute composite score as average of confidence and ml_score
for p in crypto:
    conf = p.get('confidence', 0)
    ml = p.get('ml_score', 0)
    p['composite'] = (conf + ml) / 2 if (conf is not None and ml is not None) else None

# Compare composite vs confidence
higher = sum(1 for p in crypto if p['composite'] > p.get('confidence',0))
lower = sum(1 for p in crypto if p['composite'] < p.get('confidence',0))

total = len(crypto)
print(f'Total crypto picks: {total}')
print(f'Composite > confidence: {higher} ({higher/total:.2%})')
print(f'Composite < confidence: {lower} ({lower/total:.2%})')
# Show some examples where difference is large
sorted_diff = sorted(crypto, key=lambda p: abs(p['composite'] - p.get('confidence',0)), reverse=True)[:5]
print('\nTop 5 picks with biggest confidence vs composite diff:')
for p in sorted_diff:
    print(f"- {p['symbol']} conf={p.get('confidence'):.2f} ml={p.get('ml_score'):.2f} comp={p['composite']:.2f}")
