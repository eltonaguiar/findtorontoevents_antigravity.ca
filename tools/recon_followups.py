"""Read-only follow-ups for uncharted recon."""
import os, json, sys
os.environ['AUDIT_DB_HOST']='mysql.50webs.com'
os.environ['AUDIT_DB_USER']='ejaguiar1_stocks'
os.environ['AUDIT_DB_PASS']='stocks'
os.environ['AUDIT_DB_NAME']='ejaguiar1_stocks'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from audit_trail.mysql_client import _create_connection
c=_create_connection(); cur=c.cursor()
cur.execute("SET SESSION MAX_EXECUTION_TIME=120000")

out = {}

# --- 1) Memecoin: full DDL of meme_signals + meme_signal_results, plus all timestamp cols
def cols(t):
    cur.execute("SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s ORDER BY ORDINAL_POSITION", ('ejaguiar1_stocks', t))
    return cur.fetchall()

out['meme_signals_cols'] = cols('meme_signals')
out['meme_signal_results_cols'] = cols('meme_signal_results')
out['mc_winners_cols'] = cols('mc_winners')

# Sample meme_signal_results
cur.execute("SELECT * FROM meme_signal_results LIMIT 3")
out['meme_signal_results_sample_cols'] = [d[0] for d in cur.description]
out['meme_signal_results_sample_rows'] = [[(str(v)[:80] if v is not None else None) for v in r] for r in cur.fetchall()]

# Find timestamp cols on meme_signals + check fingerprint
ts_cols = [c[0] for c in out['meme_signals_cols'] if 'date' in c[1].lower() or 'time' in c[1].lower() or 'timestamp' in c[0].lower() or c[0].endswith('_at')]
out['meme_signals_ts_cols'] = ts_cols

# Try interval check on entry_time/exit_time or signal_time/result_time
def try_interval(c1, c2):
    try:
        cur.execute(f"SELECT TIMESTAMPDIFF(SECOND, `{c1}`, `{c2}`) AS dt, COUNT(*) FROM meme_signals WHERE `{c2}` IS NOT NULL GROUP BY dt ORDER BY 2 DESC LIMIT 10")
        return [(r[0], r[1]) for r in cur.fetchall()]
    except Exception as e:
        return f"ERR: {e}"

# Check status enum on meme_signals and meme_signal_results
for tbl in ['meme_signals','meme_signal_results']:
    try:
        cur.execute(f"SELECT `status`, COUNT(*) FROM `{tbl}` GROUP BY `status` ORDER BY 2 DESC LIMIT 10")
        out[f'{tbl}_status'] = [(str(r[0]), r[1]) for r in cur.fetchall()]
    except Exception as e:
        out[f'{tbl}_status'] = f"ERR: {e}"

# Check distinct symbols / signal_type fingerprint
try:
    cur.execute("SELECT COUNT(DISTINCT symbol), COUNT(*) FROM meme_signals")
    out['meme_signals_distinct_symbols'] = cur.fetchone()
except Exception as e:
    out['meme_signals_distinct_symbols'] = f"ERR: {e}"

# Check return_pct distribution to confirm fixture-pattern (canned values)
try:
    cur.execute("SELECT return_pct, COUNT(*) FROM meme_signal_results GROUP BY return_pct ORDER BY 2 DESC LIMIT 10")
    out['meme_signal_results_return_pct_dist'] = [(str(r[0]), r[1]) for r in cur.fetchall()]
except Exception as e:
    out['meme_signal_results_return_pct_dist'] = f"ERR: {e}"

# --- 2) Penny: identify pnl col names + 0-pnl + last_updated
out['penny_picks_cols'] = cols('penny_picks')
out['penny_picks_daily_cols'] = cols('penny_picks_daily')

# Sample
cur.execute("SELECT * FROM penny_picks LIMIT 3")
out['penny_picks_sample_cols'] = [d[0] for d in cur.description]
out['penny_picks_sample_rows'] = [[(str(v)[:80] if v is not None else None) for v in r] for r in cur.fetchall()]

# Check pnl-like columns
for cand in ['return_pct','pnl_pct','pnl','realized_pnl','exit_price','current_price','entry_price','price_target']:
    real = next((c[0] for c in out['penny_picks_cols'] if c[0].lower()==cand), None)
    if real:
        try:
            cur.execute(f"SELECT COUNT(*) FROM penny_picks WHERE `{real}` IS NULL")
            null_n = cur.fetchone()[0]
            cur.execute(f"SELECT COUNT(*) FROM penny_picks WHERE `{real}`=0")
            zero_n = cur.fetchone()[0]
            out.setdefault('penny_picks_pnl_check', {})[real] = {'null': null_n, 'zero': zero_n}
        except Exception as e:
            out.setdefault('penny_picks_pnl_check', {})[real] = f"ERR: {e}"

