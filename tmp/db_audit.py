import os
import mysql.connector
import json
from datetime import datetime, timedelta

conn = mysql.connector.connect(
    host="mysql.50webs.com",
    user="ejaguiar1_stocks",
    password=os.environ.get("DB_PASS_STOCKS",""), database="ejaguiar1_stocks"
)
cur = conn.cursor(dictionary=True)

def header(title):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}")

def run(sql, params=None):
    cur.execute(sql, params or ())
    return cur.fetchall()

# ============================================================
# TABLE 1: at_consensus_picks
# ============================================================
header("TABLE 1: at_consensus_picks")

rows = run("SELECT COUNT(*) as cnt FROM at_consensus_picks")[0]['cnt']
print(f"Total rows: {rows}")

r = run("SELECT COUNT(*) as cnt FROM at_consensus_picks WHERE pnl_pct IS NOT NULL")[0]
print(f"Rows with pnl_pct NOT NULL: {r['cnt']}")
r = run("SELECT COUNT(*) as cnt FROM at_consensus_picks WHERE pnl_pct IS NULL")[0]
print(f"Rows with pnl_pct NULL: {r['cnt']}")

print("\nStatus distribution:")
for r in run("SELECT status, COUNT(*) as cnt FROM at_consensus_picks GROUP BY status ORDER BY cnt DESC"):
    print(f"  {r['status']}: {r['cnt']}")

r = run("SELECT COUNT(*) as cnt FROM at_consensus_picks WHERE status='OPEN' AND pnl_pct IS NULL")[0]
print(f"\nOPEN with no pnl_pct: {r['cnt']}")

r = run("SELECT COUNT(*) as cnt FROM at_consensus_picks WHERE entry_price <= 0 OR entry_price IS NULL")[0]
print(f"Rows with entry_price <= 0 or NULL: {r['cnt']}")
r = run("SELECT COUNT(*) as cnt FROM at_consensus_picks WHERE entry_price > 1000000")[0]
print(f"Rows with entry_price > 1M (suspicious unless BTC): {r['cnt']}")

r = run("SELECT MIN(created_at) as mn, MAX(created_at) as mx FROM at_consensus_picks")[0]
print(f"\nDate range: {r['mn']} to {r['mx']}")
print(f"Latest entry: {r['mx']}")

print("\nChecking duplicates (same symbol+direction, entry_price within 0.5%, within 24h)...")
dups = run("""
    SELECT a.id as id1, b.id as id2, a.symbol, a.direction, a.entry_price, b.entry_price as ep2,
           ABS(a.entry_price - b.entry_price)/GREATEST(a.entry_price, 0.001) * 100 as pct_diff
    FROM at_consensus_picks a
    JOIN at_consensus_picks b ON a.symbol = b.symbol
        AND a.direction = b.direction
        AND a.id < b.id
        AND ABS(a.entry_price - b.entry_price)/GREATEST(a.entry_price, 0.001) < 0.5
        AND ABS(TIMESTAMPDIFF(HOUR, a.created_at, b.created_at)) < 24
    LIMIT 20
""")
print(f"Duplicate pairs found (within 24h, <0.5% price diff): {len(dups)}")
for d in dups[:10]:
    print(f"  IDs {d['id1']},{d['id2']}: {d['symbol']} {d['direction']} prices={d['entry_price']}/{d['ep2']} diff={float(d['pct_diff']):.3f}%")

print("\nNULL counts for key fields:")
for col in ['symbol','direction','entry_price','target_price','stop_price','status','created_at']:
    r = run(f"SELECT COUNT(*) as cnt FROM at_consensus_picks WHERE `{col}` IS NULL")[0]
    if r['cnt'] > 0:
        print(f"  {col}: {r['cnt']} NULLs")

r = run("SELECT COUNT(*) as cnt FROM at_consensus_picks WHERE pnl_pct > 500 OR pnl_pct < -100")[0]
print(f"Impossible pnl_pct (>500% or <-100%): {r['cnt']}")
if r['cnt'] > 0:
    extremes = run("SELECT id, symbol, pnl_pct FROM at_consensus_picks WHERE pnl_pct > 500 OR pnl_pct < -100 ORDER BY pnl_pct DESC LIMIT 5")
    for e in extremes:
        print(f"  ID {e['id']}: {e['symbol']} pnl={e['pnl_pct']}%")

