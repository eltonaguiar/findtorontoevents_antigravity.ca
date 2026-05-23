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
  ``picks.recent_closed[]``, filtered to ``status in {WIN, LOST}`` so that
  pending/active rows are excluded.
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
    cpcv_pbo,
    deflated_sharpe,
    reality_check_pvalue,
)


def _load_closed_picks() -> list[dict[str, Any]]:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"dashboard_data.json not found at {DATA_PATH}")
    with DATA_PATH.open("r", encoding="utf-8") as fh:
        d = json.load(fh)
    rc = d.get("picks", {}).get("recent_closed", [])
    return [
        p for p in rc
        if str(p.get("status", "")).upper() in {"WIN", "LOST"}
        and isinstance(p.get("pnl_pct"), (int, float))
    ]


def _system_returns(picks: list[dict[str, Any]], source_system: str) -> dict[str, Any]:
    """Return per-strategy returns + flat returns for a single source_system."""
    rows = [p for p in picks if p.get("source_system") == source_system]
    flat = np.array([p["pnl_pct"] / 100.0 for p in rows], dtype=np.float64)
    by_strategy: dict[str, list[float]] = defaultdict(list)
    for p in rows:
        strat = p.get("strategy") or "unspecified"
        by_strategy[strat].append(p["pnl_pct"] / 100.0)
    return {
        "n_picks": len(rows),
        "flat_returns": flat,
        "by_strategy": {k: np.array(v, dtype=np.float64) for k, v in by_strategy.items()},
    }


def _build_pbo_matrix(by_strategy: dict[str, np.ndarray], min_obs: int = 30) -> np.ndarray | None:
    """Build a (T x S) matrix of equal-length per-strategy returns for PBO.

    We trim/pad each strategy series to the shortest length >= ``min_obs`` so
    the matrix is rectangular. Strategies with < ``min_obs`` picks are dropped.
    """
    eligible = {k: v for k, v in by_strategy.items() if len(v) >= min_obs}
    if len(eligible) < 2:
        return None
    T = min(len(v) for v in eligible.values())
    if T < min_obs:
        return None
    cols = [v[:T] for v in eligible.values()]
    return np.column_stack(cols)


def _annualized_sharpe(returns: np.ndarray, periods_per_year: int = 252) -> float:
    if returns.size < 2:
        return float("nan")
    mu = returns.mean()
    sd = returns.std(ddof=1)
    if sd < 1e-12:
        return float("nan")
    return float(mu / sd * math.sqrt(periods_per_year))


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

    sr = _annualized_sharpe(flat)

    try:
        rc_p = reality_check_pvalue(flat, benchmark=0.0, B=B, block_size=10)
    except Exception as exc:  # pragma: no cover
        rc_p = float("nan")
        rc_err: str | None = f"{type(exc).__name__}: {exc}"
    else:
        rc_err = None

    try:
        dsr = deflated_sharpe(sr, n_trials=n_trials, returns_array=flat)
    except Exception as exc:  # pragma: no cover
        dsr = float("nan")
        dsr_err: str | None = f"{type(exc).__name__}: {exc}"
    else:
        dsr_err = None

    M = _build_pbo_matrix(info["by_strategy"])
    if M is None:
        pbo: float | None = None
        pbo_note = "skipped (need >= 2 strategies with >= 30 picks each)"
    else:
        try:
            pbo = cpcv_pbo(M, n_folds=8, n_test_groups=2)
            pbo_note = (
                f"matrix={M.shape[0]}x{M.shape[1]} (T x strategies)"
            )
        except Exception as exc:  # pragma: no cover
            pbo = float("nan")
            pbo_note = f"error: {type(exc).__name__}: {exc}"

    return {
        "source_system": source_system,
        "n_picks": int(flat.size),
        "n_strategies": len(info["by_strategy"]),
        "annualized_sharpe": sr,
        "pbo": pbo,
        "pbo_note": pbo_note,
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
