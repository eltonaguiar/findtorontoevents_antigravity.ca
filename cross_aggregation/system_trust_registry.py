"""
System Trust Registry — Single source of truth for system reliability.

Derived from 8,457 closed picks forward test data (updated Mar 18 2026):
- Claude Gainer ST: 634 trades, 72.7% WR, PF 6.39 -> PROVEN
- Super Signals: 70 trades, 68.6% WR, PF 3.78 -> PROVEN
- Battleground: 92 trades, 63.7% WR, PF 2.48 -> PROVEN
- Aggregated Picks: 163 trades, 55.8% WR, PF 1.65 -> RELIABLE
- Mercury2: 51 trades, 51% WR, PF 1.53 -> RELIABLE
- Alpha Engine: 324 trades, 39.6% WR, PF 1.31, +340% PnL -> RELIABLE
- Rapid Fire: 152 trades, 25% WR, PF 0.34, -429% PnL -> BANNED

Phase 1 — Dynamic Trust Tiers (Mar 16 2026):
- Loads performance data from strategy_performance.json + closed_picks
- Auto-computes tier from WR + closed trade count:
    BANNED:     WR < 50% AND 30+ trades (proven losers)
    UNTRUSTED:  WR < 50% AND 10-29 trades, or WR 50-55% AND 30+ trades
    WATCH:      < 10 trades (insufficient data) — 0.3x weight
    RELIABLE:   WR 55-65% AND 10+ trades — 1.0x weight
    PROVEN:     WR > 65% AND 30+ trades — 1.5x weight

Used by:
- aggregator.py (trust-weighted consensus + conflict resolution + scoring)
- fc_crypto_pro.py (conflict winner selection)
- super_signal.py (weighted votes)
- audit dashboard (conflict annotations)
- discord_notify.py (suppress LOSER-anchored picks)
- contested_pick_checker.py (lesson annotations)

See also: data/conflict_lessons_learned.json for full rule documentation.
"""

import json
import pathlib
from typing import Dict, Optional

# Trust tiers — higher = more trusted
TIER_PROVEN = "PROVEN"       # Forward-validated, profitable, statistically significant
TIER_RELIABLE = "RELIABLE"   # Positive PnL, decent WR, but fewer trades or stale
TIER_WATCH = "WATCH"         # Mixed results, needs more data
TIER_UNTRUSTED = "UNTRUSTED" # Losing money, low WR, or broken
TIER_BANNED = "BANNED"       # Catastrophically bad, exclude from all consensus

# Trust multipliers for scoring formulas
TIER_MULTIPLIERS = {
    TIER_PROVEN: 1.5,
    TIER_RELIABLE: 1.2,
    TIER_WATCH: 1.0,
    TIER_UNTRUSTED: 0.5,
    TIER_BANNED: 0.0,
}

# Vote weights for consensus counting (replaces raw "1 vote per system")
TIER_VOTE_WEIGHTS = {
    TIER_PROVEN: 2.0,
    TIER_RELIABLE: 1.5,
    TIER_WATCH: 1.0,
    TIER_UNTRUSTED: 0.3,
    TIER_BANNED: 0.0,
}

