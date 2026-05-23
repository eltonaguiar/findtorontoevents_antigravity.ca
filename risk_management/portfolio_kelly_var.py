"""
Portfolio-Level Kelly Sizing with Per-Symbol VaR
=================================================
Implements Kelly Criterion position sizing at portfolio level
with per-symbol Value at Risk constraints.

Planned v1.2 from updates_torontoevent.html - NOW IMPLEMENTED
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class KellyVaRConfig:
    """Configuration for Kelly + VaR position sizing."""
    kelly_fraction: float = 0.25  # Quarter-Kelly for safety
    max_position_pct: float = 0.10  # Max 10% per position
    min_position_pct: float = 0.01  # Min 1% per position
    portfolio_var_limit: float = 0.02  # 2% daily VaR limit base
    per_symbol_var_limit: float = 0.01  # 1% daily VaR per symbol base
    confidence_level: float = 0.95  # 95% VaR
    correlation_decay: float = 0.94  # EWMA decay for correlations
    
    # Regime-based risk multipliers (Institutional standard)
    regime_multipliers: Dict[str, float] = None
    
    def __post_init__(self):
        if self.regime_multipliers is None:
            self.regime_multipliers = {
                "STRONG_BULL": 1.75,   # High risk budget in clear bull
                "BULL": 1.50,
                "LEANING_BULL": 1.00,
                "CHOP": 0.50,          # Preserved capital in chop
                "LEANING_BEAR": 0.35,
                "BEAR": 0.20,          # Defensive in bear
                "STRONG_BEAR": 0.15
            }


class PortfolioKellyVaR:
    """
    Portfolio-level Kelly sizing with VaR constraints.
    
    Combines:
    1. Kelly Criterion for optimal position sizing
    2. Per-symbol VaR limits
    3. Portfolio-level VaR constraint
    4. Correlation-aware risk allocation
    
    Status: IMPLEMENTED (was PLANNED v1.2)
    """
    
    def __init__(self, config: KellyVaRConfig = None):
        self.config = config or KellyVaRConfig()
        self.positions = {}
        self.returns_history = {}
        self.correlation_matrix = None
        
        logger.info("✅ Portfolio Kelly+VaR INITIALIZED (v1.2 IMPLEMENTED)")
    
    def compute_kelly_size(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        current_equity: float
    ) -> Dict:
        """
        Compute Kelly-optimal position size.
        
        Args:
            win_rate: Probability of winning (0-1)
            avg_win: Average win percentage
            avg_loss: Average loss percentage
            current_equity: Current portfolio equity
        
        Returns:
            Position sizing recommendation
        """
        # Edge case: no losses
        if avg_loss == 0:
            kelly_pct = self.config.max_position_pct
        else:
            # Kelly formula: f* = (p*b - q) / b
            # where p = win rate, q = loss rate, b = avg_win/avg_loss
            b = avg_win / avg_loss
            q = 1 - win_rate
            
            kelly_raw = (win_rate * b - q) / b
            
            # Apply Kelly fraction (safety factor)
            kelly_pct = kelly_raw * self.config.kelly_fraction
        
        # Apply bounds
        kelly_pct = np.clip(
            kelly_pct,
            self.config.min_position_pct,
            self.config.max_position_pct
        )
        
        position_value = current_equity * kelly_pct
        
        return {
            'kelly_raw': kelly_raw if avg_loss != 0 else 1.0,
            'kelly_fraction': self.config.kelly_fraction,
            'position_pct': kelly_pct,
            'position_value': position_value,
            'risk_amount': position_value * avg_loss
        }
    
    def compute_var(
        self,
        returns: np.ndarray,
        confidence: float = None
    ) -> float:
        """
        Compute Value at Risk.
        
        Args:
            returns: Array of historical returns
            confidence: Confidence level (default from config)
        
        Returns:
            VaR as positive number (e.g., 0.02 = 2%)
        """
        if confidence is None:
            confidence = self.config.confidence_level
        
        if len(returns) < 30:
            logger.warning(f"Insufficient data for VaR: {len(returns)} samples")
            return 0.05  # Conservative default
        
        # Historical VaR
        var = np.percentile(returns, (1 - confidence) * 100)
        
        return abs(var)
    
    def compute_cvar(
        self,
        returns: np.ndarray,
        confidence: float = None
    ) -> float:
        """
        Compute Conditional Value at Risk (Expected Shortfall).
        
        Returns:
            CVaR as positive number
        """
        if confidence is None:
            confidence = self.config.confidence_level
        
        var = self.compute_var(returns, confidence)
        cvar = returns[returns <= -var].mean()
        
        return abs(cvar)
    
    def update_returns(self, symbol: str, return_value: float):
        """Update returns history for a symbol."""
        if symbol not in self.returns_history:
            self.returns_history[symbol] = []
        
        self.returns_history[symbol].append(return_value)
        
        # Keep last 252 days (1 year)
        self.returns_history[symbol] = self.returns_history[symbol][-252:]
    
    def compute_correlation_matrix(self, symbols: List[str]) -> pd.DataFrame:
        """
        Compute correlation matrix for symbols.
        
        Uses EWMA for more recent relevance.
        """
        returns_df = pd.DataFrame({
            sym: self.returns_history.get(sym, [0] * 30)
            for sym in symbols
        })
        
        # EWMA correlation
        ewma_cov = returns_df.ewm(span=int(1 / (1 - self.config.correlation_decay))).cov()
        
        # Extract correlation from last period
        last_cov = ewma_cov.iloc[-len(symbols):, :]
        
        # Convert to correlation
        stds = np.sqrt(np.diag(last_cov))
        corr = last_cov / np.outer(stds, stds)
        
        return pd.DataFrame(corr, index=symbols, columns=symbols)
    
    def compute_portfolio_var(
        self,
        weights: Dict[str, float],
        symbols: List[str]
    ) -> float:
        """
        Compute portfolio-level VaR using correlation matrix.
        
        Args:
            weights: Dict of symbol -> position weight
            symbols: List of symbols in portfolio
        
        Returns:
            Portfolio VaR
        """
        if len(symbols) < 2:
            # Single asset
            symbol = symbols[0]
            returns = np.array(self.returns_history.get(symbol, [0] * 30))
            return self.compute_var(returns) * weights.get(symbol, 0)
        
        # Get correlation matrix
        corr_matrix = self.compute_correlation_matrix(symbols)
        
        # Get individual VaRs
        var_vector = np.array([
            self.compute_var(np.array(self.returns_history.get(sym, [0] * 30)))
            for sym in symbols
        ])
        
        # Weight vector
        w = np.array([weights.get(sym, 0) for sym in symbols])
        
        # Portfolio VaR: sqrt(w' * Σ * w) where Σ is covariance
        # Approximate using correlation and individual VaRs
        portfolio_var = np.sqrt(
            w @ np.outer(var_vector, var_vector) * corr_matrix.values @ w
        )
        
        return portfolio_var
    
    def size_position(
        self,
        symbol: str,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        current_equity: float,
        existing_positions: Dict[str, float] = None,
        regime: str = "LEANING_BULL"
    ) -> Dict:
        """
        Compute optimal position size with all constraints.
        
        Args:
            symbol: Trading symbol
            win_rate: Strategy win rate
            avg_win: Average win %
            avg_loss: Average loss %
            current_equity: Total equity
            existing_positions: Current positions {symbol: value}
            regime: Current market regime (e.g., BULL, CHOP)
        
        Returns:
            Sizing recommendation with all constraints applied
        """
        existing_positions = existing_positions or {}
        
        # Step 0: Apply regime multiplier to limits
        multiplier = self.config.regime_multipliers.get(regime, 1.0)
        p_var_limit = self.config.portfolio_var_limit * multiplier
        s_var_limit = self.config.per_symbol_var_limit * multiplier
        
        # Step 1: Kelly sizing
        kelly = self.compute_kelly_size(win_rate, avg_win, avg_loss, current_equity)
        position_pct = kelly['position_pct']
        
        # Step 2: Per-symbol VaR constraint
        returns = np.array(self.returns_history.get(symbol, [0] * 60))
        symbol_var = self.compute_var(returns)
        
        # Max position based on VaR limit
        max_var_position = s_var_limit / max(symbol_var, 0.001)
        position_pct = min(position_pct, max_var_position)
        
        # Step 3: Portfolio VaR constraint
        all_symbols = list(existing_positions.keys()) + [symbol]
        new_weights = {
            **{s: v / current_equity for s, v in existing_positions.items()},
            symbol: position_pct
        }
        
        portfolio_var = self.compute_portfolio_var(new_weights, all_symbols)
        
        if portfolio_var > p_var_limit:
            # Scale down to meet portfolio limit
            scale_factor = p_var_limit / portfolio_var
            position_pct *= scale_factor
            logger.info(f"Portfolio VaR limit applied ({regime}): scaled by {scale_factor:.2f}")
        
        # Step 4: Apply bounds
        position_pct = np.clip(
            position_pct,
            self.config.min_position_pct,
            self.config.max_position_pct
        )
        
        position_value = current_equity * position_pct
        
        return {
            'symbol': symbol,
            'position_pct': position_pct,
            'position_value': position_value,
            'kelly_recommendation': kelly['position_pct'],
            'var_constrained': position_pct < kelly['position_pct'],
            'symbol_var': symbol_var,
            'portfolio_var': portfolio_var,
            'risk_amount': position_value * avg_loss,
            'expected_return': position_value * (win_rate * avg_win - (1 - win_rate) * avg_loss)
        }
    
    def get_portfolio_summary(self, positions: Dict[str, float], equity: float) -> Dict:
        """
        Get portfolio risk summary.
        
        Args:
            positions: {symbol: position_value}
            equity: Total equity
        
        Returns:
            Risk metrics summary
        """
        weights = {s: v / equity for s, v in positions.items()}
        symbols = list(positions.keys())
        
        portfolio_var = self.compute_portfolio_var(weights, symbols)
        
        # Individual VaRs
        individual_vars = {
            sym: self.compute_var(np.array(self.returns_history.get(sym, [0] * 30)))
            for sym in symbols
        }
        
        # Diversification benefit
        gross_var = sum(individual_vars.values())
        diversification_benefit = (gross_var - portfolio_var) / gross_var if gross_var > 0 else 0
        
        return {
            'portfolio_var': portfolio_var,
            'portfolio_var_limit': self.config.portfolio_var_limit,
            'var_utilization': portfolio_var / self.config.portfolio_var_limit,
            'individual_vars': individual_vars,
            'diversification_benefit': diversification_benefit,
            'total_exposure': sum(abs(v) for v in positions.values()) / equity,
            'n_positions': len(positions)
        }
    
    def save_state(self, path: str):
        """Save state to disk."""
        import json
        state = {
            'returns_history': {k: v[-100:] for k, v in self.returns_history.items()},
            'config': {
                'kelly_fraction': self.config.kelly_fraction,
                'max_position_pct': self.config.max_position_pct,
                'portfolio_var_limit': self.config.portfolio_var_limit
            }
        }
        with open(path, 'w') as f:
            json.dump(state, f)
        logger.info(f"💾 Kelly+VaR state saved to {path}")
    
    def load_state(self, path: str):
        """Load state from disk."""
        import json
        with open(path, 'r') as f:
            state = json.load(f)
        self.returns_history = state['returns_history']
        logger.info(f"📂 Kelly+VaR state loaded from {path}")


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    # Initialize
    sizer = PortfolioKellyVaR()
    
    # Simulate some returns history
    np.random.seed(42)
    for sym in ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']:
        for _ in range(100):
            sizer.update_returns(sym, np.random.normal(0.001, 0.03))
    
    # Size a new position
    result = sizer.size_position(
        symbol='BTCUSDT',
        win_rate=0.65,
        avg_win=0.04,
        avg_loss=0.02,
        current_equity=100000,
        existing_positions={'ETHUSDT': 10000}
    )
    
    print(f"\nPosition Sizing Result:")
    print(f"  Position: {result['position_pct']:.2%} (${result['position_value']:,.2f})")
    print(f"  Kelly would suggest: {result['kelly_recommendation']:.2%}")
    print(f"  VaR constrained: {result['var_constrained']}")
    print(f"  Portfolio VaR: {result['portfolio_var']:.2%}")
    
    print("\n✅ Portfolio Kelly+VaR v1.2 IMPLEMENTATION COMPLETE")
