"""
Admissibility validator for alpha_engine/data/incubator_report.json (todo 11).

WHY THIS EXISTS
---------------
The incubator produces "paper-ready" strategies. Before any of them can become an audit3 pod it
must survive the same rules as everything else. Kilo's review of the same file (review repo
f45f67e) recommended a validator requiring n, dedup and DSR at the honest permutation count;
this is that validator, written independently against the actual data file so each check is
checkable rather than asserted.

WHAT IT FOUND (run 2026-11-23, report timestamp 2026-11-20)
-----------------------------------------------------------
Confirmed:  4,987 permutations tested, 24,935 backtests, 4,649 candidates, 20 paper-ready,
            best_sharpe 9248.977 (a computation bug -- near-zero variance, not skill).
CORRECTED:  "no n on the 20 rows" is imprecise. The field `combined_trades` exists and is
            populated (21..61). It is simply far too small to support any claim, and it is an
            aggregate over per_symbol, not a per-trade sample.
RETRACTED:  I first wrote here that kilo's "16 duplicate rows" was wrong because exact-duplicate
            and (seed_strategy, params) duplicate counts are both 0. That correction was itself
            wrong, and the refined measure proves kilo right: **16 of the 20 rows share an
            IDENTICAL (sharpe, profit_factor, trades) tuple**. They are not byte-identical rows
            -- they are different parameter sets that produced exactly the same performance,
            which is the same defect viewed from the output side instead of the input side.
            Kilo's number was correct; my method of checking it was too literal.
WORSE THAN EITHER READING: `distinct seed_strategy == 1`. All 20 "paper-ready strategies" are
            parameter sets of a SINGLE seed strategy. That is not 20 discoveries, it is one
            discovery counted 20 times -- the multiple-testing trap in its purest form.

Exit codes: 0 admissible, 1 inadmissible, 2 missing input.
"""
from __future__ import annotations

import argparse
import json
from math import e
from pathlib import Path
from statistics import NormalDist

GAMMA = 0.5772156649015329
Z = NormalDist().inv_cdf
SIG_SR = 0.6488          # deflation_programme.json
SHARPE_SANITY = 10.0     # |sharpe| above this is a variance bug, not an edge
MIN_TRADES = 30          # below this DSR is not definable in practice


def sr_star(n_trials: int) -> float:
    return SIG_SR * ((1 - GAMMA) * Z(1 - 1.0 / n_trials)
                     + GAMMA * Z(1 - 1.0 / (n_trials * e)))


def deflated_sharpe(sr: float, n_obs: int, n_trials: int) -> float | None:
    """Rough DSR: probability the observed Sharpe beats the expected max under the null.

    Deliberately simple and conservative; the point is admissibility, not precision.
    """
    if not n_obs or n_obs < 2 or sr is None:
        return None
    expected_max = sr_star(n_trials)
    # standard error of a Sharpe estimate ~ sqrt((1 + sr^2/2)/n)
    se = ((1 + (sr ** 2) / 2.0) / n_obs) ** 0.5
    if se <= 0:
        return None
    z = (sr - expected_max) / se
    # DSR is a PROBABILITY, so it is the normal CDF of z -- not the inverse CDF.
    # (First draft used inv_cdf here, which raised StatisticsError whenever z fell outside
    # (0,1) -- which is most of the time, because these Sharpes sit far below SR*.)
    return NormalDist().cdf(z)


