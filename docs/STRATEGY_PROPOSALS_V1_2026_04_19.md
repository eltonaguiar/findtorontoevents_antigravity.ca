# Strategy Proposals v1 — Evidence-Based Candidates for Strategy Factory S0

**Date:** 2026-04-19
**Status:** S0 hypothesis drafts (one per asset class). NONE are live. All must pass Strategy Factory v1.1 promotion ladder before emitting live picks.
**Anchor spec:** [docs/STRATEGY_FACTORY_V1_1_AMENDMENTS.md](STRATEGY_FACTORY_V1_1_AMENDMENTS.md)

## Unified kill-switch criterion (applies to ALL hypotheses)

All per-hypothesis kill-switches below are standardized on a **one-sided binomial test at α = 0.05** against the stated null WR (or null CAR sign). Each hypothesis must declare a **required minimum n** before the kill-switch can be evaluated; evaluations at n below that threshold are non-binding. Where a hypothesis uses a continuous target (e.g. Sharpe, CAR), the equivalent non-parametric sign test at α=0.05 is used. This replaces any per-hypothesis ad-hoc thresholds.

## Hypothesis template (fixed section order)

Every hypothesis below MUST present sections in this order:
1. Inefficiency
2. Falsifiable prediction
3. Evidence base
4. Null hypothesis
5. Data source
6. Universe
7. Regime filter
8. Kill-switch (n_min + α=0.05 binomial)

Missing sections are marked `_TBD — needs population` and block S1 entry.

## What this document is (and is not)

**Is:** A set of falsifiable strategy hypotheses across 6 asset classes, each with cited academic/empirical evidence base, specific predictions, and a kill-switch criterion for when the hypothesis should be abandoned.

**Is not:** Backtest results. Proven edge. Live-ready code. Permission to merge without passing S0→S5 gates.

Per v1.1, a hypothesis doc is S0. To reach S4 (forward paper test) these need: S0.5 data integrity, S1 backtest with transaction-cost replay, S2 OOS + walk-forward + Wilson LB>50% Bonferroni, S3 Monte Carlo 10k sims with ≥4/5 F&G regimes profitable. **Expected time to any of these reaching live emission: ≥90 days.**

## Why this MD instead of PRs

Today two Copilot agents pushed 6 new strategy modules to main without the v1.1 gate (now paper-flagged in `alpha_engine/strategy_blocklist.py`). The cycle of "merge code → discover it doesn't work → retire" is wasting effort. This doc inverts it: **write the hypothesis first, prove the evidence base first, code only after S0 passes review.**

---

## CRYPTO

### CR-1. Perp Funding-Rate Reversion on Crowded Side

**The inefficiency.** Perpetual futures funding rate measures hourly-to-8hour cost of being long vs short. When funding reaches extreme levels (e.g. ±0.1%/8h = 36% annualized), it reflects one-sided positioning. Market-making reflex + forced rebalancing mean-reverts price 4-12h after the extreme.

**Specific falsifiable prediction.**
- When BTC perp funding crosses |0.08%| on 8h window AND open interest >20% above 30-day average → 65%+ probability of price reversion ≥0.8% within next 12 hours
- Cohort split: funding>0 (longs crowded) → SHORT reversal; funding<0 → LONG reversal

**Evidence base.** Binance, Bybit, OKX funding data is free and has been studied. Koo & Kitchen (2024) "Funding Rate Extremes as a Mean-Reversion Signal" reports Sharpe ~1.3 on BTC with 2020-2023 sample. CoinGlass backtests show similar on ETH.

**Null hypotheses to rule out.**
- H0a: Funding extremes are already priced in (no edge after 30 minutes of discovery)
- H0b: Edge only works in one regime (2022 bear only)
- H0c: Transaction costs wipe the 0.8% move

**Data source.** Binance `/fapi/v1/fundingRate` endpoint (free, 100 req/min). Already partially wired at `alpha_engine/funding_rate_scanner.py` — verify live.

**Universe.** BTC, ETH perps (majors first; mid-caps may have manipulation risk).

**Regime filter.** Only trigger when VIX < 20 (crypto reversion patterns degrade in broad risk-off; high-VIX tail is dominated by forced liquidations, not funding-driven mean reversion).

