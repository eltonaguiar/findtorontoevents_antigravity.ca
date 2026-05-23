"""
Sentinel Fund Enhancements v2
==============================
Additional modules that complete the Sentinel enhancement roadmap:

6. HierarchicalRiskParity    -- Equalise risk contribution across buckets (pure stdlib)
7. WhaleClusterRiskScorer    -- Heuristic on-chain whale-risk scoring (no GNN)
8. StrategyPreserver         -- Paper-trade monitor instead of kill (management policy)
9. InverseStrategyGenerator  -- Auto-create inverse variants of underperformers
10. StrategyVariantCombiner  -- Blend metrics from multiple strategies into hybrids

Management Policy:
    "We do NOT prune strategies. Instead we paper-trade/monitor them,
     create inverse variants, and decommission only after extended
     observation. Every strategy is an asset -- even failing ones
     can become profitable when inverted or combined."

Usage:
    from sentinel_enhancements_v2 import (
        HierarchicalRiskParity,
        WhaleClusterRiskScorer,
        StrategyPreserver,
        InverseStrategyGenerator,
        StrategyVariantCombiner,
    )

Author: Sentinel Fund System
Version: 2.0.0
"""

import json
import logging
import math
import copy
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

from sentinel_fund_strategy import Signal, StrategyPerformance, MarketRegime

logger = logging.getLogger("SentinelEnhancementsV2")


# ===========================================================================
# 6. Hierarchical Risk-Parity (pure stdlib, no scipy)
# ===========================================================================

@dataclass
class BucketAllocation:
    """Risk-parity allocation for one bucket"""
    bucket_name: str
    strategies: List[str]
    raw_weight: float       # before normalisation
    final_weight: float     # after normalisation (sums to 1.0 across buckets)
    risk_contribution: float  # volatility contribution
    strategy_weights: Dict[str, float] = field(default_factory=dict)


class HierarchicalRiskParity:
    """
    Two-level risk-parity allocator (pure Python, no scipy):

    Level 1 -- Bucket weights:
        Allocate across {core, incubator, macro} buckets so that each
        bucket contributes equally to total portfolio volatility.

    Level 2 -- Intra-bucket weights:
        Within each bucket, weight strategies inversely proportional
        to their individual volatility (inverse-vol weighting).

    The algorithm uses iterative inverse-volatility rebalancing:
        w_i = (1 / vol_i) / sum(1 / vol_j for all j)

    This is the standard "naive risk parity" that approximates the
    full convex-optimisation solution when correlations are moderate.
    """

    def __init__(
        self,
        buckets: Optional[Dict[str, List[str]]] = None,
        min_weight: float = 0.02,    # no bucket gets < 2%
        max_weight: float = 0.60,    # no bucket gets > 60%
    ):
        self.buckets = buckets or {
            "core": [],
            "incubator": [],
            "macro": [],
        }
        self.min_weight = min_weight
        self.max_weight = max_weight

    def _estimate_volatility(self, equity_curve: List[float]) -> float:
        """Annualised volatility from an equity curve (daily returns assumed)."""
        if len(equity_curve) < 2:
            return 0.10  # default 10% vol if no data
        returns = [
            (equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1]
            for i in range(1, len(equity_curve))
            if equity_curve[i - 1] != 0
        ]
        if not returns:
            return 0.10
        mean_r = sum(returns) / len(returns)
        var = sum((r - mean_r) ** 2 for r in returns) / len(returns)
        daily_vol = math.sqrt(var)
        return daily_vol * math.sqrt(365)  # annualise for crypto (365 days)

    def _inverse_vol_weights(
        self, vols: Dict[str, float]
    ) -> Dict[str, float]:
        """Inverse-volatility weighting."""
        inv = {}
        for k, v in vols.items():
            inv[k] = 1.0 / max(v, 0.001)  # floor to avoid div-by-zero
        total = sum(inv.values())
        return {k: v / total for k, v in inv.items()} if total > 0 else {}

    def allocate(
        self,
        strategy_equity_curves: Dict[str, List[float]],
    ) -> Dict[str, BucketAllocation]:
        """
        Compute hierarchical risk-parity weights.

        Parameters:
            strategy_equity_curves: {strategy_id: [equity values]}

        Returns:
            {bucket_name: BucketAllocation}
        """
        # Step 1: compute per-strategy volatility
        strat_vols: Dict[str, float] = {}
        for sid, curve in strategy_equity_curves.items():
            strat_vols[sid] = self._estimate_volatility(curve)

        # Step 2: compute per-bucket aggregate volatility
        bucket_vols: Dict[str, float] = {}
        for bname, strats in self.buckets.items():
            member_vols = [strat_vols.get(s, 0.10) for s in strats if s in strat_vols]
            if member_vols:
                # Average vol of bucket members (simple; no correlation matrix)
                bucket_vols[bname] = sum(member_vols) / len(member_vols)
            else:
                bucket_vols[bname] = 0.10

        # Step 3: inverse-vol weights for buckets
        bucket_weights = self._inverse_vol_weights(bucket_vols)

        # Clamp
        for bname in bucket_weights:
            bucket_weights[bname] = max(
                self.min_weight,
                min(self.max_weight, bucket_weights[bname]),
            )
        # Re-normalise after clamping
        total = sum(bucket_weights.values())
        if total > 0:
            bucket_weights = {k: v / total for k, v in bucket_weights.items()}

        # Step 4: intra-bucket inverse-vol weights
        result: Dict[str, BucketAllocation] = {}
        for bname, strats in self.buckets.items():
            member_vols = {s: strat_vols.get(s, 0.10) for s in strats if s in strat_vols}
            intra_weights = self._inverse_vol_weights(member_vols)

            # Scale by bucket weight
            scaled = {s: w * bucket_weights.get(bname, 0) for s, w in intra_weights.items()}

            result[bname] = BucketAllocation(
                bucket_name=bname,
                strategies=strats,
                raw_weight=bucket_vols.get(bname, 0.10),
                final_weight=round(bucket_weights.get(bname, 0), 4),
                risk_contribution=round(bucket_vols.get(bname, 0.10), 4),
                strategy_weights={s: round(w, 6) for s, w in scaled.items()},
            )

        return result


