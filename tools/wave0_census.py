#!/usr/bin/env python3
"""
Wave 0 Census -- Read-only audit of ejaguiar1_stocks @ mysql.50webs.com
======================================================================
Uses FRESH pymysql connection per section (shared hosting drops long-lived connections).
No emoji -- plain text markers only (Windows-compatible).
Output: reports/wave0_census_2026-05-08.md
"""
import os, sys, json
from decimal import Decimal
from datetime import datetime, date, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pymysql


def _db_creds():
    raw = os.environ.get("DB_PASSWORDS_JSON")
    if not raw and os.path.exists(".env.dbpw"):
        raw = open(".env.dbpw").read()
    if not raw:
        raise SystemExit("DB_PASSWORDS_JSON not set — see docs/db_remediation.md")
    return json.loads(raw)


DB_HOST = "mysql.50webs.com"
DB_PORT = 3306
DB_USER = "ejaguiar1_stocks"
DB_PASS = _db_creds()["stocks"]
DB_NAME = "ejaguiar1_stocks"


def conn():
    return pymysql.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS,
        database=DB_NAME, connect_timeout=30, read_timeout=90,
        write_timeout=30, charset="utf8mb4", autocommit=True)


def _j(v):
    if isinstance(v, Decimal): return float(v)
    if isinstance(v, (datetime, date)): return v.isoformat()
    if isinstance(v, bytes):
        try: return v.decode("utf-8", errors="replace")
        except: return str(v)
    return v

def fm(n):
    if n is None: return "NULL"
    return f"{n:,}"

def run_section(label, fn):
    """Create fresh connection, execute fn(cur), return list of report lines."""
    print(f"  [{label}] ...")
    try:
        c = conn()
        cur = c.cursor()
        result = fn(cur)
        cur.close()
        c.close()
        return result
    except Exception as e:
        print(f"  [FAIL] {label}: {e}")
        return [f"*{label} failed: {e}*", ""]


# ---- section functions (each receives cursor, returns lines) ----

def _0a_status(cur):
    """Status distribution + total rows (information_schema)."""
    lines = []
    lines.append("## 0-A: OPEN-Population Census (`bt_backtest_trades`)")
    lines.append("")
    cur.execute("SELECT TABLE_ROWS FROM information_schema.TABLES WHERE TABLE_SCHEMA=%s AND TABLE_NAME='bt_backtest_trades'", (DB_NAME,))
    total = int(cur.fetchone()[0] or 0)
    lines.append(f"**Total rows (approx):** {fm(total)}")
    lines.append("")

    # Status distribution
    cur.execute("SELECT status, COUNT(*) AS cnt FROM bt_backtest_trades GROUP BY status ORDER BY cnt DESC")
    rows = cur.fetchall()
    lines.append("### Status Distribution")
    lines.append("| Status | Count | % |")
    lines.append("|--------|-------|---|")
    for s, cnt in rows:
        pct = round(cnt / total * 100, 2) if total else 0
        lines.append(f"| `{s}` | {fm(cnt)} | {pct}% |")
    lines.append("")
    return lines


def _0a_open_by_class(cur):
    """OPEN by asset_class."""
    lines = []
    lines.append("### OPEN Rows by Asset Class")
    lines.append("| Asset Class | OPEN Count | Avg Age (days) |")
    lines.append("|-------------|-----------|----------------|")
    cur.execute("""
        SELECT asset_class, COUNT(*) AS n,
               ROUND(AVG(TIMESTAMPDIFF(DAY, entry_time, NOW())), 1) AS avg_age
        FROM bt_backtest_trades WHERE status='OPEN'
        GROUP BY asset_class ORDER BY n DESC
    """)
    for ac, cnt, age in cur.fetchall():
        lines.append(f"| `{ac}` | {fm(cnt)} | {age} |")
    lines.append("")
    return lines


def _0a_open_total(cur):
    """OPEN total + avg age."""
    lines = []
    cur.execute("SELECT COUNT(*) FROM bt_backtest_trades WHERE status='OPEN'")
    total = cur.fetchone()[0]
    cur.execute("SELECT ROUND(AVG(TIMESTAMPDIFF(DAY, entry_time, NOW())), 1) FROM bt_backtest_trades WHERE status='OPEN'")
    avg = cur.fetchone()[0]
    lines.append(f"**TOTAL OPEN:** {fm(total)} (avg age: {avg} days)")
    lines.append("")
    return lines


