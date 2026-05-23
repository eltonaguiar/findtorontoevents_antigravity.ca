# CRYPTO — Asset Class Strategy Audit
**Date:** 2026-05-16 19:55 EST  
**Author:** Buffy (Codebuff)  
**Scope:** Forward-test performance, backtest, strategy gaps, data coverage

---

## 1. Forward-Test Performance

| Metric | Value |
|--------|-------|
| Total closed picks | 6,884 |
| Win Rate | 32.8% |
| Profit Factor | 0.41 |
| Avg PnL per pick | −0.15% |
| Total PnL | −1,056.83% |

**Verdict:** ❌ CRYPTO is deeply unprofitable in forward testing. The aggregate scoring is inversely correlated with real-money performance (the bug that the May 2026 strategy-family fix addresses).

---

## 2. Top Performing Strategies (≥15 picks)

Only 11 of 160 crypto strategies have positive AvgPnL:

| Strategy | Picks | WR | AvgPnL | In PROVEN? |
|----------|-------|-----|--------|------------|
| `ml_enhanced_FETUSDT_1d_B_lightgbm` | 44 | 56.8% | +0.17% | ✅ PROVEN_WINNERS (boost 15) |
| `ml_enhanced_INJUSDT_1d_B_lightgbm` | 28 | 96.4% | +0.14% | ❌ (prefix match via CRYPTO_PROVEN_PREFIXES) |
| `ml_enhanced_BNBUSDT_15m_B_lightgbm` | 19 | 89.5% | +0.05% | ✅ PROVEN_WINNERS (boost 5) |
| `ml_enhanced_RENDERUSDT_1h_D_ensemble_stack` | 47 | 61.7% | +0.03% | ❌ (prefix match) |
| `ml_enhanced_RENDERUSDT_4h_D_ensemble_stack` | 37 | 56.8% | +0.02% | ❌ (prefix match) |
| `ml_enhanced_DYDXUSDT_15m_D_ensemble_stack` | 31 | 96.8% | +0.02% | ❌ (prefix match) |
| `macd_crossover` | 16 | 68.8% | +0.02% | ❌ |

**Pattern:** `ml_enhanced_*` strategies dominate the positive performers. The new CRYPTO_PROVEN_PREFIXES automatically grants these +20 boost.

### Worst Strategies (should be TOXIC)

| Strategy | Picks | WR | AvgPnL |
|----------|-------|-----|--------|
| `ml_enhanced_TRXUSDT_1d_B_lightgbm` | 26 | 11.5% | −0.64% |
| `volume_spike_breakout` | 78 | 16.7% | −0.40% |
| `quan_engine_scalp` | 5,293 | 29.9% | −0.18% |
| `macd_rsi_confluence` | 66 | 36.4% | −0.17% |

`macd_rsi_confluence` is already in CRYPTO_TOXIC_STRATEGIES (-15 penalty). `quan_engine_scalp` (5,293 picks!) and `volume_spike_breakout` are NOT penalized but should be.

---

## 3. Top Performing Symbols (≥5 picks)

| Symbol | Picks | WR | AvgPnL |
|--------|-------|-----|--------|
| FETUSDT | 75 | 61.3% | +0.11% |
| INJUSDT | 56 | 50.0% | +0.07% |
| LINKUSDT | 5 | 80.0% | +0.05% |
| ZROUSDT | 5 | 40.0% | +0.04% |
| ENJUSDT | 9 | 88.9% | +0.03% |

### Worst Symbols

| Symbol | Picks | WR | AvgPnL |
|--------|-------|-----|--------|
| KATUSDT | 5 | 0.0% | −0.42% |
| ONDOUSDT | 5 | 20.0% | −0.38% |
| TREEUSDT | 5 | 0.0% | −0.31% |

---

## 4. Backtest Performance

| Backtest | WR | PF | Max DD |
|----------|-----|-----|--------|
| Hyro backtest new strategies | 60 items | Various | Various |
| Hyro extended results | 3 items | — | — |

**Note:** Crypto backtests are run through `hyro_backtest_new_strategies.json` and hyro_quan_bridge. No standalone per-strategy backtest JSONs found for crypto.

