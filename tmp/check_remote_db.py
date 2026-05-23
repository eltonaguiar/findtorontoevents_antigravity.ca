import pymysql
import os

def check_remote_db():
    conn = pymysql.connect(
        host="mysql.50webs.com",
        user="ejaguiar1_stocks",
        password=os.environ.get("DB_PASS_STOCKS",""), database="ejaguiar1_stocks",
        autocommit=True
    )
    cur = conn.cursor()
    cur.execute("SHOW TABLES")
    tables = [t[0] for t in cur.fetchall()]
    print(f"Tables in ejaguiar1_stocks:")
    for table in tables:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        print(f"  {table}: {count} rows")
    conn.close()

if __name__ == "__main__":
    check_remote_db()
