#!/usr/bin/env python3
"""Save picks_now.json to MySQL picks_now_tracker with NaN-safe handling."""
import json, math, pymysql, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.db_env import get_stocks_creds

data = json.loads((Path(__file__).resolve().parent.parent / "audit_dashboard/data/picks_now.json").read_text())
picks = data.get("picks", [])
if not picks:
    print("No picks to save")
    exit(0)

def sn(v):
    if v is None: return None
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)): return None
    try: return float(v)
    except: None
def si(v):
    if v is None: return 0
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)): return 0
    try: return int(float(v))
    except: return 0

creds = get_stocks_creds()
conn = pymysql.connect(**creds)
cur = conn.cursor()
inserted = 0
for p in picks:
    price = sn(p.get("price"))
    tp, sl = p.get("suggested_tp_pct"), p.get("suggested_sl_pct")
    cur.execute("""
        INSERT INTO picks_now_tracker 
        (generated_at, symbol, asset_class, direction, entry_price,
         suggested_tp, suggested_sl, score, rvol, rsi,
         analyst_rating, analyst_count, target_price, upside_pct,
         eli5_reason, signals)
        VALUES (NOW(), %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        p["symbol"], p.get("class",""), p.get("direction","LONG"),
        sn(price), sn(price*(1+tp/100)) if tp else None, sn(price*(1-sl/100)) if sl else None,
        sn(p.get("score")), sn(p.get("rvol")), sn(p.get("rsi")),
        str(p.get("analyst",""))[:30] or None, si(p.get("analyst_n")),
        sn(p.get("target_price")), sn(p.get("upside_pct")),
        (p.get("eli5_reason") or "")[:2000] or None,
        (p.get("signals") or "")[:500],
    ))
    inserted += 1
conn.commit()
conn.close()
print(f"✅ Saved {inserted} picks to DB")
