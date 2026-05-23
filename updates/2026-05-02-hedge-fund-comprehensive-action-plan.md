# Hedge Fund Quantitative Action Plan: From Audit to Alpha

**Date:** 2026-05-02  
**Repo:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca  
**Target:** Transform `findtorontoevents.ca/audit` into a hedge-fund-quality signal platform  
**Based on:** `HEDGE_FUND_ENHANCEMENT_PR_2026_05_02_VERBATIM.md` + independent codebase audit + library research  

---

## Executive Summary

This document provides a **foolproof, industry-standard intervention plan** that a Quantitative Researcher or Hedge Fund Manager could follow to take the current project from its mixed-performance state to institutional readiness. It is inclusive of all major insights from the verbatim PR, supplemented with critical corrections, orphaned code integration, UI/UX fixes, and asset-class-specific debug protocols.

**Three Non-Negotiable Principles:**
1. **Stop the bleeding first.** No new capital to FAIL-tier assets (Crypto C-Tier, Forex pre-recovery, Commodities, Futures).
2. **Measure before you monetize.** Every edge must pass a standardized backtest + walk-forward + Probabilistic Sharpe Ratio (PSR) gate before receiving capital.
3. **Integrate before you invent.** The repo contains ~350 KB of orphaned production-grade code. Wire it to the dashboard before building new strategies.

---

## Part 1: The Foolproof Intervention Protocol (Industry Standard)

This is the **master workflow** that supersedes any individual recommendation. A quant manager should follow these steps in exact order, regardless of how compelling any single PR or research finding appears.

### Stage 0: Triage & Hemorrhage Control (Days 1–3)
**Goal:** Prevent further destruction of capital.

1. **Run the Kill-Switch Report.** For every asset class currently emitting picks, compute:
   - Rolling 20-pick Profit Factor (PF)
   - Rolling 20-pick Win Rate (WR)
   - Max drawdown from peak NAV
2. **Halt any asset class where:**
   - PF < 1.0 for 20+ consecutive picks, OR
   - WR < 40% for 40+ consecutive picks, OR
   - Max drawdown > 15% without recovery within 10 picks
3. **Emergency gate changes (from PR, verified):**
   - `cryptoCTierEnabled = false`
   - Remove `WINNER_FILTER` from `hc_filter.js`
   - Replace `elite_score < 30` with `ml_score >= 0.82 && confidence >= 0.70`
   - Lower `riskRewardFloor` from 1.50 to 1.25
   - Unblock confidence band 0.85–0.90 (previously hard-rejected)
   - Lower `bondEliteScoreFloor` from 30 to 15

### Stage 1: Data Forensics & Pipeline Repair (Days 4–14)
**Goal:** Fix the measurement system so you can trust your metrics.

1. **Build `alpha_engine/track_calculator.py`.**
   - Input: `closed_picks.json`
   - Output: `track_records.json` keyed by `strategy:symbol:direction`
   - Fields: `track_wr`, `track_trades`, `track_wins`, `track_losses`, `updated_at`
   - Run as daily cron after resolution sweep.
2. **Fix `forward_wr` pipeline.**
   - `outcome_resolver.py` must compute and write `track_wr` per tuple.
   - `hc_filter.js` Gate 3 must read `p.track_wr`, not `p.strat_fwd_wr`.
3. **Schema enforcement layer.**
   - Reject any pick missing: `pick_id`, `symbol`, `strategy`, `direction`, `entry_price`, `take_profit`, `stop_loss`, `asset_class`, `entry_date`, `ml_score`.
   - Normalize `BUY→LONG`, `SELL→SHORT` at ingestion with provenance flag.
4. **Resolution integrity.**
   - Cap `MAX_RESOLVE_RETRIES` at 3.
   - Force `FLAT` closure with `exit_price = entry_price` at max retries (do not leave `status = null`).
   - Add yfinance fallback for forex: ECB SDW or Alpha Vantage.

### Stage 2: Edge Verification (Days 15–45)
**Goal:** Prove that each asset class has positive expected value.

For each asset class, run the **Edge Verification Protocol** (see Part 9 for report template):

1. **Backtest:** Minimum 5 years of historical data (or all available if < 5 years).
2. **Walk-forward:** 60% in-sample, 40% out-of-sample, 3 expanding windows.
3. **Transaction costs:** Crypto 0.10%, equity 0.01%, forex 1.0 bp (majors) / 3.0 bp (crosses), ETF 0.05%, bond 0.05%.
4. **Statistical gates:**
   - PSR > 0.90 (Probabilistic Sharpe Ratio)
   - DSR > 0.90 (Deflated Sharpe Ratio, correcting for multiple testing)
   - Minimum 50 closed trades out-of-sample
5. **Graduation:** Only asset classes clearing all 4 gates proceed to Stage 3.

### Stage 3: Capital Deployment Ladder (Days 46–90+)
**Goal:** Scale capital only after edge is proven.

| Phase | Capital | Requirement | Halt Trigger |
|---|---|---|---|
| Paper | $0 | All Stage 2 gates cleared | PF < 1.2 or WR < 50% for 20 trades |
| Seed | $100K | Paper PF > 1.5 and WR > 55% over 50 trades | PF < 1.3 or MDD > 10% |
| Scale | $1M | Seed PF > 1.8 and WR > 58% over 100 trades | PF < 1.5 or MDD > 15% |
| Institutional | $10M+ | Scale PF > 2.0, Sortino > 2.0, CVaR < 5% at 95% | BLACK trigger: PF < 1.0 or WR < 40% |

---

## Part 2: Asset-Class-Specific Debug & Research Playbooks

### 2.1 Crypto

**Current State:** S-Tier is an extreme outlier (PF 30.17, n=14) but unscalable. B-Tier is the workhorse. C-Tier is toxic. A-Tier decays with lookback length. **Critical new finding:** `quan_engine_scalp` dominates pick volume (≈50%) with -941% PnL. Static -8% SL is too tight (50.9% hit vs 27.7% TP). `SMART_PICKS_CRYPTO_LONG_ONLY = True` suppresses a +7.8pp short edge.

**Immediate Actions:**
- **Kill toxic strategies.** Add HARD_KILL flag for `quan_engine_scalp`, `enhanced_ml_A_xgboost`, `hs_lb_None`, `st_rsi_momentum_confluence`.
- **Disable `SMART_PICKS_CRYPTO_LONG_ONLY`.** Set to `False` in `audit_trail/quality_gates.py:544`. Preserve `CRYPTO_SHORT_REGIME_GATE_ENABLED` as safety net.
- **Enforce score floor ≥ 40.** Score-bin inversion shows 0–9 outperforming 20–29.
- **Deploy ATR-based SL/TP** (see Section 2.1.A below).
- **Suspend C-Tier permanently.** Set `cryptoCTierEnabled = false`. No shadow mode, no exceptions.
- **Cap A-Tier at L50.** Auto-demote picks > 72 hours old from A→B.
- **Add 10-day hard stop** to all A-Tier positions.
- **Maintain B-Tier** at L20–L50 window. Do not extend to L100.

**Research & Debug:**
1. **S-Tier Scaling Study (Weeks 1–4):**
   - Lower confidence floor from 0.85 to 0.80. Paper-trade the 0.80–0.84 band.
   - Integrate **Binance funding rate API** (free). Add funding-rate extreme filter (> 0.10% 8h rate = confidence boost).
   - Run HMM regime detection on BTC 4h data. Block S-Tier mean-reversion entries in "extreme_fear" regime.
