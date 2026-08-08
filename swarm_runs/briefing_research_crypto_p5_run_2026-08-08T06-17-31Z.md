# CRYPTO research P5 — SYNTHESIS swarm briefing

You are one of 3 AI engines voting on the CRYPTO research run at run_2026-08-08T06-17-31Z.

P3 backtest + P4 cross-test are complete. Numbers are real (yfinance prices, SMA-crossover proxy of spec.entry, 5y window, 5bp round-trip costs) but the signal is SIMPLIFIED — spec.entry text is not yet parsed faithfully. A faithful-signal translator is queued for v3.

## Per-candidate evidence

### `crypto_cross_mom_v1` (cerebras)
  - entry: On the first trading day of each month compute 126-day cumulative return for each ticker in ['BTC-USD','ETH-USD','SOL-USD','BNB-USD','XRP-USD']; rank assets; go long the top 2 and short the bottom 2 with equal dollar allocation (50% long, 50% short).
  - exit: Close all positions at the end of the 30-day holding period or earlier if an asset exits the top-2 / bottom-2 ranking before the 30-day horizon.
  - sizing: Equal-weight dollar allocation across long legs and across short legs; gross exposure capped at 100% of capital (net exposure may be near zero).
  - universe: ['BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'XRP-USD']
  - regime: Skip the month if 30-day realized volatility of BTC-USD exceeds 80% OR if the total crypto market cap (sum of the 5 tickers) falls more than 10% over the prior 30 days.
  - P3: PF=6.42 WR=75.0% MDD=37.1% Sharpe=0.45 n=4
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for BTC-USD (1826 bars). Signal: sma_cross (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `crypto_ts_mom_v1` (cerebras)
  - entry: At the start of each month compute 252-day past return for each ticker; if return > 0 generate a long signal, if return < 0 generate a short signal. Open positions for all signaled assets.
  - exit: Close each position after 30 days or when the sign of the 252-day return flips (whichever comes first).
  - sizing: Allocate equal dollar weight to each active signal; scale each leg to target 12% annualized volatility using a rolling 30-day realized vol estimate.
  - universe: ['BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'XRP-USD']
  - regime: Skip the month if BTC-USD 30-day realized volatility > 80% OR if the US VIX (proxy from external data) > 30.
  - P3: PF=6.42 WR=75.0% MDD=37.1% Sharpe=0.45 n=4
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for BTC-USD (1826 bars). Signal: sma_cross (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `crypto_vol_target_v1` (cerebras)
  - entry: Each day compute 30-day realized volatility of BTC-USD; set target annualized vol = 15%; compute scaling factor = target_vol / (realized_vol * sqrt(252)); go long BTC-USD with position size = min(scaling_factor,1).
  - exit: If scaling_factor falls below 0.2 (i.e., volatility spikes) move to cash; otherwise maintain daily-adjusted exposure.
  - sizing: Dynamic dollar exposure equal to scaling_factor of capital (0-100%); remainder held in cash.
  - universe: ['BTC-USD']
  - regime: Skip trading on any day where BTC-USD price drops >5% intraday or when 30-day realized vol > 80%.
  - P3: PF=6.42 WR=75.0% MDD=37.1% Sharpe=0.45 n=4
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for BTC-USD (1826 bars). Signal: sma_cross (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `crypto_regime_switch_v1` (cerebras)
  - entry: Compute 60-day simple moving average (SMA) of BTC-USD price; if price > SMA, enter a full-allocation long position in BTC-USD; if price < SMA, stay in cash.
  - exit: Switch to cash when price falls below SMA; switch back to long when price rises above SMA.
  - sizing: 100% of capital allocated to BTC-USD in bull regime, 0% in bear regime.
  - universe: ['BTC-USD']
  - regime: Skip trading days when BTC-USD 30-day realized volatility > 80% or when the 30-day market-cap drawdown of the five-asset basket exceeds 15%.
  - P3: PF=6.42 WR=75.0% MDD=37.1% Sharpe=0.45 n=4
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for BTC-USD (1826 bars). Signal: sma_cross (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `crypto_pairs_trade_v1` (cerebras)
  - entry: Using the BTC-USD and ETH-USD pair, estimate beta from OLS regression of log(ETH) on log(BTC) over the prior 60 days; compute spread = log(BTC) - beta*log(ETH); calculate mean and std of spread over the same window. If spread > mean + 2*std, go short BTC-USD and long ETH-USD (short spread). If spread < mean - 2*std, go long BTC-USD and short ETH-USD (long spread).
  - exit: Close the position when spread reverts to its mean or after a maximum holding period of 30 days, whichever occurs first.
  - sizing: Dollar-neutral: each leg receives 50% of capital (long and short legs equal in dollar terms).
  - universe: ['BTC-USD', 'ETH-USD']
  - regime: Skip any month where BTC-USD 30-day realized volatility > 80% or where the combined market-cap of the five assets falls >10% over the prior 30 days.
  - P3: PF=6.42 WR=75.0% MDD=37.1% Sharpe=0.45 n=4
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for BTC-USD (1826 bars). Signal: sma_cross (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `crypto_momentum_cross_v1` (deepseek)
  - entry: long top 2 coins by 6-month (126-day) total return, short bottom 2 coins by same metric, rebalance monthly
  - exit: exit all positions at next monthly rebalance (30 calendar days), or earlier if any position hits -15% stop-loss
  - sizing: equal-weight long and short legs, each leg sized to 25% of portfolio; total gross exposure 100%
  - universe: ['BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'XRP-USD']
  - regime: skip when average 30-day realized volatility across universe > 120% annualized (i.e., extreme panic) OR when BTC-USD 90-day return < -40% (deep bear regime)
  - P3: PF=6.42 WR=75.0% MDD=37.1% Sharpe=0.45 n=4
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for BTC-USD (1826 bars). Signal: sma_cross (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `crypto_carry_funding_v1` (deepseek)
  - entry: long SOL-USD and ETH-USD when their 7-day average funding rate (approximated by 7-day return minus 7-day risk-free proxy) is in top 2 of universe; short BNB-USD and XRP-USD when their funding rate is in bottom 2
  - exit: exit after 7 calendar days, or if any position loses 10% from entry
  - sizing: equal-weight long/short pairs, each leg 25% of portfolio; total gross 100%
  - universe: ['BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'XRP-USD']
  - regime: skip when BTC-USD 30-day return < -20% (contango tends to collapse in crashes) OR when average funding rate spread across universe < 0.02% daily (no carry opportunity)
  - P3: PF=6.42 WR=75.0% MDD=37.1% Sharpe=0.45 n=4
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for BTC-USD (1826 bars). Signal: sma_cross (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `crypto_vol_target_btc_v1` (deepseek)
  - entry: long BTC-USD when 30-day realized volatility < 80% annualized; position size inversely proportional to vol
  - exit: exit when 30-day realized volatility exceeds 120% annualized (vol spike) OR when position hits -25% trailing stop from peak
  - sizing: target 40% annualized volatility: position = 0.40 / (30-day realized vol annualized). Cap position at 100% of portfolio, floor at 10%
  - universe: ['BTC-USD']
  - regime: skip entirely when BTC-USD 90-day return < -50% (structural bear) OR when 30-day realized vol > 150% (unmanageable vol)
  - P3: PF=6.42 WR=75.0% MDD=37.1% Sharpe=0.45 n=4
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for BTC-USD (1826 bars). Signal: sma_cross (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `crypto_pairs_meanrev_v1` (deepseek)
  - entry: long ETH-USD and short BTC-USD when the spread (ETH/BTC ratio) is 2 standard deviations below its 60-day rolling mean; reverse positions when spread is 2 std above mean
  - exit: exit when spread reverts to within 0.5 std of the mean, or after 20 trading days, or if either leg moves 15% against the position
  - sizing: dollar-neutral: long ETH and short BTC with equal notional value, each leg sized to 50% of portfolio
  - universe: ['BTC-USD', 'ETH-USD']
  - regime: skip when 30-day correlation between BTC and ETH < 0.5 (cointegration likely broken) OR when BTC-USD 30-day return < -25% (systemic stress breaks pair relationships)
  - P3: PF=6.42 WR=75.0% MDD=37.1% Sharpe=0.45 n=4
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for BTC-USD (1826 bars). Signal: sma_cross (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `crypto_ml_boost_v1` (deepseek)
  - entry: long top 2 coins with highest gradient boosting prediction for next-day return (using features: 5-day momentum, 20-day volatility, 20-day volume change, BTC dominance trend); short bottom 2 coins
  - exit: exit after 1 trading day (daily rebalance), or if any position hits -8% stop-loss intraday
  - sizing: equal-weight long/short, each leg 25% of portfolio; total gross 100%
  - universe: ['BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'XRP-USD']
  - regime: skip when model confidence (average predicted probability across top/bottom picks) < 0.55 OR when BTC-USD 7-day return > 30% (euphoria distorts signals)
  - P3: PF=17.27 WR=100.0% MDD=76.6% Sharpe=0.26 n=1
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for BTC-USD (1826 bars). Signal: breakout (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `crypto_diagnostic_noedge_v1` (deepseek)
  - entry: long BTC-USD on first trading day of each month, hold for 5 trading days, then exit
  - exit: exit after exactly 5 trading days regardless of price
  - sizing: fixed 100% of portfolio into BTC-USD
  - universe: ['BTC-USD']
  - regime: none (deliberately naive to test if any calendar effect exists)
  - P3: PF=6.42 WR=75.0% MDD=37.1% Sharpe=0.45 n=4
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for BTC-USD (1826 bars). Signal: sma_cross (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `crypto_momentum_btc_v1` (xai)
  - entry: long BTC-USD when 12-month momentum > 0 (price > price 12 months ago)
  - exit: exit when 12-month momentum flips negative or after 1-month hold period
  - sizing: fixed 100% allocation to BTC-USD when signal is active, otherwise 0%
  - universe: ['BTC-USD']
  - regime: skip when 30-day realized volatility of BTC-USD > 80%
  - P3: PF=1.79 WR=31.2% MDD=59.4% Sharpe=0.4 n=32
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for BTC-USD (1826 bars). Signal: momentum (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `crypto_vol_target_eth_v1` (xai)
  - entry: long ETH-USD with dynamic sizing based on inverse of 30-day realized volatility
  - exit: no fixed exit; continuously adjust position daily based on volatility target (10% annualized vol)
  - sizing: scale position to target 10% annualized volatility based on 30-day realized vol
  - universe: ['ETH-USD']
  - regime: skip (reduce to 0% allocation) when 30-day realized volatility of ETH-USD > 100%
  - P3: PF=1.62 WR=75.0% MDD=61.6% Sharpe=0.18 n=4
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for ETH-USD (1826 bars). Signal: sma_cross (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `crypto_pairs_btc_eth_v1` (xai)
  - entry: long BTC-USD and short ETH-USD when 60-day price ratio (BTC/ETH) deviates > 2 std from 120-day mean
  - exit: exit when ratio reverts to within 1 std of 120-day mean or after 30-day hold
  - sizing: equal dollar allocation to long and short legs for market-neutral exposure
  - universe: ['BTC-USD', 'ETH-USD']
  - regime: skip when 30-day correlation between BTC-USD and ETH-USD < 0.5
  - P3: PF=6.42 WR=75.0% MDD=37.1% Sharpe=0.45 n=4
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for BTC-USD (1826 bars). Signal: sma_cross (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `crypto_regime_switch_btc_v1` (xai)
  - entry: long BTC-USD when 60-day moving average > 200-day moving average (bull regime proxy)
  - exit: exit when 60-day moving average < 200-day moving average (bear regime proxy)
  - sizing: fixed 100% allocation to BTC-USD when in bull regime, otherwise 0%
  - universe: ['BTC-USD']
  - regime: skip (stay flat) when 30-day realized volatility of BTC-USD > 90%
  - P3: PF=6.42 WR=75.0% MDD=37.1% Sharpe=0.45 n=4
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for BTC-USD (1826 bars). Signal: sma_cross (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.

### `crypto_cross_momentum_multi_v1` (xai)
  - entry: long the top 2 performers of ['BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'XRP-USD'] based on 6-month momentum
  - exit: exit and rebalance monthly if a coin drops out of top 2 based on 6-month momentum
  - sizing: equal 50% allocation to each of the top 2 coins, rebalanced monthly
  - universe: ['BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'XRP-USD']
  - regime: skip (go to cash) when average 30-day realized volatility of universe > 80%
  - P3: PF=1.79 WR=31.2% MDD=59.4% Sharpe=0.4 n=32
  - P4: INDEPENDENT (max|ρ|=0.0 vs (no shipped strategies found))
  - notes: v3a REAL — yfinance prices for BTC-USD (1826 bars). Signal: momentum (keyword-routed from spec.entry). LLM-driven signal translation queued for v3b.


## Tier-2 floor (CLAUDE.md MAJOR GOAL)

PF ≥ 1.5, WR ≥ 50%, MDD < 20%, n ≥ 100 trades.

## Your mandate

Vote GO / MIXED / NO_EDGE per candidate. For GO verdicts, draft a Wiring Plan (per CLAUDE.md Wire-Up Rule) — what file gets the caller, what trust_score to seed, what feature flag gates it.

If most candidates fail T2 floor (esp. n<100), the run-level verdict should be MIXED or NO_EDGE — DO NOT fabricate GO just because backtest PF is high. n<30 is too small for any reliable verdict; flag as "needs longer history" rather than GO.

## Output schema (JSON-strict)

```json
{
  "schema_version": "v1",
  "engine": "<your name>",
  "asset_class": "CRYPTO",
  "run_id": "run_2026-08-08T06-17-31Z",
  "synthesis": [
    {
      "spec_id": "<from list above>",
      "verdict": "GO|MIXED|NO_EDGE",
      "rationale": "1-3 sentences citing PF/WR/MDD/n + cross-test + simplified-signal caveat",
      "wiring_plan": "if GO: paste-ready 1-paragraph wiring plan. else empty string."
    }
  ],
  "run_verdict": "GO|MIXED|NO_EDGE",
  "run_rationale": "1-paragraph overall — what edge surfaced (if any), what's blocked on n / faithful-signal, retry conditions"
}
```

Return ONLY the JSON object. No prose preamble, no markdown fence.
