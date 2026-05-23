import json, pymysql, os

# Load first pick from JSON
json_path = os.path.join('audit_dashboard', 'data', 'forex_futures_picks.json')
with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)
first_pick = data['picks'][0]
print('JSON entry:')
print(json.dumps(first_pick, indent=2))

# DB connection parameters (same as mysql_trading_sync.py)
DB_HOST = os.getenv('DB_HOST', 'mysql.50webs.com')
DB_PORT = int(os.getenv('DB_PORT', '3306'))
DB_USER = os.getenv('DB_USER', 'ejaguiar1_stocks')
DB_PASS = os.getenv('DB_PASS', 'stocks')
DB_NAME = os.getenv('DB_NAME', 'ejaguiar1_stocks')

conn = pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS, database=DB_NAME, charset='utf8mb4')
cursor = conn.cursor(pymysql.cursors.DictCursor)

symbol = first_pick['symbol']
entry_date = first_pick['entry_date']
# Query the trading_picks table for matching symbol and date
sql = """
SELECT * FROM at_local_picks
WHERE symbol = %s AND DATE(created_at) = %s
LIMIT 1
"""
cursor.execute(sql, (symbol, entry_date))
row = cursor.fetchone()
print('\nDB row:')
print(row)

cursor.close()
conn.close()
