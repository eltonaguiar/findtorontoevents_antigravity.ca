#!/usr/bin/env python3
"""strand_b_audit_regression_check.py — post-implementation /audit regression
gate for the STRAND B research modules (options_flow / onchain_crypto).

STRAND B modules are opt-in research SIDECARS — they must NOT change /audit.
This script proves that, three ways:

  1. WIRE-UP — no production caller imports the STRAND B modules in the
     pick-generation / scoring path (audit_trail/, alpha_engine/).
  2. asset_class_health — per-class PF / WR / n in
     audit_dashboard/data/dashboard_data.json is byte-identical to a baseline.
  3. pf_registry — by_asset_class_policy_clean_net is identical to baseline.

First run writes the baseline (run it on origin/main BEFORE the STRAND B PRs
merge). Re-run after the next hourly pipeline job: any drift = a sidecar
leaked into production -> revert + fix the Wire-Up violation.

Read-only. Zero pip deps. Exit 0 = PASS, 1 = regression detected.
"""
from __future__ import annotations

import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASH = os.path.join(REPO, "audit_dashboard", "data", "dashboard_data.json")
PFREG = os.path.join(REPO, "audit_dashboard", "data", "pf_registry.json")
BASELINE = os.path.join(REPO, "reports", "strand_b_baseline.json")

STRAND_B_MODULES = ("options_flow_research", "onchain_crypto_research")
# Directories that constitute the production pick-generation / scoring path.
PROD_DIRS = ("audit_trail", "alpha_engine")


def _load(path: str):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None


def _ach(dashboard: dict) -> dict:
    """Per-class {pf, wr, n} from asset_class_health — the verdict-grade view."""
    h = (dashboard or {}).get("performance", {}).get("asset_class_health", {})
    out = {}
    if isinstance(h, dict):
        for ac, row in h.items():
            if isinstance(row, dict):
                out[ac] = {
                    "pf": row.get("pf", row.get("profit_factor")),
                    "wr": row.get("wr_pct", row.get("win_rate")),
                    "n": row.get("resolved_n", row.get("n")),
                }
    return out


def _pf_clean(reg: dict) -> dict:
    v = (reg or {}).get("by_asset_class_policy_clean_net", {})
    return v if isinstance(v, dict) else {}


def _wireup_violations() -> list[str]:
    """Files in the production path that import a STRAND B module."""
    hits = []
    pat = re.compile(r"\b(%s)\b" % "|".join(STRAND_B_MODULES))
    for d in PROD_DIRS:
        root = os.path.join(REPO, d)
        for dirpath, _, files in os.walk(root):
            for fn in files:
                if not fn.endswith(".py"):
                    continue
                fp = os.path.join(dirpath, fn)
                try:
                    with open(fp, encoding="utf-8", errors="ignore") as fh:
                        if pat.search(fh.read()):
                            hits.append(os.path.relpath(fp, REPO))
                except OSError:
                    continue
    return hits


def main() -> int:
    snapshot = {
        "asset_class_health": _ach(_load(DASH) or {}),
        "pf_registry_clean": _pf_clean(_load(PFREG) or {}),
    }

    if not os.path.isfile(BASELINE):
        with open(BASELINE, "w", encoding="utf-8") as fh:
            json.dump(snapshot, fh, indent=1, sort_keys=True)
        print("BASELINE WRITTEN -> reports/strand_b_baseline.json")
        print("Re-run this script after the STRAND B PRs merge + the next "
              "hourly pipeline job to check for regression.")
        return 0

    baseline = _load(BASELINE) or {}
    fails = []

    wire = _wireup_violations()
    if wire:
        fails.append("WIRE-UP: STRAND B module imported in production path: "
                      + ", ".join(wire))

    if snapshot["asset_class_health"] != baseline.get("asset_class_health"):
        fails.append("asset_class_health drifted vs baseline — a sidecar "
                     "changed /audit verdict numbers")

    if snapshot["pf_registry_clean"] != baseline.get("pf_registry_clean"):
        fails.append("pf_registry by_asset_class_policy_clean_net drifted "
                     "vs baseline")

    if fails:
        print("REGRESSION DETECTED — STRAND B leaked into production:")
        for f in fails:
            print("  FAIL: " + f)
        return 1

    print("PASS — STRAND B modules are clean sidecars: no production caller, "
          "/audit asset_class_health + pf_registry unchanged.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
