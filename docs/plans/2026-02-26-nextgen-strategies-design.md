# NextGen Strategies Design — Alpha Engine
## Date: Feb 26, 2026 (Updated)

## Overview
Add 14 new strategies to Alpha Engine via `alpha_engine/nextgen_strategies.py`.
Distilled from 60+ proposals across 3 batches of Inception Labs Mercury suggestions,
plus KIMI Research Compilation (20 strategies + 10 quant community strategies).

## Strategies (14 signals)

| # | Name | Function | Asset | Key Signal |
|---|---|---|---|---|
| 1 | Cointegration Pair Trade | `cointegration_pair_trade` | Crypto | Z-score > 2σ on log-price spread |
| 2 | ADX Volatility Breakout | `adx_volatility_breakout` | Crypto | ADX > 25 + ATR spike + 20-period break |
| 3 | Seasonal Factor Rotation | `seasonal_factor_rotation` | Crypto | Calendar seasonality + momentum |
| 4 | Multi-Factor Equity Rotation | `multi_factor_equity_rotation` | Stocks | Composite ranking (momentum+quality+vol) |
| 5 | Dead Cat Bounce Momentum | `dead_cat_bounce_momentum` | Crypto | F&G ≤ 12 + engulfing pattern + volume |
| 6 | Market Structure Break | `market_structure_break` | Crypto | Round-number level break + volume |
| 7 | Volume Acceleration Reversion | `volume_acceleration_reversion` | Crypto | Volume spike with no price move |
| 8 | Night Liquidity Drift | `night_liquidity_drift` | Crypto | Off-peak breakout (00-04 UTC) |
| 9 | Spread of Candles Gap Fill | `spread_of_candles_gap` | Crypto | Two-candle gap + gap fill target |
| 10 | VIX Correlation Divergence | `vix_correlation_divergence` | Stocks | VIX > 25 + correlation breakdown |
| 11 | Profit-Taking Re-Entry | `profit_taking_reentry` | All | Re-enter after pullback on winners |
| 12 | BB+RSI Mean Reversion | `bb_rsi_mean_reversion` | Crypto | Bollinger band touch + RSI extreme |
| 13 | Pi Cycle Regime Gate | `pi_cycle_regime_gate` | BTC | 111DMA vs 350DMA×2 (Philip Swift 2019) |
| 14 | Puell Multiple Extreme | `puell_multiple_extreme` | BTC | Mining revenue ratio extremes |

## Integration
- New file: `alpha_engine/nextgen_strategies.py`
- Exports `NEXTGEN_STRATEGIES` dict (14 strategies)
- Imported at bottom of `crypto_strategies.py` as Wave 13
- Scanner regime map entries added to `scanner.py`
- Confluence engine type classification + synergy pairs in `confluence_engine.py`
- Forward tracking: automatic via `passes_forward_gate()` (starts at 0 trades)
- All strategies follow existing `func(data, context=None) -> list[dict]` pattern

## FC-Crypto Pro Fixes (Same Session)
- Added regime-direction gate: suppresses LONG when BTC down + F&G < 30
- Extreme fear (F&G ≤ 15): ONLY longs allowed
- Tightened MAX_CRYPTO_SAME_DIR from 3 to 2

## Function Signature
```python
def strategy_name(data: dict[str, pd.DataFrame], context: dict | None = None) -> list[dict]:
    # Returns list of signal dicts with required fields:
    # strategy, symbol, category, signal_type, entry_price,
    # take_profit, stop_loss, confidence, risk_reward, reason
```