# ===========================================================================
# 7. Whale-Cluster Risk Scorer (heuristic, no GNN)
# ===========================================================================

@dataclass
class WhaleRiskAssessment:
    """Whale activity risk assessment for a symbol"""
    symbol: str
    risk_score: float           # 0.0 (safe) to 1.0 (extreme whale risk)
    risk_level: str             # low / medium / high / extreme
    components: Dict[str, float] = field(default_factory=dict)
    recommendation: str = ""


class WhaleClusterRiskScorer:
    """
    Heuristic whale-cluster risk scorer that combines on-chain and
    market-structure signals into a single risk score (0-1).

    No graph neural network -- uses weighted linear combination of
    observable features:

    Features (each normalised to 0-1):
      1. volume_spike       -- current volume / 20d avg volume
      2. large_tx_ratio     -- % of volume from txns > $100k
      3. exchange_netflow   -- net inflow to exchanges (selling pressure)
      4. funding_rate_extreme -- abs(funding rate) vs historical
      5. order_book_imbalance -- bid/ask depth ratio skew
      6. whale_wallet_change -- large wallets accumulating or dumping

    Score = weighted sum, mapped to risk level thresholds.
    """

    # Default feature weights (sum to 1.0)
    DEFAULT_WEIGHTS: Dict[str, float] = {
        "volume_spike": 0.20,
        "large_tx_ratio": 0.20,
        "exchange_netflow": 0.20,
        "funding_rate_extreme": 0.15,
        "order_book_imbalance": 0.15,
        "whale_wallet_change": 0.10,
    }

    RISK_THRESHOLDS = {
        "low": 0.25,
        "medium": 0.50,
        "high": 0.75,
        # >= 0.75 = extreme
    }

    def __init__(self, custom_weights: Optional[Dict[str, float]] = None):
        self.weights = custom_weights or self.DEFAULT_WEIGHTS.copy()
        # Normalise weights
        total = sum(self.weights.values())
        if total > 0:
            self.weights = {k: v / total for k, v in self.weights.items()}

    @staticmethod
    def _normalise_feature(value: float, low: float, high: float) -> float:
        """Clamp and normalise a feature to [0, 1]."""
        if high <= low:
            return 0.0
        return max(0.0, min(1.0, (value - low) / (high - low)))

    def score(
        self,
        symbol: str,
        volume_current: float = 0.0,
        volume_20d_avg: float = 1.0,
        large_tx_volume: float = 0.0,
        total_volume: float = 1.0,
        exchange_netflow_btc: float = 0.0,
        funding_rate: float = 0.0,
        funding_rate_avg: float = 0.0,
        bid_depth: float = 1.0,
        ask_depth: float = 1.0,
        whale_wallet_change_pct: float = 0.0,
    ) -> WhaleRiskAssessment:
        """
        Compute whale-cluster risk score from raw on-chain/market features.

        All parameters are optional -- missing data defaults to neutral (0.0 risk).
        """
        components: Dict[str, float] = {}

        # 1. Volume spike: > 3x average is concerning, > 5x is extreme
        vol_ratio = volume_current / max(volume_20d_avg, 1)
        components["volume_spike"] = self._normalise_feature(vol_ratio, 1.0, 5.0)

        # 2. Large transaction ratio: > 30% from whale txns is high
        ltx_ratio = large_tx_volume / max(total_volume, 1)
        components["large_tx_ratio"] = self._normalise_feature(ltx_ratio, 0.05, 0.40)

        # 3. Exchange netflow: positive = coins flowing to exchanges (sell pressure)
        # Normalise to +/- 1000 BTC range
        components["exchange_netflow"] = self._normalise_feature(
            exchange_netflow_btc, -500, 2000
        )

        # 4. Funding rate extreme: high abs value = overleveraged
        fr_dev = abs(funding_rate - funding_rate_avg)
        components["funding_rate_extreme"] = self._normalise_feature(fr_dev, 0.0, 0.05)

        # 5. Order book imbalance: large ask/bid ratio = sell wall
        if bid_depth > 0:
            imbalance = ask_depth / bid_depth
        else:
            imbalance = 1.0
        components["order_book_imbalance"] = self._normalise_feature(imbalance, 0.5, 3.0)

        # 6. Whale wallet change: negative = dumping
        # Map -5% (dumping) to 1.0 risk, +5% (accumulating) to 0.0
        components["whale_wallet_change"] = self._normalise_feature(
            -whale_wallet_change_pct, -5.0, 5.0
        )

        # Weighted sum
        risk_score = sum(
            components.get(feat, 0.0) * weight
            for feat, weight in self.weights.items()
        )
        risk_score = round(max(0.0, min(1.0, risk_score)), 4)

        # Risk level
        if risk_score >= self.RISK_THRESHOLDS["high"]:
            level = "extreme"
        elif risk_score >= self.RISK_THRESHOLDS["medium"]:
            level = "high"
        elif risk_score >= self.RISK_THRESHOLDS["low"]:
            level = "medium"
        else:
            level = "low"

        # Recommendation
        if level == "extreme":
            rec = "HALT: Extreme whale activity -- reduce position or wait"
        elif level == "high":
            rec = "CAUTION: Significant whale risk -- tighten stops, reduce size"
        elif level == "medium":
            rec = "MONITOR: Moderate whale activity -- proceed with standard sizing"
        else:
            rec = "CLEAR: Low whale risk -- normal operations"

        return WhaleRiskAssessment(
            symbol=symbol,
            risk_score=risk_score,
            risk_level=level,
            components={k: round(v, 4) for k, v in components.items()},
            recommendation=rec,
        )


