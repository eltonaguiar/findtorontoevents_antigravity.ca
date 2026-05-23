"""
Strategy Mutations — Viable variants extracted from banned/killed strategies.

Cross-asset analysis found that some banned strategies have profitable subsets
when filtered by symbol or direction. These mutations isolate the winning edge
and discard the losing component.

Mutation types:
  - symbol_lock: Only allow picks on symbols where the strategy is profitable.
  - direction_filter: Only allow picks in the direction where the strategy wins.

All mutations start as CANDIDATE and follow the normal promotion ladder:
  CANDIDATE -> BACKTEST_PASS -> WF_PASS -> STATS_PASS -> FORWARD_PASS -> PRODUCTION
"""

from __future__ import annotations

from typing import Any, Dict, Optional


# ---------------------------------------------------------------------------
# Symbol-locked variants: strategy profitable on specific symbols only
# ---------------------------------------------------------------------------

SYMBOL_LOCKED_VARIANTS: Dict[str, Dict[str, Any]] = {
    "st_rsi_momentum_confluence_symbol_locked": {
        "parent": "st_rsi_momentum_confluence",
        "mutation_type": "symbol_lock",
        "status": "CANDIDATE",
        "allowed_symbols": [
            "ARBUSDT", "UNIUSDT", "ATOMUSDT", "LINKUSDT", "LTCUSDT",
            "BNBUSDT", "APTUSDT", "ETHUSDT", "BTCUSDT", "TRXUSDT",
        ],
        "blocked_symbols": [
            "DOTUSDT", "OPUSDT", "ADAUSDT", "SOLUSDT", "XRPUSDT",
            "DOGEUSDT", "NEARUSDT", "AVAXUSDT", "SUIUSDT", "IMXUSDT",
        ],
        "backtest_wr": 0.743,
        "backtest_pf": 2.51,
        "backtest_trades": 191,
        "backtest_pnl": 167.88,
        "direction": "LONG",
        "created_at": "2026-04-03",
        "rationale": (
            "Symbol divergence: ARBUSDT 91.5% WR vs DOTUSDT 0% WR. "
            "Lock to profitable symbols."
        ),
    },
    "cot_positioning_CT_locked": {
        "parent": "cot_positioning",
        "mutation_type": "symbol_lock",
        "status": "CANDIDATE",
        "allowed_symbols": ["CT=F"],
        "direction": "LONG",
        "backtest_wr": 0.898,
        "backtest_pf": 13.10,
        "backtest_trades": 49,
        "created_at": "2026-05-04",
        "rationale": (
            "Cotton (CT=F) carries the entire COT-positioning edge: 89.8% WR "
            "across 49 trades, PF 13.10. Other commodity symbols dilute. "
            "Lock to CT=F LONG. Source: 10-agent swarm closed-pick analysis "
            "of asset_class==COMMODITY in alpha_engine/data/closed_picks.json "
            "(2026-05-04). Single-cell concentration acknowledged — not a "
            "diversified edge — but the cell is real and reproducible."
        ),
        "monitor_closely": True,
    },
    "cftc_cot_commercial_signal_CT_locked": {
        "parent": "cftc_cot_commercial_signal",
        "mutation_type": "symbol_lock",
        "status": "CANDIDATE",
        "allowed_symbols": ["CT=F"],
        "direction": "LONG",
        "backtest_wr": 0.875,
        "backtest_pf": 10.39,
        "backtest_trades": 40,
        "created_at": "2026-05-04",
        "rationale": (
            "Sister-strategy of cot_positioning on the same CT=F edge: 87.5% "
            "WR across 40 trades, PF 10.39. Same lock rationale and same "
            "single-cell-concentration caveat. Two independent COT-family "
            "strategies converging on the same instrument suggests the "
            "underlying signal (cotton commercial positioning) is the edge."
        ),
        "monitor_closely": True,
    },
}

