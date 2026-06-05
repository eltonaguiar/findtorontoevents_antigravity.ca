#!/usr/bin/env python3
"""Pick-data-quality CI gate (MLOps research #1 recommendation, 2026-06-04).

Consolidates the two existing report-only checkers into ONE pass/fail gate over the
canonical closed-picks ledger, so data-quality regressions are caught in CI instead
of silently polluting WR/PF (the root of the "all-red" episode):
  - resolver_hygiene_check.scan_ledger  -> never_closed / duplicates / mislabels / missing_provenance
  - backfill_provenance.backfill_report -> signal_ts + source coverage

The MLOps review (reports/MLOPS_RESEARCH_2026-06-04.md) named data-validation gates the
single highest-ROI MLOps addition: catch the signal_ts / provenance / toxic-row issues
automatically. This is that gate — report-only (never mutates the ledger), exit code
0=pass / 1=fail so a GH Action can block on it.

Thresholds (tunable via env): fail if mislabels>0, or missing-provenance share, toxic
share, or never-closed share exceed caps. Duplicate detection only counts groups with a
real signal_ts (see resolver_hygiene_check fix).

Usage: python tools/pick_data_quality_gate.py [ledger.json]   (default: canonical ledger)
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import resolver_hygiene_check as rh
import backfill_provenance as bp

DEFAULT_LEDGER = os.path.join(ROOT, "alpha_engine", "data", "closed_picks.json")

# Pass/fail caps (fractions of total rows unless noted).
MAX_MISLABELS = int(os.environ.get("PDQ_MAX_MISLABELS", "0"))          # any mislabel fails
MAX_MISSING_PROVENANCE_PCT = float(os.environ.get("PDQ_MAX_MISSING_PROV_PCT", "30"))
MAX_TOXIC_PCT = float(os.environ.get("PDQ_MAX_TOXIC_PCT", "40"))      # FORCE_CLOSED/RESOLVE_FAILED
MAX_NEVER_CLOSED_PCT = float(os.environ.get("PDQ_MAX_NEVER_CLOSED_PCT", "5"))


def _toxic_share(picks):
    if not picks:
        return 0.0, 0
    toxic = sum(1 for p in picks
                if str(p.get("exit_reason") or "").upper()
                in ("FORCE_CLOSED_TOXIC", "RESOLVE_FAILED_MAX_RETRIES"))
    return round(100 * toxic / len(picks), 2), toxic


def evaluate(picks):
    n = len(picks)
    hygiene = rh.scan_ledger(picks)
    backfill = bp.backfill_report(picks)
    toxic_pct, toxic_n = _toxic_share(picks)
    miss_prov_pct = round(100 * hygiene["missing_provenance"] / n, 2) if n else 0.0
    never_pct = round(100 * hygiene["never_closed"] / n, 2) if n else 0.0

    checks = [
        ("mislabels", hygiene["mislabels"], MAX_MISLABELS, hygiene["mislabels"] <= MAX_MISLABELS, "count"),
        ("missing_provenance_pct", miss_prov_pct, MAX_MISSING_PROVENANCE_PCT,
         miss_prov_pct <= MAX_MISSING_PROVENANCE_PCT, "%"),
        ("toxic_pct", toxic_pct, MAX_TOXIC_PCT, toxic_pct <= MAX_TOXIC_PCT, "%"),
        ("never_closed_pct", never_pct, MAX_NEVER_CLOSED_PCT, never_pct <= MAX_NEVER_CLOSED_PCT, "%"),
    ]
    passed = all(c[3] for c in checks)
    return {
        "n_total": n,
        "passed": passed,
        "checks": [{"name": c[0], "value": c[1], "cap": c[2], "pass": c[3], "unit": c[4]} for c in checks],
        "signal_ts_coverage_after_backfill_pct": backfill["signal_ts"]["coverage_after_backfill_pct"],
        "source_coverage_after_backfill_pct": backfill["source"]["coverage_after_backfill_pct"],
        "duplicate_groups": hygiene["duplicate_groups"],
        "toxic_rows": toxic_n,
        "_mutated_ledger": False,
    }


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_LEDGER
    data = json.load(open(path, encoding="utf-8"))
    picks = data if isinstance(data, list) else data.get("picks", data.get("rows", []))
    rep = evaluate(picks)
    print(json.dumps(rep, indent=2, default=str))
    print(("PASS" if rep["passed"] else "FAIL") + f" — pick-data-quality gate ({rep['n_total']} rows)")
    sys.exit(0 if rep["passed"] else 1)


if __name__ == "__main__":  # pragma: no cover
    main()
