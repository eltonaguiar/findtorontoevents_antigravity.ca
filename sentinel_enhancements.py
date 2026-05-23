"""
Sentinel Fund Enhancements
==========================
Future-proofing modules for the Sentinel Fund system:

1. MonteCarloStressTester   — Simulate extreme price scenarios to stress-test strategies
2. AdaptiveRRTarget         — Dynamic RR threshold based on volatility & expectancy
3. ExplainabilityLayer      — Human-readable reasoning for every signal decision
4. CrossExchangeArbGate     — Gate that validates cross-exchange spread profitability
5. DynamicConfidenceScaler  — Scale position size by model-generated confidence (0-1)

Usage:
    from sentinel_enhancements import (
        MonteCarloStressTester,
        AdaptiveRRTarget,
        ExplainabilityLayer,
        CrossExchangeArbGate,
        DynamicConfidenceScaler,
    )

Author: Sentinel Fund System
Version: 1.0.0
"""

import logging
import math
import random
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from sentinel_fund_strategy import Signal, StrategyPerformance, MarketRegime

logger = logging.getLogger("SentinelEnhancements")


# ---------------------------------------------------------------------------
# 1. Monte-Carlo Stress Testing
# ---------------------------------------------------------------------------

@dataclass
class StressTestResult:
    """Results from a Monte-Carlo stress test"""
    strategy_id: str
    simulations: int
    crash_magnitude_percent: float

    # Distribution of final equity across simulations
    median_equity: float = 0.0
    p5_equity: float = 0.0          # 5th percentile (worst-case)
    p95_equity: float = 0.0         # 95th percentile (best-case)

    # Risk metrics
    max_drawdown_median: float = 0.0
    max_drawdown_p95: float = 0.0   # 95th-percentile worst DD
    ruin_probability: float = 0.0   # probability of losing > ruin_threshold
    survives_crash: bool = False

    details: str = ""


