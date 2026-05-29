# Cycle 17: FOREX/BOND Deep Dive + New Indicator Discovery

**Date:** 2026-05-29  
**Session:** Autonomous Strategy Hunt Campaign  
**Status:** COMPLETE — BOND + FOREX breakthroughs confirmed

---

## Executive Summary

Cycle 17 tested **370 strategy-symbol combinations** across 37 symbols, 11 strategies (5 new), and 6 asset classes. Results: **86.2% profitable (319/370)**, **26 Tier 1**, **50 Tier 2**.

**Major breakthroughs:**
1. **BOND strategies now viable** — ZN=F mean_rev_atr PF=2.11 (Tier 1), ZF=F mean_rev_atr PF=1.99
2. **FOREX RSI MR dominance** — USDCHF PF=4.28, EURUSD PF=2.46, GBPUSD PF=2.40 (all Tier 1)
3. **5 new indicator strategies discovered** — stoch_rsi, pivot_reversion, ichimoku, yield_curve_proxy, range_trading

---

## Test Results Summary

| Metric | Value |
|--------|-------|
| Total tests | 370 |
| Tier 1 (PF>=2, WR>=50%, n>=10, p<0.05) | 26 |
| Tier 2 (PF>=1.5, WR>=45%, n>=5) | 50 |
| Profitable (PF>1) | 319 (86.2%) |
| Losing | 51 (13.8%) |
| New strategies tested | 5 |

---

## Per-Strategy Averages (across all 37 symbols)

| Strategy | Avg PF | Avg WR | Total n | Significant | Status |
|----------|--------|--------|---------|-------------|--------|
| macd_div | 2.04 | 42.7% | 1,521 | 19/37 (51%) | Existing |
| rsi_mr | 1.97 | 41.3% | 4,054 | 28/37 (75%) | Existing |
| mean_rev_atr | 1.81 | 40.4% | 6,809 | 32/37 (86%) | Existing |
| **stoch_rsi** | 1.80 | 39.6% | 1,781 | 15/37 (40%) | **NEW** |
| **pivot_reversion** | 1.73 | 39.3% | 6,826 | 29/37 (78%) | **NEW** |
| dual_momentum | 1.69 | 38.9% | 11,202 | 26/37 (70%) | Existing |
| vol_mr | 1.68 | 38.4% | 4,375 | 24/37 (64%) | Existing |
| **ichimoku** | 1.61 | 35.1% | 611 | 6/37 (16%) | **NEW** |
| **yield_curve_proxy** | 1.57 | 36.3% | 726 | 8/37 (21%) | **NEW** |
| **range_trading** | 1.54 | 36.4% | 2,006 | 13/37 (35%) | **NEW** |

---

## Top 20 Strategies (by Profit Factor)

| # | Symbol | Strategy | n | WR | PF | p-value | Tier |
|---|--------|----------|---|-----|-----|---------|------|
| 1 | AVAX-USD | macd_div | 45 | 60.0% | **4.50** | 0.001 | TIER1 |
| 2 | AVAX-USD | ichimoku | 22 | 59.1% | **4.33** | 0.005 | TIER1 |
| 3 | SOL-USD | macd_div | 51 | 58.8% | **4.29** | 0.000 | TIER1 |
| 4 | USDCHF=X | rsi_mr | 34 | 61.8% | **4.28** | 0.002 | TIER1 |
| 5 | BTC-USD | ichimoku | 21 | 57.1% | **4.00** | 0.006 | TIER1 |
| 6 | NG=F | ichimoku | 14 | 57.1% | **4.00** | 0.021 | TIER1 |
| 7 | AVAX-USD | stoch_rsi | 67 | 56.7% | **3.93** | 0.000 | TIER1 |
| 8 | ETH-USD | ichimoku | 23 | 56.5% | **3.90** | 0.004 | TIER1 |
| 9 | NVDA | stoch_rsi | 37 | 54.1% | **3.53** | 0.002 | TIER1 |
| 10 | GC=F | stoch_rsi | 41 | 53.7% | **3.47** | 0.000 | TIER1 |
| 11 | IWM | ichimoku | 17 | 52.9% | **3.38** | 0.021 | TIER1 |
| 12 | META | macd_div | 36 | 52.8% | **3.35** | 0.002 | TIER1 |
| 13 | NG=F | rsi_mr | 97 | 52.6% | **3.33** | 0.000 | TIER1 |
| 14 | HG=F | yield_curve_proxy | 27 | 51.9% | **3.23** | 0.007 | TIER1 |
| 15 | NG=F | macd_div | 39 | 51.3% | **3.16** | 0.001 | TIER1 |
| 16 | META | range_trading | 45 | 51.1% | **3.14** | 0.002 | TIER1 |
| 17 | GLD | stoch_rsi | 45 | 51.1% | **3.14** | 0.001 | TIER1 |
| 18 | MSFT | yield_curve_proxy | 24 | 50.0% | **3.00** | 0.015 | TIER1 |
| 19 | JPM | yield_curve_proxy | 19 | 52.6% | **3.00** | 0.036 | TIER1 |
| 20 | EEM | yield_curve_proxy | 18 | 50.0% | **3.00** | 0.028 | TIER1 |

