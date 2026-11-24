"""Anti-overfit audit driver -- prints PBO / Reality-Check / DSR for one or
more source_systems pulled from the live audit ledger.

OPT-IN sidecar (see CLAUDE.md Wire-Up Rule). Does not mutate any production
file. Output is a 3-line report per system suitable for paste into review
notes or a PR body.

Usage::

    python tools/run_anti_overfit_audit.py kimi_riseoftheclaw
    python tools/run_anti_overfit_audit.py kimi_riseoftheclaw claude_gainer_st multi_asset_copytrader
    python tools/run_anti_overfit_audit.py --top 5
    python tools/run_anti_overfit_audit.py --json kimi_riseoftheclaw

Notes
-----
- Returns are pulled from ``audit_dashboard/data/dashboard_data.json``,
  ``picks.recent_closed[]``, filtered to resolved rows only so that
  pending/active rows are excluded. The resolved-status vocabulary is
  ``RESOLVED_STATUSES`` below.

  .. warning::
     **Do not narrow this to ``{"WIN", "LOST"}``.** The live ledger writes
     ``WON`` (not ``WIN``). On 2026-11-20 the set ``{"WIN", "LOST"}`` matched
     2,026 of 3,455 resolved rows and the 1,429 rows it silently dropped were
     *exclusively winners* -- every subsequent DSR / PBO / Sharpe / WFE figure
     computed here was a property of a loss-only subsample, not of the
     strategy. ``_assert_status_vocabulary_is_covered`` now fails loudly if the
     ledger introduces a resolved status this module does not know about, so the
     next vocabulary drift is a red build instead of silent bias.
- Per-pick return = ``pnl_pct / 100`` (each pick treated as one observation).
- For PBO we rebuild a (T x S) returns matrix where columns are *strategies*
  inside the chosen source_system. If the system has < 2 strategies the PBO
  step is skipped and reported as N/A.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = REPO_ROOT / "audit_dashboard" / "data" / "dashboard_data.json"

# Make the alpha_engine package importable when run from anywhere.
sys.path.insert(0, str(REPO_ROOT))

from alpha_engine.anti_overfit_validator import (  # noqa: E402
    align_returns_by_period,
    cpcv_pbo,
    deflated_sharpe,
    reality_check_pvalue,
)

# Every status the live ledger uses for a pick whose P&L is final. Aligns with
# the vocabularies already used elsewhere in the repo -- audit_trail/
# dashboard_generator.py, alpha_engine/reconciliation_report.py and
# tools/edge/edge_stability.py all recognise this same family. "WON" is the one
# the audit ledger actually emits; "WIN" is kept for older exports.
RESOLVED_STATUSES: frozenset[str] = frozenset({
    "WIN", "WON",
    "LOST", "LOSS",
    "CLOSED", "CLOSED_TP", "CLOSED_SL", "CLOSED_FLAT",
    "TP_HIT", "SL_HIT", "TAKE_PROFIT", "TIME_EXIT",
})

# Statuses that are legitimately NOT final -- excluded, never a vocabulary error.
UNRESOLVED_STATUSES: frozenset[str] = frozenset({
    "OPEN", "ACTIVE", "PENDING", "NEW", "EXPIRED", "CANCELLED", "CANCELED",
    "FLAT", "SKIPPED", "VOID", "UNKNOWN", "WATCHING", "",
})


def _assert_status_vocabulary_is_covered(picks: list[dict[str, Any]]) -> None:
    """Fail loudly if the ledger emits a resolved status we would silently drop.

    The 2026-11-20 WIN/WON defect survived every test because an unrecognised
    status is not an error -- it is simply a row that never appears. This guard
    converts that silent absence into a hard failure with the offending values
    named, so the next vocabulary drift breaks the build instead of biasing
    every statistic downstream.
    """
    seen = {str(p.get("status", "")).upper() for p in picks}
    unknown = seen - RESOLVED_STATUSES - UNRESOLVED_STATUSES
    if unknown:
        raise ValueError(
            "Closed-pick ledger contains statuses this module does not "
            f"classify: {sorted(unknown)}. Add each to either "
            "RESOLVED_STATUSES or UNRESOLVED_STATUSES in "
            "tools/run_anti_overfit_audit.py -- do not let them fall through, "
            "because an unclassified row is silently excluded and biases "
            "every DSR/PBO/Sharpe figure computed from this ledger."
        )


def _load_closed_picks() -> list[dict[str, Any]]:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"dashboard_data.json not found at {DATA_PATH}")
    with DATA_PATH.open("r", encoding="utf-8") as fh:
        d = json.load(fh)
    rc = d.get("picks", {}).get("recent_closed", [])
    _assert_status_vocabulary_is_covered(rc)
    return [
        p for p in rc
        if str(p.get("status", "")).upper() in RESOLVED_STATUSES
        and isinstance(p.get("pnl_pct"), (int, float))
    ]


def _system_returns(picks: list[dict[str, Any]], source_system: str) -> dict[str, Any]:
    """Return per-strategy returns + flat returns for a single source_system."""
    rows = [p for p in picks if p.get("source_system") == source_system]
    flat = np.array([p["pnl_pct"] / 100.0 for p in rows], dtype=np.float64)
    by_strategy: dict[str, list[float]] = defaultdict(list)
    # Timestamped series: PBO rows must be shared calendar periods, so the exit
    # time travels with every return (2026-11-20).
    series: dict[str, list[tuple[Any, float]]] = defaultdict(list)
    for p in rows:
        strat = p.get("strategy") or "unspecified"
        ret = p["pnl_pct"] / 100.0
        by_strategy[strat].append(ret)
        series[strat].append((p.get("closed_at") or p.get("timestamp"), ret))
    return {
        "n_picks": len(rows),
        "flat_returns": flat,
        "by_strategy": {k: np.array(v, dtype=np.float64) for k, v in by_strategy.items()},
        "series_by_strategy": dict(series),
    }


def _build_pbo_matrix(
    series_by_strategy: dict[str, list[tuple[Any, float]]],
    min_obs: int = 30,
    n_folds: int = 8,
) -> tuple[np.ndarray | None, list[Any], dict]:
    """Build a (T x S) matrix whose rows are SHARED calendar periods.

    Was ``cols = [v[:T] for v in eligible.values()]``: each strategy's own first
    T picks stacked onto the same rows. Two strategies that traded in different
    months were therefore compared as if row 0 happened at the same time, so the
    CPCV split mixed eras and the PBO logit measured the calendar rather than
    the selection process (fixed 2026-11-20).

    Now delegates to :func:`align_returns_by_period`, which aggregates each
    strategy's returns by exit timestamp onto one day/week/month grid and zero-
    fills periods where a strategy held nothing.
    """
    return align_returns_by_period(
        series_by_strategy,
        min_obs=min_obs,
        min_rows=max(2 * n_folds, 16),
    )


def _annualized_sharpe(returns: np.ndarray, periods_per_year: int = 252) -> float:
    if returns.size < 2:
        return float("nan")
    mu = returns.mean()
    sd = returns.std(ddof=1)
    if sd < 1e-12:
        return float("nan")
    return float(mu / sd * math.sqrt(periods_per_year))


def _per_period_sharpe(returns: np.ndarray) -> float:
    """Per-period (un-annualized) Sharpe.

    ``deflated_sharpe`` requires per-period units -- its Lo (2002) estimator
    variance scales with ``SR**2``, so an annualized input silently pushes the
    result toward 1.0 (a PASS) regardless of true edge. Fixed 2026-11-20;
    see ``reports/VALIDATION_LAYER_AUDIT_2026-11-20.md`` Defect A.
    """
    if returns.size < 2:
        return float("nan")
    mu = returns.mean()
    sd = returns.std(ddof=1)
    if sd < 1e-12:
        return float("nan")
    return float(mu / sd)


def _audit_one(source_system: str, picks: list[dict[str, Any]],
               n_trials: int, B: int) -> dict[str, Any]:
    info = _system_returns(picks, source_system)
    flat = info["flat_returns"]
    if flat.size < 30:
        return {
            "source_system": source_system,
            "n_picks": int(flat.size),
            "skipped": "insufficient sample (< 30 closed picks)",
        }

    # `sr` is ANNUALIZED -- for reporting only. DSR needs per-period units.
    sr = _annualized_sharpe(flat)
    sr_pp = _per_period_sharpe(flat)

    try:
        rc_p = reality_check_pvalue(flat, benchmark=0.0, B=B, block_size=10)
    except Exception as exc:  # pragma: no cover
        rc_p = float("nan")
        rc_err: str | None = f"{type(exc).__name__}: {exc}"
    else:
        rc_err = None

    try:
        dsr = deflated_sharpe(sr_pp, n_trials=n_trials, returns_array=flat)
    except Exception as exc:  # pragma: no cover
        dsr = float("nan")
        dsr_err: str | None = f"{type(exc).__name__}: {exc}"
    else:
        dsr_err = None

    M, periods, align_info = _build_pbo_matrix(info["series_by_strategy"])
    if M is None:
        pbo: float | None = None
        pbo_note = (
            "skipped (need >= 2 strategies with >= 30 timestamped picks; "
            f"{align_info.get('note') or align_info.get('n_cols')} columns)"
        )
    else:
        try:
            pbo = cpcv_pbo(M, n_folds=8, n_test_groups=2, period_index=periods)
            pbo_note = (
                f"matrix={M.shape[0]}x{M.shape[1]} aligned by exit ts "
                f"({align_info['period']}, coverage {align_info['coverage_pct']}%)"
            )
        except Exception as exc:  # pragma: no cover
            pbo = float("nan")
            pbo_note = f"error: {type(exc).__name__}: {exc}"

    return {
        "source_system": source_system,
        "n_picks": int(flat.size),
        "n_strategies": len(info["by_strategy"]),
        "annualized_sharpe": sr,
        "per_period_sharpe": sr_pp,
        "pbo": pbo,
        "pbo_note": pbo_note,
        "pbo_alignment": align_info,
        "reality_check_p": rc_p,
        "reality_check_err": rc_err,
        "deflated_sharpe": dsr,
        "deflated_sharpe_err": dsr_err,
    }


def _print_report(result: dict[str, Any]) -> None:
    name = result["source_system"]
    if "skipped" in result:
        print(f"[{name}] SKIP -- {result['skipped']} (n={result['n_picks']})")
        return
    sr = result["annualized_sharpe"]
    pbo = result["pbo"]
    rc_p = result["reality_check_p"]
    dsr = result["deflated_sharpe"]
    pbo_str = "n/a" if pbo is None or (isinstance(pbo, float) and math.isnan(pbo)) else f"{pbo:.3f}"
    print(
        f"[{name}] n={result['n_picks']} strats={result['n_strategies']} "
        f"SR_ann={sr:+.2f}"
    )
    print(
        f"  PBO={pbo_str:<6}  RC_pvalue={rc_p:.3f}  DSR={dsr:.3f}    "
        f"({result['pbo_note']})"
    )
    verdict = []
    if isinstance(pbo, float) and not math.isnan(pbo):
        verdict.append("PBO<0.5 OK" if pbo < 0.5 else "PBO>=0.5 OVERFIT")
    if not math.isnan(rc_p):
        verdict.append("RC_p<0.05 EDGE" if rc_p < 0.05 else "RC_p>=0.05 NOT_SIG")
    if not math.isnan(dsr):
        verdict.append("DSR>=0.95 GENUINE" if dsr >= 0.95 else "DSR<0.95 SUSPECT")
    print(f"  -> {' | '.join(verdict)}")


def _gate_failures(results: list[dict[str, Any]], dsr_threshold: float) -> list[str]:
    """Systems whose DSR failed the threshold, as human-readable lines.

    A skipped system is a failure too: "insufficient sample" is not a pass.
    """
    bad: list[str] = []
    for r in results:
        name = r.get("source_system")
        if "skipped" in r:
            bad.append(f"{name}: SKIPPED ({r['skipped']}) -- cannot certify")
            continue
        dsr = r.get("deflated_sharpe")
        if dsr is None or (isinstance(dsr, float) and math.isnan(dsr)):
            bad.append(f"{name}: DSR unavailable ({r.get('deflated_sharpe_err') or 'nan'})")
            continue
        if float(dsr) < dsr_threshold:
            bad.append(f"{name}: DSR {float(dsr):.4f} < {dsr_threshold:.2f}")
    return bad


def _autopick_top(picks: list[dict[str, Any]], k: int) -> list[str]:
    counts: dict[str, int] = defaultdict(int)
    for p in picks:
        counts[p.get("source_system", "")] += 1
    counts.pop("", None)
    return [s for s, _ in sorted(counts.items(), key=lambda kv: -kv[1])[:k]]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("source_systems", nargs="*", help="source_system names to audit")
    ap.add_argument("--top", type=int, default=0,
                    help="auto-pick the top-N source_systems by closed-pick count")
    ap.add_argument("--n-trials", type=int, default=200,
                    help="DSR multiple-testing trial count (default 200)")
    ap.add_argument("--B", type=int, default=1000,
                    help="bootstrap replications for Reality Check (default 1000)")
    ap.add_argument("--json", action="store_true",
                    help="emit machine-readable JSON instead of the text report")
    ap.add_argument("--gate", action="store_true",
                    help="exit 2 when any audited system fails the DSR threshold")
    ap.add_argument("--dsr-threshold", type=float, default=0.95,
                    help="DSR floor for --gate (default 0.95, Lopez de Prado AFML)")
    args = ap.parse_args(argv)

    picks = _load_closed_picks()
    if args.top:
        targets = _autopick_top(picks, args.top)
    else:
        targets = list(args.source_systems)
    if not targets:
        ap.error("provide at least one source_system or --top N")

    results = [_audit_one(s, picks, args.n_trials, args.B) for s in targets]

    if args.json:
        # numpy floats -> plain floats for JSON
        def _coerce(o: Any) -> Any:
            if isinstance(o, dict):
                return {k: _coerce(v) for k, v in o.items()}
            if isinstance(o, (list, tuple)):
                return [_coerce(v) for v in o]
            if isinstance(o, np.floating):
                return float(o)
            if isinstance(o, np.integer):
                return int(o)
            return o
        print(json.dumps(_coerce(results), indent=2, default=str))
    else:
        for r in results:
            _print_report(r)
            print()
    if args.gate:
        failures = _gate_failures(results, args.dsr_threshold)
        audited = sum(1 for r in results if "skipped" not in r)
        if failures:
            passing = max(0, audited - len(failures))
            print(
                f"\nANTI-OVERFIT GATE: FAIL -- {len(failures)}/{len(results)} systems "
                f"below DSR {args.dsr_threshold:.2f} "
                f"({passing}/{audited} audited systems pass)",
                file=sys.stderr,
            )
            for f in failures:
                print(f"  - {f}", file=sys.stderr)
            return 2
        print(
            f"\nANTI-OVERFIT GATE: PASS -- {audited}/{len(results)} systems at "
            f"DSR >= {args.dsr_threshold:.2f}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
