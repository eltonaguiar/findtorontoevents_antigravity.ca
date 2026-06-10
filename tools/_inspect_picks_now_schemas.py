"""One-shot inspect picks_now.json + trading_picks + at_pick_outcomes schemas."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pymysql
from tools.db_env import get_stocks_creds

# 1. picks_now.json
with open('audit_dashboard/data/picks_now.json') as f:
    d = json.load(f)
print('=== picks_now.json top-level keys ===')
print(list(d.keys()))
for k in d.keys():
    v = d[k]
    if isinstance(v, list):
        print(f'  {k}: list len={len(v)}')
        if v and isinstance(v[0], dict):
            print(f'    first row keys: {list(v[0].keys())}')
            print(f'    first row: {json.dumps(v[0], indent=2)[:600]}')
    else:
        print(f'  {k}: {type(v).__name__} = {str(v)[:120]}')

# 2. trading_picks
print('\n=== trading_picks schema ===')
conn = pymysql.connect(**get_stocks_creds(), cursorclass=pymysql.cursors.DictCursor)
cur = conn.cursor()
cur.execute('DESCRIBE trading_picks')
for r in cur.fetchall():
    print(f'  {r["Field"]:24} {r["Type"]:30} {r["Null"]:4} {r["Key"]:4} {r["Default"]}')
cur.execute('SELECT COUNT(*) c, COUNT(DISTINCT symbol) s, MIN(created_at) mn, MAX(created_at) mx FROM trading_picks')
r = cur.fetchone()
print(f'  rows: {r["c"]}, symbols: {r["s"]}, created: {r["mn"]} .. {r["mx"]}')

# 3. at_pick_outcomes
print('\n=== at_pick_outcomes schema ===')
cur.execute('DESCRIBE at_pick_outcomes')
for r in cur.fetchall():
    print(f'  {r["Field"]:24} {r["Type"]:30} {r["Null"]:4} {r["Key"]:4} {r["Default"]}')
cur.execute('SELECT COUNT(*) c, COUNT(DISTINCT symbol) s, COUNT(DISTINCT pick_id) p, MAX(resolved_at) mx FROM at_pick_outcomes')
r = cur.fetchone()
print(f'  rows: {r["c"]}, symbols: {r["s"]}, distinct pick_ids: {r["p"]}, max resolved_at: {r["mx"]}')
conn.close()
