import os
import mysql.connector

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
# 2. at_raw_picks (continued)
# ============================================================
section("2. at_raw_picks (continued)")

cur.execute("SELECT source_system, COUNT(*) as cnt FROM at_raw_picks GROUP BY source_system ORDER BY cnt DESC LIMIT 15")
print("Top source_systems:")
for r in cur.fetchall():
    print("  %s: %s" % (r["source_system"], r["cnt"]))

cur.execute("SELECT COUNT(*) as cnt FROM at_raw_picks WHERE entry_price IS NULL OR entry_price = 0")
print("\nNULL/zero entry_price:", cur.fetchone()["cnt"])

cur.execute("SELECT COUNT(*) as cnt FROM at_raw_picks WHERE symbol IS NULL OR symbol = ''")
print("NULL/empty symbol:", cur.fetchone()["cnt"])

cur.execute("""
    SELECT symbol, source_system, direction, DATE(recorded_at) as dt, COUNT(*) as cnt
    FROM at_raw_picks
    GROUP BY symbol, source_system, direction, DATE(recorded_at)
    HAVING cnt > 5
    ORDER BY cnt DESC
    LIMIT 10
""")
dupes = cur.fetchall()
print("\nHigh-freq duplicates (>5/day same symbol+system+dir): %d groups" % len(dupes))
for d in dupes[:5]:
    print("  %s / %s / %s on %s: %s rows" % (d["symbol"], d["source_system"], d["direction"], d["dt"], d["cnt"]))

cur.execute("SELECT * FROM at_raw_picks ORDER BY recorded_at DESC LIMIT 3")
print("\nMost recent 3:")
for r in cur.fetchall():
    print("  sym=%s sys=%s status=%s entry=%s pnl=%s rec=%s" % (
        r.get("symbol"), r.get("source_system"), r.get("status"),
        r.get("entry_price"), r.get("pnl_pct"), r.get("recorded_at")))

cur.execute("SELECT COUNT(*) as cnt FROM at_raw_picks WHERE pnl_pct IS NOT NULL AND pnl_pct != 0")
print("\nNon-zero pnl_pct:", cur.fetchone()["cnt"])
cur.execute("SELECT COUNT(*) as cnt FROM at_raw_picks WHERE exit_price IS NOT NULL")
print("Has exit_price:", cur.fetchone()["cnt"])

# Dedup hash analysis
cur.execute("SELECT COUNT(*) as cnt FROM at_raw_picks WHERE dedup_hash IS NULL")
print("NULL dedup_hash:", cur.fetchone()["cnt"])
cur.execute("SELECT COUNT(DISTINCT dedup_hash) as cnt FROM at_raw_picks WHERE dedup_hash IS NOT NULL")
print("Distinct dedup_hashes:", cur.fetchone()["cnt"])
cur.execute("SELECT dedup_hash, COUNT(*) as cnt FROM at_raw_picks WHERE dedup_hash IS NOT NULL GROUP BY dedup_hash HAVING cnt > 1 ORDER BY cnt DESC LIMIT 5")
hash_dupes = cur.fetchall()
print("Dedup hash collisions (same hash multiple rows): %d" % len(hash_dupes))
for h in hash_dupes[:3]:
    print("  hash=%s... count=%s" % (str(h["dedup_hash"])[:16], h["cnt"]))

# Stale/banned/demoted counts
cur.execute("SELECT SUM(was_stale) as stale, SUM(was_banned) as banned, SUM(was_demoted) as demoted, SUM(was_wr_suppressed) as wr_supp FROM at_raw_picks")
r = cur.fetchone()
print("\nFiltering flags: stale=%s, banned=%s, demoted=%s, wr_suppressed=%s" % (r["stale"], r["banned"], r["demoted"], r["wr_supp"]))

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
    print("  %-30s %-30s %-5s" % (c["Field"], c["Type"], c["Null"]))

