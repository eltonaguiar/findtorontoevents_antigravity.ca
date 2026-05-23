"""
Confluence Engine -- Hybrid Strategy Ensemble Scoring
=====================================================
Instead of killing underperforming strategies, this engine detects when
multiple strategies fire on the same symbol and applies data-driven
combination rules.  A strategy that loses alone may WIN in confluence
with another.

Key findings from 68-trade correlation analysis:
  - variance_ratio_momentum + fear_greed_extreme_dca = ~72% WR combined
  - TON-USD + variance_ratio_momentum = 5W/0L (golden zone)
  - spike_macd_divergence = 100% WR on forex
  - double_top_bottom_detector = 4.8% WR (suppress unless strong confluence)
  - spike_volume_explosion = 0% WR on TON (anti-correlated with variance_ratio)

Wired into rank_and_filter_signals() in scanner.py.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# --- Strategy Classification ------------------------------------------------

STRATEGY_TYPE = {
    # Momentum
    "variance_ratio_momentum": "momentum",
    "cross_sectional_momentum": "momentum",
    "session_momentum_continuation": "momentum",
    "multi_timeframe_ema_stack": "momentum",
    "sector_rotation_momentum": "momentum",
    # Mean reversion
    "fear_greed_extreme_dca": "mean_reversion",
    "cryptopanic_news_sentiment": "mean_reversion",
    "connors_rsi2": "mean_reversion",
    "rsi_macd_confluence": "mean_reversion",
    "spike_rsi_extreme": "mean_reversion",
    "spike_zscore_extreme": "mean_reversion",
    "sopr_dip_buy_proxy": "mean_reversion",
    "mvrv_sma_proxy": "mean_reversion",
    "bollinger_mean_reversion": "mean_reversion",
    # Breakout
    "atr_volatility_breakout": "breakout",
    "spike_squeeze_breakout": "breakout",
    "break_of_structure": "breakout",
    "smart_money_fvg": "breakout",
    "spike_volume_explosion": "breakout",
    # Trend
    "hash_ribbon_buy": "trend",
    "pentoshi_htf_structure": "trend",
    "wyckoff_accumulation": "trend",
    # Carry / structural
    "funding_rate_carry": "carry",
    "funding_rate_extreme": "carry",
    "funding_rate_arbitrage": "carry",
    "cross_exchange_basis_carry": "carry",
    "oi_funding_squeeze": "carry",
    # On-chain
    "onchain_composite_score": "onchain",
    "nvt_overvaluation": "onchain",
    "stablecoin_buying_power": "onchain",
    "hayes_liquidity_index": "onchain",
    # Volatility
    "vix_spike_reversal": "volatility",
    "dvol_extreme_reversal": "volatility",
    "vol_risk_premium_carry": "volatility",
    # Event-driven
    "token_unlock_dump_short": "event",
    "liquidation_cascade_bottom": "event",
    "netflow_whale_accumulation": "event",
    "whale_accumulation_detector": "event",
    "momentum_crash_recovery": "event",
    # Pattern
    "swing_failure_pattern": "pattern",
    "double_top_bottom_detector": "pattern",
    "spike_macd_divergence": "pattern",
    # Confluence (Wave 23 -- multi-factor high-conviction)
    "fear_keltner_confluence": "confluence",
    "rsi_volume_regime_triple": "confluence",
    "whale_momentum_trust": "confluence",
    "multi_source_validated": "confluence",
    "night_fear_short_triple": "confluence",
    # Wave 11 experimental strategies
    "adaptive_vr_confluence": "momentum",
    "macd_rsi_multi_tf": "pattern",
    "session_range_breakout": "breakout",
    "sentiment_fear_z_reversal": "mean_reversion",
    # Wave 13 NextGen strategies
    "cointegration_pair_trade": "mean_reversion",
    "adx_volatility_breakout": "breakout",
    "seasonal_factor_rotation": "momentum",
    "multi_factor_equity_rotation": "momentum",
    "dead_cat_bounce_momentum": "mean_reversion",
    "market_structure_break": "breakout",
    "volume_acceleration_reversion": "mean_reversion",
    "night_liquidity_drift": "breakout",
    "spread_of_candles_gap": "mean_reversion",
    "vix_correlation_divergence": "volatility",
    "profit_taking_reentry": "momentum",
    "bb_rsi_mean_reversion": "mean_reversion",
    "pi_cycle_regime_gate": "onchain",
    "puell_multiple_extreme": "onchain",
    # CTA Bridge (cta_bridge.py)
    "cta_tsmom_blend": "momentum",
    "cta_donchian_55": "breakout",
    "cta_golden_cross": "trend",
    "cta_fx_multifactor": "momentum",
    "cta_commodity_momentum": "momentum",
    "cta_cross_asset_tsmom": "momentum",
}


# --- Proven Combination Rules (from 68-trade correlation analysis) -----------

# Synergy pairs: if both strategies fire on same symbol, boost confluence score.
# Format: frozenset({strat_a, strat_b}) -> multiplier
SYNERGY_PAIRS = {
    # variance_ratio + fear_greed = ~72% WR historically
    frozenset({"variance_ratio_momentum", "fear_greed_extreme_dca"}): 1.35,
    # Momentum + trend confirmation
    frozenset({"variance_ratio_momentum", "pentoshi_htf_structure"}): 1.25,
    frozenset({"cross_sectional_momentum", "multi_timeframe_ema_stack"}): 1.20,
    # Mean reversion cross-validation
    frozenset({"connors_rsi2", "rsi_macd_confluence"}): 1.30,
    frozenset({"connors_rsi2", "fear_greed_extreme_dca"}): 1.25,
    # On-chain + price signal confluence
    frozenset({"onchain_composite_score", "fear_greed_extreme_dca"}): 1.30,
    frozenset({"mvrv_sma_proxy", "sopr_dip_buy_proxy"}): 1.25,
    frozenset({"hash_ribbon_buy", "pentoshi_htf_structure"}): 1.30,
    # Carry + momentum = strong edge
    frozenset({"funding_rate_carry", "variance_ratio_momentum"}): 1.25,
    frozenset({"oi_funding_squeeze", "liquidation_cascade_bottom"}): 1.20,
    # Volatility + mean reversion (buy the dip with vol confirmation)
    frozenset({"vix_spike_reversal", "connors_rsi2"}): 1.30,
    frozenset({"dvol_extreme_reversal", "fear_greed_extreme_dca"}): 1.25,
    # Pattern + momentum confirmation
    frozenset({"spike_macd_divergence", "session_momentum_continuation"}): 1.20,
    frozenset({"swing_failure_pattern", "break_of_structure"}): 1.25,
}

# Anti-synergy: these combinations SUPPRESS confidence (correlated losses).
# Research (49 trades): crypto convergence = 25% WR vs 52.9% solo.
# FVG pairs and on-chain pairs are the worst offenders.
ANTI_SYNERGY_PAIRS = {
    # spike_volume_explosion anti-correlated with variance_ratio on TON
    frozenset({"spike_volume_explosion", "variance_ratio_momentum"}): 0.60,
    # double_top is 4.8% WR -- suppress unless very strong confluence
    frozenset({"double_top_bottom_detector", "spike_volume_explosion"}): 0.40,
    # FVG + FVG: 0% WR on 2 trades, same methodology = correlated failure
    frozenset({"community_ict_fvg_selective", "smart_money_fvg"}): 0.30,
    # FVG + on-chain: 0% WR, ignores macro shifts
    frozenset({"community_ict_fvg_selective", "mvrv_sma_proxy"}): 0.40,
    # On-chain + stat momentum: 0% WR on BTC (conflicting signals)
    frozenset({"mvrv_sma_proxy", "variance_ratio_momentum"}): 0.50,
}

# Forex convergence golden pairs (100% WR in data)
SYNERGY_PAIRS[frozenset({"session_momentum_continuation", "community_london_breakout_v2_forex"})] = 1.50

# NextGen synergy pairs -- Wave 13
# Cointegration + BB mean-reversion: both mean-reversion but different signals
SYNERGY_PAIRS[frozenset({"cointegration_pair_trade", "bb_rsi_mean_reversion"})] = 1.25
# Dead cat bounce + fear/greed DCA: extreme fear convergence
SYNERGY_PAIRS[frozenset({"dead_cat_bounce_momentum", "fear_greed_extreme_dca"})] = 1.30
# ADX breakout + market structure break: trend confirmation from two angles
SYNERGY_PAIRS[frozenset({"adx_volatility_breakout", "market_structure_break"})] = 1.25
# VIX divergence + VIX spike reversal: dual VIX fear-based signals
SYNERGY_PAIRS[frozenset({"vix_correlation_divergence", "vix_spike_reversal"})] = 1.30
# Volume absorption + BB reversion: both signal reversal in ranging
SYNERGY_PAIRS[frozenset({"volume_acceleration_reversion", "bb_rsi_mean_reversion"})] = 1.20

# Symbol-specific golden zones (from actual trade data)
SYMBOL_STRATEGY_GOLDEN = {
    # TON-USD + variance_ratio = 5W/0L
    ("TONUSDT", "variance_ratio_momentum"): 1.40,
    ("TON-USD", "variance_ratio_momentum"): 1.40,
    # Forex MACD divergence = 100% WR
    ("EURUSD=X", "spike_macd_divergence"): 1.30,
    ("GBPUSD=X", "spike_macd_divergence"): 1.30,
    ("USDJPY=X", "spike_macd_divergence"): 1.30,
    ("NZDUSD=X", "spike_macd_divergence"): 1.30,
    # Connors RSI-2 proven on SPY/QQQ (75% WR backtested)
    ("SPY", "connors_rsi2"): 1.35,
    ("QQQ", "connors_rsi2"): 1.35,
    ("IWM", "connors_rsi2"): 1.25,
}

# Strategies that are too unreliable solo but might contribute to ensemble
ENSEMBLE_ONLY_STRATEGIES = {
    # See HARD_KILL_STRATEGIES below -- the worst offenders are fully killed now
}

# Strategies that are COMPLETELY DISABLED -- never run, never ensemble, never anything.
# These have proven track records of catastrophic losses that no ensemble can save.
# Review quarterly: a strategy can be un-killed if retrained/fixed and backtested.
HARD_KILL_STRATEGIES = {
    "double_top_bottom_detector",  # 4.8% WR, -$17,404 across 21 trades. Kill on sight.
    "spike_volume_explosion",      # 0% WR, -$668 across 8 trades (all TON losses)
    "smart_money_fvg",             # 0% WR, -$369 across 5 trades
    "winner_pattern_precursor",    # 16% WR on 104 trades, -91.9% PnL
    "ml_enhanced_BTCUSDT_15m_D_ensemble_stack",  # 0% WR on 10 trades, -85.3% PnL
    "ml_enhanced_ADAUSDT_15m_D_ensemble_stack",  # 0% WR on 10 trades, -117.0% PnL
    "yahoo_analyst_consensus",     # 0% WR on 5 trades, 27 open positions
}

# Strategies that historically lose -- ONLY fire if 2+ other strategies agree
PROBATION_STRATEGIES: set[str] = set()  # Populated dynamically from auto_tuner state

# Type diversity bonus: different strategy types agreeing = higher edge
TYPE_DIVERSITY_BONUS = {
    2: 0.05,   # 2 different types agree
    3: 0.12,   # 3 different types agree
    4: 0.18,   # 4+ different types agree
}


# --- Main Engine -------------------------------------------------------------

def load_probation_strategies() -> set[str]:
    """Load disabled strategies from auto_tuner state -- these go into ensemble-only mode."""
    try:
        state_path = Path(__file__).parent / "data" / "tuner_state.json"
        if state_path.exists():
            state = json.loads(state_path.read_text())
            return set(state.get("disabled_strategies", {}).keys())
    except Exception:
        pass
    return set()


def compute_confluence_scores(
    signals: list[dict],
    strategy_performance: Optional[dict] = None,
) -> list[dict]:
    """
    Compute confluence scores for all signals.

    For each signal, this examines what OTHER strategies are also firing
    on the same symbol in the same direction, and applies combination rules.

    Modifies signals in-place, adding:
      - confluence_score: float (multiplier, 1.0 = neutral)
      - confluence_reason: str (explanation)
      - confluence_strategies: list[str] (which strategies agree)
      - ensemble_only: bool (True if strategy is in probation/ensemble-only mode)

    Returns the list (same reference, modified in-place).
    """
    if not signals:
        return signals

    # Load probation strategies
    probation = load_probation_strategies() | ENSEMBLE_ONLY_STRATEGIES
    PROBATION_STRATEGIES.update(probation)

    # Group signals by symbol + direction
    symbol_direction_map: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for sig in signals:
        sym = sig["symbol"]
        direction = sig.get("signal_type", "BUY")
        symbol_direction_map[(sym, direction)].append(sig)

    # Performance lookup for dynamic weighting
    perf = strategy_performance or {}

    for sig in signals:
        sym = sig["symbol"]
        strategy = sig["strategy"]
        direction = sig.get("signal_type", "BUY")
        reasons = []
        score = 1.0

        # Is this strategy in probation/ensemble-only mode?
        is_ensemble_only = strategy in probation
        sig["ensemble_only"] = is_ensemble_only

        # Find all OTHER strategies firing on same symbol + direction
        co_signals = symbol_direction_map.get((sym, direction), [])
        co_strategies = [s["strategy"] for s in co_signals if s["strategy"] != strategy]
        sig["confluence_strategies"] = co_strategies

        # -- 1. Synergy pair matching --
        for co_strat in co_strategies:
            pair = frozenset({strategy, co_strat})
            if pair in SYNERGY_PAIRS:
                mult = SYNERGY_PAIRS[pair]
                score *= mult
                reasons.append(f"synergy({co_strat})={mult:.2f}x")
            if pair in ANTI_SYNERGY_PAIRS:
                mult = ANTI_SYNERGY_PAIRS[pair]
                score *= mult
                reasons.append(f"anti-synergy({co_strat})={mult:.2f}x")

        # -- 2. Symbol-specific golden zone --
        golden_key = (sym, strategy)
        if golden_key in SYMBOL_STRATEGY_GOLDEN:
            mult = SYMBOL_STRATEGY_GOLDEN[golden_key]
            score *= mult
            reasons.append(f"golden-zone({sym})={mult:.2f}x")

        # -- 3. Type diversity bonus --
        types_present = set()
        types_present.add(STRATEGY_TYPE.get(strategy, "unknown"))
        for co_strat in co_strategies:
            types_present.add(STRATEGY_TYPE.get(co_strat, "unknown"))
        types_present.discard("unknown")
        n_types = len(types_present)
        if n_types >= 2:
            bonus = TYPE_DIVERSITY_BONUS.get(min(n_types, 4), 0.18)
            score += bonus
            reasons.append(f"type-diversity({n_types} types)+{bonus:.2f}")

        # -- 4. Performance-weighted boost --
        strat_perf = perf.get(strategy, {})
        strat_wr = strat_perf.get("win_rate", 0.5)
        strat_picks = strat_perf.get("closed_picks", 0)
        if strat_picks >= 5 and strat_wr > 0.60:
            # Proven winner -- extra boost
            boost = min((strat_wr - 0.50) * 0.5, 0.15)  # max +0.15
            score += boost
            reasons.append(f"proven-winner(WR={strat_wr:.0%})+{boost:.2f}")
        elif strat_picks >= 5 and strat_wr < 0.35:
            # Consistent loser without confluence -- penalize
            if not co_strategies:
                score *= 0.70
                reasons.append(f"solo-loser(WR={strat_wr:.0%})=-30%")

        # -- 5. Ensemble-only gate --
        if is_ensemble_only and not co_strategies:
            # Probation strategy firing alone -- heavy suppression
            score *= 0.30
            reasons.append("ensemble-only(solo)=-70%")
        elif is_ensemble_only and co_strategies:
            # Probation strategy with backup -- mild boost for being useful
            score *= 1.10
            reasons.append("ensemble-confirmed(+10%)")

        # -- 6. Convergence count bonus / crypto convergence discount --
        # Research (49 trades): crypto convergence = 25% WR vs 52.9% solo.
        # Forex convergence = 100% WR.  Apply penalty for crypto, bonus for forex.
        is_crypto = sym.endswith("USDT") or sym.endswith("-USD") or sym.startswith("BTC") or sym.startswith("ETH")
        is_forex = "=" in sym or sym.endswith("USD") and not is_crypto
        if len(co_strategies) >= 3:
            if is_crypto:
                # Crypto convergence trap: more signals ≠ better in crypto
                score *= 0.75
                reasons.append(f"crypto-convergence-discount({len(co_strategies)+1} strategies)=-25%")
            elif is_forex:
                # Forex convergence is golden
                score *= 1.25
                reasons.append(f"forex-convergence-bonus({len(co_strategies)+1} strategies)")
            else:
                # Equity / other -- mild bonus
                score *= 1.10
                reasons.append(f"convergence({len(co_strategies)+1} strategies)+10%")

        sig["confluence_score"] = round(score, 3)
        sig["confluence_reason"] = " | ".join(reasons) if reasons else "no-confluence"

    return signals


def apply_confluence_to_ml_scores(signals: list[dict]) -> list[dict]:
    """
    Apply confluence scores as multipliers to the ML score.
    This is called AFTER rank_and_filter_signals has set ml_score.

    Modifies signals in-place.
    """
    for sig in signals:
        confluence = sig.get("confluence_score", 1.0)
        if confluence != 1.0:
            original = sig.get("ml_score", 0.5)
            sig["ml_score_pre_confluence"] = original
            # Apply confluence as a multiplier, capped at 0.0-1.0
            adjusted = original * confluence
            sig["ml_score"] = round(max(0.0, min(1.0, adjusted)), 3)

    return signals


def filter_ensemble_only_signals(signals: list[dict], min_score: float = 0.40) -> list[dict]:
    """
    Remove ensemble-only strategies that still don't pass the bar after confluence.
    Keep them if confluence boosted their score above threshold.
    """
    filtered = []
    for sig in signals:
        if sig.get("ensemble_only", False) and sig.get("ml_score", 0) < min_score:
            logger.info(
                "Ensemble-only %s on %s filtered (ml_score=%.3f < %.2f)",
                sig["strategy"], sig["symbol"], sig.get("ml_score", 0), min_score,
            )
            continue
        filtered.append(sig)
    return filtered


def get_ensemble_summary(signals: list[dict]) -> dict:
    """Build a summary of confluence findings for logging/dashboard."""
    confluent = [s for s in signals if s.get("confluence_score", 1.0) > 1.0]
    suppressed = [s for s in signals if s.get("confluence_score", 1.0) < 1.0]
    ensemble_fired = [s for s in signals if s.get("ensemble_only", False)]

    return {
        "total_signals": len(signals),
        "confluent_signals": len(confluent),
        "suppressed_signals": len(suppressed),
        "ensemble_only_fired": len(ensemble_fired),
        "top_confluent": [
            {
                "symbol": s["symbol"],
                "strategy": s["strategy"],
                "confluence_score": s.get("confluence_score", 1.0),
                "confluence_reason": s.get("confluence_reason", ""),
                "ml_score": s.get("ml_score", 0),
            }
            for s in sorted(confluent, key=lambda x: x.get("confluence_score", 0), reverse=True)[:5]
        ],
    }


# ===========================================================================
# ConfluenceEngine -- Cross-Family Signal Aggregation (v2)
# ===========================================================================
# Unlike the synergy-pair approach above (which boosts/suppresses individual
# signals), this class GROUPS signals by (symbol, direction) and requires
# 2+ strategies from DIFFERENT indicator families (config.INDICATOR_FAMILIES)
# to agree within a time window before emitting a trade signal.
#
# Scoring weights (research-backed):
#   40% family diversity  -- independent confirmation is most valuable
#   20% avg confidence    -- strategy self-reported conviction
#   20% avg ML score      -- ML ranker probability
#   10% signal count      -- more signals = more conviction
#   10% avg risk:reward   -- better R:R = higher expected value
# ===========================================================================


class ConfluenceEngine:
    """Aggregate raw strategy signals into confluence-filtered trade signals.

    Only emits a signal when ``min_families`` distinct indicator families
    agree on the same symbol + direction within ``time_window_hours``.
    """

    def __init__(self, min_families: int = 2, time_window_hours: float = 4.0):
        self.min_families = min_families
        self.time_window = timedelta(hours=time_window_hours)

    def process_signals(self, raw_signals: list[dict]) -> list[dict]:
        """Group signals by (symbol, direction), filter by family diversity.

        Parameters
        ----------
        raw_signals : list[dict]
            Each dict must have keys: strategy, symbol, signal_type,
            family, confidence, ml_score, timestamp, entry_price,
            take_profit, stop_loss, risk_reward.

        Returns
        -------
        list[dict]
            Confluence signals sorted by confluence_score descending.
        """
        if not raw_signals:
            return []

        now = datetime.utcnow()

        # Filter out signals outside the time window
        valid_signals: list[dict] = []
        for sig in raw_signals:
            ts = self._parse_timestamp(sig.get("timestamp"))
            if ts is not None and (now - ts) <= self.time_window:
                valid_signals.append(sig)

        # Group by (symbol, direction)
        groups: dict[tuple[str, str], list[dict]] = {}
        for sig in valid_signals:
            key = (sig["symbol"], sig["signal_type"])
            groups.setdefault(key, []).append(sig)

        # Build confluence signals for groups meeting min_families
        results: list[dict] = []
        for (symbol, direction), signals in groups.items():
            families = set(sig["family"] for sig in signals)
            if len(families) < self.min_families:
                continue

            score = self._compute_score(signals, families)
            entry, tp, sl = self._pick_best_levels(signals)

            confidences = [sig.get("confidence", 0.0) for sig in signals]
            ml_scores = [sig.get("ml_score", 0.0) for sig in signals]

            results.append({
                "symbol": symbol,
                "direction": direction,
                "contributing_signals": signals,
                "contributing_strategies": [sig["strategy"] for sig in signals],
                "family_count": len(families),
                "families": sorted(families),
                "confluence_score": round(score, 4),
                "signal_count": len(signals),
                "entry_price": entry,
                "take_profit": tp,
                "stop_loss": sl,
                "avg_confidence": round(
                    sum(confidences) / len(confidences), 4
                ),
                "avg_ml_score": round(
                    sum(ml_scores) / len(ml_scores), 4
                ),
            })

        results.sort(key=lambda x: x["confluence_score"], reverse=True)
        return results

    @staticmethod
    def _compute_score(signals: list[dict], families: set[str]) -> float:
        """Score a confluence group.

        Weights:
          40% family diversity  (family_count / 7, capped at 1.0)
          20% avg confidence
          20% avg ML score
          10% signal count      (count / 10, capped at 1.0)
          10% avg risk:reward   (avg_rr / 5, capped at 1.0)
        """
        n = len(signals)
        family_score = min(len(families) / 7.0, 1.0)

        avg_conf = sum(sig.get("confidence", 0.0) for sig in signals) / n
        avg_ml = sum(sig.get("ml_score", 0.0) for sig in signals) / n
        count_score = min(n / 10.0, 1.0)

        rr_values = [sig.get("risk_reward", 0.0) for sig in signals]
        avg_rr = sum(rr_values) / n if rr_values else 0.0
        rr_score = min(avg_rr / 5.0, 1.0)

        return (
            0.40 * family_score
            + 0.20 * avg_conf
            + 0.20 * avg_ml
            + 0.10 * count_score
            + 0.10 * rr_score
        )

    @staticmethod
    def _pick_best_levels(
        signals: list[dict],
    ) -> tuple[float, float, float]:
        """Pick best entry, TP, and SL from contributing signals.

        - Entry: average of all entry prices (consensus level)
        - Take profit: maximum (most optimistic, reward potential)
        - Stop loss: minimum (widest, most protective)
        """
        entries = [
            sig["entry_price"] for sig in signals if sig.get("entry_price")
        ]
        tps = [
            sig["take_profit"] for sig in signals if sig.get("take_profit")
        ]
        sls = [sig["stop_loss"] for sig in signals if sig.get("stop_loss")]

        entry = sum(entries) / len(entries) if entries else 0.0
        tp = max(tps) if tps else 0.0
        sl = min(sls) if sls else 0.0

        return round(entry, 8), round(tp, 8), round(sl, 8)

    @staticmethod
    def _parse_timestamp(ts: Any) -> datetime | None:
        """Parse a timestamp from ISO string or datetime object."""
        if ts is None:
            return None
        if isinstance(ts, datetime):
            return ts
        if isinstance(ts, str):
            # Handle ISO format with or without microseconds/Z suffix
            ts_clean = ts.replace("Z", "+00:00")
            try:
                dt = datetime.fromisoformat(ts_clean)
                # Strip timezone info for UTC comparison
                return dt.replace(tzinfo=None)
            except ValueError:
                pass
            # Fallback: strptime common formats
            for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
                try:
                    return datetime.strptime(ts, fmt)
                except ValueError:
                    continue
        return None
