"""Deep-dive verification of flagged ghost cohorts."""
import os, json
import pymysql


def _db_creds():
    raw = os.environ.get("DB_PASSWORDS_JSON")
    if not raw and os.path.exists(".env.dbpw"):
        raw = open(".env.dbpw").read()
    if not raw:
        raise SystemExit("DB_PASSWORDS_JSON not set — see docs/db_remediation.md")
    return json.loads(raw)


def conn():
    return pymysql.connect(host="mysql.50webs.com", port=3306,
        user="ejaguiar1_stocks", password=_db_creds()["stocks"], database="ejaguiar1_stocks",
        connect_timeout=15, read_timeout=60, charset="utf8mb4", autocommit=True)

def q(sql, params=()):
    c = conn()
    try:
        with c.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        c.close()

def show(title, rows, lim=10):
    print(f"\n--- {title} ---")
    for r in rows[:lim]:
        print("  ", {k: (str(v)[:60] if v is not None else None) for k, v in r.items()})
    if len(rows) > lim:
        print(f"  ... +{len(rows)-lim} more")

# ============= rapid_signals =============
print("="*80)
print("RAPID_SIGNALS deep-dive")
print("="*80)
# How many distinct outcome values total
show("outcome distinct values + counts",
     q("SELECT outcome, COUNT(*) AS n FROM rapid_signals GROUP BY outcome ORDER BY n DESC"))
show("status distinct values",
     q("SELECT status, COUNT(*) AS n FROM rapid_signals GROUP BY status ORDER BY n DESC"))
# Did the outcomes get filled in or are they all NULL?
show("rows where outcome IS NOT NULL grouped by status",
     q("SELECT status, COUNT(*) AS n FROM rapid_signals WHERE outcome IS NOT NULL GROUP BY status ORDER BY n DESC"))
# 3 sample rows
show("sample rows", q("SELECT signal_id, strategy_name, pair, signal_type, entry_price, status, outcome, created_at FROM rapid_signals LIMIT 5"))

# ============= at_consensus_picks =============
print("\n"+"="*80)
print("AT_CONSENSUS_PICKS deep-dive")
print("="*80)
# Pattern: identical pnl across many rows of same symbol+direction. Smells like F4 (close on every refresh)
show("top constant cohorts (n>50, dist_entries<=2)",
     q("""SELECT symbol, direction, ROUND(pnl_pct,4) AS pnl_r, COUNT(*) AS n, COUNT(DISTINCT entry_price) AS de, COUNT(DISTINCT take_profit) AS dtp
          FROM at_consensus_picks WHERE pnl_pct IS NOT NULL
          GROUP BY symbol, direction, ROUND(pnl_pct,4)
          HAVING COUNT(*) > 50 AND COUNT(DISTINCT entry_price) <= 2
          ORDER BY n DESC LIMIT 20"""))
show("sample SPY -1.3358 cohort",
     q("""SELECT id, symbol, direction, entry_price, take_profit, stop_loss, pnl_pct, status, generated_at, closed_at, exit_price
          FROM at_consensus_picks WHERE symbol='SPY' AND direction='LONG' AND ROUND(pnl_pct,4) = -1.3358 LIMIT 5"""))
show("entry_price + tp distinct on SPY -1.3358 cohort",
     q("""SELECT COUNT(*) AS n, COUNT(DISTINCT entry_price) AS de, COUNT(DISTINCT exit_price) AS dxp, COUNT(DISTINCT generated_at) AS dgen, COUNT(DISTINCT closed_at) AS dclose
          FROM at_consensus_picks WHERE symbol='SPY' AND direction='LONG' AND ROUND(pnl_pct,4) = -1.3358"""))
show("status dist",
     q("SELECT status, COUNT(*) AS n FROM at_consensus_picks GROUP BY status ORDER BY n DESC"))

# ============= at_discord_notifications =============
print("\n"+"="*80)
print("AT_DISCORD_NOTIFICATIONS deep-dive")
print("="*80)
show("pnl_pct distribution",
     q("SELECT pnl_pct, COUNT(*) AS n FROM at_discord_notifications GROUP BY pnl_pct ORDER BY n DESC LIMIT 10"))
