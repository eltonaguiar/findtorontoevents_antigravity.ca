# Profitability Strategies — final_v2

**Date:** 2026-11-14 | **Worktree:** flaxen-hair

This document synthesizes all research into actionable profitability strategies per asset class, ranked by probability of success.

## Executive Summary

**Only ONE approach has demonstrated genuine, forward-validated edge: mega_mutation_macd_rsi / ema_momentum on CRYPTO.** All other asset classes show negative edge after PnL normalization and rigorous statistical testing (23 hypotheses, NONE PROVED).

The profitability research program exhausted the keyless data hypothesis space. To find new edges, we need:
- Intraday/order-book data
- Options/vol-risk-premium data
- Venue-level capital/margin data
- Private/proprietary data

---

## Tier 1: ACTIVE — Mega Mutation on Crypto (Forward Edge Confirmed)

### Strategy: mega_mutation_macd_rsi / ema_momentum

**Asset class:** Crypto | **Status:** Forward-validated, production-enabled

**Evidence:**
| Metric | Backtest | Forward (live since 2026-06-06) |
|--------|----------|----------------------------------|
| Profit Factor | 3.12–5.816 | **8.32** |
| Win Rate | 64–76% | **84%** |
| Trades | 100–593 | **50** |
| Statistical validation | — | Paired bootstrap pass_95=True (m048/m084), MC pct=0.949 |

**8 verified combos:**
| Mutation | Symbol | Primary | TP_ATR | SL_ATR | Tour PF | Tour WR |
|----------|--------|---------|--------|--------|---------|---------|
| macd_rsi_m048 | JUPUSDT | MACD_RSI | 2.2 | 1.2 | 6.44 | 85.7% |
| macd_rsi_m084 | ENAUSDT | MACD_RSI | 2.2 | 1.4527 | 8.28 | 83.3% |
| macd_rsi_m017 | ADAUSDT | MACD_RSI | 2.2 | 1.2 | 3.72 | 77.8% |
| macd_rsi_m048 | WIFUSDT | MACD_RSI | 2.2 | 1.2 | 4.00 | 80.0% |
| macd_rsi_m048 | STXUSDT | MACD_RSI | 2.2 | 1.2 | 4.88 | 83.3% |
| macd_rsi_m048 | RENDERUSDT | MACD_RSI | 2.2 | 1.2 | 4.08 | 87.5% |
| ema_momentum_m006 | AVAXUSDT | EMA_CROSS | 1.1429 | 1.2 | 4.66 | 87.5% |
| ema_momentum_m006 | DOTUSDT | EMA_CROSS | 1.1429 | 1.2 | 3.75 | 85.7% |

**Gates (8 total):**
1. Symbol whitelist — only the 8 tournament-validated combos
2. Entry conditions — exact tournament genes (MACD crossover + RSI filter, or EMA cross + RSI range)
3. TP/SL — ATR multiples from tournament genes
4. Position sizing — 2% risk per trade on $10k equity
5. Correlation limit — max 1 position per correlated group
6. Regime filter — BTC must be above 200-EMA (bull regime only)
7. Min edge — tournament PF >= 2.0
8. Dedup — composite key on symbol/direction/entry/TP/SL/date

**Implementation:** `quick_wins/shared/gated_scanner.py` + `quick_wins/shared/daily_forward_tracker.py`

**Production status:** `production_enable = true`, `promotion_ready = true`, no blockers

**Next steps:**
- Paper trade daily via gated scanner
- Accumulate n=100 forward picks for T2 confirmation (currently n=50)
- Investigate ENA funding-rate collinearity
- Monitor regime: BTC 200-EMA filter

---

## Tier 2: EXPLORATORY — H10 RSI(2) on SPY/QQQ (Needs Clean Forward OOS)

### Strategy: RSI(2) + T-bill Cash on SPY/QQQ

**Asset class:** Stocks/Equity | **Status:** Exploratory, NOT_PROVED, needs clean forward

**Evidence (retrospective, contaminated OOS):**
- OOS Sharpe 1.83, CAGR 22.0% vs 18.6% B&H
- OOS max drawdown: -7.6% vs -21.0% B&H
- 111 trades over 2024-01-01..2026-11-13
- DSR 0.978 (N=12), p-value 0.00194

**Why NOT_PROVED:**
1. OOS contamination — H10 is a cash-added variant of H7 created after H7's OOS was inspected
2. Effective multiple testing — N≈38 (27-cell parameter grid), DSR 0.9365 < 0.95
3. Single-day dependence — 2025-04-09 = +11.20% in one day; removing it drops DSR to 0.8993
4. Execution fragility — 1-day lag drops Sharpe to 0.696
5. Regime dependence — lags in low-vol bull years (2019, 2021, 2023)
6. Edge largely T-bill carry — +3.6pp CAGR ≈ 0.827 × 4.38% cash yield

**Clean forward test protocol:**
- Start: first signal after 2026-11-13
- Minimum: 90 calendar days or 30 round trips
- Frozen parameters: RSI(2) entry <10, exit >50, max hold 5 days, 5 bps costs, idle cash at 13-week T-bill
- Stricter gates: DSR ≥0.95 after N≥38, DSR ≥0.95 after removing best day, 2-day-lag Sharpe ≥1.0
- Risk-matched benchmark gate (not just B&H)