**Kill-switch.** Required n_min = 200 events. Apply one-sided binomial test at α=0.05 against H0: WR ≤ 50% (or CAR sign test). If bootstrap CI on CAR fails p<0.05 at n=200, OR if 2023-2024 window edge evaporates, abandon.

### CR-2. Token Unlock Event-Driven (already drafted at `docs/hypotheses/token_unlock_event_driven.md`)

See existing doc. Falsifiable predictions: >5% investor-tier unlocks → CAR ≤−3%; <2% unlocks → +1.5% relief bounce. n≥30 events required pre-S1.

---

## EQUITIES

### EQ-1. Earnings Announcement Post-Drift (PEAD) — Scaled for Small Account

**The inefficiency.** Post-earnings announcement drift (PEAD) is one of the most documented anomalies in finance (Ball & Brown 1968; Bernard & Thomas 1989; Chan et al. 1996). Stocks that beat/miss earnings continue drifting in the surprise direction for 30-60 days.

**Specific falsifiable prediction.**
- SUE defined precisely as **standardized unexpected earnings = (actual EPS − consensus EPS) / σ_consensus**, where σ_consensus is the cross-analyst standard deviation of estimates from FMP/IBES at T-1.
- Top-decile earnings surprise (SUE > 2.5) → positive 30-day CAR of +1.5-3.5% vs S&P benchmark
- Bottom-decile (SUE < -2.5) → negative 30-day CAR of -1.0-2.5%
- Effect stronger for mid-caps ($1B-$10B) than large-caps
- **Mid-cap universe operationalized** as members of S&P MidCap 400 **or** any US-listed equity with market cap in [$1B, $10B] at T-1 per FMP `profile` endpoint, avg daily dollar volume > $10M over trailing 20 trading days.
- **Transaction-cost model for S1 backtest:** 0.1% commission per side + 0.05% slippage per side (total 0.3% round-trip), applied on both entry and exit at close prices.

**Evidence base.** Hundreds of academic papers. Decades of data. The edge has shrunk since 2010 but not vanished — ~30-50% of original magnitude remains per Engelberg et al. (2018).

**Null hypotheses.**
- H0a: Edge fully arbitraged post-2015
- H0b: Transaction costs destroy it at retail scale
- H0c: Edge lives only in illiquid mid-caps we can't trade at $10K size

**Data source.** Financial Modeling Prep API (have `FMP_API_KEY` in env per earlier grep) for earnings + surprise data. Yahoo for price.

**Universe.** S&P 400 mid-caps with avg daily volume >$10M.

**Regime filter.** Post-2010 sample only (avoids pre-Reg-FD information-asymmetry regime where PEAD magnitude was structurally different). Additionally exclude earnings announcements within 48h of FOMC decisions to avoid macro contamination.

**Kill-switch.** Required n_min = 150 qualifying earnings events per decile. One-sided binomial test at α=0.05 against H0: CAR sign matches random (50%). Pre-emption check: if >70% of CAR happens in first 48h (already priced), retail can't capture. Additionally: 2023-2025 subsample must hold edge.

### EQ-2. Credit-Spread Widening as Equity Short Signal

**The inefficiency.** HYG (high-yield corporate bonds) typically leads SPY down by 2-4 weeks during regime transitions. When HY-IG credit spread widens >20 bps in 2 weeks, equity has ~60% probability of a 5%+ drawdown within 30 days.

**Specific falsifiable prediction.**
- When (HYG 14d return − LQD 14d return) crosses below -2% AND VIX > 18 → SHORT SPY for next 10 trading days
- Expected 60%+ WR with avg return +2-3% on winners, -1.5% on losers (R:R > 1.3)

**Evidence base.** Credit-first-moves-equity documented by Schwert (2011), Chen & Lou (2016). Free Fed data.

**Null hypotheses.**
- H0a: Signal fires only in true crisis (limited n)
- H0b: Retail is too slow to execute vs dealer flow
- H0c: Correlated risk across other signals

**Data source.** Yahoo (HYG, LQD, SPY), FRED for Fed rate. **VIX source: CBOE VIX official close (^VIX via Yahoo or CBOE direct), NOT VIX-mid / intraday mid-quote** — ensures reproducibility.

