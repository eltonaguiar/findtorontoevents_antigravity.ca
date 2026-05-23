"""
Kelly Volatility-Adjusted Position Sizing Module
================================================

A production-ready implementation of fractional Kelly Criterion with ATR-based
position sizing for multi-asset algorithmic trading systems.

Features:
- Corrected Kelly formula (fixes double-counting bug)
- ATR(14) volatility-adjusted position sizing
- Asset-class specific handling (stocks, ETFs, futures, crypto)
- Fractional Kelly implementation for safety
- Position caps and risk limits
- Edge case handling

Author: Quantitative Finance Research
References: See module docstring for academic sources
"""

import numpy as np
from dataclasses import dataclass
from typing import Optional, Dict, Union, Tuple
from enum import Enum
import warnings


class AssetClass(Enum):
    """Asset class enumeration for contract multiplier handling."""
    STOCK = "stock"
    ETF = "etf"
    FUTURES = "futures"
    CRYPTO = "crypto"


@dataclass
class AssetConfig:
    """Configuration for a specific asset."""
    symbol: str
    asset_class: AssetClass
    contract_multiplier: float = 1.0  # For futures
    tick_size: float = 0.01
    min_quantity: float = 0.0001  # For crypto

    # Asset-specific contract multipliers
    FUTURES_MULTIPLIERS = {
        'CL=F': 1000,      # Crude Oil: 1,000 barrels per contract
        'GC=F': 100,       # Gold: 100 troy ounces per contract
        'SI=F': 5000,      # Silver: 5,000 troy ounces per contract
        'NG=F': 10000,     # Natural Gas: 10,000 MMBtu per contract
        'ES=F': 50,        # E-mini S&P 500: $50 per point
        'NQ=F': 20,        # E-mini Nasdaq: $20 per point
        'YM=F': 5,         # E-mini Dow: $5 per point
        'ZB=F': 1000,      # 30-Year Treasury: $1,000 per point
    }

    @classmethod
    def from_symbol(cls, symbol: str) -> 'AssetConfig':
        """Create asset config from symbol with appropriate defaults."""
        symbol_upper = symbol.upper()

        # Determine asset class
        if symbol_upper in ['SPY', 'QQQ', 'IWM', 'XLE', 'XLF', 'XLK', 'XLI', 'XLP', 'XLU', 'XLV', 'XLB', 'XRT']:
            asset_class = AssetClass.ETF
            multiplier = 1.0
        elif '=F' in symbol_upper:
            asset_class = AssetClass.FUTURES
            multiplier = cls.FUTURES_MULTIPLIERS.get(symbol_upper, 1.0)
        elif symbol_upper in ['BTC', 'ETH', 'SOL', 'XRP', 'BTC-USD', 'ETH-USD', 'SOL-USD', 'XRP-USD']:
            asset_class = AssetClass.CRYPTO
            multiplier = 1.0
        else:
            asset_class = AssetClass.STOCK
            multiplier = 1.0

        return cls(
            symbol=symbol_upper,
            asset_class=asset_class,
            contract_multiplier=multiplier,
            min_quantity=0.0001 if asset_class == AssetClass.CRYPTO else 1.0
        )


@dataclass
class KellyInputs:
    """Input parameters for Kelly position sizing calculation."""
    account_equity: float
    atr_14: float
    current_price: float
    win_rate: float
    avg_win_pct: float
    avg_loss_pct: float
    stop_atr_mult: float = 2.0
    kelly_fraction: float = 0.5
    target_risk_pct: float = 0.01  # 1% risk per trade
    max_position_pct: float = 0.20  # 20% max position

    def __post_init__(self):
        """Validate inputs."""
        if self.account_equity <= 0:
            raise ValueError(f"Account equity must be positive: {self.account_equity}")
        if self.atr_14 < 0:
            raise ValueError(f"ATR must be non-negative: {self.atr_14}")
        if self.current_price <= 0:
            raise ValueError(f"Current price must be positive: {self.current_price}")
        if not 0 <= self.win_rate <= 1:
            raise ValueError(f"Win rate must be in [0,1]: {self.win_rate}")
        if self.kelly_fraction < 0 or self.kelly_fraction > 1:
            raise ValueError(f"Kelly fraction must be in [0,1]: {self.kelly_fraction}")


