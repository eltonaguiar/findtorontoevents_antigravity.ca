# PROFITABILITY FRAMEWORK — Complete Asset Class Analysis & Profit Path

**Worktree:** flaxen-hair_2026-11-15T0020 | **Date:** 2026-11-15T00:20Z | **Repo:** findtorontoevents_antigravity.ca

This document synthesizes ALL findings from:
- ALL_STRATEGIES.md (700+ strategies across 12 asset class categories)
- money-maker-ready / money-maker-readyv2 / money-maker-ready-June112026edition / money-maker-ready-July112026edition skills
- 2026-05-13-money-maker-action-plan.md
- 2026-05-11-money-maker-master-plan.html
- All 16 peer_claude-phase10b-money-maker reports (EQUITY, ETF, FOREX, BOND, COMMODITY, CRYPTO, FUTURES, PENNY)
- All previous final_v2/final_v4 audit findings
- Current local + remote GitHub state (2026-11-14)

---

## PART 1 — Every Asset Class Attempted to Be Predicted

Based on ALL_STRATEGIES.md and all money-maker skill files, here is the complete inventory:

### 1. CRYPTO (Most extensively covered — 700+ strategies)
**Location:** `alpha_engine/crypto_strategies.py`, `KIMI_RISEOFTHECLAW/`, `ml_crypto_predictor/`, `crypto_ml_edge/`, `mercury2/`, `claude_gainer_ml/`, `coinglass_strategies/`, `ml_battleground/`

**Sub-categories (19+):**
- Baby Strategies (77) — mean reversion, trend, breakout, ML ensemble
- Alpha Engine — Core Crypto (36) — RSI, MACD, Wyckoff, SMC, funding rate, liquidation cascade
- Alpha Engine — On-Chain (10) — MVRV, hash ribbon, NVT, fear/greed
- Alpha Engine — Quant (4) — TSMOM, cointegrated pairs, momentum/MR blend
- Alpha Engine — Advanced (13) — vol risk premium, dynamic momentum scaling, Kalman filter
- Alpha Engine — Event-Driven (8) — token unlock, liquidation cascade, exchange netflow
- Alpha Engine — Proven Research (10) — VWAP trend bounce, Hoffman EMA IRB, statistical pairs
- Alpha Engine — Proven Scanner (6) — Keltner squeeze, triple EMA pullback, VWAP MR
- Alpha Engine — Hybrid (7) — Hurst + volume profile, multi-sigma EMA stack
- Alpha Engine — Mercury AI (5) — Hurst regime, VWAP MR, funding term structure
- Alpha Engine — Cerebrus AI (6) — relative strength pair, funding carry pro, MVRV contrarian
- Alpha Engine — Untapped Alpha (8) — max pain gravitational, put/call contrarian, Google trends
- Alpha Engine — Market Microstructure (4) — options skew, Coinbase premium, perpetual basis
- Alpha Engine — Exchange Flow (1) — exchange reserve decline
- Alpha Engine — NextGen (13) — cointegration pair trade, ADX vol breakout, seasonal factor
- Alpha Engine — Next Gen Signals (6) — VWAP reversion, fear/greed contrarian
- Alpha Engine — Super Strategies (10) — Keltner EMA momentum, HMA breakout
- Alpha Engine — Survivor Strategies (5) — Connors R3 survivor, Keltner MR survivor
- Alpha Engine — Opposite Day (5) — overbought reversal short, crowd contrarian
- Alpha Engine — Variation Strategies (3) — Keltner HMA filter, multi-sigma volume
- Alpha Engine — Antigravity Strategies (4) — VWAP RSI institutional, liquidation cascade contrarian
- Alpha Engine — Statistical Strategies (10) — multi-sigma reversal, O-U process, Hurst adaptive
- Alpha Engine — Pattern Strategies (9) — fractal SR bounce, double top/bottom, head & shoulders
- Alpha Engine — Cyclical Strategies (9) — halving cycle, monthly seasonality, Halloween effect
- Alpha Engine — Enhanced Strategies (6) — RSI MR optimized, Connors RSI2, anti-confluence
- Alpha Engine — Experimental (4) — adaptive VR confluence, MACD RSI multi-TF
- Alpha Engine — Justin Bravo (12) — EMA-9 crypto system, Bravo nine count
- Alpha Engine — Orderbook (1) — order book imbalance
- Alpha Engine — Community (11) — EMA 9/21 + RSI, BB squeeze, RSI extreme reversal
- Alpha Engine — TradingView (15) — AlphaTrend, WaveTrend, Williams VIX Fix, TSI, QQE Mod
- Alpha Engine — Basis & Prop (8) — funding rate arb, basis trade, Connors RSI2 prop
- Alpha Engine — Specialty (5) — TVL momentum, momentum rider, cyclic streak, Hoffman trend
- Alpha Engine — New (5) — rectangle breakout, pin bar continuation, ML breakout gate
- KIMI Rise of the Claw — Crypto Acceleration (10) — pump detector, Telegram caller, Twitter alpha
- KIMI Rise of the Claw — Proven Crypto/Forex (14) — BTC 4h RSI MACD, weekly structure
- Coinglass DNA Bundle (13) — extreme reversion, whale divergence, ratio momentum
- ML Battleground — 5 Trading Systems (A-E) — filter, regime, deep learn, carry, momentum
- Crypto ML Edge — scanner, trainer, gainer detector, labeler, stationarity, validation
- Mercury2 Ensemble — scanner, ensemble, trainer, features, risk engine, top gainer
- Crypto Signal Engine — engine, trainer, features, risk engine
- ML Crypto Predictor — production engine, base/ensemble/scalping/swing models
- Claude Gainer ML — live scanner, train model, token sniffer, self-improver
- Root-Level Crypto Strategies — momentum scalping, opposite day, live spike, spike predictor
- AI-Generated Incubator Strategies (320+) — Web AI (175), Codex GPT-5 (44), Cursor AI (35)

