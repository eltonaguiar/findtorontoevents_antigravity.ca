import os
import mysql.connector

conn = mysql.connector.connect(
    host="mysql.50webs.com",
    user="ejaguiar1_stocks",
    password=os.environ.get("DB_PASS_STOCKS",""), database="ejaguiar1_stocks"
)
cur = conn.cursor(dictionary=True)

print("=== CRITICAL: at_raw_picks audit_trail_local duplicates ===")
cur.execute("""
    SELECT symbol, direction, COUNT(*) as cnt,
           MIN(recorded_at) as first, MAX(recorded_at) as last
    FROM at_raw_picks
    WHERE source_system = 'audit_trail_local' AND DATE(recorded_at) = '2026-03-10'
    GROUP BY symbol, direction
    ORDER BY cnt DESC
    LIMIT 10
""")
for r in cur.fetchall():
    print("  %s %s: %d rows (from %s to %s)" % (r["symbol"], r["direction"], r["cnt"], r["first"], r["last"]))

print("\n=== Total rows per day ===")
cur.execute("""
    SELECT DATE(recorded_at) as dt, COUNT(*) as cnt
    FROM at_raw_picks
    GROUP BY DATE(recorded_at)
    ORDER BY dt
""")
for r in cur.fetchall():
    print("  %s: %s rows" % (r["dt"], r["cnt"]))

print("\n=== at_consensus_picks per day ===")
cur.execute("""
    SELECT DATE(generated_at) as dt, COUNT(*) as cnt
    FROM at_consensus_picks
    GROUP BY DATE(generated_at)
    ORDER BY dt
""")
for r in cur.fetchall():
    print("  %s: %s rows" % (r["dt"], r["cnt"]))

print("\n=== discord: NULL discord_message_id but has webhook ===")
cur.execute("SELECT COUNT(*) as cnt FROM at_discord_notifications WHERE discord_message_id IS NOT NULL AND discord_message_id != ''")
print("  Has discord_message_id:", cur.fetchone()["cnt"])
cur.execute("SELECT COUNT(*) as cnt FROM at_discord_notifications WHERE discord_webhook IS NOT NULL AND discord_webhook != ''")
print("  Has discord_webhook:", cur.fetchone()["cnt"])
cur.execute("SELECT COUNT(*) as cnt FROM at_discord_notifications WHERE payload IS NULL")
print("  NULL payload:", cur.fetchone()["cnt"])

print("\n=== discord: COMBO_FINDINGS sample ===")
cur.execute("SELECT payload FROM at_discord_notifications WHERE event_type = 'COMBO_FINDINGS' ORDER BY created_at DESC LIMIT 3")
for r in cur.fetchall():
    print("  %s" % str(r["payload"])[:120])

print("\n=== signal_outcomes: OPEN with pnl=0 (stale) ===")
cur.execute("SELECT COUNT(*) as cnt FROM at_signal_outcomes WHERE outcome = 'OPEN' AND (pnl_pct = 0 OR pnl_pct IS NULL)")
print("  OPEN with zero/null PnL:", cur.fetchone()["cnt"])
cur.execute("SELECT MAX(opened_at) as latest FROM at_signal_outcomes WHERE outcome = 'OPEN'")
print("  Latest OPEN signal:", cur.fetchone()["latest"])

print("\n=== simulation_grid: sharpe = -9999 count ===")
cur.execute("SELECT COUNT(*) as cnt FROM simulation_grid WHERE sharpe_ratio <= -9999")
print("  Sharpe = -9999:", cur.fetchone()["cnt"])
cur.execute("SELECT COUNT(*) as cnt FROM simulation_grid WHERE profit_factor = 0")
print("  profit_factor = 0:", cur.fetchone()["cnt"])
cur.execute("SELECT COUNT(*) as cnt FROM simulation_grid WHERE total_return_pct < 0")
print("  Negative total_return:", cur.fetchone()["cnt"])
cur.execute("SELECT COUNT(*) as cnt FROM simulation_grid WHERE total_return_pct >= 0")
print("  Positive total_return:", cur.fetchone()["cnt"])

print("\n=== simulation_grid: algorithm distribution ===")
cur.execute("SELECT algorithm, COUNT(*) as cnt FROM simulation_grid GROUP BY algorithm ORDER BY cnt DESC LIMIT 15")
for r in cur.fetchall():
    print("  %s: %s" % (r["algorithm"], r["cnt"]))

print("\n=== simulation_grid: direction distribution ===")
cur.execute("SELECT direction, COUNT(*) as cnt FROM simulation_grid GROUP BY direction")
for r in cur.fetchall():
    print("  %s: %s" % (r["direction"], r["cnt"]))

print("\n=== simulation_grid: regime distribution ===")
cur.execute("SELECT regime, COUNT(*) as cnt FROM simulation_grid GROUP BY regime")
for r in cur.fetchall():
    print("  %s: %s" % (r["regime"], r["cnt"]))

conn.close()
print("\nDone.")
