import json, sys

d = json.load(open('btc_hybrid.json'))
r = d.get('research', {})

print('=== REGIME BREAKDOWN ===')
for rd in r.get('regime_breakdown', []):
    print('  %s: bars=%s, fires=%s, avg_ret=%s%%, WR=%s%%, sharpe=%s' % (
        rd['regime'], rd['bars_in_regime'], rd['signals_fired'],
        rd['avg_ret_30d'], rd['win_rate'], rd['sharpe']))

print()
print('=== PERIOD BREAKDOWN ===')
for pd in r.get('period_breakdown', []):
    print('  %s: fires=%s, avg_ret=%s%%, WR=%s%%, sharpe=%s' % (
        pd['period'], pd['fires'], pd['avg_ret_30d'], pd['win_rate'], pd['sharpe']))

print()
print('=== SIGNAL PERFORMANCE ===')
for sp in r.get('signal_performance', []):
    print('  %s: fires=%s, WR_7d=%s%%' % (sp['signal'], sp['fires'], sp['win_rate_7d']))

print()
print('=== SIGNAL LOG (first 15) ===')
for sl in r.get('signal_log', [])[:15]:
    print('  %s: price=%s, score=%s, conf=%s, regime=%s, active=%s, pos=%s, tp=%s, sl=%s' % (
        sl['d'], sl['p'], sl['score'], sl['confidence'], sl['regime'],
        sl['active'], sl.get('position_size', '?'),
        sl.get('tp_pct', '?'), sl.get('sl_pct', '?')))
    print('    signals: %s' % ', '.join(sl.get('signals', [])))

print()
print('=== REGIME DISTRIBUTION ===')
print(r.get('regime_distribution'))

print()
m = r.get('hybrid_model', {})
print('=== EQUITY CURVE (sample) ===')
eq = r.get('equity_curve', [])
print(eq[:20])
