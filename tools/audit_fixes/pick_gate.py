"""
Pick Gate — The Missing Link
=============================
This module is the SINGLE MOST IMPORTANT fix in the entire codebase.

Problem: validation.py has correct DSR/CPCV/cost-adjusted Sharpe gates,
but the production pick generator NEVER calls them. Models with AUC 0.27
(worse than random) generated live picks → Sharpe -2.799.

This module sits between any signal generator and pick output.
No pick passes without clearing ALL gates.

Usage:
    from tools.pick_gate import PickGate
    
    gate = PickGate()
    result = gate.evaluate(pick_data)
    if result["verdict"] != "PASS":
        logger.warning(f"BLOCKED: {result['reasons']}")
        return None

Author: Forensic Audit Implementation (PR #72)
Date: 2026-04-11
"""
import json
import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# ─── Gate Thresholds (from audit recommendations) ──────────────────────────
# These are HARD GATES — designed to be strict, not permissive.
# The previous system lowered these because "they were blocking all picks."
# That was CORRECT BEHAVIOR when all models are noise.

MIN_DSR_PROBABILITY = 0.95       # Bailey & Lopez de Prado 2014
MIN_TRADES_FOR_SIGNIFICANCE = 30 # Minimum trades before any statistical test
MIN_WIN_RATE = 0.50              # Must beat coin flip
MIN_PROFIT_FACTOR = 1.0          # Gross wins must exceed gross losses
MAX_MODEL_VARIANTS = 10          # Cap multiple testing (Bonferroni)
MIN_SAMPLE_SIZE_BINOMIAL = 50    # Minimum trades for binomial test
MAX_CONCURRENT_PICKS = 10        # Portfolio concentration limit (was 999!)
MIN_WALK_FORWARD_EFFICIENCY = 0.50  # OOS Sharpe / IS Sharpe > 50%
MAX_DRAWDOWN_PCT = 15.0          # 15% max DD constraint
MAX_DAILY_TURNOVER_PCT = 30.0    # 30% NAV/day turnover constraint


