import os
import mysql.connector
from decimal import Decimal

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

def get_cols(table):
    return [r['Field'] for r in run(f"DESCRIBE `{table}`")]

def find_date_col(cols):
    for c in cols:
        if 'created' in c or 'date' in c or 'time' in c or 'updated' in c or 'snapshot' in c or 'resolved' in c:
            return c
    return None

def safe_float(v):
    if v is None:
        return None
    if isinstance(v, Decimal):
        return float(v)
    return float(v)

# First, show all table schemas
header("SCHEMA DISCOVERY")
tables = [list(r.values())[0] for r in run("SHOW TABLES")]
for t in tables:
    cols = run(f"DESCRIBE `{t}`")
    print(f"\n{t}:")
    for c in cols:
        print(f"  {c['Field']} ({c['Type']}) {'NULL' if c['Null']=='YES' else 'NOT NULL'} {c['Key']} {c['Default'] or ''}")

# ============================================================
# TABLE 1: at_consensus_picks
# ============================================================
header("TABLE 1: at_consensus_picks")
cols = get_cols('at_consensus_picks')
print(f"Columns: {cols}")

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
print(f"entry_price <= 0 or NULL: {r['cnt']}")

# Find date column
date_col = None
for c in cols:
    if 'created' in c or 'timestamp' in c or 'date' in c or 'time' in c:
        date_col = c
        break
if date_col:
    r = run(f"SELECT MIN(`{date_col}`) as mn, MAX(`{date_col}`) as mx FROM at_consensus_picks")[0]
    print(f"\nDate range ({date_col}): {r['mn']} to {r['mx']}")
else:
    print(f"\nNo date column found in: {cols}")

# Duplicates
print("\nChecking duplicates (same symbol+direction, entry_price within 0.5%)...")
try:
    dups = run("""
        SELECT a.id as id1, b.id as id2, a.symbol, a.direction, a.entry_price, b.entry_price as ep2,
               ABS(a.entry_price - b.entry_price)/GREATEST(a.entry_price, 0.001) * 100 as pct_diff
        FROM at_consensus_picks a
        JOIN at_consensus_picks b ON a.symbol = b.symbol
            AND a.direction = b.direction
            AND a.id < b.id
            AND ABS(a.entry_price - b.entry_price)/GREATEST(a.entry_price, 0.001) < 0.5
        LIMIT 20
    """)
    print(f"Duplicate pairs found (<0.5% price diff): {len(dups)}")
    for d in dups[:10]:
        print(f"  IDs {d['id1']},{d['id2']}: {d['symbol']} {d['direction']} prices={d['entry_price']}/{d['ep2']} diff={safe_float(d['pct_diff']):.3f}%")
except Exception as e:
    print(f"  Duplicate check error: {e}")

# NULL counts
print("\nNULL counts for key fields:")
for col in cols:
    r = run(f"SELECT COUNT(*) as cnt FROM at_consensus_picks WHERE `{col}` IS NULL")[0]
    if r['cnt'] > 0:
        print(f"  {col}: {r['cnt']} NULLs")

# Impossible PnL
r = run("SELECT COUNT(*) as cnt FROM at_consensus_picks WHERE pnl_pct > 500 OR pnl_pct < -100")[0]
print(f"Impossible pnl_pct (>500% or <-100%): {r['cnt']}")
if r['cnt'] > 0:
    for e in run("SELECT id, symbol, pnl_pct FROM at_consensus_picks WHERE pnl_pct > 500 OR pnl_pct < -100 ORDER BY ABS(pnl_pct) DESC LIMIT 10"):
        print(f"  ID {e['id']}: {e['symbol']} pnl={e['pnl_pct']}%")

# Sample rows
print("\nSample rows (5):")
for r in run("SELECT * FROM at_consensus_picks LIMIT 5"):
    print(f"  {r}")

# ============================================================
# TABLE 2: at_raw_picks
# ============================================================
header("TABLE 2: at_raw_picks")
cols = get_cols('at_raw_picks')
print(f"Columns: {cols}")

rows = run("SELECT COUNT(*) as cnt FROM at_raw_picks")[0]['cnt']
print(f"Total rows: {rows}")