**Status:** n=1154 clean, WR 32.4%, PF 0.73 (NOT money-ready). Measurement broken — entry_price ~29% clean, ~90% positions never resolve.

---

### 2. EQUITY & OPTIONS
**Location:** `alpha_engine/equity_strategies.py`, `strategy_2_theta_options.py`, `theta_strategy.py`, root-level equity scripts

**Strategies (14 Alpha Engine + options):**
- momentum_factor_12m (Stocks)
- penny_volume_breakout (Micro-caps)
- meme_social_velocity (Meme stocks)
- quality_value_composite (Large-caps)
- intermarket_risk_on (SPY/QQQ)
- support_resistance_bounce (Stocks)
- connors_rsi2_scanner (SPY/QQQ) — WR 75.7%
- triple_rsi_scanner (Stocks)
- vix_spike_reversal_scanner (SPX) — WR 72%
- turn_of_month_scanner (SPY/QQQ)
- earnings_gap_reversal_scanner (Stocks)
- gap_reversal_tech_stocks (Tech)
- Options: 0DTE scalping (1m/5m/15m/1h/4h), theta decay v1/v2

**Root-level:** Larry Williams volatility breakout, Mark Minervini trend template, Marty Schwartz day trading, Canada-focused bot, high Sharpe portfolio

**Status:** Only class with positive cost margin (3.23×, mean +0.323%, n=738). But t=1.52, p=0.12 (not statistically significant yet). Connors RSI2 is the sole proven sleeve.

---

### 3. FOREX
**Location:** `alpha_engine/forex_strategies.py`

**Strategies (12):**
- carry_trade_momentum (Major pairs)
- forex_mean_reversion_200d (EURUSD, GBPUSD)
- jpy_risk_off (USDJPY, EURJPY)
- dxy_correlation_regime (DXY-correlated)
- forex_bollinger_squeeze (Major pairs)
- session_momentum_continuation (London/NY)
- dxy_rsi_mean_reversion (Dollar pairs)
- sunday_night_gap_trade (Major pairs)
- session_volatility_expansion (Major pairs)
- forex_tsmom_12m (Major pairs)
- forex_logistic_direction (Major pairs)
- forex_rsi2_mean_reversion (Major pairs)

**Baby/Forex rehab:** ForexBbMrRehabV1 (EUR/GBP/AUD USDT proxies), PaxgBollingerMrRehab (tokenized gold)

**Status:** WR 46.2%, PF 0.29 (stressed). SHORT-axis 57% WR vs LONG 21% on ig_contrarian_sentiment (36pp spread) but NO strategy passes DSR ≥ 0.5. Zero DSR survivors.

---

### 4. ETF
**Location:** Various across alpha_engine

**Strategies (9):**
- etf_dual_momentum
- etf_sector_momentum
- etf_faber_tactical
- etf_rsi2_pullback
- etf_sector_dual_momentum
- etf_cross_sectional_momentum
- Plus sector rotation strategies

