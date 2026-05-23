import os
import mysql.connector
from datetime import datetime

conn = mysql.connector.connect(
    host="mysql.50webs.com",
    user="ejaguiar1_stocks",
    password=os.environ.get("DB_PASS_STOCKS",""), database="ejaguiar1_stocks"
)
cur = conn.cursor(dictionary=True)

def section(title):
    print("\n" + "="*80)
    print("  " + title)
    print("="*80)

# ============================================================
# 1. at_consensus_picks
# ============================================================
section("1. at_consensus_picks")

cur.execute("SELECT COUNT(*) as cnt FROM at_consensus_picks")
print("Row count:", cur.fetchone()["cnt"])

cur.execute("DESCRIBE at_consensus_picks")
cols = cur.fetchall()
print("\nColumns:")
for c in cols:
    print("  %-30s %-30s %-5s Default=%s" % (c["Field"], c["Type"], c["Null"], c["Default"]))

cur.execute("SELECT status, COUNT(*) as cnt FROM at_consensus_picks GROUP BY status ORDER BY cnt DESC")
print("\nStatus distribution:")
for r in cur.fetchall():
    print("  %s: %s" % (r["status"], r["cnt"]))

cur.execute("SELECT COUNT(*) as cnt FROM at_consensus_picks WHERE pnl_pct IS NULL")
print("\nNULL pnl_pct:", cur.fetchone()["cnt"])

cur.execute("SELECT COUNT(*) as cnt FROM at_consensus_picks WHERE pnl_pct IS NOT NULL AND pnl_pct != 0")
print("Non-zero pnl_pct:", cur.fetchone()["cnt"])

cur.execute("SELECT COUNT(*) as cnt FROM at_consensus_picks WHERE exit_price IS NOT NULL")
print("Has exit_price:", cur.fetchone()["cnt"])

cur.execute("SELECT MIN(created_at) as mn, MAX(created_at) as mx FROM at_consensus_picks")
r = cur.fetchone()
print("\nDate range: %s to %s" % (r["mn"], r["mx"]))

cur.execute("SELECT * FROM at_consensus_picks ORDER BY created_at DESC LIMIT 3")
print("\nMost recent 3 rows:")
for r in cur.fetchall():
    print("  id=%s symbol=%s status=%s pnl=%s entry=%s exit=%s created=%s" % (
        r.get("id"), r.get("symbol"), r.get("status"), r.get("pnl_pct"),
        r.get("entry_price"), r.get("exit_price"), r.get("created_at")))

cur.execute("""
    SELECT symbol, direction, DATE(created_at) as dt, COUNT(*) as cnt
    FROM at_consensus_picks
    GROUP BY symbol, direction, DATE(created_at)
    HAVING cnt > 3
    ORDER BY cnt DESC
    LIMIT 10
""")
dupes = cur.fetchall()
print("\nPotential duplicates (same symbol+direction+date, >3/day): %d groups" % len(dupes))
for d in dupes[:5]:
    print("  %s %s on %s: %s rows" % (d["symbol"], d["direction"], d["dt"], d["cnt"]))

# ============================================================
# 2. at_raw_picks
# ============================================================
section("2. at_raw_picks")

cur.execute("SELECT COUNT(*) as cnt FROM at_raw_picks")
print("Row count:", cur.fetchone()["cnt"])

cur.execute("DESCRIBE at_raw_picks")
cols = cur.fetchall()
print("\nColumns:")
for c in cols:
    print("  %-30s %-30s %-5s Default=%s" % (c["Field"], c["Type"], c["Null"], c["Default"]))

cur.execute("SELECT MIN(created_at) as mn, MAX(created_at) as mx FROM at_raw_picks")
r = cur.fetchone()
print("\nDate range: %s to %s" % (r["mn"], r["mx"]))

cur.execute("SELECT status, COUNT(*) as cnt FROM at_raw_picks GROUP BY status ORDER BY cnt DESC")
print("\nStatus distribution:")
for r in cur.fetchall():
    print("  %s: %s" % (r["status"], r["cnt"]))

