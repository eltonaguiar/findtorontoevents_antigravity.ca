#!/usr/bin/env python3
"""Turn a db_freshness.json report into a PASS/FAIL job verdict.

Why this exists
---------------
`tools/db_freshness_check.py` returns a tri-state exit code that encodes real
health (0=GREEN, 1=YELLOW, 2=RED). Until 2026-11-26 the workflow that runs it
(`.github/workflows/db-freshness-guardian.yml`) set `continue-on-error: true`
on that step, which discarded all three codes -- so the hourly guard could only
ever report success. A genuinely stale trading DB produced a green checkmark.

The reason `continue-on-error` was there is legitimate: when the CI environment
has no DB credentials, the script cannot connect and exits 2. Failing the job on
"no secrets configured" would make the workflow red for an infrastructure reason
that is not a data problem.

This script distinguishes the two cases using the report the check always
writes, then applies the policy:

    overall GREEN            -> exit 0 (pass)
    overall YELLOW           -> exit 0 (pass, annotated as degraded)
    overall RED, all REDs are
      connectivity failures  -> exit 0 (pass, annotated as unverified)
    overall RED, any RED has
      real staleness data    -> exit 1 (fail the job)

Discriminator
-------------
`db_freshness_check.py` writes two structurally different kinds of RED check:

  * connectivity failure -> {"check": "live_picks", "status": "RED", "error": "..."}
  * genuine staleness    -> {"check": "live_picks", "status": "RED",
                             "minutes_stale": 1234, "last_pick_at": "...", ...}

So the presence of an `error` key marks an environment failure; a RED without
`error` is a real data finding and must fail the job.

If the report is missing or unreadable the script exits 0 (cannot judge) but
annotates a warning -- a missing report must not be silently treated as healthy
without the annotation, and must not fail the job because a parse bug in this
verdict script is not a trading-data problem.

Usage
-----
    python tools/db_freshness_verdict.py [report.json]

Exit codes: 0 = pass, 1 = fail (real staleness), 2 = report missing/unreadable
(2 is only used when --strict is passed; default is 0 + warning).
"""
from __future__ import annotations

import json
import sys
from typing import Any, Dict, List

DEFAULT_REPORT = "audit_dashboard/data/db_freshness.json"


def _emit(level: str, msg: str) -> None:
    """Emit a GitHub Actions annotation, falling back to plain text locally."""
    print(f"::{level}::{msg}")


def classify(report: Dict[str, Any]) -> Dict[str, Any]:
    """Classify a report into a verdict.

    Returns a dict with keys: overall, reds, env_reds, data_reds, should_fail, reason.
    Pure function -- no I/O -- so it is unit-testable.
    """
    overall = report.get("overall", "RED")
    checks: List[Dict[str, Any]] = report.get("checks") or []

    # SKIPPED checks never contribute to `overall` in db_freshness_check.py,
    # so they must not contribute here either.
    reds = [
        c for c in checks
        if isinstance(c, dict) and c.get("status") == "RED"
    ]
    env_reds = [c for c in reds if c.get("error")]
    data_reds = [c for c in reds if not c.get("error")]

    if overall == "GREEN":
        return {
            "overall": overall, "reds": reds, "env_reds": env_reds,
            "data_reds": data_reds, "should_fail": False,
            "reason": "all checks GREEN",
        }
    if overall == "YELLOW":
        return {
            "overall": overall, "reds": reds, "env_reds": env_reds,
            "data_reds": data_reds, "should_fail": False,
            "reason": "YELLOW is a warning per workflow contract, not a failure",
        }

    # overall == RED (or an unknown value, which we treat as RED)
    if data_reds:
        names = ", ".join(str(c.get("check", "?")) for c in data_reds)
        return {
            "overall": "RED", "reds": reds, "env_reds": env_reds,
            "data_reds": data_reds, "should_fail": True,
            "reason": f"genuine staleness in: {names}",
        }
    if env_reds:
        return {
            "overall": "RED", "reds": reds, "env_reds": env_reds,
            "data_reds": data_reds, "should_fail": False,
            "reason": (
                "every RED is a DB connectivity failure, not staleness "
                "(secrets likely absent in this environment)"
            ),
        }
    # RED with no per-check detail at all -- cannot attribute, do not fail.
    return {
        "overall": "RED", "reds": reds, "env_reds": env_reds,
        "data_reds": data_reds, "should_fail": False,
        "reason": "overall RED but no per-check RED detail available",
    }


def main(argv: List[str]) -> int:
    path = DEFAULT_REPORT
    strict = False
    for arg in argv[1:]:
        if arg == "--strict":
            strict = True
        elif not arg.startswith("-"):
            path = arg

    try:
        with open(path, "r", encoding="utf-8") as f:
            report = json.load(f)
    except FileNotFoundError:
        _emit("warning", f"Freshness report not found at {path} -- cannot judge; passing.")
        return 2 if strict else 0
    except Exception as exc:  # unreadable / malformed
        _emit("warning", f"Freshness report unreadable ({exc}) -- cannot judge; passing.")
        return 2 if strict else 0

    if not isinstance(report, dict):
        _emit("warning", "Freshness report is not a JSON object -- cannot judge; passing.")
        return 2 if strict else 0

    v = classify(report)

    if v["overall"] == "GREEN":
        print(f"DB freshness GREEN -- {v['reason']}")
        return 0

    if v["overall"] == "YELLOW":
        _emit("warning", f"DB freshness YELLOW (degraded, not failing) -- {v['reason']}")
        return 0

    if v["should_fail"]:
        detail = "; ".join(
            f"{c.get('check')}: minutes_stale={c.get('minutes_stale')} "
            f"(last={c.get('last_pick_at') or c.get('last_resolved_at') or c.get('last_trade_at') or c.get('last_intrabar_resolved_at')})"
            for c in v["data_reds"]
        )
        _emit("error", f"DB freshness RED -- {v['reason']}. {detail}")
        return 1

    # RED but environment-attributed: annotate loudly, do not fail.
    _emit("warning", f"DB freshness RED ignored -- {v['reason']}")
    for c in v["env_reds"]:
        print(f"  - {c.get('check')}: {str(c.get('error'))[:300]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
