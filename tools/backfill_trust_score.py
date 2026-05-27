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


def _backfill_mysql(apply: bool) -> None:
    """Backfill trust_score directly in MySQL trading_picks table."""
    try:
        from tools.db_env import stocks_creds
        import pymysql
    except ImportError:
        print("ERROR: pymysql not installed or db_env not available")
        sys.exit(1)

    creds = stocks_creds()
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

            # PR6: Derive trust_score from strategy registry.
            # Map trust_tier to numeric: PROVEN=9, ELITE=8, TRUSTED=7, DEVELOPING=5, WATCH=3, else=1
            update_sql = """
                UPDATE trading_picks
                SET trust_score = CASE
                    WHEN trust_tier = 'PROVEN' THEN 9
                    WHEN trust_tier = 'ELITE' THEN 8
                    WHEN trust_tier = 'TRUSTED' THEN 7
                    WHEN trust_tier = 'DEVELOPING' THEN 5
                    WHEN trust_tier = 'WATCH' THEN 3
                    ELSE 1
                END
                WHERE trust_score IS NULL AND trust_tier IS NOT NULL
            """
            if apply:
                cur.execute(update_sql)
                conn.commit()
                affected = cur.rowcount
                print(f"Applied: {affected} rows updated with derived trust_score")
            else:
                # Dry-run: show what would happen
                cur.execute("""
                    SELECT trust_tier, COUNT(*) AS n
                    FROM trading_picks
                    WHERE trust_score IS NULL AND trust_tier IS NOT NULL
                    GROUP BY trust_tier ORDER BY n DESC
                """)
                rows = cur.fetchall()
                print("Would update (dry-run):")
                for r in rows:
                    print(f"  {r['trust_tier']}: {r['n']} rows")
                print("Re-run with --apply to execute.")
    finally:
        conn.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="alpha_engine/data/closed_picks_enriched.json")
    ap.add_argument("--mysql", action="store_true", help="Backfill directly in MySQL")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    if args.mysql:
        _backfill_mysql(args.apply)
    else:
        _backfill_json(args.source, args.apply)


if __name__ == "__main__":
    main()
