import pandas as pd
from scipy.stats import binomtest

def test_winrate_significance(csv_path, min_trades=30):
    df = pd.read_csv(csv_path)
    results = {}
    for algo, group in df.groupby('algorithm'):
        if len(group) < min_trades:
            results[algo] = 'Insufficient data'
            continue
        wins = group['outcome'].sum()
        p_value = binomtest(wins, len(group), 0.5).pvalue
        results[algo] = 'Significant' if p_value < 0.05 else 'Not significant'
    return results

# Usage: test_winrate_significance('trades.csv')