2. **Meme Coin Pilot (Separate asset class, 5% hard cap):**
   - Universe: top 15 meme coins by CoinGecko market cap + $1M/day volume.
   - Signal stack: 40% social (Twitter/Reddit velocity via VADER + Reddit API), 35% on-chain (wallet creation velocity, holder Gini), 25% technical (hourly momentum, funding rate).
   - Scam detection: BubbleMaps wallet clustering + rug-pull proxy checks. Exclude DEX-only tokens.
   - Position sizing: max 1% per token, 0.5% daily loss limit, 72-hour max hold.
   - **Backtest requirement:** Use `VectorBT` on 2023–2025 meme coin data. Target: PF 1.3–1.8, Sharpe 0.7–1.0.
3. **Crypto Perp Funding Arbitrage (Highest-conviction new strategy):**
   - The repo already has `funding_arb_backtest.py` and `funding_arb_analysis.py` — **wire these to the dashboard.**
   - Add a "Funding Arb Scanner" panel showing:
     - Top 5 positive funding rates (annualized)
     - Recommended: short perp + long spot when 7-day avg funding > 0.01% per 8h
     - Backtested Sharpe per symbol
   - Run shadow mode for 2 weeks. Graduate if shadow PF > 2.0 at n ≥ 20.

**Free APIs to Integrate:**
- **Binance API** (free, 1200 weight/min): funding rates, order book, klines
- **CoinGecko** (free, no key): 10,000+ coins, trending, market cap
- **CryptoCompare** (free tier): social metrics, news
- **Glassnode** (limited free): exchange flows, whale thresholds
- **DeFiLlama** (free): TVL, yields

**Cheaper Picks / Micro-Cap Crypto:**
- For coins <$0.01 (SHIB, PEPE style): use **limit orders only**. Market orders will suffer 2–5% slippage.
- Reduce position size by 50% for coins with <$10M market cap.
- Require centralized exchange listing; exclude DEX-only micro-caps due to rug-pull risk (30% estimated scam rate).

---

### 2.2 Equity

**Current State:** Best-performing asset class (PF 2.90, WR 59%, n=100) but Sharpe calculation unverified. LONG-only is correct. SHORT ban should remain.

**Immediate Actions:**
- **Verify the Sharpe calculation.** Create `notebooks/equity_sharpe_verification.ipynb` using `QuantStats`.
- **Increase allocation target** from ~20% to 35–40% of portfolio — but only after L200 confirmation.
- **Conditional AAPL unban:** Allow `markov_zone_transition` strategy with score ≥ 55, `regular_divergence_reversal` with score ≥ 65. Ban "Classic Momentum" (score 999).

**Research & Debug:**
1. **Factor Sleeve Enhancement (Weeks 3–6):**
   - Target allocation: Quality 35% / Momentum 25% / Value 20% / Low-Vol 15% / ML Overlay 5%
   - Use **yfinance** + **OpenBB** to fetch fundamentals for factor scoring.
   - Quality: Piotroski F-Score (free from yfinance balance sheet data)
   - Momentum: 12-month return excluding last month (classic Jegadeesh-Titman)
   - Value: EV/EBITDA or P/B (yfinance fundamentals)
   - Low-Vol: 20-day realized volatility < 15th percentile
2. **Sector Rotation Filter (Weeks 4–6):**
   - Rank 11 GICS sectors by 6-month momentum.
   - Only allow equity picks in top-5 sectors.
   - Use **FRED API** (free) for sector ETF data (XLK, XLU, XLP, etc.) as proxies.
3. **Penny Stock Pilot (2% hard cap, experimental):**
   - Universe: $0.50–$5.00, exchange-listed only, $1M+ daily volume, bid-ask < 2%, 252+ days listed, positive book value.
   - Strategy: last-hour intraday reversal (Da, Liu & Schaumburg 2014). Short extreme winners, buy extreme losers in final hour.
   - **Transaction cost model:** 0.5% per trade minimum; spreads on sub-$1 names often 5–20%. **If costs exceed expected alpha, do not deploy.**
   - Use **limit orders only.** Market orders are prohibited.
   - Backtest on 2019–2024 data using `VectorBT`. Target: PF 1.1–1.3, Sharpe 0.3–0.5.

**Free APIs to Integrate:**
- **yfinance** (free): OHLCV, fundamentals, actions
- **OpenBB** (free): aggregates FRED, Polygon, SEC data
- **Finnhub** (free, 60 calls/min): news, earnings, sentiment
- **FRED** (free key): macro data, rates, economic indicators

---

### 2.3 ETF

**Current State:** Tactical edge at L20/L50 (PF 2.67–2.88) that structurally degrades beyond 10 days.

**Immediate Actions:**
- **10-day hard stop** for all ETF positions.
- **Re-entry only within 24–48h** of fresh signal.
- **Reduce position sizing** to 0.5× equity sizing (higher turnover, lower conviction).
- **Allocation cap:** 15–20% of portfolio (down from 25%).

**Research & Debug:**
1. **Overnight/Daytime Decomposition (Weeks 4–8):**
   - Implement Strategy #18 from MDPI (2026): Long/Reversal on XLK, XLU, XLP, XLV, XLI.
   - Decompose returns into overnight (close→open) and daytime (open→close) components.
   - The kNN reversal signal is exploited at single-period lag only.
   - Target: Sharpe 1.0–1.25.
2. **Weekly Rebalance:**
   - Auto-rebalance every Monday if time-decay > 5% from entry.

**Free APIs to Integrate:**
- **yfinance** (free): ETF OHLCV (SPY, QQQ, XLF, etc.)
- **FRED** (free): sector-specific macro data

---

### 2.4 Forex

**Current State:** 0% WR was a measurement artifact (bug-to-filter cascade). True parameters: WR 48.7%, PF 3.59 (n=273 trusted filter). Nine fixes deployed 2026-05-02.

**Immediate Actions:**
- **Verify post-fix resolution rate.** Must sustain ≥ 75% for 5 consecutive days.
- **Clear all banned symbols.** Restore EURUSD, GBPUSD, USDJPY, AUDUSD.
- **Disable confidence reject bands** until n=100 post-fix trades accumulate.
- **Set 5bp floor** for scalps (replaces 0.1bp noise threshold).
- **autoRelax:** forward WR floor 55% → 50% when fwdN < 20.

**Research & Debug:**
1. **G10 Carry Sleeve (Weeks 2–4):**
   - Use **FRED API** + **ECB SDW** for policy rate data.
   - Top pairs: USDCHF (4.75%), AUDCHF (4.35%), USDJPY (4.00%), GBPCHF (3.75%).
   - Overlay: increase size 20% when signal direction aligns with positive carry; reduce 15% when opposed.
2. **Transaction Cost Model:**
   - G10 majors: 0.15–0.28 bp total (spread + slippage)
   - G10 minors: 0.28–0.47 bp
   - Cross pairs: 0.95–1.10 bp → **reject unless expected gross PF > 1.5**
3. **Regime-Stratified Sizing:**
   - "Strong USD + Risk-Off": reduce exposure 50% (historical PF 0.85)
   - "Weak USD + Risk-On": max size allocation (historical PF 1.85)
   - Use DXY index from FRED as regime input.

**Free APIs to Integrate:**
- **FRED** (free): policy rates, DXY, VIX
- **ECB SDW** (free): EUR rates, FX reference rates
- **Alpha Vantage** (free, 25 req/day): FX pairs
- **yfinance** (free): OHLCV for major pairs

---

### 2.5 Commodities

**Current State:** Term-structure signal broken (58% flat exits at L100). Incumbent strategy banned (PF 0.02).

**Immediate Actions:**
- **Retain confidence gate ≥ 0.70.** This is the only functioning protective mechanism.
- **Reduce exposure 50%** when Brent prompt backwardation exceeds $5/barrel (geopolitical stress indicator).
- **Volatility targeting overlay:** scale positions inversely to 20-day realized vol.
   - WTI 35% vol → 0.29× sizing
   - NatGas 55% vol → 0.18× sizing
   - Gold 15% vol → 0.67× sizing