# ============================================================
# TABLE 2: at_raw_picks
# ============================================================
header("TABLE 2: at_raw_picks")

rows = run("SELECT COUNT(*) as cnt FROM at_raw_picks")[0]['cnt']
print(f"Total rows: {rows}")

r = run("SELECT COUNT(*) as cnt FROM at_raw_picks WHERE entry_price <= 0 OR entry_price IS NULL")[0]
print(f"Rows with entry_price <= 0 or NULL: {r['cnt']}")

try:
    r = run("SELECT COUNT(*) as cnt FROM at_raw_picks WHERE was_stale = 1")[0]
    print(f"was_stale=1: {r['cnt']}")
except Exception as e:
    print(f"was_stale check: {e}")

try:
    r2 = run("SELECT COUNT(*) as cnt FROM at_raw_picks WHERE was_banned = 1")[0]
    print(f"was_banned=1: {r2['cnt']}")
except Exception as e:
    print(f"was_banned check: {e}")

r = run("SELECT MIN(created_at) as mn, MAX(created_at) as mx FROM at_raw_picks")[0]
print(f"Date range: {r['mn']} to {r['mx']}")

print("\nSource distribution (top 10):")
for r in run("SELECT source_system, COUNT(*) as cnt FROM at_raw_picks GROUP BY source_system ORDER BY cnt DESC LIMIT 10"):
    print(f"  {r['source_system']}: {r['cnt']}")

print("\nNULL counts for key fields:")
for col in ['symbol','direction','entry_price','source_system','created_at']:
    r = run(f"SELECT COUNT(*) as cnt FROM at_raw_picks WHERE `{col}` IS NULL")[0]
    if r['cnt'] > 0:
        print(f"  {col}: {r['cnt']} NULLs")

dups = run("""
    SELECT symbol, direction, entry_price, source_system, COUNT(*) as cnt
    FROM at_raw_picks
    GROUP BY symbol, direction, entry_price, source_system
    HAVING cnt > 3
    ORDER BY cnt DESC LIMIT 10
""")
print(f"\nHigh-frequency duplicates (same symbol+dir+price+source, >3x):")
for d in dups[:10]:
    print(f"  {d['symbol']} {d['direction']} @{d['entry_price']} from {d['source_system']}: {d['cnt']}x")

# ============================================================
# TABLE 3: consensus_tracked
# ============================================================
header("TABLE 3: consensus_tracked")

rows = run("SELECT COUNT(*) as cnt FROM consensus_tracked")[0]['cnt']
print(f"Total rows: {rows}")

print("\nStatus distribution:")
for r in run("SELECT status, COUNT(*) as cnt FROM consensus_tracked GROUP BY status ORDER BY cnt DESC"):
    print(f"  {r['status']}: {r['cnt']}")

r = run("SELECT COUNT(*) as cnt FROM consensus_tracked WHERE exit_price = 0 AND status != 'OPEN'")[0]
print(f"\nClosed with exit_price=0 (BAD): {r['cnt']}")

try:
    r = run("SELECT COUNT(*) as cnt FROM consensus_tracked WHERE DAYOFWEEK(exit_date) IN (1,7) AND status != 'OPEN'")[0]
    print(f"Closed on weekends (suspicious for stocks): {r['cnt']}")
except Exception as e:
    print(f"Weekend check: {e}")

r = run("SELECT COUNT(*) as cnt FROM consensus_tracked WHERE entry_price <= 0 OR entry_price IS NULL")[0]
print(f"entry_price <= 0 or NULL: {r['cnt']}")

print("\nSample open positions with return validation:")
for r in run("SELECT symbol, direction, entry_price, current_price, current_return_pct FROM consensus_tracked WHERE status='OPEN' LIMIT 10"):
    ep = float(r['entry_price']) if r['entry_price'] else 0
    cp = float(r['current_price']) if r['current_price'] else 0
    stored = float(r['current_return_pct']) if r['current_return_pct'] else 0
    if ep > 0 and cp > 0:
        d = str(r['direction']).lower() if r['direction'] else ''
        if 'short' in d or 'sell' in d:
            calc = (ep - cp) / ep * 100
        else:
            calc = (cp - ep) / ep * 100
        diff = abs(stored - calc)
        flag = " *** MISMATCH" if diff > 1.0 else ""
        print(f"  {r['symbol']} {r['direction']}: entry={ep} curr={cp} stored={stored:.2f}% calc={calc:.2f}% diff={diff:.2f}%{flag}")

