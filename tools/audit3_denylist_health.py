"""audit3_denylist_health.py — fail loudly when the denylist is not actually armed.

The gate fails open by design (a missing ledger must never halt the scanner), and
fail-open is exactly how a broken cron turns into silent non-enforcement. This is
the loud half: if the ledger is missing, stale, or loaded zero kills, exit non-zero
so the workflow goes red and somebody looks.

    python3 tools/audit3_denylist_health.py --max-age-days 2 --min-strategy-kills 1

Exit codes: 0 healthy; 1 not armed / stale / too few kills.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alpha_engine.audit3_denylist import DEFAULT_LEDGER, summary  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="audit3 denylist health check")
    ap.add_argument("--ledger", default=DEFAULT_LEDGER)
    ap.add_argument("--max-age-days", type=float, default=2.0)
    ap.add_argument("--min-strategy-kills", type=int, default=1)
    args = ap.parse_args(argv)

    state = summary(args.ledger)
    state["max_age_days_checked"] = args.max_age_days
    print(json.dumps(state, indent=1))

    problems = []
    if not state["armed"]:
        problems.append(f"not armed: {state['note']}")
    else:
        age = state.get("age_days")
        if age is None or age > args.max_age_days:
            problems.append(f"ledger is {age} days old (limit {args.max_age_days})")
        if state["n_strategy_kills"] < args.min_strategy_kills:
            problems.append(
                f"loaded {state['n_strategy_kills']} strategy kills "
                f"(need >= {args.min_strategy_kills})")

    if problems:
        for p in problems:
            print(f"::error title=audit3 denylist::{p}", file=sys.stderr)
        return 1
    print("denylist healthy: armed, recent, and carrying kills")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