**Research & Debug:**
1. **Triple-Screen Replacement (Weeks 4–8):**
   - Screen 1: Momentum (12-month return)
   - Screen 2: Term structure (roll yield: long backwardation, short contango)
   - Screen 3: Idiosyncratic volatility (low vol = long, high vol = short)
   - Target: PF 1.3–1.6, Sharpe 0.5–0.7
   - Backtest on 2000–2025 data using `VectorBT`.
2. **Gold/Silver Ratio Mean Reversion (Diversifier, 20% of commodity allocation):**
   - Long-term mean ~68:1
   - Long silver/short gold when ratio > 80:1
   - Long gold/short silver when ratio < 50:1
   - Target: PF 1.2–1.4, Sharpe 0.4–0.5

**Free APIs to Integrate:**
- **FRED** (free): commodity prices, rates
- **yfinance** (free): GLD, SLV, USO, UNG (ETP proxies for futures)
- **Alpha Vantage** (free): commodity data

---

### 2.6 Bonds

**Current State:** PF 1.72, WR 50%, n=20. Trapped behind elite_score ≥ 30 gate.

**Immediate Actions:**
- **Lower bond elite_score floor from 30 to 15.** This unblocks 3–5 picks/month.
- **Duration-adjusted position caps:**
   - TLT (20+Y): 1.0% portfolio risk
   - IEF (7–10Y): 2.0% portfolio risk
   - LQD (IG Corp): 1.5% portfolio risk

**Research & Debug:**
1. **Yield Curve Steepener (Standalone, Weeks 2–4):**
   - Trigger: 2s10s spread < 45 bps
   - Structure: Long $100K TLT, Short $230K IEF (duration neutral)
   - Exit: 2s10s > 80 bps
   - Carry: ~$150/month positive
   - Target: 62% WR, +2.8% avg 6M return
   - Use **FRED API** for 2-year and 10-year Treasury yields.
2. **Yield Curve Regime Framework:**
   - STEEP (2s10s > +60 bps): full allocation
   - NORMAL (+20 to +60 bps): full allocation
   - FLAT (< +20 bps): 50% reduction
   - INVERTED (< 0 bps): block mean-reversion entirely

**Free APIs to Integrate:**
- **FRED** (free): Treasury yields, spreads, rates
- **yfinance** (free): TLT, IEF, LQD prices

---

### 2.7 Futures

**Current State:** n=2 closed trades. Inconclusive. PF 99.90 is a mathematical artifact.

**Immediate Actions:**
- **Zero live capital.** Enter accumulation mode.
- Lower gates:
   - `forwardWRMinPctFutures`: 50% → 40%
   - `scoreFloorFutures`: 35 → 25
   - `fwdMinTradesFutures`: 2 → 1

**Research & Debug:**
1. **30-Day Shadow Mode:**
   - Priority: ES=F (S&P 500), NQ=F (Nasdaq), ZN=F (10Y Treasury)
   - Target: 25+ shadow trades across all three
   - Graduation: n ≥ 20, PF > 1.2 → live at 0.5× sizing
2. **Roll-Yield Overlay:**
   - Calculate annualized contango/backwardation between front and second-nearest contract.
   - If contango > 1% annualized: reduce long positions 25%
   - If backwardation > 1%: increase long positions 25%
   - Use **yfinance** for continuous contract data.

**Free APIs to Integrate:**
- **yfinance** (free): ES=F, NQ=F, ZN=F, GC=F, CL=F, YM=F

---

### 2.8 Mutual Funds

**Policy: REJECT for active trading.**

**Rationale:**
- End-of-day NAV pricing only — no intraday TP/SL execution.
- No shorting capability — eliminates half of systematic strategies.
- No premium/discount dislocation (unlike CEFs) — primary alpha source absent.
- High expense ratios erode edge.

**Exception:** Add a **passive screener tab** for long-term allocation only.
- Filter: no-load, expense ratio < 0.50%, 5-year Sharpe > 0.5, AUM > $100M.
- Use **yfinance** for mutual fund data (ticker suffix `.FO` or `X` depending on provider).
- No picks with TP/SL. Only buy-and-hold recommendations with quarterly rebalancing.

---

## Part 3: Backtesting & Verification Protocol

### Standardized Backtest Spec
Every strategy, asset class, or gate change must pass this protocol before capital deployment.

| Parameter | Specification |
|---|---|
| **Framework** | `VectorBT` (rapid research) → `NautilusTrader` (execution fidelity) |
| **Data** | Minimum 5 years daily OHLCV (or all available if < 5 years) |
| **Costs** | Crypto 0.10% round-trip; Equity 0.01%; Forex 1.0 bp (majors); ETF 0.05%; Bond 0.05%; Futures 0.02% |
| **Walk-forward** | 60% IS / 40% OOS, 3 expanding windows |
| **Slippage** | Crypto: 0.05%; Equity: 0.01%; Forex: model spread from live data |
| **Position sizing** | Fixed fractional 2% risk per trade (unless Kelly-derived) |
| **Reinvestment** | Yes, compound returns |

### Statistical Gates (All Must Pass)

| Gate | Threshold | Tool |
|---|---|---|
| Profit Factor (PF) | ≥ 1.5 | `QuantStats` |
| Win Rate (WR) | ≥ 50% | `QuantStats` |
| Sharpe Ratio (annualized) | ≥ 1.0 | `QuantStats` |
| Probabilistic Sharpe Ratio (PSR) | ≥ 0.95 | `probabilistic_sharpe_engine.py` (existing) |
| Deflated Sharpe Ratio (DSR) | ≥ 0.95 | Custom (see mlfinlab logic or implement manually) |
| Max Drawdown (MDD) | < 20% | `QuantStats` |
| Sortino Ratio | ≥ 1.5 | `QuantStats` |
| Minimum Trades (OOS) | ≥ 50 | Manual |

### Quick Edge Report Generation (See Part 9)
A standardized 1-page report must be produced for every asset class and strategy. This ensures that a manager can compare apples-to-apples.

---

## Part 4: Data Sources & APIs to Integrate

### Immediate (Week 1–2)
| Source | Asset Classes | Data | Cost | Integration |
|---|---|---|---|---|
| **Binance API** | Crypto | Funding rates, order book, klines, perp data | Free (1200 weight/min) | `CCXT` or direct REST |
| **yfinance** | Equity, ETF, Bond, Futures, Forex | OHLCV, fundamentals | Free | Direct Python lib |
| **FRED API** | Forex, Bond, Commodity, Macro | Rates, yields, economic indicators | Free (key required) | `fredapi` or `OpenBB` |
| **CoinGecko** | Crypto | Prices, market cap, volume, trending | Free (no key) | Direct REST |
| **OpenBB Platform** | All | Aggregation layer for 30+ providers | Free | Python SDK |

### Short-Term (Month 1)
| Source | Asset Classes | Data | Cost | Integration |
|---|---|---|---|---|
| **Glassnode** | Crypto (BTC, ETH) | On-chain, exchange flows, whales | Limited free | Direct REST |
| **DeFiLlama** | Crypto | TVL, yields, protocol metrics | Free | Direct REST |
| **Finnhub** | Equity | News, earnings, sentiment, fundamentals | Free (60 calls/min) | Python SDK |
| **ECB SDW** | Forex, Rates | EUR rates, FX reference | Free | Web download / API |
| **Reddit API** | Crypto (Meme) | Subreddit posts, comments | Free (rate limited) | `PRAW` |

