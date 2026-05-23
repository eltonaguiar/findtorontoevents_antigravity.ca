#!/usr/bin/env python3
"""Deduplicate closed_picks.archive.jsonl.

Keeps only the first occurrence of each pick ID. Picks without an 'id'
field are kept (only once). Malformed lines are dropped.

Usage:
    python tools/dedup_archive.py [--dry-run]

With --dry-run, reports stats but does not modify the file.
"""
import argparse
import json
from pathlib import Path

# Default archive path (aligned with forward_validator.py)
DEFAULT_ARCHIVE = Path(__file__).resolve().parent.parent / "alpha_engine" / "data" / "closed_picks.archive.jsonl"


def dedup_archive(path: Path, dry_run: bool = False) -> dict:
    """Deduplicate a JSONL archive, keeping the first occurrence of each ID.

    Returns stats dict with counts.
    """
    if not path.exists():
        print(f"Archive not found: {path}")
        return {"error": "file not found"}

    seen_ids: set[str] = set()
    unique_lines: list[str] = []
    total_lines = 0
    malformed = 0
    malformed_line_nums: list[int] = []  # Track line numbers of malformed entries
    no_id_count = 0
    duplicate_count = 0
    kept_count = 0

    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            total_lines += 1
            raw = line.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                malformed += 1
                malformed_line_nums.append(line_num)
                continue

            pid = obj.get("id", "")
            if not pid:
                # Picks without an ID: keep them (they're rare and we can't dedup)
                no_id_count += 1
                unique_lines.append(raw)
                kept_count += 1
                continue

            if pid in seen_ids:
                duplicate_count += 1
                continue

            seen_ids.add(pid)
            unique_lines.append(raw)
            kept_count += 1

    stats = {
        "total_lines": total_lines,
        "unique_kept": kept_count,
        "duplicates_removed": duplicate_count,
        "malformed_dropped": malformed,
        "malformed_line_nums": malformed_line_nums[:20] if malformed_line_nums else [],  # First 20 only
        "no_id_kept": no_id_count,
        "unique_ids": len(seen_ids),
        "dedup_ratio": f"{duplicate_count / total_lines * 100:.1f}%" if total_lines > 0 else "N/A",
    }

    if malformed_line_nums:
        shown = malformed_line_nums[:20]
        suffix = f" (showing first {len(shown)} of {len(malformed_line_nums)})" if len(malformed_line_nums) > 20 else ""
        print(f"  Malformed lines at: {shown}{suffix}")

    if dry_run:
        print(f"[DRY RUN] Would deduplicate {path}:")
    else:
        # Write deduped content back (atomic-ish: write then rename)
        tmp = path.with_suffix(".jsonl.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            for line in unique_lines:
                f.write(line)
                f.write("\n")
        tmp.replace(path)
        print(f"Deduplicated {path}:")

    for k, v in stats.items():
        if k == "malformed_line_nums":
            continue  # Already printed above
        print(f"  {k}: {v}")

    return stats


def main():
    parser = argparse.ArgumentParser(description="Deduplicate closed_picks.archive.jsonl")
    parser.add_argument("--dry-run", action="store_true", help="Report stats without modifying the file")
    parser.add_argument("--path", type=Path, default=DEFAULT_ARCHIVE, help="Path to archive JSONL file")
    args = parser.parse_args()

    dedup_archive(args.path, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
