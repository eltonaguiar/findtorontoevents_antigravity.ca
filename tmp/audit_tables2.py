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

def find_date_cols(table):
    cur.execute("DESCRIBE %s" % table)
    cols = cur.fetchall()
    date_cols = []
    for c in cols:
        t = c["Type"].lower()
        if "date" in t or "time" in t:
            date_cols.append(c["Field"])
    return cols, date_cols

def show_date_ranges(table, date_cols):
    for dc in date_cols:
        cur.execute("SELECT MIN(`%s`) as mn, MAX(`%s`) as mx FROM %s" % (dc, dc, table))
        r = cur.fetchone()
        print("  %s range: %s to %s" % (dc, r["mn"], r["mx"]))

# ============================================================
# 1. at_consensus_picks
# ============================================================
section("1. at_consensus_picks")

cur.execute("SELECT COUNT(*) as cnt FROM at_consensus_picks")
print("Row count:", cur.fetchone()["cnt"])

cols1, dcols1 = find_date_cols("at_consensus_picks")
show_date_ranges("at_consensus_picks", dcols1)

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
cur.execute("SELECT COUNT(*) as cnt FROM at_consensus_picks WHERE closed_at IS NOT NULL")
print("Has closed_at:", cur.fetchone()["cnt"])

cur.execute("SELECT * FROM at_consensus_picks ORDER BY generated_at DESC LIMIT 3")
print("\nMost recent 3:")
for r in cur.fetchall():
    print("  id=%s symbol=%s dir=%s status=%s pnl=%s entry=%s exit=%s gen=%s" % (
        str(r.get("id",""))[:8], r.get("symbol"), r.get("direction"), r.get("status"),
        r.get("pnl_pct"), r.get("entry_price"), r.get("exit_price"), r.get("generated_at")))

cur.execute("""
    SELECT symbol, direction, DATE(generated_at) as dt, COUNT(*) as cnt
    FROM at_consensus_picks
    GROUP BY symbol, direction, DATE(generated_at)
    HAVING cnt > 3
    ORDER BY cnt DESC
    LIMIT 10
""")
dupes = cur.fetchall()
print("\nDuplicate groups (same symbol+direction+date, >3/day): %d" % len(dupes))
for d in dupes[:5]:
    print("  %s %s on %s: %s rows" % (d["symbol"], d["direction"], d["dt"], d["cnt"]))

# Consensus tier distribution
cur.execute("SELECT consensus_tier, COUNT(*) as cnt FROM at_consensus_picks GROUP BY consensus_tier ORDER BY cnt DESC")
print("\nConsensus tier distribution:")
for r in cur.fetchall():
    print("  %s: %s" % (r["consensus_tier"], r["cnt"]))

# Asset class
cur.execute("SELECT asset_class, COUNT(*) as cnt FROM at_consensus_picks GROUP BY asset_class ORDER BY cnt DESC")
print("\nAsset class distribution:")
for r in cur.fetchall():
    print("  %s: %s" % (r["asset_class"], r["cnt"]))

# Entry price issues
cur.execute("SELECT COUNT(*) as cnt FROM at_consensus_picks WHERE entry_price IS NULL OR entry_price = 0")
print("\nNULL/zero entry_price:", cur.fetchone()["cnt"])

cur.execute("SELECT COUNT(*) as cnt FROM at_consensus_picks WHERE confidence IS NULL")
print("NULL confidence:", cur.fetchone()["cnt"])

# ============================================================
# 2. at_raw_picks
# ============================================================
section("2. at_raw_picks")

cur.execute("SELECT COUNT(*) as cnt FROM at_raw_picks")
print("Row count:", cur.fetchone()["cnt"])

cols2, dcols2 = find_date_cols("at_raw_picks")
print("\nColumns:")
for c in cols2:
    print("  %-30s %-30s %-5s" % (c["Field"], c["Type"], c["Null"]))

show_date_ranges("at_raw_picks", dcols2)

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

