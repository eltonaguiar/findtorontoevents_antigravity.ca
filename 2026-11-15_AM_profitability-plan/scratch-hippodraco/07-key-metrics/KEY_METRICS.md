# Key Metrics That Must Be Satisfied — Multi-Perspective View
**Date:** 2026-11-15  
**Purpose:** Define the bar a strategy/asset class must clear before any capital is deployed.  
**Core rule (money-maker-ready):** Every performance claim must carry `(asset_class \| n \| timeframe)`. All 9 classes currently return `sizing_allowed: false`; **no class is promoted until it clears these gates on clean out-of-sample forward data.**

---

## 1. The master gate (non-negotiable)

A class/strategy is **not** profitable until it passes ALL of the following on **clean, cost-adjusted, out-of-sample forward data** (not backtest, not dashboard headline):

| Metric | Threshold | Why |
|--------|-----------|-----|
| n resolved (forward/OOS) | ≥ 100 (Tier 2) / ≥ 500 (Tier 1) | Small-n leads dissolve as n grows; CRYPTO n=1154 & EQUITY n=107 both FAIL despite n≥100 |
| Profit Factor (after costs) | ≥ 1.5 | Below 1.5 = edge indistinguishable from noise once estimator drifts |
| Win Rate (EXPIRED-inclusive) | ≥ 50% | Below coin-flip after costs = structural loser |
| Max Drawdown | ≤ 20% (default); COMMODITY ≤ 55% override | Permanent capital-loss control |
| Net expectancy after costs | > 0 | Must be economically positive, not just statistically |
| Information Coefficient | ≠ ≈0 | Currently ≈0 across all 23 hypotheses — no predictive signal |
| DSR | ≥ 0.95 with correct `nb_trials` | Corrects for all strategies tested that season (not nb_trials=1) |
| SPA family-wise | p ≤ 0.10 | Controls false discovery across the strategy family |
| PBO | ≤ 0.55 (requires ≥5 strategies) | Controls backtest overfit |
| Cost multiple | mean pnl_pct ≥ 3× round-trip cost | Survives cost model being wrong by half |
| Benchmark (SPY total return for equity/ETF) | Beat on OOS | Edge must exceed passive beta, not just be positive |

**Current state:** 0/9 classes money-ready; 0/23 hypotheses survived all gates. **Do not deploy capital.**

---

## 2. Metric definitions (formulas)

| Metric | Formula | Perspective |
|--------|---------|-------------|
| **Win Rate** | WON / (WON + LOST + EXPIRED + FLAT) | All — EXPIRED counts as non-win (old formula dropped EXPIRED and inflated FX from true ~6% to displayed 58.8%) |
| **Profit Factor** | Σ(gross profit) / \|Σ(gross loss)\| | All — gross, not net of costs until stated |
| **Net Expectancy** | adj_win × WR − adj_loss × (1 − WR) after per-class slippage bps | Pro investor / bank trader — must be > 0 after realistic costs |
| **Sharpe Ratio** | mean(r) / sd(r) × √trades_per_year_class | All — **never √252 on per-trade returns** unless exactly one trade/trading day |
| **Sortino Ratio** | mean(r) / sd_negative(r) × √trades_per_year_class | Pro investor — downside deviation only |
| **Calmar Ratio** | CAGR / \|Max DD\| | Mutual fund manager — return per unit of worst drawdown |
| **Max Drawdown** | Peak→trough on cumulative PnL, % of peak | Bank trader — permanent capital loss tolerance |
| **CVaR-95 / ES-99.5** | Mean of returns below 5th percentile | Risk manager — tail loss expectation |
| **Information Coefficient** | Rank correlation of predicted vs actual returns | Quant — currently ≈0; no signal |
| **DSR (Deflated Sharpe)** | Bailey & López de Prado, correct `nb_trials` | Quant — multiple-testing correction |
| **PBO (Probability of Backtest Overfit)** | ≤ 0.55 | Quant — overfit control |
| **Kelly Fraction** | (p×b − q) / b, capped at 0.25× (¼ Kelly) | Position sizing — bank trader / fund manager |
| **Concentration** | Top symbol ≤ 60% (COMMODITY ≤85%); top source ≤ 40% (COMMODITY ≤60%) | Risk manager — single-name / single-source bet control |

---

## 3. How different professionals weigh these metrics

### 3.1 The Quant / Data Scientist (information coefficient + DSR + PBO)
**Primary question:** "Is there any real signal, or is this overfitting noise?"
- **Information Coefficient ≈ 0** → reject immediately (no predictive signal; current state of this system across all 23 hypotheses)
- **DSR ≥ 0.95 with correct nb_trials** → required (corrects for all strategies tested that season)
- **PBO ≤ 0.55** → required if ≥5 strategies tested
- **SPA family-wise p ≤ 0.10** → required
- **Walk-forward stability** → WR/PF must not swing wildly across 2d/7d/30d windows
- **Red flag:** "90.5% WR / Sharpe 97" from a genetic-programming run (DARWIN engine) with direction oscillating run-to-run = regime-transition signature, not edge

### 3.2 The Pro Investor / Hedge Fund PM (expectancy + drawdown + capacity)
**Primary question:** "Can I size this and survive the worst month?"
- **Net expectancy after costs > 0** → required (must be economically positive)
- **Max Drawdown ≤ 20%** → required (capital preservation)
- **Calmar Ratio** → return per unit of worst drawdown
- **Sortino** → downside-only risk (more relevant than Sharpe for asymmetric strategies)
- **Capacity-aware** → does the edge degrade at larger size? (most small-n crypto edges do)
- **¼ Kelly sizing** → cap position size; never full Kelly on an unproven edge
- **Red flag:** PF 21.33 on `multi_asset_cot` (likely one-symbol CT=F concentration artifact); −64.1pp July drawdown in Variant C