cur.execute("SELECT system_name, COUNT(*) as cnt FROM at_raw_picks GROUP BY system_name ORDER BY cnt DESC LIMIT 15")
print("\nTop systems:")
for r in cur.fetchall():
    print("  %s: %s" % (r["system_name"], r["cnt"]))

cur.execute("SELECT COUNT(*) as cnt FROM at_raw_picks WHERE entry_price IS NULL OR entry_price = 0")
print("\nNULL/zero entry_price:", cur.fetchone()["cnt"])

cur.execute("SELECT COUNT(*) as cnt FROM at_raw_picks WHERE symbol IS NULL OR symbol = ''")
print("NULL/empty symbol:", cur.fetchone()["cnt"])

cur.execute("""
    SELECT symbol, system_name, direction, DATE(created_at) as dt, COUNT(*) as cnt
    FROM at_raw_picks
    GROUP BY symbol, system_name, direction, DATE(created_at)
    HAVING cnt > 5
    ORDER BY cnt DESC
    LIMIT 10
""")
dupes = cur.fetchall()
print("\nHigh-frequency duplicates (>5 same symbol+system+direction+date): %d groups" % len(dupes))
for d in dupes[:5]:
    print("  %s / %s / %s on %s: %s rows" % (d["symbol"], d["system_name"], d["direction"], d["dt"], d["cnt"]))

cur.execute("SELECT * FROM at_raw_picks ORDER BY created_at DESC LIMIT 3")
print("\nMost recent 3:")
for r in cur.fetchall():
    print("  id=%s sym=%s sys=%s status=%s entry=%s pnl=%s created=%s" % (
        r.get("id"), r.get("symbol"), r.get("system_name"), r.get("status"),
        r.get("entry_price"), r.get("pnl_pct"), r.get("created_at")))

# ============================================================
# 3. at_signal_outcomes
# ============================================================
section("3. at_signal_outcomes")

cur.execute("SELECT COUNT(*) as cnt FROM at_signal_outcomes")
print("Row count:", cur.fetchone()["cnt"])

cur.execute("DESCRIBE at_signal_outcomes")
cols3 = cur.fetchall()
print("\nColumns:")
for c in cols3:
    print("  %-30s %-30s %-5s Default=%s" % (c["Field"], c["Type"], c["Null"], c["Default"]))

cur.execute("SELECT MIN(created_at) as mn, MAX(created_at) as mx FROM at_signal_outcomes")
r = cur.fetchone()
print("\nDate range: %s to %s" % (r["mn"], r["mx"]))

cur.execute("SELECT outcome, COUNT(*) as cnt FROM at_signal_outcomes GROUP BY outcome ORDER BY cnt DESC")
print("\nOutcome distribution:")
for r in cur.fetchall():
    print("  %s: %s" % (r["outcome"], r["cnt"]))

cur.execute("SELECT AVG(pnl_pct) as avg_pnl, MIN(pnl_pct) as min_pnl, MAX(pnl_pct) as max_pnl FROM at_signal_outcomes WHERE pnl_pct IS NOT NULL")
r = cur.fetchone()
print("\nPnL stats: avg=%s, min=%s, max=%s" % (r["avg_pnl"], r["min_pnl"], r["max_pnl"]))

cur.execute("SELECT * FROM at_signal_outcomes ORDER BY created_at DESC LIMIT 5")
print("\nMost recent 5:")
for r in cur.fetchall():
    print("  id=%s sym=%s outcome=%s pnl=%s sys=%s created=%s" % (
        r.get("id"), r.get("symbol"), r.get("outcome"), r.get("pnl_pct"),
        r.get("system_name"), r.get("created_at")))

cur.execute("SELECT COUNT(*) as cnt FROM at_signal_outcomes WHERE pnl_pct IS NULL")
print("\nNULL pnl_pct:", cur.fetchone()["cnt"])

# ============================================================
# 4. at_discord_notifications
# ============================================================
section("4. at_discord_notifications")

cur.execute("SELECT COUNT(*) as cnt FROM at_discord_notifications")
print("Row count:", cur.fetchone()["cnt"])

cur.execute("DESCRIBE at_discord_notifications")
cols4 = cur.fetchall()
print("\nColumns:")
for c in cols4:
    print("  %-30s %-30s %-5s Default=%s" % (c["Field"], c["Type"], c["Null"], c["Default"]))

