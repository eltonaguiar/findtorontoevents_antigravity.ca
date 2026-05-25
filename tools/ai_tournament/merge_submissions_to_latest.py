"""
Merge submission JSONs from data/ai_tournament/submissions/ into the
audit_dashboard/data/ai_tournament_picks_latest.json snapshot the
/audit/ai-tournament.html page (and /audit/model.html drill-down) read.

Dedup key: (model_id, symbol, submitted_at, persona_id, direction). New
submissions take precedence over older entries with the same key so re-runs
are idempotent. persona_id is part of the key because one model can submit
the same symbol from multiple personas at the same instant (e.g., Mercury
V2's voss_global_macro and sharma_quant_momentum both pick QQQ in the same
batch with different TP/SL rationales).

Run after a new submission file is added; wire into ai-tournament-pipeline.yml
between the picks-fleet step and update_leaderboard so model.html sees the
new picks without waiting for the next price-tracker pass.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SUBMISSIONS = REPO / "data" / "ai_tournament" / "submissions"
LATEST = REPO / "audit_dashboard" / "data" / "ai_tournament_picks_latest.json"


def _key(p: dict) -> tuple:
    return (
        p.get("model_id", ""),
        p.get("symbol", ""),
        p.get("submitted_at", ""),
        p.get("persona_id", ""),
        p.get("direction", ""),
    )


def main() -> None:
    if LATEST.exists():
        latest = json.loads(LATEST.read_text())
        if not isinstance(latest, list):
            latest = []
    else:
        latest = []

    index = {_key(p): i for i, p in enumerate(latest)}
    added = updated = scanned = 0

    for path in sorted(SUBMISSIONS.glob("*.json")):
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError as e:
            print(f"[merge] skip {path.name} — invalid JSON: {e}")
            continue
        picks = data.get("picks") if isinstance(data, dict) else (data if isinstance(data, list) else None)
        if not picks:
            continue
        for raw_pick in picks:
            scanned += 1
            # Carry top-level provider/model_id onto the pick if missing
            if isinstance(data, dict):
                raw_pick.setdefault("model_id", data.get("model_id", ""))
                raw_pick.setdefault("provider", data.get("provider", ""))
            k = _key(raw_pick)
            if k in index:
                latest[index[k]] = raw_pick
                updated += 1
            else:
                index[k] = len(latest)
                latest.append(raw_pick)
                added += 1

    LATEST.write_text(json.dumps(latest, indent=2))
    print(
        f"[merge] scanned {scanned} picks across {len(list(SUBMISSIONS.glob('*.json')))} submission files; "
        f"added {added}, updated {updated}, total now {len(latest)}"
    )


if __name__ == "__main__":
    main()
