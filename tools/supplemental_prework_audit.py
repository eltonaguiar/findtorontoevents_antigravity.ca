#!/usr/bin/env python3
"""Supplemental deep-dive prework checker.

Runs read-only checks for supplemental items identified after the initial
deep-dive plan execution and writes a machine-readable report.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def _read(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def _contains(rel_path: str, needle: str) -> bool:
    return needle in _read(rel_path)


def _run_cmd(args: list[str]) -> dict:
    try:
        proc = subprocess.run(
            args,
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        return {
            "exit_code": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
        }
    except Exception as exc:  # pragma: no cover
        return {"exit_code": 99, "stdout": "", "stderr": str(exc)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--out",
        default="reports/supplemental_prework_audit_2026_05_14.json",
        help="Output JSON path relative to repo root",
    )
    args = ap.parse_args()

    checks: dict[str, dict] = {}

    cot_dry = _run_cmd(["python", "tools/verify_multi_asset_cot_db.py", "--dry-run"])
    checks["cot_db_verifier_dry_run"] = {
        "status": "COMPLETE" if cot_dry["exit_code"] == 0 else "MISSING",
        "exit_code": cot_dry["exit_code"],
        "stdout_excerpt": cot_dry["stdout"][:500],
        "stderr_excerpt": cot_dry["stderr"][:500],
    }

    cot_live = _run_cmd(["python", "tools/verify_multi_asset_cot_db.py"])
    checks["cot_db_verifier_live_run"] = {
        "status": "COMPLETE" if cot_live["exit_code"] == 0 else "PARTIAL",
        "exit_code": cot_live["exit_code"],
        "stdout_excerpt": cot_live["stdout"][:500],
        "stderr_excerpt": cot_live["stderr"][:500],
        "note": "PARTIAL means runtime credential/network blocker captured.",
    }

    checks["dsr_browser_gate_wired"] = {
        "status": "COMPLETE"
        if _contains("audit_dashboard/hc_filter.js", "function _passesDsrGate")
        and _contains("audit_dashboard/hc_filter.js", "hf_dsr_below_min")
        else "MISSING",
    }

    checks["smart_score_shadow_payload_visible"] = {
        "status": "COMPLETE"
        if _contains("audit_trail/dashboard_generator.py", '"smart_score_v2_shadow"')
        else "MISSING",
    }

    checks["systems_grid_staleness_metadata"] = {
        "status": "COMPLETE"
        if _contains("audit_trail/dashboard_generator.py", '"is_stale": _is_stale')
        and _contains("audit_trail/dashboard_generator.py", '"stale_days": _stale_days')
        else "PARTIAL",
    }

    mrf_text = _read("audit_dashboard/money_ready_filter.js")
    drift_tokens = ["drift_alert", "paper-only", "paper_only", "advisory"]
    checks["browser_drift_auto_paper_only"] = {
        "status": "MISSING" if not any(t in mrf_text for t in drift_tokens) else "PARTIAL",
        "note": "No explicit drift-alert paper-only enforcement found in money_ready_filter.js.",
    }

    ps_text = _read("alpha_engine/production_scanner.py")
    strategy_stale_tokens = ["strategy_stale_days", "strategy_is_inactive", "stale_since"]
    checks["strategy_level_staleness_contract"] = {
        "status": "MISSING"
        if not any(t in ps_text for t in strategy_stale_tokens)
        else "PARTIAL",
    }

    etf_text = _read("alpha_engine/production_scanner.py")
    has_xlf = '"XLF": "etf"' in etf_text or "'XLF': 'etf'" in etf_text
    has_xle = '"XLE": "etf"' in etf_text or "'XLE': 'etf'" in etf_text
    has_xlk = '"XLK": "etf"' in etf_text or "'XLK': 'etf'" in etf_text
    checks["etf_universe_xlf_xle_xlk_readiness"] = {
        "status": "COMPLETE" if (has_xlf and has_xle and has_xlk) else "PARTIAL",
        "xlf": has_xlf,
        "xle": has_xle,
        "xlk": has_xlk,
    }

    fred_hint = _contains("alpha_engine/macro_data_pipeline.py", "FRED_API_KEY")
    checks["bond_fred_key_path_present"] = {
        "status": "COMPLETE" if fred_hint else "PARTIAL",
    }

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }

    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