**Status:** All 9 hypotheses NOT_PROVED. Best walk-forward (100% consistency, WR 75%, decay +23%). n=88-100 at floor. Need universe expansion to XLF/XLE/XLK. WR range 2.22% → 68.42% across files (85× spread — measurement inconsistency).

---

### 5. BOND
**Location:** `alpha_engine/` bond strategies

**Strategies:** treasury_yield_curve, credit_spread_strategy, duration_rotation, bond_equity_rotation, treasury_yield_momentum, bond_duration_rotation, bond_tlt_ief_momentum

**Status:** n=11-18 (thin), WR 54.5%, PF 0.66. n below min_trades=60. Requires BOND scanner + FRED data unblock. No bond mutual fund data feed.

---

### 6. COMMODITY
**Location:** `alpha_engine/commodity_futures_strategies.py`

**Strategies:** futures_momentum, cot_positioning, commodity_momentum, futures_mean_reversion, treasury_yield_curve, credit_spread_strategy

**Status:** WR 67.8%, PF 3.94 (cumulative, but propped up by multi_asset_cot PF 21.33 on n=144 — likely CT=F cotton concentration). Recent-HF window PF 1.09. COT contrarian failed all 4 pre-registered checks. n≈27 post-filter (HG=F only). n below min_trades=60.

---

### 7. FUTURES
**Location:** Various

**Status:** Dead. 0 picks. WR 5.9%, PnL -96%. Needs re-emission plan or formal retirement.

---

### 8. MEMECOIN
**Status:** Quarantined (29 strategies, PF 0.50 over 1,869 trades). Class-wide blocked.

---

### 9. PENNY
**Status:** Deep oversold BLOCKED by Gate 0. n=8, WR 28.57%.

---

### 10. MUTUAL FUNDS — ZERO COVERAGE
**Status:** No algorithms, no data source, no asset class registration, no scanner, no strategies. NOT a prediction class — it is the equity risk premium.

---

## PART 2 — Which Asset Classes Have Highest Probability of Profitability with Lower Risk

Based on ALL verified data across every money-maker file, ALL_STRATEGIES.md, and all audits:

### Ranking by Profitability Probability

| Rank | Asset Class | PF | WR | MDD | Sharpe | Status | Recommendation |
|------|-------------|-----|-----|-----|--------|--------|----------------|
| **1** | **ETF TAA** | N/A (blend) | N/A | **−19%** | **0.88** | **PROVEN smart-beta** | **PRIMARY TRACK** |
| **2** | **EQUITY** | 3.23× cost | +0.323% | — | — | Positive cost margin | SECONDARY RESEARCH |
| **3** | **CRYPTO** | 0.73-1.36 | 32-46% | 100% | — | Conditional | CONDITIONAL (fill fix first) |
| 4 | COMMODITY | 1.04-3.94 | 50-67% | — | — | Propped up by cot_positioning | BLOCKED |
| 5 | FOREX | 0.077-0.29 | 24-46% | — | — | Zero DSR survivors | BLOCKED |
| 6 | BOND | 0.66-1.72 | 54-55% | — | — | n=1-18, thin | BLOCKED |
| 7 | FUTURES | — | 5.9% | -96% | — | Dead | RETIRE |
| 8 | MEMECOIN/PENNY | 0.50 | 28-34% | — | — | Quarantined | BLOCKED |

### Key Insights

**ETF Tactical Asset Allocation (TAA) — THE ONLY VALIDATED APPROACH:**
- Top-5 asset-class ETFs by 6-month momentum, monthly, abs-momentum filter → bonds
- Universe: 14 liquid free ETFs (yfinance)
- 2007-2026 (incl 2008 GFC): Sharpe 0.88 vs SPY 0.74, MaxDD −19% vs SPY −51%, Calmar 0.48 vs 0.21
- ALL 16 (top-N × lookback) grid cells cut MaxDD to −12/−17% vs SPY −24%
- 9-month region: Sharpe 1.09-1.21 / Calmar 0.81-1.10 vs SPY 1.00/0.68
- Positive all 3 time-thirds (both-halves stability)
- **Smart-beta, NOT alpha** — matches market return with ~half the drawdown
- In-sample-robust → forward-track, don't over-size

**EQUITY — Secondary research track:**
- Only class with positive cost margin (3.23×, mean +0.323%)
- Connors RSI2 is the sole proven sleeve (WR 75.7%)
- t=1.52, p=0.12 (not statistically significant — needs more n)
- Second-half PF fell 1.342 → 0.977 (regime risk)

