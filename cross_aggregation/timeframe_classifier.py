#!/usr/bin/env python3
"""
Trade Timeframe Classifier — assigns SCALP/INTRADAY/SWING/POSITION to every pick.

Tiers:
  SCALP     = < 4 hours hold (5m, 15m, 1H bars)
  INTRADAY  = 4-24 hours hold (1H, 4H bars)
  SWING     = 1-7 days hold (4H, 1D bars)
  POSITION  = 7+ days hold (1D, 1W bars)

Resolution: strategy name > max_hold_days field > system default > SWING fallback.
"""

# ── Explicit strategy → timeframe mappings ──────────────────────────────────
# Derived from code inspection, backtest configs, and maxHoldDays fields.
STRATEGY_TIMEFRAME = {
    # ── SCALP (< 4h) ──
    "rapid_fire":                           "SCALP",
    "ema_stack":                            "SCALP",
    "bollinger_squeeze":                    "SCALP",    # rapid_fire variant
    "spike_momentum_ignition":              "SCALP",
    "meme-scanner-live":                    "SCALP",
    "live_spike_trader":                    "SCALP",

    # ── INTRADAY (4-24h) ──
    "keltner_compression_expansion_sol_v1": "INTRADAY",  # 12 bars on 1H = ~12h
    "crypto_keltner_compression_expansion_v1": "INTRADAY",
    "drawdown_recovery_rsi":                "INTRADAY",
    "drawdown_recovery_rsi_eth":            "INTRADAY",
    "multi_period_rsi_confluence_xrp":      "INTRADAY",
    "multi_period_rsi_confluence_eth":      "INTRADAY",
    "crypto_drawdown_convexity_recovery_v1":"INTRADAY",
    "luxalgo_confluence":                   "INTRADAY",
    "stoch-rsi-crypto":                     "INTRADAY",
    "cci-crypto-reversal":                  "INTRADAY",
    "macd-momentum":                        "INTRADAY",
    "supertrend-crypto":                    "INTRADAY",
    "crypto-fear-reversal-scout":           "INTRADAY",
    "btc-dominance-reversal-scout":         "INTRADAY",
    "altseason-rotation-scout":             "INTRADAY",
    "crypto-momentum-scout":                "INTRADAY",
    "bollinger-squeeze":                    "INTRADAY",  # KIMI variant, longer hold than rapid_fire
    "Bollinger Squeeze Breakout":           "INTRADAY",
    "Crypto RSI Scout":                     "INTRADAY",
    "Supertrend Scout":                     "INTRADAY",
    "Altseason Rotation Signal":            "INTRADAY",
    "Extreme Fear Contrarian Buy":          "INTRADAY",
    "Pairs Trading (Cointegration)":        "INTRADAY",
    "Forex MA Scout":                       "INTRADAY",
    "Meme Coin Scout":                      "INTRADAY",
    "sr_breakout_retest":                   "INTRADAY",

    # ── SWING (1-7 days) ──
    "bollinger_keltner_squeeze_breakout":   "SWING",
    "options_25delta_skew":                 "SWING",
    "kalman_filter_trend":                  "SWING",
    "swing_structure":                      "SWING",
    "entropy_regime_breakout":              "SWING",
    "williams_r_sma_signal":               "SWING",
    "connors_williams_hybrid":              "SWING",
    "volume_profile_poc_reversion":         "SWING",
    "adaptive_vr_confluence":               "SWING",
    "macd_rsi_multi_tf":                    "SWING",
    "autocorrelation_exploiter":            "SWING",
    "cumulative_delta_divergence":          "SWING",
    "tvl_weighted_momentum":               "SWING",
    "seasonal_factor_rotation":             "SWING",
    "widened_tp_momentum_carry":            "SWING",
    "swing_failure_pattern":                "SWING",
    "break_of_structure":                   "SWING",
    "funding_rate_carry":                   "SWING",
    "oi_funding_squeeze":                   "SWING",
    "liquidation_cascade_bottom":           "SWING",
    "atr_volatility_breakout":              "SWING",
    "whale_accumulation_detector":          "SWING",
    "sentiment_price_divergence":           "SWING",
    "cross_sectional_momentum":             "SWING",
    "proven_vwap_mean_reversion":           "SWING",
    "proven_propfirm_conservative":         "SWING",
    "Betting Against Beta":                 "SWING",
    "12-1 Momentum Factor":                "SWING",
    # AI Challenge curator strategies
    "evolutionary_regime_engine":           "SWING",
    "keltner_compression_breakout":         "SWING",
    "keltner_expansion_continuation":       "SWING",
    "williams_r_sma_oscillator":            "SWING",
    "williams_r_oversold_recovery":         "SWING",
    "regime_aware_independent":             "SWING",
    "data_first_scanner_follow":            "SWING",
    "tight_tp_precision":                   "SWING",
    "tight_tp_precision_long":              "SWING",
    "ml_momentum_composite":               "SWING",
    "swing_structure_downtrend":            "SWING",

    # ── POSITION (7+ days) ──
    "ctrend_multi_horizon":                 "POSITION",
    "multi_timeframe_ema_stack":            "POSITION",
    "hurst_regime_adaptive":                "POSITION",
    "volume_profile_value_area":            "POSITION",
    "cumulative_rsi_signal":                "POSITION",
    "cross_system_regime_arbitrage":        "POSITION",
    "ttm_squeeze":                          "POSITION",
    "mvrv_contrarian_dip":                  "POSITION",
    "hash_ribbon_buy":                      "POSITION",
    "stablecoin_buying_power":              "POSITION",
    "nvt_overvaluation":                    "POSITION",
    "fear_greed_extreme_dca":               "POSITION",
    "sopr_dip_buy_proxy":                   "POSITION",
    "onchain_composite_score":              "POSITION",
    "hayes_liquidity_index":                "POSITION",
    "pentoshi_htf_structure":               "POSITION",
    "funding_rate_arbitrage":               "POSITION",
    "connors_rsi2":                         "POSITION",
    "vix_spike_reversal":                   "POSITION",

    # ── EQUITY POSITION (7+ days) — added 2026-04-30 ──
    # Long-horizon equity strategies that previously fell through to SWING
    # because no equity strategy was in this map. Per the 4-AI convergence
    # audit (Claude / FreeBuff GLM-5.1 / Codebuff / Roocode) on 2026-04-30:
    # zero EQUITY×POSITION picks on /audit out of 281 closed equity rows.
    # Only strategies with a verified live emitter or a wired registered
    # source are listed — no speculative placeholders.
    "vt_earnings_pead":                     "POSITION",  # alpha_engine/vt_baby_strategies.py:429
    "magic_formula_x_piotroski_x_acquirers":"POSITION",  # alpha_engine/value_screener_runner.py
    "tradingagents_consensus":              "POSITION",  # alpha_engine/tradingagents_emitter.py (PR #544)
    "stocks_ema_golden_cross":              "POSITION",  # verified live: producing PEP
    "smart_money_accumulation":             "POSITION",  # verified live: producing LLY

    # ── BOND SWING (mean-reversion ~3-10d) ──
    "bond_credit_spread_mean_reversion":    "SWING",     # alpha_engine/bond_strategies.py:537
}