# Use the correct date column
raw_date_col = dcols2[0] if dcols2 else "id"
cur.execute("""
    SELECT symbol, system_name, direction, DATE(`%s`) as dt, COUNT(*) as cnt
    FROM at_raw_picks
    GROUP BY symbol, system_name, direction, DATE(`%s`)
    HAVING cnt > 5
    ORDER BY cnt DESC
    LIMIT 10
""" % (raw_date_col, raw_date_col))
dupes = cur.fetchall()
print("\nHigh-freq duplicates (>5/day same symbol+system+dir): %d groups" % len(dupes))
for d in dupes[:5]:
    print("  %s / %s / %s on %s: %s rows" % (d["symbol"], d["system_name"], d["direction"], d["dt"], d["cnt"]))

cur.execute("SELECT * FROM at_raw_picks ORDER BY `%s` DESC LIMIT 3" % raw_date_col)
print("\nMost recent 3:")
for r in cur.fetchall():
    print("  id=%s sym=%s sys=%s status=%s entry=%s pnl=%s" % (
        str(r.get("id",""))[:8], r.get("symbol"), r.get("system_name"),
        r.get("status"), r.get("entry_price"), r.get("pnl_pct")))

# PnL tracking on raw picks
cur.execute("SELECT COUNT(*) as cnt FROM at_raw_picks WHERE pnl_pct IS NOT NULL AND pnl_pct != 0")
print("\nNon-zero pnl_pct:", cur.fetchone()["cnt"])
cur.execute("SELECT COUNT(*) as cnt FROM at_raw_picks WHERE exit_price IS NOT NULL")
print("Has exit_price:", cur.fetchone()["cnt"])

# ============================================================
# 3. at_signal_outcomes
# ============================================================
section("3. at_signal_outcomes")

cur.execute("SELECT COUNT(*) as cnt FROM at_signal_outcomes")
print("Row count:", cur.fetchone()["cnt"])

cols3, dcols3 = find_date_cols("at_signal_outcomes")
print("\nColumns:")
for c in cols3:
    print("  %-30s %-30s %-5s" % (c["Field"], c["Type"], c["Null"]))

show_date_ranges("at_signal_outcomes", dcols3)

cur.execute("SELECT outcome, COUNT(*) as cnt FROM at_signal_outcomes GROUP BY outcome ORDER BY cnt DESC")
print("\nOutcome distribution:")
for r in cur.fetchall():
    print("  %s: %s" % (r["outcome"], r["cnt"]))

try:
    cur.execute("SELECT AVG(pnl_pct) as avg_pnl, MIN(pnl_pct) as min_pnl, MAX(pnl_pct) as max_pnl, STDDEV(pnl_pct) as std_pnl FROM at_signal_outcomes WHERE pnl_pct IS NOT NULL")
    r = cur.fetchone()
    print("\nPnL stats: avg=%.4f, min=%.4f, max=%.4f, std=%.4f" % (
        float(r["avg_pnl"] or 0), float(r["min_pnl"] or 0),
        float(r["max_pnl"] or 0), float(r["std_pnl"] or 0)))
except:
    print("\nCould not compute PnL stats")

cur.execute("SELECT COUNT(*) as cnt FROM at_signal_outcomes WHERE pnl_pct IS NULL")
print("NULL pnl_pct:", cur.fetchone()["cnt"])

out_date_col = dcols3[0] if dcols3 else "id"
cur.execute("SELECT * FROM at_signal_outcomes ORDER BY `%s` DESC LIMIT 5" % out_date_col)
print("\nMost recent 5:")
for r in cur.fetchall():
    for k,v in r.items():
        val = str(v)[:60] if v is not None else "NULL"
        print("    %s: %s" % (k, val))
    print("  ---")

