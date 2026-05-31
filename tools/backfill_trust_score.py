#!/usr/bin/env python3
"""Backfill trust_score on closed picks where it is NULL.

Uses alpha_engine.trust_score.enrich_picks_with_trust_score to compute the
score for every pick missing one. Idempotent: skips picks that already have
a non-null trust_score.

Supports two modes:
  --source <json>   Backfill JSON file (default: closed_picks_enriched.json)
  --mysql           Backfill directly in MySQL (ejaguiar1_stocks.trading_picks)

Dry-run by default. Pass --apply to actually write.

MySQL --apply path archives affected rows to ejaguiar1_backups FIRST (mandatory).

See: reports/2026-05-26_phase1_5_causal_graph_and_p0_8_hunt.md
"""
import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

TARGET_WHERE = "trust_score IS NULL"


def _backfill_json(source: str, apply: bool) -> None:
    """Backfill trust_score in a JSON file."""
    src = Path(source)
    if not src.exists():
        raise SystemExit(f"Source not found: {src}")

    data = json.loads(src.read_text())
    picks = data["picks"] if isinstance(data, dict) else data

    null_before = sum(1 for p in picks if p.get("trust_score") is None)
    already_set = len(picks) - null_before
    print(f"Total picks: {len(picks)}")
    print(f"trust_score already set: {already_set}")
    print(f"trust_score NULL: {null_before}")

    if null_before == 0:
        print("Nothing to do.")
        return

    from alpha_engine.trust_score import enrich_picks_with_trust_score  # noqa: E402

    to_fill = [p for p in picks if p.get("trust_score") is None]
    print(f"Computing trust_score for {len(to_fill)} picks...")

    enrich_picks_with_trust_score(to_fill)
    filled = sum(1 for p in to_fill if p.get("trust_score") is not None)
    print(f"Computed trust_score for: {filled} picks")

    scores = [p["trust_score"] for p in to_fill if p.get("trust_score") is not None]
    if scores:
        import statistics
        print("trust_score distribution (newly computed):")
        print(f"  min:    {min(scores)}")
        print(f"  max:    {max(scores)}")
        print(f"  mean:   {statistics.mean(scores):.2f}")
        print(f"  median: {statistics.median(scores)}")

    out_dir = Path("reports")
    out_dir.mkdir(exist_ok=True)
    diff_name = "2026-05-26_trust_score_backfill_diff" + ("" if apply else "_dryrun") + ".json"
    diff_path = out_dir / diff_name
    diff_path.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": str(src),
        "applied": apply,
        "total_picks": len(picks),
        "already_set_before": already_set,
        "filled_now": filled,
        "still_null_after": null_before - filled,
        "score_distribution": (
            {"min": min(scores), "max": max(scores), "mean": sum(scores) / len(scores), "n": len(scores)}
            if scores else None
        ),
        "sample_first_50": [
            {"id": p.get("id"), "asset_class": p.get("asset_class"), "trust_score": p.get("trust_score"), "trust_label": p.get("trust_label")}
            for p in to_fill[:50]
        ],
    }, indent=2, default=str))
    print(f"Diff written: {diff_path}")

    if apply:
        bak = src.with_suffix(".json.bak.trust_backfill")
        shutil.copy2(src, bak)
        src.write_text(json.dumps(data, indent=2))
        print(f"Applied. Backup: {bak}")
    else:
        print("Dry-run only. Re-run with --apply.")


def _row_to_pick(row: dict) -> dict:
    cat = (row.get("category") or row.get("asset_class") or "").upper()
    return {
        "id": row.get("id"),
        "symbol": row.get("symbol"),
        "strategy": row.get("strategy") or row.get("source_system") or "",
        "asset_class": cat,
        "category": cat,
        "direction": row.get("direction"),
        "confidence": row.get("confidence"),
        "elite_score": row.get("elite_score"),
        "entry_price": row.get("entry_price"),
        "timestamp": row.get("created_at"),
        "created_at": row.get("created_at"),
    }


