import os, json, pymysql, datetime

# Load credentials from .env (already set in environment?)
# We'll read .env file directly for simplicity

def load_env():
    env = {}
    with open('C:\\findtorontoevents_antigravity.ca\.env') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip()
    return env

env = load_env()
host = env.get('MYSQL_HOST')
user = env.get('MYSQL_USERNAME')
password = env.get('DB_PASS_STOCKS')
# Connect to stocks DB for schema discovery
conn = pymysql.connect(host=host, user=user, password=password, database=env.get('DB_NAME_STOCKS'))
cur = conn.cursor()
# Discover tables
cur.execute("SHOW TABLES")
tables = [row[0] for row in cur.fetchall()]
report = []
for tbl in tables:
    cur.execute(f"DESCRIBE {tbl}")
    cols = cur.fetchall()
    report.append({"table": tbl, "columns": [{"field": c[0], "type": c[1], "null": c[2], "key": c[3], "default": c[4], "extra": c[5]} for c in cols]})
# Data quality audit and edge calculations
# We'll compute per asset class using backtests DB
back_user = env.get('MYSQL_USERNAME')
back_pass = env.get('DB_PASS_BACKTESTS')
back_db = env.get('DB_NAME_BACKTESTS')
back_conn = pymysql.connect(host=host, user=user, password=back_pass, database=back_db)
back_cur = back_conn.cursor()
# Get asset classes
back_cur.execute("SELECT DISTINCT asset_class FROM backtest_results")
asset_classes = [row[0] for row in back_cur.fetchall()]
edge_results = {}
for ac in asset_classes:
    # Count trades
    back_cur.execute("SELECT COUNT(*) FROM backtest_results WHERE asset_class=%s", (ac,))
    n = back_cur.fetchone()[0]
    if n < 30:
        continue
    # Wins/losses
    back_cur.execute("SELECT SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END), SUM(CASE WHEN pnl<0 THEN 1 ELSE 0 END) FROM backtest_results WHERE asset_class=%s", (ac,))
    wins, losses = back_cur.fetchone()
    wr = wins/(wins+losses) if (wins+losses)>0 else None
    # Profit factor
    back_cur.execute("SELECT SUM(CASE WHEN pnl>0 THEN pnl ELSE 0 END), SUM(CASE WHEN pnl<0 THEN -pnl ELSE 0 END) FROM backtest_results WHERE asset_class=%s", (ac,))
    pos, neg = back_cur.fetchone()
    pf = pos/neg if neg>0 else None
    # Sharpe (mean/std)
    back_cur.execute("SELECT AVG(pnl), STDDEV_POP(pnl) FROM backtest_results WHERE asset_class=%s", (ac,))
    mean, std = back_cur.fetchone()
    sharpe = mean/std if std and std>0 else None
    # Max drawdown placeholder (not computed)
    mdd = None
    edge_results[ac] = {"n_trades": n, "wins": wins, "losses": losses, "win_rate": wr, "profit_factor": pf, "sharpe": sharpe, "max_dd": mdd}
# Write markdown report
md_path = 'C:\\findtorontoevents_antigravity.ca\\reports\\edge_report_mysql.md'
with open(md_path, 'w') as f:
    f.write('# Edge Report\n')
    f.write(f"Generated at {datetime.datetime.utcnow().isoformat()}Z\n\n")
    for ac, data in edge_results.items():
        f.write(f"## {ac}\n")
        for k, v in data.items():
            f.write(f"- {k}: {v}\n")
        f.write('\n')
# Write JSON
json_path = 'C:\\findtorontoevents_antigravity.ca\\reports\\edge_per_class.json'
with open(json_path, 'w') as f:
    json.dump({"generated_at": datetime.datetime.utcnow().isoformat(), "asset_classes": edge_results}, f, indent=2)
print('Edge report generated')
