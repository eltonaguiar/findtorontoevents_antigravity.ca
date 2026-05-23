"""
Kelly Position Sizing - Integration Example
============================================

This example shows how to integrate the Kelly position sizing module
into your multi-asset algorithmic trading system.
"""

from kelly_position_sizing import (
    KellyPositionSizer,
    KellyInputs,
    AssetConfig,
    AssetClass,
    calculate_position_size_kelly,
    calculate_position_size_simple
)

# =============================================================================
# EXAMPLE 1: Your Crypto Battleground System
# =============================================================================

def size_crypto_position(symbol: str, account_equity: float, 
                         current_price: float, atr_14: float) -> dict:
    """
    Size a position for your crypto battleground system.

    Your system stats:
    - Win Rate: 62.4%
    - Avg PnL: +0.52% per trade
    - Target Risk: 1% per trade
    - Kelly Fraction: 0.5x (Half Kelly for safety)
    """

    # Derive avg win/loss from your stats
    # Assuming avg win ≈ 1.5%, avg loss ≈ 0.8% based on win rate and avg PnL
    win_rate = 0.624
    avg_win_pct = 0.0152  # Derived from +0.52% avg PnL
    avg_loss_pct = 0.008

    result = calculate_position_size_kelly(
        account_equity=account_equity,
        atr_14=atr_14,
        current_price=current_price,
        win_rate=win_rate,
        avg_win_pct=avg_win_pct,
        avg_loss_pct=avg_loss_pct,
        symbol=symbol,
        stop_atr_mult=2.0,
        kelly_fraction=0.5,  # Half Kelly
        target_risk_pct=0.01,  # 1% risk per trade
        max_position_pct=0.20  # 20% max position
    )

    return {
        'symbol': symbol,
        'dollar_size': result.dollar_size,
        'quantity': result.quantity,
        'risk_amount': result.risk_amount,
        'risk_pct': result.risk_pct_of_equity,
        'stop_price': result.stop_price,
        'position_pct': result.position_pct_of_equity
    }


# Example usage for BTC
btc_position = size_crypto_position(
    symbol="BTC-USD",
    account_equity=100000,
    current_price=45000.0,
    atr_14=1500.0
)

print("Crypto Battleground System - BTC Position:")
print(f"  Dollar Size: ${btc_position['dollar_size']:,.2f}")
print(f"  Quantity: {btc_position['quantity']:.4f} BTC")
print(f"  Risk: ${btc_position['risk_amount']:,.2f} ({btc_position['risk_pct']:.2%})")
print(f"  Stop Price: ${btc_position['stop_price']:,.2f}")


# =============================================================================
# EXAMPLE 2: Multi-Asset Portfolio Sizing
# =============================================================================

def size_portfolio_positions(account_equity: float, signals: list) -> list:
    """
    Size positions for a multi-asset portfolio.

    Args:
        account_equity: Total account equity
        signals: List of dicts with 'symbol', 'price', 'atr', 'win_rate', etc.

    Returns:
        List of sized positions
    """
    sizer = KellyPositionSizer()
    positions = []

    for signal in signals:
        symbol = signal['symbol']
        price = signal['price']
        atr = signal['atr']

        # Get asset config
        asset_config = AssetConfig.from_symbol(symbol)

        # Create inputs
        inputs = KellyInputs(
            account_equity=account_equity,
            atr_14=atr,
            current_price=price,
            win_rate=signal.get('win_rate', 0.55),
            avg_win_pct=signal.get('avg_win_pct', 0.02),
            avg_loss_pct=signal.get('avg_loss_pct', 0.01),
            stop_atr_mult=2.0,
            kelly_fraction=0.5,
            target_risk_pct=0.01,
            max_position_pct=0.20
        )

        # Calculate position
        result = sizer.calculate_position_size(inputs, asset_config)

        positions.append({
            'symbol': symbol,
            'asset_class': asset_config.asset_class.value,
            'dollar_size': result.dollar_size,
            'quantity': result.quantity,
            'risk_amount': result.risk_amount,
            'risk_pct': result.risk_pct_of_equity,
            'stop_price': result.stop_price
        })

    return positions


