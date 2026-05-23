#!/usr/bin/env python3
"""
PENDING Freshness Checker — scans MASTER_ACTION_PLAN_2026-05-15.md for items
marked PENDING or PLANNED and greps the codebase to determine if they're
already implemented (stale).

Usage:
    python tools/check_pending_freshness.py
    python tools/check_pending_freshness.py --json
    python tools/check_pending_freshness.py --only-stale   # only show auto-detected stale items
    python tools/check_pending_freshness.py --plan-file reports/MASTER_ACTION_PLAN_2026-05-15.md

Context:
    24+ stale PENDING items have been corrected across sessions BE through BT.
    Root cause: items added to MASTER_ACTION_PLAN when discovered, implemented
    in subsequent sessions without updating the plan.
    deepseek recommendation (session BR): add last_verified timestamps + run
    pre-session freshness check.

Exit codes:
    0 — no stale items detected (or no PENDING items found)
    1 — at least one stale PENDING detected (for CI gates)
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PLAN = REPO_ROOT / "reports" / "MASTER_ACTION_PLAN_2026-05-15.md"

# Patterns for lines that indicate a PENDING/PLANNED status
PENDING_PATTERN = re.compile(r"\|\s*M-\d+\s*\|.*?\|\s*(PENDING|PLANNED|STATUS:PENDING|STATUS:PLANNED)", re.IGNORECASE)
PENDING_ITEM_PATTERN = re.compile(r"\|\s*(M-\d+)\s*\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|(.*?)\|", re.IGNORECASE)

# Known auto-detectable proof patterns: M-id → what to grep for
# If grep finds ≥1 match, item is likely already implemented (stale PENDING)
KNOWN_SIGNALS: dict[str, list[str]] = {
    "M-001": ["CRYPTO_UTC_HOUR_FILTER", "utc_hour.*filter", "death.zone"],
    "M-002": ["db-freshness-guardian", "db_freshness", "DB_FRESHNESS"],
    "M-003": ["pcg5_gates", "passes_pcg5_gate", "pcg5_log"],
    "M-004": ["CRYPTO_QUARANTINE", "crypto_quarantine", "source_quarantine"],
    "M-006": ["trust_score", "SMART_PICKS_MIN_TRUST_SCORE"],
    "M-007": ["FOREX_HARD_DISABLE"],
    "M-008": ["multi_asset_cot.*DONE", "ab_analysis"],
    "M-009": ["slippage_validator", "SlippageValidator"],
    "M-010": ["passes_tier_gate", "get_eligible_picks", "swarm_tier_gate"],
    "M-011": [],  # PHP coordination — not detectable
    "M-012": ["dsr_score", "dsr_verdict", "DSRScorer"],
    "M-013": ["ConcentrationChecker", "concentration_checker"],
    "M-014": ["confidence.*normaliz", "clamp.*confidence", "normalize_confidence"],
    "M-016": ["live.*backtest.*drift", "drift_circuit", "_build_drift_circuit"],
    "M-017": ["position_sizer", "PositionSizer", "standalone.*position"],
    "M-019": ["mdd_gate", "MDD_GATE", "max_drawdown.*gate"],
    "M-020": ["bond.*walkforward", "walkforward.*bond", "bond_walkforward"],
    "M-022": ["commodity_carry_momo_double_sort"],
    "M-024": ["ust_tsmom_level"],
    "M-025": ["overnight_intraday_reversal"],
    "M-028": ["TIMEFRAME_15M_GATE", "timeframe_15m", "15m.*quarantine"],
    "M-029": ["sector_rotation.*v2", "sector_rotation_v2"],
    "M-030": ["WINNER_FILTER", "winner_filter"],
    "M-031": ["_build_readiness_payload", "readiness.*by_class"],
    "M-032": ["concentration_checker.*wire", "ConcentrationChecker.*passes"],
    "M-033": ["blocked.*aggregator", "_build_blocked_aggregator"],
    "M-034": ["CRYPTO_CONF_INVERSION_GATE", "conf_inversion"],
    "M-035": ["conf.*ceiling", "confidence.*ceiling", "conf_ceiling"],
    "M-036": [],  # ETF accumulation — data-only, not detectable
    "M-037": ["ml_score.*zero", "ml_score.*0.*unpopulated", "ML_SCORE_ZERO"],
    "M-038": [],  # MEMECOIN — deferred, not detectable
    "M-039": [],  # Cross-commodity spread research — not yet implemented
    "M-040": ["verify_citations", "VerifyCitations", "citation.*guard"],
    "M-041": ["_build_slippage_validation", "slippage_validation"],
    "M-042": ["verification.matrix", "verification_matrix"],
    "M-043": ["anti_overfit_validator", "AntiOverfitValidator"],
    "M-044": ["gate.parity.*test", "parity.*gate.*test"],
    "M-045": ["protocol_state.*wire", "safety_status.*wire"],
    "M-046": ["concept_registry", "concept_family"],
    "M-047": ["hf_decay_watchlist", "_build_hf_decay"],
    "M-048": ["walkforward.*gate", "_build_walkforward"],
    "M-049": ["SAFETY_HALT_GATE_ENABLED", "safety_halt_gate"],
    "M-061": ["money_ready_verdict", "MONEY_READY"],
    "M-067": ["_registry_backed_ac_breakdown", "AUDIT_HEALTH_SOURCE.*registry"],
    "M-068": ["connors_rsi2.*shadow", "bond_connors"],
    "M-071": [],  # active_picks_sync live — requires operator approval
    "M-072": [],  # MySQL contradiction — requires SQL sign-off
    "M-073": ["btc_hour_filter", "BTC_HOUR_FILTER"],
    "M-074": ["dxy_booster", "DXY_BOOSTER"],
    "M-075": ["shadow_tracker", "ShadowTracker", "promotion.*shadow"],
    "M-078": ["FOREX_SESSION_GATE", "forex_session.*gate"],
    "M-079": ["vix_4h_retest"],
    "M-080": ["win_rate.*etf.*bug", "etf.*win_rate.*field"],
    "M-081": ["symbol.*class.*consistency", "class_consistency.*check"],
    "M-082": ["WINNER_FILTER.*per.strategy", "conf_max.*override"],
    "M-083": ["elite_score.*pre.enrichment", "adjustment.from.zero"],
    "M-106": ["nb_trials.*per.symbol", "money_ready_verdict.*nb_trials"],
}


def grep_repo(pattern: str) -> bool:
    """Return True if pattern appears anywhere in .py or .yml repo files."""
    try:
        result = subprocess.run(
            ["grep", "-rl", "--include=*.py", "--include=*.yml", pattern, str(REPO_ROOT)],
            capture_output=True, text=True, timeout=15,
        )
        return bool(result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def check_item(m_id: str) -> Optional[str]:
    """
    Return the signal that was found (string), or None if nothing detected.
    Returns 'UNREGISTERED' if m_id has no signals registered.
    """
    signals = KNOWN_SIGNALS.get(m_id)
    if signals is None:
        return "UNREGISTERED"
    if not signals:
        return None  # blocked/accumulation/operator-gated — can't auto-detect
    for sig in signals:
        if grep_repo(sig):
            return sig
    return None


def parse_pending_items(plan_path: Path) -> list[dict]:
    """Extract all M-### items with PENDING/PLANNED status from the plan."""
    text = plan_path.read_text(encoding="utf-8", errors="replace")
    items = []
    for line in text.splitlines():
        m = PENDING_ITEM_PATTERN.search(line)
        if not m:
            continue
        status_col = m.group(7).strip()
        if not re.search(r"\b(PENDING|PLANNED)\b", status_col, re.IGNORECASE):
            continue
        # Skip lines that also have DONE in them (e.g. "PENDING → DONE")
        if re.search(r"\bDONE\b", status_col, re.IGNORECASE):
            continue
        m_id = m.group(1).strip()
        description = m.group(2).strip()
        items.append({
            "id": m_id,
            "description": description[:100],
            "status_col": status_col[:80],
        })
    return items


