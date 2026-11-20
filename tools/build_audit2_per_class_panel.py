#!/usr/bin/env python3
"""Add the ``per_class_verdicts`` block to audit3_ledger.json (audit2 Phase B).

The /audit2 page is static HTML+JS that renders audit3's ledger client-side, so
every number it shows must already be in the payload. This tool is the payload
generation side for the per-class verdict panel: it joins

  * the canonical per-class rollup — ``class_rollup()`` in
    ``alpha_engine/resolved_closed_view.py``, computed over the same shared cost
    model — for n / win rate / profit factor / mean net, and
  * the ledger's own ``classes`` (G0-G9 tribunal, bootstrap CI) for the verdict
    word and the confidence interval, and ``cells`` for cell counts,

and writes the result back into the ledger as ONE additional top-level key.

Why a join and not a recomputation: two implementations of the same statistic
is how two numbers start disagreeing (see the /audit vs /audit3 3x-on-ETF
incident documented at the top of resolved_closed_view.py). Nothing here is
recomputed — the rollup fields are copied verbatim, and the renderer must copy
them verbatim too.

Additive by construction: existing keys are loaded and written back unchanged;
only ``per_class_verdicts`` is added.

Usage:
    python3 tools/build_audit2_per_class_panel.py \\
        --ledger audit_dashboard/data/audit3_ledger.json \\
        --payload /tmp/audit3/dashboard_data.json \\
        [--rows /tmp/audit3/resolved_closed_picks_net.json]

``--rows`` (the canonical rows sidecar) is preferred. When it is absent the
payload is read instead: its embedded canonical block is used if the sidecar
next to it hashes correctly, otherwise the export slice is filtered through the
same ``is_performance_scored_row`` predicate the canonical view and the
tribunal both call — and the block records which of these happened.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from alpha_engine.resolved_closed_view import (  # noqa: E402
    CLASS_COST_BPS,
    COST_MODEL,
    POPULATION,
    WIN_DEFINITION,
    build_view,
    class_rollup,
    is_performance_scored_row,
    load_sidecar,
)

SCHEMA = "audit2.per_class_verdicts.v1"

#: Mirrors audit3_tribunal.WR_MIN_N: below this the tribunal itself treats a
#: cell as untested, so a class verdict resting on fewer rows is reported as
#: "inconclusive" rather than as a word that implies a judgement was made.
MIN_N_FOR_VERDICT = 20

FIELD_SOURCES = {
    "n": "class_rollup (resolved_closed_view) over the canonical rows",
    "mean_net_pct": "class_rollup — percent per trade, net of round-trip cost",
    "win_rate_pct": "class_rollup — wins on GROSS pnl, decided trades only",
    "profit_factor": "class_rollup — gross win sum / |gross loss sum|",
    "mean_cost_bps": "class_rollup — mean round-trip cost applied per row",
    "net_ci_pct": "audit3 ledger classes[].net_ci_pct — G2 bootstrap, 2000 resamples",
    "verdict": "audit3 ledger classes[].verdict — G0-G9 tribunal",
    "n_cells": "audit3 ledger cells[] grouped by asset_class",
    "n_cells_tested": "audit3 ledger cells[] with n >= 20 (WR_MIN_N)",
}


def _load_rows_from_payload(payload_path: str) -> tuple[list[dict], str]:
    """Canonical rows from a dashboard payload, with the path that produced them."""
    with open(payload_path, encoding="utf-8") as f:
        data = json.load(f)
    block = data.get("resolved_closed_picks_net") if isinstance(data, dict) else None
    if isinstance(block, dict):
        view = load_sidecar(payload_path, block)
        if view and isinstance(view.get("rows"), list):
            return view["rows"], "canonical_sidecar"
    picks: list = []
    for key_path in (("picks", "recent_closed"), ("picks",), ("candidates",),
                     ("records",), ("closed_picks",)):
        cur = data
        for k in key_path:
            cur = cur.get(k) if isinstance(cur, dict) else None
            if cur is None:
                break
        if isinstance(cur, list):
            picks = cur
            break
    view = build_view(picks, generated_at="", validity=is_performance_scored_row)
    return view["rows"], "payload_slice_canonical_predicate"


def _verdict_word(verdict: str | None, n: int | None) -> tuple[str, str]:
    """(display word, note). Never invents a judgement the tribunal did not make."""
    if verdict is None:
        return "no verdict", "class absent from the tribunal's classes block"
    if n is not None and n < MIN_N_FOR_VERDICT:
        return "inconclusive", f"n={n} < {MIN_N_FOR_VERDICT} — too few rows to judge"
    if str(verdict).upper() == "INSUFFICIENT_N":
        return "inconclusive", "tribunal verdict is INSUFFICIENT_N"
    return str(verdict), ""


def build_per_class_verdicts(ledger: dict, rows: list[dict],
                             rows_source: str = "canonical_rows") -> dict:
    """The ``per_class_verdicts`` block. Pure: no I/O, so the test can drive it."""
    rollup = class_rollup(rows or [])

    class_verdicts: dict[str, dict] = {}
    for c in (ledger.get("classes") or []):
        if isinstance(c, dict) and c.get("asset_class"):
            class_verdicts[str(c["asset_class"]).upper()] = c

    cell_counts: dict[str, dict] = {}
    for cell in (ledger.get("cells") or []):
        if not isinstance(cell, dict):
            continue
        ac = str(cell.get("asset_class") or "UNKNOWN").upper()
        slot = cell_counts.setdefault(ac, {"n_cells": 0, "n_cells_tested": 0})
        slot["n_cells"] += 1
        n = cell.get("n")
        if isinstance(n, (int, float)) and n >= MIN_N_FOR_VERDICT:
            slot["n_cells_tested"] += 1

    den = ((ledger.get("coverage") or {}).get("denominator") or {})
    entries: list[dict] = []
    for cls in sorted(set(rollup) | set(class_verdicts) | set(cell_counts)):
        roll = rollup.get(cls)
        ver = class_verdicts.get(cls)
        n = roll["n"] if roll else (ver.get("n") if ver else None)
        raw_verdict = ver.get("verdict") if ver else None
        word, note = _verdict_word(raw_verdict, n)
        entry = {
            "asset_class": cls,
            "n": n,
            # Rollup-derived: copied, never recomputed.
            "mean_net_pct": roll["mean_net_pct"] if roll else None,
            "win_rate_pct": roll["win_rate_pct"] if roll else None,
            "profit_factor": roll["profit_factor"] if roll else None,
            "mean_cost_bps": roll["mean_cost_bps"] if roll else None,
            "wins": roll["wins"] if roll else None,
            "losses": roll["losses"] if roll else None,
            "flat": roll["flat"] if roll else None,
            # Ledger-derived.
            "net_ci_pct": ver.get("net_ci_pct") if ver else None,
            "verdict": raw_verdict,
            "verdict_word": word,
            "verdict_note": note,
            "n_cells": cell_counts.get(cls, {}).get("n_cells"),
            "n_cells_tested": cell_counts.get(cls, {}).get("n_cells_tested"),
            "in_rollup": roll is not None,
            "in_tribunal": ver is not None,
            "field_sources": dict(FIELD_SOURCES),
        }
        entries.append(entry)

    entries.sort(key=lambda e: (-(e["n"] or 0), e["asset_class"]))

    return {
        "schema": SCHEMA,
        "generated_at": ledger.get("generated_at"),
        "mode": den.get("mode"),
        "ledger_mode_note": ("The denominator mode decides whether these numbers describe "
                             "the canonical book or the export slice. Phase A exists "
                             "because that difference is not cosmetic."),
        "units": {
            "mean_net_pct": "percent per trade, NET of round-trip cost",
            "win_rate_pct": "percent of decided trades (excludes flat)",
            "net_ci_pct": "percent per trade, 95% bootstrap interval",
            "mean_cost_bps": "basis points per trade",
        },
        "population": POPULATION,
        "cost_model": COST_MODEL,
        "class_cost_bps": dict(sorted(CLASS_COST_BPS.items())),
        "win_definition": WIN_DEFINITION,
        "rows_source": rows_source,
        "rows_counted": len(rows or []),
        "classes": entries,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ledger", required=True, help="audit3_ledger.json (rewritten in place, additively)")
    ap.add_argument("--payload", help="dashboard_data.json, used when --rows is absent")
    ap.add_argument("--rows", help="resolved_closed_picks_net.json (canonical rows)")
    args = ap.parse_args(argv)

    with open(args.ledger, encoding="utf-8") as f:
        ledger = json.load(f)

    rows: list[dict] = []
    rows_source = "unavailable"
    if args.rows and Path(args.rows).exists():
        with open(args.rows, encoding="utf-8") as f:
            view = json.load(f)
        rows = view.get("rows") or []
        rows_source = "canonical_rows_sidecar"
    elif args.payload and Path(args.payload).exists():
        rows, rows_source = _load_rows_from_payload(args.payload)

    if not rows:
        print("::warning title=audit2::no canonical rows available — "
              "per_class_verdicts will carry verdicts only", file=sys.stderr)

    ledger["per_class_verdicts"] = build_per_class_verdicts(ledger, rows, rows_source)
    with open(args.ledger, "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=1, sort_keys=True, allow_nan=False)
        f.write("\n")
    print(f"per_class_verdicts: {len(ledger['per_class_verdicts']['classes'])} classes "
          f"from {rows_source} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
