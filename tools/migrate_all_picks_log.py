"""One-shot migration: split ml_crypto_predictor/enhanced_models/live_picks/all_picks_log.json
into a slim hot file (OPEN/ACTIVE only) plus monthly gzipped cold shards
for terminal-status picks.

Idempotent — re-running on the new structure produces the same output.

Run:
    python -m tools.migrate_all_picks_log
"""

from __future__ import annotations

import gzip
import json
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
PICKS_DIR = REPO / "ml_crypto_predictor" / "enhanced_models" / "live_picks"
HOT_FILE = PICKS_DIR / "all_picks_log.json"
COLD_DIR = PICKS_DIR / "closed"

TERMINAL_STATUSES = {"WIN", "WON", "LOSS", "LOST", "CLOSED", "EXPIRED",
                     "TP_HIT", "SL_HIT"}


def _is_closed(p: dict) -> bool:
    status = str(p.get("status") or "").upper()
    outcome = str(p.get("outcome") or "").upper()
    return status in TERMINAL_STATUSES or outcome in TERMINAL_STATUSES


def _month_key(p: dict) -> str:
    """Pick the most-meaningful timestamp for monthly bucketing."""
    for k in ("closed_at", "generated_at", "created_at", "timestamp"):
        v = p.get(k)
        if not v:
            continue
        try:
            ts = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            return ts.strftime("%Y%m")
        except (ValueError, TypeError):
            continue
    return "unknown"


def _load_existing_shard(path: Path) -> list:
    if not path.exists():
        return []
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return json.load(f) or []
    with path.open(encoding="utf-8") as f:
        return json.load(f) or []


def _dedup_key(p: dict) -> str:
    return str(p.get("id") or "") or f"{p.get('symbol')}|{p.get('timeframe')}|{p.get('generated_at')}"


def migrate() -> dict:
    if not HOT_FILE.exists():
        return {"hot_size_before": 0, "skipped": "no_input"}

    size_before = HOT_FILE.stat().st_size
    print(f"Loading {HOT_FILE} ({size_before/1e6:.1f} MB)...")
    with HOT_FILE.open(encoding="utf-8") as f:
        all_picks = json.load(f) or []
    print(f"  loaded {len(all_picks)} picks")

    COLD_DIR.mkdir(parents=True, exist_ok=True)

    hot: list = []
    cold_by_month: dict[str, list] = defaultdict(list)
    for p in all_picks:
        if not isinstance(p, dict):
            continue
        if _is_closed(p):
            cold_by_month[_month_key(p)].append(p)
        else:
            hot.append(p)

    # Merge into any pre-existing cold shards, dedup by id.
    written_shards = []
    for month, picks in cold_by_month.items():
        shard_path = COLD_DIR / f"closed_{month}.json.gz"
        existing = _load_existing_shard(shard_path)
        seen = {_dedup_key(p): p for p in existing}
        for p in picks:
            seen[_dedup_key(p)] = p
        merged = list(seen.values())
        with gzip.open(shard_path, "wt", encoding="utf-8") as f:
            json.dump(merged, f, indent=2, default=str)
        written_shards.append((shard_path, len(merged), shard_path.stat().st_size))

    # Write slim hot file.
    with HOT_FILE.open("w", encoding="utf-8") as f:
        json.dump(hot, f, indent=2, default=str)

    size_after = HOT_FILE.stat().st_size

    return {
        "hot_size_before": size_before,
        "hot_size_after": size_after,
        "hot_count_after": len(hot),
        "cold_shards": [
            {"path": str(p.relative_to(REPO)), "n": n, "size": s}
            for p, n, s in written_shards
        ],
    }


def main():
    result = migrate()
    print(json.dumps(result, indent=2, default=str))
    before = result.get("hot_size_before", 0)
    after = result.get("hot_size_after", 0)
    if before and after:
        print(f"\nHot file: {before/1e6:.1f} MB -> {after/1e6:.1f} MB")
        print(f"Reduction: {(1 - after/before)*100:.1f}%")


if __name__ == "__main__":
    main()
