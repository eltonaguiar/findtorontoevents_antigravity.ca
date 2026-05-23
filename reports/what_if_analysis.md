# What-If Analysis — Strategy Remediation

## The Core Problem: Many Strategies Only Work in One Direction

In the current bear/choppy crypto market, strategies that bet prices will go UP (LONG) are losing money, while the same strategies betting prices will go DOWN (SHORT) are profitable. This is the single biggest finding.

**Simple explanation:** Imagine a strategy that says "buy when RSI crosses above 50" (LONG) and "sell when RSI crosses below 50" (SHORT). In a falling market, the "buy" signals keep losing because the price keeps dropping after the signal fires. But the "sell" signals keep winning because they correctly predict the continued decline. The fix: stop listening to the "buy" signals and only follow the "sell" signals until the market regime changes.

## Specific Strategy Fixes

### 1. macd_crossover — Only follow SHORT signals
- **Problem:** When this strategy says "BUY" (LONG), it's right only 19.6% of the time (loses 4 out of 5 trades)
- **But:** When it says "SELL" (SHORT), it's right 46.2% of the time (wins nearly half)
- **Fix:** Ignore all LONG signals from this strategy. Only act on SHORT signals.
- **Expected improvement:** Overall win rate jumps from 33.9% to ~46%

### 2. luxalgo_confluence — Only follow SHORT signals, only on SOL and BTC
- **Problem:** LONG signals win only 32.3% of the time
- **But:** SHORT signals win 43.5%, and specifically on SOL the strategy has 47.2% WR
- **Fix:** Ignore LONG signals. Only trade SHORT on SOL and BTC.
- **Expected improvement:** WR improves from 37.5% toward 43.5%

### 3. quan_engine_scalp — Only trade TRX and BTC
- **Problem:** This strategy trades 10+ symbols but most are losers. KAS has 29% WR (-38% PnL), TAO has 28.9% WR
- **But:** On TRX it has 50.8% WR (+26% PnL), on BTC it has 39.5% WR (+8% PnL)
- **Fix:** Stop trading KAS, HYPE, TAO, and other losing symbols. Only trade TRX and BTC.
- **Expected improvement:** Eliminates 75% of the losses

### 4. st_rsi_momentum_confluence — Remove the OP symbol
- **Problem:** One symbol (OP/Optimism) has 17.9% WR and -56.57% PnL, nearly wiping out all profits
- **But:** ARB has 97.4% WR, AVAX has 79.3% WR, ADA has 69.7% WR
- **Fix:** Block OP from this strategy. Only trade ARB, AVAX, ADA.
- **Expected improvement:** WR recovers from 36.7% back toward 56%+

### 5. crypto_keltner_v1 — SHORT signals are 2x better than LONG
- **Data:** SHORT wins 81.8% of the time. LONG wins only 37.5%.
- **This is already our best strategy** but the LONG side drags it down.
- **Consider:** Heavily favor SHORT signals from Keltner.

## Low-Signal Strategy Loosening

These strategies have great win rates but rarely fire:

### st_atr_vol_breakout (93% WR, only 18 trades ever)
- **Why so few signals:** Requires ATR% > 2.5% AND momentum > 1% AND volume > 1.8x — all three simultaneously
- **Already relaxed:** Was ATR > 3.0% and volume > 2.0x, already loosened once
- **Only trades APTUSDT** — other symbols never meet all conditions at once
- **Suggestion:** Consider an OR gate (if 2 of 3 conditions are extreme, fire even if 3rd is marginal)

### hs_lb_None (92% WR, only 12 trades)
- **Why so few:** Depends on whale traders opening new positions
- **Already tracking 80+ wallets** — adding more wallets won't help much
- **Suggestion:** Track position INCREASES (not just new opens), lower MIN_TOTAL_PNL from $500 to $200

### crypto_keltner_v1 (78% WR, ~52 trades, BTC only)
- **Why limited:** Needs Keltner band compression then expansion — inherently rare
- **BTC time filter (05:00-13:00 UTC only)** further restricts signals
- **Suggestion:** Loosen compression threshold from 5% to 6% of minimum width

## Cross-Asset Super Strategy

Only **one strategy** works across multiple asset classes:

**Bollinger MR (Mean Reversion)**
- CRYPTO: 100% WR on 2 trades
- EQUITY: 80% WR on 10 trades (JOBY, RIOT)
- This is the only candidate for true cross-asset deployment
- Needs more crypto trades to confirm

## st_bb_squeeze_expansion CORRECTION
- Previously reported as "100% WR on 14 trades" — this was a cherry-picked window
- **Full record: 43.9% WR on 41 trades, -11.55% PnL**
- Only works on TRX (87.5% WR). Strategy is currently DISABLED.

## Summary: The Market Regime Matters

The common thread: in a declining/choppy market, SHORT signals have edge and LONG signals don't. Rather than killing entire strategies, we should:
1. **Filter by direction** — suppress LONG signals in bearish regimes
2. **Filter by symbol** — each strategy has "good" and "bad" symbols
3. **Monitor regime** — when market turns bullish, re-enable LONG signals
