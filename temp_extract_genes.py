import sqlite3
import pandas as pd

conn = sqlite3.connect('E:/findtorontoevents_antigravity.ca/genome/strategy_registry.db')
query = "SELECT name, symbol_specialization, win_rate, total_trades, genes FROM strategies WHERE name LIKE 'PriceRoc%'"
df = pd.read_sql_query(query, conn)

with open('E:/findtorontoevents_antigravity.ca/temp_priceroc_genes.txt', 'w', encoding='utf-8') as f:
    for idx, row in df.iterrows():
        f.write(f"--- {row['name']} ({row['symbol_specialization']}) ---\n")
        f.write(f"Win Rate: {row['win_rate']}, Trades: {row['total_trades']}\n")
        f.write(f"Genes: {row['genes']}\n\n")

conn.close()
print("Done extracting genes.")