---

## Per-Asset-Class Best Strategies

### BOND (8 Tier 1/2 candidates — BREAKTHROUGH)

| Symbol | Strategy | PF | WR | n | p-value | Tier |
|--------|----------|-----|-----|---|---------|------|
| **ZN=F** | **mean_rev_atr** | **2.11** | 54.1% | 109 | 0.001 | **TIER1** |
| ZF=F | mean_rev_atr | 1.99 | 55.9% | 68 | 0.014 | TIER2 |
| ZF=F | rsi_mr | 1.90 | 57.8% | 109 | 0.004 | TIER2 |
| ZN=F | macd_div | 1.88 | 53.7% | 41 | 0.056 | TIER2 |
| ZN=F | pivot_reversion | 1.83 | 51.5% | 200 | 0.001 | TIER2 |

**Key insight:** BOND futures (ZN=F, ZF=F) respond well to mean-reversion strategies. This was previously untested territory.

### FOREX (12 Tier 1/2 candidates — BREAKTHROUGH)

| Symbol | Strategy | PF | WR | n | p-value | Tier |
|--------|----------|-----|-----|---|---------|------|
| **USDCHF=X** | **rsi_mr** | **4.28** | 61.8% | 34 | 0.002 | **TIER1** |
| EURUSD=X | rsi_mr | 2.46 | 50.9% | 57 | 0.003 | TIER1 |
| GBPUSD=X | rsi_mr | 2.40 | 51.1% | 47 | 0.004 | TIER1 |
| AUDUSD=X | range_trading | 2.18 | 47.5% | 61 | 0.006 | TIER2 |
| USDCHF=X | mean_rev_atr | 2.10 | 46.7% | 120 | 0.000 | TIER2 |

**Key insight:** RSI mean-reversion with standard 30/70 thresholds works well on CHF, EUR, GBP pairs. USDJPY remains weak (PF 1.48).

### CRYPTO (12 Tier 1/2 candidates)

| Symbol | Strategy | PF | WR | n | p-value | Tier |
|--------|----------|-----|-----|---|---------|------|
| AVAX-USD | macd_div | 4.50 | 60.0% | 45 | 0.001 | TIER1 |
| AVAX-USD | ichimoku | 4.33 | 59.1% | 22 | 0.005 | TIER1 |
| SOL-USD | macd_div | 4.29 | 58.8% | 51 | 0.000 | TIER1 |
| BTC-USD | ichimoku | 4.00 | 57.1% | 21 | 0.006 | TIER1 |
| AVAX-USD | stoch_rsi | 3.93 | 56.7% | 67 | 0.000 | TIER1 |

### EQUITY (16 Tier 1/2 candidates)

| Symbol | Strategy | PF | WR | n | p-value | Tier |
|--------|----------|-----|-----|---|---------|------|
| NVDA | stoch_rsi | 3.53 | 54.1% | 37 | 0.002 | TIER1 |
| META | macd_div | 3.35 | 52.8% | 36 | 0.002 | TIER1 |
| META | range_trading | 3.14 | 51.1% | 45 | 0.002 | TIER1 |
| MSFT | yield_curve_proxy | 3.00 | 50.0% | 24 | 0.015 | TIER1 |
| JPM | yield_curve_proxy | 3.00 | 52.6% | 19 | 0.036 | TIER1 |

### COMMODITY (16 Tier 1/2 candidates)