# --- 3) Last-written-at via INFORMATION_SCHEMA UPDATE_TIME for tables we missed
tables_of_interest = ['cr_pair_picks','cr_price_history','fxp_pair_picks','fxp_price_history',
                      'mf2_fund_picks','mf2_nav_history','mf2_backtest_trades','mf_nav_history',
                      'mf_fund_picks','mf_strategies','mf_funds','mf_selections',
                      'meme_signal_results','meme_signals','crypto_exchange_netflow']
for t in tables_of_interest:
    cur.execute("SELECT UPDATE_TIME, CREATE_TIME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s", ('ejaguiar1_stocks', t))
    r = cur.fetchone()
    if r:
        out.setdefault('table_update_time', {})[t] = {'update_time': str(r[0]), 'create_time': str(r[1])}

# --- 4) cr_pair_picks + fxp_pair_picks + mf2_fund_picks: status enum + recent row
for t in ['cr_pair_picks','fxp_pair_picks','mf2_fund_picks','mf2_backtest_trades','mf_fund_picks']:
    cs = cols(t)
    out.setdefault('extra_cols', {})[t] = [(x[0], x[1]) for x in cs]
    cnames = [c[0].lower() for c in cs]
    if 'status' in cnames:
        try:
            cur.execute(f"SELECT `status`, COUNT(*) FROM `{t}` GROUP BY `status` ORDER BY 2 DESC LIMIT 10")
            out.setdefault('extra_status', {})[t] = [(str(r[0]), r[1]) for r in cur.fetchall()]
        except Exception as e:
            out.setdefault('extra_status', {})[t] = f"ERR: {e}"
    # try most-recent timestamp
    for cand in ('updated_at','created_at','closed_at','signal_time','timestamp','date','as_of_date','pick_date','open_date','open_time','signal_date'):
        real = next((x[0] for x in cs if x[0].lower()==cand), None)
        if real:
            try:
                cur.execute(f"SELECT MAX(`{real}`), MIN(`{real}`) FROM `{t}`")
                mx, mn = cur.fetchone()
                out.setdefault('extra_lw', {}).setdefault(t, {})[real] = {'max': str(mx), 'min': str(mn)}
            except Exception as e:
                pass

# --- 5) Sample ddl-style first 5 rows for the picks/trades tables
for t in ['cr_pair_picks','fxp_pair_picks','mf2_fund_picks','mf2_backtest_trades','penny_picks','gm_unified_picks','gm_sec_insider_trades']:
    try:
        cur.execute(f"SELECT * FROM `{t}` LIMIT 3")
        cs2 = [d[0] for d in cur.description]
        rs = [[(str(v)[:60] if v is not None else None) for v in r] for r in cur.fetchall()]
        out.setdefault('extra_samples', {})[t] = {'cols': cs2, 'rows': rs}
    except Exception as e:
        out.setdefault('extra_samples', {})[t] = f"ERR: {e}"

# --- 6) gm_unified_picks: source distribution + recent date
try:
    cur.execute("SELECT MAX(created_at), MIN(created_at), COUNT(*) FROM gm_unified_picks")
    r = cur.fetchone()
    out['gm_unified_picks_dates'] = {'max': str(r[0]), 'min': str(r[1]), 'count': r[2]}
except Exception as e:
    out['gm_unified_picks_dates'] = f"ERR: {e}"

# --- 7) gm_sec_insider_trades fresh?
try:
    cur.execute("SELECT DATE(created_at) AS d, COUNT(*) FROM gm_sec_insider_trades GROUP BY d ORDER BY d DESC LIMIT 7")
    out['gm_sec_insider_trades_recent_days'] = [(str(r[0]), r[1]) for r in cur.fetchall()]
except Exception as e:
    out['gm_sec_insider_trades_recent_days'] = f"ERR: {e}"

# --- 8) crypto_exchange_netflow: schema and latest
try:
    out['crypto_exchange_netflow_cols'] = cols('crypto_exchange_netflow')
    cur.execute("SELECT * FROM crypto_exchange_netflow LIMIT 5")
    out['cef_sample_cols'] = [d[0] for d in cur.description]
    out['cef_sample_rows'] = [[(str(v)[:80] if v is not None else None) for v in r] for r in cur.fetchall()]
except Exception as e:
    out['crypto_exchange_netflow_err'] = f"ERR: {e}"

# Now meme signals interval check using whatever timestamp pair we find
ms_cols = [c[0] for c in out['meme_signals_cols']]
ms_lower = [c.lower() for c in ms_cols]
print('TS_CANDIDATES:', ts_cols, file=sys.stderr)
for c1 in ['signal_time','created_at','open_time','entry_time']:
    for c2 in ['result_time','exit_time','closed_at','close_time','closed','resolved_at','updated_at']:
        if c1 in ms_lower and c2 in ms_lower:
            r1 = next(x for x in ms_cols if x.lower()==c1)
            r2 = next(x for x in ms_cols if x.lower()==c2)
            out[f'ms_interval_{r1}_{r2}'] = try_interval(r1, r2)

print(json.dumps(out, indent=2, default=str))
c.close()