**CRYPTO — Conditional, not deployable yet:**
- 700+ strategies tested, ALL fail clean-cohort screen
- n=1154, WR 32.4%, PF 0.73
- Root cause: entry_price ~29% clean, systematically biased +1.3%, ~90% positions never resolve
- Must re-resolve from bar-aligned NEXT-bar entries before any edge can be verified
- Open backlog is systematic losers (dead end)

---

## PART 3 — Profitability Framework

Based on everything learned, here is the complete framework for finding profitability:

### Phase 1: Measurement Infrastructure (Weeks 1-2) — MUST DO FIRST

**All current PnL/WR numbers are untrustworthy due to measurement defects.**

| # | Fix | File | Priority |
|---|-----|------|----------|
| 1 | Enable promotion gates (FDR + single-source) | alpha_engine/money_ready_verdict.py | P0 |
| 2 | Close cost gate fail-open paths | alpha_engine/per_class_cost_gate.py | P0 |
| 3 | Stop suppressing after-cost errors | audit_trail/dashboard_generator.py | P0 |
| 4 | Add weekly/monthly loss limits | alpha_engine/risk_controls.py | P0 |
| 5 | Fix entry_price integrity (~29% clean) | alpha_engine/risk_controls.py | P0 |
| 6 | Re-resolve entries from bar-aligned NEXT-bar | tools/reresolve_intrabar.py | P0 |
| 7 | Fix PnL unit normalization (ratio vs percent, 100×) | quick_wins/shared/normalize_pnl_units.py | P0 |
| 8 | Fix pick ID uniqueness | quick_wins/shared/validate_pick_ids.py | P0 |

### Phase 2: Build Mutual Fund + ETF Infrastructure (Weeks 2-4) — PRIMARY TRACK

**Mutual funds have ZERO coverage. ETFs have 9 NOT_PROVED hypotheses.**

| # | New File | Purpose |
|---|----------|---------|
| 1 | alpha_engine/mutual_fund_ranker.py | Rank MF by solid-pick criteria |
| 2 | alpha_engine/data/mutual_fund_metadata.csv | Fund metadata (ER, load, 12b-1, min, AUM, turnover, category, benchmark, inception) |
| 3 | audit_dashboard/data/mutual_fund_nav_cache/ | NAV CSV cache (one per fund) |
| 4 | audit_dashboard/data/mf_backtest_cache/ | MF backtest result cache |
| 5 | audit_dashboard/data/mf_cache_manifest.json | SHA-256 provenance manifest |
| 6 | tools/mf_traits_walkforward_runner.py | MF walkforward runner |
| 7 | tools/mf_walkforward_backtest.py | MF walkforward backtest |
| 8 | tools/mf_trait_features.py | MF trait feature computation |
| 9 | alpha_engine/mutual_fund_strategies.py | MF strategy stubs (NAV-based monthly rebalance) |

**Modify:**
- alpha_engine/asset_class.py — Add MUTUAL_FUND_SYMBOLS, CAT_MAP, is_mutual_fund()
- ml_gatekeeper/gatekeeper.py — Add "MUTUAL_FUND": 7 to ASSET_CLASS_MAP
- audit_trail/dashboard_generator.py — Add mutual fund dashboard bucket

**Mutual Fund Solid Pick Criteria (ALL must pass):**
| Criterion | Threshold |
|-----------|-----------|
| Expense ratio | ≤ 0.20% |
| Load fees | None |
| 12b-1 fees | None |
| Minimum investment | ≤ $1,000 |
| AUM | ≥ $1B |
| Turnover | ≤ 20% |
| Tracking error | ≤ 0.25% |
| Track record | ≥ 10 years |
| Net return > benchmark | 5+ years net of fees |
| NAV freshness | ≤ 24h |

**ETF Solid Pick Criteria:**
| Criterion | Threshold |
|-----------|-----------|
| Expense ratio | ≤ 0.10% |
| AUM | ≥ $500M |
| Avg daily volume | ≥ $10M |
| Bid-ask spread | ≤ 0.05% |
| Tracking error | ≤ 0.20% |
| Track record | ≥ 5 years |
| No leverage / no inverse | Plain beta only |
| Net return > benchmark | 3+ years after costs |

---

### Phase 3: Benchmark Tests (Weeks 4-8)

| Asset Class | Test | Benchmark | Gate |
|-------------|------|-----------|------|
| **ETF** | Tactical Asset Allocation vs SPY | SPY total return | Sharpe ≥ SPY Sharpe, MaxDD ≤ SPY MaxDD |
| **EQUITY** | Connors RSI2 vs SPY | SPY total return | OOS Sharpe ≥ SPY Sharpe AND PF ≥ 1.15 |
| **CRYPTO** | POSITION horizon forward test | BTC-USD | PF ≥ 1.3, WR ≥ 55%, n ≥ 100 |

