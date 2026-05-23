#!/usr/bin/env python3
"""
reconcile_pf_registry.py — canonical-vs-verdict reconciliation gate (A8 / Move #1)

PROBLEM
-------
Two surfaces report per-asset-class PF/WR and they disagree:

  * `audit_dashboard/data/pf_registry.json`  — the canonical, deduped,
    policy-clean registry built by `tools/build_pf_registry.py`.
  * `audit_dashboard/data/dashboard_data.json::performance.asset_class_health`
    — the /audit verdict surface, recomputed inside the dashboard generator.

Before this gate the divergence was silent: nobody knew the /audit COMMODITY
tile said PF 7.71 while the canonical registry said 1.25. A verdict number is
only trustworthy if a second, independent computation agrees with it — or, if
they disagree, the disagreement is surfaced loudly.

WHAT THIS DOES
--------------
Compares the registry's policy-clean view (the view that applies the SAME
strategy/source exclusions the verdict applies) against asset_class_health,
per asset class, and prints a divergence table. Exits non-zero when any class
diverges beyond tolerance so CI / a human notices.

This is READ-ONLY. It builds nothing and runs no generator.

USAGE
-----
    python tools/reconcile_pf_registry.py [--pf-tol 0.25] [--n-tol-pct 20]

Exit codes: 0 = all classes reconcile (or only-warn), 2 = divergence found,
1 = a required input file is missing.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY = "audit_dashboard/data/pf_registry.json"
DASHBOARD = "audit_dashboard/data/dashboard_data.json"


def _load(rel: str):
    path = os.path.join(REPO_ROOT, rel)
    if not os.path.isfile(path):
        print("ERROR: missing input file: %s" % rel, file=sys.stderr)
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        print("ERROR: cannot read %s: %s" % (rel, exc), file=sys.stderr)
        return None


def _registry_policy_map(registry: dict) -> dict:
    """asset_class -> {pf, n} from the canonical net policy-clean view (M-067):
    deduped, verdict-excluded strategies removed, AND per-class round-trip
    slippage deducted — apples-to-apples with the /audit money-grade verdict.
    Falls back to the gross policy-clean view for older registry schemas."""
    out = {}
    rows = (registry.get("by_asset_class_policy_clean_net")
            or registry.get("by_asset_class_policy_clean", []))
    for r in rows:
        out[str(r.get("asset_class", "")).upper()] = {
            "pf": r.get("profit_factor"),
            "n": r.get("n"),
        }
    return out


def _health_map(dashboard: dict) -> dict:
    """asset_class -> {pf, n} from performance.asset_class_health."""
    health = (dashboard.get("performance", {}) or {}).get(
        "asset_class_health", {}) or {}
    out = {}
    for ac, h in health.items():
        if not isinstance(h, dict):
            continue
        out[str(ac).upper()] = {
            "pf": h.get("pf") if h.get("pf") is not None
            else h.get("profit_factor"),
            "n": h.get("n") if h.get("n") is not None
            else h.get("resolved_n"),
        }
    return out


def _fmt(v):
    if v is None:
        return "-"
    if isinstance(v, float):
        return "%.2f" % v
    return str(v)


def reconcile(pf_tol: float, n_tol_pct: float) -> int:
    registry = _load(REGISTRY)
    dashboard = _load(DASHBOARD)
    if registry is None or dashboard is None:
        return 1

    if not registry.get("source_files_canonical", False):
        print("WARN: registry was built from the fallback source list — its "
              "input is NOT provably identical to /audit; reconciliation "
              "below is indicative only.\n")

    reg = _registry_policy_map(registry)
    dash = _health_map(dashboard)
    classes = sorted(set(reg) | set(dash))

    print("PF REGISTRY RECONCILIATION  (registry policy-clean  vs  "
          "asset_class_health)")
    print("  generated: registry=%s" % registry.get("generated_utc", "?"))
    print("  tolerance: |dPF| <= %.2f , |dn| <= %.0f%%\n" % (pf_tol, n_tol_pct))
    print("  %-12s %9s %9s %8s | %7s %7s %7s | %s" % (
        "ASSET_CLASS", "REG_PF", "DASH_PF", "dPF",
        "REG_n", "DASH_n", "dn%", "VERDICT"))

    diverged = []
    for ac in classes:
        r = reg.get(ac, {})
        d = dash.get(ac, {})
        rpf, dpf = r.get("pf"), d.get("pf")
        rn, dn = r.get("n"), d.get("n")

        notes = []
        if rpf is None or dpf is None:
            notes.append("PF-missing")
            dpf_delta = None
        else:
            dpf_delta = abs(float(rpf) - float(dpf))
            if dpf_delta > pf_tol:
                notes.append("PF-DIVERGE")

        if rn and dn:
            dn_pct = abs(rn - dn) / max(rn, dn) * 100.0
            if dn_pct > n_tol_pct:
                notes.append("n-DIVERGE")
        else:
            dn_pct = None
            notes.append("n-missing")

        verdict = "OK" if not notes else " ".join(notes)
        if "PF-DIVERGE" in verdict or "n-DIVERGE" in verdict:
            diverged.append(ac)

        print("  %-12s %9s %9s %8s | %7s %7s %7s | %s" % (
            ac, _fmt(rpf), _fmt(dpf), _fmt(dpf_delta),
            _fmt(rn), _fmt(dn),
            ("%.0f" % dn_pct) if dn_pct is not None else "-",
            verdict))

    print()
    if diverged:
        print("DIVERGENCE: %d class(es) beyond tolerance: %s" % (
            len(diverged), ", ".join(diverged)))
        print("The /audit verdict and the canonical registry disagree. Until "
              "resolved, no PF number for these classes is verdict-grade.")
        return 2
    print("RECONCILED: every asset class agrees within tolerance.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pf-tol", type=float, default=0.25,
                    help="max allowed absolute PF difference (default 0.25)")
    ap.add_argument("--n-tol-pct", type=float, default=20.0,
                    help="max allowed n difference, percent (default 20)")
    args = ap.parse_args()
    return reconcile(args.pf_tol, args.n_tol_pct)


if __name__ == "__main__":
    sys.exit(main())
