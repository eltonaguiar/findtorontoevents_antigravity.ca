"""
Position Sizing

Kelly Criterion, risk-based sizing, and maximum exposure controls.
"Never risk more than 2% on momentum, up to 5% on Safe Bets."

ML-aware Kelly implementation based on:
- Baker & McHale (2013), parameter uncertainty shrinkage
- Osorio (2008), fat-tail adjustments for Student-t returns
- Calibrated probabilities via Platt scaling / isotonic regression
- Fractional Kelly: half-Kelly = 75% of growth with 25% of variance

See RESEARCH_KELLY_AND_SLIPPAGE.md for full literature review.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np


@dataclass
class PositionSizeResult:
    """Result of position sizing calculation."""
    target_weight: float      # Portfolio weight [0, 1]
    target_shares: int        # Number of shares
    target_value: float       # Dollar value of position
    sizing_method: str        # Which method was used
    kelly_fraction: float     # Full Kelly fraction
    risk_amount: float        # Dollar amount at risk
    max_loss_pct: float       # Max loss as % of portfolio


class PositionSizer:
    """
    Position sizing engine implementing multiple methods.
    
    Methods:
    - Kelly Criterion (full and fractional)
    - Fixed percentage risk
    - Volatility targeting
    - Equal weight
    - Risk parity
    """

    def __init__(self, portfolio_value: float = 100000):
        from .. import config
        self.portfolio_value = portfolio_value
        self.max_position_pct = config.MAX_POSITION_PCT
        self.min_position_pct = config.MIN_POSITION_PCT
        self.max_sector_pct = config.MAX_SECTOR_PCT
        self.kelly_fraction = config.KELLY_FRACTION
        self.momentum_max_risk = config.MOMENTUM_MAX_RISK
        self.safe_bet_max_risk = config.SAFE_BET_MAX_RISK

    def kelly_criterion(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        fraction: float = None,
    ) -> float:
        """
        Kelly Criterion for optimal bet sizing.
        
        f* = (p * b - q) / b
        where p = win_rate, q = 1 - p, b = avg_win / avg_loss
        
        Returns fraction of portfolio to bet [0, max_position_pct].
        """
        if fraction is None:
            fraction = self.kelly_fraction

        if avg_loss <= 0 or avg_win <= 0:
            return self.min_position_pct

        p = min(max(win_rate, 0.01), 0.99)
        q = 1 - p
        b = avg_win / avg_loss

        kelly_full = (p * b - q) / b
        kelly_full = max(kelly_full, 0)

        # Apply fraction (quarter-Kelly for safety)
        kelly_fractional = kelly_full * fraction

        # Enforce limits
        return min(max(kelly_fractional, self.min_position_pct), self.max_position_pct)

    def fixed_risk_size(
        self,
        price: float,
        stop_loss_pct: float,
        risk_per_trade_pct: float = 0.02,
    ) -> PositionSizeResult:
        """
        Fixed percentage risk sizing.
        
        Determine position size so that hitting the stop loss = risk_per_trade_pct of portfolio.
        """
        risk_amount = self.portfolio_value * risk_per_trade_pct
        loss_per_share = price * stop_loss_pct

        if loss_per_share <= 0:
            shares = 0
            target_weight = 0
        else:
            shares = int(risk_amount / loss_per_share)
            target_value = shares * price
            target_weight = target_value / self.portfolio_value

        # Cap at max position
        if target_weight > self.max_position_pct:
            target_weight = self.max_position_pct
            target_value = self.portfolio_value * target_weight
            shares = int(target_value / price)

        target_value = shares * price

        return PositionSizeResult(
            target_weight=target_weight,
            target_shares=shares,
            target_value=target_value,
            sizing_method="fixed_risk",
            kelly_fraction=0,
            risk_amount=risk_amount,
            max_loss_pct=risk_per_trade_pct,
        )

    def volatility_target_size(
        self,
        price: float,
        annualized_vol: float,
        target_vol: float = 0.15,
        vol_scalar_cap: Optional[Tuple[float, float]] = None,
    ) -> PositionSizeResult:
        """
        Volatility targeting: size positions inversely proportional to volatility.

        Higher vol → smaller position. Lower vol → bigger position.
        Target portfolio vol = target_vol.

        P3 guard (DAILY_IDEAS_LLMARENA_May162026.MD, swarm-vetted 2026-05-16)
        ------------------------------------------------------------------
        FAILURE MODE: `annualized_vol` is a LAGGED realized-vol estimate. In a
        regime shift the estimate trails the truth, so the raw scalar
        `target_vol / annualized_vol` makes sizing PRO-CYCLICAL — undersized
        going INTO a vol spike, oversized AFTER it — which raises turnover and
        can LOWER risk-adjusted return despite looking correct on iid backtests.

        `vol_scalar_cap=(lo, hi)` (opt-in; default None = unchanged behaviour)
        clamps the raw inverse-vol scalar `target_vol/annualized_vol` BEFORE the
        position-pct bounds. The `hi` cap is the real guard: it stops a stale
        near-zero vol estimate from blowing the position up. Keep `lo` SMALL
        (≈0.0 — let `min_position_pct` floor it); a large `lo` would wrongly
        force genuinely high-vol assets UP to a minimum size, defeating
        vol-targeting. Recommended: `(0.0, 2.0)`. This is an opt-in sidecar:
        callers that do not pass it get the previous behaviour exactly.
        """
        if annualized_vol <= 0:
            annualized_vol = 0.20  # Default 20%

        # Weight = target_vol / stock_vol (inversely proportional)
        vol_scalar = target_vol / annualized_vol
        if vol_scalar_cap is not None:
            lo, hi = vol_scalar_cap
            vol_scalar = min(max(vol_scalar, lo), hi)
        target_weight = vol_scalar
        target_weight = min(max(target_weight, self.min_position_pct), self.max_position_pct)

        target_value = self.portfolio_value * target_weight
        shares = int(target_value / price) if price > 0 else 0
        target_value = shares * price

        return PositionSizeResult(
            target_weight=target_weight,
            target_shares=shares,
            target_value=target_value,
            sizing_method="vol_target",
            kelly_fraction=0,
            risk_amount=target_value * annualized_vol,
            max_loss_pct=target_weight * annualized_vol,
        )

    def equal_weight_size(
        self,
        price: float,
        n_positions: int,
    ) -> PositionSizeResult:
        """Equal weight across all positions."""
        target_weight = min(1.0 / max(n_positions, 1), self.max_position_pct)
        target_value = self.portfolio_value * target_weight
        shares = int(target_value / price) if price > 0 else 0
        target_value = shares * price

        return PositionSizeResult(
            target_weight=target_weight,
            target_shares=shares,
            target_value=target_value,
            sizing_method="equal_weight",
            kelly_fraction=0,
            risk_amount=target_value,
            max_loss_pct=target_weight,
        )

    def compute_position_size(
        self,
        price: float,
        signal_confidence: float,
        signal_category: str,
        stop_loss_pct: float = 0.10,
        annualized_vol: float = 0.25,
        n_positions: int = 20,
        win_rate: float = 0.55,
        avg_win: float = 0.08,
        avg_loss: float = 0.04,
    ) -> PositionSizeResult:
        """
        Master position sizing method that combines all approaches.
        
        For momentum trades: max 2% risk per trade.
        For safe bet / dividend aristocrats: up to 5% risk.
        Uses Kelly + vol targeting as inputs, takes the minimum.
        """
        # Determine risk budget based on category
        if signal_category in ["safe_bet", "dividend_aristocrat", "quality"]:
            max_risk = self.safe_bet_max_risk
        else:
            max_risk = self.momentum_max_risk

        # Method 1: Fixed risk
        risk_result = self.fixed_risk_size(price, stop_loss_pct, max_risk)

        # Method 2: Vol targeting
        vol_result = self.volatility_target_size(price, annualized_vol)

        # Method 3: Kelly
        kelly_weight = self.kelly_criterion(win_rate, avg_win, avg_loss)

        # Method 4: Equal weight (floor)
        eq_result = self.equal_weight_size(price, n_positions)

        # Take the minimum of risk-based and vol-based (conservative)
        target_weight = min(risk_result.target_weight, vol_result.target_weight)

        # Scale by confidence
        target_weight *= signal_confidence

        # Apply Kelly as upper bound
        target_weight = min(target_weight, kelly_weight)

        # Floor at equal weight (don't go below)
        target_weight = max(target_weight, self.min_position_pct)

        # Cap at max
        target_weight = min(target_weight, self.max_position_pct)

        target_value = self.portfolio_value * target_weight
        shares = int(target_value / price) if price > 0 else 0
        target_value = shares * price

        return PositionSizeResult(
            target_weight=target_weight,
            target_shares=shares,
            target_value=target_value,
            sizing_method="composite",
            kelly_fraction=kelly_weight,
            risk_amount=target_value * stop_loss_pct,
            max_loss_pct=target_weight * stop_loss_pct,
        )


# ============================================================================
# ML-Aware Kelly Criterion
# ============================================================================

@dataclass
class TradeRecord:
    """A single completed trade for Kelly estimation."""
    return_pct: float       # Percentage return (e.g. 0.05 = 5%)
    signal_type: str = ""   # Which signal generated this trade


class MLKellySizer:
    """
    Convert ML model probability output to Kelly-optimal position size.

    Pipeline:
    1. Calibrate ML probabilities (Platt scaling or isotonic regression)
    2. Estimate win/loss ratio from rolling trade history
    3. Apply fat-tail kurtosis penalty (crypto returns have kurtosis 5-20x normal)
    4. Apply Baker-McHale parameter uncertainty shrinkage
    5. Apply fractional Kelly (quarter-Kelly default for crypto)

    References:
        Baker & McHale (2013), Decision Analysis 10(3):189-199
        Osorio (2008), SSRN 1271373 (fat-tail Kelly)
        Half-Kelly: 75% of growth, 25% of variance
        Quarter-Kelly: 56% of growth, 6% of variance
    """

    def __init__(
        self,
        kelly_fraction: float = 0.25,
        min_edge: float = 0.02,
        min_trades: int = 30,
        kurtosis_adjust: bool = True,
        uncertainty_shrink: bool = True,
        max_position_pct: float = 0.25,
        rolling_window: int = 200,
    ):
        self.kelly_fraction = kelly_fraction
        self.min_edge = min_edge
        self.min_trades = min_trades
        self.kurtosis_adjust = kurtosis_adjust
        self.uncertainty_shrink = uncertainty_shrink
        self.max_position_pct = max_position_pct
        self.rolling_window = rolling_window
        self.trade_history: List[TradeRecord] = []

    def add_trade(self, return_pct: float, signal_type: str = "") -> None:
        """Record a completed trade for Kelly parameter estimation."""
        self.trade_history.append(TradeRecord(return_pct, signal_type))

    def _get_returns(self, signal_type: str = "") -> np.ndarray:
        """Get recent returns, optionally filtered by signal type."""
        if signal_type:
            trades = [t for t in self.trade_history if t.signal_type == signal_type]
        else:
            trades = list(self.trade_history)
        trades = trades[-self.rolling_window:]
        return np.array([t.return_pct for t in trades])

    def compute_kelly(
        self,
        p_win: float,
        signal_type: str = "",
    ) -> float:
        """
        Compute adjusted Kelly fraction from a calibrated win probability.

        Parameters
        ----------
        p_win : float
            Calibrated probability of a winning trade (0-1).
            MUST be calibrated (Platt/isotonic), not raw model output.
        signal_type : str
            Filter trade history by signal type for win/loss ratio estimation.

        Returns
        -------
        float
            Optimal position weight [0, max_position_pct].
        """
        returns = self._get_returns(signal_type)

        if len(returns) < self.min_trades:
            return 0.0  # Not enough history to estimate parameters

        wins = returns[returns > 0]
        losses = returns[returns < 0]

        if len(wins) < 5 or len(losses) < 5:
            return 0.0  # Need sufficient wins AND losses

        # ---- Step 1: Win/loss ratio ----
        avg_win = float(np.mean(wins))
        avg_loss = float(abs(np.mean(losses)))
        b = avg_win / avg_loss  # Payoff ratio

        # ---- Step 2: Base Kelly ----
        p = min(max(p_win, 0.01), 0.99)
        q = 1.0 - p
        f_kelly = (p * b - q) / b

        if f_kelly <= self.min_edge:
            return 0.0  # No meaningful edge

        # ---- Step 3: Kurtosis penalty for fat tails ----
        # Crypto kurtosis is typically 5-20x normal (excess kurtosis 2-17).
        # For BTC with kurtosis ~8: penalty = 1/(1 + 8/6) = 0.43
        if self.kurtosis_adjust and len(returns) >= 30:
            excess_kurt = float(self._kurtosis(returns))
            excess_kurt = max(excess_kurt, 0)  # Only penalize fat tails
            kurtosis_penalty = 1.0 / (1.0 + excess_kurt / 6.0)
            f_kelly *= kurtosis_penalty

        # ---- Step 4: Baker-McHale uncertainty shrinkage ----
        # Shrinkage = 1 - sigma_p^2 / (p * q)
        # With N samples, sigma_p = sqrt(p*q/N)
        if self.uncertainty_shrink:
            n = len(returns)
            sigma_p = np.sqrt(p * q / n)
            shrinkage = max(0, 1.0 - sigma_p ** 2 / (p * q))
            f_kelly *= shrinkage

        # ---- Step 5: Fractional Kelly ----
        f_final = f_kelly * self.kelly_fraction

        return float(max(0, min(f_final, self.max_position_pct)))

    def compute_kelly_continuous(
        self,
        expected_return: float,
        return_volatility: float,
    ) -> float:
        """
        Continuous Kelly for Gaussian returns: f* = mu / sigma^2.

        Use this when you have a return forecast (not binary classification).

        Parameters
        ----------
        expected_return : float
            Expected return per period (e.g. 0.002 = 0.2% per trade).
        return_volatility : float
            Std dev of returns per period.

        Returns
        -------
        float
            Optimal position weight [0, max_position_pct].
        """
        if return_volatility <= 0:
            return 0.0

        f_kelly = expected_return / (return_volatility ** 2)

        if f_kelly <= 0:
            return 0.0

        # Apply fractional Kelly
        f_final = f_kelly * self.kelly_fraction

        return float(max(0, min(f_final, self.max_position_pct)))

    def diagnostics(self, signal_type: str = "") -> Dict:
        """Return diagnostic info about Kelly estimation quality."""
        returns = self._get_returns(signal_type)
        if len(returns) < self.min_trades:
            return {"status": "insufficient_data", "n_trades": len(returns)}

        wins = returns[returns > 0]
        losses = returns[returns < 0]
        win_rate = len(wins) / len(returns)
        avg_win = float(np.mean(wins)) if len(wins) > 0 else 0
        avg_loss = float(abs(np.mean(losses))) if len(losses) > 0 else 0
        b = avg_win / avg_loss if avg_loss > 0 else 0
        excess_kurt = float(self._kurtosis(returns)) if len(returns) >= 30 else 0

        return {
            "status": "ready",
            "n_trades": len(returns),
            "win_rate": round(win_rate, 4),
            "avg_win_pct": round(avg_win * 100, 2),
            "avg_loss_pct": round(avg_loss * 100, 2),
            "payoff_ratio_b": round(b, 3),
            "excess_kurtosis": round(excess_kurt, 2),
            "kurtosis_penalty": round(1.0 / (1.0 + max(excess_kurt, 0) / 6.0), 3),
            "kelly_fraction_used": self.kelly_fraction,
            "uncertainty_shrinkage": round(
                max(0, 1 - (win_rate * (1 - win_rate) / len(returns))
                    / (win_rate * (1 - win_rate) + 1e-9)), 4),
        }

    @staticmethod
    def _kurtosis(data: np.ndarray) -> float:
        """Compute excess kurtosis (Fisher's definition, normal = 0)."""
        n = len(data)
        if n < 4:
            return 0.0
        mean = np.mean(data)
        std = np.std(data, ddof=1)
        if std < 1e-12:
            return 0.0
        m4 = np.mean((data - mean) ** 4)
        return m4 / (std ** 4) - 3.0
