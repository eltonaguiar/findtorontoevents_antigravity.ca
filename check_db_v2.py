import os
import pymysql
try:
    c = pymysql.connect(host='mysql.50webs.com', user='ejaguiar1_stocks', password=os.environ.get("DB_PASS_STOCKS",""), database='ejaguiar1_stocks')
    cur = c.cursor()
    
    # Check for antigravity_experimental picks
    cur.execute('SELECT COUNT(*) FROM trading_picks WHERE source_system="antigravity_experimental"')
    count = cur.fetchone()[0]
    print(f"\nAntigravity Experimental Picks Count: {count}")
    
    # Check for the 600-variant strategies
    cur.execute('SELECT COUNT(*) FROM trading_picks WHERE strategy LIKE "%multi_asset_stocks_rsi2_pullback%"')
    count2 = cur.fetchone()[0]
    print(f"Multi-Asset Strategy (rsi2) Count: {count2}")
    
    # Recently added (today)
    cur.execute('SELECT COUNT(*) FROM trading_picks WHERE created_at >= "2026-04-02"')
    print(f"Total Picks Added Today (2026-04-02): {cur.fetchone()[0]}")
    
    c.close()
except Exception as e:
    print(f"Error connecting: {e}")
