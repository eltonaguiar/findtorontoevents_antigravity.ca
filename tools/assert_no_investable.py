#!/usr/bin/env python3
"""assert_no_investable.py — make the "0 investable" verdict an executable invariant.

CI guard: load the ranked picks and FAIL LOUDLY if any pick ever passes all five gates.
This is deliberately inverted from a normal test: today the correct state is 0 passes, so
a pass means either (a) a genuine breakthrough that must be reviewed by a human, or
(b) a regression in the gate logic. Either way it must not happen silently.

Exit 0 = invariant holds (0 full passes, as expected).
Exit 1 = a pick passed all gates OR the report is missing/malformed -> investigate.
"""
import argparse, json, sys
from pathlib import Path

GATES = {"G1", "G2", "G3", "G4", "G5"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rankings", default="reports/asset_class_rankings.json")
    ap.add_argument("--out", default="reports/investable_invariant.json")
    a = ap.parse_args()
    p = Path(a.rankings)
    if not p.exists():
        print(f"FAIL: rankings not found at {p}", file=sys.stderr); return 1
    try:
        d = json.loads(p.read_text())
    except Exception as e:
        print(f"FAIL: rankings unparseable: {e}", file=sys.stderr); return 1
    picks = d.get("picks") or []
    if not picks:
        print("FAIL: no picks in rankings (stale or empty artefact)", file=sys.stderr); return 1
    winners = []
    malformed = []
    for pk in picks:
        g = pk.get("gates") or {}
        if set(g) != GATES:
            malformed.append(pk.get("symbol")); continue
        if all(g[k] is True for k in GATES):
            winners.append(pk.get("symbol"))
    out = {"rankings": str(p), "n_picks": len(picks),
           "n_full_pass": len(winners), "full_pass_symbols": winners,
           "n_malformed": len(malformed), "malformed_symbols": malformed,
           "invariant": "0 investable", "holds": (len(winners) == 0 and len(malformed) == 0)}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=2) + "\n")
    if malformed:
        print(f"FAIL: {len(malformed)} picks have malformed gate blocks: {malformed[:8]}", file=sys.stderr)
        return 1
    if winners:
        print(f"ALARM: {len(winners)} pick(s) pass all five gates: {winners} — human review required",
              file=sys.stderr)
        return 1
    print(f"OK: invariant holds — {len(picks)} picks, 0 full passes, 0 malformed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
