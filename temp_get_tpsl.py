import sqlite3

conn = sqlite3.connect('data/live_picks.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute("SELECT symbol, side, entry_price, take_profit, stop_loss FROM live_picks WHERE symbol IN ('CL=F', 'ZN=F')")
for r in c.fetchall():
    print(dict(r))

conn.close()
