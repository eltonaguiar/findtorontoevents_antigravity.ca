"""
AI Tournament — Persona ID Backfill.

Reads picks files from data/ai_tournament/picks_*.json and assigns
persona IDs and strategy names from the model-persona mapping config.
Operates in-place or writes new files.

Usage:
    python tools/backfill_persona_picks.py --in-place --file data/ai_tournament/picks_20260521.json
    python tools/backfill_persona_picks.py --all  # backfill all files in dir
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "model_persona_mapping.json"
PICKS_DIR = REPO_ROOT / "data" / "ai_tournament"

# Strategy descriptions by persona ID (from populate_picks.py)
PERSONA_STRATEGIES: dict[str, str] = {
    "momentum_scalp": "Momentum scalping on 15min-1h timeframe",
    "trend_follower": "Trend following with 20/50 EMA cross",
    "mean_reversion": "Mean reversion with RSI < 30 / > 70",
    "value_investor": "Value with P/E < sector avg + healthy balance sheet",
    "sector_rotation": "Sector rotation based on relative strength",
    "carry_trade": "Carry trade focusing on interest rate differentials",
    "grid_trader": "Grid trading in range-bound markets",
    "growth_at_reasonable_price": "GARP — PEG < 1.5, revenue growth > 15%",
    "seasonal_pattern": "Seasonal commodity patterns (planting/harvest/storage)",
    "breakout_scanner": "Breakout from 20-day consolidation with volume",
    "momentum_momentum": "3-6 month price momentum with volume confirmation",
    "macro_hedge": "Macro-driven hedges against inflation/growth",
    "volatility_breakout": "Volatility breakout with ATR-based stops",
    "quality_compound": "Quality compounding: ROE > 15%, debt/equity < 0.5",
    "supply_demand": "Supply/demand imbalance at key price levels",
    "central_bank_policy": "Central bank policy divergence trades",
    "narrative_trader": "Narrative-driven plays (AI, energy transition, etc.)",
    "moat_investor": "Wide moat companies with pricing power",
    "global_macro": "Global macro based on GDP/inflation differentials",
    "factor_rotation": "Factor rotation (value, momentum, quality, low vol)",
    "purchasing_power_parity": "PPP-based mean reversion for currency pairs",
    "duration_call": "Duration call based on yield curve expectations",
    "liquidity_grazer": "Liquidity grab on high-timeframe levels",
    "statistical_arb": "Statistical arbitrage on correlated pairs",
    "weather_hedge": "Weather-driven commodity hedges",
    "order_flow": "Order flow imbalance at support/resistance",
    "volatility_tilt": "Volatility risk premium harvesting",
    "flight_to_safety": "Safe haven flows during risk-off events",
    "bayesian_breakout": "Bayesian probability of breakout continuation",
    "cross_sectional_momentum": "Cross-sectional momentum across sectors",
    "inventory_cycle": "Inventory cycle positioning (EIA reports)",
    "onchain_analytics": "On-chain metrics (exchange flows, whale activity)",
    "earnings_momentum": "Earnings surprise + guidance revision momentum",
    "geopolitical_risk": "Geopolitical risk premium trades",
    "quality_growth": "Quality growth at reasonable valuation",
    "technical_swing": "Technical swing on 4h-1d timeframe",
    "alpha_consensus": "Alpha engine consensus pick",
    "fallback": "Fallback synthetic pick (no API key available)",
}


def load_config() -> dict[str, Any] | None:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return None


def get_persona_for_model(model_id: str, asset_class: str) -> str:
    """Look up the persona ID for a model + asset class combination."""
    config = load_config()
    if config:
        model_cfg = config.get("models", {}).get(model_id)
        if model_cfg:
            assignments = model_cfg.get("assignments", {})
            personas = assignments.get(asset_class, [])
            if personas:
                return personas[0]
    return ""


def get_strategy_name(persona_id: str) -> str:
    return PERSONA_STRATEGIES.get(persona_id, persona_id)


def backfill_file(file_path: Path, in_place: bool = False) -> int:
    """Backfill persona IDs and strategy names for all picks in a file.
    Returns number of picks updated.
    """
    if not file_path.exists():
        print(f"[backfill] File not found: {file_path}")
        return 0

    data = json.loads(file_path.read_text())
    if not isinstance(data, list):
        print(f"[backfill] {file_path}: not a list ({type(data).__name__})")
        return 0

    updated = 0
    for pick in data:
        model_id = pick.get("model_id", "")
        asset_class = pick.get("asset_class", "EQUITY")

        needs_update = False
        if not pick.get("persona_id"):
            persona_id = get_persona_for_model(model_id, asset_class)
            if persona_id:
                pick["persona_id"] = persona_id
                needs_update = True

        if not pick.get("strategy_name"):
            persona_id = pick.get("persona_id", "")
            if persona_id:
                pick["strategy_name"] = get_strategy_name(persona_id)
                needs_update = True

        if needs_update:
            updated += 1

    if in_place and updated > 0:
        file_path.write_text(json.dumps(data, indent=2))
        print(f"[backfill] {file_path.name}: updated {updated}/{len(data)} picks (in-place)")
    else:
        print(f"[backfill] {file_path.name}: {updated}/{len(data)} would be updated")

    return updated


def main() -> None:
    in_place = "--in-place" in sys.argv
    all_files = "--all" in sys.argv
    specific_file = None

    # Check for --file argument
    if "--file" in sys.argv:
        idx = sys.argv.index("--file")
        if idx + 1 < len(sys.argv):
            specific_file = Path(sys.argv[idx + 1])

    if specific_file:
        backfill_file(specific_file, in_place)

    elif all_files:
        if not PICKS_DIR.exists():
            print(f"[backfill] No picks directory at {PICKS_DIR}")
            return
        files = sorted(PICKS_DIR.glob("picks_*.json"))
        if not files:
            print("[backfill] No picks files found")
            return
        total = 0
        for f in files:
            total += backfill_file(f, in_place)
        print(f"[backfill] Total: {total} picks updated across {len(files)} files")

    else:
        # Default: process latest file
        files = sorted(PICKS_DIR.glob("picks_*.json"), reverse=True)
        if files:
            backfill_file(files[0], in_place)
        else:
            print("[backfill] No picks files found")
            # Also try latest snapshot
            latest = REPO_ROOT / "audit_dashboard" / "data" / "ai_tournament_picks_latest.json"
            if latest.exists():
                print(f"[backfill] Processing latest snapshot: {latest}")
                backfill_file(latest, in_place)


if __name__ == "__main__":
    main()
