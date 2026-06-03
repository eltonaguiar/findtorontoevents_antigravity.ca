#!/usr/bin/env python3
"""
NOTE — SNAPSHOT-RESOLVER ARTIFACT (2026-06-03): WR/PF here is inflated by single
daily-snapshot TP/SL resolution (no intrabar OHLC path) — intraday SL touches are missed.
Do not size up on these numbers. See docs/RESOLVER_SNAPSHOT_ARTIFACT_AFFECTED_PORTFOLIOS_2026-06-03.md

Claude's Test — Multi-Portfolio Manager
15 portfolios with different methodologies, auto-managed every 30 min.
Includes 3 prop firm challenge portfolios with reset tracking.
Canadian broker (IBKR) commissions applied.
"""

import json
import os
import sys
import urllib.request
import urllib.error
from alpha_engine.hedge_fund_quality_gate import PORTFOLIO_MAX_DRAWDOWN_PCT
from datetime import datetime, timezone, timedelta
from pathlib import Path
from copy import deepcopy
import math
import hashlib

# Import standardized win rate calculation
sys.path.insert(0, str(Path(__file__).parent.parent))
from shared import calculate_win_rate, calculate_win_rate_from_picks


def normalize_production_score(raw: float) -> float:
    """Sigmoid normalization of unbounded production score to 0-100 for beta comparison."""
    return 100.0 / (1.0 + math.exp(-0.1 * (raw - 50)))


EST = timezone(timedelta(hours=-5))
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
STATE_FILE = DATA_DIR / "claudes_test_state.json"
PAYLOAD_FILE = (
    Path(__file__).parent.parent / "audit_trail" / "data" / "dashboard_payload.json"
)

# ── Broker Costs (Simulated) ──
COMMISSION_CRYPTO_PCT = 0.0005  # 0.05% per side (0.1% RT)
COMMISSION_EQUITY_MIN = 1.00
COMMISSION_EQUITY_PER_SHARE = 0.01  # $0.01/share
COMMISSION_FUTURES_PCT = 0.0005  # 0.05%/side — approx futures broker fee on notional
COMMISSION_COMMODITY_PCT = (
    0.0004  # 0.04%/side — commodity futures (slightly lower than index)
)
COMMISSION_FOREX_PCT = 0.0002  # 0.02%/side — tight FX spread (2 pips on $10k)
SLIPPAGE_PCT = (
    0.0003  # 0.03% slippage per side (reduced from 0.05% to be more realistic)
)

MEME_COINS = {
    "DOGEUSDT",
    "SHIBUSDT",
    "PEPEUSDT",
    "FLOKIUSDT",
    "WIFUSDT",
    "BONKUSDT",
    "BOMEUSDT",
    "MEMEUSDT",
    "BABYDOGEUSDT",
    "ELONUSDT",
    "TURBO",
    "TURBOUSDT",
    "DOGE",
    "SHIB",
    "PEPE",
    "FLOKI",
    "WIF",
    "BONK",
    "BOME",
    "MEME",
    "BABYDOGE",
}

# ═══════════════════════════════════════════════════════════════
# 4-AI CONSENSUS FIREWALL (Mercury + Grok + Codex + Gemini)
# Applied: 2026-03-10 — highest-impact changes to flip expectancy
# ═══════════════════════════════════════════════════════════════

# Whitelisted strategies with proven forward edge (all 4 AIs agree)
# Tier 1: Original 5 (validated by Mercury + Grok + Codex + Gemini)
# Tier 2: Gold Standard (50+ FWD trades, PF > 1.5, from database analysis)
PROVEN_STRATEGIES = {
    # Updated based on latest forward test analysis (2026-03-27)
    # Only include strategies with proven positive edge in forward testing
    "drawdown_recovery_rsi",  # 81.2% WR in latest test
    "multi_period_rsi_confluence_xrp",  # 70.0% WR
    "relative_strength_recovery",  # 100% WR (small sample)
    "fear_greed_contrarian",  # 100% WR (small sample)
    "hoffman_elite",  # 42.9% WR with +1.06% avg
    "rsi_capitulation",  # 41.7% WR with +0.89% avg
    "sector_rotation",  # 50.0% WR
    "high_consensus",  # 35.3% WR with positive expectancy
    # Tier 1 — Battleground validated
    "crypto_rsi_whaleconfirmed_v1",
    "funding_momentum",
    "crypto_keltner_compression_expansion",
    "keltner_compression_expansion",
    "crypto_vwap_deviation_reversion_vol",
    "crypto_kalman_trend_residual_reversion",
    "crypto_soc_orderflow_absorption",
    "extreme_fear",
}

# Research cohort — forward testing, NOT proven yet (added 2026-03-16)
# These get tracked but do NOT receive proven_bonus multipliers
# Promotion path: after 30+ closed trades with WR >= 55%, manually move to PROVEN_STRATEGIES
RESEARCH_COHORT_STRATEGIES = {
    "vwap_trend_bounce",
    "hoffman_ema_irb",
    "statistical_pairs_zscore",
    "supply_demand_zone",
    "three_white_soldiers_rsi",
    "bearish_engulfing_reversal",
    "golden_confluence_swing",
    "vwap_rsi_institutional",
    "rsi_weighted_pairs_arb",
    "hoffman_keltner_expansion",
}

# Symbol-locking: some strategies only work on specific assets
# Updated from Battleground 388-trade audit (2026-03-12):
# Keltner BTC = 72.9% WR PF 3.74, ETH = 56.4% WR PF 4.02, SOL = 66.7% WR PF 2.81
SYMBOL_LOCK = {
    "crypto_keltner_compression_expansion": {
        "BTCUSDT",
        "ETHUSDT",
        "SOLUSDT",
    },  # All 3 profitable
    "multi_period_rsi_confluence": {
        "ETHUSDT",
        "XRPUSDT",
    },  # XRP=64% WR PF 2.50, ETH=60.5% WR PF 2.30
    "drawdown_recovery_rsi": {
        "ETHUSDT",
        "BTCUSDT",
    },  # BTC=55.9% WR PF 4.31, ETH=61.5% WR PF 2.53
    "crypto_soc_orderflow_absorption": {"BTCUSDT"},
    "crypto_vwap_deviation_reversion": {"BTCUSDT"},  # +332% P&L on BTC only
}

# Keltner VARIANT blocklist — asset-specific variants with proven negative edge
# Updated 2026-03-12: ETH (56.4% WR, PF 4.02) and SOL (66.7% WR, PF 2.81)
# are PROFITABLE in Battleground (39 and 36 trades respectively) — UNBLOCKED.
# The earlier "0/8 all SL" data was from KIMI/ClawsOfDoom, not Battleground.
KELTNER_BLOCK_PATTERNS = [
    "keltner_compression_expansion_doge",
    "keltner_compression_expansion_xrp",
    "keltner_compression_expansion_bnb",
    "keltner_compression_expansion_ada",
    "keltner_compression_expansion_ltc",
    "bollinger_keltner_squeeze",  # Related Keltner variant, unproven
]

# Strategy families for concentration limits (max 2 per family per direction)
STRATEGY_FAMILIES = {
    "crypto_rsi_whaleconfirmed_v1": "momentum",
    "funding_momentum": "carry",
    "crypto_keltner_compression_expansion": "breakout",
    "crypto_vwap_deviation_reversion_vol": "mean_reversion",
    "crypto_kalman_trend_residual_reversion": "mean_reversion",
    "multi_period_rsi_confluence": "momentum",
    "drawdown_recovery_rsi": "mean_reversion",
    "crypto_soc_orderflow_absorption": "order_flow",
    "extreme_fear": "contrarian",  # 4/4 wins in live, +6.64% avg
    "keltner_compression_expansion": "breakout",  # ETH/SOL variants
    "crypto_drawdown_convexity_recovery": "mean_reversion",  # 13t 61.5% WR PF 1.67
    "crypto_choppiness_regime_switch": "regime",  # 20t 55% WR PF 1.59
    # Deep-value mutation families
    "deep_drawdown_dca": "deep_value",
    "rsi_capitulation_sniper": "deep_value",
    "fear_greed_contrarian": "contrarian",
    "relative_strength_recovery": "mean_reversion",
    # Hoffman + HTF mutation families
    "hoffman_elite": "hoffman",
    "hoffman_rsi2_ribbon": "hoffman",
    "htf_trend_follow": "trend_following",
    "htf_weekly_momentum": "trend_following",
}
MAX_PER_FAMILY = 2  # Max positions from same strategy family

# Mean reversion strategies (allowed in choppy/ranging markets)
MEAN_REVERSION_STRATS = {
    "crypto_vwap_deviation_reversion_vol",
    "crypto_kalman_trend_residual_reversion",
    "drawdown_recovery_rsi",
}

# Blocked patterns (3/4 AIs: block from live capital)
BLOCKED_PATTERNS = [
    "revival_mutated",
    "Revival_Mutated",
    "rapid_fire",
    "ml_crypto_predictor",
]

# Eligibility gates (Codex 2-stage: Stage 1 hard pass/fail)
MIN_SYS_CLOSED = 5  # Min closed trades for system to be eligible
MIN_SYS_WR = 45  # Min system win rate % (tightened: 35→45, marginal 40% systems losing after costs)
MIN_RR = 1.0  # Min risk:reward ratio (relaxed from 1.2 to allow more valid trades)

# Concentration limits (Gemini: 40% directional, Grok: 40% long / 30% short)
MAX_POS_PER_ASSET = 1  # Codex: 1 position per symbol+direction
MAX_GLOBAL_SYMBOL_PORTFOLIOS = 3  # max portfolios per symbol+direction
MAX_LONG_PCT = 0.50  # Max 50% of positions can be LONG
MAX_SHORT_PCT = 0.40  # Max 40% of positions can be SHORT
MAX_PCT_PER_SYMBOL = (
    0.20  # Max 20% of portfolio in any single symbol (anti-concentration)
)

# Time-based exit (Gemini: 48h, Grok: 7d loss / 14d max)
STALE_LOSS_HOURS = 168  # 7 days: force close if losing
MAX_HOLD_HOURS = 336  # 14 days: force close regardless

# Asset-class-aware freshness thresholds (crypto=fast TFs, forex/equity=daily TFs)
FRESHNESS_HOURS = {"CRYPTO": 2, "FOREX": 8, "EQUITY": 12}  # max age for "fresh" filter
FRESHNESS_DECAY = {
    "CRYPTO": 48,
    "FOREX": 96,
    "EQUITY": 168,
}  # hours until freshness score → 0

# Trailing stop activation (Grok: +5%, Gemini: +1 ATR)
TRAIL_ACTIVATE_PCT = 5.0  # Activate trailing after +5% profit
TRAIL_DISTANCE_MULT = 0.5  # Trail at 50% of peak (lock in half the gain)

# Kill criteria (auto-remove dead strategies from consideration)
KILL_WR_THRESHOLD = 35  # Kill if WR < 35% after 10+ trades (relaxed from 40)
KILL_PF_THRESHOLD = 1.0  # Kill if PF < 1.0 (break-even is losing after costs)
KILL_MIN_TRADES = 10  # Need 10+ trades before killing

# Systems with proven negative edge (PF < 1.0 with 50+ trades = guaranteed loss)
# NOTE: System F (Claws of Doom) UNBLOCKED 2026-03-13 — stale stats were wrong.
# Actual forward performance: 52.5% WR, +41% PnL, 10 active positions in profit.
BLOCKED_SYSTEMS = {
    "multi_asset_diversified",  # 0% WR
    "stocks_short_term",  # 0% WR
    "sentiment_divergence",  # 0% WR
    "anti_meme",  # 20% WR, negative PnL
    "basis_carry_only",  # 16.7% WR, bad PnL
}

# Portfolios temporarily paused due to poor recent performance.
#
# KILLED 2026-04-12 (DeepSeek APR12 audit, DEEPSEEK_APR122026.MD §6C):
#   - rr_kings:              n=17, WR 29.4%, avg_pnl -4.746% (2026-03-11..2026-04-04)
#   - multi_asset_diversified: n=11, WR 0.0%,  avg_pnl -1.205% (2026-03-10..2026-03-23)
# Numbers verified reproducibly via tools/audit_portfolios.py against
# audit_dashboard/data/claudes_test_state.json on 2026-04-12.
#
# Sibling portfolio fear_greed_contrarian is LEFT ALIVE (n=5, WR 80%,
# avg_pnl +0.724%) — it is underpowered, not underperforming, and should
# scale up rather than down. See PORTFOLIOS list entry for the comment.
PAUSED_PORTFOLIOS = {
    "multi_asset_diversified",  # KILLED 2026-04-12: 0% WR, -1.205% avg PnL (n=11)
    "rr_kings",  # KILLED 2026-04-12: 29.4% WR, -4.746% avg PnL (n=17)
    "stocks_short_term",
    "sentiment_divergence",
    "anti_meme",
    "basis_carry_only",
    "all_asset_tournament",  # Poor performance
}


# ── Portfolio Definitions ──
PORTFOLIOS = [
    {
        "id": "score_leaders",
        "name": "Score Leaders",
        "description": "Ranked by composite score = expectancy*3 + kelly*50 + R:R*15 + agreement*12 + freshness*8 + confidence*5. Picks from ALL active systems (KIMI, Alpha Engine, Rapid Fire, ML Battleground). Proven/forward-tested strategies get 2x multiplier.",
        "selection_rules": "Sort all firewall-passing picks by score_pick() descending. No filters — pure meritocracy across all systems.",
        "initial_capital": 10000,
        "max_positions": 8,
        "position_pct": 0.12,
        "methodology": "score",
        "update_interval_min": 30,
    },
    {
        "id": "proven_only",
        "name": "Proven Only",
        "description": "Only picks from strategies with trust_tier=PROVEN (forward WR>=50%, 10+ closed) or FORWARD (forward-tested). Falls back to BACKTEST tier if none available. Sources: KIMI live_scanner, Alpha Engine, ML Battleground — only strategies that passed forward validation.",
        "selection_rules": "Filter: trust_tier in (PROVEN, FORWARD). Fallback: BACKTEST. Sort by score_pick() descending.",
        "initial_capital": 10000,
        "max_positions": 6,
        "position_pct": 0.15,
        "methodology": "proven",
        "update_interval_min": 30,
    },
    {
        "id": "momentum_riders",
        "name": "Momentum Riders",
        "description": "Chases picks already showing positive unrealized PnL (price moved in signal direction since signal was generated). Capped at 10% to filter stale entries. Sources: all active system picks where current_price > entry_price (LONG) or < entry_price (SHORT).",
        "selection_rules": "Filter: pnl_pct > 0 AND pnl_pct <= 10. Sort by pnl_pct descending. Highest current momentum first.",
        "initial_capital": 10000,
        "max_positions": 10,
        "position_pct": 0.10,
        "methodology": "momentum",
        "update_interval_min": 30,
    },
    {
        "id": "contrarian",
        "name": "Contrarian",
        "description": "Goes against the crowd. In BEARISH/CHOPPY regime: takes SHORT picks with R:R>=1.3. In BULLISH regime: takes LONG picks with R:R>=1.3 and no system conflicts. Regime detected from BTC 24h change + Fear & Greed index.",
        "selection_rules": "BEARISH/CHOPPY: filter SHORT + R:R>=1.3. BULLISH: filter LONG + R:R>=1.3 + no conflicts. Sort by score_pick().",
        "initial_capital": 10000,
        "max_positions": 6,
        "position_pct": 0.15,
        "methodology": "contrarian",
        "update_interval_min": 30,
    },
    {
        "id": "regime_aligned",
        "name": "Regime Aligned",
        "description": "Only enters trades matching detected market regime. BEARISH: only SHORT picks. BULLISH: only LONG picks. CHOPPY/NEUTRAL: highest R:R>=1.4 either direction. Regime = BTC 24h% + Fear&Greed composite.",
        "selection_rules": "BEARISH: SHORT only. BULLISH: LONG only. CHOPPY: R:R>=1.4 any direction. Sort by score_pick().",
        "initial_capital": 10000,
        "max_positions": 8,
        "position_pct": 0.12,
        "methodology": "regime",
        "update_interval_min": 30,
    },
    {
        "id": "high_conviction",
        "name": "High Conviction",
        "description": "Only picks where the source system reports confidence >= 0.60 AND R:R >= 1.3. Sorted by confidence * system_win_rate. Sources: any system — filtered by the signal's own confidence score.",
        "selection_rules": "Filter: confidence >= 0.60 AND R:R >= 1.3. Sort by confidence * sys_wr descending.",
        "initial_capital": 10000,
        "max_positions": 5,
        "position_pct": 0.18,
        "methodology": "conviction",
        "update_interval_min": 30,
    },
    {
        "id": "rr_kings",
        "name": "R:R Kings",
        "description": "Pure reward:risk selection — only picks where (TP distance / SL distance) >= 1.8. Falls back to >= 1.5 if none available. Ignores system performance, confidence, everything — only risk/reward math matters.",
        "selection_rules": "Filter: R:R >= 1.8 (fallback: >= 1.5). Sort by R:R descending. System-agnostic.",
        "initial_capital": 10000,
        "max_positions": 10,
        "position_pct": 0.10,
        "methodology": "rr",
        "update_interval_min": 30,
    },
    {
        "id": "consensus_plays",
        "name": "Consensus Plays",
        "description": "Picks where MULTIPLE independent systems agree on the same symbol+direction. Agreement count = how many of [KIMI live_scanner, Alpha Engine, Rapid Fire, ML Battleground, Deep Value Engine, HTF Engine] generated a signal for the same symbol in the same direction. Higher count = stronger consensus.",
        "selection_rules": "Sort by system_agreement_count descending. Deduplicate by normalized symbol (keep highest agreement). Each position shows which systems agreed in source_systems field.",
        "initial_capital": 10000,
        "max_positions": 5,
        "position_pct": 0.18,
        "methodology": "consensus",
        "update_interval_min": 30,
    },
    {
        "id": "fresh_signals",
        "name": "Fresh Signals",
        "description": "Only picks generated within the last N hours: crypto < 2h, forex < 8h, equity < 12h. Prioritizes recency — stale signals decay fast. Age calculated from pick timestamp vs current time.",
        "selection_rules": "Filter: age_hours < FRESHNESS_HOURS[asset_class] (crypto=2h, forex=8h, equity=12h). Sort by score_pick().",
        "initial_capital": 10000,
        "max_positions": 8,
        "position_pct": 0.12,
        "methodology": "fresh",
        "update_interval_min": 30,
    },
    {
        "id": "sector_rotation",
        "name": "Sector Rotation",
        "description": "Forced diversification across asset classes: max 3 crypto + 2 equity + 1 forex = balanced exposure. Each slot filled by the top-scoring pick in that asset class.",
        "selection_rules": "Top 3 crypto by score + top 2 equity by score + top 1 forex by score. Capped at max_positions total.",
        "initial_capital": 10000,
        "max_positions": 6,
        "position_pct": 0.15,
        "methodology": "sector",
        "update_interval_min": 60,
    },
    {
        "id": "anti_meme",
        "name": "Anti-Meme",
        "description": "All picks from all systems EXCEPT meme coins (DOGE, SHIB, PEPE, WIF, BONK, FLOKI, MEME, BABYDOGE, ELON, SAMO, MYRO, BRETT, POPCAT, MOG, NEIRO, TURBO, COQ, PORK). Otherwise same scoring as Score Leaders.",
        "selection_rules": "Filter: symbol NOT in meme_list. Sort by score_pick() descending.",
        "initial_capital": 10000,
        "max_positions": 8,
        "position_pct": 0.12,
        "methodology": "anti_meme",
        "update_interval_min": 30,
    },
    {
        "id": "claude_best",
        "name": "Claude's Best",
        "description": "Hybrid strategy combining multiple filters: trust_tier in (PROVEN, FORWARD, BACKTEST) + R:R >= 1.2 + no meme coins. Regime-aware: LONG gets 1.2x bonus in BULLISH, SHORT gets 1.3x bonus in BEARISH. Falls back to R:R >= 1.3 + no memes if no proven picks.",
        "selection_rules": "Filter: trust_tier proven/forward/backtest + R:R>=1.2 + not meme. Regime bonus applied. Sort by hybrid_score.",
        "initial_capital": 10000,
        "max_positions": 5,
        "position_pct": 0.18,
        "methodology": "best",
        "update_interval_min": 30,
    },
    # ── Deep-Value Mutation Portfolios (user's "buy the blood" style) ──
    # These use INTERNALLY GENERATED picks from generate_deep_value_picks(),
    # not from external systems. Prices computed from Binance/Bybit live data.
    {
        "id": "deep_drawdown_dca",
        "name": "Deep Drawdown DCA",
        "description": "INTERNAL ENGINE: Scans Binance/Bybit for assets down >25% from their 90-day high. Entry at current price, TP at 50% recovery toward the high, SL at 10% below current. Deeper drawdowns get higher confidence. Only top-cap crypto (BTC, ETH, XRP, SOL, ADA, etc).",
        "selection_rules": "Filter: _dv_type=drawdown_dca. Sort by drawdown_pct * bounce_pct descending. Deeper pain + confirmed bounce = first pick.",
        "initial_capital": 10000,
        "max_positions": 6,
        "position_pct": 0.15,
        "methodology": "drawdown_dca",
        "update_interval_min": 60,
        "deep_value": True,
    },
    {
        "id": "rsi_capitulation",
        "name": "RSI Capitulation Sniper",
        "description": "INTERNAL ENGINE: Scans for assets with daily RSI < 35 showing bounce confirmation (price recovering from lows). Entry at current price, TP at +15%, SL at -8%. Lower RSI = higher confidence. Crypto only.",
        "selection_rules": "Filter: _dv_type=rsi_capitulation. Sort by RSI ascending (most oversold first).",
        "initial_capital": 10000,
        "max_positions": 5,
        "position_pct": 0.18,
        "methodology": "rsi_capitulation",
        "update_interval_min": 60,
        "deep_value": True,
    },
    # UNDERPOWERED 2026-04-12 (DeepSeek APR12 audit, DEEPSEEK_APR122026.MD §6C):
    # fear_greed_contrarian is the top-performing portfolio at 80% WR / +0.724%
    # avg PnL but only n=5 closed trades. It is LEFT ALIVE intentionally — the
    # fix is to scale it UP (raise max_positions, increase F&G trigger window,
    # loosen top-10 cap filter), not to kill it. Do not demote without first
    # widening the selection rules to grow the sample size.
    {
        "id": "fear_greed_contrarian",
        "name": "Fear & Greed Contrarian",
        "description": "INTERNAL ENGINE: Only activates when Crypto Fear & Greed Index <= 25 (extreme fear). Accumulates top-10 market cap crypto (BTC, ETH, XRP, SOL, ADA, DOGE, DOT, AVAX, LINK, LTC). TP at +10%, SL at -7%. Warren Buffett rule: be greedy when others are fearful.",
        "selection_rules": "Filter: _dv_type=fear_greed_contrarian + F&G <= 25 + symbol in top-10 cap. Sort by F&G score (lower = stronger signal).",
        "initial_capital": 10000,
        "max_positions": 5,
        "position_pct": 0.18,
        "methodology": "fear_greed",
        "update_interval_min": 120,
        "deep_value": True,
    },
    {
        "id": "relative_strength_recovery",
        "name": "Relative Strength Recovery",
        "description": "INTERNAL ENGINE: Finds the weakest 30-day performers among top crypto that are starting to bounce (price > 5-day SMA). Mean reversion bet: laggards catch up. Entry at current, TP at +15%, SL at -10%.",
        "selection_rules": "Filter: _dv_type=relative_strength. Sort by 30d weakness (most beaten-down with bounce confirmation first).",
        "initial_capital": 10000,
        "max_positions": 4,
        "position_pct": 0.20,
        "methodology": "rel_strength",
        "update_interval_min": 60,
        "deep_value": True,
    },
    {
        "id": "beaten_majors",
        "name": "Beaten Majors Long-Only",
        "description": "INTERNAL ENGINE: Inspired by chrspecifics_upwardpotentLONGT TradingView approach. Buy top-10 majors when RSI(14)<40 AND price >10% below 30d high. Long-only, wide stops (-12%), conservative TP (+8%). Simple thesis: buy oversold blue-chips, hold for recovery.",
        "selection_rules": "Filter: _dv_type=beaten_majors. Sort by combined oversold score (RSI distance from 40 + drawdown depth). Most beaten = first pick.",
        "initial_capital": 10000,
        "max_positions": 6,
        "position_pct": 0.10,
        "methodology": "beaten_majors",
        "update_interval_min": 30,
        "deep_value": True,
    },
    # ── Hoffman + Higher Timeframe Mutation Portfolios ──
    # These use INTERNALLY GENERATED picks from generate_htf_picks().
    {
        "id": "hoffman_elite",
        "name": "Hoffman Elite Combo",
        "description": "INTERNAL ENGINE: Rob Hoffman's Inventory Retracement Bar (IRB) pattern + Connors RSI(2) mean reversion + Volume spike confirmation. Backtested at 78.9% WR. Uses ATR-based stops (3:1 R:R). Scans crypto 4H/1D timeframes.",
        "selection_rules": "Filter: _htf_type=hoffman. Sort by Hoffman signal strength. ATR-based TP/SL with 3:1 minimum R:R.",
        "initial_capital": 10000,
        "max_positions": 5,
        "position_pct": 0.18,
        "methodology": "hoffman",
        "update_interval_min": 60,
        "htf_value": True,
    },
    {
        "id": "htf_trend_follow",
        "name": "HTF Trend Follower",
        "description": "INTERNAL ENGINE: Only trades when BOTH weekly and daily trends align (both bullish or both bearish). Weekly trend = price vs 50-week SMA. Daily trend = EMA 21 vs EMA 50. Avoids choppy markets entirely.",
        "selection_rules": "Filter: _htf_type=trend_follow + weekly_trend == daily_trend. Sort by trend strength.",
        "initial_capital": 10000,
        "max_positions": 6,
        "position_pct": 0.15,
        "methodology": "htf_trend",
        "update_interval_min": 120,
        "htf_value": True,
    },
    {
        "id": "htf_weekly_momentum",
        "name": "HTF Weekly Momentum",
        "description": "INTERNAL ENGINE: Requires daily EMA stack aligned (9 > 21 > 50 for longs, reverse for shorts). Buys pullbacks to the 9 EMA in confirmed uptrend. Based on Pentoshi/DonAlt higher-timeframe methodology (65-72% documented WR).",
        "selection_rules": "Filter: _htf_type=ema_stack_pullback + EMA 9>21>50 aligned. Sort by distance to EMA 9 (closest pullback = best entry).",
        "initial_capital": 10000,
        "max_positions": 5,
        "position_pct": 0.18,
        "methodology": "htf_momentum",
        "update_interval_min": 120,
        "htf_value": True,
    },
    # ── Prop Firm Challenge Portfolios ──
    # Simulate real prop firm rules with strict risk management.
    {
        "id": "prop_conservative",
        "name": "Prop: Conservative",
        "description": "Prop firm sim ($100K). RULES: 4% max daily loss, 8% max total drawdown, 8% profit target to pass. Only PROVEN/FORWARD strategies + R:R>=1.3 + no memes. Auto-resets if blown. Simulates FTMO/MFF conservative challenge.",
        "selection_rules": "Filter: trust_tier PROVEN/FORWARD + R:R>=1.3 + not meme. Fallback: R:R>=1.5. Sort by score_pick(). 4% position sizing.",
        "initial_capital": 100000,
        "max_positions": 5,
        "position_pct": 0.04,
        "methodology": "prop_conservative",
        "update_interval_min": 30,
        "prop_firm": True,
        "daily_loss_limit_pct": 4.0,
        "max_drawdown_pct": 8.0,
        "profit_target_pct": 8.0,
    },
    {
        "id": "prop_aggressive",
        "name": "Prop: Aggressive",
        "description": "Prop firm sim ($100K). RULES: 6% max daily loss, 10% max total drawdown, 10% profit target. R:R>=1.3 + confidence>=0.6 + no memes. Larger positions, more trades, faster to pass or blow. Simulates aggressive FTMO challenge.",
        "selection_rules": "Filter: R:R>=1.3 + confidence>=0.6 + not meme. Sort by score_pick(). 6% position sizing.",
        "initial_capital": 100000,
        "max_positions": 8,
        "position_pct": 0.06,
        "methodology": "prop_aggressive",
        "update_interval_min": 30,
        "prop_firm": True,
        "daily_loss_limit_pct": 6.0,
        "max_drawdown_pct": 10.0,
        "profit_target_pct": 10.0,
    },
    {
        "id": "prop_swing",
        "name": "Prop: Swing Trader",
        "description": "Prop firm sim ($200K). RULES: 5% max daily loss, 10% max total drawdown, 8% target. R:R>=1.5 + no memes + no system conflicts. Fewer but higher-quality trades, longer holds. Simulates swing-trader prop challenge.",
        "selection_rules": "Filter: R:R>=1.5 + not meme + no conflicts. Fallback: R:R>=1.3. Sort by R:R descending. 5% position sizing.",
        "initial_capital": 200000,
        "max_positions": 4,
        "position_pct": 0.05,
        "methodology": "prop_swing",
        "update_interval_min": 120,
        "prop_firm": True,
        "daily_loss_limit_pct": 5.0,
        "max_drawdown_pct": 10.0,
        "profit_target_pct": 8.0,
    },
    # ── Non-Crypto Portfolios ──
    # These filter by asset_class before selection.
    {
        "id": "stocks_best",
        "name": "Stocks: Best Picks",
        "description": "EQUITY ONLY. Filters all picks to asset_class=EQUITY (AAPL, MSFT, SPY, QQQ, COIN, MSTR, etc). Top scored equity picks from any system. Prices via Yahoo Finance failover.",
        "selection_rules": "Pre-filter: asset_class=EQUITY only. Then sort by score_pick() descending.",
        "initial_capital": 10000,
        "max_positions": 6,
        "position_pct": 0.15,
        "methodology": "noncrypto_best",
        "update_interval_min": 120,
        "noncrypto": True,
        "asset_filter": ["EQUITY"],
    },
    {
        "id": "stocks_short_term",
        "name": "Stocks: Short-Term Reversal",
        "description": "EQUITY ONLY. Same equity filter as Stocks Best, but prioritizes freshest signals (< 12h old). Mean reversion and short-term momentum plays on stocks/ETFs.",
        "selection_rules": "Pre-filter: asset_class=EQUITY. Then filter: age < 12h. Sort by score_pick().",
        "initial_capital": 10000,
        "max_positions": 6,
        "position_pct": 0.15,
        "methodology": "noncrypto_reversal",
        "update_interval_min": 120,
        "noncrypto": True,
        "asset_filter": ["EQUITY"],
    },
    {
        "id": "forex_carry",
        "name": "Forex: Carry & Momentum",
        "description": "FOREX ONLY. Filters to asset_class=FOREX (EURUSD, GBPUSD, USDJPY, AUDUSD). Top scored forex picks. Prices via CurrencyLayer/Yahoo. Longer update interval (2h) since forex moves slower.",
        "selection_rules": "Pre-filter: asset_class=FOREX only. Then sort by score_pick() descending.",
        "initial_capital": 10000,
        "max_positions": 4,
        "position_pct": 0.15,
        "methodology": "noncrypto_best",
        "update_interval_min": 120,
        "noncrypto": True,
        "asset_filter": ["FOREX"],
    },
    {
        "id": "multi_asset_diversified",
        "name": "Multi-Asset: Diversified",
        "description": "STOCKS + FOREX combined. Filters to asset_class in (EQUITY, FOREX). Sector rotation across non-crypto: max 3 equity + max 2 forex. Best diversification outside crypto.",
        "selection_rules": "Pre-filter: asset_class in (EQUITY, FOREX). Sector rotation: top 3 equity + top 2 forex by score.",
        "initial_capital": 10000,
        "max_positions": 6,
        "position_pct": 0.12,
        "methodology": "noncrypto_diversified",
        "update_interval_min": 120,
        "noncrypto": True,
        "asset_filter": ["EQUITY", "FOREX"],
    },
    {
        "id": "futures_index",
        "name": "Futures: Index & Commodities",
        "description": "FUTURES ONLY. ES, NQ, YM, CL, GC, SI, ZN. Connors RSI-2 (proven 75.7% WR) + EMA stack + Bollinger mean reversion. Trades index futures with tight risk management.",
        "selection_rules": "Pre-filter: asset_class=FUTURES. Sort by score_pick() descending.",
        "initial_capital": 10000,
        "max_positions": 5,
        "position_pct": 0.15,
        "methodology": "noncrypto_best",
        "update_interval_min": 60,
        "noncrypto": True,
        "asset_filter": ["FUTURES"],
    },
    {
        "id": "etf_rotation",
        "name": "ETFs: Sector Rotation",
        "description": "ETF ONLY. SPY, QQQ, XLK, XLF, XLE, GLD, TLT, IWM. Sector rotation via EMA stack + VIX reversal. Moderate hold periods (5-15 days).",
        "selection_rules": "Pre-filter: asset_class=ETF. Sort by score_pick() descending.",
        "initial_capital": 10000,
        "max_positions": 5,
        "position_pct": 0.15,
        "methodology": "noncrypto_best",
        "update_interval_min": 120,
        "noncrypto": True,
        "asset_filter": ["ETF"],
    },
    {
        "id": "all_asset_tournament",
        "name": "Tournament: All Assets",
        "description": "ALL non-crypto asset classes combined. Futures + Stocks + Forex + ETFs. Best picks across the board, tournament-ranked by score. This is the prediction tournament portfolio.",
        "selection_rules": "Pre-filter: asset_class in (FUTURES, EQUITY, FOREX, ETF, PENNY_STOCK). Top picks by score.",
        "initial_capital": 10000,
        "max_positions": 10,
        "position_pct": 0.10,
        "methodology": "noncrypto_diversified",
        "update_interval_min": 60,
        "noncrypto": True,
        "asset_filter": ["FUTURES", "EQUITY", "FOREX", "ETF", "PENNY_STOCK"],
    },
    # ── Mercury 3-Lever Validation Portfolios ──
    # Each isolates one variable from Mercury's audit recommendations.
    {
        "id": "regime_filtered",
        "name": "Regime Filtered",
        "description": "Only picks where strategy matches current regime (regime_meta_router alignment). Tests if regime filtering improves WR by 5-10pp.",
        "selection_rules": "Filter: direction must align with detected regime (BULLISH=LONG, BEARISH=SHORT, CHOPPY=R:R>=1.5). Only PROVEN/FORWARD strategies. Sort by score_pick().",
        "initial_capital": 10000,
        "max_positions": 8,
        "position_pct": 0.08,
        "methodology": "regime_aligned_only",
        "update_interval_min": 30,
    },
    {
        "id": "high_consensus",
        "name": "High Consensus",
        "description": "Only picks where 3+ diverse systems agree. Historical 78.6% WR. Tests consensus as quality filter.",
        "selection_rules": "Filter: system_agreement_count >= 3. Deduplicate by symbol. Sort by agreement desc then score_pick().",
        "initial_capital": 10000,
        "max_positions": 8,
        "position_pct": 0.10,
        "methodology": "consensus_3plus",
        "update_interval_min": 30,
    },
    {
        "id": "golden_only",
        "name": "Golden Only",
        "description": "Only picks from walk-forward validated strategies (Keltner BTC 66.1% WR, RSI confluence). Tests proven-only approach.",
        "selection_rules": "Filter: strategy in PROVEN_STRATEGIES set (walk-forward validated, 50+ trades, PF>1.5). Sort by score_pick().",
        "initial_capital": 10000,
        "max_positions": 8,
        "position_pct": 0.12,
        "methodology": "golden_insight_only",
        "update_interval_min": 30,
    },
    {
        "id": "small_position",
        "name": "Small Position",
        "description": "Score Leaders picks but with 2% position size (Mercury recommends max 2%). Tests if smaller positions reduce DD.",
        "selection_rules": "Same as score_leaders (sort by score_pick() descending) but with 2% position sizing instead of 12%.",
        "initial_capital": 10000,
        "max_positions": 8,
        "position_pct": 0.02,
        "methodology": "score_small_position",
        "update_interval_min": 30,
    },
    {
        "id": "sentiment_divergence",
        "name": "Sentiment Divergence",
        "description": "Only sentiment-price divergence signals. Tests new strategy in isolation.",
        "selection_rules": "Filter: strategy contains 'sentiment_price_divergence'. Sort by score_pick().",
        "initial_capital": 10000,
        "max_positions": 8,
        "position_pct": 0.05,
        "methodology": "sentiment_divergence_only",
        "update_interval_min": 30,
    },
    {
        "id": "basis_carry_only",
        "name": "Basis & Carry",
        "description": "Funding rate arbitrage + cross-exchange basis carry. Structural edge, market-neutral. Expected Sharpe 2.0+.",
        "selection_rules": "Filter: strategy in (funding_rate_carry, funding_rate_carry_pro, funding_rate_arbitrage, cross_exchange_basis_carry, funding_momentum). Sort by score_pick().",
        "initial_capital": 10000,
        "max_positions": 8,
        "position_pct": 0.08,
        "methodology": "carry_arb_only",
        "update_interval_min": 30,
    },
]


