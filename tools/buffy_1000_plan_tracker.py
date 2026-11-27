#!/usr/bin/env python3
"""Track the $1,000 paper allocation (PLAN-2026-11-27-1000) in MySQL.

Why a dedicated table: every existing tracking table in `ejaguiar1_stocks` is bound to a
producer (`trading_picks` has 154k rows of scanner output, `consensus_tracked` is the equity
consensus feed, `audit3_forward_observations` is the tribunal's own ledger). This plan is a
single, hand-sized, pre-registered basket, so it gets its own table rather than polluting a
producer's rows.

    python3 tools/buffy_1000_plan_tracker.py --init      # create table + insert the plan
    python3 tools/buffy_1000_plan_tracker.py --resolve   # refresh prices, update returns/status
    python3 tools/buffy_1000_plan_tracker.py --show      # print current state

Paper only. Nothing here is investment advice and no order is ever placed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.request

import pymysql

PLAN_ID = "PLAN-2026-11-27-1000"
HOST = "mysql.50webs.com"
USER = "ejaguiar1_stocks"
DB = "ejaguiar1_stocks"

DDL = """
CREATE TABLE IF NOT EXISTS buffy_1000_plan (
  id INT AUTO_INCREMENT PRIMARY KEY,
  plan_id VARCHAR(64) NOT NULL,
  sleeve VARCHAR(40) NOT NULL,
  asset_class VARCHAR(16) NOT NULL,
  symbol VARCHAR(24) NOT NULL,
  instrument VARCHAR(120),
  weight_pct DECIMAL(6,2) NOT NULL DEFAULT 0,
  notional_usd DECIMAL(10,2) NOT NULL DEFAULT 0,
  entry_date DATE NOT NULL,
  entry_price DECIMAL(18,6),
  current_price DECIMAL(18,6) NULL,
  current_return_pct DECIMAL(10,4) NULL,
  target_tp_pct DECIMAL(8,2) NULL,
  target_sl_pct DECIMAL(8,2) NULL,
  max_hold_days INT NULL,
  benchmark_symbol VARCHAR(24),
  benchmark_entry_price DECIMAL(18,6) NULL,
  benchmark_return_pct DECIMAL(10,4) NULL,
  gate_to_fund VARCHAR(255),
  rationale VARCHAR(255),
  status VARCHAR(24) NOT NULL DEFAULT 'OPEN',
  exit_date DATE NULL,
  exit_price DECIMAL(18,6) NULL,
  final_return_pct DECIMAL(10,4) NULL,
  last_checked_at DATETIME NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uniq_plan_sleeve (plan_id, sleeve)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""

# Weights and prices were taken from the live tape on 2026-11-27 (Yahoo chart API).
ROWS = [
    dict(
        sleeve="CORE_BETA", asset_class="ETF", symbol="ITOT", instrument="iShares Core S&P Total US Market ETF",
        weight_pct=70.0, notional_usd=700.00, entry_price=158.64,
        target_tp_pct=25.0, target_sl_pct=-20.0, max_hold_days=365, benchmark_symbol="SPY",
        benchmark_entry_price=728.32,
        gate_to_fund=None,
        rationale="Only line the review would act on: beta at 6.7bp/yr cost, cheapest S&P-total vehicle",
    ),
    dict(
        sleeve="CASH_HURDLE", asset_class="BOND", symbol="SGOV", instrument="iShares 0-3 Month Treasury Bond ETF",
        weight_pct=30.0, notional_usd=300.00, entry_price=100.71,
        target_tp_pct=1.1, target_sl_pct=-0.5, max_hold_days=92, benchmark_symbol="SGOV",
        benchmark_entry_price=100.71,
        gate_to_fund=None,
        rationale="4.32% cash hurdle is the bar no measured strategy beat; hold it explicitly",
    ),
    dict(
        sleeve="SHADOW_CRYPTO", asset_class="CRYPTO", symbol="BTC-USD", instrument="crypto_winners LONG cell (paper)",
        weight_pct=0.0, notional_usd=0.00, entry_price=59791.46,
        target_tp_pct=None, target_sl_pct=None, max_hold_days=90, benchmark_symbol="BTC-USD",
        benchmark_entry_price=59791.46,
        gate_to_fund="DSR >= 0.95 at n >= 100 forward rows, then fund $100 from CORE_BETA",
        rationale="Only CANDIDATE in the ledger (n=37, WR 73%, +0.634%, DSR 0.666) - too thin to fund",
    ),
    dict(
        sleeve="SHADOW_ETF_TREND", asset_class="ETF", symbol="SPY", instrument="ETF trend forward clock (paper)",
        weight_pct=0.0, notional_usd=0.00, entry_price=728.32,
        target_tp_pct=None, target_sl_pct=None, max_hold_days=120, benchmark_symbol="SPY",
        benchmark_entry_price=728.32,
        gate_to_fund="net > 4.32%/yr with cost-only rows, then fund $100 from CASH_HURDLE",
        rationale="Cost-only clock: proves whether trend adds anything over holding the vehicle",
    ),
]

YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/{}?range=5d&interval=1d"


def password() -> str:
    pw = os.environ.get("DB_PASS_STOCKS", "")
    if pw:
        return pw
    for path in (os.path.expanduser("~/dbpasses.txt"), ".env.dbpw", ".env"):
        if not os.path.exists(path):
            continue
        lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
        for i, line in enumerate(lines):
            if re.search(r"DB_PASS_STOCKS|ejaguiar1_stocks.*pass", line, re.I) and "=" in line:
                return line.split("=", 1)[1].strip().strip("\"'")
    raise SystemExit("no DB password found (set DB_PASS_STOCKS)")


def connect():
    return pymysql.connect(host=HOST, user=USER, password=password(), database=DB, connect_timeout=20)


def price(symbol: str) -> float | None:
    req = urllib.request.Request(YAHOO.format(symbol), headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return float(json.loads(resp.read().decode())["chart"]["result"][0]["meta"]["regularMarketPrice"])
    except Exception:
        return None


def init() -> None:
    con = connect()
    cur = con.cursor()
    cur.execute(DDL)
    today = dt.date.today().isoformat()
    for row in ROWS:
        cur.execute(
            f"""INSERT INTO buffy_1000_plan
                (plan_id,sleeve,asset_class,symbol,instrument,weight_pct,notional_usd,entry_date,
                 entry_price,target_tp_pct,target_sl_pct,max_hold_days,benchmark_symbol,
                 benchmark_entry_price,gate_to_fund,rationale,status)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'OPEN')
                ON DUPLICATE KEY UPDATE plan_id=plan_id""",
            (PLAN_ID, row["sleeve"], row["asset_class"], row["symbol"], row["instrument"],
             row["weight_pct"], row["notional_usd"], today, row["entry_price"],
             row["target_tp_pct"], row["target_sl_pct"], row["max_hold_days"],
             row["benchmark_symbol"], row["benchmark_entry_price"], row["gate_to_fund"], row["rationale"]),
        )
    con.commit()
    cur.execute("select count(*) from buffy_1000_plan where plan_id=%s", (PLAN_ID,))
    print(f"{PLAN_ID}: {cur.fetchone()[0]} sleeves in buffy_1000_plan (db {DB}@{HOST})")
    con.close()


def resolve() -> None:
    con = connect()
    cur = con.cursor(pymysql.cursors.DictCursor)
    cur.execute("select * from buffy_1000_plan where plan_id=%s", (PLAN_ID,))
    rows = cur.fetchall()
    for row in rows:
        px = price(row["symbol"])
        bpx = price(row["benchmark_symbol"]) if row["benchmark_symbol"] else None
        if px is None:
            print(f"  {row['sleeve']}: no quote, skipped")
            continue
        entry = float(row["entry_price"] or 0)
        b_entry = float(row["benchmark_entry_price"] or 0)
        ret = (px / entry - 1) * 100 if entry else None
        bret = (bpx / b_entry - 1) * 100 if bpx and b_entry else None
        status = row["status"]
        if ret is not None and row["target_tp_pct"] is not None and ret >= float(row["target_tp_pct"]):
            status = "TP_HIT"
        elif ret is not None and row["target_sl_pct"] is not None and ret <= float(row["target_sl_pct"]):
            status = "SL_HIT"
        cur.execute(
            """update buffy_1000_plan set current_price=%s, current_return_pct=%s,
               benchmark_return_pct=%s, status=%s, last_checked_at=NOW()
               where id=%s""",
            (px, ret, bret, status, row["id"]),
        )
        print(f"  {row['sleeve']:16s} {row['symbol']:9s} {entry:>10.2f} -> {px:>10.2f}  {ret:+7.2f}%  {status}")
    con.commit()
    con.close()


def show() -> None:
    con = connect()
    cur = con.cursor()
    cur.execute("""select sleeve,symbol,weight_pct,notional_usd,entry_date,entry_price,current_price,
                          current_return_pct,benchmark_symbol,benchmark_return_pct,status
                   from buffy_1000_plan where plan_id=%s order by notional_usd desc, sleeve""", (PLAN_ID,))
    for row in cur.fetchall():
        print("  ", row)
    con.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--init", action="store_true")
    ap.add_argument("--resolve", action="store_true")
    ap.add_argument("--show", action="store_true")
    a = ap.parse_args()
    if a.init:
        init()
    if a.resolve:
        resolve()
    if a.show:
        show()
    if not (a.init or a.resolve or a.show):
        ap.print_help(); sys.exit(1)
