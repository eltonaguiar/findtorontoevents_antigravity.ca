#!/usr/bin/env python3
"""
ALPHA_ENGINE -- Auto-Tuner & Performance Validator
====================================================
Runs after each scan cycle to:
  1. Validate strategy performance against benchmarks
  2. Disable underperforming strategies (probation -> elimination)
  3. Boost high-performers (increase allocation weight)
  4. Auto-train ML model when enough data accumulates
  5. Generate performance report for audit trail

Designed to run autonomously in GitHub Actions.
No human intervention required.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import DATA_DIR
from database import SQLiteStore
from drawdown_tracker import compute_all_drawdowns
from hedge_fund_quality_gate import PORTFOLIO_MAX_DRAWDOWN_PCT
from ml_ranker import MLSignalRanker

# ---------------------------------------------------------------------------
# Tuning thresholds
# ---------------------------------------------------------------------------

TUNING_CONFIG = {
    # Minimum closed picks before a strategy is evaluated
    "min_picks_for_eval": 5,
    # Strategy gets flagged if win rate below this after min_picks
    "warn_win_rate": 0.42,
    # Strategy gets disabled if win rate below this after min_picks_for_wr_check
    # Tightened Feb 28 2026: was 0.35 after 8 picks -- now 0.40 after 5 picks
    "disable_win_rate": 0.40,
    # Minimum picks before win-rate based disable kicks in (was 8)
    "min_picks_for_wr_check": 5,
    # Strategy gets disabled if Sharpe below this (tightened: was -0.5)
    # Per deep research: any negative Sharpe strategy is a portfolio drag
    "disable_sharpe": 0.0,
    # Strategy gets disabled if rolling 20-trade Sharpe below this
    "disable_rolling_sharpe": 0.8,
    # Strategy gets disabled if max drawdown exceeds this (was -0.30)
    "disable_max_dd": -0.25,
    # Maximum dollar loss per strategy before auto-kill ($500 cap)
    "max_strategy_loss_dollar": -500,
    # Strategy gets BOOSTED if win rate above this + Sharpe > 1
    "boost_win_rate": 0.55,
    "boost_sharpe": 1.0,
    # ML auto-train threshold
    "ml_train_threshold": 50,
    # ML re-train interval (re-train if last train was N+ picks ago)
    "ml_retrain_interval": 25,
}

# LOW CONFIDENCE STRATEGIES — policy: no kills, always mutate/invert first
# These strategies showed poor forward-test results. Per "No-Kill" policy (Mar 2026):
#   NEVER hard-block a strategy. Instead: (1) create INVERSE signal variant,
#   (2) DNA mutation (vary parameters), (3) symbol rotation.
# Strategies below get a 0.4x confidence multiplier until inverse is validated.
# Updated Feb 26 2026: added 6 more 0%-WR strategies (0% on ALL directions, non-ML)
# Updated Feb 28 2026: added 7 more 0%-WR strategies from production readiness audit
# Updated Mar 24 2026: renamed from HARD_DISABLED_STRATEGIES — no longer hard-blocked.
LOW_CONFIDENCE_STRATEGIES = {
    # --- Original disabled (Feb 26 2026) ---
    "double_top_bottom_detector",        # 1/4=25% WR, -$1134 (massive losses on SOL/ETH)
    "fourier_cycle_detector",            # 0/6=0% WR, -$935, ML but total failure
    "m2_liquidity_lag",                  # 2/9=22% WR, -$879, -4.9% avg
    "price_touch_recurrence",            # 0/5=0% WR, -$874, 100% SL_HIT
    "smart_money_fvg",                   # 0/9=0% WR, -$928, -5.2% avg
    "halloween_effect",                  # 0/5=0% WR, -$943, -9.4% avg (seasonal, irrelevant)
    "cross_sectional_momentum",          # 0/3=0% WR, -$612, -10.2% avg
    "exchange_netflow_reversal",         # 0/3=0% WR, -$466, -7.8% avg
    "momentum_mean_rev_blend",           # 0/3=0% WR, -$522, -8.7% avg (contradictory logic)
    "community_ict_fvg_selective",       # 1/8=12.5% WR, -$304, -1.9% avg (ICT unvalidated)
    "monthly_seasonality",               # 1/8=12.5% WR, -$942, -5.9% avg (calendar useless)
    # --- Added Feb 28 2026: 0% WR strategies, 100% SL_HIT, clearly broken ---
    "spike_volume_explosion",            # 0/2=0% WR, -$342, -8.5% avg, 100% SL_HIT
    "community_bb_squeeze_breakout_crypto",  # 0/2=0% WR, -$472, -11.8% avg, 100% SL_HIT
    "community_momentum_breakout_volume_crypto",  # 0/2=0% WR, -$272, -6.8% avg, 100% SL_HIT
    "spike_squeeze_breakout",            # 0/2=0% WR, -$268, -6.7% avg, 100% SL_HIT
    "sector_momentum_7d",                # 0/2=0% WR, -$329, -8.2% avg, 100% SL_HIT
    "break_of_structure",                # 0/2=0% WR, -$273, -6.8% avg, 100% SL_HIT
    "altcoin_season_rotation",           # 0/4=0% WR, -$654, -8.2% avg, 100% SL_HIT
    "btc_dominance_reversal",            # 0/2=0% WR, -$389, -9.7% avg, 100% SL_HIT
    "price_level_magnetism",             # 89% WR but NEGATIVE PnL (-$66), fake wins (tiny TP, huge SL)
    # --- Phase 1 cull: no statistical proof (p>0.05 or insufficient trades) ---
    "bb_squeeze_expansion",              # No statistical proof (p>0.05 or insufficient trades)
    "btc_dominance_rotation",            # No statistical proof
    "dynamic_momentum_scaling",          # No statistical proof
    "ema_rsi_momentum",                  # No statistical proof
    "halving_cycle_position",            # No statistical proof
    "rsi_divergence",                    # No statistical proof
    "triple_ema_trend",                  # No statistical proof
    "zscore_reversion",                  # No statistical proof
    # --- User linter additions (Feb 28 2026) ---
    "coingecko_trending_volume",         # 0/1=0% WR, -$258
    "multi_touch_level_strength",        # 0/1=0% WR, -$118
    "support_resistance_bounce",         # 0/1=0% WR, -$48
    # --- Added Mar 3 2026: confirmed net-negative in forward testing ---
    "variance_ratio_momentum",           # 3/9=33% WR across BTC/ETH/SOL -- below elimination threshold
    # --- Added Mar 7 2026: 0% WR confirmed in audit DB (1+ closed trades, all SL_HIT) ---
    "narrative_rotation",                # 0/1=0% WR, -0.11% PnL -- speculative narrative thesis
    # --- Added Mar 16 2026: 0% WR confirmed in 273-trade PnL audit ---
    "seasonal_factor_rotation",          # 0/11=0% WR, -1.20% avg, 100% SL_HIT -- fundamentally broken
    "community_london_breakout_v2_forex",  # 0/6=0% WR, -0.93% avg, MFE near zero -- anti-predictive
    # --- Added Mar 16 2026: frozen ml_score bug + 0% WR on symbol-by-symbol audit ---
    "ml_enhanced_BTCUSDT_15m_D_ensemble_stack",  # 0/10=0% WR, shorted BTC 10x with frozen ml_score 0.6794
    "ml_enhanced_ADAUSDT_15m_D_ensemble_stack",  # 0/10=0% WR, same frozen ensemble bug
    "ml_enhanced_ETHUSDT_1h_D_ensemble_stack",   # 0/3=0% WR, shorted ETH into bull market
    "ml_enhanced_ETHUSDT_4h_D_ensemble_stack",   # 0/2=0% WR, contradicted own lightgbm model
    "hurst_regime_momentum",             # 0/1=0% WR, -0.10% PnL -- Hurst momentum variant broken
    "market_structure_break",            # 0/1=0% WR, -0.05% PnL -- price action false breakouts
    "crypto_breakout_volume",            # 0/1=0% WR, -0.05% PnL -- volume breakout unreliable
    # tsmom_28d: reinstated (1/1=100% WR, +$120, TP_HIT per strategy_performance.json)
    "altcoin_dip_amplifier",             # 0/1=0% WR, -0.02% PnL -- catching falling knives
    # --- Added Mar 23 2026: 20% WR on 104 picks = confirmed net-negative ---
    "winner_pattern_precursor",          # 20% WR on 104 picks -- consistently wrong
    # inverse_winner_pattern_precursor: REMOVED (2026-03-26) — inverse strategies are the
    # profitable flip of structural losers; killing them defeats the purpose.
    # --- Added Mar 16 2026: 0% WR with 3+ trades, mutate-before-kill applied ---
    # order_book_imbalance: inverted via super_inverse_seasonal_obi (super_strategies.py)
    "order_book_imbalance",              # 0/4=0% WR, 100% SL_HIT -- inverted in super_inverse_seasonal_obi
    # --- Added Mar 17 2026: root cause analysis -- 6 highest-impact fixes ---
    "adaptive_vr_confluence",            # 1W/5L, 17% WR -- consistently wrong direction
    "forex_logistic_direction",          # 0W, 100% SL rate -- anti-predictive model
    # --- Added Mar 18 2026: system-level losers from 8,457 closed picks audit ---
    "rapid_fire",                        # 152 trades, 25% WR, PF 0.34, -429% PnL -- system banned
    "stocks_competition",                # 174 trades, 26.4% WR -- system banned
    "mercury2_fast",                     # 15 trades, 25% WR, PF 0.02 -- system banned
    # --- March 2026: forex strategies RE-ENABLED after fixing TP/SL parameters ---
    # Root cause: crypto-scale TP (2.5-3.0x ATR) was unreachable on forex.
    # Fixed to 1.2x ATR TP, 1.0x ATR SL, 0.8%/0.5% hard caps.
    # Keep community_london_breakout_v2_forex disabled (needs intraday data).
    # "community_london_breakout_v2_forex" is already in the list above (Mar 16).
    # --- Added Mar 24 2026: 0% WR on 5+ closed trades ---
    # yahoo_analyst_consensus: MOVED TO PERMANENTLY_KILLED (0/29=0% WR)
    # --- Added Mar 24 2026: catastrophic loss sizing despite ok WR ---
    "momentum_catcher",                 # 3/7=43% WR but -131% PnL -- wins tiny, losses massive
    # --- Added Mar 25 2026: losing copy trader strategies (drift analysis) ---
    # copy_hl_NMTD_25M KEPT (81.2% WR — our only reliable copy trader)
    "binance_smart_money",              # 45.8% WR, -0.21% PnL — net loser, deprioritize
    "hl_funding_fade",                  # 36.4% WR — consistently wrong on funding rate reversals
    "hl_momentum_continuation",         # 20.0% WR — worst copy strategy, rarely right
    "hl_mean_reversion",                # 50% WR on 2 trades — insufficient data, demote until proven
    # --- Added Mar 25 2026: Monte Carlo audit — strategies filling portfolio with garbage ---
    # Per Monte Carlo: only ML Enhanced (52.8% WR, 93% MC profitable) has verified edge.
    # Everything below has enough trades to confirm net-negative edge:
    "cta_tsmom_blend",                  # 6/27=22.2% WR, 19 active picks wasting capital — CONFIRMED LOSER
    "futures_bb_mean_reversion",        # 1/5=20% WR — below random
    "futures_ema_stack_momentum",       # 0/4=0% WR — zero wins on 4 trades
    # --- Added 2026-06-05: confirmed net-negative inverse ML strategies (RENDERUSDT) ---
    "inverse_ml_enhanced_RENDERUSDT_4h_D",  # PF 0.12, avg -1.73% — worse than baseline
    "inverse_ml_enhanced_RENDERUSDT_1h_D",  # insufficient data, same broken model family
}

# Backward-compat alias — callers that referenced HARD_DISABLED_STRATEGIES still work.
# These strategies are NO LONGER hard-blocked; they receive a 0.4x confidence multiplier.
HARD_DISABLED_STRATEGIES = LOW_CONFIDENCE_STRATEGIES  # alias only

# ---------------------------------------------------------------------------
# PERMANENTLY_KILLED -- strategies that must NEVER run again, period.
# Unlike LOW_CONFIDENCE (0.4x multiplier), these are fully blocked at every level.
# Added to get_disabled_strategies() output unconditionally.
# Criteria: enough closed trades to be statistically certain of negative edge.
# ---------------------------------------------------------------------------
PERMANENTLY_KILLED: set = {
    "binance_smart_money",              # 45.8% WR, 44% copy volume, illiquid alts, -0.21% PnL
    # --- Added Mar 25 2026: Monte Carlo audit confirmed these destroy portfolio value ---
    "yahoo_analyst_consensus",          # 0/29=0% WR — 12-month analyst TPs unreachable as swing targets
    "cta_tsmom_blend",                  # 6/27=22.2% WR — 19 active picks confirmed net-negative
    "winner_pattern_precursor",         # 2/39=5.1% WR — confirmed catastrophic by Monte Carlo
    # NOTE: inverse_winner_pattern_precursor REMOVED from kill list (2026-03-26).
    # Inverse strategies are the PROFITABLE flip of structural losers -- killing the
    # inverse defeats the purpose. The base is killed; the inverse should run.
    "hl_funding_fade",                  # 0/11=0% WR — consistently wrong on funding rate reversals
    # --- Added 2026-04-01: Portfolio optimization kills confirmed by closed-trade audit ---
    "quan_engine_position",             # 0/13=0% WR, 100% SL exits, -$995, TAOUSDT only (MC confirmed overfit)
    "quan_engine_scalp",                # 0% WR zombie — killed 2026-04-02
    "quan_engine_swing",                # 0% WR zombie — killed 2026-04-02
    "futures_ema_stack_momentum",       # 0/4=0% WR, 7 active zombie picks — killed 2026-04-02
    # --- Added 2026-04-02: Rapid Fire now_picks.json leak (183/500 picks = 36.6% were banned) ---
    "macd_crossover",                   # 25-31% WR on LONG/SHORT, confirmed loser — 139 leaked picks
    "rsi_overbought",                   # 29% WR SHORT-only branch of rsi_bounce, -17.1% PnL — 44 leaked picks
    "st_rsi_momentum_confluence",       # 10% WR (10W/95L), -296% PnL — killed per PEER_INTEL 2026-04-02
}

# Pattern-based disables: strategies matching these patterns are auto-killed.
# Added Mar 17 2026: 15m_D_ensemble_stack collectively lost -121% while
# 1d models gained +401%. Keep *_15m_B_lightgbm (BNBUSDT 86% WR).
HARD_DISABLED_PATTERNS = [
    "_15m_D_ensemble_stack",   # frozen ml_score bug, 0% WR across all symbols
    "_15m_B_lightgbm",         # curve-fit: BNBUSDT 94% WR but PF=99.99, only 18 trades
]

# March 2026: forex re-enabled after fixing crypto-scale TP/SL targets.
# Root cause of 0% WR was TP at 2.5-3.0x ATR (unreachable on 0.3-0.8% daily forex moves).
# Fixed to 1.2x ATR TP, 1.0x ATR SL, with 0.8%/0.5% hard percentage caps.
HARD_DISABLED_CATEGORIES = set()  # was {"forex"} -- re-enabled with proper parameters


def _load_dynamic_kill_list() -> set:
    """Load auto-kill list from strategy_priority.py's kill list JSON."""
    kill_path = DATA_DIR / "strategy_kill_list.json"
    if not kill_path.exists():
        return set()
    try:
        with open(kill_path) as f:
            data = json.load(f)
        return set(data.get("auto_kill_strategies", []))
    except (json.JSONDecodeError, IOError):
        return set()