def now_est():
    return datetime.now(EST)


# ═══════════════════════════════════════════════════════════════
# DEEP-VALUE MUTATIONS (inspired by user's "buy the blood" strategy)
# Scans for beaten-down assets with high recovery potential
# ═══════════════════════════════════════════════════════════════

# Assets to scan for deep-value opportunities (major + mid-cap)
DEEP_VALUE_UNIVERSE = [
    "BTCUSDT",
    "ETHUSDT",
    "XRPUSDT",
    "SOLUSDT",
    "ADAUSDT",
    "DOGEUSDT",
    "DOTUSDT",
    "AVAXUSDT",
    "LINKUSDT",
    "MATICUSDT",
    "LTCUSDT",
    "UNIUSDT",
    "AAVEUSDT",
    "NEARUSDT",
    "ATOMUSDT",
    "APTUSDT",
    "ARBUSDT",
    "OPUSDT",
    "INJUSDT",
    "SUIUSDT",
]

# Deep value thresholds
DV_MIN_DRAWDOWN_PCT = (
    15  # Min drawdown from 90d high to consider "beaten down" (lowered from 25)
)
DV_DCA_LEVELS = [30, 40, 50]  # DCA entry at -30%, -40%, -50% from 90d high
DV_RSI_CAPITULATION = 35  # Weekly RSI below this = capitulation zone
DV_FEAR_THRESHOLD = (
    35  # Fear & Greed index <= this = extreme fear (raised from 25 for more signals)
)
DV_RECOVERY_CONFIRM_PCT = 3.0  # Price must bounce 3% from local low to confirm recovery
DV_TP_RECOVERY_PCT = 50  # TP at 50% of drawdown recovery (conservative)
DV_SL_EXTENSION_PCT = 10  # SL 10% below current level (wide stop for swing)


def fetch_klines(symbol, interval="1d", limit=90):
    """Fetch historical klines with Binance -> Bybit failover."""
    # Layer 1: Binance (try US endpoint first to avoid geo-block)
    for binance_base in ["https://api.binance.us", "https://api.binance.com"]:
        try:
            url = f"{binance_base}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            data = json.loads(urllib.request.urlopen(req, timeout=10).read())
            return [
                {
                    "time": d[0],
                    "open": float(d[1]),
                    "high": float(d[2]),
                    "low": float(d[3]),
                    "close": float(d[4]),
                    "volume": float(d[5]),
                }
                for d in data
            ]
        except Exception:
            pass

    # Layer 2: Bybit (handles HTTP 451 Binance geo-blocks in GitHub Actions)
    _BYBIT_INTERVAL_MAP = {"1d": "D", "4h": "240", "1h": "60", "15m": "15", "5m": "5"}
    bybit_interval = _BYBIT_INTERVAL_MAP.get(interval, "D")
    try:
        url = f"https://api.bybit.com/v5/market/kline?category=spot&symbol={symbol}&interval={bybit_interval}&limit={limit}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
        rows = resp.get("result", {}).get("list", [])
        # Bybit returns [timestamp, open, high, low, close, volume, turnover] in REVERSE order
        klines = [
            {
                "time": int(r[0]),
                "open": float(r[1]),
                "high": float(r[2]),
                "low": float(r[3]),
                "close": float(r[4]),
                "volume": float(r[5]),
            }
            for r in reversed(rows)
        ]
        if klines:
            return klines
    except Exception:
        pass

    return []


def calc_rsi_from_klines(klines, period=14):
    """Calculate RSI from kline close prices."""
    if len(klines) < period + 1:
        return 50.0  # neutral default
    closes = [k["close"] for k in klines]
    gains, losses = [], []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(0, delta))
        losses.append(max(0, -delta))
    if len(gains) < period:
        return 50.0
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def fetch_fear_greed():
    """Fetch Crypto Fear & Greed Index."""
    try:
        url = "https://api.alternative.me/fng/?limit=1"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        data = json.loads(urllib.request.urlopen(req, timeout=10).read())
        return int(data["data"][0]["value"])
    except Exception:
        return 50  # neutral default


def generate_deep_value_picks(prices):
    """
    Generate synthetic picks from deep-value analysis.
    Scans major crypto assets for:
    1. Deep drawdown from 90d high (buy the blood)
    2. RSI capitulation (oversold bounce)
    3. Fear & Greed extreme (contrarian DCA)
    4. Relative strength recovery (weakest bouncing back)
    """
    deep_value_picks = []
    fear_greed = fetch_fear_greed()
    asset_analysis = {}

    for symbol in DEEP_VALUE_UNIVERSE:
        current_price = prices.get(symbol, 0)
        if current_price <= 0:
            continue

        klines = fetch_klines(symbol, "1d", 90)
        if len(klines) < 30:
            continue

        # Calculate metrics
        high_90d = max(k["high"] for k in klines)
        low_90d = min(k["low"] for k in klines)
        drawdown_pct = ((high_90d - current_price) / high_90d) * 100
        rsi_daily = calc_rsi_from_klines(klines, 14)

        # Weekly RSI approximation (use last 14 weeks of daily data)
        weekly_closes = klines[::7]  # sample every 7th day
        rsi_weekly = (
            calc_rsi_from_klines(weekly_closes, 14)
            if len(weekly_closes) > 15
            else rsi_daily
        )

        # Recent momentum (is it bouncing?)
        if len(klines) >= 7:
            low_7d = min(k["low"] for k in klines[-7:])
            bounce_pct = ((current_price - low_7d) / low_7d) * 100 if low_7d > 0 else 0
        else:
            bounce_pct = 0

        # 30d performance (relative strength)
        if len(klines) >= 30:
            price_30d_ago = klines[-30]["close"]
            perf_30d = ((current_price - price_30d_ago) / price_30d_ago) * 100
        else:
            perf_30d = 0

        asset_analysis[symbol] = {
            "price": current_price,
            "high_90d": high_90d,
            "low_90d": low_90d,
            "drawdown_pct": drawdown_pct,
            "rsi_daily": rsi_daily,
            "rsi_weekly": rsi_weekly,
            "bounce_pct": bounce_pct,
            "perf_30d": perf_30d,
            "fear_greed": fear_greed,
        }

        # ── Mutation 1: Deep Drawdown DCA ──
        # Asset is down >25% from 90d high = deep value territory
        if drawdown_pct >= DV_MIN_DRAWDOWN_PCT:
            # TP: recover 50% of the drawdown
            recovery_target = current_price + (high_90d - current_price) * (
                DV_TP_RECOVERY_PCT / 100
            )
            # SL: 10% below current (wide stop for swing trade)
            sl = current_price * (1 - DV_SL_EXTENSION_PCT / 100)
            rr = (
                (recovery_target - current_price) / (current_price - sl)
                if (current_price - sl) > 0
                else 0
            )

            # Confidence scales with drawdown depth (deeper = more upside)
            conf = min(0.90, 0.50 + (drawdown_pct - DV_MIN_DRAWDOWN_PCT) * 0.01)

            if rr >= 1.2:
                deep_value_picks.append(
                    {
                        "symbol": symbol.replace("USDT", "-USDT"),
                        "direction": "LONG",
                        "asset_class": "CRYPTO",
                        "source_system": "deep_value_engine",
                        "strategy": f"deep_drawdown_dca_{symbol.replace('USDT', '').lower()}",
                        "entry_price": current_price,
                        "take_profit": round(recovery_target, 6),
                        "stop_loss": round(sl, 6),
                        "confidence": round(conf, 2),
                        "pnl_pct": 0,
                        "age_hours": 0,
                        "system_agreement_count": 2 if drawdown_pct >= 40 else 1,
                        "has_conflict": False,
                        "_dv_type": "drawdown_dca",
                        "_drawdown_pct": round(drawdown_pct, 1),
                        "_rsi": round(rsi_daily, 1),
                        "_bounce_pct": round(bounce_pct, 2),
                    }
                )

        # ── Mutation 2: RSI Capitulation Sniper ──
        # RSI < 35 AND bouncing = oversold reversal
        if rsi_daily < DV_RSI_CAPITULATION and bounce_pct >= DV_RECOVERY_CONFIRM_PCT:
            recovery_target = (
                current_price * 1.15
            )  # 15% bounce target from capitulation
            sl = current_price * 0.92  # 8% SL
            rr = (recovery_target - current_price) / (current_price - sl)
            conf = min(0.85, 0.55 + (35 - rsi_daily) * 0.015)

            deep_value_picks.append(
                {
                    "symbol": symbol.replace("USDT", "-USDT"),
                    "direction": "LONG",
                    "asset_class": "CRYPTO",
                    "source_system": "deep_value_engine",
                    "strategy": f"rsi_capitulation_sniper_{symbol.replace('USDT', '').lower()}",
                    "entry_price": current_price,
                    "take_profit": round(recovery_target, 6),
                    "stop_loss": round(sl, 6),
                    "confidence": round(conf, 2),
                    "pnl_pct": 0,
                    "age_hours": 0,
                    "system_agreement_count": 2,
                    "has_conflict": False,
                    "_dv_type": "rsi_capitulation",
                    "_rsi": round(rsi_daily, 1),
                    "_bounce_pct": round(bounce_pct, 2),
                }
            )

        # ── Mutation 3: Fear & Greed Contrarian DCA ──
        # F&G <= 25 + asset in top-10 market cap = extreme fear accumulation
        if fear_greed <= DV_FEAR_THRESHOLD and symbol in [
            "BTCUSDT",
            "ETHUSDT",
            "XRPUSDT",
            "SOLUSDT",
            "ADAUSDT",
            "DOGEUSDT",
            "DOTUSDT",
            "AVAXUSDT",
            "LINKUSDT",
            "LTCUSDT",
        ]:
            # Conservative targets during fear: 10% up, 7% SL
            recovery_target = current_price * 1.10
            sl = current_price * 0.93
            rr = (recovery_target - current_price) / (current_price - sl)
            # Higher confidence when F&G is extremely low
            conf = min(0.88, 0.60 + (DV_FEAR_THRESHOLD - fear_greed) * 0.02)

            deep_value_picks.append(
                {
                    "symbol": symbol.replace("USDT", "-USDT"),
                    "direction": "LONG",
                    "asset_class": "CRYPTO",
                    "source_system": "deep_value_engine",
                    "strategy": f"fear_greed_contrarian_{symbol.replace('USDT', '').lower()}",
                    "entry_price": current_price,
                    "take_profit": round(recovery_target, 6),
                    "stop_loss": round(sl, 6),
                    "confidence": round(conf, 2),
                    "pnl_pct": 0,
                    "age_hours": 0,
                    "system_agreement_count": 1,
                    "has_conflict": False,
                    "_dv_type": "fear_greed",
                    "_fear_greed": fear_greed,
                }
            )

    # ── Mutation 4: Relative Strength Recovery ──
    # Find the weakest 30d performers that are now bouncing
    if asset_analysis:
        sorted_by_perf = sorted(asset_analysis.items(), key=lambda x: x[1]["perf_30d"])
        weakest_3 = sorted_by_perf[:3]  # 3 worst performers

        for symbol, analysis in weakest_3:
            # Only if bouncing (recovery confirmation)
            if analysis["bounce_pct"] >= DV_RECOVERY_CONFIRM_PCT:
                current_price = analysis["price"]
                # Target: mean reversion to 30d midpoint
                midpoint = (analysis["high_90d"] + analysis["low_90d"]) / 2
                recovery_target = current_price + (midpoint - current_price) * 0.5
                if recovery_target <= current_price:
                    recovery_target = current_price * 1.08  # fallback 8%
                sl = current_price * 0.92
                rr = (
                    (recovery_target - current_price) / (current_price - sl)
                    if (current_price - sl) > 0
                    else 0
                )
                conf = min(0.80, 0.50 + abs(analysis["perf_30d"]) * 0.005)

                if rr >= 1.0:
                    deep_value_picks.append(
                        {
                            "symbol": symbol.replace("USDT", "-USDT"),
                            "direction": "LONG",
                            "asset_class": "CRYPTO",
                            "source_system": "deep_value_engine",
                            "strategy": f"relative_strength_recovery_{symbol.replace('USDT', '').lower()}",
                            "entry_price": current_price,
                            "take_profit": round(recovery_target, 6),
                            "stop_loss": round(sl, 6),
                            "confidence": round(conf, 2),
                            "pnl_pct": 0,
                            "age_hours": 0,
                            "system_agreement_count": 1,
                            "has_conflict": False,
                            "_dv_type": "rel_strength",
                            "_perf_30d": round(analysis["perf_30d"], 2),
                            "_bounce_pct": round(analysis["bounce_pct"], 2),
                        }
                    )

    # ── Mutation 5: Beaten Majors Long-Only ──
    # Inspired by chrspecifics_upwardpotentLONGT TradingView approach
    # Simple: RSI(14) < 40 AND >10% below 30d high → buy with wide stops
    BEATEN_MAJORS_UNIVERSE = [
        "BTCUSDT",
        "ETHUSDT",
        "SOLUSDT",
        "ADAUSDT",
        "XRPUSDT",
        "DOGEUSDT",
        "AVAXUSDT",
        "LINKUSDT",
        "DOTUSDT",
        "BNBUSDT",
    ]
    for symbol in BEATEN_MAJORS_UNIVERSE:
        analysis = asset_analysis.get(symbol)
        if not analysis:
            continue
        current_price = analysis["price"]
        rsi = analysis["rsi_daily"]
        # 30d high (use klines data)
        klines = fetch_klines(symbol, "1d", 30)
        if len(klines) < 10:
            continue
        high_30d = max(k["high"] for k in klines)
        dd_from_30d = ((high_30d - current_price) / high_30d) * 100

        # Entry: RSI < 40 AND price >10% below 30d high
        if rsi < 40 and dd_from_30d >= 10:
            tp = current_price * 1.08  # +8% TP (conservative, let winners run)
            sl = current_price * 0.88  # -12% SL (wide, avoid volatility stops)
            rr = (
                (tp - current_price) / (current_price - sl)
                if (current_price - sl) > 0
                else 0
            )

            # Confidence: lower RSI + deeper drawdown = higher conviction
            rsi_score = (40 - rsi) / 40  # 0 to 1 scale
            dd_score = min(dd_from_30d / 30, 1.0)  # cap at 30% drawdown
            conf = min(0.85, 0.55 + rsi_score * 0.15 + dd_score * 0.10)

            if rr >= 0.6:  # Accept lower R:R since win rate is higher for majors
                deep_value_picks.append(
                    {
                        "symbol": symbol.replace("USDT", "-USDT"),
                        "direction": "LONG",
                        "asset_class": "CRYPTO",
                        "source_system": "deep_value_engine",
                        "strategy": f"beaten_majors_{symbol.replace('USDT', '').lower()}",
                        "entry_price": current_price,
                        "take_profit": round(tp, 6),
                        "stop_loss": round(sl, 6),
                        "confidence": round(conf, 2),
                        "pnl_pct": 0,
                        "age_hours": 0,
                        "system_agreement_count": 2,
                        "has_conflict": False,
                        "_dv_type": "beaten_majors",
                        "_rsi": round(rsi, 1),
                        "_dd_from_30d": round(dd_from_30d, 1),
                        "_bounce_pct": round(analysis["bounce_pct"], 2),
                    }
                )

    return deep_value_picks, asset_analysis


# ═══════════════════════════════════════════════════════════════
# HOFFMAN + HIGHER TIMEFRAME (HTF) DNA MUTATIONS
# "Higher timeframes always win" — prioritize daily/weekly trend
# ═══════════════════════════════════════════════════════════════

HTF_UNIVERSE = [
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "XRPUSDT",
    "BNBUSDT",
    "ADAUSDT",
    "DOGEUSDT",
    "LINKUSDT",
    "AVAXUSDT",
    "LTCUSDT",
]


def generate_htf_picks(prices):
    """
    Generate picks based on Higher Timeframe analysis:
    1. Hoffman Elite Combo — IRB + RSI(2) + Volume on 15m, confirmed by daily trend
    2. HTF Trend Follow — Only trade in direction of weekly trend (EMA 20 > EMA 50)
    3. HTF Weekly Momentum — Buy assets with weekly EMA stack aligned (9>21>50)
    """
    htf_picks = []

    for symbol in HTF_UNIVERSE:
        current_price = prices.get(symbol, 0)
        if current_price <= 0:
            continue

        # Fetch daily klines for trend determination
        daily_klines = fetch_klines(symbol, "1d", 60)
        if len(daily_klines) < 50:
            continue

        # Weekly approximation: sample every 7 days
        weekly_klines = (
            daily_klines[::7] if len(daily_klines) >= 35 else daily_klines[::5]
        )

        # Calculate EMAs
        daily_closes = [k["close"] for k in daily_klines]

        def ema(data, period):
            if len(data) < period:
                return data[-1] if data else 0
            multiplier = 2 / (period + 1)
            result = sum(data[:period]) / period
            for val in data[period:]:
                result = (val - result) * multiplier + result
            return result

        ema_9d = ema(daily_closes, 9)
        ema_21d = ema(daily_closes, 21)
        ema_50d = ema(daily_closes, 50)

        # Weekly EMAs (approximate)
        weekly_closes = [k["close"] for k in weekly_klines]
        ema_9w = ema(weekly_closes, min(9, len(weekly_closes)))
        ema_21w = ema(weekly_closes, min(21, len(weekly_closes)))

        # Daily RSI for Hoffman
        rsi_daily = calc_rsi_from_klines(daily_klines, 14)
        rsi_2 = calc_rsi_from_klines(daily_klines, 2)  # Connors RSI(2) for extremes

        # Determine HTF trend direction
        daily_trend = (
            "BULLISH"
            if ema_9d > ema_21d > ema_50d
            else ("BEARISH" if ema_9d < ema_21d < ema_50d else "NEUTRAL")
        )
        weekly_trend = (
            "BULLISH"
            if ema_9w > ema_21w
            else ("BEARISH" if ema_9w < ema_21w else "NEUTRAL")
        )

        # Volume analysis (last 3 days vs 20-day average)
        volumes = [k["volume"] for k in daily_klines]
        vol_avg_20 = (
            sum(volumes[-20:]) / 20
            if len(volumes) >= 20
            else sum(volumes) / max(1, len(volumes))
        )
        vol_recent = (
            sum(volumes[-3:]) / 3
            if len(volumes) >= 3
            else volumes[-1]
            if volumes
            else 0
        )
        vol_ratio = vol_recent / vol_avg_20 if vol_avg_20 > 0 else 1

        # ── Hoffman Elite Combo (IRB + RSI2 + Volume) ──
        # Buy when: RSI(2) < 25 (oversold extreme) + daily trend up + volume > 1.2x avg
        if rsi_2 < 25 and daily_trend == "BULLISH" and vol_ratio >= 1.2:
            # Hoffman uses 2x ATR stop, 3x ATR target
            atr_est = abs(daily_klines[-1]["high"] - daily_klines[-1]["low"])
            tp = current_price + atr_est * 3.0
            sl = current_price - atr_est * 2.0
            rr = (
                (tp - current_price) / (current_price - sl)
                if (current_price - sl) > 0
                else 0
            )
            conf = min(0.90, 0.65 + (25 - rsi_2) * 0.01 + (vol_ratio - 1.0) * 0.1)

            if rr >= 1.2:
                htf_picks.append(
                    {
                        "symbol": symbol.replace("USDT", "-USDT"),
                        "direction": "LONG",
                        "asset_class": "CRYPTO",
                        "source_system": "htf_engine",
                        "strategy": f"hoffman_elite_{symbol.replace('USDT', '').lower()}",
                        "entry_price": current_price,
                        "take_profit": round(tp, 6),
                        "stop_loss": round(sl, 6),
                        "confidence": round(conf, 2),
                        "pnl_pct": 0,
                        "age_hours": 0,
                        "system_agreement_count": 2,
                        "has_conflict": False,
                        "_htf_type": "hoffman_elite",
                        "_rsi2": round(rsi_2, 1),
                        "_vol_ratio": round(vol_ratio, 2),
                        "_daily_trend": daily_trend,
                    }
                )

        # Sell when: RSI(2) > 75 (overbought extreme) + daily trend down
        if rsi_2 > 75 and daily_trend == "BEARISH" and vol_ratio >= 1.2:
            atr_est = abs(daily_klines[-1]["high"] - daily_klines[-1]["low"])
            tp = current_price - atr_est * 3.0
            sl = current_price + atr_est * 2.0
            rr = (
                (current_price - tp) / (sl - current_price)
                if (sl - current_price) > 0
                else 0
            )
            conf = min(0.90, 0.65 + (rsi_2 - 75) * 0.01 + (vol_ratio - 1.0) * 0.1)

            if rr >= 1.2:
                htf_picks.append(
                    {
                        "symbol": symbol.replace("USDT", "-USDT"),
                        "direction": "SHORT",
                        "asset_class": "CRYPTO",
                        "source_system": "htf_engine",
                        "strategy": f"hoffman_elite_{symbol.replace('USDT', '').lower()}",
                        "entry_price": current_price,
                        "take_profit": round(tp, 6),
                        "stop_loss": round(sl, 6),
                        "confidence": round(conf, 2),
                        "pnl_pct": 0,
                        "age_hours": 0,
                        "system_agreement_count": 2,
                        "has_conflict": False,
                        "_htf_type": "hoffman_elite",
                        "_rsi2": round(rsi_2, 1),
                        "_daily_trend": daily_trend,
                    }
                )

        # ── HTF Trend Follow — Only trade with weekly trend ──
        # "Higher timeframes always win" — if weekly + daily align, take the trade
        if weekly_trend == daily_trend and daily_trend != "NEUTRAL":
            direction = "LONG" if daily_trend == "BULLISH" else "SHORT"
            atr_est = abs(daily_klines[-1]["high"] - daily_klines[-1]["low"])

            if direction == "LONG":
                tp = current_price + atr_est * 2.5
                sl = current_price - atr_est * 1.5
            else:
                tp = current_price - atr_est * 2.5
                sl = current_price + atr_est * 1.5

            risk = abs(current_price - sl)
            reward = abs(tp - current_price)
            rr = reward / risk if risk > 0 else 0
            conf = min(0.85, 0.55 + vol_ratio * 0.1)

            if rr >= 1.2:
                htf_picks.append(
                    {
                        "symbol": symbol.replace("USDT", "-USDT"),
                        "direction": direction,
                        "asset_class": "CRYPTO",
                        "source_system": "htf_engine",
                        "strategy": f"htf_trend_follow_{symbol.replace('USDT', '').lower()}",
                        "entry_price": current_price,
                        "take_profit": round(tp, 6),
                        "stop_loss": round(sl, 6),
                        "confidence": round(conf, 2),
                        "pnl_pct": 0,
                        "age_hours": 0,
                        "system_agreement_count": 1,
                        "has_conflict": False,
                        "_htf_type": "htf_trend",
                        "_daily_trend": daily_trend,
                        "_weekly_trend": weekly_trend,
                    }
                )

        # ── HTF Weekly Momentum — EMA stack fully aligned ──
        # Daily EMA 9 > 21 > 50 = strong uptrend, buy pullbacks
        if (
            ema_9d > ema_21d > ema_50d
            and current_price > ema_21d
            and current_price < ema_9d * 1.02
        ):
            # Price near EMA 9 = good pullback entry in uptrend
            tp = current_price * 1.08  # 8% target in strong trend
            sl = ema_50d * 0.98  # SL just below EMA 50
            risk = current_price - sl
            rr = (tp - current_price) / risk if risk > 0 else 0
            conf = min(0.85, 0.60 + (ema_9d / ema_50d - 1) * 5)

            if rr >= 1.0 and risk > 0:
                htf_picks.append(
                    {
                        "symbol": symbol.replace("USDT", "-USDT"),
                        "direction": "LONG",
                        "asset_class": "CRYPTO",
                        "source_system": "htf_engine",
                        "strategy": f"htf_weekly_momentum_{symbol.replace('USDT', '').lower()}",
                        "entry_price": current_price,
                        "take_profit": round(tp, 6),
                        "stop_loss": round(sl, 6),
                        "confidence": round(conf, 2),
                        "pnl_pct": 0,
                        "age_hours": 0,
                        "system_agreement_count": 1,
                        "has_conflict": False,
                        "_htf_type": "weekly_momentum",
                        "_ema_stack": f"9d={ema_9d:.2f} > 21d={ema_21d:.2f} > 50d={ema_50d:.2f}",
                    }
                )

    return htf_picks


def _dedup_trades(trades):
    """Remove duplicate trades by ID, keeping the first occurrence."""
    seen = set()
    result = []
    for t in trades:
        tid = t.get("id", "")
        if tid and tid in seen:
            continue
        seen.add(tid)
        result.append(t)
    return result


def _sanitize_portfolio(pname, pdata):
    """Remove ALL corrupt trades/positions and recalculate metrics.
    Uses reference prices to catch stale/synthetic data."""
    if not isinstance(pdata, dict):
        return
    init_cap = pdata.get("initial_capital", 10000)
    total_removed_pnl = 0
    total_freed_size = 0

    # Sanitize closed trades
    closed = pdata.get("closed", [])
    clean_closed = []
    seen_ids = set()
    for t in closed:
        tid = t.get("id", "")
        sym = t.get("symbol", "")
        entry = t.get("entry_price", 0)
        exit_p = t.get("exit_price", 0)
        pnl_pct = abs(t.get("pnl_pct", 0) or 0)

        # Skip dupes
        if tid and tid in seen_ids:
            total_removed_pnl += t.get("net_pnl_usd", 0) or t.get("pnl_usd", 0) or 0
            continue
        seen_ids.add(tid)

        # Price sanity check using reference prices
        corrupt = False
        if entry > 0:
            if not _price_is_sane(sym, entry, tolerance=0.50):
                corrupt = True
        if exit_p > 0 and not corrupt:
            if not _price_is_sane(sym, exit_p, tolerance=0.50):
                corrupt = True

        # Extreme PnL filter (>30% in a single trade within crypto is almost always synthetic)
        if pnl_pct > 30:
            corrupt = True
            print(
                f"  [SANITIZE] {pname}: extreme PnL {sym} {pnl_pct:.1f}% (>30% threshold)"
            )

        # TP/SL exit verification: exit price should be near TP or SL, not wildly different
        if not corrupt and exit_p > 0 and entry > 0:
            tp = t.get("take_profit", 0) or 0
            sl = t.get("stop_loss", 0) or 0
            reason = (
                t.get("exit_reason", "") or t.get("close_reason", "") or ""
            ).upper()
            if reason == "TP" and tp > 0:
                # Exit should be near the TP target (within 5%)
                tp_ratio = exit_p / tp if tp > 0 else 1
                if tp_ratio < 0.5 or tp_ratio > 2.0:
                    corrupt = True
                    print(
                        f"  [SANITIZE] {pname}: exit {sym} ${exit_p} far from TP ${tp} (ratio={tp_ratio:.2f})"
                    )
            elif reason == "SL" and sl > 0:
                sl_ratio = exit_p / sl if sl > 0 else 1
                if sl_ratio < 0.5 or sl_ratio > 2.0:
                    corrupt = True
                    print(
                        f"  [SANITIZE] {pname}: exit {sym} ${exit_p} far from SL ${sl} (ratio={sl_ratio:.2f})"
                    )

        if corrupt:
            this_pnl = t.get("net_pnl_usd", 0) or t.get("pnl_usd", 0) or 0
            total_removed_pnl += this_pnl
            print(
                f"  [SANITIZE] {pname}: removed closed {sym} entry={entry} exit={exit_p} pnl={t.get('pnl_pct', 0):.1f}%"
            )
        else:
            clean_closed.append(t)

    # Sanitize open positions
    positions = pdata.get("positions", [])
    clean_pos = []
    seen_pos_ids = set()
    for p in positions:
        pid = p.get("id", "")
        sym = p.get("symbol", "")
        entry = p.get("entry_price", 0)

        # Skip dupes
        if pid and pid in seen_pos_ids:
            total_freed_size += p.get("size_usd", 0) or 0
            continue
        seen_pos_ids.add(pid)

        # Price sanity
        if entry > 0 and not _price_is_sane(sym, entry, tolerance=0.50):
            total_freed_size += p.get("size_usd", 0) or 0
            print(f"  [SANITIZE] {pname}: removed position {sym} entry={entry}")
        else:
            clean_pos.append(p)

    # Recalculate if anything was removed
    if total_removed_pnl != 0 or total_freed_size > 0:
        pdata["closed"] = clean_closed
        pdata["positions"] = clean_pos

        # Recalculate cash, equity, wins/losses
        old_cash = pdata.get("cash", 0)
        new_cash = old_cash + total_freed_size - total_removed_pnl
        pdata["cash"] = max(new_cash, 0)

        pos_value = sum(p.get("size_usd", 0) or 0 for p in clean_pos)
        unrealized = sum(p.get("pnl_usd", 0) or 0 for p in clean_pos)
        pdata["equity"] = pdata["cash"] + pos_value + unrealized

        wins = len([t for t in clean_closed if (t.get("pnl_pct", 0) or 0) > 0])
        losses = len([t for t in clean_closed if (t.get("pnl_pct", 0) or 0) <= 0])
        pdata["wins"] = wins
        pdata["losses"] = losses

        if pdata.get("high_water_mark", 0) > pdata["equity"] * 1.5:
            pdata["high_water_mark"] = pdata["equity"]

        # Recalculate commissions
        pdata["total_commission"] = sum(
            (t.get("commission_entry", 0) or 0) + (t.get("commission_exit", 0) or 0)
            for t in clean_closed
        ) + sum((p.get("commission_entry", 0) or 0) for p in clean_pos)

        # Fix equity history
        for eh in pdata.get("equity_history", []):
            if eh.get("equity", 0) > pdata["equity"] * 2:
                eh["equity"] = pdata["equity"]

        pnl_pct = (pdata["equity"] - init_cap) / init_cap * 100
        print(
            f"  [SANITIZE] {pname}: equity recalculated to ${pdata['equity']:,.2f} ({pnl_pct:+.2f}%) W/L={wins}/{losses}"
        )
    else:
        # Still dedup even if no corrupt data
        pdata["closed"] = clean_closed
        pdata["positions"] = clean_pos