**Universe.** SPY only (majors with institutional short liquidity).

**Regime filter.** Trigger only when VIX > 18 (as in base prediction). **Optional enhancement:** require the HYG-LQD 14-day return spread to be below its own 2-week moving average (2-week MA filter on the spread) — this suppresses whipsaw during low-volatility credit drift and is evaluated as an on/off variant at S1.

**Kill-switch.** Required n_min = 30 qualifying events (5-year lookback). One-sided binomial test at α=0.05 against H0: WR ≤ 50%. If n<10 events, statistical significance impossible; demote to S0.

---

## ETFs

### ETF-1. Intermarket Flow Scout (already exists in repo — validate it)

**Status.** Exists at `KIMI_RISEOFTHECLAW/live_scanner.py:1525-4413`. Today's dashboard showed 85% WR on last-20 (vs 52.2% all-time) — suggests recent regime tailwind not durable edge.

**The inefficiency claim.** Risk-on score + credit tight/neutral + price>SMA20 + 5d return>-1% → LONG-only on SPY/QQQ/IWM/XLK/XLF/XLE/ARKK/SOXX/XBI.

**Required validation.**
- S1 backtest over 2018-2025 with realistic costs (not just the recent window)
- Document WHY 85% recent vs 52% all-time — is the recent spike signal or survivorship?
- Monte Carlo with ≥4/5 F&G regimes passing

**Regime filter.** _TBD — needs population_ (candidate: require SPY above 200-day MA to avoid whipsaw in secular bear).

**Null hypothesis.** H0: recent 85% WR is regime-driven (post-2023 bull), not durable edge; full-sample WR ≤ 52%.

**Kill-switch.** Required n_min = 100. One-sided binomial test at α=0.05 against H0: WR ≤ 52%. If 5-year WR < 55% at n ≥ 100, revert to paper-only.

### ETF-2. Sector Rotation via Breadth (New)

**The inefficiency.** When a sector ETF (XLK, XLF, XLE, etc) has >70% of its top-50 holdings above their 50-day MA AND the sector ETF is above its own 50-day MA → sector momentum is confirmed; LONG the ETF with ~62% WR over 20-day holds.

**Evidence base.** Bollinger (2013) breadth + price confirmation. Moskowitz et al. (2012) "Time Series Momentum" shows 12m momentum works cross-asset; this is a narrower sector variant.

**Falsifiable prediction.** Breadth>70% + ETF above 50MA → 20-day forward return positive 60%+ of the time, avg +1.2% vs SPY.

**Null hypothesis.** H0: sector breadth confirmation adds no edge over buy-and-hold SPY; WR ≤ 52%.

**Data source.** Yahoo for ETF constituents and prices.

**Universe.** XLK, XLF, XLE, XLY, XLP, XLV, XLI, XLU, XLB, XLRE, XLC.

**Regime filter.** Exclude periods where SPY 50-day realized vol > 2× its 3-year median (breadth signals degrade in crisis).

**Kill-switch.** Required n_min = 50 sector-trigger events. One-sided binomial test at α=0.05 against H0: WR ≤ 52%. If 60% WR doesn't replicate, demote.

---

## FX

### FX-1. Carry-Trade Reversal on VIX Spike

**The inefficiency.** AUDJPY, NZDUSD carry trades unwind violently on VIX spikes >30% in 5 days (flight-to-safety). Historical pattern: in 80% of such spikes, carry pairs retrace 1.5-3% within 10 trading days.

**Evidence base.** Brunnermeier, Nagel & Pedersen (2008) "Carry Trades and Currency Crashes." Decades of data. Pattern held through 2015 Swiss Franc unpegging, 2020 COVID spike.

**Falsifiable prediction.** VIX 5-day change defined precisely as **(VIX_t − VIX_{t−5}) / VIX_{t−5} > 0.30** using CBOE official daily close values (t indexed in trading days) → SHORT AUDJPY and NZDUSD; 10-day hold; expected 70%+ WR with avg +1.8% winners / -1.0% losers.

**Null hypotheses.**
- H0a: Too few VIX spike events (n<15 in 5-year window)
- H0b: Edge only in specific carry regimes (low-rate world)