# Find date columns dynamically
date_cols3 = [c["Field"] for c in cols3 if "date" in c["Type"].lower() or "time" in c["Type"].lower()]
for dc in date_cols3:
    cur.execute("SELECT MIN(`%s`) as mn, MAX(`%s`) as mx FROM at_signal_outcomes" % (dc, dc))
    r = cur.fetchone()
    print("  %s: %s to %s" % (dc, r["mn"], r["mx"]))

cur.execute("SELECT outcome, COUNT(*) as cnt FROM at_signal_outcomes GROUP BY outcome ORDER BY cnt DESC")
print("\nOutcome distribution:")
for r in cur.fetchall():
    print("  %s: %s" % (r["outcome"], r["cnt"]))

try:
    cur.execute("SELECT AVG(pnl_pct) as a, MIN(pnl_pct) as mi, MAX(pnl_pct) as ma, STDDEV(pnl_pct) as s FROM at_signal_outcomes WHERE pnl_pct IS NOT NULL")
    r = cur.fetchone()
    print("\nPnL: avg=%.4f, min=%.4f, max=%.4f, std=%.4f" % (
        float(r["a"] or 0), float(r["mi"] or 0), float(r["ma"] or 0), float(r["s"] or 0)))
except Exception as e:
    print("PnL stats error:", e)

cur.execute("SELECT COUNT(*) as cnt FROM at_signal_outcomes WHERE pnl_pct IS NULL")
print("NULL pnl_pct:", cur.fetchone()["cnt"])

# Use first date column for ordering
ord_col = date_cols3[0] if date_cols3 else "id"
cur.execute("SELECT * FROM at_signal_outcomes ORDER BY `%s` DESC LIMIT 5" % ord_col)
print("\nMost recent 5:")
for r in cur.fetchall():
    for k,v in r.items():
        val = str(v)[:60] if v is not None else "NULL"
        print("    %s: %s" % (k, val))
    print("  ---")

# System breakdown in outcomes
# Get actual column names to find system reference
sys_cols = [c["Field"] for c in cols3 if "system" in c["Field"].lower() or "source" in c["Field"].lower()]
if sys_cols:
    sc = sys_cols[0]
    cur.execute("SELECT `%s`, COUNT(*) as cnt, AVG(pnl_pct) as avg_pnl FROM at_signal_outcomes GROUP BY `%s` ORDER BY cnt DESC LIMIT 10" % (sc, sc))
    print("\nOutcomes by %s:" % sc)
    for r in cur.fetchall():
        print("  %s: %d outcomes, avg_pnl=%.4f" % (r[sc], r["cnt"], float(r["avg_pnl"] or 0)))

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
    print("  %-30s %-30s %-5s" % (c["Field"], c["Type"], c["Null"]))

date_cols4 = [c["Field"] for c in cols4 if "date" in c["Type"].lower() or "time" in c["Type"].lower()]
for dc in date_cols4:
    cur.execute("SELECT MIN(`%s`) as mn, MAX(`%s`) as mx FROM at_discord_notifications" % (dc, dc))
    r = cur.fetchone()
    print("  %s: %s to %s" % (dc, r["mn"], r["mx"]))

# Check for notification_type column
type_cols = [c["Field"] for c in cols4 if "type" in c["Field"].lower()]
if type_cols:
    tc = type_cols[0]
    cur.execute("SELECT `%s`, COUNT(*) as cnt FROM at_discord_notifications GROUP BY `%s` ORDER BY cnt DESC LIMIT 10" % (tc, tc))
    print("\nNotification types:")
    for r in cur.fetchall():
        print("  %s: %s" % (r[tc], r["cnt"]))

status_cols = [c["Field"] for c in cols4 if "status" in c["Field"].lower()]
if status_cols:
    sc = status_cols[0]
    cur.execute("SELECT `%s`, COUNT(*) as cnt FROM at_discord_notifications GROUP BY `%s` ORDER BY cnt DESC" % (sc, sc))
    print("\nStatus distribution:")
    for r in cur.fetchall():
        print("  %s: %s" % (r[sc], r["cnt"]))

