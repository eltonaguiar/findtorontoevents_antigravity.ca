#!/usr/bin/env python3
"""CI gate: money_ready_verdict.py must not declare a class MONEY_READY
when the canonical pf_registry says that class is below the Tier-2 PF floor.

Why this exists
---------------
The /audit "Money Ready" surface is driven by `alpha_engine/money_ready_verdict.py`,
which can compute a per-class PF from a *subset* ledger (`closed_picks`). The
canonical, policy-clean, slippage-net view lives in
`audit_dashboard/data/pf_registry.json` (see CLAUDE.md "PF Registry Canonical").
When the two disagree, the dashboard can show MONEY_READY on a class the
canonical ledger rates sub-floor — a live falsehood on the audit page.

This gate is independent of the (peer-hot) dashboard_generator.py. It fails the
build (exit 2) if any MONEY_READY class either:
  (1) has a canonical pf_registry PF below PF_FLOOR (1.5, Tier-2 minimum), or
  (2) is concentration-bypassed: top_symbol_share > CONC_LIMIT and the
      verdict's concentration cap did not engage.

Exit codes: 0 = clean, 2 = divergence/bypass found, 3 = could not evaluate.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PF_REGISTRY = REPO / "audit_dashboard" / "data" / "pf_registry.json"
VERDICT_SCRIPT = REPO / "alpha_engine" / "money_ready_verdict.py"

PF_FLOOR = 1.5      # Tier-2 minimum profit factor (CLAUDE.md / PERFORMANCE_CHARTER)
CONC_LIMIT_DEFAULT = 0.60   # default top-symbol-share concentration limit


def _conc_limits() -> tuple[float, dict]:
    """The concentration limits money_ready_verdict.py actually enforces.

    The gate must enforce the SAME per-class policy money_ready uses (e.g. the
    documented COMMODITY=0.85 override for the CT=F PROBATION->FULL promotion),
    not an invented stricter rule. Falls back to a flat default if the import
    is unavailable.
    """
    try:
        sys.path.insert(0, str(REPO / "alpha_engine"))
        from money_ready_verdict import (  # type: ignore
            MAX_SYMBOL_CONCENTRATION, MAX_SYMBOL_CONCENTRATION_BY_CLASS,
        )
        return float(MAX_SYMBOL_CONCENTRATION), dict(MAX_SYMBOL_CONCENTRATION_BY_CLASS)
    except Exception:
        return CONC_LIMIT_DEFAULT, {}


def _load_verdicts() -> dict:
    """Run money_ready_verdict.py --json and parse the per-class verdict map."""
    out = subprocess.run(
        [sys.executable, str(VERDICT_SCRIPT), "--json", "--ci"],
        capture_output=True, text=True, cwd=str(REPO), timeout=300,
    )
    if out.returncode != 0:
        print(f"::error::money_ready_verdict.py exited {out.returncode}")
        print(out.stderr[-1500:])
        sys.exit(3)
    # The script prints pure JSON; tolerate leading noise just in case.
    txt = out.stdout.strip()
    start = txt.find("{")
    if start < 0:
        print("::error::money_ready_verdict.py produced no JSON")
        sys.exit(3)
    return json.loads(txt[start:])


def _load_registry_pf() -> dict:
    """Return {asset_class: profit_factor} from the pf_registry canonical view."""
    reg = json.loads(PF_REGISTRY.read_text(encoding="utf-8"))
    canon_key = reg.get("canonical_view")
    rows = reg.get(canon_key)
    if not isinstance(rows, list):
        print(f"::error::pf_registry canonical_view '{canon_key}' is not a list")
        sys.exit(3)
    return {
        r["asset_class"]: r.get("profit_factor")
        for r in rows
        if isinstance(r, dict) and "asset_class" in r
    }, canon_key


def main() -> int:
    verdicts = _load_verdicts()
    registry_pf, canon_key = _load_registry_pf()
    conc_default, conc_by_class = _conc_limits()

    flags: list[str] = []
    checked: list[str] = []

    for cls, v in verdicts.items():
        if not isinstance(v, dict) or v.get("verdict") != "MONEY_READY":
            continue
        checked.append(cls)
        reg_pf = registry_pf.get(cls)

        # (1) PF divergence vs canonical registry.
        if reg_pf is None:
            print(f"::warning::{cls} MONEY_READY but pf_registry has no PF "
                  f"(undefined) -- cannot confirm against canonical floor")
        elif reg_pf < PF_FLOOR:
            flags.append(
                f"{cls}: MONEY_READY but canonical pf_registry "
                f"({canon_key}) PF={reg_pf:.3f} < {PF_FLOOR} floor "
                f"(verdict-reported PF={v.get('pf')})"
            )

        # (2) Concentration bypass. Enforce money_ready's OWN per-class limit
        # (e.g. the documented COMMODITY=0.85 CT=F-promotion override) -- the
        # gate must not invent a stricter rule than the policy it audits.
        share = v.get("top_symbol_share")
        capped = v.get("concentration_capped")
        limit = conc_by_class.get(cls.upper(), conc_default)
        if isinstance(share, (int, float)) and share > limit and not capped:
            flags.append(
                f"{cls}: MONEY_READY with top_symbol_share={share:.3f} "
                f"> {limit} class limit and concentration_capped=False "
                f"(top_symbol={v.get('top_symbol')})"
            )

    if not checked:
        print("ci_gate_money_ready_vs_registry: no MONEY_READY classes — PASS")
        return 0

    print(f"ci_gate_money_ready_vs_registry: checked MONEY_READY classes: "
          f"{', '.join(checked)}")
    if flags:
        for f in flags:
            print(f"::error::{f}")
        print(f"\nFAIL -- {len(flags)} money-ready/registry divergence(s). "
              f"The /audit Money-Ready surface disagrees with the canonical "
              f"pf_registry. Fix the verdict source or the registry before merge.")
        return 2

    print("PASS -- every MONEY_READY class clears the canonical PF floor "
          "and concentration limit.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