# Example signals
signals = [
    {'symbol': 'SPY', 'price': 450.0, 'atr': 2.5, 'win_rate': 0.58},
    {'symbol': 'QQQ', 'price': 380.0, 'atr': 3.2, 'win_rate': 0.56},
    {'symbol': 'JPM', 'price': 150.0, 'atr': 2.1, 'win_rate': 0.54},
    {'symbol': 'BTC-USD', 'price': 45000.0, 'atr': 1500.0, 'win_rate': 0.624},
    {'symbol': 'ETH-USD', 'price': 3000.0, 'atr': 120.0, 'win_rate': 0.60},
    {'symbol': 'CL=F', 'price': 75.0, 'atr': 1.5, 'win_rate': 0.52},
    {'symbol': 'GC=F', 'price': 2000.0, 'atr': 25.0, 'win_rate': 0.51},
]

portfolio = size_portfolio_positions(100000, signals)

print("\nMulti-Asset Portfolio:")
print("-" * 80)
for pos in portfolio:
    print(f"{pos['symbol']:10} | {pos['asset_class']:8} | "
          f"${pos['dollar_size']:>10,.2f} | Qty: {pos['quantity']:>10.4f} | "
          f"Risk: {pos['risk_pct']:>6.2%}")


# =============================================================================
# EXAMPLE 3: Simple Volatility-Adjusted Sizing (No Kelly)
# =============================================================================

def size_by_volatility_only(account_equity: float, price: float, 
                            atr: float, symbol: str) -> dict:
    """
    Size position purely by volatility (no Kelly adjustment).
    Use this when you don't have reliable win rate statistics.
    """
    result = calculate_position_size_simple(
        account_equity=account_equity,
        atr_14=atr,
        current_price=price,
        symbol=symbol,
        target_risk_pct=0.01,  # 1% risk
        stop_atr_mult=2.0,
        max_position_pct=0.20
    )

    return {
        'dollar_size': result.dollar_size,
        'quantity': result.quantity,
        'risk_amount': result.risk_amount,
        'risk_pct': result.risk_pct_of_equity,
        'stop_price': result.stop_price
    }


# Example for a new strategy without proven edge
new_strategy_position = size_by_volatility_only(
    account_equity=100000,
    price=150.0,
    atr=3.0,
    symbol="IWM"
)

print("\nVolatility-Only Sizing (New Strategy):")
print(f"  Dollar Size: ${new_strategy_position['dollar_size']:,.2f}")
print(f"  Quantity: {new_strategy_position['quantity']:.0f} shares")
print(f"  Risk: ${new_strategy_position['risk_amount']:,.2f}")


# =============================================================================
# EXAMPLE 4: Batch Processing for Live Trading
# =============================================================================

