import os
from audit_trail.mysql_client import _create_connection

db = _create_connection()
cur = db.cursor()
with open('audit_trail/migration_add_futures_etf.sql') as f:
    sql = f.read()

queries = [q.strip() for q in sql.split(';') if q.strip()]
for q in queries:
    # Skip table if it doesn't exist error 1146
    try:
        cur.execute(q)
        print("Success:", q[:50])
    except Exception as e:
        if '1146' in str(e):
            print("Skipping missing table:", q[:50])
        else:
            print("Error executing:", q[:50], "\n", e)

db.commit()
db.close()
print('Migration complete')