# ===========================================================================
# 8. Strategy Preserver (paper-trade monitor, NO killing)
# ===========================================================================

class StrategyStatus(Enum):
    """Management-approved strategy lifecycle states"""
    LIVE_CORE = "live_core"             # Full allocation, proven
    LIVE_INCUBATOR = "live_incubator"   # Reduced allocation, promising
    PAPER_TRADE = "paper_trade"         # No real capital, monitoring only
    INVERSE_CANDIDATE = "inverse_candidate"  # Failing -> try inverse
    VARIANT_CANDIDATE = "variant_candidate"  # Low edge -> try combination
    DECOMMISSIONED = "decommissioned"   # Final state after extended observation


@dataclass
class PreservationRecord:
    """Record for a preserved (not killed) strategy"""
    strategy_id: str
    original_status: str
    current_status: str  # StrategyStatus value
    paper_trade_start: Optional[str] = None
    paper_trades: int = 0
    paper_wr: float = 0.0
    paper_pnl: float = 0.0
    inverse_created: bool = False
    variants_created: List[str] = field(default_factory=list)
    observation_days: int = 0
    last_review: Optional[str] = None
    notes: str = ""


class StrategyPreserver:
    """
    Management policy: NEVER kill a strategy outright. Instead:

    1. Underperformers -> paper_trade (monitor with zero real capital)
    2. Consistently negative EV -> inverse_candidate (flip direction)
    3. Low edge but positive -> variant_candidate (combine with others)
    4. Only decommission after 30+ days of paper-trade observation
       AND management sign-off

    This replaces the kill-list with a preservation ledger.
    """

    PAPER_TRADE_FILE = "sentinel_preservation_ledger.json"
    MIN_OBSERVATION_DAYS = 30  # must paper-trade for at least 30 days

    def __init__(self, data_dir: str = "."):
        self.data_dir = Path(data_dir)
        self.ledger: Dict[str, PreservationRecord] = {}
        self._load_ledger()

    def _load_ledger(self):
        path = self.data_dir / self.PAPER_TRADE_FILE
        if path.exists():
            try:
                data = json.loads(path.read_text())
                for sid, rec in data.items():
                    self.ledger[sid] = PreservationRecord(
                        strategy_id=sid,
                        **{k: v for k, v in rec.items() if k != "strategy_id"}
                    )
            except (json.JSONDecodeError, TypeError):
                pass

    def _save_ledger(self):
        path = self.data_dir / self.PAPER_TRADE_FILE
        data = {}
        for sid, rec in self.ledger.items():
            data[sid] = {
                "strategy_id": rec.strategy_id,
                "original_status": rec.original_status,
                "current_status": rec.current_status,
                "paper_trade_start": rec.paper_trade_start,
                "paper_trades": rec.paper_trades,
                "paper_wr": rec.paper_wr,
                "paper_pnl": rec.paper_pnl,
                "inverse_created": rec.inverse_created,
                "variants_created": rec.variants_created,
                "observation_days": rec.observation_days,
                "last_review": rec.last_review,
                "notes": rec.notes,
            }
        path.write_text(json.dumps(data, indent=2))

    def preserve_instead_of_kill(
        self,
        strategy_id: str,
        perf: StrategyPerformance,
        reason: str = "",
    ) -> PreservationRecord:
        """
        Instead of adding to kill_list, move to paper-trade monitoring.

        Decides the preservation path:
          - Negative EV consistently -> inverse_candidate
          - Low EV but positive     -> variant_candidate
          - Otherwise               -> paper_trade
        """
        if perf.expectancy < -0.3 and perf.total_trades >= 15:
            status = StrategyStatus.INVERSE_CANDIDATE.value
            note = f"Negative EV ({perf.expectancy:.2f}%) with {perf.total_trades} trades -> inverse candidate"
        elif 0 <= perf.expectancy < 0.15 and perf.total_trades >= 10:
            status = StrategyStatus.VARIANT_CANDIDATE.value
            note = f"Low EV ({perf.expectancy:.2f}%) -> variant/combination candidate"
        else:
            status = StrategyStatus.PAPER_TRADE.value
            note = f"Moved to paper-trade monitoring: {reason}"

        rec = PreservationRecord(
            strategy_id=strategy_id,
            original_status="live" if strategy_id not in self.ledger else self.ledger[strategy_id].original_status,
            current_status=status,
            paper_trade_start=datetime.now().isoformat(),
            paper_trades=0,
            paper_wr=0.0,
            paper_pnl=0.0,
            notes=note,
            last_review=datetime.now().isoformat(),
        )
        self.ledger[strategy_id] = rec
        self._save_ledger()

        logger.info(f"PRESERVED (not killed): {strategy_id} -> {status}: {note}")
        return rec

    def record_paper_trade(
        self,
        strategy_id: str,
        pnl_percent: float,
    ):
        """Record a paper trade result for a preserved strategy."""
        if strategy_id not in self.ledger:
            return
        rec = self.ledger[strategy_id]
        rec.paper_trades += 1
        rec.paper_pnl += pnl_percent
        if pnl_percent > 0:
            wins = int(rec.paper_wr * (rec.paper_trades - 1))
            wins += 1
            rec.paper_wr = wins / rec.paper_trades
        else:
            wins = int(rec.paper_wr * (rec.paper_trades - 1))
            rec.paper_wr = wins / rec.paper_trades
        self._save_ledger()

    def review_preserved_strategies(self) -> Dict[str, Any]:
        """
        Generate a review report for management.
        Returns strategies grouped by recommended action.
        """
        report = {
            "review_date": datetime.now().isoformat(),
            "total_preserved": len(self.ledger),
            "ready_for_reinstatement": [],    # paper-trade went well
            "ready_for_inverse": [],          # inverse candidate with enough data
            "ready_for_variant": [],          # variant candidate
            "continue_monitoring": [],        # need more observation
            "decommission_candidates": [],    # prolonged failure even in paper
        }

        for sid, rec in self.ledger.items():
            # Calculate observation days
            if rec.paper_trade_start:
                try:
                    start = datetime.fromisoformat(rec.paper_trade_start)
                    rec.observation_days = (datetime.now() - start).days
                except ValueError:
                    rec.observation_days = 0

            entry = {
                "strategy_id": sid,
                "status": rec.current_status,
                "paper_trades": rec.paper_trades,
                "paper_wr": round(rec.paper_wr * 100, 1),
                "paper_pnl": round(rec.paper_pnl, 2),
                "observation_days": rec.observation_days,
                "notes": rec.notes,
            }

            if rec.paper_trades >= 30 and rec.paper_wr >= 0.55 and rec.paper_pnl > 0:
                report["ready_for_reinstatement"].append(entry)
            elif rec.current_status == StrategyStatus.INVERSE_CANDIDATE.value:
                if rec.paper_trades >= 20:
                    report["ready_for_inverse"].append(entry)
                else:
                    report["continue_monitoring"].append(entry)
            elif rec.current_status == StrategyStatus.VARIANT_CANDIDATE.value:
                report["ready_for_variant"].append(entry)
            elif rec.observation_days >= 60 and rec.paper_pnl < -10:
                report["decommission_candidates"].append(entry)
            else:
                report["continue_monitoring"].append(entry)

        self._save_ledger()
        return report