r = run("SELECT COUNT(*) as cnt FROM at_raw_picks WHERE entry_price <= 0 OR entry_price IS NULL")[0]
print(f"entry_price <= 0 or NULL: {r['cnt']}")

# Stale/banned
for flag in ['was_stale', 'was_banned', 'is_stale', 'is_banned', 'stale', 'banned']:
    if flag in cols:
        r = run(f"SELECT COUNT(*) as cnt FROM at_raw_picks WHERE `{flag}` = 1")[0]
        print(f"{flag}=1: {r['cnt']}")

# Date
date_col = find_date_col(cols)
if date_col:
    r = run(f"SELECT MIN(`{date_col}`) as mn, MAX(`{date_col}`) as mx FROM at_raw_picks")[0]
    print(f"Date range ({date_col}): {r['mn']} to {r['mx']}")

# Source distribution
if 'source_system' in cols:
    print("\nSource distribution:")
    for r in run("SELECT source_system, COUNT(*) as cnt FROM at_raw_picks GROUP BY source_system ORDER BY cnt DESC LIMIT 10"):
        print(f"  {r['source_system']}: {r['cnt']}")

# NULLs
print("\nNULL counts:")
for col in cols:
    r = run(f"SELECT COUNT(*) as cnt FROM at_raw_picks WHERE `{col}` IS NULL")[0]
    if r['cnt'] > 0:
        print(f"  {col}: {r['cnt']} NULLs")

# Duplicates
print("\nHigh-frequency duplicates (>3x same symbol+dir+price+source):")
try:
    src_col = 'source_system' if 'source_system' in cols else cols[0]
    dups = run(f"""
        SELECT symbol, direction, entry_price, `{src_col}`, COUNT(*) as cnt
        FROM at_raw_picks
        GROUP BY symbol, direction, entry_price, `{src_col}`
        HAVING cnt > 3
        ORDER BY cnt DESC LIMIT 10
    """)
    for d in dups:
        print(f"  {d['symbol']} {d['direction']} @{d['entry_price']} from {d[src_col]}: {d['cnt']}x")
except Exception as e:
    print(f"  Error: {e}")

# ============================================================
# TABLE 3: consensus_tracked
# ============================================================
header("TABLE 3: consensus_tracked")
cols = get_cols('consensus_tracked')
print(f"Columns: {cols}")

rows = run("SELECT COUNT(*) as cnt FROM consensus_tracked")[0]['cnt']
print(f"Total rows: {rows}")

print("\nStatus distribution:")
for r in run("SELECT status, COUNT(*) as cnt FROM consensus_tracked GROUP BY status ORDER BY cnt DESC"):
    print(f"  {r['status']}: {r['cnt']}")

# Zero exits
if 'exit_price' in cols:
    r = run("SELECT COUNT(*) as cnt FROM consensus_tracked WHERE exit_price = 0 AND status != 'OPEN'")[0]
    print(f"\nClosed with exit_price=0 (BAD): {r['cnt']}")
    if r['cnt'] > 0:
        for e in run("SELECT id, symbol, status, exit_price FROM consensus_tracked WHERE exit_price = 0 AND status != 'OPEN' LIMIT 5"):
            print(f"  {e}")

# Weekend exits
if 'exit_date' in cols:
    r = run("SELECT COUNT(*) as cnt FROM consensus_tracked WHERE DAYOFWEEK(exit_date) IN (1,7) AND status != 'OPEN'")[0]
    print(f"Closed on weekends: {r['cnt']}")

if 'entry_price' in cols:
    r = run("SELECT COUNT(*) as cnt FROM consensus_tracked WHERE entry_price <= 0 OR entry_price IS NULL")[0]
    print(f"entry_price <= 0 or NULL: {r['cnt']}")

# Return accuracy
print("\nSample open positions with return validation:")
open_rows = run("SELECT * FROM consensus_tracked WHERE status='OPEN' LIMIT 10")
for r in open_rows:
    ep = safe_float(r.get('entry_price'))
    cp = safe_float(r.get('current_price'))
    stored = safe_float(r.get('current_return_pct'))
    sym = r.get('symbol','?')
    d = str(r.get('direction','')).lower()
    if ep and cp and ep > 0:
        if 'short' in d or 'sell' in d:
            calc = (ep - cp) / ep * 100
        else:
            calc = (cp - ep) / ep * 100
        diff = abs((stored or 0) - calc)
        flag = " *** MISMATCH" if diff > 2.0 else ""
        print(f"  {sym} {d}: entry={ep} curr={cp} stored={stored}% calc={calc:.2f}%{flag}")