cur.execute("SELECT MIN(created_at) as mn, MAX(created_at) as mx FROM at_discord_notifications")
r = cur.fetchone()
print("\nDate range: %s to %s" % (r["mn"], r["mx"]))

cur.execute("SELECT notification_type, COUNT(*) as cnt FROM at_discord_notifications GROUP BY notification_type ORDER BY cnt DESC LIMIT 10")
print("\nNotification types:")
for r in cur.fetchall():
    print("  %s: %s" % (r["notification_type"], r["cnt"]))

cur.execute("SELECT status, COUNT(*) as cnt FROM at_discord_notifications GROUP BY status ORDER BY cnt DESC")
print("\nStatus distribution:")
for r in cur.fetchall():
    print("  %s: %s" % (r["status"], r["cnt"]))

cur.execute("SELECT COUNT(*) as cnt FROM at_discord_notifications WHERE message IS NULL OR message = ''")
print("\nNULL/empty message:", cur.fetchone()["cnt"])

cur.execute("SELECT * FROM at_discord_notifications ORDER BY created_at DESC LIMIT 3")
print("\nMost recent 3:")
for r in cur.fetchall():
    msg = str(r.get("message",""))[:80] if r.get("message") else "NULL"
    print("  id=%s type=%s status=%s msg=%s... created=%s" % (
        r.get("id"), r.get("notification_type"), r.get("status"), msg, r.get("created_at")))

# ============================================================
# 5. simulation_grid
# ============================================================
section("5. simulation_grid")

cur.execute("SELECT COUNT(*) as cnt FROM simulation_grid")
print("Row count:", cur.fetchone()["cnt"])

cur.execute("DESCRIBE simulation_grid")
cols5 = cur.fetchall()
print("\nColumns:")
for c in cols5:
    print("  %-30s %-30s %-5s Default=%s" % (c["Field"], c["Type"], c["Null"], c["Default"]))

cur.execute("SELECT * FROM simulation_grid LIMIT 3")
rows = cur.fetchall()
print("\nSample 3 rows:")
for r in rows:
    for k,v in r.items():
        val = str(v)[:80] if v is not None else "NULL"
        print("  %s: %s" % (k, val))
    print("  ---")

# Check for NULLs in key columns
print("\nNULL counts per column:")
for col_info in cols5:
    col = col_info["Field"]
    cur.execute("SELECT COUNT(*) as cnt FROM simulation_grid WHERE `%s` IS NULL" % col)
    null_cnt = cur.fetchone()["cnt"]
    if null_cnt > 0:
        print("  NULL in %s: %s" % (col, null_cnt))

# Date range
date_cols = [c["Field"] for c in cols5 if "date" in c["Field"].lower() or "time" in c["Field"].lower() or "created" in c["Field"].lower()]
for dc in date_cols:
    cur.execute("SELECT MIN(`%s`) as mn, MAX(`%s`) as mx FROM simulation_grid" % (dc, dc))
    r = cur.fetchone()
    print("\n%s range: %s to %s" % (dc, r["mn"], r["mx"]))

cur.execute("SELECT COUNT(*) as total, COUNT(DISTINCT id) as distinct_ids FROM simulation_grid")
r = cur.fetchone()
print("\nTotal rows: %s, Distinct IDs: %s" % (r["total"], r["distinct_ids"]))

# Check for any grouping columns
try:
    cur.execute("SELECT strategy_name, COUNT(*) as cnt FROM simulation_grid GROUP BY strategy_name ORDER BY cnt DESC LIMIT 10")
    print("\nTop strategies in simulation_grid:")
    for r in cur.fetchall():
        print("  %s: %s" % (r["strategy_name"], r["cnt"]))
except:
    pass

try:
    cur.execute("SELECT symbol, COUNT(*) as cnt FROM simulation_grid GROUP BY symbol ORDER BY cnt DESC LIMIT 10")
    print("\nTop symbols in simulation_grid:")
    for r in cur.fetchall():
        print("  %s: %s" % (r["symbol"], r["cnt"]))
except:
    pass

conn.close()
print("\n\nAudit complete.")