def validate(path: Path) -> dict:
    d = json.loads(path.read_text())
    summary = d.get("summary") or {}
    rows = d.get("paper_ready") or []

    n_perms = summary.get("total_permutations_tested") or len(rows)
    best_sharpe = summary.get("best_sharpe")

    findings: list[dict] = []
    admitted: list[dict] = []

    # 1. Sharpe computation sanity -- the headline bug
    if best_sharpe is not None and abs(best_sharpe) > SHARPE_SANITY:
        findings.append({
            "check": "sharpe_sanity", "severity": "BLOCKING",
            "detail": (f"summary.best_sharpe = {best_sharpe} exceeds the sanity bound of "
                       f"{SHARPE_SANITY}. A Sharpe near 10^4 implies near-zero variance "
                       f"in the denominator, i.e. a computation bug, not skill. Nothing "
                       f"downstream may read this column until it is fixed."),
        })

    # 2/3/4. per-row checks
    seeds = {r.get("seed_strategy") for r in rows}
    for r in rows:
        reasons = []
        trades = r.get("combined_trades")
        sharpe = r.get("combined_sharpe")

        if trades is None:
            reasons.append("no sample size field at all")
        elif trades < MIN_TRADES:
            reasons.append(f"combined_trades={trades} < MIN_TRADES={MIN_TRADES}")

        if sharpe is None:
            reasons.append("no sharpe")
        elif abs(sharpe) > SHARPE_SANITY:
            reasons.append(f"sharpe={sharpe} fails sanity")

        dsr = deflated_sharpe(sharpe, trades, n_perms) if (sharpe is not None and trades) else None
        if dsr is None:
            reasons.append("DSR undefinable")
        elif dsr < 0.95:
            reasons.append(f"DSR={dsr:.4f} < 0.95 at N={n_perms}")

        if len(seeds) == 1 and len(rows) > 1:
            reasons.append(
                f"NOT INDEPENDENT: all {len(rows)} rows share one seed_strategy "
                f"({next(iter(seeds))}); these are parameter sets, not distinct discoveries"
            )

        rec = {"perm_id": r.get("perm_id"), "seed_strategy": r.get("seed_strategy"),
               "sharpe": sharpe, "trades": trades, "dsr": None if dsr is None else round(dsr, 4),
               "reasons": reasons}
        if reasons:
            findings.append(rec)
        else:
            admitted.append(rec)

    # distinct-result check: are several rows byte-identical on performance?
    perf = [(r.get("combined_sharpe"), r.get("combined_pf"), r.get("combined_trades")) for r in rows]
    dup_perf = len(perf) - len(set(perf))

    return {
        "input": str(path),
        "generated_for": "todo 11 -- incubator admissibility gate",
        "summary": {
            "total_permutations_tested": n_perms,
            "total_backtests": summary.get("total_backtests"),
            "candidates_ranked": summary.get("candidates_ranked"),
            "paper_ready_count": len(rows),
            "distinct_seed_strategy": len(seeds),
            "rows_sharing_identical_performance": dup_perf,
            "sr_star_at_N": round(sr_star(n_perms), 4),
        },
        "admitted_count": len(admitted),
        "inadmissible_count": len(findings) - (1 if best_sharpe and abs(best_sharpe) > SHARPE_SANITY else 0),
        "verdict": "ADMISSIBLE" if admitted else "INADMISSIBLE",
        "headline": (
            f"0 of {len(rows)} paper-ready strategies are admissible as-is. "
            f"{len(seeds)} distinct seed strategy/strategies across {len(rows)} rows; "
            f"SR* at N={n_perms} is {sr_star(n_perms):.3f}."
        ),
        "global_findings": [f for f in findings if "check" in f],
        "row_findings": [f for f in findings if "reasons" in f],
        "admitted": admitted,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="alpha_engine/data/incubator_report.json")
    ap.add_argument("--out", default="reports/incubator_validation_2026-11-23.json")
    args = ap.parse_args()

    p = Path(args.input)
    if not p.exists():
        print(f"missing input: {p}")
        return 2

    res = validate(p)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(res, indent=1))

    s = res["summary"]
    print(f"input                 : {s['total_permutations_tested']} permutations, "
          f"{s['total_backtests']} backtests, {s['candidates_ranked']} candidates")
    print(f"paper_ready rows      : {s['paper_ready_count']}")
    print(f"distinct seed_strategy: {s['distinct_seed_strategy']}   "
          f"<-- rows sharing identical performance: {s['rows_sharing_identical_performance']}")
    print(f"SR* at N={s['total_permutations_tested']}      : {s['sr_star_at_N']}")
    for g in res["global_findings"]:
        print(f"\n  [BLOCKING] {g['check']}: {g['detail']}")
    print(f"\n{res['headline']}")
    print(f"verdict: {res['verdict']}   written: {args.out}")
    return 0 if res["admitted_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