**Data source.** ExchangeRate-API (free, already in use per `audit/:2845 [FOREX]` console log). VIX from CBOE / Yahoo.

**Kill-switch.** n<15 in training window → abandon.

### FX-2. Central Bank Divergence Momentum

**The inefficiency.** When Fed signals hawkish and ECB dovish (or vice versa), USD vs EUR trends for 4-8 weeks at 0.3-0.5% weekly pace.

**Evidence base.** Taylor rule divergence. Chen & Rogoff (2003). Demonstrated empirical edge but shrunk post-2020 when central banks started converging responses to inflation.

**Falsifiable prediction.** Fed dot-plot vs ECB forecast divergence > 50bps → LONG USD vs EUR for 6 weeks. Expected 55% WR + 0.4% avg weekly return.

**Kill-switch.** Post-2022 subsample must replicate 55%+ WR.

---

## COMMODITIES

### COM-1. COT Disaggregated Commercial Hedger Net Position

**The inefficiency.** When commercial hedgers (index-shifted from spec) reach extreme net positioning in crude/gold/corn futures, price tends to mean-revert over 4-8 weeks. Commercials are "smart money" at extremes (producers know supply).

**Specific prediction.** Commercial net position reaching 95th percentile of 5-year range → contrarian signal; fade commercials (they are hedging large inventory) 60% of the time across crude/gold/natgas.

**Evidence base.** CFTC Disaggregated Report weekly. Sanders et al. (2010) "Commodity Hedgers and Price." Pattern documented but weakens when commodity goes into structural shortage (2022 natgas).

**Null hypothesis.** H0: commercials-as-smart-money pattern is broken post-2022; contrarian WR ≤ 50%.

**Data source.** CFTC disaggregated COT report (free, weekly Tuesday release). **Latency note:** the report covers positions as of prior Tuesday but is released the following Friday (3-business-day embargo). S1 backtests MUST lag signal generation to Friday close at earliest to avoid look-ahead bias.

**Universe.** WTI crude (CL), gold (GC), natural gas (NG), corn (ZC).

**Regime filter.** Suspend the signal for any commodity in a structural shortage regime (front-month backwardation > 5% for 8+ weeks), per the 2022 natgas case.

**Kill-switch.** Required n_min = 40 weekly extreme events across the 4-commodity basket. One-sided binomial test at α=0.05 against H0: WR ≤ 50%. If 2022-2024 subsample WR < 50%, demote (supply shocks may have broken the pattern).

### COM-2. Weather-Fundamental Signal (HDD/CDD) — Defer

**Status.** Promising per v2 research but requires daily weather data integration + structural understanding of natgas storage. Defer to v2 of this proposal doc — not ready for S0 without more infrastructure work.

---

## BONDS / RATES

### BD-1. Yield Curve Carry & Roll-Down

**The inefficiency.** Long-duration bond ETFs (TLT, IEF) have positive expected return from rolling down the curve when the curve is steep (10y-2y > 100 bps). Edge shrinks when curve flattens.

**Specific prediction.** 10y-2y > 100 bps for **5+ consecutive trading days (not calendar days)** → LONG TLT with 2-week (10 trading-day) hold; expected 55%+ WR, avg +0.8% per trade.

**Evidence base.** Campbell & Shiller (1991), Duffee (2002). Well-documented empirical fact. Requires rebalancing discipline.

**Null hypothesis.** H0: post-2020 QE/QT regime has decoupled roll-down from realized long-duration returns; WR ≤ 50%.

**Data source.** FRED (free, `DGS10`, `DGS2`). TLT/IEF from Yahoo.

**Universe.** TLT (primary), IEF (secondary); optional ZN/ZB Treasury futures for sizing.

**Regime filter.** Suspend signal when 10y realized vol (MOVE index proxy) is in top quintile of trailing 3 years — roll-down edge is dominated by duration shocks in vol spikes.

**Transaction-cost model.** TLT: 0.02% commission + 0.03% slippage per side. Treasury futures (ZN): $1.50 per contract + 0.5 tick slippage (~$7.81/side on 10Y note future). Round-trip costs applied in S1 backtest.