def _backfill_mysql(apply: bool, batch_size: int = 500) -> None:
    """Backfill trust_score in MySQL via enrich_picks_with_trust_score.

    Before --apply: archives all NULL trust_score rows to ejaguiar1_backups.
    """
    try:
        from tools.db_env import get_stocks_creds
        from tools.db_backup import require_archive_before_apply
        import pymysql
    except ImportError:
        print("ERROR: pymysql not installed or db_env/db_backup not available")
        sys.exit(1)

    from alpha_engine.trust_score import enrich_picks_with_trust_score  # noqa: E402

    creds = get_stocks_creds()
    conn = pymysql.connect(**creds, cursorclass=pymysql.cursors.DictCursor)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS n FROM trading_picks WHERE trust_score IS NULL")
            null_count = cur.fetchone()["n"]
            cur.execute("SELECT COUNT(*) AS n FROM trading_picks WHERE trust_score IS NOT NULL")
            set_count = cur.fetchone()["n"]
            print(f"MySQL trading_picks: {null_count} NULL trust_score, {set_count} already set")

            if null_count == 0:
                print("Nothing to do.")
                return

            archive = require_archive_before_apply(
                source_table="trading_picks",
                where=TARGET_WHERE,
                purpose="trust_score_backfill",
                apply=apply,
                max_rows=500_000,
            )

            if not apply:
                cur.execute(
                    """
                    SELECT id, symbol, strategy, category, direction, confidence, created_at
                    FROM trading_picks WHERE trust_score IS NULL
                    ORDER BY id DESC LIMIT 10
                    """
                )
                sample = [_row_to_pick(r) for r in cur.fetchall()]
                enrich_picks_with_trust_score(sample)
                print("Dry-run sample (10 most recent NULL rows):")
                for p in sample:
                    print(f"  id={p['id']} {p.get('symbol')} trust_score={p.get('trust_score')}")
                if archive:
                    print(f"Would archive {archive.row_count} rows to ejaguiar1_backups.{archive.archive_table}")
                print(f"Would backfill up to {null_count} rows in batches of {batch_size}. Re-run with --apply.")
                return

            if not archive or not archive.applied:
                raise SystemExit("ABORT: ejaguiar1_backups archive failed or not applied — no mutations run.")

            total_updated = 0
            while True:
                cur.execute(
                    """
                    SELECT id, symbol, strategy, category, direction, confidence,
                           elite_score, entry_price, created_at
                    FROM trading_picks
                    WHERE trust_score IS NULL
                    ORDER BY id ASC
                    LIMIT %s
                    """,
                    (batch_size,),
                )
                rows = cur.fetchall()
                if not rows:
                    break
                picks = [_row_to_pick(r) for r in rows]
                enrich_picks_with_trust_score(picks)
                for p in picks:
                    ts_val = p.get("trust_score")
                    if ts_val is None:
                        continue
                    cur.execute(
                        "UPDATE trading_picks SET trust_score=%s, updated_at=NOW() "
                        "WHERE id=%s AND trust_score IS NULL",
                        (int(ts_val), p["id"]),
                    )
                    total_updated += cur.rowcount
                conn.commit()
                print(f"  batch updated={total_updated}")

            print(
                f"Applied: {total_updated} rows enriched. "
                f"Restore from ejaguiar1_backups.{archive.archive_table} if needed."
            )
    finally:
        conn.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="alpha_engine/data/closed_picks_enriched.json")
    ap.add_argument("--mysql", action="store_true", help="Backfill directly in MySQL")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--batch-size", type=int, default=500)
    args = ap.parse_args()

    if args.mysql:
        _backfill_mysql(args.apply, batch_size=args.batch_size)
    else:
        _backfill_json(args.source, args.apply)


if __name__ == "__main__":
    main()
