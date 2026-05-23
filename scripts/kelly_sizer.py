# kelly_sizer.py - Compute Kelly fractions from live trade data via API
# Run periodically after trade closes
# Requirements: pip install requests
#
# Uses call_api('algo_stats') to get trade data, computes Kelly locally,
# then post_to_api('update_position_sizing', {...}) to write back.

import os
import sys
import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import call_api, post_to_api

def compute_kelly():
    data = call_api('algo_stats')
    if not data or not data.get('ok'):
        print('algo_stats API failed or returned no data')
        return 0

    # Expect list of {algorithm_name, asset_class, sample_size, wins, avg_win_pct, avg_loss_pct}
    results = data.get('stats', data.get('rows', []))
    if isinstance(results, dict):
        results = [results]
    if not results:
        return 0

    updated = 0
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    for row in results:
        sample = int(row.get('sample_size', row.get('sample_size', 0)))
        if sample < 5:
            continue
        wins = int(row.get('wins', 0))
        win_rate = wins / sample
        avg_win = float(row.get('avg_win_pct', 0) or 0)
        avg_loss = float(row.get('avg_loss_pct', 0.01) or 0.01)

        if avg_loss <= 0:
            avg_loss = 0.01

        odds = avg_win / avg_loss
        full_kelly = win_rate - ((1 - win_rate) / odds)
        half_kelly = full_kelly / 2
        if half_kelly < 0:
            half_kelly = 0
        if half_kelly > 0.25:
            half_kelly = 0.25

        algo = row.get('algorithm_name', row.get('algo_name', ''))
        asset = row.get('asset_class', 'stocks')

        result = post_to_api('update_position_sizing', {
            'algorithm_name': algo,
            'asset_class': asset,
            'win_rate': round(win_rate, 4),
            'avg_win_pct': round(avg_win, 4),
            'avg_loss_pct': round(avg_loss, 4),
            'full_kelly': round(full_kelly, 4),
            'half_kelly': round(half_kelly, 4),
            'sample_size': sample,
            'updated_at': now,
        })
        if result.get('ok'):
            updated += 1

    return updated

if __name__ == '__main__':
    updated = compute_kelly()
    print(f'Updated Kelly for {updated} algorithm/asset combos')
