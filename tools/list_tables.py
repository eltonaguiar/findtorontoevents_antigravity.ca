#!/usr/bin/env python3
import os
from dotenv import load_dotenv
import mysql.connector

load_dotenv()
HOST = os.getenv('MYSQL_HOST')

def get_credentials(db_name):
    if db_name == os.getenv('DB_NAME_STOCKS'):
        return os.getenv('DB_USER'), os.getenv('DB_PASS_STOCKS')
    elif db_name == os.getenv('DB_NAME_BACKTESTS'):
        return os.getenv('DB_BACKTESTS_USER'), os.getenv('DB_PASS_BACKTESTS')
    else:
        return os.getenv('MYSQL_USERNAME'), os.getenv('DB_PASS_STOCKS')


def list_tables(db_name):
    user, pwd = get_credentials(db_name)
    conn = mysql.connector.connect(host=HOST, user=user, password=pwd, database=db_name)
    cur = conn.cursor()
    cur.execute('SHOW TABLES')
    tables = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return tables

if __name__ == '__main__':
    dbs = [os.getenv('DB_NAME_STOCKS'), os.getenv('DB_NAME_BACKTESTS')]
    for db in dbs:
        if not db:
            continue
        try:
            tbls = list_tables(db)
            print(f"{db}: {tbls}")
        except Exception as e:
            print(f"Error for {db}: {e}")
