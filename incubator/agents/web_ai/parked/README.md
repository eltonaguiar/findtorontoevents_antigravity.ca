# Parked Strategies

These strategies require specialized data sources that are not available in standard OHLCV backtests.

## Why Parked?

We only backtest with **real data**. Synthetic data can produce misleading results, so these strategies remain parked until we have proper data infrastructure.

## Categories

### On-Chain (001-010)
Require blockchain data APIs (Glassnode, CryptoQuant, direct node access):
- Whale wallet tracking
- Exchange flows
- MVRV, NUPL, SOPR metrics
- Network velocity

### Cross-Asset (016-020)
Require external market data:
- SPX correlation
- DXY inverse
- Multi-asset feeds

### Microstructure (021-030)
Require L2 order book data:
- Order book imbalance
- Spread analysis
- VWAP deviation
- Session-based strategies

### Funding & Derivatives (031-035)
Require exchange-specific APIs:
- Funding rates
- Premium index
- Perp-spot basis

### Options & Sentiment (051-070)
Require specialized feeds:
- Options chain data
- Social sentiment APIs
- Liquidation feeds

## Reactivation Criteria

A strategy moves from `parked/` to active when:
1. Real data source is integrated
2. Historical data is available for backtesting
3. Data quality is verified

## Data Infrastructure Roadmap

See [`incubator/STRATEGY_INVENTORY.md`](../../STRATEGY_INVENTORY.md) for full roadmap.

---

*Parked strategies: 46*
*Active strategies: 174*
*Total: 220 new strategies + 222 existing = 442*

### Update Log
- **2026-02-26:** Added 20 Google Antigravity strategies (201-220) - all active
- **2026-02-26:** Parked 46 strategies requiring specialized data