# ===========================================================================
# 9. Inverse Strategy Generator
# ===========================================================================

@dataclass
class InverseStrategy:
    """An automatically generated inverse variant"""
    original_id: str
    inverse_id: str
    flip_direction: bool     # True = flip long<->short
    flip_entry_exit: bool    # True = swap TP and SL logic
    original_wr: float
    expected_inverse_wr: float
    rationale: str


class InverseStrategyGenerator:
    """
    When a strategy consistently loses, its inverse may consistently win.

    For a strategy with WR=30% and RR=1.5, the inverse has:
      - Expected WR ~= 70% (1 - original WR)
      - Direction flipped (long -> short, short -> long)
      - TP and SL swapped

    This is only valid when:
      1. Original has enough trades (>= 20)
      2. Original has consistent negative EV (not random noise)
      3. The market structure allows the inverse (e.g., can short)

    The generator creates a config dict that existing scanners can
    consume to run the inverse in paper-trade mode.
    """

    MIN_TRADES_FOR_INVERSE = 20
    MAX_ORIGINAL_WR = 0.40  # only invert strategies that lose often

    def evaluate_for_inverse(
        self,
        strategy_id: str,
        perf: StrategyPerformance,
    ) -> Optional[InverseStrategy]:
        """
        Evaluate if a strategy is a good inverse candidate.
        Returns None if not suitable.
        """
        if perf.total_trades < self.MIN_TRADES_FOR_INVERSE:
            return None

        if perf.win_rate > self.MAX_ORIGINAL_WR:
            return None  # not consistently losing enough

        if perf.expectancy >= 0:
            return None  # already profitable, no need to invert

        expected_wr = 1.0 - perf.win_rate
        inverse_id = f"{strategy_id}_inverse"

        # Estimate inverse RR: if original has avg_win=1%, avg_loss=2%,
        # inverse gets avg_win=2%, avg_loss=1% (roughly)
        rationale = (
            f"Original WR={perf.win_rate:.0%}, EV={perf.expectancy:.2f}%. "
            f"Inverse expected WR~={expected_wr:.0%}. "
            f"Original avg_loss={abs(perf.avg_loss):.2f}% becomes inverse avg_win."
        )

        return InverseStrategy(
            original_id=strategy_id,
            inverse_id=inverse_id,
            flip_direction=True,
            flip_entry_exit=True,
            original_wr=perf.win_rate,
            expected_inverse_wr=expected_wr,
            rationale=rationale,
        )

    def generate_inverse_signal(
        self,
        original_signal: Signal,
        inverse_meta: InverseStrategy,
    ) -> Signal:
        """
        Create an inverse signal from an original signal.
        Flips direction and swaps TP/SL.
        """
        flipped_dir = "short" if original_signal.direction == "long" else "long"

        return Signal(
            strategy_id=inverse_meta.inverse_id,
            symbol=original_signal.symbol,
            direction=flipped_dir,
            entry_price=original_signal.entry_price,
            stop_loss=original_signal.take_profit,   # TP becomes SL
            take_profit=original_signal.stop_loss,    # SL becomes TP
            timestamp=original_signal.timestamp,
            confidence=original_signal.confidence,
            supporting_systems=[f"inverse_of_{original_signal.strategy_id}"],
            metadata={
                "inverse_of": original_signal.strategy_id,
                "original_direction": original_signal.direction,
                "generation_method": "auto_inverse",
            },
        )

    def batch_evaluate(
        self,
        performances: Dict[str, StrategyPerformance],
    ) -> List[InverseStrategy]:
        """Evaluate all strategies and return viable inverse candidates."""
        candidates = []
        for sid, perf in performances.items():
            inv = self.evaluate_for_inverse(sid, perf)
            if inv is not None:
                candidates.append(inv)
        candidates.sort(key=lambda x: x.expected_inverse_wr, reverse=True)
        return candidates