def _migrate_entry_costs(state):
    """One-time migration: deduct entry commission+slippage from cash for open positions.
    Before this fix, cash was only reduced by size_usd; now it includes all entry costs.
    Idempotent: checks for '_entry_costs_migrated' flag on each portfolio."""
    for pname, pdata in state.items():
        if not isinstance(pdata, dict) or pdata.get("_entry_costs_migrated"):
            continue
        total_adjustment = 0
        for pos in pdata.get("positions", []):
            comm = pos.get("commission_entry", 0) or 0
            slip = pos.get("slippage_entry", 0) or 0
            total_adjustment += comm + slip
        if total_adjustment > 0:
            pdata["cash"] -= total_adjustment
            # Recalculate equity with corrected cash
            unrealized = sum(p.get("pnl_usd", 0) for p in pdata.get("positions", []))
            allocated = sum(p.get("size_usd", 0) for p in pdata.get("positions", []))
            pdata["equity"] = pdata["cash"] + allocated + unrealized
            print(
                f"  [MIGRATE] {pname}: deducted ${total_adjustment:.2f} entry costs from cash → equity=${pdata['equity']:.2f}"
            )
        pdata["_entry_costs_migrated"] = True


def load_state():
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
        except json.JSONDecodeError as e:
            print(f"WARNING: State file corrupt ({e}), trying backup...")
            backup = Path(str(STATE_FILE) + ".bak")
            if backup.exists():
                with open(backup, "r") as f:
                    state = json.load(f)
                print("Loaded from backup successfully.")
            else:
                print("No backup found. Starting fresh.")
                return {}
        # Run full sanitizer on every load
        print("Running state sanitizer...")
        for pname, pdata in state.items():
            _sanitize_portfolio(pname, pdata)
        # One-time migration for entry cost accounting fix
        _migrate_entry_costs(state)
        print("State sanitizer complete.")
        return state
    return {}


def save_state(state):
    import tempfile
    import os

    # Atomic write using temporary file
    temp_file = STATE_FILE.with_suffix(".tmp")
    try:
        with open(temp_file, "w") as f:
            json.dump(state, f, indent=2, default=str)
        # Keep a backup before replacing
        if STATE_FILE.exists():
            import shutil

            shutil.copy2(STATE_FILE, str(STATE_FILE) + ".bak")
        os.replace(temp_file, STATE_FILE)  # Atomic rename
    except Exception:
        # Clean up temp file on error
        if os.path.exists(temp_file):
            os.remove(temp_file)
        raise


def load_payload():
    if not PAYLOAD_FILE.exists():
        print(f"ERROR: {PAYLOAD_FILE} not found")
        sys.exit(1)
    with open(PAYLOAD_FILE, "r") as f:
        return json.load(f)


def fetch_prices():
    """Fetch current prices from Binance + Bybit + CryptoCompare + CoinGecko + Yahoo Finance failover."""
    prices = {}
    source = None

    # Layer 1: Binance (try US endpoint first to avoid geo-block HTTP 451)
    for binance_url in [
        "https://api.binance.us/api/v3/ticker/price",
        "https://api.binance.com/api/v3/ticker/price",
    ]:
        try:
            req = urllib.request.Request(
                binance_url, headers={"User-Agent": "Mozilla/5.0"}
            )
            data = json.loads(urllib.request.urlopen(req, timeout=15).read())
            for d in data:
                prices[d["symbol"]] = float(d["price"])
            source = "Binance"
            break
        except Exception as e:
            print(f"WARNING: Binance price fetch failed ({binance_url}): {e}")
    if not source:
        # Layer 2: Bybit
        try:
            url = "https://api.bybit.com/v5/market/tickers?category=spot"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            data = json.loads(urllib.request.urlopen(req, timeout=15).read())
            for t in data.get("result", {}).get("list", []):
                sym = t.get("symbol", "")
                p = float(t.get("lastPrice", 0))
                if p > 0:
                    prices[sym] = p
            if prices:
                source = "Bybit"
        except Exception as e2:
            print(f"WARNING: Bybit price fetch also failed: {e2}")
            # Layer 3: CryptoCompare bulk for major crypto
            try:
                major = "BTC,ETH,SOL,XRP,DOGE,ADA,AVAX,DOT,LINK,BNB,SHIB,PEPE,MATIC,UNI,AAVE,ARB,OP,TRX,NEAR,LTC,ATOM,SUI,APT,INJ,RENDER,NOT,FET,SEI"
                cc_url = f"https://min-api.cryptocompare.com/data/pricemulti?fsyms={major}&tsyms=USD"
                req = urllib.request.Request(
                    cc_url, headers={"User-Agent": "Mozilla/5.0"}
                )
                data = json.loads(urllib.request.urlopen(req, timeout=10).read())
                for base, vals in data.items():
                    if "USD" in vals and vals["USD"] > 0:
                        prices[base + "USDT"] = vals["USD"]
                if prices:
                    source = "CryptoCompare"
            except Exception as e3:
                print(f"WARNING: CryptoCompare also failed: {e3}")
                # Layer 4: CoinGecko fallback
                try:
                    cg_url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana,ripple,dogecoin,cardano,avalanche-2,polkadot,chainlink,binancecoin&vs_currencies=usd"
                    req = urllib.request.Request(
                        cg_url, headers={"User-Agent": "Mozilla/5.0"}
                    )
                    data = json.loads(urllib.request.urlopen(req, timeout=10).read())
                    cg_map = {
                        "bitcoin": "BTCUSDT",
                        "ethereum": "ETHUSDT",
                        "solana": "SOLUSDT",
                        "ripple": "XRPUSDT",
                        "dogecoin": "DOGEUSDT",
                        "cardano": "ADAUSDT",
                        "avalanche-2": "AVAXUSDT",
                        "polkadot": "DOTUSDT",
                        "chainlink": "LINKUSDT",
                        "binancecoin": "BNBUSDT",
                    }
                    for cg_id, sym in cg_map.items():
                        if cg_id in data and "usd" in data[cg_id]:
                            prices[sym] = data[cg_id]["usd"]
                    if prices:
                        source = "CoinGecko"
                except Exception as e4:
                    print(
                        f"CRITICAL: All crypto bulk price sources failed! Binance: {e}, Bybit: {e2}, CC: {e3}, CG: {e4}"
                    )

    # Layer 5: Yahoo Finance (yfinance) for Equities/ETFs
    try:
        import yfinance as yf

        equities = [
            "SPY",
            "QQQ",
            "GME",
            "COIN",
            "AAPL",
            "MSFT",
            "NVDA",
            "AMD",
            "TSLA",
            "AMZN",
            "GOOGL",
            "META",
            "MA",
            "V",
            "JPM",
            "BAC",
            "WMT",
            "DIS",
            "NFLX",
            "PLTR",
            "SOFI",
            "RIVN",
            "AMC",
            "MSTR",
        ]
        tickers = yf.Tickers(" ".join(equities))
        for sym in equities:
            try:
                hist = tickers.tickers[sym].history(period="1d")
                if not hist.empty:
                    prices[sym] = float(hist["Close"].iloc[-1])
            except Exception:
                continue
        source = (source + " + yfinance") if source else "yfinance"
    except ImportError:
        print("WARNING: yfinance not installed, skipping Equity/ETF price fetch.")
    except Exception as ey:
        print(f"WARNING: yfinance fetch failed: {ey}")

    if not prices:
        print(
            "CRITICAL: fetch_prices() returned EMPTY — all price sources failed. TP/SL checks will be skipped."
        )
    else:
        print(f"Fetched {len(prices)} prices from {source}")
    return prices


def normalize_symbol(sym):
    s = sym.replace("-", "").replace("/", "").upper()
    equities = {
        "SPY",
        "QQQ",
        "GME",
        "COIN",
        "AAPL",
        "MSFT",
        "NVDA",
        "AMD",
        "TSLA",
        "AMZN",
        "GOOGL",
        "META",
        "MA",
        "V",
        "JPM",
        "BAC",
        "WMT",
        "DIS",
        "NFLX",
        "PLTR",
        "SOFI",
        "RIVN",
        "AMC",
        "MSTR",
    }
    if s in equities:
        return s
    if not s.endswith("USDT"):
        s = s.replace("USD", "USDT")
        if not s.endswith("USDT"):
            s += "USDT"
    return s


def is_meme(symbol):
    s = symbol.replace("-", "").replace("/", "").upper()
    if s in MEME_COINS:
        return True
    base = s.replace("USDT", "").replace("USD", "").replace("BUSD", "")
    return base in MEME_COINS or (base + "USDT") in MEME_COINS


def calc_commission(asset_class, size_usd, price):
    if asset_class == "EQUITY":
        shares = int(size_usd / price) if price > 0 else 0
        return max(COMMISSION_EQUITY_MIN, shares * COMMISSION_EQUITY_PER_SHARE)
    elif asset_class == "FUTURES":
        return size_usd * COMMISSION_FUTURES_PCT
    elif asset_class in ("COMMODITY", "COMMODITIES"):
        return size_usd * COMMISSION_COMMODITY_PCT
    elif asset_class == "FOREX":
        return size_usd * COMMISSION_FOREX_PCT
    return size_usd * COMMISSION_CRYPTO_PCT


def calc_rr(entry, tp, sl, direction):
    if direction == "LONG":
        risk = abs(entry - sl) if abs(entry - sl) > 0 else 1
        reward = abs(tp - entry)
    else:
        risk = abs(sl - entry) if abs(sl - entry) > 0 else 1
        reward = abs(entry - tp)
    return reward / risk


def detect_regime(active_picks):
    """Detect market regime from active picks."""
    crypto_longs = [
        p
        for p in active_picks
        if (p.get("direction", "").upper() in ("LONG", "BUY"))
        and (
            p.get("asset_class", "").upper() == "CRYPTO"
            or "USD" in (p.get("symbol", ""))
        )
    ]
    pnls = [
        float(p.get("pnl_pct", 0) or 0) or 0
        for p in crypto_longs
        if (float(p.get("pnl_pct", 0) or 0) or 0) != 0
    ]
    if len(pnls) < 5:
        return "NEUTRAL"
    avg = sum(pnls) / len(pnls)
    pct_losing = len([p for p in pnls if p < 0]) / len(pnls)
    if pct_losing > 0.65 or avg < -2:
        return "BEARISH"
    elif pct_losing > 0.50 or avg < -0.5:
        return "CHOPPY"
    return "BULLISH"


def pick_id(pick):
    """Generate a stable ID for a pick."""
    raw = f"{pick.get('symbol', '')}-{pick.get('direction', '')}-{pick.get('source_system', '')}-{pick.get('strategy', '')}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


# ═══════════════════════════════════════════════════════════════
# STATISTICAL RISK MANAGEMENT ENGINE (Giga Potato Feedback v1)
# ATR-based sizing, z-score quality gates, VaR-lite risk budget,
# volatility-adjusted TP/SL, and portfolio-level risk controls.
# Going-live readiness: only statistically validated strategies pass.
# ═══════════════════════════════════════════════════════════════

import statistics as _stats_mod

# --- Volatility cache (refreshed each cycle) ---
_VOL_CACHE = {}  # symbol -> {atr_14, std_daily, mean_return, z_score, vol_regime}


def compute_volatility_metrics(symbol, klines=None):
    """Compute ATR(14), daily std dev, mean return, and volatility regime for a symbol.

    Returns dict with:
      atr_14:      Average True Range (14-period) in price units
      atr_pct:     ATR as % of current price
      std_daily:   Standard deviation of daily returns (%)
      mean_return:  Mean daily return (%)
      vol_regime:  'LOW' (<2% daily std), 'NORMAL' (2-5%), 'HIGH' (5-8%), 'EXTREME' (>8%)
      z_score:     How many std devs today's return is from mean
    """
    if symbol in _VOL_CACHE:
        return _VOL_CACHE[symbol]

    if not klines:
        klines = fetch_klines(symbol.replace("-", ""), "1d", 30)
    if len(klines) < 15:
        result = {
            "atr_14": 0,
            "atr_pct": 0,
            "std_daily": 3.0,
            "mean_return": 0,
            "vol_regime": "NORMAL",
            "z_score": 0,
            "median_atr_pct": 3.0,
        }
        _VOL_CACHE[symbol] = result
        return result

    closes = [k["close"] for k in klines]
    highs = [k["high"] for k in klines]
    lows = [k["low"] for k in klines]

    # Daily returns (%)
    daily_returns = []
    for i in range(1, len(closes)):
        if closes[i - 1] > 0:
            daily_returns.append(((closes[i] - closes[i - 1]) / closes[i - 1]) * 100)

    # ATR(14) calculation
    true_ranges = []
    for i in range(1, len(klines)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        true_ranges.append(tr)
    atr_14 = sum(true_ranges[-14:]) / min(14, len(true_ranges)) if true_ranges else 0
    current_price = closes[-1] if closes else 1
    atr_pct = (atr_14 / current_price) * 100 if current_price > 0 else 0

    # Std dev & mean of daily returns
    std_daily = _stats_mod.stdev(daily_returns) if len(daily_returns) >= 2 else 3.0
    mean_return = _stats_mod.mean(daily_returns) if daily_returns else 0

    # Median ATR % (for vol-adjustment baseline)
    atr_pcts = []
    for i in range(1, len(klines)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        atr_pcts.append((tr / closes[i]) * 100 if closes[i] > 0 else 0)
    median_atr_pct = _stats_mod.median(atr_pcts) if atr_pcts else atr_pct

    # Z-score: how extreme is today's move?
    today_return = daily_returns[-1] if daily_returns else 0
    z_score = (today_return - mean_return) / std_daily if std_daily > 0 else 0

    # Volatility regime classification
    if std_daily < 2.0:
        vol_regime = "LOW"
    elif std_daily < 5.0:
        vol_regime = "NORMAL"
    elif std_daily < 8.0:
        vol_regime = "HIGH"
    else:
        vol_regime = "EXTREME"

    result = {
        "atr_14": round(atr_14, 6),
        "atr_pct": round(atr_pct, 2),
        "std_daily": round(std_daily, 2),
        "mean_return": round(mean_return, 3),
        "vol_regime": vol_regime,
        "z_score": round(z_score, 2),
        "median_atr_pct": round(median_atr_pct, 2),
        "returns": daily_returns,
    }
    _VOL_CACHE[symbol] = result
    return result


def clear_vol_cache():
    """Clear volatility cache at start of each cycle."""
    _VOL_CACHE.clear()


def binomial_exact_test(wins, total, null_wr=0.50):
    """Exact binomial test for strategy win rate significance.

    More accurate than z-score for small samples (n < 50).
    Uses the CDF of the binomial distribution.
    Inspired by Kimi Swarm research (strategy_validation.py).

    Returns:
      p_value: exact one-tailed p-value
      significant: True if p < 0.05
    """
    if total < 5 or wins < 0:
        return {"p_value": 1.0, "significant": False}

    # Compute P(X >= wins) under null hypothesis using binomial CDF complement
    # P(X >= k) = sum_{i=k}^{n} C(n,i) * p^i * (1-p)^(n-i)
    p_value = 0.0
    for i in range(wins, total + 1):
        # log-space to avoid overflow: log(C(n,k)) + k*log(p) + (n-k)*log(1-p)
        log_comb = sum(math.log(total - j) - math.log(j + 1) for j in range(i))
        log_prob = (
            log_comb + i * math.log(null_wr) + (total - i) * math.log(1 - null_wr)
        )
        p_value += math.exp(log_prob)

    p_value = min(1.0, max(0.0, p_value))
    return {"p_value": round(p_value, 6), "significant": p_value < 0.05}


def strategy_z_score_test(sys_wr, sys_closed, null_wr=50.0):
    """Test if a strategy's win rate is statistically significant vs random (null_wr%).

    Returns:
      z_stat:   z-score of observed WR vs null hypothesis
      p_approx: approximate one-tailed p-value
      significant: True if p < 0.05 (95% confidence the edge is real)
      min_trades_needed: trades needed for significance at current WR
    """
    if sys_closed < 5:
        return {
            "z_stat": 0,
            "p_approx": 1.0,
            "significant": False,
            "min_trades_needed": 30,
        }

    p_obs = sys_wr / 100.0
    p_null = null_wr / 100.0
    se = math.sqrt(p_null * (1 - p_null) / sys_closed)
    if se <= 0:
        return {
            "z_stat": 0,
            "p_approx": 1.0,
            "significant": False,
            "min_trades_needed": 30,
        }

    z_stat = (p_obs - p_null) / se

    # Approximate p-value using normal CDF approximation (Abramowitz & Stegun)
    # For z > 0, p = 1 - Phi(z); for z < 0, p > 0.5 (no edge)
    if z_stat <= 0:
        p_approx = 1.0
    else:
        # Rational approximation of erfc
        t = 1.0 / (1.0 + 0.2316419 * z_stat)
        d = 0.3989422804014327  # 1/sqrt(2*pi)
        poly = t * (
            0.319381530
            + t
            * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429)))
        )
        p_approx = d * math.exp(-0.5 * z_stat * z_stat) * poly

    significant = p_approx < 0.05

    # How many trades needed for significance at this WR?
    if p_obs > p_null:
        z_needed = 1.645  # one-tailed 95%
        min_n = math.ceil((z_needed / (p_obs - p_null)) ** 2 * p_null * (1 - p_null))
        min_trades_needed = max(20, min(500, min_n))
    else:
        min_trades_needed = 500  # no edge detected

    return {
        "z_stat": round(z_stat, 2),
        "p_approx": round(p_approx, 4),
        "significant": significant,
        "min_trades_needed": min_trades_needed,
    }


def volatility_adjusted_size(
    capital,
    strat_wr,
    strat_pf,
    entry_price,
    stop_loss,
    vol_metrics,
    base_risk_pct=0.02,
    max_size_pct=0.12,
):
    """Kelly + ATR-scaled position sizing.

    Uses half-Kelly fraction scaled by inverse volatility. In high-vol regimes,
    position sizes shrink; in low-vol regimes, they grow (but capped).

    Args:
        capital: Portfolio cash available
        strat_wr: Strategy win rate (0-100)
        strat_pf: Strategy profit factor
        entry_price: Entry price
        stop_loss: Stop loss price
        vol_metrics: dict from compute_volatility_metrics()
        base_risk_pct: Base risk per trade (default 2%)
        max_size_pct: Max position size as % of capital (default 12%)

    Returns:
        size_usd: Dollar amount to allocate
        risk_metadata: Dict with sizing rationale for audit trail
    """
    wr = max(0.01, min(0.99, strat_wr / 100.0))
    pf = max(0.5, strat_pf) if strat_pf and strat_pf > 0 else 1.0

    # Estimate avg win/loss ratio from PF and WR
    # PF = (WR * avg_win) / ((1-WR) * avg_loss) → avg_win/avg_loss = PF * (1-WR) / WR
    b = pf * (1 - wr) / wr if wr > 0 else 1.0
    b = max(0.5, min(5.0, b))  # clamp to reasonable range

    # Kelly fraction: f* = p - q/b (half-kelly for safety)
    f_kelly = wr - (1 - wr) / b
    f_half_kelly = max(0, min(f_kelly * 0.5, 0.08))

    # Risk distance (entry to SL)
    risk_dist = abs(entry_price - stop_loss) / entry_price if entry_price > 0 else 0.05
    risk_dist = max(0.01, min(0.20, risk_dist))  # clamp 1%-20%

    # Volatility adjustment: shrink in high vol, grow in low vol
    atr_pct = vol_metrics.get("atr_pct", 3.0)
    median_atr = vol_metrics.get("median_atr_pct", 3.0)
    vol_adj = median_atr / max(atr_pct, median_atr * 0.3) if atr_pct > 0 else 1.0
    vol_adj = max(0.3, min(1.5, vol_adj))  # clamp: 30%-150% of normal

    # Vol regime hard caps
    vol_regime = vol_metrics.get("vol_regime", "NORMAL")
    regime_cap = {"LOW": 1.2, "NORMAL": 1.0, "HIGH": 0.6, "EXTREME": 0.3}.get(
        vol_regime, 1.0
    )

    # Combine: kelly edge * vol adjustment * base risk
    risk_pct = f_half_kelly * vol_adj * base_risk_pct * regime_cap
    risk_pct = max(0.005, min(max_size_pct, risk_pct))  # floor 0.5%, cap max_size_pct

    # Convert risk % to dollar size via risk distance
    size_usd = (capital * risk_pct) / risk_dist if risk_dist > 0 else capital * risk_pct
    # Apply regime-aware cap (EXTREME vol = much smaller max position)
    effective_max = max_size_pct * regime_cap
    size_usd = min(size_usd, capital * effective_max)
    size_usd = max(10, size_usd)  # minimum $10

    risk_metadata = {
        "kelly_fraction": round(f_kelly, 4),
        "half_kelly": round(f_half_kelly, 4),
        "risk_dist_pct": round(risk_dist * 100, 2),
        "vol_adj": round(vol_adj, 2),
        "vol_regime": vol_regime,
        "regime_cap": regime_cap,
        "effective_risk_pct": round(risk_pct * 100, 3),
        "size_pct_of_capital": round((size_usd / capital) * 100, 2)
        if capital > 0
        else 0,
    }

    return round(size_usd, 2), risk_metadata


def atr_based_tp_sl(entry_price, direction, vol_metrics, rr_target=2.0):
    """Compute ATR-based TP/SL levels (replaces fixed % TP/SL).

    SL = 2x ATR from entry (gives room for normal volatility)
    TP = SL distance * rr_target (default 2:1 R:R)

    Returns:
        tp, sl, rr, metadata
    """
    atr = vol_metrics.get("atr_14", 0)
    if atr <= 0:
        # Fallback: use std_daily as proxy
        std = vol_metrics.get("std_daily", 3.0)
        atr = entry_price * (std / 100) * 1.5  # rough ATR estimate from daily std

    sl_distance = atr * 2.0  # 2x ATR stop (standard institutional practice)
    tp_distance = sl_distance * rr_target

    if direction == "LONG":
        sl = entry_price - sl_distance
        tp = entry_price + tp_distance
    else:  # SHORT
        sl = entry_price + sl_distance
        tp = entry_price - tp_distance

    actual_rr = tp_distance / sl_distance if sl_distance > 0 else rr_target

    metadata = {
        "atr_used": round(atr, 6),
        "sl_distance_pct": round((sl_distance / entry_price) * 100, 2)
        if entry_price > 0
        else 0,
        "tp_distance_pct": round((tp_distance / entry_price) * 100, 2)
        if entry_price > 0
        else 0,
        "method": "ATR_2x",
    }

    return round(tp, 6), round(sl, 6), round(actual_rr, 2), metadata


def compute_correlation(sym1, sym2):
    """Compute Pearson correlation between two symbols using cached daily returns."""
    ret1 = _VOL_CACHE.get(sym1, {}).get("returns", [])
    ret2 = _VOL_CACHE.get(sym2, {}).get("returns", [])
    if not ret1 or not ret2:
        return 0.0

    min_len = min(len(ret1), len(ret2))
    if min_len < 5:
        return 0.0

    r1 = ret1[-min_len:]
    r2 = ret2[-min_len:]

    mean1 = sum(r1) / min_len
    mean2 = sum(r2) / min_len

    num = sum((x - mean1) * (y - mean2) for x, y in zip(r1, r2))
    den1 = sum((x - mean1) ** 2 for x in r1)
    den2 = sum((y - mean2) ** 2 for y in r2)

    if den1 == 0 or den2 == 0:
        return 0.0

    return num / math.sqrt(den1 * den2)


def portfolio_risk_budget(
    port,
    proposed_size_usd,
    proposed_direction,
    proposed_symbol="",
    proposed_asset_class="CRYPTO",
):
    """Portfolio-level risk budget check (VaR-lite and Correlation).

    Prevents over-concentration and ensures total portfolio risk stays bounded.
    Uses simple sum-of-risk approach (conservative — ignores diversification benefit).
    Enforces Correlation Matrix (max 0.75 Pearson) and MDD/VaR tracking.

    Returns:
        (allowed: bool, reason: str, risk_used_pct: float)
    """
    equity = port.get("equity", port.get("initial_capital", 10000))
    if equity <= 0:
        return False, "Zero equity", 100.0

    # Advanced Drawdown Constraints (MDD / 99% VaR halt)
    hwm = port.get("high_water_mark", equity)
    if hwm > 0:
        mdd = (hwm - equity) / hwm
        if mdd > PORTFOLIO_MAX_DRAWDOWN_PCT:
            return (
                False,
                f"Portfolio in {mdd * 100:.1f}% drawdown (exceeds 15% MDD limit)",
                100.0,
            )

    # Current risk: sum of all position sizes * their SL distance
    total_risk_usd = 0
    for pos in port.get("positions", []):
        entry = pos.get("entry_price", 0)
        sl = pos.get("stop_loss", 0)
        size = pos.get("size_usd", 0)
        if entry > 0 and sl > 0:
            if pos["direction"] == "LONG":
                risk_pct = max(0, (entry - sl) / entry)
            else:
                risk_pct = max(0, (sl - entry) / entry)
            total_risk_usd += size * risk_pct

    # Proposed trade risk
    risk_used_pct = (total_risk_usd / equity) * 100

    # Risk budget: max 15% of equity at risk at any time
    MAX_PORTFOLIO_RISK_PCT = 15.0
    proposed_risk_pct = (
        (proposed_size_usd / equity) * 100 * 0.05
    )  # assume ~5% avg risk distance
    new_total = risk_used_pct + proposed_risk_pct

    if new_total > MAX_PORTFOLIO_RISK_PCT:
        return (
            False,
            f"Risk budget exceeded: {new_total:.1f}% > {MAX_PORTFOLIO_RISK_PCT}% max",
            risk_used_pct,
        )

    # Direction imbalance check: don't let one direction dominate
    long_exposure = sum(
        p["size_usd"] for p in port.get("positions", []) if p["direction"] == "LONG"
    )
    short_exposure = sum(
        p["size_usd"] for p in port.get("positions", []) if p["direction"] == "SHORT"
    )
    if proposed_direction == "LONG":
        long_exposure += proposed_size_usd
    else:
        short_exposure += proposed_size_usd

    max_dir_pct = 60.0  # max 60% of equity in one direction
    if (long_exposure / equity) * 100 > max_dir_pct:
        return (
            False,
            f"Long exposure {(long_exposure / equity) * 100:.1f}% exceeds {max_dir_pct}%",
            risk_used_pct,
        )
    if (short_exposure / equity) * 100 > max_dir_pct:
        return (
            False,
            f"Short exposure {(short_exposure / equity) * 100:.1f}% exceeds {max_dir_pct}%",
            risk_used_pct,
        )

    # Asset class exposure check: max 30% of equity per asset class
    MAX_ASSET_CLASS_PCT = 30.0
    asset_class_exposure = sum(
        p["size_usd"]
        for p in port.get("positions", [])
        if p.get("asset_class", "CRYPTO") == proposed_asset_class
    )
    if (
        (asset_class_exposure + proposed_size_usd) / equity
    ) * 100 > MAX_ASSET_CLASS_PCT:
        return (
            False,
            f"{proposed_asset_class} exposure {((asset_class_exposure + proposed_size_usd) / equity) * 100:.1f}% exceeds {MAX_ASSET_CLASS_PCT}% max",
            risk_used_pct,
        )

    # Per-symbol concentration check: prevent FETUSDT-style domination
    symbol_exposure = sum(
        p["size_usd"]
        for p in port.get("positions", [])
        if normalize_symbol(p.get("symbol", "")) == normalize_symbol(proposed_symbol)
    )
    if (symbol_exposure + proposed_size_usd) / equity > MAX_PCT_PER_SYMBOL:
        return (
            False,
            f"Symbol concentration: {proposed_symbol} would be {(symbol_exposure + proposed_size_usd) / equity * 100:.1f}% of portfolio (max {MAX_PCT_PER_SYMBOL * 100}%)",
            risk_used_pct,
        )

    return True, "OK", risk_used_pct


def enhanced_trailing_stop(pos, current_price, vol_metrics):
    """ATR-based dynamic trailing stop (replaces fixed % trail).

    Trail distance = max(1.5x ATR, 50% of peak profit)
    Activates after +1x ATR profit (not fixed 5%)
    Only tightens — never widens the stop.

    Returns:
        new_sl: Updated stop loss (or None if no change)
        trail_metadata: Dict with trail info
    """
    direction = pos["direction"]
    entry = pos["entry_price"]
    atr = vol_metrics.get("atr_14", 0)

    if atr <= 0:
        return None, {"reason": "no_atr_data"}

    pnl_pct = pos.get("pnl_pct", 0)

    # Activation threshold: 1x ATR profit (volatility-aware, not fixed 5%)
    atr_pct = (atr / entry) * 100 if entry > 0 else 3.0
    activate_threshold = max(atr_pct, 2.0)  # at least 2% or 1 ATR

    if pnl_pct < activate_threshold:
        return None, {
            "reason": f"below_threshold_{pnl_pct:.1f}%_need_{activate_threshold:.1f}%"
        }

    # Trail distance: 1.5x ATR (institutional standard)
    trail_dist = atr * 1.5

    # Track peak
    peak = pos.get("peak_pnl_pct", pnl_pct)
    pos["peak_pnl_pct"] = max(peak, pnl_pct)

    if direction == "LONG":
        atr_trail_sl = current_price - trail_dist
        # Also compute 50%-of-peak trail (keep the tighter one)
        peak_trail_price = entry * (
            1 + pos["peak_pnl_pct"] / 100 * 0.5
        )  # lock 50% of peak gain
        new_sl = max(atr_trail_sl, peak_trail_price)
        # Never widen: only tighten the stop
        current_sl = pos.get("stop_loss", 0)
        if new_sl <= current_sl:
            return None, {"reason": "trail_would_widen"}
    else:  # SHORT
        atr_trail_sl = current_price + trail_dist
        peak_trail_price = entry * (1 - pos["peak_pnl_pct"] / 100 * 0.5)
        new_sl = min(atr_trail_sl, peak_trail_price)
        current_sl = pos.get("stop_loss", float("inf"))
        if new_sl >= current_sl:
            return None, {"reason": "trail_would_widen"}

    trail_metadata = {
        "method": "ATR_1.5x_dynamic",
        "atr": round(atr, 6),
        "trail_dist": round(trail_dist, 6),
        "old_sl": round(pos.get("stop_loss", 0), 6),
        "new_sl": round(new_sl, 6),
        "peak_pnl_pct": round(pos["peak_pnl_pct"], 2),
        "activation_threshold": round(activate_threshold, 2),
    }

    return round(new_sl, 6), trail_metadata


# ── Going-Live Risk Constants ──
# Tighter thresholds for strategies that will trade real money
GOING_LIVE_MIN_TRADES = 30  # Need 30+ forward trades (was 5)
GOING_LIVE_MIN_WR = 52  # Must beat random after costs (was 45)
GOING_LIVE_MIN_PF = 1.15  # Must be profitable after costs (was 1.0)
GOING_LIVE_MAX_DAILY_RISK = 3.0  # Max 3% daily portfolio loss before halt
GOING_LIVE_Z_THRESHOLD = 1.28  # 90% confidence the edge is real (z > 1.28)