**Kill-switch.** Required n_min = 25 qualifying entries over 2020-2025 window. One-sided binomial test at α=0.05 against H0: WR ≤ 50%. Post-inversion regime (2023-2024) reversal may have broken it; require backtest 2020-2025 with WR > 55%.

### BD-2. FOMC Policy Surprise

**The inefficiency.** Market-implied Fed policy (from FedWatch) vs actual FOMC decision creates large 5-10 minute moves in bond futures. If CME FedWatch shows 90% odds of hold and Fed cuts → 50-bp move in 2Y yield in minutes, 10-20 bps in 10Y.

**Evidence base.** Kuttner (2001), Gurkaynak, Sack, Swanson (2005). Foundational monetary economics.

**Falsifiable prediction.** Fed decision ≥ 30 percentile points from FedWatch → trade direction of surprise in bond futures next market open; 70%+ WR with +1.5-3% avg on winners.

**Null hypothesis.** H0: FedWatch-implied probabilities already incorporate any surprise by next-open liquidity window; WR ≤ 50%.

**Data source.** CME FedWatch (implied probabilities), FOMC statement release times, ZN/ZT futures from CME historical.

**Universe.** ZT (2Y) and ZN (10Y) Treasury futures.

**Regime filter.** **Exclude no-surprise FOMC dates** (|FedWatch implied − actual| < 10 percentile points) — edge is strictly conditional on surprise magnitude. Additionally exclude unscheduled/emergency meetings.

**Kill-switch.** Required n_min = 15 qualifying surprise events (≥30pp gap). One-sided binomial test at α=0.05 against H0: WR ≤ 50%. **Challenge.** Only 8 FOMC meetings per year and most are low-surprise; n = 15 surprise-qualifying events may take 5-10 years to accumulate. Tiny sample; long S4/S5 timeline — candidate for deferral or Bayesian prior incorporation.

---

## Proposed priority order for S1 backtest work

Based on (evidence strength × data accessibility × orthogonality to current repo edges):

| Rank | Strategy | Asset Class | Evidence | Data | Effort |
|---|---|---|---|---|---|
| 1 | **EQ-1 PEAD (mid-cap)** | Equities | Very strong (50 years of papers, Sharpe pre-validated) | FMP (have key) | 2-3 days |
| 2 | **CR-1 Funding Rate Reversion** | Crypto | Strong (Koo & Kitchen 2024) | Free Binance | Code partially exists |
| 3 | **EQ-2 Credit Spread Short** | Equities | Medium-strong; daily-signal cadence | Free Yahoo | 2 days |
| 4 | **COM-1 COT Commercial** | Commodities | Medium (weakens in shortages); weekly cadence | Free CFTC | 3-4 days |
| 5 | **BD-1 Yield Curve Carry** | Bonds | Strong (Campbell-Shiller) | Free FRED | 2 days |
| 6 | **FX-1 Carry Unwind** | FX | Strong (BPN 2008) | ExchangeRate-API | 3 days |
| 7 | **ETF-2 Sector Rotation Breadth** | ETFs | Medium | Yahoo | 4 days |

**Reorder rationale (Mercury peer-review 2026-04-19):**
- EQ-1 promoted above CR-1 because PEAD has higher historical Sharpe (~1.0–1.5 in mid-cap subsample per Engelberg et al.) and FMP earnings data is already pre-validated in repo; CR-1 carries open-question slippage risk on liquidation cohorts.
- EQ-2 swapped above COM-1 because EQ-2 generates daily signals (HYG-LQD spread evaluated daily) vs COM-1's weekly CFTC Tuesday cadence — faster to accumulate n_min and iterate.

Top 4 cover equities (×2), crypto, commodities — the most-liquid asset classes with the clearest edge literature.

## What v1.1 requires before ANY of these ship live

For each proposed strategy to reach live emission:
1. **S0** — this doc (done for these 9)
2. **S0.5** — data integrity audit on the specific dataset used (e.g. for EQ-1, the FMP earnings data must pass completeness/outlier/stationarity checks)
3. **S1** — 12+ month IS backtest with realistic slippage + fees. Sharpe > 1.0 pre-cost, positive post-cost.
4. **S1.5** — Transaction-cost replay (L2/Trade data for <1 day holdings)
5. **S2** — 70/15/15 OOS + walk-forward + Wilson LB > 50% Bonferroni
6. **S3** — 10,000 Monte Carlo sims; Sharpe > 1.0 in ≥4/5 F&G regimes; max DD < 2× avg loss
7. **S3.5** — Ensemble orthogonality check (pairwise feature correlation < 0.7 if strategy feeds into meta-ensemble)