def is_strategy_disabled(strategy_name: str, category: str = "") -> bool:
    """Check if a strategy is hard-blocked from generating signals.

    Per NO-KILL policy (Mar 2026): strategies in LOW_CONFIDENCE_STRATEGIES are
    NOT blocked here — they receive a 0.4x confidence multiplier elsewhere.
    Only pattern-matched bugs (frozen ml_score) and category blocks are hard-blocked.
    """
    # LOW_CONFIDENCE_STRATEGIES: NOT blocked — low confidence, not dead.
    # Use get_strategy_confidence_multiplier() to apply 0.4x penalty instead.

    # Pattern match only for confirmed frozen-bug variants (e.g., *_15m_D_ensemble_stack)
    for pattern in HARD_DISABLED_PATTERNS:
        if pattern in strategy_name:
            return True
    # Category match
    if category.lower() in HARD_DISABLED_CATEGORIES:
        return True
    # Dynamic auto-kill from strategy_priority.py's kill list JSON.
    # As of Mar 2026, strategy_priority.py enforces MUTATE-BEFORE-KILL:
    # only strategies where mutation was attempted AND also failed appear in this list.
    # Strategies needing mutation go to mutation_candidates.json instead.
    if strategy_name in _load_dynamic_kill_list():
        return True
    return False


