# ASSET CLASS ANALYSIS BY HOLDING PERIOD vs TRADING STYLE

**Worktree:** flaxen-hair_2026-11-15T0020 | **Date:** 2026-11-15T00:27Z | **Repo:** findtorontoevents_antigravity.ca

---

## Executive Summary

**No trading style is proven profitable in this system.** Day trading and scalping have the WORST economics due to costs + multiple testing penalties. Long-term holding of quality assets has the highest probability of positive expected returns but is NOT alpha — it is market beta.

The analysis below breaks down each asset class by holding period and trading style, with cost-adjusted reality checks.

---

## Trading Style Definitions

| Style | Typical Hold | Typical Trades/Month | Cost Impact | Profitability Evidence |
|-------|-------------|---------------------|-------------|----------------------|
| Scalping | Seconds to minutes | 10-50+ per day | CRITICAL (spread + commission eat all edge) | NOT proven anywhere |
| Day Trading | Minutes to hours (flat by close) | 5-20 per day | HIGH (commissions + slippage) | NOT proven anywhere |
| Swing Trading | Days to weeks | 2-8 per month | MODERATE | EQUITY Connors RSI2 shows promise |
| Position Trading | Weeks to months | 1-3 per month | LOW | EQUITY shows some signal |
| Long-Term Investing | Months to years | 0-2 per year | MINIMAL | ETF TAA validated smart-beta |

---

## Asset Class by Trading Style

### CRYPTO

| Style | Evidence | Verdict |
|-------|----------|---------|
| Scalping | 700+ strategies tested, ALL fail clean-cohort screen | NOT viable |
| Day Trading | n=1154 clean, WR 32.4%, PF 0.73 | NOT viable |
| Swing Trading | Entry_price ~29% clean, ~90% positions never resolve | NOT viable until fill fix |
| Position Trading | Same data issues as above | NOT viable |
| Long-Term Holding | No long-term crypto strategy tested | NOT tested |

**Bottom Line:** Crypto cannot be traded profitably in this system until entry_price integrity (~29% clean) is fixed AND positions are resolved.

---

### EQUITY (US)

| Style | Evidence | Verdict |
|-------|----------|---------|
| Scalping | Not tested; costs would dominate | NOT recommended |
| Day Trading | connors_rsi2_scanner shows promise on intraday but n too small | NOT yet viable |
| Swing Trading | connors_rsi2_scanner WR 75.7%, vix_spike_reversal_scanner WR 72% | PROMISING (slot 2) |
| Position Trading | t=1.52, p=0.12 (not statistically significant) | Needs more data |
| Long-Term Holding | SPY/QQQ buy-and-hold is the baseline benchmark | Benchmark |

**Best Style:** Swing trading with Connors RSI2 on SPY/QQQ, but must pass pre-registered test vs SPY total return.

---

### ETF

| Style | Evidence | Verdict |
|-------|----------|---------|
| Scalping | Not tested; costs would dominate | NOT viable |
| Day Trading | All 9 ETF hypotheses NOT_PROVED | NOT viable |
| Swing Trading | Best walk-forward (100% consistency, WR 75%, decay +23%) but n=88-100 at floor | PROMISING but needs n≥150 |
| Position Trading | Tactical Asset Allocation (monthly rebalance) | VALIDATED smart-beta |
| Long-Term Holding | Buy-and-hold broad index ETFs | Benchmark |

**Best Style:** Monthly tactical asset allocation (top-5 ETFs by 6-month momentum). This is NOT alpha — it is smart-beta crash avoidance.

---

### FOREX

| Style | Evidence | Verdict |
|-------|----------|---------|
| Scalping | Zero DSR survivors | NOT viable |
| Day Trading | Zero DSR survivors | NOT viable |
| Swing Trading | Zero DSR survivors | NOT viable |
| Position Trading | Zero DSR survivors | NOT viable |
| Long-Term Holding | Zero DSR survivors | NOT viable |

**Bottom Line:** No forex trading style is profitable in this system. Apply mutation-before-kill protocol.

---

### COMMODITY / FUTURES

| Style | Evidence | Verdict |
|-------|----------|---------|
| Scalping | Not tested; costs prohibitive | NOT viable |
| Day Trading | Not tested | NOT viable |
| Swing Trading | cot_positioning family PF 21.33 on n=144 (likely CT=F concentration) | Suspect — needs DB verification |
| Position Trading | Commodity momentum strategies untested cleanly | NOT viable |
| Long-Term Holding | No long-term commodity strategy | NOT tested |

**Bottom Line:** Commodity COT data needs verification. Recent-HF window PF 1.09 (near break-even). Not yet viable.

---

### BOND

