#!/usr/bin/env python3
"""
refresh_cftc_cot.py — DB-landing collector for CFTC Commitments-of-Traders (COT).

Lands weekly COT positioning into ejaguiar1_stocks.cftc_cot_weekly (a NEW table)
so the commercial-hedger / non-commercial positioning signal (a SANCTIONED
non-crypto edge source per the /audit incident guard; Briese; CFTC) can accrue.

Reuses the tested CFTC Socrata fetch + parse from tools/cot_fetcher_socrata.py
(fetch_cot + SYMBOL_MAP) — no new HTTP/parse logic. Unlike that script (which
writes per-symbol JSON to audit_dashboard/data/), this lands DIRECTLY into the
DB via idempotent upsert, keyed on (symbol, report_date) — the prior-Tuesday
data-date, NOT the fetch date, which is the documented COT timing-leakage guard
(reports/cot_timing_leakage_audit_2026-05-13.md).

PRICE-SIDE CAVEAT: a COT-positioning backtest needs a commodity-FUTURES price
feed (GC/CL/CT/...) to resolve outcomes; we do not yet have a dense one. This
collector lands the SIGNAL feed; the price side is a separate operator gap.

Usage:
    python3 tools/refresh_cftc_cot.py --dry-run
    python3 tools/refresh_cftc_cot.py --execute --weeks 260   # ~5yr backfill
    python3 tools/refresh_cftc_cot.py --execute               # weekly incremental (default 12w)
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import pymysql

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.db_env import get_stocks_creds
from tools.cot_fetcher_socrata import fetch_cot, SYMBOL_MAP

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger("refresh_cftc_cot")

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS `cftc_cot_weekly` (
  `id` int NOT NULL AUTO_INCREMENT,
  `symbol` varchar(20) NOT NULL,
  `market_name` varchar(255) NOT NULL DEFAULT '',
  `report_date` date NOT NULL,
  `open_interest` bigint NOT NULL DEFAULT 0,
  `noncomm_long` bigint NOT NULL DEFAULT 0,
  `noncomm_short` bigint NOT NULL DEFAULT 0,
  `noncomm_net` bigint NOT NULL DEFAULT 0,
  `comm_long` bigint NOT NULL DEFAULT 0,
  `comm_short` bigint NOT NULL DEFAULT 0,
  `comm_net` bigint NOT NULL DEFAULT 0,
  `noncomm_net_pct_of_oi` decimal(8,2) NOT NULL DEFAULT 0.00,
  `comm_net_pct_of_oi` decimal(8,2) NOT NULL DEFAULT 0.00,
  `ingested_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_cot` (`symbol`,`report_date`),
  KEY `idx_report_date` (`report_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
"""

UPSERT_SQL = """
INSERT INTO cftc_cot_weekly
  (symbol, market_name, report_date, open_interest, noncomm_long, noncomm_short,
   noncomm_net, comm_long, comm_short, comm_net, noncomm_net_pct_of_oi, comm_net_pct_of_oi)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
ON DUPLICATE KEY UPDATE
  market_name=VALUES(market_name), open_interest=VALUES(open_interest),
  noncomm_long=VALUES(noncomm_long), noncomm_short=VALUES(noncomm_short),
  noncomm_net=VALUES(noncomm_net), comm_long=VALUES(comm_long),
  comm_short=VALUES(comm_short), comm_net=VALUES(comm_net),
  noncomm_net_pct_of_oi=VALUES(noncomm_net_pct_of_oi),
  comm_net_pct_of_oi=VALUES(comm_net_pct_of_oi)
"""


def get_db():
    keep = ("host", "user", "password", "database", "port", "connect_timeout")
    return pymysql.connect(**{k: v for k, v in get_stocks_creds().items() if k in keep})


def to_row(d):
    rd = d.get("report_date")
    if not rd:
        return None  # report_date is NOT NULL / part of the unique key
    return (
        str(d.get("symbol", ""))[:20], str(d.get("market_name") or "")[:255], rd,
        int(d.get("open_interest") or 0),
        int(d.get("noncomm_long") or 0), int(d.get("noncomm_short") or 0), int(d.get("noncomm_net") or 0),
        int(d.get("comm_long") or 0), int(d.get("comm_short") or 0), int(d.get("comm_net") or 0),
        float(d.get("noncomm_net_pct_of_oi") or 0), float(d.get("comm_net_pct_of_oi") or 0),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Land CFTC COT weekly positioning into cftc_cot_weekly")
    ap.add_argument("--dry-run", action="store_true", help="Preview only; no write")
    ap.add_argument("--execute", action="store_true", help="Write to DB")
    ap.add_argument("--weeks", type=int, default=12, help="Weeks of COT history per symbol (260=~5yr)")
    ap.add_argument("--symbols", default="", help="Comma list (default: all of SYMBOL_MAP)")
    args = ap.parse_args()
    dry = not args.execute or args.dry_run

    symbols = ([s.strip().upper() for s in args.symbols.split(",") if s.strip()]
               if args.symbols else sorted(SYMBOL_MAP.keys()))
    logger.info("refresh_cftc_cot | dry_run=%s | %d symbols | weeks=%d", dry, len(symbols), args.weeks)

    conn = get_db()
    if not dry:
        with conn.cursor() as cur:
            cur.execute(CREATE_TABLE_SQL)
            conn.commit()

    total = 0
    ok = fail = 0
    for sym in symbols:
        try:
            recs = fetch_cot(sym, weeks=args.weeks)
        except Exception as exc:
            logger.warning("%s: fetch error %s", sym, str(exc)[:80]); fail += 1; continue
        rows = [r for r in (to_row(d) for d in recs) if r]
        if rows and not dry:
            with conn.cursor() as cur:
                cur.executemany(UPSERT_SQL, rows)
                conn.commit()
        total += len(rows)
        ok += 1
        logger.info("%s -> %d weekly rows %s", sym, len(rows), "(would upsert)" if dry else "upserted")
        time.sleep(0.2)
    logger.info("Done | symbols ok=%d fail=%d | rows %s=%d",
                ok, fail, "(would upsert)" if dry else "upserted", total)
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