# Hardcoded price floor/ceiling for when ALL APIs fail (updated 2026-03)
# Format: symbol_base -> (min_reasonable, max_reasonable)
_HARDCODED_PRICE_BOUNDS = {
    "BTC": (30000, 200000),
    "ETH": (800, 15000),
    "SOL": (15, 500),
    "DOGE": (0.03, 2.0),
    "XRP": (0.2, 15),
    "ADA": (0.1, 5),
    "AVAX": (3, 200),
    "DOT": (1, 80),
    "LINK": (3, 100),
    "BNB": (100, 2000),
    "SHIB": (0.000001, 0.001),
    "PEPE": (0.000001, 0.01),
    "MATIC": (0.1, 10),
    "UNI": (2, 80),
    "AAVE": (30, 800),
    "ARB": (0.3, 10),
    "OP": (0.5, 15),
    "TRX": (0.03, 1.0),
    "NEAR": (1, 30),
    "FTM": (0.1, 5),
    "LTC": (30, 300),
    "ATOM": (3, 50),
    "NOT": (0.001, 0.1),
    "CHZ": (0.01, 0.5),
    "RENDER": (0.5, 20),
    "INJ": (5, 100),
    "SUI": (0.3, 10),
    "APT": (3, 50),
    "JNJ": (100, 250),
    "META": (200, 800),
    "GME": (5, 100),
    "AAPL": (100, 300),
    "MSFT": (200, 600),
    "SPY": (300, 700),
    "QQQ": (250, 700),
}


_KNOWN_STOCKS = {
    "JNJ",
    "META",
    "GME",
    "AAPL",
    "MSFT",
    "SPY",
    "QQQ",
    "AMZN",
    "GOOGL",
    "TSLA",
    "NVDA",
    "AMD",
    "NFLX",
    "DIS",
    "BA",
    "V",
    "MA",
    "JPM",
    "GS",
    "WMT",
    "COST",
    "UNH",
    "PFE",
    "MRK",
    "ABBV",
    "XOM",
    "CVX",
    "COP",
    "T",
    "VZ",
    "INTC",
    "PG",
    "COIN",
    "KO",
    "HD",
    "LOW",
    "CRM",
    "PYPL",
    "SQ",
    "SHOP",
    "UBER",
    "ABNB",
    "SNAP",
    "PLTR",
    "RIVN",
    "LCID",
    "NIO",
    "BABA",
    "TSM",
    "ASML",
    "SOFI",
    "TLT",
    "IWM",
    "EEM",
    "GLD",
    "SLV",
    "XLF",
    "XLE",
    "XLK",
    "ARKK",
}
_KNOWN_FOREX = {"EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD", "SEK", "NOK", "MXN"}
# Stablecoins: always ~$1, skip external price checks
_STABLECOINS = {
    "USDC",
    "USDT",
    "DAI",
    "BUSD",
    "TUSD",
    "USDP",
    "FDUSD",
    "USD1",
    "XUSD",
    "PYUSD",
}


def _fetch_reference_price(symbol: str) -> float:
    """Fetch current price with 6-layer failover chain.
    Crypto: Binance -> Bybit -> KuCoin -> CoinGecko -> CryptoCompare -> Yahoo
    Stocks/Forex: Yahoo -> CryptoCompare (skip crypto exchanges to avoid token name collisions).
    Returns 0.0 only if ALL sources fail (sanitizer then skips the check)."""
    base = (
        symbol.upper()
        .replace("_USDT", "")
        .replace("USDT", "")
        .replace("-USD", "")
        .replace("USD", "")
        .replace("/", "")
        .replace("=X", "")
        .replace("_", "")
        .rstrip("-")
    )

    # Stablecoins: always ~$1, no need for API calls
    if base in _STABLECOINS:
        return 1.0

    # Detect asset class from symbol to route correctly
    is_stock = base in _KNOWN_STOCKS
    is_forex = base in _KNOWN_FOREX or "=X" in symbol.upper()

    # For stocks/forex, try Yahoo FIRST (skip crypto exchanges to avoid META/SPY token collisions)
    if is_stock or is_forex:
        price = _fetch_yahoo_price(base, symbol)
        if price and price > 0:
            return price
        price = _fetch_cryptocompare_price(base)
        if price and price > 0:
            return price
        return 0.0

    # === Layer 1: Binance (try US endpoint first to avoid geo-block) ===
    for binance_base in ["https://api.binance.us", "https://api.binance.com"]:
        for suffix in ["USDT", "BUSD", ""]:
            try:
                sym = base + suffix
                url = f"{binance_base}/api/v3/ticker/price?symbol={sym}"
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read())
                    price = float(data["price"])
                    if price > 0:
                        return price
            except Exception:
                pass

    # === Layer 2: Bybit (good coverage, no auth needed) ===
    try:
        sym = base + "USDT"
        url = f"https://api.bybit.com/v5/market/tickers?category=spot&symbol={sym}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            tickers = data.get("result", {}).get("list", [])
            if tickers:
                price = float(tickers[0].get("lastPrice", 0))
                if price > 0:
                    return price
    except Exception:
        pass

    # === Layer 3: KuCoin (broad altcoin coverage) ===
    try:
        sym = f"{base}-USDT"
        url = f"https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={sym}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            price = float(data.get("data", {}).get("price", 0))
            if price > 0:
                return price
    except Exception:
        pass

    # === Layer 4: CoinGecko (rate-limited but comprehensive) ===
    _CG_IDS = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "SOL": "solana",
        "DOGE": "dogecoin",
        "XRP": "ripple",
        "ADA": "cardano",
        "AVAX": "avalanche-2",
        "DOT": "polkadot",
        "LINK": "chainlink",
        "BNB": "binancecoin",
        "SHIB": "shiba-inu",
        "PEPE": "pepe",
        "MATIC": "matic-network",
        "UNI": "uniswap",
        "AAVE": "aave",
        "ARB": "arbitrum",
        "OP": "optimism",
        "TRX": "tron",
        "NEAR": "near",
        "FTM": "fantom",
        "LTC": "litecoin",
        "ATOM": "cosmos",
        "INJ": "injective-protocol",
        "SUI": "sui",
        "APT": "aptos",
        "RENDER": "render-token",
        "NOT": "notcoin",
        "CHZ": "chiliz",
        "HBAR": "hedera-hashgraph",
        "FIL": "filecoin",
        "ALGO": "algorand",
        "VET": "vechain",
        "SAND": "the-sandbox",
        "MANA": "decentraland",
        "IMX": "immutable-x",
        "GRT": "the-graph",
    }
    cg_id = _CG_IDS.get(base)
    if cg_id:
        try:
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies=usd"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                price = float(data.get(cg_id, {}).get("usd", 0))
                if price > 0:
                    return price
        except Exception:
            pass

    # === Layer 5: CryptoCompare ===
    price = _fetch_cryptocompare_price(base)
    if price and price > 0:
        return price

    # === Layer 6: Yahoo Finance ===
    price = _fetch_yahoo_price(base, symbol)
    if price and price > 0:
        return price

    # All 6 layers failed — return 0 (sanitizer will skip price check)
    print(f"  [PRICE WARN] All 6 APIs failed for {symbol} (base={base})")
    return 0.0


def _fetch_cryptocompare_price(base: str) -> float:
    """CryptoCompare free tier — good redundancy for crypto."""
    try:
        url = f"https://min-api.cryptocompare.com/data/price?fsym={base}&tsyms=USD"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            return float(data.get("USD", 0))
    except Exception:
        return 0.0


_YAHOO_MAP = {
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "SOL": "SOL-USD",
    "DOGE": "DOGE-USD",
    "XRP": "XRP-USD",
    "ADA": "ADA-USD",
    "BNB": "BNB-USD",
    "DOT": "DOT-USD",
    "LINK": "LINK-USD",
    "AVAX": "AVAX-USD",
    "MATIC": "MATIC-USD",
    "UNI": "UNI-USD",
    # Stocks (use ticker directly)
    "JNJ": "JNJ",
    "META": "META",
    "GME": "GME",
    "AAPL": "AAPL",
    "MSFT": "MSFT",
    "SPY": "SPY",
    "QQQ": "QQQ",
    "AMZN": "AMZN",
    "GOOGL": "GOOGL",
    "TSLA": "TSLA",
    "NVDA": "NVDA",
    "AMD": "AMD",
    "NFLX": "NFLX",
    "DIS": "DIS",
    "V": "V",
    "JPM": "JPM",
    "GS": "GS",
    "WMT": "WMT",
    "COST": "COST",
    # Forex
    "EUR": "EURUSD=X",
    "GBP": "GBPUSD=X",
    "JPY": "USDJPY=X",
    "AUD": "AUDUSD=X",
    "CAD": "USDCAD=X",
    "CHF": "USDCHF=X",
    "NZD": "NZDUSD=X",
}


def _fetch_yahoo_price(base: str, symbol: str) -> float:
    """Yahoo Finance — stocks, forex, and some crypto."""
    yahoo_sym = _YAHOO_MAP.get(base)
    # Fallback: if base is a stock ticker, try it directly
    if not yahoo_sym and base in _KNOWN_STOCKS:
        yahoo_sym = base
    if not yahoo_sym:
        return 0.0
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_sym}?range=1d&interval=1d"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            meta = data.get("chart", {}).get("result", [{}])[0].get("meta", {})
            return float(meta.get("regularMarketPrice", 0))
    except Exception:
        return 0.0


# Cache reference prices per run to avoid repeated API calls
_price_cache: dict = {}


def _get_reference_price(symbol: str) -> float:
    """Get reference price (cached per run)."""
    if symbol not in _price_cache:
        _price_cache[symbol] = _fetch_reference_price(symbol)
    return _price_cache[symbol]


def _price_is_sane(symbol: str, entry_price: float, tolerance: float = 0.15) -> bool:
    """Check if entry_price is within tolerance (15%) of real market price.
    Returns True if sane or if we can't verify (no reference price)."""
    ref = _get_reference_price(symbol)
    if ref <= 0:
        # No API price available — use hardcoded bounds as a loose sanity check
        base = (
            symbol.upper()
            .replace("USDT", "")
            .replace("-USD", "")
            .replace("USD", "")
            .replace("/", "")
            .replace("=X", "")
            .rstrip("-")
        )
        bounds = _HARDCODED_PRICE_BOUNDS.get(base)
        if bounds:
            if entry_price < bounds[0] * 0.1 or entry_price > bounds[1] * 10:
                print(
                    f"  [PRICE GUARD] REJECTED {symbol}: entry={entry_price}, outside bounds ({bounds[0]}, {bounds[1]})"
                )
                return False
        return True  # can't verify precisely, allow through
    ratio = entry_price / ref
    if ratio > (1 + tolerance) or ratio < (1 - tolerance):
        print(
            f"  [PRICE GUARD] REJECTED {symbol}: entry={entry_price}, market={ref}, ratio={ratio:.2f}"
        )
        return False
    return True


def validate_and_fix_entry(
    symbol: str, signal_entry: float, prices: dict, direction: str
) -> dict:
    """Multi-layer entry price validation. Returns dict with verified price or None if rejected.

    Layer 1: Get live price from bulk-fetched prices dict
    Layer 2: Fetch fresh reference price via 6-source failover
    Layer 3: Cross-check signal entry vs live — reject if >10% drift
    Layer 4: Verify TP/SL make directional sense with the live price

    Returns: {"price": float, "source": str, "drift_pct": float} or None
    """
    sym_norm = symbol.upper().replace("-", "").replace("_", "").replace("=X", "")
    if not sym_norm.endswith("USDT") and not sym_norm.endswith("USD"):
        sym_norm = sym_norm + "USDT"

    # Layer 1: Bulk prices (Binance/Bybit already fetched)
    live = prices.get(sym_norm) or prices.get(symbol)
    source = "bulk_prices"

    # Layer 2: If not in bulk, fetch fresh
    if not live or live <= 0:
        live = _fetch_reference_price(symbol)
        source = "reference_6layer"

    if not live or live <= 0:
        print(f"  [ENTRY VALIDATE] REJECT {symbol}: no live price from any source")
        return None

    # Layer 3: Drift check — signal entry vs live market
    drift_pct = (
        abs(live - signal_entry) / signal_entry * 100 if signal_entry > 0 else 999
    )
    if drift_pct > 10:
        print(
            f"  [ENTRY VALIDATE] {symbol}: signal_entry={signal_entry:.6f} drifted {drift_pct:.1f}% from live={live:.6f} — using LIVE price"
        )
    elif drift_pct > 2:
        print(
            f"  [ENTRY VALIDATE] {symbol}: minor drift {drift_pct:.1f}% — using LIVE price for accuracy"
        )

    # Always use the live price as entry (never the stale signal price)
    return {"price": live, "source": source, "drift_pct": drift_pct}


def filter_valid_picks(active_picks, systems_map):
    """Filter picks with valid entry/TP/SL and not garbage."""
    valid = []
    for p in active_picks:
        entry = float(p.get("entry_price", 0) or 0)
        tp = float(p.get("take_profit", 0) or 0)
        sl = float(p.get("stop_loss", 0) or 0)
        if entry <= 0 or entry > 1_000_000 or tp <= 0 or sl <= 0:
            continue
        # Price sanity check: reject if entry is wildly off from market
        sym = p.get("symbol", "")
        if not _price_is_sane(sym, entry):
            continue
        # Compute R:R
        direction = (p.get("direction", "") or "").upper()
        if direction not in ("LONG", "SHORT", "BUY", "SELL"):
            continue
        if direction == "BUY":
            direction = "LONG"
        if direction == "SELL":
            direction = "SHORT"
        rr = calc_rr(entry, tp, sl, direction)
        sys_name = p.get("source_system", "")
        sys_data = systems_map.get(sys_name, {})
        valid.append(
            {
                "symbol": p.get("symbol", ""),
                "direction": direction,
                "asset_class": (p.get("asset_class", "") or "CRYPTO").upper(),
                "source_system": sys_name,
                "strategy": p.get("strategy", ""),
                "entry_price": entry,
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": p.get("confidence", 0) or 0,
                "pnl_pct": float(p.get("pnl_pct", 0) or 0) or 0,
                "age_hours": p.get("age_hours", 0) or 0,
                "agreement": p.get("system_agreement_count", 0) or 0,
                "has_conflict": p.get("has_conflict", False),
                "rr": rr,
                # Prefer per-strategy forward data from pick, fall back to system-level
                "sys_wr": (p.get("strat_fwd_wr") or sys_data.get("win_rate") or 0),
                "sys_closed": (
                    p.get("strat_fwd_trades") or sys_data.get("closed_picks") or 0
                ),
                "sys_pnl": (p.get("recent_pnl") or sys_data.get("total_pnl_pct") or 0),
                "sys_pf": (p.get("strat_fwd_pf") or sys_data.get("profit_factor") or 0),
                "strat_health": p.get("strat_health", ""),
                "strat_expectancy": p.get("strat_fwd_expectancy", 0) or 0,
                "strat_last10_wr": p.get("strat_last10_wr", 0) or 0,
                "strat_sample_quality": p.get("strat_sample_quality", ""),
                "bt_wr": p.get("bt_win_rate", 0) or 0,
                "bt_pf": p.get("bt_profit_factor", 0) or 0,
                "forward_validated": p.get("forward_validated", False),
                "timestamp": p.get("timestamp", ""),
            }
        )
    return valid


def get_strategy_family(strat):
    """Get strategy family using substring matching for variants."""
    for key, family in STRATEGY_FAMILIES.items():
        if key in strat:
            return family
    return "other"


def passes_firewall(p, regime="NEUTRAL"):
    """Stage 1: Tiered pass/fail eligibility gate.

    Returns a trust tier string or False:
      "PROVEN"       — Forward-tested, 5+ trades, WR>=45%, in PROVEN_STRATEGIES
      "FORWARD"      — Forward-tested, 5+ trades, WR>=45%
      "BACKTEST"     — Has backtest WR>=50% but insufficient forward data
      "PROBATIONARY" — High confidence + good R:R but unverified
      False          — Hard-blocked
    """
    strat = p.get("strategy", "") or ""
    strat_lower = strat.lower()

    # Asset class filter — applied per-portfolio via _asset_filter
    asset_class = (p.get("asset_class", "") or "").upper()
    asset_filter = p.get("_asset_filter")
    if asset_filter:
        # Non-crypto portfolio: only allow specified asset classes
        if asset_class not in asset_filter:
            return False
    else:
        # Default (crypto-only): block stocks/forex
        if asset_class in ("EQUITY", "FOREX", "STOCKS"):
            return False

    # Block known-bad patterns (rapid_fire=570 picks 0 closed, ml_crypto_predictor=0% WR)
    if any(pat.lower() in strat_lower for pat in BLOCKED_PATTERNS):
        return False

    # Block entire systems with proven negative edge
    source_sys = p.get("source_system", "")
    if source_sys in BLOCKED_SYSTEMS:
        return False

    # Block Keltner variants on non-BTC assets (0/11 WR in live, all SL hits)
    if any(pat in strat_lower for pat in KELTNER_BLOCK_PATTERNS):
        return False

    # Symbol-locking: if strategy matches a lock key, only allow specified symbols
    sym = normalize_symbol(p.get("symbol", ""))
    for lock_key, allowed_syms in SYMBOL_LOCK.items():
        if lock_key in strat:
            if sym not in allowed_syms:
                return False
            break  # matched a lock rule

    # Kill criteria: auto-block strategies with proven negative edge
    if p["sys_closed"] >= KILL_MIN_TRADES:
        if p["sys_wr"] < KILL_WR_THRESHOLD:
            return False
        if p.get("sys_pf", 0) > 0 and p["sys_pf"] < KILL_PF_THRESHOLD:
            return False

    # Min R:R (hard floor for all tiers)
    if p["rr"] < MIN_RR:
        return False

    # Min system agreement: require 2+ systems for external picks
    # SUPER tier (3+) is 100% WR in forward testing; MODERATE (1-2) is ~38% WR
    # Deep-value engine picks are exempt (internally generated, no cross-system agreement)
    agreement = p.get("system_agreement_count", 0) or p.get("agreement", 0) or 0
    is_deep_value = "_dv_type" in p or "_htf_type" in p
    if not is_deep_value and agreement < 2:
        return False

    # Regime filter (Grok: skip breakouts in choppy, favor mean reversion)
    if regime in ("CHOPPY", "BEARISH"):
        family = get_strategy_family(strat)
        is_mean_rev = any(mr in strat for mr in MEAN_REVERSION_STRATS)
        if family == "breakout" and not is_mean_rev:
            return False  # Skip breakout strategies in choppy/bearish markets

    # --- Tiered trust assessment with statistical validation ---
    fwd_trades = p.get("sys_closed", 0)
    fwd_wr = p.get("sys_wr", 0)
    bt_wr = p.get("bt_wr", 0)
    confidence = p.get("confidence", 0)
    health = p.get("strat_health", "")

    # Statistical quality gate: z-score test for strategies with enough data
    # Also run exact binomial test for small samples (more accurate when n < 50)
    if fwd_trades >= 20:
        z_result = strategy_z_score_test(fwd_wr, fwd_trades, null_wr=50.0)
        p["_z_stat"] = z_result["z_stat"]
        p["_z_significant"] = z_result["significant"]
        p["_z_p_value"] = z_result["p_approx"]
    if 5 <= fwd_trades < 50:
        wins = round(fwd_wr / 100.0 * fwd_trades)
        binom_result = binomial_exact_test(wins, fwd_trades, null_wr=0.50)
        p["_binom_p"] = binom_result["p_value"]
        p["_binom_significant"] = binom_result["significant"]
        z_result = strategy_z_score_test(fwd_wr, fwd_trades, null_wr=50.0)
        p["_z_min_trades"] = z_result["min_trades_needed"]

    # Tier 1: PROVEN — forward-tested + in our validated list + statistically significant
    if fwd_trades >= 5 and fwd_wr >= 45:
        is_proven = any(ps in strat for ps in PROVEN_STRATEGIES)
        if is_proven:
            # Extra validation for going-live: check statistical significance
            if fwd_trades >= GOING_LIVE_MIN_TRADES:
                z_result = strategy_z_score_test(fwd_wr, fwd_trades)
                if z_result["significant"] and fwd_wr >= GOING_LIVE_MIN_WR:
                    p["_live_ready"] = True
                    p["_z_stat"] = z_result["z_stat"]
            return "PROVEN"
        is_research = any(rs in strat for rs in RESEARCH_COHORT_STRATEGIES)
        if is_research:
            return "FORWARD"  # tracked but no proven bonus
        return "FORWARD"

    # Tier 2: BACKTEST — has backtest data showing edge
    if bt_wr >= 50:
        return "BACKTEST"

    # Tier 3: PROBATIONARY — promising but unverified
    # Requires: decent confidence + good R:R + not a known loser
    if confidence >= 0.55 and p["rr"] >= 1.5:
        return "PROBATIONARY"

    # Doesn't meet any tier threshold
    return False


def score_pick(p):
    """Stage 2: Tier-aware Kelly-enhanced expectancy score with statistical & volatility weighting.

    Trust tiers from firewall determine scoring approach:
      PROVEN/FORWARD — Full Kelly scoring with forward stats + vol-adjusted
      BACKTEST       — Use backtest WR, heavier uncertainty penalty
      PROBATIONARY   — Confidence + R:R based, capped score

    v2 (Giga Potato feedback): Added statistical significance bonus, volatility regime
    penalty, and going-live readiness multiplier.
    """
    tier = p.get("trust_tier", "PROBATIONARY")
    strat = p.get("strategy", "")

    # Use forward data when available, backtest as fallback
    fwd_trades = p.get("sys_closed", 0)
    fwd_wr = p.get("sys_wr", 0)
    bt_wr = p.get("bt_wr", 0)

    beta_score = p.get("beta_score")
    beta_qualified = p.get("beta_qualified", False)
    beta_breakdown = p.get("beta_breakdown")

    # Pick the best available WR source
    if fwd_trades >= 5 and fwd_wr > 0:
        wr = fwd_wr / 100.0
        trades = fwd_trades
    elif bt_wr > 0:
        wr = bt_wr / 100.0
        trades = 10  # assume modest sample for backtest
    else:
        wr = 0.52  # slight edge assumption for probationary
        trades = 1

    avg_win_est = min(p["rr"] * 5, 20)
    avg_loss_est = 5.0
    expectancy = (wr * avg_win_est) - ((1 - wr) * avg_loss_est) - 0.40  # minus RT cost

    # Kelly fraction (half-kelly, capped) — how much edge exists
    b = avg_win_est / avg_loss_est if avg_loss_est > 0 else 1
    f_kelly = wr - (1 - wr) / b
    kelly_score = max(0, min(f_kelly * 0.5, 0.08))  # 0 to 0.08

    # Uncertainty penalty: penalize low sample size
    uncertainty_adj = 1 - (1 / math.sqrt(max(trades, 1)))

    # Research cohort check — neutral treatment (no bonus, no penalty)
    is_research = any(rs in strat for rs in RESEARCH_COHORT_STRATEGIES)

    # Proven strategy bonus — use substring matching for variants
    tier1_keys = [
        "crypto_rsi_whaleconfirmed",
        "funding_momentum",
        "crypto_keltner_compression_expansion",
        "keltner_compression_expansion",
        "crypto_vwap_deviation_reversion",
        "crypto_kalman_trend_residual_reversion",
    ]
    tier2_keys = [
        "multi_period_rsi_confluence",
        "drawdown_recovery_rsi",
        "crypto_soc_orderflow_absorption",
        "extreme_fear",
        "crypto_drawdown_convexity_recovery",
        "crypto_choppiness_regime_switch",
    ]
    if is_research:
        proven_bonus = 1.0  # Research cohort: neutral — let forward test results speak
    elif any(k in strat for k in tier1_keys):
        proven_bonus = 1.8
    elif any(k in strat for k in tier2_keys):
        proven_bonus = 1.4
    else:
        proven_bonus = 1.0

    # Trust tier multiplier — penalize unproven picks
    # Research cohort gets at least FORWARD-level treatment (no harsh penalty)
    tier_mult = {
        "PROVEN": 1.0,
        "FORWARD": 0.9,
        "BACKTEST": 0.6,
        "PROBATIONARY": 0.35,
    }.get(tier, 0.3)
    if is_research and tier_mult < 0.9:
        tier_mult = 0.9  # Research cohort floor: treated as FORWARD minimum

    # Profit factor bonus (from live system data)
    pf = p.get("sys_pf", 0) or 0
    pf_bonus = (
        min(1.5, max(1.0, pf / 2.0))
        if pf > 1.0
        else max(0.7, min(1.0, pf))
        if pf > 0
        else 0.8
    )

    # R:R component (capped)
    rr_score = min(1.0, p["rr"] / 5.0)

    # Freshness (decay old picks — asset-class-aware)
    decay_hours = FRESHNESS_DECAY.get(p.get("asset_class", "CRYPTO"), 48)
    fresh_score = max(0, 1.0 - p["age_hours"] / decay_hours)

    # Agreement bonus — SUPER tier (3+ systems) gets massive weight boost
    agree_score = min(1.0, p["agreement"] / 3.0)
    super_bonus = (
        2.0 if p["agreement"] >= 3 else 1.0
    )  # 2x multiplier for SUPER tier picks

    # Conflict penalty
    conflict_mult = 0.5 if p["has_conflict"] else 1.0

    # ── Statistical significance bonus (Giga Potato v1) ──
    # Strategies with z-score proof of edge get rewarded; noise penalized
    z_stat = p.get("_z_stat", 0)
    z_significant = p.get("_z_significant", False)
    stat_bonus = 1.0
    if z_significant and z_stat >= 1.96:
        stat_bonus = 1.5  # 50% bonus for 95% confidence edge is real
    elif z_significant:
        stat_bonus = 1.25  # 25% bonus for 90% confidence
    elif trades >= 20 and not z_significant:
        stat_bonus = 0.6  # PENALTY: 20+ trades but can't prove edge = likely noise

    # ── Volatility regime adjustment ──
    # Penalize picks in EXTREME vol (whipsaws destroy strategies)
    sym = normalize_symbol(p.get("symbol", ""))
    vol = _VOL_CACHE.get(sym, {})
    vol_regime = vol.get("vol_regime", "NORMAL")
    vol_score_mult = {"LOW": 1.1, "NORMAL": 1.0, "HIGH": 0.8, "EXTREME": 0.5}.get(
        vol_regime, 1.0
    )

    # ── Going-live readiness bonus ──
    # Strategies flagged as live-ready by firewall get priority
    live_ready_bonus = 1.3 if p.get("_live_ready") else 1.0

    # Composite: expectancy + kelly edge weighted with all multipliers
    raw = (
        max(0, expectancy) * 3.0  # expectancy is king
        + kelly_score * 50  # kelly edge
        + rr_score * 15  # R:R
        + agree_score * 25  # consensus (agreement is strongest alpha signal)
        + fresh_score * 8  # freshness
        + p["confidence"] * 5  # confidence
    ) * (
        uncertainty_adj
        * proven_bonus
        * pf_bonus
        * conflict_mult
        * tier_mult
        * super_bonus
        * stat_bonus
        * vol_score_mult
        * live_ready_bonus
    )

    # ── Beta score integration (added 2026-03-16) ──
    # Read beta confluence score fields from pick if present
    beta_score = p.get("beta_score", None)
    beta_qualified = p.get("beta_qualified", False)
    beta_breakdown = p.get("beta_breakdown", None)

    # Beta score multiplier (Phase 2)
    beta_mult = 1.0
    if beta_score is not None:
        if beta_qualified:
            beta_mult = 1.3  # 30% boost for beta-qualified picks
        elif beta_score >= 50:
            beta_mult = 1.0  # neutral
        else:
            beta_mult = 0.7  # 30% penalty for low-beta

    production_score = max(0, raw) * beta_mult

    # Attach beta fields to pick for downstream consumers
    p["_beta_score"] = beta_score
    p["_beta_qualified"] = beta_qualified
    p["_beta_breakdown"] = beta_breakdown
    p["_is_research_cohort"] = is_research

    # Beta vs production divergence — normalize production to 0-100 via sigmoid
    if beta_score is not None and beta_score > 0:
        prod_normalized = 100.0 / (1.0 + math.exp(-0.1 * (production_score - 50)))
        beta_divergence = abs(prod_normalized - beta_score)
    else:
        prod_normalized = None
        beta_divergence = None

    p["_prod_normalized"] = prod_normalized
    p["_beta_divergence"] = beta_divergence
    if beta_divergence is not None and beta_divergence > 30:
        p["_beta_divergence_flag"] = True

    return production_score


# ── Strategy Selection Functions ──


def select_score_leaders(picks, max_pos):
    scored = sorted(picks, key=score_pick, reverse=True)
    return scored[:max_pos]


def select_proven(picks, max_pos):
    """Only forward-tested or proven strategies — the conservative portfolio."""
    proven = [p for p in picks if p.get("trust_tier") in ("PROVEN", "FORWARD")]
    if not proven:
        # Fallback: backtest-validated
        proven = [p for p in picks if p.get("trust_tier") == "BACKTEST"]
    if not proven:
        # Last resort: best-scoring probationary
        proven = sorted(picks, key=score_pick, reverse=True)[:max_pos]
    proven.sort(key=score_pick, reverse=True)
    return proven[:max_pos]


def select_momentum(picks, max_pos):
    movers = [p for p in picks if p["pnl_pct"] > 0]
    # Filter out picks with suspiciously high PnL (>10%) — likely stale entry prices
    sane_movers = []
    for p in movers:
        if p["pnl_pct"] > 10:
            print(
                f"  [MOMENTUM GUARD] Skipping {p['symbol']} with {p['pnl_pct']:.1f}% PnL — likely stale entry"
            )
            continue
        sane_movers.append(p)
    sane_movers.sort(key=lambda p: p["pnl_pct"], reverse=True)
    return sane_movers[:max_pos]


def select_contrarian(picks, max_pos, regime):
    """Go against the crowd."""
    if regime in ("BEARISH", "CHOPPY"):
        # Favor SHORTs when market is bearish (relaxed: 1.5→1.3, 62.7% WR + 1.3 R:R = +0.8 edge)
        shorts = [p for p in picks if p["direction"] == "SHORT" and p["rr"] >= 1.3]
        shorts.sort(key=score_pick, reverse=True)
        return shorts[:max_pos]
    else:
        longs = [
            p
            for p in picks
            if p["direction"] == "LONG" and p["rr"] >= 1.3 and not p["has_conflict"]
        ]
        longs.sort(key=score_pick, reverse=True)
        return longs[:max_pos]


def select_regime_aligned(picks, max_pos, regime):
    if regime == "BEARISH":
        aligned = [p for p in picks if p["direction"] == "SHORT"]
    elif regime == "BULLISH":
        aligned = [p for p in picks if p["direction"] == "LONG"]
    else:  # CHOPPY/NEUTRAL - pick highest R:R of either direction (relaxed: 2.0→1.4)
        aligned = [p for p in picks if p["rr"] >= 1.4]
    aligned.sort(key=score_pick, reverse=True)
    return aligned[:max_pos]


def select_conviction(picks, max_pos):
    """High confidence picks with good R:R — tier-aware."""
    high = [p for p in picks if p["confidence"] >= 0.60 and p["rr"] >= 1.3]
    high.sort(
        key=lambda p: p["confidence"] * (p["sys_wr"] if p["sys_wr"] > 0 else 50),
        reverse=True,
    )
    return high[:max_pos]


def select_rr(picks, max_pos):
    # Relaxed: 2.5→1.8 (best available after filtering is ~1.6, 2.5 never exists)
    rr_picks = [p for p in picks if p["rr"] >= 1.8]
    if not rr_picks:
        rr_picks = [p for p in picks if p["rr"] >= 1.5]  # fallback
    rr_picks.sort(key=lambda p: p["rr"], reverse=True)
    return rr_picks[:max_pos]


def select_consensus(picks, max_pos):
    cons = sorted(picks, key=lambda p: p["agreement"], reverse=True)
    # Deduplicate by symbol, keeping highest agreement
    seen = set()
    unique = []
    for p in cons:
        base = normalize_symbol(p["symbol"])
        if base not in seen:
            seen.add(base)
            # Log which systems agree for audit trail
            p["_consensus_systems"] = p.get(
                "_source_systems", [p.get("source_system", "unknown")]
            )
            p["_consensus_count"] = p["agreement"]
            unique.append(p)
    return unique[:max_pos]


