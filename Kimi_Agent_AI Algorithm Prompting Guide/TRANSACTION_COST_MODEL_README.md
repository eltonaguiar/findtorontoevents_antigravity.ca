# Transaction Cost Model - Documentation

## Overview

This module provides a comprehensive transaction cost modeling system for multi-asset trading. It supports:

- **Asset Classes**: Stocks, ETFs, Futures, Crypto, Forex, Options
- **Commission Models**: Tiered, flat, maker/taker, per-contract
- **Slippage Estimation**: Volume-based, volatility-based, combined models
- **Market Impact**: Almgren-Chriss, square root models
- **Post-Commission PnL**: Full cost tracking and reporting

## Files

| File | Description |
|------|-------------|
| `transaction_cost_model.py` | Core cost modeling classes and functions |
| `cost_model_integration.py` | Portfolio manager integration examples |
| `TRANSACTION_COST_MODEL_README.md` | This documentation file |

## Quick Start

```python
from transaction_cost_model import (
    TransactionCostModel,
    TradeDetails,
    AssetClass
)

# Initialize cost model
cost_model = TransactionCostModel()

# Create a trade
trade = TradeDetails(
    symbol="JPM",
    asset_class=AssetClass.STOCK,
    quantity=100,
    price=175.50,
    volume_24h=15_000_000,  # For slippage estimation
    volatility=0.25         # Annual vol for impact estimation
)

# Calculate costs
commission = cost_model.calculate_commission(trade)
slippage = cost_model.estimate_slippage(trade)
impact = cost_model.calculate_market_impact(trade)

print(f"Commission: ${commission:.2f}")
print(f"Slippage: ${slippage:.2f}")
print(f"Market Impact: ${impact:.2f}")
```

## Core Classes

### TransactionCostModel

Main class for calculating transaction costs across all asset classes.

```python
cost_model = TransactionCostModel()

# Or with custom configurations
cost_model = TransactionCostModel(configs={
    AssetClass.STOCK: custom_stock_config,
    AssetClass.CRYPTO: custom_crypto_config
})
```

**Key Methods:**

| Method | Description |
|--------|-------------|
| `calculate_commission(trade, is_maker=False)` | Calculate commission for a trade |
| `estimate_slippage(trade)` | Estimate slippage based on volume/volatility |
| `calculate_market_impact(trade)` | Calculate market impact (if configured) |
| `calculate_round_trip_cost(...)` | Calculate complete round-trip costs |
| `calculate_post_commission_pnl(...)` | Calculate PnL after all costs |
| `estimate_breakeven_move(...)` | Estimate required price move to break even |

### TradeDetails

Data class containing all information needed for cost calculation.

```python
trade = TradeDetails(
    symbol="BTC-USD",
    asset_class=AssetClass.CRYPTO,
    quantity=0.5,           # Positive for buy, negative for sell
    price=67500.00,
    order_type=OrderType.MARKET,
    volume_24h=35_000_000_000,  # Optional: for slippage
    volatility=0.65,            # Optional: for impact
    bid_ask_spread=0.001,       # Optional: for slippage
    market_cap=None             # Optional: for impact
)
```

### PositionPnL

Tracks PnL with full cost breakdown.

```python
pnl = cost_model.calculate_post_commission_pnl(
    symbol="JPM",
    asset_class=AssetClass.STOCK,
    quantity=100,
    entry_price=175.50,
    exit_price=180.00,
    entry_volume_24h=15_000_000,
    exit_volume_24h=15_000_000,
    volatility=0.25
)

print(f"Gross PnL: ${pnl.gross_pnl:.2f}")
print(f"Net PnL: ${pnl.net_pnl:.2f}")
print(f"Cost Drag: {pnl.cost_drag_pct:.1f}%")
```

## Default Cost Configurations

### Stocks (JPM, V)

```python
Commission: Tiered - max(0.000%, $0.005/share) [min: $1.00]
Slippage: Combined (volume + volatility + spread)
Regulatory: 0.0023% (SEC fee)
```

### ETFs (SPY, QQQ)

```python
Commission: Tiered - max(0.000%, $0.005/share) [min: $1.00]
Slippage: Combined model
Regulatory: 0.0023% (SEC fee)
```

### Futures (CL=F, GC=F, ZN=F)

