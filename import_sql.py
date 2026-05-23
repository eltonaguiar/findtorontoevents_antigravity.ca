import sqlite3, pathlib, sys
sql_path = pathlib.Path('data/10_123_0_33 (6).sql')
if not sql_path.exists():
    print('SQL file not found at', sql_path)
    sys.exit(1)
conn = sqlite3.connect('data/audit_trail.db')
with sql_path.open('r', encoding='utf-8') as f:
    script = f.read()
try:
    conn.executescript(script)
    conn.commit()
    print('SQL script executed successfully')
except Exception as e:
    print('Error executing SQL script:', e)
finally:
    conn.close()
