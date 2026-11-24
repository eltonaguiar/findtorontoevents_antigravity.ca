#!/usr/bin/env python3
"""kill_list_reconcile.py — publish the union of the two kill vocabularies, and who reads each.

Why this exists
---------------
External review v3 observed that the two kill lists share exactly one name
(`futures_momentum`) and asked for them to be reconciled. They are **two different
instruments**, and merging them would make both worse:

* `alpha_engine/strategy_kill_list.json` — name-level blocklist. `institutional_kills`
  are manual quant-review decisions (2026-05-28 P0 sweep), `auto_kill_strategies` come
  from the honest kill switch. No direction, no n, no expectancy, no asset class.
  Read by `alpha_engine/strategy_suppression.py::load_kill_list` and by the S1 loader
  in `alpha_engine/production_scanner.py`.
* `audit_dashboard/data/audit3_ledger.json` — expectancy-based, **direction-aware**
  cells from the realized closed ledger (audit3 tribunal). Each kill carries n,
  net %/trade and a BH harm q. Read by `alpha_engine/audit3_denylist.py::denied_reason`.

`luxalgo_confluence` is the proof they cannot be one list: audit3 kills it LONG and
keeps it as a CANDIDATE SHORT. A name-only list cannot express that, and folding the
legacy names into audit3's doctrine would promote decisions made on different data
into a different statistical contract.

So the reconciliation is published, not merged: this tool prints the union with
provenance per name. A name in **neither** list is the only genuinely unguarded case,
and this report makes that set visible instead of implicit.

Usage:
  python3 tools/kill_list_reconcile.py            # human-readable summary
  python3 tools/kill_list_reconcile.py --json     # machine-readable, stable keys
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LEGACY = REPO / "alpha_engine" / "strategy_kill_list.json"
LEDGER = REPO / "audit_dashboard" / "data" / "audit3_ledger.json"

# Which code actually enforces each list. Kept here so the answer to "who blocks
# this name?" is one grep away instead of folklore.
READERS = {
    "legacy_strategy_kill_list": [
        "alpha_engine/strategy_suppression.py::load_kill_list",
        "alpha_engine/production_scanner.py (S1 institutional kill list loader)",
    ],
    "audit3_ledger": [
        "alpha_engine/audit3_denylist.py::denied_reason",
        "tools/audit3_denylist_health.py (CI armed/staleness check)",
    ],
}

SEMANTICS = {
    "legacy_strategy_kill_list": {
        "granularity": "strategy name",
        "direction_aware": False,
        "basis": "manual quant review (2026-05-28 P0) + honest kill switch",
        "carries": ["name"],
    },
    "audit3_ledger": {
        "granularity": "strategy x direction cell (plus class and symbol scopes)",
        "direction_aware": True,
        "basis": "realized closed ledger expectancy after measured costs (BH harm q <= 0.10)",
        "carries": ["n", "net_expectancy_pct", "harm_q", "direction", "asset_class"],
    },
}


def _key(name: str) -> str:
    return (name or "").strip().casefold()


def load_legacy(path: Path = LEGACY) -> dict[str, list[str]]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, list[str]] = {}
    for bucket in ("institutional_kills", "auto_kill_strategies"):
        for name in doc.get(bucket) or []:
            if isinstance(name, str) and name.strip():
                out.setdefault(_key(name), []).append(bucket)
    for name in ((doc.get("honest_kill_switch") or {}).get("newly_killed") or []):
        if isinstance(name, str) and name.strip():
            out.setdefault(_key(name), []).append("honest_kill_switch.newly_killed")
    return out


def load_audit3(path: Path = LEDGER) -> tuple[dict[str, list[dict]], dict[str, dict]]:
    """Return (strategy kills by name, class kills)."""
    doc = json.loads(path.read_text(encoding="utf-8"))
    kills: dict[str, list[dict]] = {}
    for cell in doc.get("cells") or []:
        if not isinstance(cell, dict) or cell.get("verdict") != "KILL":
            continue
        name = _key(str(cell.get("strategy") or ""))
        if not name:
            continue
        kills.setdefault(name, []).append({
            "asset_class": cell.get("asset_class"),
            "direction": cell.get("direction"),
            "n": cell.get("n"),
            "net_expectancy_pct": cell.get("net_expectancy_pct"),
            "harm_q": cell.get("harm_q"),
        })
    classes: dict[str, dict] = {}
    for kill in (doc.get("kill_tribunal") or {}).get("kills") or []:
        if not isinstance(kill, dict) or str(kill.get("scope") or "").lower() != "class":
            continue
        ac = str(kill.get("asset_class") or "").upper()
        if ac:
            classes[ac] = {"n": kill.get("n"), "net_expectancy_pct": kill.get("net_expectancy_pct")}
    return kills, classes


def reconcile(legacy_path: Path = LEGACY, ledger_path: Path = LEDGER) -> dict:
    legacy = load_legacy(legacy_path)
    a3, classes = load_audit3(ledger_path)
    overlap = sorted(set(legacy) & set(a3))
    return {
        "legacy_path": str(legacy_path.relative_to(REPO)),
        "ledger_path": str(ledger_path.relative_to(REPO)),
        "readers": READERS,
        "semantics": SEMANTICS,
        "counts": {
            "legacy_names": len(legacy),
            "audit3_kill_cells_named": len(a3),
            "audit3_kill_rows": sum(len(v) for v in a3.values()),
            "audit3_kill_classes": len(classes),
            "overlap": len(overlap),
            "union": len(set(legacy) | set(a3)),
        },
        "overlap": {name: {"legacy": legacy[name], "audit3": a3[name]} for name in overlap},
        "audit3_only": {name: a3[name] for name in sorted(set(a3) - set(legacy))},
        "legacy_only_count": len(set(legacy) - set(a3)),
        "class_kills": classes,
        "note": ("Kept separate on purpose: the legacy list is name-only policy, the audit3 "
                 "ledger is direction-aware expectancy. Overlap is expected to be small "
                 "because the two universes differ; a name in neither list is the only "
                 "unguarded case."),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Union of the two kill vocabularies, with provenance")
    ap.add_argument("--json", action="store_true", help="print stable JSON")
    ap.add_argument("--legacy", default=str(LEGACY))
    ap.add_argument("--ledger", default=str(LEDGER))
    args = ap.parse_args()

    try:
        rep = reconcile(Path(args.legacy), Path(args.ledger))
    except (OSError, ValueError) as exc:
        print(f"cannot reconcile kill lists: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(rep, indent=2))
        return 0

    c = rep["counts"]
    print(f"legacy {rep['legacy_path']}: {c['legacy_names']} names")
    print(f"audit3 {rep['ledger_path']}: {c['audit3_kill_cells_named']} killed strategies "
          f"({c['audit3_kill_rows']} cells), {c['audit3_kill_classes']} killed classes")
    print(f"overlap: {c['overlap']}   union: {c['union']}\n")
    for name, hit in rep["overlap"].items():
        print(f"  BOTH  {name}")
        print(f"        legacy: {', '.join(hit['legacy'])}")
        for cell in hit["audit3"]:
            print(f"        audit3: {cell['asset_class']} {cell['direction']} n={cell['n']} "
                  f"net={cell['net_expectancy_pct']}%/trade q={cell['harm_q']}")
    print()
    for name, cells in rep["audit3_only"].items():
        print(f"  audit3-only  {name}")
        for cell in cells:
            print(f"        {cell['asset_class']} {cell['direction']} n={cell['n']} "
                  f"net={cell['net_expectancy_pct']}%/trade")
    print(f"\n  legacy-only: {rep['legacy_only_count']} names")
    if rep["class_kills"]:
        print(f"  class kills: {', '.join(sorted(rep['class_kills']))}")
    print(f"\n{rep['note']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