# ---------------------------------------------------------------------------
# Direction-filtered variants: strategy profitable in one direction only
# ---------------------------------------------------------------------------

DIRECTION_FILTERED_VARIANTS: Dict[str, Dict[str, Any]] = {
    "macd_crossover_short_only": {
        "parent": "macd_crossover",
        "mutation_type": "direction_filter",
        "status": "CANDIDATE",
        "allowed_direction": "SHORT",
        "backtest_wr": 0.786,
        "backtest_trades": 14,
        "backtest_pnl": 2.27,
        "created_at": "2026-04-03",
        "rationale": "SHORT 78.6% WR vs LONG 0% WR. Direction asymmetry.",
    },
    "irb_hoffman_short_only": {
        "parent": "irb_hoffman",
        "mutation_type": "direction_filter",
        "status": "CANDIDATE",
        "allowed_direction": "SHORT",
        "backtest_wr": 0.833,
        "backtest_trades": 6,
        "backtest_pnl": 4.85,
        "created_at": "2026-04-03",
        "rationale": "SHORT 83.3% WR vs LONG 0% WR. Clear direction edge.",
    },
    "ig_contrarian_sentiment_short_only": {
        "parent": "ig_contrarian_sentiment",
        "mutation_type": "direction_filter",
        "status": "CANDIDATE",
        "allowed_direction": "SHORT",
        "backtest_wr": 0.571,
        "backtest_trades": 42,
        "created_at": "2026-05-04",
        "rationale": (
            "FOREX retail-sentiment contrarian: SHORT 57.1% WR (n=42) vs "
            "LONG 19.8% WR (n=111) — 37.3pp asymmetry, the largest uncovered "
            "FOREX direction-filter gap after PR #786. LONG side is the "
            "primary leak. Source: 10-agent swarm closed-pick analysis of "
            "asset_class==FOREX 2026-05-04. Mutate-before-kill: no parent "
            "kill, just SHORT-only candidate."
        ),
        "monitor_closely": True,
    },
    "ml_crypto_predictor_short_only": {
        "parent": "ml_crypto_predictor",
        "mutation_type": "direction_filter",
        "status": "CANDIDATE",
        "allowed_direction": "SHORT",
        "backtest_wr": None,  # Known 100% WR on FETUSDT/SUIUSDT SHORT combos
        "backtest_trades": None,
        "created_at": "2026-04-04",
        "rationale": (
            "Parent LONG 0% WR, 41 trades, contributed -15238% cum PnL "
            "(flagged by copilot-quant-audit). Parent added to PERMANENTLY_KILLED. "
            "SHORT direction retained — existing _100WR_COMBOS already reward "
            "ml_crypto_predictor SHORT on FETUSDT/SUIUSDT. This mutation formalizes "
            "the SHORT-only variant."
        ),
    },
    "myfxbook_retail_contrarian_short_only": {
        "parent": "myfxbook_retail_contrarian",
        "mutation_type": "direction_filter",
        "status": "CANDIDATE",
        "allowed_direction": "SHORT",
        "backtest_wr": 0.462,
        "backtest_trades": 13,
        "created_at": "2026-05-04",
        "rationale": (
            "Parent FOREX strategy: SHORT 46.2% WR (n=13) vs LONG 10.5% WR "
            "(n=86) — 36pp asymmetry per tools/mutation_analysis.py output "
            "in reports/deep_dive_FOREX_mutation_2026_05_04.md. LONG side "
            "is the leak (FOREX class PF 0.27 with this strategy active). "
            "Mutate-before-kill: keep SHORT side as CANDIDATE, demote LONG."
        ),
        "monitor_closely": True,
    },
    "forex_rsi2_mean_reversion_short_only": {
        "parent": "forex_rsi2_mean_reversion",
        "mutation_type": "direction_filter",
        "status": "CANDIDATE",
        "allowed_direction": "SHORT",
        "backtest_wr": 0.273,
        "backtest_trades": 11,
        "created_at": "2026-05-04",
        "rationale": (
            "Parent FOREX strategy: SHORT 27.3% WR (n=11) vs LONG 2.7% WR "
            "(n=73) — 25pp asymmetry per mutation_analysis.py. LONG side "
            "near-zero. SHORT WR still below charter T2 floor — CANDIDATE "
            "only, monitor_closely. Aligns with crypto_risk_gates.py HARD_KILL "
            "intent without a blanket parent kill."
        ),
        "monitor_closely": True,
    },
}