def run(plan_path: Path, only_stale: bool = False, output_json: bool = False) -> list[dict]:
    if not plan_path.exists():
        print(f"ERROR: Plan file not found: {plan_path}", file=sys.stderr)
        sys.exit(2)

    pending = parse_pending_items(plan_path)
    results = []

    for item in pending:
        m_id = item["id"]
        signal = check_item(m_id)
        is_stale = signal is not None and signal != "UNREGISTERED"
        is_unregistered = signal == "UNREGISTERED"

        result = {
            "id": m_id,
            "description": item["description"],
            "status_col": item["status_col"],
            "stale": is_stale,
            "signal_found": signal if is_stale else None,
            "unregistered": is_unregistered,
            "verdict": "STALE_PENDING" if is_stale else ("UNREGISTERED" if is_unregistered else "PENDING_CLEAN"),
        }
        results.append(result)

    stale = [r for r in results if r["stale"]]
    clean = [r for r in results if not r["stale"] and not r["unregistered"]]
    unreg = [r for r in results if r["unregistered"]]

    if output_json:
        print(json.dumps(results, indent=2))
        return results

    print(f"\n=== PENDING Freshness Check — {plan_path.name} ===")
    print(f"PENDING items found: {len(results)}")
    print(f"  STALE (likely already implemented): {len(stale)}")
    print(f"  CLEAN (not yet detected in codebase): {len(clean)}")
    print(f"  UNREGISTERED (no grep signals defined): {len(unreg)}")
    print()

    if stale:
        print("--- STALE PENDING ITEMS (update MASTER_ACTION_PLAN to DONE) ---")
        for r in stale:
            print(f"  {r['id']:<8}  signal='{r['signal_found']}'")
            print(f"           {r['description'][:90]}")
        print()

    if not only_stale:
        if clean:
            print("--- CLEAN PENDING (genuinely not yet implemented) ---")
            for r in clean:
                print(f"  {r['id']:<8}  {r['description'][:90]}")
            print()
        if unreg:
            print("--- UNREGISTERED (add grep signals to KNOWN_SIGNALS dict) ---")
            for r in unreg:
                print(f"  {r['id']:<8}  {r['description'][:90]}")
            print()

    if stale:
        print(f"ACTION REQUIRED: {len(stale)} stale PENDING items detected.")
        print("Update MASTER_ACTION_PLAN to DONE before starting new session work.")
    else:
        print("✅ No stale PENDING items detected.")

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Check PENDING freshness in MASTER_ACTION_PLAN")
    parser.add_argument("--plan-file", default=str(DEFAULT_PLAN), help="Path to MASTER_ACTION_PLAN")
    parser.add_argument("--json", action="store_true", dest="output_json", help="Output JSON")
    parser.add_argument("--only-stale", action="store_true", help="Only show stale items")
    parser.add_argument("--check", action="store_true", help="Exit 1 if stale items found (CI mode)")
    args = parser.parse_args()

    results = run(Path(args.plan_file), only_stale=args.only_stale, output_json=args.output_json)
    stale_count = sum(1 for r in results if r.get("stale"))

    if args.check and stale_count > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
