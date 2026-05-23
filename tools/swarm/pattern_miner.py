"""Pattern miner — find (tier × class × regime) cells with edge.

Reads `audit_dashboard/data/swarm_picks.json`. Groups resolved picks by
(consensus_tier, asset_class, regime_at_entry.btc_regime). Highlights:
- Winning cells: WR > 60% AND n >= 5 (lowered from 10 until store grows)
- Losing cells: WR < 40% AND n >= 5

Writes:
- `reports/swarm_review/patterns_<label>.md`
- `audit_dashboard/data/swarm_pattern_tags.json` (per-pick pattern_tags hints)

Run: `python tools/swarm/pattern_miner.py [--min-n N]`
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.swarm.swarm_pick_schema import load_store, update_pattern_tags

STORE_PATH = REPO_ROOT / "audit_dashboard" / "data" / "swarm_picks.json"
PATTERNS_OUT = REPO_ROOT / "audit_dashboard" / "data" / "swarm_pattern_tags.json"
REPORTS_DIR = REPO_ROOT / "reports" / "swarm_review"


def _is_win(p: dict) -> bool | None:
    o = p.get("outcome")
    if not o or o.get("pnl_pct") is None:
        return None
    return o["pnl_pct"] > 0


def mine(picks: list[dict], min_n: int) -> dict:
    cells: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for p in picks:
        if _is_win(p) is None:
            continue
        regime = p.get("regime_at_entry", {}).get("btc_regime", "UNK")
        cells[(p["consensus_tier"], p["asset_class"], regime)].append(p)

    winning, losing, sparse = [], [], []
    for key, rows in sorted(cells.items()):
        wins = sum(1 for p in rows if _is_win(p))
        n = len(rows)
        wr = wins / n * 100
        cell = {"tier": key[0], "class": key[1], "regime": key[2],
                "n": n, "wins": wins, "win_rate_pct": round(wr, 1)}
        if n < min_n:
            sparse.append(cell)
        elif wr > 60:
            winning.append(cell)
        elif wr < 40:
            losing.append(cell)
    return {"winning": winning, "losing": losing, "sparse": sparse,
            "min_n_threshold": min_n,
            "generated_at": datetime.now(timezone.utc).isoformat()}


def write_report(patterns: dict, out_path: Path) -> None:
    lines = [f"# Swarm Pick Pattern Mining — {patterns['generated_at']}",
             f"\nMin n threshold: {patterns['min_n_threshold']}",
             "\n## Winning cells (WR > 60%)\n"]
    if patterns["winning"]:
        lines.append("| Tier | Class | Regime | n | wins | WR% |")
        lines.append("|---|---|---|---|---|---|")
        for c in patterns["winning"]:
            lines.append(f"| {c['tier']} | {c['class']} | {c['regime']} | {c['n']} | {c['wins']} | {c['win_rate_pct']} |")
    else:
        lines.append("(none yet — store needs more resolved picks)")

    lines.append("\n## Losing cells (WR < 40%)\n")
    if patterns["losing"]:
        lines.append("| Tier | Class | Regime | n | wins | WR% |")
        lines.append("|---|---|---|---|---|---|")
        for c in patterns["losing"]:
            lines.append(f"| {c['tier']} | {c['class']} | {c['regime']} | {c['n']} | {c['wins']} | {c['win_rate_pct']} |")
    else:
        lines.append("(none yet)")

    lines.append(f"\n## Sparse cells (n < {patterns['min_n_threshold']})\n")
    lines.append("| Tier | Class | Regime | n | wins | WR% |")
    lines.append("|---|---|---|---|---|---|")
    for c in patterns["sparse"]:
        lines.append(f"| {c['tier']} | {c['class']} | {c['regime']} | {c['n']} | {c['wins']} | {c['win_rate_pct']} |")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-n", type=int, default=5)
    args = parser.parse_args()

    picks = load_store(STORE_PATH)
    if not picks:
        print("No picks in store.")
        return

    patterns = mine(picks, args.min_n)
    PATTERNS_OUT.write_text(json.dumps(patterns, indent=2), encoding="utf-8")
    label = datetime.now(timezone.utc).strftime("%Y_%m_%d")
    out_path = REPORTS_DIR / f"patterns_{label}.md"
    write_report(patterns, out_path)
    # Backfill pattern_tags on every pick from the fresh miner output
    tag_result = update_pattern_tags(STORE_PATH, PATTERNS_OUT)
    print(f"Patterns: {PATTERNS_OUT}")
    print(f"Report: {out_path}")
    print(f"Winning cells: {len(patterns['winning'])}, losing: {len(patterns['losing'])}, sparse: {len(patterns['sparse'])}")
    print(f"Tagged {tag_result['tagged']} picks (winning={tag_result['winning']}, losing={tag_result['losing']}, sparse={tag_result['sparse']})")


if __name__ == "__main__":
    main()
