import os
import pymysql
try:
    c=pymysql.connect(host='mysql.50webs.com', user='ejaguiar1_stocks', password=os.environ.get("DB_PASS_STOCKS",""), database='ejaguiar1_stocks')
    cur=c.cursor()
    cur.execute('SELECT source_system, COUNT(*) FROM trading_picks GROUP BY source_system')
    print("Database Contents by Source System:")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]}")
    
    # Check for specific experimental picks
    cur.execute('SELECT COUNT(*) FROM trading_picks WHERE source_system="experimental_new"')
    print(f"\nExperimental Picks Count: {cur.fetchone()[0]}")
    
    c.close()
except Exception as e:
    print(f"Error connecting: {e}")
