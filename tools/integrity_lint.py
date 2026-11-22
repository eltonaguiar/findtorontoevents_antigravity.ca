#!/usr/bin/env python3
"""Integrity lint — catch the three defects that actually produced fake results here.

WHY THESE THREE (todos 26, 27, 30)
-----------------------------------
Every false positive in this programme came from one of a small number of
mechanical mistakes, not from bad judgement. Those mistakes are detectable by
pattern, so they should be machine-checked rather than remembered.

  CHECK A — SELECTION ON THE DEPENDENT VARIABLE (todo 26)
      A median computed after dropping negative observations guarantees a positive
      answer. This happened: the cost-horizon ladder was published as "median gross
      edge across all POSITIVE cells", which roughly doubled it at 3 of 4 horizons.
      Detects a sign filter feeding an aggregate within the same function.

  CHECK B — FORWARD-LEDGER PROVENANCE (todo 27)
      A forward observation must be written BEFORE its outcome exists. If
      created_at > closed_at the row is a backfill. This happened: all 430 H-119
      "forward" rows were written on one day, median 103 days after they closed.

  CHECK C — TRIALS DISCLOSED (todo 30)
      Any artifact reporting a Sharpe / PF / hit rate must state n_trials, because
      the best of N looks good by construction. Silent omission is how a
      single-winner-of-many gets promoted.

WHAT THIS DOES NOT DO
  It is a heuristic linter, not a proof. A clean run means "none of these three
  known patterns appear", not "the numbers are correct". False negatives are
  expected — a smarter version of the same mistake will pass. Its value is that the
  three most common ones cannot silently recur.

Usage:
  python3 tools/integrity_lint.py            # report
  python3 tools/integrity_lint.py --strict   # exit 1 on any finding (CI)
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCAN_DIRS = ["tools", "alpha_engine", "audit_trail", "verified_strategies"]
AGG_CALLS = {"median", "mean", "fmean", "statistics.median", "statistics.mean",
             "np.median", "np.mean", "numpy.median", "numpy.mean"}
LEDGERS = ["reports/forward_observations.jsonl"]
BASELINE = ROOT / "reports" / "integrity_lint" / "baseline.json"


def finding_key(f: dict) -> str:
    """Stable identity for a finding: file + function/detail, NOT line number.

    Line numbers shift on every unrelated edit, so keying on them would make the
    baseline go stale constantly and the gate would be disabled out of frustration.
    """
    return "|".join([f.get("check", ""), f.get("file", ""),
                     f.get("function", ""), str(f.get("detail", ""))[:120]])


# --------------------------------------------------------------------------- #
def check_selection_on_dv() -> list[dict]:
    """Flag a sign filter whose output feeds an aggregate, in the same function."""
    findings = []
    for d in SCAN_DIRS:
        base = ROOT / d
        if not base.is_dir():
            continue
        for path in base.rglob("*.py"):
            try:
                src = path.read_text(errors="ignore")
                tree = ast.parse(src)
            except (SyntaxError, OSError):
                continue
            for fn in [n for n in ast.walk(tree)
                       if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
                # Collect names bound to a comprehension filtered by "> 0".
                filtered: set[str] = set()
                for node in ast.walk(fn):
                    if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                        continue
                    val = node.value
                    if not (isinstance(val, (ast.ListComp, ast.GeneratorExp))
                            and val.generators):
                        continue
                    for gen in val.generators:
                        for cond in gen.ifs:
                            if (isinstance(cond, ast.Compare)
                                    and any(isinstance(c, ast.Gt) for c in cond.ops)
                                    and any(isinstance(x, ast.Constant)
                                            and x.value == 0
                                            for x in cond.comparators)):
                                tgts = (node.targets if isinstance(node, ast.Assign)
                                        else [node.target])
                                for t in tgts:
                                    if isinstance(t, ast.Name):
                                        filtered.add(t.id)
                if not filtered:
                    continue
                # Does an aggregate consume one of those names?
                for node in ast.walk(fn):
                    if not isinstance(node, ast.Call):
                        continue
                    name = ast.unparse(node.func)
                    if name.split(".")[-1] not in {"median", "mean", "fmean"}:
                        continue
                    for arg in node.args:
                        if (isinstance(arg, ast.Name) and arg.id in filtered):
                            # SEVERITY. "Average winning trade" is a legitimate
                            # metric: filtering trades to PnL>0 and averaging them
                            # IS the definition of mean win size. The defect is
                            # filtering a set of STRATEGIES/CANDIDATES by a
                            # performance stat and then aggregating, which hides
                            # the losers from the population being described.
                            nm = arg.id.lower()
                            benign = any(w in nm for w in
                                         ("win", "print", "gain", "loss",
                                          "up", "long"))
                            findings.append({
                                "check": "A_selection_on_dv",
                                "severity": "LOW (probably mean-win metric)"
                                if benign else "HIGH",
                                "file": str(path.relative_to(ROOT)),
                                "function": fn.name,
                                "line": node.lineno,
                                "detail": (f"aggregate `{name}({arg.id})` where "
                                           f"`{arg.id}` was filtered to > 0"),
                            })
    return findings


def check_ledger_provenance() -> list[dict]:
    findings = []
    for rel in LEDGERS:
        p = ROOT / rel
        if not p.exists():
            findings.append({"check": "B_ledger_provenance", "file": rel,
                             "detail": "ledger missing (expected for a forward clock)"})
            continue
        bad = total = 0
        earliest = None
        for ln in p.read_text(errors="ignore").splitlines():
            ln = ln.strip()
            if not ln:
                continue
            try:
                r = json.loads(ln)
            except json.JSONDecodeError:
                continue
            total += 1
            try:
                c, cl = (datetime.fromisoformat(r["created_at"]),
                         datetime.fromisoformat(r["closed_at"]))
            except (KeyError, TypeError, ValueError):
                continue
            if c > cl:
                bad += 1
                if earliest is None or c < earliest:
                    earliest = c
        if bad:
            findings.append({
                "check": "B_ledger_provenance",
                "file": rel,
                "detail": (f"{bad}/{total} rows created AFTER their own close "
                           f"(backfilled, not forward). Earliest such write: "
                           f"{earliest.date() if earliest else '?'}"),
                "rows_total": total, "rows_backfilled": bad,
            })
    return findings


def check_trials_disclosed() -> list[dict]:
    """Artifacts reporting a Sharpe/PF must state how many trials produced it."""
    findings = []
    rep = ROOT / "reports"
    if not rep.is_dir():
        return findings
    seen = 0
    for p in rep.rglob("*.json"):
        try:
            if p.stat().st_size > 5_000_000:
                continue
            text = p.read_text(errors="ignore")
            d = json.loads(text)
        except (json.JSONDecodeError, OSError):
            continue
        flat = text.lower()
        if not any(k in flat for k in ('"sharpe"', '"pf"', '"profit_factor"')):
            continue
        # PRECISION. A single-strategy artifact does not need a trials count —
        # n_trials=1 is implied. The obligation only exists where a winner was
        # SELECTED from several, so require evidence of a search: a list of >=3
        # named strategies/cells/models alongside the performance stats.
        names = set(re.findall(r'"(?:strategy|strategy_name|name|model|cell)"\s*:\s*"([^"]{1,40})"', text))
        if len(names) < 3:
            continue
        seen += 1
        if not any(k in flat for k in ('"n_trials"', '"trials"', '"n_cells"',
                                       '"search_breadth"', '"n_strategies"')):
            findings.append({
                "check": "C_trials_disclosed",
                "file": str(p.relative_to(ROOT)),
                "detail": (f"selects among {len(names)} named candidates and "
                           f"reports Sharpe/PF but no n_trials field"),
            })
    return findings, seen


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 if any NEW blocking finding vs baseline")
    ap.add_argument("--accept", action="store_true",
                    help="record current findings as the baseline")
    a = ap.parse_args()

    print("=== INTEGRITY LINT ===")
    print("  Heuristic checks for the three defects that produced fake results")
    print("  in this programme. A clean run is not a proof of correctness.\n")

    fa = check_selection_on_dv()
    hi = [f for f in fa if f.get("severity") == "HIGH"]
    lo = [f for f in fa if f.get("severity") != "HIGH"]
    print(f"--- CHECK A: selection on the dependent variable ---")
    print(f"  HIGH {len(hi)}  |  LOW (probably a legitimate mean-win metric) {len(lo)}")
    if not hi:
        print("  no HIGH findings")
    for f in hi:
        print(f"  {f['file']}:{f['line']} [{f['function']}] {f['detail']}")
    if lo:
        print(f"  ({len(lo)} LOW findings suppressed — trade-level >0 filters")
        print(f"   feeding a mean-win style metric are the normal definition.)")

    fb = check_ledger_provenance()
    print(f"\n--- CHECK B: forward-ledger provenance ---")
    if not fb:
        print("  all ledger rows were created BEFORE their own close")
    for f in fb:
        print(f"  {f['file']}: {f['detail']}")

    fc, seen = check_trials_disclosed()
    print(f"\n--- CHECK C: n_trials disclosed ---")
    print(f"  artifacts reporting Sharpe/PF: {seen}")
    if not fc:
        print("  all of them disclose a trial count")
    for f in fc[:15]:
        print(f"  {f['file']}: {f['detail']}")
    if len(fc) > 15:
        print(f"  ... and {len(fc)-15} more")

    total = len(fa) + len(fb) + len(fc)
    blocking = [f for f in fa if f.get("severity") == "HIGH"] + fb
    print(f"\n=== SUMMARY: {total} finding(s) "
          f"(A={len(fa)} [HIGH {len(hi)}] B={len(fb)} C={len(fc)}) ===")
    if total:
        print("  Findings are not automatically wrong — each needs a human read.")
        print("  Check A HIGH and Check B are almost always real.")

    # BASELINE GATE. A linter that fails on day one because of pre-existing debt
    # gets switched off within a week. So block only on findings that are NEW
    # relative to an accepted baseline; the debt stays visible above but does not
    # stop the build.
    cur_keys = {finding_key(f) for f in blocking}
    if a.accept:
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        BASELINE.write_text(json.dumps({
            "accepted_utc": datetime.now(timezone.utc).isoformat(),
            "note": ("Pre-existing integrity debt. Anything NOT in this list fails"
                     " CI. Remove entries as they are fixed; never add without a"
                     " human read."),
            "keys": sorted(cur_keys),
        }, indent=2))
        print(f"\nACCEPTED baseline: {len(cur_keys)} blocking finding(s) "
              f"grandfathered -> {BASELINE.relative_to(ROOT)}")
        return 0

    base: set[str] = set()
    if BASELINE.exists():
        try:
            base = set(json.loads(BASELINE.read_text()).get("keys", []))
        except (json.JSONDecodeError, OSError):
            base = set()
    new = sorted(cur_keys - base)
    fixed = sorted(base - cur_keys)
    print(f"\n  blocking now: {len(cur_keys)}  |  baselined: {len(base)}  "
          f"|  NEW: {len(new)}  |  fixed since baseline: {len(fixed)}")
    if fixed:
        print(f"  {len(fixed)} baselined finding(s) no longer reproduce — "
              f"re-run --accept to shrink the baseline.")
    if new:
        print("\n  NEW BLOCKING FINDINGS:")
        for k in new:
            print(f"    {k.replace('|', ' :: ')}")
    if a.strict and new:
        return 1
    if a.strict and not BASELINE.exists():
        print("\n  (no baseline yet — run --accept once to grandfather existing debt)")
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