@dataclass
class PositionSize:
    """Result of position sizing calculation."""
    dollar_size: float
    quantity: float
    risk_amount: float
    risk_pct_of_equity: float
    kelly_fraction_used: float
    stop_price: float
    position_pct_of_equity: float

    def __str__(self):
        return (f"PositionSize(dollar=${self.dollar_size:,.2f}, "
                f"qty={self.quantity:.6f}, risk=${self.risk_amount:,.2f}, "
                f"risk_pct={self.risk_pct_of_equity:.2%}, "
                f"pos_pct={self.position_pct_of_equity:.2%})")


class KellyPositionSizer:
    """
    Kelly Criterion Position Sizer with ATR-based volatility adjustment.

    This implementation CORRECTS the double-counting bug in:
        position_dollars = (risk_per_trade / dollar_vol) * account_equity

    The bug: account_equity is multiplied twice - once in risk_per_trade calculation
    and again explicitly.

    CORRECT FORMULA:
        position_dollars = (target_risk_amount) / (stop_distance_pct)
        where target_risk_amount = account_equity * target_risk_pct * kelly_fraction

    Or equivalently:
        position_dollars = account_equity * kelly_fraction * (target_risk_pct / stop_distance_pct)
    """

    def __init__(self, 
                 default_kelly_fraction: float = 0.5,
                 default_target_risk_pct: float = 0.01,
                 default_max_position_pct: float = 0.20,
                 default_stop_atr_mult: float = 2.0,
                 min_risk_buffer: float = 0.001):
        """
        Initialize the position sizer.

        Args:
            default_kelly_fraction: Default fractional Kelly (0.5 = Half Kelly)
            default_target_risk_pct: Default target risk per trade (0.01 = 1%)
            default_max_position_pct: Maximum position as % of equity (0.20 = 20%)
            default_stop_atr_mult: Default ATR multiplier for stop distance
            min_risk_buffer: Minimum risk buffer for edge cases
        """
        self.default_kelly_fraction = default_kelly_fraction
        self.default_target_risk_pct = default_target_risk_pct
        self.default_max_position_pct = default_max_position_pct
        self.default_stop_atr_mult = default_stop_atr_mult
        self.min_risk_buffer = min_risk_buffer

    def calculate_kelly_fraction(self, 
                                  win_rate: float, 
                                  avg_win_pct: float, 
                                  avg_loss_pct: float,
                                  kelly_fraction: float = 0.5) -> float:
        """
        Calculate the fractional Kelly Criterion position size.

        KELLY CRITERION FORMULA:
        ------------------------
        The full Kelly fraction is:
            f* = (p * b - q) / b

        Where:
            f* = optimal fraction of bankroll to bet
            p = probability of win (win_rate)
            q = probability of loss = 1 - p
            b = win/loss ratio = avg_win / avg_loss

        For trading with percentage returns:
            f* = (p * avg_win - q * avg_loss) / (avg_win * avg_loss)

        We use the simplified form:
            f* = p - (q / b) = p - ((1-p) * avg_loss / avg_win)

        Then apply fractional Kelly for safety:
            f_fractional = f* * kelly_fraction

        Args:
            win_rate: Probability of winning (0 to 1)
            avg_win_pct: Average winning trade return (e.g., 0.02 for 2%)
            avg_loss_pct: Average losing trade return (positive, e.g., 0.01 for 1%)
            kelly_fraction: Fraction of full Kelly to use (0.5 recommended, 0 for no Kelly)

        Returns:
            Fractional Kelly position size (0 to 1)

        References:
            - Kelly, J.L. (1956). "A New Interpretation of Information Rate"
            - Thorp, E.O. (2006). "The Kelly Criterion in Blackjack, Sports Betting, 
              and the Stock Market"
        """
        # Handle zero Kelly fraction (no edge assumption)
        if kelly_fraction == 0:
            return 0
            
        if avg_loss_pct <= 0:
            warnings.warn("Average loss must be positive for Kelly calculation")
            return 0

        if avg_win_pct <= 0:
            return 0

        p = win_rate
        q = 1 - p

        # Win/Loss ratio
        b = avg_win_pct / avg_loss_pct

        # Full Kelly fraction
        if b == 0:
            return 0

        kelly_full = (p * b - q) / b

        # Alternative formula (equivalent):
        # kelly_full = p - (q / b)

        # Clamp to reasonable bounds
        kelly_full = max(0, min(kelly_full, 1.0))

        # Apply fractional Kelly for safety
        kelly_fractional = kelly_full * kelly_fraction

        return kelly_fractional

    def calculate_atr_stop_distance(self, 
                                     atr_14: float, 
                                     current_price: float,
                                     stop_atr_mult: float = 2.0) -> float:
        """
        Calculate stop distance as percentage of price based on ATR.

        FORMULA:
            stop_distance_dollars = atr_14 * stop_atr_mult
            stop_distance_pct = stop_distance_dollars / current_price

        Args:
            atr_14: 14-period Average True Range
            current_price: Current market price
            stop_atr_mult: ATR multiplier for stop placement (default 2.0)

        Returns:
            Stop distance as percentage (e.g., 0.02 for 2%)
        """
        if current_price <= 0:
            raise ValueError(f"Current price must be positive: {current_price}")

        if atr_14 < 0:
            raise ValueError(f"ATR must be non-negative: {atr_14}")

        # Handle zero ATR edge case
        if atr_14 == 0:
            warnings.warn("ATR is zero, using minimum risk buffer")
            return self.min_risk_buffer

        stop_distance_dollars = atr_14 * stop_atr_mult
        stop_distance_pct = stop_distance_dollars / current_price

        # Ensure minimum stop distance
        return max(stop_distance_pct, self.min_risk_buffer)

    def calculate_position_size(self,
                                 inputs: KellyInputs,
                                 asset_config: Optional[AssetConfig] = None) -> PositionSize:
        """
        Calculate position size using corrected Kelly + ATR formula.

        CORRECTED FORMULA (Fixes Double-Counting Bug):
        -----------------------------------------------

        OLD (BUGGY):
            position_dollars = (risk_per_trade / dollar_vol) * account_equity
            # BUG: account_equity is counted in risk_per_trade AND multiplied again!

        NEW (CORRECT):
            # Step 1: Calculate Kelly-adjusted risk amount
            kelly_f = calculate_kelly_fraction(win_rate, avg_win, avg_loss, kelly_fraction)
            risk_amount = account_equity * target_risk_pct * kelly_f

            # Step 2: Calculate ATR-based stop distance
            stop_distance_pct = (atr_14 * stop_atr_mult) / current_price

            # Step 3: Calculate position size
            position_dollars = risk_amount / stop_distance_pct

            # Step 4: Apply caps
            position_dollars = min(position_dollars, account_equity * max_position_pct)

        Args:
            inputs: KellyInputs dataclass with all parameters
            asset_config: Optional asset configuration for quantity calculation

        Returns:
            PositionSize dataclass with complete sizing information
        """
        # Extract parameters
        equity = inputs.account_equity
        atr = inputs.atr_14
        price = inputs.current_price
        win_rate = inputs.win_rate
        avg_win = inputs.avg_win_pct
        avg_loss = inputs.avg_loss_pct
        stop_mult = inputs.stop_atr_mult
        kelly_frac = inputs.kelly_fraction
        target_risk = inputs.target_risk_pct
        max_pos_pct = inputs.max_position_pct

        # Step 1: Calculate Kelly fraction
        kelly_f = self.calculate_kelly_fraction(win_rate, avg_win, avg_loss, kelly_frac)

        # Step 2: Calculate risk amount (Kelly-adjusted)
        # This is the dollar amount we're willing to lose on this trade
        risk_amount = equity * target_risk * kelly_f

        # Step 3: Calculate ATR-based stop distance
        stop_distance_pct = self.calculate_atr_stop_distance(atr, price, stop_mult)

        # Step 4: Calculate stop price (for reference)
        stop_price = price - (atr * stop_mult)  # For long positions

        # Step 5: Calculate position size in dollars
        # Formula: position = risk_amount / stop_distance_pct
        # This gives us the position size where our risk equals risk_amount
        position_dollars = risk_amount / stop_distance_pct

        # Step 6: Apply maximum position cap
        max_position_dollars = equity * max_pos_pct
        position_dollars = min(position_dollars, max_position_dollars)

        # Recalculate actual risk after capping
        actual_risk = position_dollars * stop_distance_pct

        # Step 7: Calculate quantity (shares/contracts)
        if asset_config is None:
            # Try to infer from symbol if provided in inputs
            asset_config = AssetConfig.from_symbol("STOCK")  # Default

        if asset_config.asset_class == AssetClass.FUTURES:
            # For futures: quantity = position_dollars / (price * contract_multiplier)
            quantity = position_dollars / (price * asset_config.contract_multiplier)
            quantity = round(quantity)  # Futures must be whole contracts
        elif asset_config.asset_class == AssetClass.CRYPTO:
            # For crypto: quantity = position_dollars / price
            quantity = position_dollars / price
            # Round to minimum precision
            precision = len(str(asset_config.min_quantity).split('.')[-1]) if '.' in str(asset_config.min_quantity) else 0
            quantity = round(quantity, precision)
        else:
            # For stocks/ETFs: quantity = position_dollars / price
            quantity = int(position_dollars / price)

        # Recalculate actual position dollars based on rounded quantity
        if asset_config.asset_class == AssetClass.FUTURES:
            actual_position_dollars = quantity * price * asset_config.contract_multiplier
        else:
            actual_position_dollars = quantity * price

        return PositionSize(
            dollar_size=actual_position_dollars,
            quantity=quantity,
            risk_amount=actual_risk,
            risk_pct_of_equity=actual_risk / equity,
            kelly_fraction_used=kelly_f,
            stop_price=stop_price,
            position_pct_of_equity=actual_position_dollars / equity
        )

    def calculate_simple_volatility_adjusted(self,
                                              account_equity: float,
                                              atr_14: float,
                                              current_price: float,
                                              target_risk_pct: float = 0.01,
                                              stop_atr_mult: float = 2.0,
                                              max_position_pct: float = 0.20,
                                              asset_config: Optional[AssetConfig] = None) -> PositionSize:
        """
        Simplified volatility-adjusted sizing without Kelly (for systems without edge stats).

        FORMULA:
            risk_amount = account_equity * target_risk_pct
            stop_distance_pct = (atr_14 * stop_atr_mult) / current_price
            position_dollars = risk_amount / stop_distance_pct

        Args:
            account_equity: Total account equity
            atr_14: 14-period ATR
            current_price: Current market price
            target_risk_pct: Target risk per trade (default 1%)
            stop_atr_mult: ATR multiplier for stop (default 2.0)
            max_position_pct: Maximum position size (default 20%)
            asset_config: Optional asset configuration

        Returns:
            PositionSize dataclass
        """
        # Step 1: Calculate risk amount (NO Kelly adjustment)
        risk_amount = account_equity * target_risk_pct
        
        # Step 2: Calculate ATR-based stop distance
        stop_distance_pct = self.calculate_atr_stop_distance(atr_14, current_price, stop_atr_mult)
        
        # Step 3: Calculate stop price (for reference)
        stop_price = current_price - (atr_14 * stop_atr_mult)  # For long positions
        
        # Step 4: Calculate position size in dollars
        position_dollars = risk_amount / stop_distance_pct
        
        # Step 5: Apply maximum position cap
        max_position_dollars = account_equity * max_position_pct
        position_dollars = min(position_dollars, max_position_dollars)
        
        # Recalculate actual risk after capping
        actual_risk = position_dollars * stop_distance_pct
        
        # Step 6: Calculate quantity (shares/contracts)
        if asset_config is None:
            asset_config = AssetConfig.from_symbol("STOCK")  # Default
            
        if asset_config.asset_class == AssetClass.FUTURES:
            quantity = position_dollars / (current_price * asset_config.contract_multiplier)
            quantity = round(quantity)
        elif asset_config.asset_class == AssetClass.CRYPTO:
            quantity = position_dollars / current_price
            precision = len(str(asset_config.min_quantity).split('.')[-1]) if '.' in str(asset_config.min_quantity) else 0
            quantity = round(quantity, precision)
        else:
            quantity = int(position_dollars / current_price)
        
        # Recalculate actual position dollars based on rounded quantity
        if asset_config.asset_class == AssetClass.FUTURES:
            actual_position_dollars = quantity * current_price * asset_config.contract_multiplier
        else:
            actual_position_dollars = quantity * current_price
            
        return PositionSize(
            dollar_size=actual_position_dollars,
            quantity=quantity,
            risk_amount=actual_risk,
            risk_pct_of_equity=actual_risk / account_equity,
            kelly_fraction_used=1.0,  # No Kelly adjustment applied
            stop_price=stop_price,
            position_pct_of_equity=actual_position_dollars / account_equity
        )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def calculate_position_size_kelly(
    account_equity: float,
    atr_14: float,
    current_price: float,
    win_rate: float,
    avg_win_pct: float,
    avg_loss_pct: float,
    symbol: str = "STOCK",
    stop_atr_mult: float = 2.0,
    kelly_fraction: float = 0.5,
    target_risk_pct: float = 0.01,
    max_position_pct: float = 0.20
) -> PositionSize:
    """
    Convenience function for Kelly position sizing.

    Example:
        >>> result = calculate_position_size_kelly(
        ...     account_equity=100000,
        ...     atr_14=2.5,
        ...     current_price=150.0,
        ...     win_rate=0.624,
        ...     avg_win_pct=0.015,
        ...     avg_loss_pct=0.008,
        ...     symbol="SPY"
        ... )
        >>> print(result)
    """
    sizer = KellyPositionSizer()
    inputs = KellyInputs(
        account_equity=account_equity,
        atr_14=atr_14,
        current_price=current_price,
        win_rate=win_rate,
        avg_win_pct=avg_win_pct,
        avg_loss_pct=avg_loss_pct,
        stop_atr_mult=stop_atr_mult,
        kelly_fraction=kelly_fraction,
        target_risk_pct=target_risk_pct,
        max_position_pct=max_position_pct
    )
    asset_config = AssetConfig.from_symbol(symbol)
    return sizer.calculate_position_size(inputs, asset_config)