# Master registry — update as new performance data arrives
SYSTEM_TRUST = {
    # --- PROVEN (forward-validated, profitable) ---
    # DEMOTED 2026-04-04 per attribution_tracker on 1,200 closed picks:
    #   battleground: 35.7% WR, PF 0.28, PnL -3.6% (n=14 recent) -> WATCH
    #   super_signals: 50.4% WR, PF 0.77, PnL -50.7% (n=119 recent) -> WATCH
    # Both LOSE money despite historical PROVEN labels. Historical 63.7%/68.6% WR
    # was stale. Fresh attribution shows systematic degradation.
    "battleground": {
        "tier": TIER_WATCH,
        "forward_wr": 0.357,
        "total_pnl": -3.6,
        "closed_trades": 14,
        "notes": (
            "DEMOTED 2026-04-04: attribution shows 35.7% WR, PF 0.28 on recent 14 picks. "
            "Historical 63.7% WR / PF 2.48 (92 picks) was stale. Re-promote if "
            "30-day rolling WR exceeds 55% AND PF exceeds 1.3."
        ),
        "significant_strategies": [
            "multi_period_rsi_confluence_eth",
            "drawdown_recovery_rsi_eth",
            "keltner_compression_expansion_sol_v1",
            "multi_timeframe_ema_stack",
        ],
    },
    "claude_gainer_st": {
        "tier": TIER_PROVEN,
        "forward_wr": 0.727,
        "total_pnl": None,
        "closed_trades": 634,
        "notes": "634 trades, 72.7% WR, PF 6.39. Top system by WR and PF. Promoted Mar 18 2026.",
    },
    "super_signals": {
        "tier": TIER_WATCH,
        "forward_wr": 0.504,
        "total_pnl": -50.7,
        "closed_trades": 119,
        "notes": (
            "DEMOTED 2026-04-04: attribution shows 50.4% WR, PF 0.77, -50.7% PnL "
            "on recent 119 picks. Historical 68.6% WR / PF 3.78 (70 picks) was stale. "
            "Asymmetric losses — 50% WR but PF<1 means losses dwarf wins. "
            "Re-promote if 30-day rolling PF > 1.3 AND calmar > 0."
        ),
    },
    "claws_of_doom": {
        "tier": TIER_PROVEN,
        "forward_wr": 0.525,
        "total_pnl": 41.01,
        "closed_trades": 59,
        "notes": "Fear Contrarian. Only works at initial F&G<15 bounce. Second bounce = no edge.",
    },

    # --- RELIABLE (positive or breakeven, decent data) ---
    "aggregated_picks": {
        "tier": TIER_RELIABLE,
        "forward_wr": 0.558,
        "total_pnl": None,
        "closed_trades": 163,
        "notes": "163 trades, 55.8% WR, PF 1.65. Consensus aggregator. Promoted Mar 18 2026.",
    },
    "mercury2": {
        "tier": TIER_RELIABLE,
        "forward_wr": 0.51,
        "total_pnl": None,
        "closed_trades": 51,
        "notes": "51 trades, 51% WR, PF 1.53. Updated Mar 18 2026.",
    },
    "alpha_engine": {
        "tier": TIER_RELIABLE,
        "forward_wr": 0.396,
        "total_pnl": 340.0,
        "closed_trades": 324,
        "notes": "324 trades, 39.6% WR but PF 1.31, +340% PnL. Low WR offset by strong R:R. Promoted Mar 18 2026.",
    },
    "mega_mutation": {
        "tier": TIER_RELIABLE,
        "forward_wr": 0.833,
        "total_pnl": None,
        "closed_trades": 0,
        "notes": "Tournament-proven (Sharpe 4.79-8.38) but no live closures yet. MACD_RSI picks > EMA_CROSS picks.",
    },
    "cross_system_consensus": {
        "tier": TIER_RELIABLE,
        "forward_wr": 0.575,
        "total_pnl": 64.28,
        "closed_trades": 40,
        "notes": "SUPER tier (4+ systems) is reliable. STRONG/MODERATE tiers are 50/50.",
    },
    "luxalgo_filters": {
        "tier": TIER_RELIABLE,
        "forward_wr": None,
        "total_pnl": None,
        "closed_trades": 0,
        "notes": "Fresh SELL signals valid 24-48h on large-caps when RSI>70. Not validated on altcoins vs Mega Mutation.",
    },
    "genome": {
        "tier": TIER_RELIABLE,
        "forward_wr": None,
        "total_pnl": None,
        "closed_trades": 0,
        "notes": "Walk-forward validated in tournament. No live closures yet.",
    },
    "multi_asset_copytrader": {
        "tier": TIER_RELIABLE,
        "forward_wr": 0.464,
        "total_pnl": 61.17,
        "closed_trades": 468,
        "notes": (
            "PROMOTED 2026-04-04: 468 closed / 46.4% WR / PF 1.75 / +61.17% PnL / "
            "calmar 1.26. Diversified across BOND/COMMODITY/EQUITY/FOREX, daily-fresh. "
            "Sub-strategies: futures_momentum 158t +30.57% (metals/rates), "
            "stocks_rsi2_pullback 8W/0L +15.91%. Only copytrader source with both "
            "legitimate PnL and active signals. Re-promote to PROVEN if PF>2.0 "
            "sustained over 30d AND last_signal_at stays <12h."
        ),
    },
    # ── Prediction Market sources — PROVISIONAL TIER_WATCH ──
    # These systems fire fresh signals (last_signal < 2h) but have closed_picks=0
    # because the PM closer pipeline is broken: universal_pick_resolver.py:459-488
    # treats event-market picks as crypto TP/SL trades against BTC/ETH spot,
    # which is the wrong mental model. Kalshi/Polymarket events resolve on their
    # settlement date, not on crypto price movement.
    #
    # GIVEN: these sources publish high-signal picks (whale wallets, event-driven
    # consensus, conviction-filtered kalshi signals) but have no attribution data.
    # Parking at TIER_WATCH with provisional notes so they're visible on /audit/
    # without being over-filtered. Re-tier once prediction_market_agents/pm_resolver.py
    # lands + 30d of real closed-pick data accumulates.
    "pm_kalshi_signals": {
        "tier": TIER_WATCH,
        "forward_wr": None,
        "total_pnl": None,
        "closed_trades": 0,
        "notes": (
            "PROVISIONAL 2026-04-04: Kalshi event-market consensus signals. "
            "Closer pipeline broken (treats PM picks as crypto TP/SL) — no "
            "closed_picks yet. Re-tier when pm_resolver.py ships + 30d data. "
            "Fresh signals (<2h) verified."
        ),
    },
    "pm_whale_signals": {
        "tier": TIER_WATCH,
        "forward_wr": None,
        "total_pnl": None,
        "closed_trades": 0,
        "notes": (
            "PROVISIONAL 2026-04-04: Polymarket whale-wallet tracking signals. "
            "Closer pipeline broken — no closed_picks. Re-tier after pm_resolver."
        ),
    },
    "pm_high_conviction": {
        "tier": TIER_WATCH,
        "forward_wr": None,
        "total_pnl": None,
        "closed_trades": 0,
        "notes": (
            "PROVISIONAL 2026-04-04: High-conviction filtered prediction-market "
            "picks. Closer pipeline broken — no closed_picks. Re-tier after "
            "pm_resolver."
        ),
    },
    "prediction_market_consensus": {
        "tier": TIER_WATCH,
        "forward_wr": None,
        "total_pnl": None,
        "closed_trades": 0,
        "notes": (
            "PROVISIONAL 2026-04-04: Cross-PM consensus aggregator. "
            "Closer pipeline broken — no closed_picks. Re-tier after pm_resolver."
        ),
    },
    "polymarket_signals": {
        "tier": TIER_WATCH,
        "forward_wr": None,
        "total_pnl": None,
        "closed_trades": 0,
        "notes": (
            "PROVISIONAL 2026-04-04: Polymarket momentum-agent signals. "
            "Currently 0 active picks — system dormant. Closer pipeline broken."
        ),
    },

    # --- WATCH (mixed or insufficient data) ---
    # NOTE: 2026-04-29 — `kimi` static UNTRUSTED entry deleted (formerly:
    # 38.5% WR / 270 trades / -219 total_pnl, last edited 2026-03-15).
    # Lifetime stats drowned the recent EQUITY 30d edge (WR 79%, PF 7.4,
    # n=82, +304% sum) and forced 6 of 7 dormant S-tier EQUITY strategies
    # (all 100% kimi-sourced) to zero active picks. Static-deletion lets
    # `get_trust("kimi")` fall back to TIER_WATCH (1.0x vote, defaults at
    # SYSTEM_TRUST.get fallback in line ~577 below) and lets
    # `get_dynamic_system_tier` recompute from closed_picks each run.
    # See:
    #   - reports/kimi_riseoftheclaw_promotion_diagnosis_2026_04_29.md
    #   - Phase 2-B EQUITY panel 9/9 unanimous
    #   - PR companion: audit_trail/quality_gates.py
    #     `_NC_SCORE_EXEMPT_SOURCES` += "kimi_riseoftheclaw"
    # Documented behavior in docs/CHATWITHIT.md:4234 already asserts
    # `get_tier("kimi") == "WATCH"` (this restores doc-consistency).
    "crypto_signal_engine": {
        "tier": TIER_WATCH,
        "forward_wr": None,
        "total_pnl": None,
        "closed_trades": 1,
        "notes": "Hourly scans, mixed results. Too few closed trades to evaluate.",
    },
    "coinglass": {
        "tier": TIER_WATCH,
        "forward_wr": None,
        "total_pnl": None,
        "closed_trades": 0,
        "notes": "3 active picks, no closures. Barely generating signals.",
    },
    "breakout_b": {
        "tier": TIER_WATCH,
        "forward_wr": None,
        "total_pnl": None,
        "closed_trades": 0,
        "notes": "8 open picks, no closures yet.",
    },
    "ml_crypto_pred": {
        "tier": TIER_WATCH,
        "forward_wr": None,
        "total_pnl": None,
        "closed_trades": 0,
        "notes": "28 open picks, 1857 model zoo. Never retrained. Theater until proven otherwise.",
    },
    "smart_money": {
        "tier": TIER_WATCH,
        "forward_wr": None,
        "total_pnl": 0,
        "closed_trades": 0,
        "notes": "Smart Money Intelligence — Finnhub analyst + insider sentiment for 12 equities. New system, WATCH tier until proven.",
    },
    "kol_consensus": {
        "tier": TIER_WATCH,
        "forward_wr": None,
        "total_pnl": 0,
        "closed_trades": 0,
        "notes": "KOL consensus signal — weighted multi-platform analyst agreement (Twitter, YouTube, Telegram, Substack, NewsAPI). WATCH until forward-validated.",
    },
    "quan_engine": {
        "tier": TIER_WATCH,
        "forward_wr": None,
        "total_pnl": None,
        "closed_trades": 0,
        "notes": "3 picks only. Near-dead.",
    },
    "chatgpt_combined": {
        "tier": TIER_WATCH,
        "forward_wr": None,
        "total_pnl": None,
        "closed_trades": 0,
        "notes": "MavilimW + Range Filter + Cyberpunk + Volume. New, no closed trades. Watching.",
    },

    # --- UNTRUSTED (losing money) ---
    "crypto_ml_edge": {
        "tier": TIER_UNTRUSTED,
        "forward_wr": 0.333,
        "total_pnl": -9.08,
        "closed_trades": 21,
        "notes": "33.3% WR. Barely above coin flip.",
    },
    "paper_trading": {
        "tier": TIER_UNTRUSTED,
        "forward_wr": 0.382,
        "total_pnl": -124.45,
        "closed_trades": 34,
        "notes": "Heavy losses. Do not trust in conflicts.",
    },
    "claude_gainer_ml": {
        "tier": TIER_UNTRUSTED,
        "forward_wr": None,
        "total_pnl": None,
        "closed_trades": 0,
        "notes": "AUC 0.537 (random). Useless.",
    },

    # --- BANNED (catastrophically bad, exclude from consensus) ---
    "ml_bg_a": {
        "tier": TIER_BANNED,
        "forward_wr": 0.053,
        "total_pnl": -62.49,
        "closed_trades": 19,
        "notes": "System A Filter. 5.3% WR. Fired SELL at F&G=11. Always wrong at extremes.",
    },
    "ml_bg_b": {
        "tier": TIER_BANNED,
        "forward_wr": 0.053,
        "total_pnl": -64.15,
        "closed_trades": 19,
        "notes": "System B Regime. 5.3% WR. Same catastrophic failure as System A.",
    },
    "ml_bg_c": {
        "tier": TIER_BANNED,
        "forward_wr": 0.0,
        "total_pnl": -5.89,
        "closed_trades": 5,
        "notes": "System C DeepLearn. 0% WR. seq_len bug (trained 200, inferred 60). Garbage outputs.",
    },
    "ml_bg_ensemble": {
        "tier": TIER_BANNED,
        "forward_wr": 0.0,
        "total_pnl": -36.98,
        "closed_trades": 8,
        "notes": "Ensemble of System A+B. Amplified both failures. 0% WR.",
    },
    "predictions": {
        "tier": TIER_BANNED,
        "forward_wr": None,
        "total_pnl": 0,
        "closed_trades": 1,
        "notes": "Dead since Mar 2 2026. No functioning workflow. Only 1 consensus pick total. ADA -71%, LTC -46%, SOL -35% on stale picks. Banned Mar 16 2026.",
    },

    # --- BANNED (added 2026-03-15 audit — proven losers polluting consensus) ---
    "multi_asset": {
        "tier": TIER_BANNED,
        "forward_wr": 0.258,
        "total_pnl": None,
        "closed_trades": 80,
        "notes": "25.8% WR, 80 trades, PF 0.28. Blocked 2026-03-15.",
    },
    "crypto_winners": {
        "tier": TIER_BANNED,
        "forward_wr": 0.396,
        "total_pnl": None,
        "closed_trades": 48,
        "notes": "39.6% WR, 48 trades, PF 0.30. Blocked 2026-03-15.",
    },

    # --- BANNED (added 2026-03-18 audit — 8,457 closed picks forward test data) ---
    "rapid_fire": {
        "tier": TIER_BANNED,
        "forward_wr": 0.25,
        "total_pnl": -429.0,
        "closed_trades": 152,
        "notes": "152 trades, 25% WR, PF 0.34, -429% PnL. Banned 2026-03-18.",
    },
    "stocks_competition": {
        "tier": TIER_BANNED,
        "forward_wr": 0.264,
        "total_pnl": None,
        "closed_trades": 174,
        "notes": "174 trades, 26.4% WR. Banned 2026-03-18.",
    },
    "fast_stocks_competition": {
        "tier": TIER_BANNED,
        "forward_wr": 0.12,
        "total_pnl": None,
        "closed_trades": 50,
        "notes": "50 trades, 12% WR. Banned 2026-03-18.",
    },
    "mercury2_fast": {
        "tier": TIER_BANNED,
        "forward_wr": 0.25,
        "total_pnl": None,
        "closed_trades": 15,
        "notes": "15 trades, 25% WR, PF 0.02. Banned 2026-03-18.",
    },
    "claude_gainer_ml_perf": {
        "tier": TIER_BANNED,
        "forward_wr": 0.0,
        "total_pnl": None,
        "closed_trades": 10,
        "notes": "10 trades, 0% WR. Banned 2026-03-18.",
    },
    "kimi_signal_tracking": {
        "tier": TIER_BANNED,
        "forward_wr": 0.375,
        "total_pnl": -90.0,
        "closed_trades": 48,
        "notes": "48 trades, 37.5% WR, -90% PnL. Banned 2026-03-18.",
    },
    "alpha_engine_fast": {
        "tier": TIER_UNTRUSTED,
        "forward_wr": 0.446,
        "total_pnl": -96.0,
        "closed_trades": 312,
        "notes": "312 trades, 44.6% WR, PF 0.74, -96% PnL. Untrusted 2026-03-18.",
    },

    # --- SANDBOX (new research-backed strategies, added 2026-03-19) ---
    "beta_adjusted_residual_momentum": {
        "tier": TIER_WATCH,
        "forward_wr": None,
        "total_pnl": None,
        "closed_trades": 0,
        "notes": "Liu & Tsyvinski RFS — CAPM residual momentum. SANDBOX 0.40 weight until proven.",
    },
    "stablecoin_flow_momentum": {
        "tier": TIER_WATCH,
        "forward_wr": None,
        "total_pnl": None,
        "closed_trades": 0,
        "notes": "Stablecoin supply flow as leading indicator. SANDBOX 0.40 weight until proven.",
    },
    "disposition_effect_contrarian": {
        "tier": TIER_WATCH,
        "forward_wr": None,
        "total_pnl": None,
        "closed_trades": 0,
        "notes": "Kaustia 2010 JFE — contrarian against disposition bias. SANDBOX 0.40 weight until proven.",
    },
    "cross_sectional_reversal": {
        "tier": TIER_WATCH,
        "forward_wr": None,
        "total_pnl": None,
        "closed_trades": 0,
        "notes": "Short-term mean reversion, -0.6 corr with momentum. SANDBOX 0.40 weight until proven.",
    },
    "token_unlock_event_short": {
        "tier": TIER_WATCH,
        "forward_wr": None,
        "total_pnl": None,
        "closed_trades": 0,
        "notes": "Keyrock study — short before cliff unlocks (>2.5% supply). SANDBOX 0.40 weight until proven.",
    },
    "btc_power_law_deviation": {
        "tier": TIER_WATCH,
        "forward_wr": None,
        "total_pnl": None,
        "closed_trades": 0,
        "notes": "Giovanni Santostasi power-law corridor. SANDBOX 0.40 weight until proven.",
    },
    "nvm_metcalfe_valuation": {
        "tier": TIER_WATCH,
        "forward_wr": None,
        "total_pnl": None,
        "closed_trades": 0,
        "notes": "Metcalfe NVM ratio — network value vs active addresses. SANDBOX 0.40 weight until proven.",
    },
    "eth_gas_fee_reversal": {
        "tier": TIER_WATCH,
        "forward_wr": None,
        "total_pnl": None,
        "closed_trades": 0,
        "notes": "ETH gas fee spike reversal — high fees = peak activity = sell. SANDBOX 0.40 weight until proven.",
    },
    "okx_top_trader_consensus": {
        "tier": TIER_WATCH,
        "forward_wr": None,
        "total_pnl": None,
        "closed_trades": 0,
        "notes": "OKX verified top trader long/short ratio. SANDBOX 0.45 weight (verified traders).",
    },
    "binance_crowd_contrarian": {
        "tier": TIER_WATCH,
        "forward_wr": None,
        "total_pnl": None,
        "closed_trades": 0,
        "notes": "Fade Binance retail crowd when extreme skew. SANDBOX 0.40 weight until proven.",
    },
    "cme_cot_positioning": {
        "tier": TIER_WATCH,
        "forward_wr": None,
        "total_pnl": None,
        "closed_trades": 0,
        "notes": "CME COT institutional positioning z-score. SANDBOX 0.40 weight until proven.",
    },
    "weekly_oi_change_momentum": {
        "tier": TIER_WATCH,
        "forward_wr": None,
        "total_pnl": None,
        "closed_trades": 0,
        "notes": "OI surge + flat price = imminent breakout signal. SANDBOX 0.40 weight until proven.",
    },
    "miner_capitulation_recovery": {
        "tier": TIER_WATCH,
        "forward_wr": None,
        "total_pnl": None,
        "closed_trades": 0,
        "notes": "Hash ribbon miner capitulation recovery. SANDBOX 0.40 weight until proven.",
    },
    "gainer_auto_promote": {
        "tier": TIER_WATCH,
        "forward_wr": None,
        "total_pnl": None,
        "closed_trades": 0,
        "notes": "Auto-promotes top 24h Binance gainers. SANDBOX 0.35 weight (reactive, not predictive).",
    },
}