# system breakdown
try:
    cur.execute("SELECT system_name, COUNT(*) as cnt, AVG(pnl_pct) as avg_pnl FROM at_signal_outcomes GROUP BY system_name ORDER BY cnt DESC LIMIT 10")
    print("\nOutcomes by system:")
    for r in cur.fetchall():
        print("  %s: %s outcomes, avg_pnl=%.4f" % (r["system_name"], r["cnt"], float(r["avg_pnl"] or 0)))
except:
    pass

# ============================================================
# 4. at_discord_notifications
# ============================================================
section("4. at_discord_notifications")

cur.execute("SELECT COUNT(*) as cnt FROM at_discord_notifications")
print("Row count:", cur.fetchone()["cnt"])

cols4, dcols4 = find_date_cols("at_discord_notifications")
print("\nColumns:")
for c in cols4:
    print("  %-30s %-30s %-5s" % (c["Field"], c["Type"], c["Null"]))

show_date_ranges("at_discord_notifications", dcols4)

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

disc_date_col = dcols4[0] if dcols4 else "id"
cur.execute("SELECT * FROM at_discord_notifications ORDER BY `%s` DESC LIMIT 3" % disc_date_col)
print("\nMost recent 3:")
for r in cur.fetchall():
    msg = str(r.get("message",""))[:100] if r.get("message") else "NULL"
    print("  id=%s type=%s status=%s created=%s" % (
        r.get("id"), r.get("notification_type"), r.get("status"), r.get(disc_date_col)))
    print("    msg: %s..." % msg)

# Check for failed notifications
try:
    cur.execute("SELECT COUNT(*) as cnt FROM at_discord_notifications WHERE status = 'FAILED'")
    print("\nFailed notifications:", cur.fetchone()["cnt"])
except:
    pass

# Message length analysis
cur.execute("SELECT AVG(LENGTH(message)) as avg_len, MAX(LENGTH(message)) as max_len, MIN(LENGTH(message)) as min_len FROM at_discord_notifications WHERE message IS NOT NULL")
r = cur.fetchone()
print("Message length: avg=%.0f, max=%s, min=%s" % (float(r["avg_len"] or 0), r["max_len"], r["min_len"]))

# ============================================================
# 5. simulation_grid
# ============================================================
section("5. simulation_grid")

cur.execute("SELECT COUNT(*) as cnt FROM simulation_grid")
print("Row count:", cur.fetchone()["cnt"])

cols5, dcols5 = find_date_cols("simulation_grid")
print("\nColumns:")
for c in cols5:
    print("  %-30s %-30s %-5s" % (c["Field"], c["Type"], c["Null"]))

show_date_ranges("simulation_grid", dcols5)

cur.execute("SELECT * FROM simulation_grid LIMIT 3")
rows = cur.fetchall()
print("\nSample 3 rows:")
for r in rows:
    for k,v in r.items():
        val = str(v)[:80] if v is not None else "NULL"
        print("  %s: %s" % (k, val))
    print("  ---")

# NULLs per column
print("\nNULL counts per column:")
for col_info in cols5:
    col = col_info["Field"]
    cur.execute("SELECT COUNT(*) as cnt FROM simulation_grid WHERE `%s` IS NULL" % col)
    null_cnt = cur.fetchone()["cnt"]
    if null_cnt > 0:
        print("  %s: %s NULLs (of %s)" % (col, null_cnt, 5846))

cur.execute("SELECT COUNT(*) as total, COUNT(DISTINCT id) as distinct_ids FROM simulation_grid")
r = cur.fetchone()
print("\nTotal: %s, Distinct IDs: %s" % (r["total"], r["distinct_ids"]))

# Group by interesting columns
for col in ["strategy_name", "symbol", "asset_class", "status"]:
    try:
        cur.execute("SELECT `%s`, COUNT(*) as cnt FROM simulation_grid GROUP BY `%s` ORDER BY cnt DESC LIMIT 10" % (col, col))
        results = cur.fetchall()
        if results:
            print("\nTop %s values:" % col)
            for r in results:
                print("  %s: %s" % (r[col], r["cnt"]))
    except:
        pass

conn.close()
print("\n\nAudit complete.")
