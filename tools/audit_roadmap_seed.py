#!/usr/bin/env python3
"""Seed audit_roadmap_items from incidents_enhancements_feed.json + EAGLE audit PRs.

Usage:
  python tools/audit_roadmap_seed.py --dry-run
  python tools/audit_roadmap_seed.py --apply

Requires: tools/sql/audit_roadmap_items.sql applied once on ejaguiar1_stocks.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FEED = ROOT / "audit_dashboard" / "data" / "incidents_enhancements_feed.json"

EAGLE_EXTRA = [
    ("ENHANCEMENT", "CRYPTO", "P1", "OPEN", None,
     "Enable CONFIDENCE_INVERT_CRYPTO in smart-picks GHA",
     "Ranker inverts CRYPTO confidence (incident #17).",
     "alpha_engine/smart_picks_engine.py",
     "Set CONFIDENCE_INVERT_CRYPTO=1 in smart-picks-tracker.yml",
     "Smart Picks CRYPTO WR aligns with 0.5-0.6 conf bucket",
     "updates/2026-05-27-crypto-confidence-invert-ranker.md", "cursor-composer"),
    ("ENHANCEMENT", "EQUITY", "P1", "DONE", None,
     "VIX regime active gate on passes_active_gate",
     "Block EQUITY/ETF active picks when VIX>22.",
     "audit_trail/quality_gates.py",
     "passes_vix_regime_active_gate wired; default ON",
     "High-VIX EQUITY momentum picks blocked at admission",
     "reports/EAGLE-2026-05-27T02-25-00_EST-cursor-composer-strategy-audit.md", "cursor-composer"),
    ("ENHANCEMENT", "EQUITY", "P1", "DONE", None,
     "Speculative EQUITY quarantine (GME/AMC/NIO/…)",
     "Block mis-tagged EQUITY on RESEARCH_ONLY_SPECULATIVE_SYMBOLS.",
     "alpha_engine/config.py",
     "passes_speculative_equity_gate in passes_active_gate",
     "Zero production EQUITY picks on gap-risk symbols",
     "reports/EAGLE-2026-05-27T02-25-00_EST-cursor-composer-strategy-audit.md", "cursor-composer"),
    ("MILESTONE", "OVERALL", "P0", "OPEN", "M-001",
     "BTC UTC hour death-zone filter",
     "Reject CRYPTO picks 08-09Z; boost 22Z bucket.",
     "alpha_engine/score_booster.py",
     "Wire M-001 env gate from 90-day CRYPTO plan",
     "CRYPTO PF +0.1-0.2 on policy-clean cohort",
     "reports/asset_class_90day_plan_CRYPTO_2026-05-15.md", "cursor-composer"),
]


def _conn():
    import pymysql
    password = os.environ.get("DB_STOCKS_PASSWORD") or os.environ.get("DB_PASS_STOCKS") or ""
    if not password:
        raise RuntimeError("DB credentials missing")
    return pymysql.connect(
        host=os.environ.get("DB_STOCKS_HOST", "mysql.50webs.com"),
        port=int(os.environ.get("DB_STOCKS_PORT", "3306")),
        user=os.environ.get("DB_STOCKS_USER", "ejaguiar1_stocks"),
        password=password,
        database=os.environ.get("DB_STOCKS_NAME", "ejaguiar1_stocks"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def _load_rows() -> list[tuple]:
    rows: list[tuple] = []
    if FEED.exists():
        data = json.loads(FEED.read_text(encoding="utf-8"))
        for item in data.get("incidents", {}).get("OVERALL", []):
            rows.append((
                "INCIDENT",
                item.get("asset_class") or "OVERALL",
                item.get("severity") or "P2",
                item.get("status") or "OPEN",
                None,
                item.get("title", "")[:255],
                item.get("description"),
                item.get("affected_component"),
                item.get("recommended_fix"),
                None,
                item.get("link_md_path"),
                item.get("reported_by") or "feed",
            ))
        for cls, items in (data.get("enhancements") or {}).items():
            if not isinstance(items, list):
                continue
            for item in items:
                rows.append((
                    "ENHANCEMENT",
                    item.get("asset_class") or cls,
                    "P1",
                    item.get("status") or "OPEN",
                    None,
                    item.get("title", "")[:255],
                    item.get("description"),
                    item.get("category"),
                    item.get("success_metric"),
                    item.get("success_metric"),
                    item.get("link_md_path"),
                    item.get("proposed_by") or "feed",
                ))
    rows.extend(EAGLE_EXTRA)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    rows = _load_rows()
    print(f"Loaded {len(rows)} roadmap rows")
    if args.dry_run or not args.apply:
        for r in rows[:5]:
            print(" ", r[0], r[1], r[5][:60])
        if not args.apply:
            print("DRY-RUN — use --apply")
            return 0
    conn = _conn()
    ins = upd = 0
    try:
        cur = conn.cursor()
        for (itype, ac, pri, st, mnum, title, desc, comp, fix, metric, evpath, reporter) in rows:
            cur.execute("SELECT id FROM audit_roadmap_items WHERE title=%s AND asset_class=%s LIMIT 1", (title, ac))
            ex = cur.fetchone()
            if ex:
                cur.execute(
                    """UPDATE audit_roadmap_items SET item_type=%s, priority=%s, status=%s, m_number=%s,
                       description=%s, affected_component=%s, recommended_fix=%s, success_metric=%s,
                       evidence_path=%s, reported_by=%s WHERE id=%s""",
                    (itype, pri, st, mnum, desc, comp, fix, metric, evpath, reporter, ex["id"]),
                )
                upd += 1
            else:
                cur.execute(
                    """INSERT INTO audit_roadmap_items
                       (item_type, asset_class, priority, status, m_number, title, description,
                        affected_component, recommended_fix, success_metric, evidence_path, reported_by)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (itype, ac, pri, st, mnum, title, desc, comp, fix, metric, evpath, reporter),
                )
                ins += 1
        conn.commit()
    finally:
        conn.close()
    print(f"Inserted {ins}, updated {upd}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
