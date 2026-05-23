# ☠️ Strategy Graveyard

> **Last Updated:** 2026-03-01  
> **Total Graveyard Strategies:** 27  
> **Total PnL Destroyed:** -$12,839.17  
> **Classification Method:** Kelly Fraction, Win Rate, Total PnL from forward testing

## What is the Graveyard?

The Graveyard is where strategies go to die — permanently. A strategy lands here when forward testing proves it has **negative expected value (EV)**. These strategies are:

- ❌ **Disabled forever** — they will never generate trade picks again
- 📚 **Kept for reference** — so future AI agents don't recreate failed concepts
- 📊 **Data preserved** — historical performance data stays for analysis
- 🧪 **Educational** — understanding failure modes prevents systemic errors

## Why Not Just Delete Them?

1. **Avoid duplicate research** — If we delete `halloween_effect`, some future agent might try to build "seasonal_crypto_calendar" — the same thing with a different name
2. **Pattern recognition** — Common failure modes (tiny TP/huge SL, calendar effects, on-chain latency) help us avoid building new strategies with the same flaws
3. **Benchmarking** — The graveyard serves as a "theory validation" bucket: if these strategies suddenly start working, it tells us the market regime changed dramatically

## Graveyard Registry

### Catastrophic Loss (>$500 each)

| Strategy | WR | Kelly | PnL | Trades | Death Cause |
|---|---|---|---|---|---|
| double_top_bottom_detector | 25.0% | -4.31 | -$1,134 | 4 | R:R ratio catastrophically wrong |
| exchange_netflow_reversal | 0.0% | 0.00 | -$992 | 6 | On-chain data too slow for hourly TF |
| halloween_effect | 0.0% | 0.00 | -$943 | 5 | Calendar anomalies don't work in 24/7 crypto |
| monthly_seasonality | 12.5% | -0.98 | -$942 | 8 | Same — no reliable monthly patterns |
| fourier_cycle_detector | 0.0% | 0.00 | -$935 | 6 | Overfitted to noise; cycles don't repeat |
| smart_money_fvg | 0.0% | 0.00 | -$928 | 9 | ICT/SMC concepts have ZERO edge in crypto |
| m2_liquidity_lag | 22.2% | -0.81 | -$879 | 9 | Macro liquidity moves too slowly for trading |
| price_touch_recurrence | 0.0% | 0.00 | -$874 | 5 | Support/resistance levels too noisy |
| momentum_mean_rev_blend | 0.0% | 0.00 | -$712 | 4 | Contradictory signals cancel any edge |
| altcoin_season_rotation | 0.0% | 0.00 | -$654 | 4 | Alt season detection unreliable |
| cross_sectional_momentum | 0.0% | 0.00 | -$612 | 3 | Wrong timeframe for cross-sectional momentum |

### Medium Loss ($200-$500 each)

| Strategy | WR | Kelly | PnL | Trades | Death Cause |
|---|---|---|---|---|---|
| community_bb_squeeze_breakout_crypto | 0.0% | 0.00 | -$472 | 2 | False breakouts in choppy markets |
| btc_dominance_reversal | 0.0% | 0.00 | -$389 | 2 | BTC dominance changes too slowly |
| spike_volume_explosion | 0.0% | 0.00 | -$342 | 2 | Volume spikes are noise, not signal |
| sector_momentum_7d | 0.0% | 0.00 | -$329 | 2 | 7-day sector momentum too short |
| community_ict_fvg_selective | 12.5% | -1.65 | -$304 | 8 | ICT FVG = retail trap |
| break_of_structure | 0.0% | 0.00 | -$273 | 2 | Structure breaks are noise in crypto |
| community_momentum_breakout_volume_crypto | 0.0% | 0.00 | -$272 | 2 | Same false breakout problem |
| spike_squeeze_breakout | 0.0% | 0.00 | -$268 | 2 | Squeeze → whipsaw, not breakout |
| coingecko_trending_volume | 0.0% | 0.00 | -$258 | 1 | "Trending" = pump & dump |

### Minor Loss (<$200 each, but still negative EV)

| Strategy | WR | Kelly | PnL | Trades | Death Cause |
|---|---|---|---|---|---|
| multi_touch_level_strength | 0.0% | 0.00 | -$118 | 1 | Not enough data points for signal |
| halving_cycle_position | 0.0% | 0.00 | -$80 | 1 | Halving cycle too macro for active trading |
| price_level_magnetism | 88.9% | -0.75 | -$66 | 9 | ⚠️ FAKE WINS: 89% WR but loses money (tiny TP, huge SL) |
| support_resistance_bounce | 0.0% | 0.00 | -$48 | 1 | S/R too noisy in crypto |
| stablecoin_buying_power | 50.0% | -0.07 | -$17 | 2 | Stablecoin data arrives too late |
| session_momentum_continuation | 66.7% | -0.03 | -$1 | 3 | Tiny edge completely erased by fees |
| failed_breakout_reversal | 50.0% | -1.50 | -$0 | 2 | Average loss >> average win |

## Lessons Learned

### 🚫 Lesson 1: Calendar/Seasonal Strategies DON'T Work in Crypto
**Dead strategies:** halloween_effect, monthly_seasonality, halving_cycle_position  
**Why:** Crypto trades 24/7/365. There are no market closes, no institutional rebalancing dates, no holiday effects. Calendar anomalies that work in equities (Sell in May, January Effect) have zero applicability.

### 🚫 Lesson 2: ICT/SMC Concepts Have ZERO Forward Edge
**Dead strategies:** smart_money_fvg, community_ict_fvg_selective, break_of_structure  
**Why:** Inner Circle Trader and Smart Money Concepts are popular on YouTube but produce ZERO alpha in systematic testing. Fair Value Gaps, Break of Structure, and Order Blocks are pattern-matching artifacts that don't survive live trading costs.

### 🚫 Lesson 3: On-Chain Metrics Are Too Slow for Hourly Trading
**Dead strategies:** exchange_netflow_reversal, m2_liquidity_lag, stablecoin_buying_power  
**Why:** On-chain data (exchange flows, M2 supply, stablecoin metrics) updates too slowly. By the time the signal appears, the price move has already happened. These might work on daily/weekly timeframes but are garbage on hourly.

### 🚫 Lesson 4: High Win Rate ≠ Profitable
**Dead strategy:** price_level_magnetism (89% WR, NEGATIVE PnL)  
**Why:** This strategy had tiny take-profits and huge stop-losses. It won 8 out of 9 trades but the single loss wiped out all gains. A 89% win rate with a negative Kelly fraction means guaranteed ruin over time.

### 🚫 Lesson 5: Blending Contradictory Signals Cancels Edge
**Dead strategy:** momentum_mean_rev_blend  
**Why:** Combining momentum (buy high, sell higher) with mean reversion (buy low, sell high) in the same strategy produces contradictory signals that cancel any edge either approach might have individually.

## Technical Implementation

```python
# In alpha_engine/strategy_guard.py
from alpha_engine.strategy_guard import is_graveyard, GRAVEYARD

# Check if a strategy is dead
if is_graveyard("halloween_effect"):
    print("This strategy is in the graveyard - do not trade")

# Get all graveyard strategies
print(f"Total graveyard: {len(GRAVEYARD)}")
```

Graveyard state is also stored in `stabilization/disabled_strategies.json` under the `"graveyard"` key.
