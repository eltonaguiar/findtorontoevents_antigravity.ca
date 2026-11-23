"""
Reproduce the "momentum/breakout/Ichimoku generate 0.6% of signals" figure.

WHY THIS EXISTS
---------------
The operator ruling of 2026-11-23 accepted the reasoning but graded the 0.6% claim
PROVISIONAL, not measured, because its input (audit_dashboard/data/dashboard_data.json)
is a generated artifact that is NOT tracked on main. A reader who clones the repo cannot
re-run the number, so it was not a source.

This script closes that: it emits the input's sha256, its generated_at, and the exact
row counts, so the claim can be checked against any copy of the payload — and re-derived
if someone regenerates it. Output is small enough to commit.

The distinction the ruling draws, and I am honouring:
  * uncommitted artifact + bare number  -> PROVISIONAL
  * committed input, or hash + row count + aggregation script -> MEASURED

WHAT THIS DOES NOT PROVE
------------------------
It measures the share of resolved signals whose SOURCE/SYSTEM NAME matches
momentum|breakout. System names are scanner names, not strategy families. So this
refutes the hub's claim *as expressed through system names* and says nothing about
whether momentum logic runs inside a scanner named something else. That gap is the
finding, not a caveat to be argued away.

Usage:
    python3 tools/hub_signal_share.py
    python3 tools/hub_signal_share.py --input path/to/dashboard_data.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

DEFAULT_INPUT = Path("audit_dashboard/data/dashboard_data.json")
OUT = Path("reports/hub_signal_share_2026-11-23.json")

MOMENTUM = re.compile(r"momentum|breakout", re.I)
ICHIMOKU = re.compile(r"ichimoku", re.I)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def aggregate(systems: list[dict]) -> dict:
    live = [s for s in systems if (s.get("resolved_picks") or 0) > 0]
    total = sum(s.get("resolved_picks", 0) for s in live)

    def bucket(pred) -> dict:
        sel = [s for s in live if pred(s.get("name") or "")]
        r = sum(s.get("resolved_picks", 0) for s in sel)
        w = sum(s.get("wins", 0) or 0 for s in sel)
        gw = sum(s.get("gross_win", 0) or 0 for s in sel)
        gl = sum(abs(s.get("gross_loss", 0) or 0) for s in sel)
        return {
            "systems": len(sel),
            "resolved": r,
            "share_pct": round(100 * r / total, 4) if total else None,
            "win_rate_pct": round(100 * w / r, 2) if r else None,
            "profit_factor": round(gw / gl, 4) if gl else None,
            "system_names": sorted(s.get("name") for s in sel)[:20],
        }

    return {
        "systems_total": len(systems),
        "systems_with_resolved": len(live),
        "resolved_signals_total": total,
        "momentum_or_breakout": bucket(lambda n: bool(MOMENTUM.search(n))),
        "ichimoku": bucket(lambda n: bool(ICHIMOKU.search(n))),
        "everything_else": bucket(lambda n: not MOMENTUM.search(n) and not ICHIMOKU.search(n)),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=str(DEFAULT_INPUT))
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    p = Path(args.input)
    if not p.exists():
        raise SystemExit(
            f"input not found: {p}\n"
            "This payload is a GENERATED artifact and is not tracked on main. "
            "Regenerate it, or point --input at a copy. Without it the 0.6% figure "
            "cannot be re-derived and must be reported as PROVISIONAL."
        )

    d = json.loads(p.read_text())
    systems = d.get("systems") or []
    if not isinstance(systems, list) or not systems:
        raise SystemExit(f"no 'systems' list in {p} -- payload shape changed?")

    agg = aggregate(systems)
    mb, ic = agg["momentum_or_breakout"], agg["ichimoku"]
    combined = None
    if agg["resolved_signals_total"]:
        combined = round(
            100 * (mb["resolved"] + ic["resolved"]) / agg["resolved_signals_total"], 4
        )

    out = {
        "claim_under_test": (
            "live-vs-research.html: 'strategies that FAILED forward testing "
            "(momentum, breakout, Ichimoku) are generating 80%+ of our signals'"
        ),
        "measured_combined_share_pct": combined,
        "verdict": "REFUTED" if (combined is not None and combined < 80) else "NOT REFUTED",
        "input": {
            "path": str(p),
            "sha256": sha256_of(p),
            "bytes": p.stat().st_size,
            "generated_at": d.get("generated_at"),
        },
        "aggregation": agg,
        "limitation": (
            "Matches SYSTEM NAMES, not strategy families. Refutes the claim as expressed "
            "through system names; cannot see momentum logic inside a differently-named "
            "scanner. Family attribution is lost at resolved-history level."
        ),
        "reproduce": "python3 tools/hub_signal_share.py",
    }

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=1))

    print(f"input sha256      : {out['input']['sha256']}")
    print(f"generated_at      : {out['input']['generated_at']}")
    print(f"systems           : {agg['systems_total']} total / {agg['systems_with_resolved']} with resolved>0")
    print(f"resolved signals  : {agg['resolved_signals_total']}")
    print(f"momentum|breakout : {mb['resolved']} = {mb['share_pct']}%")
    print(f"ichimoku          : {ic['resolved']} = {ic['share_pct']}%  ({ic['systems']} systems)")
    print(f"combined          : {combined}%  -> {out['verdict']} (claim: 80%+)")
    print(f"written           : {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