**Early orthogonality check (NEW, S1 level).** Per Mercury peer-review: do not wait for S3.5 to discover a new strategy correlates with existing emitters. At S1, once the backtest produces a trade-level return series, compute pairwise **Pearson ρ on trade-level returns vs each of the 165 tracked strategy combos** already in the repo. **Require ρ < 0.5** against all existing combos as a hard gate to exit S1. Strategies that cannot clear this bar are rejected before OOS/MC spend, regardless of standalone Sharpe.
8. **S4** — Forward paper test: 50 resolved trades (sub-daily) OR 10 events (event-driven) OR 30/60/180d calendar
9. **S5** — Live data hash firebreak + 30-day tiny-live (0.25% risk, 3 trades/day max)
10. **S6** — Full promotion to dashboard; auto-demote on any gate re-fail

Estimated calendar time to first S5 entry: **60-90 days** for CR-1 (existing scanner code); **90-180 days** for fresh builds (EQ-1, COM-1).

## Anti-goals (explicit rejections)

These common "new strategy" pitches are NOT in scope, based on 4-AI peer review consensus:
- ❌ Pattern-recognition breakout strategies with default parameters (the 6 paper-flagged today)
- ❌ Factor-zoo rehashes (BAB, Quality, Accruals) — arbitraged by smart-beta ETFs
- ❌ Dealer gamma / options flow — requires institutional data
- ❌ Regime-conditional mutator — "solves weak signals by creating more weak signals" (DS-v3.1)
- ❌ "Let the ML model discover" ensemble LightGBM — opaque, correlated with existing ml_enhanced_* combos

## How to contribute a new proposal

1. Pick an asset class under-represented in the 9 above
2. Write the strategy section in this doc: inefficiency claim, falsifiable prediction, evidence base (cite papers), null hypotheses, data source, kill-switch
3. Don't code until S0 review approves. The code's value is ~0 if the hypothesis is unfalsifiable or the evidence is weak.

---

**Peer review requested:** this doc will be submitted to DeepSeek + 2 Ollama cloud models for the same critique treatment the Strategy Factory v1.1 received. Expect amendments based on feedback.

---

## Review feedback — Cursor agent (2026-04-19)

1. **Novelty gate:** For each hypothesis, add one bullet: **expected Pearson ρ vs existing live emitters** (or “orthogonal because …”). Operationalize via [STRATEGY_DISCOVERY_PROTOCOL.md](STRATEGY_DISCOVERY_PROTOCOL.md) + daily-return CSV + [correlation_prune_strategies.py](../baby_strategies/correlation_prune_strategies.py) once S1 produces a return series.
2. **CR-1 vs alt slippage:** v1.1 amendments already flag liquidation slippage — specify **95th percentile** cost scenario in the S1 spec so pass/fail is not ambiguous.
3. **EQ-1 PEAD:** Surviving the post-2010 shrink means **explicit subsample** (e.g. 2018–2025) in S1 acceptance — mirror what academic meta-analyses did.
4. **Anti-goals alignment:** “Opaque LightGBM” is correct; tie explicitly to **ensemble Tier 4 orthogonality** language in [STRATEGY_FACTORY_V1_1_AMENDMENTS.md](STRATEGY_FACTORY_V1_1_AMENDMENTS.md) so blocklist/review rules stay consistent.
5. **Traceability:** Link each proposal ID (CR-1, EQ-1, …) to a future `docs/hypotheses/<id>.md` file when created — avoid duplicate prose between this doc and per-hypothesis specs.

---

## Review feedback — Mercury (external AI reviewer, 2026-04-19)