### 3.3 The Mutual Fund Manager (beta capture + cost + tracking error)
**Primary question:** "Can I beat the benchmark after fees, consistently, for clients?"
- **Beat SPY total return (equity/ETF) or BTC-USD (crypto) or flat cash (FX direction)** on clean OOS — edge must exceed passive beta, not just be positive
- **Expense ratio ≤ 0.10–0.20%** for any MF/ETF sleeve; high AUM; low turnover (≤20%/yr); R² ≥ 0.99 vs index
- **Tracking error** vs stated benchmark must be justified by alpha, not hidden factor bets
- **Long horizon** (10+ years) — broad index funds have historically been positive; month-to-month is a coin flip
- **Red flag:** Claiming "mutual funds are winners" without NAV infrastructure, class registration, or clean OOS — MF is allocation/cost discipline, not ML prediction

### 3.4 The Bank's Top Stock Trader (execution + fill reality + risk limits)
**Primary question:** "Can I actually fill this at the stated price, and what's my daily loss limit?"
- **Execution-realistic fills** — assumes real slippage, intrabar TP-before-SL (26.4% of crypto TP_HITs hit SL first), not end-of-bar ideal pricing
- **Daily soft-stop: −2% total PnL triggers pause** (Hyro/prop overlay)
- **Rolling 30-day drawdown halt: >30% → pause all sizing**
- **Position sizing 1–2% risk per trade** max; quarter-Kelly
- **Concentration caps** — top symbol ≤60%, top source ≤40%
- **Blank-field / stale-price rejection** — no trading on unpriced picks (87.4% of `active_raw` has blank `current_price`)
- **Red flag:** "81% fake 0% PnL" — picks with exit==entry stamped same second; fabricated flats

---

## 4. Asset-class-specific thresholds (per money-maker-readyv2 success criteria)

| Class | n target | WR target | PF target | Notes |
|-------|----------|-----------|-----------|-------|
| EQUITY | ≥ 500 forward | ≥ 55% | ≥ 1.5 | vs SPY total return; only proven sleeve: `stocks_rsi2_pullback` |
| ETF | ≥ 150 | ≥ 55% | ≥ 1.3 | Expand universe XLF/XLE/XLK; cleanest OOS profile |
| CRYPTO | ≥ 100 | ≥ 50% | ≥ 1.5 | After OHLCV backfill ≥180d 1h + intrabar replay |
| COMMODITY | ≥ 50 post-dedup | ≥ 50% | ≥ 1.5 | Real feed only; no crypto proxies |
| BOND | ≥ 100 eventually | ≥ 50% | ≥ 1.5 | FRED unblock; n currently 18 |
| FOREX | ≥ 100 | ≥ 50% | ≥ 1.5 | After spread-aware costs; currently blocked |
| MUTUAL FUND | ≥ 100 forward | ≥ 50% | ≥ 1.5 | Only after class registration + NAV source |
| PENNY / MEME | — | — | — | Blocked / quarantined |

---

## 5. The "outperform S&P 500 / outperform buy & hold" bar (previously missed)

This was a gap in earlier analysis. Any equity/ETF claim must answer:

| Question | Required evidence |
|----------|-------------------|
| Does the strategy beat **SPY total return** (not price-only) over the same window? | Pre-registered OOS test; report excess return + t-stat |
| Does it beat **buy & hold** of the same universe? | Same-entry-date buy-and-hold comparison; report alpha |
| Is the excess return **cost-adjusted**? | Deduct per-class slippage/commissions before comparing |
| Is it **risk-adjusted**, not just raw return? | Report Sharpe/Sortino/Calmar vs benchmark |
| Does it survive **multiple-testing**? | Correct nb_trials; DSR≥0.95 |

**Honest statement:** No strategy in this system has yet demonstrated a clean, cost-adjusted, out-of-sample beat of SPY total return. Variant C (equity/ETF walk-forward) shows PF 1.26 / +98.7pp over 8 months but PF < 1.5 and WR < 50% — **not yet T2-certified**. Until it clears SPY on clean OOS with published n, the "boring alternative" (buy-and-hold low-cost index) remains the higher-probability lower-risk deployment.

---

## 6. Metric red flags (auto-reject)

| Red flag | Example from this system |
|----------|-------------------------|
| Information Coefficient ≈ 0 | All 23 hypotheses, 4 protocol versions |
| nb_trials = 1 | Treats class aggregate as one strategy |
| Sharpe uses √252 on per-trade returns | Wrong unless exactly 1 trade/trading day |
| EXPIRED dropped from WR denominator | Inflated FX from true ~6% to 58.8% |
| Best-of-thousands reported as single test | Multiple-testing trap; DSR collapses |
| PF > ~10 | Likely corrupt/outlier pnl_pct rows (CADJPY +428%) |
| Direction oscillates run-to-run | DARWIN engine regime-transition signature |
| n < 100 or single-snapshot | Not statistically meaningful |
| "Smart Picks WR 78.9%" vs raw DB 39.4% | Single-source concentration (100% alpha_engine) |

---

## 7. Bottom line

A strategy is **ready for capital** only when it:
1. Clears every metric in §1 on **clean, cost-adjusted, out-of-sample forward data**,
2. Beats a **transparent benchmark** (SPY total return for equity/ETF, BTC-USD for crypto, flat cash for FX),
3. Is sized at **¼ Kelly or lower** with **DD-halt** rules,
4. And is monitored against **pre-registered kill criteria**.

Until then — and currently **no class qualifies** — the highest-probability lower-risk capital deployment is **low-cost diversified index ETFs/mutual funds**, with the research system running as a paper-pilot satellite under strict gates.

---