# ── System-level defaults (when strategy not in map) ──
SYSTEM_TIMEFRAME_DEFAULT = {
    "rapid_fire":               "SCALP",
    "live_spike_trader":        "SCALP",
    "meme_scanner":             "SCALP",

    "battleground":             "INTRADAY",
    "incubator_battleground":   "INTRADAY",
    "luxalgo_filters":          "INTRADAY",
    "kimi_riseoftheclaw":       "INTRADAY",
    "kimi_live_signals":        "INTRADAY",
    "riseoftheclaw":            "INTRADAY",
    "fc_crypto_pro":            "INTRADAY",
    "claude_gainer_st":         "INTRADAY",
    "chatgpt_combined":         "INTRADAY",

    "alpha_engine":             "SWING",
    "alpha_engine_fast":        "SWING",
    "mercury2":                 "SWING",
    "paper_trading":            "SWING",
    "crypto_signal_engine":     "SWING",
    "quan_engine":              "SWING",
    "breakout_a_sr":            "SWING",
    "breakout_b_ml":            "SWING",
    "breakout_c_spike":         "SWING",
    "stocks_competition":       "SWING",
    "multi_asset":              "SWING",
    "ai_challenge_claude":      "SWING",
    "ai_challenge_grok":        "SWING",
    "ai_challenge_kimi_moonshot": "SWING",
    "ai_challenge_antigravity": "SWING",
    "ai_challenge_mercury":     "SWING",
    "ai_challenge_predictable": "SWING",
    "ai_challenge_scanner":     "SWING",

    "genome":                   "POSITION",
    "mega_mutation":            "POSITION",
    "predictions":              "POSITION",
    "ml_crypto_pred":           "POSITION",
    "coinglass":                "POSITION",
    "crypto_ml_edge":           "POSITION",

    # ── Non-crypto POSITION lanes (added 2026-04-30) ──
    "tradingagents":            "POSITION",  # PR #544 — 5-90d horizon
    "value_screener":           "POSITION",  # UEPS magic-formula picks (3y+ holding)

    # ── Bond ──
    "bond_agent":               "SWING",     # .github/workflows/bond-agent.yml
}

