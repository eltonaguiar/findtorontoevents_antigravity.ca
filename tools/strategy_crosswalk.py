#!/usr/bin/env python3
"""strategy_crosswalk.py -- resolve the two pick taxonomies into ONE trial count.

WHY THIS EXISTS
    DSR deflates the best observed statistic by the number of trials N and is
    monotone decreasing in N, so the trial count decides pass/fail. Two
    artifacts each claim to report it and they disagree badly:

        audit3_ledger.json :: cells                      342 distinct pairs
        pf_registry :: by_asset_class_strategy_policy_clean_net 695 pairs
        shared 124 / audit3-only 218 / pf-only 571 / union 913

    tools/trial_population_reconcile.py could only report that as a bracket
    [695, 913] because it compares LABEL SETS. This tool removes the bracket
    by comparing GRAINS.

THE ROOT CAUSE, IN CODE
    tools/build_pf_registry.py::

        def _strategy(row):
            return _norm(row.get("source_system") or row.get("strategy"))

    The registry keys every row by the EMISSION ENGINE when the pick carries
    one, and only falls back to the strategy string when it does not. audit3
    keys on the pick's own `strategy` string. So the two label sets are not
    two taxonomies of the same objects -- they are two GRANULARITIES of the
    same objects. An engine label can cover many strategies, which is why the
    registry shows 695 cells for 666 distinct labels while audit3 shows 210
    CRYPTO labels the registry never mentions individually.

    Comparing them 1:1 therefore manufactures "drift" that is really
    collapsing: a strategy the registry DOES hold, filed under its umbrella.

WHAT THIS TOOL DOES
    Every policy-clean row carries both fields, so the mapping is derived per
    pick rather than guessed from label spelling:

        source_system -> { strategy strings }

    and then it classifies every audit3 pair against the book:

        DIRECT     the pair is a registry cell under its own name
        COLLAPSED  the strategy IS in the book, filed under another label
                   (previously miscounted as "audit3-only" drift)
        ABSENT     the strategy appears nowhere in the policy-clean book

    N is then reported at the correct grain -- distinct
    (asset_class, strategy) over the policy-clean book -- instead of at engine
    grain or at a union built from mismatched grains.

USAGE
    python tools/strategy_crosswalk.py
    python tools/strategy_crosswalk.py --json out.json --md report.md
    python tools/strategy_crosswalk.py --strict   # exit 1 on unattributable rows
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BPR_PATH = ROOT / "tools" / "build_pf_registry.py"
LEDGER = ROOT / "audit_dashboard" / "data" / "audit3_ledger.json"
REGISTRY = ROOT / "audit_dashboard" / "data" / "pf_registry.json"
UNKNOWN = "UNKNOWN"


def _load_bpr():
    """Load the registry builder as a module so we read the SAME rows it reads.

    Re-implementing its loaders would let this tool drift from the artifact it
    is explaining, which is the exact failure mode it exists to catch.
    """
    spec = importlib.util.spec_from_file_location("_bpr_crosswalk", BPR_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _clean(value) -> str:
    return str(value or "").strip()


def _is_unknown(value: str) -> bool:
    return (not value) or value.upper() == UNKNOWN


def load_audit3_pairs() -> tuple[set, int]:
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    pairs: set = set()
    rows = 0
    for cell in data.get("cells") or []:
        if not isinstance(cell, dict):
            continue
        cls = _clean(cell.get("asset_class")).upper()
        strat = _clean(cell.get("strategy"))
        if not cls or not strat:
            continue
        rows += 1
        pairs.add((cls, strat))
    return pairs, rows


def classify_audit3_pairs(
    a3_pairs: set,
    engine_pairs: set,
    strategies_by_class: dict,
) -> tuple[set, set, set]:
    """Split audit3 (class, strategy) pairs into DIRECT / COLLAPSED / ABSENT.

    DIRECT     the pair is itself a registry cell -- both artifacts name it the
               same way, so it was always counted once.
    COLLAPSED  the strategy exists in the policy-clean book, but the registry
               filed those rows under a different label (its `source_system`
               umbrella). Comparing label sets 1:1 scored these as "drift"
               when the trial was in fact already counted.
    ABSENT     the strategy appears nowhere in the policy-clean book, so it
               never entered the book whose statistic DSR deflates.

    Only ABSENT pairs are genuinely outside the trial population.
    """
    direct = {p for p in a3_pairs if p in engine_pairs}
    collapsed = {
        p for p in (a3_pairs - direct)
        if p[1] in strategies_by_class.get(p[0], set())
    }
    absent = a3_pairs - direct - collapsed
    return direct, collapsed, absent


def analyse() -> dict:
    bpr = _load_bpr()
    raw_rows, source_meta = bpr.load_rows()
    classified = bpr.classify_rows(raw_rows)
    kept = classified["kept"]
    policy = [r for r in kept if not bpr._is_policy_excluded(r)]

    engine_grain: set = set()          # (class, _strategy(row)) == registry cells
    strategy_grain: set = set()        # (class, actual strategy string)
    fan_out: dict = defaultdict(set)   # (class, engine label) -> {strategy}
    src_to_strategy: dict = defaultdict(set)  # (class, source_system) -> {strategy}
    unattributable: list = []
    unknown_rows = 0

    for row in policy:
        cls = bpr._asset_class(row)
        engine = bpr._strategy(row)
        strat = _clean(row.get("strategy"))
        src = _clean(row.get("source_system"))

        if not cls or not engine:
            unattributable.append({
                "asset_class": cls or None,
                "engine_label": engine or None,
                "strategy": strat or None,
                "symbol": _clean(row.get("symbol")) or None,
            })
            continue

        engine_grain.add((cls, engine))
        fan_out[(cls, engine)].add(strat or UNKNOWN)
        if src:
            src_to_strategy[(cls, src)].add(strat or UNKNOWN)

        if _is_unknown(strat):
            unknown_rows += 1
        else:
            strategy_grain.add((cls, strat))

    strategies_by_class: dict = defaultdict(set)
    for cls, strat in strategy_grain:
        strategies_by_class[cls].add(strat)

    # Cells whose rows carry no strategy string at all. They are real trials but
    # cannot be named, so dropping them would make the strategy grain SMALLER
    # than the engine grain -- i.e. lowering N by discarding evidence. They are
    # counted back as one unnamed trial per (class, label) bucket.
    unattributable_cells = {
        (cls, label)
        for (cls, label), parts in fan_out.items()
        if parts and all(_is_unknown(part) for part in parts)
    }
    closed_grain = strategy_grain | unattributable_cells

    a3_pairs, a3_rows = load_audit3_pairs()

    direct, collapsed, absent = classify_audit3_pairs(
        a3_pairs, engine_grain, strategies_by_class
    )

    # ABSENT is the only bucket that is genuinely outside the book, and the word
    # alone hides three different causes with three different meanings:
    #
    #   policy_excluded       the strategy WAS ingested and closed, then dropped
    #                         by _is_policy_excluded. Re-admitting it is a policy
    #                         decision, not a data gap.
    #   dropped_pre_aggregate it reached the loader but never survived dedup /
    #                         spot-flicker filtering, so it never got a cell.
    #   not_in_inputs         no loaded input row carries this strategy at all --
    #                         audit3 is scoring something this build never saw.
    kept_pairs: set = set()
    for row in kept:
        strat = _clean(row.get("strategy"))
        if not _is_unknown(strat):
            kept_pairs.add((bpr._asset_class(row), strat))

    input_pairs: set = set()
    for row in raw_rows:
        if not isinstance(row, dict):
            continue
        strat = _clean(row.get("strategy"))
        if not _is_unknown(strat):
            input_pairs.add((bpr._asset_class(row), strat))

    absent_policy_excluded = {p for p in absent if p in kept_pairs}
    absent_dropped = {
        p for p in absent if p not in kept_pairs and p in input_pairs
    }
    absent_unseen = absent - absent_policy_excluded - absent_dropped

    union_strategy = strategy_grain | a3_pairs

    # REPRODUCTION GUARD. This tool exists to explain a shipped artifact, so it
    # must rebuild that artifact rather than a lookalike. The registry ingests
    # gated inputs (PF_REGISTRY_INCLUDE_OUTCOMES=1 pulls ~25k rows from
    # at_pick_outcomes); if a gate is off the recount silently under-counts and
    # every "absent" pair is an artefact of missing input, not of taxonomy.
    shipped = json.loads(REGISTRY.read_text(encoding="utf-8"))
    shipped_pairs = {
        (_clean(r.get("asset_class")).upper(), _clean(r.get("strategy")))
        for r in (shipped.get("by_asset_class_strategy_policy_clean_net") or [])
        if isinstance(r, dict)
    }
    missing_from_recount = shipped_pairs - engine_grain
    extra_in_recount = engine_grain - shipped_pairs
    reproduces = not missing_from_recount and not extra_in_recount

    def per_class(pairs) -> dict:
        out: dict = defaultdict(int)
        for cls, _ in pairs:
            out[cls] += 1
        return dict(sorted(out.items()))

    engine_by_class = per_class(engine_grain)
    strategy_by_class = per_class(strategy_grain)
    closed_by_class = per_class(closed_grain)

    umbrellas = sorted(
        (
            {
                "asset_class": cls,
                "label": label,
                "n_strategies": len(parts),
                "strategies": sorted(parts)[:12],
            }
            for (cls, label), parts in fan_out.items()
            if len(parts) > 1
        ),
        key=lambda d: (-d["n_strategies"], d["asset_class"], d["label"]),
    )

    return {
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "registry_generated": json.loads(
            REGISTRY.read_text(encoding="utf-8")
        ).get("generated_utc"),
        "rows_loaded": len(raw_rows),
        "rows_kept_after_dedup": len(kept),
        "rows_policy_clean": len(policy),
        "rows_unknown_strategy": unknown_rows,
        "unattributable_rows": unattributable[:20],
        "unattributable_count": len(unattributable),
        "reproduction": {
            "shipped_cells": len(shipped_pairs),
            "recomputed_cells": len(engine_grain),
            "exact_match": reproduces,
            "n_missing_from_recount": len(missing_from_recount),
            "n_extra_in_recount": len(extra_in_recount),
            "missing_examples": sorted(f"{c} / {s}" for c, s in missing_from_recount)[:15],
            "extra_examples": sorted(f"{c} / {s}" for c, s in extra_in_recount)[:15],
        },
        "counts": {
            "n_engine_grain": len(engine_grain),
            "n_strategy_grain": len(strategy_grain),
            "n_unattributable_cells": len(unattributable_cells),
            "n_trials_closed": len(closed_grain),
            "n_audit3_pairs": len(a3_pairs),
            "n_audit3_rows": a3_rows,
            "n_union_strategy_grain": len(union_strategy),
            "audit3_direct": len(direct),
            "audit3_collapsed": len(collapsed),
            "audit3_absent": len(absent),
            "absent_policy_excluded": len(absent_policy_excluded),
            "absent_dropped_pre_aggregation": len(absent_dropped),
            "absent_not_in_inputs": len(absent_unseen),
        },
        "per_class": {
            cls: {
                "n_engine": engine_by_class.get(cls, 0),
                "n_strategy": strategy_by_class.get(cls, 0),
                "n_closed": closed_by_class.get(cls, 0),
            }
            for cls in sorted(
                set(engine_by_class) | set(strategy_by_class) | set(closed_by_class)
            )
        },
        "umbrella_labels": umbrellas[:20],
        "umbrella_label_count": len(umbrellas),
        "absent_attribution": {
            "policy_excluded": sorted(
                f"{c} / {s}" for c, s in absent_policy_excluded
            )[:60],
            "dropped_pre_aggregation": sorted(
                f"{c} / {s}" for c, s in absent_dropped
            )[:60],
            "not_in_inputs": sorted(f"{c} / {s}" for c, s in absent_unseen)[:60],
        },
        "collapsed_pairs": sorted(f"{c} / {s}" for c, s in collapsed),
        "absent_pairs": sorted(f"{c} / {s}" for c, s in absent)[:400],
        "source_files": source_meta,
    }


def render_md(result: dict) -> str:
    c = result["counts"]
    lines = [
        "# Strategy crosswalk — closing the trial-count bracket",
        "",
        f"- crosswalk generated: `{result['generated_utc']}`",
        f"- pf_registry generated: `{result['registry_generated']}`",
        f"- policy-clean rows analysed: {result['rows_policy_clean']}",
        "",
        "## Reproduction check",
        "",
        f"- shipped registry cells: **{result['reproduction']['shipped_cells']}**",
        f"- cells this recount rebuilds: **{result['reproduction']['recomputed_cells']}**",
        f"- exact match: **{result['reproduction']['exact_match']}** "
        f"(missing {result['reproduction']['n_missing_from_recount']}, "
        f"extra {result['reproduction']['n_extra_in_recount']})",
        "",
    ]
    if not result["reproduction"]["exact_match"]:
        lines += [
            "> **WARNING — NOT REPRODUCIBLE.** The recount does not rebuild the shipped",
            "> artifact, so every count below describes a different population. The usual",
            "> cause is a gated input being off: `PF_REGISTRY_INCLUDE_OUTCOMES=1` adds the",
            "> ~25k `at_pick_outcomes` rows the shipped registry depends on. Do not quote",
            "> `n_strategy_grain` from a run whose reproduction check failed.",
            "",
        ]
    lines += [
        "## Root cause",
        "",
        "`tools/build_pf_registry.py::_strategy` keys each row as",
        "`source_system or strategy`, i.e. by **emission engine** when the pick has one.",
        "audit3 keys on the pick's own `strategy` string. The two artifacts are two",
        "**granularities** of the same picks, not two taxonomies — so comparing their",
        "label sets 1:1 manufactures drift that is really collapsing.",
        "",
        "## Resolved counts",
        "",
        "| quantity | count |",
        "|---|---|",
        f"| registry cells, engine grain (`n_engine`) | {c['n_engine_grain']} |",
        f"| distinct (class, strategy) in the policy-clean book | {c['n_strategy_grain']} |",
        f"| unnamed (class, label) buckets with no strategy string | {c['n_unattributable_cells']} |",
        f"| **CLOSED trial count (named strategies + unnamed buckets)** | **{c['n_trials_closed']}** |",
        f"| audit3 distinct pairs | {c['n_audit3_pairs']} |",
        f"| union at strategy grain (sensitivity) | {c['n_union_strategy_grain']} |",
        "",
        "### How audit3's 342 pairs classify against the book",
        "",
        "| bucket | count | meaning |",
        "|---|---|---|",
        f"| DIRECT | {c['audit3_direct']} | registry cell under its own name |",
        f"| COLLAPSED | {c['audit3_collapsed']} | in the book, filed under another label |",
        f"| ABSENT | {c['audit3_absent']} | nowhere in the policy-clean book |",
        "",
        "### Why the absent pairs are absent",
        "",
        "| cause | count | meaning |",
        "|---|---|---|",
        f"| policy_excluded | {c['absent_policy_excluded']} | ingested and closed, then dropped by `_is_policy_excluded` |",
        f"| dropped_pre_aggregation | {c['absent_dropped_pre_aggregation']} | reached the loader, failed dedup / spot-flicker |",
        f"| not_in_inputs | {c['absent_not_in_inputs']} | no loaded input row carries this strategy |",
        "",
        "## Per class",
        "",
        "| class | engine grain | strategy grain | **closed** |",
        "|---|---|---|---|",
    ]
    for cls, row in result["per_class"].items():
        lines.append(
            f"| {cls} | {row['n_engine']} | {row['n_strategy']} | "
            f"**{row['n_closed']}** |"
        )

    lines += [
        "",
        "## Umbrella labels that collapse strategies",
        "",
        f"{result['umbrella_label_count']} labels cover more than one strategy string.",
        "Largest fan-outs:",
        "",
        "| class | label | strategies under it |",
        "|---|---|---|",
    ]
    for u in result["umbrella_labels"][:12]:
        lines.append(f"| {u['asset_class']} | `{u['label']}` | {u['n_strategies']} |")

    lines += [
        "",
        "## Verification",
        "",
        "- Rows come from `build_pf_registry.load_rows()` + `classify_rows()` and the same",
        "  `_is_policy_excluded` filter the artifact uses, so this explains the shipped",
        "  695 rather than a parallel recount.",
        f"- Unattributable policy-clean rows: **{result['unattributable_count']}**.",
        f"- Rows with no strategy string (cannot be attributed to a trial): {result['rows_unknown_strategy']}.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json")
    ap.add_argument("--md")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 if any policy-clean row cannot be attributed")
    ap.add_argument("--require-reproduction", action="store_true",
                    help="exit 2 unless the recount rebuilds the shipped registry exactly")
    args = ap.parse_args()

    result = analyse()
    md = render_md(result)

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    json_path = Path(args.json) if args.json else ROOT / "reports" / f"strategy_crosswalk_{stamp}.json"
    md_path = Path(args.md) if args.md else ROOT / "reports" / f"strategy_crosswalk_{stamp}.md"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(md + "\n", encoding="utf-8")

    c = result["counts"]
    print(md)
    print(f"wrote {json_path.relative_to(ROOT)} and {md_path.relative_to(ROOT)}")

    if args.require_reproduction and not result["reproduction"]["exact_match"]:
        print("FAIL: recount does not reproduce the shipped registry "
              f"({result['reproduction']['recomputed_cells']} vs "
              f"{result['reproduction']['shipped_cells']} cells)", file=sys.stderr)
        return 2

    if args.strict and result["unattributable_count"]:
        print(f"FAIL: {result['unattributable_count']} policy-clean rows unattributable",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