try:
    r = run("SELECT MIN(entry_date) as mn, MAX(entry_date) as mx FROM consensus_tracked")[0]
    print(f"\nDate range: {r['mn']} to {r['mx']}")
except:
    r = run("SELECT MIN(created_at) as mn, MAX(created_at) as mx FROM consensus_tracked")[0]
    print(f"\nDate range: {r['mn']} to {r['mx']}")

r = run("SELECT COUNT(*) as cnt FROM consensus_tracked WHERE current_return_pct > 500 OR current_return_pct < -100")[0]
print(f"Impossible returns (>500% or <-100%): {r['cnt']}")
if r['cnt'] > 0:
    for e in run("SELECT id, symbol, current_return_pct FROM consensus_tracked WHERE current_return_pct > 500 OR current_return_pct < -100 LIMIT 5"):
        print(f"  ID {e['id']}: {e['symbol']} ret={e['current_return_pct']}%")

# ============================================================
# TABLE 4: pf_challenge_positions
# ============================================================
header("TABLE 4: pf_challenge_positions")

rows = run("SELECT COUNT(*) as cnt FROM pf_challenge_positions")[0]['cnt']
print(f"Total rows: {rows}")

print("\nStatus distribution:")
for r in run("SELECT status, COUNT(*) as cnt FROM pf_challenge_positions GROUP BY status ORDER BY cnt DESC"):
    print(f"  {r['status']}: {r['cnt']}")

r = run("SELECT COUNT(*) as cnt FROM pf_challenge_positions WHERE entry_price <= 0 OR entry_price IS NULL")[0]
print(f"entry_price <= 0 or NULL: {r['cnt']}")

print("\nPnL stats for closed positions:")
r = run("""SELECT COUNT(*) cnt, AVG(pnl_pct) avg_pnl, MIN(pnl_pct) min_pnl, MAX(pnl_pct) max_pnl,
    SUM(CASE WHEN pnl_pct>0 THEN 1 ELSE 0 END) as wins
    FROM pf_challenge_positions WHERE status='closed'""")[0]
if r['cnt'] and r['cnt'] > 0:
    avg = float(r['avg_pnl']) if r['avg_pnl'] else 0
    print(f"  Closed: {r['cnt']}, Avg PnL: {avg:.2f}%, Min: {r['min_pnl']}%, Max: {r['max_pnl']}%, Wins: {r['wins']}")

try:
    r = run("SELECT MIN(entry_time) as mn, MAX(entry_time) as mx FROM pf_challenge_positions")[0]
    print(f"Date range: {r['mn']} to {r['mx']}")
except:
    pass

print("\nNULL counts:")
for col in ['symbol','direction','entry_price','status','portfolio_id','pnl_pct']:
    try:
        r2 = run(f"SELECT COUNT(*) as cnt FROM pf_challenge_positions WHERE `{col}` IS NULL")[0]
        if r2['cnt'] > 0:
            print(f"  {col}: {r2['cnt']} NULLs")
    except:
        pass

# Portfolio distribution
print("\nPortfolio distribution:")
for r in run("SELECT portfolio_id, COUNT(*) as cnt FROM pf_challenge_positions GROUP BY portfolio_id ORDER BY cnt DESC LIMIT 10"):
    print(f"  {r['portfolio_id']}: {r['cnt']}")

# ============================================================
# TABLE 5: portfolio_snapshots
# ============================================================
header("TABLE 5: portfolio_snapshots")

rows = run("SELECT COUNT(*) as cnt FROM portfolio_snapshots")[0]['cnt']
print(f"Total rows: {rows}")

print("\nAll snapshots:")
for r in run("SELECT * FROM portfolio_snapshots ORDER BY snapshot_time DESC LIMIT 30"):
    print(f"  {r}")

