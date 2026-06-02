"""
Promotion gates for verified-strategy production sidecars.

Reads forward-stats JSON (etf / crypto_wf / faber) and walk-forward report.
Default: lab PASS alone does not enable live merge — forward virtual n>=100 required for ETF.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

_ROOT = Path(__file__).resolve().parent.parent
_ETF_STATS = _ROOT / "reports" / "etf_forward_stats_latest.json"
_PILOT_DASH = _ROOT / "reports" / "pilot_forward_dashboard.json"
_WF_REPORT = _ROOT / "verified_strategies" / "WALKFORWARD_REPORT.json"
_H102_GLOB = "h102_connors_rsi2_crypto_*.md"


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, OSError):
        return None


def etf_forward_report() -> Dict[str, Any]:
    return _load_json(_ETF_STATS) or {}


def etf_scanner_merge_allowed() -> bool:
    """Merge ETF verified picks into active only when forward stats recommend it."""
    if os.environ.get("ETF_VERIFIED_FORCE_MERGE", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    ):
        return True
    report = etf_forward_report()
    if report.get("recommend_scanner_enable") is True:
        return True
    pilot = report.get("paper_pilot_forward") or {}
    return pilot.get("promotion_ready") is True


def etf_scanner_shadow_active() -> bool:
    """Env flag set but promotion not ready — shadow log only."""
    flag = os.environ.get("ETF_VERIFIED_DUAL_MOMENTUM_ENABLED", "0").strip().lower()
    if flag in ("shadow",):
        return True
    if flag in ("1", "true", "yes", "on"):
        return not etf_scanner_merge_allowed()
    return False


def equity_wf_pass() -> bool:
    try:
        from verified_strategies.walkforward_gate import sleeve_verdict

        return sleeve_verdict("equity_momentum_12_1") == "PASS"
    except ImportError:
        return False


def equity_merge_allowed() -> bool:
    if os.environ.get("EQUITY_VERIFIED_FORCE_MERGE", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    ):
        return True
    mode = os.environ.get("EQUITY_VERIFIED_MOMENTUM_12_1_ENABLED", "0").strip().lower()
    if mode == "live":
        return True
    return equity_wf_pass()


def connors_harness_admissible() -> bool:
    if os.environ.get("CONNORS_RSI2_HARNESS_ADMISSIBLE", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    ):
        return True
    reports = sorted((_ROOT / "reports").glob(_H102_GLOB), reverse=True)
    if not reports:
        return False
    try:
        text = reports[0].read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    if "harness admissible=True" in text.replace(" ", ""):
        return True
    if "**ADMISSIBLE**" in text and "UNTESTED" not in text.split("## Verdict", 1)[-1][:200]:
        return True
    return False


def build_edge_status() -> Dict[str, Any]:
    """Dashboard + deploy payload for verified pilot strip."""
    etf = etf_forward_report()
    dash = _load_json(_PILOT_DASH) or {}
    wf = _load_json(_WF_REPORT) or {}

    def _wf_verdict(key: str) -> Optional[str]:
        block = wf.get(key)
        if isinstance(block, dict):
            return block.get("verdict")
        return None

    pilot = etf.get("paper_pilot_forward") or {}
    return {
        "timestamp": etf.get("timestamp") or dash.get("timestamp"),
        "trust_hierarchy": [
            "policy_clean money_ready_verdict (live sizing)",
            "verified_strategies lab + walk-forward (promotion candidate)",
            "paper_pilot virtual forward (n>=100 gate)",
            "ai-tournament / pf.html (separate universe — not money-ready)",
        ],
        "live_money_ready": "0/6 classes Tier-2 — see money_ready_verdict.json",
        "lab_tier2_sleeve": "ETF dual momentum (MULTI_CLASS_LAB PASS)",
        "sleeves": {
            "etf_verified_dual_momentum": {
                "lab_wf": _wf_verdict("etf_dual_momentum"),
                "forward_n": pilot.get("n_closed", 0),
                "promotion_ready": pilot.get("promotion_ready", False),
                "recommend_merge": etf_scanner_merge_allowed(),
                "env_flag": "ETF_VERIFIED_DUAL_MOMENTUM_ENABLED",
                "scanner_mode": (
                    "live_merge"
                    if etf_scanner_merge_allowed()
                    else "shadow_or_off"
                ),
            },
            "crypto_verified_donchian": {
                "lab_wf": _wf_verdict("crypto_donchian"),
                "production_blocked": _wf_verdict("crypto_donchian") != "PASS",
                "env_flag": "CRYPTO_VERIFIED_DONCHIAN_ENABLED",
            },
            "equity_verified_momentum_12_1": {
                "lab_wf": _wf_verdict("equity_momentum_12_1"),
                "scanner_mode": "live_merge" if equity_merge_allowed() else "shadow",
                "env_flag": "EQUITY_VERIFIED_MOMENTUM_12_1_ENABLED",
            },
            "connors_rsi2_crypto": {
                "harness_admissible": connors_harness_admissible(),
                "scanner_mode": "shadow_only",
                "env_flag": "CONNORS_RSI2_CRYPTO_ENABLED",
            },
        },
        "disputed_surfaces": [
            "CRYPTO Smart Picks / Verified Alpha / HC / ELITE (claude_gainer_st concentration)",
        ],
        "report": "reports/quant_strategy_root_cause_review_2026-06-02.md",
    }