### Medium-Term (Quarter 1)
| Source | Asset Classes | Data | Cost | Integration |
|---|---|---|---|---|
| **Dune Analytics** | Crypto | SQL querying across chains | Free community tier | Web / API |
| **Alpha Vantage** | Equity, Forex, Crypto | Technical indicators, news sentiment | Free (25 req/day) | Python SDK |
| **LunarCrush** | Crypto | Social sentiment, Galaxy Score | Freemium | Direct REST |
| **Arkham Intelligence** | Crypto | Wallet labeling, entity tracking | Free (Intel-to-Earn) | Web |

### Data Quality Checklist
- [ ] Every pick has `asset_class` explicitly set at source (no inference without provenance)
- [ ] Every non-crypto price fetch has a fallback source (yfinance → FRED/ECB/Alpha Vantage)
- [ ] Every API response is logged with timestamp and HTTP status
- [ ] Stale data alerts fire if any feed is > 1 hour behind for crypto, > 24 hours for equities

---

## Part 5: Recommended GitHub Libraries

### P0 — Integrate This Week
| Library | URL | Purpose | Why Now |
|---|---|---|---|
| **QuantStats** | https://github.com/ranaroussi/quantstats | Analytics, Sharpe, Monte Carlo, tear sheets | Replaces dead `pyfolio`/`empyrical`. Needed for PSR/DSR reporting. |
| **Riskfolio-Lib** | https://github.com/dcajasn/Riskfolio-Lib | Portfolio optimization, 24 risk measures, HRP | Needed for Golden Portfolio allocation and tail-risk modeling. |
| **hmmlearn** | https://github.com/hmmlearn/hmmlearn | HMM regime detection | Needed for regime-conditional gating (bull/neutral/bear). |
| **CCXT** | https://github.com/ccxt/ccxt | Multi-exchange crypto data & execution | Needed for funding rate, order book, and perp data. |
| **OpenBB Platform** | https://github.com/OpenBB-finance/OpenBBTerminal | Data aggregation orchestrator | Unifies yfinance, FRED, Polygon, FMP under one API. |

### P1 — Integrate This Month
| Library | URL | Purpose |
|---|---|---|
| **VectorBT** | https://github.com/polakowo/vectorbt | Rapid backtesting, parameter sweeps |
| **PyBroker** | https://github.com/edtechre/pybroker | ML-heavy strategy backtesting |
| **NautilusTrader** | https://github.com/nautechsystems/nautilus_trader | Execution-fidelity backtesting + live trading |
| **arch** | https://github.com/bashtage/arch | GARCH volatility forecasting |
| **TsFresh** | https://github.com/blue-yonder/tsfresh | Automated time-series feature extraction |

### P2 — Evaluate This Quarter
| Library | URL | Purpose |
|---|---|---|
| **Hummingbot** | https://github.com/hummingbot/hummingbot | Crypto market-making & arbitrage execution |
| **Zipline-Reloaded** | https://github.com/stefan-jansen/zipline-reloaded | US equity factor research (Pipeline API) |
| **PyCaret** | https://github.com/pycaret/pycaret | Low-code ML benchmarking |

### Deprecated — Do Not Use
| Library | Status | Replacement |
|---|---|---|
| **Backtrader** | Archived, Python 3.10+ issues | PyBroker or NautilusTrader |
| **pyfolio** | Dead (Quantopian 2019) | QuantStats |
| **empyrical** | Dead (Quantopian 2019) | QuantStats |

### Installation Command
```bash
pip install quantstats riskfolio-lib hmmlearn ccxt openbb[yfinance,fred,fmp] vectorbt pybroker arch tsfresh
```

---

## Part 6: Orphaned Goldmines Integration Roadmap

The repo contains sophisticated code that does not flow to the dashboard. Integrate these **before** building new strategies.

### Phase A: Low-Effort, High-Impact (Weeks 1–2)

| Module | Integration Path | Dashboard Output |
|---|---|---|
| `probabilistic_sharpe_engine.py` | Run against every strategy backtest before leaderboard entry | Add "Deflated Sharpe" and "Sharpe p-value" columns to Strategy Leaderboard |
| `empirical_bayes_scorer.py` | Wire into `alpha_engine/smart_picks_engine.py` or `audit_trail/quality_gates.py` | Add "Bayesian Win %" column to active picks |
| `funding_arb_analysis.py` + `funding_arb_backtest.py` | Run daily, output JSON to `audit_dashboard/data/` | New "Funding Arb Scanner" tab |
| `onchain_metrics_agent.py` | Run every 6 hours, write snapshot JSON | Add "Whale Flow" and "Exchange Reserve Δ%" columns to crypto pick cards |
| `l2_orderbook_agent.py` | Run continuously for active crypto symbols | Add real-time "Spread" and "Book Imbalance" micro-badges |

### Phase B: Medium-Effort, Strategic (Weeks 3–6)

| Module | Integration Path | Dashboard Output |
|---|---|---|
| `quantum_fusion_crypto_engine.py` | Read `quantum_fusion_report.json`, feed ensemble confidence into scoring | "Quantum Score: X/100" badge on crypto picks |
| `alpha_engine/cross_asset_edge_discovery.py` | Render `cross_asset_edge_report.json` | New "Cross-Asset Edge Map" panel with Sharpe/WR/PF heatmaps |
| `alpha_engine/market_microstructure_strategies.py` | Execute Deribit skew + Coinbase premium + OBI signals | "Microstructure Signals" widget (LONG/SHORT per symbol) |
| `crypto_fusion_predictor.py` | Run nightly predictions | "24h Predicted Direction" column with HMM regime label |

### Phase C: Research-Grade (Weeks 6–12)

| Module | Integration Path | Dashboard Output |
|---|---|---|
| `vpin_mean_reversion_strategy.py` | Generate signals, run through backtest protocol | VPIN regime label per symbol (calm/spike/post-spike) |
| `alpha_engine/microstructure_momentum.py` | Pairs trading signals (Ornstein-Uhlenbeck exits) | New "Pairs Trading" tab |
| `alpha_engine/exchange_flow_strategies.py` | Supply squeeze alerts | Alert banner when exchange reserve decline > 3% over 7d |

---

## Part 7: UI/UX & Dashboard Improvements

### 7.1 Navigation Restructure

**Current problem:** Users cannot find High Conviction picks because it is a filter button, not a tab. Smart Picks has a hidden credibility warning. Empty tabs degrade trust.

**New Tab Structure:**

| Tab | Content | Visibility |
|---|---|---|
| **Overview** | System health, alerts, summary stats | Always |
| **Actionable Picks** | All picks passing ml_score ≥ 0.82 + R:R ≥ 1.25 + no dead band | Always (default landing) |
| ├─ Sub-filter: "Hedge Fund Gate Passed" | Same as above, explicit branding | Button inside tab |
| ├─ Sub-filter: "Verified Alpha" | Prediction market consensus + copy-trader + track n≥10 | Button inside tab |
| ├─ Sub-filter: "Smart Picks" | Only if historical confluence data is backfilled | Button inside tab, disabled with tooltip if not ready |
| **All Live Signals** | Current "Active Picks" unfiltered (transparency) | Always |
| **Strategy Leaderboard** | Per-strategy performance, now with Deflated Sharpe + PSR | Always |
| **Advanced Signals** | Orphaned module outputs: Funding Arb, Whale Flow, Quantum Score, Microstructure | Always |
| **Cross-Asset Edge Map** | Heatmap from `cross_asset_edge_discovery.py` | Always |
| **Closed Picks** | Historical trade log | Always |
| **US Equity Picks** | Long-term value / swing screener | **Hidden until n≥50 closed trades** |
| **ML Health** | Model drift, validation metrics | Always |

**Remove/Hide:** `tab-research`, `tab-portfolios`, `tab-systems`, `tab-btvsfwd`, `tab-bundles`, `tab-audit`, `tab-claudetoppicks`, `tab-aibattle` (or delete the HTML divs entirely).

