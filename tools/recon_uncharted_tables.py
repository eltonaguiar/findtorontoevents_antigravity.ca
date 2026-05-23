"""Read-only reconnaissance of uncharted DB table families.

Covers: memecoin, mutual fund (mf_/mf2_), goldmine (gm_), penny stock,
crypto whale (crypto_whale_/cr_), forex pro (fxp_).

Outputs: JSON to stdout. Caller materializes the markdown report.
"""
import os, json, sys
from datetime import datetime

os.environ['AUDIT_DB_HOST']='mysql.50webs.com'
os.environ['AUDIT_DB_USER']='ejaguiar1_stocks'
os.environ['AUDIT_DB_PASS']='stocks'
os.environ['AUDIT_DB_NAME']='ejaguiar1_stocks'

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from audit_trail.mysql_client import _create_connection

c = _create_connection()
cur = c.cursor()
cur.execute("SET SESSION MAX_EXECUTION_TIME=120000")

# 1) Inventory tables per family via INFORMATION_SCHEMA
families = {
    'memecoin_explicit': ['meme_signals','meme_signal_results','meme_ml_models','meme_ml_predictions','mc_winners'],
    'penny_explicit': ['penny_picks','penny_picks_daily','penny_stocks'],
}
prefix_families = {
    'mutual_fund_v1': 'mf_',
    'mutual_fund_v2': 'mf2_',
    'goldmine': 'gm_',
    'crypto_whale_long': 'crypto_whale_',
    'crypto_whale_short': 'cr_',
    'forex_pro': 'fxp_',
}

inventory = {}

for fam, names in families.items():
    inventory[fam] = []
    for n in names:
        cur.execute(
            "SELECT TABLE_NAME, TABLE_ROWS FROM INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s", ('ejaguiar1_stocks', n))
        r = cur.fetchone()
        if r: inventory[fam].append({'table': r[0], 'approx_rows': r[1]})
        else: inventory[fam].append({'table': n, 'approx_rows': None, 'missing': True})

for fam, prefix in prefix_families.items():
    cur.execute(
        "SELECT TABLE_NAME, TABLE_ROWS FROM INFORMATION_SCHEMA.TABLES "
        "WHERE TABLE_SCHEMA=%s AND TABLE_NAME LIKE %s ORDER BY TABLE_NAME",
        ('ejaguiar1_stocks', prefix + '%'))
    rows = cur.fetchall()
    # exclude mf2_ from mf_ (LIKE 'mf_%' matches mf2_too); strip mf2 dups from mutual_fund_v1
    if fam == 'mutual_fund_v1':
        rows = [r for r in rows if not r[0].startswith('mf2_')]
    if fam == 'crypto_whale_short':
        rows = [r for r in rows if not r[0].startswith('crypto_whale_')]
    inventory[fam] = [{'table': r[0], 'approx_rows': r[1]} for r in rows]


def col_list(table):
    cur.execute("SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s ORDER BY ORDINAL_POSITION",
                ('ejaguiar1_stocks', table))
    return cur.fetchall()


def exact_count(table):
    try:
        cur.execute(f"SELECT COUNT(*) FROM `{table}`")
        return cur.fetchone()[0]
    except Exception as e:
        return f"ERR: {e}"


def last_written(table, cols):
    cnames = [c[0].lower() for c in cols]
    candidates = ['updated_at','created_at','closed_at','timestamp','signal_time',
                  'date','last_update','inserted_at','as_of','as_of_date','prediction_date',
                  'fetched_at','picked_at','generated_at','signal_date']
    for cand in candidates:
        if cand in cnames:
            real = next(c[0] for c in cols if c[0].lower()==cand)
            try:
                cur.execute(f"SELECT MAX(`{real}`) FROM `{table}`")
                v = cur.fetchone()[0]
                if v is not None:
                    return real, str(v)
            except Exception as e:
                continue
    return None, None


