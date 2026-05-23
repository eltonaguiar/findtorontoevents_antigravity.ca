import os
import pymysql
try:
    c = pymysql.connect(host='mysql.50webs.com', user='ejaguiar1_stocks', password=os.environ.get("DB_PASS_STOCKS",""), database='ejaguiar1_stocks')
    cur = c.cursor()
    
    # Check for multi_asset_copytrader picks
    cur.execute('SELECT COUNT(*) FROM trading_picks WHERE source_system="multi_asset_copytrader"')
    count = cur.fetchone()[0]
    print(f"\nMulti-Asset Copytrader Picks Count: {count}")
    
    # Check for specific strategies
    print("\nTop Strategies in DB Today:")
    cur.execute('SELECT strategy, COUNT(*) FROM trading_picks WHERE created_at >= "2026-04-02" GROUP BY strategy ORDER BY COUNT(*) DESC LIMIT 10')
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]}")
    
    c.close()
except Exception as e:
    print(f"Error connecting: {e}")
