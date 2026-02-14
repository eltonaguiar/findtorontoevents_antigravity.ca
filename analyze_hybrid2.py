import json, sys

fname = sys.argv[1] if len(sys.argv) > 1 else 'btc_hybrid2.json'
d = json.load(open(fname))
r = d.get('research', {})
m = r.get('hybrid_model', {})

print('=== %s HYBRID v2 RESULTS ===' % r.get('asset', '?'))
print('Sharpe:       %s' % m.get('sharpe_ratio'))
print('Sortino:      %s' % m.get('sortino_ratio'))
print('Adj Sharpe:   %s' % m.get('sharpe_adj'))
print('Win Rate 30d: %s' % m.get('win_rate_30d'))
print('Total Return: %s' % m.get('total_return'))
print('Adj Return:   %s' % m.get('total_return_adj'))
print('Max DD:       %s' % m.get('max_drawdown'))
print('Calmar:       %s' % m.get('calmar_ratio'))
print('Signals:      %s' % m.get('total_signals'))
print('TP/SL:        %s' % m.get('tp_sl_record'))
print('vs BH:        %s' % r.get('vs_buy_hold'))
print()

print('=== REGIME BREAKDOWN ===')
for rd in r.get('regime_breakdown', []):
    print('  %s: bars=%s, fires=%s, avg=%s%%, WR=%s%%, sharpe=%s' % (
        rd['regime'], rd['bars_in_regime'], rd['signals_fired'],
        rd['avg_ret_30d'], rd['win_rate'], rd['sharpe']))

print()
print('=== PERIOD BREAKDOWN ===')
for pd in r.get('period_breakdown', []):
    print('  %s: fires=%s, avg=%s%%, adj_avg=%s%%, WR=%s%%, sharpe=%s, sortino=%s' % (
        pd['period'], pd['fires'], pd['avg_ret_30d'], pd.get('avg_adj_ret_30d', '?'),
        pd['win_rate'], pd['sharpe'], pd.get('sortino', '?')))

print()
print('=== SIGNAL PERFORMANCE ===')
for sp in r.get('signal_performance', []):
    if sp['fires'] > 0:
        print('  %s: fires=%s, WR_7d=%s%%' % (sp['signal'], sp['fires'], sp['win_rate_7d']))

print()
print('=== REGIME DISTRIBUTION ===')
print(r.get('regime_distribution'))

print()
print('=== FIRST 10 SIGNALS ===')
for sl in r.get('signal_log', [])[:10]:
    print('  %s: $%s, score=%s, conf=%s, regime=%s, active=%s, pos=%s' % (
        sl['d'], sl['p'], sl['score'], sl['confidence'], sl['regime'],
        sl['active'], sl.get('position_size', '?')))
    print('    sigs: %s' % ', '.join(sl.get('signals', [])))