def _0a_open_strategy(cur):
    """OPEN by strategy (top 15)."""
    lines = []
    lines.append("### OPEN Rows by Strategy (Top 15)")
    lines.append("| Strategy | OPEN Count |")
    lines.append("|----------|-----------|")
    cur.execute("""
        SELECT strategy, COUNT(*) AS n
        FROM bt_backtest_trades WHERE status='OPEN' AND strategy IS NOT NULL AND strategy!=''
        GROUP BY strategy ORDER BY n DESC LIMIT 15
    """)
    for s, n in cur.fetchall():
        lines.append(f"| `{s}` | {fm(n)} |")
    lines.append("")
    return lines


def _0a_age_buckets(cur):
    """OPEN age buckets."""
    lines = []
    lines.append("### OPEN Age Buckets")
    lines.append("| Age Bucket | Count |")
    lines.append("|------------|-------|")
    buckets = [
        ("< 1 hour", "entry_time > NOW() - INTERVAL 1 HOUR"),
        ("1-24 hours", "entry_time > NOW() - INTERVAL 24 HOUR AND entry_time <= NOW() - INTERVAL 1 HOUR"),
        ("1-7 days", "entry_time > NOW() - INTERVAL 7 DAY AND entry_time <= NOW() - INTERVAL 24 HOUR"),
        ("7-30 days", "entry_time > NOW() - INTERVAL 30 DAY AND entry_time <= NOW() - INTERVAL 7 DAY"),
        ("30-60 days", "entry_time > NOW() - INTERVAL 60 DAY AND entry_time <= NOW() - INTERVAL 30 DAY"),
        ("> 60 days", "entry_time <= NOW() - INTERVAL 60 DAY"),
    ]
    for label, cond in buckets:
        cur.execute(f"SELECT COUNT(*) FROM bt_backtest_trades WHERE status='OPEN' AND {cond}")
        cnt = cur.fetchone()[0]
        lines.append(f"| {label} | {fm(cnt)} |")
    lines.append("")
    return lines


def _0b_p01(cur):
    """P0-1: quan_engine MATICUSDT ghosts."""
    lines = []
    lines.append("## 0-B: Ghost Sweeps")
    lines.append("")
    lines.append("### P0-1: `quan_engine` MATICUSDT Constant-PnL Ghosts")
    lines.append("| Strategy | Symbol | Direction | PnL% | Count |")
    lines.append("|----------|--------|-----------|------|-------|")
    cur.execute("""
        SELECT strategy, symbol, direction, ROUND(pnl_pct,4), COUNT(*)
        FROM bt_backtest_trades
        WHERE symbol='MATICUSDT' AND strategy IN ('quan_engine','quan_engine_scalp','quan_engine_swing','meta_strategy')
        GROUP BY strategy, symbol, direction, ROUND(pnl_pct,4)
        ORDER BY COUNT(*) DESC LIMIT 20
    """)
    total = 0
    for row in cur.fetchall():
        total += row[-1]
        lines.append("| " + " | ".join(str(_j(v)) for v in row) + " |")
    lines.append(f"**Total ghost rows:** {fm(total)}")
    lines.append("")
    return lines


def _0b_p02(cur):
    """P0-2: meta_strategy ghost template."""
    lines = []
    lines.append("### P0-2: `meta_strategy` Constant-PnL Template")
    lines.append("| Strategy | Symbol | Direction | PnL% | Count |")
    lines.append("|----------|--------|-----------|------|-------|")
    cur.execute("""
        SELECT strategy, symbol, direction, ROUND(pnl_pct,4), COUNT(*)
        FROM bt_backtest_trades WHERE strategy='meta_strategy'
        GROUP BY strategy, symbol, direction, ROUND(pnl_pct,4)
        ORDER BY COUNT(*) DESC LIMIT 20
    """)
    total = 0
    for row in cur.fetchall():
        total += row[-1]
        lines.append("| " + " | ".join(str(_j(v)) for v in row) + " |")
    lines.append(f"**Total ghost rows:** {fm(total)}")
    lines.append("")
    return lines


