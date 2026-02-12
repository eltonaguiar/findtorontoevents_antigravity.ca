import pandas as pd
import json

def archive_signals(signals_df, output='signals_archive.csv'):
    signals_df.to_csv(output, index=False)
    signals_df.to_json(output.replace('.csv', '.json'), orient='records')

# Usage: archive_signals(pd.DataFrame([...]))