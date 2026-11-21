#!/usr/bin/env python3
"""Reconcile the two cell-count artifacts that feed DSR trial counts.

Two artifacts both claim to report "how many cells did we test", and they
disagree by up to 3x:

  audit_dashboard/data/audit3_ledger.json :: cells
      One row per (asset_class, strategy, direction, namespace) that survived
      audit3's own inclusion filters.  367 rows / 342 distinct pairs on the
      2026-11-21 ledger.  Strategy labels come from the picks' own `strategy`
      string (e.g. "vwap-reclaim-scout", "EMA 9/21 bullish crossover, ...").

  audit_dashboard/data/pf_registry.json
      :: by_asset_class_strategy_policy_clean_net
      One row per (asset_class, strategy), policy-clean, deduped, net of
      slippage.  695 rows on the 2026-11-21 registry.  Strategy labels come
      from `at_raw_picks.source_system`, a different taxonomy.

Why the arbitration matters: DSR (Deflated Sharpe Ratio) deflates the best
observed statistic by the number of trials N and is monotone decreasing in N.
Whichever artifact supplies N therefore decides pass/fail.  That is the whole
CRYPTO flip:

    N=14   -> DSR 0.9978  PASS
    N=629  -> DSR 0.9284  FAIL

(reports/2026-11-21-dsr-trial-baseline-flip.md).

WHAT THE 2026-11-21 PAIR ACTUALLY SHOWED
    The tool was written expecting audit3's cells to be a FILTERED SUBSET of
    the pf_registry population (audit3 keeps only cells passing an
    n/significance filter, so it should under-count).  That expectation was
    WRONG, and the check exists precisely so a wrong expectation cannot be
    assumed into the record:

        audit3 pairs           342
        pf_registry pairs      695
        shared                 124
        audit3-only            218     <- pf_registry does NOT carry these
        pf-only                571

    The counts disagree in BOTH directions, so the two artifacts are not at
    different filter settings of one population -- they are two taxonomies.
    audit3 has 54 EQUITY strategy labels where pf_registry has 19; pf_registry
    has 629 CRYPTO labels where audit3 has 210.  Neither count is "the" trial
    count and the 3x "disagreement" is not a filter artefact.  The known root
    cause is documented in the repo: the registry derives strategy names from
    `at_raw_picks.source_system` while the pipeline emits its own strategy
    strings, and no crosswalk exists
    (reports/peer_claude-phase2-perf-crypto_result_2026-05-31.md).

DECISION ENCODED HERE -- what supplies N
    PRIMARY  N = distinct (asset_class, strategy) in
             pf_registry.by_asset_class_strategy_policy_clean_net.

             Rationale: DSR corrects the selection that produced the reported
             statistic, and that statistic is computed from pf_registry
             (alpha_engine/money_ready_verdict.py reads this book).  Trials
             that never entered the book the verdict reads did not contribute
             to the maximum being deflated.

    UPPER    N_union = distinct pairs in (audit3 cells U pf_registry cells).
    BOUND    Reported alongside, every run, as a sensitivity.  This is the
             count to adopt if a crosswalk shows audit3-only labels are
             genuinely distinct strategies rather than renamed duplicates.
             Union is the conservative direction: raising N can only kill a
             class, never save one.

    The union under-counts duplicates and the primary under-counts the true
    search space; until a strategy crosswalk exists, the honest statement is a
    bracketed N, and the primary is the lower end of it.

Usage:
    python tools/trial_population_reconcile.py
    python tools/trial_population_reconcile.py --json out.json --md report.md
    python tools/trial_population_reconcile.py --strict   # exit 1 on drift
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "audit_dashboard" / "data" / "audit3_ledger.json"
REGISTRY = ROOT / "audit_dashboard" / "data" / "pf_registry.json"

REGISTRY_KEY = "by_asset_class_strategy_policy_clean_net"
SYMBOL_KEY = "by_asset_class_strategy_symbol"

# Grain of the primary definition.  Change only with a matching update to
# money_ready_verdict.NB_TRIALS_BY_CLASS and a new flip report.
TRIAL_GRAIN = "asset_class x strategy"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def audit3_pairs(ledger: dict) -> tuple[set[tuple[str, str]], int]:
    """Reduce audit3 cells to (asset_class, strategy) pairs.

    audit3 splits a cell by direction (LONG/SHORT) and namespace
    (discovery/confirmatory), so one strategy can occupy several rows.  Both
    splits are subdivisions of one trial, not extra trials: the strategy was
    chosen once and then reported by direction.  Row count is returned
    separately so the split is visible rather than silently discarded.
    """
    pairs: set[tuple[str, str]] = set()
    rows = 0
    for c in ledger.get("cells") or []:
        if not isinstance(c, dict):
            continue
        cls = str(c.get("asset_class") or "").strip().upper()
        strat = str(c.get("strategy") or "").strip()
        if not cls or not strat:
            continue
        rows += 1
        pairs.add((cls, strat))
    return pairs, rows


def registry_rows(registry: dict, key: str = REGISTRY_KEY) -> list[dict]:
    return [r for r in (registry.get(key) or []) if isinstance(r, dict)]


def registry_pairs(registry: dict, key: str = REGISTRY_KEY) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for r in registry_rows(registry, key):
        cls = str(r.get("asset_class") or "").strip().upper()
        strat = str(r.get("strategy") or "").strip()
        if cls and strat:
            pairs.add((cls, strat))
    return pairs


def reconcile(ledger: dict, registry: dict) -> dict:
    a3, a3_rows = audit3_pairs(ledger)
    pf = registry_pairs(registry)
    sym = registry_pairs(registry, SYMBOL_KEY)
    union = a3 | pf

    cells_by_cls: dict[str, int] = {}
    for c in ledger.get("cells") or []:
        if isinstance(c, dict):
            cls = str(c.get("asset_class") or "").strip().upper()
            if cls:
                cells_by_cls[cls] = cells_by_cls.get(cls, 0) + 1

    by_class: dict[str, dict] = {}
    for cls in sorted({c for c, _ in union}):
        a3_cls = {s for c, s in a3 if c == cls}
        pf_cls = {s for c, s in pf if c == cls}
        sym_cls = {s for c, s in sym if c == cls}
        only_a3 = sorted(a3_cls - pf_cls)
        by_class[cls] = {
            "n_trials_primary": len(pf_cls),
            "n_trials_union_upper_bound": len(a3_cls | pf_cls),
            "pf_strategies": len(pf_cls),
            "audit3_strategies": len(a3_cls),
            "audit3_cell_rows": cells_by_cls.get(cls, 0),
            "pf_symbol_strategies": len(sym_cls),
            "shared": len(a3_cls & pf_cls),
            "audit3_only_count": len(only_a3),
            "audit3_only": only_a3,
            "pf_only_count": len(pf_cls - a3_cls),
            "audit3_over_pf_pct": (
                round(100.0 * len(a3_cls) / len(pf_cls), 1) if pf_cls else None),
        }

    return {
        "trial_grain": TRIAL_GRAIN,
        "primary_definition": (
            "distinct (asset_class, strategy) in pf_registry."
            f"{REGISTRY_KEY} -- the book the class verdict reads"),
        "upper_bound_definition": (
            "distinct (asset_class, strategy) in audit3 cells U pf_registry "
            "policy-clean cells -- adopt if a crosswalk proves the "
            "audit3-only labels are distinct strategies"),
        "subset_hypothesis_holds": not (a3 - pf),
        "finding": (
            "audit3 cells are a filtered subset of pf_registry; it under-counts "
            "by construction and must never supply N"
            if not (a3 - pf) else
            "NOT a filter: the artifacts use different strategy taxonomies and "
            "disagree in both directions, so neither is the trial count on its "
            "own and N is bracketed [primary, union]"),
        "affected_subset": sorted(a3 - pf),
        "totals": {
            "audit3_cell_rows": a3_rows,
            "audit3_strategies": len(a3),
            "pf_strategy_cells": len(pf),
            "pf_symbol_strategy_cells": len(sym),
            "shared": len(a3 & pf),
            "audit3_only": len(a3 - pf),
            "pf_only": len(pf - a3),
            "union_upper_bound": len(union),
            "reduction_audit3_rows_to_pairs": (
                round(a3_rows / len(a3), 2) if a3 else None),
            "undercount_if_pf_used_pct": (
                round(100.0 * (1 - len(pf) / len(union)), 1) if union else None),
        },
        "by_class": by_class,
        "n_trials_primary_by_class": {
            c: v["n_trials_primary"] for c, v in by_class.items()},
        "n_trials_union_by_class": {
            c: v["n_trials_union_upper_bound"] for c, v in by_class.items()},
        "open_fix": (
            "Build a strategy-name crosswalk (at_raw_picks.source_system <-> "
            "pipeline `strategy` string). Until it exists the two artifacts "
            "cannot be compared and N stays bracketed."),
    }


def render_md(res: dict, ledger: dict, registry: dict) -> str:
    t = res["totals"]
    lines = [
        "# Trial-population reconciliation — audit3 cells vs pf_registry strategies",
        "",
        f"- audit3 ledger generated: `{ledger.get('generated_at')}`",
        f"- pf_registry generated: `{registry.get('generated_utc')}`",
        f"- Grain: `{res['trial_grain']}`",
        f"- **Primary N:** {res['primary_definition']}",
        f"- **Upper bound:** {res['upper_bound_definition']}",
        "",
        "## Finding",
        "",
        res["finding"],
        "",
        "| quantity | count |",
        "|---|---|",
        f"| audit3 `cells` rows (direction × namespace split) | {t['audit3_cell_rows']} |",
        f"| audit3 distinct (class, strategy) | {t['audit3_strategies']} |",
        f"| pf_registry policy-clean (class, strategy) | {t['pf_strategy_cells']} |",
        f"| pf_registry (class, strategy, symbol) | {t['pf_symbol_strategy_cells']} |",
        f"| shared | {t['shared']} |",
        f"| **audit3-only** (pf does not carry) | **{t['audit3_only']}** |",
        f"| **pf-only** (audit3 does not score) | **{t['pf_only']}** |",
        f"| union (upper bound) | {t['union_upper_bound']} |",
        "",
        f"The disagreement is mutual, so it is not a filter setting: audit3 rows "
        f"collapse {t['reduction_audit3_rows_to_pairs']}x onto pairs (direction/"
        f"namespace are subdivisions), and the two label sets overlap on only "
        f"{t['shared']} of {t['union_upper_bound']} pairs "
        f"({round(100.0*t['shared']/t['union_upper_bound'],1) if t['union_upper_bound'] else 0}%).",
        "",
        "## Per class",
        "",
        "| class | N primary | N union | pf | audit3 | audit3/pf | shared | audit3-only |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for cls, v in res["by_class"].items():
        pct = "n/a" if v["audit3_over_pf_pct"] is None else f"{v['audit3_over_pf_pct']}%"
        lines.append(
            f"| {cls} | **{v['n_trials_primary']}** | {v['n_trials_union_upper_bound']} | "
            f"{v['pf_strategies']} | {v['audit3_strategies']} | {pct} | "
            f"{v['shared']} | {v['audit3_only_count']} |")
    lines += [
        "",
        "## Subset test",
        "",
        ("PASS — every audit3 pair exists in pf_registry."
         if res["subset_hypothesis_holds"] else
         f"FAIL — {t['audit3_only']} audit3 pairs are absent from pf_registry. "
         "The two artifacts are two taxonomies, not two filter settings. "
         "Sample of pairs only audit3 scored:"),
        "",
    ]
    if not res["subset_hypothesis_holds"]:
        for cls, strat in res["affected_subset"][:12]:
            lines.append(f"- `{cls}` / `{strat}`")
        lines.append("")
    lines += [
        "## Why not the other available grains",
        "",
        f"- `by_asset_class_strategy_symbol` ({t['pf_symbol_strategy_cells']} "
        "cells): the scanner selects at strategy level; one strategy firing on "
        "40 symbols is one decision examined, not 40. Using it triple-counts "
        "and is not comparable to the strategy rows the verdict reads.",
        "- audit3 `cells`: it is not a filter of the registry book and it is not "
        "a superset of it either. It cannot supply N alone.",
        "- Neither count alone. The honest statement is a bracket: N_primary "
        f"{t['pf_strategy_cells']} to N_union {t['union_upper_bound']}. Using "
        "the primary is the internally consistent choice because the deflated "
        "statistic is computed from that same book; the union is the "
        "conservative bound to adopt once the crosswalk lands.",
        "",
        "Raising N can only kill a class, never save one — DSR is monotone "
        "decreasing in N.",
        "",
        f"**Open fix:** {res['open_fix']}",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ledger", default=str(LEDGER))
    ap.add_argument("--registry", default=str(REGISTRY))
    ap.add_argument("--json", dest="json_out", default=None)
    ap.add_argument("--md", dest="md_out", default=None)
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 when the subset test fails (taxonomy drift)")
    args = ap.parse_args()

    ledger, registry = _load(Path(args.ledger)), _load(Path(args.registry))
    res = reconcile(ledger, registry)
    t = res["totals"]

    print("# trial-population reconciliation")
    print(f"# primary N: {res['primary_definition']}")
    print(f"# upper bnd: {res['upper_bound_definition']}")
    print(f"audit3 rows={t['audit3_cell_rows']} pairs={t['audit3_strategies']}  "
          f"pf strategies={t['pf_strategy_cells']}  "
          f"pf symbol-strategies={t['pf_symbol_strategy_cells']}  "
          f"union={t['union_upper_bound']}")
    print(f"shared={t['shared']}  audit3-only={t['audit3_only']}  "
          f"pf-only={t['pf_only']}")
    print()
    print(f"{'class':<14}{'N_pri':>7}{'N_uni':>7}{'pf':>6}{'audit3':>8}"
          f"{'a3/pf':>8}{'shared':>8}{'a3only':>8}")
    for cls, v in res["by_class"].items():
        pct = "n/a" if v["audit3_over_pf_pct"] is None else f"{v['audit3_over_pf_pct']}%"
        print(f"{cls:<14}{v['n_trials_primary']:>7}"
              f"{v['n_trials_union_upper_bound']:>7}{v['pf_strategies']:>6}"
              f"{v['audit3_strategies']:>8}{pct:>8}{v['shared']:>8}"
              f"{v['audit3_only_count']:>8}")
    print()
    print(res["finding"])
    if not res["subset_hypothesis_holds"]:
        print(f"subset test FAILED: {t['audit3_only']} audit3 pairs absent from "
              f"pf_registry -> N is bracketed [{t['pf_strategy_cells']}, "
              f"{t['union_upper_bound']}].")

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(res, indent=2), encoding="utf-8")
        print(f"\nwrote {args.json_out}")
    if args.md_out:
        Path(args.md_out).write_text(render_md(res, ledger, registry), encoding="utf-8")
        print(f"wrote {args.md_out}")

    if args.strict and not res["subset_hypothesis_holds"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
