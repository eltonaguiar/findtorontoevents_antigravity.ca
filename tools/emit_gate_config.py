#!/usr/bin/env python3
"""
Gate Config Emitter — generates audit_dashboard/data/gate_config.json.

Reads env vars (same defaults as quality_gates.py) and writes a structured
gate config snapshot. Run by .github/workflows/gate-config-emit.yml after
every quality_gates.py change and on schedule.

Usage:
    python tools/emit_gate_config.py
    python tools/emit_gate_config.py --out audit_dashboard/data/gate_config.json

Output format:
    {
        "generated_at": "<ISO UTC>",
        "gates": [
            {
                "id": "FOREX_HARD_DISABLE",
                "label": "FOREX Hard Disable",
                "description": "Blocks all FOREX picks",
                "env_var": "FOREX_HARD_DISABLE",
                "default": "1",
                "current": "1",
                "active": true,
                "asset_class": "FOREX",
                "category": "class_disable",
                "severity": "P0"
            },
            ...
        ]
    }
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = REPO_ROOT / "audit_dashboard" / "data" / "gate_config.json"

# Curated list of gates operators care about, with metadata.
# 'default': value quality_gates.py uses when env var is absent.
# 'active_when': "1" means active when env var == "1"; "0" means active when env var == "0".
GATE_REGISTRY: list[dict] = [
    # P0 — Class disables
    {
        "id": "FOREX_HARD_DISABLE",
        "label": "FOREX Hard Disable",
        "description": "Blocks all FOREX picks from pipeline. Enabled while carry-factor research is in progress.",
        "env_var": "FOREX_HARD_DISABLE",
        "default": "1",
        "active_when": "1",
        "asset_class": "FOREX",
        "category": "class_disable",
        "severity": "P0",
    },
    {
        "id": "CRYPTO_UTC_HOUR_FILTER",
        "label": "CRYPTO UTC-Hour Death-Zone Filter",
        "description": "Rejects CRYPTO picks during 06:00-11:00 UTC (0% WR window). Boosts 22:00 UTC.",
        "env_var": "CRYPTO_HOUR_FILTER_DISABLED",
        "default": "0",
        "active_when": "0",
        "asset_class": "CRYPTO",
        "category": "timing_gate",
        "severity": "P0",
    },
    {
        "id": "FOREX_SESSION_GATE",
        "label": "FOREX Session Gate (08-16 UTC)",
        "description": "Blocks FOREX picks outside 08:00-16:00 UTC trading session.",
        "env_var": "FOREX_SESSION_GATE_DISABLED",
        "default": "0",
        "active_when": "0",
        "asset_class": "FOREX",
        "category": "timing_gate",
        "severity": "P0",
    },
    # P1 — Risk gates
    {
        "id": "SAFETY_HALT_GATE_ENABLED",
        "label": "Safety Halt Gate",
        "description": "Rejects ALL picks when safety_status verdict == STOP (Binance CB, severe drift).",
        "env_var": "SAFETY_HALT_GATE_ENABLED",
        "default": "1",
        "active_when": "1",
        "asset_class": "ALL",
        "category": "risk_gate",
        "severity": "P0",
    },
    {
        "id": "ANTI_OVERFIT_VALIDATOR",
        "label": "Anti-Overfit Validator",
        "description": "Runs DSR/PBO anti-overfit checks on each pick's strategy.",
        "env_var": "ANTI_OVERFIT_VALIDATOR_ENABLED",
        "default": "1",
        "active_when": "1",
        "asset_class": "ALL",
        "category": "anti_overfit",
        "severity": "P0",
    },
    {
        "id": "SWARM_TIER_GATE",
        "label": "Swarm Tier Gate (M-010)",
        "description": "Enforces min consensus tier for swarm-originated picks (default: strong=3+/66%+).",
        "env_var": "SWARM_TIER_GATE_ENABLED",
        "default": "1",
        "active_when": "1",
        "asset_class": "SWARM",
        "category": "tier_gate",
        "severity": "P1",
    },
    {
        "id": "WF_VERDICT_FAILING_BLOCK",
        "label": "Walk-Forward Failing Block",
        "description": "Blocks strategies with FAILING walk-forward verdict from producing new picks.",
        "env_var": "WF_VERDICT_FAILING_BLOCK_ENABLED",
        "default": "1",
        "active_when": "1",
        "asset_class": "ALL",
        "category": "walkforward_gate",
        "severity": "P1",
    },
    {
        "id": "DECAY_SOFT_DEMOTE",
        "label": "Decay Soft Demotion",
        "description": "Auto-demotes strategies showing sustained WR decay in recent picks.",
        "env_var": "DECAY_SOFT_DEMOTE_ENABLED",
        "default": "1",
        "active_when": "1",
        "asset_class": "ALL",
        "category": "decay_gate",
        "severity": "P1",
    },
    {
        "id": "HF_QUALITY_GATE",
        "label": "HF Quality Gate",
        "description": "Applies hedge-fund grade quality thresholds (PF/WR/n floors) before publish.",
        "env_var": "HF_QUALITY_GATE_ENABLED",
        "default": "1",
        "active_when": "1",
        "asset_class": "ALL",
        "category": "quality_gate",
        "severity": "P1",
    },
    {
        "id": "BOND_MIN_N_GATE",
        "label": "BOND Minimum N Gate",
        "description": "Blocks BOND picks until class reaches minimum resolved_n threshold (n≥30).",
        "env_var": "BOND_MIN_N_GATE",
        "default": "1",
        "active_when": "1",
        "asset_class": "BOND",
        "category": "accumulation_gate",
        "severity": "P1",
    },
    {
        "id": "ETF_TIGHT_GATE",
        "label": "ETF Tight Quality Gate",
        "description": "Applies tighter PF/WR thresholds for ETF class until n≥150 OOS-ready.",
        "env_var": "ETF_TIGHT_GATE",
        "default": "1",
        "active_when": "1",
        "asset_class": "ETF",
        "category": "quality_gate",
        "severity": "P1",
    },
    {
        "id": "VIX_YC_SCORE_BONUS",
        "label": "VIX + Yield Curve Score Bonus (EQUITY)",
        "description": "Adds +15 score bonus for EQUITY picks when VIX<22 and YC spread>0 (risk-on).",
        "env_var": "VIX_YC_SCORE_BONUS_ENABLED",
        "default": "1",
        "active_when": "1",
        "asset_class": "EQUITY",
        "category": "score_bonus",
        "severity": "P1",
    },
    # Shadow/opt-in gates (normally OFF)
    {
        "id": "TIMEFRAME_15M_GATE",
        "label": "15-Minute Timeframe Quarantine (M-028)",
        "description": "Rejects picks on 15m timeframes. Default shadow (stamp-only); set=1 to enforce.",
        "env_var": "TIMEFRAME_15M_GATE",
        "default": "0",
        "active_when": "1",
        "asset_class": "ALL",
        "category": "shadow_gate",
        "severity": "P2",
    },
    {
        "id": "CRYPTO_CONF_INVERSION_GATE",
        "label": "CRYPTO Confidence Inversion Gate (M-034)",
        "description": "Blocks high-confidence picks from anti-correlated CRYPTO sources. Shadow by default.",
        "env_var": "CRYPTO_CONF_INVERSION_GATE",
        "default": "0",
        "active_when": "1",
        "asset_class": "CRYPTO",
        "category": "shadow_gate",
        "severity": "P2",
    },
    {
        "id": "BT_WR_DRIFT_GATE",
        "label": "BT/FWD WR Drift Gate",
        "description": "Blocks strategies where BT WR diverges >2σ from forward WR. Shadow by default.",
        "env_var": "BT_WR_DRIFT_GATE_ENABLED",
        "default": "0",
        "active_when": "1",
        "asset_class": "ALL",
        "category": "shadow_gate",
        "severity": "P2",
    },
    {
        "id": "OVERCONFIDENCE_DECAY",
        "label": "Overconfidence Decay (Score Booster)",
        "description": "Decays extreme scores (|score|>threshold) by 20% to prevent overconfidence blowups.",
        "env_var": "OVERCONFIDENCE_DECAY",
        "default": "1",
        "active_when": "1",
        "asset_class": "ALL",
        "category": "score_modifier",
        "severity": "P1",
    },
    {
        "id": "AUDIT_DOW_GATE",
        "label": "Day-of-Week Gate (SUPREME EDGE)",
        "description": "Restricts picks to statistically optimal days of week. Default OFF (shadow).",
        "env_var": "AUDIT_DOW_GATE",
        "default": "0",
        "active_when": "1",
        "asset_class": "ALL",
        "category": "shadow_gate",
        "severity": "P3",
    },
    {
        "id": "SLIPPAGE_PROMOTION_GATE",
        "label": "Net-of-Cost Slippage / Expectancy Promotion Gate (P1/#7)",
        "description": "Blocks MONEY_READY promotion when post-slippage expectancy is negative. ENFORCED by default (2026-05-19, swarm-settled Q1 verdict — the real money-ready promotion gate); set SLIPPAGE_PROMOTION_GATE_ENABLED=0 to disable.",
        "env_var": "SLIPPAGE_PROMOTION_GATE_ENABLED",
        "default": "1",
        "active_when": "1",
        "asset_class": "ALL",
        "category": "hard_gate",
        "severity": "P1",
    },
]


def get_gate_status(gate: dict) -> dict:
    """Compute active status for a gate from current env."""
    env_var = gate["env_var"]
    default = gate["default"]
    active_when = gate["active_when"]

    current = os.environ.get(env_var, default)
    # Normalize: treat "true"/"TRUE"/"True" as "1", "false"/"FALSE" as "0"
    current_norm = current.strip().lower()
    if current_norm in ("true", "yes", "on"):
        current_norm = "1"
    elif current_norm in ("false", "no", "off"):
        current_norm = "0"
    else:
        current_norm = current.strip()

    is_active = (current_norm == active_when)

    return {
        **gate,
        "current": current,
        "active": is_active,
        "status": "ACTIVE" if is_active else ("SHADOW" if gate.get("category") == "shadow_gate" else "DISABLED"),
    }


def emit(out_path: Path) -> dict:
    generated_at = datetime.now(timezone.utc).isoformat()
    gates = [get_gate_status(g) for g in GATE_REGISTRY]

    payload = {
        "generated_at": generated_at,
        "gate_count": len(gates),
        "active_count": sum(1 for g in gates if g["active"]),
        "shadow_count": sum(1 for g in gates if g.get("status") == "SHADOW"),
        "disabled_count": sum(1 for g in gates if not g["active"] and g.get("status") != "SHADOW"),
        "gates": gates,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Emit gate_config.json for audit dashboard")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output path")
    args = parser.parse_args()

    out_path = Path(args.out)
    payload = emit(out_path)
    print(f"gate_config.json written: {out_path}")
    print(f"  gates: {payload['gate_count']}  active: {payload['active_count']}  shadow: {payload['shadow_count']}  disabled: {payload['disabled_count']}")
    print(f"  generated_at: {payload['generated_at']}")


if __name__ == "__main__":
    main()
