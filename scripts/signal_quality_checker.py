import pandas as pd

def check_signal_quality(csv_path):
    df = pd.read_csv(csv_path)
    df['gap'] = (pd.to_datetime(df['execution_time']) - pd.to_datetime(df['signal_time'])).dt.total_seconds() / 3600
    quality = df.groupby('algorithm')['gap'].mean()
    quality = quality.apply(lambda x: 'A' if x < 1 else 'F' if x > 24 else 'C')
    return quality

# Usage: check_signal_quality('signals.csv')