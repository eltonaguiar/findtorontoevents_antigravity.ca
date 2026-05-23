"""
Strategy Guard - Prevents disabled strategies from generating picks
Reads from stabilization/disabled_strategies.json
"""

import json
from pathlib import Path
from functools import wraps
from datetime import datetime

DISABLED_FILE = Path("stabilization/disabled_strategies.json")


def get_disabled_strategies():
    """Load list of disabled strategy names"""
    if not DISABLED_FILE.exists():
        return set()
    
    try:
        with open(DISABLED_FILE, 'r') as f:
            data = json.load(f)
        return set(data.get("disabled", []))
    except Exception:
        return set()


def is_strategy_disabled(strategy_name):
    """Check if a strategy is disabled"""
    disabled = get_disabled_strategies()
    return strategy_name in disabled


def filter_strategies(strategy_dict):
    """Filter out disabled strategies from a dictionary"""
    disabled = get_disabled_strategies()
    filtered = {k: v for k, v in strategy_dict.items() if k not in disabled}
    removed = [k for k in strategy_dict if k in disabled]
    return filtered, removed


def log_filtered_strategies(removed):
    """Log which strategies were filtered out"""
    if removed:
        print(f"[GUARD] Filtered {len(removed)} disabled strategies: {', '.join(removed)}")


class StrategyGuard:
    """Context manager for strategy filtering"""
    
    def __init__(self, strategies_dict):
        self.original = strategies_dict.copy()
        self.filtered, self.removed = filter_strategies(strategies_dict)
    
    def __enter__(self):
        if self.removed:
            print(f"[STRATEGY GUARD] {len(self.removed)} strategies disabled: {self.removed}")
        return self.filtered
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass  # No cleanup needed


# ☠️ GRAVEYARD -- 27 strategies with negative expected value
# These are permanently disabled based on forward testing (2026-03-01)
# They remain in code for reference but will NEVER generate picks
# See STRATEGY_GRAVEYARD.md for full death certificates
GRAVEYARD = {
    # Catastrophic loss (>$500 each)
    "double_top_bottom_detector",     # -$1,134 | 25% WR | Kelly: -4.31
    "exchange_netflow_reversal",      # -$992  | 0% WR  | on-chain too slow
    "halloween_effect",               # -$943  | 0% WR  | calendar doesn't work in crypto
    "monthly_seasonality",            # -$942  | 12.5% WR | same
    "fourier_cycle_detector",         # -$935  | 0% WR  | overfitted cycles
    "smart_money_fvg",                # -$928  | 0% WR  | ICT concepts = zero edge
    "m2_liquidity_lag",               # -$879  | 22% WR | macro too slow for hourly
    "price_touch_recurrence",         # -$874  | 0% WR  | S/R too noisy
    "momentum_mean_rev_blend",        # -$712  | 0% WR  | contradictory signals
    "altcoin_season_rotation",        # -$654  | 0% WR  | alt season unreliable
    "cross_sectional_momentum",       # -$612  | 0% WR  | wrong timeframe
    # Medium loss ($200-$500 each)
    "community_bb_squeeze_breakout_crypto",  # -$472 | 0% WR
    "btc_dominance_reversal",                # -$389 | 0% WR
    "spike_volume_explosion",                # -$342 | 0% WR
    "sector_momentum_7d",                    # -$329 | 0% WR
    "community_ict_fvg_selective",           # -$304 | 12.5% WR | Kelly: -1.65
    "break_of_structure",                    # -$273 | 0% WR
    "community_momentum_breakout_volume_crypto",  # -$272 | 0% WR
    "spike_squeeze_breakout",                # -$268 | 0% WR
    "coingecko_trending_volume",             # -$258 | 0% WR
    # Minor loss (<$200 but still negative EV)
    "multi_touch_level_strength",            # -$118 | 0% WR
    "halving_cycle_position",                # -$80  | 0% WR
    "price_level_magnetism",                 # -$66  | 89% WR but NEGATIVE PnL!
    "support_resistance_bounce",             # -$48  | 0% WR
    "stablecoin_buying_power",               # -$17  | 50% WR | Kelly: -0.07
    "session_momentum_continuation",         # -$1   | 67% WR | Kelly: -0.03
    "failed_breakout_reversal",              # -$0   | 50% WR | Kelly: -1.50
}

# Legacy alias
DISABLED_BY_TRIAGE = GRAVEYARD


def is_graveyard(strategy_name):
    """Check if a strategy is in the graveyard (permanently retired)"""
    return strategy_name in GRAVEYARD
