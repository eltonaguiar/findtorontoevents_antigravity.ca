"""
One-time backfill for the existing picks snapshot.

The merge/ingest pipeline now normalizes every NEW pick, but historical rows
already in audit_dashboard/data/ai_tournament_picks_latest.json keep their old
values until re-merged (seed rows are no longer in the submission files, so they
never get re-normalized). This script applies the same normalize_pick() pass to
the snapshot and flags the corrupt-timestamp seed rows.

DRY-RUN BY DEFAULT — prints a diff summary and writes nothing. Pass --apply to
write the file back (a .bak copy is made first).

  python tools/ai_tournament/backfill_normalize_picks.py            # dry run
  python tools/ai_tournament/backfill_normalize_picks.py --apply     # write

What it changes:
  - direction / asset_class / symbol-class / empty persona  -> canonical
  - resolved_at < submitted_at  -> data_integrity_flag = "TS_ANOMALY"
    (flagged only; timestamps are NOT rewritten, so stats consumers can exclude
     these rather than trust fabricated times)
"""
from __future__ import annotations

import json
import shutil
import sys
from collections import Counter
from pathlib import Path

from normalize import is_timestamp_anomaly, normalize_pick

REPO = Path(__file__).resolve().parents[2]
LATEST = REPO / "audit_dashboard" / "data" / "ai_tournament_picks_latest.json"
APPLY = "--apply" in sys.argv
TS_FLAG = "TS_ANOMALY"


def main() -> None:
    picks = json.loads(LATEST.read_text())
    changes: Counter[str] = Counter()
    examples: dict[str, str] = {}

    for p in picks:
        before = (p.get("direction"), p.get("asset_class"), str(p.get("persona_id", "")))
        normalize_pick(p)
        after = (p.get("direction"), p.get("asset_class"), str(p.get("persona_id", "")))
        if before[0] != after[0]:
            changes["direction"] += 1
            examples.setdefault("direction", f"{before[0]} -> {after[0]}")
        if before[1] != after[1]:
            changes["asset_class"] += 1
            examples.setdefault("asset_class", f"{p.get('symbol')}: {before[1]} -> {after[1]}")
        if before[2] != after[2]:
            changes["persona_id"] += 1

        if is_timestamp_anomaly(p) and p.get("data_integrity_flag") != TS_FLAG:
            p["data_integrity_flag"] = TS_FLAG
            changes["ts_anomaly_flagged"] += 1

    print(f"[backfill] {len(picks)} picks scanned")
    for k, v in sorted(changes.items()):
        ex = f"  (e.g. {examples[k]})" if k in examples else ""
        print(f"[backfill]   {k}: {v}{ex}")
    if not changes:
        print("[backfill] nothing to change")
        return

    if not APPLY:
        print("[backfill] DRY RUN — no file written. Re-run with --apply to write.")
        return

    bak = LATEST.with_suffix(".json.bak")
    shutil.copy2(LATEST, bak)
    LATEST.write_text(json.dumps(picks, indent=2))
    print(f"[backfill] wrote {LATEST} (backup at {bak.name})")


if __name__ == "__main__":
    main()