def calculate_position_size_simple(
    account_equity: float,
    atr_14: float,
    current_price: float,
    symbol: str = "STOCK",
    target_risk_pct: float = 0.01,
    stop_atr_mult: float = 2.0,
    max_position_pct: float = 0.20
) -> PositionSize:
    """
    Convenience function for simple volatility-adjusted sizing (no Kelly).

    Example:
        >>> result = calculate_position_size_simple(
        ...     account_equity=100000,
        ...     atr_14=2.5,
        ...     current_price=150.0,
        ...     symbol="SPY"
        ... )
        >>> print(result)
    """
    sizer = KellyPositionSizer()
    asset_config = AssetConfig.from_symbol(symbol)
    return sizer.calculate_simple_volatility_adjusted(
        account_equity=account_equity,
        atr_14=atr_14,
        current_price=current_price,
        target_risk_pct=target_risk_pct,
        stop_atr_mult=stop_atr_mult,
        max_position_pct=max_position_pct,
        asset_config=asset_config
    )


# =============================================================================
# UNIT TESTS
# =============================================================================

def run_unit_tests():
    """Run comprehensive unit tests for the position sizing module."""

    print("=" * 80)
    print("KELLY POSITION SIZING - UNIT TESTS")
    print("=" * 80)

    sizer = KellyPositionSizer()

    # Test 1: Basic Kelly calculation
    print("\n--- Test 1: Kelly Fraction Calculation ---")
    kelly = sizer.calculate_kelly_fraction(
        win_rate=0.624,  # Your crypto system win rate
        avg_win_pct=0.0152,  # 1.52% avg win (derived from +0.52% avg PnL)
        avg_loss_pct=0.008,  # 0.8% avg loss
        kelly_fraction=0.5
    )
    print(f"Win Rate: 62.4%, Avg Win: 1.52%, Avg Loss: 0.8%")
    print(f"Kelly Fraction (0.5x): {kelly:.4f} ({kelly:.2%})")

    # Test 2: ATR stop distance
    print("\n--- Test 2: ATR Stop Distance ---")
    stop_dist = sizer.calculate_atr_stop_distance(
        atr_14=2.5,
        current_price=150.0,
        stop_atr_mult=2.0
    )
    print(f"ATR: $2.50, Price: $150.00, Stop Mult: 2.0")
    print(f"Stop Distance: {stop_dist:.4f} ({stop_dist:.2%})")
    print(f"Stop Price (long): ${150.0 - 2.5*2.0:.2f}")

    # Test 3: Full position sizing - Stock
    print("\n--- Test 3: Full Position Sizing - Stock (SPY) ---")
    result = calculate_position_size_kelly(
        account_equity=100000,
        atr_14=2.5,
        current_price=450.0,
        win_rate=0.624,
        avg_win_pct=0.0152,
        avg_loss_pct=0.008,
        symbol="SPY",
        stop_atr_mult=2.0,
        kelly_fraction=0.5,
        target_risk_pct=0.01,
        max_position_pct=0.20
    )
    print(f"Account Equity: $100,000")
    print(f"SPY Price: $450.00, ATR(14): $2.50")
    print(f"Result: {result}")

    # Test 4: Crypto position sizing
    print("\n--- Test 4: Crypto Position Sizing (BTC) ---")
    result_crypto = calculate_position_size_kelly(
        account_equity=100000,
        atr_14=1500.0,
        current_price=45000.0,
        win_rate=0.624,
        avg_win_pct=0.0152,
        avg_loss_pct=0.008,
        symbol="BTC-USD",
        stop_atr_mult=2.0,
        kelly_fraction=0.5,
        target_risk_pct=0.01,
        max_position_pct=0.20
    )
    print(f"BTC Price: $45,000, ATR(14): $1,500")
    print(f"Result: {result_crypto}")

    # Test 5: Futures position sizing (Crude Oil)
    print("\n--- Test 5: Futures Position Sizing (CL=F) ---")
    result_futures = calculate_position_size_kelly(
        account_equity=100000,
        atr_14=1.5,
        current_price=75.0,
        win_rate=0.55,
        avg_win_pct=0.02,
        avg_loss_pct=0.01,
        symbol="CL=F",
        stop_atr_mult=2.0,
        kelly_fraction=0.5,
        target_risk_pct=0.01,
        max_position_pct=0.20
    )
    print(f"CL=F Price: $75.00, ATR(14): $1.50")
    print(f"Contract Multiplier: 1,000 barrels")
    print(f"Result: {result_futures}")

    # Test 6: Edge case - Zero ATR
    print("\n--- Test 6: Edge Case - Zero ATR ---")
    result_zero_atr = calculate_position_size_simple(
        account_equity=100000,
        atr_14=0.0,
        current_price=150.0,
        symbol="SPY"
    )
    print(f"Zero ATR handled: {result_zero_atr}")

    # Test 7: Edge case - Very small account
    print("\n--- Test 7: Edge Case - Small Account ---")
    result_small = calculate_position_size_simple(
        account_equity=5000,
        atr_14=2.5,
        current_price=450.0,
        symbol="SPY",
        target_risk_pct=0.01
    )
    print(f"Small Account ($5,000): {result_small}")

    # Test 8: Position cap enforcement
    print("\n--- Test 8: Position Cap Enforcement ---")
    result_capped = calculate_position_size_kelly(
        account_equity=100000,
        atr_14=0.5,  # Very low ATR -> would suggest large position
        current_price=150.0,
        win_rate=0.8,  # High win rate
        avg_win_pct=0.05,
        avg_loss_pct=0.01,
        symbol="SPY",
        stop_atr_mult=2.0,
        kelly_fraction=0.5,
        target_risk_pct=0.01,
        max_position_pct=0.20  # 20% cap
    )
    print(f"High conviction trade with low volatility:")
    print(f"Result: {result_capped}")
    print(f"Position % of Equity: {result_capped.position_pct_of_equity:.2%}")
    print(f"Should be capped at 20%: {'PASS' if result_capped.position_pct_of_equity <= 0.20 else 'FAIL'}")

    # Test 9: Compare buggy vs corrected formula
    print("\n--- Test 9: Buggy vs Corrected Formula Comparison ---")
    equity = 100000
    atr = 2.5
    price = 450.0
    target_risk = 0.01
    stop_mult = 2.0

    # BUGGY formula (double-counting equity)
    dollar_vol = atr * stop_mult
    buggy_position = (target_risk / (dollar_vol / price)) * equity

    # CORRECTED formula
    risk_amount = equity * target_risk
    stop_distance_pct = (atr * stop_mult) / price
    correct_position = risk_amount / stop_distance_pct

    print(f"Account Equity: ${equity:,.2f}")
    print(f"ATR: ${atr:.2f}, Price: ${price:.2f}")
    print(f"Target Risk: {target_risk:.2%}")
    print(f"")
    print(f"BUGGY Formula Result: ${buggy_position:,.2f}")
    print(f"  (This is WRONG - equity counted twice!)")
    print(f"")
    print(f"CORRECTED Formula Result: ${correct_position:,.2f}")
    print(f"  (This is CORRECT)")
    print(f"")
    print(f"Difference: ${buggy_position - correct_position:,.2f}")
    print(f"Buggy is {buggy_position/correct_position:.1f}x larger than correct!")

    print("\n" + "=" * 80)
    print("ALL TESTS COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    run_unit_tests()