# ---------------------------------------------------------------------------
# Combo-filtered variants: symbol + time window restrictions
# ---------------------------------------------------------------------------

COMBO_FILTERED_VARIANTS: Dict[str, Dict[str, Any]] = {
    "quan_engine_scalp_symbol_time_locked": {
        "parent": "quan_engine_scalp",
        "mutation_type": "combo_filter",
        "status": "CANDIDATE",
        "allowed_symbols": ["AVAXUSDT", "TRXUSDT", "XRPUSDT", "ETCUSDT"],
        "allowed_hours_utc": [22, 23, 0, 1, 2, 3, 4, 5],  # Night session only
        "backtest_wr": 0.651,
        "backtest_pf": 1.89,
        "backtest_trades": 86,
        "backtest_pnl": 12.11,
        "created_at": "2026-04-04",
        "rationale": (
            "Parent 25% WR overall, but AVAX/TRX/XRP/ETC during 22:00-05:00 UTC "
            "= 65.1% WR on 86 trades, PF 1.89. 4 non-correlated symbols. "
            "Night session avoids the 08:00-17:00 death zone."
        ),
    },
    "quan_engine_scalp_best4_hours": {
        "parent": "quan_engine_scalp",
        "mutation_type": "combo_filter",
        "status": "CANDIDATE",
        "allowed_symbols": ["AVAXUSDT", "TRXUSDT", "XRPUSDT", "ETCUSDT"],
        "allowed_hours_utc": [0, 3, 22, 23],  # Tightest window
        "backtest_wr": 0.680,
        "backtest_pf": 2.35,
        "backtest_trades": 50,
        "backtest_pnl": 9.25,
        "created_at": "2026-04-04",
        "rationale": (
            "Higher-conviction variant of symbol_time_locked. "
            "68.0% WR, PF 2.35 on 50 trades. Fewer signals but higher quality."
        ),
    },
}

# ---------------------------------------------------------------------------
# Inverse variants: flip direction on symbols where parent consistently loses
# ---------------------------------------------------------------------------

INVERSE_SYMBOL_VARIANTS: Dict[str, Dict[str, Any]] = {
    "quan_engine_scalp_inverse_weak_symbols": {
        "parent": "quan_engine_scalp",
        "mutation_type": "inverse_symbol_lock",
        "status": "CANDIDATE",
        "inverse_symbols": [
            "ICPUSDT", "ETHUSDT", "ADAUSDT", "DOTUSDT",
            "ONDOUSDT", "KASUSDT", "XLMUSDT",
        ],
        "estimated_wr": 0.834,
        "estimated_trades": 507,
        "estimated_pnl": 181.84,
        "created_at": "2026-04-04",
        "rationale": (
            "Parent has 21.1% WR on these 7 symbols (507 trades). "
            "Inverting direction gives ~83.4% WR. All 7 symbols individually "
            "profitable when inverted (ICP 89%, ETH 87%, ADA 87%, DOT 85%, "
            "KAS 84%, ONDO 80%, XLM 71%). Multi-symbol = high robustness. "
            "CAVEAT: R:R inverts too (2:1 becomes ~1:2). Monitor closely."
        ),
        "monitor_closely": True,
    },
}

# ---------------------------------------------------------------------------
# Combined registry of all mutation variants
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Inverse contrarian variants: parent's LONG signal used as SHORT indicator
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Revival variants: resurrecting killed strategies on proven symbol+direction
# ---------------------------------------------------------------------------