| Style | Evidence | Verdict |
|-------|----------|---------|
| Scalping | Not tested | NOT viable |
| Day Trading | Not tested | NOT viable |
| Swing Trading | n=11-18, below min_trades=60 | NOT viable yet |
| Position Trading | n=11-18 | NOT viable yet |
| Long-Term Holding | Not tested | NOT tested |

**Bottom Line:** Bond data too sparse. Requires FRED API key + BOND scanner + more data.

---

### MUTUAL FUNDS

| Style | Evidence | Verdict |
|-------|----------|---------|
| All styles | Zero infrastructure exists | NOT a prediction class |

**Bottom Line:** Mutual funds are NOT a prediction class. Do not build mutual fund prediction. Hold low-cost index mutual funds as core allocation instead.

---

## Trading Style Performance Summary

| Style | Best Asset Class | Best PF | Best WR | Recommendation |
|-------|-------------|---------|---------|----------------|
| Scalping | None | N/A | N/A | DO NOT TRADE |
| Day Trading | None | N/A | N/A | DO NOT TRADE |
| Swing Trading | EQUITY (Connors RSI2) | 3.23× cost margin | 75.7% | PROMISING (slot 2) |
| Position Trading | EQUITY | Positive cost margin | +0.323% mean | NEEDS VALIDATION |
| Long-Term Holding | ETF (SPY/QQQ) | Market beta | Market return | CORE ALLOCATION |

**Recommendation:**
1. **Core:** Low-cost diversified ETFs/mutual funds (buy-and-hold)
2. **Satellite:** EQUITY swing trading (Connors RSI2) — only after pre-registered test passes
3. **Do NOT trade:** Crypto day/swing, Forex any style, Futures, Memecoin, Penny

---

## Top Algorithms by Trading Style

### Swing Trading (Days to Weeks)

| Algorithm | Asset Class | Claimed WR | Claimed PF | Status |
|-----------|-------------|------------|------------|--------|
| Connors RSI2 | EQUITY (SPY/QQQ) | 75.7% | Not independently verified | PROMISING sleeve |
| VIX Spike Reversal | EQUITY (SPX) | 72% | Not independently verified | PROMISING sleeve |
| EMA-9 Crypto System | CRYPTO | Not verified | Not verified | FAILED clean screen |
| Hamilton Dynamic | Various | Not verified | Not verified | NOT tested |

### Position Trading (Weeks to Months)

| Algorithm | Asset Class | Claimed WR | Claimed PF | Status |
|-----------|-------------|------------|------------|--------|
| ETF Dual Momentum | ETF | 75% (walk-forward) | Not independently verified | PROMISING |
| Faber Tactical | ETF | Not verified | Not verified | NOT verified |
| Sector Rotation | EQUITY/ETF | Not verified | Not verified | NOT verified |

### Long-Term Holding (Months to Years)

| Algorithm | Asset Class | Evidence |
|-----------|-------------|----------|
| Buy-and-Hold SPY | EQUITY | Market return (benchmark) |
| Tactical Asset Allocation | ETF | Sharpe 0.88 vs SPY 0.74, MaxDD −19% vs SPY −51% |
| 60/40 Stock/Bond | MULTI-ASSET | Standard benchmark |

---

## TradingView / Trading Contest Winners

**Important:** TradingView contest winners are **survivorship bias**, NOT proof of repeatable method. Winners are selected from thousands of participants. Do NOT copy contest methods without statistical validation.

**Famous Contest-Winning Approaches (for reference only, not endorsement):**

| Trader/Style | Asset Class | Claimed Performance | Reality Check |
|-------------|-------------|---------------------|---------------|
| Hoffman (Eugene Hoffman) | Various | Various | No verifiable clean data in this repo |
| Various TradingView Champions | Crypto/Forex/Equity | 73-91% WR claimed | Single-snapshot/MISPRICED_ENTRY artifacts; ~50% picks still OPEN |
| Various Pine Script authors | Various | Various | No independent verification |

**Critical:** All contest performance figures are forward-test on small samples (28-89 resolved picks). Institutional-grade requires n≥100 resolved + OOS stability. None of the TradingView contest winners in this system meet that bar.

---

## Holding Period Recommendations by Asset Class

| Asset Class | Recommended Holding Period | Reason |
|-------------|---------------------------|--------|
| CRYPTO | Do not trade (fill bug unresolved) | Data integrity prevents any holding period |
| EQUITY | Swing (days-weeks) or Long-term (years) | Connors RSI2 swing; SPY long-term |
| ETF | Monthly rebalance (TAA) | Smart-beta works at monthly frequency |
| FOREX | Do not trade | Zero DSR survivors |
| COMMODITY | Do not trade (data insufficient) | n too small |
| BOND | Do not trade (data insufficient) | n too small |
| FUTURES | Do not trade | Dead |
| MUTUAL FUNDS | Do not trade (not a prediction class) | Hold low-cost index funds instead |

---
