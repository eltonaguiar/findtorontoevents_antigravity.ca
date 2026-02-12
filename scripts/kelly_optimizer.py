import pandas as pd
import numpy as np

def optimize_kelly(csv_path, regime='bull'):
    df = pd.read_csv(csv_path)
    df = df[df['regime'] == regime]
    win_rate = df['outcome'].mean()
    avg_win = df[df['outcome'] == 1]['return'].mean()
    avg_loss = abs(df[df['outcome'] == 0]['return'].mean())
    kelly = (win_rate * (avg_win / avg_loss) - (1 - win_rate)) / (avg_win / avg_loss)
    return max(0, kelly * 0.5)  # Half-Kelly

# Usage: optimize_kelly('trades.csv', 'bull')