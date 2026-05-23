#!/usr/bin/env python3
"""ETL checksum + zero-PnL example collector (Day 1-2 of Week 1).

Per `reports/grok_solo_week1_checklist_2026-05-12.md` Day 1 task:
"reproduce & document zero-PnL bug (20 examples)" + Day 2 task:
"basic quality report (markdown + diff)".

Outputs:
- `reports/zero_pnl_examples_<UTC>.md` — 20 spot-check rows per asset class
- `reports/etl_checksum_<UTC>.json` — per-class checksums for diff

NO writes to DB. Read-only diagnostic.

Usage:
    python tools/data_audit/etl_checksum.py
    python tools/data_audit/etl_checksum.py --class CRYPTO --sample 50
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import pymysql
except ImportError:
    print("ERROR: pymysql not installed", file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parents[2]

TERMINAL_STATUSES = ("WON", "LOST", "WIN", "LOSS", "TP_HIT", "SL_HIT", "EXPIRED",
                     "closed_win", "closed_loss")
ASSET_CLASSES = ("CRYPTO", "EQUITY", "FOREX", "COMMODITY", "FUTURES", "ETF",
                 "BOND", "MEMECOIN", "PENNY_STOCK")


def connect():
    return pymysql.connect(
        host=os.environ.get("DB_STOCKS_HOST", "mysql.50webs.com"),
        user=os.environ.get("DB_STOCKS_USER", "ejaguiar1_stocks"),
        password=os.environ.get("DB_STOCKS_PASSWORD", "stocks"),
        database=os.environ.get("DB_STOCKS_NAME", "ejaguiar1_stocks"),
        port=int(os.environ.get("DB_STOCKS_PORT", "3306")),
        connect_timeout=30,
        read_timeout=120,
    )


def collect_zero_pnl_examples(cur, asset_class: str, sample: int = 20):
    """Pull `sample` rows where pnl_pct=0 + terminal status. Classify each
    into one of 4 causes per Mimo Day 2 framework:
    (a) Execution failure (exit_price IS NULL or 0)
    (b) Resolver bug (exit_price>0 AND exit_price != entry_price AND pnl_pct=0)
    (c) Data gap (timestamp mismatch indicators)
    (d) Legitimate zero (exit_price == entry_price)
    """
    placeholders = ",".join(["%s"] * len(TERMINAL_STATUSES))
    cur.execute(f"""
        SELECT id, strategy, symbol, direction, entry_price, exit_price,
               pnl_pct, status, exit_reason, created_at, closed_at
        FROM trading_picks
        WHERE asset_class = %s
          AND status IN ({placeholders})
          AND pnl_pct = 0
        ORDER BY RAND()
        LIMIT %s
    """, (asset_class,) + TERMINAL_STATUSES + (sample,))
    rows = cur.fetchall()

    classified = []
    for r in rows:
        entry = float(r.get("entry_price") or 0)
        exit_p = float(r.get("exit_price") or 0)
        if exit_p <= 0:
            cause = "a_execution_failure"
        elif entry > 0 and abs(exit_p - entry) > 1e-9:
            cause = "b_resolver_bug"
        elif entry > 0 and abs(exit_p - entry) < 1e-9:
            cause = "d_legitimate_zero"
        else:
            cause = "c_data_gap"
        classified.append({**{k: str(v) if v is not None else None for k, v in r.items()},
                           "cause": cause})
    return classified


def compute_class_checksum(cur, asset_class: str):
    """Per-class quality fingerprint for diff-tracking."""
    placeholders = ",".join(["%s"] * len(TERMINAL_STATUSES))
    cur.execute(f"""
        SELECT
            COUNT(*) AS n_total,
            SUM(CASE WHEN pnl_pct = 0 THEN 1 ELSE 0 END) AS n_zero_pnl,
            SUM(CASE WHEN exit_price IS NULL OR exit_price = 0 THEN 1 ELSE 0 END) AS n_missing_exit,
            SUM(CASE WHEN status IN ('WON','TP_HIT','WIN','closed_win') AND pnl_pct < 0 THEN 1 ELSE 0 END) AS n_won_with_neg_pnl,
            SUM(CASE WHEN status IN ('LOST','SL_HIT','LOSS','closed_loss') AND pnl_pct > 0 THEN 1 ELSE 0 END) AS n_lost_with_pos_pnl,
            MIN(created_at) AS first_created_at,
            MAX(created_at) AS last_created_at,
            MAX(closed_at) AS last_closed_at
        FROM trading_picks
        WHERE asset_class = %s
          AND status IN ({placeholders})
    """, (asset_class,) + TERMINAL_STATUSES)
    row = cur.fetchone()
    if not row:
        return None
    fingerprint_str = "|".join(str(row.get(k)) for k in sorted(row.keys()))
    fingerprint = hashlib.sha256(fingerprint_str.encode()).hexdigest()[:16]
    return {"asset_class": asset_class, "fingerprint": fingerprint,
            **{k: (str(v) if isinstance(v, datetime) else v) for k, v in row.items()}}


def write_examples_md(examples_by_class: dict, out_path: Path):
    lines = [
        f"# Zero-PnL Examples (per-class spot-check) — {datetime.now(timezone.utc).isoformat()}",
        "",
        "Per Mimo Day 2 framework, classified into 4 causes:",
        "- (a) execution_failure — exit_price NULL/0",
        "- (b) resolver_bug — exit_price>0 AND differs from entry but pnl_pct=0 (writer dropped recompute)",
        "- (c) data_gap — entry_price missing or other gap signature",
        "- (d) legitimate_zero — exit_price == entry_price (true break-even)",
        "",
    ]
    for ac, examples in examples_by_class.items():
        if not examples:
            continue
        lines.append(f"## {ac} ({len(examples)} examples)")
        lines.append("")
        lines.append("| id | strategy | symbol | direction | entry | exit | status | exit_reason | cause |")
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for r in examples[:20]:
            lines.append(
                f"| {r.get('id', '?')[:24]} | {r.get('strategy', '?')[:24]} | {r.get('symbol', '?')} | "
                f"{r.get('direction', '?')} | {r.get('entry_price', '?')} | {r.get('exit_price', '?')} | "
                f"{r.get('status', '?')} | {r.get('exit_reason', '?')[:16] if r.get('exit_reason') else '-'} | "
                f"{r.get('cause', '?')} |"
            )
        lines.append("")
        # Cause distribution
        from collections import Counter
        cause_dist = Counter(r["cause"] for r in examples)
        lines.append("Cause distribution: " + ", ".join(f"{c}={n}" for c, n in cause_dist.most_common()))
        lines.append("")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"# wrote {out_path}", file=sys.stderr)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--class", dest="asset_class", default=None,
                   help="Restrict to one asset class (default: all)")
    p.add_argument("--sample", type=int, default=20, help="Examples per class (default 20)")
    p.add_argument("--out-examples", default=None)
    p.add_argument("--out-checksum", default=None)
    args = p.parse_args()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_examples = Path(args.out_examples) if args.out_examples else (
        ROOT / f"reports/zero_pnl_examples_{stamp}.md"
    )
    out_checksum = Path(args.out_checksum) if args.out_checksum else (
        ROOT / f"reports/etl_checksum_{stamp}.json"
    )

    try:
        conn = connect()
    except Exception as e:
        print(f"DB connect failed: {e}", file=sys.stderr)
        sys.exit(1)

    cur = conn.cursor(pymysql.cursors.DictCursor)
    classes = [args.asset_class] if args.asset_class else list(ASSET_CLASSES)

    examples_by_class = {}
    checksums = []
    for ac in classes:
        try:
            examples_by_class[ac] = collect_zero_pnl_examples(cur, ac, args.sample)
            ck = compute_class_checksum(cur, ac)
            if ck:
                checksums.append(ck)
            print(f"# {ac}: {len(examples_by_class[ac])} examples + checksum", file=sys.stderr)
        except Exception as e:
            print(f"# {ac} failed: {e}", file=sys.stderr)
    cur.close()
    conn.close()

    write_examples_md(examples_by_class, out_examples)

    out_checksum.parent.mkdir(parents=True, exist_ok=True)
    out_checksum.write_text(
        json.dumps({"generated_at": datetime.now(timezone.utc).isoformat(),
                    "checksums": checksums}, indent=2, default=str),
        encoding="utf-8"
    )
    print(f"# wrote {out_checksum}", file=sys.stderr)


if __name__ == "__main__":
    main()
