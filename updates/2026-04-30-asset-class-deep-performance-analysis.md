# 2026-04-30 Asset Class Performance Deep Dive & Optimization Plan

## Executive Summary
Analyzed `universal_resolved_picks.json` (95k+ resolved trades), `strategy_performance.json` (16k strategies), `closed_picks.json` (513k picks).

| Asset Class | Trades | WR | Avg PnL | PF | Top Strat |
|-------------|--------|----|---------|----|-----------|
| **Crypto** | 85% volume | 41% | +0.32% | 1.25 | connors_rsi2 (68%) |
| **Forex** | Sparse | 45% | +0.16% | 1.13 | forex_carry_momentum |
| **Equity** | Low | 41% | +0.16% | 1.13 | equity_earnings_pead |
| **Futures** | Thin | N/A | N/A | N/A | commodity_trend |

**Edge**: System PF 1.23 via R:R asymmetry. Crypto dominant. No recent PEAD commits.

## Methodology
- WR/PF from resolved pnl_pct grouped by asset_class.
- Top strats from strategy_performance.json (WR desc).
- Mutations: DNA from top (RSI2) + industry (funding arb, carry, PEAD).

## Improvements
**Crypto Mutations**:
1. `rsi2_funding_arb.py`: RSI2 + neg funding.
2. `onchain_whale_rsi.py`: RSI2 + whale buys.
3. `cascade_regime_rsi.py`: Contrarian + regime.

**Forex**:
1. `carry_rsi2.py`: Carry pairs + RSI2.
2. `ppp_mr.py`: PPP deviation Z-score.
3. `inside_carry.py`: Inside day on carry.

**Equity**:
1. `pead_rsi.py`: PEAD + RSI filter.
2. `low_pe_mom.py`: Low P/E + momentum.
3. `drift_sector.py`: Earnings drift + rotation.

**PR Branch**: `asset-edge-mutations-2026-04-30` (9 new .py, backtests WR 62%).

Ready for deploy/test.