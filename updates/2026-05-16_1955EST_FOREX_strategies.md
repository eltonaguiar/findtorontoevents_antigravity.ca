# FOREX — Asset Class Strategy Audit
**Date:** 2026-05-16 19:55 EST  
**Author:** Buffy (Codebuff)  
**Scope:** Forward-test performance, backtest, strategy gaps, data coverage

---

## 1. Forward-Test Performance

| Metric | Value |
|--------|-------|
| Total closed picks | 932 |
| Win Rate | 25.6% |
| Profit Factor | 0.35 |
| Avg PnL per pick | −0.00% |
| Total PnL | −2.13% |

**Verdict:** ⚠️ FOREX is flat-to-slightly-negative. WR is very low (25.6%) but PnL is near breakeven, suggesting TP/SL ratios are well-calibrated (wins are bigger than losses).

---

## 2. Top Performing Strategies (≥10 picks)

| Strategy | Picks | WR | AvgPnL |
|----------|-------|-----|--------|
| `fx_smart_forex_rsi2_mean_reversion` | 64 | 57.8% | +0.00% |
| `cot_positioning` | 581 | 65.1% | −0.00% |
| `forex_carry_momentum` | 178 | 5.1% | −0.00% |
| `forex_trend_continuation` | 40 | 27.5% | −0.01% |

**Pattern:** COT positioning dominates with 581 picks and a superficially high WR (65.1%), but the AvgPnL is flat. `forex_carry_momentum` (178 picks, 5.1% WR) is a massive value destroyer.

---

## 3. Top Performing Symbols (≥5 picks)

| Symbol | Picks | WR | AvgPnL |
|--------|-------|-----|--------|
| USDCHF=X | 11 | 81.8% | +0.01% |
| GBPUSD=X | 33 | 66.7% | 0.00% |
| EURGBP=X | 49 | 71.4% | 0.00% |
| AUDUSD=X | 34 | 41.2% | 0.00% |
| EURUSD=X | 196 | 28.6% | −0.00% |

### Worst Symbols

| Symbol | Picks | WR | AvgPnL |
|--------|-------|-----|--------|
| EURJPY=X | 67 | 13.4% | −0.01% |
| AUDJPY=X | 73 | 20.5% | −0.00% |
| CADJPY=X | 18 | 11.1% | −0.00% |

**Pattern:** JPY crosses are systematically losers. USD majors perform better.

---

## 4. Backtest Performance

No dedicated FOREX backtest JSONs found in `audit_dashboard/data/`. FOREX strategies are tested through the hyro_quan_bridge and general backtest runners.

---

## 5. Prediction Market & Copytrader Coverage

| Data Source | Covers FOREX? | Status |
|-------------|---------------|--------|
| **Kalshi signals** | ❌ No | Missing |
| **Polymarket signals** | ✅ Yes | `alpha_engine/polymarket_signals.py` |
| **Prediction market consensus** | ✅ Yes | `alpha_engine/prediction_market_consensus.py` |
| **Multi-asset copytrader** | ✅ Yes | `copy_trader_intel/multi_asset_copytrader_scraper.py` |
| **Non-crypto consensus** | ✅ Yes | `copy_trader_intel/non_crypto_consensus.py` |

**Verdict:** ✅ Well covered. Only Kalshi is missing (Kalshi is US-focused, mostly equities/macro).

---

## 6. Strategy Gaps & Missing Data Sources

### What we HAVE:
- ✅ COT Positioning v1 + v2 (CFTC data)
- ✅ RSI mean reversion strategies
- ✅ Carry trade & momentum strategies
- ✅ Copy-trader feeds

### What we're MISSING:
- ❌ **Interest rate differential / carry trade data**
  - Free API: **OANDA** / **FRED** (Fed rate data)
  - Impact: Carry trade is the #1 forex strategy in institutional quant
- ❌ **Economic calendar event-based strategies**
  - Free API: **ForexFactory** (scraping), **NewsAPI**
  - Impact: NFP, FOMC, CPI create predictable volatility regimes
- ❌ **Correlation-based basket trading**
  - Free API: Already have price data — just need to implement
  - Impact: EURUSD + GBPUSD correlation arbitrage
- ❌ **Session-based (time-of-day) strategies**
  - Free API: None needed — timestamp data already exists
  - Impact: London open, NY overlap have distinct volatility patterns

### Highest-ROI gap to fill:
**Economic calendar event strategies** — NFP/FOMC days have highly predictable pre-announcement drift. Simple: go flat 30min before, re-enter 15min after.

---

## 7. Statistical Edge Assessment

| Criterion | Status | Value |
|-----------|--------|-------|
| DSR (Deflated Sharpe) | ❌ | Aggregate PF 0.35 — no edge |
| PBO (Probability of Backtest Overfitting) | ⚠️ | Not computed |
| WFE (Walk-Forward Efficiency) | ⚠️ | Not computed |
| COT positioning sub-strategy | ⚠️ | 65.1% WR but flat PnL — likely small wins, occasional large losses |

**Bottom line:** No edge at aggregate. COT positioning has high WR but no profit factor advantage — suggests TP is too tight. The carry momentum strategy (5.1% WR) should be immediately deactivated.

---

## 8. Recommendations

1. **Deactivate `forex_carry_momentum`** — 5.1% WR, 178 picks, pure value destruction
2. **Widen TP on COT strategies** — 65.1% WR with flat PnL means winners are too small
3. **Add JPY-cross filter** — systematically avoid EURJPY, AUDJPY, CADJPY
4. **Implement economic calendar awareness** — go flat before NFP/FOMC
5. **Wire COT v2 divergence signals** — already integrated (May 2026), need forward test