---

## 5. Prediction Market & Copytrader Coverage

| Data Source | Covers CRYPTO? | Status |
|-------------|---------------|--------|
| **Kalshi signals** | ✅ Yes | `alpha_engine/kalshi_signals.py` (27KB) |
| **Polymarket signals** | ✅ Yes | `alpha_engine/polymarket_signals.py` (29KB) |
| **Polymarket BTC up/down agent** | ✅ Yes | `prediction_market_agents/polymarket_btc_updown_agent.py` (11KB) |
| **Polymarket momentum agent** | ✅ Yes | `prediction_market_agents/polymarket_momentum_agent.py` (4KB) |
| **Prediction market consensus** | ✅ Yes | `alpha_engine/prediction_market_consensus.py` (25KB) |
| **Multi-asset copytrader** | ✅ Yes | `copy_trader_intel/multi_asset_copytrader_scraper.py` (102KB) |
| **Polymarket copytrader scraper** | ✅ Yes | `copy_trader_intel/polymarket_scraper.py` (60KB) |

**Verdict:** ✅ CRYPTO is the **best-covered** asset class for external data. No gaps.

---

## 6. Strategy Gaps & Missing Data Sources

### What we HAVE:
- ✅ ml_enhanced_* ML strategies (strongest performers)
- ✅ COT positioning (commodity but some crypto cross-over)
- ✅ Fear & Greed contrarian strategies
- ✅ Copy-trader feeds (HL, OKX, Bybit, BingX, PM)
- ✅ Prediction market consensus (Kalshi + Polymarket)
- ✅ Kelly position sizing
- ✅ Hedge fund quality gate
- ✅ Funding rate arbitrage scanner

### What we're MISSING:
- ❌ On-chain data (whale wallets, exchange flows, stablecoin mint/burn)
  - Free API: **Glassnode free tier**, **CryptoQuant** (limited free)
  - Impact: Could detect accumulation/distribution before price moves
- ❌ Open interest / liquidation heatmap
  - Free API: **Coinglass** (already have `coinglass_db.json` but not wired to scoring)
  - Impact: Liquidation cascades are major reversal signals
- ❌ Social sentiment (Twitter/X, Reddit, Telegram)
  - Free API: **LunarCrush** free tier
  - Impact: Meme coin pumps often precede by social volume spikes
- ❌ Options flow / Deribit data
  - Free API: **Deribit** public API
  - Impact: Max pain, gamma exposure levels

### Highest-ROI gap to fill:
**Coinglass liquidation data** — already in the repo (`coinglass_db.json`, 27MB) but not wired to `smart_picks_engine.py` scoring. Liquidations >$10M in 5min are extremely reliable reversal signals.

---

## 7. Statistical Edge Assessment

| Criterion | Status | Value |
|-----------|--------|-------|
| DSR (Deflated Sharpe) | ❌ | Aggregate PF 0.41 — no edge |
| PBO (Probability of Backtest Overfitting) | ⚠️ | Not computed for crypto |
| WFE (Walk-Forward Efficiency) | ⚠️ | Not computed on closed picks |
| Top-strategy edge (FETUSDT) | ⚠️ | +0.17% per trade, 44 picks — small sample |

**Bottom line:** No statistical edge at the aggregate level. Individual `ml_enhanced_*` strategies on specific symbols show promise but insufficient sample size for DSR > 0.95 confidence. Need 200+ trades per symbol/strategy combo to validate.

---

## 8. Recommendations

1. **Expand CRYPTO_TOXIC_STRATEGIES** — add `quan_engine_scalp` (5,293 picks, −0.18% AvgPnL) and `volume_spike_breakout` (78 picks, −0.40% AvgPnL)
2. **Wire Coinglass liquidation data** into `smart_picks_engine.py` as a reversal signal
3. **Add on-chain flow data** (Glassnode free tier) for whale accumulation detection
4. **Increase minimum trade count** for PROVEN status — 15 picks is too few for statistical significance
5. **Enable PER_CLASS_ML_ENFORCE** for crypto to hard-filter low-quality ML picks