# Aliases for system name normalization
SYSTEM_ALIASES = {
    "system_f": "claws_of_doom",
    "system_f_clawsofdoom": "claws_of_doom",
    "ml_battleground_system_f": "claws_of_doom",
    "ml_bg_system_f": "claws_of_doom",
    "system_a": "ml_bg_a",
    "system_b": "ml_bg_b",
    "system_c": "ml_bg_c",
    "filter": "ml_bg_a",
    "regime": "ml_bg_b",
    "deeplearn": "ml_bg_c",
    "battleground_dna": "battleground",
    "battleground_arena": "battleground",
    "mega_mutation_master": "mega_mutation",
    "cross_aggregation": "cross_system_consensus",
    "fc_crypto_pro": "cross_system_consensus",
    # "super_signals" is now its own PROVEN entry — no longer aliased to cross_system_consensus
    "prop_firm": "predictions",
    "stocks_comp": "predictions",
    "kimi_riseoftheclaw": "kimi",
    "rise_of_the_claw": "kimi",
    # "alpha_engine_fast" is now its own UNTRUSTED entry — no longer aliased to alpha_engine
    "signal_engine": "crypto_signal_engine",
    "chatgpt_combined_v1": "chatgpt_combined",
    "mavilimw_range_filter": "chatgpt_combined",
    "ml_bg_system_c": "ml_bg_c",
    "multi_asset_institutional": "multi_asset",
}