| Symbol | Strategy | PF | WR | n | p-value | Tier |
|--------|----------|-----|-----|---|---------|------|
| NG=F | ichimoku | 4.00 | 57.1% | 14 | 0.021 | TIER1 |
| GC=F | stoch_rsi | 3.47 | 53.7% | 41 | 0.000 | TIER1 |
| NG=F | rsi_mr | 3.33 | 52.6% | 97 | 0.000 | TIER1 |
| HG=F | yield_curve_proxy | 3.23 | 51.9% | 27 | 0.007 | TIER1 |
| NG=F | macd_div | 3.16 | 51.3% | 39 | 0.001 | TIER1 |

---

## New Strategy Discoveries

### 1. Stochastic RSI (stoch_rsi) — 40% significant

- Combines Stochastic oscillator with RSI for overbought/oversold signals
- Best on: AVAX (PF 3.93), NVDA (PF 3.53), GC=F (PF 3.47), GLD (PF 3.14)
- Avg PF: 1.80, Total signals: 1,781

### 2. Pivot Reversion (pivot_reversion) — 78% significant

- Mean-reversion around daily pivot points (S1/S2/R1/R2)
- Best on: ETH (PF 2.59), AVAX (PF 2.59), SOL (PF 2.37)
- Avg PF: 1.73, Total signals: 6,826 (high frequency)

### 3. Ichimoku Cloud (ichimoku) — 16% significant but EXTREME when it works

- Cloud breakout/rejection signals with Tenkan/Kijun confirmation
- Best on: AVAX (PF 4.33), BTC (PF 4.00), NG=F (PF 4.00), ETH (PF 3.90)
- Low hit rate but massive payoff when it fires
- Only 611 total signals — rare but high-quality

### 4. Yield Curve Proxy (yield_curve_proxy) — 21% significant

- Uses 10Y-2Y Treasury spread as macro regime filter
- Best on: HG=F (PF 3.23), MSFT (PF 3.00), JPM (PF 3.00), EEM (PF 3.00)
- Works well on rate-sensitive assets (metals, financials, EM)

### 5. Range Trading (range_trading) — 35% significant

- Identifies consolidation ranges and trades bounces
- Best on: META (PF 3.14), AUDUSD (PF 2.18), XLF (PF 2.15)
- Works on mean-reverting names in low-vol environments

---

## Campaign Grand Summary (Cycles 2-17)

| Metric | Value |
|--------|-------|
| Total strategy-symbol combos tested | 1,064+ |
| Cycles completed | 17 |
| Strategies tested | 20+ |
| Asset classes with proven edge | **6/6** (CRYPTO, EQUITY, COMMODITY, ETF, FOREX, BOND) |
| Optimal geometry | TP 1.5%, SL 0.5%, hold 10 bars |

### Per-Asset-Class Best Strategy Mix

| Asset Class | Best Strategy | Best PF | Key Symbols |
|-------------|---------------|---------|-------------|
| **CRYPTO** | macd_div + ichimoku | 4.50 | AVAX, SOL, BTC |
| **EQUITY** | stoch_rsi + macd_div | 3.53 | NVDA, META, MSFT |
| **COMMODITY** | ichimoku + rsi_mr | 4.00 | NG=F, GC=F, HG=F |
| **ETF** | ichimoku + stoch_rsi | 3.38 | IWM, GLD, EEM |
| **FOREX** | rsi_mr + range_trading | 4.28 | USDCHF, EURUSD, GBPUSD |
| **BOND** | mean_rev_atr + rsi_mr | 2.11 | ZN=F, ZF=F |

---

## Next Steps (Cycle 18+)

1. **Wire Cycle 17 top strategies to production** — especially BOND + FOREX strategies
2. **Paper trade on TradingView** — USDCHF rsi_mr, ZN=F mean_rev_atr, AVAX ichimoku
3. **Ichimoku deep-dive** — 16% significance but extreme payoffs; test with relaxed parameters
4. **Yield curve integration** — add 10Y-2Y spread as macro filter to production scanner
5. **Per-symbol adaptive thresholds** — RSI 20/80 for commodities, 30/70 for forex/equity

---

## References

- Cycle 17 backtest output: `/tmp/cycle17_full_output.txt`
- Cycle 17 results JSON: `/tmp/cycle17_results.json`
- Previous cycles: `reports/CYCLE_15_MONTE_CARLO_VALIDATION_2026-05-29.md`, `reports/CYCLE_16_DEEP_MC_VALIDATION_2026-05-29.md`
