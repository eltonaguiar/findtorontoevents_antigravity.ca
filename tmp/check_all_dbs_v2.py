import pymysql

def check_all_remote_dbs_v2():
    dbs = [
        "ejaguiar1_stocks", "ejaguiar1_memecoin", "ejaguiar1_news",
        "ejaguiar1_sportsbet", "ejaguiar1_tvmoviestrailers",
        "ejaguiar1_events", "ejaguiar1_favcreators"
    ]
    passwords = {
        "ejaguiar1_stocks": "stocks",
        "ejaguiar1_memecoin": "memecoin",
        "ejaguiar1_news": "news",
        "ejaguiar1_sportsbet": "sportsbet",
        "ejaguiar1_tvmoviestrailers": "tvmoviestrailers",
        "ejaguiar1_events": "events",
        "ejaguiar1_favcreators": "favcreators"
    }
    for db in dbs:
        try:
            conn = pymysql.connect(
                host="mysql.50webs.com",
                user=db,
                password=passwords.get(db, "stocks"),
                database=db,
                autocommit=True
            )
            print(f"Database: {db}")
            cur = conn.cursor()
            cur.execute("SHOW TABLES")
            for t in cur.fetchall():
                table = t[0]
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                print(f"  {table}: {cur.fetchone()[0]} rows")
            conn.close()
        except Exception as e:
            print(f"Failed to connect to {db}: {e}")

if __name__ == "__main__":
    check_all_remote_dbs_v2()