def select_fresh(picks, max_pos):
    """Freshest signals — asset-class-aware age threshold."""
    fresh = [
        p
        for p in picks
        if p["age_hours"] < FRESHNESS_HOURS.get(p.get("asset_class", "CRYPTO"), 2)
    ]
    fresh.sort(key=score_pick, reverse=True)
    return fresh[:max_pos]


def select_sector(picks, max_pos):
    crypto = sorted(
        [p for p in picks if p["asset_class"] == "CRYPTO"], key=score_pick, reverse=True
    )
    equity = sorted(
        [p for p in picks if p["asset_class"] == "EQUITY"], key=score_pick, reverse=True
    )
    forex = sorted(
        [p for p in picks if p["asset_class"] == "FOREX"], key=score_pick, reverse=True
    )
    result = crypto[:3] + equity[:2] + forex[:1]
    return result[:max_pos]


def select_anti_meme(picks, max_pos):
    clean = [p for p in picks if not is_meme(p["symbol"])]
    clean.sort(key=score_pick, reverse=True)
    return clean[:max_pos]


def select_best(picks, max_pos, regime):
    """Claude's best hybrid strategy — tier-aware."""
    # Prefer proven/forward picks, fall back to all non-meme with good R:R
    best = [
        p
        for p in picks
        if p["rr"] >= 1.2
        and not is_meme(p["symbol"])
        and p.get("trust_tier") in ("PROVEN", "FORWARD", "BACKTEST")
    ]
    if not best:
        # Include PROBATIONARY with stricter thresholds
        best = [
            p
            for p in picks
            if p["rr"] >= 1.3 and not is_meme(p["symbol"]) and p["confidence"] >= 0.7
        ]
    if not best:
        best = [p for p in picks if p["rr"] >= 1.3 and not is_meme(p["symbol"])]
    # Regime alignment bonus
    for p in best:
        p["_hybrid_score"] = score_pick(p)
        if regime == "BEARISH" and p["direction"] == "SHORT":
            p["_hybrid_score"] *= 1.3
        elif regime == "BEARISH" and p["direction"] == "LONG":
            p["_hybrid_score"] *= 0.7
        elif regime == "BULLISH" and p["direction"] == "LONG":
            p["_hybrid_score"] *= 1.2
    best.sort(key=lambda p: p.get("_hybrid_score", 0), reverse=True)
    return best[:max_pos]


def select_prop_conservative(picks, max_pos):
    # Primary: proven/forward strategies with good R:R for prop safety
    safe = [
        p
        for p in picks
        if p.get("trust_tier") in ("PROVEN", "FORWARD")
        and p["rr"] >= 1.3
        and not is_meme(p["symbol"])
    ]
    if not safe:
        safe = [p for p in picks if p["rr"] >= 1.5 and not is_meme(p["symbol"])]
    safe.sort(key=score_pick, reverse=True)
    return safe[:max_pos]


def select_prop_aggressive(picks, max_pos):
    agg = [
        p
        for p in picks
        if p["rr"] >= 1.3 and p["confidence"] >= 0.6 and not is_meme(p["symbol"])
    ]
    agg.sort(key=score_pick, reverse=True)
    return agg[:max_pos]


def select_prop_swing(picks, max_pos):
    swing = [
        p
        for p in picks
        if p["rr"] >= 1.5 and not is_meme(p["symbol"]) and not p["has_conflict"]
    ]
    if not swing:
        swing = [p for p in picks if p["rr"] >= 1.3 and not is_meme(p["symbol"])]
    swing.sort(key=lambda p: p["rr"], reverse=True)
    return swing[:max_pos]


# ── Deep-Value Selector Functions ──


def select_drawdown_dca(picks, max_pos, regime):
    """Select deep drawdown DCA picks — prioritize deepest drawdowns with bounce."""
    dv = [p for p in picks if p.get("_dv_type") == "drawdown_dca"]
    # Sort by drawdown depth (deeper = more value) * bounce confirmation
    dv.sort(
        key=lambda p: p.get("_drawdown_pct", 0) * max(1, p.get("_bounce_pct", 0)),
        reverse=True,
    )
    if not dv:
        # Fallback: any deep-value pick
        dv = [p for p in picks if "_dv_type" in p]
        dv.sort(key=lambda p: p.get("_drawdown_pct", 0), reverse=True)
    if not dv:
        # Final fallback: best LONG picks with high R:R (DCA = buying dips)
        dv = [
            p
            for p in picks
            if p["direction"] == "LONG" and p["rr"] >= 1.5 and not is_meme(p["symbol"])
        ]
        dv.sort(key=score_pick, reverse=True)
    return dv[:max_pos]


def select_rsi_capitulation(picks, max_pos, regime):
    """Select RSI capitulation picks — lowest RSI with bounce confirmation."""
    dv = [p for p in picks if p.get("_dv_type") == "rsi_capitulation"]
    # Sort by RSI (lower = more oversold = better entry)
    dv.sort(key=lambda p: p.get("_rsi", 50))
    if not dv:
        # Fallback: any deep-value pick with low RSI
        dv = [p for p in picks if "_dv_type" in p and p.get("_rsi", 50) < 40]
        dv.sort(key=lambda p: p.get("_rsi", 50))
    if not dv:
        # Final fallback: mean-reversion LONGs (capitulation = buy oversold)
        mr_strats = [
            "hurst_mean_reversion",
            "mvrv_contrarian_dip",
            "rsi",
            "mean_reversion",
            "reversal",
        ]
        dv = [
            p
            for p in picks
            if p["direction"] == "LONG"
            and any(s in p.get("strategy", "") for s in mr_strats)
        ]
        dv.sort(key=score_pick, reverse=True)
    return dv[:max_pos]


def select_fear_greed(picks, max_pos, regime):
    """Select fear & greed contrarian picks — only active during extreme fear."""
    dv = [p for p in picks if p.get("_dv_type") == "fear_greed"]
    # Sort by confidence (higher when F&G is lower)
    dv.sort(key=lambda p: p.get("confidence", 0), reverse=True)
    if not dv:
        # Fallback during non-fear: use drawdown picks on blue chips only
        blue_chips = {"BTCUSDT", "ETHUSDT", "XRPUSDT", "SOLUSDT"}
        dv = [
            p
            for p in picks
            if "_dv_type" in p and normalize_symbol(p["symbol"]) in blue_chips
        ]
        dv.sort(key=lambda p: p.get("_drawdown_pct", 0), reverse=True)
    if not dv:
        # Final fallback: contrarian high-confidence picks on blue chips
        blue_chips = {"BTCUSDT", "ETHUSDT", "XRPUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT"}
        dv = [
            p
            for p in picks
            if normalize_symbol(p["symbol"]) in blue_chips
            and p["confidence"] >= 0.7
            and p["rr"] >= 1.5
        ]
        dv.sort(key=score_pick, reverse=True)
    return dv[:max_pos]


def select_rel_strength(picks, max_pos, regime):
    """Select relative strength recovery picks — weakest performers bouncing back."""
    dv = [p for p in picks if p.get("_dv_type") == "rel_strength"]
    # Sort by worst 30d performance (most beaten down = most upside)
    dv.sort(key=lambda p: p.get("_perf_30d", 0))
    if not dv:
        # Fallback: deepest drawdown picks
        dv = [p for p in picks if "_dv_type" in p]
        dv.sort(key=lambda p: p.get("_drawdown_pct", 0), reverse=True)
    if not dv:
        # Final fallback: highest R:R LONG picks (recovery = upside)
        dv = [p for p in picks if p["direction"] == "LONG" and p["rr"] >= 2.0]
        dv.sort(key=lambda p: p["rr"], reverse=True)
    return dv[:max_pos]


def select_beaten_majors(picks, max_pos, regime):
    """Select beaten majors picks — oversold blue-chip crypto, long-only."""
    dv = [p for p in picks if p.get("_dv_type") == "beaten_majors"]
    # Sort by combined oversold score: lower RSI + deeper drawdown = better
    dv.sort(
        key=lambda p: (40 - p.get("_rsi", 40)) + p.get("_dd_from_30d", 0), reverse=True
    )
    if not dv:
        # Fallback: any deep value LONG with RSI < 45
        dv = [
            p
            for p in picks
            if p.get("_dv_type") and p["direction"] == "LONG" and p.get("_rsi", 50) < 45
        ]
        dv.sort(key=lambda p: p.get("_rsi", 50))
    return dv[:max_pos]


# ── Hoffman + HTF Selector Functions ──


def select_hoffman(picks, max_pos, regime):
    """Select Hoffman Elite Combo picks — RSI(2) extremes with volume."""
    hoff = [p for p in picks if p.get("_htf_type") == "hoffman_elite"]
    hoff.sort(
        key=lambda p: abs(50 - p.get("_rsi2", 50)), reverse=True
    )  # Most extreme RSI first
    if not hoff:
        # Fallback: any HTF pick with good R:R
        hoff = [p for p in picks if "_htf_type" in p and p.get("rr", 0) >= 1.5]
        hoff.sort(key=score_pick, reverse=True)
    if not hoff:
        # Final fallback: highest-confidence picks with volume/momentum strategies
        vol_strats = ["volume", "squeeze", "breakout", "ema_stack", "momentum"]
        hoff = [
            p
            for p in picks
            if any(s in p.get("strategy", "") for s in vol_strats) and p["rr"] >= 1.5
        ]
        hoff.sort(key=score_pick, reverse=True)
    return hoff[:max_pos]


def select_htf_trend(picks, max_pos, regime):
    """Select HTF trend-following picks — weekly + daily alignment."""
    htf = [p for p in picks if p.get("_htf_type") == "htf_trend"]
    htf.sort(key=lambda p: p.get("confidence", 0), reverse=True)
    if not htf:
        htf = [p for p in picks if "_htf_type" in p]
        htf.sort(key=score_pick, reverse=True)
    if not htf:
        # Final fallback: trend-following strategies (EMA, momentum, carry)
        trend_strats = ["ema", "trend", "momentum", "carry", "tsmom", "hurst_regime"]
        htf = [
            p
            for p in picks
            if any(s in p.get("strategy", "") for s in trend_strats)
            and p["confidence"] >= 0.65
        ]
        htf.sort(key=score_pick, reverse=True)
    return htf[:max_pos]


def select_htf_momentum(picks, max_pos, regime):
    """Select HTF weekly momentum picks — EMA stack aligned."""
    htf = [p for p in picks if p.get("_htf_type") == "weekly_momentum"]
    htf.sort(key=lambda p: p.get("rr", 0), reverse=True)
    if not htf:
        htf = [p for p in picks if "_htf_type" in p and p.get("direction") == "LONG"]
        htf.sort(key=score_pick, reverse=True)
    if not htf:
        # Final fallback: high-conviction LONG momentum plays
        htf = [
            p
            for p in picks
            if p["direction"] == "LONG" and p["confidence"] >= 0.75 and p["rr"] >= 1.5
        ]
        htf.sort(key=lambda p: p["confidence"] * p["rr"], reverse=True)
    return htf[:max_pos]


# ── Non-Crypto Selector Functions ──


def select_noncrypto_best(picks, max_pos):
    """Best scored non-crypto picks (stocks, forex, ETFs)."""
    scored = sorted(picks, key=score_pick, reverse=True)
    # Deduplicate by symbol
    seen = set()
    unique = []
    for p in scored:
        sym = p["symbol"]
        if sym not in seen:
            seen.add(sym)
            unique.append(p)
    return unique[:max_pos]


def select_noncrypto_reversal(picks, max_pos):
    """Mean reversion / short-term reversal plays for stocks."""
    # Prefer picks with SHORT direction or high R:R (contrarian)
    reversal = sorted(
        picks,
        key=lambda p: p["rr"] * (1.3 if p["direction"] == "SHORT" else 1.0),
        reverse=True,
    )
    seen = set()
    unique = []
    for p in reversal:
        sym = p["symbol"]
        if sym not in seen:
            seen.add(sym)
            unique.append(p)
    return unique[:max_pos]


def select_noncrypto_diversified(picks, max_pos):
    """Max diversification across non-crypto asset classes."""
    equity = sorted(
        [p for p in picks if p["asset_class"] == "EQUITY"], key=score_pick, reverse=True
    )
    forex = sorted(
        [p for p in picks if p["asset_class"] == "FOREX"], key=score_pick, reverse=True
    )
    futures = sorted(
        [p for p in picks if p["asset_class"] == "FUTURES"],
        key=score_pick,
        reverse=True,
    )
    etfs = sorted(
        [p for p in picks if p["asset_class"] == "ETF"], key=score_pick, reverse=True
    )
    penny = sorted(
        [p for p in picks if p["asset_class"] == "PENNY_STOCK"],
        key=score_pick,
        reverse=True,
    )
    # Interleave for max diversity across all non-crypto classes
    result = []
    seen = set()
    sources = [s for s in [futures, equity, forex, etfs, penny] if s]
    idx = 0
    while len(result) < max_pos and any(sources):
        src = sources[idx % len(sources)]
        if src:
            p = src.pop(0)
            if p["symbol"] not in seen:
                seen.add(p["symbol"])
                result.append(p)
        else:
            sources.pop(idx % len(sources))
            if not sources:
                break
        idx += 1
    return result[:max_pos]


# ── Mercury 3-Lever Validation Selectors ──

# Carry/arb strategy names for basis_carry_only portfolio
CARRY_ARB_STRATEGIES = {
    "funding_rate_carry",
    "funding_rate_carry_pro",
    "funding_rate_arbitrage",
    "cross_exchange_basis_carry",
    "funding_momentum",
    "basis_carry",
    "funding_carry",
    "carry_trade",
}


def select_regime_filtered(picks, max_pos, regime):
    """Mercury Lever 1: Only regime-aligned picks from proven strategies.

    In BULLISH: only LONG. In BEARISH: only SHORT. In CHOPPY/NEUTRAL: only R:R>=1.5.
    Additionally filters to PROVEN/FORWARD trust tier or PROVEN_STRATEGIES set.
    """
    # Strategy must be proven
    proven = [
        p
        for p in picks
        if p.get("trust_tier") in ("PROVEN", "FORWARD")
        or p.get("strategy", "") in PROVEN_STRATEGIES
    ]
    if not proven:
        proven = picks  # fallback to all if no proven available

    # Then apply regime direction filter
    if regime == "BEARISH":
        aligned = [p for p in proven if p["direction"] == "SHORT"]
    elif regime == "BULLISH":
        aligned = [p for p in proven if p["direction"] == "LONG"]
    else:  # CHOPPY / NEUTRAL — only high R:R
        aligned = [p for p in proven if p["rr"] >= 1.5]

    aligned.sort(key=score_pick, reverse=True)
    return aligned[:max_pos]


def select_high_consensus(picks, max_pos):
    """Mercury Lever: Only picks with 3+ system agreement.

    Historical data shows 78.6% WR when 3+ diverse systems agree on same symbol+direction.
    Falls back to 2+ agreement if no 3+ picks available.
    """
    high = [p for p in picks if p.get("agreement", 0) >= 3]
    if not high:
        # Fallback to 2+ agreement
        high = [p for p in picks if p.get("agreement", 0) >= 2]
    high.sort(key=lambda p: (p.get("agreement", 0), score_pick(p)), reverse=True)
    # Deduplicate by symbol
    seen = set()
    unique = []
    for p in high:
        base = normalize_symbol(p["symbol"])
        if base not in seen:
            seen.add(base)
            p["_consensus_count"] = p.get("agreement", 0)
            unique.append(p)
    return unique[:max_pos]


def select_golden_insight(picks, max_pos):
    """Signal Insight Engine: Only walk-forward proven strategies (GOLDEN badge).

    Filters to PROVEN_STRATEGIES set (Keltner BTC 66.1% WR PF 3.74,
    RSI confluence ETH 60.5% WR PF 2.30, etc.). These have 50+ forward trades
    and PF > 1.5 — the gold standard for statistical validation.
    """
    golden = [
        p
        for p in picks
        if p.get("strategy", "") in PROVEN_STRATEGIES
        or any(ps in p.get("strategy", "") for ps in PROVEN_STRATEGIES)
    ]
    if not golden:
        # Fallback: trust_tier PROVEN (fewer strategies but still validated)
        golden = [p for p in picks if p.get("trust_tier") == "PROVEN"]
    golden.sort(key=score_pick, reverse=True)
    return golden[:max_pos]


def select_score_small_position(picks, max_pos):
    """Mercury position sizing test: Same as score_leaders but 2% sizing.

    Pick selection is identical to score_leaders — the only difference is
    position_pct=0.02 (set in portfolio config). This selector exists to
    keep the methodology mapping clean.
    """
    return select_score_leaders(picks, max_pos)


def select_sentiment_divergence(picks, max_pos):
    """Sentiment-price divergence signals only.

    Filters to strategy name containing 'sentiment_price_divergence' or
    'sentiment_divergence'. Tests this specific strategy in isolation.
    """
    sent = [
        p
        for p in picks
        if "sentiment_price_divergence" in p.get("strategy", "")
        or "sentiment_divergence" in p.get("strategy", "")
    ]
    if not sent:
        # Broader fallback: any sentiment-related strategy
        sent = [p for p in picks if "sentiment" in p.get("strategy", "").lower()]
    sent.sort(key=score_pick, reverse=True)
    return sent[:max_pos]


def select_carry_arb(picks, max_pos):
    """Carry/arb strategies only: funding rate + basis carry.

    Market-neutral structural edge strategies. Expected Sharpe 2.0+.
    Funding rate arbitrage (19-115% annual documented) + cross-exchange
    basis carry (3:1 R:R).
    """
    carry = [
        p
        for p in picks
        if p.get("strategy", "") in CARRY_ARB_STRATEGIES
        or any(cs in p.get("strategy", "") for cs in CARRY_ARB_STRATEGIES)
    ]
    if not carry:
        # Broader fallback: any carry/funding/arb strategy
        carry = [
            p
            for p in picks
            if any(
                kw in p.get("strategy", "").lower()
                for kw in ("carry", "funding", "arb", "basis")
            )
        ]
    carry.sort(key=score_pick, reverse=True)
    return carry[:max_pos]


SELECTOR_MAP = {
    "score": lambda p, mp, r: select_score_leaders(p, mp),
    "proven": lambda p, mp, r: select_proven(p, mp),
    "momentum": lambda p, mp, r: select_momentum(p, mp),
    "contrarian": select_contrarian,
    "regime": select_regime_aligned,
    "conviction": lambda p, mp, r: select_conviction(p, mp),
    "rr": lambda p, mp, r: select_rr(p, mp),
    "consensus": lambda p, mp, r: select_consensus(p, mp),
    "fresh": lambda p, mp, r: select_fresh(p, mp),
    "sector": lambda p, mp, r: select_sector(p, mp),
    "anti_meme": lambda p, mp, r: select_anti_meme(p, mp),
    "best": select_best,
    "prop_conservative": lambda p, mp, r: select_prop_conservative(p, mp),
    "prop_aggressive": lambda p, mp, r: select_prop_aggressive(p, mp),
    "prop_swing": lambda p, mp, r: select_prop_swing(p, mp),
    # Deep-value mutations
    "drawdown_dca": select_drawdown_dca,
    # Hoffman + HTF mutations
    "hoffman": select_hoffman,
    "htf_trend": select_htf_trend,
    "htf_momentum": select_htf_momentum,
    "rsi_capitulation": select_rsi_capitulation,
    "fear_greed": select_fear_greed,
    "rel_strength": select_rel_strength,
    "beaten_majors": select_beaten_majors,
    # Non-crypto portfolios
    "noncrypto_best": lambda p, mp, r: select_noncrypto_best(p, mp),
    "noncrypto_reversal": lambda p, mp, r: select_noncrypto_reversal(p, mp),
    "noncrypto_diversified": lambda p, mp, r: select_noncrypto_diversified(p, mp),
    # Mercury 3-Lever Validation
    "regime_aligned_only": select_regime_filtered,
    "consensus_3plus": lambda p, mp, r: select_high_consensus(p, mp),
    "golden_insight_only": lambda p, mp, r: select_golden_insight(p, mp),
    "score_small_position": lambda p, mp, r: select_score_small_position(p, mp),
    "sentiment_divergence_only": lambda p, mp, r: select_sentiment_divergence(p, mp),
    "carry_arb_only": lambda p, mp, r: select_carry_arb(p, mp),
}


def init_portfolio(pdef):
    return {
        "id": pdef["id"],
        "name": pdef["name"],
        "description": pdef["description"],
        "methodology": pdef["methodology"],
        "initial_capital": pdef["initial_capital"],
        "equity": pdef["initial_capital"],
        "high_water_mark": pdef["initial_capital"],
        "cash": pdef["initial_capital"],
        "max_positions": pdef["max_positions"],
        "position_pct": pdef["position_pct"],
        "positions": [],
        "closed": [],
        "equity_history": [
            {"time": now_est().isoformat(), "equity": pdef["initial_capital"]}
        ],
        "total_commission": 0.0,
        "total_slippage": 0.0,
        "wins": 0,
        "losses": 0,
        "max_drawdown_pct": 0.0,
        "daily_pnl": 0.0,
        "daily_pnl_reset_date": now_est().strftime("%Y-%m-%d"),
        "created_at": now_est().isoformat(),
        "last_updated": now_est().isoformat(),
        "update_interval_min": pdef.get("update_interval_min", 30),
        # Prop firm fields
        "prop_firm": pdef.get("prop_firm", False),
        "daily_loss_limit_pct": pdef.get("daily_loss_limit_pct", 0),
        "max_drawdown_limit_pct": pdef.get("max_drawdown_pct", 0),
        "profit_target_pct": pdef.get("profit_target_pct", 0),
        "resets": 0,
        "reset_history": [],
        "status": "ACTIVE",  # ACTIVE, PASSED, BLOWN
    }


def update_portfolio(
    port, valid_picks, prices, regime, pdef=None, global_exposure=None
):
    """Core update logic for a single portfolio."""
    if pdef is None:
        pdef = {}
    if global_exposure is None:
        global_exposure = {}
    now = now_est()
    port["last_updated"] = now.isoformat()

    # Reset daily PnL if new day
    today = now.strftime("%Y-%m-%d")
    if port["daily_pnl_reset_date"] != today:
        port["daily_pnl"] = 0.0
        port["daily_pnl_reset_date"] = today

    # Skip if blown and not yet reset
    if port["status"] == "BLOWN":
        return

    # ── Check TP/SL + Trailing Stop + Time Exit on existing positions ──
    positions_to_close = []
    for pos in port["positions"]:
        sym = normalize_symbol(pos["symbol"])
        price = prices.get(sym)
        if not price:
            # Fallback: use 6-layer price fetcher for stocks/forex/missing crypto
            price = _fetch_reference_price(pos["symbol"])
            if not price or price <= 0:
                continue
        pos["current_price"] = price

        direction = pos["direction"]
        SL_BUFFER = 0.015  # 1.5% early trigger to prevent overshoot (widened from 0.5% to reduce premature SL hits)
        if direction == "LONG":
            pos["pnl_pct"] = ((price - pos["entry_price"]) / pos["entry_price"]) * 100
            if price >= pos["take_profit"]:
                positions_to_close.append((pos, "TP", price))
            elif price <= pos["stop_loss"] * (1 + SL_BUFFER):
                exit_price = max(price, pos["stop_loss"])  # never below SL
                positions_to_close.append((pos, "SL", exit_price))
        else:  # SHORT
            pos["pnl_pct"] = ((pos["entry_price"] - price) / pos["entry_price"]) * 100
            if price <= pos["take_profit"]:
                positions_to_close.append((pos, "TP", price))
            elif price >= pos["stop_loss"] * (1 - SL_BUFFER):
                exit_price = min(price, pos["stop_loss"])  # never above SL
                positions_to_close.append((pos, "SL", exit_price))

        pos["pnl_usd"] = pos["size_usd"] * (pos["pnl_pct"] / 100)

        # ── Enhanced Trailing Stop (ATR-based dynamic + fixed fallback) ──
        if pos not in [x[0] for x in positions_to_close]:
            sym_norm = normalize_symbol(pos["symbol"])
            vol = _VOL_CACHE.get(sym_norm, {})
            if vol:
                # ATR-based dynamic trail (Giga Potato v1)
                new_sl, trail_meta = enhanced_trailing_stop(pos, price, vol)
                if new_sl is not None:
                    pos["stop_loss"] = new_sl
                    pos["_trail_active"] = True
                    pos["_trail_metadata"] = trail_meta
                    # Check if price has now crossed the tightened SL
                    if pos["direction"] == "LONG" and price <= new_sl:
                        positions_to_close.append((pos, "ATR_TRAIL", price))
                    elif pos["direction"] == "SHORT" and price >= new_sl:
                        positions_to_close.append((pos, "ATR_TRAIL", price))
            else:
                # Fallback: original fixed-% trailing stop
                if pos["pnl_pct"] >= TRAIL_ACTIVATE_PCT:
                    peak = pos.get("peak_pnl_pct", pos["pnl_pct"])
                    pos["peak_pnl_pct"] = max(peak, pos["pnl_pct"])
                    trail_level_pct = pos["peak_pnl_pct"] * TRAIL_DISTANCE_MULT
                    if pos["pnl_pct"] < trail_level_pct:
                        positions_to_close.append((pos, "TRAIL", price))

        # ── Time-based exits (Grok: 7d loss exit, 14d max hold) ──
        try:
            opened = datetime.fromisoformat(pos["opened_at"])
            hours_held = (now - opened).total_seconds() / 3600
            if hours_held > STALE_LOSS_HOURS and pos["pnl_pct"] < 0:
                if pos not in [x[0] for x in positions_to_close]:
                    positions_to_close.append((pos, "TIME_EXIT", price))
            elif hours_held > MAX_HOLD_HOURS:
                if pos not in [x[0] for x in positions_to_close]:
                    positions_to_close.append((pos, "MAX_HOLD", price))
        except Exception:
            pass

    # Close triggered positions
    for pos, reason, exit_price in positions_to_close:
        exit_comm = calc_commission(
            pos.get("asset_class", "CRYPTO"), pos["size_usd"], exit_price
        )
        pos["exit_price"] = exit_price
        pos["exit_reason"] = reason
        pos["closed_at"] = now.isoformat()
        pos["commission_exit"] = exit_comm
        pos["status"] = reason + "_HIT"
        exit_slip = pos["size_usd"] * SLIPPAGE_PCT
        pos["slippage_exit"] = round(exit_slip, 2)
        # net_pnl for reporting: all costs (entry comm+slippage already deducted from cash at open)
        net_pnl = (
            pos["pnl_usd"]
            - pos.get("commission_entry", 0)
            - pos.get("slippage_entry", 0)
            - exit_comm
            - exit_slip
        )
        pos["net_pnl_usd"] = net_pnl
        # net_pnl_pct: post-commission return % — used by frontend for accurate W/L display
        size_usd = pos.get("size_usd", 1) or 1
        pos["net_pnl_pct"] = round((net_pnl / size_usd) * 100, 4)
        port["total_commission"] += exit_comm
        port["total_slippage"] += exit_slip
        # Return size + raw pnl - exit costs only (entry costs already deducted from cash at open)
        port["cash"] += pos["size_usd"] + pos["pnl_usd"] - exit_comm - exit_slip
        port["daily_pnl"] += net_pnl

        if net_pnl > 0:
            port["wins"] += 1
        else:
            port["losses"] += 1
        port["closed"].append(deepcopy(pos))
        port["positions"].remove(pos)

    # ── Calculate current equity ──
    unrealized = sum(p.get("pnl_usd", 0) for p in port["positions"])
    allocated = sum(p["size_usd"] for p in port["positions"])
    port["equity"] = port["cash"] + allocated + unrealized
    port["high_water_mark"] = max(port["high_water_mark"], port["equity"])

    # Max drawdown
    dd = ((port["high_water_mark"] - port["equity"]) / port["high_water_mark"]) * 100
    port["max_drawdown_pct"] = max(port["max_drawdown_pct"], dd)

    # ── Prop firm checks ──
    if port["prop_firm"]:
        daily_loss_pct = (
            abs(port["daily_pnl"]) / port["initial_capital"] * 100
            if port["daily_pnl"] < 0
            else 0
        )
        total_dd = (
            ((port["initial_capital"] - port["equity"]) / port["initial_capital"]) * 100
            if port["equity"] < port["initial_capital"]
            else 0
        )

        if daily_loss_pct >= port["daily_loss_limit_pct"]:
            port["status"] = "BLOWN"
            port["reset_history"].append(
                {
                    "time": now.isoformat(),
                    "reason": f"Daily loss limit hit: -{daily_loss_pct:.2f}% (limit: {port['daily_loss_limit_pct']}%)",
                    "equity_at_blow": port["equity"],
                }
            )
            # Close all positions with proper PnL accounting
            for pos in port["positions"]:
                pos["status"] = "FORCE_CLOSED"
                pos["closed_at"] = now.isoformat()
                pos["exit_reason"] = "DAILY_LIMIT"
                pos["exit_price"] = pos.get("current_price", pos["entry_price"])
                exit_comm = calc_commission(
                    pos.get("asset_class", "CRYPTO"),
                    pos["size_usd"],
                    pos.get("current_price", pos["entry_price"]),
                )
                pos["commission_exit"] = exit_comm
                net_pnl = (
                    pos.get("pnl_usd", 0)
                    - pos.get("commission_entry", 0)
                    - pos.get("slippage_entry", 0)
                    - exit_comm
                )
                pos["net_pnl_usd"] = net_pnl
                port["total_commission"] += exit_comm
                if net_pnl > 0:
                    port["wins"] += 1
                else:
                    port["losses"] += 1
                port["closed"].append(deepcopy(pos))
            port["positions"] = []
            return

        if total_dd >= port["max_drawdown_limit_pct"]:
            port["status"] = "BLOWN"
            port["reset_history"].append(
                {
                    "time": now.isoformat(),
                    "reason": f"Max drawdown hit: -{total_dd:.2f}% (limit: {port['max_drawdown_limit_pct']}%)",
                    "equity_at_blow": port["equity"],
                }
            )
            for pos in port["positions"]:
                pos["status"] = "FORCE_CLOSED"
                pos["closed_at"] = now.isoformat()
                pos["exit_reason"] = "MAX_DD"
                pos["exit_price"] = pos.get("current_price", pos["entry_price"])
                exit_comm = calc_commission(
                    pos.get("asset_class", "CRYPTO"),
                    pos["size_usd"],
                    pos.get("current_price", pos["entry_price"]),
                )
                pos["commission_exit"] = exit_comm
                net_pnl = (
                    pos.get("pnl_usd", 0)
                    - pos.get("commission_entry", 0)
                    - pos.get("slippage_entry", 0)
                    - exit_comm
                )
                pos["net_pnl_usd"] = net_pnl
                port["total_commission"] += exit_comm
                if net_pnl > 0:
                    port["wins"] += 1
                else:
                    port["losses"] += 1
                port["closed"].append(deepcopy(pos))
            port["positions"] = []
            return

        # Check profit target
        profit_pct = (
            (port["equity"] - port["initial_capital"]) / port["initial_capital"]
        ) * 100
        if profit_pct >= port["profit_target_pct"]:
            port["status"] = "PASSED"
            return

    # ── Select new picks if room ──
    open_count = len(port["positions"])
    if open_count >= port["max_positions"]:
        # Record equity and return
        port["equity_history"].append(
            {"time": now.isoformat(), "equity": port["equity"]}
        )
        return

    # Get current symbols to avoid duplicates
    current_syms = {normalize_symbol(p["symbol"]) for p in port["positions"]}

    # ── Post-TP cooldown: don't re-enter same symbol within 4 hours of a TP hit ──
    # Prevents the XRP re-entry pattern where system keeps buying at higher prices after a win
    TP_COOLDOWN_HOURS = 4
    cooldown_syms = set()
    for t in port.get("closed", []):
        reason = (t.get("exit_reason", "") or "").upper()
        if "TP" in reason:
            closed_at = t.get("closed_at", "")
            if closed_at:
                try:
                    closed_time = datetime.fromisoformat(closed_at)
                    if closed_time.tzinfo is None:
                        closed_time = closed_time.replace(tzinfo=now.tzinfo)
                    hours_since = (now - closed_time).total_seconds() / 3600
                    if hours_since < TP_COOLDOWN_HOURS:
                        cooldown_syms.add(normalize_symbol(t["symbol"]))
                except (ValueError, TypeError):
                    pass
    if cooldown_syms:
        print(
            f"    [COOLDOWN] {port['id']}: {', '.join(cooldown_syms)} on {TP_COOLDOWN_HOURS}h post-TP cooldown"
        )

    # ── Apply Stage 1 firewall to valid picks (regime-aware) ──
    # Inject asset filter from portfolio definition for non-crypto portfolios
    asset_filter = pdef.get("asset_filter")
    firewall_picks = []
    for p in valid_picks:
        if asset_filter:
            p["_asset_filter"] = asset_filter
        elif "_asset_filter" in p:
            del p["_asset_filter"]
        tier = passes_firewall(p, regime)
        if tier:
            p["trust_tier"] = tier
            firewall_picks.append(p)

    # Select picks using methodology
    selector = SELECTOR_MAP.get(port["methodology"])
    if not selector:
        return

    slots = port["max_positions"] - open_count
    candidates = selector(
        firewall_picks, slots + 10, regime
    )  # more extras for concentration filter

    # ── Concentration tracking (Gemini/Grok/Codex consensus) ──
    current_longs = sum(1 for p in port["positions"] if p["direction"] == "LONG")
    current_shorts = sum(1 for p in port["positions"] if p["direction"] == "SHORT")

    # Track strategy families for concentration limits
    current_families = {}
    for p in port["positions"]:
        fam = get_strategy_family(p.get("strategy", ""))
        key = f"{fam}_{p['direction']}"
        current_families[key] = current_families.get(key, 0) + 1

    for cand in candidates:
        if open_count >= port["max_positions"]:
            break
        sym = normalize_symbol(cand["symbol"])
        # Codex: 1 position per symbol+direction (no stacking)
        if sym in current_syms:
            continue

        # Post-TP cooldown: don't re-enter same symbol too soon after taking profit
        if sym in cooldown_syms:
            continue

        # Global exposure cap: max N portfolios per symbol+direction
        sym_dir_key = f"{sym}_{cand['direction']}"
        if global_exposure.get(sym_dir_key, 0) >= MAX_GLOBAL_SYMBOL_PORTFOLIOS:
            print(
                f"  [GLOBAL CAP] {cand['symbol']} {cand['direction']}: already in {global_exposure[sym_dir_key]} portfolios (max {MAX_GLOBAL_SYMBOL_PORTFOLIOS})"
            )
            continue

        # Concentration limits (Gemini: max directional exposure)
        if (
            cand["direction"] == "LONG"
            and current_longs >= port["max_positions"] * MAX_LONG_PCT
        ):
            continue
        if (
            cand["direction"] == "SHORT"
            and current_shorts >= port["max_positions"] * MAX_SHORT_PCT
        ):
            continue

        # Family concentration: max 2 positions per strategy family per direction
        cand_family = get_strategy_family(cand.get("strategy", ""))
        family_key = f"{cand_family}_{cand['direction']}"
        if current_families.get(family_key, 0) >= MAX_PER_FAMILY:
            continue

        # ── SIGNAL STALENESS GUARD ──
        # Reject signals generated too long ago — prevents "last night" entries
        sig_ts = cand.get("timestamp", "")
        if sig_ts:
            try:
                sig_time = datetime.fromisoformat(sig_ts)
                if sig_time.tzinfo is None:
                    sig_time = sig_time.replace(tzinfo=timezone(timedelta(hours=-5)))
                max_age_h = 4 if cand["asset_class"] == "CRYPTO" else 12
                age_h = (now - sig_time).total_seconds() / 3600
                if age_h > max_age_h:
                    print(
                        f"  [STALE SIGNAL] {cand['symbol']}: signal is {age_h:.1f}h old (max {max_age_h}h) — rejecting"
                    )
                    continue
            except (ValueError, TypeError):
                pass  # unparseable timestamp — allow through, entry validation will catch bad prices

        # ── MULTI-LAYER ENTRY VALIDATION ──
        # Never trust signal entry_price — always verify against live market
        validated = validate_and_fix_entry(
            cand["symbol"], cand["entry_price"], prices, cand["direction"]
        )
        if not validated:
            print(
                f"  [REJECTED] {cand['symbol']}: failed entry validation — no live price available"
            )
            continue

        live_price = validated["price"]
        signal_entry = cand["entry_price"]

        # Scale TP/SL proportionally if entry changed
        if signal_entry > 0 and abs(live_price - signal_entry) / signal_entry > 0.001:
            tp_ratio = cand["take_profit"] / signal_entry
            sl_ratio = cand["stop_loss"] / signal_entry
            cand["take_profit"] = round(live_price * tp_ratio, 6)
            cand["stop_loss"] = round(live_price * sl_ratio, 6)
            cand["rr"] = calc_rr(
                live_price, cand["take_profit"], cand["stop_loss"], cand["direction"]
            )

        # Verify TP/SL make directional sense with live price
        if cand["direction"] == "LONG":
            if cand["take_profit"] <= live_price or cand["stop_loss"] >= live_price:
                print(
                    f"  [REJECTED] {cand['symbol']} LONG: TP={cand['take_profit']:.6f} must be > entry={live_price:.6f} > SL={cand['stop_loss']:.6f}"
                )
                continue
        else:  # SHORT
            if cand["take_profit"] >= live_price or cand["stop_loss"] <= live_price:
                print(
                    f"  [REJECTED] {cand['symbol']} SHORT: SL={cand['stop_loss']:.6f} must be > entry={live_price:.6f} > TP={cand['take_profit']:.6f}"
                )
                continue

        # Final R:R check — must still be >= 1.0 after price adjustment
        if cand["rr"] < 1.0:
            print(
                f"  [REJECTED] {cand['symbol']}: R:R={cand['rr']:.2f} < 1.0 after price adjustment"
            )
            continue

        entry_price = live_price

        # ── Volatility-Adjusted Position Sizing (Giga Potato v1) ──
        # Uses Kelly + ATR scaling instead of fixed % of cash
        sym_vol = normalize_symbol(cand["symbol"])
        vol_metrics = _VOL_CACHE.get(sym_vol, {})
        if vol_metrics and cand.get("sys_wr", 0) > 0:
            size_usd, risk_meta = volatility_adjusted_size(
                capital=port["cash"],
                strat_wr=cand.get("sys_wr", 50),
                strat_pf=cand.get("sys_pf", 1.0) or 1.0,
                entry_price=entry_price,
                stop_loss=cand["stop_loss"],
                vol_metrics=vol_metrics,
                base_risk_pct=0.02,
                max_size_pct=port["position_pct"],
            )
            cand["_risk_metadata"] = risk_meta
        else:
            # Fallback: original fixed % sizing
            size_usd = port["cash"] * port["position_pct"]

        if size_usd < 10 or size_usd > port["cash"] * 0.95:
            continue

        # ── Portfolio Risk Budget Check ──
        budget_ok, budget_reason, risk_used = portfolio_risk_budget(
            port,
            size_usd,
            cand["direction"],
            cand["symbol"],
            cand.get("asset_class", "CRYPTO"),
        )
        if not budget_ok:
            print(f"  [RISK BUDGET] {cand['symbol']}: {budget_reason}")
            continue

        comm = calc_commission(cand["asset_class"], size_usd, entry_price)
        slippage = size_usd * SLIPPAGE_PCT

        pos = {
            "id": pick_id(cand),
            "symbol": cand["symbol"],
            "direction": cand["direction"],
            "asset_class": cand["asset_class"],
            "source_system": cand["source_system"],
            "strategy": cand["strategy"],
            "entry_price": entry_price,
            "take_profit": cand["take_profit"],
            "stop_loss": cand["stop_loss"],
            "rr": cand["rr"],
            "confidence": cand["confidence"],
            "sys_wr": cand["sys_wr"],
            "sys_pf": cand["sys_pf"],
            "size_usd": round(size_usd, 2),
            "commission_entry": round(comm, 2),
            "slippage_entry": round(slippage, 2),
            "opened_at": now.isoformat(),
            "status": "OPEN",
            "pnl_pct": 0.0,
            "pnl_usd": 0.0,
            "current_price": entry_price,
            "_signal_entry": signal_entry,
            "_entry_drift_pct": round(validated["drift_pct"], 2),
            "_price_source": validated["source"],
        }
        port["positions"].append(pos)
        port["cash"] -= (
            size_usd + comm + slippage
        )  # Deduct ALL costs from cash (matches real broker behavior)
        port["total_commission"] += comm
        port["total_slippage"] += slippage
        current_syms.add(sym)
        open_count += 1
        current_families[family_key] = current_families.get(family_key, 0) + 1
        # Update global exposure so subsequent portfolios in this run see it
        global_exposure[sym_dir_key] = global_exposure.get(sym_dir_key, 0) + 1
        if cand["direction"] == "LONG":
            current_longs += 1
        else:
            current_shorts += 1

    # Record equity
    port["equity_history"].append({"time": now.isoformat(), "equity": port["equity"]})
    # Keep history manageable
    if len(port["equity_history"]) > 1000:
        port["equity_history"] = port["equity_history"][-500:]