REVIVAL_VARIANTS: Dict[str, Dict[str, Any]] = {
    "obv_divergence_revival": {
        "parent": "st_obv_support_divergence",
        "mutation_type": "symbol_direction_lock",
        "status": "CANDIDATE",
        "allowed_symbols": ["DOTUSDT", "ETHUSDT", "OPUSDT", "APTUSDT"],
        "allowed_direction": "LONG",
        "recent_wr": 0.73,
        "recent_trades": 11,
        "backtest_wr": None,  # Needs backtesting — forward-test data only
        "created_at": "2026-04-04",
        "rationale": (
            "Parent st_obv_support_divergence is in PERMANENTLY_KILLED but "
            "recent 11 trades show 73% WR. All wins are LONG on DOT (3 wins), "
            "ETH, OP, APT. Revival locks to these 4 symbols + LONG-only. "
            "OBV divergence near support + RSI < 45 is the core signal. "
            "Symbol-lock isolates the profitable subset."
        ),
        "monitor_closely": True,
    },
}

INVERSE_CONTRARIAN_VARIANTS: Dict[str, Dict[str, Any]] = {
    "stochrsi_macd_combo_inverse_short": {
        "parent": "stochrsi_macd_combo",
        "mutation_type": "inverse_direction",
        "status": "CANDIDATE",
        "original_direction": "LONG",
        "mutated_direction": "SHORT",
        "blocked_symbols": ["UUSDT", "DUSDT", "BFUSDUSDT", "RLUSDUSDT"],  # noise/broken
        "estimated_wr": 0.692,
        "estimated_trades": 13,  # real trades only
        "created_at": "2026-04-04",
        "rationale": (
            "Parent LONG signal = 42.1% WR. Inverse (SHORT when parent says LONG) "
            "= 69.2% WR on 13 real trades. Winning symbols: BTCUSDT, KERNELUSDT, "
            "ZBTUSDT. Needs broken symbols blocked. Cross-asset potential high "
            "(MACD+EMA+volume logic is universal)."
        ),
    },
    "widened_tp_momentum_carry_night_short": {
        "parent": "widened_tp_momentum_carry",
        "mutation_type": "combo_filter",
        "status": "CANDIDATE",
        "allowed_direction": "SHORT",
        "allowed_hours_utc": [22, 23, 0, 1, 2],
        "allowed_asset_classes": ["FOREX", "EQUITY", "CRYPTO"],
        "disable_trailing_stop": True,
        "estimated_wr": 0.833,
        "estimated_trades": 6,
        "created_at": "2026-04-04",
        "rationale": (
            "Parent 33.3% WR overall, but Hour-0 UTC window = 83% WR (5/6). "
            "Non-crypto assets 67% WR (2/3). SHORT-only + time expiry exits "
            "are the only winning combination. Wider TP works better on less "
            "volatile instruments (forex/equities). Trailing stop kills winners — "
            "disable it. SMALL SAMPLE — monitor closely."
        ),
        "monitor_closely": True,
    },
}

ALL_MUTATIONS: Dict[str, Dict[str, Any]] = {
    **SYMBOL_LOCKED_VARIANTS,
    **DIRECTION_FILTERED_VARIANTS,
    **COMBO_FILTERED_VARIANTS,
    **INVERSE_SYMBOL_VARIANTS,
    **REVIVAL_VARIANTS,
    **INVERSE_CONTRARIAN_VARIANTS,
}


# ---------------------------------------------------------------------------
# Filter helpers — used by quality_gates.py to enforce mutation constraints
# ---------------------------------------------------------------------------