# Date range
date_col = find_date_col(cols)
if date_col:
    r = run(f"SELECT MIN(`{date_col}`) as mn, MAX(`{date_col}`) as mx FROM consensus_tracked")[0]
    print(f"\nDate range ({date_col}): {r['mn']} to {r['mx']}")

# Impossible returns
if 'current_return_pct' in cols:
    r = run("SELECT COUNT(*) as cnt FROM consensus_tracked WHERE current_return_pct > 500 OR current_return_pct < -100")[0]
    print(f"Impossible returns (>500% or <-100%): {r['cnt']}")

# ============================================================
# TABLE 4: pf_challenge_positions
# ============================================================
header("TABLE 4: pf_challenge_positions")
cols = get_cols('pf_challenge_positions')
print(f"Columns: {cols}")

rows = run("SELECT COUNT(*) as cnt FROM pf_challenge_positions")[0]['cnt']
print(f"Total rows: {rows}")

print("\nStatus distribution:")
for r in run("SELECT status, COUNT(*) as cnt FROM pf_challenge_positions GROUP BY status ORDER BY cnt DESC"):
    print(f"  {r['status']}: {r['cnt']}")

if 'entry_price' in cols:
    r = run("SELECT COUNT(*) as cnt FROM pf_challenge_positions WHERE entry_price <= 0 OR entry_price IS NULL")[0]
    print(f"entry_price <= 0 or NULL: {r['cnt']}")

if 'pnl_pct' in cols:
    print("\nPnL stats for closed:")
    r = run("""SELECT COUNT(*) cnt, AVG(pnl_pct) avg_pnl, MIN(pnl_pct) min_pnl, MAX(pnl_pct) max_pnl,
        SUM(CASE WHEN pnl_pct>0 THEN 1 ELSE 0 END) as wins
        FROM pf_challenge_positions WHERE status='closed'""")[0]
    if r['cnt'] and r['cnt'] > 0:
        print(f"  Closed: {r['cnt']}, Avg PnL: {safe_float(r['avg_pnl']):.2f}%, Min: {r['min_pnl']}%, Max: {r['max_pnl']}%, Wins: {r['wins']}")

# Date range
date_col = find_date_col(cols)
if date_col:
    r = run(f"SELECT MIN(`{date_col}`) as mn, MAX(`{date_col}`) as mx FROM pf_challenge_positions")[0]
    print(f"Date range ({date_col}): {r['mn']} to {r['mx']}")

# NULLs
print("\nNULL counts:")
for col in cols:
    r = run(f"SELECT COUNT(*) as cnt FROM pf_challenge_positions WHERE `{col}` IS NULL")[0]
    if r['cnt'] > 0:
        print(f"  {col}: {r['cnt']} NULLs")

# Portfolio distribution
if 'portfolio_id' in cols:
    print("\nPortfolio distribution:")
    for r in run("SELECT portfolio_id, COUNT(*) as cnt FROM pf_challenge_positions GROUP BY portfolio_id ORDER BY cnt DESC LIMIT 15"):
        print(f"  {r['portfolio_id']}: {r['cnt']}")

# ============================================================
# TABLE 5: portfolio_snapshots
# ============================================================
header("TABLE 5: portfolio_snapshots")
cols = get_cols('portfolio_snapshots')
print(f"Columns: {cols}")

rows = run("SELECT COUNT(*) as cnt FROM portfolio_snapshots")[0]['cnt']
print(f"Total rows: {rows}")

print("\nAll snapshots:")
for r in run("SELECT * FROM portfolio_snapshots ORDER BY 1 LIMIT 30"):
    print(f"  {r}")

# ============================================================
# TABLE 6: at_signal_outcomes
# ============================================================
header("TABLE 6: at_signal_outcomes")
cols = get_cols('at_signal_outcomes')
print(f"Columns: {cols}")

