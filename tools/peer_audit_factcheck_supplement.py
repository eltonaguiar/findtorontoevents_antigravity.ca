"""Supplemental queries for peer audit fact-check."""
import os, json
from decimal import Decimal
from datetime import datetime, date

os.environ['AUDIT_DB_HOST']='mysql.50webs.com'
os.environ['AUDIT_DB_USER']='ejaguiar1_stocks'
os.environ['AUDIT_DB_PASS']='stocks'
os.environ['AUDIT_DB_NAME']='ejaguiar1_stocks'

from audit_trail.mysql_client import _create_connection

def _j(v):
    if isinstance(v, Decimal): return float(v)
    if isinstance(v, (datetime,date)): return v.isoformat()
    return v

def fa(cur, sql):
    cur.execute(sql); cols=[d[0] for d in cur.description]
    return [{c:_j(v) for c,v in zip(cols,r)} for r in cur.fetchall()]

def fone(cur,sql):
    cur.execute(sql); r=cur.fetchone(); return _j(r[0]) if r else None

c = _create_connection(); cur=c.cursor()
cur.execute("SET SESSION MAX_EXECUTION_TIME=120000")

out={}

# Rapid signals deeper
out['rapid_signals_pnl_summary'] = fa(cur, """
  SELECT
    COUNT(*) AS n_total,
    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) AS n_pos_pnl,
    SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) AS n_neg_pnl,
    SUM(CASE WHEN pnl = 0 THEN 1 ELSE 0 END) AS n_zero_pnl,
    SUM(CASE WHEN pnl IS NULL THEN 1 ELSE 0 END) AS n_null_pnl,
    AVG(pnl) AS avg_pnl, MIN(pnl) AS min_pnl, MAX(pnl) AS max_pnl
  FROM rapid_signals
""")
out['rapid_signals_pnl_top_constants'] = fa(cur, """
  SELECT pnl, outcome, COUNT(*) AS n FROM rapid_signals
  GROUP BY pnl, outcome ORDER BY n DESC LIMIT 20
""")
out['rapid_signals_signal_type'] = fa(cur, """
  SELECT signal_type, COUNT(*) AS n FROM rapid_signals GROUP BY signal_type
""")
out['rapid_signals_outcome_by_type'] = fa(cur, """
  SELECT signal_type, outcome, COUNT(*) AS n FROM rapid_signals
  GROUP BY signal_type, outcome ORDER BY signal_type, outcome
""")

# Finding 1 deeper: time-travel by source_systems + asset class
out['finding1_breakdown_by_class'] = fa(cur, """
  SELECT asset_class, COUNT(*) AS time_travel_rows
  FROM at_consensus_picks
  WHERE closed_at IS NOT NULL AND generated_at IS NOT NULL
    AND closed_at < generated_at
  GROUP BY asset_class ORDER BY time_travel_rows DESC
""")
out['finding1_breakdown_by_status'] = fa(cur, """
  SELECT status, COUNT(*) AS n
  FROM at_consensus_picks
  WHERE closed_at IS NOT NULL AND generated_at IS NOT NULL
    AND closed_at < generated_at
  GROUP BY status ORDER BY n DESC
""")

# Consensus_tracked: status breakdown + entry_date span + ticker uniqueness
out['ct_status_dist'] = fa(cur, """
  SELECT status, COUNT(*) AS n FROM consensus_tracked GROUP BY status ORDER BY n DESC
""")
out['ct_date_span'] = fa(cur, """
  SELECT MIN(entry_date) AS min_d, MAX(entry_date) AS max_d, COUNT(DISTINCT entry_date) AS n_dates
  FROM consensus_tracked
""")
out['ct_round_to_2dp'] = fone(cur, """
  SELECT COUNT(*) FROM consensus_tracked WHERE entry_price = ROUND(entry_price,2)
""")
out['ct_zero_return_breakdown'] = fa(cur, """
  SELECT status, COUNT(*) AS n FROM consensus_tracked
  WHERE final_return_pct = 0 GROUP BY status
""")

# at_audit_events column type — confirm it's same enum
print(json.dumps(out, indent=2, default=str))
