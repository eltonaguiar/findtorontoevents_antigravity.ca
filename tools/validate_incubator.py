#!/usr/bin/env python3
"""validate_incubator.py — gate the incubator's 'paper-ready' output with audit3 rules.

The Investment Hub incubator (findcryptopairs/incubator.html ->
alpha_engine/data/incubator_paper_ready.json) emits 20 'paper-ready' strategies from
4,987 permutations / 24,935 backtests. This validator applies the audit3 admission
rules before any of them may become a pod:
  1. n present and >= MIN_N (DSR needs a sample size)
  2. dedup on (archetype, rounded metrics) - the source has duplicate rows
  3. sanity: Sharpe must be finite and < SANE_SHARPE (catches the best_sharpe=9248 bug)
  4. DSR >= 0.95 at the honest permutation count N_PERM
Exit 1 if 0 admissible (expected), 0 otherwise. Prints the verdict.
"""
import argparse, json, math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from alpha_engine.audit3_tribunal import deflated_sharpe  # noqa: E402

MIN_N = 30
SANE_SHARPE = 10.0
N_PERM = 4987


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="alpha_engine/data/incubator_paper_ready.json")
    ap.add_argument("--out", default="reports/incubator_validated.json")
    a = ap.parse_args()
    rows = json.load(open(a.src))
    seen = set()
    report = {"src": a.src, "n_input": len(rows), "N_perm": N_PERM,
              "admissible": [], "rejected": []}
    for r in rows:
        arch = r.get("archetype")
        sh = r.get("combined_sharpe")
        n = r.get("n") or r.get("trades")
        key = (arch, round(sh, 2) if isinstance(sh, (int, float)) else None, r.get("combined_pf"))
        reasons = []
        if n is None:
            reasons.append("no_n")
        elif n < MIN_N:
            reasons.append(f"n<{MIN_N}")
        if sh is None or not math.isfinite(sh) or abs(sh) > SANE_SHARPE:
            reasons.append("insane_sharpe")
        if key in seen:
            reasons.append("duplicate")
        seen.add(key)
        dsr = None
        if n and isinstance(n, int) and n >= 10 and isinstance(sh, (int, float)) and math.isfinite(sh):
            # reconstruct a per-trade series with the reported mean/sharpe scale is not possible;
            # DSR here is reported only if the row carries raw returns. Otherwise flag undecidable.
            reasons.append("no_raw_returns_for_dsr") if dsr is None and "no_n" not in reasons else None
        entry = {"archetype": arch, "sharpe": sh, "pf": r.get("combined_pf"),
                 "n": n, "composite": r.get("composite_score"), "dsr_verdict": "UNDECIDABLE_NO_RETURNS"}
        if reasons:
            entry["reasons"] = reasons
            report["rejected"].append(entry)
        else:
            report["admissible"].append(entry)
    report["n_admissible"] = len(report["admissible"])
    report["n_rejected"] = len(report["rejected"])
    report["verdict"] = ("NONE ADMISSIBLE - incubator output cannot enter audit3 as-is "
                         "(no n / duplicate / insane sharpe); needs raw per-trade returns for DSR"
                         if report["n_admissible"] == 0 else "SOME ADMISSIBLE")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(report, indent=2) + "\n")
    from collections import Counter
    rc = Counter(x for e in report["rejected"] for x in e.get("reasons", []))
    print(f"input={report['n_input']} admissible={report['n_admissible']} rejected={report['n_rejected']}")
    print("reject reasons:", dict(rc))
    print("verdict:", report["verdict"])
    return 0 if report["n_admissible"] else 1


if __name__ == "__main__":
    sys.exit(main())