rows = run("SELECT COUNT(*) as cnt FROM at_signal_outcomes")[0]['cnt']
print(f"Total rows: {rows}")

print("\nOutcome distribution:")
for r in run("SELECT outcome, COUNT(*) as cnt FROM at_signal_outcomes GROUP BY outcome ORDER BY cnt DESC"):
    print(f"  {r['outcome']}: {r['cnt']}")

if 'pnl_pct' in cols:
    r = run("SELECT AVG(pnl_pct) avg_pnl, MIN(pnl_pct) min_pnl, MAX(pnl_pct) max_pnl, STDDEV(pnl_pct) std_pnl FROM at_signal_outcomes WHERE pnl_pct IS NOT NULL")[0]
    print(f"\nPnL stats: Avg={safe_float(r['avg_pnl']):.2f}%, Min={r['min_pnl']}%, Max={r['max_pnl']}%, StdDev={safe_float(r['std_pnl']):.2f}%")

    r = run("SELECT COUNT(*) as cnt FROM at_signal_outcomes WHERE pnl_pct > 500 OR pnl_pct < -100")[0]
    print(f"Impossible PnL (>500% or <-100%): {r['cnt']}")
    if r['cnt'] > 0:
        for e in run("SELECT id, symbol, pnl_pct, outcome FROM at_signal_outcomes WHERE pnl_pct > 500 OR pnl_pct < -100 LIMIT 10"):
            print(f"  {e}")

date_col = find_date_col(cols)
if date_col:
    r = run(f"SELECT MIN(`{date_col}`) as mn, MAX(`{date_col}`) as mx FROM at_signal_outcomes")[0]
    print(f"Date range ({date_col}): {r['mn']} to {r['mx']}")

print("\nNULL counts:")
for col in cols:
    r = run(f"SELECT COUNT(*) as cnt FROM at_signal_outcomes WHERE `{col}` IS NULL")[0]
    if r['cnt'] > 0:
        print(f"  {col}: {r['cnt']} NULLs")

# ============================================================
# TABLE 7: at_discord_notifications
# ============================================================
header("TABLE 7: at_discord_notifications")
cols = get_cols('at_discord_notifications')
print(f"Columns: {cols}")

rows = run("SELECT COUNT(*) as cnt FROM at_discord_notifications")[0]['cnt']
print(f"Total rows: {rows}")

print("\nEvent type distribution:")
for r in run("SELECT event_type, COUNT(*) as cnt FROM at_discord_notifications GROUP BY event_type ORDER BY cnt DESC"):
    print(f"  {r['event_type']}: {r['cnt']}")

if 'entry_price' in cols:
    r = run("SELECT COUNT(*) as cnt FROM at_discord_notifications WHERE entry_price IS NOT NULL AND entry_price <= 0")[0]
    print(f"\nentry_price <= 0 (non-null): {r['cnt']}")
    r = run("SELECT COUNT(*) as cnt FROM at_discord_notifications WHERE entry_price IS NULL")[0]
    print(f"entry_price NULL: {r['cnt']}")

date_col = find_date_col(cols)
if date_col:
    r = run(f"SELECT MIN(`{date_col}`) as mn, MAX(`{date_col}`) as mx FROM at_discord_notifications")[0]
    print(f"Date range ({date_col}): {r['mn']} to {r['mx']}")

# ============================================================
# TABLE 8: strategy_health
# ============================================================
header("TABLE 8: strategy_health")
cols = get_cols('strategy_health')
print(f"Columns: {cols}")

rows = run("SELECT COUNT(*) as cnt FROM strategy_health")[0]['cnt']
print(f"Total rows: {rows}")

print("\nAll rows:")
for r in run("SELECT * FROM strategy_health LIMIT 45"):
    print(f"  {r}")

# ============================================================
# FULL TABLE INVENTORY
# ============================================================
header("FULL TABLE INVENTORY")
for t in tables:
    cnt = run(f"SELECT COUNT(*) as c FROM `{t}`")[0]['c']
    print(f"  {t}: {cnt} rows")

conn.close()
print("\n" + "="*80)
print("  AUDIT COMPLETE")
print("="*80)