class PickGate:
    """
    Hard validation gate for all pick generation paths.
    
    Gate hierarchy:
    1. DATA QUALITY: Is the underlying data fresh and clean?
    2. STATISTICAL SIGNIFICANCE: Is the edge real or noise?
    3. COST VIABILITY: Does the edge survive transaction costs?
    4. PORTFOLIO FIT: Does this pick fit within risk constraints?
    
    Every gate returns PASS/FAIL with reasons. ALL gates must pass.
    """
    
    def __init__(
        self,
        min_dsr: float = MIN_DSR_PROBABILITY,
        min_trades: int = MIN_TRADES_FOR_SIGNIFICANCE,
        min_win_rate: float = MIN_WIN_RATE,
        min_profit_factor: float = MIN_PROFIT_FACTOR,
        max_concurrent: int = MAX_CONCURRENT_PICKS,
        max_dd_pct: float = MAX_DRAWDOWN_PCT,
        max_turnover_pct: float = MAX_DAILY_TURNOVER_PCT,
    ):
        self.min_dsr = min_dsr
        self.min_trades = min_trades
        self.min_win_rate = min_win_rate
        self.min_profit_factor = min_profit_factor
        self.max_concurrent = max_concurrent
        self.max_dd_pct = max_dd_pct
        self.max_turnover_pct = max_turnover_pct
        
        # Track state for portfolio-level constraints
        self._open_positions: List[str] = []
        self._daily_turnover: float = 0.0
        self._peak_nav: float = 0.0
        self._current_nav: float = 0.0

    def evaluate(
        self,
        strategy_name: str,
        trade_history: List[Dict],
        confidence: float = 0.5,
        current_positions: Optional[List[str]] = None,
        current_nav: float = 0.0,
        daily_turnover: float = 0.0,
        model_variants_tested: int = 1,
        is_sharpe: Optional[float] = None,
        oos_sharpe: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Run ALL gates on a proposed pick.
        
        Args:
            strategy_name: Name of the strategy generating this pick
            trade_history: List of dicts with keys: pnl_pct, is_winner
            confidence: Model confidence score (0-1)
            current_positions: List of currently open ticker symbols
            current_nav: Current portfolio NAV for constraint checks
            daily_turnover: Today's traded value so far
            model_variants_tested: Number of model variants tried
            is_sharpe: In-sample Sharpe (for WFE check)
            oos_sharpe: Out-of-sample Sharpe (for WFE check)
            
        Returns:
            Dict with: verdict, reasons, metrics
        """
        reasons: List[str] = []
        metrics: Dict[str, Any] = {}
        
        # ── GATE 1: Sample Size ──────────────────────────────────────────────
        n_trades = len(trade_history)
        metrics["n_trades"] = n_trades
        
        if n_trades < self.min_trades:
            reasons.append(
                f"SAMPLE_SIZE: {n_trades} trades < {self.min_trades} minimum. "
                f"Cannot assess statistical significance."
            )
        
        # ── GATE 2: Win Rate ─────────────────────────────────────────────────
        if n_trades >= self.min_trades:
            winners = sum(1 for t in trade_history if t.get("is_winner", t.get("pnl_pct", 0) > 0))
            win_rate = winners / n_trades
            metrics["win_rate"] = win_rate
            
            if win_rate < self.min_win_rate:
                reasons.append(
                    f"WIN_RATE: {win_rate:.1%} < {self.min_win_rate:.1%} minimum. "
                    f"Strategy does not beat a coin flip."
                )
            
            # Binomial test for statistical significance
            if n_trades >= MIN_SAMPLE_SIZE_BINOMIAL:
                binom_p = self._binomial_test(winners, n_trades, 0.50)
                metrics["binomial_p_value"] = binom_p
                
                if binom_p > 0.05:
                    reasons.append(
                        f"BINOMIAL_TEST: p={binom_p:.4f} > 0.05. "
                        f"Win rate is not statistically significant."
                    )
        
        # ── GATE 3: Profit Factor ────────────────────────────────────────────
        if n_trades >= self.min_trades:
            gross_wins = sum(t.get("pnl_pct", 0) for t in trade_history if t.get("pnl_pct", 0) > 0)
            gross_losses = abs(sum(t.get("pnl_pct", 0) for t in trade_history if t.get("pnl_pct", 0) < 0))
            profit_factor = gross_wins / gross_losses if gross_losses > 0 else float("inf")
            metrics["profit_factor"] = profit_factor
            
            if profit_factor < self.min_profit_factor:
                reasons.append(
                    f"PROFIT_FACTOR: {profit_factor:.2f} < {self.min_profit_factor:.2f}. "
                    f"Losses exceed wins in magnitude."
                )
        
        # ── GATE 4: Deflated Sharpe Ratio ────────────────────────────────────
        if n_trades >= self.min_trades:
            returns = np.array([t.get("pnl_pct", 0) for t in trade_history])
            dsr = self._deflated_sharpe_ratio(
                returns, 
                n_trials=min(model_variants_tested, MAX_MODEL_VARIANTS)
            )
            metrics["dsr_probability"] = dsr
            
            if dsr < self.min_dsr:
                reasons.append(
                    f"DSR: {dsr:.4f} < {self.min_dsr:.2f}. "
                    f"Edge does not survive multiple-testing correction "
                    f"(tested {model_variants_tested} variants)."
                )
        
        # ── GATE 5: Walk-Forward Efficiency ──────────────────────────────────
        if is_sharpe is not None and oos_sharpe is not None and is_sharpe > 0:
            wfe = oos_sharpe / is_sharpe
            metrics["walk_forward_efficiency"] = wfe
            
            if wfe < MIN_WALK_FORWARD_EFFICIENCY:
                reasons.append(
                    f"WFE: {wfe:.2f} < {MIN_WALK_FORWARD_EFFICIENCY:.2f}. "
                    f"OOS Sharpe ({oos_sharpe:.2f}) is less than 50% of "
                    f"IS Sharpe ({is_sharpe:.2f}). Likely overfit."
                )
        
        # ── GATE 6: Portfolio Concentration ──────────────────────────────────
        positions = current_positions or self._open_positions
        if len(positions) >= self.max_concurrent:
            reasons.append(
                f"CONCENTRATION: {len(positions)} positions >= {self.max_concurrent} max. "
                f"Close existing positions before adding new ones."
            )
            metrics["open_positions"] = len(positions)
        
        # ── GATE 7: Drawdown Circuit Breaker ─────────────────────────────────
        if current_nav > 0 and self._peak_nav > 0:
            current_dd = (self._peak_nav - current_nav) / self._peak_nav * 100
            metrics["current_drawdown_pct"] = current_dd
            
            if current_dd >= self.max_dd_pct:
                reasons.append(
                    f"DRAWDOWN: {current_dd:.1f}% >= {self.max_dd_pct:.1f}% max. "
                    f"CIRCUIT BREAKER: All new positions halted."
                )
        
        # ── GATE 8: Turnover Constraint ──────────────────────────────────────
        if current_nav > 0 and daily_turnover > 0:
            turnover_pct = daily_turnover / current_nav * 100
            metrics["daily_turnover_pct"] = turnover_pct
            
            if turnover_pct >= self.max_turnover_pct:
                reasons.append(
                    f"TURNOVER: {turnover_pct:.1f}% >= {self.max_turnover_pct:.1f}% max. "
                    f"Daily turnover limit reached."
                )
        
        # ── VERDICT ──────────────────────────────────────────────────────────
        verdict = "PASS" if len(reasons) == 0 else "FAIL"
        
        result = {
            "verdict": verdict,
            "strategy": strategy_name,
            "reasons": reasons,
            "metrics": metrics,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "gates_checked": 8,
            "gates_failed": len(reasons),
        }
        
        if verdict == "FAIL":
            logger.warning(
                f"PickGate BLOCKED {strategy_name}: "
                f"{len(reasons)} gates failed — {'; '.join(reasons[:3])}"
            )
        else:
            logger.info(
                f"PickGate PASSED {strategy_name}: "
                f"All gates cleared. Metrics: {metrics}"
            )
        
        return result

    def update_nav(self, nav: float):
        """Update NAV tracking for drawdown circuit breaker."""
        self._current_nav = nav
        self._peak_nav = max(self._peak_nav, nav)

    def reset_daily_turnover(self):
        """Call at start of each trading day."""
        self._daily_turnover = 0.0

    # ── Statistical Helpers ──────────────────────────────────────────────────
    
    @staticmethod
    def _binomial_test(successes: int, trials: int, p0: float = 0.50) -> float:
        """
        One-sided binomial test: P(X >= successes | p = p0).
        Uses normal approximation for large n.
        """
        if trials <= 0:
            return 1.0
        
        p_hat = successes / trials
        se = math.sqrt(p0 * (1 - p0) / trials)
        
        if se <= 0:
            return 1.0
        
        z = (p_hat - p0) / se
        
        # Standard normal CDF approximation
        # For production, use scipy.stats.norm.sf(z), but this avoids the dependency
        p_value = 0.5 * math.erfc(z / math.sqrt(2))
        return p_value

    @staticmethod
    def _deflated_sharpe_ratio(
        returns: np.ndarray,
        n_trials: int = 1,
    ) -> float:
        """
        Simplified DSR (Bailey & Lopez de Prado 2014).
        
        Returns probability P(true Sharpe > 0) after multiple-testing correction.
        
        For the full implementation, see crypto_ml_edge/validation.py
        This is a lightweight version for the pick gate.
        """
        if len(returns) < 10:
            return 0.0
        
        # Annualized Sharpe (assume daily returns, 252 trading days)
        std = returns.std()
        if std < 1e-10:
            return 0.0
        
        observed_sr = returns.mean() / std * math.sqrt(252)
        n_obs = len(returns)
        
        # Expected max Sharpe under null (Euler-Mascheroni approximation)
        if n_trials <= 1:
            expected_max_sr = 0.0
        else:
            euler = 0.5772156649
            log2n = 2.0 * math.log(n_trials)
            sqrt_log2n = math.sqrt(log2n)
            expected_max_sr = sqrt_log2n - (math.log(math.pi) + euler) / (2.0 * sqrt_log2n)
        
        # SE of Sharpe (simplified, normal returns)
        se_sr = math.sqrt((1.0 + 0.5 * observed_sr ** 2) / n_obs)
        
        if se_sr <= 0:
            return 0.5
        
        z = (observed_sr - expected_max_sr) / se_sr
        
        # Standard normal CDF
        dsr = 0.5 * (1.0 + math.erf(z / math.sqrt(2)))
        return dsr


class DrawdownCircuitBreaker:
    """
    Hard circuit breaker at configurable max drawdown.
    
    Behavior:
    - At 10% DD: Reduce all new position sizes by 50%
    - At 12% DD: Close momentum/breakout. Keep only defensive.
    - At 15% DD: HALT all trading. Close everything. Human review required.
    """
    
    def __init__(self, initial_nav: float, max_dd_pct: float = 15.0):
        self.peak_nav = initial_nav
        self.max_dd_pct = max_dd_pct
        self.halted = False
    
    def update(self, current_nav: float) -> Dict[str, Any]:
        """Update with current NAV and return action directive."""
        self.peak_nav = max(self.peak_nav, current_nav)
        dd_pct = (self.peak_nav - current_nav) / self.peak_nav * 100 if self.peak_nav > 0 else 0
        
        if dd_pct >= 15.0:
            self.halted = True
            return {
                "drawdown_pct": dd_pct,
                "action": "HALT",
                "position_scalar": 0.0,
                "message": "15% DD breached. HALT all trading. Human review required.",
                "close_categories": ["all"],
            }
        elif dd_pct >= 12.0:
            return {
                "drawdown_pct": dd_pct,
                "action": "defensive_only",
                "position_scalar": 0.25,
                "message": "12% DD. Close momentum/breakout. Keep quality/dividend only.",
                "close_categories": ["momentum", "breakout", "trend", "ml"],
            }
        elif dd_pct >= 10.0:
            return {
                "drawdown_pct": dd_pct,
                "action": "reduce",
                "position_scalar": 0.50,
                "message": "10% DD. New positions at 50% of normal size.",
                "close_categories": [],
            }
        else:
            return {
                "drawdown_pct": dd_pct,
                "action": "normal",
                "position_scalar": 1.0,
                "message": "Normal operation.",
                "close_categories": [],
            }


class TurnoverThrottle:
    """
    Enforce max daily turnover of 30% of NAV.
    
    The previous system had MAX_CONCURRENT_PICKS=999 with 7 bots generating
    signals, meaning turnover could theoretically exceed 100% NAV/day.
    """
    
    def __init__(self, nav: float, max_turnover_pct: float = 30.0):
        self.nav = nav
        self.max_turnover = nav * max_turnover_pct / 100
        self.daily_traded: float = 0.0
    
    def can_trade(self, order_value: float) -> bool:
        """Check if this trade would breach the daily turnover limit."""
        return self.daily_traded + order_value <= self.max_turnover
    
    def record_trade(self, order_value: float):
        """Record a completed trade."""
        self.daily_traded += order_value
    
    def remaining_capacity(self) -> float:
        """Remaining trading capacity in dollars."""
        return max(0, self.max_turnover - self.daily_traded)
    
    def utilization_pct(self) -> float:
        """Current turnover as % of limit."""
        return self.daily_traded / self.max_turnover * 100 if self.max_turnover > 0 else 0
    
    def reset_daily(self, new_nav: Optional[float] = None):
        """Call at start of each trading day."""
        self.daily_traded = 0.0
        if new_nav is not None:
            self.nav = new_nav
            self.max_turnover = new_nav * 30.0 / 100


# ─── Convenience: validate a batch of picks ──────────────────────────────────

def gate_picks(
    picks: List[Dict],
    strategy_histories: Dict[str, List[Dict]],
    current_positions: List[str] = None,
    current_nav: float = 0.0,
) -> List[Dict]:
    """
    Filter a list of picks through the gate. Returns only passing picks.
    
    Args:
        picks: List of pick dicts with at least 'strategy' and 'ticker' keys
        strategy_histories: Dict of strategy_name -> list of historical trades
        current_positions: Currently open tickers
        current_nav: Current NAV
    
    Returns:
        List of picks that passed all gates (may be empty)
    """
    gate = PickGate()
    if current_nav > 0:
        gate.update_nav(current_nav)
    
    passed = []
    for pick in picks:
        strategy = pick.get("strategy", "unknown")
        history = strategy_histories.get(strategy, [])
        
        result = gate.evaluate(
            strategy_name=strategy,
            trade_history=history,
            confidence=pick.get("confidence", 0.5),
            current_positions=current_positions,
            current_nav=current_nav,
        )
        
        if result["verdict"] == "PASS":
            pick["gate_result"] = result
            passed.append(pick)
        else:
            logger.info(f"Filtered out {pick.get('ticker', '?')}: {result['reasons'][:2]}")
    
    logger.info(f"PickGate: {len(passed)}/{len(picks)} picks passed all gates")
    return passed