msg_cols = [c["Field"] for c in cols4 if "message" in c["Field"].lower() or "payload" in c["Field"].lower() or "content" in c["Field"].lower()]
if msg_cols:
    mc = msg_cols[0]
    cur.execute("SELECT COUNT(*) as cnt FROM at_discord_notifications WHERE `%s` IS NULL OR `%s` = ''" % (mc, mc))
    print("\nNULL/empty %s: %s" % (mc, cur.fetchone()["cnt"]))
    cur.execute("SELECT AVG(LENGTH(`%s`)) as avg_len, MAX(LENGTH(`%s`)) as max_len, MIN(LENGTH(`%s`)) as min_len FROM at_discord_notifications WHERE `%s` IS NOT NULL" % (mc, mc, mc, mc))
    r = cur.fetchone()
    print("Message length: avg=%.0f, max=%s, min=%s" % (float(r["avg_len"] or 0), r["max_len"], r["min_len"]))

ord4 = date_cols4[0] if date_cols4 else "id"
cur.execute("SELECT * FROM at_discord_notifications ORDER BY `%s` DESC LIMIT 3" % ord4)
print("\nMost recent 3:")
for r in cur.fetchall():
    for k,v in r.items():
        val = str(v)[:100] if v is not None else "NULL"
        print("    %s: %s" % (k, val))
    print("  ---")

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
    print("  %-30s %-30s %-5s" % (c["Field"], c["Type"], c["Null"]))

date_cols5 = [c["Field"] for c in cols5 if "date" in c["Type"].lower() or "time" in c["Type"].lower()]
for dc in date_cols5:
    cur.execute("SELECT MIN(`%s`) as mn, MAX(`%s`) as mx FROM simulation_grid" % (dc, dc))
    r = cur.fetchone()
    print("  %s: %s to %s" % (dc, r["mn"], r["mx"]))

cur.execute("SELECT * FROM simulation_grid LIMIT 3")
rows = cur.fetchall()
print("\nSample 3 rows:")
for r in rows:
    for k,v in r.items():
        val = str(v)[:80] if v is not None else "NULL"
        print("  %s: %s" % (k, val))
    print("  ---")

# NULLs
total5 = 5846
print("\nNULL counts:")
for col_info in cols5:
    col = col_info["Field"]
    cur.execute("SELECT COUNT(*) as cnt FROM simulation_grid WHERE `%s` IS NULL" % col)
    null_cnt = cur.fetchone()["cnt"]
    if null_cnt > 0:
        print("  %s: %s NULLs (%.1f%%)" % (col, null_cnt, 100.0*null_cnt/total5))

cur.execute("SELECT COUNT(*) as total, COUNT(DISTINCT id) as distinct_ids FROM simulation_grid")
r = cur.fetchone()
print("\nTotal: %s, Distinct IDs: %s" % (r["total"], r["distinct_ids"]))

# Group by interesting columns
for col in [c["Field"] for c in cols5 if "name" in c["Field"].lower() or "symbol" in c["Field"].lower() or "class" in c["Field"].lower() or "status" in c["Field"].lower() or "type" in c["Field"].lower()]:
    try:
        cur.execute("SELECT `%s`, COUNT(*) as cnt FROM simulation_grid GROUP BY `%s` ORDER BY cnt DESC LIMIT 10" % (col, col))
        results = cur.fetchall()
        if results:
            print("\nTop %s values:" % col)
            for r in results:
                print("  %s: %s" % (r[col], r["cnt"]))
    except:
        pass

# Check for numeric columns with suspicious values
for col_info in cols5:
    t = col_info["Type"].lower()
    col = col_info["Field"]
    if "decimal" in t or "float" in t or "double" in t:
        try:
            cur.execute("SELECT AVG(`%s`) as a, MIN(`%s`) as mi, MAX(`%s`) as ma FROM simulation_grid WHERE `%s` IS NOT NULL" % (col, col, col, col))
            r = cur.fetchone()
            print("  %s: avg=%s, min=%s, max=%s" % (col, r["a"], r["mi"], r["ma"]))
        except:
            pass

conn.close()
print("\n\nAudit complete.")