# Tier ordering for adjacency checks
TIER_ORDER = {"SCALP": 0, "INTRADAY": 1, "SWING": 2, "POSITION": 3}


def classify_timeframe(pick: dict, system_name: str = "") -> str:
    """
    Classify a pick's trade timeframe.

    Priority:
      1. Explicit strategy name match
      2. max_hold_days / maxHoldDays field on the pick
      3. System-level default
      4. Fallback: SWING
    """
    # 1. Strategy name lookup
    strategy = pick.get("strategy", "") or ""
    if strategy in STRATEGY_TIMEFRAME:
        return STRATEGY_TIMEFRAME[strategy]

    # 2. max_hold_days / time_horizon_days field
    # `time_horizon_days` was added 2026-04-30 so picks emitted by the
    # TradingAgents emitter (PR #544) and by other long-horizon producers
    # that don't set max_hold_days still classify correctly. Order matters
    # — explicit max_hold_days wins if both are present.
    hold_days = (
        pick.get("max_hold_days")
        or pick.get("maxHoldDays")
        or pick.get("hold_days")
        or pick.get("time_horizon_days")
    )
    if hold_days is not None:
        try:
            d = float(hold_days)
            if d < 0.17:        # < 4 hours
                return "SCALP"
            elif d <= 1.0:      # 4-24 hours
                return "INTRADAY"
            elif d <= 7.0:      # 1-7 days
                return "SWING"
            else:               # 7+ days
                return "POSITION"
        except (ValueError, TypeError):
            pass

    # 3. System-level default
    sys = system_name or pick.get("source_system", "") or ""
    if sys in SYSTEM_TIMEFRAME_DEFAULT:
        return SYSTEM_TIMEFRAME_DEFAULT[sys]

    # 4. Fallback
    return "SWING"


def is_real_conflict(tf_a: str, tf_b: str) -> bool:
    """
    Returns True if two timeframes are close enough to be a real conflict.
    Same tier or adjacent tiers = conflict.
    2+ tiers apart = NOT a conflict (e.g., SCALP vs SWING).
    """
    dist = abs(TIER_ORDER.get(tf_a, 2) - TIER_ORDER.get(tf_b, 2))
    return dist <= 1


def timeframe_label(tf: str) -> str:
    """Human-readable label with typical hold period."""
    labels = {
        "SCALP":    "Scalp (<4h)",
        "INTRADAY": "Intraday (4-24h)",
        "SWING":    "Swing (1-7d)",
        "POSITION": "Position (7d+)",
    }
    return labels.get(tf, tf)