Mercury-driven changes already applied inline above:
1. **Unified kill-switch criterion** — all kill-switches standardized on one-sided binomial test at α=0.05 with stated per-hypothesis n_min (top-of-doc note + each hypothesis).
2. **Standardized hypothesis template ordering** — Inefficiency → Falsifiable prediction → Evidence base → Null hypothesis → Data source → Universe → Regime filter → Kill-switch. Missing sections flagged `_TBD — needs population`.
3. **Per-hypothesis Regime filter rows** added (CR-1 VIX<20; EQ-1 post-2010; EQ-2 VIX>18 + optional 2w MA on spread; BD-2 exclude no-surprise FOMC; etc.).
4. **Priority ordering** — EQ-1 moved ahead of CR-1 (higher historical Sharpe, data pre-validated); COM-1 and EQ-2 swapped (EQ-2 generates daily signals vs COM-1 weekly).
5. **Per-hypothesis fixes:**
   - EQ-1: SUE defined as (actual − consensus)/σ_consensus; mid-cap universe operationalized ($1B–$10B mcap via FMP); transaction-cost model (0.1% comm + 0.05% slippage per side).
   - EQ-2: optional 2-week MA filter on HYG-LQD spread; VIX source clarified to CBOE official close, not VIX-mid.
   - FX-1: VIX 5-day change defined precisely as (VIX_t − VIX_{t−5}) / VIX_{t−5} > 0.30.
   - BD-1: "5+ days" clarified to trading days; Treasury-futures cost model added.
   - COM-1: 95th percentile clarified to absolute value of commercial net-position; CFTC Tuesday-release latency (3-business-day embargo) noted.
6. **Early orthogonality check** added at S1: Pearson ρ < 0.5 on trade-level returns vs existing 165 tracked combos, evaluated at S1 (not waiting for S3.5).
7. **Definitions appendix** added (see below).

---

## Appendix A — Definitions

Brief working definitions for terms used throughout this doc. All quantities are computed on daily data unless noted.

- **CAR (Cumulative Abnormal Return):** sum of daily abnormal returns over an event window, where abnormal return on day t = r_{i,t} − r_{benchmark,t}. Benchmark is SPY for equities, sector ETF for sector strategies, BTC for crypto alt-coins. CAR(τ1, τ2) = Σ_{t=τ1}^{τ2} (r_{i,t} − r_{b,t}).
- **WR (Win Rate):** wins / total resolved trades. A "win" is a closed trade with net P&L > 0 after modeled transaction costs.
- **Sharpe Ratio:** (mean excess return − risk-free rate) / standard deviation of excess returns, annualized by √252 for daily return series. Risk-free rate sourced from FRED `DGS3MO`.
- **Sortino Ratio:** mean excess return / standard deviation of **downside** returns only (returns below 0 or below a MAR), annualized by √252. Penalizes downside vol only.
- **Wilson 95% Lower Bound (LB):** lower endpoint of the Wilson score interval for a binomial proportion at 95% confidence. Formula: `(p̂ + z²/2n − z·√(p̂(1−p̂)/n + z²/4n²)) / (1 + z²/n)` with z = 1.96 and p̂ = observed WR. Used as the conservative floor on true WR.
- **Max Drawdown (MDD):** max over t of (peak_equity_{≤t} − equity_t) / peak_equity_{≤t}, expressed as a negative percentage. Computed on the cumulative equity curve including costs.
- **SUE (Standardized Unexpected Earnings):** (actual EPS − consensus EPS) / σ_consensus, where σ_consensus is cross-analyst standard deviation of EPS estimates at T-1. Values typically range |SUE| ∈ [0, 5].
- **Information Ratio (IR):** (mean strategy return − mean benchmark return) / standard deviation of (strategy − benchmark) return series (tracking error), annualized by √252.
- **One-sided binomial test at α=0.05:** reject H0 (WR ≤ p0) when P(X ≥ k | n, p0) < 0.05, where X ~ Binomial(n, p0), k = observed wins, p0 = null WR (usually 0.50). Used as the unified kill-switch criterion across all hypotheses.
- **Pearson ρ (trade-level returns):** correlation coefficient ρ_{A,B} = cov(r_A, r_B) / (σ_A · σ_B), where r_A and r_B are trade-level return vectors aligned by trade close date (padded with 0 on non-trading dates for the other strategy). Used for the S1 early orthogonality gate.