def get_strategy_confidence_multiplier(strategy_name: str) -> float:
    """Return confidence multiplier for a strategy.

    LOW_CONFIDENCE_STRATEGIES get 0.4x until an inverse variant is validated.
    Everything else gets 1.0x.
    """
    if strategy_name in LOW_CONFIDENCE_STRATEGIES:
        return 0.4
    return 1.0


# Strategies restricted to specific directions (great one way, terrible the other)
# Based on closed-pick long/short analysis (Feb 26 2026)
# Updated Mar 3 2026: Alpha LONG 25.95% WR / -1.01% expectancy vs SHORT 64.71% WR / +2.12%
# Added more SELL-only restrictions for strategies with negative long-side expectancy
DIRECTION_RESTRICTED_STRATEGIES = {
    # -- Mar 16 2026: SELL-only restrictions REMOVED --
    # System-wide SHORT WR = 20.5% (27/132 closed picks). Forcing strategies
    # to SELL-only was destroying performance. The hard SHORT gate in
    # forward_validator.py now blocks ALL shorts when WR < 40%.
    # These strategies are now unrestricted (BUY signals will flow through):
    #   autocorrelation_exploiter, adaptive_vr_confluence, multi_sigma_reversal,
    #   volume_profile_value_area, community_london_breakout_v2_forex,
    #   hurst_regime_adaptive, connors_rsi2_crypto, vwap_sd_mean_reversion,
    #   community_rsi_extreme_reversal_crypto, rsi_macd_confluence,
    #   funding_rate_carry, oi_funding_squeeze
    #
    # BUY-only: strong LONG record (keep these)
    "fear_greed_extreme_dca": "BUY",       # BUY 3/3=100% +6.0% (contrarian by nature)
}

# ---------------------------------------------------------------------------
# TIER 1: Rigorously Proven (survivor_backtest.py -- 24 symbols, 5yr, 8 checks)
# Passed p<0.05 binomial, multi-asset, regime-robust, OOS profitable
# Updated Feb 28 2026 after full rigorous backtest
# ---------------------------------------------------------------------------
TIER1_PROVEN = {
    # Connors RSI-2: 895 trades, 68.4% WR, Sharpe 1.17, PF 1.53, p=0.000000, 21/24
    "connors_rsi2_crypto": 5.0,
    # VWAP Mean Reversion: 732 trades, 64.3% WR, Sharpe 0.53, PF 1.37, p=0.000000, 20/24
    "vwap_sd_mean_reversion": 5.0,
    # MACD Divergence: 515 trades, 67.8% WR, Sharpe 0.57, PF 1.42, p=0.000000, 16/24
    "rsi_macd_confluence": 4.0,
    # Bollinger Mean Reversion: 361 trades, 60.7% WR, Sharpe 0.72, PF 1.53, p=0.00003, 17/24
    # NOTE: No standalone scanner strategy yet -- boost applies via confluence_engine
    "bollinger_mean_reversion": 4.0,
    # RSI Extreme Reversal: 118 trades, 58.5% WR, Sharpe 0.70, PF 1.68, p=0.040, 15/22
    # Production name: community_rsi_extreme_reversal_crypto (community_strategies.py)
    "community_rsi_extreme_reversal_crypto": 3.0,
}