def _0b_p03(cur):
    """P0-3: Phantom EXPIRED rows."""
    lines = []
    lines.append("### P0-3: Phantom EXPIRED Rows (pnl=0, exit=entry)")
    lines.append("| Asset Class | Phantoms | Total | Phantom % |")
    lines.append("|-------------|---------|-------|-----------|")
    cur.execute("""
        SELECT asset_class,
               SUM(CASE WHEN status='EXPIRED' AND pnl_pct=0 AND exit_price=entry_price THEN 1 ELSE 0 END),
               COUNT(*)
        FROM bt_backtest_trades
        WHERE asset_class IN ('EQUITY','FUTURES','ETF','FOREX','COMMODITY','BOND')
        GROUP BY asset_class ORDER BY SUM(CASE WHEN status='EXPIRED' AND pnl_pct=0 AND exit_price=entry_price THEN 1 ELSE 0 END) DESC
    """)
    for ac, ph, tot in cur.fetchall():
        pct = round(ph/tot*100,1) if tot else 0
        flag = " [HIGH]" if pct > 50 else ""
        lines.append(f"| `{ac}` | {fm(ph)} | {fm(tot)} | {pct}%{flag} |")
    lines.append("")
    return lines


def _0b_large(cur):
    """Large constant-PnL cohorts (> 1000)."""
    lines = []
    lines.append("### All Constant-PnL Cohorts > 1000 Rows")
    lines.append("| Strategy | Symbol | Direction | Asset Class | PnL% | Count |")
    lines.append("|----------|--------|-----------|-------------|------|-------|")
    cur.execute("""
        SELECT strategy, symbol, direction, asset_class, ROUND(pnl_pct,4), COUNT(*)
        FROM bt_backtest_trades WHERE pnl_pct IS NOT NULL
        GROUP BY strategy, symbol, direction, asset_class, ROUND(pnl_pct,4)
        HAVING COUNT(*) > 1000 ORDER BY COUNT(*) DESC LIMIT 30
    """)
    rows = cur.fetchall()
    if rows:
        for row in rows:
            lines.append("| " + " | ".join(str(_j(v)) for v in row) + " |")
    else:
        lines.append("| *(none)* | | | | | |")
    lines.append("")
    return lines


def _0c_integrity(cur):
    """PnL integrity: recompute vs stored."""
    lines = []
    lines.append("## 0-C: PnL Integrity Check")
    lines.append("")
    cur.execute("""
        SELECT
            SUM(CASE WHEN entry_price>0 AND exit_price>0 AND entry_price!=exit_price THEN 1 ELSE 0 END),
            SUM(CASE WHEN entry_price>0 AND exit_price>0 AND entry_price!=exit_price
                     AND ABS(pnl_pct - ((exit_price-entry_price)/entry_price*100)) > 1 THEN 1 ELSE 0 END)
        FROM bt_backtest_trades
        WHERE pnl_pct IS NOT NULL AND status NOT IN ('OPEN','ACTIVE')
    """)
    comp, mism = cur.fetchone()
    lines.append(f"- Computable rows: {fm(comp)}")
    if comp:
        pct = round(mism/comp*100, 1)
        lines.append(f"- Mismatch >1%: {fm(mism)} ({pct}%)")
        if pct > 50: lines.append("- Verdict: [CRITICAL] SEVERE (>50%)")
        elif pct > 10: lines.append("- Verdict: [WARNING] MODERATE (10-50%)")
        else: lines.append("- Verdict: [OK] (<10%)")
    lines.append("")
    return lines


def _0c_by_class(cur):
    """PnL mismatch by asset class."""
    lines = []
    lines.append("### PnL Mismatch by Asset Class")
    lines.append("| Asset Class | Computable | Mismatch | Mismatch% |")
    lines.append("|-------------|-----------|----------|-----------|")
    cur.execute("""
        SELECT asset_class,
               SUM(CASE WHEN entry_price>0 AND exit_price>0 AND entry_price!=exit_price THEN 1 ELSE 0 END),
               SUM(CASE WHEN entry_price>0 AND exit_price>0 AND entry_price!=exit_price
                        AND ABS(pnl_pct-((exit_price-entry_price)/entry_price*100))>1 THEN 1 ELSE 0 END)
        FROM bt_backtest_trades
        WHERE pnl_pct IS NOT NULL AND status NOT IN ('OPEN','ACTIVE')
        GROUP BY asset_class ORDER BY 2 DESC
    """)
    for ac, comp, mism in cur.fetchall():
        if comp:
            pct = round(mism/comp*100, 1)
            flag = " [CRITICAL]" if pct>50 else " [WARN]" if pct>10 else ""
            lines.append(f"| `{ac}` | {fm(comp)} | {fm(mism)} | {pct}%{flag} |")
    lines.append("")
    return lines