show("sample",
     q("SELECT id, symbol, direction, entry_price, pnl_pct, strategy, created_at FROM at_discord_notifications LIMIT 3"))

# ============= trading_picks =============
print("\n"+"="*80)
print("TRADING_PICKS deep-dive")
print("="*80)
show("biggest timestamp clusters",
     q("""SELECT created_at, COUNT(*) AS n, COUNT(DISTINCT symbol) AS dsym, COUNT(DISTINCT strategy) AS dstr, COUNT(DISTINCT source_system) AS dsrc
          FROM trading_picks GROUP BY created_at HAVING COUNT(*) > 100 ORDER BY n DESC LIMIT 10"""))
show("biggest constant cohorts",
     q("""SELECT source_system, symbol, direction, ROUND(pnl_pct,4) AS pnl_r, COUNT(*) AS n, COUNT(DISTINCT entry_price) AS de
          FROM trading_picks WHERE pnl_pct IS NOT NULL
          GROUP BY source_system, symbol, direction, ROUND(pnl_pct,4)
          HAVING COUNT(*) > 100 AND COUNT(DISTINCT entry_price) <= 2
          ORDER BY n DESC LIMIT 20"""))
show("status dist",
     q("SELECT status, COUNT(*) AS n FROM trading_picks GROUP BY status ORDER BY n DESC LIMIT 10"))
show("pnl_pct distinct count",
     q("SELECT COUNT(DISTINCT ROUND(pnl_pct,4)) AS dpnl, COUNT(*) AS total, SUM(CASE WHEN pnl_pct IS NULL THEN 1 ELSE 0 END) AS nulls FROM trading_picks"))

# ============= miracle_picks2/3, daytrader_sim, cw_winners, at_signal_outcomes =============
print("\n"+"="*80)
print("MIRACLE_PICKS3 deep-dive (n=644 distinct_pnl=1)")
print("="*80)
show("outcome distribution",
     q("SELECT outcome, COUNT(*) AS n FROM miracle_picks3 GROUP BY outcome ORDER BY n DESC"))
show("sample",
     q("SELECT id, ticker, strategy_name, entry_price, take_profit_price, outcome, scan_date FROM miracle_picks3 LIMIT 3"))

print("\n"+"="*80)
print("MIRACLE_PICKS2 deep-dive")
print("="*80)
show("outcome distribution",
     q("SELECT outcome, COUNT(*) AS n FROM miracle_picks2 GROUP BY outcome ORDER BY n DESC"))

print("\n"+"="*80)
print("DAYTRADER_SIM_TRADES deep-dive")
print("="*80)
show("pnl distribution",
     q("SELECT pnl, COUNT(*) AS n FROM daytrader_sim_trades GROUP BY pnl ORDER BY n DESC LIMIT 10"))
show("sample",
     q("SELECT id, ticker, strategy_name, entry_price, exit_price, pnl, sim_date FROM daytrader_sim_trades LIMIT 3"))

print("\n"+"="*80)
print("CW_WINNERS deep-dive")
print("="*80)
show("outcome distribution",
     q("SELECT outcome, COUNT(*) AS n FROM cw_winners GROUP BY outcome ORDER BY n DESC"))
show("verdict distribution",
     q("SELECT verdict, COUNT(*) AS n FROM cw_winners GROUP BY verdict ORDER BY n DESC"))
show("sample",
     q("SELECT id, pair, price_at_signal, price_at_resolve, verdict, target_pct, outcome FROM cw_winners LIMIT 3"))

print("\n"+"="*80)
print("AT_SIGNAL_OUTCOMES deep-dive")
print("="*80)
show("outcome distribution",
     q("SELECT outcome, COUNT(*) AS n FROM at_signal_outcomes GROUP BY outcome ORDER BY n DESC"))
show("pnl_pct distribution",
     q("SELECT ROUND(pnl_pct,4) AS pnl_r, COUNT(*) AS n FROM at_signal_outcomes GROUP BY ROUND(pnl_pct,4) ORDER BY n DESC LIMIT 10"))