class MonteCarloStressTester:
    """
    Simulate N random trade sequences (with optional crash injection)
    to estimate tail-risk behaviour of a strategy.

    Uses the strategy's historical win-rate, avg-win, avg-loss to
    bootstrap synthetic trade streams.
    """

    def __init__(
        self,
        n_simulations: int = 1000,
        trades_per_sim: int = 100,
        ruin_threshold_percent: float = 30.0,
        seed: Optional[int] = None,
    ):
        self.n_simulations = n_simulations
        self.trades_per_sim = trades_per_sim
        self.ruin_threshold = ruin_threshold_percent
        if seed is not None:
            random.seed(seed)

    def stress_test(
        self,
        perf: StrategyPerformance,
        crash_magnitude_percent: float = 30.0,
    ) -> StressTestResult:
        """
        Run Monte-Carlo stress test.

        For each simulation:
          1. Generate `trades_per_sim` random trades using the strategy's
             win-rate / avg-win / avg-loss.
          2. At a random point inject a crash event that causes a single
             loss of `crash_magnitude_percent`.
          3. Track equity curve, max-drawdown, and whether ruin occurs.
        """
        if perf.total_trades < 5:
            return StressTestResult(
                strategy_id=perf.strategy_id,
                simulations=0,
                crash_magnitude_percent=crash_magnitude_percent,
                details="Insufficient trade history (need ≥ 5 trades)",
            )

        wr = max(perf.win_rate, 0.01)
        avg_w = abs(perf.avg_win) if perf.avg_win else 0.5
        avg_l = abs(perf.avg_loss) if perf.avg_loss else 0.5

        final_equities: List[float] = []
        max_drawdowns: List[float] = []
        ruin_count = 0

        for _ in range(self.n_simulations):
            equity = 100.0
            peak = 100.0
            worst_dd = 0.0

            # Decide where the crash lands
            crash_index = random.randint(0, self.trades_per_sim - 1)

            for t in range(self.trades_per_sim):
                if t == crash_index:
                    # Inject crash
                    pnl = -crash_magnitude_percent
                else:
                    pnl = avg_w if random.random() < wr else -avg_l

                equity *= (1 + pnl / 100)
                if equity > peak:
                    peak = equity
                dd = (peak - equity) / peak * 100 if peak > 0 else 0
                if dd > worst_dd:
                    worst_dd = dd

            final_equities.append(equity)
            max_drawdowns.append(worst_dd)
            if (100 - equity) > self.ruin_threshold:
                ruin_count += 1

        final_equities.sort()
        max_drawdowns.sort()
        n = self.n_simulations

        median_eq = final_equities[n // 2]
        p5_eq = final_equities[int(n * 0.05)]
        p95_eq = final_equities[int(n * 0.95)]

        median_dd = max_drawdowns[n // 2]
        p95_dd = max_drawdowns[int(n * 0.95)]
        ruin_prob = ruin_count / n

        survives = p5_eq > (100 - self.ruin_threshold)

        return StressTestResult(
            strategy_id=perf.strategy_id,
            simulations=n,
            crash_magnitude_percent=crash_magnitude_percent,
            median_equity=round(median_eq, 2),
            p5_equity=round(p5_eq, 2),
            p95_equity=round(p95_eq, 2),
            max_drawdown_median=round(median_dd, 2),
            max_drawdown_p95=round(p95_dd, 2),
            ruin_probability=round(ruin_prob, 4),
            survives_crash=survives,
            details=(
                f"{'PASS' if survives else 'FAIL'}: "
                f"5th-pctl equity={p5_eq:.1f}, "
                f"ruin prob={ruin_prob:.1%}, "
                f"95th-pctl DD={p95_dd:.1f}%"
            ),
        )


# ---------------------------------------------------------------------------
# 2. Adaptive RR Target
# ---------------------------------------------------------------------------

class AdaptiveRRTarget:
    """
    Instead of a static 1.5 RR gate, compute a dynamic minimum RR
    based on:
      - Recent realised volatility (higher vol -> demand higher RR)
      - Strategy expectancy (higher expectancy -> can accept lower RR)
      - Market regime

    Formula:
        dynamic_rr = base_rr
                     * vol_factor          (1.0 – 1.5)
                     * expectancy_factor   (0.8 – 1.2)
                     * regime_factor       (0.9 – 1.3)
    """

    def __init__(
        self,
        base_rr: float = 1.5,
        vol_window: int = 24,       # hours of price data
        min_rr_floor: float = 1.0,  # never go below this
        max_rr_cap: float = 3.0,    # never demand above this
    ):
        self.base_rr = base_rr
        self.vol_window = vol_window
        self.min_rr_floor = min_rr_floor
        self.max_rr_cap = max_rr_cap

    def compute_target(
        self,
        recent_prices: List[float],
        strategy_expectancy: float = 0.5,
        regime: MarketRegime = MarketRegime.UNKNOWN,
    ) -> Tuple[float, Dict[str, float]]:
        """
        Returns (dynamic_rr, breakdown_dict).
        """
        # --- Volatility factor ---
        vol_factor = 1.0
        if len(recent_prices) >= 2:
            returns = [
                (recent_prices[i] - recent_prices[i - 1]) / recent_prices[i - 1]
                for i in range(1, len(recent_prices))
            ]
            vol = statistics.stdev(returns) if len(returns) > 1 else 0.0
            # Map vol to [1.0, 1.5]: vol < 1% -> 1.0, vol > 5% -> 1.5
            vol_factor = 1.0 + min(max(vol - 0.01, 0) / 0.04, 0.5)

        # --- Expectancy factor ---
        # High expectancy (>1%) -> can accept lower RR (0.8x)
        # Low expectancy (<0.2%) -> demand higher RR (1.2x)
        if strategy_expectancy > 1.0:
            exp_factor = 0.8
        elif strategy_expectancy > 0.5:
            exp_factor = 0.9
        elif strategy_expectancy > 0.2:
            exp_factor = 1.0
        else:
            exp_factor = 1.2

        # --- Regime factor ---
        regime_factors = {
            MarketRegime.TRENDING: 0.9,        # Trends carry -> accept lower RR
            MarketRegime.MEAN_REVERTING: 1.0,
            MarketRegime.RANGING: 1.1,          # Chop -> need more cushion
            MarketRegime.HIGH_VOLATILITY: 1.3,  # Wild -> demand high RR
            MarketRegime.LOW_VOLATILITY: 1.0,
            MarketRegime.UNKNOWN: 1.1,
        }
        regime_factor = regime_factors.get(regime, 1.1)

        dynamic_rr = self.base_rr * vol_factor * exp_factor * regime_factor
        dynamic_rr = max(self.min_rr_floor, min(dynamic_rr, self.max_rr_cap))

        breakdown = {
            "base_rr": self.base_rr,
            "vol_factor": round(vol_factor, 3),
            "exp_factor": round(exp_factor, 3),
            "regime_factor": round(regime_factor, 3),
            "dynamic_rr": round(dynamic_rr, 3),
        }

        return round(dynamic_rr, 3), breakdown


# ---------------------------------------------------------------------------
# 3. Explainability Layer
# ---------------------------------------------------------------------------

@dataclass
class SignalExplanation:
    """Human-readable audit trail for a signal decision"""
    strategy_id: str
    symbol: str
    direction: str
    final_status: str
    reasoning: str               # one-line summary
    gate_details: List[str]      # ordered list of gate pass/fail
    sizing_details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""

    def to_markdown(self) -> str:
        """Render as a compact markdown block"""
        gates = "\n".join(f"  - {g}" for g in self.gate_details)
        sizing = ", ".join(f"{k}={v}" for k, v in self.sizing_details.items())
        return (
            f"**{self.strategy_id}** {self.direction.upper()} {self.symbol} "
            f"-> **{self.final_status}**\n"
            f"> {self.reasoning}\n\n"
            f"Gates:\n{gates}\n\n"
            f"Sizing: {sizing}"
        )


class ExplainabilityLayer:
    """
    Wraps the Sentinel pipeline and produces a SignalExplanation
    for every processed signal, suitable for client reports or
    compliance logs.
    """

    def explain(
        self,
        signal: Signal,
        perf: StrategyPerformance,
        status: str,
        position_size: float,
        regime: MarketRegime = MarketRegime.UNKNOWN,
        net_expectancy: float = 0.0,
        cost_percent: float = 0.0,
        dynamic_rr: Optional[float] = None,
        stress_result: Optional[StressTestResult] = None,
    ) -> SignalExplanation:
        """Build a full explanation for a signal decision."""
        gate_details: List[str] = []
        reasons: List[str] = []

        # RR
        rr_target = dynamic_rr if dynamic_rr else 1.5
        rr_ok = signal.rr >= rr_target
        gate_details.append(
            f"{'PASS' if rr_ok else 'FAIL'} RR: {signal.rr:.2f} "
            f"(target >= {rr_target:.2f})"
        )
        if rr_ok:
            reasons.append(f"RR={signal.rr:.1f}")

        # Consensus
        n_sys = len(signal.supporting_systems)
        cons_ok = n_sys >= 2
        gate_details.append(
            f"{'PASS' if cons_ok else 'FAIL'} Consensus: "
            f"{n_sys} system{'s' if n_sys != 1 else ''}"
        )
        if cons_ok:
            reasons.append(f"{n_sys}-sys consensus")

        # Cost viability
        if net_expectancy > 0:
            gate_details.append(
                f"PASS Cost: net edge {net_expectancy:.2f}% "
                f"after {cost_percent:.2f}% costs"
            )
        elif cost_percent > 0:
            gate_details.append(
                f"FAIL Cost: edge consumed by {cost_percent:.2f}% costs"
            )

        # Regime
        gate_details.append(f"INFO Regime: {regime.value}")
        if regime != MarketRegime.UNKNOWN:
            reasons.append(f"{regime.value} regime")

        # Performance
        if perf.total_trades >= 10:
            wr_ok = perf.win_rate >= 0.30
            gate_details.append(
                f"{'PASS' if wr_ok else 'WARN'} WR: {perf.win_rate:.0%} "
                f"({perf.total_trades} trades)"
            )

        # Stress test
        if stress_result and stress_result.simulations > 0:
            gate_details.append(
                f"{'PASS' if stress_result.survives_crash else 'FAIL'} "
                f"Stress: ruin prob {stress_result.ruin_probability:.1%}, "
                f"5th-pctl equity {stress_result.p5_equity:.0f}"
            )
            if not stress_result.survives_crash:
                reasons.append("fails crash test")

        # Build one-line reasoning
        if status == "approved":
            reasoning = f"Approved: {', '.join(reasons)}"
        elif status == "incubator":
            reasoning = f"Incubator: needs more evidence — {', '.join(reasons) or 'insufficient gates passed'}"
        else:
            reasoning = f"Rejected: {', '.join(reasons) or 'did not meet minimum criteria'}"

        return SignalExplanation(
            strategy_id=signal.strategy_id,
            symbol=signal.symbol,
            direction=signal.direction,
            final_status=status,
            reasoning=reasoning,
            gate_details=gate_details,
            sizing_details={
                "position_pct": f"{position_size:.2%}",
                "rr": f"{signal.rr:.2f}",
                "confidence": f"{signal.confidence:.2f}",
            },
            timestamp=datetime.now().isoformat(),
        )


# ---------------------------------------------------------------------------
# 4. Cross-Exchange Arbitrage Gate
# ---------------------------------------------------------------------------

@dataclass
class ArbOpportunity:
    """A validated cross-exchange spread"""
    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    spread_percent: float
    net_profit_percent: float   # after fees
    is_profitable: bool


class CrossExchangeArbGate:
    """
    Gate that validates cross-exchange spread profitability before
    approving an arbitrage signal.

    Requires price feeds from at least 2 exchanges.
    """

    # Default taker fees per exchange (percent)
    DEFAULT_FEES: Dict[str, float] = {
        "binance": 0.10,
        "coinbase": 0.20,
        "kraken": 0.16,
        "bybit": 0.10,
        "okx": 0.10,
    }

    def __init__(
        self,
        min_net_profit_percent: float = 0.5,
        custom_fees: Optional[Dict[str, float]] = None,
    ):
        self.min_net_profit = min_net_profit_percent
        self.fees = {**self.DEFAULT_FEES, **(custom_fees or {})}

    def check_spread(
        self,
        symbol: str,
        exchange_prices: Dict[str, float],
    ) -> Optional[ArbOpportunity]:
        """
        Given {exchange: price} for a symbol, find the best spread
        and return an ArbOpportunity (or None if < 2 exchanges).
        """
        if len(exchange_prices) < 2:
            return None

        # Find best buy (lowest) and best sell (highest)
        buy_ex = min(exchange_prices, key=exchange_prices.get)
        sell_ex = max(exchange_prices, key=exchange_prices.get)

        buy_price = exchange_prices[buy_ex]
        sell_price = exchange_prices[sell_ex]

        if buy_price <= 0:
            return None

        gross_spread = (sell_price - buy_price) / buy_price * 100

        # Deduct fees (buy taker + sell taker)
        buy_fee = self.fees.get(buy_ex, 0.20)
        sell_fee = self.fees.get(sell_ex, 0.20)
        net_profit = gross_spread - buy_fee - sell_fee

        return ArbOpportunity(
            symbol=symbol,
            buy_exchange=buy_ex,
            sell_exchange=sell_ex,
            buy_price=buy_price,
            sell_price=sell_price,
            spread_percent=round(gross_spread, 4),
            net_profit_percent=round(net_profit, 4),
            is_profitable=net_profit >= self.min_net_profit,
        )

    def validate_arb_signal(
        self,
        signal: Signal,
        exchange_prices: Dict[str, float],
    ) -> Tuple[bool, str, Optional[ArbOpportunity]]:
        """
        Gate-check an arbitrage signal.
        Returns (passed, reason, opportunity).
        """
        opp = self.check_spread(signal.symbol, exchange_prices)
        if opp is None:
            return False, "Insufficient exchange data", None

        if not opp.is_profitable:
            return (
                False,
                f"Spread {opp.spread_percent:.2f}% -> net {opp.net_profit_percent:.2f}% "
                f"(need >= {self.min_net_profit:.2f}%)",
                opp,
            )

        return (
            True,
            f"Arb OK: buy {opp.buy_exchange} @ {opp.buy_price:.2f}, "
            f"sell {opp.sell_exchange} @ {opp.sell_price:.2f}, "
            f"net {opp.net_profit_percent:.2f}%",
            opp,
        )


# ---------------------------------------------------------------------------
# 5. Dynamic-Confidence Scaling
# ---------------------------------------------------------------------------

class DynamicConfidenceScaler:
    """
    Takes a model-generated confidence score (0-1) and maps it
    to a position-size multiplier using a calibrated curve.

    The mapping is non-linear: low confidence -> aggressive shrink,
    high confidence -> moderate boost (never > max_boost).

    Integrates with RiskBudgetAllocator via the `confidence_boost`
    argument of `calculate_position_size`.
    """

    def __init__(
        self,
        min_confidence: float = 0.3,   # below this -> reject
        neutral_confidence: float = 0.6,  # at this -> 1.0x (no change)
        max_boost: float = 1.5,        # maximum multiplier
        min_scale: float = 0.25,       # minimum multiplier (before rejection)
    ):
        self.min_confidence = min_confidence
        self.neutral = neutral_confidence
        self.max_boost = max_boost
        self.min_scale = min_scale

    def scale(self, confidence: float) -> Tuple[float, str]:
        """
        Map confidence -> (multiplier, description).

        Returns (0.0, "rejected") if confidence < min_confidence.
        """
        if confidence < self.min_confidence:
            return 0.0, f"Confidence {confidence:.2f} below floor {self.min_confidence}"

        if confidence <= self.neutral:
            # Linear interpolation from min_scale to 1.0
            t = (confidence - self.min_confidence) / (self.neutral - self.min_confidence)
            mult = self.min_scale + t * (1.0 - self.min_scale)
        else:
            # Linear interpolation from 1.0 to max_boost
            t = (confidence - self.neutral) / (1.0 - self.neutral)
            mult = 1.0 + t * (self.max_boost - 1.0)

        mult = round(min(mult, self.max_boost), 4)
        return mult, f"Confidence {confidence:.2f} -> {mult:.2f}x size"

    def apply_to_signal(
        self,
        signal: Signal,
        model_confidence: Optional[float] = None,
    ) -> Tuple[float, str]:
        """
        Convenience: use signal.confidence if no model_confidence supplied.
        """
        conf = model_confidence if model_confidence is not None else signal.confidence
        return self.scale(conf)


# ---------------------------------------------------------------------------
# Enhanced Sentinel Integrator (drop-in upgrade)
# ---------------------------------------------------------------------------

class EnhancedSentinelIntegrator:
    """
    Drop-in wrapper that adds all five enhancements on top of
    the existing SentinelIntegrator pipeline.

    Usage:
        from sentinel_enhancements import EnhancedSentinelIntegrator
        from sentinel_integrator import SentinelIntegrator

        base = SentinelIntegrator()
        enhanced = EnhancedSentinelIntegrator(base)

        result = enhanced.process_signal_enhanced(signal, prices, expectancy)
    """

    def __init__(self, base_integrator):
        self.base = base_integrator

        # Enhancement modules
        self.stress_tester = MonteCarloStressTester(n_simulations=500)
        self.adaptive_rr = AdaptiveRRTarget()
        self.explainer = ExplainabilityLayer()
        self.arb_gate = CrossExchangeArbGate()
        self.confidence_scaler = DynamicConfidenceScaler()

    def process_signal_enhanced(
        self,
        signal: Signal,
        recent_prices: Optional[List[float]] = None,
        strategy_expectancy: float = 0.5,
        model_confidence: Optional[float] = None,
        exchange_prices: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Enhanced pipeline:
          1. Adaptive RR gate
          2. Cross-exchange arb check (if exchange_prices given)
          3. Dynamic confidence scaling
          4. Base Sentinel pipeline
          5. Monte-Carlo stress test
          6. Explainability layer
        """
        notes: List[str] = []
        regime = self.base.current_regime

        # --- 1. Adaptive RR ---
        dynamic_rr = None
        if recent_prices and len(recent_prices) >= 2:
            dynamic_rr, rr_breakdown = self.adaptive_rr.compute_target(
                recent_prices, strategy_expectancy, regime
            )
            if signal.rr < dynamic_rr:
                notes.append(
                    f"Adaptive RR block: signal RR {signal.rr:.2f} < "
                    f"dynamic target {dynamic_rr:.2f}"
                )
                explanation = self.explainer.explain(
                    signal,
                    self.base.sentinel.performance_tracker.get(
                        signal.strategy_id,
                        StrategyPerformance(strategy_id=signal.strategy_id),
                    ),
                    "rejected",
                    0.0,
                    regime,
                    dynamic_rr=dynamic_rr,
                )
                return {
                    "status": "rejected",
                    "position_size": 0.0,
                    "reason": notes[-1],
                    "explanation": explanation,
                    "adaptive_rr": rr_breakdown,
                }

        # --- 2. Cross-exchange arb gate ---
        arb_result = None
        if exchange_prices:
            passed, reason, arb_opp = self.arb_gate.validate_arb_signal(
                signal, exchange_prices
            )
            arb_result = {
                "passed": passed,
                "reason": reason,
                "opportunity": arb_opp,
            }
            if not passed and "arb" in signal.strategy_id.lower():
                notes.append(f"Arb gate block: {reason}")
                explanation = self.explainer.explain(
                    signal,
                    StrategyPerformance(strategy_id=signal.strategy_id),
                    "rejected",
                    0.0,
                    regime,
                )
                return {
                    "status": "rejected",
                    "position_size": 0.0,
                    "reason": reason,
                    "explanation": explanation,
                    "arb_check": arb_result,
                }

        # --- 3. Dynamic confidence scaling ---
        conf_mult, conf_desc = self.confidence_scaler.apply_to_signal(
            signal, model_confidence
        )
        notes.append(conf_desc)
        if conf_mult == 0.0:
            explanation = self.explainer.explain(
                signal,
                StrategyPerformance(strategy_id=signal.strategy_id),
                "rejected",
                0.0,
                regime,
            )
            return {
                "status": "rejected",
                "position_size": 0.0,
                "reason": conf_desc,
                "explanation": explanation,
            }

        # --- 4. Base Sentinel pipeline ---
        processed = self.base.process_signal(
            signal, strategy_expectancy
        )

        # Apply confidence multiplier to position size
        adjusted_size = processed.position_size * conf_mult

        # --- 5. Monte-Carlo stress test (for approved/incubator) ---
        stress_result = None
        if processed.status in ("approved", "incubator"):
            perf = self.base.sentinel.performance_tracker.get(
                signal.strategy_id,
                StrategyPerformance(strategy_id=signal.strategy_id),
            )
            stress_result = self.stress_tester.stress_test(perf)

            if stress_result.simulations > 0 and not stress_result.survives_crash:
                # Downgrade to incubator if fails stress test
                if processed.status == "approved":
                    processed.status = "incubator"
                    adjusted_size *= 0.5
                    notes.append(
                        f"Downgraded to incubator: fails 30% crash test "
                        f"(ruin prob {stress_result.ruin_probability:.1%})"
                    )

        # --- 6. Explainability ---
        perf = self.base.sentinel.performance_tracker.get(
            signal.strategy_id,
            StrategyPerformance(strategy_id=signal.strategy_id),
        )
        explanation = self.explainer.explain(
            signal,
            perf,
            processed.status,
            adjusted_size,
            regime,
            net_expectancy=processed.net_expectancy,
            cost_percent=processed.cost_check[1],
            dynamic_rr=dynamic_rr,
            stress_result=stress_result,
        )

        return {
            "status": processed.status,
            "book": processed.book,
            "position_size": round(adjusted_size, 6),
            "confidence_multiplier": conf_mult,
            "net_expectancy": processed.net_expectancy,
            "confidence_score": processed.confidence_score,
            "explanation": explanation,
            "reasoning": explanation.reasoning,
            "adaptive_rr": dynamic_rr,
            "stress_test": stress_result,
            "arb_check": arb_result,
            "notes": notes + processed.processing_notes,
        }

    def batch_process_enhanced(
        self,
        signals: List[Signal],
        recent_prices: Optional[List[float]] = None,
        strategy_expectancies: Optional[Dict[str, float]] = None,
        model_confidences: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """Process a batch of signals with all enhancements."""
        if recent_prices:
            self.base.update_market_regime(recent_prices)

        expectancies = strategy_expectancies or {}
        confidences = model_confidences or {}

        results = []
        for signal in signals:
            r = self.process_signal_enhanced(
                signal,
                recent_prices,
                expectancies.get(signal.strategy_id, 0.5),
                confidences.get(signal.strategy_id),
            )
            results.append(r)

        approved = [r for r in results if r["status"] == "approved"]
        incubator = [r for r in results if r["status"] == "incubator"]
        rejected = [r for r in results if r["status"] == "rejected"]

        return {
            "timestamp": datetime.now().isoformat(),
            "regime": self.base.current_regime.value,
            "summary": {
                "total": len(signals),
                "approved": len(approved),
                "incubator": len(incubator),
                "rejected": len(rejected),
            },
            "approved": approved,
            "incubator": incubator,
            "rejected": rejected,
        }


# ---------------------------------------------------------------------------
# Demo / Self-Test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 80)
    print("SENTINEL ENHANCEMENTS — Self-Test")
    print("=" * 80)

    # 1. Monte-Carlo
    print("\n--- 1. Monte-Carlo Stress Test ---")
    perf = StrategyPerformance(
        strategy_id="funding_carry",
        total_trades=50,
        winning_trades=37,
        losing_trades=13,
        win_rate=0.74,
        avg_win=1.61,
        avg_loss=0.80,
    )
    tester = MonteCarloStressTester(n_simulations=500, seed=42)
    result = tester.stress_test(perf, crash_magnitude_percent=30)
    print(f"  Strategy: {result.strategy_id}")
    print(f"  Median equity: {result.median_equity}")
    print(f"  5th pctl equity: {result.p5_equity}")
    print(f"  95th pctl DD: {result.max_drawdown_p95}%")
    print(f"  Ruin probability: {result.ruin_probability:.1%}")
    print(f"  Survives crash: {result.survives_crash}")

    # 2. Adaptive RR
    print("\n--- 2. Adaptive RR Target ---")
    arr = AdaptiveRRTarget()
    prices = [50000 + i * 100 + random.gauss(0, 200) for i in range(50)]
    target, breakdown = arr.compute_target(prices, 1.61, MarketRegime.TRENDING)
    print(f"  Dynamic RR target: {target}")
    print(f"  Breakdown: {breakdown}")

    # 3. Explainability
    print("\n--- 3. Explainability Layer ---")
    sig = Signal(
        strategy_id="funding_carry",
        symbol="BTC-USDT",
        direction="short",
        entry_price=65000,
        stop_loss=66500,
        take_profit=62000,
        timestamp=datetime.now(),
        supporting_systems=["funding_carry", "volume_profile_value_area"],
        confidence=0.75,
    )
    explainer = ExplainabilityLayer()
    exp = explainer.explain(
        sig, perf, "approved", 0.015,
        MarketRegime.TRENDING, net_expectancy=1.2, cost_percent=0.15,
        stress_result=result,
    )
    print(exp.to_markdown())

    # 4. Cross-Exchange Arb Gate
    print("\n--- 4. Cross-Exchange Arb Gate ---")
    gate = CrossExchangeArbGate(min_net_profit_percent=0.3)
    opp = gate.check_spread("BTC-USDT", {
        "binance": 65000,
        "coinbase": 65400,
        "kraken": 65150,
    })
    if opp:
        print(f"  Best spread: buy {opp.buy_exchange} -> sell {opp.sell_exchange}")
        print(f"  Gross: {opp.spread_percent:.2f}% | Net: {opp.net_profit_percent:.2f}%")
        print(f"  Profitable: {opp.is_profitable}")

    # 5. Dynamic Confidence Scaler
    print("\n--- 5. Dynamic Confidence Scaler ---")
    scaler = DynamicConfidenceScaler()
    for c in [0.2, 0.4, 0.6, 0.8, 0.95]:
        mult, desc = scaler.scale(c)
        print(f"  {desc}")

    print("\n" + "=" * 80)
    print("All enhancements operational.")
    print("=" * 80)