# TIER 2: Forward-test winners (small sample but profitable in live)
TIER2_FORWARD = {
    "autocorrelation_exploiter": 4.0,   # 83% WR, +$1,459, 6 trades (p=0.051)
    "hurst_regime_adaptive": 4.0,       # 71% WR, +$854, 7 trades
    "volume_profile_value_area": 3.0,   # 80% WR, +$887, 5 trades
    "multi_sigma_reversal": 3.0,        # 100% WR, +$656, 3 trades
    "fear_greed_extreme_dca": 3.0,      # 100% WR, +$360, 3 trades
}

# Combined: TIER1 overwrites TIER2 where overlapping (higher priority)
PROVEN_STRATEGY_BOOST = {**TIER2_FORWARD, **TIER1_PROVEN}

# Persistent state file
TUNER_STATE_PATH = DATA_DIR / "tuner_state.json"


def load_tuner_state() -> dict:
    """Load or initialize tuner state."""
    if TUNER_STATE_PATH.exists():
        with open(TUNER_STATE_PATH) as f:
            return json.load(f)
    return {
        "disabled_strategies": {},
        "boosted_strategies": {},
        "probation_strategies": {},
        "last_ml_train_picks": 0,
        "tuning_log": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def save_tuner_state(state: dict):
    """Save tuner state."""
    state["last_updated"] = datetime.now(timezone.utc).isoformat()
    TUNER_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TUNER_STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def log_event(state: dict, event_type: str, strategy: str, reason: str, data: dict = None):
    """Append an event to the tuning log."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": event_type,
        "strategy": strategy,
        "reason": reason,
    }
    if data:
        entry["data"] = data
    state["tuning_log"].append(entry)
    # Keep last 200 events
    if len(state["tuning_log"]) > 200:
        state["tuning_log"] = state["tuning_log"][-200:]
    print(f"  [{event_type}] {strategy}: {reason}")


# ---------------------------------------------------------------------------
# Core tuning logic
# ---------------------------------------------------------------------------

def evaluate_strategies(db: SQLiteStore, state: dict) -> dict:
    """
    Evaluate all strategies and return actions.
    Returns dict: {strategy: {action, reason, stats}}
    """
    cfg = TUNING_CONFIG
    actions = {}

    # Get all strategies that have closed picks
    from crypto_strategies import CRYPTO_STRATEGIES
    from forex_strategies import FOREX_STRATEGIES
    from equity_strategies import EQUITY_STRATEGIES

    all_strategies = set()
    all_strategies.update(CRYPTO_STRATEGIES.keys())
    all_strategies.update(FOREX_STRATEGIES.keys())
    all_strategies.update(EQUITY_STRATEGIES.keys())

    for strategy_name in all_strategies:
        # Hard-disabled strategies: immediate kill, no evaluation needed
        # Includes exact name, pattern match (*_15m_D_ensemble_stack), and category match (forex)
        _strat_cat = "forex" if strategy_name in FOREX_STRATEGIES else ""
        if is_strategy_disabled(strategy_name, _strat_cat):
            actions[strategy_name] = {
                "action": "DISABLE",
                "reason": f"HARD DISABLED (confirmed net-negative by audit)",
                "stats": {},
            }
            continue

        stats = db.compute_strategy_stats(strategy_name)
        closed = stats.get("closed_picks", 0)

        if closed < cfg["min_picks_for_eval"]:
            actions[strategy_name] = {
                "action": "MONITOR",
                "reason": f"Insufficient data ({closed}/{cfg['min_picks_for_eval']} picks)",
                "stats": stats,
            }
            continue

        win_rate = stats.get("win_rate", 0)
        sharpe = stats.get("sharpe", 0)
        rolling_sharpe = stats.get("rolling_sharpe", sharpe)
        max_dd = stats.get("max_drawdown", 0)

        # Rolling Sharpe decay check: if Sharpe has gone negative over recent
        # trades, the strategy is degrading and should be demoted (P1 roadmap item)
        if closed >= 10 and rolling_sharpe < -0.5:
            actions[strategy_name] = {
                "action": "PROBATION",
                "reason": f"Sharpe decay: rolling_sharpe={rolling_sharpe:.2f} < -0.5 ({closed} trades). Strategy may be degrading.",
                "stats": stats,
            }
            log_event(state, "SHARPE_DECAY", strategy_name,
                      f"Rolling Sharpe {rolling_sharpe:.2f} below -0.5 threshold",
                      {"rolling_sharpe": rolling_sharpe, "overall_sharpe": sharpe})
            continue

        # $500 loss cap: kill any strategy that has lost > $500 (Feb 28 2026)
        # NOTE: Per "Mutate Before Kill" rule, consider DNA mutation / inverse
        # / symbol rotation before permanent disable. Loss cap still triggers
        # immediate disable for capital preservation, but flag for review.
        total_pnl_dollar = stats.get("total_pnl_dollar", 0)
        if total_pnl_dollar < cfg["max_strategy_loss_dollar"] and closed >= 3:
            actions[strategy_name] = {
                "action": "DISABLE",
                "reason": f"Loss cap exceeded: ${total_pnl_dollar:.2f} < ${cfg['max_strategy_loss_dollar']} after {closed} trades. Review: mutate/invert before permanent kill.",
                "stats": stats,
            }
            continue

        # ML strategies get more patience -- they can improve with data (Feb 26 2026)
        ml_keywords = ["ml_", "neural", "deep", "adaptive", "hurst", "fourier",
                        "autocorrelation", "variance_ratio", "regime", "classifier"]
        is_ml = any(kw in strategy_name.lower() for kw in ml_keywords)
        # ML strategies need 12+ picks (vs min_picks_for_wr_check) and lower disable threshold
        disable_picks_threshold = 12 if is_ml else cfg.get("min_picks_for_wr_check", 5)
        disable_wr_threshold = 0.25 if is_ml else cfg["disable_win_rate"]

        # Direction-aware evaluation: check if strategy has a strong direction
        # Don't kill a strategy that's 0% on BUY but 100% on SELL
        direction_stats = stats.get("direction_stats", {})
        has_strong_direction = False
        strong_direction = None
        for direction in ("BUY", "SELL"):
            d_stats = direction_stats.get(direction, {})
            d_closed = d_stats.get("closed", 0)
            d_wr = d_stats.get("win_rate", 0)
            if d_closed >= 2 and d_wr >= 0.60:
                has_strong_direction = True
                strong_direction = direction
                break

        # Check for DISABLE conditions
        if closed >= disable_picks_threshold and win_rate < disable_wr_threshold:
            if has_strong_direction:
                # Don't disable -- restrict to strong direction instead
                actions[strategy_name] = {
                    "action": "RESTRICT",
                    "reason": f"Overall WR {win_rate*100:.1f}% bad, but {strong_direction} is strong. Restricting to {strong_direction} only.",
                    "stats": stats,
                    "restrict_direction": strong_direction,
                }
            elif is_ml:
                # ML gets probation instead of immediate disable
                actions[strategy_name] = {
                    "action": "PROBATION",
                    "reason": f"ML strategy: WR {win_rate*100:.1f}% < {disable_wr_threshold*100}% (patience, may improve with data)",
                    "stats": stats,
                }
            else:
                # NOTE: Per user's "Mutate Before Kill" rule, consider DNA
                # mutation (parameter variation), INVERSE signal (flip
                # direction), or symbol rotation before permanently disabling
                # a strategy. Only disable after mutation attempts fail.
                actions[strategy_name] = {
                    "action": "DISABLE",
                    "reason": f"Win rate {win_rate*100:.1f}% < {disable_wr_threshold*100}% threshold ({disable_picks_threshold}+ picks). Consider: mutate params, invert signal, or rotate symbols before killing.",
                    "stats": stats,
                }
        elif sharpe < cfg["disable_sharpe"]:
            if has_strong_direction:
                actions[strategy_name] = {
                    "action": "RESTRICT",
                    "reason": f"Sharpe {sharpe:.2f} < 0 overall, but {strong_direction} is profitable. Restricting.",
                    "stats": stats,
                    "restrict_direction": strong_direction,
                }
            else:
                # NOTE: Per user's "Mutate Before Kill" rule, try DNA
                # mutation / inverse / symbol rotation before killing.
                actions[strategy_name] = {
                    "action": "DISABLE",
                    "reason": f"Sharpe {sharpe:.2f} < {cfg['disable_sharpe']} threshold. Consider: mutate params, invert signal, or rotate symbols before killing.",
                    "stats": stats,
                }
        elif closed >= 20 and rolling_sharpe < cfg["disable_rolling_sharpe"]:
            actions[strategy_name] = {
                "action": "DISABLE",
                "reason": f"Rolling 20-trade Sharpe {rolling_sharpe:.2f} < {cfg['disable_rolling_sharpe']} (degrading)",
                "stats": stats,
            }
        elif max_dd < cfg["disable_max_dd"]:
            actions[strategy_name] = {
                "action": "DISABLE",
                "reason": f"Max drawdown {max_dd*100:.1f}% exceeds {cfg['disable_max_dd']*100}% limit",
                "stats": stats,
            }
        # P-value gate: strategies with enough data but no statistical edge
        elif closed >= 20 and stats.get("p_value", 1.0) > 0.10:
            p_val = stats.get("p_value", 1.0)
            actions[strategy_name] = {
                "action": "PROBATION",
                "reason": f"No statistical edge: p={p_val:.3f} > 0.10 after {closed} trades",
                "stats": stats,
            }
            continue
        # Check for PROBATION conditions (warning zone)
        elif win_rate < cfg["warn_win_rate"]:
            actions[strategy_name] = {
                "action": "PROBATION",
                "reason": f"Win rate {win_rate*100:.1f}% below {cfg['warn_win_rate']*100}% warning level",
                "stats": stats,
            }
        # Check for BOOST conditions
        elif win_rate >= cfg["boost_win_rate"] and sharpe >= cfg["boost_sharpe"]:
            actions[strategy_name] = {
                "action": "BOOST",
                "reason": f"Strong performer: WR={win_rate*100:.1f}%, Sharpe={sharpe:.2f}",
                "stats": stats,
            }
        else:
            actions[strategy_name] = {
                "action": "ACTIVE",
                "reason": f"WR={win_rate*100:.1f}%, Sharpe={sharpe:.2f}, PF={stats.get('profit_factor', 0):.2f}",
                "stats": stats,
            }

    return actions


def apply_actions(state: dict, actions: dict):
    """Apply tuning actions to state."""
    for strategy, info in actions.items():
        action = info["action"]

        if action == "DISABLE":
            if strategy not in state["disabled_strategies"]:
                state["disabled_strategies"][strategy] = {
                    "disabled_at": datetime.now(timezone.utc).isoformat(),
                    "reason": info["reason"],
                    "stats_at_disable": {
                        "win_rate": info["stats"].get("win_rate", 0),
                        "sharpe": info["stats"].get("sharpe", 0),
                        "closed_picks": info["stats"].get("closed_picks", 0),
                    },
                }
                log_event(state, "DISABLED", strategy, info["reason"])
            # Remove from boost/probation if present
            state["boosted_strategies"].pop(strategy, None)
            state["probation_strategies"].pop(strategy, None)

        elif action == "PROBATION":
            if strategy not in state["probation_strategies"]:
                state["probation_strategies"][strategy] = {
                    "since": datetime.now(timezone.utc).isoformat(),
                    "reason": info["reason"],
                }
                log_event(state, "PROBATION", strategy, info["reason"])

        elif action == "BOOST":
            if strategy not in state["boosted_strategies"]:
                state["boosted_strategies"][strategy] = {
                    "since": datetime.now(timezone.utc).isoformat(),
                    "boost_factor": 1.5,  # 50% more allocation weight
                }
                log_event(state, "BOOSTED", strategy, info["reason"])
            # Remove from probation if present
            state["probation_strategies"].pop(strategy, None)

        elif action == "RESTRICT":
            # Strategy has a strong direction -- restrict rather than kill
            restrict_dir = info.get("restrict_direction", "BUY")
            if "direction_restrictions" not in state:
                state["direction_restrictions"] = {}
            state["direction_restrictions"][strategy] = {
                "allowed_direction": restrict_dir,
                "since": datetime.now(timezone.utc).isoformat(),
                "reason": info["reason"],
            }
            log_event(state, "RESTRICTED", strategy, info["reason"])
            # Remove from disabled if it was there (we're restricting, not killing)
            state["disabled_strategies"].pop(strategy, None)

        elif action == "ACTIVE":
            # Remove from probation if it recovered
            if strategy in state["probation_strategies"]:
                log_event(state, "RECOVERED", strategy, f"Recovered from probation: {info['reason']}")
                state["probation_strategies"].pop(strategy)
            # Remove restriction if it recovered
            if "direction_restrictions" in state:
                state.get("direction_restrictions", {}).pop(strategy, None)

    # Re-enable disabled strategies if they've been disabled > 7 days
    # BUT NEVER re-enable HARD_DISABLED (graveyard) strategies -- they are permanently dead
    now = datetime.now(timezone.utc)
    stab_path = Path(__file__).resolve().parent.parent / "stabilization" / "disabled_strategies.json"
    graveyard_set = set()
    if stab_path.exists():
        try:
            with open(stab_path) as _gf:
                graveyard_set = set(json.load(_gf).get("graveyard", []))
        except Exception:
            pass
    permanent_dead = HARD_DISABLED_STRATEGIES | graveyard_set

    for strategy in list(state["disabled_strategies"].keys()):
        if strategy in permanent_dead:
            continue  # Never resurrect graveyard strategies
        disabled_at = state["disabled_strategies"][strategy].get("disabled_at", "")
        try:
            dt_val = datetime.fromisoformat(disabled_at.replace("Z", "+00:00"))
            if (now - dt_val.replace(tzinfo=timezone.utc)).days > 7:
                log_event(state, "RE-ENABLED", strategy, "7-day cooldown expired, giving another chance")
                state["disabled_strategies"].pop(strategy)
        except (ValueError, AttributeError):
            pass


def maybe_train_ml(db: SQLiteStore, state: dict, ranker: MLSignalRanker):
    """Auto-train ML model if enough new data has accumulated.

    Always attempts training when no model file exists on disk (common on CI
    where SQLite is ephemeral). ranker.train() handles JSON import fallback.
    """
    cfg = TUNING_CONFIG
    summary = db.get_summary()
    total_closed = summary.get("closed_picks", 0)
    last_train = state.get("last_ml_train_picks", 0)

    # Force training if no model file exists (cold start / CI ephemeral DB)
    from config import ML_MODEL_PATH
    force_train = not ML_MODEL_PATH.exists()

    if not force_train:
        if total_closed < cfg["ml_train_threshold"]:
            print(f"  ML: Need {cfg['ml_train_threshold']} closed picks, have {total_closed}. Skipping.")
            return

        if total_closed - last_train < cfg["ml_retrain_interval"]:
            print(f"  ML: Last trained at {last_train} picks, now {total_closed}. "
                  f"Need {cfg['ml_retrain_interval']} more to retrain.")
            return

    if force_train:
        print(f"  ML: No model on disk -- forcing training (DB has {total_closed}, will try JSON import)...")
    else:
        print(f"  ML: Training model ({total_closed} closed picks, {total_closed - last_train} new)...")

    metrics = ranker.train(db)

    if metrics.get("status") == "trained":
        state["last_ml_train_picks"] = metrics.get("samples", total_closed)
        log_event(state, "ML_TRAINED", "ml_ranker",
                  f"ROC-AUC={metrics.get('cv_roc_auc', 0)*100:.1f}%, "
                  f"samples={metrics.get('samples', 0)}",
                  metrics)
        print(f"  ML: Trained! ROC-AUC={metrics.get('cv_roc_auc', 0)*100:.1f}%, "
              f"model={metrics.get('model_type', '?')}, samples={metrics.get('samples', 0)}")
    else:
        print(f"  ML: {metrics.get('status', 'unknown')}")


def generate_report(actions: dict, state: dict, db: SQLiteStore) -> str:
    """Generate a performance report."""
    summary = db.get_summary()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        "=" * 60,
        f"  ALPHA ENGINE -- Auto-Tuner Report",
        f"  {now}",
        "=" * 60,
        "",
        f"  Portfolio: {summary['open_picks']} open, {summary['closed_picks']} closed",
        f"  Win/Loss: {summary['won']}/{summary['lost']} "
        f"(WR: {summary['win_rate']*100:.1f}%)",
        "",
    ]

    # Strategy breakdown
    active = [s for s, a in actions.items() if a["action"] == "ACTIVE"]
    boosted = [s for s, a in actions.items() if a["action"] == "BOOST"]
    probation = [s for s, a in actions.items() if a["action"] == "PROBATION"]
    disabled = [s for s, a in actions.items() if a["action"] == "DISABLE"]
    monitoring = [s for s, a in actions.items() if a["action"] == "MONITOR"]

    lines.append(f"  Strategies: {len(active)} active, {len(boosted)} boosted, "
                 f"{len(probation)} probation, {len(disabled)} disabled, "
                 f"{len(monitoring)} monitoring")
    lines.append("")

    if boosted:
        lines.append("  BOOSTED (increased allocation):")
        for s in boosted:
            lines.append(f"    + {s}: {actions[s]['reason']}")
        lines.append("")

    if probation:
        lines.append("  PROBATION (warning zone):")
        for s in probation:
            lines.append(f"    ! {s}: {actions[s]['reason']}")
        lines.append("")

    if disabled:
        lines.append("  DISABLED (stopped trading):")
        for s in disabled:
            lines.append(f"    X {s}: {actions[s]['reason']}")
        lines.append("")

    if active:
        lines.append("  ACTIVE:")
        for s in active:
            stats = actions[s]["stats"]
            lines.append(f"    {s}: WR={stats.get('win_rate', 0)*100:.0f}% "
                         f"Sharpe={stats.get('sharpe', 0):.2f} "
                         f"PF={stats.get('profit_factor', 0):.2f} "
                         f"({stats.get('closed_picks', 0)} picks)")
        lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API (called by scanner or workflow)
# ---------------------------------------------------------------------------

def get_disabled_strategies() -> set[str]:
    """Get set of currently disabled strategy names (for scanner to skip).

    Merges four sources:
      1. HARD_DISABLED_STRATEGIES (hardcoded above)
      2. HARD_DISABLED_PATTERNS (pattern-based, e.g. *_15m_D_ensemble_stack)
      3. tuner_state.json (auto-tuner runtime disables)
      4. stabilization/disabled_strategies.json (manual cull list)

    NOTE: Pattern and category disables are checked dynamically via
    is_strategy_disabled() -- this set only contains exact names.
    Scanner should also call is_strategy_disabled() for pattern/category checks.
    """
    state = load_tuner_state()
    disabled = set(state.get("disabled_strategies", {}).keys())
    # Always include hard-disabled strategies
    disabled.update(HARD_DISABLED_STRATEGIES)
    # Always include permanently killed strategies (absolute block)
    # Use case-insensitive comparison for killed strategies
    disabled.update({s.lower() for s in PERMANENTLY_KILLED})
    # Also merge stabilization/disabled_strategies.json (strategy_guard list)
    stab_path = Path(__file__).resolve().parent.parent / "stabilization" / "disabled_strategies.json"
    if stab_path.exists():
        try:
            with open(stab_path) as f:
                stab = json.load(f)
            disabled.update(stab.get("disabled", []))
        except Exception:
            pass
    return disabled


def get_direction_restrictions() -> dict[str, str]:
    """Get direction restrictions for strategies.

    Returns dict: {strategy_name: allowed_direction} where direction is "BUY" or "SELL".
    Strategies not in this dict have no restriction (both directions allowed).
    Merges static (data-backed) restrictions with dynamic (auto-tuner) restrictions.
    """
    restrictions = dict(DIRECTION_RESTRICTED_STRATEGIES)
    # Merge dynamic restrictions from tuner state
    state = load_tuner_state()
    for strat, info in state.get("direction_restrictions", {}).items():
        if strat not in restrictions:  # Static takes precedence
            restrictions[strat] = info.get("allowed_direction", "BUY")
    return restrictions


def get_boost_factors() -> dict[str, float]:
    """Get boost factors for strategies (>1.0 means boosted).

    Merges auto-tuner dynamic boosts with proven strategy static boosts.
    Static boosts from PROVEN_STRATEGY_BOOST take precedence (data-backed).
    """
    state = load_tuner_state()
    boosts = {s: info.get("boost_factor", 1.0)
              for s, info in state.get("boosted_strategies", {}).items()}
    # Apply proven strategy boosts ONLY if statistically significant
    # Load strategy performance to check p-values
    try:
        import json as _json
        perf_path = DATA_DIR / "strategy_performance.json"
        if perf_path.exists():
            with open(perf_path) as _f:
                _perf = _json.load(_f)
            for strat, boost_factor in PROVEN_STRATEGY_BOOST.items():
                strat_data = _perf.get(strat, {})
                p_val = strat_data.get("p_value", 1.0)
                if p_val < 0.05:
                    boosts[strat] = boost_factor
                else:
                    # No boost without statistical significance
                    boosts.setdefault(strat, 1.0)
        else:
            # No performance data yet -- apply boosts as-is (cold start)
            boosts.update(PROVEN_STRATEGY_BOOST)
    except Exception:
        boosts.update(PROVEN_STRATEGY_BOOST)
    return boosts


# ---------------------------------------------------------------------------
# Circuit Breakers -- system-wide emergency stops (Feb 28 2026)
# ---------------------------------------------------------------------------

CIRCUIT_BREAKERS = {
    "consecutive_losing_weeks": 3,       # 3 losing weeks in a row → pause all
    # System-wide DD hard cap — reads PORTFOLIO_MAX_DRAWDOWN_PCT from
    # hedge_fund_quality_gate (single source of truth, env-overridable via
    # HF_GATE_PORTFOLIO_MAX_DD). Convert fraction (0.15) → negative pct (-15.0).
    "max_system_drawdown_pct": -PORTFOLIO_MAX_DRAWDOWN_PCT * 100,
    "min_system_win_rate": 0.40,         # Overall WR < 40% over last 50 trades → pause all
    "max_single_strategy_loss": -500,    # Any strategy loses > $500 → disable that strategy
    "halt_duration_hours": 24,           # How long to pause after circuit breaker trips
}


def check_circuit_breakers(performance_data: dict, closed_picks: list) -> dict:
    """Check system-wide circuit breakers. Returns action dict.

    Args:
        performance_data: Dict from strategy_performance.json
        closed_picks: List of closed pick dicts

    Returns:
        {"halt_system": bool, "reasons": [...], "disable_strategies": [...]}
    """
    result = {"halt_system": False, "reasons": [], "disable_strategies": []}

    # Exclude outlier symbols whose outsized PnL inflates metrics
    try:
        from elite_scorer import OUTLIER_SYMBOLS as _CB_OUTLIER
    except ImportError:
        _CB_OUTLIER = {"FETUSDT", "RENDERUSDT"}
    _filtered_closed = [
        p for p in closed_picks
        if str(p.get("symbol", "") or "").upper() not in _CB_OUTLIER
    ]

    # Check overall WR on last 50 trades (excluding outlier symbols)
    recent = _filtered_closed[-50:] if len(_filtered_closed) >= 50 else _filtered_closed
    if len(recent) >= 20:
        recent_wins = sum(1 for p in recent if float(p.get("pnl_pct", 0) or 0) > 0)
        recent_wr = recent_wins / len(recent)
        if recent_wr < CIRCUIT_BREAKERS["min_system_win_rate"]:
            result["halt_system"] = True
            result["reasons"].append(
                f"System WR {recent_wr:.1%} < {CIRCUIT_BREAKERS['min_system_win_rate']:.0%} "
                f"over last {len(recent)} trades"
            )

    # Check system-wide drawdown from closed picks (excluding outlier symbols)
    if _filtered_closed:
        pnls = [float(p.get("pnl_pct", 0) or 0) for p in _filtered_closed]
        equity = 0.0
        peak = 0.0
        max_dd = 0.0
        for pnl in pnls:
            equity += pnl
            if equity > peak:
                peak = equity
            dd = equity - peak
            if dd < max_dd:
                max_dd = dd
        dd_pct = max_dd * 100
        if dd_pct < CIRCUIT_BREAKERS["max_system_drawdown_pct"]:
            result["halt_system"] = True
            result["reasons"].append(
                f"System drawdown {dd_pct:.1f}% exceeds "
                f"{CIRCUIT_BREAKERS['max_system_drawdown_pct']}% limit"
            )

    # Check per-strategy loss cap
    for strat_name, stats in performance_data.items():
        pnl = stats.get("total_pnl_dollar", 0)
        if pnl < CIRCUIT_BREAKERS["max_single_strategy_loss"] and stats.get("closed_picks", 0) >= 3:
            result["disable_strategies"].append(strat_name)
            result["reasons"].append(
                f"{strat_name}: ${pnl:.2f} < ${CIRCUIT_BREAKERS['max_single_strategy_loss']}"
            )

    # Check consecutive losing weeks from tuner state
    state = load_tuner_state()
    weekly_pnl = state.get("weekly_pnl_history", [])
    if len(weekly_pnl) >= CIRCUIT_BREAKERS["consecutive_losing_weeks"]:
        recent_weeks = weekly_pnl[-CIRCUIT_BREAKERS["consecutive_losing_weeks"]:]
        if all(w.get("pnl", 0) < 0 for w in recent_weeks):
            result["halt_system"] = True
            result["reasons"].append(
                f"{CIRCUIT_BREAKERS['consecutive_losing_weeks']} consecutive losing weeks"
            )

    return result


# ---------------------------------------------------------------------------
# Drawdown Gating — auto-demote/restore via LOW_CONFIDENCE_STRATEGIES
# ---------------------------------------------------------------------------

# Thresholds for drawdown-based demotion and restoration
DRAWDOWN_GATE_CONFIG = {
    "demote_drawdown_pct": 100.0,    # Demote if current drawdown >= 100%
    "demote_loss_streak": 15,         # Demote if longest losing streak >= 15
    "restore_drawdown_pct": 50.0,     # Restore if current drawdown < 50%
    "restore_loss_streak": 10,        # Restore if loss streak < 10
}


def apply_drawdown_gating(state: dict) -> tuple[int, int]:
    """Check per-strategy drawdowns and demote/restore from LOW_CONFIDENCE.

    Demote: drawdown >= 100% OR loss streak >= 15 → add to LOW_CONFIDENCE_STRATEGIES
    Restore: drawdown < 50% AND loss streak < 10 → remove from LOW_CONFIDENCE_STRATEGIES

    Per mutate-before-kill policy: we demote to LOW_CONFIDENCE (0.4x multiplier),
    never hard-kill. The strategy keeps running at reduced confidence.

    Returns:
        (demoted_count, restored_count)
    """
    cfg = DRAWDOWN_GATE_CONFIG
    report = compute_all_drawdowns()
    per_strategy = report.get("per_strategy", {})

    demoted = []
    restored = []

    # Track which strategies were demoted by drawdown gating (vs manually listed)
    if "drawdown_gated_strategies" not in state:
        state["drawdown_gated_strategies"] = []

    previously_gated = set(state.get("drawdown_gated_strategies", []))

    for strategy_name, metrics in per_strategy.items():
        current_dd = metrics.get("current_drawdown_pct", 0.0)
        loss_streak = metrics.get("longest_losing_streak", 0)

        # Skip permanently killed — they're already blocked at a higher level
        # Use case-insensitive comparison (strategies may arrive as lowercase)
        if strategy_name.lower() in {s.lower() for s in PERMANENTLY_KILLED}:
            continue

        in_low_confidence = strategy_name in LOW_CONFIDENCE_STRATEGIES
        was_gated_by_dd = strategy_name in previously_gated

        # --- DEMOTE CHECK ---
        should_demote = (
            current_dd >= cfg["demote_drawdown_pct"]
            or loss_streak >= cfg["demote_loss_streak"]
        )

        if should_demote and not in_low_confidence:
            LOW_CONFIDENCE_STRATEGIES.add(strategy_name)
            previously_gated.add(strategy_name)
            reason_parts = []
            if current_dd >= cfg["demote_drawdown_pct"]:
                reason_parts.append(f"drawdown={current_dd:.1f}%>={cfg['demote_drawdown_pct']}%")
            if loss_streak >= cfg["demote_loss_streak"]:
                reason_parts.append(f"loss_streak={loss_streak}>={cfg['demote_loss_streak']}")
            reason = ", ".join(reason_parts)
            demoted.append(strategy_name)
            log_event(state, "DRAWDOWN_DEMOTE", strategy_name,
                      f"Demoted to LOW_CONFIDENCE: {reason}",
                      {"current_drawdown_pct": current_dd, "longest_losing_streak": loss_streak})

        # --- RESTORE CHECK ---
        # Only restore strategies that were demoted BY drawdown gating,
        # not ones that were manually added to LOW_CONFIDENCE_STRATEGIES.
        elif was_gated_by_dd and in_low_confidence:
            should_restore = (
                current_dd < cfg["restore_drawdown_pct"]
                and loss_streak < cfg["restore_loss_streak"]
            )
            if should_restore:
                LOW_CONFIDENCE_STRATEGIES.discard(strategy_name)
                previously_gated.discard(strategy_name)
                restored.append(strategy_name)
                log_event(state, "DRAWDOWN_RESTORE", strategy_name,
                          f"Restored from LOW_CONFIDENCE: drawdown={current_dd:.1f}%<{cfg['restore_drawdown_pct']}%, "
                          f"loss_streak={loss_streak}<{cfg['restore_loss_streak']}",
                          {"current_drawdown_pct": current_dd, "longest_losing_streak": loss_streak})

    state["drawdown_gated_strategies"] = sorted(previously_gated)

    if demoted or restored:
        print(f"  [DRAWDOWN_GATING] Demoted {len(demoted)} strategies, restored {len(restored)} strategies")
        if demoted:
            print(f"    Demoted: {', '.join(sorted(demoted))}")
        if restored:
            print(f"    Restored: {', '.join(sorted(restored))}")
    else:
        print("  [DRAWDOWN_GATING] No changes (0 demoted, 0 restored)")

    return len(demoted), len(restored)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("\nALPHA ENGINE -- Auto-Tuner")
    print("-" * 40)

    db = SQLiteStore()
    ranker = MLSignalRanker()
    state = load_tuner_state()

    # Step 1: Drawdown gating — demote/restore strategies based on drawdown metrics
    print("\n[1/4] Drawdown gating (demote/restore LOW_CONFIDENCE)...")
    apply_drawdown_gating(state)

    # Step 2: Evaluate all strategies
    print("\n[2/4] Evaluating strategy performance...")
    actions = evaluate_strategies(db, state)

    # Step 3: Apply tuning actions
    print("\n[3/4] Applying tuning actions...")
    apply_actions(state, actions)

    # Step 4: ML model training
    print("\n[4/4] Checking ML model...")
    maybe_train_ml(db, state, ranker)

    # Generate and print report
    report = generate_report(actions, state, db)
    print(report)

    # Save state
    save_tuner_state(state)

    # Save report to file
    report_path = DATA_DIR / "tuner_report.txt"
    with open(report_path, "w") as f:
        f.write(report)

    # Save performance snapshot as JSON (for dashboard consumption)
    perf_snapshot = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": db.get_summary(),
        "strategy_actions": {s: {"action": a["action"], "reason": a["reason"]}
                             for s, a in actions.items()},
        "disabled_count": len(state.get("disabled_strategies", {})),
        "boosted_count": len(state.get("boosted_strategies", {})),
        "ml_trained": ranker.is_trained,
    }
    with open(DATA_DIR / "performance_snapshot.json", "w") as f:
        json.dump(perf_snapshot, f, indent=2)

    db.close()
    print(f"\nTuner state saved to {TUNER_STATE_PATH}")


if __name__ == "__main__":
    main()