```python
Commission: $1.40/contract
  - Broker: $0.50
  - Exchange: $0.85
  - Clearing: $0.05
Slippage: Volume-based (2 bps base)
Regulatory: $0.02/contract (NFA fee)
```

### Crypto (BTC, ETH)

```python
Commission: Maker 0.08%, Taker 0.12%
Slippage: Combined (volume + volatility)
Market Impact: Square root model enabled
```

## Commission Models

### TieredCommissionModel

Most common for stocks and ETFs.

```python
from transaction_cost_model import TieredCommissionModel

commission_model = TieredCommissionModel(
    percentage_rate=0.001,    # 0.1% of notional
    per_share_rate=0.01,      # $0.01 per share
    min_commission=1.0,       # Minimum $1.00
    max_commission=None       # No maximum
)
```

### CryptoCommissionModel

Maker/taker fees for crypto exchanges.

```python
from transaction_cost_model import CryptoCommissionModel

commission_model = CryptoCommissionModel(
    maker_rate=0.0008,   # 0.08% for maker orders
    taker_rate=0.0012    # 0.12% for taker orders
)

# Calculate commission
taker_commission = commission_model.calculate(trade, is_maker=False)
maker_commission = commission_model.calculate(trade, is_maker=True)
```

### FuturesCommissionModel

Per-contract fees for futures.

```python
from transaction_cost_model import FuturesCommissionModel

commission_model = FuturesCommissionModel(
    per_contract_fee=0.50,   # Broker fee
    exchange_fee=0.85,        # Exchange fee
    clearing_fee=0.05         # Clearing fee
)
```

## Slippage Models

### VolumeBasedSlippageModel

Slippage based on trade size relative to volume.

```python
from transaction_cost_model import VolumeBasedSlippageModel

slippage_model = VolumeBasedSlippageModel(
    base_slippage_bps=5.0,      # 5 basis points base
    volume_exponent=0.5,         # Square root model
    min_slippage_bps=1.0,        # Minimum 1 bps
    max_slippage_bps=100.0       # Maximum 100 bps
)
```

Formula: `slippage = base_slippage * (trade_size / volume)^exponent`

### VolatilityBasedSlippageModel

Slippage incorporating market volatility.

```python
from transaction_cost_model import VolatilityBasedSlippageModel

slippage_model = VolatilityBasedSlippageModel(
    base_slippage_bps=5.0,
    volatility_multiplier=10.0,
    reference_volatility=0.20   # 20% annual vol baseline
)
```

### CombinedSlippageModel

Weighted combination of volume, volatility, and spread.

```python
from transaction_cost_model import CombinedSlippageModel

slippage_model = CombinedSlippageModel(
    volume_weight=0.4,
    volatility_weight=0.4,
    spread_weight=0.2
)
```

## Market Impact Models (Advanced)

### Almgren-Chriss Model

Industry-standard market impact model.

```python
from transaction_cost_model import AlmgrenChrissModel

impact_model = AlmgrenChrissModel(
    temporary_impact_coef=0.5,
    permanent_impact_coef=0.2,
    temp_exponent=0.6,
    perm_exponent=0.6
)
```

Formula:
- Temporary: `h * sigma * (X/V)^gamma`
- Permanent: `g * sigma * (X/V)^delta`

### SquareRootImpactModel

Simpler alternative to Almgren-Chriss.

```python
from transaction_cost_model import SquareRootImpactModel

impact_model = SquareRootImpactModel(impact_coef=1.0)
```

Formula: `Impact = eta * sigma * sqrt(X/V)`

## Portfolio Manager Integration

### CostAwarePortfolioManager

Ready-to-use portfolio manager with integrated cost tracking.

```python
from cost_model_integration import CostAwarePortfolioManager

# Initialize
pm = CostAwarePortfolioManager()
pm.deposit(100_000)

# Enter position with automatic cost calculation
entry_result = pm.enter_position(
    symbol="JPM",
    asset_class=AssetClass.STOCK,
    quantity=100,
    price=175.50,
    volume_24h=15_000_000,
    volatility=0.25
)

# Update prices
pm.update_prices({'JPM': 180.00})

# Exit position with full PnL tracking
exit_result = pm.exit_position(
    symbol="JPM",
    price=180.00,
    volume_24h=15_000_000,
    volatility=0.25
)

print(f"Net PnL: ${exit_result['net_pnl']:.2f}")
print(f"Cost Drag: {(exit_result['total_costs'] / exit_result['gross_pnl'] * 100):.1f}%")
```

