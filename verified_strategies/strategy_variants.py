#!/usr/bin/env python3
"""
EAGLE synthesis — canonical strategy variation registry (2026-05-19 → 2026-06-02).

Maps lab sleeves to safe parameter mutation grids recommended across EAGLE*.MD*
reviews (blackboxai, deepseek_v4, minimax EAGLE3/4/5, Composer, Codex).

Used by mutation_framework (PARAMETER axis) and variant_sweep_runner.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class VariantSpec:
    sleeve: str
    asset_class: str
    param_grid: Dict[str, List] = field(default_factory=dict)
    notes: str = ""
    eagle_source: str = ""


# Tournament + lab consensus (EAGLE3 edge matrix, EAGLE2 verified pilots)
EAGLE_STRATEGY_VARIANTS: Dict[str, VariantSpec] = {
    "etf_dual_momentum": VariantSpec(
        sleeve="etf_dual_momentum",
        asset_class="ETF",
        param_grid={"lookback_months": [9, 12, 14], "top_n": [2, 3, 5]},
        notes="Only Tier-2 lab PASS (PF~1.6 n=104); forward n still <100",
        eagle_source="EAGLE2 deepseek_v4_flash, Composer",
    ),
    "faber_taa": VariantSpec(
        sleeve="faber_taa",
        asset_class="ETF",
        param_grid={"sma_period": [180, 200, 220], "risk_off_weight": [0.0, 0.25]},
        notes="Faber rotation; needs cost-adjusted WF re-run",
        eagle_source="EAGLE2 blackboxai §5.2",
    ),
    "crypto_donchian": VariantSpec(
        sleeve="crypto_donchian",
        asset_class="CRYPTO",
        param_grid={"channel_days": [18, 20, 25], "atr_mult_sl": [1.5, 2.0, 2.5]},
        notes="Verified donchian; production opt-in sidecar",
        eagle_source="updates/2026-06-02-verified-strategies-real-ohlcv",
    ),
    "connors_rsi2": VariantSpec(
        sleeve="connors_rsi2",
        asset_class="CRYPTO",
        param_grid={"rsi_entry": [2, 5, 7], "hold_days": [1, 2, 3]},
        notes="H-102 lab PF~1.3; mutate RSI threshold before invert",
        eagle_source="reports/h102_connors_rsi2_crypto_2026-06-02",
    ),
    "equity_momentum_12_1": VariantSpec(
        sleeve="equity_momentum_12_1",
        asset_class="EQUITY",
        param_grid={"skip_months": [1], "top_n": [5, 10, 20]},
        notes="Academic 12-1; equity production still weak — regime gate first",
        eagle_source="EAGLE per_class_top_strategy 2026-05-27",
    ),
    "vwap_reversion": VariantSpec(
        sleeve="vwap_reversion",
        asset_class="CRYPTO",
        param_grid={"z_entry": [1.5, 2.0, 2.5], "max_hold_bars": [12, 24, 48]},
        notes="WF PASS lab; 0 forward closes — pilot only",
        eagle_source="EAGLE2 GPT5_3_CODEX",
    ),
    "bollinger_mr": VariantSpec(
        sleeve="bollinger_mr",
        asset_class="CRYPTO",
        param_grid={"bb_period": [18, 20, 22], "bb_std": [1.5, 2.0, 2.5]},
        notes="WF PASS lab OOS PF~1.67; not merged to production",
        eagle_source="EAGLE2 deepseek_v4_flash",
    ),
    "cross_asset_mom_vix": VariantSpec(
        sleeve="cross_asset_mom_vix",
        asset_class="ETF",
        param_grid={"vix_threshold": [20, 25, 30]},
        notes="REJECTED 2026-06-02 — keep for mutation refutation only",
        eagle_source="updates/2026-06-02-cross-asset-momentum-vt-rejected",
    ),
}


def list_variants() -> List[str]:
    return sorted(EAGLE_STRATEGY_VARIANTS.keys())


def get_variant(sleeve: str) -> VariantSpec | None:
    key = sleeve.lower().replace("-", "_")
    return EAGLE_STRATEGY_VARIANTS.get(key) or EAGLE_STRATEGY_VARIANTS.get(
        next((k for k in EAGLE_STRATEGY_VARIANTS if key in k), "")
    )