def normalize_system_name(name: str) -> str:
    """Normalize system name to canonical form."""
    key = name.lower().strip().replace(" ", "_").replace("-", "_")
    return SYSTEM_ALIASES.get(key, key)


def get_trust(system_name: str) -> dict:
    """Get trust info for a system. Returns WATCH tier for unknown systems."""
    canonical = normalize_system_name(system_name)
    return SYSTEM_TRUST.get(canonical, {
        "tier": TIER_WATCH,
        "forward_wr": None,
        "total_pnl": None,
        "closed_trades": 0,
        "notes": f"Unknown system '{system_name}'. Defaulting to WATCH.",
    })


def get_tier(system_name: str) -> str:
    """Get trust tier string for a system."""
    return get_trust(system_name)["tier"]


def get_multiplier(system_name: str) -> float:
    """Get scoring multiplier for a system."""
    tier = get_tier(system_name)
    return TIER_MULTIPLIERS.get(tier, 1.0)


def get_vote_weight(system_name: str) -> float:
    """Get consensus vote weight for a system."""
    tier = get_tier(system_name)
    return TIER_VOTE_WEIGHTS.get(tier, 1.0)


def resolve_conflict(systems_long: list[str], systems_short: list[str]) -> tuple[str, str, float]:
    """
    Resolve a symbol-level conflict between LONG and SHORT systems.

    Returns:
        (winning_direction, reason, confidence_delta)
    """
    long_weight = sum(get_vote_weight(s) for s in systems_long)
    short_weight = sum(get_vote_weight(s) for s in systems_short)

    # Get best system on each side
    best_long = max(systems_long, key=lambda s: get_multiplier(s)) if systems_long else None
    best_short = max(systems_short, key=lambda s: get_multiplier(s)) if systems_short else None

    best_long_tier = get_tier(best_long) if best_long else TIER_WATCH
    best_short_tier = get_tier(best_short) if best_short else TIER_WATCH

    total = long_weight + short_weight
    if total == 0:
        return "SKIP", "All systems banned", 0.0

    long_pct = long_weight / total
    short_pct = short_weight / total

    if long_weight > short_weight * 1.5:
        return "LONG", f"Trust-weighted {long_pct:.0%} LONG (anchored by {best_long} [{best_long_tier}])", long_pct - 0.5
    elif short_weight > long_weight * 1.5:
        return "SHORT", f"Trust-weighted {short_pct:.0%} SHORT (anchored by {best_short} [{best_short_tier}])", short_pct - 0.5
    else:
        return "CONTESTED", f"Split {long_pct:.0%}/{short_pct:.0%} — LONG anchor: {best_long} [{best_long_tier}], SHORT anchor: {best_short} [{best_short_tier}]", 0.0