### Position Summary

```python
# Get all open positions
positions_df = pm.get_position_summary()
print(positions_df)

# Get closed trades history
closed_df = pm.get_closed_trades_summary()
print(closed_df)

# Get portfolio summary
summary = pm.get_portfolio_summary()
print(f"Total Equity: ${summary['total_equity']:,.2f}")
print(f"Net Unrealized PnL: ${summary['net_unrealized_pnl']:,.2f}")
```

## Retail Trader Presets

### Interactive Brokers Configuration

```python
from transaction_cost_model import (
    create_retail_stock_config,
    create_retail_futures_config
)

# IBKR Stock config
ibkr_stock = create_retail_stock_config('interactive_brokers')

# IBKR Futures config
ibkr_futures = create_retail_futures_config('interactive_brokers')
```

### Crypto Exchange Configurations

```python
from transaction_cost_model import create_retail_crypto_config

# Coinbase Pro
coinbase = create_retail_crypto_config('coinbase_pro')

# Binance.US
binance_us = create_retail_crypto_config('binance_us')

# Kraken
kraken = create_retail_crypto_config('kraken')
```

### Zero-Commission Brokers

```python
# Robinhood, Webull style
zero_commission = create_retail_stock_config('zero_commission')
```

## Migration from Legacy System

If you're migrating from the existing 0.1% + $0.01/share + 0.05% slippage model:

```python
from transaction_cost_model import create_cost_model_from_current
from cost_model_integration import migrate_from_legacy_cost_model

# Create cost model matching legacy parameters
cost_model = create_cost_model_from_current(
    current_percentage=0.001,    # 0.1%
    current_per_share=0.01,       # $0.01/share
    current_slippage=0.0005       # 0.05%
)

# Or migrate entire portfolio manager
pm = migrate_from_legacy_cost_model(
    legacy_percentage=0.001,
    legacy_per_share=0.01,
    legacy_slippage=0.0005
)
```

## Breakeven Analysis

Calculate the price move required to break even after costs:

```python
breakeven = cost_model.estimate_breakeven_move(
    symbol="SPY",
    asset_class=AssetClass.ETF,
    quantity=100,
    price=595.00,
    volume_24h=25_000_000_000,
    volatility=0.16
)

print(f"Round-trip Cost: ${breakeven['round_trip_cost']:.2f}")
print(f"Required Move: ${breakeven['breakeven_price_move']:.2f}")
print(f"Required Move %: {breakeven['breakeven_pct']:.3f}%")
```

## Example Output

### Cost Configuration Summary

```
Asset Class  Commission Model                                    Exchange Fees  Regulatory Fees  Market Impact
STOCK        Tiered: max(0.000%, $0.005/share) [min: $1.00]     $0             0.0023%          Disabled
ETF          Tiered: max(0.000%, $0.005/share) [min: $1.00]     $0             0.0023%          Disabled
FUTURES      Futures: $1.400/contract                            $0             2.0000%          Disabled
CRYPTO       Crypto: Maker 0.080%, Taker 0.120%                  $0             $0               Enabled
```

### Round-Trip Cost Analysis

```
Trade: JPM 100 shares
Entry: $175.50 | Exit: $180.00

Gross PnL:          $450.00
Total Commission:     $2.81
Total Slippage:      $26.31
Total Cost:          $29.12
Cost % of Notional:   0.082%
Net PnL:            $420.88
Cost Drag:            6.5%
```

## Best Practices

1. **Always include volume data** for accurate slippage estimation
2. **Use volatility data** when available for better impact modeling
3. **Update configurations** to match your actual broker fees
4. **Track costs per position** for accurate PnL reporting
5. **Use breakeven analysis** before entering trades
6. **Consider cost drag** in strategy performance evaluation

## Performance Considerations

- Cost calculations are lightweight and suitable for real-time use
- Market impact models require more data (volume, volatility)
- Cache configurations to avoid repeated initialization
- Pre-calculate breakeven levels for frequently traded assets

## Testing

Run the built-in examples:

```bash
python transaction_cost_model.py
python cost_model_integration.py
```

## License

This module is provided as part of the quantitative finance research toolkit.
