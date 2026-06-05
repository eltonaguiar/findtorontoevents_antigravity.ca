# Daily Ideas & Research Log

## 2026-05-13 — User brainstorm dump (alt-data + asset-class expansion)

Captured for future swarm rounds + backtests. Each block = candidate prompt for `tools/swarm/swarm_run.py --preset non-opus-4 --critique-first`.

### IDEA-A: Top proven criteria per asset class (20-round research)

Run 20 swarm rounds per asset class harvesting proven academic + practitioner criteria. After research, backtest the criteria, cross-check against existing safety gates / entry criteria. Use Python TA pattern finding (pandas-ta, mplfinance, pyti). Goal: enumerate what actually works per class.

Sub-prompts:
- EQUITY: value stocks (P/E, P/B, EV/EBITDA), long-term patterns, financial-statement deltas, earnings-revision triggers, "skyrocket" precursors (insider buy clusters, short-squeeze setups, breakout-on-volume, sector rotation entry).
- CRYPTO: on-chain whale flows, funding rates, NUPL extremes, dormancy flow, exchange netflow, stablecoin minting velocity.
- BOND: credit-spread regimes (HYG-LQD, TED), yield-curve shape, real-rate vs inflation expectations.
- FOREX: interest-rate differentials, BoJ/Fed policy divergence, CoT FOREX section.
- FUTURES: COT commercial extremes (already wired), seasonality (grain harvest cycles, energy winter draws), term-structure backwardation.
- ETF: macro-regime overlays (VIX, yield curve, DXY).

### IDEA-B: Penny stocks revisit

Existing repo likely has penny-stock page. Re-validate at <$6 / <$3 / <$2 / <$1 buckets. Per-bucket edge analysis: is sub-$2 universe systematically different from $3-$6 bucket? Find the bucket with the cleanest risk/reward.

Sub-prompts:
- Microcap WR + PF historical by float-size bin
- Pump-and-dump red flags (premarket spike + dilution filing + zero institutional)
- Catalyst-driven moves (FDA, merger announce, contract win)

### IDEA-C: Mutual funds (no-load + low-redemption-fee)

User point: "we get in and out without being locked in. with mutual funds we would likely pay hefty commission but there are certain mutual funds technically we could buy and hold and get out." Filter for no-load / no-12b1 / no-redemption-fee / no-short-term-trading-restriction. Vanguard / Fidelity / Schwab class candidates.

Sub-prompts:
- yfinance fund universe filter for `quoteType=MUTUALFUND` + `expense_ratio < 0.5%` + `front_load=0` + `back_load=0`
- 5y / 10y Sharpe per-fund ranking
- Compare to ETF equivalents — is the fund version worth it?

### IDEA-D: Options data + correlation to underlying

Options flow (Polygon free tier? CBOE volume data?), put/call ratios, max-pain analysis, dark-pool prints. Correlate option-flow regime to next-week underlying move.

Sub-prompts:
- Put/call ratio extremes as contrarian signal
- Unusual options activity (UOA) detector — calls bought above ask in size as bullish lead
- Max-pain pin theory near OPEX

### IDEA-E: "Secret patterns" — corporate-relationship arbitrage

User example: vendor known associated with Samsung → SEC filing or partnership announcement → trade Samsung-related ETF or supplier stock before broader market notices. Generalize: SEC 8-K + 13D/G filings, EDGAR full-text search for partnership keywords, GovTribe contract awards, USPTO patent assignments, court-docket data (PACER), import/export bills of lading (Panjiva / Import Genius free tiers).

Sub-prompts:
- Detect supplier-relationship announcements via EDGAR 8-K keyword search
- Patent assignments → predict M&A or partnership 30-60 days ahead
- Government contract awards (SAM.gov) → small-cap winner signals

#### IDEA-E Analysis (2026-05-24 — 2-engine swarm)

**Engines:** DeepSeek V3.2 + Cerebras. Both reviewed the same codebase context (existing , ,  VT Restatement Short,  EDGAR stubs, May 14 swarm scoring at 23/100 rank 7).

**Verdict: 4.5/10 composite — niche diversification play, not a primary alpha source.** Engines disagreed sharply on feasibility (DeepSeek 2/10 vs Cerebras 7/10), but converged on one point: the full vision (USPTO + SAM + PACER + Panjiva) is over-engineering. MVP-only is the right first step.

| Criterion | DeepSeek | Cerebras | Composite |
|---|---|---|---|
| Gap fit | 3/10 (no gap — Form 4/13D already cover corporate catalysts) | 7/10 (orthogonal gap — partnership ≠ insider buy/sell) | **5/10** |
| Realism / signal count | 2/10 (50-100 actionable/yr from 80K 8-Ks = 0.1%) | 6/10 (4-6/wk true partnerships >00M cap) | **4/10** |
| Data accessibility | 5/10 (free but noisy; PACER adds 0-50/mo) | 8/10 (EDGAR FTS API + SEC 13D/G + USPTO all zero-cost) | **6.5/10** |
| Integration feasibility | 4/10 (~400 loc, no entry/exit/backtest framework) | 7/10 (~150 loc MVP, reuse EdgarFtsClient, plug into vt_partner_strategies) | **5.5/10** |
| Priority vs EDGE_CRITERIA | 1/10 (behind confidence fix, regime audit, FOREX kill) | 4/10 (nice-to-have diversification post-core fixes) | **2.5/10** |
| **Overall** | **2/10** | **7/10** | **~4.5/10** |

**DeepSeek's core objection (valid):** Partnership announcements are PR, not capital commitment. Insider buys (Form 4) and activist filings (13D) show people putting money where their mouth is. A press release about a "strategic partnership" has no skin in the game — the 95%+ false-positive rate is structural, not fixable with better keyword filters.

**Cerebras's core defense (also valid):** The edge is *speed of dissemination*, not depth of signal. A Samsung-supplier 8-K that moves the supplier stock 3-5% in the first 2 hours is a real phenomenon (documented in academic event-study literature). The question is whether a keyword scanner can beat the market's NLP-parsing latency on a /usr/bin/bash budget. Probably not — but at ~150 lines and zero new dependencies, it's a cheap experiment.

**Salvageable elements (for future Sprint if priority rises):**
- **8-K keyword scanner MVP (~80 lines):**  reusing the  pattern from . Query EDGAR 8-K FTS API for  with a 7-day lookback. Regex-filter for company names >00M market cap. Emit  to . Paper-trade for 30 days, measure realized PF.
- **Discard:** USPTO patent assignment scraper, SAM.gov contract awards, PACER docket monitoring, Panjiva bills of lading — all require separate scrapers, auth, or paid tiers with unproven signal value. Do not build until the 8-K MVP proves PF>1.2 after transaction costs.
- **Estimated effort:** 2-4 hours for MVP. Accept/Reject criterion: if 30-day paper-trade PF < 1.0 OR signal count < 10, kill the idea permanently.

**Decision: DEFER — do not implement now.** Priority is below Sprint 1 (confidence fix + regime audit + FOREX kill) and below higher-scoring ideas (IDEA-A asset-class criteria research at 8/10 from May 14 swarm, IDEA-H Polymarket at 6/10). Revisit only if a future Sprint has slack and the core confidence/regime/FOREX pipeline is stable.

### IDEA-F: Chinese / Hong Kong markets

HSI / SSE / SZSE indices, ADR universe (BABA, JD, BIDU, PDD), KraneShares ETFs (KWEB, KBA, KGRN). Trade A-share-ADR premium/discount as stat-arb. Cross-listed pairs.

Sub-prompts:
- HSI vs SPX correlation regime detection (decoupling phases)
- China stimulus headlines → KWEB momentum
- PBoC liquidity injection schedule as macro tilt

### IDEA-G: Gas-price correlation

Natural gas (NG=F, KOLD/UNG) + gasoline (RB=F) prices ↔ consumer-discretionary spend, transportation stocks, refiners (XOM, CVX, MPC, VLO). Lag/lead — does gas price spike predict consumer-staples relative-outperformance?

Sub-prompts:
- WTI/Brent → consumer staples vs discretionary ratio
- NG winter draws → utilities momentum
- Refinery crack spreads → refiner-stock alpha

### IDEA-H: Polymarket data correlation

Prediction-market prices (Polymarket, Kalshi, PredictIt) → equity/macro signal. User caveat: correlation ≠ causation; investigate hidden factors.

Sub-prompts:
- Election market odds → small-cap risk-on bias (R) or healthcare bias (D)
- Geopolitical event markets → oil/gold spike forecasting
- Fed-meeting probability markets → STIR (short-term interest rate) trade
- Causation check: do Polymarket odds LEAD or LAG the underlying market?

#### IDEA-H Analysis (2026-05-24 — 2-engine swarm)

**Engines:** DeepSeek V3.2 + Cerebras. Both reviewed the full PM infrastructure (8,700+ loc across 11 production files — , , , , , , , , , , ), quality_gates weights (prediction_market_consensus=14, polymarket_signals=14, pm_whale_signals=10), and the existing  dict in .

**Verdict: 7.5/10 composite — strong infrastructure leverage, the highest-scoring idea from the May 13 brainstorm so far.** Both engines agreed this is the best candidate among the 12 ideas given the deep existing PM foundation. The key insight: 40% of the code is already written — IDEA-H is extending the PM engine from crypto-only to equity/macro, not building from scratch.

| Criterion | DeepSeek | Cerebras | Composite |
|---|---|---|---|
| Gap fit | 7/10 (strong but domain shift from crypto→equity; 40% infra reuse) | 9/10 (natural extension of existing PM engine) | **8/10** |
| Realism / signal count | 8-15/wk raw, 35% actionable = 3-5/wk | 4-6/wk clean (odds>70%, vol>50k, trend≥2h) | **4-6/wk** |
| Data accessibility | /usr/bin/bash — Polymarket Gamma + Kalshi + FRED + yfinance, all free | 9/10 — /usr/bin/bash incremental, all already licensed or free | **9/10** |
| Integration feasibility | ~570 LOC total (450 new + 120 modified) | ~560 LOC total (pm_macro_overlay.py ~200 loc + lead_lag_analyzer.py ~250 loc + extensions) | **~560 LOC** |
| Priority vs EDGE_CRITERIA | 6/10 (Sprint 3 — after core foundation stable via Sprint 2) | 7.5/10 (Sprint 2 candidate, synergizes with symbol-universe audit) | **6.5/10** |
| **Overall** | **6.8/10** | **8.2/10** | **~7.5/10** |

**Key point of agreement: Fed-rate correlation is the highest-signal entry point.** Both engines independently identified Polymarket Fed-meeting probability markets as the cleanest signal — they have the most liquidity, the tightest bid-ask spreads, and the most direct mapping to tradable instruments (fed funds futures / STIR). Election and geopolitical markets are noisier but worth Phase 2.

**DeepSeek's caution (valid):** EQUITY/MACRO PM markets have 10-100× lower liquidity than crypto PM markets. A Fed rate market might have 0-200K volume vs BTC markets at -50M. Signal reliability drops accordingly — ~35% of extracted signals are actionable vs ~55% for crypto PM. The 3-5 clean signals/week is lower than intuition suggests.

**Cerebras's optimism (also valid):** The edge is **cross-platform agreement**, not raw probability. When BOTH Polymarket AND Kalshi agree on a Fed rate outcome AND the probability is >70%, the signal quality jumps. The existing  already implements strict pairwise agreement — IDEA-H is wiring that same pattern to macro instruments.

**Salvageable elements (MVP-first build plan):**

- **Phase 1 — Fed-rate correlation MVP (~150 LOC):** Create . Query Polymarket Gamma API for Fed rate markets (), cross-reference with Kalshi rate markets via the existing  dict. When both platforms agree direction with probability >70%, emit a macro signal: . Reuse the existing  weight framework and  staleness guard (4h). Wire into  with weight=10 (conservative — lower than crypto PM at 14 due to thinner data). **No new dependencies.**
- **Phase 2 — Election/geopolitical extension (~200 LOC):** Create . Map election markets to sector ETFs (R=small-cap/IWM, D=healthcare/XLV). Map geopolitical markets to commodities (oil conflict → USO, gold safe-haven → GLD). Use the same Polymarket+Kalshi pairwise agreement pattern. Expected: 2-3 sector-rotation signals + 1-2 commodity signals per week.
- **Lead/lag analysis (~100 LOC):** Create . Simple cross-correlation: for each PM event with >20 daily data points, compute (PM_odds[t], underlying_return[t-3..t+3]) correlation window. If PM odds lead by 1-3 days with Pearson r>0.3, flag as leading indicator. If odds lag by 1-3 days, flag as reactive (discard for trading). Output:  consumed by  to adjust source weights dynamically. **Critical:** gates must use ONLY data up to the pick timestamp (no forward-looking leakage).

**Discard (~1,300 LOC saved):**
- Full PM-to-market correlation matrix — too noisy at current liquidity levels; simple pairwise is sufficient
- Real-time WebSocket ingestion — hourly polling via existing CI/CD ( workflow) is sufficient; real-time adds latency complexity with no signal gain at 4-6 signals/week
- ML lead/lag predictors (LSTM, Granger causality) — simple cross-correlation is sufficient for MVP; ML adds overfit risk with n<100 weekly signals
- Multi-exchange arbitrage (PredictIt, Manifold, Metaculus) — Polymarket+Kalshi covers 80%+ of relevant volume; adding more exchanges dilutes signal/noise
- Full sector-rotation backtester — paper-trade the MVP for 60 days first; backtest only if PF>1.2 after 30+ resolved signals

**Estimated effort:** 4-8 hours for Phase 1 MVP. 10-15 hours for Phase 1+2+lead/lag. **No new dependencies, no new API keys, /usr/bin/bash recurring cost.**

**Accept/Reject criterion for Phase 1 MVP:** After 60 days paper-trading with ≥30 resolved signals: PF≥1.25 AND WR≥50% → promote to Sprint 3 full build. PF<1.0 OR signal count <10 resolved → kill the MVP, archive findings.

**Decision: RECOMMEND FOR SPRINT 2 — highest ROI idea from the May 13 brainstorm.** Scores 7.5/10 vs IDEA-E's 4.5/10. The existing 8,700-line PM infrastructure means ~40% of the work is already done. The Fed-rate correlation MVP is 150 LOC, /usr/bin/bash cost, and extends an already-production system into a new asset class. Priority is below Sprint 1 (DONE — confidence fix + regime audit + FOREX kill) and alongside Sprint 2 candidates (PBO/CPCV harness, symbol universe audit). Recommend slotting into Sprint 2 if the PBO/CPCV harness doesn't consume the full sprint.

#### IDEA-A Analysis (2026-05-24 — 2-engine swarm)

**Engines:** DeepSeek V3.2 + Cerebras. Both reviewed the full per-asset-class infrastructure: 22 CRYPTO-only proven strategies (1,835 lines), hedge_fund_quality_gate (478 lines) with per-class rejection rules, non_crypto_quality_gate (785 lines), and live performance data from dashboard_data.json + TOP10_STRATEGIES_PER_ASSET_CLASS_2026-05-19.md.

**Gap fit: 8/10 (both engines agree).** The gap is stark: 22 proven strategies exist for CRYPTO but ZERO for EQUITY, COMMODITY, FOREX, ETF, or BOND. EQUITY is dead (n=5, PF=0.25). BOND is dead (n=5, PF=0.00). ETF is overfit (n=2, PF=11.99). The codebase has per-class REJECTION rules but no per-class ENTRY criteria outside CRYPTO. Only FOREX (PF=1.49 via cta_replicator) and COMMODITY (PF=1.42 via multi_asset_cot) are functional beyond crypto.

**Key divergence: surgical vs comprehensive.** DeepSeek recommends a SURGICAL approach: audit CRYPTO gates instead of discovering new criteria (the 22 strategies exist but aren't properly gated — PF=0.66 class-level), isolate FOREX cta_replicator instead of running 20 rounds (PF=2.51 standalone), defer BOND/ETF until n>30, and focus 20-round research on EQUITY + COMMODITY only. Estimated 500-650 LOC over 3 weeks. Cerebras recommends running 20 rounds for ALL 6 classes, adding on-chain data (Glassnode ~$2k/mo), macro overlays, and full swarm orchestration. Estimated 1,500 LOC over 8 days parallelized.

**Per-class assessment (synthesized from both engines):**

| Class | Current PF/n | Recommendation | Expected ROI | LOC est |
|-------|-------------|----------------|-------------|---------|
| CRYPTO | 0.66/1127 | AUDIT gates, don't research new criteria. Retroactively apply hedge_fund_quality_gate banned-symbol + dead-confidence-band filters to all 1127 closed picks. The 22 strategies have proven WRs 55-83% individually — the class-level PF drag is gating/execution, not criteria deficiency. | PF+0.10-0.15 immediate | 0 (no code, just audit) |
| EQUITY | 0.25/5 | RESEARCH 20 rounds using FREE data only (Yahoo Finance P/E-P/B-EV/EBITDA, SEC EDGAR insider filings, FRED macro). Target 3 criteria: value-momentum composite, insider buy clusters (≥3 officers buying within 30 days), earnings-revision triggers (EPS surprise + guidance raise). Cross-check against EQUITY confidence reject band [0.60, 0.65). | High — greenfield with no existing criteria, large TAM | +250 LOC |
| COMMODITY | 1.42/55 | RESEARCH 5-10 rounds focusing on ADDITIVE criteria: seasonality (grain harvest cycles — ZC/ZW/ZS, energy winter draws — NG, metals seasonals), term-structure backwardation confirmation. COT commercial extremes already work (PF 1.60); the goal is to add orthogonal signals that raise WR from 54.5% to 58%. | Medium — already functional, seeking edge stacking | +150 LOC |
| FOREX | 1.49/148 | ISOLATE cta_replicator (PF 2.51, n=109) from the FOREX basket. The class PF 1.49 is dragged by multi_asset_copytrader (PF 0.16, n=325). Instead of researching new criteria, surgically split FOREX into: (a) high-conviction (cta_replicator + signal_validation FOREX cohort at 63% WR) vs (b) kill-list (multi_asset_copytrader FOREX, alpha_engine FOREX at PF 0.59). Raise FOREX allocation from 0% to 15% for the high-conviction basket. | High — 2.5x PF strategy already exists, just needs isolation | +80 LOC |
| ETF | 11.99/2 | DEFER until n≥30. OOS Sharpe +6.37 with decay 10.8 and only 12 folds = severe overfit suspicion. The two-pick sample is statistically meaningless. | Low until charter floor met | 0 |
| BOND | 0.00/5 | DEFER until n≥30. Current n=5 at PF=0.00 — no signal. Activate the BOND scanner workflow (FRED_API_KEY already set) to grow sample to charter floor 30+, then re-evaluate. | Low until pipeline active | 0 |

**Integration feasibility:**
- **Entry criteria registry:** `alpha_engine/proven_research_strategies.py` gets non-crypto strategy functions for the first time — currently 22 CRYPTO-only, add equity_value_momentum(), commodity_seasonality(), forex_cta_isolated(). New ~250 LOC.
- **Quality gate extension:** `alpha_engine/hedge_fund_quality_gate.py` gets EQUITY value-metric gates (e.g., P/E floor, insider-cluster min count), COMMODITY seasonality window checks. New ~80 LOC.
- **Quarantine manifest:** FOREX allocation raised from 0% → 15% for high-conviction FOREX basket only (not blanket). Update in `audit_dashboard/data/quarantine_manifest.json` or config equivalent. ~20 LOC.
- **No new files needed.** All changes are extensions to existing modules.

**Priority ranking vs Sprint 3-6:**
1. **IMMEDIATE (zero code):** CRYPTO audit — retroactively apply existing hedge_fund_quality_gate to all closed picks, measure PF impact
2. **SPRINT 3:** IDEA-A EQUITY + COMMODITY criteria (500-650 LOC) + P4 correlation matrix shell (both engines agree P4 is parallel)
3. **SPRINT 4:** IDEA-A FOREX isolation (80 LOC) + P5 CPCV harness
4. **SPRINT 5:** P6 external data integration
5. **DEFERRED:** IDEA-A BOND/ETF until charter floor n≥30 met

**Salvage vs discard:**
- **Salvage:** ALL existing files (proven_research_strategies.py, hedge_fund_quality_gate.py, non_crypto_quality_gate.py, quarantine_manifest) — extended, not replaced. The existing per-class rejection infrastructure (banned symbols, confidence bands, RSI killzones) stays intact and is the foundation new ENTRY criteria build upon.
- **Discard:** Nothing. Pure extension.
- **CRYPTO specifically:** The 22 existing strategies are SALVAGED but RE-GATED. Don't touch the strategy code itself — fix the gate that lets them through unfiltered.

**Bottom-line score: 7/10 composite.**

**Decision: APPROVED WITH SCOPE MODIFICATION.** IDEA-A is approved for EQUITY + COMMODITY (20 rounds each, free data only), FOREX isolation (no research, just surgical split), and CRYPTO audit (zero code, gate retroactive application). BOND and ETF are DEFERRED until charter-floor n≥30. The full "20 rounds per class × 6 classes = 120 rounds" original vision is pared to ~35 rounds (20 EQUITY + 15 COMMODITY) — a 70% scope reduction that preserves the highest-ROI targets. Estimated 500-650 LOC across 3 sprints. Expected class-level PF lift: EQUITY 0.25→0.50+ (pilot), COMMODITY 1.42→1.55+, FOREX 0.27→0.60+ (by isolation).


### IDEA-A Debate Swarm Consensus — 2026-05-24

**2-engine debate:** Risk Manager (DeepSeek) vs Portfolio Manager (Cerebras) on the curated picks allocation. Both engines agree on class direction; they disagree on aggressiveness.

#### Consensus Allocation Table

| Class | Risk Mgr | Port Mgr | **Consensus** | Verdict |
|-------|----------|----------|---------------|---------|
| **EQUITY** | 8% | 22% | **15%** | DEPLOY — strongest forward-test signal (WR 58%, n=164) |
| **ETF** | 6% | 12% | **9%** | DEPLOY — SPY short + GLD long verified edge |
| **CRYPTO** | 5% | 10% | **7%** | WARN — n=23 below 30-trade floor, size down until gate audit |
| **COMMODITY** | 5% | 8% | **6%** | WARN — COT edge real, all-SHORT bias needs monitoring |
| **BOND** | 2% | 8% | **5%** | WARN — good WR but negative PnL (same trap as FOREX) |
| **FOREX** | 0% | 0% | **0%** | 🔴 KILL — both engines agree: positive WR + negative PnL = statistical trap |
| **PENNY** | 0% | 0% | **0%** | ⏳ ACCUMULATE — paper-only, n=0 resolved |
| **FUTURES** | 0% | 0% | **0%** | ⏳ ACCUMULATE — paper-only, n=0 resolved |
| **CASH** | 74% | 40% | **58%** | Buffer — deployable as n grows per class |

**Total: 100%** (42% deployed, 58% in reserve)

#### Risk Budget Allocation

| Class | Risk Drawdown Cap |
|-------|-------------------|
| EQUITY | 10% |
| ETF | 5% |
| CRYPTO | 5% |
| COMMODITY | 3% |
| BOND | 2% |
| **Portfolio Max DD** | **15%** |

> **Note:** Per-class risk budgets are independent limits, not additive. They won't all hit simultaneously due to correlation diversification. The 15% portfolio-wide cap is the binding constraint.

Risk Manager's 15% portfolio-wide drawdown cap is adopted as the hard limit. The Portfolio Manager's argument for higher per-class risk budgets is acknowledged but deferred until n≥30 for CRYPTO, COMMODITY, BOND, and until FOREX cta_replicator isolation completes.

#### Areas of Agreement (Both Engines)

1. **EQUITY is the flagship class** — WR 58% at n=164 is the most statistically reliable signal in the portfolio. Both engines agree to overweight EQUITY relative to all other deployed classes.
2. **FOREX must be killed at 0%** — the 57.3% WR / -0.39% PnL pattern is unambiguous statistical trap. No engine dissents.
3. **PENNY + FUTURES stay at 0%** — both engines agree: deploy zero capital until first resolution. The scaffolding added today (banned symbols, confidence floors) is the correct posture.
4. **CRYPTO, COMMODITY, BOND all WARN** — all three have forward-test edge but insufficient sample size (CRYPTO n=23) or negative PnL despite good WR (BOND).

#### Areas of Disagreement (Resolved via Consensus)

1. **CASH buffer:** RM demanded 74% (near-catastrophe protection), PM argued 40% (capital efficiency). **Consensus: 58%** — enough to cover a 3σ event while keeping 42% deployed against proven edge. Cash scales down as class-level n grows past 30.
2. **EQUITY allocation:** RM capped at 8% ("n=164 is backtest-contaminated"), PM pushed for 22% ("forward-test WR 58% is real"). **Consensus: 15%** — above RM floor, below PM ceiling, with review trigger at n=300.
3. **ETF gating:** RM wanted 6% due to liquidity concerns on GLD. PM wanted 12% citing WR stability across sub-classes (SPY short + GLD long). **Consensus: 9%** — split the difference, monitor GLD bid-ask spread monthly.

#### Top 3 Immediate Actions (Synthesized)

1. **Execute FOREX kill** — already at 0% in quarantine_manifest. Lock allocation at 0% until cta_replicator (PF 2.51) is isolated into high-conviction basket (target: Sprint 4).
2. **Gate-audit EQUITY + CRYPTO** — both classes show the "garbage-inflated raw n, profitable forward-test n" pattern. Audit the quality gates to stop backtest/synthetic contamination (zero-code fix, same treatment as CRYPTO IDEA-A recommendation).
3. **Deploy consensus allocation** — set per-class caps at EQUITY 15%, ETF 9%, CRYPTO 7%, COMMODITY 6%, BOND 5%, CASH 58%. Adjust monthly as n milestones hit (n=30, 50, 100).

#### Bottom Line

> The portfolio has ONE proven-class edge (EQUITY, WR 58%, n=164) and FOUR monitored-class signals (ETF, CRYPTO, COMMODITY, BOND). Deploy 42% against the proven edge while holding 58% cash reserve. Re-evaluate monthly as n accumulates. FOREX remains killed until cta_replicator isolation. Risk budget: 15% max portfolio drawdown, hard cap.

### IDEA-I: Weather → farming / soft commodities

Forecast rain (NOAA GFS, ECMWF, weather.com API) → corn/wheat/soy futures (ZC/ZW/ZS=F). Drought monitor + crop-progress weekly (USDA WASDE).

Sub-prompts:
- 14-day precipitation forecast Iowa/Illinois → ZC=F directional bias
- ENSO regime → soft commodities (sugar, coffee, cocoa, OJ)
- Hurricane cone → energy (refinery shutdowns) + insurance vol

### IDEA-J: Mining equipment costs vs minerals / commodities

Caterpillar/Komatsu capex cycles + steel input cost (HRC futures) → leading indicator for copper (HG=F), iron ore, coal. Miner capex cuts = commodity base.

Sub-prompts:
- CAT ER guidance → next-quarter copper trend
- Baker Hughes rig count → 6-month WTI direction
- AISI steel mill utilization → HG=F leading indicator

### IDEA-K: Weddings vs diamond prices

US wedding count (Knot industry report) + India gold demand (WGC quarterly) → diamond price (Polished Prices index), gold (GLD), Signet (SIG). Wedding count = seasonal + demographically forecastable.

Sub-prompts:
- US marriage rate vs SIG revenue
- India festival calendar (Diwali, wedding seasons) → gold imports → GLD seasonal alpha
- Lab-grown vs natural diamond divergence

### IDEA-L: Other alt-data threads

- Cruise-ship bookings (CCL, RCL, NCLH ER lookahead)
- TSA throughput → airline + hospitality
- Container shipping rates (Drewry WCI, Freightos FBX) → FDX, UPS, XPO, MATX
- Box office revenue → DIS, NFLX
- Sports betting handle (state DGE reports) → DKNG, FLUT, MGM
- Job postings (LinkedIn/Indeed Hiring Lab) → labor leading indicator
- Subway turnstile data (NYC MTA open data) → urban-recovery proxy
- Crypto whale-wallet labels (Arkham, Nansen free tier) → smart-money flow
- Reddit WSB mention velocity → meme-stock squeeze precursor (partially wired)

### Execution plan

Phase 1: pick 3 ideas with cleanest free-tier data path. Score each on: (a) data accessibility, (b) backtestable horizon ≥10y, (c) economic logic strength.
Phase 2: run 4-engine swarm on each (~$0.07 × 3 = $0.21) asking for falsifiable hypothesis + minimum-viable backtest spec.
Phase 3: implement min-viable backtest with yfinance + free feeds. Tier-classify.
Phase 4: cross-check against existing safety gates. New edge contradicting a gate → mutation-axes analysis before deploy.

## 2026-05-12 — Hedge-fund-rescue swarm brief (post-Round-14)

User directive at end of Round 14 (Week 1 rescue complete):

> Add this to daily_ideas.MD and ask our agent swarm over 10 rounds to
> build a document together. Make them build individual documents, I
> review and merge, then have them each give final feedback on the merged
> document.
>
> **How to get this to a hedge fund level performance.** Let's say I was
> hired as a Quant to save this company and fix their performance by asset
> class — give a plan, can be high-level to start, but what would you do?
>
> Come up with new strategies? Look for hidden insights like picks with
> low score but high PnL, or picks with high-score and low PnL, or top
> strategies that haven't had picks in a while, DNA mutation of
> strategies, machine learning?
>
> What exactly would you do to basically guarantee success — you know,
> like how REAL successful companies do it?

**Swarm plan (compressed from 10 → 3 rounds for feasibility):**

- **Round 1 (parallel, ~6 personas):** each writes a focused 400-600-word
  doc to `reports/quant_swarm_round1_<persona>_2026-05-12.md`:
  - Renaissance (stat-arb + mean-reversion)
  - Two Sigma (ML-heavy)
  - DE Shaw (event-driven + alt data)
  - Citadel (multi-asset systematic)
  - AQR (factor investing — Carry/Momentum/Value/Defensive)
  - Bridgewater (All Weather macro)
- **Round 2 (synthesis):** I merge into
  `reports/quant_swarm_merged_round2_2026-05-12.md`
- **Round 3 (cross-review):** each persona reviews the merged doc; flags
  drift/disagreement; saves to
  `reports/quant_swarm_round3_<persona>_review_2026-05-12.md`
- **Final merge:** I incorporate review notes into a final
  `reports/quant_rescue_master_plan_2026-05-12.md`

Hidden-insight queries explicitly mentioned by user:
1. Picks with **low score but high PnL** → score is missing some signal
2. Picks with **high score but low PnL** → score over-fits noise
3. **Top strategies dormant** (no picks in a while) → emission decay flag
4. **DNA mutation of strategies** — three-axis mutation protocol per
   `docs/MUTATION_THREE_AXIS_PROTOCOL.md`
5. **ML reality check** — per `reports/ml_staleness_audit_2026-05-12.md`

---

## 2026-05-12 — User brief (queued post-Round-9 deep-dive sequence)

User directive at end of Round 9 ROR-MC build:

**1. Updates entry**
> Once all todos complete, add entry under `findtorontoevents.ca/updates/index.html` indicating changes completed, **expected impact per asset class**, and overall impact on `findtorontoevents.ca/audit`.

**2. Deep-dive worst asset classes**
> Deep-dive into the database and/or strategies by asset class. Identify worst asset classes; how to get them to at least decent performance. Possibly pull in more data. Look at GitHubs with predictive models for those asset classes; evaluate.

Concrete worst classes today (post-resolver-v2 snapshot per `dashboard_data.json::performance.asset_class_health`):
- **FOREX** PF 0.27 / WR 46.4% / n=1169 — class-blocked (hedge_fund_sprint)
- **FUTURES** 5.9% WR — silent-dead, no production scanner
- **BOND** PF 1.72 / WR 55.6% / n=18 — meets PF+WR but n sub-floor (charter 100). BOND scanner registry wired this session (commit 5c7a8c43a27), should ramp.

External-model candidates worth evaluating:
- **FOREX**: stefan-jansen/machine-learning-for-trading (Ch. 12-18, deep RL on FX), polyrabbit/forex-quantitative-trading
- **FUTURES**: backtrader/backtrader-contrib (rolling-cot futures strategies), AI4Finance-Foundation/FinRL (deep RL on commodity + futures rollovers)
- **BOND**: pyportfolioopt (Black-Litterman over treasury duration), QuantConnect/Lean (treasury yield-curve strategies)
- **ETF**: tradytics, polyrabbit/etf-rotation-strategies

**3. Machine-learning audit**
> Are our ML models actually learning? Actually predicting effectively? Getting us better picks per asset class? Any stale ML?

Current ML inventory (from memory + repo grep):
- `ml_gatekeeper/` — gatekeeper model, joblib + json artifacts (committed hourly per audit-dashboard.yml)
- `ml_consensus/` — consensus learner
- `enhanced_models/` — boosted variants
- `ml_crypto_v3` (memory `ml_crypto_v3.md`)
- `ml_enhanced_*` family (4 with DSR>=0.9995 per anti_overfit; 3 flagged "placeholder-stat suspect" by Agent E per `money_ready_filter.js`)
- `kimi_signal_tracking` (blacklisted per supreme-edge P0 #2, commit 4a2d337a5dc)
- `claude_gainer_st` (blacklisted, ML calibration inversion per Kimi audit)
- `enhanced_ml_*`, `ml_crypto_predictor` (SHORT-blocked per BLOCKED_DIRECTION_TRIPLES)

Audit questions to answer:
1. Per-model: when last retrained? Compare model artifact mtime vs cron expected cadence.
2. Per-model: live forward WR vs backtest WR — divergence > 15pp = decay (already in `fwd_vs_bt_divergence` payload).
3. Per-model: confidence-vs-realized-WR correlation. Memory `project_performance_reality` notes confidence INVERTS on ETF/CRYPTO. If still true, ML is anti-edge on those classes.
4. Stale detector: any model with no commit in 7d while its cron is active = silent-dead.
5. Feature drift: `hf_stats.concept_drift.KS_D` was uncomputed last we checked (Master Plan §6). Recompute.

### Execution sequence

1. Ship Round 9 (Step 7 ROR MC + cron).
2. Ship Round 10: updates/index.html entry with per-class expected impact.
3. Deep-dive worst classes: write `reports/asset_class_deep_dive_<class>_2026-05-12.md` per FOREX/FUTURES/BOND. Use cavecrew-investigator agents in parallel.
4. ML staleness audit: write `reports/ml_staleness_audit_2026-05-12.md` with model-by-model retraining age + decay flags + confidence-inversion check.
5. External-model evaluation: cite the GitHubs, identify candidates worth replicating into baby_strategies/ via the harness (commit 9747f9594ec scope).

NFA — all of this is research surface; no real-money sizing without the 10-step Lopez de Prado readiness gate clear.

---

## 2026-05-11 — Top prompts worth revisiting / deep-dive (session synthesis)

Drawn from the May-10/11 session that shipped the research orchestrator + edge stability suite. Each entry = a prompt or sub-thread that produced strong outcomes but still has slack to mine.

### A. v3b — LLM-driven spec-faithful signal translator (HIGHEST LEVERAGE)

**Prompt:** "Replace SMA(50)/SMA(200) proxy with engine-emitted structured `signal_spec` JSON per candidate. Dispatch to handler registry."

**Why revisit:** every NO_EDGE verdict across 7 asset classes is **caused** by the SMA proxy not parsing natural-language `spec.entry`. Keyword router (v3a, commit `a060a87b3c8`) routes only 2/14 BOND specs off the SMA default. Real edge likely hidden behind faithful translation. Output JSON: `{signal_type, params, primary_ticker, secondary_ticker, regime_gate}`. Cost ~$1/run across all classes.

**Deep-dive:** pair-strategy support (TIP/IEF long-short, LQD/HYG ratio), regime-gated entries (VIX > N skip), multi-leg sizing. Likely unblocks MIXED → GO transitions on COMMODITY + EQUITY (already pass T2 floors per edge_stability).

### B. Per-asset-class deep-dive question batches (feed into orchestrator P1)

**Prompt:** "For each class — 5-7 specific questions a quant fund would research next."

**Why revisit:** session's edge-stability design agent produced concrete, asset-class-anchored questions worth firing as their own P1 swarms:
- **CRYPTO** — Hyperliquid HLP carry replication; cross-exchange basis arb post-BinanceUS; on-chain perp signals (funding skew, taker imbalance, OI delta) post-2024 Sharpe>1.5; BTC seasonal-by-UTC-hour; MATICUSDT 2.5%-TP post-merge check.
- **FOREX** — FX carry surviving 2015-2020 CHF/EUR collapse; MyFXBook top-100 AUD/JPY 2024-2026 canonical structure; 13-21 UTC session gate academic basis vs overfit; EUR/USD post-COVID regime-switching with PF>1.5 OOS; trend-following FX majors retail bps budget.
- **BOND** — IG-credit carry post-QE duration window; TLT/IEF momentum 3yr live tracks; PIMCO BOND-fund ETF basket replication minimum n; treasury curve steepener MR 2024-2025; HYG/LQD ratio MR.
- **COMMODITY** — why WR<50 with PF>1.5 (TP/SL ratio); DBMF/KMLM commodity-momentum replication; gold/silver ratio MR 2024-2026; crude contango/backwardation roll-yield current regime; natgas seasonal surviving LNG-export shift.
- **EQUITY** — QMOM/IMOM post-2024 momentum-crash survival; Russell-2000 cross-sectional momentum 20bp slippage; earnings drift PEAD vs HFT crowding 2026; sector-rotation XLF/XLE/XLK Sharpe; short-interest squeeze-fade meme-era vs persistent.
- **ETF** — risk-parity rotation post-2022 reset; NAV vs market price arb retail; sector-momentum monthly rebalance Sharpe post-fee; EFA/VEA vs VTI relative-strength; SVXY/UVXY rebalance edge.
- **INDEX** — SPX/NDX overnight gap post-0DTE flood; VIX term-structure roll post-2024; index seasonality 2020-2026 OOS; pre-FOMC drift bps + decay; SPX/RUT spread MR.

**Deep-dive:** drop into `tools/research/fire_class_p1.py` as a `--question-set <name>` flag so future runs target specific edge hypotheses instead of generic literature surveys.

### C. Edge-stability + research orchestrator pipeline integration

**Prompt:** "Distinguish forward-looking (research) from backward-looking (edge stability) — different surfaces, different cadences."

**Why revisit:** today (commits `bf9f65ed699` + `762b935c0fa`) the two surfaces live on different /audit pages and share only nav style. Cross-link inside `research_index.html` → "see edge stability of currently-shipped strategies" + reverse-link in `edge_stability.html` → "research candidate replacements" would close the loop.

**Deep-dive:** automate. When `edge_stability_<CLASS>.json::consistency_verdict == DECAYING_EDGE`, trigger a P1 swarm for that class focused on "what replaces strategy X?" via a new `tools/research/decay_replacement_pipeline.py`. Wire into `.github/workflows/research-orchestrator.yml`.

### D. Hallucination-guard methodology (export to other agent workflows)

**Prompt:** "verify_citations.py HEAD-checks every URL; engines >25% hallucination → 0.5x weight, >50% excluded."

**Why revisit:** session data showed engine traits are stable — `cerebras` rarely hallucinates URLs, `deepseek` mid (~25-50%), `inception` heavily (>50% on BOND/EQUITY/COMMODITY). Hallucination rate is per-engine, not per-run. Worth surfacing as a score in `tools/swarm/swarm_stats.py` so future agents auto-pick engines.

**Deep-dive:** broaden beyond URL-checking. Check fact-claims: cited PF/WR vs paper's actual Sharpe; claimed instrument vs paper's; claimed window vs paper's. Adds ground-truth scoring beyond URL liveness.

### E. NO_EDGE protocol as first-class deliverable

**Prompt:** "If 5 passes yield no edge, ship a 'no edge found' page that's just as valuable as the positive case."

**Why revisit:** 6 of 7 P5 verdicts came back NO_EDGE today — pages render with citations + rejected candidates + retry conditions, but readers don't know to look there. Index page should sort NO_EDGE prominently with "retry conditions" + "what we tried" exposed so future agents inherit the lit review.

**Deep-dive:** ship `tools/research/no_edge_kb.py` that aggregates every NO_EDGE run into a queryable knowledge base ("has anyone tried X on Y class? what was found?"). Saves swarm $$ on duplicate research.

### F. Generator dry_run gap (E-D3 prereq)

**Prompt:** "3 pick generators (smart_picks_engine, production_scanner, dashboard_generator) don't have `dry_run` kwargs. Blocks Layer 2 generation verification."

**Why revisit:** gate for the post-quarantine verification suite Agent E designed. Until dry_run lands, `tools/verify_quarantine.py` can't prove a quarantined strategy didn't sneak into pick generation. Documented at `audit_trail/GENERATOR_DRY_RUN_GAP.md`, not implemented.

**Deep-dive:** 3 small PRs (one per generator). Each ships a test asserting `dry_run=True` mtime-of-side-effect-file unchanged. Pairs with `feedback_gate_at_execution_not_generation.md`.

### G. Drift-pause activation (Agent D Approach C hybrid)

**Prompt:** "Auto-quarantine strategies when drift exceeds threshold. JSON probation tier auto-managed; permanent BAN human-only PR."

**Why revisit:** ~26h dev work, full design at `tasks/a53c89219838c17e1.output`. Approach C wins (probation JSON read by `quality_gates._load_probation`, hot-reload by next picks generation, mutate-before-kill gate fires investigation doc generation + `mutation_analysis.py` automatically). 25% blast-circuit-breaker. CLAUDE4's 14 manual quarantines (kimi_signal_tracking, baby_strats crypto_soc_*, ml_crypto_pred_v12) become ground-truth fixtures.

**Deep-dive:** D-Phase-1 first (JSON-backed probation tier + `is_on_probation()` + sizer multiplier wire-in to `is_blocked_pick`). Then mutate-before-kill enforcement.

### H. Cross-engine consensus on methodology questions

**Prompt:** "Has anyone found persistent edge in X published 2022-2026? Cite or say no."

**Why revisit:** session showed `cerebras + deepseek + xai` consensus on P5 verdicts is high-signal because P3 numbers are deterministic — disagreement isolates spec interpretation. Use same pattern for **methodology questions** (e.g., "is walk-forward valid for daily-bar bond strategies?", "what PF floor at our cost model?").

**Deep-dive:** new `tools/swarm/examples/methodology_consensus.yaml` that fans methodology Qs to engine pool. Surfaces decisions ("drop monthly rebalance for weekly?") with consensus + dissent.

### I. graphify-intel skill — wire deeper

**Prompt:** "`/graphify-intel` slash skill wraps graph queries. Replaces 3+ Grep/Read roundtrips per cross-file investigation."

**Why revisit:** skill shipped (commit `a28904ebec0`) but graph still AST-only (no semantic LLM phase — `pip install openai` missing). Semantic phase adds clusters + surprising-connection report.

**Deep-dive:** auto-extract on git push via post-commit hook. Use graph to auto-flag PRs touching nodes downstream of `BLOCKED_SOURCE_SYSTEMS` or `passes_active_gate` — high-blast-radius edits get human review.

### J. CPCV upgrade for p3_backtest_runner

**Prompt:** "Close `project_cpcv_gap_2026_04_28.md`. Walk-forward → CPCV (Combinatorially Purged Cross-Validation)."

**Why revisit:** López de Prado's CPCV gives better overfitting detection than k-fold walk-forward for small-n cohorts (exactly our state — all 14 BOND candidates have n<30 today). Switching unblocks honest verdicts at small-n.

**Deep-dive:** mlfinlab CPCV vendored via `experiments/hedgelib_2026_05_10/`. Already audited as DOA on Py 3.14 install — use standalone purged-CV from `alpha_engine/integrations/` instead (per `project_next_phase_integrations_2026_04_22.md` — already wired but orphan).

---

**Session cost summary (2026-05-10/11):** ~$2.10 across 28 swarm passes (7×P1 + 7×P2 + 7×P5 + 7 P1 follow-ons). Hallucination guard fired per class; verified-citation subset only fed P2; engine vote weights propagated to P5.

**Commits anchoring above prompts:** `8d1b3344e12 → 762b935c0fa` on `feat/audit-dashboard-enhancements-hermes-2026-05-09` (research orchestrator + edge stability + 9 PRs). See `CLAUDE1.MD` for full breakdown.

---

## 2026-05-09 — Production-Readiness Subset Hunt: Find Consistent Winners

**Source prompt (verbatim for re-processing):**

> we need to get our project findtorontoevents.ca/audit ready for PRODUCTION REAL WORLD USE.. like we are talking we make hedge-fund level picks per asset class, and people spend their REAL money on our picks.. so we cant mess around anymore. Which asset class could we trust for that.. and if none.. then i need you to take baseline of our current state.. in terms of what the baseline contains, check our project strategies. and build and determine the best possible prompt and then give it to our code swarm and ask for optimizations .. similarly, ask for the best queries, after feeding in a document detailing our database schema and backtesting protocol etc.. You need to check the performance PER ASSET CLASS. not system wide.. and maybe check the performance based on NOT forward looking "edge" filters. is there any subset of our data that if we filtered it by we have winners consistently .. WR or profit factor

**All performance claims labeled with: asset_class | n | timeframe.**

### KEY FINDING — yes, consistent-winner subsets exist (verified)

Source: `audit_dashboard/data/dashboard_data.json::systems` (post-resolver-v2, generated 2026-05-10T00:06:06Z, cumulative-since-system-inception, last_signal_at per row).

**6 systems verified Tier-2 by full charter (`docs/PERFORMANCE_CHARTER.md` v1.0): PF≥1.5, WR≥50%, MDD≤20%, n≥100.**

| system | asset_class | n closed | WR % | PF | MDD % | last_signal | tier |
|---|---|---|---|---|---|---|---|
| `aggregated_picks` | CRYPTO | 440 | 77.8 | **6.84** | 14.43 | 2026-05-09T23:00Z | T2 (T1 except MDD>10) |
| `claude_gainer_st` | CRYPTO | 3,447 | **80.1** | **6.80** | 11.31 | 2026-05-09T12:50Z | T2 (T1 except MDD>10) |
| `copy_trader_intel` | COMMODITY+CRYPTO | 739 | 50.0 | 1.84 | **2.23** ← T1 by MDD! | 2026-05-09T22:47Z | T2 |
| `ml_crypto_pred_v12` | CRYPTO | 123 | 55.6 | 2.53 | 11.0 | **2026-02-22T13:38Z** ← stale 2.5 months! | T2 but inactive |
| `multi_asset_cot` | COMMODITY | 130 | **86.9** | **19.19** | 17.83 | 2026-05-08T23:27Z | T2 |
| `signal_validation` | CRYPTO+FOREX | 501 | 55.7 | 2.31 | 13.14 | 2026-05-09T18:44Z | T2 |

**Standout per asset class:**
- **CRYPTO:** `aggregated_picks` (n=440) + `claude_gainer_st` (n=3,447) — both ~80% WR, PF ~6.8, MDD ~12-14%. Cumulative since system inception.
- **COMMODITY:** `multi_asset_cot` (n=130) — 86.9% WR / PF 19.19 / MDD 17.83% — extreme PF but small n; needs walk-forward verification before Tier 1 promotion.
- **CRYPTO+COMMODITY:** `copy_trader_intel` (n=739) — only 50% WR but **MDD 2.23%** which is well inside Tier 1's 10% cap. PF 1.84 borderline.
- **CRYPTO+FOREX:** `signal_validation` (n=501) — 55.7% WR / PF 2.31 / MDD 13.14%.

### CONTRAST — system-wide aggregate is misleading

Same data source, system-wide:
- Total closed picks: 30,286 (8,774 valid post-noise-filter); compounded PnL **-78.25%**
- 131 systems, only 39 active picks
- Sharpe 0.13, MDD 681% (`hf_stats`, but stale 2026-04-22)

The **system-wide aggregate is destroyed by `kimi_signal_tracking` (CRYPTO, n=657, PF 0.26, -955 PnL%)** and `alpha_engine_fast` (PF 0.62, -128 PnL%). Strip those + the other dragger systems and the picture is much better than the aggregate suggests.

### IMPLICATIONS

The user's question — "is there any subset that consistently wins" — answers **YES**:
1. The 6 Tier-2 systems above already meet hedge-fund-grade thresholds on PF/WR/MDD/n (per charter v1.0).
2. They are ASSET-CLASS-SPECIFIC: CRYPTO is the dominant winner (4/6 systems), COMMODITY is the pure-edge winner (`multi_asset_cot` PF 19.19).
3. NONE meet full Tier 1 (PF≥2 + WR≥55 + MDD≤10 + n≥200) — closest is `copy_trader_intel` (MDD ✓, n ✓, but PF 1.84 < 2 + WR 50 < 55).
4. EQUITY/ETF/BOND/FUTURES asset classes have no Tier-2 winners despite EQUITY class-aggregate looking OK (PF 1.58, WR 53.7, n=438) — that's the ONLY-EQUITY class verdict, but no individual system isolates EQUITY edge.
5. FOREX has zero Tier-2 winners and the class-aggregate is PF 0.27 — STAY OUT until rehab.

### NEXT STEPS

1. Spawn 5-engine swarm with this baseline + ask for: per-class real-money verdict, best DB queries to verify, hedge-fund-grade roadmap to Tier 1, drift-handling plan.
2. Walk-forward verification on the 6 Tier-2 systems (current numbers are cumulative; need rolling 30/90d to confirm consistency).
3. Quarantine kimi_signal_tracking + investigate alpha_engine_fast.
4. Investigate `ml_crypto_pred_v12` 2.5-month staleness — system stopped emitting?

---

## 2026-05-08 - Comprehensive Strategy Audit, DB Performance Review & Bug Hunt

**Source Prompt (saved verbatim for swarm/idea re-processing):**

look into our current strategies that feed into our database ejaguiar1_stocks or ejaguiar1_backtests .. and then check our performance by asset class and look for gaps in our backtesting timeframe, methodology, etc, and look to expand our strategy , and fix bugs in our database.. i.e. has a table not been updated in awhile? are we accidently pulling a wrong symbol into incorrect asset class. etc.. save your results into docs/ALLSTRATEGIES.MD and review our .MDs of existing strategies listing , we may already have ALL_STRATEGIES.MD or something like taht in fact I see a bunch 
C:\actions-runners\runner-1\_work\findtorontoevents_antigravity.ca\findtorontoevents_antigravity.ca\docs\ALL_STRATEGIES.md
... [full list of 70+ duplicate paths omitted for brevity - see original message]

proceed

**Notes for later review:**
- After completing the above audit tasks, re-read this file.
- Decide: re-process daily ideas via swarm? Expand with new ideas from audit findings? Run existing ideas through multi-agent review?
- Cross-reference with CHATWITHCLAUDE.MD and updates/ for continuity.
## 2026-05-08 - 48h Audit Picks Investigation + Swarm Consensus + Cron/AI-Picks Check

**Prompt saved for processing:**
investigate all our findtorontoevents.ca/audit picks by asset class over the past 48 hours and (both opened and closed) and feed each pick into an agent swarm, or leverage AI keys to ask AIs for their opinion and  look for consensus amongst AIs ..  also check if our cronjob is setup to constantly monitor strategies, or if there is an "AI based picks" something like that feeding into findtorontoevents.ca/audit some picks (maybe from our other hermes instance on my laptop) , also save that to DAILY_IDEAS.MD

**Action items added:**
- Query universal_resolved_picks.json + MySQL for last 48h (opened/closed)
- Group by asset class (CRYPTO/FOREX/EQUITY)
- Spawn swarm or multi-AI consensus on each pick
- Verify cron for strategy monitoring
- Detect "AI based picks" sources (chatgpt_combined, hermes-laptop, etc.)
- Append findings here + main ALL_STRATEGIES.md update

## 2026-05-09 - Mega Spec Swarm + Full Implementation + Unit Tests for /audit + /audit/hyrotrader

**Source prompt (saved verbatim, queued for self-verify in T+2h):**

```
/goal per our earlier requirement, generate a bunch of spec swarms. and get them all completed.
[Pasted text #2: 37 lines → /root/.hermes/pastes/paste_2_130449.txt]
get them all completed in specs but not only that fully implemented.
backtested and verified, unit tested
if done create a unit testing for all componenent of findtorontoevents.ca/audit and findtorontoevents.ca/audit/hyrotrader
including all systems / strategies etc
please proceed autonomously without asking questions, if unclear deploy a code swarm to get some ideas of the best path forward.
```

**Verification task (T+2h, ~14:00 UTC 2026-05-09):**
1. Re-read this entry.
2. Check status of:
   - Spec-swarm output dirs (look in `swarm_runs/` for new runs since 2026-05-09T12:00Z)
   - Implementation: are referenced strategies/components shipped to `alpha_engine/` / `audit_trail/` / `audit_dashboard/`?
   - Backtests: are there `__main__` blocks producing real numbers OR `tests/test_*` or `incubator/backtest_results/` entries?
   - Unit tests: do `tests/test_audit_*` and `tests/test_hyrotrader_*` exist? `pytest -k audit -k hyrotrader -q` count.
   - Verification: is there a verification report (`reports/verify_*_2026-05-09.md`)?
3. If gaps → deploy parallel subagents to close them.
4. If hermes paste #2 contents reachable at `/root/.hermes/pastes/paste_2_130449.txt` (WSL host), pull via `wsl cat ...` and add to this entry.

**Pre-existing context (already shipped this loop):**
- 3 new strategies: sentiment_macro_contrarian, crypto_pairs_arb, regime_filtered_momentum (commit 273908c1c19)
- Top-7 swarm queue items #1-#7 shipped
- Loop2 16-queue items #3, #7, #11, #12 shipped
- EW compound cap hardened 10→2 + ceiling 9999%
- Coverage validation: 5000 audit-rounds = 24 distinct names = 2.4% of 1008 production strategies (`docs/strategy-audit-rounds/COVERAGE_VALIDATION_2026-05-09.md`)
- Pending: FRED_API_KEY secret; Sharpe annualization redesign; rolling-window EW compound replacement

---

## 2026-05-11 22:55 EST — Multi-model trial-and-error: prove best model per asset class

**Source:** task carried over from another agent's session troubleshooting the Ollama ernie:latest setup. Bartowski's template for `hf.co/bartowski/baidu_ERNIE-4.5-21B-A3B-Thinking-GGUF:Q4_K_M` is buggy (missing user block + truncated `tart|>assistant` literal) so `ernie:latest` returns off-topic creative writing. Custom `ernie-coder.Modelfile` built (temp 0.2 / num_ctx 32k / proper chat template) but model still crashes with CUDA OOM unless `num_gpu=0` (CPU only). Forking it forward as an experiment idea, not a bug-fix.

### Core idea

Move from *theoretical* "which model is best at trading picks?" to **trial-and-error** with a measurable scoreboard. We already have:
- 40+ Ollama models installed locally: ERNIE 4.5 variants, Qwen3-coder 480B cloud, Qwen2.5-coder family, Kimi K2 / K2.5 / K2-thinking cloud, GLM 4.6 / 4.7 / 5 cloud, MiniMax M2 / M2.5 cloud, DeepSeek V3.1 / V3.2 / R1, GPT-OSS 20B / 120B cloud, Cogito 2.1 671B cloud, Llama 4 Scout, Mixtral 8x7B, Mistral / Mistral-Nemo, Phi-3.5, Gemma 3 / 4 cloud, Llama 3 / 3.1, plus existing `gpu-forced-qwen`, `claude-100-gpu`, `qwen3-vl 235B cloud`, etc.
- A persona-divergent fanout pattern (just used 10 different lenses → consensus aggregation for theswarm paper picks — see `TV_PICKS_WHY_2026-05-11_2229EST.MD` once committed).

### Experiment proposal

1. **Per-asset-class model bake-off:**
   - For each class (CRYPTO, EQUITY, FOREX, COMMODITY, ETF, FUTURES, BOND), ask every available model the SAME prompt: "Pick LONG/SHORT/SKIP for these 10 symbols + reasoning + timeframe + data sources you used."
   - Score over time: every pick gets a forward-validation outcome (WR + PF + R-multiple).
   - Build a leaderboard: `model × asset_class → live WR / PF`. Refresh weekly.

2. **"What's in the brain?" probe round:**
   - Ask each model to **list the data points it weighted** when making each pick. Capture as JSON: `{model, symbol, pick, data_points_cited: [..], confidence}`.
   - Compare cited data points across models — does ERNIE actually lean on COT positioning while DeepSeek leans on price-action? Or does every model just hallucinate the same Wikipedia-y rationales?
   - This is the diagnostic that separates "smart model" from "well-trained-to-sound-smart model."

3. **Debate round (10-20 turns):**
   - Pair up models cross-family (e.g., Qwen3-coder 480B vs Kimi K2.5 vs GLM 4.6 vs Llama4 Scout).
   - Topic: "What are the BEST criteria + FREE data sources for picking edge in CRYPTO?" (then same for each class)
   - Let them debate 10-20 turns with a moderator agent forcing concrete proposals (no hand-waving).
   - At the end, the moderator emits a `criteria_v1.md` per asset class (what to look at, where to scrape it from — Scrapling-compatible sources preferred so we can automate ingest).

4. **Backtest the criteria:**
   - Translate `criteria_v1.md` into a signal generator (this is where the v3b LLM signal-spec translator from idea A above starts paying compounding returns).
   - Backtest against the same 7,000-trade ledger we already have (`audit_dashboard/data/dashboard_data.json::performance`).
   - Promote criteria that beat T2 floors (PF>1.5 / WR>50). Reject the rest.

5. **Cycle:** if no criterion clears T2 in a class, swap in a fresh roster of models the next cycle. Specifically rotate the families: large MoE (Kimi K2 / Qwen 480B) ↔ dense (Llama 4 Scout / Llama 3.1) ↔ thinking-token (DeepSeek R1 32B / ERNIE Thinking / Kimi K2-thinking) ↔ small fast (Phi 3.5 / Qwen 3 4B). Cross-family disagreement = the signal worth chasing.

### Infra to build (not now, but on the runway)

- `tools/swarm/model_bakeoff.py` — single command: `python model_bakeoff.py --class CRYPTO --models all-local,all-cloud --symbols 10 --round-id 2026_05_11`. Writes `tools/swarm/bakeoff_runs/<round_id>/<model>/<class>.json` with picks + cited data points.
- `tools/swarm/data_point_diff.py` — compares which data points each model claims to use; flags hallucinated sources (e.g., a model citing a Bloomberg terminal it can't access).
- `tools/swarm/debate_orchestrator.py` — 10-20 round debate runner with a moderator critic that rejects vague hand-waving and forces concrete `data_source: <url>` + `signal: <formula>` proposals.
- `tools/swarm/criteria_backtester.py` — wire `criteria_v1.md` → signal generator → backtest harness → leaderboard update.

### Local-vs-cloud blend (cost vs latency tradeoff)

- **Local large (Llama4 Scout 67GB, Mixtral 26GB, ERNIE 13GB, Qwen2.5-coder 32B):** good for the high-volume bakeoff loop — free per query but slow.
- **Cloud large (Kimi K2 1T, Qwen3-coder 480B, Cogito 2.1 671B, GLM 4.6, DeepSeek V3.2):** good for the debate round where reasoning quality matters more than QPS.
- **Local small (Phi 3.5, Qwen 3 4B, Gemma 3 4B):** good for the "data-point extraction" probe — cheap, fast, and we don't need 200B params to ask "what did you weight?"
- **Thinking-token models specifically (DeepSeek R1, ERNIE Thinking, Kimi K2-thinking):** these are the ones we want for the debate round — visible reasoning chains are easier to fact-check.

### Suspicious tells to watch for (overfitting diagnostics)

- Every model converging on the same pick → could be real consensus OR shared training-data anchor. Cross-check the cited data points (are they all citing the same 2023 article?).
- A model with high local WR but low debate-round contribution = sample-mining without underlying methodology. Demote.
- Models that refuse to specify timeframe → vague signal, demote.
- Models that cite paid/inaccessible sources (Bloomberg, Refinitiv) → likely hallucinating, demote.

### Pre-existing ernie:latest crash fix (separate ticket)

To make ERNIE-thinking actually usable in this pipeline:
- The bartowski template is unfixable as-is. Use `ollama show <model> --modelfile` then rewrite TEMPLATE block.
- VRAM OOM on 13GB ERNIE: requires `keep_alive=0` on whatever model is currently loaded before requesting ERNIE, OR `num_gpu=0` (CPU offload, slow but works).
- Custom `ernie-coder.Modelfile` already at `tools/ernie-coder.Modelfile` — keep it; just don't reuse the broken bartowski TEMPLATE.

### Pending followups carried in from prior session

- The asset-class-health snapshot the other agent fed ERNIE shows: COMMODITY PF 3.77 + EQUITY PF 1.59 + CRYPTO PF 1.39 ALL pass T2 PF floor, but **EQUITY** and **CRYPTO** both meet WR>50 + PF>1.5 (cleanest T2 candidates). FOREX PF 0.28 with -1032% cumulative PnL → already sizing-off (correct per `[Mutate Before Kill]`). BOND n=11 too thin to score. Asset-class allocation in `theswarm` paper should weight COMMODITY/EQUITY first.

---

## 2026-05-12 17:25 EST — Swarm-pick tracking infra shipped (Q3 = YES decision)

Implements `docs/SWARM_PICK_TRACKING_DESIGN.md` design tasks 1-6 in two commits (`7ee3b5ca8f3` schema/backfill/resolver-skeleton + `4d688ed0cd9` resolver-wired/weekly-review/pattern-miner).

**Q3 decision (locked):** `models_consulted[].underlying_model` is REQUIRED on every vote — without it, the multi-model bake-off can't distinguish "MOMENTUM_TECH persona is good" from "Opus-4.7 backing that persona is good." 1 extra string field per vote.

**Files shipped:**
- `tools/swarm/swarm_pick_schema.py` — validator + tier-derivation. Enforces side-sanity on write (LONG: tp>entry>sl, SHORT: sl>entry>tp). Atomic write via tmp-then-rename.
- `tools/swarm/backfill_sessions.py` — hand-mapped 38-pick backfill from the two committed session .MD files. Refuses overwrite.
- `audit_dashboard/data/swarm_picks.json` — 38 records (22 round-1 + 16 round-2). 5 already resolved by first resolver run.
- `tools/swarm/outcome_resolver_swarm.py` — yfinance-backed `fetch_high_low()` with SYMBOL_MAP for crypto/forex/futures + exchange-prefix strip for stocks. APT-USD + POL-USD delisted on yfinance — return None (pick stays open). TODO: TV MCP `data_get_ohlcv` fallback for delisted crypto.
- `tools/swarm/weekly_review.py` — per-tier + per-class + per-persona + per-underlying-model WR/PF report + `swarm_leaderboard.json` (consumable by future fanouts to weight votes by historical accuracy).
- `tools/swarm/pattern_miner.py` — winning vs losing `(tier × class × regime)` cells. Lowered n threshold to 5 (from design's 10) since store is still seeded — bump back when resolved-pick count crosses 100.

**Live numbers as of 2026-05-12 17:22 EST:**
- 38 picks tracked, 5 resolved, 33 open.
- Overall WR 40%, PF 0.8 (n=5 — not statistically significant yet; need 100+ resolved for any conclusion).
- Per-class so far: ETF 100% WR (n=1 — GLD), FUTURES 100% WR (n=1 — MCL), CRYPTO 0% WR (n=2 — ADA shorts didn't hit TP in 1d window), FOREX 0% (n=1 — USDJPY stopped out).
- Per-persona top so far: NEWS_FLOW agreed on 7 picks 1 resolved 100% WR (single sample). All others n=0 resolved.

**Remaining design tasks (not yet shipped):**
- Task 4-extension: TV MCP `data_get_ohlcv` fallback for delisted yfinance tickers (APT/POL today)
- Task 7-10: dashboard panel on `/audit` (subagent dispatched 2026-05-12 17:25, awaiting result)
- Cron-style schedule: wire `outcome_resolver_swarm.py` + `weekly_review.py` + `pattern_miner.py` as a Sunday-23:00-EST routine via `/schedule` skill so the pipeline auto-refreshes.
- Backfill round-3+ as new sessions land — extend `backfill_sessions.py` with one function per session or write a generic `.MD` parser.

**Bake-off precondition met:** with `underlying_model` field stamped on every vote, the data pipeline can now answer "is Opus-4.7 better than Qwen3-coder-480B at FOREX picks?" once enough resolved picks accumulate across both models. The DAILY_IDEAS.MD 2026-05-11 22:55 EST proposal can now plug into `swarm_picks.json` as its persistence layer.

---

## 2026-05-12 — Statistical Edge Per Asset Class: Data-Driven Analysis

**Source:** `audit_dashboard/data/dashboard_data.json` (generated 2026-05-12T20:14Z), 134 systems, 32 with n>=20.

### Class-Level Edge Ranking (sorted by PF × WR composite)

| Rank | Class | PF | WR | Verdict |
|------|-------|----|----|---------|
| 1 | **COMMODITY** | **3.94** | **67.8%** | **STRONG EDGE** — class-level meets T2 on both axes |
| 2 | EQUITY | 1.55 | 53.2% | DEFENSIVE — meets T2 PF, borderline WR |
| 3 | ETF | 1.34 | 56.1% | BORDERLINE — WR passes T2, PF slightly below |
| 4 | CRYPTO | 1.36 | 46.5% | **MASKED** — top systems are great but class dragged by high-volume losers |
| 5 | UNKNOWN | 2.40 | 50.0% | SUSPECT — misclassified picks, audit needed |
| 6 | BOND | 0.66 | 54.5% | INSUFFICIENT n, degraded from May 10 |
| 7 | FOREX | 0.29 | 46.2% | **TOXIC** — pure FOREX is uninvestable |
| 8 | FUTURES | 0.00 | 0.0% | **DEAD** — no signals |
| 9 | SPORTS | 0.00 | 0.0% | **ELIMINATE** — confirmed dead weight |

### Hidden Insight #1: Two Distinct Edge Regimes

**Regime A — Trend-Following (low WR, high PF, fat-tailed):**
- `multi_asset_copytrader` — PF 4.09, WR 36.1%, n=812, MDD 16.7%, avg win 1.83/avg loss 0.49
- Wins 1-in-3 but pays 3.7x on winners vs losers.
- Most robust risk-adjusted returns in the entire dataset.

**Regime B — Pattern Recognition (high WR, medium PF, thin-tailed):**
- `multi_asset_cot` — PF 21.33, WR 88.2%, n=144, MDD 17.8%
- `aggregated_picks` — PF 5.47, WR 73.3%, n=363, MDD 49.2%
- High hit rate but severe drawdowns.

**Implication:** Blend Regime-A (60%, sizing overlay for tails) + Regime-B (40%, tight MDD stop) for lower combined MDD.

### Hidden Insight #2: CRYPTO True Edge Masked by High-Volume Losers

Top CRYPTO systems are elite: `aggregated_picks` (PF 5.47, WR 73.3%, n=363), `mega_mutation` (PF 2.32, WR 56.8%, n=148), `claude_gainer` (PF 2.23, WR 56.2%, n=32). Class-level PF 1.36 is dragged by `luxalgo_filters` (PF 1.08, n=1,329), `baby_strats_forward` (PF 1.40, n=2,042), and `kimi_signal_tracking` (PF 0.28, n=173, MDD 995%). Concentrated top-3 yields blended PF ~3.3.

### Hidden Insight #3: multi_asset_copytrader Is Most Robust System

PF 4.09 across 5 classes (BOND/COMMODITY/EQUITY/FOREX/FUTURES), n=812, MDD 16.67% (inside Tier-1 cap). Best candidate for go-live paper trading NOW. Needs walk-forward verification.

### Hidden Insight #4: FOREX's Only Viable Entry Point

`signal_validation` (CRYPTO+FOREX): PF 4.31, WR 51.0%, n=98, MDD 8.14%. Only system touching FOREX with positive PF. Isolate its FOREX-specific signals.

### Hidden Insight #5: No System Achieves Full Tier 1

Closest: `multi_asset_cot` (MDD 17.83% >10, n=144 <200), `aggregated_picks` (MDD 49.25% >10), `multi_asset_copytrader` (WR 36.1% <55), `signal_validation` (n=98 <200, WR 51% <55). COMMODITY closest to full Tier 1.

### Hidden Insight #6: Emission Decay Is Natural Selection

5 dead systems — ALL poor performers (PF 0.31-0.92). No good system went dark.

### Actionable Next Steps

1. **Papers trade `multi_asset_copytrader`** — best risk-adjusted system, multi-asset, n=812
2. **Isolate `signal_validation` FOREX signals** — only known FOREX entry point
3. **Combine `aggregated_picks` + `mega_mutation` as CRYPTO ensemble** — joint MDD stop at 30%
4. **Remove SPORTS class** — PF None, WR 0%, confirmed dead weight
5. **Walk-forward validate `multi_asset_cot`** — PF 21.33 is suspicious without rolling verification

---

## 2026-05-12 — TV Paper Trace Lessons (5 resolved + 13 open across 4 accts, 21:15 EST snapshot)

Source: TV state captured at 2026-05-12 21:15 EST traced against `audit_dashboard/data/dashboard_data.json::systems` (gen 2026-05-12 23:23Z), `swarm_leaderboard.json::by_tier`, and `performance.asset_class_health`.

### 2026-05-12 — Lesson: Single-persona swarm picks have no production validation

**Pattern observed:** 22 of 38 swarm picks (`swarm_picks.json`) are `consensus_tier=single` (1/1 vote). Only the `single` tier has any resolved outcomes in `swarm_leaderboard.json::by_tier` (n=5, WR 40%, PF 0.80). `unanimous`/`strong`/`moderate` tiers have 0/16 resolved. Winning TV picks RUNE-L (single MOMENTUM_TECH conf 55) and BNB-L (single FUND_VALUE) come from underlying systems (`momentum_tech`, `fund_value`) that are NOT in the `systems` block at all. The closest live tracker `aggregated_picks` reports WR 73.2% / PF 5.42 (n=366) but excludes single-persona swarm output.
**Hypothesis:** Single-persona picks are untracked alpha. We are flying blind on >55% of TV swarm volume. Either suppress them in TV deployment, or wire them through `aggregated_picks` ingestion so they accumulate audited stats.
**Backtest required:** Backfill last 60 days of single-persona swarm picks via `alpha_engine/swarm_picks_resolver.py` (or build it if missing) — resolve TP/SL/timeout against historical OHLCV; compute per-persona WR/PF; compare to multi-persona resolved cohort.
**Acceptance criteria:** Promote `single` tier to TV-eligible only if backfilled n>=100 yields PF >= 1.30 AND WR >= 50%. Otherwise gate behind tier>=`moderate` (2+ votes) at deploy time.
**Effort:** 6h

### 2026-05-12 — Lesson: SHORT-bias on EQUITY/CRYPTO is not yet supported by sample

**Pattern observed:** Among 13 TV picks captured tonight, SHORTs net winning on EQUITY mega-caps (TSLA-S +$110, NVDA-S −$21 but tier-5/6) and on coins where ml_strategy_reviver_inverse fires (ADA-S +$61 zerounderscore, ADA-S +$49 theswarm). But SHORTs also dominate the loser column: DOT-S −$64 CLOSED, DOGE-S −$29 CLOSED, POL-S −$16. Resolved swarm-leaderboard CRYPTO cohort is 0/2 wins so far. `alpha_engine` (n=926, active) has PF 1.61 across mixed sides — no side breakdown is published; we cannot confirm SHORT-edge from production data.
**Hypothesis:** SHORTs in mega-cap EQUITY during the current macro-bear regime (5/6 personas SHORT TSLA / NVDA in the swarm vote) have positive expectancy, but CRYPTO SHORTs lack edge. The pattern is asset-class-conditional, not universal.
**Backtest required:** Run `tools/mutation_analysis.py` (or equivalent side-stratified scanner) on closed picks across last 120 days, grouped by `(asset_class, side)`. Confirm whether EQUITY-SHORT PF beats EQUITY-LONG PF, AND whether CRYPTO-SHORT PF is below 1.0.
**Acceptance criteria:** Add an asset-class-conditional side gate to TV deployment only if EQUITY-SHORT PF>=1.40 with n>=80 AND CRYPTO-SHORT PF<=1.05 (current "no edge" zone). Otherwise treat side-bias as noise.
**Effort:** 4h

### 2026-05-12 — Lesson: Class health predicts winners better than persona-count

**Pattern observed:** TV winners cluster on STABLE asset classes: GLD-L (COMMODITY: WR 70.7% / PF 4.08 / n=280), TSLA-S + LLY-L (EQUITY: WR 52% / PF 1.58 / n=410), ADA shorts (CRYPTO: WR 46.6% / PF 1.37 / n=7758). TV losers cluster on stressed/thin classes: TLT-L (BOND thin n=11 / PF 0.66), BAC-L (despite EQUITY-stable, tier=moderate 2 personas only), POL-S (CRYPTO but POL=MATIC rebrand — `quan_engine` MATIC artifact warning in MEMORY.md). Across resolved swarm cohort, `by_asset_class` shows COMMODITY/FUTURES winning singletons, while CRYPTO 0/2.
**Hypothesis:** Class-health verdict (`asset_class_health[status]`) is a stronger ex-ante filter than swarm tier. A `strong` tier pick on a `stressed` class (TLT, FOREX) should be downgraded; a `single` pick on a `stable` high-PF class (COMMODITY) deserves promotion.
**Backtest required:** Join `swarm_picks.json` with `performance.asset_class_health` at pick time; compute conditional WR/PF for (tier, class_status) cells. Compare to baseline (tier-only and class-only).
**Acceptance criteria:** Class-status-conditioned gating must lift system PF >= +0.15 vs current tier-only gate on a 90-day walk-forward holdout. Reject if lift < +0.10.
**Effort:** 5h

### Notes on what did NOT make the lesson cut

- "6+ persona agreement beats 3-5" — UNTESTABLE: only 5 of 38 picks resolved, all `single` tier. Zero data on `strong`/`unanimous`/`moderate` outcomes. Re-check in 7 days once outcomes accrue.
- "`underlying_model=claude-opus-4-7` outperforms" — UNTESTABLE: `by_underlying_model` has only 1 key (only Opus tracked). Null hypothesis cannot be rejected.

---

## 2026-05-12 — PCG-5: Portfolio Construction Gate Stack v1 (NOVEL methodology)

Source: portfolio-construction methodology agent (2026-05-12 21:50 EST) responding to honest swarm verdict "methodology generates *candidates*, not *portfolios*."

**Verdict on novelty:** the *individual primitives* exist scattered in the repo (CRYPTO_SHORT_REGIME_GATE in `quality_gates.py:729-820`, `asset_class_concentration` WARN/BLOCK in `dashboard_generator.py:13888-13935`, partial-TP helpers in `combined_confidence_strategy.py`, correlation matrix in `correlation_regime.json`) — but **the packaged 5-gate exec-time REJECT stack across all accounts is NOVEL.** Existing gates are mostly *disclosure* (warn the user, write to dashboard), not *enforcement* (reject the pick).

### Methodology — PCG-5

Runs AFTER candidate generation, BEFORE order submission. Reads live state from `audit_dashboard/data/{dashboard_data.json, correlation_regime.json, edge_stability/*}` plus per-account position dumps. Returns: `APPROVE` / `NET` (close offsetting leg first) / `REJECT`.

**Gate 1 — REGIME_DIRECTIONAL_GATE**
- if regime ∈ {BULL,BULLISH} AND pick.asset_class=EQUITY AND pick.direction=SHORT → REJECT unless thesis.catalyst ∈ {earnings_miss, downgrade, fraud, dilution}. Mirror for BEAR + LONG. Extends existing CRYPTO_SHORT_REGIME_GATE to EQUITY/ETF/INDEX_STOCK.

**Gate 2 — CROSS_ACCOUNT_NET_POSITION**
- scan all accounts keyed by canonical_symbol. If opposite-direction position on another account: if size_new > size_existing → NET (close existing first), else REJECT. If same-direction same account → REJECT (duplicate). Correlation expansion: pairs (BTC/ETH ρ>0.85, EUR/GBP, ES/NQ) as same symbol.

**Gate 3 — CONCENTRATION_REJECT**
- if class.top_share_pct >= 50% AND pick.symbol = class.top_symbol → REJECT. Force rotation to class-cousin. WARN 50-70%, hard block ≥ 70%.

**Gate 4 — PROFIT_LOCK_SCAN**
- every cycle: if any open position unrealized_pnl_pct >= +3.0%, require one of {SL_at_breakeven, partial_close_50pct, trailing_stop_armed}. Else block new picks on same account.

**Gate 5 — CROSS_CLASS_CORRELATION_DEMOTE**
- if |corr(class_A, SPY)| >= 0.35 in current 30d window → class_A.sizing_role = `risk_on_beta`. Counts toward EQUITY exposure cap, not own bucket. Reverts when corr < 0.20 for 7 consecutive days.

### Implementation plan

Ship as `audit_trail/portfolio_gates.py` imported by every account's exec wrapper. Shadow-mode 7 days (log to `audit_dashboard/data/pcg5_log.json`), then enforce.

### Tonight's PCG-5-approved picks (placed 2026-05-12 22:00-23:00 EST)

- **zerounderscore:** AUDUSD-L 5000 (TP 0.7309 SL 0.7208) — Gate 5 demoted half-size (AUD risk-on); MCL-L 1ctr @ 101.07 (TP 104.10 SL 99.55) — Gate 3 rotation away from CT=F
- **theswarm:** MHG-L 1ctr @ 6.6495 (TP 6.848 SL 6.5155) — copper, Gate 3 rotation; MGC would have failed Gate 5 (GLD-L already long gold)
- **Leap:** SOL-S 15 @ 95.578 (TP 88.40 SL 100.35) — small per CRYPTO DECAYING_EDGE
- **SL tightens (Gate 4):** TSLA-S→440, ADA-S theswarm→0.2775, LLY→970, BTC-S Leap→81,500

### PCG-5 REJECTED tonight (gates fired)

1. "Add another equity SHORT (SQ/RBLX/COIN-S)" → Gate 1 (BULL + EQUITY + SHORT, no catalyst)
2. "Add more CT=F LONG" → Gate 3 (75% concentrated)
3. "Add GLD-L as hedge" → Gate 5 (GLD↔SPY +0.7674, demoted to risk-on beta)
4. "Open BTC-L on Leap/zerounderscore" → Gate 2 (theswarm has BTC-L, Leap has BTC-S)
5. "Open ADA-L anywhere" → Gate 2 (ADA-S open on theswarm + zerounderscore)
6. "MGC theswarm" → Gate 5 (GLD-L already on theswarm = doubling gold)

### Memory candidate

"**PCG-5 — disclosure ≠ enforcement.**" Repo publishes concentration/correlation/penalties as scoring inputs and dashboard banners, but none reject a pick at exec time. Crypto-short regime gate (2026-04-29) is the only true exec-time gate. Every PCG-5 sibling follows the same pattern: take an existing published metric and promote it from "FYI banner" to "exec-time REJECT."

Suggested filename: `memory/feedback_disclosure_is_not_enforcement.md`. Tie-in: cleaner restatement of existing `feedback_gate_at_execution_not_generation.md` — generalized from "filter-named accounts" to "every published risk metric."

### Effort + acceptance

- Phase 1 (shadow log): 8h. Ship `portfolio_gates.py` + wire into `tv-paper-trade` skill pre-execute path.
- Phase 2 (enforce): 4h after 7d shadow shows >50% picks would have been re-routed.
- Acceptance: realized PF on next 100 PCG-5-approved picks must beat realized PF on prior 100 ungated picks by ≥ 0.15. If not, demote Gates 4+5 first (most aggressive), keep Gates 1-3.

---

## 2026-05-14 — User prompt: "stuck-in-backtest, what protocol moves us to real money?"

**Source prompt (verbatim, captured 2026-05-14T23:12Z, queued for swarm processing):**

> What sort of protocol would you recommend to take a giant repository which tries to predict stocks/crypto/forex/bonds/commodities/futures ... and then find out whether we need to be expanding our strategies, mutating the strategies, improving our safety gates, expanding to other stuff like options.. how we can identify the most effective changes we can perform to improve our win-rate /profits to more of a "spending real money" vs just backtesting.. we have been stuck backtesting for months.. and havent had much success despite extensive use of AI .
>
> our repo is https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/
> and website findtorontoevents.ca/audit and findtorontoevents.ca/audit/hyrotrader
> with our updates under findtorontoevents.ca/updates

**Why captured here:** user explicitly framed this as a stuck-in-backtest diagnostic and asked for a *protocol* (repeatable). Goal is move-the-needle from paper to real-money. Process must answer: expand vs mutate vs gate-tighten vs broaden-asset-class. Tie-in to existing money-maker-ready skill output (`reports/money_maker_ready_*.md`), supreme-plan tracker, and `[North Star: HF Edge Per Asset Class]`.

### Sketch — "Stuck-in-Backtest Escape Protocol" (S-BEP)

Self-diagnosis ladder. Each rung must show measurable lift before climbing:

1. **Diagnose stuck-state** — quantify months in backtest vs $0 live. Compute (a) tally of strategies passing internal gates but never deployed, (b) ratio of dead-emitter to live-emitter systems, (c) fwd_vs_bt decay distribution, (d) drift `KS_D` trend.
2. **Honest baseline** — re-run `/money-maker-ready` + cross-verify with DB queries. Tier-classify every system today. Anything claimed Tier-2 that doesn't survive cross-check = drop.
3. **Bottleneck identification** — what is gating live deployment? Pick exactly one of {data-quality, resolver bug, sample size n<floor, MDD too high, drift, no walk-forward, no shadow record, regulatory/operational}. **The protocol fails if you try to fix more than one bottleneck per cycle.**
4. **Smallest experiment that proves edge** — for ONE candidate strategy on ONE asset class:
   a. shadow-paper 30 picks (real-time, not historical replay),
   b. compute realized vs predicted WR/PF gap,
   c. gate: shadow PF ≥ 0.85 × backtest PF AND realized WR within ±5pp of backtest WR.
5. **Real-money pilot at 0.1% sizing** — only after the shadow gate passes. 30 picks live. Stop on hard MDD cap.
6. **Scale gate** — 0.1% → 0.5% only if pilot PF ≥ 1.30 AND MDD ≤ 12%. 0.5% → 1% only after 60 more clean picks.
7. **Expand outward** — only after one class proves Steps 4-6 does the protocol authorize: (a) mutation rounds on adjacent strategies (per `MUTATION_THREE_AXIS_PROTOCOL.md`), (b) new asset-class expansion, (c) options sleeve. Out-of-order expansion = protocol violation.
8. **Continuous drift watchdog** — auto-pause sizing on `KS_D > 0.10` per money-maker-ready P1. Pause is not a kill; it's a re-validate.

### Sub-questions to swarm

- Is "expanding strategies" the right play when 33/42 audited strategies are OVERFIT_LIKELY (per supreme plan)? Or is the bottleneck *strategy quality density* not *count*?
- What gates are missing that would have caught the kimi_signal_tracking PF-flip BEFORE live deployment?
- Options expansion (CBOE put/call, UOA, max-pain) — does it deepen existing crypto/equity edge, or just add a new surface to overfit?
- AI-extensive use w/o success: are we hitting the *Goodhart trap* — optimizing for swarm-consensus metrics instead of realized PnL? If so, what metric do swarms have to predict to count as useful?
- Hyrotrader sub-account specifics — does the `/audit/hyrotrader` surface have its own bottleneck distinct from `/audit`?

### Acceptance — when this protocol has "worked"

- ≥1 asset class reaches real-money pilot stage (Step 5) within 8 weeks of protocol start
- ≥1 pilot strategy clears Step 6 scale gate within 16 weeks
- Drift watchdog auto-pause fires at least once and is acted on (re-validates, not ignored)
- `reports/money_maker_ready_*.md` cadence becomes daily and tracks a tightening verdict over time

### Effort: design 8h, full implementation 4-6 weeks. Tie-in: feed the daily supreme-plan tracker (proposed 2026-05-14) with `(stuck_state_quantified, bottleneck_identified, experiment_status, drift_state)`.

---

## 2026-05-14 — ChatGPT FOOLPROOF restatement (5th protocol, same family)

User pasted ChatGPT-style synthesis of `FOOLPROOF_ACTION_PLAN.md v2.1`. Adds: a Risk-Management Kill-Switch ladder (5% portfolio DD → halve, 10% → full stop, asset PF<0.80 for 5d → halt that class, 3 consecutive >5% losses → reduce to 25%, correlation>0.70 top-3 → flag concentration risk) — slightly different from but compatible with our Kimi Level-3 thresholds. The 12-week milestone table is identical to Foolproof §11. Convergence confirmed: this is the same 8-stage Gate Ladder rendered yet again by a 5th LLM. Action: incorporate the kill-switch ladder's specific numbers (5%/10%/etc.) into `reports/expanded_enhancement_plan_2026-05-14.md` Section 5 Stage D recommendations when implementing PCG-5 Phase 2.

---

## 2026-05-14 — Mercury 6-phase protocol = Inception Labs (verbatim duplicate, confirmed convergence)

User pasted Mercury 6-phase protocol on 2026-05-14T23:30Z; text is **byte-for-byte identical** to the Inception Labs 6-phase protocol captured earlier this date. Confirms this is a shared canonical "Foundations → Validation → Robustness → Paper → Live → Continuous → Options" template across multiple LLMs (likely sourced from a common doc — possibly López de Prado AFML structure or QuantStart-style curricula). No additional content to merge; the Mercury input fully overlaps the Inception merge below and the expanded enhancement plan at `reports/expanded_enhancement_plan_2026-05-14.md` already maps both into the Gate Ladder. Action: cite Mercury alongside Inception in any future protocol references.

---

## 2026-05-14 — Inception Labs 6-phase protocol (captured verbatim)

User-pasted from Inception Labs. Same family as Kimi's Gate System but split across 6 numbered phases. Captured for cross-merge into expanded enhancement plan + future swarm rounds. Verbatim source:

- **Phase 0 — Foundations & Governance:** version control + reproducibility (Git tags v1.0-alpha/beta), CI/CD running unit + data-integrity + quick backtest on every push, audit/compliance read-only trail, risk-policy framework (max daily/weekly drawdown, position-size caps, kill-switch).
- **Phase 1 — Data & Model Validation:** data hygiene (no missing timestamps, corporate actions, time-zones, survivorship-bias + look-ahead checks), feature sanity plots over time for drift, walk-forward (12m train → 3m OOS rolling), Sharpe/Sortino/Calmar/MDD + bootstrap CI + p>0.05 reject, overfit detection (param count vs effective data, AIC/BIC, CV loss).
- **Phase 2 — Robustness & Stress Testing:** parameter sensitivity ±10%, scenario analysis (2008/2020 replay + synthetic), transaction-cost modeling (slippage + commission + latency), OOD detection (autoencoder, reconstruction error > 3σ → safety gate), Monte-Carlo ruin probability.
- **Phase 3 — Paper-Trading & Shadow Mode:** paper-trade with live data zero capital, shadow mode parallel to prod no orders, KPIs (latency, fill-rate, slippage, realized vs predicted), promote-only-if (paper Sharpe > 1.0 AND MDD < 5% equity AND OOD < 1% ticks).
- **Phase 4 — Controlled Live Deployment:** ≤1% capital per new strategy, Kelly-fraction / vol-scaled sizing, dynamic ATR-based limits, real-time monitoring dashboard with alerts, kill-switch on drawdown/OOD/latency, A/B testing disjoint capital slices with statistical tests on live returns.
- **Phase 5 — Continuous Improvement Loop:** nightly data refresh, monthly model retrain on rolling 2y window with hold-out gate, automated hyperparameter mutation (Bayesian / GA) kept only if passes Phase 2, sub-models per new asset class feeding unified risk manager, monthly performance review documented.
- **Phase 6 — Expansion to New Instruments (e.g. Options):** IV-surface + Greeks in feature set, delta-neutral spreads first (calendar/iron condor), Vega/Theta/max-loss tracking, liquidity filter (OI > 10k + tight spread), regulatory/margin compliance.

**Quick-start checklist:** Data pipeline → Backtest framework → Robustness suite → Paper-trading → Safety gates → Live-trading sandbox → Continuous loop.

**Open questions Inception flagged:** (1) which phase to prioritize given current bottlenecks? (2) recommended CI/CD + monitoring tools? (3) how to integrate options/derivatives with risk controls?

**Tie-in:** merges 1:1 with Kimi Gate System (Levels 1-5) above. Kimi Level 1 = Inception Phase 1; Kimi Level 2 = Inception Phase 2; Kimi Level 3 = Inception Phase 0 (governance + circuit breakers) + Phase 4 (live deployment kill-switch); Kimi Level 4 = Inception Phase 3 (paper/shadow) + Phase 4 micro-deployment; Kimi Level 5 (expansion) = Inception Phase 5 + 6.

---

## 2026-05-14 — Grok "Foolproof Live-Trading Protocol v1" (captured verbatim)

User-pasted Grok output. Audit on `findtorontoevents.ca/audit` + `mysql.50webs.com::ejaguiar1_*`. Captured for direct cross-merge.

**Grok's snapshot of our state (55k+ resolved trades):**
- System-wide: −3.56% avg return, 11.13% WR, PF 0.46 (NOTE — disagrees with current `asset_class_health` aggregates; Grok numbers likely older or computed pre-resolver-v2).
- COMMODITY = only genuine edge (PF ~3.77, DSR 1.0 on `cot_positioning` + CT=F).
- EQUITY best ML accuracy (83%+) but low volume.
- CRYPTO dominates volume but drags PnL (confidence inversion in gatekeeper).
- FOREX stressed PF 0.29 but documented SHORT bias.
- BOND + FUTURES thin/silent.
- CFTC COT (May 5 2026): commercials covering shorts in energy, record net-long in agriculture → reinforces COMMODITY edge.

**Grok Gate System v1 — same family as Kimi + Inception, 5 levels:**
1. Paper-Cut Gate (Monkey test + out-of-time 60/20/20, Sharpe>1, PF>1.5, >100 trades, WR>50, 2+ regimes).
2. Slippage & Reality Gate (crypto 0.1% round-trip, stocks 0.001+borrow, FX spread, position<1% ADV, 100-500ms latency sim, weekend test). Net-after-cost >50% gross or kill.
3. Safety Architecture Gate (hard daily 2% / weekly 5% / 3-loss-cooldown, quarter-Kelly + 2% risk-per-trade, no >3 strategies ρ>0.7, auto-shutdown if 30d Sharpe<0.5).
4. Skin-in-the-Game Gate ($500–$2k for 30 days REAL, paper+live shadow, journal every deviation, scale-to-10% if live Sharpe > 0.7× backtest).
5. Expansion Matrix (no 4th asset class until 3 are live-profitable 90d).

**Per-asset-class roadmap (Grok specifics, next 7 days):**
- **COMMODITY (P1):** wire COT commercial z-score gate (`quality_gates.py` + `extract_features`), run `cot_positioning` on CT=F with **lag-corrected** backtest (per `reports/cot_timing_leakage_audit_2026-05-13.md`), target PF>4.0 / DSR 1.0 → Level 4 micro-deployment.
- **EQUITY (P2):** per-class `ml_score >= 55` gate + FRED GDP/ISM overlay.
- **CRYPTO (P3):** Tuesday-only hard filter + cap `quan_engine` to 12% volume (already shipped via PR #906 per `supreme_plan_review_2026-05-13.md`).
- **FOREX (P4):** SHORT-only + COT reversal gate.
- **BOND (P5):** fix `FRED_API_KEY` secret + expand universe (TLT/IEF) + Connors RSI2 on TLT/IEF.

**Grok's commit-target file (proposed, content to be merged not blindly accepted):** `FOOLPROOF_ACTION_PLAN.md` v1 at repo root with first-real-money-date 2026-05-23 on COMMODITY `cot_positioning` CT=F.

**Important caveat:** Grok references `FRED_API_KEY` secret and a Tuesday-only crypto gate. The FRED key is already a known gap (cited in supreme-edge P0 cluster). The Tuesday-only claim needs cross-verification — it conflicts with `feedback_long_source_bias.md` and `reference_clean_data_symbol_wr.md` which call out *22 UTC* as the best slot and *08-09* as death zone, not Tuesday-vs-other-weekdays. Statement requires DB-query reproducer before trusting.

**Tie-in:** merge into `reports/expanded_enhancement_plan_2026-05-14.md` (separate file). Map each Grok level to corresponding Kimi level and Inception phase. Cross-check Grok per-class claims against current `asset_class_health` + `tier2_proven_strategies.cards` before accepting any specific gate config.

---

## 2026-05-14 — User prompt: "what techniques would a quant/hedge fund manager apply to fix gaps?"

User-pasted prompt (verbatim, 2026-05-14T23:50Z, queued for swarm + future research):

> Our website/github has been struggling to predict consistently stocks/crypto/forex/bonds/commodities/futures..etc. We MIGHT have some hidden edge.. we might have some extra factors if we add it that can get us to winners.. what sort of techniques would a Quant/hedge fund manager apply to our codebase to optimally fix the gaps?

**Why captured:** complements `2026-05-14 — Stuck-in-Backtest Escape Protocol` (S-BEP). That captured the *process*. This captures the *technique-set* question. Tie-in: feed both to swarm for cross-validation rounds.

### Mercury 2 reply (captured verbatim 2026-05-14T23:55Z) — concrete quant-fund-style playbook

7-section playbook with exact file targets. Pasted below for archival. Already partially absorbed into `reports/expanded_enhancement_plan_2026-05-14.md`; this is the source.

#### Section 1 — Data-enrichment / hidden-edge sources (with code locations)

| Edge source | Why | Code location | Quick start |
|---|---|---|---|
| CFTC COT commercial positioning | Proven edge for COMMODITY+FOREX (extends `cot_positioning`) | `audit_trail/quality_gates.py::extract_features()` + `audit_trail/feature_engine.py` | Reuse `COT_DATA_URL` constant; add `cots` column to daily feature df |
| Glassnode on-chain (MVRV/SOPR/exchange-flow) | Crypto-specific supply/demand invisible to price-only features | `forward_testing/signal_quality_ml.py::build_feature_vector()` | `pip install glassnode` or HTTP endpoint; merge JSON into `crypto_features` |
| LunarCrush social sentiment | Early pump-and-dump detection → better short-side timing | `audit_trail/quality_gates.py::ml_score` calc | Add `social_score` (0-1), feed to `signal_quality_ml` |
| FRED macro (VIX, CPI, Treasury yields, credit spreads) | Regime-aware filters for EQUITY/FOREX/BOND/COMMODITY | `audit_trail/feature_engine.py::add_macro_features()` | `pandas_datareader` last 60d; join on date |
| Option implied-vol surface (yfinance / ivol) | Delta-neutral vol-carry edge for EQUITY/ETF + high-vol regime filter | `audit_trail/feature_engine.py::add_option_features()` | Compute `iv30d`, `iv60d`, `skew` per ticker |
| Weather / calendar / agricultural cycles | COMMODITY seasonality | `audit_trail/feature_engine.py::add_seasonality_features()` | CSV of US holidays + month-of-year flag |

**Implementation tip:** lazy-load each new source returning None on failure. Existing quality_gates already fail-open on missing fields.

#### Section 2 — Feature engineering + edge extraction

- Cross-asset correlation features (crypto-vs-gold, equity-vs-bond) → `audit_trail/feature_engine.py` after per-asset features
- Lagged returns / vol windows (1/3/7 day) → `forward_testing/signal_quality_ml.py::create_lag_features()`
- Factor-model residuals (Fama-French, Barra) → `audit_trail/feature_engine.py::add_factor_residuals()`
- Non-linear interactions (XGBoost trees, NN embeddings) → replace logistic regression with `xgboost.XGBClassifier` in `signal_quality_ml`
- Feature-importance pruning (SHAP) → post-training step drops features SHAP<0.01

#### Section 3 — Model selection + robustness

- Bayesian hyperparam search (`optuna`) — 200 trials on 30-day rolling
- Ensemble (GBM + RF + Linear) — average probabilities
- CPCV (Purged Combinatorial CV) per `project_cpcv_gap_2026_04_28.md`
- Monte-Carlo ruin simulation — verify P(DD>30%) < 5% before paper trade
- PSR/DSR bootstrap — bump reps to 20,000 for tighter CI

#### Section 4 — Risk-gate + safety enhancements (vs current)

| Gate | Current | Mercury 2 target |
|---|---|---|
| R:R band | 1.25-3.0 (empirical) | **Harden to 1.5-2.0** — but contradicts our `config/hf_quality_gates.json:15` empirical PF measurement showing 1.25 better. Mercury 2 here is repeating the Foolproof §4.2 target we already determined was stale. NOT accepted without re-test. |
| ml_score | 0.82 (live, n>0 at 0.82) | 0.90 — but 0.90 yields n=0 per config line 15. NOT accepted without volume verification. |
| Tracking window | 24h (legacy global; 120h FOREX/BOND) | **Global 120h** — agreed P0 #5 in expanded plan |
| Transaction-cost model | MISSING | **Populate `TRANSACTION_COST_MODEL`** — agreed P0 #4 in expanded plan |
| Drift auto-pause | **SHIPPED 2026-05-14** (`_passes_drift_auto_pause_gate`) | Already done |
| Circuit-breaker | Daily 2% hard | Add soft CB that halves Kelly when 30d Sharpe<0.5 |
| Correlation cap | None | Reject new pick when portfolio-avg corr > 0.7 |

#### Section 5 — Execution + deployment

- CI/CD model training: `ci-model.yml` GHA running optuna → `config/best_params.json`
- Paper-trade sandbox: existing `alpha_engine/paper_trading/`
- Shadow-mode live: duplicate pick list in `smart_picks_engine`, one to exchange one shadow
- Real-money micro: $500 on COMMODITY `cot_positioning` (only T2 class)
- Daily Supreme Tracker: `scripts/daily_supreme_tracker.py` (already spec'd `reports/expanded_enhancement_plan §6`)
- Monitor: extend `audit_dashboard/template.html` with drift-gate status + per-asset cost-model breakdown

#### Section 6 — 7-step diagnostic loop

Edge report → weakest asset → root cause (monkey test 1000 random) → hypothesize → paper-trade ≥50 picks or 2 weeks → measure vs control (PSR/DSR, PF>1.2 WR>50) → deploy or rollback.

#### Section 7 — First-week sprint (~30h)

- Day 1: hf_stats fresh + verify gate config (DONE today)
- Day 2: drift gate wiring + stale-payload unit test (DONE today)
- Day 3: crypto-short gate fix (DONE today)
- Day 4: Glassnode MVRV pilot → 7-day crypto backtest
- Day 5: COT lag patch PR #941 → re-run `cot_positioning` walk-forward
- Day 6-7: enable daily edge report + $500 shadow on COMMODITY `cot_positioning` + drift-gate Slack alert simulation

**Open questions Mercury 2 asked back:** (1) prioritize which hidden source first (COT/Glassnode/FRED/option-IV)? (2) push drift-gate PR now or wait for COT lag patch? (3) want detailed 7-day paper-trade plan for COMMODITY?

---

## 2026-05-14 — Kimi reconcile investigator finding (P0 #3 resolved as type-(a))

Subagent investigator returned. **VERDICT: (a) — blacklist is at-intake-only, not retroactive.**

**Evidence:**
- `alpha_engine/config.py:216` lists `kimi_signal_tracking` in `BLACKLISTED_STRATEGIES`.
- Enforcement sites: `alpha_engine/smart_picks_engine.py:770` (intake gate), `alpha_engine/copy_trader_bridge.py:204` (copy-trader emission), `alpha_engine/outcome_resolver.py:751-757` (marks new resolves `exit_reason=BLACKLISTED`).
- `universal_resolved_picks.json` has 1,183 `kimi_signal_tracking` picks. ZERO have `exit_reason=BLACKLISTED`. All sample picks are Feb-Apr 2026 (pre-blacklist).
- `dashboard_data.json::systems.kimi_signal_tracking` shows 16 resolved picks (PF 5.80 / WR 76.2%) + 1,167 excluded (`_is_valid_resolved_pick` filter). The 16 winners are all pre-blacklist legacy edge.
- `riseoftheclaw/data/signal_tracking.json` (last_updated 2026-05-14 04:51 — AFTER blacklist) has 12 NEW signals with `entry_time=2026-05-13`, but `exit_price=None` / `exit_reason=None` (unresolved). These do NOT appear in `picks.active` on dashboard (intake gate IS blocking new emissions from reaching active list).

**Implication:** the "PF 5.80" figure on dashboard isn't a contradiction — it's correctly reporting the 16 pre-blacklist realized winners. The misleading part is the **dashboard label** doesn't say "blacklisted, legacy stats only". Two fixes:

1. **Display fix (low):** add a `blacklisted: true` flag to `systems[]` entries that are in `BLACKLISTED_STRATEGIES`. Dashboard renders a "BLACKLISTED — legacy stats" badge. ~2h.
2. **Emission fix (medium):** `riseoftheclaw/data/signal_tracking.json` is still being written even though picks are blocked at intake. Either (a) stop the writer entirely OR (b) document that the file is a "rejected emissions log" — useful for audit but not a live picks source. ~2h to decide + label.

**Original SUPREME EDGE P0 #2 claim re-verified:** -954% PnL / PF 0.26 was the **pre-noise-filter cumulative** as of 2026-05-11. Post-resolver-v2 + noise-filter, the 16 surviving resolved picks happen to be the cleanest wins, hence PF 5.80. Not a contradiction — just the cleaned subset. P0 #3 closes as "verified-not-bug". No code fix required for correctness; only the display-label cosmetic.

## 2026-05-15 operator gap-to-hedge-fund prompt

Note: MySQL credentials in original prompt have been REDACTED for security. Per `feedback_security_db_creds_exposure_2026_05_12`, rotate immediately if exposed.

```
review our project
https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/
which feeds to 50webs findtorontoevents.ca/audit
and findtorontoevents.ca/audit/hyrotrader
which uses github actions and mysql database mysql.50webs.com ejaguiar1_stocks pw:[REDACTED — rotated]
ejaguiar1_backtests pw:[REDACTED — rotated]
use our github PAT (part of the .env) to create a set of PRs to enhance our project

Check files: reports/MASTER_ACTION_PLAN_2026-05-15.md, reports/master_plan_lineage_2026-05-15.md, reports/supreme_plan_review_2026-05-13.md, reports/supreme_edge_plan_next_2026-05-12.md

Look for what are the gaps between our project and a world-class hedge fund.
We have been stuck in a paper trading cycle for months and need to bridge the gap to finally get to a state where we can trust our data with real money for trading.

Our project tries to predict crypto/stocks(aka equity)/forex/bonds/etfs/commodities/futures + penny stocks/cheap stocks. Despite running this for months we don't seem ready to use real money.

We also considered "swarm picks" — bunch of free/paid AIs giving trade ideas + why + datasets used + what a quant/hedge fund would do to get us to world-class. We tried to integrate copy traders/prediction markets (kalshi/polymarket) and a bunch of github projects e.g. https://github.com/virattt/ai-hedge-fund. We have tools\swarm + ruflo swarm (2 types of AI agent swarm) for idea generation/research/testing plans/coding.

Give us a list of prioritized enhancements to bridge the gaps and take our project to world-class for each asset class.
- what will it take? More strategies? Better backtesting? More symbols? Deep dive into super-failing asset classes?
- Which asset class is almost ready for REAL MONEY? Possibly COMMODITY (cotton CT=F per session evidence — PF 10.94 / 87.2% WR on n=39 in recent_closed). If so, why? And what else?
- How can we find a reliable statistical edge?
```

## 2026-05-15 — MASTER_ACTION_PLAN gap-to-HF table + M-050..M-054 (selection capture, lines 578-613)

Captured from `reports/MASTER_ACTION_PLAN_2026-05-15.md` IDE selection so the gap matrix + 5 ranked enhancements + M-050..M-054 are searchable from daily_ideas without re-opening the master plan.

**STATUS: pending operator triage**

**Gap to world-class hedge fund — per asset class:**

| Class | Live PF | Gap to PF>2 | Action |
|---|---|---|---|
| COMMODITY | 2.08 (resolved-v2 n=816) | already there | **REAL MONEY CANDIDATE** — cotton (CT=F) sub-class PF 10.94 on n=39 confirmed; awaiting Stage F real-money pilot per 6-Level Gate-to-Money |
| EQUITY | 1.42 (T2 candidate, n=428) | needs +0.58 PF or n→1000 | factor sleeves + extended OOS |
| ETF | 1.20 (borderline, n=88) | needs n→200 + PF→1.5 | wait for accrual |
| CRYPTO | 1.26 (sub-T2, n=8162) | needs −20% volume share on `quan_engine` drag (PF 0.66, 21% vol) | quan_engine quarantine pending |
| BOND | 1.72 (meets T2 thresholds, n=18) | needs n→100 floor | thin data — keep accruing |
| FOREX | 0.27 (genuine sub-floor, n=1249) | requires mutation-before-kill cycle | deep-dive gate open |
| FUTURES | n=2 | needs accumulation 90d | Donchian breakout system |

**Note on live-data discrepancy:** operator's table (PF 2.08 / n=816) reflects earlier snapshot. Current `dashboard_data.json::performance.asset_class_health.COMMODITY` (pulled 2026-05-15) reads PF 2.49 / WR 61.5% / n=322 — stronger headline numbers, lower n. Either way COMMODITY clears Tier-2 PF>1.5 with margin and is the only class doing so reliably.

**5 prioritized enhancements to bridge to world-class:**

1. **Resolver gap close** (P0 long-pending) — 0/3,500 unresolved was #1 blocker. Live `picks.recent_closed` now shows 3,500 resolved per `dashboard_data.json` so this MAY already be resolved post-`outcome_resolver.py:115-126 PNL_WIN_THRESHOLD_BY_CLASS` fix (2026-04-28). Verify before new architecture work.
2. **Cotton-style proof per asset class** — Tier-2 candidacy requires evidence pack: (a) walkforward decay≥0 across 3+ folds, (b) PSR>0.95, (c) DSR>0.95, (d) live 30 picks at projected PF on live tape. COMMODITY/CT=F has DSR=1.0000 + PF 10.94 already; needs (d).
3. **Swarm pick provenance** — current `swarm_picks_data.picks` (38 entries) is single-model (claude-opus-4-7) with persona prompts, NOT multi-model. Route personas to genuinely different underlying models (Sonnet, Haiku, Grok, DeepSeek) for real ensemble diversity.
4. **Statistical-edge finder** — implement Lopez de Prado PBO/CPCV harness (not just per-strategy backtest) so edges surviving structural overfitting surface. Memory `project_cpcv_gap_2026_04_28` already flags missing.
5. **Cross-AI stat validation** — 4 different AIs run perf numbers from `audit_dashboard/data/dashboard_data.json` and report WR/PF. Convergence = trust climbs. Divergence = surface it.

### 20.1 — Master plan additions (M-050 thru M-054)

| ID | Idea | Asset class | Owner | First action |
|---|---|---|---|---|
| M-050 | Cotton (CT=F) live-pilot — 30 picks @ projected PF on live tape | COMMODITY | operator | Charter Stage F entry; daily reconciliation |
| M-051 | Multi-model swarm ensemble (Sonnet/Haiku/Grok/DeepSeek/Claude) for real diversity | all | claude-desktop | swap one persona to Sonnet, measure WR delta |
| M-052 | PBO/CPCV harness per Lopez de Prado | all | (unassigned) | spike against COMMODITY first |
| M-053 | 4-AI stat-validation cross-check | all | claude-desktop | 4 engines compute PF/WR from dashboard_data.json, surface divergence |
| M-054 | ai-hedge-fund (virattt/ai-hedge-fund) integration spike | crypto/equity | (unassigned) | read repo, propose adapter |

## 2026-05-15 — User prompt: "how would a quant baseline performance + hunt gaps cheaply?"

Operator framing: Quant trying to save company with gigantic codebase predicting stocks/crypto/forex/bonds/commodities/futures/ETFs + penny stocks + meme coins. Wants baseline-then-gap-hunt playbook using mostly free data + existing AI API budget (no expensive paid feeds).

Specific sub-questions raised:
- Asset class with too few symbols in universe?
- Backtests great but forward bad? (overfit signature)
- Failing strategies — delete? invert? re-sim with different entry criteria?
- Industry-standard / proven-pattern research?
- Scrape social for great strategies?
- Pick AI brains for per-class concepts: what free data, what stats/math, what backtest type? e.g. stocks → earnings perf correlation, financial statements, SEC filings?

### Answer captured (caveman-compressed, full technical substance)

**Phase 0 — Baseline (free, do first):**
- Single source of truth = `audit_dashboard/data/dashboard_data.json::performance.asset_class_health` (resolver-v2 trustworthy post 2026-04-28 fix).
- Per class compute: n, WR, PF, Sharpe, Sortino, MDD, expectancy, avg hold, payoff ratio, BT-vs-FW WR delta (the overfit detector).
- Per strategy×class: same matrix + survivorship (did it stop emitting?) + Darwin score v2.
- Per symbol×class: same + concentration (top-5 symbols % of volume — quan_engine MATIC ghost was 755/1001 = 75%, that's the smell).
- Universe-size table: symbols emitted vs symbols in feed (small universe = no edge room).

**Phase 1 — Gap taxonomy (5 buckets, each with a fix path):**

| Gap | Detector | Fix path |
|---|---|---|
| Thin universe | `symbols_emitted / symbols_available < 0.2` | Expand scraper coverage; check `*_scraper.py` modules |
| BT/FW divergence | `BT_WR − FW_WR > 15pp` | PBO/CPCV (M-052), Deflated Sharpe; suspect overfitting |
| Concentration ghost | top-5 symbols >50% volume | Quarantine (quan_engine MATIC, clone_hl_copy placeholder) |
| Resolver/data bug | impossible numbers (100/100/100, -0.27 PF) | Audit resolver before killing |
| Genuine sub-floor | clean n>500, PF<1 | Mutate-before-kill (`docs/MUTATION_THREE_AXIS_PROTOCOL.md`) — try inverse, symbol rotation, time-of-day filter; only kill if all 3 axes fail |

**Phase 2 — Industry-standard playbook per class (free-data first):**

| Class | Free data | Math | Proven backtest pattern |
|---|---|---|---|
| EQUITY | yfinance OHLCV, SEC EDGAR (10-K/10-Q/8-K free API), FRED macro, Finnhub free tier earnings calendar, Reddit/StockTwits | PEAD (post-earnings drift), Fama-French 3/5-factor regression, accruals (Sloan), short-interest, insider Form 4 | Walkforward 252d train / 63d test; PEAD = 60-day drift post-surprise |
| CRYPTO | Binance/CoinGecko/Kucoin OHLCV (failover chain), Hyperliquid funding, on-chain via Dune free tier, LunarCrush social | Funding-rate carry, perp-spot basis, MVRV, NVT, social momentum (LunarCrush already wired) | Triple-barrier (López de Prado); regime-switching HMM (already have 7-state) |
| FOREX | OANDA practice feed (free), FRED rate differentials, MyFXBook public copy-trader leaderboard scrape | Carry-trade rate-diff, Dollar smile, COT positioning (CFTC free CSV) | Walk-forward + carry overlay; mean-reversion only in ranging regime |
| BOND | FRED yield curve, TreasuryDirect, ETF proxies (TLT/IEF/SHY) | Slope (2s10s), curvature, real yield, breakeven inflation | Macro-regime gated; trend in TLT |
| COMMODITY | yfinance futures continuous, CFTC COT free, USDA WASDE reports free | Backwardation/contango, COT extremes, seasonality | Donchian breakout (50/100d) — Turtle Traders proven; KMLM/DBMF replication |
| ETF | yfinance + ETF.com flows (scrape) | Sector rotation, factor tilts | Cross-sectional momentum (12-1 month) |
| FUTURES | Same as commodity + index futures via CME free EOD | Trend-following CTA replication (DBMF/KMLM ~$2B AUM each) | 12-month time-series momentum (Hurst exponent confirmation) |
| PENNY/MEME | Reddit (free API), Twitter scrape, Pump.fun on-chain | Volume spike Z-score, social mention rate-of-change, holder concentration | Event-driven only; tight stops; treat as lottery sleeve <2% portfolio |

**Phase 3 — Failing-strategy decision tree (instead of "delete?"):**
```
fail_strategy:
  if n < 30: hold, accrue more
  elif BT/FW gap > 15pp: PBO/CPCV → if PBO>0.5, kill (overfit)
  elif concentration top1 >40%: quarantine that symbol, re-eval residual
  elif PF < 0.7 and n>200:
    try axis-1 (inverse) → if PF>1.3, ship inverted
    try axis-2 (symbol rotation) → drop bottom-quartile symbols
    try axis-3 (regime gate) → only fire in matching HMM state
    if all fail: kill with autopsy doc in reports/deep_dive_<class>_<date>.md
  else: keep, monitor
```

**Phase 4 — Cheap edge-hunting using AI keys we already have:**
- Use existing swarm (`tools/swarm` + `tools/swarm-ruflo`) to fan questions to Cerebras/Ollama-cloud/DeepSeek/Grok/Kimi for FREE.
- Per-class prompt template:
  - "Given asset class X, free data sources Y, give 5 statistical signals with academic citation + expected Sharpe + implementation skeleton in Python."
  - Cross-validate: 4+ models propose same signal = high-confidence candidate.
  - Then backtest the convergent signal on our universe with vectorbt/bt (already wired per `project_next_phase_integrations_2026_04_22`).
- Scrape MyFXBook/eToro public leaderboards (free) for top forex copy traders → reverse-engineer their entry signals via correlation analysis on their trade timestamps vs our feature library.

**Phase 5 — How pros do it (cheap version):**
- AQR/Renaissance: factor zoo + ensemble. Cheap version: implement Fama-French 5 + momentum + quality on EQUITY (free via yfinance + EDGAR).
- Two Sigma: alternative data. Cheap version: Reddit/Twitter sentiment (free), Google Trends (free), GitHub commits for crypto projects (free), satellite imagery via Planet Labs free tier.
- Bridgewater: macro regime. Cheap version: FRED-based 4-quadrant regime detector (growth↑↓ × inflation↑↓) — gates all strategies.
- Citadel: execution edge. Not replicable cheaply; skip until real-money phase.
- DE Shaw: stat-arb. Cheap version: cointegration pairs (statsmodels free) on EQUITY/ETF — `cointegration_finder.py` spike.

**Phase 6 — Operator first 5 actions (ranked by ROI):**
1. **PBO/CPCV harness (M-052)** — single biggest credibility lift; surfaces overfit vs real edge. Spike on COMMODITY first.
2. **Per-class universe-size audit** — one-shot script, output table of symbols_emitted/symbols_available per class. If FOREX has 7 pairs and CRYPTO has 200, that alone explains FOREX sub-floor.
3. **BT/FW divergence dashboard tile** — surface the overfit detector on /audit.
4. **Multi-model swarm fan-out (M-051)** — query 6 AI engines with the per-class prompt template above; converge signals.
5. **CFTC COT + FRED ingestor** — 2 free data sources unlock COMMODITY/FOREX/BOND macro overlay. Highest free-data ROI.

**Anti-patterns to avoid (already burned us this session):**
- Don't kill on raw `by_asset_class` aggregates — use `asset_class_health` (resolver-v2).
- Don't trust headline WR until ghost-symbol cleanup (MATIC 660-row artifact, quan_engine 755-row twin).
- Don't trust paper account names as gates (`feedback_gate_at_execution_not_generation`).
- Don't paste DB creds / PATs in chat (memory `security_pat_exposure_2026_05_15`).

## 2026-05-15 — Grok senior-quant brutal assessment of MASTER_ACTION_PLAN

Operator pulled in Grok as outside-quant second opinion. Grok reviewed branch `docs/master-action-plan-2026-05-15` (commit 533ff90c8de…), live MASTER_ACTION_PLAN_2026-05-15.md (65k lines, M-001..M-027+), open PRs post-triage, MySQL forensics on `ejaguiar1_stocks`/`ejaguiar1_backtests`, dashboard_data.json.

### Verdict: "No — current plan won't reach world-class in present form"

Reasons:
- Laundry list of ideas (M-001..M-027+) not a dependency-managed execution roadmap with kill criteria.
- Underestimates foundational rot in data quality + outcome tracking.
- Spreads effort across asset classes instead of concentrating where edge plausibly exists (COMMODITY/cotton).
- Good instincts (DB freshness, drift CB, sizing, DSR, COT lag correction) but lacks ruthless prioritization.

Good news: recent triage (Claude+Copilot merges) cut main from 36 fail → 4 fail / 122 pass. Necessary hygiene done; now needs strategy.

### Grok's baseline reality table (live dashboard_data.json + DB forensics)

| Class | PF / WR / n | Verdict | Biggest problem |
|---|---|---|---|
| COMMODITY | 2.49 / 61.5% / 322 | Best candidate | Tiny active universe (mostly CT=F + HG=F) |
| EQUITY | 1.57 / 51.9% / 420 | Marginal T2 | No earnings/SEC integration |
| ETF | 1.48 / 58.5% / 106 | Borderline | Very small n |
| CRYPTO | 1.36 / 46.7% / 8011 | Sub-T2 drag | Low-quality symbols + quan_engine/unknown drag |
| FOREX | 0.81 / 52.3% / 342 | Recovering, weak | Historically terrible |
| BOND | 0.66 / 54.5% / 11 | Stat-meaningless | n=11 (TLT/HYG concentration) |
| FUTURES | Dead | — | Almost nothing |

### DB reality (CRITICAL — biggest finding)

- `at_raw_picks`: 145k+ signals, but **only 0.08% have outcomes** in `at_signal_outcomes`.
- `paper_trades` table: **completely empty**.
- `paper_portfolio_daily` table: **completely empty**.
- Hundreds of thousands of ghost rows.
- **No reliable "what happened after we published this pick" loop for most history.**

⇒ This is THE single biggest reason world-class (or even reliable T2) cannot be claimed yet. No trustworthy forward test.

### 6 gaps vs world-class operation
1. **Symbol universe & liquidity coverage** — unknown per class. Probably too many garbage meme/penny names, too few liquid contracts in commodities/futures.
2. **Outcome tracking** — catastrophic (per above). Without resolved outcomes + paper P&L, DSR/walk-forward/pruning are theater.
3. **Forward validation discipline** — weak. Lots of backtests, little rolling OOS + live decay measurement.
4. **Strategy lifecycle management** — no systematic delete/invert/re-param/quarantine process. Failures linger.
5. **Execution realism** — slippage, sizing, concentration, drift CB still scaffolding (Kimi WORLD_CLASS_ENHANCEMENT_PLAN + Phase J safety modules trying to fix).
6. **Data enrichment per class** — ~zero fundamental/macro/sentiment for equity+bond. Crypto has on-chain but not systematically used.

### Grok's prioritized 90-day plan

**Phase 0 (next 3–4 weeks) — stop the bleeding:**
- Finish DB Freshness Guardian; make GHA actually fail run on RED (most code exists).
- Force outcome tracking to work: resolver populates `at_signal_outcomes` reliably; paper trading writes to `paper_trades` + `paper_portfolio_daily`.
- Symbol universe audit script per asset class (coverage% + liquidity filter via free sources).

**Phase 1 (next 6–8 weeks) — pick ONE horse:**
- COMMODITY cotton (CT=F) is the only rational pilot. Kimi + Grok converged on same conclusion.
- Everything else (most M-00x for equity/bond/ETF/etc.) deprioritize or strict opt-in sidecar until cotton is production-grade with real paper-trading track record.

**Phase 2 — systematic pruning + inversion framework:**
For any strategy live >60–90 days:
- If OOS/live Sharpe < 0.3–0.4 AND stat-significant → delete or hard quarantine.
- If strong negative correlation with main signal → consider inverted version (under-used in our system).
- Otherwise → tighten entry filters or add cost model BEFORE touching parameters.

### Leveraging AI API keys (the smart way)

Use as research accelerator, never as oracle.

**Good prompt patterns:**
- "For [asset class], list 8–10 high-signal, low-cost features that appear in peer-reviewed papers 2018–2025, with the free data source for each."
- "Summarize core logic, entry/exit rules, common failure modes of classic [carry / momentum / mean-reversion] strategy in [FX / commodities / equities], including realistic transaction cost assumptions."
- "What free or cheap data series should I pull to test whether earnings surprise + post-earnings drift still works in current regime for mid-cap US stocks?"

**Bad use:** asking LLM to write production position sizers or risk models without heavy verification.

### Free/low-cost data sources per class (Grok's realistic list)

- **Equity/Penny/Meme:** yfinance (prices+some fundamentals), SEC EDGAR (10-K/Q via `sec-edgar-downloader`), FRED (macro), Google Trends (sentiment proxy).
- **Crypto:** CoinGecko (excellent free tier), on-chain via public explorers or free Dune queries.
- **Forex:** ECB daily rates, FRED, OANDA free tier.
- **Commodity/Futures:** CME delayed EOD, Quandl free EIA energy series, USGS metals.
- **Bond:** FRED Treasury + corporate filings via EDGAR.
- **Sentiment:** Responsible Reddit scrape (PRAW with rate limits) + Twitter/X API + LunarCrush free crypto.

### Final recommendation (Grok)

> Stop treating MASTER_ACTION_PLAN_2026-05-15.md as sacred. Treat it as brain dump of ideas.

90-day winning strategy:
1. Make data trustworthy (Freshness Guardian + outcome tracking).
2. Pick one asset class (cotton) and make it genuinely production-grade with proper sizing/costs/kills/paper-trading.
3. Build simple but ruthless pruning + inversion framework.
4. ONLY THEN expand universe + add cleverer ideas (PEAD, sector momentum, TSMOM, etc.).

### Grok's offer (operator deferred routing decision)

Two paths offered:
- (A) Write tight 90-day execution plan as new .md replacing sprawling master plan (data ingestion priorities per class free-only, minimal M-IDs that matter now, delete/invert decision framework, AI prompt templates per class).
- (B) Start with deep audit of ONE asset class (e.g. COMMODITY symbol coverage + data flow) first.

Operator routing: pending.

### Convergent findings — Grok ∩ this session ∩ Kimi ∩ Mercury

| Finding | Grok | Mercury 6-phase | Kimi WORLD_CLASS | this session daily_ideas |
|---|---|---|---|---|
| Outcome tracking catastrophic | ✓ DB forensic 0.08% | ✓ Phase 0 | ✓ resolver gap | ✓ resolver-v2 verify (#1 enh) |
| COMMODITY/cotton is the pilot | ✓ | ✓ | ✓ | ✓ (M-050) |
| Stop spreading effort | ✓ | ✓ | ✓ | (implicit) |
| PBO/CPCV missing | (implied: forward validation gap) | ✓ | ✓ | ✓ (M-052) |
| Free data per class | ✓ explicit list | ✓ | ✓ | ✓ Phase 2 table |
| Mutate-before-kill / inversion | ✓ | partial | ✓ | ✓ Phase 3 tree |
| Symbol universe audit | ✓ | ✓ | ✓ | ✓ #2 enhancement |

5 independent senior-quant analyses (Grok / Mercury / Kimi / Inception / ChatGPT) all converge on **same 4-step plan**. Convergence ≥ trust. **Path forward unambiguous** — execute, don't re-deliberate.

## 2026-05-15 — 3-investigator verification of Grok claims (subagent fan-out)

User said "use subagents and see if you can assist on research/analysis/enhancements". Dispatched 3 parallel `caveman:cavecrew-investigator` agents (read-only, caveman-compressed output) to verify Grok's biggest claims against local repo state.

### Investigator 1 — Outcome tracking rot claim: **PARTIALLY WRONG**

Grok conflated two different systems:

| System | Status | Source |
|---|---|---|
| Local resolver `alpha_engine/outcome_resolver.py` | **WORKS** — hourly cron via `.github/workflows/outcome-resolver.yml:6`; writes `alpha_engine/data/closed_picks.json`; `dashboard_data.json::recent_closed` = 3,500 resolved; only 66/3500 (1.9%) have null PnL | repo evidence |
| 50webs MySQL DB (`at_signal_outcomes`) | **GHOST-INFESTED** — 121 outcomes / 145,879 raw picks = 0.08% as Grok cited; DB is stale, manual sync only | Grok's DB query |
| `paper_trades` + `paper_portfolio_daily` tables | **EMPTY BY DESIGN** — generator at `alpha_engine/copytrader_integration.py:82` has NO active caller; suspended pending Phase J safety infra (PRs #1026/#1052) | `claude_chat_audit_review_2026-05-15.md:38` + `paper_trading/mysql_sync.py:60` |

**Verdict:** Resolver works. DB ghost-infestation is a separate cleanup task, NOT a "no outcome tracking" emergency. Paper-trading emptiness is deliberate (Phase J gate). Grok was reading dead DB rows, not live local state.

**Action implication:** Don't redo resolver. DO: (a) clear 655k ghost rows from MySQL, (b) wire paper_trades generator post-Phase-J.

### Investigator 2 — Symbol universe audit: REAL THIN CLASSES DIFFER FROM GROK'S CLAIM

| Class | Emitting / Config | Top-1 | Flag |
|---|---|---|---|
| CRYPTO | 179 / 109 (+64% from copy-trader CEX integrations) | BTCUSDT 15.9% | OK |
| EQUITY | 47 / 50 (94%) | AMD 11.2% | OK |
| ETF | 11 / 11 (100%) | QQQ 18.7% | OK |
| FOREX | 22 / 20 (110%) | EURUSD 9.9% | **OK — NOT thin** |
| COMMODITY | 9 / 25 (36%) | CT=F **55%** | **GHOST + scanner underutilization** |
| BOND | **2 / 14 (14%)** | TLT **75%** | **GHOST + scanner barely firing** |
| FUTURES | **0 / 14 (0%)** | — | **DEAD — `production_scanner.py::passes_active_gate` not routing** |

Sources: `audit_dashboard/data/dashboard_data.json` (picks.recent_closed n=3500, picks.active n=29); `alpha_engine/config.py:92-131` (SECTOR_MAP), `:536-580` (FOREX 20 pairs), `:615-646` (COMMODITY 25), `:781-798` (BOND 14).

**Verdict reversal:** FOREX is NOT thin. **BOND is the thinnest (14% utilization, TLT 75% concentration).** COMMODITY is next (36%, CT=F 55%). FUTURES is dead at the scanner level. Investigator 2's verdict overrides Grok's "FOREX historically terrible" framing — FOREX has plenty of universe, the strategies are the problem.

**Action implication:**
- BOND: expand `bond_scanner.py` to emit from full 14-symbol roster (currently TLT/HYG only).
- COMMODITY: scanner not exercising 16/25 contracts; verify COT sensitivity gate isn't filtering too hard.
- FUTURES: check `production_scanner.py::passes_active_gate` FUTURES branch — 14 symbols configured, 0 emitting.

### Investigator 3 — CT=F (cotton) Stage F readiness: **REBUTTED**

Memory claim: PF 10.94 / WR 87.2% / n=39 / DSR=1.0000 → "real-money candidate".

Actual `recent_closed` filter on CT=F:
- **n=48** (41 WON + 7 LOST), **WR=85.4%** (close to memory but not 87.2%)
- **PnL field bug:** `realized_pnl_pct` ALWAYS NULL; dashboard reads `pnl_pct` instead. PF 10.94 cannot be verified from this data without the schema fix.
- **CT=F has ZERO active picks** — emitter dormant since ~2026-05-12. Recent COT-lag-corrector patches (`tools/cot_lag_corrector.py` + dedup guard) may have halted emission.
- Sources: `multi_asset_copytrader` + `multi_asset_cot` (two source systems, not one).

**Other COMMODITY symbols (cotton sole winner):**

| Symbol | n | WR |
|---|---|---|
| CT=F (cotton) | 41W/7L | **82.9%** |
| ZW=F (wheat) | 10 | 0% |
| ZS=F (soy) | 8 | 0% |
| CL=F (crude) | 4 | 0% |
| GC=F (gold) | 3 | 0% |
| SI=F (silver) | 3 | 0% |
| HG=F, KC=F | 2 each | 0% |
| NG=F | 1 | 0% |

⇒ **CT=F is the sole COMMODITY winner; everything else wipes out.** The 2.49 PF / 61.5% WR aggregate is entirely a cotton-survivorship artifact.

**Charter §2 Tier-2 floor:** PF≥1.5 / WR≥50% / **MDD≤20% / n≥100**. CT=F has **n=48 (below n≥100 floor)**. Cannot enter Stage F real-money pilot yet.

**3 blockers to Stage F:**
1. **n<100** — need 52 more closed CT=F trades to clear floor.
2. **Signal stopped** — zero active picks; emitter dormant since 2026-05-12. Investigate cot_lag_corrector dedup guard.
3. **PnL schema mismatch** — `realized_pnl_pct` always NULL; PF/Sharpe/DSR cannot be trusted until schema fixed.

### Consolidated 5-action shortlist (post-investigation)

Ranked by ROI given verified evidence:

1. **Unblock CT=F emitter** — investigate why `multi_asset_cot` + `multi_asset_copytrader` stopped emitting cotton since 2026-05-12. Likely culprit: `tools/cot_lag_corrector.py` dedup guard. Without this, cannot accrue n→100 for Stage F.
2. **Fix `realized_pnl_pct` schema bug** — without this, no class can claim PF/Sharpe/DSR rigorously. Highest-leverage data-integrity fix.
3. **Wire FUTURES branch in `production_scanner.py::passes_active_gate`** — 14 configured symbols, 0 emitting. Free coverage expansion.
4. **Expand `bond_scanner.py` beyond TLT/HYG** — 12 configured BOND symbols never tested. Could unlock real BOND signal or kill class definitively.
5. **MySQL ghost-row purge** — separate from local resolver fix; clean 655k stale rows from `at_raw_picks` so future DB-based audits are meaningful.

Note: items 1+2 are **strict prerequisites** before any "real money" decision. Items 3+4 are universe-expansion safety nets. Item 5 is hygiene.

## 2026-05-15 — CRITICAL REVERSAL: top 2 actions invalidated by 2nd-round investigation

User authorized autonomous execution. Dispatched 2 more `caveman:cavecrew-investigator` agents to find exact fix points for actions #1 (CT=F emitter unblock) and #2 (realized_pnl_pct schema fix). Both came back with reversals.

### Reversal 1 — CT=F is NOT dormant due to cot_lag_corrector. It is **deliberately blacklisted.**

| File | Line | Finding |
|---|---|---|
| `audit_trail/quality_gates.py` | 1266-1273 | `COMMODITY_BLACKLIST` set contains **CT=F** explicitly |
| `audit_trail/quality_gates.py` | 1262 | Justification: "CT=F (cotton) n=12 WR 8.3% sum -8.41% KILL" (2026-04-29) |
| `audit_trail/quality_gates.py` | 5072-5081 | `passes_active_gate()` hard-rejects if `symbol.upper() in COMMODITY_BLACKLIST` unless env `COMMODITY_SUBCLASS_KILL_DISABLED=1` |

**Phase 2-D panel verdict (2026-04-29) killed CT=F because rolling-window WR dropped to 8.3% on n=12.** The 82.9% WR / n=48 Investigator-3 saw in `recent_closed` is the **pre-kill historical window** — those picks resolved into `recent_closed` but the gate prevents NEW CT=F emission.

⇒ Memory + `reports/MASTER_ACTION_PLAN_2026-05-15.md` M-050 + this session's earlier daily_ideas + the Grok/Kimi/Mercury convergence claims that "CT=F is the real-money candidate" are **all reading the historical pre-kill window**. The operator's own kill protocol already disqualified cotton.

**Three possible interpretations:**
1. **Phase 2-D kill was too aggressive** (n=12 below a sane kill-floor; should have waited for n≥50). Under this read, cotton should be revived.
2. **The 82.9% WR is regime-window survivorship** (hot streak then mean-reversion; kill caught the reversion). Under this read, revival loses money.
3. **Two sub-strategies inside the CT=F bucket** — n=12/WR 8.3% rolling vs n=48/WR 82.9% lifetime cannot both be true unless the kill missed a sub-pattern.

**High-leverage data-interpretation problem, not a code bug.** Cannot be "fixed" by code; requires CT=F pick histogram by date + rolling-50 WR overlay + source-system split + Phase 2-D verdict re-replay.

**Risk of naive revival:** flipping `COMMODITY_SUBCLASS_KILL_DISABLED=1` without re-running the analysis means trusting a number (82.9%) the operator's own protocol already labeled false.

### Reversal 2 — `realized_pnl_pct` is **dead-code fallback chain**, not a silent-wrong-answer bug

| File | Line | Op | Field |
|---|---|---|---|
| `alpha_engine/outcome_resolver.py` | 964 | write | `pnl_pct` only (NO `realized_pnl_pct`) |
| `alpha_engine/forward_validator.py` | 787, 1295 | write | `pnl_pct` only |
| `audit_dashboard/template.html` | 15158, 16401, 16410, 16481 | read | `realized_pnl_pct \|\| pnl_pct \|\| 0` (fallback) |
| `audit_trail/dashboard_generator.py` | 6998 | read | `realized_pnl_pct` (in fallback chain) |

**Field is never populated. All reads fall back to `pnl_pct`. PF/WR/DSR are NOT wrong — they read the right field via fallback.** Investigator-3's "PF 10.94 cannot be verified" was wrong; PF is computable from `pnl_pct`, which IS populated. Action: simplify the dead-code fallback chain. Low priority, no data-integrity issue.

### Revised 5-action shortlist (post-reversal)

Old action 1 (CT=F unblock) → **paused pending sub-strategy autopsy of the n=48 vs n=12 paradox**.
Old action 2 (schema fix) → **demoted to low-priority cleanup**.

New ranked actions:

1. **CT=F kill-vs-revive autopsy** — produce `reports/deep_dive_cotton_2026-05-15.md`: per-source split (`multi_asset_copytrader` vs `multi_asset_cot`), rolling-50 WR timeline, regime decomposition (HMM state per pick), Phase 2-D kill-window re-replay. If kill correct → kill stays; if Phase 2-D used too-small n → revive with stricter MATCH gate (PR #1058). Do NOT manually flip the env var without the autopsy.
2. **Wire FUTURES branch in `production_scanner.py::passes_active_gate`** — 14 configured symbols, 0 emitting. Verify it's not symmetric-blacklist style like COMMODITY_BLACKLIST.
3. **Expand `bond_scanner.py` beyond TLT/HYG** — 12 of 14 BOND symbols never tested (TLT 75% concentration).
4. **Audit other COMMODITY blacklist entries** — Phase 2-D killed 7/7 sub-class symbols. If cotton kill was wrong, others may be too.
5. **Re-think "5-AI convergence = trust"** — Grok/Mercury/Kimi/Inception/ChatGPT all agreed cotton was the real-money pilot. They all read stale memory. Convergence at the input-data layer ≠ convergence at truth.

### Meta-lesson

This session demonstrates the most dangerous failure mode of multi-AI consensus: **5 senior-quant analyses converged on the wrong conclusion (cotton = real-money) because they all read the same stale memory entries.** Convergence at the data-input layer creates the illusion of independent verification.

**Tighter protocol going forward:**
- Before claiming any asset class real-money ready, grep `audit_trail/quality_gates.py::*_BLACKLIST` for the symbol.
- Before trusting an AI's "convergent" finding, ask: did all AIs read the same input file? If yes, that's correlated noise, not independent signal.
- M-053 (4-AI stat-validation cross-check) must **rotate the input file** per engine to avoid this trap.

## 2026-05-15 — REVERSAL 3: FUTURES is also a deliberate kill, not unwired. Only BOND survives.

Verified actions #2 (FUTURES gate) and #3 (BOND scanner) directly via grep of `audit_trail/quality_gates.py`:

### FUTURES — 0/14 emitting is DELIBERATE (drain kill)

| Line | Entry | Meaning |
|---|---|---|
| `quality_gates.py:1317` | `BLOCKED_ASSET_CLASSES = set()` | class-level block removed 2026-04-16 (caused data starvation) |
| `quality_gates.py:1611-1617` | 7 `(strategy, "FUTURES")` pairs blocked | connors_rsi2, hyperopt_connors_rsi2, mean_reversion_bollinger, extreme_oversold_bounce, vix_reversal, futures_mean_reversion, ema_stack_momentum — all 0% WR |
| `quality_gates.py:1916` | `("FUTURES", "futures_momentum")` | 7d WR 4% vs 42% baseline |
| `quality_gates.py:2006-2013` | `("FUTURES", "multi_asset_copytrader")` | "n=157, WR=2.5% → critical drain, surgical block" |

⇒ FUTURES isn't unwired by accident — **every emitter (strategy + source) is individually blocked because the class genuinely drained at 2.5% WR.** Matches memory `project_futures_kill_without_replacement`. Action #2 ("wire FUTURES gate") is **invalid** — the gate works fine, FUTURES needs **NEW strategies**, not gate-wiring. Rollback note already at `:2010-2013`: run `tools/mutation_analysis.py` first if FUTURES is rebuilt.

### BOND — 2/14 emitting IS a genuine scanner-coverage gap (action #3 SURVIVES)

| Line | Entry | Meaning |
|---|---|---|
| `quality_gates.py:1987` | `("BOND", "alpha_engine_fast")` | only ONE strategy-pair blocked |
| — | no `BOND` in `BLOCKED_ASSET_CLASSES` | class is alive |
| `quality_gates.py:5218` | `_is_bond_etf_exempt` | BOND/ETF given thin-sample exemption (Phase 3, PF 1.72/WR 50%) |

⇒ BOND class is alive and even exempted for being thin. Only `alpha_engine_fast` is blocked for BOND. So **only TLT/HYG emitting (2/14) is a real scanner gap, not a kill.** Action #3 (expand `bond_scanner.py` to the full 14-symbol roster) is the **one genuinely actionable code item** from the original shortlist.

**Caveat before editing bond_scanner:** adding 12 untested BOND symbols floods the system with picks that have n=0 history. The Tier-2 n≥100 floor means they won't size up, but they WILL consume scan budget. Expansion should be **staged** — add 3-4 symbols, accrue n≥50, then add the rest. Not a one-shot 14-symbol dump.

### Final session tally — 3 reversals, 1 survivor

| Original action | Verdict | Why |
|---|---|---|
| 1. CT=F emitter unblock | ❌ REVERSED | deliberately blacklisted (Phase 2-D, WR 8.3%/n=12) |
| 2. realized_pnl_pct schema fix | ❌ DEMOTED | dead-code fallback chain, no data bug |
| 2b. FUTURES gate wiring | ❌ REVERSED | every emitter deliberately blocked (2.5% WR drain) |
| 3. bond_scanner expansion | ✅ SURVIVES | genuine scanner gap; class alive + exempted |
| 4. COMMODITY blacklist audit | ✅ VALID | Phase 2-D killed 7/7 — if cotton kill wrong, others may be |
| 5. MySQL ghost purge | ✅ VALID | hygiene, separate from local resolver |

**The deepest meta-finding of the session:** the "thin/dead asset class" framing — repeated by Grok, the master plan, and this session's own first-pass analysis — is **mostly wrong**. CRYPTO/EQUITY/ETF/FOREX have healthy universes. COMMODITY and FUTURES are *deliberately* shrunk by kill protocols that already ran. The system is not leaking from un-wired gates; it is doing exactly what its kill protocols told it to do. **The real gap is kill-WITHOUT-replacement** — when a class drains, the protocol kills the bad strategies but no process generates new ones. That is the M-052 (PBO/CPCV harness) + strategy-generation gap, not a wiring bug.

**Single highest-leverage next action:** build a **strategy-replacement pipeline** that triggers when a class/strategy gets killed — auto-spawn a deep-dive subagent that proposes 3 replacement strategies (from the free-data + academic-signal library in the Phase-2 table above), backtests them, and queues survivors. Without this, every kill permanently shrinks the tradeable universe and the system slowly starves. This is why the project has been "stuck in paper trading for months": kills outpace births.

## 2026-05-15 — Swarm second-opinion sharpens the root-cause diagnosis

Ran `/swarm-second-opinion` (consensus-3 preset: deepseek, xai, kilo) on the kill-without-replacement hypothesis. Run dir: `swarm_runs/second-opinion-20260515T080442Z`. xai returned malformed JSON (transport 400) → 2/3 valid. **DeepSeek + Kilo both HIGH confidence, both agree.**

### CONSENSUS (2/2 valid engines)

- Kill-without-replacement diagnosis is **directionally correct but incomplete — it is the proximal cause, not the root.**
- The proposed auto-spawn pipeline is a **patch, NOT the highest-leverage move.** Both engines independently said: without fixing the deeper issue first, replacement strategies get killed as fast as they spawn — Kilo's phrase: *"a faster-running conveyor belt to the kill floor."*
- The **deeper root cause** is two-fold:
  1. **Kill thresholds are mis-calibrated** — they fire on small-n rolling windows (FUTURES n=157, cotton n=12) with no statistical test. A 2.5% WR on n=157 could be noise around a true 40% WR with high variance (DeepSeek). Kill logic uses fixed WR/PF/decay cutoffs without sample-size or variance adjustment.
  2. **Forward-validation is not wired into kill decisions.** `walk_forward_validator.py` exists and emits ROBUST/MODERATE/FRAGILE verdicts, but its output does NOT feed kill-threshold calibration. Kill thresholds are calibrated on **in-sample closed picks that include the very strategies about to be killed** — circular.

### Kilo's codebase evidence (raised confidence)

- `commodity_kill_switch.py` + `fx_kill_switch.py` run post-ingest hard-blocks (PF<0.9 @ n≥20, 0% WR @ n≥15, decay>15pp).
- `strategy_killer.py` runs separate multi-source kill classification.
- `PERMANENTLY_KILLED_STRATEGIES` in `quality_gates.py` = **65+ entries, growing**, many zero-WR at large n.
- Score floors in `quality_gates.py:314-370` have been **raised, lowered, re-raised multiple times in weeks** → "no stable calibration anchor."
- `score_booster` enrichment is **crypto-gated** (`quality_gates.py:346-350`) → COMMODITY/FUTURES/EQUITY strategies operate at a systematic scoring disadvantage. COMMODITY actionable range 30-55 vs floor 60 = ~0 picks pass — a structural bias, not a strategy-quality problem.

### REVISED highest-leverage action order (swarm-corrected)

The auto-spawn pipeline drops from **step 1 → step 4**. Correct order:

1. **Re-calibrate kill thresholds on walk-forward data.** Use `walk_forward_validator.py` ROBUST/MODERATE verdicts as the kill gate — NOT raw rolling WR/PF/decay. Require minimum n (DeepSeek: n>100; Kilo: n≥30) + a statistical test (binomial / Bayesian posterior) before any kill. Stops premature death of high-variance strategies.
2. **Build an incubator pipeline.** New COMMODITY/FUTURES candidates start at **zero kill pressure**, must accrue 30+ forward-test trades in the target class, THEN graduate to live scoring. No incubator exists today — this is why every kill is permanent.
3. **Decouple `score_booster` from crypto-only gating** so COMMODITY/FUTURES/EQUITY get equivalent enrichment. The crypto-only clamp artificially widens the cross-class quality gap.
4. **THEN add the auto-spawn pipeline** — gated by per-class minimum-viable-sample so spawned candidates get a runway before the evaluator can kill them.

> Kilo: *"The auto-spawn proposal is step 4, not step 1 — stopping at step 4 yields a faster-running conveyor belt to the kill floor."*

### Why this matters for "stuck in paper trading for months"

The system has been killing strategies on **statistically-insufficient evidence** (small-n rolling windows) and calibrating its kill thresholds on **the same dead strategies' in-sample data**. This is a self-reinforcing downward ratchet: every cycle, the survivor pool shrinks, thresholds re-tune to the shrunken pool, more strategies fall below, repeat. Real-money confidence is unreachable not because edge doesn't exist but because the **evaluation machinery destroys evidence faster than it accumulates.** The fix is statistical rigor in the kill gate + an incubator runway — not more strategy births into the same meat grinder.

### M-IDs to add to master plan

- **M-055** — Re-calibrate kill thresholds: walk-forward ROBUST/MODERATE gate + min-n + binomial/Bayesian test. Owner: unassigned. First action: audit `commodity_kill_switch.py` / `fx_kill_switch.py` / `strategy_killer.py` cutoffs.
- **M-056** — Strategy incubator pipeline: zero-kill-pressure runway, 30+ forward trades before live scoring. Owner: unassigned.
- **M-057** — Decouple `score_booster` from crypto-only gating (`quality_gates.py:346-350`). Owner: unassigned.
- **M-058** — Auto-spawn replacement pipeline (gated by M-055/M-056). Owner: unassigned. **Explicitly sequenced last.**

## 2026-05-15 — Phase 2-D kill audit (full 6 symbols) + gate-bypass swarm verdict

Two more `caveman:cavecrew-investigator` subagents dispatched on the open action items. Findings below. (Peer PR #1065 "Phase 2-D kill audit — verdicts not reproducible from resolver-v2" landed independently and corroborates.)

### Phase 2-D commodity-kill audit — 3 of 5 kills are data-flawed

Recomputed each killed symbol's PRE-kill stats from `dashboard_data.json::picks.recent_closed` vs the blacklist comment's cited numbers (`quality_gates.py:1258-1264`):

| Symbol | Cited (n/WR/sum) | Recomputed PRE-kill | Verdict |
|---|---|---|---|
| GC=F (gold) | 91 / 39.6% / −0.52 | n=3 / 0.0% / −1.41 | **KILL_DATA_FLAWED** (n 91→3) |
| SI=F (silver) | 181 / 44.2% / −4.47 | n=3 / 33.3% / PF 0.06 / −3.93 | **KILL_DATA_FLAWED** (n 181→3) |
| CL=F (crude) | 6 / 16.7% / −5.25 | n=4 / 25.0% / PF 1.03 / +0.27 | KILL_DATA_VALID (inconclusive, n≤4) |
| CT=F (cotton) | 12 / 8.3% / −8.41 | n=12 / 66.7% / PF 3.50 / +32.30 | **KILL_DATA_FLAWED** (confirmed by deep-dive) |
| KC=F (coffee) | 12 / 8.3% / −6.02 | n=2 / 0.0% / −5.91 | KILL_DATA_VALID (inconclusive, n≤2) |
| agro/energy (ZC/ZS/ZW/LE/HE/BZ/HO/RB/NG) | — | NO_DATA in recent_closed | no verdict |

**Caveat:** `recent_closed` is a recent window — the cited n=91/n=181 for GC=F/SI=F may be a fuller ledger snapshot not present in `recent_closed`, OR (per the subagent) aggregate counts across all commodities. The "n 91→3" gap is therefore **suggestive, not conclusive** for GC=F/SI=F. CT=F is conclusive (n=12 matches exactly, WR 8.3%→66.7%). **Do NOT auto-unblacklist GC=F/SI=F** — that needs a full-ledger recompute, not the recent_closed window. The cotton deep-dive (`reports/deep_dive_cotton_2026-05-15.md`) is the only fully-proven case.

**Conclusion:** Phase 2-D used unreliable data at panel time (2026-04-29) — at minimum the small-n kills (CT=F, and KC=F citing the *identical* n=12/WR 8.3%) are bogus, consistent with unresolved-pick-counted-as-loss. This is exactly why **M-055 (kill-threshold re-calibration) is the P0**: a kill protocol that fires on panel-time snapshots of unresolved picks will keep mis-killing. The kill gate must read only the resolver-v2 ledger and require a min-n floor.

### Gate-bypass — swarm says don't "fix" it the obvious way

The bug report: 29 CT=F picks emitted post-blacklist. Investigator traced it — `audit_trail/dashboard_generator.py:7883-7903` loads `multi_asset_closed.json` and adds closed picks to the dashboard **without** calling `passes_active_gate()`. All 14 `COMMODITY_BLACKLIST` symbols can leak into the dashboard's closed list this way.

Asked the swarm whether to fix at (A) dashboard display filter or (B) emission gate. DeepSeek (HIGH confidence; xai+kilo failed transport) gave the correct third answer:

> **Gate at execution/sizing — NOT generation, NOT dashboard display.** Blacklisted symbols should be rejected at order placement / position sizing. Leave generation and dashboard display unchanged so the historical record stays intact for re-evaluation.

This is right: filtering CLOSED picks off the dashboard would **hide the very evidence** (cotton's real 66.7%/82.9% WR) needed to overturn a bad kill — entrenching the Phase 2-D error. The 29 CT=F picks showing in `recent_closed` is **correct behavior**, not a bug. `passes_active_gate()` is already the execution-side gate.

**Resolved action:** NO code change to `dashboard_generator.py`. Remaining real question — verify the `multi_asset_copytrader` / `multi_asset_cot` OPEN picks pass through `passes_active_gate()` before any execution/sizing step. If they do, there is no leak — only a display artifact. If they don't, fix at the sizing module (e.g. `position_sizer`/order-router), not the dashboard. Logged as a verification task, not a code edit.

### Session action-item status (rolled up)

| Item | Status |
|---|---|
| Cotton CT=F real-money claim | REVERSED — blacklisted; kill was data-flawed; verdict HOLD_KILLED_PENDING_DATA (deep-dive PR #1061) |
| Phase 2-D kill audit | DONE — peer PR #1065 + this entry; 3/5 kills data-flawed |
| Gate-bypass "bug" | RESOLVED as non-bug — display artifact; gate belongs at execution (swarm verdict) |
| M-055 kill-threshold re-calibration | OPEN P0 — the through-line of every finding this session |
| M-056/M-057/M-058 | OPEN — sequenced after M-055 |
| BOND scanner expansion beyond TLT/HYG | OPEN — only genuinely-thin class |
| FUTURES | OPEN — needs new strategies (all emitters deliberately blocked) |
| /goal skill | DONE — PR #1066 |




---

## 2026-05-15 — Operator idea: research_index broken links + per-AI pick attribution

> in parallel get the broken links within https://findtorontoevents.ca/audit/research_index.html fixed.
> e.g. for one of the runs I see a bunch of local files, likely you could find the most relevant ..
>
>     E:\findtorontoevents_antigravity.ca\research\asset_class\bond\run_2026-05-11T19-34-52Z
>     E:\findtorontoevents_antigravity.ca_deepdive_pr\research\asset_class\bond\run_2026-05-11T19-34-52Z
>     E:\swarmv2-wt\research\asset_class\bond\run_2026-05-11T19-34-52Z
>     E:\tmp\dailyidea-main-push\research\asset_class\bond\run_2026-05-11T19-34-52Z
>     E:\tmp\ghcopilot-main-20260514-1\research\asset_class\bond\run_2026-05-11T19-34-52Z
>
> I believe the purpose is to find out our performance per asset class or something like that?
> or to see our research process and swarm picks per asset class and the reason why each AI made
> a pick, and then individually we should be able to track which AI is great at guessing picks,
> for short-term vs long-term and which asset class, and what are they doing differently.

**Interpretation / action items:**
- `research_index.html` links point to absolute local Windows paths (`E:\...`) — broken on the live
  site. Fix: rewrite to repo-relative web paths (`research/asset_class/<class>/run_*/...`), or
  publish the referenced run artifacts under `/audit/research/`.
- The 5 paths above are the *same run* (`run_2026-05-11T19-34-52Z`) duplicated across 5 worktrees/
  clones — canonical copy is `research/asset_class/bond/run_2026-05-11T19-34-52Z` in the main repo.
- North-star feature: per-AI pick attribution — track which engine/persona made each pick, its
  rationale, horizon (short vs long), asset class, and realized outcome → leaderboard of
  "which AI is best at which asset class / horizon". Candidate home: extend the swarm
  pick-provenance work (M-051) + `research_index.html` as the UI surface.

---

## 2026-05-16 — Debate Swarm: PROVEN Statistical Edge Per Asset Class

**Saved at:** 2026-05-16T07:30Z
**Requested by:** operator (Claude Code session)

### Prompt (saved verbatim — for cloud agents / Kimi swarm):

> Once done create a "debate swarm" and have them debate in multiple rounds until each and every cloud model we have that is able to respond. They will debate the topic of what are the top actions we can take on our github repository and/or database / github actions jobs, backtesting protocol and other code pieces / such as strategies... what are the top priority action items that can take us from a theoretical "it might maybe work" to a "PROVEN statistical edge" per asset class. An edge strong enough that we can actually trust to spend our own REAL money on it... and we have more winners than losers, or bigger winners than losers... and a proven statistical edge.
>
> The swarm will also debate a prompt that we can provide to cloud agents, or a Kimi cloud swarm of agents etc, where they will be able to go through the prompt and provide us extreme value-add and action items where if implemented will ensure we get world-class hedge-fund level performance per asset class (or at least narrow down which asset classes are predictable and worthy to put real money into it... and look into other stuff such as DNA mutation or inverse of failing strategies, or expansion to penny stocks / meme coins / no or low-fee mutual funds etc).
>
> Run some other swarms also related to the perspectives of a hedge fund manager, and a Quant, risk manager, etc... and then review all swarm_runs output (including earlier output) and recent .MD files over the past week especially and look for action items and check each one against our code base.
>
> The swarm will review this prompt / skill along with our reports/MASTER_ACTION_PLAN_2026-05-15.md / money-maker-readyv2 along with our 90day plans etc.

### Swarm debate questions:

1. **"Proven edge" gate**: What is the minimum statistical bar (n, WR, PF, CI-lower, AC1, DSR) before we can trust real money on each asset class? Where are we today vs that bar?

2. **Pipeline integrity**: Elite systems (aggregated_picks OOS PF=7.02, kimi_signal_tracking OOS PF=15.94) absent from active_picks.json. What is the P0 fix path?

3. **Kill list vs mutation**: mutation_lab (PF=0.19), battleground (PF=0.00), alpha_engine (PF=0.67) — kill, mutate, or isolate? What does the DNA mutation protocol say?

4. **EQUITY mislabeling**: signal_validation tags crypto tokens as EQUITY. Does fixing this change EQUITY verdict from "promising" to "unproven"?

5. **COMMODITY pipeline**: multi_asset_cot n=0 in OOS dataset despite dashboard PF=4.72. Pipeline bug or dead system?

6. **Cloud agent mega-prompt**: Design a prompt that a Kimi/Gemini/GPT-5 cloud swarm can use to independently verify our edge claims and propose highest-ROI next actions.

7. **Expansion**: penny stocks, meme coins, low-fee mutual funds — which has the most accessible edge given our current tooling?

8. **Inverse/DNA mutation**: Which failing strategies have the highest potential for inversion or mutation?

### Personas for debate rounds:
- **Hedge Fund Manager**: Risk-adjusted returns, Sharpe/Sortino, MDD, institutional credibility
- **Quantitative Analyst**: Statistical rigor, multiple-testing correction, walk-forward, regime changes
- **Risk Manager**: Tail risk, correlation clustering, position sizing, circuit breakers
- **Data Engineer**: Pipeline integrity, data quality, resolver accuracy, ghost systems
- **Devil's Advocate**: Challenge every positive claim; higher bars; survivorship bias, look-ahead bias

### Reference files for swarm context:
- `reports/MASTER_ACTION_PLAN_2026-05-15.md`
- `reports/money_maker_ready_20260516T060000Z.md`
- `reports/oos_validation_2026-05-16.md`
- `reports/asset_class_90day_plan_*.md` (all 8 classes)
- `ASSET_CLASS_DEEP_ANALYSIS_REPORT.md`
- `ASSET_CLASS_DEEP_DIVE.md`
- All `reports/asset_class_*` files

### Expected deliverables from swarm:
1. Per-class verdict: REAL MONEY READY / ACCUMULATING / BLOCKED / KILL
2. Top 10 highest-ROI code actions (with file + function targets)
3. Cloud agent mega-prompt (copy-paste ready for Kimi/Gemini/GPT)
4. Mutation candidates with specific hypothesis for each failing strategy
5. Expansion roadmap (penny/meme/mutual fund) with effort estimate


### Vetting Notes — MiniMax "ULTIMATE_PROVEN_STATISTICAL_EDGE_2026_05_16.md"

MiniMax is **directionally correct** but used the wrong dataset (55,510 live dashboard picks vs our 5,000-pick pre-registered OOS split). Their "Proven ML Combo" at 79.4% WR is actually our **kimi_signal_tracking** (76.6% WR, PF=7.7) and **aggregated_picks** (77.9% WR, PF=6.94). Full vetting: [minimax_ultimate_edge_2026-05-16_VETTED.md](reports/peer_notes/minimax_ultimate_edge_2026-05-16_VETTED.md)


### MiniMax Session 2 — EXACT_FILTERS_FOR_UI (2026-05-16, HIGH CREDIBILITY)

MiniMax read the actual KIMI codebase and all code references verified 100% accurate. Key filters confirmed in code:
- `win_probability >= 0.65` — `KIMI_FEB172026/live_scanner.py:306` ✅
- `MIN_CONFIDENCE=65, MIN_RR=2.0` — `KIMI_RISEOFTHECLAW/alpha_engine_v2.py:76-78` ✅
- `ELIMINATION_RULES: danger=25, promotion=55, champions=75` — `KIMI_FEB172026/elimination_engine.py:20-28` ✅
- 24-feature ML ranker — `KIMI_FEB172026/ml_signal_ranker.py:99-108` ✅

Full vetted doc: [EXACT_FILTERS_FOR_UI_minimax_2026-05-16.md](docs/EXACT_FILTERS_FOR_UI_minimax_2026-05-16.md)

Statistical claims (COMMODITY 89.8%, ETF 57.4%) still from dashboard not OOS — see [minimax_ultimate_edge_2026-05-16_VETTED.md](reports/peer_notes/minimax_ultimate_edge_2026-05-16_VETTED.md)


---

## 2026-05-16 — Comet Browser deep-inspect: repo audit + critical path findings

Source: Comet browser deep-inspection of https://github.com/eltonaguiar/findtorontoevents_antigravity.ca (141,651 commits). Captured for swarm prioritisation + next-sprint planning.

### What exists and is actually strong

- `antigravity_quant_engine.py` — well-architected 6-stage pipeline: StrategyEvaluator → RegimeDetector → AgreementAlpha → SignalWeightedScorer → KellySizer → FinalGate. IC-weighted signals, family deduplication, live Binance fallback.
- 5-agent ensemble with ML scoring (Spearman rho +0.33 on ml_score).
- 1,927 closed picks with decile analysis (top 20% decile: WR 60%, avg PnL +4.2%).
- 28 dedicated researcher agent reports in `CRYPTO_ML_WORLDCLASS_RESEARCH/` already audited the system; `FINAL_SYNTHESIS_REPORT.md` is the synthesis.
- `DEFINITIVE_HEDGE_FUND_PIPELINE.md`: 110 picks/week → 5-10/week plan, projected WR 41% → 85-94%.
- RegimeDetector: live 6-regime classification from BTC/ETH 4h Binance klines (STRONG_BULL / BULL / LEANING_BULL / CHOP / LEANING_BEAR / BEAR).
- AgreementAlpha: family deduplication, MIN 2 diverse models with 55% confidence floor.
- SignalWeightedScorer: 14 IC-weighted signals (bb_squeeze=10, volume_surge=8, ema_cross=7…).
- KellySizer: half-Kelly with score/regime/chop caps.

### Critical path — what is broken

| Issue | Evidence |
|---|---|
| Backtest-forward correlation = -0.91 | System is anti-predictive — higher backtest score → worse live result |
| 78.9% of trades hit SL | Stops too tight for 15m noise level |
| 96.5% of strategies fail OOS | Only 1 in 260 survives walk-forward |
| DNA live WR = 14.3% | DNA mutations generating junk |
| elite_score rho = +0.012 | Essentially zero predictive power — should be retired |
| Banned strategies (PF < 1.0) still making picks | Graveyard not enforced at generation time |
| 43 memories, 0 embeddings in agentmemory | Semantic search non-functional |
| Cost model subtracts fees on every bar, not just trade bars | All DSR computations invalid |

The 28-agent audit's Three Laws (FINAL_SYNTHESIS_REPORT.md): (1) fix signal quality first, (2) reduce transaction costs, (3) enforce existing infrastructure.

### Proposed next module: edge_concentrator.py

Target: drop between AgreementAlpha and FinalGate. Four components:

1. Rolling IC monitor — daily IC per strategy x symbol pair, Bayesian shrinkage toward zero for n<30, auto-pause if rolling 30-day IC < 0.05.
2. ATR-based dynamic TP/SL — SL = entry +/- (ATR_14 x multiplier), TP targeting_ratio by regime (STRONG_BULL 2.5, BULL 2.0, LEANING_BULL 1.8, CHOP 1.5, LEANING_BEAR 1.2, BEAR 0.8). Directly addresses 78.9% SL hit rate.
3. Symbol tier filtering — Tier 1 (always: BTC/ETH/SOL/BNB), Tier 2 (IC>0.10: XRP/ADA/AVAX/DOT/LINK/MATIC/UNI), Tier 3 (IC>0.15 + ATR check). Kill list: UNI/APT/OP until IC prove-out.
4. Regime-routed strategy allocation — CHOP: only mean-reversion (BB squeeze, RSI divergence). STRONG_BULL: only trend + breakout. BEAR: only short-biased + funding-rate extreme.

Reads from alpha_engine/data/strategy_symbol_edge_registry.json. Standard lib + numpy + pandas only. Success criterion: 110 picks → 5-10/week, 41% → 70%+ WR.

See DAILY_IDEAS_PROMPTS.MD "Comet Browser arena.ai Prompt 2026-05-16" for the full arena.ai Battle Mode prompt.

### Claude audit of Minimax edge claims (same session)

| Minimax Claim | Reality | Verdict |
|---|---|---|
| cot_positioning_CT_locked LONG WR=89.8%, n=49, PF=13.1 | COT LONG: n=3, WR=33.3%, PF=0.14; strategy not found | FABRICATED |
| COT is LONG-side edge | cot_positioning SHORT WR=62.1%/PF=1.85; cftc_cot_commercial_signal SHORT WR=56.2%/PF=2.41 | DIRECTION WRONG |
| ml_enhanced INJ/FET/DYDX/RENDER 85-100% WR | DYDX n=10 WR=100% (tiny sample); overall ml_enhanced n=261, WR=48.7%, PF=1.19 | CHERRY-PICKED |
| Confidence 0.85-0.90 WR=82%, PF=11.8 | Actual: n=12, WR=50%, PF=4.76 | 4x INFLATED |
| AuditEnsemble_LONG WR=94.7% | Recent: n=9, WR=33.3%, PF=0.99 (losing) | STALE |

Real institutional edges (recent_closed, verified): mega_mutation/macd_rsi_m048 (n=45, WR=71%, PF=4.95), baby_strats_forward/vwap_deviation_reversion_eth (n=59, WR=61%, PF=2.53), kimi_riseoftheclaw/rs-breakout-scout (n=36, WR=75%, PF=4.38), dna_winner_picks/claude_ml_moderate_mut (n=101, WR=61%, PF=2.49), COT SHORT (WR=56-62%, PF=1.85-2.41).

## 2026-05-17 — Grok 4.3 (WSL): Cross-agent daily_ideas corpus review (30+ files) + Phase 2 plan

User provided the full list of daily_ideas / DAILY_IDEAS*.MD files from main tree + worktrees + reports/ + grok_sessions/ (Grok, Cursor, Kimi, Copilot, Ollama, NVIDIA, HuggingFace, LLM Arena, synthesis, edge_per_class, etc.).

**Review outcome vs live repo state:**
- The "FUTURES =F classification fix" flagged as the next step in the 2026-05-16 handoff report was **already shipped** in that session. `audit_trail/dashboard_generator.py:_derive_asset_class` now has first-class `contract_type` support (index/rates/currency_future → FUTURES) + robust =F root logic that correctly routes COMMODITY vs FUTURES (with explicit-hint escape for our own futures emitters). FUTURES tile is now populated.
- Current per-class reality (post all 05-16 shipments): COMMODITY Tier-1 verified clean post COT dedup (PF ~2.57+), EQUITY Tier-2 (PF~1.56), ETF/CRYPTO building, FOREX in mutation, BOND/FUTURES thin but unblocked.
- Free API audit: Strong production stack (yfinance universal, Binance public, Coingecko, DefiLlama TVL/capital flows, CFTC COT, FRED partial, CME public). Gaps repeatedly called out: high-quality free earnings/PEAD data (SEC EDGAR / Nasdaq), options flow (Polygon free tier + CBOE), futures OI/roll-yield (CME direct), FX carry differentials, deeper on-chain.
- World-class gap analysis (AQR factors/carry/momentum, DE Shaw PEAD, DBMF/KMLM CTA momentum+roll, Bridgewater macro, FX carry) synthesized into concrete P1 scaffolds and backtests.

**Top recommended Phase 2 actions** (ranked by impact × verifiability from the corpus):
1. PEAD full backtest + emitter integration for EQUITY.
2. CTA/DBMF replication scaffold (`tools/research/dbmf_replication.py`) for COMMODITY sustainability.
3. FOREX carry factor scaffold + gate.
4. ETF sector rotation relative strength + macro overlay.
5. PCG-5 portfolio gate stack (shadow mode first).
6. `tools/free_data_audit.py` + close 2-3 highest-leverage free gaps above.

Full details, free API table, world-class gap matrix, and verification checklist live in the committed report:
`reports/per_asset_class_edge_phase2_free_api_audit_2026-05-16.md` (PR on `docs/phase2-per-asset-edge-free-api-2026-05-16`).

All changes keep the "75/75 quality_gates + live dashboard_generator run + per-class PF uplift" bar. Goal remains: profitable predictions with positive profit factor **per asset class** via statistical edge that beats costs.


## 2026-05-17 — Session V: /audit verdict de-contamination + canonical PF registry (PRs #1150-1152)

Strategic repo assessment found the root blocker is not strategy edge but the
**measurement layer**: the `/audit` `asset_class_health` verdict recomputes
PF/WR inside `dashboard_generator.py` with no independent cross-check, and was
systematically inflated.

Shipped:
- **PR #1150** — COMMODITY `sizing_allowed` forced `false` (headline PF 7.71 is
  the CT=F/COT leak); `PERMANENTLY_KILLED_STRATEGIES` (quan_engine family, ~70%
  of the CRYPTO ledger @ PF 0.38) excluded from the verdict aggregate.
- **PR #1151** — `build_pf_registry.py` ingests the full 32-ledger source set,
  dedups re-emissions (~41% dup rate), exposes `by_asset_class_policy_clean`;
  `reconcile_pf_registry.py` cross-checks registry vs verdict, exits 2 on
  divergence.
- **PR #1152** — both wired into the hourly `audit-dashboard.yml` pipeline.

Reconciliation result — 6/9 classes diverge. Canonical (policy-clean) PF:
COMMODITY 1.25 (tile 7.71), CRYPTO 1.24 (tile 1.33), EQUITY 0.74 (tile 1.65),
FOREX 0.36 (tile 0.85). **Every class is sub- or near-floor.** No class is
real-money ready; the registry, not the tile, is verdict-grade.

### IDEA-V1: M-067 — generator reads the registry (swarm-planned)

Make `asset_class_health` READ `pf_registry.json` instead of recomputing, so
the two cannot diverge. Planned by a 3-agent swarm (investigator: 64 consumer
refs; Plan agent: 6-task design; red-team: 10-risk register). Must-fix risks:
slippage-honesty (registry PF is gross — gross-as-verdict flips COMMODITY from
loser to winner), registry never committed, staleness detection, live-sizing
reaction to PF/n shifts. Full plan: `MASTER_ACTION_PLAN_2026-05-15.md` §25.

### IDEA-V2: external-AI roadmap convergence trap — STOP the intake

8 external-AI "real-money roadmaps" (Ernie, GLM, MiMo, Sauna, Sonnet-4.6,
ppl-sonar, Grok-4.2, ChatGPT-o3, gpt-5-search) all audited the PUBLIC dashboard
surface, not the repo, and invented the same false gaps (no execution/risk/
kill-switch/regime layer — all exist). Lesson: N AIs reading the same surface
≠ verification. Library shopping-lists (vectorbt/ccxt/Riskfolio/Prefect) miss
the point — the blocker is a corrupted ledger, not missing libraries. Stop the
roadmap-review cycle; the genuine items (White's Reality Check M-065, CIRO
M-066) are already captured.


---

## 2026-05-17 ~09:30 UTC -- External-AI Input Audit (Opus 4.7)

Reviewed **7 external-AI deliverables** this session (LMArena 5-gap audit, 4
crypto-predictor code dumps, Baidu ERNIE: 12 docx + 9 paste-ready code files).
**Verdict: integrate none.**

**Consistent failure pattern** -- external AIs have no repo access, so they
produce plausible code that does not survive contact with the codebase:
phantom file paths (risk/, ml_ops/, feature_repo/, execution_service/ -- none
exist); reinvent already-validated modules (pbo_cscv.py, deflated_sharpe.py,
position_sizing.py all exist); duplicate shipped work; assume a production HFT
execution stack the repo deliberately is NOT. One external AI fabricated a
tool-run result it could not execute.

**Standing rule:** grep the live repo before acting on any external "already
exists" / "already verified" claim. The bottleneck is repo-grounded execution,
not idea generation.


---

## 2026-05-17 ~10:45 UTC -- Money-Ready /audit tab + CI hardening (Opus 4.7)

Shipped the **Money Ready** tab on findtorontoevents.ca/audit (PR #1163):
per-asset-class money_ready_verdict (DSR + PBO/CSCV + SPA gates), refreshed
daily, with one archived snapshot per UTC day + drift vs the prior day so
improvement/degradation is monitorable.

- `tools/money_ready_snapshot.py` execs `money_ready_verdict.py --json`
  as a **subprocess** (never imports it) -- immune to a peer editing that
  module. Validates the output schema, fails loud on drift.
- Daily workflow `money-ready-snapshot.yml` (06:15 UTC).
- Design vetted by a 3-engine swarm (deepseek + xai + cerebras) -- unanimous:
  producer must subprocess, not import.
- CI: `Deploy Rise of the Claw` verify step fixed (PR #1165) -- a curl
  timeout under `bash -e` (exit 28) was failing deploys; guarded all curls
  + made the health check non-fatal. GH Actions otherwise healthy (1 real
  failure / 100 runs; the rest are by-design push-supersede cancellations).

Seed verdict 2026-05-17: MONEY_READY = COMMODITY; WATCH = CRYPTO, EQUITY, ETF.

## 2026-05-18 00:41 UTC — /audit pipeline explainer prompt (for briefing any AI)

Saved per user request. Full doc: reports/AUDIT_PIPELINE_EXPLAINER_PROMPT.md
(includes how /audit is fed — repo + GitHub Actions + MySQL ejaguiar1_stocks/
ejaguiar1_backtests — current per-asset-class status, the cotton/CT=F edge
verdict [real-looking but single-symbol-concentrated + leakage-inflated =
too risky, not a real edge], and a benchmark vs how top quants/hedge funds/
AI labs validate edge: deflated Sharpe, PBO/CSCV, White Reality Check, CPCV,
pre-registered hypotheses, economic priors, net-of-cost capacity-aware
backtests).

Use it verbatim to brief an AI before asking for per-class edge improvements.
Companion harvest already run: NO_EDGE_BRAINSTORM_CLOUD.MD.

---

## 2026-05-18 — Deep real-money-ready audit prompt (logged for later execution)

Operator request — captured as a standing idea (deferred, not yet run). Run as
a full `/money-maker-readyv2` pass when prioritized:

> Refer data-science / obsidian skills + others. Research recent .MDs that
> publish performance of active/closed picks per asset class on
> findtorontoevents.ca/audit. Find the baseline data store —
> mysql.50webs.com `ejaguiar1_stocks` + `ejaguiar1_backtests` (creds via env
> vars DB_PASS_STOCKS / DB_PASS_BACKTESTS — never hardcode/paste), plus the
> GitHub Actions jobs that feed it.
>
> 1. Pick traceability — is there a solid way to trace each pick and its
>    methodology end-to-end? Get that critiqued.
> 2. Missed-gainers check — pull "top crypto gainers by day", check if the
>    system missed them and why. Repeat per asset class.
> 3. Real-money-ready verdict — deep analysis of whether the system(s) can
>    stop backtesting and take real capital. Research the exact stats that
>    must pass (deflated Sharpe, PBO/CSCV, White Reality Check, CPCV,
>    net-of-cost capacity-aware, pre-registered hypothesis, economic prior).
> 4. If not ready (likely): how to improve per asset class. Mistakes? What
>    would a quant / hedge-fund manager say to do? What does the DB / strategy
>    pool say? Any obvious free datasets / strategies missing?
> 5. Any asset class performing worse than a coin flip where the issue is
>    findable? Any corrupt/wrong DB data where filtering one thing makes
>    profit great? Any consistent filter set (FWD WR, score, etc.) that would
>    have been reliably profitable?
>
> Cross-reference: `reports/ROADMAP_TO_EDGE_2026-05-18.md` (swarm-reviewed:
> 5–8% odds of HF-grade edge on current infra), `reports/pf_registry_*.md`
> (canonical policy-clean ledger), `reports/EQUITY_VERDICT_FINAL_2026-05-18.md`.
> Prior state: 8 harness kills, no canonical edge. The genuinely-new analysis
> not yet done = the magic-filter hunt (mine
> `pf_registry.json::by_asset_class_strategy_symbol/date` for any PF≥1.5,
> n≥30 slice) and the missed-gainers gap.

Status: PENDING. Owner: unassigned. Note for executor — the `pf_registry.json`
strategy/symbol/date views are the fastest canonical path to the filter hunt;
do NOT re-derive from raw `closed_picks.json` (unit-mismatch trap).

---

## 2026-05-18 — Reusable session-handoff & edge-harvest prompts

Operator-supplied prompts, logged for reuse in future sessions.

### Prompt A — session handoff (CHATBIBLE + summary docs)

> Once done, use the protocol in `CHATBIBLE.MD` to summarize your changes, and
> drop your chat transcript summary to a .MD, plus a .MD summarizing your
> accomplishments and future steps — for this session and for future sessions
> — especially: how can we get findtorontoevents.ca/audit to be a world-class
> prediction system across all asset classes? How many weeks / months / years
> away are we? What speeds it up — more symbols? more strategies? more
> research? more bug fixes? more DB analysis?

### Prompt B — multi-AI edge harvest

> If you have no other action items, use subagents and consult other AIs and/or
> the agent swarm. Harvest ideas on how to actually get to safe + profitable
> per asset class. Exhaust all API keys, trying every model family per key
> (use any Windows environment variable). Heavily use `grok -p` (correct cwd
> `/tmp`, `--no-alt-screen --output-format json`) for fast second opinions.
> Use subagents as needed.

### Prompt C — magic-filter hunt (recommended, not yet run)

> Mine `audit_dashboard/data/pf_registry.json` views
> `by_asset_class_strategy_symbol` / `_strategy_date` / `_strategy_policy_clean_net`
> for ANY slice with PF≥1.5 and n≥30 — a regime / symbol / time-of-day / score
> bucket / FWD-WR bucket that is consistently profitable. Conversely, find any
> corrupt-data cohort whose removal flips a class from sub-1.0 PF to positive.
> Do NOT re-derive from raw `closed_picks.json` (pnl_pct unit-mismatch trap).

### Prompt D — pick traceability audit (recommended, not yet run)

> For one pick per asset class on findtorontoevents.ca/audit, trace it
> end-to-end: which source emitted it, which gates it passed/failed, why it is
> or is not in Smart Picks / High Conviction / Money Ready. Critique whether
> the methodology is sound and reproducible. Then check "top crypto gainers by
> day" — did the system miss them, and why? Repeat per asset class.

Status: Prompts A + B executed 2026-05-18 (see reports/EDGE_HARVEST_2026-05-18.md,
CLAUDE_DESKTOP1_*_2026-05-18_0213EST.MD). Prompts C + D PENDING.

---

## 2026-05-18 — Vet the master plan + codify all /audit frontend paths

Idea / task (verbatim):

> Vet your suggested action plan: ask our other AIs extensively (ollama cloud
> models, X_AI/Grok, kimi code, DeepSeek). Run a multi-phase debate where the
> AIs double-check the plan. Give them a STRONG prerequisite so they don't have
> to dig into our database — be explicit about which DB tables / JSON files /
> filters matter.
>
> Codify / log ALL paths under findtorontoevents.ca/audit front-end — every
> "button" and every "tab": Smart Picks button vs Smart Picks tab, High
> Conviction picks button, Money Ready, all tabs/buttons. Fact-check each, and
> get the manifest auto-updated at least every 24 hours.
>
> Then double-check performance per asset class when applying each of these
> buttons, and also the "?Guide" concepts.

Plan being vetted: reports/MASTER_ENHANCEMENT_PLAN_2026_05_18.md (measurement-
first, 6-phase; no asset class money-ready; paper-only sandbox).
Status: executing 2026-05-18 — see reports/audit_frontend_manifest*, the AI
debate synthesis, and per-button per-class performance section below.

---

## 2026-05-18 — Path to Hedge-Fund Grade Performance

**User prompt (2026-05-18T08:00Z):**

> Check all .MD within the past week for enhancements or key stats per asset
> class. Determine if there is a statistical edge (even a buried one) or what
> we need to get hedge-fund level performance.
>
> Ideas to explore:
> - More symbol universe expansion
> - More aggressive strategies
> - Pool strategies from copytraders / the web and backtest ourselves
> - Check TradingView Pine scripts and backtest them ourselves
> - What is our path to truly profit and top-notch hedge fund performance?

**Current state (2026-05-18T08:00Z per money_ready_verdict()):**
- COMMODITY: MONEY_READY PF=3.67 WR=71.9% n=139 (note: CT=F 84% concentration blocks PBO)
- CRYPTO: MONEY_READY PF=2.87 WR=70.8% n=291 (DSR validation still pending)
- ETF: WATCH n=105, VIX gate enforced (VIX>=20 blocks picks)
- EQUITY: INSUFFICIENT_DATA n=31 (MySQL ghost-rows blocking, PA console action needed)
- FOREX: NOT_READY PF=0.36 WR=23.4%
- BOND/FUTURES: INSUFFICIENT_DATA

**Honest edge verdict from deep-dives (reports/DEEP_DIVE_MONEYREADY_2026-05-18.md):**
- NO strategy passes the walk-forward efficiency harness (eff>=0.30, 3/5 windows)
- Best candidate: `st_fear_greed_contrarian` n=91, PF~2.8, WR=74.7% — but ONE regime only
- COMMODITY PF=2.30 may be a leakage mirage (COT look-ahead, 38/47 picks are CT=F)
- CRYPTO confidence field had 146 rows with values in [15,78] (percent-as-integer bug)

**Path to institutional grade — prioritized:**
1. **C-2 Exchange net-flow cross-sectional spread** (CRYPTO) — best new strategy to build
   - Long 2 majors with largest exchange outflow, short 2 with largest inflow
   - Market-neutral, beta-cancelling — fixes the beta-domination defect behind all 9 harness kills
   - Cost: ~$30-200/mo CryptoQuant feed; daily bars, no tick infra needed
   - Pre-register in hypothesis_registry.json BEFORE any backtest
2. **E-1 PEAD intraday-anchored** (EQUITY) — long drift after earnings surprise, ~$30/mo Polygon
3. **C-3 Funding-settlement liquidation cascade** (CRYPTO) — free data, medium effort
4. MySQL purge (PA console ~2026-05-24) to unlock EQUITY n from 31 to ~200+
5. CT=F concentration cap enforce (COMMODITY_CTF_CAP=1) to enable PBO
6. Widen edge_stability_harness.py to read all 32 pf_registry ledger files (not just closed_picks.json)

**GitHub libraries for efficient MD/strategy indexing:**
- `vectorbt` — fast backtesting (already imported, needs wiring to production path)
- `quantstats` — tearsheet generation per strategy class
- `openbb-sdk` — free alternative data aggregator (FRED, SEC, crypto)
- `alphalens` — Quantopian-style factor analysis to validate edge persistence over time
- `ccxt` — exchange API aggregator for crypto strategies from copytraders
- `ta-lib` / `pandas-ta` — fast indicator calculation for Pine script backtest recreation

**TradingView Pine → Python backtest path:**
1. Export Pine script logic (RSI, EMA crossovers, Supertrend, etc.) to pandas-ta equivalents
2. Run on OHLCV from yfinance (free) or Polygon ($30/mo for intraday)
3. Validate on pf_registry before adding to production pick path
4. Pre-register hypothesis in hypothesis_registry.json first
5. Forward test ≥30 picks before wiring to production

---

## 2026-05-18 — Quickest Path to Profitable Picks: Framework + MySQL Audit Table + New Symbols

**Session:** Synthesized from CORRECTED_GAMEPLAN_2026-05-18.md, daily_ideas_edge_sweep_2026_05_17.md, SUPREME_PLAN_90days.md, money-maker-action-plan, live pf_registry.json + money_ready_verdict.py output.

---

### LIVE STATUS (2026-05-18T19:46Z)

| Class | n (policy_clean_net) | WR | PF | money_ready_verdict |
|---|---|---|---|---|
| COMMODITY | 51 | 56.9% | 1.67 | MONEY_READY (whitelist n=143, WR=69.9%, PF=3.14) |
| CRYPTO | 2,083 | 44.2% | 1.16 | MONEY_READY (whitelist n=291, WR=70.8%, PF=2.87) |
| EQUITY | 37 | 45.9% | 1.28 | INSUFFICIENT_DATA |
| FOREX | 295 | 12.5% | 0.17 | NOT_READY (hard-disabled) |
| FUTURES | 12 | 16.7% | 0.96 | INSUFFICIENT_DATA |
| ETF | 0 (pf_registry sync gap) | — | — | INSUFFICIENT_DATA |
| BOND | 1 | 0% | 0.00 | INSUFFICIENT_DATA |

**Critical discrepancy to investigate:** `money_ready_verdict` shows CRYPTO WR=70.8%/PF=2.87 but `pf_registry::by_asset_class_policy_clean_net` shows WR=44.2%/PF=1.16 on the full 2,083-pick universe. The verdict is computed on a whitelist subset. The true edge is narrower than the dashboard implies. Always cross-check both sources.

---

### FRAMEWORK: Three Axes to Profitable Picks

#### Axis 1 — Kill the Bleeders (zero new code, immediate PF lift)

Run this to find current drag candidates:
```bash
python -c "
import json
d = json.load(open('audit_dashboard/data/pf_registry.json', encoding='utf-8'))
rows = [r for r in d['by_asset_class_strategy_policy_clean_net'] if r.get('n',0)>=20 and r.get('profit_factor') is not None and r['profit_factor'] < 1.2]
for r in sorted(rows, key=lambda x: x['profit_factor']):
    print(f\"{r['asset_class']} | {r['strategy']} | n={r['n']} PF={r['profit_factor']:.2f}\")
"
```

Candidates already identified (must add to `BLOCKED_ASSET_STRATEGY_PAIRS` in quality_gates.py after mutation-axes review per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`):
- `st_fear_greed_contrarian` (CRYPTO): n=139, PF=0.88
- `multi_period_rsi_confluence_eth` (CRYPTO): n=26, PF=1.11
- `atr_percentile_gate` (CRYPTO): n=29, PF=1.10

Each block raises the effective CRYPTO aggregate PF. Run mutation analysis before killing: `python tools/mutation_analysis.py`.

#### Axis 2 — Expand Proven Winners to New Symbols

**CRYPTO proven strategies to expand (top by PF, n>=20, from live pf_registry 2026-05-18):**

| Strategy | Current Symbol | n | WR | PF | Expansion Candidates |
|---|---|---|---|---|---|
| ml_enhanced_*_15m_D_ensemble_stack | DYDXUSDT | 31 | 96.8% | 53.44 | GMXUSDT, PERPUSDT (perp DEX same regime) |
| ml_enhanced_*_1d_B_lightgbm | INJUSDT | 28 | 96.4% | 40.98 | SEIUSDT, TIAUSDT (L1 same cohort) |
| ml_enhanced_*_1d_B_lightgbm | FETUSDT | 44 | 56.8% | 9.25 | AGIXUSDT, OCEANUSDT (AI-token cohort) |
| ml_enhanced_*_1h_D_ensemble_stack | RENDERUSDT | 47 | 61.7% | 3.80 | AKASHUSDT, IOTAUSDT |
| mega_mutation | CRYPTO (broad) | 72 | 56.9% | 2.19 | Already multi-symbol; expand to 50 coins |

**COMMODITY — fastest path from PF=1.67 to n>=100 (currently one strategy: `multi_asset_copytrader`):**

CT=F (cotton) has 84.9% concentration. Add these 4 symbols to the COMMODITY scanner universe via `multi_asset/cot_pipeline.py` (CFTC Socrata already wired):
- GC=F (gold): CFTC COT commercial net positions — documented 12-18mo predictive power
- SI=F (silver): correlated to GC=F, smaller sizing
- CL=F (crude oil): Baker Hughes rig count + OPEC supply calendar as co-signal
- ZS=F (soybeans): USDA WASDE crop report cadence as natural signal timing

#### Axis 3 — MySQL Daily Pick Audit Table (DOES NOT EXIST — build this next)

**Current state:** `schema-baseline.sql` has `at_incubator_strategies.rejection_reasons` (strategy-level). No table tracks why individual picks were rejected each day, or whether rejected picks would have been profitable.

**Proposed schema:**
```sql
CREATE TABLE daily_pick_audit (
  id INT AUTO_INCREMENT PRIMARY KEY,
  audit_date DATE NOT NULL,
  symbol VARCHAR(30) NOT NULL,
  strategy VARCHAR(100) NOT NULL,
  asset_class VARCHAR(30) NOT NULL,
  gate_that_fired VARCHAR(80) NOT NULL,
  rejection_reason TEXT,
  score DECIMAL(8,4) DEFAULT NULL,
  confidence DECIMAL(6,4) DEFAULT NULL,
  would_have_closed_profitable TINYINT DEFAULT NULL,
  hypothetical_pnl_pct DECIMAL(10,4) DEFAULT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_dpa_date_class (audit_date, asset_class),
  KEY idx_dpa_gate (gate_that_fired),
  KEY idx_dpa_symbol (symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**Wire-up:** in `audit_trail/quality_gates.py::passes_active_gate()`, after each `return False, reason`, INSERT one row. Backfill `would_have_closed_profitable` nightly by joining against `closed_picks` on `(symbol, strategy, audit_date)`.

**Queries this unlocks:**
1. Which gate fires most on ETF picks? — `SELECT gate_that_fired, COUNT(*) FROM daily_pick_audit WHERE asset_class='ETF' GROUP BY 1 ORDER BY 2 DESC`
2. Are we over-filtering? — `SELECT AVG(would_have_closed_profitable) FROM daily_pick_audit WHERE would_have_closed_profitable IS NOT NULL` — if >50%, gates are too aggressive
3. Opportunity cost of any gate — filter by `gate_that_fired='<gate_name>'`

---

### ETF: The Most Underserved Candidate

MySQL `by_asset_class` raw shows ETF closed=85, wins=50, WR=61.0%, PF=2.00. But `pf_registry::by_asset_class_policy_clean_net` shows ETF n=0. This is a sync gap, not a real lack of edge. Walk-forward profile: OOS WR=75%, fold consistency=100%, +23% improving trend — the best OOS of all classes.

**Fastest fix:** check `.github/workflows/mysql-trading-sync.yml` scope — does it include ETF? Run `gh run list --workflow=mysql-trading-sync.yml --limit 5`. If the sync is missing ETF, add it and ETF may immediately show PF>=2.0 in pf_registry.

**New ETF symbols:** XLF, XLE, XLK, XLV, XLI (SPDRs with 15+ years history). Signal: relative-strength rank across 11 SPDRs, monthly rebalance. Candidate file: `alpha_engine/etf_rotation_strategy.py`.

---

### Best AI Prompt (use as session-opener)

> "Read `audit_dashboard/data/pf_registry.json::by_asset_class_policy_clean_net` and run `python alpha_engine/money_ready_verdict.py`. Compare them — if money_ready_verdict shows PF>1.5 for a class but pf_registry shows PF<1.2 for the same class, identify which strategies are in the whitelist but not the full universe. Then: (1) block any strategy with n>=20 and PF<1.0 using BLOCKED_ASSET_STRATEGY_PAIRS after mutation-axes review; (2) identify 2-3 new symbols for the top-performing strategies and spec a PR; (3) check if daily_pick_audit table exists in schema-baseline.sql and if not, create it and wire into passes_active_gate(). Always cross-check PF numbers against pf_registry before claiming any class is MONEY_READY."

---

### Open Action Items

| Priority | Action | Class | Effort | Blocker |
|---|---|---|---|---|
| P0 | Investigate ETF pf_registry sync gap (MySQL WR=61%/PF=2.0 vs pf_registry n=0) | ETF | XS | None |
| P0 | Fix MySQL silent-fail: `mysql-trading-sync.yml` line 43 `\|\| echo "non-fatal"` | Infra | XS | None |
| P1 | Block `st_fear_greed_contrarian` (CRYPTO, n=139, PF=0.88) after mutation review | CRYPTO | S | Mutation review |
| P1 | Add GC=F/SI=F/CL=F/ZS=F to COMMODITY scanner universe | COMMODITY | M | COT feed check |
| P1 | Design + wire `daily_pick_audit` MySQL table | Infra | M | PA console DB access |
| P2 | Expand ml_enhanced to GMXUSDT/PERPUSDT (DYDX-cohort) | CRYPTO | M | Model retrain |
| P2 | Wire FRED_API_KEY secret → BOND scanner (n=1 → target n=20) | BOND | S | FRED_API_KEY secret |

NFA — all picks are research surface. No real-money sizing without DSR>=0.95, PBO<0.10, n>=100 clean trades, and drift_alert=FALSE on that class.

---

## 2026-05-18 — Session CT Corrections + Refined Profitability Prompt

### ETF Root Cause Correction

**Previous entry was wrong:** The ETF n=0 in pf_registry is NOT a mysql-trading-sync.yml scope gap.

Investigation (2026-05-18T20:30Z):
- `alpha_engine/data/active_picks_etf.json`: 14 ETF picks
- `alpha_engine/data/etf_sector_picks.json`: 19 ETF picks
- `alpha_engine/data/scanner_output/active_picks_etf.json`: 11 ETF picks
- All 21 `closed_picks.json` files: **0 ETF picks**

**Real root cause:** ETF picks are being generated but never closing (resolved to closed). The outcome_resolver isn't processing ETF picks — likely because ETF picks lack TP/SL price levels or expiry timestamps, so the resolver never fires a close event. Fix: inspect ETF pick schema vs non-ETF picks; add TP/SL/expiry to ETF pick generators.

**Impact:** Until this is fixed, ETF will always show n=0 in pf_registry regardless of how many active picks are generated.

### Gate Changes This Session (2026-05-18 Session CT)

- **M-109 RR gate ENFORCED** (commit `6e6c4d9f63`): `RR_HIGH_GATE_ENFORCE=1` is now the default. ~15% of open picks with risk_reward > 1.5 are hard-rejected. EV math: RR=1.5-2.0 → EV = -0.228 per unit. Kill-switch: `RR_HIGH_GATE_ENABLED=0`.
- **Gate 2 (ML_ENHANCED_CRYPTO_QUARANTINE)**: DEFERRED — 112 surviving ml_enhanced variants need individual audit before bulk quarantine.
- **Gate 3 (MDD_GATE_ENFORCE)**: REJECTED — sequential equity-curve MDD is wrong methodology for a diversified system. Redesign as rolling 30d or portfolio-level MDD.
- **futures_momentum**: Zero-sizing monitor mode maintained. 4/4 swarm said block; operator kept in monitor for regime-stratified data collection until 2026-07-18.

### Refined Optimal AI Prompt (Session CT)

Copy-paste prompt for any AI agent to get the fastest path to profitable picks per asset class:

```
You are a quant trading analyst for findtorontoevents_antigravity.ca (repo: eltonaguiar/findtorontoevents_antigravity.ca).

ORIENT (read in this order):
1. `audit_dashboard/data/dashboard_data.json::performance.asset_class_health` — current WR/PF/n per class
2. `audit_dashboard/data/pf_registry.json::canonical_view` (or by_asset_class_policy_clean_net) — canonical universe PF
3. `alpha_engine/data/strategy_performance.json` — per-strategy n/WR/PF

KEY NUMBERS (2026-05-18):
- CRYPTO: n=2,083 WR=44.2% PF=1.155 (canonical) — biggest drag: st_fear_greed_contrarian (n=139, PF=0.88)
- COMMODITY: n=51 WR=56.9% PF=1.673 — good but 84.9% CT=F concentration (add GC=F/SI=F/CL=F/ZS=F)
- EQUITY: n=37 WR=45.9% PF=1.277 — thin sample; MySQL purge needed (~2026-05-24)
- FOREX: n=295 WR=12.5% PF=0.174 — hard-disabled; raw PF=3.177 suggests non-JPY SHORT edge may be collateral damage
- ETF: n=0 — picks generated but NOT resolving (outcome_resolver doesn't close ETF picks — missing TP/SL)
- BOND: n=0 — FRED_API_KEY not wired; bond scanner runs but no resolved trades
- FUTURES: n=12 WR=16.7% PF=0.96 — zero-sizing monitor mode until 2026-07-18

THREE AXES:
Axis 1 (KILL): Block st_fear_greed_contrarian CRYPTO (n=139, PF=0.88) after mutation-axes review.
  Run: python tools/mutation_analysis.py --strategy st_fear_greed_contrarian
  If no axis rescues it: add ("CRYPTO", "st_fear_greed_contrarian") to BLOCKED_ASSET_STRATEGY_PAIRS in audit_trail/quality_gates.py.

Axis 2 (EXPAND): COMMODITY — add GC=F/SI=F/CL=F/ZS=F to multi_asset/cot_pipeline.py (CFTC Socrata already wired).
  CRYPTO — expand ml_enhanced_*_1d_B_lightgbm from INJUSDT (PF=41, n=28) to SEIUSDT/TIAUSDT.

Axis 3 (BUILD): Fix ETF outcome_resolver — inspect why ETF closed_picks.json is always empty.
  Check: alpha_engine/outcome_resolver.py — does it filter by asset_class? Does ETF emit TP/SL?
  Target: get n>=30 ETF resolved picks to validate WR=61%/PF=2.00 from MySQL historical data.

NEVER do: size real capital (pf_registry PF<1.5 on canonical universe), ignore pf_registry in favor of money_ready_verdict whitelist, run dashboard_generator.py locally (auto-generated).

QUALITY GATE: Before claiming any class is MONEY_READY, verify:
  python -c "from alpha_engine.money_ready_verdict import money_ready_verdict; print(money_ready_verdict('CRYPTO'))"
  Then cross-check with pf_registry canonical n and PF.
```


---

## 2026-05-19 — Quant rescue prompt (operator, for swarm/AI consultation)

Operator-supplied prompt for consulting AIs on diagnosing a failing prediction system.

> You are a quant assigned to fix a failing company who tried to predict
> stocks/crypto/forex/bonds/commodities/etfs/futures.. and is not profitable..
> and definitely doesnt have more or more profitable winners than losers.
>
> What stats do you run? What methodology do you run through their GitHub
> Actions, MySQL database?

Status: used 2026-05-19 — responses from Mercury 2 + Grok harvested + reviewed
(see reports/QUANT_RESCUE_REVIEW_2026-05-19.md). Reusable for future AI consults.


---

## 2026-05-19 — Full System Audit Prompt (Lopez de Prado level)

Source: User-supplied AI consultation prompts for cracking the edge problem.
All 4 prompts below submitted to agent swarm 2026-05-19.

### Context (from audit snapshot)
- Overall (55k+ closed picks): 11.13% WR, −3.56% avg return, Sharpe −2.34, PF 0.46
- EQUITY: best performer (recent PF ~1.55, WR 51%, n=426). T2 candidate.
- COMMODITY (CT=F COT): headline PF 2.48 but recent decay + data artifacts.
- CRYPTO: 46% WR, PF <1.3; inverted confidence (high ML_score = worse WR).
- FOREX/ETF/BOND: Sub-floor or tiny n.
- Core problems: lookahead leakage, inverted confidence, strategy decay, sparse forward-testing, no CPCV/DSR/PBO/MinTRL gates in GHA.

### Prompt 1 – Full System Audit (Claude Opus)
```
You are a world-class quant researcher (Lopez de Prado level).
Audit this entire repo: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/
Focus ONLY on the prediction pipeline (alpha_engine, feature_store, data_pipeline, backtest_results, audit_trail).
Identify every source of lookahead bias, survivorship bias, data leakage, inverted confidence, and strategy decay.
Then propose concrete fixes + new validation gates (WFE, CPCV, DSR, PBO, MinTRL).
Output in this exact format:
1. Leakage inventory (file + line)
2. Confidence recalibration plan
3. New readiness gates to add to GitHub Actions
4. One new strategy skeleton per asset class that would pass the new gates
```

### Prompt 2 – Strategy Regeneration (Ring-2.6-1T or GLM-5.1)
```
Act as a senior quant PM.
We have poor forward WR and inverted confidence across asset classes.
Using only the data schema from database/ and the current feature_store, generate 3 new high-conviction strategy ideas (one each for EQUITY, CRYPTO, COMMODITY) that explicitly avoid the failures in failed_strategies/.
For each idea provide:
- Entry/exit rules
- Feature list (no lookahead)
- Walk-forward test plan
- Expected statistical edge (Sharpe target, MinTRL)
```

### Prompt 3 – Confidence & Scoring Fix (MiMo or Claude)
```
Our ml_score is inverted (high score → low WR).
Fix the scoring booster in alpha_engine/config.py and audit_trail/quality_gates.py so that confidence becomes monotonic with forward performance.
Propose a new hybrid score (ml_score × regime_factor × freshness) and show the math.
```

### Prompt 4 – GitHub Actions Upgrade
```
Add automated gates to .github/workflows/audit-dashboard.yml:
- Run full CPCV + DSR + PBO on every new pick batch
- Auto-quarantine any strategy with forward WR <48% or PF <1.2
- Alert on confidence inversion
Output the complete updated workflow YAML.
```

### Bounce-Back Plan (7–14 day execution order)
1. **Kill multi-asset mixing** — freeze to EQUITY only (strongest cohort: WR 51%, PF 1.55)
2. **Add LDP gates** — CPCV, DSR>0.95, PBO<0.05, MinTRL<90d, WFE>60% in GHA
3. **Rebuild confidence** — monotonic hybrid: 0.55×ml + 0.25×regime + 0.15×freshness + 0.05×fwd_wr_30
4. **Paper-pilot 4 weeks** — top 3 EQUITY strategies through new gates, 30-50 closed picks
5. **External model review** — Claude Opus 4.7 Max or GLM-5.1 with top 5 failing strategies + backtest CSV

### Model Priority for IDE Agents
| Priority | Model | Strength | Prompt Focus |
|----------|-------|----------|--------------|
| 1 | Claude Opus 4.6/4.7 | Lowest hallucination on quant pipelines | Strategy audit + LDP gate implementation |
| 2 | GLM-5.1 (Zhipu) | Leakage & decay detection | Feature-store + backtest hygiene |
| 3 | Ring-2.6-1T (inclusionAI) | Multi-step planning | Strategy generation + walk-forward redesign |
| 4 | MiMo-V2.5-Pro (Xiaomi) | Fast iteration | Confidence recalibration experiments |

### Grok Feedback (2026-05-19) — Validity Verdict
Grok proposed 4 code changes; swarm validation in progress (see reports/audit_swarm_2026-05-19.md):
- `lopez_de_prado_gates()`: DSR formula appears SIMPLIFIED (real LDP DSR accounts for trials/non-normality). PBO=1-WR² is not the standard formula. Flag for swarm review.
- `hybrid_score(... forward_wr_30)`: using 30-day FORWARD WR in a live scoring function = lookahead bias if `forward_wr_30` is future data. Valid concept if `forward_wr_30` = trailing 30d historical.
- `equity_momentum_regime_signal()`: `df['close'].pct_change(252).std()` on full DataFrame = lookahead. Needs to be rolling or computed on strictly past data.
- Hybrid score weights (0.55/0.25/0.15/0.05): reasonable starting point but unvalidated.

### CPCV / DSR — Definitions
- **CPCV (Combinatorial Purged Cross-Validation)**: Lopez de Prado 2018. Generates multiple test paths by combinatorially splitting the data timeline, with purging to prevent leakage between train/test. Avoids path-dependency of standard k-fold.
- **DSR (Deflated Sharpe Ratio)**: Sharpe corrected for selection bias (number of trials, non-normality, skewness). DSR = SR × (1 - γ × ln(N_trials)) approximately. Rejects results that pass only by overfitting.
- **PBO (Probability of Backtest Overfitting)**: From CPCV. Fraction of test paths where the best in-sample strategy performs below median out-of-sample. PBO > 0.5 = strategy is likely overfit.
- **MinTRL (Minimum Track Record Length)**: How long a strategy needs to live to achieve SR confidence above a target at given significance.
- **WFE (Walk-Forward Efficiency)**: OOS Sharpe / IS Sharpe. Below 60% suggests overfitting.

Status: swarm analysis in progress — see reports/audit_swarm_2026-05-19.md for results

### Swarm Audit Results (2026-05-19) — Final Verdicts
Swarm completed (agent a85d3551), report at reports/audit_swarm_2026-05-19.md:
- **Grok DSR**: OVERSIMPLIFIED — missing N (trials), skewness/kurtosis, T scaling. Our existing statistical_gates.py has the correct implementation.
- **Grok PBO**: FLAWED — `1-WR²` has no theoretical basis; real PBO needs CPCV rank comparison. Even Grok's v3 "PBO proxy" using forward_wr is not real PBO.
- **Grok forward_wr_30 in hybrid score**: CRITICAL LOOKAHEAD — future WR as scoring input invalidates all backtest results.
- **Grok regime global std()**: LOOKAHEAD — fixed with `rolling(252).std().shift(1)` benchmark.
- **Confidence inversion root cause**: Label leakage #1 (ml_score negatively correlated with forward returns = textbook diagnostic), overfit #2, regime change #3.
- **Best action for 0/14 gate passes**: Ensemble of weak signals first (variance reduces √14 = 3.7×), then intraday data if still failing (14-day window with daily data = only 14 observations; with 5-min = ~1,092).

### Equity Validation Results (2026-05-19)
Script: alpha_engine/validation/run_equity_edge_test.py (uses correct LdP DSR, not Grok's formula)
Output:
  n=69 EQUITY resolved picks (from 87 found, 9953 total pool)
  WR=46.4% (32W/37L), Mean PnL=+0.41%, PF=1.23, SR=1.487
  DSR: PASS (probability=1.000, E[maxSR|50trials]=~0)
  Newey-West t-stat: FAIL (t=0.578, p=0.563 — not significant)
  VERDICT: NOT YET PROVEN — n=69 below 100 threshold, NW fails
Primary blocker: need n≥100 resolved EQUITY picks for reliable inference.

### Grok Rounds 4-8 (2026-05-19) — Persistent Errors + What Changed
Round 4 (v2 "final corrected"): DSR still wrong (`sr * norm.cdf(...)`) — acknowledged by Grok in round 7.
Round 5 (validation script): Same DSR bug, new format. PBO still `1-forward_wr**2`.
Round 6 (swarm feedback): Meta-advice on swarm prompt design; no new code.
Round 7 (acknowledging DSR error): Grok admits `sr * norm.cdf(...)` was wrong. Provides correct formula.
Round 8 ("what prompt would prevent this"): Grok proposes ideal prompt format. Reasonable lesson.
PBO: STILL NOT FIXED across all rounds — `1 - mean_forward_wr**2` persists.

Correct DSR (verified in statistical_gates.py line 239): `norm_cdf((SR - E[maxSR]) / sr_std)` — no `sr *` prefix.
Real PBO requires CPCV (Bailey et al. 2016) — not achievable with just WR data.
Our purged_cv.py has PurgedKFoldCV (purge_days=5, embargo_days=5) — can be extended to CPCV.

### New Deliverables (2026-05-19 session)
- alpha_engine/validation/run_equity_edge_test.py — correct DSR (uses statistical_gates.py), NW t-stat, real data
- alpha_engine/strategies/equity_momentum_regime.py — point-in-time regime signal (rolling vol + shift(1))
- docs/STRATEGY_PERFORMANCE_BLUEPRINT.md — where to find strategies/performance in repo + DB
- reports/audit_swarm_2026-05-19.md — full swarm verdicts on Grok feedback + 4 audit prompts
- tools/h035_funding_settlement_pressure.py — H-035 TESTED_KILL (sign-flip)
- tools/mysql_dedup_fix.py + .github/workflows/mysql_dedup_fix.yml — dedup fix via GHA (IP-restricted)
- audit_trail/quality_gates.py — _normalize_confidence extended (val>10 → /100)

---

## 2026-05-19 — AI Prediction Tournament + Stealth Browser Council

### IDEA-AI-TOURNAMENT: AI Model Prediction Tournament

**Summary:** Pit every cloud AI model family we have API access to against live financial markets. Each model chooses its own symbol universe, generates a production-grade trading strategy per asset class, and produces forward-test picks tracked live.

**Core concept:**
- Models compete against each other AND against our own validated strategies in the audit dashboard
- Forward-test picks tracked live via GitHub Actions daily price pulls
- Hallucination checks: any backtest claim independently reproduced using real OHLC data
- Page: findtorontoevents.ca/audit/ai-tournament

**Model matrix (Phase 1 — cloud):**
Mercury (inception-labs), Cerebras (llama-4-scout), Ring-2.6-1T, Grok-3, DeepSeek-R1, GPT-4o, Claude Opus, Gemini 2.5 Pro, GLM-4 (OFOX), Qwen3-235B, Mistral Large, Command R+

**Phase 2 (future):** Local models via Ollama (gemma3:1b, llama3.2:1b, qwen2.5:1.5b, etc.)

**Methodology:** `docs/AI_PREDICTION_TOURNAMENT_METHODOLOGY.md`
**Swarm review:** `reports/ai_tournament_methodology_swarm_review_20260519.md` — all 3 engines NEEDS_WORK, key fixes adopted:
- Pre-registered symbol universe (not free-choice)
- Min n=30 per class before ranking
- CI-based scoring: `Score = lower95(WR) × lower95(PF)`
- Trade-level submission required; exact binomial test on WR claims
- Closing price at expiry (not mid-price); slippage: 5-10bps equity, 0.2% crypto
- Pin model versions at tournament start
- FOREX window: 21 days (not 10)
- Min RR ≥ 1.5; SL ≤ 2×TP enforced at submission

**No-shortcuts prompt:** `/noshortcutsprompt` skill created at `.claude/skills/noshortcutsprompt/SKILL.md`

**Pre-registered universe (v1.0):**
- EQUITY: S&P 500 constituents
- CRYPTO: Top 30 by market cap (CoinMarketCap)
- FOREX: EURUSD, GBPUSD, USDJPY, AUDUSD, USDCHF
- COMMODITY: XAUUSD, XAGUSD, CL=F, NG=F, HG=F
- BOND: US10Y, US30Y
- ETF: SPY, QQQ, IWM, EEM, GLD

**Data integrity flags:**
- 🟢 FORWARD_TEST — live market, post-tournament-start
- 🟡 BACKTEST_VERIFIED — independently reproduced
- 🔴 BACKTEST_DISPUTED — not reproducible within ±10%
- ⚫ HALLUCINATION_CONFIRMED — fabricated data + -1 pick penalty

---

### IDEA-STEALTH-BROWSER: Anonymous Multi-AI Council via Stealth Browsing

**Summary:** Use stealth/anti-detect browser automation + rotating proxies to query free/guest-accessible AI web interfaces anonymously — building a "council of AIs" without API keys, accounts, or static IP exposure.

**Why:** Many AIs are accessible without sign-in (Grok, Meta AI, Perplexity, You.com, HuggingChat, Poe, DuckDuckGo AI Chat). This gives access to additional model opinions for zero marginal API cost.

**Target interfaces (no/minimal sign-in):**
- grok.com / grok.x.ai — no X account required (web)
- meta.ai — Llama guest access
- perplexity.ai — guest mode (rate-limited)
- you.com/chat — YouChat guest access
- poe.com — daily free messages, many models
- huggingface.co/chat — optional login, open models
- duckduckgo.com/chat — free GPT-4o mini, Llama 3, Mixtral (strips IP)
- felo.ai — multilingual AI search, no login

**Stealth frameworks:**
- **CloakBrowser** (CloakHQ/CloakBrowser) — source-level Chromium fingerprint patches, passes 30/30 bot tests, same API as Playwright (`pip install cloakbrowser`)
- **Camoufox** (daijro/camoufox) — Firefox alternative, different engine fingerprint
- **Stealth-Browser MCP** (vibheksoni/stealth-browser-mcp) — wraps into MCP server for Claude agent use
- **Nodriver** — avoids CDP signatures entirely

**Proxy strategy:**
- Start with Tor (`socks5://127.0.0.1:9050`) for free but slower
- ProxyBroker for rotating free proxy pool
- Residential proxies (IPRoyal/Bright Data) for production reliability
- CloakBrowser supports: `launch(proxy="http://user:pw@gate:8000", geoip=True)` — auto-adjusts timezone/locale to match proxy IP

**POC architecture:**
1. Python + CloakBrowser + proxy rotator
2. Per query: pick random proxy → fresh browser context → navigate to target → type prompt → extract response → close context
3. Fan same prompt to 3-5 targets in parallel (different proxies)
4. Collect labeled responses → feed into swarm synthesis pipeline

**Integration with our system:**
- Could replace expensive API calls for exploratory research questions
- Could provide "anonymous second opinions" from proprietary models (Grok, GPT) without API costs
- Could be used to gather AI opinions on stocks/picks without leaving a footprint
- Feed into `tools/swarm/swarm_run.py` as a new engine type: `--engines stealthweb`

**POC script:** `tools/stealth_browser_poc/` (skeleton to be created)
**Priority:** Medium — start after AI Tournament Phase 1B (model prompting round) completes

---

## 2026-05-19 — Anonymous AI council prompt (saved per user request)

### PROMPT: Institutional Stock Prediction Pipeline Code Harvest

Saved from the consult-webscrape proof-of-concept session. Use this prompt with the 6 known-working anonymous sources (especially eye2.ai which returns actual Python code).

```
Write production-grade Python code for ONE institutional-quality stock prediction pipeline. Requirements: (1) pull market data, (2) feature engineering, (3) proper train/validation split for time series, (4) model training, (5) backtest function, (6) risk controls, (7) clear runnable script structure, (8) no placeholders. Return full source code only
```

**Working sources for this prompt:**
- `eye2.ai` — returns real Python code with TimeSeriesSplit, RandomForest, proper feature engineering
- `chatgot.io` — returns class-based template (some scraper truncation)

**How to run:**
```bash
python tools/anon_ai_council/deep_probe_from_manifest.py \
  --input swarm_runs/source_manifest_probe_2026-05-19.json \
  --output swarm_runs/deep_probe_code_harvest_$(date -u +%Y%m%d).json \
  --limit 20 --timeout 22
```

**Context:** GitHub Copilot built the `tools/anon_ai_council/` skill; Claude Code completed the benchmark (6/102 anonymous sources work). Reports: `updates/2026-05-19-anonymous-ai-council-*.md`.

---

## 2026-05-24 — AI Tournament Pipeline Hedge-Fund-Grade Session

### Session Overview
Built and hardened a 34-model, 9-asset-class tournament prediction pipeline. 3,149 picks in `tournament_picks` table, 53.4% overall WR.

### Key Deliverables
- **Pipeline:** DB ingest fix → Kelly sizing → price tracker PENNY/FUTURES → kill gates → copy trader adapter → position sizing rules
- **Analytics:** Edge significance gate (4-test framework), portfolio analytics (Sharpe/VaR/drawdown), concentration monitor, performance reporting
- **Data:** FRED API key fix → all 7 series live; Kalshi/Polymarket wired into research; Copy Trader adapter (20+ picks/2h)
- **Quality:** Persona_WR confidence proxy, auto-zero KILLED personas, asset-class-level blocking (FOREX KILLED, BOND WARN)
- **UX:** Model summary table + ELI5 on tournament page; PENNY/FUTURES added to universe

### Key Findings
- 0 Tier-1 edge pairs pass all 4 statistical gates (strict by design)
- deep_value × EQUITY: 60 picks, 60% WR, +1.07% PnL — only proven edge pair
- FOREX: 57.3% WR but -0.39% avg PnL — statistical trap, zero allocation
- regime_adaptive 84.6% WR is SYNTHETIC_SEED data from old pipeline (not our pipeline)
- ML calibration is SYSTEM-WIDE INVERTED — confidence 0.85-0.90 has 20% WR
- UEPS (US Equity Picks) has n=0/100 — no live equity picks yet

### Remaining Gaps for IDEA-B (Hedge Fund Grade Picks)
- [ ] Statistical kill gates need walk-forward validation
- [ ] FRED macro regime → pick direction integration (data exists, not wired to scoring)
- [ ] Polymarket whale consensus → only 1 symbol with 2+ agreement (need Dune addresses)
- [ ] "Super Secure Picks" persona category for conservative capital preservation
- [ ] HYROTRADER crypto-only → need multi-asset expansion
- [ ] UEPS needs first 100 picks to build track record
- [ ] ML calibration inversion fix — confidence is anti-predictive
- [ ] 353 legacy picks with future timestamps need cleanup

### Reports Generated
- reports/EDGE_CRITERIA_SWARM_2026-05-24.md
- reports/EDGE_CRITERIA_SWARM_SYNTHESIS_2026-05-24.md
- reports/HEDGE_FUND_GAP_ANALYSIS_2026-05-24.md
- updates/2026-05-24-ai-tournament-hedge-fund-readiness.html

### Agent Swarm: 3-engine (quant + systems + portfolio) + 3-engine follow-up (action plan + gap analysis + integration)
### Files Modified: 20+ across pipeline, analytics, dashboard, config, CI workflows
## 2026-05-24 — Persona-Based Safe-Pick System: Swarm Critique + Integration Analysis

**Source:** User-provided prompt template + Python script for "Persona-Based LLMs for Safe-Pick Asset-Class Recommendations." Evaluated against our existing `ASSET_CLASS_EDGE_AND_SAFETY_REVIEW_2026-05-24.md` and `EDGE_CRITERIA_ACTION_PLAN_2026-05-24.md`.

**Swarm engines consulted:** DeepSeek (deepseek-v4-flash, 967 tokens in / 2,148 out) + Cerebras (gpt-oss-120b, 994 tokens in / 4,000 out). OpenRouter failed (key limit exceeded). Run ID: `swarm_runs/persona_safe_pick/run_20260524T035822Z`.

### Swarm Consensus Verdict: 3/10 — Steal the documentation, discard the implementation

Both engines independently converged on the same conclusion within a narrow band (Cerebras ~4/10 on useful elements, DeepSeek 3/10 overall). The proposal has a sophisticated framing but collapses under the weight of our existing infrastructure.

---

### 1. Gap Fit — Which of OUR gaps does this fill?

| Gap (from our review) | Filled? | Notes |
|---|---|---|
| No unified safety definition across asset classes | **Partial** | Formalizes definitions but they're hardcoded, not data-driven |
| Inconsistent data-frequency handling | **No** | Script uses single-point `yfinance.info`, not time-series |
| No back-testing of safety filters | **No** | Prompt mentions protocol; script has `# TODO: backtest` |
| Missing safety layer for crypto/ETFs | **Shallow** | Crypto filter is `vol<30%` — far too permissive |
| No composite safety score | **Yes (concept)** | The 0-1 safety score is the only genuinely additive element |
| No persona documentation per class | **Yes** | Prompt forces standardized descriptions per asset class |

**Bottom line:** Fills 2/6 gaps (and those partially). The implementation gaps (data frequency, backtesting, rejection rules) remain untouched.

---

### 2. Realism — Paper Tiger Thresholds

Both engines ran universe scans against the proposed thresholds (market_cap>$50B, vol<12%, beta<0.9, D/E<0.4, FCF growth>5%, div_yield≥1%, Sharpe>1.2, maxDD<12%, CAGR>8%).

**Cerebras result:** ~2 stocks survive from S&P 500 (0.5% of universe).
**DeepSeek result:** 0-3 stocks. "In 2023, exactly **0** S&P 500 stocks passed all filters simultaneously."

The thresholds are over-constrained for any live-trading pipeline. This would produce 0-1 picks per year, making the conviction stack useless 99% of the time. Crypto vol<30% filter eliminates Bitcoin (60-80% annualized vol) — you'd only get stablecoins and 2-3 large-cap alts.

**Fix paths if adopted:**
- Relax Sharpe to >0.8, maxDD to <20%, CAGR to >5% (tiered, not binary)
- OR: Use safety_score as a confidence multiplier, not a pass/fail gate
- OR: Add tiered buckets — S-tier gets tight thresholds, A-tier gets relaxed

---

### 3. Integration Feasibility — ~150 Lines of Glue Code Needed

**Where it would plug in:**

```
per_asset_class_predictor.py (raw IC-weighted scores)
    ↓
persona_safe_pick.py (NEW: filters by persona rules)
    ↓
conviction_stack.py (tiers S/A/B) ← needs 5th score input
    ↓
hedge_fund_quality_gate.py (rejection rules) ← needs dynamic rules
```

**Integration cost:**
- JSON loader (`load_persona_rules.py`): ~25 lines
- Mapper (safety_score → conviction tier): ~30 lines
- Quality gate refactoring (static if→dynamic rules): ~30 lines
- Wrapper around value_screener.py: ~15 lines
- Refactor conviction_stack.py for 5th score: ~50 lines
- **Total: ~150 lines** plus testing

**DeepSeek recommended approach:** Use safety_score as a **final gate** (if safety < 0.5, reject regardless of other scores), not as a 5th input to the predictor. The safety_score is highly correlated with existing metrics already in `hedge_fund_quality_gate.py`, so adding it as an input would require re-weighting all scores.

---

### 4. Redundancy — 70% Overlap with Existing Code

| Our Persona (from review) | Proposed Persona | Overlap |
|---|---|---|
| Fortress Value (EQUITY) | "Defensive Value" | 80% (market_cap, D/E, vol, Sharpe) |
| Institutional Grade (CRYPTO) | "Stable Store" | 90% (vol filter only — ours is far more comprehensive) |
| Supply-Demand Fortress (COMMODITY) | N/A (not in script) | No overlap — script missing commodities |
| Momentum Fortress (ETF) | "Core Holding" | New but trivial (simple vol+beta filter) |

**Our existing `value_screener.py` already does:** Magic Formula rank, Piotroski F-Score, Acquirer's Multiple, Altman Z'', Beneish M, ROIC, FCF Yield, D/E, EPS history, dividend growth — all via time-series data. The proposed script does a subset with single-point `yfinance.info`.

**Our existing `hedge_fund_quality_gate.py` already does:** Per-class rejection rules, confidence dead bands, banned symbols, banned strategies, RSI overbought, forward-WR gates, trust-tier gates, regime-directional gates.

**Conclusion:** The only additive element is the **composite safety_score (0-1)** and the **formal persona documentation**. Both can be adopted without the full system.

---

### 5. Python Script — Production Readiness: 10% Salvageable

| Component | Status | What Needs Changing |
|---|---|---|
| **FCF growth** | Placeholder (`fcf_growth = 0.06`) | Needs `yfinance.download()` with 5 years of quarterly data → ~50 lines |
| **Backtest protocol** | Stub (`# TODO: backtest`) | Needs walk-forward with vectorbt/backtrader → ~200 lines |
| **Crypto handling** | Trivial (`vol<30%`) | Needs MVRV, exchange flows, funding rates → ~80 lines + Glassnode API |
| **Missing asset classes** | FOREX/BOND/COMMODITY/FUTURES missing | ~700 lines total + API keys for OANDA/FRED/CME/Quandl |
| **Error handling** | None (crashes on any missing ticker) | try/except + exponential backoff + cache → ~40 lines |
| **Testing** | None | Unit tests with mocked yfinance → ~50 lines |
| **Overall flow + JSON schema** | ✅ Salvageable | Clean architecture, matches our output format |
| **Threshold constants** | ✅ Salvageable | Can be externalized to `config/persona_thresholds.yaml` |

**Total rewrite needed:** ~1,170 lines across all components. 2-4 week project for a senior dev.

---

### 6. Priority Ranking vs EDGE_CRITERIA_ACTION_PLAN

Both engines independently ranked the persona system **5th out of 5** priorities:

| # | Item | Lines | Impact | Consensus |
|---|---|---|---|---|
| 1 | **P1 — Fix confidence field** | 5 | High (unlocks conviction_stack) | Do first |
| 2 | **P0 — Regime label audit** | 25 | Critical (prevents data leakage) | Do immediately |
| 3 | **FOREX zero-allocation** | 8 | Medium (stops bleeding) | Do third |
| 4 | **P3 — Position sizing rules** | 80 | High (risk management) | Do fourth |
| 5 | **Persona system** | 300+ | Low (redundant) | **Do last / skip** |

---

### 7. Novelty Assessment — What's Actually New?

**Genuinely novel:**
1. **Composite safety_score (0-1):** No single scalar for safety exists in our stack. This could be a useful **gate** (not input) after existing quality checks.
2. **Dynamic rule engine:** JSON-driven persona rules allow swapping/tuning safety thresholds without touching Python — but this requires refactoring the quality gate from static `if` statements.
3. **Persona documentation framework:** The prompt template forces standardized, human-readable descriptions that can be version-controlled.

**NOT novel — already in our stack:**
- All the actual filter metrics (vol, beta, D/E, Sharpe) are already in `value_screener.py` + `hedge_fund_quality_gate.py`
- The tiering system is already in `conviction_stack.py`
- No new alpha signals are introduced
- No new data sources are proposed

**DeepSeek's blunt verdict:** "The 'persona' framing is marketing copy. Nothing genuinely novel."

---

### 8. Missing Asset Classes — 700+ Lines to Extend

| Class | API Required | Lines | Key Safety Metrics |
|---|---|---|---|
| FOREX | OANDA/IBKR | 150 | Spread, rollover cost, carry trade, CVA |
| BONDS | FRED/BBG | 200 | Yield curve, duration, credit rating, OAS |
| COMMODITIES | Barchart/Quandl | 150 | Contango/backwardation, storage costs, roll yield |
| FUTURES | CME/IBKR | 200 | Expiry roll, margin requirement, basis |

**Total:** ~700 lines + API keys + data contracts. Biggest blocker is data licensing — paid feeds needed for bond ratings and futures margin data.

---

### 9. Composite Score Interaction — Recommendation: Gate, Not Input

**Current architecture:**
```
predictor → [trust, elite, ml, smart] → conviction_stack → quality_gate
```

**If adopted (recommended):**
```
predictor → [trust, elite, ml, smart] → conviction_stack → safety_gate (NEW) → quality_gate
```

**Rationale:** The safety_score is **highly correlated** with existing metrics already in `hedge_fund_quality_gate.py`. Adding it as a 5th input to `conviction_stack.py` would require re-weighting all scores and introduce multicollinearity. As a gate, it provides a clean pass/fail layer without disrupting the predictor weights.

**Implementation (30 minutes):**
```python
# Add to hedge_fund_quality_gate.py
def passes_safety_score_gate(pick: dict) -> tuple[bool, str]:
    safety = compute_safety_score(pick)  # 0-1 composite
    if safety < 0.50:
        return False, f"safety_score={safety:.2f} < 0.50"
    if safety < 0.70:
        return True, f"WARN: safety_score={safety:.2f} < 0.70"
    return True, f"OK: safety_score={safety:.2f}"
```

---

### 10. Bottom Line: 3/10 — Steal 3 Things, Discard the Rest

**✅ Steal (3 items, ~30 minutes):**

1. **Persona definitions as documentation** → Add as docstrings/comments in `hedge_fund_quality_gate.py` per asset class. The standardized format (Name, Role, Core Definition, Data Sources, Filters, Backtest Protocol, Output Format) is genuinely useful for onboarding and audit trail.

2. **Composite safety_score formula** → Add as a function in `alpha_engine/value_screener.py` (~50 lines). The weighted-average approach (vol × 0.25 + beta × 0.20 + Sharpe × 0.20 + DD × 0.15 + CAGR × 0.20) is sound, just needs relaxed thresholds. Use it as a **gate** (not input) in the quality pipeline.

3. **Per-asset-class safety definition template** → Formalize the YAML structure: `config/persona_thresholds.yaml` with per-class thresholds that feed both the safety_score computation and the existing quality gates. This makes thresholds configurable without code changes.

**❌ Discard (everything else):**

1. The Python script entirely — it's a toy with `fcf_growth = 0.06` placeholder
2. The crypto `vol<30%` filter — replace with our existing on-chain metrics
3. The stated backtest protocol — our existing walk-forward validation is better
4. The "persona" framing beyond documentation — it adds complexity without new edge
5. The thresholds as hard pass/fail — use tiered buckets instead

---

### Cross-Engine Convergence Table

| Finding | DeepSeek | Cerebras | Our Review |
|---|---|---|---|
| Paper tiger thresholds | ✓ 0-3 picks survive | ✓ ~2 picks survive | ✓ Confirmed |
| 70% redundant | ✓ | ✓ | ✓ |
| Lower priority than EDGE_CRITERIA | ✓ 5th/5 | ✓ 5th/5 | ✓ |
| Safety_score as gate, not input | ✓ | ✓ (via mapper) | ✓ |
| Script 90% rewrite needed | ✓ | ✓ | ✓ |
| Persona docs are salvageable | ✓ | ✓ | ✓ |
| Missing classes: 700+ lines | ✓ | ✓ | ✓ |
| Overall score | 3/10 | ~4/10 (useful elements) | 3.5/10 |

**3 independent analyses converge on the same conclusion.** The persona approach is well-framed but adds almost nothing beyond what our `value_screener.py` + `hedge_fund_quality_gate.py` + `conviction_stack.py` already do. Steal the documentation framework and the composite score formula, discard the implementation, fix the P0/P1 items first.

---

### Implementation Recommendation (If User Wants to Proceed)

**30-minute minimal version:**
1. Add safety_score function to `alpha_engine/value_screener.py` (~50 lines)
2. Add safety_score gate to `alpha_engine/hedge_fund_quality_gate.py` (~15 lines)
3. Add persona docstrings per asset class in `hedge_fund_quality_gate.py` (~30 lines)
4. Create `config/persona_thresholds.yaml` with relaxed thresholds (~30 lines)

**Total:** ~125 lines. No new modules. No API keys. No refactoring of conviction_stack.

**What this gets you:** A configurable safety score that gates picks at the quality layer, with documented per-class safety definitions. 80% of the proposal's value at 10% of the cost.

---

### Session cost

Swarm run: $0.0043 (DeepSeek + Cerebras, OpenRouter skipped). Total session swarm cost: ~$0.01.

**Files created:**
- `tmp/persona_safe_pick_swarm_prompt.txt` — swarm prompt
- `swarm_runs/persona_safe_pick/` — swarm output directory (deepseek.json, cerebras.json, _summary.json)
- `DAILY_IDEAS.MD` — this appendix appended

---

---

## 2026-05-25 02:55 UTC (22:55 EST 2026-05-24) — Tier-Rating Algorithm Question (cross-model survey)

**Source:** user request via Claude Opus 4.7 session, broadcast queued to the AI tournament fleet for inclusion in next prompting cycle.

### Question posed to every model in the tournament

> "If you were challenged to give a pick rating system to create a tier list of symbols on a scale of 1–10 per asset class, what algorithm would you use for each asset class? Output one weighted-formula recipe per class (EQUITY, ETF, CRYPTO, FOREX, COMMODITY, BOND, FUTURES, PENNY) with the exact feature weights you'd use, why you chose them, and the data feed each feature requires. Also state at what score you'd refuse to enter the trade (the floor)."

**Why we're asking:** to harvest each model's belief about the right per-class scoring objective and convert the highest-agreement formulas into a `score_v3` candidate for `alpha_engine/score_pick.py`. Currently smart_picks uses a class-agnostic composite; we suspect per-class formulas would lift WR/PF meaningfully (especially on FOREX which is sub-floor — see CLAUDE.md Goal #1 status).

### Claude Opus 4.7 — proposed answer (first respondent)

Each class gets a **0–100 sub-score** that's mapped to 1–10 via deciles (≥90 = 10, ≥80 = 9, …). The features and weights:

**EQUITY** (target Tier 2: PF>1.5 / WR>50%)
| Feature | Weight | Data feed |
|---|---|---|
| Momentum (12-1 mo return, sector-relative) | 25% | yfinance |
| Quality (ROIC ttm, debt/equity) | 20% | SimFin / SEC EDGAR |
| Earnings revision delta 30d | 15% | Zacks API or yfinance.recommendations |
| Realized-vol regime (1mo < 12mo median) | 15% | yfinance |
| Insider buying 90d (% of float) | 10% | OpenInsider scrape |
| Liquidity (ADV > $50M) | 10% | yfinance |
| Catalyst proximity (earnings within 21d) | 5% | yfinance.calendar |

**Floor: refuse < 4/10.** Rationale: project data shows EQUITY all-time PF 1.92 — protecting that against the recent n=33 WR 33% degradation needs the momentum × quality combo + regime tag.

**ETF** (current borderline T2 — n=87, push to 100)
| Feature | Weight | Data feed |
|---|---|---|
| Trend (price > 50dma > 200dma) | 30% | yfinance |
| Cross-asset breadth confirmation | 20% | yfinance (constituent breadth) |
| Flow proxy (volume z-score 5d vs 60d) | 20% | yfinance |
| Sector momentum rank (top decile) | 15% | computed |
| VIX regime (<22 = risk-on) | 15% | ^VIX |

**Floor: < 4/10.** ETFs are beta-dominated — trend + flow + regime is the high-Sharpe recipe.

**CRYPTO** (sub-T2; needs concentration cut)
| Feature | Weight | Data feed |
|---|---|---|
| Funding-rate regime (-0.01% to 0.05% favorable for long) | 25% | Binance / Bybit funding API |
| Spot volume z-score 7d | 20% | Binance API (+ CoinGecko fallback) |
| Whale-tx 10k+ count 24h vs 30d median | 15% | on-chain (Glassnode free tier / Whale Alert) |
| Open-interest delta 24h | 15% | Binance OI |
| ATR-normalised distance from 20dma (mean-rev signal) | 15% | computed |
| RSI(14) NOT in 70-85 (avoid exhaustion zone) | 10% | computed |

**Floor: < 5/10** (crypto needs a higher bar because slippage + funding eats edge). Targets the `quan_engine 18% volume @ PF 0.70` problem — funding + whale gates are the historically validated screens.

**FOREX** (sub-floor PF 0.27 — mutate-before-kill mandatory)
| Feature | Weight | Data feed |
|---|---|---|
| Interest-rate differential (carry, 2Y spread) | 30% | FRED |
| DXY trend regime (50dma slope) | 20% | yfinance ^DXY |
| Commitments of Traders — small-spec extreme (contrarian) | 20% | CFTC weekly |
| Realized-vol regime (low-vol = carry, high-vol = trend) | 15% | yfinance |
| News-event proximity (CPI / NFP / FOMC within 48h → skip) | 15% | FRED calendar |

**Floor: < 6/10** (the highest floor — FOREX requires high conviction to overcome 1-2 pip spreads compounding). This is the Tier-2 rescue plan: pivot off pure technical to **carry + COT + macro-event** as the spine, in line with `docs/MUTATION_THREE_AXIS_PROTOCOL.md`.

**COMMODITY** (close to T2: PF 1.78 / WR 46.9%, lift WR)
| Feature | Weight | Data feed |
|---|---|---|
| Term-structure (contango vs backwardation, slope) | 25% | CME / Nasdaq Data Link |
| COT commercials net positioning | 20% | CFTC |
| Inventory delta (oil EIA / gold COMEX / nat-gas EIA) | 20% | EIA / COMEX |
| Seasonal pattern (calendar bias z-score) | 15% | computed historical |
| USD inverse (DXY trend negative = commodity tailwind) | 10% | yfinance |
| Geopolitical-tension news tag | 10% | RSS scrape (OilPrice/Reuters) |

**Floor: < 5/10.** COT + inventory is the proven hedge-fund recipe (Bridgewater, multi-strat commodity pods).

**BOND** (T2 PF+WR but n=18 — needs scale)
| Feature | Weight | Data feed |
|---|---|---|
| Yield-curve slope (10Y-2Y) regime | 30% | FRED |
| Real-yield regime (10Y TIPS) | 25% | FRED |
| TSMOM signal (12mo momentum on ^TNX) | 20% | yfinance |
| Fed-funds path expectation vs market (CME FedWatch) | 15% | CME FedWatch |
| Inflation surprise index | 10% | FRED CPI YoY surprise |

**Floor: < 5/10.** Bonds are macro-pure — the regime features ARE the signal.

**FUTURES** (broad — applies the relevant per-class formula above, weighted)
| Feature | Weight | Data feed |
|---|---|---|
| Underlying class score (EQUITY/COMMODITY formula) | 50% | computed |
| Roll-yield (front-month vs next) | 20% | CME |
| COT non-commercials extreme | 15% | CFTC |
| OI trend (5d delta) | 15% | CME |

**Floor: < 5/10.**

**PENNY** (highest dispersion — strictest gate)
| Feature | Weight | Data feed |
|---|---|---|
| Short-interest % of float (squeeze fuel) | 25% | Finra / Fintel |
| Recent earnings beat × revenue growth > 25% | 20% | yfinance |
| Volume spike z-score 5d vs 60d | 20% | yfinance |
| Float < 50M (squeeze ceiling) | 15% | yfinance |
| Insider buying 30d | 10% | OpenInsider |
| News catalyst tag (FDA / contract / partnership) | 10% | RSS |

**Floor: < 7/10** (highest — most picks must be rejected; survivor edge is huge).

### Implementation path

1. Add the question above as a system-prompt addendum in the next AI-tournament pipeline run (`tools/ai_tournament/generate_picks_fleet.py` → inject before per-class persona prompt).
2. Each model's answer captured in a new submission file `data/ai_tournament/tier_algorithms/<model>_<date>.json` (schema: `{ model_id, asset_class, formula: [{feature, weight, data_feed, why}], floor }`).
3. Cross-model consensus extracted via majority-weight per feature → seeds `alpha_engine/score_v3.py` (new file, opt-in sidecar per the Wire-Up Rule with a documented production caller target).
4. Run on existing closed picks; compare WR/PF lift vs current `score_pick.py` per class. Promote only classes where lift is statistically significant (n>=100, paired bootstrap p<0.05).

### Next step

Queue the question for grok3, qwen3_6_max, deepseek_v4, cerebras_llama4, cursor_agent, ring_261T, gemini_2_5_pro, mercury_v2 in the next pipeline run. Append each model's verbatim answer to this entry (or a follow-up entry).


---

## 2026-05-25 03:00 UTC — Tier-rating algorithm: cross-model responses

Ran the question through tools/swarm/swarm_run.py against deepseek + cerebras + gemini in parallel. Cerebras returned non-JSON (worker error). Two valid responses below — see full files in `swarm_runs/tier_rating_20260525T025721Z/`.

### deepseek (deepseek-chat, 29s)

```json
{
  "model_id": "alpha_engine_v3_candidate",
  "answered_at": "2025-04-09T14:30:00Z",
  "asset_classes": {
    "EQUITY": {
      "features": [
        {
          "name": "earnings_surprise_zscore",
          "weight": 30,
          "data_feed": "yfinance earnings calendar + IBKR fundamental data",
          "why": "Forward-looking earnings beats drive 70% of short-term price discovery in liquid equities"
        },
        {
          "name": "institutional_flow_ratio",
          "weight": 25,
          "data_feed": "NASDAQ TotalView ITCH + FINRA ATS data via Polygon.io",
          "why": "Dark pool volume / total volume > 0.35 signals smart money accumulation"
        },
        {
          "name": "short_interest_days_to_cover",
          "weight": 20,
          "data_feed": "FINRA short interest file (biweekly)",
          "why": "Days-to-cover > 5 creates gamma squeeze potential on positive catalyst"
        },
        {
          "name": "relative_strength_20d_vs_spy",
          "weight": 15,
          "data_feed": "yfinance adjusted close",
          "why": "Momentum persistence over 20 days predicts next-week continuation 62% of time"
        },
        {
          "name": "implied_volatility_percentile",
          "weight": 10,
          "data_feed": "yfinance options chain (30-day IV)",
          "why": "IV < 20th percentile signals undervalued optionality; IV > 80th signals froth"
        }
      ],
      "floor": 4,
      "signature_insight": "Most systems overweight P/E ratios for equities, but in the current regime of earnings dispersion, the earnings surprise z-score relative to whisper numbers is 3x more predictive than trailing multiples."
    },
    "ETF": {
      "features": [
        {
          "name": "premium_discount_zscore",
          "weight": 35,
          "data_feed": "yfinance NAV + market price (1-min bars)",
          "why": "Persistent >1% premium signals retail euphoria; discount signals liquidation pressure"
        },
        {
          "name": "creation_redemption_flow",
          "weight": 30,
          "data_feed": "Bloomberg AP flow data via ETF Global",
          "why": "Net creations > 0.5% of AUM in a week predicts 2-week outperformance"
        },
        {
          "name": "sector_concentration_herfindahl",
          "weight": 20,
          "data_feed": "yfinance holdings breakdown (top 10)",
          "why": "HHI > 2500 means the ETF is a single-sector bet, not a diversifier"
        },
        {
          "name": "bid_ask_spread_bps",
          "weight": 15,
          "data_feed": "yfinance intraday quote data",
          "why": "Spread > 50 bps on a $50 ETF signals structural illiquidity that erodes returns"
        }
      ],
      "floor": 3,
      "signature_insight": "Rating systems treat ETFs like stocks, but the primary driver is the creation/redemption mechanism - a premium >2% with low creations is a short signal, not a buy signal."
    },
    "CRYPTO": {
      "features": [
        {
          "name": "funding_rate_8h_ema",
          "weight": 35,
          "data_feed": "Binance futures API (perpetual funding rate)",
          "why": "Sustained funding > 0.05% predicts 72-hour mean reversion with 68% accuracy"
        },
        {
          "name": "exchange_netflow_24h",
          "weight": 25,
          "data_feed": "Glassnode exchange flow data",
          "why": "Net outflow > 1% of circulating supply signals accumulation; inflow > 2% signals distribution"
        },
        {
          "name": "stablecoin_dominance_change",
          "weight": 20,
          "data_feed": "CoinGecko stablecoin market cap data",
          "why": "USDT.D + USDC.D rising > 0.5% in 24h predicts altcoin underperformance"
        },
        {
          "name": "onchain_active_addresses_7d_ma",
          "weight": 15,
          "data_feed": "CoinMetrics network data",
          "why": "Active addresses declining while price rising is a bearish divergence with 80% hit rate"
        },
        {
          "name": "open_interest_change_24h",
          "weight": 5,
          "data_feed": "Coinglass OI data",
          "why": "OI up > 20% with flat price signals impending liquidation cascade"
        }
      ],
      "floor": 5,
      "signature_insight": "The biggest mistake is using 24h volume as a signal - it's easily wash-traded. Funding rate and exchange flows are the only honest signals in crypto."
    },
    "FOREX": {
      "features": [
        {
          "name": "carry_trade_differential_3m",
          "weight": 30,
          "data_feed": "FRED (DFII10 for USD, respective central bank rates via Bloomberg)",
          "why": "Interest rate differentials explain 60% of medium-term FX moves in G10 pairs"
        },
        {
          "name": "cftc_net_speculative_positioning_zscore",
          "weight": 25,
          "data_feed": "CFTC COT report (legacy format, net non-commercial positions)",
          "why": "Extreme positioning (>2 std dev) predicts 2-week reversals with 72% accuracy"
        },
        {
          "name": "purchasing_power_parity_deviation",
          "weight": 20,
          "data_feed": "OECD CPI data + FRED real exchange rate indices",
          "why": "PPP deviation > 20% is a mean-reversion signal over 3-6 months"
        },
        {
          "name": "volatility_regime_switch_indicator",
          "weight": 15,
          "data_feed": "yfinance EUR/USD 1-month ATM IV",
          "why": "IV > 12% signals regime switch; trend-following fails, mean-reversion works"
        },
        {
          "name": "central_bank_hawkishness_score",
          "weight": 10,
          "data_feed": "Bloomberg central bank sentiment index (proprietary NLP)",
          "why": "Hawkish surprise in minutes moves rates 50% more than data releases"
        }
      ],
      "floor": 4,
      "signature_insight": "Most systems ignore the CFTC COT report for FX, but net speculative positioning is the single most predictive feature - when 90% of specs are long, the top is in."
    },
    "COMMODITY": {
      "features": [
        {
          "name": "eia_inventory_surprise",
          "weight": 35,
          "data_feed": "EIA Weekly Petroleum Status Report (crude + products)",
          "why": "Inventory surprise > 2 std dev moves crude 3% intraday with 80% directional accuracy"
        },
        {
          "name": "cftc_producer_hedging_ratio",
          "weight": 25,
          "data_feed": "CFTC COT report (commercial long/short ratio)",
          "why": "Producers hedging > 80% of production signals price top; under-hedging signals bottom"
        },
        {
          "name": "contango_backwardation_structure",
          "weight": 20,
          "data_feed": "CME futures curve (front vs 12-month)",
          "why": "Backwardation > 5% predicts spot outperformance over next month"
        },
        {
          "name": "usd_index_correlation_30d",
          "weight": 15,
          "data_feed": "FRED (DTWEXBGS) + yfinance commodity ETF",
          "why": "Dollar correlation > -0.8 means commodity is a pure dollar play; < -0.3 means supply-driven"
        },
        {
          "name": "global_pmi_trend",
          "weight": 5,
          "data_feed": "S&P Global PMI (manufacturing, via FRED or Bloomberg)",
          "why": "PMI > 50 rising adds 2% tailwind to industrial commodities"
        }
      ],
      "floor": 4,
      "signature_insight": "Rating systems use spot price momentum, but the futures curve structure (contango/backwardation) is 2x more predictive - backwardation is a physical shortage signal."
    },
    "BOND": {
      "features": [
        {
          "name": "yield_curve_slope_2y10y",
          "weight": 35,
          "data_feed": "FRED (DGS2 + DGS10)",
          "why": "Steepening > 50bp predicts risk-on rotation; inversion deepening predicts recession"
        },
        {
          "name": "fed_funds_futures_implied_rate_change",
          "weight": 30,
          "data_feed": "CME FedWatch Tool (30-day Fed Funds futures)",
          "why": "Probability of 25bp hike/cut > 70% moves 2-year yields 10bp same day"
        },
        {
          "name": "breakeven_inflation_rate_5y5y",
          "weight": 20,
          "data_feed": "FRED (T5YIE + T10YIE)",
          "why": "Breakeven > 2.5% signals inflation panic; < 1.5% signals deflation risk"
        },
        {
          "name": "corporate_spread_oas",
          "weight": 15,
          "data_feed": "FRED (BAMLC0A0CM for IG, BAMLH0A0HYM for HY)",
          "why": "HY spread widening > 100bp in a week predicts 10-year yield drop of 20bp"
        }
      ],
      "floor": 3,
      "signature_insight": "The biggest mistake is treating bonds as 'safe' - the yield curve slope is the only thing that matters for direction; duration is a trap in steepening regimes."
    },
    "FUTURES": {
      "features": [
        {
          "name": "cftc_managed_money_long_short_ratio",
          "weight": 35,
          "data_feed": "CFTC COT report (managed money category)",
          "why": "Managed money net long > 80% of open interest is a contrarian top signal"
        },
        {
          "name": "roll_yield_annualized",
          "weight": 30,
          "data_feed": "CME futures curve (front vs deferred)",
          "why": "Positive roll yield > 10% annualized is a structural carry trade signal"
        },
        {
          "name": "volume_open_interest_divergence",
          "weight": 20,
          "data_feed": "CME daily volume + open interest data",
          "why": "Volume up 50% with OI flat signals liquidation; OI up with volume flat signals accumulation"
        },
        {
          "name": "basis_to_spot_deviation",
          "weight": 15,
          "data_feed": "yfinance spot vs futures price",
          "why": "Basis > 2% signals arbitrage opportunity; basis < -2% signals backwardation squeeze"
        }
      ],
      "floor": 4,
      "signature_insight": "Most systems ignore roll yield - but in futures, the carry (positive or negative) determines 80% of total return over a quarter."
    },
    "PENNY": {
      "features": [
        {
          "name": "insider_buying_dollar_value",
          "weight": 40,
          "data_feed": "SEC EDGAR Form 4 filings via SEC API",
          "why": "Insider buying > $100k in a month predicts 50% upside with 65% accuracy"
        },
        {
          "name": "reverse_merger_rumor_score",
          "weight": 25,
          "data_feed": "OTC Markets news feed + SEC 8-K filings",
          "why": "Reverse merger announcements drive 200%+ moves; pre-announcement volume spike is predictive"
        },
        {
          "name": "bid_ask_spread_percent",
          "weight": 20,
          "data_feed": "yfinance quote data (1-min bars)",
          "why": "Spread > 10% means you lose 10% on entry; only tradeable if spread < 5%"
        },
        {
          "name": "outstanding_shares_change_30d",
          "weight": 15,
          "data_feed": "OTC Markets share structure data",
          "why": "Share count up > 20% in 30 days signals toxic dilution; down > 10% signals buyback"
        }
      ],
      "floor": 6,
      "signature_insight": "The single biggest mistake is using technical analysis on penny stocks - they're too illiquid. Insider buying and share structure changes are the only reliable signals."
    }
  },
  "engine": "deepseek",
  "_swarm_meta": {
    "raw_path": "swarm_runs/tier_rating_20260525T025721Z/deepseek.json.raw.txt",
    "engine": "deepseek",
    "ts": "20260525T025750Z",
    "session_id": "",
    "model_fingerprint": "deepseek-v4-flash",
    "tokens_in": 643,
    "tokens_out": 2744,
    "transport_status": "200",
    "retry_count": 0
  }
}
```

### gemini (gemini-exp-1206-cli, 66s)

```json
{
  "model_id": "gemini-exp-1206-cli",
  "answered_at": "2026-05-25T00:00:00Z",
  "asset_classes": {
    "EQUITY": {
      "features": [
        {
          "name": "Earnings Revision Momentum",
          "weight": 30,
          "data_feed": "Zacks / IEX Cloud",
          "why": "Captures institutional repricing and analyst sentiment shifts ahead of actual price action."
        },
        {
          "name": "Relative Strength vs SPY",
          "weight": 25,
          "data_feed": "yfinance",
          "why": "Confirms idiosyncratic alpha generation rather than just riding a beta-driven market float."
        },
        {
          "name": "Free Cash Flow Yield",
          "weight": 20,
          "data_feed": "Edgar / Financial Modeling Prep",
          "why": "Provides a hard fundamental downside floor against multiple contraction in tightening regimes."
        },
        {
          "name": "Options Put/Call Volatility Skew",
          "weight": 15,
          "data_feed": "Polygon.io / CBOE",
          "why": "Reveals hidden smart-money hedging activity and expected tail-risk direction."
        },
        {
          "name": "Insider Buying Breadth",
          "weight": 10,
          "data_feed": "SEC Form 4 / Finviz",
          "why": "Signals asymmetric, high-conviction accumulation from those with perfect internal information."
        }
      ],
      "floor": 6,
      "signature_insight": "Relying purely on backward-looking P/E ratios instead of forward earnings revision momentum inevitably traps systems in value traps."
    },
    "ETF": {
      "features": [
        {
          "name": "Net Inflow/Outflow Velocity",
          "weight": 30,
          "data_feed": "ETF Global / Bloomberg",
          "why": "Tracks the mechanical creation/redemption pressure directly driving the underlying basket of assets."
        },
        {
          "name": "Sector Relative VIX",
          "weight": 25,
          "data_feed": "CBOE / yfinance",
          "why": "Avoids allocating to sectors experiencing stealth volatility expansion before absolute price breaks."
        },
        {
          "name": "Premium/Discount to NAV",
          "weight": 20,
          "data_feed": "IEX Cloud / yfinance",
          "why": "Exploits structural arbitrage gaps and extreme retail sentiment before market makers close them."
        },
        {
          "name": "Macro Trend Alignment (200 SMA)",
          "weight": 15,
          "data_feed": "yfinance",
          "why": "Prevents catching falling knives during systemic macro-regime shifts across entire sectors."
        },
        {
          "name": "Dividend Yield vs Risk-Free Rate",
          "weight": 10,
          "data_feed": "FRED (DGS10) / yfinance",
          "why": "Measures the baseline yield-seeker demand floor for income-focused ETF products."
        }
      ],
      "floor": 5,
      "signature_insight": "Treating ETFs like single stocks ignores the mechanical reality of AP creation/redemption flows that override pure price technicals."
    },
    "CRYPTO": {
      "features": [
        {
          "name": "Perp Funding Rate Delta",
          "weight": 35,
          "data_feed": "Binance / Bybit API",
          "why": "Flags heavily overcrowded leverage ripe for engineered liquidation cascades."
        },
        {
          "name": "On-Chain Active Addresses",
          "weight": 25,
          "data_feed": "Glassnode / CryptoQuant",
          "why": "Validates whether speculative price rallies are supported by actual network utilization and adoption."
        },
        {
          "name": "Exchange Net Position Change",
          "weight": 20,
          "data_feed": "CryptoQuant",
          "why": "Detects institutional/whale accumulation or distribution before it impacts the spot order books."
        },
        {
          "name": "Social Dominance Sentiment",
          "weight": 15,
          "data_feed": "LunarCrush",
          "why": "Captures the retail herd momentum that predictably drives terminal blow-off tops."
        },
        {
          "name": "Moving Average Ribbon (4h)",
          "weight": 5,
          "data_feed": "Binance Spot API",
          "why": "Provides a baseline localized trend context to filter out counter-trend chop."
        }
      ],
      "floor": 7,
      "signature_insight": "Ignoring derivative funding rates is fatal; crypto price action is heavily dictated by leverage liquidations, not just organic spot demand."
    },
    "FOREX": {
      "features": [
        {
          "name": "Real Interest Rate Differential",
          "weight": 35,
          "data_feed": "FRED / Central Bank APIs",
          "why": "Acts as the primary gravitational pull for massive, sustained institutional capital flows."
        },
        {
          "name": "COT Non-Commercial Net Positioning",
          "weight": 25,
          "data_feed": "CFTC COT Report",
          "why": "Tracks speculative extremes to identify crowded trades ripe for vicious mean reversion."
        },
        {
          "name": "Sovereign CDS Spreads",
          "weight": 20,
          "data_feed": "Bloomberg / Refinitiv",
          "why": "Serves as an early warning system for hidden geopolitical tail-risks or debt crises."
        },
        {
          "name": "Terms of Trade Index Momentum",
          "weight": 10,
          "data_feed": "World Bank / OECD",
          "why": "Anchors long-term currency valuation to the structural realities of a country's export/import balance."
        },
        {
          "name": "RSI Divergence (Daily)",
          "weight": 10,
          "data_feed": "OANDA API",
          "why": "Times the exhaustion points of overextended, multi-month macro currency trends."
        }
      ],
      "floor": 7,
      "signature_insight": "Applying pure equity-style TA fails because FX pairs are relative liquidity ratios driven by central bank divergence, not corporate cash flows."
    },
    "COMMODITY": {
      "features": [
        {
          "name": "Roll Yield / Curve Structure",
          "weight": 35,
          "data_feed": "CME Group API",
          "why": "Backwardation implies immediate physical scarcity, driving spot prices up and creating positive roll yield."
        },
        {
          "name": "Commercial Hedger Positioning",
          "weight": 25,
          "data_feed": "CFTC COT Report",
          "why": "Tracks the 'smart money' that actually produces or consumes the physical asset in the real economy."
        },
        {
          "name": "Global Inventory Drawdowns",
          "weight": 20,
          "data_feed": "EIA (Energy) / USDA (Agri)",
          "why": "Confirms fundamental, structural supply-demand imbalances outside of speculative paper trading."
        },
        {
          "name": "US Dollar Inverse Correlation",
          "weight": 10,
          "data_feed": "yfinance (DXY)",
          "why": "Accounts for the mechanical denominator effect since global commodities are priced in USD."
        },
        {
          "name": "Historical Seasonality Win-Rate",
          "weight": 10,
          "data_feed": "Moore Research Center",
          "why": "Respects the intrinsic, unavoidable harvest and consumption cycles of physical goods."
        }
      ],
      "floor": 6,
      "signature_insight": "Trading commodities without analyzing the futures curve guarantees bleeding capital to negative roll yield in contango markets."
    },
    "BOND": {
      "features": [
        {
          "name": "Yield Curve Slope (2Y/10Y)",
          "weight": 35,
          "data_feed": "FRED (T10Y2Y)",
          "why": "Dictates duration risk premium and signals broader economic regime shifts (recession vs expansion)."
        },
        {
          "name": "Breakeven Inflation Momentum",
          "weight": 25,
          "data_feed": "FRED (T5YIE)",
          "why": "Separates nominal yield changes from real yield drivers, critical for inflation-adjusted purchasing power."
        },
        {
          "name": "Central Bank Balance Sheet Velocity",
          "weight": 20,
          "data_feed": "FRED (WALCL)",
          "why": "Tracks the sheer, brute-force liquidity that either crushes or lifts aggregate bond prices."
        },
        {
          "name": "Credit Spread (BAA vs 10Y)",
          "weight": 15,
          "data_feed": "FRED (BAA10Y)",
          "why": "Measures systemic risk appetite and default probabilities spilling over into safe-haven treasuries."
        },
        {
          "name": "Term Premium",
          "weight": 5,
          "data_feed": "NY Fed (Adrian-Crump-Moench)",
          "why": "Captures the shifting excess compensation investors demand for bearing long-term interest rate risk."
        }
      ],
      "floor": 5,
      "signature_insight": "Equating high yield with high quality traps systems in duration risk; bonds must be modeled as macro liquidity derivatives, not isolated assets."
    },
    "FUTURES": {
      "features": [
        {
          "name": "Volume Profile / VWAP Deviations",
          "weight": 30,
          "data_feed": "CME Group API / Sierra Chart",
          "why": "Pinpoints hidden institutional liquidity resting levels and value areas untouched by standard time-based charts."
        },
        {
          "name": "Order Book Imbalance (Level 2)",
          "weight": 25,
          "data_feed": "CME Globex Level 2",
          "why": "Catches micro-structure directional pressure milliseconds before it translates into price movement."
        },
        {
          "name": "Open Interest Delta",
          "weight": 20,
          "data_feed": "CME Group API",
          "why": "Confirms whether a price spike is driven by aggressive new money entering or just trapped shorts covering."
        },
        {
          "name": "Cross-Asset Beta Arbitrage",
          "weight": 15,
          "data_feed": "yfinance (NQ vs DXY/TNX)",
          "why": "Measures systemic algorithmic arbitrage flows that drag index futures regardless of localized technicals."
        },
        {
          "name": "Session Pivot Point Confluence",
          "weight": 10,
          "data_feed": "Local algorithm calculation",
          "why": "Respects algorithmic and psychological boundaries that dictate intraday mean-reversion zones."
        }
      ],
      "floor": 7,
      "signature_insight": "Trading index futures based on daily chart patterns ignores that intraday movement is entirely dominated by algorithmic liquidity seeking and order book microstructure."
    },
    "PENNY": {
      "features": [
        {
          "name": "Relative Volume (RVOL)",
          "weight": 40,
          "data_feed": "Polygon.io / Finviz",
          "why": "Illiquid micro-caps only move when extreme, abnormal retail or chatroom volume violently enters the order book."
        },
        {
          "name": "Float vs Short Interest",
          "weight": 25,
          "data_feed": "Ortex / FINRA",
          "why": "Identifies highly constrained supply structures that are mathematically ripe for parabolic short squeezes."
        },
        {
          "name": "SEC Filing Catalysts",
          "weight": 15,
          "data_feed": "Edgar API",
          "why": "Distinguishes legitimate fundamental catalyst pumps (FDA approvals, contracts) from baseless manipulation."
        },
        {
          "name": "Dilution Risk (Shelf/Warrants)",
          "weight": 10,
          "data_feed": "BamSEC / Edgar API",
          "why": "Acts as a hard veto to avoid buying right before a toxic financing vehicle dumps newly printed shares on retail."
        },
        {
          "name": "VWAP Reclaim (1m/5m)",
          "weight": 10,
          "data_feed": "Polygon.io",
          "why": "Proves intraday momentum buyers have successfully absorbed and overwhelmed the morning short-sellers."
        }
      ],
      "floor": 8,
      "signature_insight": "Applying standard fundamental valuations to penny stocks is a death sentence; they are strictly instruments of liquidity, float dynamics, and catalyst momentum."
    }
  },
  "engine": "gemini",
  "_swarm_meta": {
    "raw_path": "swarm_runs/tier_rating_20260525T025721Z/gemini.json.raw.txt",
    "engine": "gemini",
    "ts": "20260525T025828Z",
    "session_id": "",
    "model_fingerprint": "",
    "tokens_in": 0,
    "tokens_out": 0,
    "transport_status": "ok",
    "retry_count": 0
  }
}
```

### Next step

Run a consensus extractor (TODO: tools/ai_tournament/consensus_tier_algorithm.py): for each (asset_class, feature_concept) tuple, take the median weight across models that included it (Claude/Deepseek/Gemini so far); features with >=2-model consensus go into `alpha_engine/score_v3.py` (opt-in sidecar per Wire-Up Rule, with a documented production-caller target). Pending: cursor_agent, grok3, ring_261T, qwen3_6_max, mercury_v2, nemotron3_super responses — to queue, append this prompt to their next pipeline run.

### deepseek-cli (additional response, captured 03:05 UTC via Kilo session)

Note: this is a second deepseek response in prose form (not strict JSON), distinct from the structured deepseek answer in the swarm run above. Format: per-class factor list with weights summing to 100, z-score/percentile normalization, piecewise linear map to 1-10.

| Asset | Core factors (weight %) | Normalization |
|---|---|---|
| **EQUITY** | ROE 20 · Debt/EBITDA 15 · FCF yield 15 · 12mo momentum 15 · RSI(14) 10 · earnings surprise 10 · insider buying 5 · sector RS 10 | z-score vs peer group, clip [-2,2], rescale 0-100 |
| **ETF** | 4wk net flow %AUM 25 · 12wk total return 20 · expense ratio (inv) 10 · holdings HHI (inv) 10 · tracking error (inv) 10 · factor exposure fit 15 · ADV 10 | same |
| **BOND** | YTW vs benchmark 20 · duration-adjusted spread 15 · credit rating numeric 15 · interest coverage 10 · debt/EBITDA 10 · real-yield + breakeven fit 15 · bid-ask (inv) 10 | percentile in universe |
| **COMMODITY** | 3mo spot momentum 20 · roll-yield (backwardation) 15 · inventory vs 5yr avg 15 · demand-shock idx (PMI/construction) 15 · supply-shock idx (rig count/OPEC) 10 · realised vol (inv) 10 · USD correlation (inv) 5 | percentile |
| **FOREX** | Carry differential 20 · REER deviation (PPP) 15 · 12wk momentum 15 · 25-delta RR carry skew 10 · CA balance %GDP 10 · TOT for commodity-linked 10 · ADV 10 | percentile |
| **CRYPTO** | Active addresses 3mo Δ 15 · GitHub commits 15 · MVRV z-score 15 · 90d momentum 15 · 24h vol/mcap 10 · regulatory risk (inv) 10 · risk-on correlation (inv) 10 | percentile |

**Implementation pipeline (deepseek):** weekly cron → pull factor data → percentile/z-score within peer group → weighted sum → map 0-100 to 1-10 via deciles → Tier 9-10 = Buy, 7-8 = Hold, ≤6 = Review/Reduce. **No CRYPTO/FOREX floor specified** (gap vs Claude's answer which had explicit floors at 5/10 and 6/10).

---

## 2026-05-25 03:15 UTC — Prompt provenance + Ring-2.6-1T (opencode) integration

### The 4 canonical prompts sent to the AI tournament fleet this session

For reproducibility — these are the *exact* prompts the user sent to every model (Mercury V2, Grok-3, Qwen3.6-flash, Nemotron 3 Super, Ring-2.6-1T, deepseek, gemini, cerebras, claude_opus_4_7). Save these verbatim and use them on every future round so cross-model answers are apples-to-apples.

**Prompt 1 — hedge-fund personas + per-asset-class picks:**
> "Give me a list of personas that could similar to ones a hedge fund would use, then act as each persona, and come up with the top picks per asset class for ETFs / stocks for picks based on the latest market data and come up with a list of picks including TP/PL, entry reason"
>
> (immediately followed by `/dropchat-multipc` so peer agents see the output)

**Prompt 2 — expand into a database-ready spec per model+persona+pick:**
> "expand your results given with the following: Your Provider-Model (Qwen — … model?) + prompt given + your ideal trading style for each asset class, and a specific rationale for each pick, and your strategy, how long to hold it? what TP/SL? what was the pick based on? a guess? how many symbols did they check? what did you research? Also survey the personas you used ask them how we can improve their picks, what data points do they need? other stats? etc"

**Prompt 3 — tier-rating algorithm per asset class:**
> "furthermore if you were challenged to give a pick rating system to create a tier list of symbols on a scale of 1-10 per asset class, what algorithm would you use for each asset class?"

**Prompt 4 — prompt provenance (this entry):**
> "save these prompts appending them to our DAILY_IDEAS.MD and commit that to github."

These 4 prompts now feed directly into the new DB schema (committed 2026-05-25 03:10 UTC):
- Prompt text → `tournament_prompts.system_prompt` / `user_prompt`
- Prompt 2 self-survey output → `tournament_pick_research.symbols_screened` + `sources_jsonl` + `research_basis` + `self_audit_response`
- Prompt 3 output → `tournament_rating_algorithms.features` JSON + `floor_score` + `signature_insight`

### Ring-2.6-1T (via OpenRouter / opencode) — playbook ingested

Source: `hedge_fund_persona_playbook_v2.md` (570 lines, 2026-05-25). 8 personas (Macro Strategist · Quant/StatArb · Event-Driven · CTA/Trend · Value · Risk Parity · Vol Trader · Crypto-Native). Top picks across all classes: NVDA 9.4 · AAPL 9.1 · QQQ 9.2 · BTC 9.1 · GLD 7.8.

**Tier-rating algorithms now seeded in `tournament_rating_algorithms` (5 rows for ring_261T):**

| Asset | Top weight | Floor | Signature insight |
|---|---|---|---|
| EQUITY | Quality 25% | 5/10 | Quality dominates over momentum (20%) — contrarian to most retail screens |
| ETF | Trend 25% + MacroAlign 25% (tied) | 5/10 | Macro alignment tied for #1 weight — unusual for ETF systems that lean pure technical |
| CRYPTO | OnChainHealth 30% | 5/10 | MVRV + exchange flows dominate; narrative explicitly weighted (20%) |
| COMMODITY | MacroTrend 30% | 5/10 | Real-rate + geopolitical risk premium as core; seasonality + carry are equal sleeves |
| BOND | MacroTrend 30% | 5/10 | Derived from shared COMMODITY/BOND algo, feature definitions adapted for fixed income |

Self-assessment survey captured under `hedge_fund_persona_playbook_v2.md §4`:
- Edge-decay rates: 3-6mo crypto narratives · 6-12mo quant factors · 12-18mo macro positioning · 24+mo value structural
- Sharpe targets: vol trader 1.5 · quant 1.2 · value 1.1 · macro 1.0
- Missing-data list per persona: dark pool prints (quant), options flow (event-driven), volume profile (CTA), on-chain whale tracking (crypto), customer concentration (value), realised vol decomposition (risk parity), variance swaps (vol trader), credit default swaps (macro)

### Cross-model tier-rating consensus update (3 models with structured answers in DB now: claude_opus_4_7, deepseek, ring_261T)

**EQUITY consensus features (all 3):** momentum, quality/ROIC, earnings/value
**ETF consensus (3/3):** trend, relative strength, liquidity
**CRYPTO consensus (3/3):** on-chain/funding/MVRV, volume, momentum
**FOREX consensus (2/2 of those answering):** rate differential (carry), real/PPP deviation, momentum
**COMMODITY consensus (2/2):** macro/regime, supply-demand (inventories/COT), real rates / USD

Next step: write `tools/ai_tournament/consensus_tier_algorithm.py` to take consensus features with ≥2-model agreement, derive averaged weights, emit seed for `alpha_engine/score_v3.py` (opt-in sidecar per Wire-Up Rule).

---

## 2026-05-25 03:25 UTC — Attribution flag: grok_heavy vs mercury_v2

User re-attributed the 5-persona hedge-fund picks (Voss/Reed/Sharma/Chen/Lang, 20 picks across EQUITY/ETF/COMMODITY) to **Grok HEAVY** (xAI). The same picks were saved earlier this session under `mercury_v2_20260525.json` because the user's initial message attributed them to "Mercury (Inception labs)".

**Both submission files are now on disk** until clarification:
- `data/ai_tournament/submissions/mercury_v2_20260525.json` (original attribution)
- `data/ai_tournament/submissions/grok_heavy_hedgefund_20260525.json` (latest attribution)

This is detectable in `ai_tournament_model_summary.json` — both `mercury_v2` and `grok_heavy` will show the same 5 personas and overlapping symbol set. Once the user confirms which model actually generated these, the wrong one should be deleted (with a note in the next DAILY_IDEAS entry).

**Why this matters:** the AI-tournament leaderboard ranks by model. Double-counting picks under two model_ids inflates `ring_eligible` for one model and silently misses for the other. The next price-tracker run will resolve them under whichever model_id is on disk — picks resolved twice under different model_ids will skew tournament_model_stats.


## 2026-05-25 03:30 UTC — Attribution resolved: it was Grok HEAVY

User confirmed the 5-persona Voss/Reed/Sharma/Chen/Lang hedge-fund picks (20 picks across EQUITY/ETF/COMMODITY) came from **Grok HEAVY (xAI)**, not Mercury V2 (Inception Labs). The mercury_v2_20260525.json file was an attribution error from earlier this session and has been removed. Picks now live only under `grok_heavy_hedgefund_20260525.json` so the price-tracker won't double-resolve. Persona registry entries (`voss_global_macro`, `reed_long_short_fundamental`, `sharma_quant_momentum`, `chen_thematic_ai_growth`, `lang_value_contrarian`) remain as-is in `tools/ai_tournament/persona_registry.py` — they're model-agnostic strategy archetypes, correctly tied to Grok HEAVY going forward.


---

## 2026-05-25 03:50 UTC — Audit UI / Edge / Freshness audit (consolidated)

Two independent audits this hour (Claude Opus 4.7 + Ring-2.6-1T via opencode) converged on the same 7 findings:
1. **HC overlay broken** — trust_score NULL on 99.99% of closed picks; cited "CRYPTO 60.3% N=562 / EQUITY 68.1% N=72" stats unreproducible.
2. **Smart Picks "1.4h ago" is file age, not pick age** — `signal_time` field missing from payload, UI falls back to dashboard-file `age_hours`.
3. **`smart_picks.json` itself is 25 days stale** (last regen 2026-04-30).
4. **Swarm Picks abandoned** — newest pick 13 days old, no new picks flowing despite daily cron.
5. **`signal_outcomes` table 82 days stale** — outcome-resolver pipeline dead.
6. **Top-N Rank Backtest tool broken** ("Access denied" DB connect).
7. **5 FOREX rows have `pnl_pct < -100%`** (one at -106,700%) — unit-clamp bug commit #876 missed them. Distorts FOREX PF to ~0.00.

Full report: [reports/2026-05-25_audit_ui_edge_audit.md](reports/2026-05-25_audit_ui_edge_audit.md). Combined P0 list embedded there.

**Honest profitability verdict (both auditors agree):** real edge is narrow — cot_positioning (DSR=1.0 / n=104 / PF 3.28 = legit) + ML-enhanced crypto LONGs with conf 0.80-0.85 (PF up to 99 but on tiny samples = unreliable). The "82% WR / PF 13" headline cells are post-hoc segment searches, not actionable forward signals. The system should NOT be treated as production-ready in current state. The Smart Picks button's own tooltip is the most accurate sentence on the page: "use it as a live signal overlay, not as a standalone edge filter."


---

## 2026-05-29 — 200-day MA trend strategy tracking + ai_leaderboard "golden finder" + /audit filter deep-dive (prompt captured)

> Start a buy when stock Price above 200 day Simple moving average, sell when price goes below it.
> Start some strategy tracking under https://findtorontoevents.ca/audit/ai_leaderboard.html across each
> asset class based on this simple strategy. Ensure we have at least a few entries and variations of this
> using Hull Moving Average, EMA, and simple moving average.
>
> Try with the daily closing price. If that day's close is above 200 day MA hold, if below sell. You enter
> the next trading day after stock closes above 200 day MA.
>
> Strategy doesn't need a SL/TP — the 200day MA is both an entry/exit rule, acts as a trailing stop, but
> with risk control you can say risk no more than 1% to 2% per trade, and stop loss below a certain price etc.
>
> For variations ask /PeerReviewSwarmOptions, and create a bunch of variations and track their performance.
>
> Under ai_leaderboard.html, we need a way to quickly find out if a particular Model-Persona, or persona
> (if not unique to the model) is highly profitable, so we don't lose a "GOLDEN" opportunity buried in the stats.
>
> We have a TON of filters under /audit — do a deep dive with a bunch of subagents and ask other AIs to also
> help with the analysis. Delegate with as many peers as possible to double-check various parts. Double-check
> for hallucination; make sure these other AIs are REALLY able to check the webpage and/or database to verify
> things (feed them real data extracts — never let a model claim it "fetched" a URL).

**Build notes / acceptance:**
- MA variants to track per asset class: SMA-200, EMA-200, HMA-200 (+ shorter-period variations from peer consult).
- Entry: enter next trading day after daily close > MA; Exit: close < MA. No TP; MA = trailing exit. Risk overlay: 1–2%/trade, hard floor stop.
- Surface results on ai_leaderboard.html; add sortable/highlighted "golden" view (high PF/WR per model-persona).


2025-05-31
If you had a project https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/ with github actions to refresh data. a set of key databases and their credentials , and also AI api keys that can be leveraged to delegate parallel agents
mysql.50webs.com 
/home/eaguiar2015/dbpasses.txt

ejaguiar1_stocks
ejaguiar1_backtests
any database operation that can be destructive, should make a backup to ejaguiar1_backtests

now we have pages findtorontoevents.ca/audit with  text which needs to be automated and have a date/time stamp..|

we have predictions including TP/SL for stocks/crypto/forex/bonds/ETFs/commodities /futures + plans for penny stocks'/IPOs/cheap stocks..

However, even if we back-test , we arent sure how to properly measure future performance, and how many trades would be considered a statistically valid edge? 

How can we determine if a strategy is ready for production?

we also have a ton of filtesr and buttons under findtorontoevents.ca/audit which we try to document the stats on each permutation of filter options/buton clicks into https://findtorontoevents.ca/audit/pick_funnel.html
We also have "verified alpha" tab, and 
We are trying to avoid having some hidden edge.
we have an AI leaderboard https://findtorontoevents.ca/audit/ai_leaderboard.html we try to compare performance against buy & hold, but what sort of Quant/hedge fund manageger sstats would be ideal?

We have a set of personas and picks per asset class, and a portfolio by each AI model fed into 
https://findtorontoevents.ca/audit/ai-tournament.html

overall our main sources of potentially profitable picks would be on 
https://findtorontoevents.ca/audit/ai-tournament.html
OR 
findtorontoevents.ca/audit 

but how can be verify an edge on those pages?
leaderboard looks something like this:

#	Model	Provider	WR	WR 95% CI	PF	Score*	n picks	n resolved	Tier	Status
#1	deepseek_v4	DeepSeek	57.7%	[50.9%, 64.2%]	3.46	1.288	249	208	T1	LIVE
#2	gpt4o	OpenAI	59.7%	[51.2%, 67.6%]	3.14	1.090	223	134	T1	LIVE
#3	deepseek_r1	DeepSeek	62.9%	[54.4%, 70.7%]	2.93	1.028	168	132	T1	LIVE
#4	grok3	xAI	55.8%	[50.1%, 61.3%]	2.29	0.871	369	303	T1	LIVE

it also has model performance
Model Summary — All-Time Performance
[?] ELI5
46 models · 4953 picks · 3692 resolved · refreshed May 31, 08:51 AM EST
Model	Picks	WR	PF	Resolved	W/L	Avg PnL	Last Pick (EST)	Personas	Classes	Drill-down
grok3	369	55.8%	2.29	303	169/134	+2.73%	May 31, 08:37 AM	15	8	View picks →
deepseek_v4	249	57.7%	3.46	208	120/88	+4.23%	May 31, 08:36 AM	10	7	View picks →


There are also risk-managed portfolios, but the automation seems broken!
Model Portfolios — Risk-Managed Books (Model Portfolios — Risk-Managed Books on https://findtorontoevents.ca/audit/ai-tournament.html)
One paper portfolio per (AI-model × risk appetite). Each book runs the model's daily picks through a lifecycle engine (entry/sizing/TP/SL/exit) plus appetite-specific risk caps (gross exposure, per-position weight, drawdown breaker). See docs/DESIGN_AI_MODEL_HEDGE_FUND_PORTFOLIOS_2026-05-29.md.

12 portfolio(s) · refreshed May 29, 06:33 PM EST
All
Conservative
Balanced
Aggressive
Portfolio	Provider	NAV	Total Return	CAGR	Sharpe 30d	Sortino 30d	MaxDD	PF	Gross Exp	#Open	Last Mark (EST)	Drill
cursor_agent__aggressive AGG	—	$100000.00	0.00%	—	—	—	-0.00%	—	159.2%	14	May 28, 08:00 PM	View →
cursor_agent__balanced BAL	—	$100000.00	0.00%	—	—	—	-0.00%	—	42.2%	9	May 28, 08:00 PM	View →
cursor_agent__conservative CONS	—	$100000.00	0.00%	—	—	—	-0.00%	—	11.6%	6	May 28, 08:00 PM	View →
deepseek_v4__aggressive AGG	—	$100002.41	+0.00%	—	—	—	-0.00%	—	158.0%	11	May 28, 08:00 PM	View →

Create a comprehensive plan to get us from "coin flip" or "hidden edge" to actually getting profitable strategies per asset class!

## 2026-06-02 — User prompt append (EAGLE swarm + edge hunt)

```text
sync our project with github, then review all *EAGLE*.MD and run each .MD over the past 72 hours, into an agent swarm for review. Then collectively have them summarized with key insights and strategies, and compare against our current state of strategies/back testing methodologies, stats. Consider methods such as bonneferi, but leverage our AIs with the API keys

The main thing is we are trying to get profitable picks by asset class, and identify where on our website/project has the most profitable picks.
Most likely findtorontoevents.ca/audit or https://findtorontoevents.ca/audit/ai_leaderboard.html https://findtorontoevents.ca/audit/ai-tournament.html https://findtorontoevents.ca/audit/pick_funnel.html

see also our research here:
https://findtorontoevents.ca/audit/research_index.html

Then leverage all working API keys/ models and create a brainstorming of strategies, backtesting, have them feed in against our strategies, the strategies should all be documented by asset class in our database ejaguiar1_stocks, or ejaguiar1_backtests identify where.
DB passes are in the .txt (/home/eaguiar2015/dbpasses.txt)

review /home/eaguiar2015/dbpasses.txt and feel free to leverage our Lite LLM Server
http://localhost:4000/v1 in 20 minutes, test the new modes
ollama-cloud-large
ollama-cloud
ollama-cloud-local

run some testing of the new modes to assist with further brainstorms
review also these:
1. Executive Summary
Core Issue: The production-ready audit book lacks deployable edge. Research-grade edge exists only in isolated tournament or lab sleeves, not in the live, policy-clean layer.
Root Causes: Mismatch between research and production standards, over-broad emitter set, concentration artifacts, and resolver/label contamination.
Goal: Convert verified research edge into stable, capital-ready strategies while tightening data hygiene and validation pipelines.
2. Current State (as of 2026-06-02)
Asset Class Live PF/WR Research Edge Primary Pain Point
CRYPTO < 0.5 PF, high WR Sub-cohort edge in tournament models Selection/gating mismatch, concentration
EQUITY Negative PF, low WR None Weak emitters / failed holdout
ETF Small sample, modest PF Dual-momentum promising Insufficient forward data
FOREX High WR, terrible PF Minor edge Data/resolver errors, mislabeled exits
COMMODITY Too few clean samples N/A Sample size / stability
FUTURES Concentration-driven spikes N/A Artifact risk
BOND No live sample N/A Data gap
Portfolio Health: 81 portfolios (66 active). The deepseek_v4__aggressive portfolio has 11 open names, confirming the issue is not empty but mis-aligned.

3. Key Diagnostic Findings
Inconsistent Validation Standards - Lab uses generous splits; production demands policy-clean, walk-forward proof.
Emitter Over-Breadth - Too many weak emitters dilute real edge.
Concentration Artifacts - Single source dominance inflates surface stats.
Resolver/Label Pollution - Disputed cohorts and TIME_EXIT-type mislabels distort PF/WR.
Insufficient Forward Sampling - ETF and crypto sub-sleeves lack enough forward data for robust promotion.
4. Enhancement Blueprint
4.1. Data & Resolver Hygiene
Action Owner Deadline Success Metric
Audit and purge disputed resolver entries (CRYPTO, FOREX) Data Engineering 2 weeks < 1% disputed tags in live feed
Implement source-provenance tagging for every price/label record Data Engineering 3 weeks 100% records have source_id & fallback fields
Deploy automated duplicate detection on pf_portfolios.json QA 1 week Zero duplicate portfolio IDs
4.2. Validation Pipeline Standardization
Step Description Tooling Acceptance Criteria
Pre-registration Hypothesis must be logged before backtest Internal registry (Git) 100% hypotheses pre-registered
Purged-Embargoed Walk-Forward Use >= 30 day purge + 10 day embargo per fold backtest_engine_v2 Consistent PF/WR across folds (delta <= 0.05)
Cost/Slippage Model Asset-class-specific cost curves applied in every run cost_model_lib Simulated net PF matches live after slippage
Multiple-Testing Correction DSR / PBO / SPA corrections applied stat_corrections Adjusted p-value < 0.05 for promoted sleeves
Block Bootstrap Preserve temporal dependence bootstrap_block Confidence intervals stable across 1000 resamples
Regime Robustness Test across trend/volatility regimes regime_classifier Edge persists in >= 3 of 4 regimes
4.3. Emitter & Strategy Discipline
Emit-Culling - Retain only emitters with OOS PF >= 0.6 and WR >= 0.55 after corrections.
Promotion Gate - Require forward paper evidence (>= 2 months) before any live sizing.
Shadow-Sizing - Deploy new sleeves at <= 0.5% of allocated capital for 4 weeks, monitor live PF/WR.
Gradual Scaling - Increase sizing only after live PF stays within 10% of paper PF for 8 weeks.
4.4. Targeted Edge Development
Candidate Rationale Immediate Action
ETF Dual-Momentum Best lab edge, low concentration Build forward walk-forward, start shadow-size (0.2%)
Crypto VWAP/Bollinger Walk-Forward Promising sub-cohort edge Resolve resolver issues, run mutation tests
DeepSeek_v4 Tournament Portfolio Highest tournament PF Isolate top-performing sleeves, run production-grade validation
GPT-4o & Grok-3 Lab Sleeves Consistent paper edge Conduct regime-robustness checks, schedule for promotion pipeline
4.5. Mutation & Inversion Strategy
Mutation: Apply feature-level perturbations (e.g., alternative volatility filters) on failed but plausible sleeves; retain if PF improves >= 0.05.
Inversion: Use only on sleeves with explicit OOS proof of negative edge; invert signal and re-validate.
4.6. Monitoring & Governance
Metric Frequency Alert Threshold
Live PF Daily < 0.4 for > 5 days
WR Daily > 0.7 with PF < 0.4
Concentration Score (Herfindahl-Hirschman) Weekly > 0.25
Resolver Dispute Rate Weekly > 2%
Regime Drift Monthly Edge shift > 15% across regimes
All metrics feed into a Quant Ops Dashboard (built on Grafana) with automated Slack alerts.

5. Timeline (12-Week Horizon)
Week Milestone
1-2 Data/Resolver audit, duplicate purge
3-4 Deploy standardized validation pipeline; pre-register hypotheses
5-6 Run purged-embargoed walk-forward on ETF dual-momentum & crypto VWAP/Bollinger
7 Shadow-size approved sleeves (ETF, Crypto)
8-9 Mutation testing on failed lab sleeves; evaluate inversion candidates
10 Promote any sleeve meeting live PF/WR gate (>= 0.5 PF, <= 0.6 WR)
11-12 Full-size rollout for successful sleeves; update Quant Ops Dashboard
6. Success Definition (Quarterly Review)
Deployable Edge: At least 2 new capital-ready sleeves with live PF >= 0.5 and WR <= 0.6.
Data Cleanliness: Resolver dispute rate < 1% across all live feeds.
Concentration: HHI for aggregate book < 0.20.
Operational Efficiency: End-to-end validation pipeline latency <= 5 minutes per sleeve.
7. Risks & Mitigations
Risk Likelihood Impact Mitigation
Unexpected resolver drift Medium High (PF collapse) Continuous resolver health checks; fallback to backup source
Over-fitting during mutation Low Medium Strict out-of-sample holdout; block-bootstrap verification
Regulatory policy change Low High Maintain policy-clean flagging; rapid re-validation pipeline
Capital allocation lag Medium Low Pre-approved shadow-size budget; automated scaling scripts
8. Governance & Ownership
Function Lead Primary Deliverable
Data Integrity Data Engineering (Alex Kim) Resolver audit report, duplicate removal script
Backtesting & Validation Quant Research (Dr. Mia Patel) Standardized pipeline, pre-registration logs
Strategy Promotion Portfolio Management (Sam Rossi) Shadow-size schedule, promotion gate checklist
Monitoring Ops (Jenna Lee) Grafana dashboard, alert routing
Risk Oversight CRO (Victor Chen) Quarterly risk review, HHI tracking
Prepared by:
Quant Review Team - EAGLE2 Initiative
Date: 2026-06-02

Copy
Listen
Follow up

Can you provide a detailed example of the standardized validation pipeline steps and code snippets?

What specific metrics and thresholds should we use to monitor concentration and resolver dispute rates in real time?

How can we implement the mutation testing framework for failed lab sleeves, and what tools do you recommend for that?

Overall we are looking for
#1, more strategies per asset class, and a better methodology to ensure we are backtesting effectively for each asset class, and able to quickly get to profitable strategies.
For example, lets say our current picks havent been forward-tested.. but given our current websites/github .. what are the best possible picks, and why?
NVDA? maybe BTCUSD? ... and why? maybe some safe long-term picks that are well-known?

#2 more backtests per asset class.
#3 more research and analysis on any hidden edge within our project
#4 more research regarding on if we have proven statistical edge? do our strategies pass the typical stuff like monte carlo? bonferroni correction, do they pass the statistical methods for "real money" worthy picks?

#5 do research on "if you had a system for prediction of stocks/crypto/forex/bonds/etfs/commodities/futures..

What statistical measures would be most important, to see if the picks are "real money ready", what sort of backtesting is bare minimum, and what would be ideal, and what about forward-testing how many picks?"

#6 look into these:
Statistical measures that separate "real-money-ready" signals from research-only artefacts

Measure Why it matters for production readiness Typical threshold (rule-of-thumb)
Annualized Sharpe Ratio (or Information Ratio vs. benchmark) Captures risk-adjusted return; a high Sharpe that disappears after costs is a red flag. >= 1.0 (Sharpe) or >= 0.8 (IR) after slippage & transaction costs.
Profit-Factor (PF) Ratio of gross profit to gross loss; directly reflects whether the strategy is profitable before scaling. >= 1.5 (bare minimum) -> >= 2.0 (ideal).
Win-Rate (WR) % of winning trades; useful when combined with PF because a high WR with low PF often signals tiny gains offset by large losses. 45-55% is acceptable if PF is strong; > 60% only if PF is modest.
Maximum Drawdown (MDD) & Calmar Ratio Shows tail-risk; production capital cannot tolerate deep, prolonged drawdowns. MDD <= 20% (monthly) or Calmar >= 3.0.
Turnover / Trade-Frequency High turnover inflates costs; must be realistic given market liquidity and execution latency. Turnover <= 30% / yr for equities/ETFs; <= 70% / yr for crypto/FX.
Liquidity-Adjusted Slippage Expected slippage per trade (bps) based on market depth; should be baked into PF. <= 5 bps for large-cap equities/ETFs; <= 15 bps for crypto/FX.
Regime-Robustness Score Consistency of performance across volatility/trend regimes (e.g., low-vol vs. high-vol). Edge (PF, Sharpe) within +/-10% across >= 3 of 4 regimes.
Multiple-Testing- DSR/PBO/SPA) Controls for data-snooping; a "real" edge must survive statistical penalties. Adjusted p-value < 0.05 after correction.
Herfindahl-Hirschman Index (HHI) of Source Concentration Prevents a single model or data source from dominating the book. HHI < 0.20 for the aggregate portfolio.
Out-of-Sample (OOS) Decay Difference between in-sample (IS) and OOS metrics; large decay signals over-fitting. PF OOS >= 80% of IS PF; Sharpe OOS >= 70% of IS Sharpe.
1. Bare-minimum back-testing checklist
Step Description Minimal implementation
a. Data hygiene Use only clean, policy-approved price/label data; remove duplicates and disputed resolver entries. Simple CSV audit + duplicate filter; manual spot-check of disputed tags.
b. Pre-registration Log hypothesis (signal definition, universe, cost assumptions) before any back-test. Text file or internal ticket; timestamped.
c. Split-sample test One simple IS/OOS split (e.g., 70%/30%). Quick train-test split; no purging.
d. Cost & slippage model Apply a flat per-trade cost (e.g., 5 bps) and a basic slippage model proportional to turnover. Flat fee + linear slippage.
e. Basic performance metrics PF, Sharpe, WR, MDD, turnover. Compute with pandas/NumPy.
f. Simple multiple-testing guard Bonferroni correction for the number of tested signals. Adjust p-value = alpha / N.
If a signal fails any of the above (e.g., PF < 1.5, MDD > 30%), it is not ready for capital.

2. Ideal (production-grade) back-testing pipeline
Component Ideal practice Reason
Data provenance Every price/label record carries source_id, fallback, timestamp, and version. Guarantees traceability and easy replacement of bad feeds.
Purged-embargoed walk-forward 30-day purge + 10-day embargo per fold; rolling windows (e.g., 12-month training, 3-month testing). Removes look-ahead bias and leakage from overlapping trades.
Block-bootstrap confidence intervals 1,000 resamples preserving temporal dependence. Provides robust error bars for PF, Sharpe, etc.
Regime-segmented analysis Separate performance for low-vol, high-vol, trending, mean-reverting regimes (identified via a volatility filter). Shows whether edge survives market changes.
Full cost model Asset-class-specific commissions, market impact, latency, and execution-quality penalties. Aligns back-test with real-world P&L.
Multiple-testing correction (DSR/PBO/SPA) Apply Data-Snooping-Robust (DSR) or Probability-of-Back-test-Overfitting (PBO) methods. Controls for data-mining bias.
Shadow-size simulation Run the strategy at a tiny capital allocation (<= 0.5% of total) on live data for 4-8 weeks before any scaling. Early detection of hidden execution or data issues.
Automated monitoring dashboard Real-time metrics (PF, WR, MDD, HHI, resolver dispute rate) with alerts. Enables rapid response to deteriorating performance.
Versioned strategy repository Git-tracked code, config, and hyper-parameters; immutable releases. Guarantees reproducibility and auditability.
3. Forward-testing (live-paper) guidelines
Aspect Recommended practice
Number of picks Minimum 30-50 distinct symbols (or signal instances) per asset class to achieve statistical significance.
Duration At least 2 x the longest look-back window (e.g., if you use a 12-month walk-forward, forward-test for >= 24 months).
Capital allocation Start with <= 0.5% of total portfolio per strategy; monitor live PF/WR for 4-8 weeks before any up-scale.
Performance thresholds Live PF must stay within +/-10% of the back-tested PF; Sharpe within +/-15%.
Regime exposure Ensure the forward test covers at least three distinct market regimes (e.g., low-vol bull, high-vol bear, sideways).
Statistical validation After the forward period, re-run block-bootstrap on the live-paper P&L; the 95% CI for PF should not cross 1.0.
Continuous re-registration Any tweak to the signal after the forward test must be logged as a new hypothesis and re-back-tested.
4. Putting it together - a quick decision flow
Pre-register hypothesis -> Back-test with purged-embargoed walk-forward + full cost model.
Check: PF >= 1.5, Sharpe >= 1.0, MDD <= 20%, HHI < 0.20, OOS decay <= 20%.
If pass, run shadow-size live-paper on >= 30 symbols for >= 8 weeks.
Monitor live PF/WR; require >= 0.9 x back-test PF and <= 1.1 x back-test Sharpe.
Promote to real capital only after the above criteria hold for two consecutive 4-week windows and regime-robustness is confirmed.
Next step: Do you have a specific asset class or existing strategy you'd like to evaluate against this framework, or should we draft a concrete back-testing template for one of them?

Copy
Listen
Follow up

Can you provide a concrete back-testing template for an ETF dual-momentum strategy using the ideal pipeline?

What are the most common data-resolver issues you see in crypto and how can we systematically clean them?

How many live-paper forward-testing weeks are typically needed before a strategy can be safely scaled to full capital?
```

---

## 2026-06-02 — EAGLE swarm + real-money readiness research dump (user prompt)

**Saved for:** multi-AI swarm review of all `EAGLE*.MD*` (72h), LiteLLM (`ollama-cloud-large`, `ollama-cloud`, `ollama-cloud-local`), DB strategy inventory (`ejaguiar1_stocks`, `ejaguiar1_backtests`), Bonferroni/DSR/PBO gates, profitable-pick surface hunt.

**Surfaces to rank:** `/audit`, `/audit/ai_leaderboard.html`, `/audit/ai-tournament.html`, `/audit/pick_funnel.html`, `/audit/research_index.html`

**Goals (#1–#6):**
1. More strategies per asset class + better backtest methodology; best possible picks today (e.g. NVDA? BTCUSD? safe long-term?) given current site/GitHub even if not forward-tested.
2. More backtests per asset class.
3. Hidden edge research inside the project.
4. Proven statistical edge? Monte Carlo, Bonferroni, DSR/PBO — real-money worthy?
5. If building a prediction system across stocks/crypto/forex/bonds/ETFs/commodities/futures — which stats matter, bare-minimum vs ideal backtest, forward-test pick counts?
6. Implement concentration + resolver dispute monitoring; mutation framework for failed lab sleeves.

**Executive summary (2026-06-02 baseline):**
- Production audit book lacks deployable edge; research edge in tournament/lab only.
- Root causes: research≠production standards, emitter over-breadth, concentration artifacts, resolver/label contamination.
- Asset class snapshot: CRYPTO/EQUITY/FOREX weak live; ETF dual-momentum best lab candidate; tournament deepseek_v4/gpt4o/grok3 strong on paper only.
- 81 portfolios (66 active); deepseek_v4__aggressive has 11 open — not empty, mis-aligned.

**Enhancement blueprint (12-week):**
- Data/resolver hygiene: disputed purge, provenance tagging, duplicate detection on pf_portfolios.json.
- Validation: pre-register → purged-embargoed WF → cost model → DSR/PBO/SPA → block bootstrap → regime robustness → shadow-size → gradual scale.
- Emitter discipline: OOS PF≥0.6, WR≥0.55; forward paper ≥2 months before live sizing.
- Targets: ETF dual-momentum shadow; crypto VWAP/Bollinger after resolver fix; isolate deepseek_v4 tournament sleeves.
- Monitoring: daily PF/WR, weekly HHI & dispute rate >2% alert, regime drift monthly.

**Statistical measures for real-money-ready (reference thresholds):**
| Measure | Threshold |
|---------|-----------|
| Sharpe (net) | ≥1.0 bare; ≥1.5 ideal |
| PF | ≥1.5 bare; ≥2.0 ideal |
| WR | 45–55% if PF strong |
| MDD | ≤20% monthly |
| HHI | <0.20 aggregate |
| DSR/PBO/SPA | adj p<0.05 |
| OOS decay | PF OOS ≥80% IS |
| Forward test | ≥30–50 symbols, ≥8 weeks shadow, live PF within ±10% of backtest |

**Bare-minimum backtest:** clean data, pre-register, 70/30 split, flat costs, PF/Sharpe/WR/MDD, Bonferroni α/N.

**Ideal pipeline:** provenance, purged-embargo WF, block bootstrap, regime segments, full cost model, DSR/PBO, shadow simulation, Grafana monitoring.

**Forward-testing:** ≥30–50 picks per class, ≥2× longest lookback duration, ≤0.5% capital start, re-run block bootstrap on live-paper PnL; 95% CI for PF must not cross 1.0.

**Follow-up questions captured:**
- Concrete ETF dual-momentum backtest template (ideal pipeline)?
- Common crypto resolver issues + systematic cleaning?
- How many live-paper weeks before full capital scale?

**Infra:** `/home/eaguiar2015/dbpasses.txt`, LiteLLM `http://localhost:4000/v1`, test modes `ollama-cloud-large`, `ollama-cloud`, `ollama-cloud-local` after ~20min proxy restart.
---

## 2026-06-02 — EAGLE2 Swarm Strategy Brainstorm

### Context
Our /audit production book has no deployable edge. The real edge is in:
- AI tournament models (deepseek_v4 PF 3.46, gpt4o PF 3.14, grok3 PF 2.29)
- Verified lab sleeves (ETF dual momentum PF 1.60, crypto VWAP/Bollinger)
- Paper trading outperformers (Williams %R 81% WR, Triple RSI 91% WR)

### Goals
1. More strategies per asset class with better backtesting methodology
2. More backtests per asset class
3. Research on hidden edge within our project
4. Statistical significance: Monte Carlo, Bonferroni, DSR/PBO/SPA
5. Framework for "real-money-ready" picks
6. Statistical measures for production readiness

### Key URLs
- /audit: https://findtorontoevents.ca/audit
- AI Leaderboard: https://findtorontoevents.ca/audit/ai_leaderboard.html
- AI Tournament: https://findtorontoevents.ca/audit/ai-tournament.html
- Pick Funnel: https://findtorontoevents.ca/audit/pick_funnel.html
- Research Index: https://findtorontoevents.ca/audit/research_index.html

### Statistical Measures for Real-Money Readiness
| Measure | Why It Matters | Threshold |
|---------|---------------|-----------|
| Annualized Sharpe | Risk-adjusted return | >= 1.0 after costs |
| Profit Factor | Gross profit / gross loss | >= 1.5 bare minimum, >= 2.0 ideal |
| Win Rate | % winning trades | 45-55% acceptable, >60% only if PF modest |
| Max Drawdown | Tail risk | <= 20% monthly |
| Regime Robustness | Across volatility/trend states | Edge persists in >= 3 of 4 regimes |
| DSR/PBO/SPA | Controls data-snooping | Adjusted p < 0.05 |
| HHI Concentration | Single source dominance | < 0.20 |
| OOS Decay | IS vs OOS metrics | OOS PF >= 80% of IS PF |

### Forward-Testing Guidelines
- Minimum 30-50 distinct picks per asset class
- Duration >= 2x longest look-back window
- Start at <= 0.5% capital per strategy
- Live PF must stay within +/-10% of backtested PF
- Cover at least 3 distinct market regimes
- After forward period: block-bootstrap on live P&L, 95% CI for PF should not cross 1.0

### Action Plan
- Test LiteLLM new modes: ollama-cloud-large, ollama-cloud, ollama-cloud-local
- Run EAGLE*.MD swarm review
- Identify best current picks per asset class
- Compare against statistical framework

---

## EAGLE_JUNE2 Quant Review — claude-opus-4-7 — 2026-06-02 06:50Z

**Source:** `EAGLE_JUNE2_claude-opus-4-7.md` (462 lines, 41 KB, origin/main @ `c4fb174b3`)

**Why this is a research-to-production problem, not a "wait longer" problem:**
- 0/6 live classes pass Tier-2 (per `money_ready_verdict.json` 06:21Z).
- 1 lab Tier-2 pass: ETF Dual Momentum Sectors PF 1.60 / WR 53.8% / n=104 (lab-only, walk-forward PASS, paper pilot just wired).
- 4 model portfolios have positive paper PnL at 2-day noise floor: `deepseek_v4__aggressive` +0.40% (11 open positions, $100,403), `llama4_scout__aggressive` +0.14%, `cursor_agent__balanced` +0.015%, `together_deepseek_v3__aggressive` +0.001%.
- "Empty portfolio" was a WebFetch/JS-render artifact — the JSON has 11 open positions.

**Per-class root cause (1-line each):**
- CRYPTO: research edge in sub-cohorts, but deployed aggregate book loses (selection/gating/concentration mismatch).
- EQUITY: honest failure (n=52, expectancy -1.77%, DSR 0.0; 40% concentrated in `regime_terminal`).
- ETF: best candidate, but n=3. Forward sample is the answer here only.
- FOREX: data/resolver problem + weak edge (DSR 0.0002, all-strategy permutation ranks every FOREX strategy at null).
- COMMODITY: too little clean sample; lab sub-sleeves at right WR but below PF gate.
- FUTURES: concentration/artifact risk (85% `multi_asset_scanner`).
- BOND: data gap, not strategy failure (78 raw emitting, 0 closed).

**Quant verdicts on the 6 questions:**
- More time? No for main book. Yes for ETF. CRYPTO/EQUITY are honest failures.
- Do strategies suck? Deployed mix mostly does. Lab has 1 real sleeve. Tournament has 4 micro-edges.
- What's wrong? Research→production translation gap; concentration masquerading as edge; SL/TP mis-tuning; score-booster local inversion; data-feed silent breaks.
- DNA-mutate? YES, selectively on 6 candidates per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`. Not blanket.
- Invert? NO. Global ML inversion is REFUTED. conf 0.50-0.60 is the BEST band.
- Data feed dead? Partially. Real silence: data feed (PR #435), gate rejection, blocklist, universe, resolver pre-#433.

**Concrete next actions (§7 in EAGLE_JUNE2):**
1. Concentration cap on production_scanner: reject emit when `top_source > 0.50 AND n < 50`.
2. Score booster recalibration on 0.50-0.60 conf band as high-signal anchor.
3. SL/TP audit using intrabar OHLC replay (NOT winsorization — 2026-05-31 SL tightening collapsed PF via whipsaw).
4. Category taxonomy fix (collapse `stock`/`stocks`/`equity`) to re-classify UNKNOWN bucket.
5. ETF paper pilot Day-30: n≥30 + MDD<15% + PF≥1.20 promotion gate.
6. CRYPTO sub-cohort paper pilot: 2 best DSR-1.0 sleeves (ml_enhanced INJUSDT 1d + DYDXUSDT 15m), paper only.
7. Resolver intrabar OHLC replay on 9,657 ghost OPEN picks (upstream T2 blocker per `project-session-close-2026-05-31.md`).

**Other EAGLE files referenced (parallel agents):**
- `EAGLE2_2026-06-02_CLAUDE_CODE.md` — comprehensive enhancement plan
- `EAGLE2_2026-06-02_deepseek_v4_flash.MD` — Grok/DeepSeek-flash variant
- `EAGLE2_EAGLE_2026-06-02_blackboxai.md` — blackboxai variant
- `EAGLE3_2026-06-02_minimax-m3-free.md` — admissibility gate + CRYPTO LONG→SHORT flip + kill noise personas

**Cross-cutting thread:** the 4 EAGLE plans converge on (a) unified admissibility pipeline, (b) DSR/PBO at production_scanner gate, (c) resolver intrabar as upstream T2 blocker, (d) per-class mutation framework, (e) concentration monitoring.

---

## 2026-06-02 — EAGLE2 Multi-Model Synthesis + Strategy Brainstorm

**Source:** User directive + quant assessment + Mercury 2 analysis  
**Goal:** Get profitable picks by asset class, identify where most profitable picks live  

### Key Questions to Answer:
1. More strategies per asset class + better backtesting methodology
2. More backtests per asset class
3. Hidden edge research within project
4. Proven statistical edge (Monte Carlo, Bonferroni, etc.)
5. Statistical measures for "real money ready" picks
6. Bare-minimum vs ideal backtesting pipeline

### Statistical Measures for Real-Money-Ready:

| Measure | Threshold | Why |
|---------|-----------|-----|
| Sharpe Ratio | ≥ 1.0 after costs | Risk-adjusted return |
| Profit Factor | ≥ 1.5 (bare) → ≥ 2.0 (ideal) | Gross profit / gross loss |
| Win Rate | 45-55% acceptable if PF strong | Combined with PF |
| Max Drawdown | ≤ 20% monthly | Tail risk |
| Turnover | ≤ 30%/yr equities, ≤ 70%/yr crypto | Cost impact |
| Slippage | ≤ 5bps equities, ≤ 15bps crypto | Execution quality |
| Regime Robustness | ±10% across ≥ 3/4 regimes | Consistency |
| DSR/PBO/SPA | Adjusted p < 0.05 | Multiple testing |
| HHI | < 0.20 | Source concentration |
| OOS Decay | PF OOS ≥ 80% IS PF | Overfitting check |

### Bare-Minimum Backtesting:
1. Data hygiene (clean, deduped)
2. Pre-register hypothesis
3. Simple IS/OOS split (70/30)
4. Flat cost model (5bps)
5. Basic metrics (PF, Sharpe, WR, MDD)
6. Bonferroni correction

### Ideal Pipeline:
1. Data provenance (source_id, fallback, timestamp)
2. Purged-embargoed walk-forward (30d purge, 10d embargo)
3. Block bootstrap CI (1000 resamples)
4. Regime-segmented analysis
5. Full cost model (per asset class)
6. DSR/PBO/SPA correction
7. Shadow-size simulation (0.5% capital, 4-8 weeks)
8. Automated monitoring dashboard

### Forward-Testing Guidelines:
- Minimum 30-50 distinct symbols per asset class
- Duration: 2× longest look-back window
- Start at ≤ 0.5% capital per strategy
- Live PF within ±10% of backtest PF
- Cover ≥ 3 distinct market regimes
- Block-bootstrap on live P&L (95% CI for PF must not cross 1.0)

### Where Most Profitable Picks Live:
1. /audit/ai-tournament.html — best paper edge (deepseek_v4, gpt4o, grok3)
2. /audit/pick_funnel.html — good for discovery, bad for sizing
3. /audit/ — main production book (currently weak)
4. /audit/research_index.html — research outputs

### Assets to Investigate:
- NVDA: Blue-chip compounder, +2285% backtest, Sharpe 2.08
- BTCUSD: Donchian breakout +371%, MultiTF momentum +269%
- ETF dual-momentum: Best lab edge, PF 1.22, 54.9% WR
- macd_rsi_momentum: Walk-forward validated PF 3.33, 65.4% WR daily

---

## 2026-06-02 (re-run) — Full verbatim user prompt + swarm directive

**Workflow:** sync GitHub → review all `EAGLE*.MD*` (72h) → LiteLLM swarm (`ollama-cloud-large`, `ollama-cloud`, `ollama-cloud-local`) → Bonferroni/DSR/PBO vs live state → `reports/EAGLE_SWARM_SYNTHESIS_2026-06-02.md`

**Surfaces:** [findtorontoevents.ca/audit](https://findtorontoevents.ca/audit), [ai_leaderboard](https://findtorontoevents.ca/audit/ai_leaderboard.html), [ai-tournament](https://findtorontoevents.ca/audit/ai-tournament.html), [pick_funnel](https://findtorontoevents.ca/audit/pick_funnel.html), [research_index](https://findtorontoevents.ca/audit/research_index.html)

**DB:** `ejaguiar1_stocks`, `ejaguiar1_backtests` — credentials `/home/eaguiar2015/dbpasses.txt`

**LiteLLM:** `http://localhost:4000/v1` — test `ollama-cloud-large`, `ollama-cloud`, `ollama-cloud-local`

### 1. Executive Summary
- **Core issue:** Production audit book lacks deployable edge; research edge only in tournament/lab sleeves.
- **Root causes:** Research≠production standards, emitter over-breadth, concentration artifacts, resolver/label contamination.
- **Goal:** Convert verified research edge to capital-ready strategies; tighten data hygiene + validation.

### 2. Current State (2026-06-02)
| Asset Class | Live PF/WR | Research Edge | Pain Point |
|-------------|-----------|---------------|------------|
| CRYPTO | <0.5 PF, high WR | Tournament sub-cohorts | Gating/concentration mismatch |
| EQUITY | Negative PF, low WR | None | Weak emitters |
| ETF | Small n, modest PF | Dual-momentum | Insufficient forward data |
| FOREX | High WR, terrible PF | Minor | Resolver mislabels |
| COMMODITY | Too few samples | N/A | Sample size |
| FUTURES | Concentration spikes | N/A | Artifact risk |
| BOND | No sample | N/A | Data gap |

81 portfolios (66 active); `deepseek_v4__aggressive` has 11 open — mis-aligned, not empty.

### 3–8. Blueprint (condensed archive)
- **Hygiene:** disputed purge, provenance tagging, pf_portfolios dedupe.
- **Validation:** pre-register → purged-embargo WF (30d/10d) → costs → DSR/PBO/SPA → block bootstrap → regime robustness.
- **Discipline:** OOS PF≥0.6, WR≥0.55; forward paper ≥2mo; shadow ≤0.5%; scale after 8w within ±10% paper PF.
- **Targets:** ETF dual-momentum shadow; crypto VWAP/Bollinger; isolate deepseek_v4 tournament sleeves.
- **Monitoring:** daily PF/WR; weekly HHI>0.25, dispute>2%; monthly regime drift >15%.
- **12-week timeline:** weeks 1–2 hygiene; 3–4 pipeline; 5–6 WF; 7 shadow; 8–9 mutation; 10–12 scale.
- **Success:** 2 capital-ready sleeves; dispute <1%; HHI <0.20; pipeline ≤5min/sleeve.

### Goals #1–#6 (user)
1. More strategies/class + better backtest; best picks now (NVDA? BTCUSD? safe long-term?) if not forward-tested.
2. More backtests per class.
3. Hidden edge in project.
4. Monte Carlo, Bonferroni, real-money statistical proof.
5. Cross-asset prediction system: bare-min vs ideal backtest + forward pick counts.
6. Concentration + resolver monitoring; mutation framework for failed lab sleeves.

### Statistical measures (real-money-ready)
| Measure | Threshold |
|---------|-----------|
| Sharpe (net) | ≥1.0 bare |
| PF | ≥1.5 bare, ≥2.0 ideal |
| WR | 45–55% if PF strong |
| MDD | ≤20% monthly |
| HHI | <0.20 |
| DSR/PBO/SPA | adj p<0.05 |
| OOS decay | PF OOS ≥80% IS |

**Bare-min:** hygiene, pre-register, 70/30, 5bps costs, PF/Sharpe/WR/MDD, Bonferroni α/N.

**Ideal:** provenance, purged WF, block bootstrap, regimes, full costs, DSR/PBO, shadow 4–8w, Grafana.

**Forward:** 30–50 symbols/class; 2× lookback duration; ≤0.5% start; live PF ±10% backtest; 95% CI PF must not cross 1.0.

**Decision flow:** pre-register → ideal backtest → gates → shadow 8w → two 4w windows → scale.

**Follow-ups:** ETF dual-momentum template; crypto resolver cleaning; weeks before full capital (answer: 8w shadow minimum, 16w safer).

**Re-run artifact:** `python3 tools/eagle_swarm_synthesis.py` → `reports/EAGLE_SWARM_SYNTHESIS_2026-06-02.md`

**Re-run artifact:** `python3 tools/eagle_swarm_synthesis.py` → `reports/EAGLE_SWARM_SYNTHESIS_2026-06-02.md`
**Best-picks verify:** `python3 tools/verify_best_picks_swarm.py` → `reports/best_picks_swarm_review_2026-06-02.json`
**Consolidated swarm:** `reports/EAGLE_SWARM_CONSOLIDATED_2026-06-02.md`

### 2026-06-05 — Audit & Money-Ready Tiering Brainstorm

**Audit Findings (Universal Resolver & Dashboard Generator):**
- **Resolver:** Robust handling of reverse splits and asset-class specific hold windows (e.g., 48h for Crypto, 72h for Forex, 120h for Bonds) to prevent stale picks from skewing stats.
- **Dashboard:** Strong data integrity filters in place:
    - : Filters out "ghost rows" (zero-PnL artifacts), corrupt PnL (JPY pip-vs-percent), and price-magnitude corruption.
    - : Uses standardized  formula.
    - : Excludes effectively flat trades (noise) from win-rate calculations.

**Brainstorm: "Money-Ready" Tiering Framework:**
To bridge the gap to real money, we need clear, non-embarrassing tiers of confidence:
- **Tier 1 (Institutional/Mutual Fund Ready):** 
    - Statistically significant sample size (e.g., N > 50 or 100).
    - Consistent edge across multiple market regimes.
    - High Win Rate (WR) + high Profit Factor (PF) + low Max Drawdown (MDD).
    - Verified through both paper trading and (if possible) small-scale live execution.
- **Tier 2 (High Conviction/Aggressive):**
    - Emerging edge with growing sample size.
    - Strong performance in recent windows.
    - Suitable for "paper trading" or very small "skin in the game" amounts.
- **Tier 3 (Research/Experimental):**
    - New strategies, low sample size.
    - High volatility in performance.
    - Purely for data gathering and refinement.

**Immediate Action Items:**
- Identify which asset classes/strategies currently meet Tier 1 criteria.
- Audit the "best possible picks" mentioned in recent updates to see if they are truly Tier 1.
- Deploy sub-agents to cross-reference  research with dashboard performance.

---

### 2026-06-05 ~05:50 UTC — Operator /loop prompt + Bridge-Tier consolidation (claude-opus-4-7)

**Operator's /loop prompt (saved verbatim, scheduled at `7 * * * *` job `e65b9a0e`, session-only, 7-day expiry):**

> keep going we need constant progres towards statitically valid scrutnized algorithms across each asset class, that are ready for us to put REAL money into.. we need to find a way to bridge the gap quickly to get to being "money-ready" . .our paper trading / tracking had flaws such as resolver issues, reverse stock causing skewed Win-rates scrunitize all win-rates and stats & wording on findtorontoevents.ca/audit and https://findtorontoevents.ca/audit/ai_leaderboard.html and https://findtorontoevents.ca/audit/ai-tournament.html including performance by portfolio, asset class, model, etc. and ensure we REALLY have picks that would performance reliably..  we are talking about mutual fund worthy performance.. or genius level stock picker level.. we cant have any embrassing bunch of loser after loser picks.. no coin flips.

**Frustration context:** months struggling, 0/9 asset classes trustworthy enough for real money, embarrassment risk on public-facing audit.

#### Reconciling Zoocode's draft above with the CANONICAL tier framework

Zoocode's "Tier 1 = N>50" above does NOT match the codebase's canonical tier table at `docs/PERFORMANCE_CHARTER.md`. Using the wrong thresholds publicly is exactly the embarrassment the operator is trying to avoid. Authoritative reference table (cite this, not the simplified version):

| Tier | PF | WR | MaxDD | n | What it means |
|---|---|---|---|---|---|
| **Tier 1 (Renaissance)** | ≥2.0 | ≥55% | ≤10% | ≥200 | Long-run target. Real, large-money grade. |
| **Tier 2 (Institutional/Sized-up)** | ≥1.5 | ≥50% | ≤20% | ≥100 | Minimum for sizing up beyond pilot. |
| **Tier 3 (Marginal/Probation)** | ≥1.2 | ≥45% | ≤25% | ≥100 | Paper-trading floor only. |
| Below Tier 3 | <1.2 OR WR<45% OR MDD>25% | — | — | — | Do NOT size. |

**Sample-size discipline** (PERFORMANCE_CHARTER §10):
- n<30 → "insufficient data" (no inference permitted)
- 30 ≤ n < 100 → "developing" (directional only, NOT promotable)
- n ≥ 100 → tier classification permitted

#### The Bridge: a 5-stage progression from coin-flip to mutual-fund-worthy

The "months-long gap" the operator describes is actually well-formalized already — it's just spread across multiple docs. Consolidated for /audit publication:

| Stage | Label | Gate to enter | Sizing | Days from cold start |
|---|---|---|---|---|
| 0 | **Backtest only** | Idea has working code | 0% (no live picks) | Day 0 |
| 1 | **Shadow / Lab-validated** | Backtest passes T2 stats on cleaned data | 0% (shadow emission only) | ~14 days |
| 2 | **Forward-paper pilot** | Lab-validated + walk-forward PASS + ≥1 LLM peer review | 0% (paper book) | ~30 days |
| 3 | **WATCH (forward n→100)** | Forward n ≥ 30, WR/PF trending toward T2 | 0.1% notional, drawdown-halted | ~60 days |
| 4 | **MONEY_READY (Tier 2)** | Forward n ≥ 100, DSR/PBO/SPA pass post-slippage, single-source HHI<0.20 | Kelly-fraction sized | ~90-120 days |
| 5 | **Tier 1 (Renaissance)** | n ≥ 200 forward, PF ≥ 2.0 maintained across 2+ regimes | Full strategy weight | 6-12 months |

**Honesty rule:** every audit-surface cell that publishes a WR/PF MUST also publish its stage. Stage 0-2 cells must NOT say "Best Picks" without "PAPER WATCH — DO NOT SIZE" inline.

#### Audit of the existing "best possible picks" entry (`updates/index.html` ~line 816, dated 2026-06-02)

The most recent best-possible-picks entry already published:
- **Title**: "EAGLE-4 + EAGLE-5 Gates — Code Diff, Smoke Test, Best Picks & 12-Week Plan"
- **Paper-watch picks**: CRYPTO SHORT (BTC/ETH); ETF: EEM, IWM, GLD; EQUITY: BAC, JPM, MSFT, NVDA
- **Caveat already present**: "do NOT size (0/9 money-ready per `money_ready_verdict.json`)"
- **Only shadow-pilot**: `etf_verified_dual_momentum`

**Status check needed today (2026-06-05)**: are those picks still in their expected ranges? Has any of them resolved? File ENH if entries are now stale-but-still-displayed as if current.

#### Highest-leverage bridge ideas brainstormed (this session)

1. **Stage banner on every cell** — auto-prefix each /audit asset-class cell with its current Stage (1-5) instead of just verdict. Removes the "looks T1 but is shadow" ambiguity at the source.
2. **Per-row tier caveat field in JSON** (already filed ENH #132) — tournament leaderboard JSON needs `wr_artifact_risk` per row so non-browser consumers don't mis-cite Tier-1.
3. **WR units unified** (already filed ENH #131) — pick decimal OR percent across all canonical JSON, enforce via CI.
4. **Bridge-stage accelerator: piggyback off ETF DM** — `etf_verified_dual_momentum` is the only sleeve approaching Stage 3. Wire it to live emission with 0.1% notional + circuit-breaker the day forward n hits 30 (currently 0).
5. **Per-class "fastest credible bridge" table** — publish to /audit so the operator can show stakeholders "ETF: ~60 days, CRYPTO: ~90 days, EQUITY: gated on trust_score=7 sleeve first, BOND: no data yet" instead of just "0/9 ready".
6. **Bias-survivor sleeve formal entry** (`reports/high_quality_picks_plan_2026-06-05.md`) — 12 picks identified, top 5 in open-consensus state (BND/SHY/IWM/SPY LONG, SHY SHORT). Wire to a 4-week forward-pilot with mandatory ENH gates instead of leaving in a one-off report.
7. **DISPUTED-banner-to-data flip** — tournament's 67-91% WR caveat lives only in HTML. Move to data layer so anyone reading the JSON sees the caveat.
8. **Stop publishing aggregate WR/PF when n<30** — the COMMODITY n=4 PF 10.50 cell makes the dashboard look serious when it's anecdote. Show "INSUFFICIENT DATA (n=4)" instead of a PF number.

#### Related already-filed enhancements/incidents (this session, for reviewer cross-link)

- `ENH OVERALL #129` — Backfill 1034 zero-PnL rows in `at_pick_outcomes` after `_compute_pnl` landed
- `ENH OVERALL #130` — EXEC_PLAN_06 VRP entry blocked by 11 methodology bugs (DeepSeek-corroborated 5/11)
- `ENH OVERALL #131` — WR unit inconsistency (decimal vs percent) across canonical JSON
- `ENH OVERALL #132` — Tournament leaderboard JSON missing per-row DISPUTED/artifact caveat field
- `ENH FOREX #4` — FOREX n/WR/PF disagree between `money_ready_verdict` and `pf_registry` at same timestamp
- `INCIDENT STOCKS #11` — Hermes/Nemotron-3-Super + Gemini-YOLO backupless `trading_picks` mutation 2026-06-05T05:30Z

#### What NOT to do (operator embarrassment-avoidance hard rules)

- ❌ Do NOT publish "Tier 1" label on any sleeve with n<200 + forward PF<2.0 (even if backtest looks great)
- ❌ Do NOT promote any strategy to `PROMOTED_STRATEGIES` without all 5 stages complete (re: Gemini's PROMOTED_STRATEGIES bypass today, defused)
- ❌ Do NOT cite the VRP harvest "VALIDATED ✅" backtest from `_CLAUDE_CLOUD_MINIMIX_*` until 11 methodology bugs are fixed
- ❌ Do NOT flip CRYPTO LONG production back on (Grok's `CRYPTO_PRODUCTION_BLOCK_LONG=1` is the right default)
- ❌ Do NOT publish aggregate per-class WR when n<30 — show "INSUFFICIENT DATA" caption instead

— claude-opus-4-7 (session: /loop e65b9a0e + 3-agent parallel scan)

---

## /loop 2h — Deep Winner Hunt Per Asset Class (2026-06-05)

**Operator prompt:**
> /loop 2h keep going and dig deeper until you find us true winners per asset class. Scrutinize picks continuously looping until you narrow down winners that are statistically valid, even if we can't forward test them, we need the best possible picks. So maybe a stock with a proven track record, or something like NVDA which has a lot of potential I would say. Maybe try to pull stock analyst consensus or something? Pro trader calls? etc.

**What this loop should do each iteration:**
1. Query live DB (`ejaguiar1_stocks.trading_picks`) for source systems passing: n≥30, WR≥50%, PF≥1.5, closed_at NOT NULL, 2026+
2. Run concentration check (HHI < 0.30 per symbol)
3. Pull analyst consensus via yfinance for top EQUITY/ETF candidates (recommendationMean ≤ 2.0 = Strong Buy/Buy)
4. Check CoinGecko/Binance funding rates for CRYPTO directional bias
5. Cross-reference with `reports/wr_scrutiny_honest_2026-06-05.md` (source: mega_mutation n=296 WR=63.9%)
6. Emit a ranked shortlist: top 3 picks per asset class with statistical backing
7. Log findings to `reports/winner_hunt_<date>.md`

**Current best candidates (as of 2026-06-05 live DB query):**
- CRYPTO: `mega_mutation` n=296 WR=63.9% PF=3.12 — top symbols: JUPUSDT (85.1%), ENAUSDT (80%), ADAUSDT (77.8%)
- EQUITY/ETF: `battleground_luxalgo` n=129 WR=51.9% PF=1.76 — needs analyst cross-check
- STOCKS: need deeper per-symbol analysis (NVDA, QQQ, SPY analyst consensus)

**Hard rules for this loop:**
- ❌ Never claim "winner" on n<30 with real closed_at
- ❌ Never cite batch-day artifact sources (kimi_signal_tracking = all 146 on one day)
- ❌ Never cite NULL pnl_pct picks in WR/PF calculations
- ✅ Analyst consensus: yfinance `ticker.info['recommendationMean']` ≤ 2.0 = strong candidate
- ✅ Minimum: binomial p-value < 0.05 on observed WR with observed n

