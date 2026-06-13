#!/usr/bin/env python3
"""persist_p1_5_demotions.py — make P1-5 demotions durable in MySQL PF_PORTFOLIO.

Commit a82ac1b57f (2026-06-12) demoted 5 losing conservative portfolios to
shadow_paper_only in the per-portfolio + roster JSONs. Those JSONs are
REGENERATED from MySQL by a daily GHA workflow, so the demotions will be
silently overwritten on the next regen unless the underlying PF_PORTFOLIO
table is also updated. This script is the surgical, transactional UPDATE
that makes the demotions durable. DRY-RUN by default; pass --execute to commit.

5 demoted portfolios (per PLAN_INSIGHTS_NEXT_STEPS_TRACKER P1-5):
  aimlapi_gpt4o__conservative       PF=0.10 WR=11% sharpe=-7.09
  gh_models_gpt4o__conservative     PF=0.10 WR=11% sharpe=-7.06
  gpt4o__conservative               PF=0.11 WR=10% sharpe=-6.52
  gpt5_chat__conservative           PF=0.32 WR=20% sharpe=-4.98
  deepseek_r1__conservative         PF=0.43 WR=20% sharpe=-3.16

Borderline groq_kimi_k2__conservative (PF=0.63 Sharpe=+0.69) NOT touched.

PF_PORTFOLIO currently lacks status_reason/status_changed_at columns; the
script ALTER TABLE adds them (idempotent via information_schema check),
then UPDATEs all 5 rows in a single transaction. PREREQ: run
  python3 tools/db_backup_to_backups.py --source-db ejaguiar1_stocks --tables PF_PORTFOLIO
BEFORE executing.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pymysql  # noqa: E402
from tools.db_env import get_stocks_creds  # noqa: E402

DEMOTED = [
    "aimlapi_gpt4o__conservative",
    "gh_models_gpt4o__conservative",
    "gpt4o__conservative",
    "gpt5_chat__conservative",
    "deepseek_r1__conservative",
]
REASON = ("DEMOTED_2026-06-13 (P1-5 durable): PF<0.5, WR<=20%, negative Sharpe, "
          "n_closed>=9 — fails TIER-2. See commit a82ac1b57f + tracker P1-5.")
CHANGED_AT = "2026-06-13 04:50:00"  # MySQL DATETIME literal (UTC)
NEW_STATUS = "shadow_paper_only"

CHECK_COLS = ("SELECT COLUMN_NAME FROM information_schema.COLUMNS "
              "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'PF_PORTFOLIO' "
              "AND COLUMN_NAME IN ('status_reason', 'status_changed_at')")
ALTER_FOR = {"status_reason": "ALTER TABLE PF_PORTFOLIO ADD COLUMN status_reason TEXT NULL",
             "status_changed_at": "ALTER TABLE PF_PORTFOLIO ADD COLUMN status_changed_at DATETIME NULL"}


def _conn():
    c = get_stocks_creds()
    return pymysql.connect(
        **{k: v for k, v in c.items() if k in ("host", "user", "password", "database", "port", "connect_timeout")},
        autocommit=False)


def run(execute: bool) -> int:
    conn = _conn()
    try:
        cur = conn.cursor()
        mode = "EXECUTE" if execute else "DRY-RUN"
        print(f"[p1-5] mode={mode} target=PF_PORTFOLIO (ejaguiar1_stocks) n={len(DEMOTED)}")

        # ── Phase 1: idempotent ALTER TABLE for missing columns ──
        cur.execute(CHECK_COLS)
        have = {r[0] for r in cur.fetchall()}
        need = set(ALTER_FOR) - have
        for col in sorted(need):
            print(f"[p1-5] SQL (migration): {ALTER_FOR[col]}")
            if execute:
                cur.execute(ALTER_FOR[col])
        if not need:
            print(f"[p1-5] columns already present; skipping migration")

        # ── Phase 2: UPDATEs in a single transaction ─────────────
        print(f"[p1-5] BEGIN TRANSACTION" + ("" if execute else " (will ROLLBACK)"))
        if execute:
            cur.execute("START TRANSACTION")

        summary = []
        for name in DEMOTED:
            cur.execute("SELECT status FROM PF_PORTFOLIO WHERE portfolio_key=%s", (name,))
            row = cur.fetchone()
            if row is None:
                print(f"[p1-5]   SKIP (not in DB): {name}")
                summary.append((name, None, "NOT_FOUND"))
                continue
            if row[0] == NEW_STATUS:
                print(f"[p1-5]   SKIP (already {NEW_STATUS}): {name}")
                summary.append((name, 0, "ALREADY_DEMOTED"))
                continue
            print(f"[p1-5] SQL: UPDATE PF_PORTFOLIO SET status={NEW_STATUS!r}, "
                  f"status_reason=<P1-5 reason>, status_changed_at={CHANGED_AT!r} "
                  f"WHERE portfolio_key={name!r}")
            if execute:
                cur.execute("UPDATE PF_PORTFOLIO SET status=%s, status_reason=%s, "
                            "status_changed_at=%s WHERE portfolio_key=%s",
                            (NEW_STATUS, REASON, CHANGED_AT, name))
                summary.append((name, cur.rowcount, "UPDATED"))
            else:
                summary.append((name, None, "DRY_RUN"))

        # ── Phase 3: post-UPDATE verify (exec mode only) ─────────
        if execute:
            ph = ",".join(["%s"] * len(DEMOTED))
            cur.execute(f"SELECT portfolio_key, status, status_changed_at "
                        f"FROM PF_PORTFOLIO WHERE portfolio_key IN ({ph}) "
                        f"ORDER BY portfolio_key", DEMOTED)
            print(f"[p1-5] --- POST-UPDATE VERIFY ---")
            for r in cur.fetchall():
                print(f"  {r[0]:40s} status={r[1]:20s} changed_at={r[2]}")

        if execute:
            conn.commit()
            print(f"[p1-5] COMMIT")
        else:
            conn.rollback()
            print(f"[p1-5] DRY-RUN complete; ROLLBACK (no changes written)")

        print(f"[p1-5] --- SUMMARY ---")
        for name, rows, state in summary:
            print(f"  {name:40s} rows={rows} state={state}")
        return 0
    except Exception as exc:
        conn.rollback()
        print(f"[p1-5] ERROR: {exc}; ROLLBACK performed.", file=sys.stderr)
        return 1
    finally:
        conn.close()


def main(argv):
    ap = argparse.ArgumentParser(description="Persist P1-5 demotions to MySQL PF_PORTFOLIO")
    ap.add_argument("--execute", action="store_true",
                    help="actually commit the UPDATEs (default is dry-run/rollback)")
    args = ap.parse_args(argv)
    return run(execute=args.execute)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
