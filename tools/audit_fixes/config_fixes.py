"""
Config Fixes — Restore Production-Grade Values
================================================
The config.py has several values that were temporarily changed during
testing sprints and never reverted. This module provides the corrected
values and a function to patch them.

Changes:
1. MAX_CONCURRENT_PICKS: 999 → 10 (was uncapped for testing)
2. MIN_DSR_PROBABILITY: 0.60 → 0.75 (was lowered because it blocked all picks)
3. MIN_DSR_PRODUCTION: 0.80 → 0.95 (must be strict in production)
4. CANDIDATE_PAIRS: 34 → 10 (reduces multiple-testing inflation)

Author: Forensic Audit Implementation (PR #72)
Date: 2026-04-11
"""

# ─── CORRECTED VALUES ────────────────────────────────────────────────────────

# These override crypto_ml_edge/config.py values

CORRECTED_CONFIG = {
    # Position limits — was 999 (uncapped) during "TESTING SPRINT"
    "MAX_CONCURRENT_PICKS": 10,
    
    # DSR gates — were lowered because they "blocked ALL picks"
    # That blocking was CORRECT BEHAVIOR when all models are noise.
    # Now restored to proper thresholds.
    "MIN_DSR_PROBABILITY": 0.75,    # For research/training phase
    "MIN_DSR_PRODUCTION": 0.95,     # For live pick generation
    
    # Universe — reduced from 34 to top-10 by liquidity
    # Each added pair = more multiple testing inflation
    "DEFAULT_PAIRS": [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
        "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT", "TAOUSDT",
    ],
    
    # Kelly fraction — keeping current conservative setting
    "KELLY_FRACTION": 0.15,
    
    # TP/SL — adjusted per audit Section 5.2 recommendations
    "TPSL_CONFIG": {
        "1h": {"tp_atr_mult": 2.5, "sl_atr_mult": 1.5, "max_hold_bars": 24},
        "4h": {"tp_atr_mult": 3.5, "sl_atr_mult": 2.0, "max_hold_bars": 20},
    },
}


def get_corrected_value(key: str):
    """Get a corrected config value."""
    return CORRECTED_CONFIG.get(key)


def print_diff():
    """Print the diff between current and corrected config values."""
    current = {
        "MAX_CONCURRENT_PICKS": 999,
        "MIN_DSR_PROBABILITY": 0.60,
        "MIN_DSR_PRODUCTION": 0.80,
        "DEFAULT_PAIRS_COUNT": 34,
        "TPSL_1h_tp": 3.0,
        "TPSL_1h_sl": 2.0,
    }
    
    corrected = {
        "MAX_CONCURRENT_PICKS": 10,
        "MIN_DSR_PROBABILITY": 0.75,
        "MIN_DSR_PRODUCTION": 0.95,
        "DEFAULT_PAIRS_COUNT": 10,
        "TPSL_1h_tp": 2.5,
        "TPSL_1h_sl": 1.5,
    }
    
    print("\n" + "=" * 60)
    print("CONFIG FIXES — Current vs Corrected")
    print("=" * 60)
    
    for key in current:
        old = current[key]
        new = corrected[key]
        changed = "← CHANGED" if old != new else ""
        print(f"  {key:30s}  {str(old):>8s} → {str(new):>8s}  {changed}")
    
    print("=" * 60 + "\n")


# ─── Patch file generator ────────────────────────────────────────────────────

CONFIG_PATCH = """
# ─── PATCHED VALUES (Forensic Audit Fix, 2026-04-11) ────────────────────────
# See QUANT_FORENSIC_AUDIT_REPORT.md for justification of each change.

# RESTORED: Was 999 during "TESTING SPRINT" — no portfolio concentration control
MAX_CONCURRENT_PICKS = 10

# RESTORED: Was lowered from 0.75 because DSR "blocked ALL picks"
# That blocking was CORRECT BEHAVIOR when all models are noise (AUC 0.27).
MIN_DSR_PROBABILITY = 0.75

# RESTORED: Production gate must be strict (was 0.80, should be 0.95)
MIN_DSR_PRODUCTION = 0.95

# UPDATED: TP/SL per Kelly-optimal analysis (Section 5.2)
# Previous: 1h TP=3.0/SL=2.0 (R:R = 1.5:1, breakeven at 40% WR)
# New: 1h TP=2.5/SL=1.5 (R:R = 1.67:1, breakeven at 37.5% WR)
TPSL_CONFIG = {
    "1h":  {"tp_atr_mult": 2.5, "sl_atr_mult": 1.5, "max_hold_bars": 24},
    "4h":  {"tp_atr_mult": 3.5, "sl_atr_mult": 2.0, "max_hold_bars": 20},
}
"""


if __name__ == "__main__":
    print_diff()
    print("Patch content for config.py:")
    print(CONFIG_PATCH)