**Go/No-Go at Week 8:** If ETF TAA and EQUITY both fail pre-registered tests, keep both blocked and preserve passive benchmark sleeve.

---

### Phase 4: Risk Management & Live Capital (Weeks 9-13)

**Position Sizing:**
| Parameter | Conservative | Moderate | Aggressive |
|-----------|-------------|----------|------------|
| Risk per trade | 1.0% | 1.5% | 2.0% |
| Kelly fraction | 0.25 | 0.25 | 0.25 |
| Max single position | 3% | 4% | 5% |
| Max crypto allocation | 10% | 15% | 20% |

**Drawdown Controls:**
| Horizon | Threshold | Action |
|---------|-----------|--------|
| Daily | -2% | Block new picks |
| Weekly | -5% | 48h halt |
| Monthly | -10% | Full halt |
| Quarterly | -15% | Strategy reset |

**Risk-Adjusted Return Thresholds:**
| Metric | Minimum | Target |
|--------|---------|--------|
| Sharpe Ratio | > 0.5 | > 1.0 |
| Sortino Ratio | > 1.0 | > 2.0 |
| Calmar Ratio | > 0.5 | > 1.0 |
| Max Drawdown | < 15% | < 10% |
| Deflated Sharpe | ≥ 0.95 | ≥ 0.95 |

---

## PART 4 — Separate Risk Management Webpage

**File:** `risk_dashboard.html` (standalone, under `audit_dashboard/`)

**Sections:**
1. Portfolio Health Gauge (equity curve, drawdown gauge, VaR, CVaR)
2. Drawdown Controls Progress Bars (daily/weekly/monthly)
3. Position Sizing Table (Kelly %, position %, risk $, ATR stop, regime)
4. Correlation Heatmap (asset correlation matrix)
5. Risk-Adjusted Returns Table (Sharpe, Sortino, Calmar, PSR, Max DD, verdict)
6. Kill Switch Status (level, multiplier, auto-recovery)
7. QA Alerts (PnL=0%, blank fields, open items)

**Data:** `alpha_engine/data/risk_metrics.json` generated by `tools/risk_dashboard_data.py`

**Refresh:** Every 60 seconds

---

## PART 5 — What NOT to Do

| Tempting Action | Why Not |
|-----------------|---------|
| Deploy mega-mutation crypto forward picks | 21/50 may be synthetic/replay; aggregate uses different row sets |
| Tune commodity COT until it passes | Failed all 4 pre-registered checks |
| Add mutual funds as prediction class | Equity risk premium, not signal; structurally untradeable as picks |
| Mine more strategies | 170 ledgers sampled; 4 pass at 95% vs 8.5 by chance |
| Fix FOREX entries to close 16pp gap | Structural problem |
| Turn on more emitting systems | Sizing disabled everywhere for a reason |
| Re-enable push trigger on audit-dashboard.yml | Known cancel-cascade risk |

---

## PART 6 — Go/No-Go Decision

**NO-GO for live capital deployment today.**

**Conditions to revisit:**
1. Measurement gates pass (cohort_id, filter hash, source timestamp, row-level denominator)
2. Promotion gates fail closed (FDR + single-source enabled)
3. EQUITY pre-registered test: vs SPY, n≥500, OOS Sharpe ≥ SPY Sharpe AND PF ≥ 1.15
4. CRYPTO post-fix forward test: POSITION horizon n≥100, PF ≥ 1.3, WR ≥ 55%
5. CI failures resolved (Python 3.11/3.12)

If both EQUITY and CRYPTO fail pre-registered tests, keep both blocked and preserve passive benchmark sleeve (ETF TAA).

---

## PART 7 — Implementation Roadmap (90 Days)

| Weeks | Work | Deliverable |
|-------|------|-------------|
| 1 | PnL validation, blank field flags, promotion gates fail-closed, QA infrastructure | Measurement fixed |
| 2-4 | Mutual fund + ETF infrastructure (NAV cache, ranker, backtest tools) | MF/ETF ready for testing |
| 4-8 | EQUITY 24-month benchmark vs SPY; CRYPTO forward test post-fill-fix | Alpha vs beta determination |
| 9-13 | Review forward data against gates; publish trial count | Scale or wind down |

**Success at day 90 is NOT "profitable."** It is one class with a pre-registered, benchmark-relative result and known trial count.

---