class PositionSizingEngine:
    """
    Production-ready position sizing engine for live trading.
    """

    def __init__(self, 
                 default_kelly_fraction: float = 0.5,
                 default_target_risk: float = 0.01,
                 default_max_position: float = 0.20):

        self.sizer = KellyPositionSizer(
            default_kelly_fraction=default_kelly_fraction,
            default_target_risk_pct=default_target_risk,
            default_max_position_pct=default_max_position
        )

        # Strategy-specific Kelly fractions
        self.strategy_kelly = {
            'crypto_battleground': 0.5,  # Your proven system
            'momentum_etfs': 0.3,
            'mean_reversion': 0.25,
            'new_strategy': 0.0  # No Kelly until proven
        }

    def size_signal(self, signal: dict, account_equity: float) -> dict:
        """
        Size a single trading signal.

        Expected signal format:
        {
            'symbol': 'BTC-USD',
            'price': 45000.0,
            'atr_14': 1500.0,
            'strategy': 'crypto_battleground',
            'win_rate': 0.624,  # Optional
            'avg_win_pct': 0.0152,  # Optional
            'avg_loss_pct': 0.008  # Optional
        }
        """
        symbol = signal['symbol']
        strategy = signal.get('strategy', 'default')

        # Get Kelly fraction for this strategy
        kelly_frac = self.strategy_kelly.get(strategy, 0.25)

        # Get asset config
        asset_config = AssetConfig.from_symbol(symbol)

        # Build inputs
        inputs = KellyInputs(
            account_equity=account_equity,
            atr_14=signal['atr_14'],
            current_price=signal['price'],
            win_rate=signal.get('win_rate', 0.55),
            avg_win_pct=signal.get('avg_win_pct', 0.02),
            avg_loss_pct=signal.get('avg_loss_pct', 0.01),
            kelly_fraction=kelly_frac
        )

        # Calculate
        result = self.sizer.calculate_position_size(inputs, asset_config)

        return {
            'symbol': symbol,
            'action': signal.get('action', 'BUY'),
            'quantity': result.quantity,
            'dollar_size': result.dollar_size,
            'stop_price': result.stop_price,
            'risk_amount': result.risk_amount,
            'risk_pct': result.risk_pct_of_equity,
            'kelly_fraction': result.kelly_fraction_used
        }

    def size_signals(self, signals: list, account_equity: float) -> list:
        """Size multiple signals."""
        return [self.size_signal(s, account_equity) for s in signals]


# Usage
engine = PositionSizingEngine()

live_signals = [
    {
        'symbol': 'BTC-USD',
        'price': 45000.0,
        'atr_14': 1500.0,
        'strategy': 'crypto_battleground',
        'action': 'BUY',
        'win_rate': 0.624,
        'avg_win_pct': 0.0152,
        'avg_loss_pct': 0.008
    },
    {
        'symbol': 'SPY',
        'price': 450.0,
        'atr_14': 2.5,
        'strategy': 'momentum_etfs',
        'action': 'BUY',
        'win_rate': 0.58,
        'avg_win_pct': 0.018,
        'avg_loss_pct': 0.012
    },
    {
        'symbol': 'SOL-USD',
        'price': 100.0,
        'atr_14': 5.0,
        'strategy': 'new_strategy',
        'action': 'BUY'
    }
]

sized_positions = engine.size_signals(live_signals, account_equity=100000)

print("\nLive Trading - Sized Signals:")
print("-" * 80)
for pos in sized_positions:
    print(f"{pos['action']:4} {pos['quantity']:>10.4f} {pos['symbol']:10} "
          f"@ ${pos['dollar_size']:>12,.2f} | Stop: ${pos['stop_price']:,.2f} "
          f"| Kelly: {pos['kelly_fraction']:.2%}")


# =============================================================================
# EXAMPLE 5: Risk Monitoring
# =============================================================================

def calculate_portfolio_risk(positions: list, account_equity: float) -> dict:
    """
    Calculate total portfolio risk from sized positions.
    """
    total_risk = sum(p['risk_amount'] for p in positions)
    total_exposure = sum(p['dollar_size'] for p in positions)

    return {
        'total_risk_dollars': total_risk,
        'total_risk_pct': total_risk / account_equity,
        'total_exposure_dollars': total_exposure,
        'total_exposure_pct': total_exposure / account_equity,
        'num_positions': len(positions),
        'account_equity': account_equity
    }


risk_summary = calculate_portfolio_risk(sized_positions, 100000)

print("\nPortfolio Risk Summary:")
print(f"  Total Risk: ${risk_summary['total_risk_dollars']:,.2f} "
      f"({risk_summary['total_risk_pct']:.2%})")
print(f"  Total Exposure: ${risk_summary['total_exposure_dollars']:,.2f} "
      f"({risk_summary['total_exposure_pct']:.2%})")
print(f"  Positions: {risk_summary['num_positions']}")

if risk_summary['total_risk_pct'] > 0.05:
    print("  ⚠️ WARNING: Total risk exceeds 5% of account!")
