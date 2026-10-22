"""Update opencode_paper_trading_status.json from latest DB counts.

Run hourly via cron or GitHub Actions.
"""
import json, os, sys, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pymysql
DB_HOST=os.getenv("AUDIT_DB_HOST","mysql.50webs.com")
DB_PORT=int(os.getenv("AUDIT_DB_PORT","3306"))
DB_USER=os.getenv("AUDIT_DB_USER","ejaguiar1_stocks")
DB_PASS=os.getenv("AUDIT_DB_PASS","stocks1234560")
DB_NAME=os.getenv("AUDIT_DB_NAME","ejaguiar1_stocks")
conn=pymysql.connect(host=DB_HOST,port=DB_PORT,user=DB_USER,password=DB_PASS,database=DB_NAME,connect_timeout=15)
cur=conn.cursor()
cur.execute("""
SELECT COUNT(*) n, SUM(status='WON') w
FROM at_raw_picks
WHERE source_system='AlphaEngine' AND strategy='luxalgo_confluence' AND direction='SHORT'
  AND symbol IN ('XRPUSDT','ETHUSDT','BTCUSDT','STXUSDT') AND status IN ('WON','LOST')
""")
n,w=cur.fetchone()
conn.close()
status={
  "agent":"OPENCODE_BEAM",
  "model":"beam-free",
  "updated_at":datetime.datetime.utcnow().isoformat()+"Z",
  "primary_candidate":{
    "strategy":"luxalgo_confluence",
    "direction":"SHORT",
    "symbols":["XRPUSDT","ETHUSDT","BTCUSDT","STXUSDT"],
    "status":"PAPER_TESTING",
    "n_resolved":int(n),
    "win_rate":round(w/n,4) if n else 0,
  },
  "notes":"Auto-updated by opencode_paper_trading_update.py"
}
out="audit_dashboard/data/opencode_paper_trading_status.json"
os.makedirs(os.path.dirname(out),exist_ok=True)
json.dump(status, open(out,"w"), indent=2)
print("updated", n, w)
