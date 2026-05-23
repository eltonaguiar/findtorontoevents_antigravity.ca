import os
os.environ["AUDIT_DB_HOST"] = "mysql.50webs.com"
os.environ["AUDIT_DB_USER"] = "ejaguiar1_stocks"
os.environ["AUDIT_DB_PASS"] = "stocks"
os.environ["AUDIT_DB_NAME"] = "ejaguiar1_stocks"

from audit_trail.mysql_client import _create_connection

try:
    conn = _create_connection()
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    print("Tables in ejaguiar1_stocks:")
    for table in tables:
        print(table[0])

    # For each table, get count and sample
    for table_name in [t[0] for t in tables]:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"\n{table_name}: {count} rows")

        if count > 0:
            cursor.execute(f"DESCRIBE {table_name}")
            columns = cursor.fetchall()
            print("Columns:", [col[0] for col in columns])

            cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
            rows = cursor.fetchall()
            print("Sample rows:")
            for row in rows:
                print(row)

    conn.close()
except Exception as e:
    print(f"Error: {e}")