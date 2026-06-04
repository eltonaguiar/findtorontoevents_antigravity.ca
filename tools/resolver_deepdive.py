#!/usr/bin/env python3
"""Deep-dive into resolver + DB to diagnose the pipeline integrity crisis."""
import mysql.connector
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

conn = mysql.connector.connect(
    host='mysql.50webs.com',
    user='ejaguiar1_stocks',
    password=os.environ.get('DB_PASS_STOCKS','') or os.environ.get('MYSQL_PASSWORD',''),
    database='ejaguiar1_stocks'
)
cur = conn.cursor()

# 1. at_pick_outcomes: structure + stats
print("=== at_pick_outcomes: columns ===")
cur.execute("DESCRIBE at_pick_outcomes")
for r in cur.fetchall():
    print(f"  {r[0]} {r[1]}")

print("\n=== at_pick_outcomes: counts by status ===")
cur.execute("SELECT status, COUNT(*) FROM at_pick_outcomes GROUP BY status ORDER BY COUNT(*) DESC")
for r in cur.fetchall():
    print(f"  {r[0]:15s}: {r[1]}")

print("\n=== at_pick_outcomes: counts by resolution_method ===")
cur.execute("SELECT resolution_method, COUNT(*) FROM at_pick_outcomes GROUP BY resolution_method ORDER BY COUNT(*) DESC")
for r in cur.fetchall():
    print(f"  {r[0]:15s}: {r[1]}")

print("\n=== at_pick_outcomes: counts by asset_class ===")
cur.execute("SELECT asset_class, COUNT(*) FROM at_pick_outcomes GROUP BY asset_class ORDER BY COUNT(*) DESC")
for r in cur.fetchall():
    print(f"  {r[0]:15s}: {r[1]}")

print("\n=== EXPIRED% by class (TIME_EXPIRED vs TP_HIT vs SL_HIT) ===")
cur.execute("""
    SELECT asset_class,
           COUNT(*) as total,
           SUM(CASE WHEN resolution_method='TIME_EXPIRED' THEN 1 ELSE 0 END) as time_exit,
           SUM(CASE WHEN resolution_method='TP_HIT' THEN 1 ELSE 0 END) as tp_hit,
           SUM(CASE WHEN resolution_method='SL_HIT' THEN 1 ELSE 0 END) as sl_hit,
           ROUND(100.0 * SUM(CASE WHEN resolution_method='TIME_EXPIRED' THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0), 1) as pct_expired
    FROM at_pick_outcomes
    GROUP BY asset_class
    ORDER BY total DESC
""")
for r in cur.fetchall():
    print(f"  {r[0]:15s}: total={r[1]} expired={r[2]} tp={r[3]} sl={r[4]} expired%={r[5]}%")

print("\n=== at_pick_outcomes: sample EXPIRED rows (non-crypto) ===")
cur.execute("""
    SELECT symbol, strategy, asset_class, pnl_pct, resolution_method, resolved_at
    FROM at_pick_outcomes
    WHERE resolution_method = 'TIME_EXPIRED' AND asset_class != 'CRYPTO'
    ORDER BY resolved_at DESC
    LIMIT 10
""")
for r in cur.fetchall():
    print(f"  {r[0]:12s} | {r[1]:25s} | {r[2]:10s} | pnl={r[3]}% | method={r[4]} | resolved={r[5]}")

# 2. Check universal_resolved_picks.json
resolved_file = ROOT / "audit_trail" / "data" / "universal_resolved_picks.json"
if resolved_file.exists():
    with open(resolved_file) as f:
        resolved = json.load(f)
    total = len(resolved) if isinstance(resolved, list) else len(resolved.get("resolved", []))
    print(f"\n=== universal_resolved_picks.json: {total} resolved picks ===")
    
    # Count by exit_reason
    picks = resolved if isinstance(resolved, list) else resolved.get("resolved", [])
    from collections import Counter
    reasons = Counter(p.get("exit_reason", p.get("status", "?")) for p in picks if isinstance(p, dict))
    for reason, count in reasons.most_common(10):
        print(f"  {reason:15s}: {count}")
    
    # Count by asset_class
    classes = Counter(p.get("asset_class", "UNKNOWN") for p in picks if isinstance(p, dict))
    for cls, count in classes.most_common(10):
        print(f"  {cls:15s}: {count}")
else:
    print(f"\n=== universal_resolved_picks.json: NOT FOUND ===")

# 3. Check signal_outcomes freshness
outcomes_file = ROOT / "alpha_engine" / "data" / "signal_outcomes.json"
if outcomes_file.exists():
    import os
    mtime = os.path.getmtime(outcomes_file)
    from datetime import datetime, timezone
    age_days = (datetime.now(timezone.utc) - datetime.fromtimestamp(mtime, tz=timezone.utc)).days
    size = outcomes_file.stat().st_size
    print(f"\n=== signal_outcomes.json: {size/1e6:.1f}MB, {age_days} days old ===")
else:
    print(f"\n=== signal_outcomes.json: NOT FOUND ===")

# 4. Check at_pick_outcomes for duplicate symbol entries
print("\n=== Potential dedup issues: symbol+strategy combos with >5 entries ===")
cur.execute("""
    SELECT symbol, strategy, status, COUNT(*) as cnt
    FROM at_pick_outcomes
    GROUP BY symbol, strategy, status
    HAVING cnt > 5
    ORDER BY cnt DESC
    LIMIT 20
""")
for r in cur.fetchall():
    print(f"  {r[0]:12s} | {r[1]:5s} | {r[2]:25s} | {r[3]} entries")

cur.close()
conn.close()