def check_mutation_filter(
    strategy: str,
    symbol: str,
    direction: str,
) -> tuple[bool, str]:
    """Check if a pick passes the mutation filter for its strategy.

    Returns:
        (allowed, reason) tuple. allowed=True if the pick should proceed.
    """
    # Check symbol-locked variants
    for variant_id, cfg in SYMBOL_LOCKED_VARIANTS.items():
        if strategy == variant_id:
            sym_upper = symbol.upper()
            if sym_upper not in cfg["allowed_symbols"]:
                return False, (
                    f"Symbol {sym_upper} not in allowed list for "
                    f"mutation {variant_id}"
                )
            # Also check direction if specified
            if cfg.get("direction") and direction.upper() != cfg["direction"]:
                return False, (
                    f"Direction {direction} not allowed for "
                    f"mutation {variant_id} (requires {cfg['direction']})"
                )
            return True, "Passes symbol-lock filter"

    # Check direction-filtered variants
    for variant_id, cfg in DIRECTION_FILTERED_VARIANTS.items():
        if strategy == variant_id:
            if direction.upper() != cfg["allowed_direction"]:
                return False, (
                    f"Direction {direction} not allowed for "
                    f"mutation {variant_id} (requires {cfg['allowed_direction']})"
                )
            return True, "Passes direction filter"

    # Check combo-filtered variants (symbol + time window)
    for variant_id, cfg in COMBO_FILTERED_VARIANTS.items():
        if strategy == variant_id:
            sym_upper = symbol.upper()
            if sym_upper not in cfg["allowed_symbols"]:
                return False, (
                    f"Symbol {sym_upper} not in allowed list for "
                    f"combo mutation {variant_id}"
                )
            return True, "Passes combo filter (time checked at entry)"

    # Check inverse-symbol variants
    for variant_id, cfg in INVERSE_SYMBOL_VARIANTS.items():
        if strategy == variant_id:
            sym_upper = symbol.upper()
            if sym_upper not in cfg["inverse_symbols"]:
                return False, (
                    f"Symbol {sym_upper} not in inverse list for "
                    f"mutation {variant_id}"
                )
            return True, "Passes inverse-symbol filter"

    # Check revival variants (symbol + direction lock)
    for variant_id, cfg in REVIVAL_VARIANTS.items():
        if strategy == variant_id:
            sym_upper = symbol.upper()
            if sym_upper not in cfg["allowed_symbols"]:
                return False, (
                    f"Symbol {sym_upper} not in allowed list for "
                    f"revival mutation {variant_id}"
                )
            if direction.upper() != cfg["allowed_direction"]:
                return False, (
                    f"Direction {direction} not allowed for "
                    f"revival mutation {variant_id} (requires {cfg['allowed_direction']})"
                )
            return True, "Passes revival symbol+direction filter"

    # Not a mutation strategy — always allowed
    return True, "Not a mutation strategy"


def get_mutation_for_parent(
    parent_strategy: str,
    symbol: str,
    direction: str,
) -> Optional[str]:
    """Given a parent strategy name, check if a mutation variant applies.

    If the pick's symbol/direction match a mutation's constraints, return
    the mutation variant ID so the pick can be re-attributed.

    Returns None if no mutation applies.
    """
    for variant_id, cfg in ALL_MUTATIONS.items():
        if cfg["parent"] != parent_strategy:
            continue

        mutation_type = cfg["mutation_type"]

        if mutation_type == "symbol_lock":
            if symbol.upper() in cfg["allowed_symbols"]:
                if cfg.get("direction") and direction.upper() != cfg["direction"]:
                    continue
                return variant_id

        elif mutation_type == "direction_filter":
            if direction.upper() == cfg["allowed_direction"]:
                return variant_id

        elif mutation_type == "combo_filter":
            if symbol.upper() in cfg["allowed_symbols"]:
                if cfg.get("direction") and direction.upper() != cfg["direction"]:
                    continue
                return variant_id

        elif mutation_type == "inverse_symbol_lock":
            if symbol.upper() in cfg["inverse_symbols"]:
                return variant_id

        elif mutation_type == "symbol_direction_lock":
            if symbol.upper() in cfg["allowed_symbols"]:
                if direction.upper() == cfg["allowed_direction"]:
                    return variant_id

    return None
