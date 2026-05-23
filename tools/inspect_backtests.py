#!/usr/bin/env python3
import os
from dotenv import load_dotenv
import mysql.connector

load_dotenv()
HOST = os.getenv('MYSQL_HOST')
USER = os.getenv('DB_BACKTESTS_USER')
PASS = os.getenv('DB_PASS_BACKTESTS')
DB = os.getenv('DB_NAME_BACKTESTS')

conn = mysql.connector.connect(host=HOST, user=USER, password=PASS, database=DB)
cur = conn.cursor()
cur.execute('SHOW TABLES')
tables = [row[0] for row in cur.fetchall()]
print('Tables:', tables)
for tbl in tables:
    cur.execute(f'SHOW COLUMNS FROM `{tbl}`')
    cols = [row[0] for row in cur.fetchall()]
    print(tbl, cols)
cur.close()
conn.close()
