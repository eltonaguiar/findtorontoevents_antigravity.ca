#!/usr/bin/env python3
"""Backfill trust_score on closed picks where it is NULL.

Uses alpha_engine.trust_score.enrich_picks_with_trust_score to compute the
score for every pick missing one. Idempotent: skips picks that already have
a non-null trust_score.

Dry-run by default. Pass --apply to actually write the file.

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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="alpha_engine/data/closed_picks_enriched.json")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    src = Path(args.source)
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

    # Compute on the rows that need it
    from alpha_engine.trust_score import enrich_picks_with_trust_score  # noqa: E402

    to_fill = [p for p in picks if p.get("trust_score") is None]
    print(f"Computing trust_score for {len(to_fill)} picks...")

    enriched = enrich_picks_with_trust_score(to_fill)
    # enrich_picks_with_trust_score mutates in place, but be defensive
    filled = sum(1 for p in to_fill if p.get("trust_score") is not None)
    print(f"Computed trust_score for: {filled} picks")

    # Summary stats
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
    diff_name = "2026-05-26_trust_score_backfill_diff" + ("" if args.apply else "_dryrun") + ".json"
    diff_path = out_dir / diff_name
    diff_path.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": str(src),
        "applied": args.apply,
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

    if args.apply:
        bak = src.with_suffix(".json.bak.trust_backfill")
        shutil.copy2(src, bak)
        src.write_text(json.dumps(data, indent=2))
        print(f"Applied. Backup: {bak}")
    else:
        print("Dry-run only. Re-run with --apply.")


if __name__ == "__main__":
    main()
