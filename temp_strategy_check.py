import sqlite3
import pandas as pd

conn = sqlite3.connect('E:/findtorontoevents_antigravity.ca/data/live_picks.db')
query = """
SELECT symbol, direction, entry_price, take_profit, stop_loss, strategy, confidence, score
FROM live_picks
WHERE status = 'ACTIVE'
"""
df = pd.read_sql_query(query, conn)
conn.close()

print(df[df['strategy'].str.contains('justin|connor|battleground|confluence|drawdown|rsi', case=False, na=False)].to_string())
