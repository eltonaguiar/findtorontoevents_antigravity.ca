#!/usr/bin/env python3
import os, json, sys, math, statistics
from pathlib import Path
from dotenv import load_dotenv
import mysql.connector

load_dotenv()
HOST = os.getenv('MYSQL_HOST')

# Credentials per database

def get_credentials(db_name):
    if db_name == os.getenv('DB_NAME_STOCKS'):
        return os.getenv('DB_USER'), os.getenv('DB_PASS_STOCKS')
    elif db_name == os.getenv('DB_NAME_BACKTESTS'):
        return os.getenv('DB_BACKTESTS_USER'), os.getenv('DB_PASS_BACKTESTS')
    else:
        return os.getenv('MYSQL_USERNAME'), os.getenv('DB_PASS_STOCKS')


def get_db_schema(db_name):
    user, pwd = get_credentials(db_name)
    conn = mysql.connector.connect(host=HOST, user=user, password=pwd, database=db_name)
    cur = conn.cursor()
    cur.execute("SHOW TABLES")
    tables = [row[0] for row in cur.fetchall()]
    schema = {}
    for tbl in tables:
        cur.execute(f"SHOW COLUMNS FROM `{tbl}`")
        cols = [{"Field": row[0], "Type": row[1], "Null": row[2], "Key": row[3], "Default": row[4], "Extra": row[5]} for row in cur.fetchall()]
        cur.execute(f"SELECT COUNT(*) FROM `{tbl}`")
        count = cur.fetchone()[0]
        schema[tbl] = {"columns": cols, "row_count": count}
    cur.close()
    conn.close()
    return schema

# Data‑quality & edge calculations for backtest data

def fetch_trades():
    db = os.getenv('DB_NAME_BACKTESTS')
    user, pwd = get_credentials(db)
    conn = mysql.connector.connect(host=HOST, user=user, password=pwd, database=db)
    cur = conn.cursor(dictionary=True)
    # Use bt_backtest_trades which contains asset_class, strategy, pnl_pct, direction, confidence, entry_time, exit_time
    cur.execute("SELECT asset_class, strategy, pnl_pct, direction, confidence, entry_time, exit_time FROM bt_backtest_trades")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def asset_class_stats(trades):
    stats = {}
    for t in trades:
        ac = (t['asset_class'] or 'UNKNOWN').upper()
        if ac not in stats:
            stats[ac] = []
        stats[ac].append(t)
    return stats


def compute_metrics(pnls):
    # Filter out None values
    pnls = [p for p in pnls if p is not None]
    n = len(pnls)
    if n == 0:
        return {"n": 0, "win_rate": 0, "profit_factor": 0, "avg_win": 0, "avg_loss": 0, "wl_ratio": 0, "expectancy": 0, "sharpe": 0, "max_drawdown": 0, "median": 0, "skewness": 0}
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    win_rate = len(wins) / n if n else 0
    profit_factor = (sum(wins) / abs(sum(losses))) if losses else float('inf')
    avg_win = sum(wins) / len(wins) if wins else 0
    avg_loss = sum(losses) / len(losses) if losses else 0
    wl_ratio = avg_win / abs(avg_loss) if avg_loss else 0
    expectancy = (win_rate * avg_win) - ((1 - win_rate) * abs(avg_loss))
    sharpe = statistics.mean(pnls) / statistics.stdev(pnls) if n > 1 else 0
    max_dd = 0
    peak = 0
    cum = 0
    for p in pnls:
        cum += p
        if cum > peak:
            peak = cum
        draw = peak - cum
        if draw > max_dd:
            max_dd = draw
    median = statistics.median(pnls) if pnls else 0
    if n > 2:
        mean = statistics.mean(pnls)
        std = statistics.stdev(pnls)
        skew = sum(((p - mean) / std) ** 3 for p in pnls) / n
    else:
        skew = 0
    return {
        "n": n,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "wl_ratio": wl_ratio,
        "expectancy": expectancy,
        "sharpe": sharpe,
        "max_drawdown": max_dd,
        "median": median,
        "skewness": skew,
    }


def per_strategy_breakdown(trades):
    strat = {}
    for t in trades:
        key = ((t['asset_class'] or 'UNKNOWN').upper(), (t['strategy'] or 'UNKNOWN'))
        strat.setdefault(key, []).append(t)
    result = {}
    for (ac, name), rows in strat.items():
        pnls = [r['pnl_pct'] for r in rows]
        metrics = compute_metrics(pnls)
        result.setdefault(ac, []).append({
            "strategy": name,
            "metrics": metrics,
        })
    for ac in result:
        result[ac].sort(key=lambda x: x['metrics']['profit_factor'], reverse=True)
    return result


def main():
    # 1. Schema report (already done before)
    dbs = [os.getenv('DB_NAME_STOCKS'), os.getenv('DB_NAME_BACKTESTS')]
    schema_report = {}
    for db in dbs:
        if not db:
            continue
        try:
            schema_report[db] = get_db_schema(db)
        except Exception as e:
            schema_report[db] = {"error": str(e)}
    # 2. Edge calculations from backtest trades
    trades = fetch_trades()
    # Data‑quality audit (nulls, duplicates, date ranges)
    null_counts = {k: sum(1 for t in trades if t[k] is None) for k in trades[0]}
    seen = set()
    dup = 0
    for t in trades:
        key = (t['asset_class'], t['strategy'], t['entry_time'], t['exit_time'])
        if key in seen:
            dup += 1
        else:
            seen.add(key)
    date_ranges = {}
    for ac, group in asset_class_stats(trades).items():
        dates = [t['entry_time'] for t in group if t['entry_time']]
        if dates:
            date_ranges[ac] = {"earliest": min(dates).isoformat(), "latest": max(dates).isoformat()}
    # Edge per asset class
    asset_stats = {}
    for ac, group in asset_class_stats(trades).items():
        pnls = [t['pnl_pct'] for t in group]
        asset_stats[ac] = compute_metrics(pnls)
    # Per‑strategy breakdown
    strat_breakdown = per_strategy_breakdown(trades)
    # Build final report
    from datetime import datetime
    report = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "schema": schema_report,
        "null_counts": null_counts,
        "duplicate_rows": dup,
        "date_ranges": date_ranges,
        "asset_class_metrics": asset_stats,
        "strategy_breakdown": strat_breakdown,
    }
    out_md = Path(__file__).parent.parent / "reports" / "edge_report_mysql.md"
    out_json = Path(__file__).parent.parent / "reports" / "edge_per_class.json"
    out_md.parent.mkdir(parents=True, exist_ok=True)
    with open(out_md, "w", encoding="utf-8") as f:
        f.write(f"# Edge Report – {report['generated_at']}\n\n")
        f.write("## Asset Class Metrics\n\n")
        for ac, m in asset_stats.items():
            f.write(f"**{ac}** – n={m['n']}, WR={m['win_rate']:.2%}, PF={m['profit_factor']:.2f}, Sharpe={m['sharpe']:.2f}\n\n")
        f.write("## Strategy Breakdown (top 5 per class)\n\n")
        for ac, lst in strat_breakdown.items():
            f.write(f"### {ac}\n")
            for entry in lst[:5]:
                m = entry['metrics']
                f.write(f"- {entry['strategy']}: n={m['n']}, WR={m['win_rate']:.2%}, PF={m['profit_factor']:.2f}\n")
            f.write("\n")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"Reports written to {out_md} and {out_json}")

if __name__ == "__main__":
    main()