# ===========================================================================
# 10. Strategy Variant Combiner
# ===========================================================================

@dataclass
class StrategyVariant:
    """A hybrid strategy created by combining metrics from parents"""
    variant_id: str
    parent_ids: List[str]
    combination_method: str   # "consensus_boost", "metric_blend", "regime_switch"
    description: str
    expected_improvement: str
    config: Dict[str, Any] = field(default_factory=dict)


class StrategyVariantCombiner:
    """
    Creates new strategy variants by combining existing strategies:

    Methods:
      1. consensus_boost   -- Only fire when N parent strategies agree
      2. metric_blend      -- Average the entry/TP/SL from multiple parents
      3. regime_switch     -- Use parent A in trending, parent B in ranging
      4. confidence_stack  -- Stack confidence scores from parents

    This turns low-edge individual strategies into higher-edge
    combinations without destroying the originals.
    """

    def create_consensus_variant(
        self,
        parent_ids: List[str],
        min_agreement: int = 2,
    ) -> StrategyVariant:
        """
        Create a variant that only fires when >= min_agreement parents
        produce a signal for the same symbol + direction.
        """
        vid = "consensus_" + "_".join(sorted(parent_ids)[:3])
        if len(parent_ids) > 3:
            vid += f"_+{len(parent_ids) - 3}"

        return StrategyVariant(
            variant_id=vid,
            parent_ids=parent_ids,
            combination_method="consensus_boost",
            description=(
                f"Fires only when >= {min_agreement} of "
                f"{len(parent_ids)} parents agree on direction"
            ),
            expected_improvement=(
                f"Higher WR due to consensus filter; "
                f"fewer trades but better quality"
            ),
            config={
                "min_agreement": min_agreement,
                "parents": parent_ids,
            },
        )

    def create_metric_blend_variant(
        self,
        parent_ids: List[str],
        blend_weights: Optional[Dict[str, float]] = None,
    ) -> StrategyVariant:
        """
        Create a variant that averages entry/TP/SL from parents
        (weighted by their historical performance).
        """
        vid = "blend_" + "_".join(sorted(parent_ids)[:3])
        weights = blend_weights or {p: 1.0 / len(parent_ids) for p in parent_ids}

        return StrategyVariant(
            variant_id=vid,
            parent_ids=parent_ids,
            combination_method="metric_blend",
            description=(
                f"Blends entry/TP/SL from {len(parent_ids)} parents "
                f"using performance-weighted average"
            ),
            expected_improvement="Smoother entries, reduced noise from any single parent",
            config={
                "weights": weights,
                "parents": parent_ids,
            },
        )

    def create_regime_switch_variant(
        self,
        trending_parent: str,
        ranging_parent: str,
        mean_rev_parent: Optional[str] = None,
    ) -> StrategyVariant:
        """
        Create a variant that switches between parents based on
        the current market regime.
        """
        parents = [trending_parent, ranging_parent]
        if mean_rev_parent:
            parents.append(mean_rev_parent)

        vid = f"regime_switch_{trending_parent[:8]}_{ranging_parent[:8]}"

        return StrategyVariant(
            variant_id=vid,
            parent_ids=parents,
            combination_method="regime_switch",
            description=(
                f"Uses {trending_parent} in trending markets, "
                f"{ranging_parent} in ranging"
                + (f", {mean_rev_parent} in mean-reverting" if mean_rev_parent else "")
            ),
            expected_improvement="Regime-adaptive; avoids wrong-regime losses",
            config={
                "trending": trending_parent,
                "ranging": ranging_parent,
                "mean_reverting": mean_rev_parent,
            },
        )

    def create_confidence_stack_variant(
        self,
        parent_ids: List[str],
    ) -> StrategyVariant:
        """
        Create a variant that stacks confidence from parents.
        Final confidence = average of parent confidences.
        Position size scales with stacked confidence.
        """
        vid = "confstack_" + "_".join(sorted(parent_ids)[:3])

        return StrategyVariant(
            variant_id=vid,
            parent_ids=parent_ids,
            combination_method="confidence_stack",
            description=(
                f"Stacks confidence from {len(parent_ids)} parents; "
                f"higher stacked confidence -> larger position"
            ),
            expected_improvement="Better calibrated sizing from multi-source confidence",
            config={
                "parents": parent_ids,
                "aggregation": "weighted_average",
            },
        )

    def blend_signals(
        self,
        signals: List[Signal],
        weights: Optional[Dict[str, float]] = None,
    ) -> Optional[Signal]:
        """
        Given multiple signals for the same symbol, produce a blended signal.
        Only blends if all signals agree on direction.
        Returns None if directions conflict.
        """
        if not signals:
            return None

        directions = set(s.direction for s in signals)
        if len(directions) > 1:
            return None  # conflict

        symbols = set(s.symbol for s in signals)
        if len(symbols) > 1:
            return None  # different symbols

        w = weights or {s.strategy_id: 1.0 / len(signals) for s in signals}
        total_w = sum(w.get(s.strategy_id, 0) for s in signals) or 1.0

        # Weighted average of prices
        entry = sum(s.entry_price * w.get(s.strategy_id, 0) for s in signals) / total_w
        tp = sum(s.take_profit * w.get(s.strategy_id, 0) for s in signals) / total_w
        sl = sum(s.stop_loss * w.get(s.strategy_id, 0) for s in signals) / total_w
        conf = sum(s.confidence * w.get(s.strategy_id, 0) for s in signals) / total_w

        parent_ids = [s.strategy_id for s in signals]
        vid = "blend_" + "_".join(sorted(parent_ids)[:3])

        return Signal(
            strategy_id=vid,
            symbol=signals[0].symbol,
            direction=signals[0].direction,
            entry_price=round(entry, 2),
            take_profit=round(tp, 2),
            stop_loss=round(sl, 2),
            timestamp=max(s.timestamp for s in signals),
            confidence=round(conf, 4),
            supporting_systems=parent_ids,
            metadata={
                "generation_method": "metric_blend",
                "parent_count": len(signals),
                "weights": {s.strategy_id: round(w.get(s.strategy_id, 0), 4) for s in signals},
            },
        )

    def auto_generate_variants(
        self,
        performances: Dict[str, StrategyPerformance],
        category_map: Optional[Dict[str, str]] = None,
    ) -> List[StrategyVariant]:
        """
        Automatically suggest variant combinations based on
        strategy performance profiles.

        Groups by category and creates:
          - Consensus variants within each category
          - Regime-switch variants across categories
          - Confidence-stack variants for high-WR strategies
        """
        variants: List[StrategyVariant] = []
        categories = category_map or {}

        # Group by category
        by_cat: Dict[str, List[str]] = {}
        for sid, cat in categories.items():
            by_cat.setdefault(cat, []).append(sid)

        # Within-category consensus variants
        for cat, strats in by_cat.items():
            if len(strats) >= 3:
                variants.append(
                    self.create_consensus_variant(strats[:5], min_agreement=2)
                )

        # Cross-category regime-switch (if we have trend + mean-rev)
        trend_strats = by_cat.get("trend_following", [])
        mr_strats = by_cat.get("mean_reversion", [])
        if trend_strats and mr_strats:
            variants.append(
                self.create_regime_switch_variant(
                    trending_parent=trend_strats[0],
                    ranging_parent=mr_strats[0],
                    mean_rev_parent=mr_strats[1] if len(mr_strats) > 1 else None,
                )
            )

        # Confidence-stack for high-WR strategies
        high_wr = [sid for sid, p in performances.items() if p.win_rate >= 0.55]
        if len(high_wr) >= 2:
            variants.append(
                self.create_confidence_stack_variant(high_wr[:4])
            )

        return variants