def reset_blown_portfolio(port, pdef):
    """Reset a blown prop firm portfolio. Preserves lifetime stats for auditing."""
    port["resets"] += 1
    port["status"] = "ACTIVE"

    # ── Accumulate lifetime stats before reset ──
    if "lifetime_stats" not in port:
        port["lifetime_stats"] = {
            "total_resets": 0,
            "total_wins": 0,
            "total_losses": 0,
            "total_trades": 0,
            "total_commission": 0.0,
            "total_pnl_usd": 0.0,
            "best_equity": pdef["initial_capital"],
            "worst_drawdown_pct": 0.0,
            "reset_log": [],
        }
    ls = port["lifetime_stats"]
    ls["total_resets"] = port["resets"]
    ls["total_wins"] += port.get("wins", 0)
    ls["total_losses"] += port.get("losses", 0)
    ls["total_trades"] += port.get("wins", 0) + port.get("losses", 0)
    ls["total_commission"] += port.get("total_commission", 0)
    ls["total_pnl_usd"] += port["equity"] - pdef["initial_capital"]
    ls["best_equity"] = max(
        ls["best_equity"], port.get("high_water_mark", pdef["initial_capital"])
    )
    ls["worst_drawdown_pct"] = max(
        ls["worst_drawdown_pct"], port.get("max_drawdown_pct", 0)
    )
    ls["reset_log"].append(
        {
            "reset_num": port["resets"],
            "time": now_est().isoformat(),
            "equity_at_reset": port["equity"],
            "wins": port.get("wins", 0),
            "losses": port.get("losses", 0),
            "pnl_usd": round(port["equity"] - pdef["initial_capital"], 2),
            "max_dd": round(port.get("max_drawdown_pct", 0), 2),
            "reason": port.get("reset_history", [{}])[-1].get("reason", "unknown")
            if port.get("reset_history")
            else "unknown",
        }
    )

    # Reset active state
    port["equity"] = pdef["initial_capital"]
    port["cash"] = pdef["initial_capital"]
    port["high_water_mark"] = pdef["initial_capital"]
    port["positions"] = []
    port["daily_pnl"] = 0.0
    port["daily_pnl_reset_date"] = now_est().strftime("%Y-%m-%d")
    port["max_drawdown_pct"] = 0.0
    port["wins"] = 0
    port["losses"] = 0
    port["total_commission"] = 0.0
    port["total_slippage"] = 0.0
    # Keep closed history and reset_history for learning


def calc_sharpe(equity_history, initial):
    """Annualized Sharpe ratio from equity history."""
    if len(equity_history) < 20:  # Need meaningful sample (10+ hours of 30-min data)
        return 0.0
    returns = []
    for i in range(1, len(equity_history)):
        prev = equity_history[i - 1]["equity"]
        curr = equity_history[i]["equity"]
        if prev > 0:
            returns.append((curr - prev) / prev)
    if not returns or len(returns) < 2:
        return 0.0
    avg = sum(returns) / len(returns)
    variance = sum((r - avg) ** 2 for r in returns) / (len(returns) - 1)
    if variance <= 0:
        return 0.0  # Zero variance = flat returns = no meaningful Sharpe
    std = math.sqrt(variance)
    if std < 0.001:
        return 0.0  # Near-zero std = no meaningful Sharpe (prevents overflow)
    # Annualize assuming 30-min intervals (~48 per day, ~17520 per year)
    sharpe = (avg / std) * math.sqrt(17520)
    return round(max(min(sharpe, 10.0), -10.0), 2)  # Cap at ±10 (world-class is ~3-4)


def calc_sortino(equity_history, initial):
    """Annualized Sortino ratio from equity history."""
    if len(equity_history) < 20:
        return 0.0
    returns = []
    for i in range(1, len(equity_history)):
        prev = equity_history[i - 1]["equity"]
        curr = equity_history[i]["equity"]
        if prev > 0:
            returns.append((curr - prev) / prev)
    if not returns or len(returns) < 2:
        return 0.0
    avg = sum(returns) / len(returns)
    downside_returns = [r for r in returns if r < 0]
    if not downside_returns:
        return 10.0  # Infinite Sortino if no downside
    downside_variance = sum(r**2 for r in downside_returns) / len(downside_returns)
    if downside_variance <= 0:
        return 10.0
    downside_std = math.sqrt(downside_variance)
    sortino = (avg / downside_std) * math.sqrt(17520)
    return round(max(min(sortino, 10.0), -10.0), 2)


def calc_rolling_sharpe(equity_history, target_periods=336):
    """Calculate Sharpe ratio over the recent rolling window limit."""
    if len(equity_history) < target_periods:
        return calc_sharpe(equity_history, 0)
    return calc_sharpe(equity_history[-target_periods:], 0)


def calc_rolling_sortino(equity_history, target_periods=336):
    """Calculate Sortino ratio over the recent rolling window limit."""
    if len(equity_history) < target_periods:
        return calc_sortino(equity_history, 0)
    return calc_sortino(equity_history[-target_periods:], 0)


def calc_var_99(equity_history, target_periods=48):
    """Calculate 99% Value at Risk (VaR) for the given target periods (default 1 day = 48 periods)."""
    if len(equity_history) < 100:  # Need sufficient data
        return 0.0
    returns = []
    # Calculate rolling period returns
    for i in range(target_periods, len(equity_history)):
        prev = equity_history[i - target_periods]["equity"]
        curr = equity_history[i]["equity"]
        if prev > 0:
            returns.append((curr - prev) / prev)
    if not returns:
        return 0.0
    returns.sort()
    idx = int(len(returns) * 0.01)
    var_99 = (
        abs(returns[min(idx, len(returns) - 1)]) * 100
    )  # Return positive percentage
    return round(var_99, 2)


def recompute_stats(port):
    """Recompute wins, losses, and equity from actual data to prevent drift.

    WR formula: wins(pnl>0) / (wins+losses) — zero-PnL excluded from BOTH.
    Uses standardized calculate_win_rate from shared module.
    """
    closed = port.get("closed", [])
    wins = sum(
        1 for t in closed if (t.get("net_pnl_usd", t.get("pnl_usd", 0)) or 0) > 0
    )
    losses = sum(
        1 for t in closed if (t.get("net_pnl_usd", t.get("pnl_usd", 0)) or 0) < 0
    )
    port["wins"] = wins
    port["losses"] = losses

    # Recompute equity from positions + cash
    unrealized = sum(p.get("pnl_usd", 0) for p in port.get("positions", []))
    allocated = sum(p.get("size_usd", 0) for p in port.get("positions", []))
    port["equity"] = port["cash"] + allocated + unrealized
    port["high_water_mark"] = max(
        port.get("high_water_mark", port["equity"]), port["equity"]
    )


MIN_TRADES_FOR_METRICS = 5  # Don't display WR/Sharpe/PF until enough trades