**Implementation:** `research/profitability/backtest.py` with frozen H10 parameters, forward ledger at `research/profitability/forward/ledger.csv`

---

## Tier 3: NEW HYPOTHESES (Untested Asset Classes)

### Bonds — Zero Coverage

**No bond-specific profitability hypotheses tested.**

**Proposed strategies:**
1. **Bond ETF TSMOM** — TLT, IEF, SHY, TBT with 12-month lookback, monthly rebalancing
2. **Bond dual momentum** — Bonds vs T-bills based on 12-month momentum
3. **Treasury carry** — Short-term Treasuries vs longer-duration bonds

**Data needed:** Treasury.gov yields, Nasdaq ETF prices (already available)

**Risk model:** Interest rate risk, lower volatility but lower returns

---

### Mutual Funds — Zero Coverage

**No mutual fund data source or algorithm exists.**

**Proposed strategies:**
1. **Mutual fund dual momentum** — Monthly NAV-based rebalancing across equity, bond, balanced, international categories
2. **Mutual fund sector rotation** — Rotate between fund categories based on momentum

**Data needed:** Mutual fund NAV feed (CSV/JSON), yfinance fallback

**Implementation:** Add MUTUAL_FUND to `alpha_engine/config.py` asset_class enum, create `alpha_engine/mutual_fund_strategies.py`

**Risk:** NAV lag (same-day price not available until after market close)

---

### Forex — Zero Coverage

**No forex-specific profitability hypotheses tested.**

**Proposed strategies:**
1. **Forex carry trade** — High-yield currency (AUD, NZD) vs low-yield (JPY, CHF)
2. **Forex trend following** — Major pairs (EUR/USD, USD/JPY, GBP/USD) with 200-day SMA filter
3. **Forex mean reversion** — RSI(2) < 30 on oversold pairs

**Data needed:** Forex price feed (er-api, yfinance)

**Risk:** High leverage risk; position sizing limits essential

---

### Commodities/Futures — Zero Coverage

**No commodity/futures profitability hypotheses tested.**

**Proposed strategies:**
1. **Commodity TSMOM** — GC=F, SI=F, CL=F, ZN=F, NG=F with 12-month lookback
2. **Agricultural seasonality** — Planting/harvest cycle patterns
3. **Futures roll yield** — Contango/backwardation capture

**Data needed:** Futures price feed, COT data

**Risk:** High volatility, roll risk, position limits needed

---

## Cross-Cutting Risk Management (All Strategies)

| Rule | Specification | Source |
|------|---------------|--------|
| Position sizing | Max 2% risk per trade | TradingView contest research |
| Kelly Criterion | 0.25×–0.5× full Kelly | TradingView contest research |
| Daily loss cap | -5% | TradingView contest research |
| Monthly loss cap | -20% | TradingView contest research |
| Correlation limit | Max 1 per correlated group | TradingView contest research |
| Regime filter | BTC > 200-EMA (crypto); SPY > 200-SMA (equity) | mega_mutation_gated_scanner |
| Stop loss | Technical-level (swing low/high) | TradingView contest research |
| Losing streak | 3 losses → stop session | TradingView contest research |
| DSR gate | ≥0.95 | finpredict-v4 scoring framework |
| Bootstrap CI | PF_lower > 1.0 | finpredict-v4 scoring framework |
| Walk-forward | ≥60% profitable folds, mean OOS PF > 1.2 | finpredict-v4 scoring framework |

---

## What Does NOT Work (Definitive)

| Strategy | Asset Class | Reason |
|----------|-------------|--------|
| Crypto momentum/reversal (30 pairs) | Crypto | SPA p=0.488, negative CAGR |
| ETF momentum/reversal (50 ETFs) | ETFs | Underperforms benchmark |
| Equity RSI(2) standalone | Stocks | Fails absolute return vs B&H |
| Sector RSI(2) + trend + cash | Stocks | DSR 0.603 |
| International RSI(2) + cash | Stocks | Sharpe 0.31 |
| Peer VWAP mean reversion | Crypto | FALSIFIED (annualization error, PBO not PBO, DSR not DSR, intrabar stops PF 0.81) |
| TradingView contest winner methods | All | Survivorship bias, not repeatable |

---

## Decision Matrix: Which Strategy to Trade?

| Criterion | mega_mutation (Crypto) | H10 RSI(2) (Equity) | Funding Carry (Crypto) | New Asset Classes |
|-----------|----------------------|---------------------|------------------------|-------------------|
| Forward edge confirmed | YES (84% WR, PF 8.32) | NO (retrospective only) | PARTIAL (DSR 1.0) | NO (untested) |
| Statistical validity | PARTIAL (pass_95=True) | NO (contaminated OOS) | NO (n=10 <30) | NO |
| Production ready | YES | NO | NO | NO |
| Data availability | YES (Binance API) | YES (Nasdaq) | YES (Binance funding) | PARTIAL |
| Capital efficiency | HIGH | MEDIUM | LOW (capital-intensive) | UNKNOWN |
| Recommended action | **PAPER TRADE NOW** | Clean forward test | Monitor | Develop hypotheses |