def _0d_nulls(cur):
    """NULL ratios on key columns."""
    lines = []
    lines.append("## 0-D: Data-Type Sanity")
    lines.append("")
    tables_cols = [
        ("bt_backtest_trades", ["confidence", "pnl_pct", "entry_price", "exit_price", "strategy", "direction"]),
        ("trading_picks", ["confidence", "pnl_pct", "entry_price", "strategy", "source_system"]),
    ]
    for table, cols in tables_cols:
        cur.execute(f"SELECT TABLE_ROWS FROM information_schema.TABLES WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s", (DB_NAME, table))
        total = int(cur.fetchone()[0] or 0)
        lines.append(f"### `{table}` -- NULL Ratios (approx total: {fm(total)})")
        lines.append("| Column | NULL Count | % NULL |")
        lines.append("|--------|-----------|--------|")
        for col in cols:
            try:
                cur.execute(f"SELECT COUNT(*) FROM `{table}` WHERE `{col}` IS NULL")
                nulls = cur.fetchone()[0]
                pct = round(nulls/total*100, 1) if total else 0
                flag = " [HIGH]" if pct>50 else " [WARN]" if pct>25 else ""
                lines.append(f"| `{col}` | {fm(nulls)} | {pct}%{flag} |")
            except Exception as e:
                lines.append(f"| `{col}` | ERR | -- |")
        lines.append("")
    return lines


def _0e_indexes(cur):
    """Index health for key tables."""
    lines = []
    lines.append("## 0-E: Index Health")
    lines.append("")

    large = ["bt_backtest_trades", "trading_picks"]
    for table in large:
        cur.execute(f"SHOW INDEX FROM `{table}`")
        rows = cur.fetchall()
        if rows:
            lines.append(f"### `{table}` ({len(rows)} index entries)")
            lines.append("| Key_name | Column_name | Seq |")
            lines.append("|----------|-------------|-----|")
            for r in rows:
                lines.append(f"| `{r[2]}` | `{r[4]}` | {r[3]} |")
        else:
            lines.append(f"### `{table}` -- NO INDEXES")
        lines.append("")
    return lines


def _freeze_check(cur):
    """Forward validator freeze check."""
    lines = []
    lines.append("## P0-5: Forward Validator Freeze Check")
    lines.append("")
    cur.execute("SELECT MAX(imported_at), TIMESTAMPDIFF(HOUR, MAX(imported_at), NOW()) FROM bt_backtest_trades WHERE status IN ('WON','LOST')")
    last, hrs = cur.fetchone()
    if last:
        lines.append(f"- Last WON/LOST write: {last}")
        lines.append(f"- Hours ago: {hrs}")
        lines.append(f"- Verdict: [FROZEN] ({hrs}h since last terminal write)" if (hrs and hrs>26) else "- Verdict: [OK] Active")
    cur.execute("SELECT COUNT(*), MAX(imported_at) FROM bt_backtest_trades WHERE imported_at > NOW() - INTERVAL 1 HOUR")
    cnt, recent = cur.fetchone()
    lines.append(f"- Writes in last hour: {fm(cnt)} (most recent: {recent})")
    lines.append("")
    return lines


# ===== MAIN =====
def main():
    print("Wave 0 Census -- mysql.50webs.com")
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    report = []
    report.append("# Wave 0 Census Report")
    report.append("")
    report.append(f"**Generated:** {now_utc}")
    report.append(f"**DB:** `{DB_NAME}` @ `{DB_HOST}`")
    report.append("**Mode:** READ-ONLY")
    report.append("")

    # Run each section with fresh connection
    report += run_section("0-A:status-dist", _0a_status)
    report += run_section("0-A:open-by-class", _0a_open_by_class)
    report += run_section("0-A:open-total", _0a_open_total)
    report += run_section("0-A:open-strategy", _0a_open_strategy)
    report += run_section("0-A:age-buckets", _0a_age_buckets)
    report += run_section("0-B:p01-ghosts", _0b_p01)
    report += run_section("0-B:p02-meta", _0b_p02)
    report += run_section("0-B:p03-phantoms", _0b_p03)
    report += run_section("0-B:large-cohorts", _0b_large)
    report += run_section("0-C:integrity", _0c_integrity)
    report += run_section("0-C:by-class", _0c_by_class)
    report += run_section("0-D:nulls", _0d_nulls)
    report += run_section("0-E:indexes", _0e_indexes)
    report += run_section("P0-5:freeze", _freeze_check)

    path = "reports/wave0_census_2026-05-08.md"
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(report))
    print(f"\n[DONE] Report: {path}  ({len(report)} lines)")


if __name__ == "__main__":
    main()
