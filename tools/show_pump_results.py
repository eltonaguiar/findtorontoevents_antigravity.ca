import json
with open('pump_results.json') as f:
    d = json.load(f)
picks = d.get('picks', [])
print(f"Total candidates scoring 40+: {len(picks)}")
print("=" * 100)
print(f"{'#':>3} {'PAIR':<20} {'SCORE':>5}  {'GRADE':<12} {'TP%':>4} {'SL%':>4}  THESIS_SUMMARY")
print("-" * 100)
for i, p in enumerate(picks):
    thesis = p.get('thesis', '')[:80]
    print(f"{i+1:>3} {p['pair']:<20} {float(p['pump_score']):>5.0f}  {p['pump_grade']:<12} {p['tp_pct']:>4}% {p['sl_pct']:>4}%  {thesis}")