def sample_rows(table, n=3):
    try:
        cur.execute(f"SELECT * FROM `{table}` LIMIT {n}")
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        return cols, [[(str(v)[:60] if v is not None else None) for v in r] for r in rows]
    except Exception as e:
        return [], [[f"ERR: {e}"]]


report = {'inventory': inventory, 'detail': {}}

# detailed per-table
for fam, tbls in inventory.items():
    report['detail'][fam] = []
    for t in tbls:
        if t.get('missing'):
            report['detail'][fam].append({'table': t['table'], 'missing': True})
            continue
        name = t['table']
        cols = col_list(name)
        ec = exact_count(name)
        lw_col, lw_val = last_written(name, cols)
        scols, srows = sample_rows(name, 3)
        entry = {
            'table': name,
            'columns': [{'name': c[0], 'type': c[1]} for c in cols],
            'exact_count': ec,
            'last_written_col': lw_col,
            'last_written_at': lw_val,
            'sample_cols': scols,
            'sample_rows': srows,
        }
        # status enum distribution if present
        cnames = [c[0].lower() for c in cols]
        if 'status' in cnames:
            try:
                cur.execute(f"SELECT `status`, COUNT(*) FROM `{name}` GROUP BY `status` ORDER BY 2 DESC LIMIT 20")
                entry['status_dist'] = [(str(r[0]), r[1]) for r in cur.fetchall()]
            except Exception as e:
                entry['status_dist'] = f"ERR: {e}"
        report['detail'][fam].append(entry)

# Family-specific drilldowns

# Memecoin: meme_signals 1m38s ghost interval check
try:
    cur.execute("SELECT COUNT(*) FROM meme_signals WHERE TIMESTAMPDIFF(SECOND, created_at, closed_at)=98")
    report['memecoin_98s_ghosts'] = cur.fetchone()[0]
except Exception as e:
    report['memecoin_98s_ghosts'] = f"ERR: {e}"

try:
    cur.execute("""SELECT TIMESTAMPDIFF(SECOND, created_at, closed_at) AS dt, COUNT(*)
                   FROM meme_signals WHERE closed_at IS NOT NULL
                   GROUP BY dt ORDER BY 2 DESC LIMIT 10""")
    report['memecoin_close_interval_dist'] = [(r[0], r[1]) for r in cur.fetchall()]
except Exception as e:
    report['memecoin_close_interval_dist'] = f"ERR: {e}"

# Mutual fund schema diff
def schema_set(t):
    cs = col_list(t)
    return set((c[0].lower(), c[1].lower()) for c in cs)

try:
    s1 = schema_set('mf_nav_history')
    s2 = schema_set('mf2_nav_history')
    report['mf_schema_diff'] = {
        'mf_nav_history_only': sorted(list(s1 - s2)),
        'mf2_nav_history_only': sorted(list(s2 - s1)),
        'shared': sorted(list(s1 & s2)),
    }
except Exception as e:
    report['mf_schema_diff'] = f"ERR: {e}"

# Penny: 0-PnL phantom check
for t in ['penny_picks','penny_picks_daily','penny_stocks']:
    try:
        cur.execute(f"SELECT COUNT(*) FROM `{t}`")
        n = cur.fetchone()[0]
        # try common pnl-ish columns
        cs = [x[0] for x in col_list(t)]
        for pc in ('pnl_pct','pnl','realized_pnl','return_pct'):
            if pc in [c.lower() for c in cs]:
                real = next(c for c in cs if c.lower()==pc)
                cur.execute(f"SELECT COUNT(*) FROM `{t}` WHERE `{real}`=0")
                report.setdefault('penny_zero_pnl', {})[t] = {'col': real, 'zeros': cur.fetchone()[0], 'total': n}
                break
    except Exception as e:
        report.setdefault('penny_zero_pnl', {})[t] = f"ERR: {e}"

print(json.dumps(report, indent=2, default=str))
c.close()