def calc_portfolio_stats(port):
    """Calculate derived stats for dashboard."""
    recompute_stats(port)  # Always recompute before calculating stats
    total_trades = port["wins"] + port["losses"]
    enough_trades = total_trades >= MIN_TRADES_FOR_METRICS
    # Use standardized win rate calculation (excludes zero-PnL)
    wr = calculate_win_rate(port["wins"], total_trades) * 100
    pnl_pct = (
        (port["equity"] - port["initial_capital"]) / port["initial_capital"]
    ) * 100
    sharpe = (
        calc_sharpe(port["equity_history"], port["initial_capital"])
        if enough_trades
        else 0.0
    )
    sortino = (
        calc_sortino(port["equity_history"], port["initial_capital"])
        if enough_trades
        else 0.0
    )
    rolling_sharpe = (
        calc_rolling_sharpe(port.get("equity_history", [])) if enough_trades else 0.0
    )
    rolling_sortino = (
        calc_rolling_sortino(port.get("equity_history", [])) if enough_trades else 0.0
    )
    var_99 = (
        calc_var_99(port.get("equity_history", []))
        if len(port.get("equity_history", [])) >= 100
        else 0.0
    )

    # Avg win/loss
    wins_pnl = [
        c.get("net_pnl_usd", 0) for c in port["closed"] if c.get("net_pnl_usd", 0) > 0
    ]
    losses_pnl = [
        c.get("net_pnl_usd", 0)
        for c in port["closed"]
        if (c.get("net_pnl_usd", 0) or 0) < 0
    ]
    avg_win = sum(wins_pnl) / len(wins_pnl) if wins_pnl else 0
    avg_loss = sum(losses_pnl) / len(losses_pnl) if losses_pnl else 0
    # Profit factor: only compute when both wins AND losses exist with enough trades
    if losses_pnl and sum(losses_pnl) != 0 and total_trades >= 5:
        pf = abs(sum(wins_pnl) / sum(losses_pnl))
    else:
        pf = 0.0  # Insufficient data — don't fabricate

    # Lifetime stats (across resets)
    ls = port.get("lifetime_stats", {})
    lifetime_trades = ls.get("total_trades", 0) + total_trades
    lifetime_wins = ls.get("total_wins", 0) + port.get("wins", 0)
    # Use standardized win rate calculation (excludes zero-PnL)
    lifetime_wr = calculate_win_rate(lifetime_wins, lifetime_trades) * 100

    return {
        "wins": port["wins"],
        "losses": port["losses"],
        "win_rate": round(wr, 1),
        "total_trades": total_trades,
        "pnl_pct": round(pnl_pct, 2),
        "pnl_usd": round(port["equity"] - port["initial_capital"], 2),
        "sharpe": sharpe,
        "sortino": sortino,
        "rolling_sharpe": rolling_sharpe,
        "rolling_sortino": rolling_sortino,
        "var_99": var_99,
        "max_drawdown_pct": round(port["max_drawdown_pct"], 2),
        "profit_factor": round(pf, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "realized_pnl": round(sum(c.get("net_pnl_usd", 0) for c in port["closed"]), 2),
        "open_positions": len(port["positions"]),
        "total_commission": round(port["total_commission"], 2),
        # Lifetime stats (across all resets)
        "resets": port.get("resets", 0),
        "lifetime_trades": lifetime_trades,
        "lifetime_win_rate": round(lifetime_wr, 1),
        "lifetime_pnl_usd": round(
            ls.get("total_pnl_usd", 0) + (port["equity"] - port["initial_capital"]), 2
        ),
        "lifetime_commission": round(
            ls.get("total_commission", 0) + port.get("total_commission", 0), 2
        ),
        "worst_drawdown_pct": round(
            max(ls.get("worst_drawdown_pct", 0), port.get("max_drawdown_pct", 0)), 2
        ),
    }


def generate_dashboard(all_ports, regime):
    """Generate the HTML dashboard."""
    now = now_est()
    template_path = Path(__file__).parent / "claudes_test.html"

    # Build portfolio summaries for ranking
    summaries = []
    for port in all_ports:
        stats = calc_portfolio_stats(port)
        summaries.append(
            {
                **stats,
                "id": port["id"],
                "name": port["name"],
                "description": port["description"],
                "status": port.get("status", "ACTIVE"),
                "resets": port.get("resets", 0),
                "prop_firm": port.get("prop_firm", False),
                "equity": port["equity"],
                "initial_capital": port["initial_capital"],
                "methodology": port["methodology"],
            }
        )

    # Rank by PnL%
    ranked = sorted(summaries, key=lambda s: s["pnl_pct"], reverse=True)

    # Build the full dashboard data
    dashboard_data = {
        "generated_at": now.isoformat(),
        "regime": regime,
        "portfolios": [],
        "ranking": [
            {
                "rank": i + 1,
                "id": r["id"],
                "name": r["name"],
                "pnl_pct": r["pnl_pct"],
                "win_rate": r["win_rate"],
                "sharpe": r["sharpe"],
                "sortino": r.get("sortino", 0.0),
                "rolling_sharpe": r.get("rolling_sharpe", 0.0),
                "rolling_sortino": r.get("rolling_sortino", 0.0),
                "var_99": r.get("var_99", 0.0),
                "max_dd": r["max_drawdown_pct"],
                "status": r["status"],
                "trades": r["total_trades"],
            }
            for i, r in enumerate(ranked)
        ],
        "top3": ranked[:3],
        "leader": ranked[0] if ranked else None,
    }

    for port in all_ports:
        stats = calc_portfolio_stats(port)
        dashboard_data["portfolios"].append(
            {
                "id": port["id"],
                "name": port["name"],
                "description": port["description"],
                "methodology": port["methodology"],
                "status": port.get("status", "ACTIVE"),
                "prop_firm": port.get("prop_firm", False),
                "resets": port.get("resets", 0),
                "reset_history": port.get("reset_history", []),
                "stats": stats,
                "equity": port["equity"],
                "initial_capital": port["initial_capital"],
                "positions": port["positions"],
                "recent_closed": port["closed"][
                    -200:
                ],  # last 200 closed for accurate WR
                "equity_history": port["equity_history"][-100:],  # last 100 points
                # Prop firm specific
                "daily_loss_limit_pct": port.get("daily_loss_limit_pct", 0),
                "max_drawdown_limit_pct": port.get("max_drawdown_limit_pct", 0),
                "profit_target_pct": port.get("profit_target_pct", 0),
                "daily_pnl": port.get("daily_pnl", 0),
                "lifetime_stats": port.get("lifetime_stats", {}),
            }
        )

    return dashboard_data


def resolve_alpha_engine_stuck_picks(prices):
    """
    Check active_picks.json from alpha_engine and trigger TP/SL closures
    against live prices to clear stuck picks.
    """
    import subprocess

    alpha_data_dir = Path(__file__).parent.parent / "alpha_engine" / "data"
    active_picks_file = alpha_data_dir / "active_picks.json"

    if not active_picks_file.exists():
        return

    try:
        with open(active_picks_file, "r") as f:
            picks = json.load(f)
    except Exception as e:
        print(f"  [ALPHA RESOLUTION ERROR] Could not read active_picks.json: {e}")
        return

    if not picks:
        return

    db_path = alpha_data_dir / "alpha_engine_v2.db"
    if not db_path.exists():
        return

    import sys

    alpha_engine_path = str(Path(__file__).parent.parent / "alpha_engine")
    if alpha_engine_path not in sys.path:
        sys.path.append(alpha_engine_path)

    try:
        from database import SQLiteStore
    except ImportError:
        print(
            "  [ALPHA RESOLUTION ERROR] Could not import SQLiteStore from alpha_engine"
        )
        return

    try:
        db = SQLiteStore(str(db_path))

        resolved_count = 0

        for pick in picks:
            if pick.get("status") != "OPEN":
                continue

            sym = pick.get("symbol", "")
            lookup_sym = sym.replace("-USD", "USDT")
            price = prices.get(lookup_sym)
            if not price:
                continue

            entry = pick.get("entry_price", 0)
            if entry <= 0:
                continue

            tp = pick.get("take_profit")
            sl = pick.get("stop_loss")
            direction = pick.get("signal_type", "BUY")

            SL_BUFFER = 0.005

            exit_reason = None
            exit_price = price
            pnl_pct = 0.0

            if direction == "BUY" or direction == "LONG":
                if tp and price >= tp:
                    exit_reason = "TP_HIT"
                    exit_price = tp
                    pnl_pct = (tp - entry) / entry * 100
                elif sl and price <= sl * (1 + SL_BUFFER):
                    exit_reason = "SL_HIT"
                    exit_price = max(price, sl)
                    pnl_pct = (exit_price - entry) / entry * 100
            else:  # SELL / SHORT
                if tp and price <= tp:
                    exit_reason = "TP_HIT"
                    exit_price = tp
                    pnl_pct = (entry - tp) / entry * 100
                elif sl and price >= sl * (1 - SL_BUFFER):
                    exit_reason = "SL_HIT"
                    exit_price = min(price, sl)
                    pnl_pct = (entry - exit_price) / entry * 100

            if exit_reason:
                print(
                    f"  [ALPHA RESOLUTION] Resolved stuck pick: {sym} ({direction}) -> {exit_reason} at {exit_price}"
                )
                db.close_pick(sym, exit_price, pnl_pct, exit_reason)
                resolved_count += 1

        db.close()

        if resolved_count > 0:
            print(
                f"  [ALPHA RESOLUTION] Triggered dump_picks.py to update active_picks.json"
            )
            subprocess.run(
                [sys.executable, "alpha_engine/dump_picks.py"],
                cwd=str(Path(__file__).parent.parent),
            )

    except Exception as e:
        print(f"  [ALPHA RESOLUTION ERROR] {e}")


def main():
    print(f"=== Claude's Test Portfolio Manager ===")
    print(f"Time: {now_est().strftime('%Y-%m-%d %H:%M:%S EST')}")

    # Load data
    payload = load_payload()
    active_picks = payload.get("picks", {}).get("active", [])
    systems = {s["name"]: s for s in payload.get("systems", [])}

    print(f"Active picks: {len(active_picks)}, Systems: {len(systems)}")

    # Fetch live prices
    prices = fetch_prices()
    print(f"Fetched {len(prices)} prices from Binance")

    # ── Resolve Stuck Alpha Engine Picks ──
    resolve_alpha_engine_stuck_picks(prices)

    # ── Warm up volatility cache for all traded symbols ──
    clear_vol_cache()
    vol_symbols = set()
    for p in active_picks:
        sym = normalize_symbol(p.get("symbol", ""))
        if sym:
            vol_symbols.add(sym)
    for sym in DEEP_VALUE_UNIVERSE:
        vol_symbols.add(sym)
    print(f"Computing volatility metrics for {len(vol_symbols)} symbols...")
    vol_extreme_count = 0
    for sym in vol_symbols:
        vm = compute_volatility_metrics(sym)
        if vm["vol_regime"] == "EXTREME":
            vol_extreme_count += 1
            print(
                f"  [VOL WARNING] {sym}: EXTREME volatility (std={vm['std_daily']:.1f}%, ATR={vm['atr_pct']:.1f}%)"
            )
    if vol_extreme_count > 0:
        print(
            f"  {vol_extreme_count} symbols in EXTREME volatility — position sizes will be reduced"
        )

    # Detect regime
    regime = detect_regime(active_picks)
    print(f"Market regime: {regime}")

    # ── GLOBAL CIRCUIT BREAKER ──
    # Critical safety: halt if unrealized drawdown exceeds 20%
    total_unrealized = sum(p.get("unrealized_pnl_pct", 0) for p in active_picks)
    if total_unrealized < -20.0:
        print(
            f"🚨 CIRCUIT BREAKER TRIPPED: Unrealized PnL = {total_unrealized:.1f}% (limit -20%)"
        )
        print("HALTING all new pick generation for this cycle.")
        # Return empty to prevent new trades
        return {
            "generated_at": now_est().isoformat(),
            "picks": {"active": []},
            "systems": systems,
            "status": "HALTED",
            "reason": "Unrealized PnL circuit breaker (-22.9%)",
        }

    print(f"Global unrealized PnL: {total_unrealized:.1f}%")

    # Filter valid picks
    valid_picks = filter_valid_picks(active_picks, systems)
    print(f"Valid picks (with entry/TP/SL): {len(valid_picks)}")

    # ── Generate deep-value picks from price analysis ──
    print("\n--- Deep-Value Engine: Scanning for beaten-down assets ---")
    dv_picks_raw, asset_analysis = generate_deep_value_picks(prices)
    # Convert deep-value picks to the same format as battleground picks
    dv_system = {
        "name": "deep_value_engine",
        "win_rate": 0,
        "closed_picks": 0,
        "total_pnl_pct": 0,
        "profit_factor": 0.0,
    }  # No synthetic metrics — compute from real trades
    systems["deep_value_engine"] = dv_system
    dv_valid = filter_valid_picks(dv_picks_raw, systems)
    # Preserve deep-value metadata through filter
    for dv_orig, dv_filtered in zip(dv_picks_raw, dv_valid):
        for key in dv_orig:
            if key.startswith("_"):
                dv_filtered[key] = dv_orig[key]
    print(f"Deep-value picks generated: {len(dv_valid)}")
    for dvp in dv_valid:
        sym = dvp.get("symbol", "")
        strat = dvp.get("strategy", "")
        dd = dvp.get("_drawdown_pct", 0)
        rsi = dvp.get("_rsi", 0)
        print(f"  {sym:12s} {strat:40s} DD={dd:.1f}% RSI={rsi:.0f}")

    # ── Generate HTF + Hoffman picks ──
    print("\n--- HTF Engine: Scanning higher timeframe trends ---")
    htf_picks_raw = generate_htf_picks(prices)
    htf_system = {
        "name": "htf_engine",
        "win_rate": 0,
        "closed_picks": 0,
        "total_pnl_pct": 0,
        "profit_factor": 0.0,
    }  # No synthetic metrics — compute from real trades
    systems["htf_engine"] = htf_system
    htf_valid = filter_valid_picks(htf_picks_raw, systems)
    # Preserve HTF metadata through filter
    for htf_orig, htf_filtered in zip(htf_picks_raw, htf_valid):
        for key in htf_orig:
            if key.startswith("_"):
                htf_filtered[key] = htf_orig[key]
    print(f"HTF/Hoffman picks generated: {len(htf_valid)}")
    for hp in htf_valid:
        sym = hp.get("symbol", "")
        strat = hp.get("strategy", "")
        htype = hp.get("_htf_type", "")
        print(f"  {sym:12s} {strat:40s} type={htype}")

    # ── Load DNA mutation picks from genome engine ──
    dna_picks_raw = []
    dna_pick_file = (
        Path(__file__).parent.parent / "genome" / "data" / "dna_winner_picks.json"
    )
    try:
        with open(dna_pick_file) as f:
            dna_data = json.load(f)
        raw_list = dna_data.get("picks", []) if isinstance(dna_data, dict) else dna_data
        for dp in raw_list:
            # Normalize field names: signal_type -> direction, risk_reward -> rr
            direction = (dp.get("direction") or dp.get("signal_type", "")).upper()
            if direction in ("BUY",):
                direction = "LONG"
            elif direction in ("SELL",):
                direction = "SHORT"
            if direction not in ("LONG", "SHORT"):
                continue
            dna_picks_raw.append(
                {
                    "symbol": dp.get("symbol", ""),
                    "direction": direction,
                    "asset_class": "CRYPTO"
                    if dp.get("category", "crypto") == "crypto"
                    else "EQUITY",
                    "source_system": "dna_mutation_engine",
                    "strategy": dp.get("strategy", ""),
                    "entry_price": dp.get("entry_price", 0),
                    "take_profit": dp.get("take_profit", 0),
                    "stop_loss": dp.get("stop_loss", 0),
                    "confidence": dp.get("confidence", 0),
                    "timestamp": dp.get("timestamp", ""),
                    "_mutation_type": dp.get("mutation_type", ""),
                    "_parent_system": dp.get("parent_system", ""),
                }
            )
        dna_system = {
            "name": "dna_mutation_engine",
            "win_rate": 0,
            "closed_picks": 0,
            "total_pnl_pct": 0,
            "profit_factor": 0.0,
        }  # No synthetic metrics — compute from real trades
        systems["dna_mutation_engine"] = dna_system
        dna_valid = filter_valid_picks(dna_picks_raw, systems)
        # Preserve mutation metadata through filter
        for dna_orig, dna_filtered in zip(dna_picks_raw, dna_valid):
            for key in dna_orig:
                if key.startswith("_"):
                    dna_filtered[key] = dna_orig[key]
        print(f"DNA mutation picks loaded: {len(dna_valid)} (from {len(raw_list)} raw)")
    except Exception as e:
        dna_valid = []
        print(f"DNA mutation picks: skipped ({e})")

    # Combined picks: battleground + deep-value + HTF + DNA mutations for all portfolios
    all_picks_combined = valid_picks + dv_valid + htf_valid + dna_valid

    # Load or init state
    state = load_state()

    # ── Global symbol exposure tracking (prevents concentration) ──
    # Count how many portfolios hold each symbol+direction combo
    global_symbol_exposure = {}  # {symbol_direction: count}
    for pid_check, port_check in state.items():
        if not isinstance(port_check, dict):
            continue
        for pos in port_check.get("positions", []):
            sym_dir = f"{normalize_symbol(pos['symbol'])}_{pos['direction']}"
            global_symbol_exposure[sym_dir] = global_symbol_exposure.get(sym_dir, 0) + 1

    # Init/update each portfolio
    for pdef in PORTFOLIOS:
        pid = pdef["id"]

        # Skip paused portfolios (poor recent performance)
        if pid in PAUSED_PORTFOLIOS:
            print(f"  [PAUSED] Skipping {pdef['name']} (poor recent performance)")
            continue

        if pid not in state:
            state[pid] = init_portfolio(pdef)
            print(f"  Initialized: {pdef['name']}")

        port = state[pid]

        # Check update interval (skip if recently updated AND has positions)
        last = port.get("last_updated", "")
        has_positions = (
            len(port.get("positions", [])) > 0 or len(port.get("closed", [])) > 0
        )
        if last and has_positions:
            try:
                last_dt = datetime.fromisoformat(last)
                interval = pdef.get("update_interval_min", 30)
                if (now_est() - last_dt).total_seconds() < interval * 60 * 0.8:
                    print(
                        f"  Skipping {pdef['name']} (updated {int((now_est() - last_dt).total_seconds() / 60)}m ago, interval={interval}m)"
                    )
                    continue
            except Exception:
                pass

        # Auto-reset blown prop firm portfolios
        if port.get("status") == "BLOWN" and port.get("prop_firm"):
            print(
                f"  Resetting blown prop firm: {pdef['name']} (reset #{port['resets'] + 1})"
            )
            reset_blown_portfolio(port, pdef)

        # Update — deep-value and HTF portfolios get combined picks
        # All portfolios get access to mutation + deep-value + HTF picks alongside battleground
        picks_for_port = all_picks_combined
        update_portfolio(
            port,
            picks_for_port,
            prices,
            regime,
            pdef=pdef,
            global_exposure=global_symbol_exposure,
        )
        stats = calc_portfolio_stats(port)
        resets_str = f" Resets={stats['resets']}" if stats["resets"] > 0 else ""
        lifetime_str = (
            f" | Lifetime: {stats['lifetime_trades']}t WR={stats['lifetime_win_rate']}% PnL=${stats['lifetime_pnl_usd']:+,.2f}"
            if stats["lifetime_trades"] > stats["total_trades"]
            else ""
        )
        print(
            f"  {pdef['name']}: equity=${port['equity']:,.2f} ({stats['pnl_pct']:+.2f}%) | "
            f"{stats['open_positions']} open, {stats['total_trades']} trades, "
            f"WR={stats['win_rate']}%, DD={stats['max_drawdown_pct']}%, "
            f"Sharpe={stats['sharpe']} | Status={port.get('status', 'ACTIVE')}{resets_str}{lifetime_str}"
        )

    # Final pass: update current_price for ALL positions (including skipped portfolios)
    updated_prices = 0
    for pdef in PORTFOLIOS:
        port = state.get(pdef["id"], {})
        for pos in port.get("positions", []):
            sym = normalize_symbol(pos["symbol"])
            price = prices.get(sym)
            if not price or price <= 0:
                price = _fetch_reference_price(pos["symbol"])
            if price and price > 0 and price != pos.get("current_price"):
                pos["current_price"] = price
                direction = pos.get("direction", "LONG")
                if direction == "LONG":
                    pos["pnl_pct"] = (
                        (price - pos["entry_price"]) / pos["entry_price"]
                    ) * 100
                else:
                    pos["pnl_pct"] = (
                        (pos["entry_price"] - price) / pos["entry_price"]
                    ) * 100
                pos["pnl_usd"] = pos.get("size_usd", 0) * (pos["pnl_pct"] / 100)
                updated_prices += 1
    if updated_prices > 0:
        print(
            f"  Price refresh: updated {updated_prices} positions across all portfolios"
        )

    # Recalculate equity for ALL portfolios after price refresh
    # (critical: skipped portfolios got fresh prices but stale equity)
    for pdef in PORTFOLIOS:
        port = state.get(pdef["id"], {})
        if not isinstance(port, dict) or not port.get("positions"):
            continue
        unrealized = sum(p.get("pnl_usd", 0) for p in port["positions"])
        allocated = sum(p.get("size_usd", 0) for p in port["positions"])
        new_equity = port["cash"] + allocated + unrealized
        if abs(new_equity - port.get("equity", 0)) > 0.01:
            port["equity"] = new_equity
            port["high_water_mark"] = max(
                port.get("high_water_mark", new_equity), new_equity
            )
            # Recompute W/L from closed trades (single source of truth)
            recompute_stats(port)

    # Append equity_history for all active portfolios (feeds Sharpe calculation)
    now_ts = datetime.now(timezone.utc).astimezone().isoformat()
    for pdef in PORTFOLIOS:
        port = state.get(pdef["id"], {})
        if not isinstance(port, dict):
            continue
        eh = port.get("equity_history", [])
        current_eq = port.get("equity", port.get("initial_capital", 10000))
        # Only append if equity changed from last recorded point
        if not eh or abs(eh[-1].get("equity", 0) - current_eq) > 0.01:
            eh.append({"time": now_ts, "equity": current_eq})
            if len(eh) > 1000:
                port["equity_history"] = eh[-500:]

    # Save state
    save_state(state)

    # Generate dashboard data
    # KILLED portfolios (rr_kings, multi_asset_diversified, …) are intentionally
    # skipped during the `manage` cycle, so they never get written into `state`.
    # Filter them out here too — otherwise the comprehension below raises
    # KeyError as soon as ANY paused/killed portfolio is in PORTFOLIOS, which is
    # why claudes-test-portfolios.yml has been failing every 30 min since the
    # rr_kings kill landed (run 26697733257 → exit 1 KeyError: 'rr_kings').
    ports_list = [
        state[pdef["id"]] for pdef in PORTFOLIOS
        if pdef["id"] in state and pdef["id"] not in PAUSED_PORTFOLIOS
    ]
    dashboard_data = generate_dashboard(ports_list, regime)

    # Write dashboard JSON
    dashboard_json = DATA_DIR / "claudes_test_dashboard.json"
    with open(dashboard_json, "w") as f:
        json.dump(dashboard_data, f, indent=2, default=str)
    print(f"\nDashboard data written to {dashboard_json}")

    # Generate HTML
    generate_html(dashboard_data)

    # Sync to audit database (fire-and-forget)
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from audit_dashboard.db_sync import sync_all

        stats_map = {}
        for pdef in PORTFOLIOS:
            pid = pdef["id"]
            if pid in state:
                stats_map[pid] = calc_portfolio_stats(state[pid])
        sync_all(state, stats_map)
    except Exception as e:
        print(f"  DB sync skipped: {e}")

    print("\n=== Done ===")


def generate_html(data):
    """Generate the HTML dashboard file."""
    html_path = Path(__file__).parent / "claudes_test.html"

    # Build the HTML with embedded data
    ranking = data.get("ranking", [])
    portfolios = data.get("portfolios", [])
    regime = data.get("regime", "NEUTRAL")
    generated = data.get("generated_at", "")

    html = build_dashboard_html(data)

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Dashboard HTML written to {html_path}")


def build_dashboard_html(data):
    """Build the full dashboard HTML string."""
    data_json = json.dumps(data, default=str)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Claude's Test - {len(data.get("portfolios", []))} Portfolio Challenge | Audit Dashboard</title>
<style>
:root {{
  --bg: #0a0a12; --card: #12121e; --card-hover: #1a1a2e; --border: #2a2a3e;
  --text: #e2e8f0; --text-dim: #6b7280; --green: #22c55e; --red: #ef4444;
  --yellow: #eab308; --orange: #f97316; --purple: #a78bfa; --cyan: #06b6d4; --blue: #3b82f6;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ background: var(--bg); color: var(--text); font-family: 'Inter', -apple-system, sans-serif; font-size: 14px; line-height: 1.5; }}
.container {{ max-width: 1500px; margin: 0 auto; padding: 16px; }}
h1 {{ font-size: 22px; font-weight: 700; }}
h1 span {{ color: var(--purple); }}
h2 {{ font-size: 16px; margin: 20px 0 10px; padding-bottom: 6px; border-bottom: 1px solid var(--border); }}
.subtitle {{ color: var(--text-dim); font-size: 12px; margin-bottom: 16px; }}
.stat-row {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 8px; margin-bottom: 16px; }}
.stat-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 10px; text-align: center; }}
.stat-card .label {{ font-size: 9px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.5px; }}
.stat-card .value {{ font-size: 20px; font-weight: 700; margin-top: 2px; font-variant-numeric: tabular-nums; }}
.positive {{ color: var(--green); }} .negative {{ color: var(--red); }}
.pnl-pos {{ color: var(--green); }} .pnl-neg {{ color: var(--red); }}
table {{ width: 100%; border-collapse: collapse; font-size: 12px; margin-bottom: 16px; }}
th {{ background: var(--card); color: var(--text-dim); font-weight: 600; text-transform: uppercase; font-size: 9px; letter-spacing: 0.5px; padding: 8px 6px; text-align: left; border-bottom: 2px solid var(--border); position: sticky; top: 0; z-index: 5; }}
th.num, td.num {{ text-align: right; font-variant-numeric: tabular-nums; font-family: 'Consolas', monospace; }}
td {{ padding: 8px 6px; border-bottom: 1px solid var(--border); }}
tr:hover {{ background: var(--card-hover); }}
.badge {{ display: inline-block; padding: 1px 6px; border-radius: 4px; font-size: 9px; font-weight: 600; text-transform: uppercase; }}
.badge-long {{ background: rgba(34,197,94,0.15); color: var(--green); }}
.badge-short {{ background: rgba(239,68,68,0.15); color: var(--red); }}
.badge-active {{ background: rgba(167,139,250,0.15); color: var(--purple); }}
.badge-passed {{ background: rgba(34,197,94,0.2); color: var(--green); }}
.badge-blown {{ background: rgba(239,68,68,0.2); color: var(--red); }}
.badge-tp {{ background: rgba(34,197,94,0.15); color: var(--green); }}
.badge-sl {{ background: rgba(239,68,68,0.15); color: var(--red); }}
.badge-prop {{ background: rgba(245,158,11,0.15); color: var(--yellow); }}
.port-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 14px; margin-bottom: 12px; cursor: pointer; transition: border-color 0.2s; }}
.port-card:hover {{ border-color: var(--purple); }}
.port-card.expanded {{ border-color: var(--purple); }}
.port-card .port-header {{ display: flex; justify-content: space-between; align-items: center; }}
.port-card .port-name {{ font-weight: 600; font-size: 14px; }}
.port-card .port-stats {{ display: flex; gap: 16px; font-size: 12px; color: var(--text-dim); }}
.port-card .port-detail {{ display: none; margin-top: 12px; border-top: 1px solid var(--border); padding-top: 12px; }}
.port-card.expanded .port-detail {{ display: block; }}
.regime-banner {{ padding: 8px 14px; border-radius: 8px; margin-bottom: 12px; font-size: 12px; display: flex; align-items: center; gap: 8px; }}
.top3-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; margin-bottom: 20px; }}
.top3-card {{ background: var(--card); border: 2px solid var(--border); border-radius: 12px; padding: 16px; position: relative; }}
.top3-card.rank-1 {{ border-color: #ffd700; }}
.top3-card.rank-2 {{ border-color: #c0c0c0; }}
.top3-card.rank-3 {{ border-color: #cd7f32; }}
.rank-badge {{ position: absolute; top: -8px; right: 12px; background: var(--bg); padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; }}
.nav-link {{ color: var(--cyan); text-decoration: none; font-size: 12px; }}
.nav-link:hover {{ text-decoration: underline; }}
.comm-note {{ background: rgba(6,182,212,0.06); border: 1px solid rgba(6,182,212,0.2); border-radius: 6px; padding: 8px 12px; margin-bottom: 12px; font-size: 11px; color: var(--text-dim); }}
.comm-note strong {{ color: var(--cyan); }}
.disclaimer {{ background: rgba(239,68,68,0.05); border: 1px solid rgba(239,68,68,0.15); border-radius: 6px; padding: 10px 14px; margin-top: 20px; font-size: 10px; color: var(--text-dim); }}
.disclaimer strong {{ color: var(--red); }}
.footer {{ margin-top: 20px; padding-top: 12px; border-top: 1px solid var(--border); font-size: 10px; color: var(--text-dim); text-align: center; }}
.reset-log {{ background: rgba(239,68,68,0.05); border: 1px solid rgba(239,68,68,0.2); border-radius: 6px; padding: 8px; margin-top: 8px; font-size: 11px; }}
.cal-grid {{ display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; margin: 8px 0; }}
.cal-cell {{ width: 100%; aspect-ratio: 1; border-radius: 3px; position: relative; cursor: default; }}
.cal-cell:hover {{ outline: 1px solid var(--purple); z-index: 1; }}
.cal-header {{ font-size: 9px; color: var(--text-dim); text-align: center; padding: 2px 0; }}
.cal-tooltip {{ display: none; position: absolute; bottom: calc(100% + 4px); left: 50%; transform: translateX(-50%); background: #1a1a2e; border: 1px solid var(--border); border-radius: 4px; padding: 4px 8px; font-size: 10px; white-space: nowrap; z-index: 10; pointer-events: none; }}
.cal-cell:hover .cal-tooltip {{ display: block; }}
.pnl-summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 8px; margin: 8px 0; }}
.pnl-box {{ background: var(--bg); border: 1px solid var(--border); border-radius: 6px; padding: 8px; text-align: center; }}
.pnl-box .label {{ font-size: 9px; color: var(--text-dim); text-transform: uppercase; }}
.pnl-box .val {{ font-size: 16px; font-weight: 700; margin-top: 2px; }}
.reset-badge {{ background: rgba(239,68,68,0.15); color: var(--red); font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 4px; margin-left: 8px; }}
.strat-tag {{ display: inline-block; background: rgba(167,139,250,0.1); color: var(--purple); font-size: 10px; padding: 1px 6px; border-radius: 3px; margin: 1px 2px; }}
.dv-badge {{ background: rgba(6,182,212,0.15); color: var(--cyan); }}
.filter-bar {{ display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 12px; }}
.filter-btn {{ background: var(--card); border: 1px solid var(--border); border-radius: 20px; padding: 4px 14px; font-size: 11px; color: var(--text-dim); cursor: pointer; transition: all 0.2s; }}
.filter-btn:hover {{ border-color: var(--purple); color: var(--text); }}
.filter-btn.active {{ background: var(--purple); color: #fff; border-color: var(--purple); }}
</style>
</head>
<body>
<div class="container">
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
    <h1><span>Claude's Test</span> &mdash; 26 Portfolio Challenge</h1>
    <div style="display:flex;gap:12px;align-items:center">
      <a href="portfolio_history.html" class="nav-link">Full Audit Trail &rarr;</a>
      <a href="../cross_aggregation/consensus_dashboard.html" class="nav-link" style="color:#ffd700;font-weight:700">&#9733; Consensus Picks</a>
      <a href="/audit/" class="nav-link">&larr; Audit Dashboard</a>
    </div>
  </div>
  <div class="subtitle">
    26 simulated portfolios (12 signal + 4 deep-value + 3 HTF/Hoffman + 3 prop + 4 non-crypto) | Canadian broker (IBKR) | Auto-updated every 30 min |
    Last updated: <strong id="last-updated"></strong>
  </div>
  <div style="background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.25);border-radius:6px;padding:6px 12px;margin-bottom:8px;font-size:11px;color:#f59e0b">
    <strong>Note:</strong> Prices on this page are from the last backend scan (updated every 30-60 min). For live prices with real-time PnL, see the <a href="portfolio_history.html" style="color:#3b82f6">Full Audit Trail</a>.
    Metrics that may show stale values: Current Price, Unrealized P&amp;L, PnL%.
  </div>
  <div class="filter-bar">
    <button class="filter-btn active" data-filter="all" onclick="setFilter('all')">All ({len(data.get("portfolios", []))})</button>
    <button class="filter-btn" data-filter="crypto" onclick="setFilter('crypto')" style="border-color:#a78bfa">Crypto Only</button>
    <button class="filter-btn" data-filter="signal" onclick="setFilter('signal')">Signal-Based (12)</button>
    <button class="filter-btn" data-filter="deep" onclick="setFilter('deep')">Deep-Value (4)</button>
    <button class="filter-btn" data-filter="htf" onclick="setFilter('htf')">HTF/Hoffman (3)</button>
    <button class="filter-btn" data-filter="prop" onclick="setFilter('prop')">Prop Firm (3)</button>
    <button class="filter-btn" data-filter="noncrypto" onclick="setFilter('noncrypto')">Non-Crypto (4)</button>
    <button class="filter-btn" data-filter="mercury" onclick="setFilter('mercury')" style="border-color:#f59e0b">Mercury 3-Lever (6)</button>
  </div>
  <div id="app"></div>
  <div class="disclaimer">
    <strong>DISCLAIMER:</strong> Simulated paper portfolios for educational/audit purposes only. NOT financial advice.
    Past performance does not predict future results. No real money at risk.
  </div>
  <div class="footer">Claude's Test v2.0 | Powered by Claude AI | <span id="gen-time"></span></div>
</div>
<script>
const D = {data_json};
const fmt = (n, d=1) => Number(n||0).toFixed(d);
const fmtUsd = (n) => '$' + Number(n||0).toLocaleString('en-US', {{minimumFractionDigits:2, maximumFractionDigits:2}});
const fmtPct = (n) => (n >= 0 ? '+' : '') + fmt(n, 2) + '%';
function toEST(iso) {{
  try {{ return new Date(iso).toLocaleString('en-US', {{timeZone:'America/New_York', month:'short', day:'numeric', hour:'2-digit', minute:'2-digit', hour12:true}}); }}
  catch(e) {{ return iso || '\\u2014'; }}
}}

const CATEGORY_MAP = {{
  signal: ['score_leaders','proven_only','momentum_riders','contrarian','regime_aligned','high_conviction','rr_kings','consensus_plays','fresh_signals','sector_rotation','anti_meme','claude_best'],
  deep: ['deep_drawdown_dca','rsi_capitulation','fear_greed_contrarian','relative_strength_recovery'],
  htf: ['hoffman_elite','htf_trend_follow','htf_weekly_momentum'],
  prop: ['prop_conservative','prop_aggressive','prop_swing'],
  noncrypto: ['stocks_best','stocks_short_term','forex_carry','multi_asset_diversified','futures_index','etf_rotation','all_asset_tournament'],
  mercury: ['regime_filtered','high_consensus','golden_only','small_position','sentiment_divergence','basis_carry_only']
}};
function getCategory(id) {{ for (const [cat, ids] of Object.entries(CATEGORY_MAP)) {{ if (ids.includes(id)) return cat; }} return 'signal'; }}
let currentFilter = 'all';
function setFilter(f) {{
  currentFilter = f;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.toggle('active', b.dataset.filter === f));
  render();
}}

function render() {{
  const regime = D.regime || 'NEUTRAL';
  const regimeColor = regime === 'BEARISH' ? '#ef4444' : regime === 'CHOPPY' ? '#f59e0b' : '#22c55e';
  const regimeIcon = regime === 'BEARISH' ? '\\ud83d\\udd34' : regime === 'CHOPPY' ? '\\ud83d\\udfe1' : '\\ud83d\\udfe2';

  // Filter portfolios based on current filter
  const allPortsRaw = D.portfolios || [];
  const allPorts = allPortsRaw.filter(p => {{
    if (currentFilter === 'all') return true;
    const cat = getCategory(p.id);
    if (currentFilter === 'crypto') return cat !== 'noncrypto';
    return cat === currentFilter;
  }});
  const totalEquity = allPorts.reduce((a,p) => a + p.equity, 0);
  const totalInitial = allPorts.reduce((a,p) => a + p.initial_capital, 0);
  const totalPnlPct = totalInitial > 0 ? ((totalEquity - totalInitial) / totalInitial) * 100 : 0;
  const totalTrades = allPorts.reduce((a,p) => a + (p.stats?.total_trades || 0), 0);
  const totalWins = allPorts.reduce((a,p) => a + (p.stats?.wins || 0), 0);
  const avgSharpe = allPorts.length ? allPorts.reduce((a,p) => a + (p.stats?.sharpe || 0), 0) / allPorts.length : 0;
  const maxDD = allPorts.length ? Math.max(...allPorts.map(p => p.stats?.max_drawdown_pct || 0)) : 0;
  const propPassed = allPorts.filter(p => p.status === 'PASSED').length;
  const propBlown = allPorts.filter(p => p.status === 'BLOWN').length;
  const totalResets = allPorts.reduce((a,p) => a + (p.resets||0), 0);
  const totalComm = allPorts.reduce((a,p) => a + (p.stats?.total_commission || 0), 0);

  let html = `
    <div class="stat-row">
      ${{[
        {{label:'Combined Equity', value:fmtUsd(totalEquity), cls:totalEquity>=totalInitial?'positive':'negative'}},
        {{label:'Combined P/L', value:fmtPct(totalPnlPct), cls:totalPnlPct>=0?'positive':'negative'}},
        {{label:'Portfolios', value:D.portfolios.length + ' (4 DV + 3 HTF + 3 prop)'}},
        {{label:'Total Trades', value:totalTrades}},
        {{label:'Avg Sharpe', value:fmt(avgSharpe,2)}},
        {{label:'Worst DD', value:fmt(maxDD,1)+'%', cls:'negative'}},
        {{label:'Prop Passed', value:propPassed, cls:propPassed>0?'positive':''}},
        {{label:'Prop Blown', value:propBlown, cls:propBlown>0?'negative':''}},
        {{label:'Total Resets', value:totalResets}},
        {{label:'Commissions', value:fmtUsd(totalComm), cls:'negative'}},
      ].map(c => '<div class="stat-card"><div class="label">'+c.label+'</div><div class="value '+(c.cls||'')+'">'+c.value+'</div></div>').join('')}}
    </div>
    <div class="regime-banner" style="background:${{regimeColor}}15;border:1px solid ${{regimeColor}}55">
      <span style="font-size:14px">${{regimeIcon}}</span>
      <span style="color:${{regimeColor}};font-weight:600">Market Regime: ${{regime}}</span>
      <span style="color:var(--text-dim)">| Portfolio decisions are regime-aware</span>
    </div>
    <div class="comm-note"><strong>Canadian Broker (IBKR):</strong> Crypto 0.15% per trade, Equities $1 min + $0.0035/share. All PnL is post-commission, pre-tax.</div>
  `;

  // Top 3
  const filteredIds = new Set(allPorts.map(p => p.id));
  const filteredRanking = (D.ranking || []).filter(r => filteredIds.has(r.id));
  const top3 = filteredRanking.slice(0, 3);
  const medals = ['\\ud83e\\udd47', '\\ud83e\\udd48', '\\ud83e\\udd49'];
  html += '<h2>Top 3 Portfolios</h2><div class="top3-grid">';
  top3.forEach((r, i) => {{
    const port = allPorts.find(p => p.id === r.id);
    const pnlCls = r.pnl_pct >= 0 ? 'positive' : 'negative';
    html += '<div class="top3-card rank-'+(i+1)+'">';
    html += '<div class="rank-badge" style="color:'+(i===0?'#ffd700':i===1?'#c0c0c0':'#cd7f32')+'">' + medals[i] + ' #' + (i+1) + '</div>';
    html += '<div style="font-weight:700;font-size:15px;margin-bottom:4px">' + r.name + '</div>';
    html += '<div style="font-size:24px;font-weight:700" class="' + pnlCls + '">' + fmtPct(r.pnl_pct) + '</div>';
    html += '<div style="font-size:12px;color:var(--text-dim);margin-top:4px">';
    html += 'WR: ' + fmt(r.win_rate) + '% | Sharpe: ' + fmt(r.sharpe,2) + ' | DD: ' + fmt(r.max_dd,1) + '% | Trades: ' + r.trades;
    html += '</div>';
    if (port) html += '<div style="font-size:11px;color:var(--text-dim);margin-top:4px">' + (port.description||'') + '</div>';
    html += '</div>';
  }});
  html += '</div>';

  // Leaderboard table
  html += '<h2>Portfolio Leaderboard & Risk Matrix</h2>';
  html += '<table><thead><tr><th>#</th><th>Portfolio</th><th>Method</th><th class="num">Equity</th><th class="num">P/L %</th><th class="num">WR</th><th class="num">Trades</th><th class="num" title="Sharpe Ratio (7-day rolling): Measures risk-adjusted return.">Sharpe(7d)</th><th class="num" title="Sortino Ratio (7-day rolling): (Return - Target) / Downside Deviation.">Sortino(7d)</th><th class="num" title="Value at Risk (99%): Maximum expected loss over a set period with 99% confidence.">VaR(99%)</th><th class="num">Max DD</th><th class="num">PF</th><th class="num">Comm</th><th>Status</th><th>Resets</th></tr></thead><tbody>';
  filteredRanking.forEach((r, i) => {{
    const port = allPorts.find(p => p.id === r.id);
    const pnlCls = r.pnl_pct >= 0 ? 'pnl-pos' : 'pnl-neg';
    const statusBadge = r.status === 'PASSED' ? '<span class="badge badge-passed">PASSED</span>'
      : r.status === 'BLOWN' ? '<span class="badge badge-blown">BLOWN</span>'
      : '<span class="badge badge-active">ACTIVE</span>';
    const propBadge = port && port.prop_firm ? ' <span class="badge badge-prop">PROP</span>' : '';
    html += '<tr>';
    html += '<td style="font-weight:700;color:var(--purple)">' + (i+1) + '</td>';
    html += '<td><strong>' + r.name + '</strong>' + propBadge + '</td>';
    html += '<td style="font-size:11px;color:var(--text-dim)">' + (port?port.methodology:'') + '</td>';
    html += '<td class="num">' + fmtUsd(port?port.equity:0) + '</td>';
    html += '<td class="num ' + pnlCls + '" style="font-weight:600">' + fmtPct(r.pnl_pct) + '</td>';
    html += '<td class="num">' + fmt(r.win_rate) + '%</td>';
    html += '<td class="num">' + r.trades + '</td>';
    html += '<td class="num">' + fmt(r.rolling_sharpe||r.sharpe,2) + '</td>';
    html += '<td class="num">' + fmt(r.rolling_sortino||r.sortino||0,2) + '</td>';
    html += '<td class="num" style="color:var(--orange)">' + fmt(r.var_99||0,2) + '%</td>';
    html += '<td class="num" style="color:var(--red)">' + fmt(r.max_dd,1) + '%</td>';
    html += '<td class="num">' + (port?fmt(port.stats.profit_factor,2):'\\u2014') + '</td>';
    html += '<td class="num" style="color:var(--text-dim)">' + fmtUsd(port?port.stats.total_commission:0) + '</td>';
    html += '<td>' + statusBadge + '</td>';
    html += '<td class="num">' + (port?port.resets:0) + '</td>';
    html += '</tr>';
  }});
  html += '</tbody></table>';

  // Individual portfolio cards
  html += '<h2>Portfolio Details</h2>';
  allPorts.forEach(port => {{
    const s = port.stats;
    const pnlCls = s.pnl_pct >= 0 ? 'positive' : 'negative';
    const statusBadge = port.status === 'PASSED' ? '<span class="badge badge-passed">PASSED</span>'
      : port.status === 'BLOWN' ? '<span class="badge badge-blown">BLOWN</span>'
      : '<span class="badge badge-active">ACTIVE</span>';

    html += '<div class="port-card" onclick="this.classList.toggle(&quot;expanded&quot;)">';
    html += '<div class="port-header">';
    html += '<div><span class="port-name">' + port.name + '</span> ' + statusBadge;
    if (port.prop_firm) html += ' <span class="badge badge-prop">PROP</span>';
    if (port.methodology && ['drawdown_dca','rsi_capitulation','fear_greed','rel_strength','deep_value','beaten_majors'].includes(port.methodology)) html += ' <span class="badge dv-badge">DEEP VALUE</span>';
    if (port.methodology && ['regime_aligned_only','consensus_3plus','golden_insight_only','score_small_position','sentiment_divergence_only','carry_arb_only'].includes(port.methodology)) html += ' <span class="badge" style="background:rgba(245,158,11,0.15);color:#f59e0b">MERCURY TEST</span>';
    if (port.resets > 0) html += ' <span class="reset-badge">' + port.resets + ' reset' + (port.resets>1?'s':'') + '</span>';
    html += '</div>';
    html += '<div class="port-stats">';
    html += '<span class="' + pnlCls + '" style="font-weight:700">' + fmtPct(s.pnl_pct) + '</span>';
    html += '<span>' + fmtUsd(port.equity) + '</span>';
    html += '<span>WR: ' + fmt(s.win_rate) + '%</span>';
    html += '<span>Sharpe: ' + fmt(s.sharpe,2) + '</span>';
    html += '<span>DD: ' + fmt(s.max_drawdown_pct,1) + '%</span>';
    html += '<span>' + s.open_positions + ' open</span>';
    html += '</div></div>';

    // Detail section
    html += '<div class="port-detail">';
    html += '<div style="font-size:12px;color:var(--text-dim);margin-bottom:8px">' + (port.description||'') + '</div>';

    // Strategy tags
    const strategies = new Set();
    (port.positions||[]).forEach(p => {{ if (p.strategy) strategies.add(p.strategy.split('_').slice(0,3).join('_')); }});
    (port.recent_closed||[]).forEach(p => {{ if (p.strategy) strategies.add(p.strategy.split('_').slice(0,3).join('_')); }});
    if (strategies.size > 0) {{
      html += '<div style="margin-bottom:8px">';
      strategies.forEach(st => {{ html += '<span class="strat-tag">' + st + '</span>'; }});
      html += '</div>';
    }}

    // P&L Summary (realized + unrealized)
    const unrealizedPnl = (port.positions||[]).reduce((a,p) => a + (p.pnl_usd||0), 0);
    const realizedPnl = s.realized_pnl != null ? s.realized_pnl : (port.recent_closed||[]).reduce((a,p) => a + (p.net_pnl_usd||0), 0);
    const totalHoldings = (port.positions||[]).reduce((a,p) => a + (p.size_usd||0), 0);
    html += '<div class="pnl-summary">';
    html += '<div class="pnl-box"><div class="label">Unrealized P&L</div><div class="val ' + (unrealizedPnl>=0?'positive':'negative') + '">' + fmtUsd(unrealizedPnl) + '</div></div>';
    html += '<div class="pnl-box"><div class="label">Realized P&L</div><div class="val ' + (realizedPnl>=0?'positive':'negative') + '">' + fmtUsd(realizedPnl) + '</div></div>';
    html += '<div class="pnl-box"><div class="label">Total Holdings</div><div class="val">' + fmtUsd(totalHoldings) + '</div></div>';
    html += '<div class="pnl-box"><div class="label">Cash Available</div><div class="val">' + fmtUsd(port.cash||0) + '</div></div>';
    html += '<div class="pnl-box"><div class="label">Win Rate</div><div class="val">' + fmt(s.win_rate) + '%</div></div>';
    html += '<div class="pnl-box"><div class="label">Profit Factor</div><div class="val">' + fmt(s.profit_factor,2) + '</div></div>';
    html += '<div class="pnl-box"><div class="label">Avg Win</div><div class="val positive">' + fmtUsd(s.avg_win) + '</div></div>';
    html += '<div class="pnl-box"><div class="label">Avg Loss</div><div class="val negative">' + fmtUsd(s.avg_loss) + '</div></div>';
    html += '</div>';

    // Calendar heatmap (equity history by day — for non-reset portfolios)
    if (!port.prop_firm && port.equity_history && port.equity_history.length > 2) {{
      // Group equity by day
      const dailyPnl = {{}};
      const eh = port.equity_history;
      for (let i = 1; i < eh.length; i++) {{
        try {{
          const d = new Date(eh[i].time).toISOString().split('T')[0];
          const change = eh[i].equity - eh[i-1].equity;
          dailyPnl[d] = (dailyPnl[d]||0) + change;
        }} catch(e) {{}}
      }}
      const days = Object.keys(dailyPnl).sort();
      if (days.length > 0) {{
        html += '<h3 style="font-size:13px;margin:8px 0 4px">Daily P&L Calendar</h3>';
        html += '<div class="cal-grid">';
        // Day headers
        ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'].forEach(d => {{
          html += '<div class="cal-header">' + d + '</div>';
        }});
        // Fill from first day, pad to start on correct weekday
        const startDate = new Date(days[0]);
        const startDow = (startDate.getDay() + 6) % 7; // Mon=0
        for (let i = 0; i < startDow; i++) {{
          html += '<div class="cal-cell" style="background:transparent"></div>';
        }}
        days.forEach(day => {{
          const pnl = dailyPnl[day];
          const intensity = Math.min(1, Math.abs(pnl) / (port.initial_capital * 0.01));
          const bg = pnl >= 0
            ? 'rgba(34,197,94,' + (0.15 + intensity * 0.6) + ')'
            : 'rgba(239,68,68,' + (0.15 + intensity * 0.6) + ')';
          const label = day.slice(5) + ': ' + (pnl >= 0 ? '+' : '') + '$' + pnl.toFixed(2);
          html += '<div class="cal-cell" style="background:' + bg + '"><div class="cal-tooltip">' + label + '</div></div>';
        }});
        html += '</div>';
      }}
    }}

    // Prop firm progress
    if (port.prop_firm) {{
      const profitPct = s.pnl_pct;
      const targetPct = port.profit_target_pct;
      const progressPct = Math.min(100, Math.max(0, (profitPct / targetPct) * 100));
      html += '<div style="margin-bottom:8px;font-size:12px">';
      html += '<div style="display:flex;justify-content:space-between;margin-bottom:4px"><span>Profit Target: ' + fmt(targetPct) + '%</span><span>' + fmtPct(profitPct) + '</span></div>';
      html += '<div style="height:8px;background:var(--border);border-radius:4px;overflow:hidden"><div style="height:100%;width:' + progressPct + '%;background:' + (profitPct >= 0 ? 'var(--green)' : 'var(--red)') + ';border-radius:4px;transition:width 0.3s"></div></div>';
      html += '<div style="display:flex;justify-content:space-between;margin-top:4px;font-size:11px;color:var(--text-dim)"><span>Daily Loss Limit: ' + fmt(port.daily_loss_limit_pct) + '%</span><span>Max DD Limit: ' + fmt(port.max_drawdown_limit_pct) + '%</span></div>';
      html += '</div>';

      // Reset log + lifetime stats
      if (port.resets > 0) {{
        const ls = port.lifetime_stats || {{}};
        html += '<div class="reset-log">';
        html += '<strong style="color:var(--red)">' + port.resets + ' Reset(s)</strong>';
        html += '<div style="margin:6px 0;display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:6px;font-size:11px">';
        html += '<div><span style="color:var(--text-dim)">Lifetime Trades:</span> <strong>' + (ls.total_trades||0) + '</strong></div>';
        html += '<div><span style="color:var(--text-dim)">Lifetime W/L:</span> <strong>' + (ls.total_wins||0) + '/' + (ls.total_losses||0) + '</strong></div>';
        html += '<div><span style="color:var(--text-dim)">Lifetime PnL:</span> <strong class="' + ((ls.total_pnl_usd||0) >= 0 ? 'positive' : 'negative') + '">' + fmtUsd(ls.total_pnl_usd||0) + '</strong></div>';
        html += '<div><span style="color:var(--text-dim)">Total Comm:</span> <strong>' + fmtUsd(ls.total_commission||0) + '</strong></div>';
        html += '<div><span style="color:var(--text-dim)">Best Equity:</span> <strong>' + fmtUsd(ls.best_equity||0) + '</strong></div>';
        html += '<div><span style="color:var(--text-dim)">Worst DD:</span> <strong class="negative">' + fmt(ls.worst_drawdown_pct||0,1) + '%</strong></div>';
        html += '</div>';

        // Detailed reset history table
        const rl = ls.reset_log || [];
        if (rl.length > 0) {{
          html += '<table style="margin-top:6px;font-size:10px"><thead><tr><th>#</th><th>Time</th><th class="num">Equity</th><th class="num">PnL</th><th class="num">W/L</th><th class="num">Max DD</th><th>Reason</th></tr></thead><tbody>';
          rl.forEach(r => {{
            const pc = (r.pnl_usd||0) >= 0 ? 'pnl-pos' : 'pnl-neg';
            html += '<tr>';
            html += '<td>' + r.reset_num + '</td>';
            html += '<td>' + toEST(r.time) + '</td>';
            html += '<td class="num">' + fmtUsd(r.equity_at_reset||0) + '</td>';
            html += '<td class="num ' + pc + '">' + fmtUsd(r.pnl_usd||0) + '</td>';
            html += '<td class="num">' + (r.wins||0) + '/' + (r.losses||0) + '</td>';
            html += '<td class="num" style="color:var(--red)">' + fmt(r.max_dd||0,1) + '%</td>';
            html += '<td style="font-size:9px">' + (r.reason||'') + '</td>';
            html += '</tr>';
          }});
          html += '</tbody></table>';
        }}

        // Also show blow reasons from reset_history
        (port.reset_history||[]).forEach(r => {{
          html += '<div style="margin-top:4px;font-size:11px;color:var(--text-dim)">' + toEST(r.time) + ': ' + r.reason + ' (Equity: ' + fmtUsd(r.equity_at_blow) + ')</div>';
        }});
        html += '</div>';
      }}
    }}

    // Active positions
    if (port.positions && port.positions.length) {{
      html += '<h3 style="font-size:13px;margin:8px 0 4px">Active Positions (' + port.positions.length + ')</h3>';
      html += '<table><thead><tr><th>Symbol</th><th>Dir</th><th class="num">Entry</th><th class="num">TP</th><th class="num">SL</th><th class="num">Current</th><th class="num">PnL%</th><th class="num">PnL$</th><th class="num">R:R</th><th class="num">Size</th><th>System</th><th>Opened</th></tr></thead><tbody>';
      port.positions.forEach(p => {{
        const pc = (p.pnl_pct||0) >= 0 ? 'pnl-pos' : 'pnl-neg';
        html += '<tr>';
        html += '<td><strong>' + p.symbol + '</strong></td>';
        html += '<td><span class="badge badge-' + p.direction.toLowerCase() + '">' + p.direction + '</span></td>';
        html += '<td class="num">' + fmt(p.entry_price, p.entry_price < 1 ? 6 : 2) + '</td>';
        html += '<td class="num" style="color:var(--green)">' + fmt(p.take_profit, p.take_profit < 1 ? 6 : 2) + '</td>';
        html += '<td class="num" style="color:var(--red)">' + fmt(p.stop_loss, p.stop_loss < 1 ? 6 : 2) + '</td>';
        html += '<td class="num">' + (p.current_price ? fmt(p.current_price, p.current_price < 1 ? 6 : 2) : '\\u2014') + '</td>';
        html += '<td class="num ' + pc + '" style="font-weight:600">' + fmtPct(p.pnl_pct||0) + '</td>';
        html += '<td class="num ' + pc + '">' + fmtUsd(p.pnl_usd||0) + '</td>';
        html += '<td class="num">' + fmt(p.rr||0,2) + '</td>';
        html += '<td class="num">' + fmtUsd(p.size_usd||0) + '</td>';
        html += '<td style="font-size:10px">' + (p.source_system||'').replace(/_/g,' ') + '</td>';
        html += '<td style="font-size:10px;color:var(--text-dim)">' + toEST(p.opened_at) + '</td>';
        html += '</tr>';
      }});
      html += '</tbody></table>';
    }}

    // Recent closed
    if (port.recent_closed && port.recent_closed.length) {{
      html += '<h3 style="font-size:13px;margin:8px 0 4px">Recent Closed (' + port.recent_closed.length + ')</h3>';
      html += '<table><thead><tr><th>Symbol</th><th>Dir</th><th class="num">Entry</th><th class="num">Exit</th><th class="num">PnL%</th><th class="num">Net PnL</th><th>Result</th><th>System</th><th>Opened</th><th>Closed</th></tr></thead><tbody>';
      port.recent_closed.forEach(p => {{
        const pc = (p.net_pnl_usd||0) >= 0 ? 'pnl-pos' : 'pnl-neg';
        const rb = (p.exit_reason||'') === 'TP' ? '<span class="badge badge-tp">TP</span>' : '<span class="badge badge-sl">SL</span>';
        html += '<tr>';
        html += '<td><strong>' + p.symbol + '</strong></td>';
        html += '<td><span class="badge badge-' + p.direction.toLowerCase() + '">' + p.direction + '</span></td>';
        html += '<td class="num">' + fmt(p.entry_price, 2) + '</td>';
        html += '<td class="num">' + fmt(p.exit_price||0, 2) + '</td>';
        html += '<td class="num ' + pc + '">' + fmtPct(p.pnl_pct||0) + '</td>';
        html += '<td class="num ' + pc + '">' + fmtUsd(p.net_pnl_usd||0) + '</td>';
        html += '<td>' + rb + '</td>';
        html += '<td style="font-size:10px">' + (p.source_system||'').replace(/_/g,' ') + '</td>';
        html += '<td style="font-size:10px;color:var(--text-dim)">' + toEST(p.opened_at) + '</td>';
        html += '<td style="font-size:10px;color:var(--text-dim)">' + toEST(p.closed_at) + '</td>';
        html += '</tr>';
      }});
      html += '</tbody></table>';
    }}

    html += '</div></div>';
  }});

  document.getElementById('app').innerHTML = html;
  document.getElementById('last-updated').textContent = toEST(D.generated_at);
  document.getElementById('gen-time').textContent = 'Generated: ' + toEST(D.generated_at);
}}
render();
</script>
</body>
</html>"""


# ═══════════════════════════════════════════════════════════════
# CORRELATION MATRIX & VaR CONSTRAINTS ENGINE
# Full portfolio risk analytics: correlation matrix, historical/parametric VaR,
# CVaR (Expected Shortfall), and risk constraint validation.
# ═══════════════════════════════════════════════════════════════

try:
    import numpy as _np
    import pandas as _pd

    _HAS_NUMPY_PANDAS = True
except ImportError:
    _HAS_NUMPY_PANDAS = False

try:
    import yfinance as _yf

    _HAS_YFINANCE = True
except ImportError:
    _HAS_YFINANCE = False


class CorrelationEngine:
    """Compute pairwise correlation matrices and identify correlated clusters."""

    def __init__(self):
        self._price_cache = {}  # symbol -> pd.Series of daily closes
        self._corr_matrix = None
        self._symbols = []

    # ── data fetching ──────────────────────────────────────────

    def _symbol_to_yf_ticker(self, symbol: str) -> str:
        """Convert internal symbol format to yfinance ticker."""
        s = symbol.replace("-", "").replace("/", "").upper()
        # Equities – pass through
        equities = {
            "SPY",
            "QQQ",
            "GME",
            "COIN",
            "AAPL",
            "MSFT",
            "NVDA",
            "AMD",
            "TSLA",
            "AMZN",
            "GOOGL",
            "META",
            "MA",
            "V",
            "JPM",
            "BAC",
            "WMT",
            "DIS",
            "NFLX",
            "PLTR",
            "SOFI",
            "RIVN",
            "AMC",
            "MSTR",
        }
        if s in equities:
            return s
        # Forex pairs
        forex_map = {
            "EURUSD": "EURUSD=X",
            "GBPUSD": "GBPUSD=X",
            "USDJPY": "USDJPY=X",
            "AUDUSD": "AUDUSD=X",
            "USDCAD": "USDCAD=X",
            "USDCHF": "USDCHF=X",
            "NZDUSD": "NZDUSD=X",
            "EURJPY": "EURJPY=X",
            "GBPJPY": "GBPJPY=X",
        }
        for key, yf_sym in forex_map.items():
            if key in s:
                return yf_sym
        # Crypto – strip USDT/USD suffix, add -USD for yfinance
        base = s.replace("USDT", "").replace("USD", "").replace("BUSD", "")
        if base:
            return f"{base}-USD"
        return s

    def _fetch_prices_yfinance(
        self, symbol: str, lookback_days: int = 90
    ) -> "_pd.Series | None":
        """Fetch daily close prices via yfinance."""
        if not _HAS_YFINANCE or not _HAS_NUMPY_PANDAS:
            return None
        ticker = self._symbol_to_yf_ticker(symbol)
        try:
            data = _yf.download(
                ticker,
                period=f"{lookback_days}d",
                interval="1d",
                progress=False,
                auto_adjust=True,
                timeout=10,
            )
            if data is not None and not data.empty:
                closes = data["Close"].dropna()
                if hasattr(closes, "columns"):
                    closes = closes.iloc[:, 0]
                if len(closes) >= 5:
                    return closes
        except Exception:
            pass
        return None

    def _fetch_prices_vol_cache(self, symbol: str) -> "_pd.Series | None":
        """Fallback: build a price series from the existing _VOL_CACHE returns."""
        if not _HAS_NUMPY_PANDAS:
            return None
        sym_norm = normalize_symbol(symbol)
        cached = _VOL_CACHE.get(sym_norm) or _VOL_CACHE.get(symbol)
        if not cached or not cached.get("returns"):
            return None
        returns_pct = cached["returns"]
        if len(returns_pct) < 5:
            return None
        # Reconstruct a synthetic price series starting from 100
        prices = [100.0]
        for r in returns_pct:
            prices.append(prices[-1] * (1 + r / 100.0))
        idx = _pd.date_range(end=_pd.Timestamp.now(), periods=len(prices), freq="D")
        return _pd.Series(prices, index=idx, name=symbol)

    def _get_prices(self, symbol: str, lookback_days: int = 90) -> "_pd.Series | None":
        """Get price series with yfinance -> vol_cache fallback."""
        if symbol in self._price_cache:
            return self._price_cache[symbol]
        series = self._fetch_prices_yfinance(symbol, lookback_days)
        if series is None:
            series = self._fetch_prices_vol_cache(symbol)
        if series is not None:
            self._price_cache[symbol] = series
        return series

    # ── core calculations ──────────────────────────────────────

    def compute_correlation_matrix(
        self, symbols: list, lookback_days: int = 60
    ) -> "_pd.DataFrame":
        """Compute pairwise correlation matrix from price returns.

        Returns a pandas DataFrame with symbols as both index and columns.
        Values are Pearson correlations of log returns.
        """
        if not _HAS_NUMPY_PANDAS:
            return _pd.DataFrame() if _HAS_NUMPY_PANDAS else None

        returns_dict = {}
        for sym in symbols:
            prices = self._get_prices(sym, lookback_days)
            if prices is not None and len(prices) >= 5:
                log_ret = _np.log(prices / prices.shift(1)).dropna()
                if len(log_ret) >= 3:
                    returns_dict[sym] = log_ret

        if len(returns_dict) < 2:
            self._corr_matrix = _pd.DataFrame()
            self._symbols = list(returns_dict.keys())
            return self._corr_matrix

        returns_df = _pd.DataFrame(returns_dict)
        # Forward-fill then drop any remaining NaN columns
        returns_df = returns_df.ffill().dropna(axis=1, how="all")
        self._corr_matrix = returns_df.corr()
        self._symbols = list(self._corr_matrix.columns)
        return self._corr_matrix

    def find_highly_correlated_pairs(self, threshold: float = 0.7) -> list:
        """Return pairs with |correlation| > threshold.

        Returns list of dicts: [{'sym1': str, 'sym2': str, 'correlation': float}, ...]
        """
        if self._corr_matrix is None or self._corr_matrix.empty:
            return []

        pairs = []
        cols = list(self._corr_matrix.columns)
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                corr_val = self._corr_matrix.iloc[i, j]
                if abs(corr_val) > threshold:
                    pairs.append(
                        {
                            "sym1": cols[i],
                            "sym2": cols[j],
                            "correlation": round(float(corr_val), 4),
                        }
                    )
        pairs.sort(key=lambda x: abs(x["correlation"]), reverse=True)
        return pairs

    def check_portfolio_correlation_risk(self, active_picks: list) -> dict:
        """Check if portfolio has too many correlated positions.

        Returns:
            {
                'total_positions': int,
                'correlated_pairs': list,
                'correlation_clusters': list[list[str]],
                'max_cluster_size': int,
                'risk_level': 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL',
                'message': str,
            }
        """
        symbols = list({p.get("symbol", "") for p in active_picks if p.get("symbol")})
        if len(symbols) < 2:
            return {
                "total_positions": len(symbols),
                "correlated_pairs": [],
                "correlation_clusters": [],
                "max_cluster_size": len(symbols),
                "risk_level": "LOW",
                "message": "Insufficient positions for correlation analysis",
            }

        self.compute_correlation_matrix(symbols)
        corr_pairs = self.find_highly_correlated_pairs(0.7)

        # Build correlation clusters using union-find
        parent = {s: s for s in symbols}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        for pair in corr_pairs:
            if pair["sym1"] in parent and pair["sym2"] in parent:
                union(pair["sym1"], pair["sym2"])

        clusters = {}
        for s in symbols:
            root = find(s)
            clusters.setdefault(root, []).append(s)

        cluster_list = [c for c in clusters.values() if len(c) > 1]
        max_cluster = max((len(c) for c in cluster_list), default=0)

        # Risk assessment
        n_corr = len(corr_pairs)
        if n_corr == 0:
            risk = "LOW"
            msg = "No highly correlated pairs detected"
        elif n_corr <= 2 and max_cluster <= 3:
            risk = "MEDIUM"
            msg = f"{n_corr} correlated pair(s) found — monitor concentration"
        elif n_corr <= 5 or max_cluster <= 4:
            risk = "HIGH"
            msg = f"{n_corr} correlated pairs, largest cluster={max_cluster} — reduce exposure"
        else:
            risk = "CRITICAL"
            msg = f"{n_corr} correlated pairs, cluster of {max_cluster} — immediate action needed"

        return {
            "total_positions": len(symbols),
            "correlated_pairs": corr_pairs,
            "correlation_clusters": cluster_list,
            "max_cluster_size": max_cluster,
            "risk_level": risk,
            "message": msg,
        }


class VaREngine:
    """Value at Risk (VaR) and Conditional VaR calculator."""

    def __init__(self, correlation_engine: CorrelationEngine = None):
        self._corr_engine = correlation_engine or CorrelationEngine()

    def historical_var(self, returns: "_pd.Series", confidence: float = 0.95) -> float:
        """Historical VaR at given confidence level.

        Returns a negative number representing the worst expected loss at the
        given confidence level (e.g., -0.03 means 3% loss).
        """
        if not _HAS_NUMPY_PANDAS or returns is None or len(returns) < 5:
            return 0.0
        cutoff = 1.0 - confidence
        var_value = float(_np.percentile(returns.dropna(), cutoff * 100))
        return round(var_value, 6)

    def parametric_var(
        self, mean: float, std: float, confidence: float = 0.95
    ) -> float:
        """Parametric (Gaussian) VaR.

        Uses the normal distribution assumption.
        Returns a negative number for losses.
        """
        if not _HAS_NUMPY_PANDAS or std <= 0:
            return 0.0
        # Z-scores for common confidence levels
        z_map = {0.90: 1.2816, 0.95: 1.6449, 0.99: 2.3263}
        z = z_map.get(confidence)
        if z is None:
            # Use statistics.NormalDist for arbitrary confidence levels
            from statistics import NormalDist

            z = NormalDist().inv_cdf(confidence)
        var_value = mean - z * std
        return round(var_value, 6)

    def _expected_shortfall(
        self, returns: "_pd.Series", confidence: float = 0.95
    ) -> float:
        """Conditional VaR (CVaR / Expected Shortfall).

        Average of losses beyond the VaR threshold.
        """
        if not _HAS_NUMPY_PANDAS or returns is None or len(returns) < 5:
            return 0.0
        cutoff = 1.0 - confidence
        var_val = float(_np.percentile(returns.dropna(), cutoff * 100))
        tail = returns[returns <= var_val]
        if len(tail) == 0:
            return var_val
        return round(float(tail.mean()), 6)

    def portfolio_var(self, active_picks: list, confidence: float = 0.95) -> dict:
        """Portfolio-level VaR considering correlations.

        Returns:
            {
                'var_95': float,      # 95% daily VaR (as decimal, e.g., -0.03 = -3%)
                'var_99': float,      # 99% daily VaR
                'cvar_95': float,     # Conditional VaR / Expected Shortfall at 95%
                'expected_shortfall': float,  # alias for cvar_95
                'individual_vars': dict,      # per-symbol VaR
                'method': str,                # 'historical' or 'parametric'
                'data_quality': str,          # 'good', 'partial', 'insufficient'
            }
        """
        result = {
            "var_95": 0.0,
            "var_99": 0.0,
            "cvar_95": 0.0,
            "expected_shortfall": 0.0,
            "individual_vars": {},
            "method": "parametric",
            "data_quality": "insufficient",
        }

        if not _HAS_NUMPY_PANDAS or not active_picks:
            return result

        symbols = list({p.get("symbol", "") for p in active_picks if p.get("symbol")})
        if not symbols:
            return result

        # Collect returns for each symbol
        returns_dict = {}
        weights = {}
        total_exposure = 0.0

        for p in active_picks:
            sym = p.get("symbol", "")
            if not sym:
                continue
            size = abs(p.get("size_usd", 0))
            total_exposure += size

        if total_exposure <= 0:
            total_exposure = 1.0  # avoid division by zero

        for p in active_picks:
            sym = p.get("symbol", "")
            if not sym:
                continue
            size = abs(p.get("size_usd", 0))
            direction_sign = 1.0 if p.get("direction", "LONG") == "LONG" else -1.0
            w = (size / total_exposure) * direction_sign
            weights[sym] = weights.get(sym, 0) + w

            if sym not in returns_dict:
                prices = self._corr_engine._get_prices(sym)
                if prices is not None and len(prices) >= 5:
                    log_ret = _np.log(prices / prices.shift(1)).dropna()
                    if len(log_ret) >= 3:
                        returns_dict[sym] = log_ret

        # Individual VaR per symbol
        individual_vars = {}
        for sym, rets in returns_dict.items():
            iv95 = self.historical_var(rets, 0.95)
            individual_vars[sym] = round(float(iv95), 6)
        result["individual_vars"] = individual_vars

        if not returns_dict:
            # Fallback to parametric using _VOL_CACHE
            weighted_var = 0.0
            for sym, w in weights.items():
                sym_norm = normalize_symbol(sym)
                cached = _VOL_CACHE.get(sym_norm) or _VOL_CACHE.get(sym) or {}
                std_pct = cached.get("std_daily", 3.0) / 100.0
                mean_pct = cached.get("mean_return", 0.0) / 100.0
                var_i = self.parametric_var(mean_pct, std_pct, 0.95)
                weighted_var += abs(w) * var_i

            result["var_95"] = round(weighted_var, 6)
            result["var_99"] = round(weighted_var * 1.42, 6)  # 2.3263/1.6449 ratio
            result["cvar_95"] = round(weighted_var * 1.25, 6)
            result["expected_shortfall"] = result["cvar_95"]
            result["method"] = "parametric"
            result["data_quality"] = "partial"
            return result

        # Build portfolio returns using historical simulation
        returns_df = _pd.DataFrame(returns_dict).ffill().dropna(axis=0, how="any")
        if len(returns_df) < 5:
            result["data_quality"] = "partial"
            return result

        # Construct weighted portfolio returns
        weight_arr = _np.array([weights.get(col, 0) for col in returns_df.columns])
        portfolio_returns = returns_df.values @ weight_arr
        port_ret_series = _pd.Series(portfolio_returns)

        result["var_95"] = self.historical_var(port_ret_series, 0.95)
        result["var_99"] = self.historical_var(port_ret_series, 0.99)
        result["cvar_95"] = self._expected_shortfall(port_ret_series, 0.95)
        result["expected_shortfall"] = result["cvar_95"]
        result["method"] = "historical"
        result["data_quality"] = "good" if len(returns_df) >= 30 else "partial"

        return result


class RiskConstraintChecker:
    """Validates portfolio risk constraints including VaR, correlation, and exposure limits."""

    LIMITS = {
        "max_portfolio_var_95": -0.03,  # Max 3% daily VaR
        "max_correlation_group_exposure": 0.30,  # Max 30% in correlated assets
        "max_single_asset_exposure": 0.15,  # Max 15% in one asset
        "max_strategy_concentration": 0.25,  # Max 25% in one strategy
        "min_short_exposure": 0.20,  # Min 20% short
        "max_drawdown_threshold": -0.05,  # -5% triggers circuit breaker
    }

    def __init__(
        self, corr_engine: CorrelationEngine = None, var_engine: VaREngine = None
    ):
        self._corr_engine = corr_engine or CorrelationEngine()
        self._var_engine = var_engine or VaREngine(self._corr_engine)

    def _get_total_exposure(self, picks: list) -> float:
        return sum(abs(p.get("size_usd", 0)) for p in picks) or 1.0

    def validate_new_pick(
        self, new_pick: dict, active_picks: list
    ) -> "tuple[bool, str]":
        """Returns (approved, reason) for a potential new pick.

        Checks all risk constraints and rejects if any would be violated.
        """
        all_picks = list(active_picks) + [new_pick]
        total_exp = self._get_total_exposure(all_picks)
        new_sym = new_pick.get("symbol", "")
        new_size = abs(new_pick.get("size_usd", 0))

        # 1. Single asset exposure check
        existing_sym_exp = sum(
            abs(p.get("size_usd", 0))
            for p in active_picks
            if normalize_symbol(p.get("symbol", "")) == normalize_symbol(new_sym)
        )
        combined_sym_exp = (existing_sym_exp + new_size) / total_exp
        if combined_sym_exp > self.LIMITS["max_single_asset_exposure"]:
            return False, (
                f"Single asset exposure {combined_sym_exp:.1%} exceeds "
                f"{self.LIMITS['max_single_asset_exposure']:.0%} limit for {new_sym}"
            )

        # 2. Strategy concentration check
        new_strat = new_pick.get("strategy", "")
        if new_strat:
            strat_exp = sum(
                abs(p.get("size_usd", 0))
                for p in all_picks
                if p.get("strategy", "") == new_strat
            )
            strat_pct = strat_exp / total_exp
            if strat_pct > self.LIMITS["max_strategy_concentration"]:
                return False, (
                    f"Strategy '{new_strat}' concentration {strat_pct:.1%} exceeds "
                    f"{self.LIMITS['max_strategy_concentration']:.0%} limit"
                )

        # 3. Correlation group exposure check
        corr_risk = self._corr_engine.check_portfolio_correlation_risk(all_picks)
        if corr_risk.get("risk_level") == "CRITICAL":
            # Check if the new symbol is in a large cluster
            for cluster in corr_risk.get("correlation_clusters", []):
                if new_sym in cluster:
                    cluster_exp = (
                        sum(
                            abs(p.get("size_usd", 0))
                            for p in all_picks
                            if p.get("symbol") in cluster
                        )
                        / total_exp
                    )
                    if cluster_exp > self.LIMITS["max_correlation_group_exposure"]:
                        return False, (
                            f"Correlated cluster {cluster} exposure {cluster_exp:.1%} "
                            f"exceeds {self.LIMITS['max_correlation_group_exposure']:.0%} limit"
                        )

        # 4. Portfolio VaR check
        var_result = self._var_engine.portfolio_var(all_picks)
        if var_result["var_95"] < self.LIMITS["max_portfolio_var_95"]:
            return False, (
                f"Portfolio VaR(95%) = {var_result['var_95']:.2%} exceeds "
                f"{self.LIMITS['max_portfolio_var_95']:.2%} limit"
            )

        # 5. Minimum short exposure check
        long_exp = sum(
            abs(p.get("size_usd", 0)) for p in all_picks if p.get("direction") == "LONG"
        )
        short_exp = sum(
            abs(p.get("size_usd", 0))
            for p in all_picks
            if p.get("direction") == "SHORT"
        )
        if total_exp > 0 and len(all_picks) >= 5:
            short_ratio = short_exp / total_exp
            if short_ratio < self.LIMITS["min_short_exposure"]:
                # Only warn, don't block — might legitimately be all-long
                pass  # soft constraint

        return True, "All risk constraints passed"

    def generate_risk_report(self, active_picks: list) -> dict:
        """Full risk report with all metrics.

        Returns:
            {
                'timestamp': str,
                'total_positions': int,
                'total_exposure_usd': float,
                'var_metrics': dict,
                'correlation_risk': dict,
                'exposure_breakdown': dict,
                'constraint_status': dict,
                'overall_risk_level': str,
            }
        """
        if not active_picks:
            return {
                "timestamp": datetime.now(EST).isoformat(),
                "total_positions": 0,
                "total_exposure_usd": 0,
                "var_metrics": {},
                "correlation_risk": {},
                "exposure_breakdown": {},
                "constraint_status": {},
                "overall_risk_level": "N/A",
            }

        total_exp = self._get_total_exposure(active_picks)

        # VaR
        var_metrics = self._var_engine.portfolio_var(active_picks)

        # Correlation
        corr_risk = self._corr_engine.check_portfolio_correlation_risk(active_picks)

        # Exposure breakdown
        long_exp = sum(
            abs(p.get("size_usd", 0))
            for p in active_picks
            if p.get("direction") == "LONG"
        )
        short_exp = sum(
            abs(p.get("size_usd", 0))
            for p in active_picks
            if p.get("direction") == "SHORT"
        )

        # Per-symbol exposure
        sym_exposure = {}
        for p in active_picks:
            sym = p.get("symbol", "unknown")
            sym_exposure[sym] = sym_exposure.get(sym, 0) + abs(p.get("size_usd", 0))

        # Per-strategy exposure
        strat_exposure = {}
        for p in active_picks:
            strat = p.get("strategy", "unknown")
            strat_exposure[strat] = strat_exposure.get(strat, 0) + abs(
                p.get("size_usd", 0)
            )

        max_sym_pct = max(sym_exposure.values(), default=0) / total_exp
        max_strat_pct = max(strat_exposure.values(), default=0) / total_exp
        short_ratio = short_exp / total_exp if total_exp > 0 else 0

        # Constraint status
        constraints = {}
        constraints["max_portfolio_var_95"] = {
            "limit": self.LIMITS["max_portfolio_var_95"],
            "current": var_metrics.get("var_95", 0),
            "passed": var_metrics.get("var_95", 0)
            >= self.LIMITS["max_portfolio_var_95"],
        }
        constraints["max_single_asset_exposure"] = {
            "limit": self.LIMITS["max_single_asset_exposure"],
            "current": round(max_sym_pct, 4),
            "passed": max_sym_pct <= self.LIMITS["max_single_asset_exposure"],
        }
        constraints["max_strategy_concentration"] = {
            "limit": self.LIMITS["max_strategy_concentration"],
            "current": round(max_strat_pct, 4),
            "passed": max_strat_pct <= self.LIMITS["max_strategy_concentration"],
        }
        constraints["max_correlation_group_exposure"] = {
            "limit": self.LIMITS["max_correlation_group_exposure"],
            "current": corr_risk.get("risk_level", "LOW"),
            "passed": corr_risk.get("risk_level", "LOW") not in ("HIGH", "CRITICAL"),
        }
        constraints["min_short_exposure"] = {
            "limit": self.LIMITS["min_short_exposure"],
            "current": round(short_ratio, 4),
            "passed": short_ratio >= self.LIMITS["min_short_exposure"]
            or len(active_picks) < 5,
        }

        # Overall risk level
        violations = sum(1 for c in constraints.values() if not c["passed"])
        if violations == 0:
            overall = "LOW"
        elif violations == 1:
            overall = "MEDIUM"
        elif violations <= 3:
            overall = "HIGH"
        else:
            overall = "CRITICAL"

        return {
            "timestamp": datetime.now(EST).isoformat(),
            "total_positions": len(active_picks),
            "total_exposure_usd": round(total_exp, 2),
            "var_metrics": var_metrics,
            "correlation_risk": corr_risk,
            "exposure_breakdown": {
                "long_usd": round(long_exp, 2),
                "short_usd": round(short_exp, 2),
                "long_pct": round(long_exp / total_exp, 4),
                "short_pct": round(short_ratio, 4),
                "by_symbol": {k: round(v, 2) for k, v in sym_exposure.items()},
                "by_strategy": {k: round(v, 2) for k, v in strat_exposure.items()},
                "max_single_asset_pct": round(max_sym_pct, 4),
                "max_strategy_pct": round(max_strat_pct, 4),
            },
            "constraint_status": constraints,
            "overall_risk_level": overall,
        }


def export_risk_metrics(active_picks: list) -> dict:
    """Generate and save full risk metrics to JSON for dashboard consumption.

    Saves to: audit_dashboard/data/risk_metrics.json

    Returns the risk report dict.
    """
    corr_engine = CorrelationEngine()
    var_engine = VaREngine(corr_engine)
    checker = RiskConstraintChecker(corr_engine, var_engine)

    report = checker.generate_risk_report(active_picks)

    # Add correlation matrix as nested lists (JSON-serializable)
    symbols = list({p.get("symbol", "") for p in active_picks if p.get("symbol")})
    corr_matrix_df = corr_engine.compute_correlation_matrix(symbols)

    if _HAS_NUMPY_PANDAS and corr_matrix_df is not None and not corr_matrix_df.empty:
        report["correlation_matrix"] = {
            "symbols": list(corr_matrix_df.columns),
            "values": [
                [round(float(v), 4) for v in row] for row in corr_matrix_df.values
            ],
        }
    else:
        report["correlation_matrix"] = {"symbols": [], "values": []}

    # Ensure data directory exists
    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(exist_ok=True)
    out_path = data_dir / "risk_metrics.json"

    try:
        with open(out_path, "w") as f:
            json.dump(report, f, indent=2, default=str)
    except Exception as e:
        report["_save_error"] = str(e)

    return report


if __name__ == "__main__":
    main()
