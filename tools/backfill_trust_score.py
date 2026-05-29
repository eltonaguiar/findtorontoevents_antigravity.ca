#!/usr/bin/env python3
"""Backfill trust_score on closed picks where it is NULL.

Uses alpha_engine.trust_score.enrich_picks_with_trust_score to compute the
score for every pick missing one. Idempotent: skips picks that already have
a non-null trust_score.

Supports two modes:
  --source <json>   Backfill JSON file (default: closed_picks_enriched.json)
  --mysql           Backfill directly in MySQL (ejaguiar1_stocks.trading_picks)

Dry-run by default. Pass --apply to actually write.

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
        print(f"trust_score distribution (newly computed):")
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


def _backfill_mysql(apply: bool, backup_db: str = None) -> None:
    """Backfill trust_score directly in MySQL trading_picks table.

    Reversible: before the destructive UPDATE, snapshots exactly the rows the
    UPDATE will touch into a UTC-timestamped backup table in the same database,
    commits the snapshot, then runs the UPDATE and asserts the affected-row count
    matches the snapshot. On mismatch it rolls back the UPDATE (keeping the
    backup table) and aborts.

    backup_db: (reserved) cross-DB archive target for future parity. The default
    behavior snapshots into the same database regardless.
    """
    try:
        from tools.db_env import get_stocks_creds
        import pymysql
    except ImportError:
        print("ERROR: pymysql not installed or db_env not available")
        sys.exit(1)

    # The rows the UPDATE will touch — used for both the snapshot and the
    # dry-run preview so they are guaranteed to describe the same set.
    target_where = "trust_score IS NULL AND trust_tier IS NOT NULL"

    creds = get_stocks_creds()
    conn = pymysql.connect(**creds, cursorclass=pymysql.cursors.DictCursor)
    try:
        with conn.cursor() as cur:
            # Count NULL trust_score rows
            cur.execute("SELECT COUNT(*) AS n FROM trading_picks WHERE trust_score IS NULL")
            null_count = cur.fetchone()["n"]
            cur.execute("SELECT COUNT(*) AS n FROM trading_picks WHERE trust_score IS NOT NULL")
            set_count = cur.fetchone()["n"]
            print(f"MySQL trading_picks: {null_count} NULL trust_score, {set_count} already set")

            if null_count == 0:
                print("Nothing to do.")
                return

            # Count exactly the rows the UPDATE will touch.
            cur.execute(f"SELECT COUNT(*) AS n FROM trading_picks WHERE {target_where}")
            snapshot_count = cur.fetchone()["n"]

            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
            backup_table = f"trust_score_backfill_bak_{ts}"

            # PR6: Derive trust_score from strategy registry.
            # Map trust_tier to numeric: PROVEN=9, ELITE=8, TRUSTED=7, DEVELOPING=5, WATCH=3, else=1
            update_sql = f"""
                UPDATE trading_picks
                SET trust_score = CASE
                    WHEN trust_tier = 'PROVEN' THEN 9
                    WHEN trust_tier = 'ELITE' THEN 8
                    WHEN trust_tier = 'TRUSTED' THEN 7
                    WHEN trust_tier = 'DEVELOPING' THEN 5
                    WHEN trust_tier = 'WATCH' THEN 3
                    ELSE 1
                END
                WHERE {target_where}
            """

            if not apply:
                # Dry-run: show what would happen, including the backup table name.
                cur.execute(f"""
                    SELECT trust_tier, COUNT(*) AS n
                    FROM trading_picks
                    WHERE {target_where}
                    GROUP BY trust_tier ORDER BY n DESC
                """)
                rows = cur.fetchall()
                print("Would update (dry-run):")
                for r in rows:
                    print(f"  {r['trust_tier']}: {r['n']} rows")
                print(f"Would total: {snapshot_count} rows")
                print(f"Would snapshot to backup table: {backup_table} (same DB)")
                if backup_db:
                    print(f"  (--backup-db reserved target noted: {backup_db}; not used in same-DB snapshot)")
                print("Re-run with --apply to execute.")
                return

            # --apply path: snapshot the exact rows first, committed before UPDATE.
            cur.execute(f"""
                CREATE TABLE `{backup_table}` AS
                SELECT id, symbol, trust_score AS old_trust_score, trust_tier,
                       UTC_TIMESTAMP() AS captured_at
                FROM trading_picks
                WHERE {target_where}
            """)
            conn.commit()
            cur.execute(f"SELECT COUNT(*) AS n FROM `{backup_table}`")
            backed_up = cur.fetchone()["n"]
            print(f"Backup table created and committed: {backup_table} ({backed_up} rows)")

            # Now run the destructive UPDATE.
            cur.execute(update_sql)
            affected = cur.rowcount
            if affected != snapshot_count:
                conn.rollback()
                raise SystemExit(
                    f"ABORT: UPDATE affected {affected} rows but snapshot captured "
                    f"{snapshot_count} rows. Rolled back the UPDATE; backup table "
                    f"`{backup_table}` is preserved for inspection."
                )
            conn.commit()
            print(f"Applied: {affected} rows updated with derived trust_score "
                  f"(matches snapshot of {snapshot_count}). Reversible via `{backup_table}`.")
    finally:
        conn.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="alpha_engine/data/closed_picks_enriched.json")
    ap.add_argument("--mysql", action="store_true", help="Backfill directly in MySQL")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--backup-db", default=None,
                    help="(reserved) cross-DB archive target, e.g. ejaguiar1_backups")
    args = ap.parse_args()

    if args.mysql:
        _backfill_mysql(args.apply, backup_db=args.backup_db)
    else:
        _backfill_json(args.source, args.apply)


if __name__ == "__main__":
    main()
