"""
Transaction Cost Model Integration Guide
========================================
Integration examples for portfolio management systems.

This module demonstrates how to integrate the TransactionCostModel
with your existing portfolio manager for post-commission PnL tracking.
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from transaction_cost_model import (
    TransactionCostModel,
    TradeDetails,
    AssetClass,
    OrderType,
    PositionPnL,
    CostBreakdown,
    create_retail_stock_config,
    create_retail_crypto_config,
    create_retail_futures_config,
    create_cost_model_from_current
)


# =============================================================================
# PORTFOLIO MANAGER INTEGRATION
# =============================================================================

@dataclass
class PortfolioPosition:
    """Enhanced position with cost tracking."""
    symbol: str
    asset_class: AssetClass
    quantity: float
    avg_entry_price: float
    market_price: float
    entry_time: datetime = field(default_factory=datetime.now)
    
    # Cost tracking
    entry_cost: float = 0.0
    accumulated_costs: float = 0.0
    
    @property
    def market_value(self) -> float:
        """Current market value."""
        return self.quantity * self.market_price
    
    @property
    def cost_basis(self) -> float:
        """Total cost basis including transaction costs."""
        return (self.quantity * self.avg_entry_price) + self.entry_cost + self.accumulated_costs
    
    @property
    def gross_unrealized_pnl(self) -> float:
        """Gross unrealized PnL (before costs)."""
        return self.quantity * (self.market_price - self.avg_entry_price)
    
    @property
    def net_unrealized_pnl(self) -> float:
        """Net unrealized PnL (after costs)."""
        return self.market_value - self.cost_basis
    
    @property
    def unrealized_return_pct(self) -> float:
        """Unrealized return percentage."""
        if self.cost_basis == 0:
            return 0.0
        return (self.net_unrealized_pnl / self.cost_basis) * 100


class CostAwarePortfolioManager:
    """
    Portfolio manager with integrated transaction cost tracking.
    
    This class demonstrates how to integrate the TransactionCostModel
    into your existing portfolio management system.
    """
    
    def __init__(self, cost_model: Optional[TransactionCostModel] = None):
        """
        Initialize the portfolio manager.
        
        Args:
            cost_model: TransactionCostModel instance. If None, uses defaults.
        """
        self.cost_model = cost_model or TransactionCostModel()
        self.positions: Dict[str, PortfolioPosition] = {}
        self.closed_trades: List[PositionPnL] = []
        self._cash_balance: float = 0.0
        
    @property
    def cash(self) -> float:
        """Current cash balance."""
        return self._cash_balance
    
    @property
    def total_market_value(self) -> float:
        """Total market value of all positions."""
        return sum(pos.market_value for pos in self.positions.values())
    
    @property
    def total_cost_basis(self) -> float:
        """Total cost basis including transaction costs."""
        return sum(pos.cost_basis for pos in self.positions.values())
    
    @property
    def gross_unrealized_pnl(self) -> float:
        """Total gross unrealized PnL."""
        return sum(pos.gross_unrealized_pnl for pos in self.positions.values())
    
    @property
    def net_unrealized_pnl(self) -> float:
        """Total net unrealized PnL (after costs)."""
        return sum(pos.net_unrealized_pnl for pos in self.positions.values())
    
    @property
    def total_equity(self) -> float:
        """Total equity (cash + positions)."""
        return self._cash_balance + self.total_market_value
    
    def deposit(self, amount: float) -> None:
        """Deposit cash into the portfolio."""
        self._cash_balance += amount
    
    def enter_position(
        self,
        symbol: str,
        asset_class: AssetClass,
        quantity: float,
        price: float,
        volume_24h: Optional[float] = None,
        volatility: Optional[float] = None,
        timestamp: Optional[datetime] = None
    ) -> Dict[str, float]:
        """
        Enter a new position with cost tracking.
        
        Args:
            symbol: Trading symbol
            asset_class: Asset class
            quantity: Position size (positive for long)
            price: Entry price
            volume_24h: 24h volume for slippage estimation
            volatility: Annualized volatility
            timestamp: Entry timestamp
        
        Returns:
            Dictionary with trade details and costs
        """
        if quantity <= 0:
            raise ValueError("Quantity must be positive for entry")
        
        timestamp = timestamp or datetime.now()
        
        # Calculate entry costs
        trade = TradeDetails(
            symbol=symbol,
            asset_class=asset_class,
            quantity=quantity,
            price=price,
            volume_24h=volume_24h,
            volatility=volatility
        )
        
        commission = self.cost_model.calculate_commission(trade)
        slippage = self.cost_model.estimate_slippage(trade)
        impact = self.cost_model.calculate_market_impact(trade)
        
        total_entry_cost = commission + slippage + impact
        notional = quantity * price
        
        # Check if we have enough cash
        total_required = notional + total_entry_cost
        if total_required > self._cash_balance:
            raise ValueError(
                f"Insufficient funds. Required: ${total_required:,.2f}, "
                f"Available: ${self._cash_balance:,.2f}"
            )
        
        # Deduct cash
        self._cash_balance -= total_required
        
        # Create or update position
        if symbol in self.positions:
            # Average into existing position
            existing = self.positions[symbol]
            total_qty = existing.quantity + quantity
            total_cost = (existing.quantity * existing.avg_entry_price + 
                         existing.entry_cost + quantity * price + total_entry_cost)
            
            existing.quantity = total_qty
            existing.avg_entry_price = total_cost / total_qty
            existing.entry_cost += total_entry_cost
            existing.entry_time = timestamp
        else:
            # New position
            self.positions[symbol] = PortfolioPosition(
                symbol=symbol,
                asset_class=asset_class,
                quantity=quantity,
                avg_entry_price=price,
                market_price=price,
                entry_time=timestamp,
                entry_cost=total_entry_cost,
                accumulated_costs=0.0
            )
        
        return {
            'symbol': symbol,
            'quantity': quantity,
            'price': price,
            'notional': notional,
            'commission': commission,
            'slippage': slippage,
            'market_impact': impact,
            'total_cost': total_entry_cost,
            'cash_remaining': self._cash_balance
        }
    
    def exit_position(
        self,
        symbol: str,
        quantity: Optional[float] = None,
        price: Optional[float] = None,
        volume_24h: Optional[float] = None,
        volatility: Optional[float] = None,
        timestamp: Optional[datetime] = None
    ) -> Dict[str, float]:
        """
        Exit a position with cost tracking.
        
        Args:
            symbol: Symbol to exit
            quantity: Quantity to exit (None = full position)
            price: Exit price (None = use market price)
            volume_24h: 24h volume for slippage
            volatility: Annualized volatility
            timestamp: Exit timestamp
        
        Returns:
            Dictionary with PnL details
        """
        if symbol not in self.positions:
            raise ValueError(f"No position found for {symbol}")
        
        position = self.positions[symbol]
        timestamp = timestamp or datetime.now()
        
        # Determine exit quantity and price
        exit_qty = quantity if quantity is not None else position.quantity
        exit_price = price if price is not None else position.market_price
        
        if exit_qty > position.quantity:
            raise ValueError(f"Cannot exit more than position size ({position.quantity})")
        
        # Calculate exit costs
        exit_trade = TradeDetails(
            symbol=symbol,
            asset_class=position.asset_class,
            quantity=-exit_qty,  # Negative for sell
            price=exit_price,
            volume_24h=volume_24h,
            volatility=volatility
        )
        
        exit_commission = self.cost_model.calculate_commission(exit_trade)
        exit_slippage = self.cost_model.estimate_slippage(exit_trade)
        exit_impact = self.cost_model.calculate_market_impact(exit_trade)
        exit_cost = exit_commission + exit_slippage + exit_impact
        
        # Calculate PnL
        exit_notional = exit_qty * exit_price
        entry_notional = exit_qty * position.avg_entry_price
        
        # Pro-rata entry costs
        pro_rata_entry_cost = (exit_qty / position.quantity) * position.entry_cost
        pro_rata_accumulated = (exit_qty / position.quantity) * position.accumulated_costs
        
        gross_pnl = exit_notional - entry_notional
        total_costs = pro_rata_entry_cost + pro_rata_accumulated + exit_cost
        net_pnl = gross_pnl - total_costs
        
        # Add proceeds to cash (minus exit costs)
        self._cash_balance += exit_notional - exit_cost
        
        # Record closed trade
        closed_trade = PositionPnL(
            symbol=symbol,
            quantity=exit_qty,
            entry_price=position.avg_entry_price,
            exit_price=exit_price,
            entry_time=position.entry_time,
            exit_time=timestamp,
            entry_cost=CostBreakdown(
                commission=pro_rata_entry_cost,
                slippage=0,  # Combined in entry_cost
                market_impact=0,
                fees=0,
                total_cost=pro_rata_entry_cost
            ),
            exit_cost=CostBreakdown(
                commission=exit_commission,
                slippage=exit_slippage,
                market_impact=exit_impact,
                fees=0,
                total_cost=exit_cost
            )
        )
        self.closed_trades.append(closed_trade)
        
        # Update or remove position
        if exit_qty >= position.quantity:
            del self.positions[symbol]
        else:
            position.quantity -= exit_qty
            position.entry_cost -= pro_rata_entry_cost
            position.accumulated_costs -= pro_rata_accumulated
        
        return {
            'symbol': symbol,
            'quantity': exit_qty,
            'entry_price': position.avg_entry_price if symbol in self.positions else 0,
            'exit_price': exit_price,
            'gross_pnl': gross_pnl,
            'entry_cost': pro_rata_entry_cost,
            'exit_cost': exit_cost,
            'total_costs': total_costs,
            'net_pnl': net_pnl,
            'return_pct': (net_pnl / entry_notional * 100) if entry_notional > 0 else 0,
            'cash_balance': self._cash_balance
        }
    
    def update_prices(self, prices: Dict[str, float]) -> None:
        """Update market prices for positions."""
        for symbol, price in prices.items():
            if symbol in self.positions:
                self.positions[symbol].market_price = price
    
    def get_position_summary(self) -> pd.DataFrame:
        """Get summary of all open positions."""
        if not self.positions:
            return pd.DataFrame()
        
        data = []
        for pos in self.positions.values():
            data.append({
                'Symbol': pos.symbol,
                'Asset Class': pos.asset_class.name,
                'Quantity': pos.quantity,
                'Avg Entry': f"${pos.avg_entry_price:,.2f}",
                'Market Price': f"${pos.market_price:,.2f}",
                'Market Value': f"${pos.market_value:,.2f}",
                'Cost Basis': f"${pos.cost_basis:,.2f}",
                'Gross PnL': f"${pos.gross_unrealized_pnl:,.2f}",
                'Net PnL': f"${pos.net_unrealized_pnl:,.2f}",
                'Return %': f"{pos.unrealized_return_pct:.2f}%"
            })
        
        return pd.DataFrame(data)
    
    def get_closed_trades_summary(self) -> pd.DataFrame:
        """Get summary of all closed trades."""
        if not self.closed_trades:
            return pd.DataFrame()
        
        data = []
        for trade in self.closed_trades:
            data.append({
                'Symbol': trade.symbol,
                'Quantity': trade.quantity,
                'Entry Price': f"${trade.entry_price:,.2f}",
                'Exit Price': f"${trade.exit_price:,.2f}" if trade.exit_price else "N/A",
                'Gross PnL': f"${trade.gross_pnl:,.2f}",
                'Total Costs': f"${trade.total_costs:,.2f}",
                'Net PnL': f"${trade.net_pnl:,.2f}",
                'Cost Drag': f"{trade.cost_drag_pct:.1f}%"
            })
        
        return pd.DataFrame(data)
    
    def get_portfolio_summary(self) -> Dict[str, float]:
        """Get high-level portfolio summary."""
        return {
            'cash': self._cash_balance,
            'market_value': self.total_market_value,
            'total_equity': self.total_equity,
            'gross_unrealized_pnl': self.gross_unrealized_pnl,
            'net_unrealized_pnl': self.net_unrealized_pnl,
            'num_positions': len(self.positions),
            'num_closed_trades': len(self.closed_trades),
            'total_closed_pnl': sum(t.net_pnl for t in self.closed_trades)
        }


# =============================================================================
# MIGRATION FROM EXISTING SYSTEM
# =============================================================================

def migrate_from_legacy_cost_model(
    legacy_percentage: float = 0.001,
    legacy_per_share: float = 0.01,
    legacy_slippage: float = 0.0005
) -> CostAwarePortfolioManager:
    """
    Migrate from legacy cost model to new comprehensive model.
    
    Legacy model: 0.1% + $0.01/share + 0.05% slippage
    
    Args:
        legacy_percentage: Legacy percentage fee
        legacy_per_share: Legacy per-share fee
        legacy_slippage: Legacy slippage estimate
    
    Returns:
        CostAwarePortfolioManager with migrated configuration
    """
    # Create cost model matching legacy parameters
    cost_model = create_cost_model_from_current(
        current_percentage=legacy_percentage,
        current_per_share=legacy_per_share,
        current_slippage=legacy_slippage
    )
    
    return CostAwarePortfolioManager(cost_model=cost_model)


# =============================================================================
# USAGE EXAMPLES
# =============================================================================

def example_basic_usage():
    """Demonstrate basic usage of the cost-aware portfolio manager."""
    print("=" * 70)
    print("EXAMPLE: Basic Cost-Aware Portfolio Management")
    print("=" * 70)
    
    # Create portfolio manager with default cost model
    pm = CostAwarePortfolioManager()
    
    # Deposit initial capital
    pm.deposit(100_000)
    print(f"\n💰 Initial Deposit: $100,000")
    
    # Enter JPM position
    print("\n📈 Entering JPM Position:")
    jpm_entry = pm.enter_position(
        symbol="JPM",
        asset_class=AssetClass.STOCK,
        quantity=100,
        price=175.50,
        volume_24h=15_000_000,
        volatility=0.25
    )
    print(f"  Bought 100 JPM @ $175.50")
    print(f"  Notional: ${jpm_entry['notional']:,.2f}")
    print(f"  Commission: ${jpm_entry['commission']:.2f}")
    print(f"  Slippage: ${jpm_entry['slippage']:.2f}")
    print(f"  Total Cost: ${jpm_entry['total_cost']:.2f}")
    print(f"  Cash Remaining: ${jpm_entry['cash_remaining']:,.2f}")
    
    # Enter BTC position
    print("\n📈 Entering BTC Position:")
    btc_entry = pm.enter_position(
        symbol="BTC-USD",
        asset_class=AssetClass.CRYPTO,
        quantity=0.25,
        price=67_500.00,
        volume_24h=35_000_000_000,
        volatility=0.65
    )
    print(f"  Bought 0.25 BTC @ $67,500")
    print(f"  Notional: ${btc_entry['notional']:,.2f}")
    print(f"  Commission: ${btc_entry['commission']:.2f}")
    print(f"  Slippage: ${btc_entry['slippage']:.2f}")
    print(f"  Total Cost: ${btc_entry['total_cost']:.2f}")
    print(f"  Cash Remaining: ${btc_entry['cash_remaining']:,.2f}")
    
    # Update prices (simulate market movement)
    print("\n📊 Updating Market Prices:")
    pm.update_prices({'JPM': 180.00, 'BTC-USD': 70_000.00})
    print(f"  JPM: $175.50 → $180.00 (+2.56%)")
    print(f"  BTC: $67,500 → $70,000 (+3.70%)")
    
    # Show position summary
    print("\n📋 Open Positions Summary:")
    print(pm.get_position_summary().to_string(index=False))
    
    # Show portfolio summary
    print("\n📊 Portfolio Summary:")
    summary = pm.get_portfolio_summary()
    print(f"  Cash: ${summary['cash']:,.2f}")
    print(f"  Market Value: ${summary['market_value']:,.2f}")
    print(f"  Total Equity: ${summary['total_equity']:,.2f}")
    print(f"  Gross Unrealized PnL: ${summary['gross_unrealized_pnl']:,.2f}")
    print(f"  Net Unrealized PnL: ${summary['net_unrealized_pnl']:,.2f}")
    
    # Exit JPM position
    print("\n📉 Exiting JPM Position:")
    jpm_exit = pm.exit_position(
        symbol="JPM",
        price=180.00,
        volume_24h=15_000_000,
        volatility=0.25
    )
    print(f"  Sold 100 JPM @ $180.00")
    print(f"  Gross PnL: ${jpm_exit['gross_pnl']:,.2f}")
    print(f"  Total Costs: ${jpm_exit['total_costs']:.2f}")
    print(f"  Net PnL: ${jpm_exit['net_pnl']:,.2f}")
    print(f"  Return: {jpm_exit['return_pct']:.2f}%")
    
    # Show closed trades
    print("\n📋 Closed Trades Summary:")
    print(pm.get_closed_trades_summary().to_string(index=False))
    
    # Final portfolio state
    print("\n📊 Final Portfolio State:")
    final_summary = pm.get_portfolio_summary()
    print(f"  Cash: ${final_summary['cash']:,.2f}")
    print(f"  Market Value: ${final_summary['market_value']:,.2f}")
    print(f"  Total Equity: ${final_summary['total_equity']:,.2f}")
    print(f"  Total Closed PnL: ${final_summary['total_closed_pnl']:,.2f}")
    
    return pm


def example_custom_cost_configuration():
    """Demonstrate custom cost configuration for different brokers."""
    print("\n" + "=" * 70)
    print("EXAMPLE: Custom Cost Configuration")
    print("=" * 70)
    
    # Create custom cost model for Interactive Brokers
    from transaction_cost_model import (
        TransactionCostModel,
        AssetCostConfig,
        TieredCommissionModel,
        CombinedSlippageModel
    )
    
    configs = {
        AssetClass.STOCK: AssetCostConfig(
            asset_class=AssetClass.STOCK,
            commission_model=TieredCommissionModel(
                percentage_rate=0.0035,  # 0.35%
                per_share_rate=0.0035,   # $0.0035/share
                min_commission=0.35,
                max_commission=0.01
            ),
            slippage_model=CombinedSlippageModel(),
            regulatory_fees=0.0000229
        ),
        AssetClass.CRYPTO: create_retail_crypto_config('binance_us')
    }
    
    cost_model = TransactionCostModel(configs)
    pm = CostAwarePortfolioManager(cost_model=cost_model)
    pm.deposit(50_000)
    
    print("\n📊 Custom Configuration (Interactive Brokers + Binance.US):")
    print(cost_model.get_cost_summary().to_string(index=False))
    
    # Compare costs
    print("\n💰 Cost Comparison:")
    
    # Stock trade with IBKR
    trade = TradeDetails(
        symbol="AAPL",
        asset_class=AssetClass.STOCK,
        quantity=100,
        price=185.00,
        volume_24h=50_000_000,
        volatility=0.22
    )
    
    ibkr_commission = cost_model.calculate_commission(trade)
    default_model = TransactionCostModel()
    default_commission = default_model.calculate_commission(trade)
    
    print(f"\n  AAPL 100 shares @ $185.00:")
    print(f"    IBKR Commission: ${ibkr_commission:.2f}")
    print(f"    Default Commission: ${default_commission:.2f}")
    print(f"    Difference: ${ibkr_commission - default_commission:.2f}")
    
    return pm


def example_breakeven_analysis():
    """Demonstrate breakeven analysis for trading decisions."""
    print("\n" + "=" * 70)
    print("EXAMPLE: Breakeven Analysis")
    print("=" * 70)
    
    cost_model = TransactionCostModel()
    
    assets = [
        ('SPY', AssetClass.ETF, 100, 595.00, 25_000_000_000, 0.16),
        ('JPM', AssetClass.STOCK, 100, 175.50, 15_000_000, 0.25),
        ('BTC-USD', AssetClass.CRYPTO, 0.5, 67_500, 35_000_000_000, 0.65),
        ('CL=F', AssetClass.FUTURES, 2, 78.50, 500_000_000, 0.35),
    ]
    
    print("\n📊 Breakeven Analysis for Various Assets:")
    print("-" * 70)
    print(f"{'Asset':<12} {'Qty':<10} {'Price':<12} {'Round-trip Cost':<16} {'Breakeven Move':<16} {'Breakeven %':<12}")
    print("-" * 70)
    
    for symbol, asset_class, qty, price, volume, vol in assets:
        be = cost_model.estimate_breakeven_move(
            symbol=symbol,
            asset_class=asset_class,
            quantity=qty,
            price=price,
            volume_24h=volume,
            volatility=vol
        )
        
        print(f"{symbol:<12} {qty:<10} ${price:<11,.2f} ${be['round_trip_cost']:<15,.2f} "
              f"${be['breakeven_price_move']:<15,.2f} {be['breakeven_pct']:<11,.3f}%")
    
    print("-" * 70)
    print("\n💡 Key Insights:")
    print("  - SPY (ETF): Lowest breakeven due to high liquidity")
    print("  - BTC: Higher costs due to volatility and crypto fees")
    print("  - Futures: Contract-based fees can be high for small notionals")


# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == "__main__":
    # Run all examples
    example_basic_usage()
    example_custom_cost_configuration()
    example_breakeven_analysis()
    
    print("\n" + "=" * 70)
    print("✅ ALL EXAMPLES COMPLETE")
    print("=" * 70)