def annotate_conflict_for_dashboard(symbol: str, long_systems: list[str], short_systems: list[str]) -> dict:
    """
    Generate a conflict annotation dict for the audit dashboard.
    Replaces the current binary has_conflict=True with actionable info.
    """
    direction, reason, confidence = resolve_conflict(long_systems, short_systems)

    return {
        "symbol": symbol,
        "has_conflict": True,
        "recommended_direction": direction,
        "resolution_reason": reason,
        "confidence_delta": round(confidence, 3),
        "long_systems": [{"name": s, "tier": get_tier(s), "weight": get_vote_weight(s)} for s in long_systems],
        "short_systems": [{"name": s, "tier": get_tier(s), "weight": get_vote_weight(s)} for s in short_systems],
    }


# ---------------------------------------------------------------------------
# Phase 1: Dynamic Trust Tier Computation (Mar 16 2026)
# ---------------------------------------------------------------------------
# Loads performance data from JSON files and computes trust tiers dynamically
# instead of relying solely on hardcoded SYSTEM_TRUST entries.

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

# Performance data sources (checked in order)
_PERF_SOURCES = [
    "alpha_engine/data/strategy_performance.json",
    "audit_trail/data/dashboard_payload.json",
]

# Closed picks paths for system-level WR computation
_SYSTEM_CLOSED_PICKS = {
    "mercury2":       "mercury2/data/closed_picks.json",
    "alpha_engine":   "alpha_engine/data/closed_picks.json",
    "battleground":   "battleground/data/closed_picks.json",
    "claws_of_doom":  "ml_battleground/system_f_clawsofdoom/data/closed_picks.json",
    "kimi":           "KIMI_RISEOFTHECLAW/data/closed_picks.json",
    "crypto_ml_edge": "crypto_ml_edge/data/closed_picks.json",
    "paper_trading":  "paper_trading/data/closed_picks.json",
    "ml_bg_a":        "ml_battleground/system_a_filter/data/closed_picks.json",
    "ml_bg_b":        "ml_battleground/system_b_regime/data/closed_picks.json",
    "ml_bg_c":        "ml_battleground/system_c_deeplearn/data/closed_picks.json",
    "coinglass_strategies": "coinglass_strategies/data/closed_picks.json",
    "genome":         "genome/data/closed_picks.json",
    "mega_mutation":  "genome/data/mega_mutation_closed.json",
}

# Cache for dynamic performance data (loaded once per aggregator run)
_dynamic_perf_cache: Optional[Dict] = None


def _compute_tier_from_stats(win_rate: float, closed_trades: int) -> str:
    """
    Compute trust tier from win rate and trade count.

    Thresholds (Phase 1 — Mar 16 2026):
      BANNED:     WR < 50% AND 30+ trades → 0.0x vote (blocked from consensus)
      UNTRUSTED:  WR < 50% AND 10-29 trades → 0.3x vote (demoted)
      UNTRUSTED:  WR 50-55% AND 30+ trades → 0.3x vote (marginal, demoted)
      WATCH:      < 10 trades → 1.0x vote (insufficient data)
      WATCH:      WR 50-55% AND 10-29 trades → 1.0x vote (could go either way)
      RELIABLE:   WR 55-65% AND 10+ trades → 1.5x vote (normal+)
      PROVEN:     WR > 65% AND 30+ trades → 2.0x vote (promoted)
    """
    if closed_trades < 10:
        return TIER_WATCH  # Insufficient data

    if win_rate < 0.50:
        if closed_trades >= 30:
            return TIER_BANNED    # Proven loser with statistical significance — zero weight
        return TIER_UNTRUSTED     # Likely loser, small sample — 0.3x weight

    if win_rate < 0.55:
        if closed_trades >= 30:
            return TIER_UNTRUSTED  # Marginal, demoted weight
        return TIER_WATCH          # Could go either way

    if win_rate < 0.65:
        return TIER_RELIABLE       # Decent performance

    # WR >= 65%
    if closed_trades >= 30:
        return TIER_PROVEN         # Statistically significant winner
    return TIER_RELIABLE           # Good WR but small sample


