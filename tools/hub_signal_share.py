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
import sys
from pathlib import Path

# AGENTS.md import gotcha: run as `python3 tools/hub_signal_share.py` there is no parent
# package, so `audit_trail.*` is not importable unless REPO ROOT is on sys.path.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

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


def aggregate_by_family(systems: list[dict]) -> dict:
    """Family-level attribution (operator condition iii).

    Uses audit_trail.strategy_family to map each SYSTEM name to a family. This is a JUDGEMENT,
    not a measurement, and every bucket says so. Crucially this is still name-level: the
    dashboard `systems` aggregate carries no per-pick `strategy`, so a scanner whose name says
    nothing about its internal family lands in `unknown` rather than being guessed.
    """
    try:
        from audit_trail.strategy_family import family_of, is_claim_family
    except ImportError:
        from strategy_family import family_of, is_claim_family  # type: ignore

    live = [s for s in systems if (s.get("resolved_picks") or 0) > 0]
    total = sum(s.get("resolved_picks", 0) for s in live)

    fams: dict[str, dict] = {}
    for s in live:
        fam, prov = family_of(None, s.get("name") or "")
        b = fams.setdefault(fam, {"systems": 0, "resolved": 0, "wins": 0,
                                  "gross_win": 0.0, "gross_loss": 0.0,
                                  "provenance": set(), "examples": []})
        b["systems"] += 1
        b["resolved"] += s.get("resolved_picks", 0) or 0
        b["wins"] += s.get("wins", 0) or 0
        b["gross_win"] += s.get("gross_win", 0) or 0
        b["gross_loss"] += abs(s.get("gross_loss", 0) or 0)
        b["provenance"].add(prov)
        if len(b["examples"]) < 6:
            b["examples"].append(s.get("name"))

    rows = []
    for fam, b in sorted(fams.items(), key=lambda kv: -kv[1]["resolved"]):
        rows.append({
            "family": fam,
            "is_claim_family": is_claim_family(fam),
            "systems": b["systems"],
            "resolved": b["resolved"],
            "share_pct": round(100 * b["resolved"] / total, 4) if total else None,
            "win_rate_pct": round(100 * b["wins"] / b["resolved"], 2) if b["resolved"] else None,
            "profit_factor": round(b["gross_win"] / b["gross_loss"], 4) if b["gross_loss"] else None,
            "provenance": sorted(b["provenance"]),
            "examples": b["examples"],
        })

    claim = sum(r["resolved"] for r in rows if r["is_claim_family"])
    return {
        "resolved_signals_total": total,
        "claim_families": ["momentum", "breakout", "trend_following"],
        "claim_family_resolved": claim,
        "claim_family_share_pct": round(100 * claim / total, 4) if total else None,
        "verdict": "REFUTED" if total and 100 * claim / total < 80 else "NOT REFUTED",
        "by_family": rows,
    }



def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=str(DEFAULT_INPUT))
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--by-family", action="store_true", help="attribute by strategy FAMILY (name->family judgement)")
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

    byfam = aggregate_by_family(systems) if args.by_family else None

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
        "by_family": byfam,
        "reproduce": "python3 tools/hub_signal_share.py --by-family",
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
    if byfam:
        print("\n--- BY FAMILY (name->family is a JUDGEMENT, see strategy_family_mapping.json) ---")
        for r in byfam["by_family"]:
            mark = "*" if r["is_claim_family"] else " "
            print(f" {mark} {r['family']:16s} sys={r['systems']:3d} resolved={r['resolved']:6d} "
                  f"share={str(r['share_pct']):>7s}% WR={str(r['win_rate_pct']):>6s}% PF={r['profit_factor']}")
        print(f"\n   claim families (momentum+breakout+trend) = {byfam['claim_family_resolved']} "
              f"= {byfam['claim_family_share_pct']}%  -> {byfam['verdict']} (claim: 80%+)")
    print(f"written           : {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