### 7.2 Pick Card Enhancements

Each active pick card should display:
- **Base data:** Symbol, Direction, Entry, TP, SL, R:R, ml_score, confidence
- **Gate status:** Pass/Fail per gate (elite_score legacy, ml_score, R:R, confidence, track WR)
- **Orphaned enrichments:**
  - Quantum Score (0–100)
  - Bayesian Win %
  - Whale Flow Direction (🐋 In / 🐋 Out)
  - Funding Rate Annualized (for perps)
  - 24h Predicted Direction (from HMM+XGBoost)
- **Risk badge:** GREEN/YELLOW/AMBER/RED based on kill-switch ladder

### 7.3 High Conviction vs Smart Picks vs Verified Alpha

| Concept | What It Is | When to Use It | Current Issue | Fix |
|---|---|---|---|---|
| **High Conviction** | Filter preset: score ≥ 40 + forward WR + trust tier + regime | Use when you want statistically gated picks with track records | Hidden inside filter bar, not a tab | Make it a prominent sub-filter button with a 🛡️ shield icon |
| **Smart Picks** | AI-curated basket scored on 6 dimensions | Use when you want ML-confluence scoring | Historical confluence fields missing from 98% of records; tooltip warning hidden | Add banner: "Smart Picks beta — backtest validation in progress." Do not promote to primary until validated. |
| **Verified Alpha** | Auditable signals (prediction markets, copy-traders, ≥55% FWD WR) | Use when you want transparency into signal provenance | Redundant with Active Picks + filter | Consolidate into "Actionable Picks" sub-filter; remove standalone tab |

**User Journey:**
1. Land on **Overview** → see system health (GREEN/YELLOW/RED).
2. Click **Actionable Picks** → see all picks passing the new hedge-fund gates.
3. Apply **🛡️ High Conviction** filter → narrows to proven track record + regime alignment.
4. Check **Advanced Signals** tab → see if Quantum Score or Whale Flow agrees with the pick.
5. Click pick card → see full risk profile, gate chain, and confidence breakdown.

---

## Part 8: The 12-Week Hedge Fund Manager Playbook

This is a condensed, week-by-week checklist that a CIO or Quant PM can hand to an engineering team.

### Week 1: Emergency Triage — Updated with Multi-AI Review
- [ ] **Kill toxic strategies immediately.** Add HARD_KILL to:
  - `quan_engine_scalp` (50% of pick volume, -941% PnL)
  - `enhanced_ml_A_xgboost` (-410% PnL contribution)
  - `hs_lb_None` (part of -600% toxic cluster)
  - `st_rsi_momentum_confluence` (part of -600% toxic cluster)
- [ ] **Audit whitelist contradictions.** Auto-remove from `core_whitelist.json` any strategy with PnL < -20% over last 500 picks.
- [ ] Suspend Crypto C-Tier (config change)
- [ ] Abolish WINNER_FILTER (`hc_filter.js`)
- [ ] Replace elite_score with ml_score ≥ 0.82 (`hedge_fund_quality_gate.py`)
- [ ] Lower R:R floor to 1.25 (`hf_quality_gates.json`)
- [ ] Unblock confidence 0.85–0.90
- [ ] Lower bond elite_score floor to 15
- [ ] **Set `SMART_PICKS_CRYPTO_LONG_ONLY = False`** (`audit_trail/quality_gates.py:544`). Shorts have +7.8pp WR edge.
- [ ] **Enforce minimum score floor of 40.** Score-bin analysis shows 0–9 outperforms 20–29 (non-monotonic calibration bug).
- [ ] **Deploy ATR-based SL/TP for crypto.** Current static -8% SL hits 50.9% of the time vs only 27.7% TP hit rate.
- [ ] Deploy kill-switch ladder (GREEN→YELLOW→AMBER→RED→BLACK)
- [ ] **Integrate orphaned modules:** `probabilistic_sharpe_engine.py`, `empirical_bayes_scorer.py`

### Week 2: Forex Recovery & Data Plumbing
- [ ] Verify forex resolution rate ≥ 75% sustained 5 days
- [ ] Clear forex banned symbols
- [ ] Set 5bp scalp floor
- [ ] Build `track_calculator.py` and wire to `hc_filter.js`
- [ ] Add schema enforcement layer (12 required fields)
- [ ] **Integrate orphaned modules:** `funding_arb_analysis.py`, `onchain_metrics_agent.py`

### Week 3: Statistical Infrastructure
- [ ] Deploy bootstrap CI + PSR/DSR calculator
- [ ] Add `QuantStats` to all reporting pipelines (replace pyfolio/empyrical)
- [ ] Add volatility targeting module (15% ± 2% portfolio vol)
- [ ] Implement decay tracker + auto-demotion (A→B→block)

### Week 4: Golden Portfolio Launch Prep
- [ ] HRP allocator deploy (`alpha_engine/hrp_allocator.py`)
- [ ] Quarter-Kelly sizing (f = 0.25)
- [ ] ETF 10-day hard stop enforcement
- [ ] AAPL conditional unban live
- [ ] **Integrate orphaned modules:** `quantum_fusion_crypto_engine.py`, `crypto_fusion_predictor.py`

### Week 5–6: New Strategy Paper Trading
- [ ] Crypto perp funding arb: shadow mode on 2+ exchanges
- [ ] Forex carry sleeve: G10 overlay paper trading
- [ ] CEF NAV discount: scraper + calculation engine
- [ ] Commodity triple-screen: backtest on 2000–2025 data

### Week 7–8: Golden Portfolio Live
- [ ] Deploy $500K tranche 1
- [ ] Scale to $1M if PF > 5.0, WR > 65%, MDD < 15%
- [ ] Regime gate (HMM) + correlation gate live
- [ ] **Integrate orphaned modules:** `cross_asset_edge_discovery.py`, `market_microstructure_strategies.py`

### Week 9–10: Institutional Validation
- [ ] 1,000 bootstrap runs per asset class
- [ ] PSR > 0.95 for T1 assets
- [ ] DSR > 0.95 for T1 assets
- [ ] Cost gate live (net-of-cost PF filter)
- [ ] 8 researcher personas running daily

### Week 11: Meme Coin & Penny Stock Pilots
- [ ] Meme coin shadow mode (social + on-chain signals)
- [ ] Penny stock liquidity filter validation
- [ ] Both capped at 5% and 2% respectively

### Week 12: Go/No-Go Decision
- [ ] Full audit package review
- [ ] CVaR < 5% at 95% confidence
- [ ] Sortino > 3.0
- [ ] If all clear: authorize $10M+ institutional phase
- [ ] If any gate fails: 30-day remediation window

---

## Part 9: Quick Edge Verification Report Template

Every asset class and strategy must produce this 1-page report before capital deployment. Paste into `reports/edge_verification_<asset>_<date>.md`.