show("sample",
     q("SELECT id, symbol, direction, entry_price, exit_price, pnl_pct, outcome, source_system FROM at_signal_outcomes LIMIT 3"))

print("\n"+"="*80)
print("DAYTRADER_SIM_DAYS deep-dive (n=176 distinct_pnl=1 ALL ZEROES?)")
print("="*80)
show("return_pct dist",
     q("SELECT return_pct, COUNT(*) AS n FROM daytrader_sim_days GROUP BY return_pct ORDER BY n DESC LIMIT 5"))
show("sample",
     q("SELECT id, sim_date, total_invested, total_pnl, return_pct, wins, losses FROM daytrader_sim_days LIMIT 5"))

# ============= at_raw_picks - new strategy mention: alpha_engine MATIC LONG -15 =============
print("\n"+"="*80)
print("AT_RAW_PICKS — NEW finding: alpha_engine MATICUSDT LONG @ -15.0 cohort")
print("="*80)
show("at_raw_picks columns",
     q("SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='ejaguiar1_stocks' AND TABLE_NAME='at_raw_picks'"))
show("alpha_engine MATIC -15 cohort sample",
     q("""SELECT id, source_system, symbol, direction, entry_price, take_profit, stop_loss, pnl_pct, status
          FROM at_raw_picks WHERE source_system='alpha_engine' AND symbol='MATICUSDT' AND ROUND(pnl_pct,4)=-15.0 LIMIT 3"""))

# ============= simulation_grid (no pnl col detected, recheck schema) =============
print("\n"+"="*80)
print("SIMULATION_GRID schema + sample")
print("="*80)
show("columns",
     q("SELECT COLUMN_NAME, DATA_TYPE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='ejaguiar1_stocks' AND TABLE_NAME='simulation_grid'"))
show("sample", q("SELECT * FROM simulation_grid LIMIT 2"))

# ============= alpha_picks/stock_picks recheck =============
print("\n"+"="*80)
print("ALPHA_PICKS schema + outcome cols")
print("="*80)
show("columns",
     q("SELECT COLUMN_NAME, DATA_TYPE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='ejaguiar1_stocks' AND TABLE_NAME='alpha_picks'"))
show("sample", q("SELECT * FROM alpha_picks LIMIT 1"))

print("\n"+"="*80)
print("STOCK_PICKS schema")
print("="*80)
show("columns",
     q("SELECT COLUMN_NAME, DATA_TYPE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='ejaguiar1_stocks' AND TABLE_NAME='stock_picks'"))

# ============= fxp_pair_picks / cr_pair_picks recheck =============
print("\n"+"="*80)
print("FXP_PAIR_PICKS schema")
print("="*80)
show("cols",
     q("SELECT COLUMN_NAME, DATA_TYPE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='ejaguiar1_stocks' AND TABLE_NAME='fxp_pair_picks'"))

print("\n"+"="*80)
print("CR_PAIR_PICKS schema")
print("="*80)
show("cols",
     q("SELECT COLUMN_NAME, DATA_TYPE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='ejaguiar1_stocks' AND TABLE_NAME='cr_pair_picks'"))

# ============= sports DB lm_arena_bets =============
print("\n"+"="*80)
print("LM_ARENA_BETS (sports DB) deep-dive")
print("="*80)
sports = pymysql.connect(host="mysql.50webs.com", port=3306,
    user="ejaguiar1_sportsbet", password=_db_creds()["sportsbet"], database="ejaguiar1_sportsbet",
    connect_timeout=15, read_timeout=60, charset="utf8mb4", autocommit=True)
try:
    with sports.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute("SELECT COUNT(*) AS n FROM lm_arena_bets")
        print("  total rows:", cur.fetchone())
        cur.execute("SELECT status, COUNT(*) AS n FROM lm_arena_bets GROUP BY status ORDER BY n DESC")
        print("  status dist:")
        for r in cur.fetchall(): print("   ", r)
        cur.execute("SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='ejaguiar1_sportsbet' AND TABLE_NAME='lm_arena_bets'")
        print("  cols:", [r["COLUMN_NAME"] for r in cur.fetchall()])
finally:
    sports.close()