# ============================================================
# TABLE 6: at_signal_outcomes
# ============================================================
header("TABLE 6: at_signal_outcomes")

rows = run("SELECT COUNT(*) as cnt FROM at_signal_outcomes")[0]['cnt']
print(f"Total rows: {rows}")

print("\nOutcome distribution:")
for r in run("SELECT outcome, COUNT(*) as cnt FROM at_signal_outcomes GROUP BY outcome ORDER BY cnt DESC"):
    print(f"  {r['outcome']}: {r['cnt']}")

r = run("SELECT AVG(pnl_pct) avg_pnl, MIN(pnl_pct) min_pnl, MAX(pnl_pct) max_pnl, STDDEV(pnl_pct) std_pnl FROM at_signal_outcomes WHERE pnl_pct IS NOT NULL")[0]
avg = float(r['avg_pnl']) if r['avg_pnl'] else 0
std = float(r['std_pnl']) if r['std_pnl'] else 0
print(f"\nPnL stats: Avg={avg:.2f}%, Min={r['min_pnl']}%, Max={r['max_pnl']}%, StdDev={std:.2f}%")

r = run("SELECT COUNT(*) as cnt FROM at_signal_outcomes WHERE pnl_pct > 500 OR pnl_pct < -100")[0]
print(f"Impossible PnL (>500% or <-100%): {r['cnt']}")

r = run("SELECT MIN(resolved_at) as mn, MAX(resolved_at) as mx FROM at_signal_outcomes")[0]
print(f"Date range: {r['mn']} to {r['mx']}")

print("\nNULL counts:")
for col in ['symbol','outcome','pnl_pct','resolved_at']:
    r2 = run(f"SELECT COUNT(*) as cnt FROM at_signal_outcomes WHERE `{col}` IS NULL")[0]
    if r2['cnt'] > 0:
        print(f"  {col}: {r2['cnt']} NULLs")

# ============================================================
# TABLE 7: at_discord_notifications
# ============================================================
header("TABLE 7: at_discord_notifications")

rows = run("SELECT COUNT(*) as cnt FROM at_discord_notifications")[0]['cnt']
print(f"Total rows: {rows}")

print("\nEvent type distribution:")
for r in run("SELECT event_type, COUNT(*) as cnt FROM at_discord_notifications GROUP BY event_type ORDER BY cnt DESC"):
    print(f"  {r['event_type']}: {r['cnt']}")

r = run("SELECT COUNT(*) as cnt FROM at_discord_notifications WHERE entry_price IS NOT NULL AND entry_price <= 0")[0]
print(f"\nentry_price <= 0 (non-null): {r['cnt']}")
r = run("SELECT COUNT(*) as cnt FROM at_discord_notifications WHERE entry_price IS NULL")[0]
print(f"entry_price NULL: {r['cnt']}")

r = run("SELECT MIN(created_at) as mn, MAX(created_at) as mx FROM at_discord_notifications")[0]
print(f"Date range: {r['mn']} to {r['mx']}")

# ============================================================
# TABLE 8: strategy_health
# ============================================================
header("TABLE 8: strategy_health")

rows = run("SELECT COUNT(*) as cnt FROM strategy_health")[0]['cnt']
print(f"Total rows: {rows}")

print("\nSample data (first 10):")
sample = run("SELECT * FROM strategy_health LIMIT 10")
if sample:
    cols = list(sample[0].keys())
    print(f"  Columns: {cols}")
    for r in sample:
        print(f"  {r}")

try:
    r = run("SELECT MIN(updated_at) as mn, MAX(updated_at) as mx FROM strategy_health")[0]
    print(f"\nDate range: {r['mn']} to {r['mx']}")
except:
    pass

# ============================================================
# CROSS-TABLE INTEGRITY + FULL TABLE LIST
# ============================================================
header("CROSS-TABLE INTEGRITY + FULL TABLE LIST")

print("All tables in database:")
for r in run("SHOW TABLES"):
    tbl = list(r.values())[0]
    cnt = run(f"SELECT COUNT(*) as c FROM `{tbl}`")[0]['c']
    print(f"  {tbl}: {cnt} rows")

conn.close()
print("\n" + "="*80)
print("  AUDIT COMPLETE")
print("="*80)