```markdown
# Edge Verification Report: [ASSET CLASS / STRATEGY]
**Date:** YYYY-MM-DD  
**Analyst:** [Name]  
**Dataset:** [Source + date range]  

## 1. Performance Metrics
| Metric | Value | Threshold | Pass? |
|---|---|---|---|
| Profit Factor (PF) | X.XX | ≥ 1.5 | Y/N |
| Win Rate (WR) | XX.X% | ≥ 50% | Y/N |
| Sharpe (annualized) | X.XX | ≥ 1.0 | Y/N |
| Sortino | X.XX | ≥ 1.5 | Y/N |
| Max Drawdown | XX.X% | < 20% | Y/N |
| Probabilistic Sharpe (PSR) | X.XX | ≥ 0.95 | Y/N |
| Deflated Sharpe (DSR) | X.XX | ≥ 0.95 | Y/N |
| Trades (OOS) | XXX | ≥ 50 | Y/N |

## 2. Backtest Configuration
- Framework: [VectorBT / NautilusTrader / Other]
- Walk-forward: [60/40, 3 windows / Other]
- Transaction costs: [List per asset]
- Slippage model: [Fixed % / Variable spread]
- Position sizing: [Fixed fractional / Kelly / Other]

## 3. Asset-Class Specific Checks
- [ ] Crypto: Funding rate regime aligned? C-Tier excluded?
- [ ] Equity: Factor purity verified? Sector rotation filter applied?
- [ ] ETF: 10-day stop enforced? Single-lag decay confirmed?
- [ ] Forex: Cost model applied? Carry differential checked?
- [ ] Commodity: Triple-screen validated? Roll yield included?
- [ ] Bond: Yield curve regime noted? Duration risk capped?
- [ ] Futures: Shadow mode completed? Roll yield overlay active?

## 4. Data Quality
- [ ] All picks have required 12 fields
- [ ] Asset class explicitly set (not inferred)
- [ ] No unresolved ghost picks (> 5% unresolved = fail)
- [ ] Price fetch fallback tested

## 5. Risk Assessment
- **Primary risk:** [Describe]
- **Mitigation:** [Describe]
- **Kill-switch trigger:** [e.g., PF < 1.2 for 10 trades]

## 6. Verdict
[ ] APPROVED for paper trading  
[ ] APPROVED for live capital ($X)  
[ ] REJECTED — reason: ____________  
[ ] NEEDS MORE DATA — require: ____________

## 7. Signed Off By
- Quant Analyst: ____________ Date: ____________
- Risk Manager: ____________ Date: ____________
- CIO / PM: ____________ Date: ____________
```

---

## Part 10: Double-Check, Risk Disclosures & Honest Answers

### 10.1 "If We Implement Your PRs, Are You SURE Our TP/SL Will Be Ideal?"

**No. Absolutely not.** The PRs fix **gate logic and asset class selection**. They do **not** fix:
- TP/SL calibration methodology
- Slippage and fill probability
- Gap risk (especially overnight for equities, weekends for crypto)
- Partial fill handling
- Borrow availability for shorts

**What you must do separately:**
1. **TP Hit Rate Analysis:** For every resolved pick, compute `actual_exit / take_profit`. If < 90% of picks that "won" actually hit TP, your TP levels are too optimistic.
2. **SL Hit Rate Analysis:** Compute `actual_exit / stop_loss`. If > 10% of picks that "lost" exited worse than SL, your SL levels are too tight or gap risk is unmodeled.
3. **Slippage Distribution:** Compare `actual_entry` vs `signal_entry_price` for 100+ picks. If median slippage > 0.1% for crypto or > 0.01% for equity, adjust cost models.

### 10.2 What Was Overlooked?

1. **The equity Sharpe of 5.395 is unverified.** Demand independent recalculation.
2. **The "killed alpha" figure assumes unresolved picks would have been winners.** They may not have been. Discount by 40–60%.
3. **Cross-asset correlation estimates are assumptions, not measurements.** The Golden Portfolio correlation matrix uses assumed values. Compute from 2-year rolling returns.
4. **Capacity constraints are ignored.** A $4M equity sleeve with 40 positions implies $100K per position. For small-cap picks, this moves the market. No market impact model is present.
5. **Tax and regulatory considerations are absent.** Crypto perp funding arb may be treated as ordinary income, not capital gains. CEF strategies may generate unwanted K-1s. Consult a tax advisor before scaling.
6. **The PR assumes continuous deployment of engineers.** 258 hours ≈ 6.5 weeks at 1 FTE. With QA, testing, and bug fixes, budget 10–12 weeks.
7. **Mutual funds are dismissed but not formally excluded from the signal pipeline.** Add explicit mutual fund rejection in `outcome_resolver.py`.

### 10.3 Key Web Data Points to Monitor Daily

| Data Point | Source | Why It Matters | Alert Threshold |
|---|---|---|---|
| BTC funding rate (8h) | Binance API | Perp arb entry/exit | > 0.01% or < -0.01% |
| DXY (USD Index) | FRED / yfinance | Forex regime classification | > 110 or < 100 |
| VIX | FRED / yfinance | Equity volatility regime | > 30 (bear) or < 15 (bull) |
| 2s10s spread | FRED | Bond yield curve regime | < 20 bps (flat alert) |
| Brent backwardation | yfinance (BNO/UKOIL proxy) | Commodity stress filter | > $5/barrel |
| BTC exchange netflow | Glassnode / CryptoQuant | On-chain supply pressure | > +20K BTC/day (inflow = bearish) |
| Reddit / Twitter sentiment | PRAW / VADER | Meme coin early signal | Velocity spike > 3σ |
| Coinbase Premium Index | Coinbase API / `market_microstructure_strategies.py` | Institutional demand proxy | > +0.10% (premium = bullish) |

### 10.4 Orphaned Code Integration Priority Revisited

After reviewing the codebase independently, the **highest-ROI integration** is:

1. **`probabilistic_sharpe_engine.py`** (already exists, just needs dashboard wiring)
2. **`empirical_bayes_scorer.py`** (fixes the exact "empty track record" problem the PR complains about)
3. **`funding_arb_backtest.py`** (the PR's highest-conviction new strategy already exists)
4. **`onchain_metrics_agent.py`** (free alpha, just needs scheduling)
5. **`alpha_engine/cross_asset_edge_discovery.py`** (already proved equity is under-allocated)

**Do not build new strategies until these 5 are wired.**

---

## Appendices

### A. Quick Reference: Asset Class Triage

| Asset Class | Action | Max Allocation | Key Metric to Watch |
|---|---|---|---|
| Equities | SCALE | 40% | L200 PF > 2.5 |
| ETFs | SCALE (tactical) | 20% | 10-day time stop adherence |
| Crypto S-Tier | SCALE (capped) | 10% | n ≥ 50 before increasing |
| Crypto B-Tier | MAINTAIN | 5% | L20–L50 window only |
| Crypto A-Tier | MONITOR | 5% | Kill if PF < 1.3 |
| Bonds | SCALE (after n=50) | 15% | 2s10s regime |
| Forex | RECOVER → SCALE | 15% | Post-fix resolution rate |
| Commodities | REBUILD | 0% until triple-screen | Flat-exit rate < 30% |
| Futures | ACCUMULATE | 0% until n=20 shadow | Shadow PF > 1.2 |
| Crypto Perps | DEVELOP | 20% (if validated) | 7-day avg funding > 0.01% |
| Meme Coins | PILOT | 5% hard cap | Scam detection pass rate |
| Penny Stocks | EXPERIMENTAL | 2% hard cap | Liquidity filter pass rate |
| Mutual Funds | EXCLUDE | 0% | N/A |

### B. Recommended IDE Agent Prompts

To delegate research and fixes to IDE agents (Cursor, Kimi, Claude), use these prompts:

**Agent 1: Gate Fix Agent**
```
In hedge_fund_quality_gate.py and hc_filter.js:
1. Remove WINNER_FILTER entirely.
2. Replace elite_score < 30 with ml_score >= 0.82 && confidence >= 0.70.
3. Lower R:R floor from 1.5 to 1.25.
4. Unblock confidence 0.85–0.90.
5. Add bond-specific elite_score floor of 15.
6. Write unit tests verifying each gate behavior on sample picks.
```

**Agent 2: Track Calculator Agent**
```
Create alpha_engine/track_calculator.py that:
1. Reads closed_picks.json.
2. Groups by strategy:symbol:direction.
3. Computes track_wr, track_trades, track_wins, track_losses.
4. Persists to track_records.json.
5. Updates hc_filter.js to read p.track_wr instead of p.strat_fwd_wr.
6. Add a test that verifies Gate 3 operates on live data.
```

**Agent 3: Orphaned Integration Agent**
```
Integrate these existing modules into the audit dashboard:
1. probabilistic_sharpe_engine.py → Add Deflated Sharpe + PSR columns to Strategy Leaderboard.
2. empirical_bayes_scorer.py → Add Bayesian Win % column to active picks.
3. funding_arb_backtest.py → Create a "Funding Arb Scanner" tab showing top opportunities.
4. onchain_metrics_agent.py → Add whale flow badges to crypto pick cards.
Do not modify strategy logic; only wire outputs to the dashboard HTML/JS.
```

**Agent 4: Backtest Validation Agent**
```
For [ASSET CLASS], run a standardized backtest using VectorBT:
1. Load 5 years of data from [SOURCE].
2. Apply the current strategy with transaction costs [X].
3. Run 60/40 walk-forward with 3 expanding windows.
4. Compute PF, WR, Sharpe, Sortino, MDD, PSR, DSR.
5. Generate the Edge Verification Report template from Part 9.
6. Flag if any gate threshold is failed.
```

### C. One-Line Summary for the CIO

> Stop feeding C-Tier, Forex, and Commodities. Fix the elite_score gate today. Wire the 5 orphaned goldmines this week. Verify the 5.395 Sharpe independently. Scale capital only after PSR > 0.95 and n ≥ 200. The platform has real edge, but the edges are buried under bad gates, empty tabs, and disconnected code.

---

**Document Status:** FINAL  
**Next Review Date:** 2026-05-16 (after Week 2 triage completion)  
**Owner:** Quantitative Audit Team / Kimi Code CLI  


## Part 2.5: Multi-AI Review Deep Dives — Implementation Details

The following sections contain concrete implementation code and protocols derived from cross-AI review of the codebase. These address the highest-ROI fixes identified by multiple independent audits.

---

### 2.5.A ATR-Based Dynamic SL/TP for Crypto

**Problem:** Current static SL (-8%) hits on 50.9% of crypto picks while TP only hits 27.7%. For assets with 3–5% daily ATR, a static -8% SL is aggressive and captures noise rather than genuine risk.

**Solution:** Switch to ATR-based dynamic SL/TP per asset class.

```python
# alpha_engine/atr_calculator.py
import pandas as pd
import numpy as np

def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> float:
    """Calculate Average True Range using Wilder's smoothing."""
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, min_periods=period).mean()
    return atr.iloc[-1]

def dynamic_sl_tp(
    entry_price: float,
    atr_value: float,
    side: str = "long",
    sl_mult: float = 1.5,
    tp_mult: float = 2.0,
    min_sl_pct: float = 0.005,   # 0.5% hard floor
    max_sl_pct: float = 0.15     # 15% hard ceiling
) -> tuple[float, float]:
    """
    Returns (stop_loss, take_profit) based on ATR multiples.
    Crypto default: SL = 1.5×ATR, TP = 2.0×ATR (asymmetric 1:1.33 R:R).
    """
    raw_sl = atr_value * sl_mult
    raw_tp = atr_value * tp_mult
    
    # Convert to percentage of entry
    sl_pct = raw_sl / entry_price
    tp_pct = raw_tp / entry_price
    
    # Enforce hard floors/ceilings
    sl_pct = max(min(sl_pct, max_sl_pct), min_sl_pct)
    tp_pct = max(tp_pct, min_sl_pct * 1.5)  # TP must be > 1.5× min SL
    
    if side.lower() == "long":
        sl = entry_price * (1 - sl_pct)
        tp = entry_price * (1 + tp_pct)
    else:
        sl = entry_price * (1 + sl_pct)
        tp = entry_price * (1 - tp_pct)
    
    return round(sl, 4), round(tp, 4)


# Asset-class specific multipliers (calibrated from adaptive_tp_sl.json + audit data)
ATR_CONFIG = {
    "crypto":    {"sl_mult": 1.5, "tp_mult": 2.0, "period": 14},
    "equity":    {"sl_mult": 2.0, "tp_mult": 2.5, "period": 14},
    "etf":       {"sl_mult": 1.8, "tp_mult": 2.2, "period": 14},
    "forex":     {"sl_mult": 1.2, "tp_mult": 1.8, "period": 14},
    "commodity": {"sl_mult": 1.5, "tp_mult": 2.0, "period": 14},
    "bond":      {"sl_mult": 1.5, "tp_mult": 2.0, "period": 14},
    "futures":   {"sl_mult": 1.5, "tp_mult": 2.0, "period": 14},
}
```

**Integration Steps:**
1. Create `alpha_engine/atr_calculator.py` with the code above.
2. In `outcome_resolver.py` or pick-generation pipeline, replace static `sl_pct`/`tp_pct` with:
   ```python
   from alpha_engine.atr_calculator import dynamic_sl_tp, ATR_CONFIG
   cfg = ATR_CONFIG[asset_class]
   sl, tp = dynamic_sl_tp(entry_price, atr_value, side, cfg["sl_mult"], cfg["tp_mult"])
   ```
3. For crypto specifically, the old static defaults were `sl_pct=0.02` (2%) in `adaptive_tp_sl.json`, but live data shows -8% was being applied. **Reconcile the deployed config with the JSON.**
4. Add unit tests verifying:
   - SL < entry < TP for LONG picks
   - TP < entry < SL for SHORT picks
   - ATR-based SL is within [0.5%, 15%] band

**Expected Impact:**
- Reduce crypto SL hit rate from 50.9% → ~35%
- Improve TP/SL ratio from 0.54 → ~0.85
- Estimated WR improvement: +3–5pp for crypto

---

### 2.5.B Whitelist Audit & Auto-Removal Protocol

**Problem:** `core_whitelist.json` (last updated 2026-03-03) protects strategies that are simultaneously generating large losses. The whitelist is stale and contradicts live performance data.

**Solution:** Automated whitelist hygiene script.

```python
# tools/audit_whitelist.py
import json
from datetime import datetime

WHITELIST_PATH = "core_whitelist.json"
KILL_LIST_PATH = "kill_list.json"
LOSS_THRESHOLD = -0.20   # -20% over last 500 picks
REVIEW_BUFFER_DAYS = 7

def audit_whitelist():
    with open(WHITELIST_PATH) as f:
        whitelist = json.load(f)
    
    with open(KILL_LIST_PATH) as f:
        kill_list = json.load(f)
    
    removed = []
    for strategy in list(whitelist.get("core_strategies", [])):
        sid = strategy["id"]
        pnl = get_strategy_pnl(sid, lookback=500)  # existing DB function
        
        if pnl < LOSS_THRESHOLD:
            strategy["status"] = "suspended"
            strategy["suspended_at"] = datetime.utcnow().isoformat()
            strategy["suspension_reason"] = f"PnL {pnl:.1%} < threshold {LOSS_THRESHOLD:.1%}"
            
            kill_list["strategies"].append({
                "id": sid,
                "reason": "auto_whitelist_audit",
                "pnl": pnl,
                "removed_at": datetime.utcnow().isoformat()
            })
            
            whitelist["core_strategies"].remove(strategy)
            removed.append(sid)
            alert_team(f"[WHITELIST AUDIT] Removed {sid}: PnL={pnl:.1%}")
    
    whitelist["last_updated"] = datetime.utcnow().isoformat()
    
    with open(WHITELIST_PATH, "w") as f:
        json.dump(whitelist, f, indent=2)
    with open(KILL_LIST_PATH, "w") as f:
        json.dump(kill_list, f, indent=2)
    
    return removed

def alert_team(msg: str):
    # Wire to Discord webhook, email, or dashboard alert feed
    print(f"[ALERT] {msg}")
```

**Immediate Actions:**
1. Run `audit_whitelist.py` manually today.
2. Add the four toxic strategies to `kill_list.json` with `reason: "emergency_multi_ai_audit"`.
3. Schedule `audit_whitelist.py` as a weekly cron (Sundays at 00:00 UTC).
4. Add a dashboard widget: **"Whitelist Health"** showing count of protected strategies, count on watchlist (PnL -10% to -20%), and count auto-removed this week.

**Expected Impact:**
- Remove protection from ~4–8 losing strategies immediately
- Prevent future "protected loser" scenarios
- Align safety logic with actual performance

---

### 2.5.C UNKNOWN Pick Re-Classification Protocol

**Problem:** 410 picks classified as "UNKNOWN" deliver 45.37% WR and the best average PnL — yet they are invisible to asset-class-specific dashboards and filtering logic.

**Root Cause:** Symbol classifier in `outcome_resolver.py` falls back to "UNKNOWN" when suffix inference fails. Many are likely equities/ETFs mis-routed through the crypto pipeline.

**Solution:** Enhanced symbol classifier + re-classification sweep.

```python
# alpha_engine/symbol_classifier.py
import re

KNOWN_ETFS = {"SPY", "QQQ", "GLD", "USO", "TLT", "IEF", "LQD", "XLK", "XLU", "XLP", "XLV", "XLI", "XLE"}
KNOWN_EQUITY_PATTERNS = re.compile(r"^[A-Z]{1,5}$")  # Standard US equity tickers
KNOWN_CRYPTO_PATTERNS = re.compile(r"(USDT|USD|BUSD|USDC)$")
KNOWN_FOREX_PATTERNS = re.compile(r"^([A-Z]{3})([A-Z]{3})$")  # EURUSD, GBPJPY, etc.
KNOWN_FUTURES_SUFFIXES = {"=F"}

def classify_symbol(symbol: str, strategy_hint: str | None = None) -> str:
    """
    Deterministic symbol classification with audit trail.
    Returns one of: CRYPTO, EQUITY, ETF, FOREX, COMMODITY, BOND, FUTURES, INDEX
    """
    symbol = symbol.upper().strip()
    
    # Direct suffix matches
    if symbol.endswith("=X"):
        return "FOREX"
    if symbol.endswith("=F"):
        return "FUTURES"
    if symbol.endswith("USDT") or symbol.endswith("USD") and not symbol.startswith("FX"):
        return "CRYPTO"
    
    # Known ETF list
    base = symbol.replace("-USD", "").replace("-USDT", "").split(".")[0]
    if base in KNOWN_ETFS:
        return "ETF"
    
    # Standard equity ticker (1-5 uppercase letters)
    if KNOWN_EQUITY_PATTERNS.match(base) and len(base) <= 5:
        return "EQUITY"
    
    # Forex 6-letter pattern
    if KNOWN_FOREX_PATTERNS.match(base):
        return "FOREX"
    
    # Strategy hint fallback
    if strategy_hint:
        if "crypto" in strategy_hint.lower() or "bitcoin" in strategy_hint.lower():
            return "CRYPTO"
        if "forex" in strategy_hint.lower() or "fx" in strategy_hint.lower():
            return "FOREX"
        if "commodity" in strategy_hint.lower() or "gold" in strategy_hint.lower() or "oil" in strategy_hint.lower():
            return "COMMODITY"
        if "bond" in strategy_hint.lower() or "treasury" in strategy_hint.lower():
            return "BOND"
    
    # Default with flag for manual review
    return "UNKNOWN"


def run_reclassification_sweep():
    """Re-classify all UNKNOWN picks and route to correct pipelines."""
    unknown_picks = fetch_picks_where(asset_class="UNKNOWN")
    reclassified = {"CRYPTO": 0, "EQUITY": 0, "ETF": 0, "FOREX": 0, "COMMODITY": 0, "BOND": 0, "FUTURES": 0, "UNKNOWN": 0}
    
    for pick in unknown_picks:
        new_class = classify_symbol(pick["symbol"], pick.get("strategy"))
        if new_class != "UNKNOWN":
            update_pick(pick["pick_id"], asset_class=new_class, reclassified_at=datetime.utcnow().isoformat())
        reclassified[new_class] += 1
    
    return reclassified
```

**Integration Steps:**
1. Replace `_resolve_asset_class()` in `outcome_resolver.py` with `classify_symbol()`.
2. Run `run_reclassification_sweep()` as a one-time migration.
3. Add `_asset_class_inference_source` field to every pick: `"symbol_suffix"`, `"known_list"`, `"strategy_hint"`, or `"default"`.
4. For any pick still returning "UNKNOWN" after re-classification, create a manual review queue (`UNKNOWN_REVIEW_QUEUE.json`).

**Expected Impact:**
- Unlock 410 picks for correct asset-class filtering and dashboard visibility
- Potentially improve non-crypto pipeline throughput by 20–40%
- Reduce mis-routed equity picks entering crypto cost models

---

### 2.5.D Score-Bin Inversion Fix

**Problem:** Lower score bins (0–9) outperform mid-range bins (20–29). The score-to-performance relationship is non-monotonic, indicating a calibration bug in the scoring model or a data leakage issue.

**Immediate Fix:**
```python
# In hedge_fund_quality_gate.py or hc_filter.js
MIN_SCORE_FLOOR = 40  # Hard reject anything below 40

# Gate logic addition:
if score < MIN_SCORE_FLOOR:
    block_pick(reason=f"score_bin_inversion_floor: {score} < {MIN_SCORE_FLOOR}")
```

**Long-Term Fix (Weeks 2–4):**
1. Re-train the scoring model with a **loss-aware objective** (e.g., weighted cross-entropy where false positives cost 2× false negatives).
2. Verify no data leakage: ensure score features do not include post-entry price action.
3. Implement isotonic regression post-processing to enforce monotonicity of score vs. observed WR.

**Expected Impact:**
- Immediate: filter out worst-performing bin, lifting aggregate WR by ~1–2pp
- Long-term: restore trust in score-based position sizing

---

### 2.5.E Pipeline Starvation Fix for Non-Crypto Assets

**Problem:** Equity, commodity, ETF, and bond pipelines have near-zero survivorship. The current filters are calibrated for crypto volatility and inadvertently kill non-crypto signals.

**Root Causes:**
- Volatility thresholds tuned for 50%+ annualized vol (crypto) applied to 15% vol assets (bonds)
- Liquidity filters requiring $10M+ daily volume exclude thin but valid commodity/bond instruments
- `elite_score` floor of 30 penalizes low-volatility assets (bonds naturally score lower due to lower return variance)

**Fixes:**

| Asset Class | Current Constraint | Fix |
|---|---|---|
| Equity | Vol filter rejects < 20% vol | Lower to 10% vol floor |
| ETF | Liquidity $10M/day | Lower to $2M/day for sector ETFs |
| Bond | elite_score ≥ 30 | Lower to 15 (already in Phase 0) |
| Commodity | Momentum-only signal | Add mean-reversion + carry fallback strategies |
| Forex | forwardWRMinPct 55% | autoRelax to 50% when fwdN < 20 (already in Phase 0) |

**Add class-specific fallback strategies:**
- If equity pipeline produces zero picks for 24h, loosen score floor by 5 points (max 2 times)
- If bond pipeline produces zero picks for 48h, activate yield-curve steepener as standalone signal
- If commodity pipeline produces zero picks for 24h, switch to gold/silver ratio mean-reversion

**Expected Impact:**
- Restore non-crypto pipeline throughput to 5–10 picks/day aggregate
- Diversify portfolio away from crypto concentration

---