# ===========================================================================
# Demo / Self-Test
# ===========================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("SENTINEL ENHANCEMENTS v2 -- Self-Test")
    print("=" * 80)

    # --- 6. Risk Parity ---
    print("\n--- 6. Hierarchical Risk-Parity ---")
    rp = HierarchicalRiskParity(buckets={
        "core": ["funding_carry", "hurst_regime"],
        "incubator": ["new_strat_a", "new_strat_b"],
        "macro": ["btc_dominance"],
    })
    curves = {
        "funding_carry": [100 + i * 0.5 for i in range(60)],
        "hurst_regime": [100 + i * 0.3 + (i % 5) * 0.2 for i in range(60)],
        "new_strat_a": [100 + i * 0.1 - (i % 3) * 0.5 for i in range(60)],
        "new_strat_b": [100 - i * 0.2 for i in range(60)],
        "btc_dominance": [100 + i * 0.4 for i in range(60)],
    }
    alloc = rp.allocate(curves)
    for bname, ba in alloc.items():
        print(f"  {bname}: weight={ba.final_weight:.1%}, vol={ba.risk_contribution:.4f}")
        for s, w in ba.strategy_weights.items():
            print(f"    {s}: {w:.4%}")

    # --- 7. Whale Risk ---
    print("\n--- 7. Whale-Cluster Risk Scorer ---")
    whale = WhaleClusterRiskScorer()
    assessment = whale.score(
        symbol="BTC-USDT",
        volume_current=5_000_000,
        volume_20d_avg=2_000_000,
        large_tx_volume=800_000,
        total_volume=5_000_000,
        exchange_netflow_btc=500,
        funding_rate=0.03,
        funding_rate_avg=0.01,
        bid_depth=100,
        ask_depth=250,
        whale_wallet_change_pct=-2.0,
    )
    print(f"  Risk score: {assessment.risk_score}")
    print(f"  Level: {assessment.risk_level}")
    print(f"  Recommendation: {assessment.recommendation}")
    for feat, val in assessment.components.items():
        print(f"    {feat}: {val:.3f}")

    # --- 8. Strategy Preserver ---
    print("\n--- 8. Strategy Preserver ---")
    preserver = StrategyPreserver()
    bad_perf = StrategyPerformance(
        strategy_id="ema_crossover",
        total_trades=25,
        winning_trades=7,
        losing_trades=18,
        win_rate=0.28,
        expectancy=-0.45,
        avg_win=1.0,
        avg_loss=0.7,
    )
    rec = preserver.preserve_instead_of_kill("ema_crossover", bad_perf, "low WR")
    print(f"  {rec.strategy_id}: {rec.current_status}")
    print(f"  Notes: {rec.notes}")

    low_perf = StrategyPerformance(
        strategy_id="bollinger_squeeze",
        total_trades=30,
        winning_trades=14,
        losing_trades=16,
        win_rate=0.47,
        expectancy=0.05,
        avg_win=0.8,
        avg_loss=0.7,
    )
    rec2 = preserver.preserve_instead_of_kill("bollinger_squeeze", low_perf, "breakeven")
    print(f"  {rec2.strategy_id}: {rec2.current_status}")
    print(f"  Notes: {rec2.notes}")

    # --- 9. Inverse Strategy ---
    print("\n--- 9. Inverse Strategy Generator ---")
    inv_gen = InverseStrategyGenerator()
    inv = inv_gen.evaluate_for_inverse("ema_crossover", bad_perf)
    if inv:
        print(f"  Inverse candidate: {inv.inverse_id}")
        print(f"  Expected WR: {inv.expected_inverse_wr:.0%}")
        print(f"  Rationale: {inv.rationale}")

        # Generate an inverse signal
        test_sig = Signal(
            strategy_id="ema_crossover",
            symbol="BTC-USDT",
            direction="long",
            entry_price=65000,
            stop_loss=64000,
            take_profit=67000,
            timestamp=datetime.now(),
            confidence=0.5,
        )
        inv_sig = inv_gen.generate_inverse_signal(test_sig, inv)
        print(f"  Original: {test_sig.direction} entry={test_sig.entry_price} TP={test_sig.take_profit} SL={test_sig.stop_loss}")
        print(f"  Inverse:  {inv_sig.direction} entry={inv_sig.entry_price} TP={inv_sig.take_profit} SL={inv_sig.stop_loss}")

    # --- 10. Variant Combiner ---
    print("\n--- 10. Strategy Variant Combiner ---")
    combiner = StrategyVariantCombiner()

    perfs = {
        "funding_carry": StrategyPerformance(strategy_id="funding_carry", win_rate=0.74, total_trades=50),
        "hurst_regime": StrategyPerformance(strategy_id="hurst_regime", win_rate=0.62, total_trades=40),
        "autocorrelation": StrategyPerformance(strategy_id="autocorrelation", win_rate=0.58, total_trades=35),
        "vwap_reversion": StrategyPerformance(strategy_id="vwap_reversion", win_rate=0.55, total_trades=20),
    }
    cat_map = {
        "funding_carry": "funding_arb",
        "hurst_regime": "trend_following",
        "autocorrelation": "mean_reversion",
        "vwap_reversion": "mean_reversion",
    }
    variants = combiner.auto_generate_variants(perfs, cat_map)
    for v in variants:
        print(f"  {v.variant_id}: {v.combination_method}")
        print(f"    Parents: {v.parent_ids}")
        print(f"    {v.description}")

    # Test signal blending
    print("\n  Signal Blending Test:")
    sig_a = Signal(
        strategy_id="autocorrelation",
        symbol="ETH-USDT",
        direction="long",
        entry_price=3500,
        stop_loss=3400,
        take_profit=3700,
        timestamp=datetime.now(),
        confidence=0.65,
    )
    sig_b = Signal(
        strategy_id="vwap_reversion",
        symbol="ETH-USDT",
        direction="long",
        entry_price=3480,
        stop_loss=3380,
        take_profit=3720,
        timestamp=datetime.now(),
        confidence=0.58,
    )
    blended = combiner.blend_signals([sig_a, sig_b])
    if blended:
        print(f"    Blended: entry={blended.entry_price} TP={blended.take_profit} SL={blended.stop_loss}")
        print(f"    Confidence: {blended.confidence:.2f}")
        print(f"    Parents: {blended.supporting_systems}")

    print("\n" + "=" * 80)
    print("All v2 enhancements operational.")
    print("=" * 80)
