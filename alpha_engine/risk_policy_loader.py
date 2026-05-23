"""
Load unified risk policy JSON (HF P1).

Safe defaults if file missing or invalid. See config/risk_policy.json.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_PATH = _REPO_ROOT / "config" / "risk_policy.json"

_FALLBACK: dict[str, Any] = {
    "version": 2,
    "crypto": {
        # 2026-05-09 v2: tightened per swarm 4/4 + cycle-4 TON disaster.
        # Was 10 / 5 — too permissive; allowed 7 open shorts on TON's 40% pump.
        "max_equity_pct_per_symbol": 5,
        "max_equity_pct_per_direction": 20,
        "max_portfolios_same_symbol_direction": 2,
        "per_trade_cap_pct": 3,
    },
    "asset_class_budget_pct": {
        "CRYPTO": 0.70,
        "EQUITY": 0.20,
        "FOREX": 0.05,
        "COMMODITY": 0.03,
        "ETF": 0.02,
    },
    "non_crypto_absolute_caps": {
        "EQUITY": 2,
        "FOREX": 2,
        "COMMODITY": 1,
        "ETF": 1,
        "FUTURES": 1,
    },
    "trust_tier_policy": {
        "conviction_blacklist": ["SANDBOX", "PROBATION", "UNPROVEN", "DEMOTED"],
        "conviction_min_score": 50,
        "testing_allowlist": ["WATCH", "DEVELOPING", "PROVEN"],
    },
    "equity": {
        "max_single_system_picks": 2,
        "max_single_system_share_pct": 0.60,
    },
    "forex": {
        "max_active_picks": 2,
    },
    "non_crypto": {
        "max_total_picks": 3,
        "min_trades_overrides": {},
        "goldmine_min_score": 25,
        "goldmine_min_conf": 0.60,
        "goldmine_min_trades_to_relax": 30,
        "last_policy_change_at": None,
    },
    "policy_flags": {
        "enable_non_crypto_throughput_v2": False,
        "enable_direction_aware_conviction_v2": False,
        "enable_asset_class_ml_composite_v2": False,
        "enable_goldmine_floor_v2": False,
        "disable_non_crypto_ml_null_penalty_v2": False,
        "enable_concentration_probation_v2": False,
    },
    "concentration_controls": {
        "mode": "tag",
        "max_symbol_strategy_exposure": 2,
        "max_strategy_system_exposure": 3,
    },
    "sports": {"max_stake_pct_bankroll": 5},
}


def load_risk_policy(path: Path | None = None) -> dict[str, Any]:
    """Return merged policy dict; never raises."""
    p = path or _DEFAULT_PATH
    out = json.loads(json.dumps(_FALLBACK))
    if not p.is_file():
        return out
    try:
        raw = json.loads(p.read_text(encoding="utf-8", errors="replace"))
        if isinstance(raw, dict):
            out.update(raw)
            if isinstance(raw.get("crypto"), dict):
                out["crypto"] = {**_FALLBACK["crypto"], **raw["crypto"]}
            if isinstance(raw.get("sports"), dict):
                out["sports"] = {**_FALLBACK["sports"], **raw["sports"]}
            if isinstance(raw.get("asset_class_budget_pct"), dict):
                out["asset_class_budget_pct"] = {
                    **_FALLBACK["asset_class_budget_pct"],
                    **raw["asset_class_budget_pct"],
                }
            if isinstance(raw.get("non_crypto_absolute_caps"), dict):
                out["non_crypto_absolute_caps"] = {
                    **_FALLBACK["non_crypto_absolute_caps"],
                    **raw["non_crypto_absolute_caps"],
                }
            if isinstance(raw.get("trust_tier_policy"), dict):
                out["trust_tier_policy"] = {
                    **_FALLBACK["trust_tier_policy"],
                    **raw["trust_tier_policy"],
                }
            if isinstance(raw.get("equity"), dict):
                out["equity"] = {**_FALLBACK["equity"], **raw["equity"]}
            if isinstance(raw.get("forex"), dict):
                out["forex"] = {**_FALLBACK["forex"], **raw["forex"]}
            if isinstance(raw.get("non_crypto"), dict):
                out["non_crypto"] = {**_FALLBACK["non_crypto"], **raw["non_crypto"]}
            if isinstance(raw.get("policy_flags"), dict):
                out["policy_flags"] = {**_FALLBACK["policy_flags"], **raw["policy_flags"]}
            if isinstance(raw.get("concentration_controls"), dict):
                out["concentration_controls"] = {
                    **_FALLBACK["concentration_controls"],
                    **raw["concentration_controls"],
                }
    except (json.JSONDecodeError, OSError, TypeError):
        pass
    return out
