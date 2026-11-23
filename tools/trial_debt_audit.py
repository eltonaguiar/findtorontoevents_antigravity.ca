#!/usr/bin/env python3
"""Audit the hypothesis registry to establish the TRUE programme-level trial count.

Backlog items C1/C2 (docs/BACKLOG_100_2026-11-23.md).

WHY THIS IS THE LOAD-BEARING NUMBER
The programme's headline is "0 of 6 asset classes survive deflation at N=90" and
"146 pre-registered hypotheses, 0/55 survive". Every one of those claims is a
function of N. If N is inflated by duplicates or by entries that were never
actually run, the deflation penalty is overstated and something may be
admissible. If N is understated, the real position is worse than advertised.

Neither direction is acceptable to guess. buffy verified their own N=29 in
notes/buffy-dsr-multiplicity-one-trial-margin-2026-11-22 and explicitly counted
3 zero-cell hypotheses as trials ("they were still searches and they consumed the
same degrees of freedom"). This audit applies that same rule programme-wide.

Counting rules, stated up front so they can be argued with:
  T1 A DISTINCT id is one trial.
  T2 An entry with a duplicate id is NOT a second trial (it is a re-file).
  T3 A hypothesis that RAN but produced no admissible cell STILL counts
     (buffy's rule: it consumed degrees of freedom).
  T4 A hypothesis that never ran counts too, and is reported separately --
     the search that was planned but abandoned is the hardest one to remember
     and the easiest one to forget when deflating.
  T5 `archived_failures` entries are counted as trials (they were run).
  T6 Withdrawn/superseded entries are reported separately, NOT silently dropped.

Read-only. Emits reports/trial_debt_audit_2026-11-23.json
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REG = ROOT / "reports" / "hypothesis_registry.json"
OUT = ROOT / "reports" / "trial_debt_audit_2026-11-23.json"


def registry_copy_sizes() -> dict[str, int]:
    """Count `hypotheses` in EVERY checkout, not just the main tree.

    Measured 2026-11-23: the copies are NOT in sync -- main tree 120, and the
    worktrees hold 99 / 106 / 108 / 108 / 108 / 109. So "the registry has N" is
    only meaningful with a path attached. A hash, or a count, without a path is
    not evidence -- same rule as an un-provenanced digest.
    """
    out = {}
    for p in [ROOT / "reports" / "hypothesis_registry.json"] + \
             sorted((ROOT / ".kilo" / "worktrees").glob("*/reports/hypothesis_registry.json")):
        try:
            d = json.loads(p.read_text())
        except Exception:
            continue
        rel = str(p.relative_to(ROOT))
        out[rel] = len(d.get("hypotheses", []))
    return out


# The FIVE numbers in circulation, and what object each one actually is. Kept
# here so the audit cannot repeat my own error of quoting a trial count without
# naming which object it counts.
TRIAL_COUNT_OBJECTS = [
    {"value": 146, "object": "copilot's cited figure -- UNSOURCED",
     "status": "WITHDRAWN: never derived, inherited and repeated"},
    {"value": 108, "object": "registry pre-registrations in worktree copies",
     "status": "snapshot-dependent; main tree holds 120"},
    {"value": 362, "object": "scored cells in the ledger DSR column",
     "status": "defensible conservative bound"},
    {"value": 658, "object": "symbols",
     "status": "REJECTED: a symbol is not a hypothesis (unit error)"},
    {"value": 25, "object": "correlation-adjusted EFFECTIVE trials (20-30)",
     "status": "REJECTED as primary: computed from realised return correlations, "
               "so it is outcome-dependent and circular"},
]

# Lists that hold runnable hypotheses. Anything not here is metadata.
SKIP_KEYS = {"schema_version", "description", "rule", "notes"}

# Status vocabulary DERIVED from the registry, not guessed. My first pass used an
# invented set of statuses and left 62 of 154 ids "unrecognised", which would have
# silently reclassified a third of the programme. Groups below are exhaustive for
# the observed vocabulary; anything outside them is reported, never defaulted.
RAN_STATUSES = {
    "refuted", "tested_kill", "tested_weak", "tested_pass", "killed", "rejected",
    "failed", "inconclusive", "measured", "complete", "done", "tested",
    "no_cell", "no_admissible_cell",
}
# Forward/running: pre-registered AND consuming a trial (buffy's T3 rule -- they
# already spent degrees of freedom), but with no closed outcome yet.
RUNNING_STATUSES = {
    "forward_observation", "forward_shadow", "forward-shadow", "paper_pilot",
}
NOT_RUN_STATUSES = {
    "pre_registered", "pre-registered", "registered", "registered-untested",
    "untested", "pending", "queued", "planned", "not_started", "proposed",
}
# Registered but permanently unmeasurable on current data. Still a claimed search;
# excluded from ran-N and reported on its own line.
DATA_GAP_STATUSES = {"untested_data_gap", "data_gap", "blocked"}


def entries(reg: dict) -> list[tuple[str, dict]]:
    out = []
    for k, v in reg.items():
        if k in SKIP_KEYS or not isinstance(v, list):
            continue
        for e in v:
            if isinstance(e, dict) and e.get("id"):
                out.append((k, e))
    return out


def main() -> int:
    reg = json.loads(REG.read_text())
    rows = entries(reg)

    by_id: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    for src, e in rows:
        by_id[str(e["id"])].append((src, e))

    dup_ids = {i: v for i, v in by_id.items() if len(v) > 1}

    # T3/T4: did it run?
    ran, running, not_run, data_gap, unknown = [], [], [], [], []
    for i, occ in by_id.items():
        e = occ[0][1]
        st = str(e.get("status", "")).strip().lower()
        res = e.get("result")
        has_result = bool(res) and str(res).strip().lower() not in ("", "null", "none", "-")
        if st in RAN_STATUSES or has_result:
            ran.append(i)
        elif st in RUNNING_STATUSES:
            running.append(i)
        elif st in DATA_GAP_STATUSES:
            data_gap.append(i)
        elif st in NOT_RUN_STATUSES:
            not_run.append(i)
        else:
            unknown.append((i, e.get("status")))

    # status histogram over distinct ids
    statuses = Counter(str(occ[0][1].get("status", "<none>")).strip().lower()
                       for occ in by_id.values())

    distinct = len(by_id)
    total_rows = len(rows)

    print("=" * 84)
    print("TRIAL DEBT AUDIT - what is the real N?")
    print("=" * 84)
    print(f"hypothesis-bearing lists      {len({s for s, _ in rows})}")
    print(f"total rows across all lists   {total_rows}")
    print(f"DISTINCT ids (rule T1)        {distinct}")
    print(f"duplicate ids                 {len(dup_ids)}"
          f"  -> {total_rows - distinct} redundant row(s)")
    print()
    print(f"ran / has a result            {len(ran)}")
    print(f"running forward (trial spent)  {len(running)}")
    print(f"registered but never ran      {len(not_run)}")
    print(f"registered, permanent data gap {len(data_gap)}")
    print(f"status outside the vocabulary   {len(unknown)}")
    print()
    print("status histogram (distinct ids):")
    for s, c in statuses.most_common(14):
        print(f"   {s:<22} {c}")

    if dup_ids:
        print("\n" + "=" * 84)
        print("T2 - DUPLICATE IDS (these inflate any naive len() count)")
        print("=" * 84)
        for i, occ in list(dup_ids.items())[:12]:
            srcs = ", ".join(f"{s}" for s, _ in occ)
            print(f"   {i:<18} x{len(occ)}  in: {srcs}")
        if len(dup_ids) > 12:
            print(f"   ... and {len(dup_ids) - 12} more")

    if unknown:
        print("\n" + "=" * 84)
        print("UNRECOGNISED STATUS - cannot classify as ran / not-run")
        print("=" * 84)
        for i, s in unknown[:12]:
            print(f"   {i:<18} status={s!r}")

    # The three candidate N values the programme might legitimately use
    candidates = {
        "naive_total_rows": total_rows,
        "distinct_ids": distinct,
        "distinct_that_ran": len(ran),
        "ran_plus_running_forward": len(ran) + len(running),
        "ran_plus_running_plus_datagap": len(ran) + len(running) + len(data_gap),
        "all_distinct_ever_registered": distinct,
    }
    print("\n" + "=" * 84)
    print("CANDIDATE N VALUES - which one should the deflation use?")
    print("=" * 84)
    for k, v in candidates.items():
        print(f"   {k:<38} {v}")
    print("\n   The defensible N for deflation is the number of DISTINCT SEARCHES")
    print("   THAT RAN, because an unsearched hypothesis cannot have produced the")
    print("   maximum statistic we are deflating against. Every larger candidate is")
    print("   conservative; every smaller one is a goalpost move.")

    print("\n" + "=" * 84)
    print("REGISTRY COPY SIZES -- 'the registry has N' needs a path")
    print("=" * 84)
    for k, v in registry_copy_sizes().items():
        print(f"   {k:<62} {v}")

    print("\n" + "=" * 84)
    print("THE FIVE NUMBERS IN CIRCULATION -- and which object each counts")
    print("=" * 84)
    for o in TRIAL_COUNT_OBJECTS:
        print(f"   N={o['value']:<4} {o['object']}")
        print(f"            -> {o['status']}")

    payload = {
        "generated": "2026-11-23",
        "source": "reports/hypothesis_registry.json",
        "rules": {
            "T1": "a distinct id is one trial",
            "T2": "duplicate id is a re-file, not a second trial",
            "T3": "a hypothesis that ran but produced no admissible cell still counts",
            "T4": "never-ran hypotheses reported but excluded from ran-N",
            "T5": "archived_failures count as trials",
            "T6": "withdrawn/superseded reported, never silently dropped",
        },
        "total_rows": total_rows,
        "distinct_ids": distinct,
        "redundant_rows": total_rows - distinct,
        "duplicate_id_count": len(dup_ids),
        "duplicate_ids": {i: [s for s, _ in occ] for i, occ in dup_ids.items()},
        "ran": len(ran),
        "running_forward": len(running),
        "not_run": len(not_run),
        "data_gap": len(data_gap),
        "unknown_status": [{"id": i, "status": s} for i, s in unknown],
        "status_histogram": dict(statuses),
        "candidate_N": candidates,
        "defensible_N": len(ran) + len(running),
        "defensible_N_basis": "distinct searches that ran OR are running forward -- both "
                              "consumed degrees of freedom (rule T3, buffy 2026-11-22)",
        "registry_copy_sizes": registry_copy_sizes(),
        "trial_count_objects_in_circulation": TRIAL_COUNT_OBJECTS,
        "claimed_N_elsewhere": {
            "note": "earlier revisions of this tool recorded a 'programme_headline' "
                    "of 146. That number was NEVER derived from any artifact -- a "
                    "search of every reports/*.json for 146 near a trial word found "
                    "only provenance_index.json by_status.OPEN=146, an unrelated "
                    "pick-status tally. The 146 figure is WITHDRAWN here.",
            "withdrawn_value": 146,
            "candidate_origin": "provenance_index.json by_status.OPEN = 146 (a status "
                                "tally, not a trial count) -- INFERENCE, not proven",
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2))
    print(f"\nwritten: {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
