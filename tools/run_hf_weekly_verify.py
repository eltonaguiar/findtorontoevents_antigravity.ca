#!/usr/bin/env python3
"""
Weekly hedge-fund verification runner.

Runs:
1) HC validation stack (`tools/run_hc_plan_validation.py`)
2) CSV-based hedge-fund review (`tools/hf_enhancement_review.py`)
3) Threshold checks for profitability/risk targets
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]


def _run(cmd: list[str]) -> tuple[bool, int]:
    proc = subprocess.run(cmd, cwd=_REPO, check=False)
    return proc.returncode == 0, proc.returncode


def _check_targets(report: dict) -> tuple[bool, list[str]]:
    issues: list[str] = []
    by_ac = report.get("closed_by_asset_class", {})
    active = report.get("active_inventory", {})
    concentration = report.get("active_concentration", {})
    by_tier = report.get("closed_by_trust_tier", {})
    pass_watch = report.get("active_pass_watchlist", {})
    score_tier_validation = report.get("score_tier_validation", {})

    crypto_pf = (by_ac.get("CRYPTO") or {}).get("profit_factor")
    if crypto_pf is None or crypto_pf < 1.25:
        issues.append(f"CRYPTO profit_factor below target (got {crypto_pf})")

    non_crypto = [k for k in by_ac.keys() if k != "CRYPTO"]
    non_crypto_sum = 0.0
    for ac in non_crypto:
        non_crypto_sum += float((by_ac.get(ac) or {}).get("sum_pnl_pct") or 0.0)
    if non_crypto_sum < -50.0:
        issues.append(f"Non-crypto sum_pnl too negative ({non_crypto_sum:.2f}%)")

    top_system_share = float(concentration.get("top_system_share_pct") or 0.0)
    if top_system_share > 35.0:
        issues.append(f"Top system concentration too high ({top_system_share:.2f}%)")

    pass_rate = float(pass_watch.get("pass_rate_pct") or 0.0)
    if pass_rate < 6.0 or pass_rate > 15.0:
        issues.append(f"Enhanced pass-rate outside guardrail ({pass_rate:.2f}%)")
    pass_symbol = float(pass_watch.get("top_symbol_share_pct") or 0.0)
    if pass_symbol > 30.0:
        issues.append(f"Pass-set symbol concentration too high ({pass_symbol:.2f}%)")

    if not bool(score_tier_validation.get("avg_pnl_monotonic_non_decreasing")):
        issues.append("Score-tier avg_pnl monotonicity failed")
    if not bool(score_tier_validation.get("wr_monotonic_non_decreasing")):
        issues.append("Score-tier WR monotonicity failed")

    proven_wr = float((by_tier.get("PROVEN") or {}).get("wr_pct") or 0.0)
    sandbox_wr = float((by_tier.get("SANDBOX") or {}).get("wr_pct") or 100.0)
    if proven_wr <= sandbox_wr:
        issues.append(f"Trust-tier separation broken (PROVEN WR {proven_wr} <= SANDBOX WR {sandbox_wr})")

    for ac, row in active.items():
        n = int(row.get("n_active") or 0)
        if n <= 0:
            continue
        sandbox_n = int((row.get("trust_tier_mix") or {}).get("SANDBOX", 0))
        if sandbox_n / n > 0.5:
            issues.append(f"{ac} active SANDBOX concentration > 50% ({sandbox_n}/{n})")

    return (len(issues) == 0), issues


def _build_remediation_tasks(report: dict, issues: list[str]) -> list[dict]:
    tasks: list[dict] = []
    by_ac = report.get("closed_by_asset_class", {})
    diagnostics = report.get("strategy_diagnostics", {})
    pass_watch = report.get("active_pass_watchlist", {})

    for issue in issues:
        tasks.append({"scope": "portfolio", "issue": issue, "priority": "high"})

    for ac, row in by_ac.items():
        pf = row.get("profit_factor")
        if ac != "CRYPTO" and (pf is None or float(pf) < 1.0):
            tasks.append(
                {
                    "scope": f"sleeve:{ac}",
                    "issue": f"PF below 1.0 ({pf})",
                    "action": "de-risk and cap new entries",
                    "priority": "high",
                }
            )

    claude = (diagnostics.get("claude_gainer_audit") or {})
    if claude.get("score_discount_recommended"):
        tasks.append(
            {
                "scope": "strategy:claude_gainer",
                "issue": "fixed TP clustering suggests synthetic inflation",
                "action": "keep score discount and isolate reporting contribution",
                "priority": "high",
            }
        )

    fast = (diagnostics.get("fast_stocks_decision") or {})
    if str(fast.get("state")) in {"retire", "de_risk"}:
        tasks.append(
            {
                "scope": "strategy:fast_stocks_competition",
                "issue": f"state={fast.get('state')}",
                "action": "ban or keep in capped probation until criteria met",
                "priority": "high",
            }
        )

    if float(pass_watch.get("top_asset_class_share_pct") or 0.0) > 80.0:
        tasks.append(
            {
                "scope": "breadth-recovery",
                "issue": "active pass-set concentrated in one asset class",
                "action": "unlock one non-crypto pilot sleeve at capped size",
                "priority": "medium",
            }
        )

    return tasks


def main() -> int:
    ap = argparse.ArgumentParser(description="Run weekly HF verification checks.")
    ap.add_argument("--closed", type=Path, required=True)
    ap.add_argument("--active", type=Path, required=True)
    ap.add_argument("--all-picks", type=Path, required=True, dest="all_picks")
    ap.add_argument(
        "--json-out",
        type=Path,
        default=_REPO / "audit_trail" / "data" / "hf_enhancement_review.json",
    )
    args = ap.parse_args()

    py = sys.executable
    ok_hc, hc_code = _run([py, "tools/run_hc_plan_validation.py", "--skip-plan-read"])
    if not ok_hc:
        print("FAILED: run_hc_plan_validation.py", hc_code)
        return 1

    ok_review, review_code = _run(
        [
            py,
            "tools/hf_enhancement_review.py",
            "--closed",
            str(args.closed),
            "--active",
            str(args.active),
            "--all-picks",
            str(args.all_picks),
            "--json-out",
            str(args.json_out),
        ]
    )
    if not ok_review:
        print("FAILED: hf_enhancement_review.py", review_code)
        return 1

    report = json.loads(args.json_out.read_text(encoding="utf-8"))
    ok_targets, issues = _check_targets(report)
    if not ok_targets:
        print("HF weekly verify FAILED:")
        for i in issues:
            print(" -", i)
        remediation = _build_remediation_tasks(report, issues)
        remediation_path = _REPO / "audit_trail" / "data" / "hf_remediation_tasks.json"
        remediation_path.parent.mkdir(parents=True, exist_ok=True)
        remediation_path.write_text(json.dumps(remediation, indent=2), encoding="utf-8")
        print("Remediation tasks written:", remediation_path)
        return 2

    print("HF weekly verify PASS")
    print("Top system share:", report.get("active_concentration", {}).get("top_system_share_pct"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

