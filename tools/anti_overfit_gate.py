#!/usr/bin/env python3
"""Blocking anti-overfit gate.

Every statistical gate in this repo has historically been advisory
(``continue-on-error: true``), so a strategy can fail DSR/PBO and still be
promoted. This script is the enforcement point: it exits non-zero.

Contracts
---------
* **Fail closed.** A statistic that could not be computed is a FAILED gate.
  ``nan < 0.95`` is False and ``nan >= 0.05`` is False, so the naive
  ``if v < threshold`` form silently passes an unmeasurable metric. We treat
  ``nan``/``None`` as an explicit failure, never a pass.
* **Per-period Sharpe.** DSR is deflated against per-period units. Feeding it
  an annualised Sharpe inflates the result by sqrt(252) and manufactures
  significance; ``deflated_sharpe`` rejects that with a ValueError.
* **Real peer matrix only.** PBO needs >= 2 competing strategies. A single
  return series cannot produce PBO -- see ``tools/pbo.py``.

Usage
-----
    python3 tools/anti_overfit_gate.py --top 5
    python3 tools/anti_overfit_gate.py --source-system claude_gainer_st
    python3 tools/anti_overfit_gate.py --top 5 --json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.run_anti_overfit_audit import (  # noqa: E402
    _audit_one,
    _autopick_top,
    _load_closed_picks,
)

# Promotion thresholds ("north star" gates).
DSR_MIN = 0.95
PBO_MAX = 0.05
MIN_PICKS = 100          # below this the gate is not evaluable, so it fails
MIN_STRATEGIES_FOR_PBO = 2


def _is_bad_number(value: Any) -> bool:
    """True when ``value`` is missing or nan."""
    if value is None:
        return True
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return isinstance(value, float) and math.isnan(value)
    return True


def check_result(result: dict[str, Any]) -> list[str]:
    """Return a list of gate failures for one audited source system.

    Empty list means the source system passed every evaluable gate.
    """
    failures: list[str] = []

    if result.get("skipped"):
        return [f"gate not evaluable: {result['skipped']}"]

    n = result.get("n_picks") or 0
    if n < MIN_PICKS:
        failures.append(
            f"n={n} < {MIN_PICKS} closed picks: sample too small to clear "
            f"the DSR/PBO gates"
        )

    dsr = result.get("deflated_sharpe")
    if _is_bad_number(dsr):
        err = result.get("deflated_sharpe_err")
        failures.append(
            f"DSR NOT EVALUABLE (nan/None){' -- ' + str(err) if err else ''}"
        )
    elif dsr < DSR_MIN:
        failures.append(f"DSR {dsr:.4f} < {DSR_MIN} (multiple-testing "
                        f"correction not survived)")

    pbo = result.get("pbo")
    if pbo is None:
        failures.append(
            "PBO NOT EVALUABLE (no peer matrix) -- "
            f"{result.get('pbo_note', 'need >= 2 strategies')}"
        )
    elif _is_bad_number(pbo):
        failures.append(
            f"PBO NOT EVALUABLE (nan){' -- ' + str(result.get('pbo_note')) if result.get('pbo_note') else ''}"
        )
    elif pbo >= PBO_MAX:
        failures.append(f"PBO {pbo:.4f} >= {PBO_MAX} (backtest overfit)")

    return failures


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-system", action="append", default=[],
                    help="source_system to gate (repeatable)")
    ap.add_argument("--top", type=int, default=0,
                    help="gate the N highest-pick-count source systems")
    ap.add_argument("--n-trials", type=int, default=200,
                    help="DSR trial-accounting count (default 200)")
    ap.add_argument("--B", type=int, default=1000,
                    help="bootstrap replications for the Reality Check")
    ap.add_argument("--json", action="store_true",
                    help="emit machine-readable JSON")
    ap.add_argument("--allow-empty", action="store_true",
                    help="exit 0 when no source systems are selected "
                         "(cron safety valve; never use on a promotion PR)")
    args = ap.parse_args(argv)

    try:
        picks = _load_closed_picks()
    except FileNotFoundError as exc:
        print(f"[anti-overfit-gate] FAIL: closed-pick data unavailable.\n"
              f"  {exc}\n"
              f"  The gate cannot measure DSR/PBO without a closed-pick "
              f"ledger, and an unmeasured gate is a FAILED gate.", file=sys.stderr)
        return 2
    if args.top:
        targets = _autopick_top(picks, args.top)
    else:
        targets = list(dict.fromkeys(args.source_system))

    if not targets:
        msg = ("no source systems selected: pass --source-system and/or "
               "--top N")
        if args.allow_empty:
            print(f"[anti-overfit-gate] SKIP: {msg}", file=sys.stderr)
            return 0
        print(f"[anti-overfit-gate] FAIL: {msg}", file=sys.stderr)
        return 2

    report: dict[str, Any] = {
        "thresholds": {"dsr_min": DSR_MIN, "pbo_max": PBO_MAX,
                       "min_picks": MIN_PICKS},
        "systems": [],
    }
    any_fail = False

    for system in targets:
        result = _audit_one(system, picks, args.n_trials, args.B)
        failures = check_result(result)
        if failures:
            any_fail = True
        report["systems"].append({
            "source_system": system,
            "n_picks": result.get("n_picks"),
            "deflated_sharpe": result.get("deflated_sharpe"),
            "pbo": result.get("pbo"),
            "per_period_sharpe": result.get("per_period_sharpe"),
            "passed": not failures,
            "failures": failures,
        })

    report["passed"] = not any_fail

    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print("=" * 72)
        print("ANTI-OVERFIT GATE -- BLOCKING")
        print(f"  DSR >= {DSR_MIN}   PBO < {PBO_MAX}   n >= {MIN_PICKS}")
        print("  Unmeasurable (nan/None) statistics FAIL the gate.")
        print("=" * 72)
        for entry in report["systems"]:
            status = "PASS" if entry["passed"] else "FAIL"
            print(f"\n[{status}] {entry['source_system']}  "
                  f"(n={entry['n_picks']})")
            print(f"        DSR={entry['deflated_sharpe']}  "
                  f"PBO={entry['pbo']}  "
                  f"SR/period={entry['per_period_sharpe']}")
            for failure in entry["failures"]:
                print(f"        - {failure}")
        print()
        print("RESULT:", "PASS" if report["passed"] else "FAIL")
        print("=" * 72)

    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