def load_dynamic_performance() -> Dict[str, Dict]:
    """
    Load performance data from all available sources.

    Returns dict of system_name -> {win_rate, closed_trades, total_pnl, computed_tier}.
    Merges strategy-level data (from alpha_engine) into system-level aggregates,
    and loads system-level closed_picks for direct WR computation.
    """
    global _dynamic_perf_cache
    if _dynamic_perf_cache is not None:
        return _dynamic_perf_cache

    perf: Dict[str, Dict] = {}

    # 1. Load strategy-level performance (alpha_engine strategies)
    for src in _PERF_SOURCES:
        src_path = _REPO_ROOT / src
        if not src_path.exists():
            continue
        try:
            data = json.loads(src_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                for strat_name, stats in data.items():
                    if not isinstance(stats, dict):
                        continue
                    wr = stats.get("win_rate", stats.get("forward_wr"))
                    closed = stats.get("closed_picks", stats.get("closed_trades", 0))
                    if wr is not None and closed is not None:
                        perf[f"strategy:{strat_name}"] = {
                            "win_rate": float(wr),
                            "closed_trades": int(closed),
                            "total_pnl_pct": stats.get("total_pnl_pct", stats.get("total_pnl", 0)),
                            "source": src,
                        }
        except (json.JSONDecodeError, OSError):
            continue

    # 2. Load system-level closed picks for direct WR computation
    for sys_name, rel_path in _SYSTEM_CLOSED_PICKS.items():
        closed_path = _REPO_ROOT / rel_path
        if not closed_path.exists():
            continue
        try:
            closed_picks = json.loads(closed_path.read_text(encoding="utf-8"))
            if not isinstance(closed_picks, list) or len(closed_picks) < 1:
                continue
            total = len(closed_picks)
            wins = sum(
                1 for c in closed_picks
                if c.get("status", "").upper() in ("WON", "WIN", "CLOSED_TP")
                or c.get("exit_reason", "").lower() in ("take_profit", "tp_hit")
                or (c.get("pnl_pct", c.get("net_pnl_pct", 0)) or 0) > 0
            )
            wr = wins / total if total > 0 else 0
            total_pnl = sum(float(c.get("pnl_pct", c.get("net_pnl_pct", 0)) or 0) for c in closed_picks)
            perf[f"system:{sys_name}"] = {
                "win_rate": round(wr, 4),
                "closed_trades": total,
                "total_pnl_pct": round(total_pnl, 4),
                "source": rel_path,
            }
        except (json.JSONDecodeError, OSError):
            continue

    # 3. Compute dynamic tier for each entry
    for key, stats in perf.items():
        stats["computed_tier"] = _compute_tier_from_stats(
            stats["win_rate"], stats["closed_trades"]
        )

    _dynamic_perf_cache = perf
    return perf


def get_dynamic_system_tier(system_name: str) -> Dict:
    """
    Get the trust tier for a system, using dynamic performance data when available.

    Priority:
      1. Dynamic performance data (from closed_picks / strategy_performance.json)
      2. Static SYSTEM_TRUST registry (hardcoded from manual audits)
      3. Default WATCH tier for unknown systems

    Returns dict with: tier, vote_weight, multiplier, source, win_rate, closed_trades
    """
    canonical = normalize_system_name(system_name)
    perf = load_dynamic_performance()

    # Check dynamic system-level data first
    sys_key = f"system:{canonical}"
    if sys_key in perf:
        stats = perf[sys_key]
        computed_tier = stats["computed_tier"]

        # Static registry can ONLY upgrade a dynamic BANNED to UNTRUSTED if
        # there's a strong reason (e.g. profitable despite low WR due to R:R).
        # Never let static override a dynamic BANNED with PROVEN/RELIABLE.
        static = SYSTEM_TRUST.get(canonical)
        if static and computed_tier == TIER_BANNED:
            static_tier = static.get("tier", TIER_WATCH)
            # Allow mercury2-style systems: low WR but profitable
            if static_tier in (TIER_RELIABLE, TIER_PROVEN) and (static.get("total_pnl") or 0) > 0:
                computed_tier = TIER_UNTRUSTED  # Promote from BANNED to UNTRUSTED (still demoted)

        return {
            "tier": computed_tier,
            "vote_weight": TIER_VOTE_WEIGHTS.get(computed_tier, 1.0),
            "multiplier": TIER_MULTIPLIERS.get(computed_tier, 1.0),
            "source": "dynamic",
            "win_rate": stats["win_rate"],
            "closed_trades": stats["closed_trades"],
            "total_pnl_pct": stats.get("total_pnl_pct", 0),
        }

    # Fall back to static registry
    static = SYSTEM_TRUST.get(canonical)
    if static:
        tier = static["tier"]
        return {
            "tier": tier,
            "vote_weight": TIER_VOTE_WEIGHTS.get(tier, 1.0),
            "multiplier": TIER_MULTIPLIERS.get(tier, 1.0),
            "source": "static_registry",
            "win_rate": static.get("forward_wr"),
            "closed_trades": static.get("closed_trades", 0),
            "total_pnl_pct": static.get("total_pnl", 0),
        }

    # Unknown system: WATCH tier with low weight
    return {
        "tier": TIER_WATCH,
        "vote_weight": TIER_VOTE_WEIGHTS.get(TIER_WATCH, 1.0),
        "multiplier": TIER_MULTIPLIERS.get(TIER_WATCH, 1.0),
        "source": "unknown_default",
        "win_rate": None,
        "closed_trades": 0,
        "total_pnl_pct": 0,
    }


def get_dynamic_vote_weight(system_name: str) -> float:
    """Get consensus vote weight using dynamic performance data."""
    return get_dynamic_system_tier(system_name)["vote_weight"]


def is_system_blocked(system_name: str) -> bool:
    """Check if a system should be completely blocked from consensus."""
    info = get_dynamic_system_tier(system_name)
    return info["tier"] == TIER_BANNED


def get_all_system_tiers() -> Dict[str, Dict]:
    """
    Get trust tiers for ALL known systems (for logging/dashboard).
    Returns dict of system_name -> tier info.
    """
    all_systems = set(SYSTEM_TRUST.keys())
    perf = load_dynamic_performance()
    for key in perf:
        if key.startswith("system:"):
            all_systems.add(key.split(":", 1)[1])

    result = {}
    for sys_name in sorted(all_systems):
        result[sys_name] = get_dynamic_system_tier(sys_name)
    return result


def reset_dynamic_cache():
    """Reset the dynamic performance cache (call at start of each aggregator run)."""
    global _dynamic_perf_cache
    _dynamic_perf_cache = None


# ---------------------------------------------------------------------------
# Phase 2: Graduated Elimination / Promotion System (Mar 16 2026)
# ---------------------------------------------------------------------------
# Formal tier system with allocation limits, rolling performance windows,
# and promotion/demotion paths. Replaces ad-hoc signal insight tiers with
# a data-driven lifecycle: S → A → B → C → ELIMINATED → (walk-forward) → C
#
# Tier definitions:
#   TIER_S_CORE:   WR >= 65%, 50+ trades, PF >= 2.0 → allocation_max 50%
#   TIER_A_VIABLE: WR >= 55%, 20+ trades, PF >= 1.5 → allocation_max 30%
#   TIER_B_PROBATION: WR >= 45%, 10+ trades        → allocation_max 15%
#   TIER_C_RECOVERY:  WR >= 35%, 5+ trades          → allocation_max 5%
#   ELIMINATED:        WR < 35% or PF < 0.5          → allocation_max 0%
# ---------------------------------------------------------------------------

ALLOC_TIER_S_CORE = "TIER_S_CORE"
ALLOC_TIER_A_VIABLE = "TIER_A_VIABLE"
ALLOC_TIER_B_PROBATION = "TIER_B_PROBATION"
ALLOC_TIER_C_RECOVERY = "TIER_C_RECOVERY"
ALLOC_TIER_ELIMINATED = "ELIMINATED"

ALLOCATION_TIERS = {
    ALLOC_TIER_S_CORE: {
        "label": "S-Core",
        "allocation_max": 0.50,
        "score_multiplier": 1.0,
        "min_wr": 0.65,
        "min_trades": 50,
        "min_pf": 2.0,
        "color": "#fbbf24",
        "description": "Elite — walk-forward proven, statistically significant alpha",
    },
    ALLOC_TIER_A_VIABLE: {
        "label": "A-Viable",
        "allocation_max": 0.30,
        "score_multiplier": 0.60,
        "min_wr": 0.55,
        "min_trades": 20,
        "min_pf": 1.5,
        "color": "#22c55e",
        "description": "Solid performer — consistent edge, moderate allocation",
    },
    ALLOC_TIER_B_PROBATION: {
        "label": "B-Probation",
        "allocation_max": 0.15,
        "score_multiplier": 0.30,
        "min_wr": 0.45,
        "min_trades": 10,
        "min_pf": None,  # No PF requirement for probation
        "color": "#f97316",
        "description": "On notice — must improve or face demotion",
    },
    ALLOC_TIER_C_RECOVERY: {
        "label": "C-Recovery",
        "allocation_max": 0.05,
        "score_multiplier": 0.05,
        "min_wr": 0.35,
        "min_trades": 5,
        "min_pf": None,
        "color": "#ef4444",
        "description": "Last chance — 10 more trades before elimination",
    },
    ALLOC_TIER_ELIMINATED: {
        "label": "Eliminated",
        "allocation_max": 0.0,
        "score_multiplier": 0.0,
        "min_wr": None,
        "min_trades": None,
        "min_pf": None,
        "color": "#64748b",
        "description": "Eliminated — zero allocation. Walk-forward re-entry possible.",
    },
}

# Promotion/demotion thresholds (rolling 20-trade window)
PROMO_DEMOTION_RULES = {
    # From TIER_B: promote to A if rolling WR > 55%
    (ALLOC_TIER_B_PROBATION, ALLOC_TIER_A_VIABLE): {"rolling_wr_min": 0.55, "rolling_pf_min": 1.5},
    # From TIER_A: demote to B if rolling WR drops below 50%
    (ALLOC_TIER_A_VIABLE, ALLOC_TIER_B_PROBATION): {"rolling_wr_max": 0.50},
    # From TIER_C: promote to B if rolling WR > 45% over 10 trades
    (ALLOC_TIER_C_RECOVERY, ALLOC_TIER_B_PROBATION): {"rolling_wr_min": 0.45, "min_window": 10},
    # From TIER_C: eliminate if 10 trades pass and WR < 35%
    (ALLOC_TIER_C_RECOVERY, ALLOC_TIER_ELIMINATED): {"rolling_wr_max": 0.35, "min_window": 10},
    # From TIER_B: demote to C if rolling WR drops below 40%
    (ALLOC_TIER_B_PROBATION, ALLOC_TIER_C_RECOVERY): {"rolling_wr_max": 0.40},
    # From TIER_S: demote to A if rolling WR drops below 60%
    (ALLOC_TIER_S_CORE, ALLOC_TIER_A_VIABLE): {"rolling_wr_max": 0.60},
    # From TIER_A: promote to S if rolling WR > 65% and PF > 2.0
    (ALLOC_TIER_A_VIABLE, ALLOC_TIER_S_CORE): {"rolling_wr_min": 0.65, "rolling_pf_min": 2.0, "min_window": 20},
}

# Persistence path for tier state (tracks current tier + trade window)
_TIER_STATE_PATH = _REPO_ROOT / "cross_aggregation" / "data" / "allocation_tiers.json"

ROLLING_WINDOW = 20  # Number of recent trades for promotion/demotion decisions


def _compute_rolling_stats(closed_picks: list, window: int = ROLLING_WINDOW) -> dict:
    """
    Compute rolling WR and PF from the most recent N closed picks.

    Returns: {rolling_wr, rolling_pf, rolling_trades, total_trades}
    """
    if not closed_picks:
        return {"rolling_wr": 0, "rolling_pf": 0, "rolling_trades": 0, "total_trades": 0}

    recent = closed_picks[-window:]  # Last N picks
    total = len(recent)
    wins = sum(
        1 for c in recent
        if c.get("status", "").upper() in ("WON", "WIN", "CLOSED_TP")
        or c.get("exit_reason", "").lower() in ("take_profit", "tp_hit")
        or (c.get("pnl_pct", c.get("net_pnl_pct", 0)) or 0) > 0
    )
    losses = total - wins

    rolling_wr = wins / total if total > 0 else 0

    # Profit factor = gross_wins / gross_losses
    gross_wins = sum(
        abs(float(c.get("pnl_pct", c.get("net_pnl_pct", 0)) or 0))
        for c in recent
        if (c.get("pnl_pct", c.get("net_pnl_pct", 0)) or 0) > 0
    )
    gross_losses = sum(
        abs(float(c.get("pnl_pct", c.get("net_pnl_pct", 0)) or 0))
        for c in recent
        if (c.get("pnl_pct", c.get("net_pnl_pct", 0)) or 0) < 0
    )
    rolling_pf = gross_wins / gross_losses if gross_losses > 0 else (10.0 if gross_wins > 0 else 0)

    return {
        "rolling_wr": round(rolling_wr, 4),
        "rolling_pf": round(rolling_pf, 4),
        "rolling_trades": total,
        "total_trades": len(closed_picks),
    }


def compute_allocation_tier(
    win_rate: float,
    closed_trades: int,
    profit_factor: float = 0,
    rolling_stats: Optional[dict] = None,
    current_tier: Optional[str] = None,
    walk_forward_validated: bool = False,
) -> dict:
    """
    Compute the allocation tier for a strategy based on its performance.

    Args:
        win_rate: Overall win rate (0-1)
        closed_trades: Total closed trades
        profit_factor: Overall profit factor
        rolling_stats: Rolling 20-trade stats from _compute_rolling_stats()
        current_tier: Current tier (for promotion/demotion logic)
        walk_forward_validated: If True, eliminated strategies can re-enter as TIER_C

    Returns:
        dict with: tier, allocation_max, score_multiplier, label, color, reason, promotion_path
    """
    # Check promotion/demotion if we have a current tier and rolling stats
    if current_tier and rolling_stats and rolling_stats.get("rolling_trades", 0) >= 5:
        new_tier = _check_promotion_demotion(current_tier, rolling_stats)
        if new_tier and new_tier != current_tier:
            tier_info = ALLOCATION_TIERS[new_tier]
            direction = "PROMOTED" if _tier_rank(new_tier) > _tier_rank(current_tier) else "DEMOTED"
            return {
                "tier": new_tier,
                "allocation_max": tier_info["allocation_max"],
                "score_multiplier": tier_info["score_multiplier"],
                "label": tier_info["label"],
                "color": tier_info["color"],
                "reason": f"{direction} from {current_tier} → {new_tier} "
                          f"(rolling {rolling_stats['rolling_trades']}t: "
                          f"WR={rolling_stats['rolling_wr']:.1%}, PF={rolling_stats['rolling_pf']:.2f})",
                "promotion_path": _get_promotion_path(new_tier),
            }

    # Walk-forward re-entry: eliminated strategies can return as TIER_C
    if current_tier == ALLOC_TIER_ELIMINATED and walk_forward_validated:
        tier_info = ALLOCATION_TIERS[ALLOC_TIER_C_RECOVERY]
        return {
            "tier": ALLOC_TIER_C_RECOVERY,
            "allocation_max": tier_info["allocation_max"],
            "score_multiplier": tier_info["score_multiplier"],
            "label": tier_info["label"],
            "color": tier_info["color"],
            "reason": "RE-ENTERED via walk-forward validation. 10-trade probation.",
            "promotion_path": _get_promotion_path(ALLOC_TIER_C_RECOVERY),
        }

    # Fresh classification (no current tier or insufficient rolling data)
    tier = _classify_from_stats(win_rate, closed_trades, profit_factor)
    tier_info = ALLOCATION_TIERS[tier]
    return {
        "tier": tier,
        "allocation_max": tier_info["allocation_max"],
        "score_multiplier": tier_info["score_multiplier"],
        "label": tier_info["label"],
        "color": tier_info["color"],
        "reason": f"Classified: WR={win_rate:.1%}, {closed_trades}t, PF={profit_factor:.2f}",
        "promotion_path": _get_promotion_path(tier),
    }


def _tier_rank(tier: str) -> int:
    """Rank tiers numerically for comparison (higher = better)."""
    return {
        ALLOC_TIER_S_CORE: 4,
        ALLOC_TIER_A_VIABLE: 3,
        ALLOC_TIER_B_PROBATION: 2,
        ALLOC_TIER_C_RECOVERY: 1,
        ALLOC_TIER_ELIMINATED: 0,
    }.get(tier, -1)


def _classify_from_stats(win_rate: float, closed_trades: int, profit_factor: float) -> str:
    """Classify a strategy into an allocation tier from raw stats."""
    if closed_trades < 5:
        return ALLOC_TIER_C_RECOVERY  # Too few trades for any confidence

    if win_rate < 0.35 or (profit_factor < 0.5 and closed_trades >= 10):
        return ALLOC_TIER_ELIMINATED

    if win_rate >= 0.65 and closed_trades >= 50 and profit_factor >= 2.0:
        return ALLOC_TIER_S_CORE

    if win_rate >= 0.55 and closed_trades >= 20 and profit_factor >= 1.5:
        return ALLOC_TIER_A_VIABLE

    if win_rate >= 0.45 and closed_trades >= 10:
        return ALLOC_TIER_B_PROBATION

    if win_rate >= 0.35 and closed_trades >= 5:
        return ALLOC_TIER_C_RECOVERY

    return ALLOC_TIER_ELIMINATED


def _check_promotion_demotion(current_tier: str, rolling_stats: dict) -> Optional[str]:
    """
    Check if a strategy should be promoted or demoted based on rolling stats.

    Returns new tier if transition should happen, None otherwise.
    """
    rwr = rolling_stats.get("rolling_wr", 0)
    rpf = rolling_stats.get("rolling_pf", 0)
    rtrades = rolling_stats.get("rolling_trades", 0)

    for (from_tier, to_tier), rules in PROMO_DEMOTION_RULES.items():
        if from_tier != current_tier:
            continue

        min_window = rules.get("min_window", 5)
        if rtrades < min_window:
            continue

        # Check demotion (rolling WR below max threshold)
        if "rolling_wr_max" in rules:
            if rwr < rules["rolling_wr_max"]:
                return to_tier

        # Check promotion (rolling WR above min threshold)
        if "rolling_wr_min" in rules:
            if rwr >= rules["rolling_wr_min"]:
                # Also check PF if required
                if "rolling_pf_min" in rules:
                    if rpf >= rules["rolling_pf_min"]:
                        return to_tier
                else:
                    return to_tier

    return None


def _get_promotion_path(tier: str) -> str:
    """Get a human-readable promotion/demotion path description."""
    paths = {
        ALLOC_TIER_S_CORE: "Maintain WR>=60% to stay. Drops below → A-Viable.",
        ALLOC_TIER_A_VIABLE: "WR>=65% + PF>=2.0 over 20t → S-Core. WR<50% → B-Probation.",
        ALLOC_TIER_B_PROBATION: "WR>=55% + PF>=1.5 → A-Viable. WR<40% → C-Recovery.",
        ALLOC_TIER_C_RECOVERY: "Last chance: 10 trades. WR>=45% → B-Probation. WR<35% → Eliminated.",
        ALLOC_TIER_ELIMINATED: "Walk-forward validation required to re-enter as C-Recovery.",
    }
    return paths.get(tier, "Unknown tier.")


def load_tier_state() -> dict:
    """Load persisted tier state from disk."""
    if _TIER_STATE_PATH.exists():
        try:
            return json.loads(_TIER_STATE_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_tier_state(state: dict):
    """Persist tier state to disk."""
    _TIER_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _TIER_STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def compute_all_allocation_tiers() -> dict:
    """
    Compute allocation tiers for all known strategies/systems.

    Loads closed picks, computes rolling stats, applies promotion/demotion,
    and returns a dict suitable for the dashboard payload.
    """
    state = load_tier_state()
    perf = load_dynamic_performance()
    result = {}

    for key, stats in perf.items():
        name = key.split(":", 1)[1] if ":" in key else key
        wr = stats.get("win_rate", 0)
        closed = stats.get("closed_trades", 0)

        # Load closed picks for rolling stats if available
        rolling = {"rolling_wr": wr, "rolling_pf": 0, "rolling_trades": closed, "total_trades": closed}

        # Try to get actual closed picks for proper rolling window
        canonical = name if not key.startswith("strategy:") else name
        rel_path = _SYSTEM_CLOSED_PICKS.get(canonical)
        if rel_path:
            closed_path = _REPO_ROOT / rel_path
            if closed_path.exists():
                try:
                    picks = json.loads(closed_path.read_text(encoding="utf-8"))
                    if isinstance(picks, list):
                        rolling = _compute_rolling_stats(picks)
                except (json.JSONDecodeError, OSError):
                    pass

        # Estimate PF from rolling stats or total PnL
        pf = rolling.get("rolling_pf", 0)
        if pf == 0 and wr > 0:
            # Rough PF estimate: PF ≈ (WR * avg_win) / ((1-WR) * avg_loss)
            # Assume avg_win ≈ avg_loss for estimation
            pf = wr / (1 - wr) if wr < 1 else 10.0

        current_tier = state.get(name, {}).get("tier")
        tier_result = compute_allocation_tier(
            win_rate=wr,
            closed_trades=closed,
            profit_factor=pf,
            rolling_stats=rolling,
            current_tier=current_tier,
        )
        tier_result["rolling_stats"] = rolling
        result[name] = tier_result

        # Update state
        state[name] = {"tier": tier_result["tier"], "last_updated": "auto"}

    save_tier_state(state)
    return result
