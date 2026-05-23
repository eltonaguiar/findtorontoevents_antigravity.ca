# Crypto Prediction Enhancement Plan (Evidence-Backed, Multi-Agent)

**Date:** 2026-03-17  
**Workspace:** `e:\findtorontoevents_antigravity.ca`  
**System:** Alpha Engine + Forward Validator + ML Ranker

## 1) Objective
Build a prediction stack that learns from **time**, **volatility regime**, **entry quality**, and **exit outcomes**, while enforcing feature integrity and statistically robust validation.

## 2) Current System Snapshot (from architecture mapping)
- Scanner cadence: GitHub Actions every 10 minutes.
- Core pipeline: `production_scanner.py` -> `forward_validator.py` -> `scanner.py` -> `ml_ranker.py` -> `elite_scorer.py` -> `active_picks.json`/`premium_signals.json`.
- Strategy surface: 200+ strategies across 30+ modules.
- ML model family: XGBoost/LightGBM/RandomForest, 39-feature ranker.
- Live gates: RR, direction gates, VPIN toxicity, DSR/WRC penalties, cooldown, LDS, GARCH adjustment, SL calibration.

## 3) Parallel Workstreams Already Running
1. Feature audit + dead-feature remediation + time/vol features.
2. Adaptive SL/TP calibrator (MAE/MFE-based) integrated into `forward_validator.py`.
3. End-to-end scanner/ML architecture map.
4. Feature contract + feature health gate.
5. Entry timing optimizer + regime interactions.

## 4) Evidence Review Method
- Focused on primary sources (NBER/BIS/journal papers) and robust empirical findings.
- Prioritized effects that are implementable in live trading with latency, cost, and leakage constraints.
- Graded each predictor family by reproducibility and deployment fit.

## 5) What Actually Works (Evidence Tiers)

### Tier A (strongest and most reproducible)
1. **Momentum / trend persistence (time-series + cross-sectional variants)**
   - Repeatedly documented in crypto literature, often strongest in larger/liquid coins and specific horizons.
   - Implementation: rolling return ranks, trend state transitions, volatility-scaled momentum.
2. **Carry / basis (spot-futures spread, perp funding context)**
   - Structural mispricing and segmentation effects documented; carry has predictive content for stress/crash states.
   - Implementation: annualized basis, funding persistence, basis term structure, carry z-score.
3. **Microstructure imbalance for short horizons (OFI / order-book imbalance class)**
   - Strong for short-horizon direction/execution quality, weaker at long horizons without regime conditioning.
   - Implementation: OBI/OFI at multiple depths + liquidity/vol filters.

### Tier B (works conditionally, requires context)
1. **Intraday seasonality / session effects**
   - Return/volatility periodicity exists; predictive power is regime- and liquidity-dependent.
   - Implementation: cyclic time features + interaction terms (symbol x hour, regime x hour).
2. **Attention proxies (search/sentiment)**
   - Can add incremental predictive power but unstable and crowding-prone.
   - Implementation: capped/decayed features, avoid hard gating.
3. **On-chain activity factors**
   - Useful in medium horizons for select assets; noisy if used raw.
   - Implementation: smoothed z-scores, chain-specific reliability weighting.

### Tier C (high risk of overfit unless tightly controlled)
1. Complex deep architectures without strict walk-forward discipline.
2. Sparse niche factors with low coverage and unstable data latency.
3. Heavily hand-tuned threshold stacks without post-selection validation.

## 5.1 Ranked Predictor Families For 4h/1d Models (research synthesis)
1. **Funding/Basis/Carry (Grade A)**  
   Strongest deployable family for 4h-1d context. Most robust when treated as crowding/carry state rather than unconditional direction.
2. **Trend / Time-Series Momentum (Grade A-)**  
   Stable in daily crypto evidence; works best with volatility scaling and jump-aware gating.
3. **Cross-Sectional Momentum / Spillover (Grade A-)**  
   Useful at portfolio level and single-asset relative-strength overlays.
4. **Short-Horizon Reversal (Grade B+)**  
   Useful in overextension/liquidity-stress states; weak in strong trend regimes.
5. **Options Skew / IV Structure (Grade B-/C+)**  
   Better as crash-risk/regime filter than directional alpha.
6. **On-Chain Variables (Grade C for direction, B for regime/volatility)**  
   Better as slow regime overlay than short-horizon entry signal.

## 5.2 Labeling and Horizon Policy
- Primary labels:
  - `fwd_ret_4h`, `fwd_ret_1d`, `fwd_ret_7d` (net of fees/slippage)
  - `entry_edge_bps_15m`, `entry_edge_bps_60m`
  - early `mae_4h`, `mfe_4h` for exit calibration
- Overlap control:
  - skip most recent bar for slow factors when needed
  - enforce purging/embargo by max horizon

## 6) Root Causes To Fix First
1. Feature matrix integrity is still the bottleneck (dead/constant features dominate).
2. Entry labels are under-specified (direction only; no explicit entry-quality objective).
3. Stop calibration was mostly static before the new calibrator.
4. Validation can still overstate edge if retraining/selection discipline is weak.

## 7) Enhanced Target Architecture

## 7.1 Feature Contract Layer (hard requirement)
- At signal creation time, compute and persist a **versioned feature snapshot**.
- Train only on rows passing schema + completeness checks.
- Persist provenance: data source, timestamp, latency class, fallback path.

## 7.2 Dual-Model Decision Stack
1. **Directional model**: win-probability / expected-return class.
2. **Entry quality model**: predicts adverse excursion and entry drift (`enter_now`, `wait`, `skip`).

## 7.3 Adaptive Exit Layer
- Keep new MAE/MFE calibrator in tighten-only mode initially.
- Expand from group-level to hierarchical calibration as sample size grows.

## 7.4 Regime Router
- Volatility/trend/chop state + liquidity state + event state.
- Route model weights, thresholds, and sizing by regime.

## 8) Detailed Phase Plan

### Phase 1 — Feature Truth (Days 1-4)
**Goal:** eliminate dead-feature training and lock deterministic feature generation.

**Build**
- Merge feature contract + health gate first.
- Persist full feature vector in `extra_json`/`ml_features_at_entry` at signal time.
- Add training preflight report:
  - dead feature count
  - constant feature count
  - per-feature coverage
  - stale-source share

**Acceptance criteria**
- Training aborted if dead features > 50% (initial threshold).
- 100% of new picks have contract-valid feature snapshots.
- Reproducibility test: same input snapshot -> identical feature vector hash.

### Phase 2 — Time-of-Day Learning (Days 5-7)
**Goal:** learn hour/session effects without hardcoded blackout overreach.

**Build**
- Add cyclic hour/day features + session buckets.
- Add interactions: `symbol x hour`, `regime x hour`, `vol_bucket x hour`.
- Add calibration reports by UTC hour block.

**Acceptance criteria**
- Statistically stable hour effect in at least one liquid symbol family.
- Better calibration (Brier/ECE) vs baseline without reducing trade count excessively.

### Phase 3 — Volatility-Regime Context (Week 2, Days 1-3)
**Goal:** stop mixing incompatible market states.

**Build**
- Define regime labels using trailing realized vol + trend/chop metrics + liquidity.
- Train regime-conditional heads or single model with regime interactions.
- Route gating/sizing by regime confidence.

**Acceptance criteria**
- Per-regime performance dispersion narrows (fewer regime blowups).
- Regime-aware model beats pooled model OOS.

### Phase 4 — Entry Timing Optimization (Week 2, Days 4-6)
**Goal:** reduce bad fills and late entries.

**Build**
- Labels: `entry_edge_bps_{5m,15m,60m}`, early MAE, first-hit timing.
- Pre-entry policy: `enter_now` / `wait_1_bar` / `skip`.
- Keep throughput guardrail to avoid over-filtering.

**Acceptance criteria**
- Lower adverse entry drift vs baseline.
- Equal or better expectancy after costs.

### Phase 5 — Stop-Loss/TP Calibration (Week 3, Days 1-4)
**Goal:** adapt exits to symbol/strategy/regime/session.

**Build**
- Productionize `sl_calibrator.py` outputs with hierarchical fallback.
- Safety constraints: tighten-only mode first, bounded multipliers, min RR floor.
- Add explainability fields to closed picks.

**Acceptance criteria**
- Reduced SL-hit rate for same or better net expectancy.
- No increase in tail drawdowns during canary period.

### Phase 6 — Continuous Learning & Governance (Week 3, Days 5-7)
**Goal:** robust retraining without false discoveries.

**Build**
- Purged/embargoed walk-forward CV as default.
- Selection-bias controls: DSR/PBO-aware promotion policy.
- Champion/challenger deployment and drift triggers.

**Acceptance criteria**
- Promotion only if candidate beats champion on OOS + calibration + drawdown metrics.
- Auto rollback on calibration drift or drawdown breach.

## 9) Rollout Strategy

### Stage A: Shadow Mode
- Compute new features and decisions, but do not execute.
- Compare against current production outputs for 7-10 days.

### Stage B: Canary (10-20% flow)
- Enable by symbol subset and top-liquidity pairs.
- Daily risk committee report (PnL decomposition + calibration + gate blocks).

### Stage C: Full Rollout
- Expand only after meeting KPI thresholds for two consecutive weekly windows.

## 10) KPI Dashboard (must-pass)
1. Dead feature ratio: <= 25% (near-term), <= 10% (target).
2. Constant feature ratio: <= 20%.
3. Entry drift reduction: >= 15% improvement.
4. Net expectancy improvement after costs.
5. Per-regime stability: no single regime drives all returns.
6. Calibration quality: lower Brier/ECE than baseline.
7. Risk: no deterioration in max drawdown / tail loss.
8. Execution quality: implementation shortfall and realized spread improve vs baseline.
9. Cost realism: expected net edge pass-rate remains positive under 2x spread/latency stress.
10. Model governance: challenger only promoted if post-cost OOS metrics exceed champion for two consecutive windows.

## 11) Ownership Map
- Feature contract + health gate: Agents 1 + 4.
- Regime + time interactions: Agents 1 + 5.
- Entry timing layer: Agent 5.
- SL/TP calibration: Agent 2.
- Pipeline integration and docs: Agent 3 + main integrator.
- Model routing by horizon (GBM/linear/deep challengers): ML platform owner.
- Execution cost engine (fees/spread/impact/latency/funding): execution + data engineering.
- Portfolio sizing policy (HRP/vol-target/fractional-Kelly/DD governor): risk + portfolio engineering.
- Label/objective upgrade (triple-barrier + meta-label + utility-aware loss): ML research + MLOps.

## 12) Immediate Next Actions (next 24h)
1. Merge architecture map output into this plan as final module inventory.
2. Merge feature contract changes first; run preflight audit on latest closed picks.
3. Keep SL calibrator in tighten-only shadow mode for one cycle.
4. Launch entry optimizer in shadow mode and collect decision deltas.
5. Produce first daily KPI report with dead/constant feature breakdown.

## 13) Microstructure + Derivatives Signal Specification (from completed subagent track)

### 13.1 Priority ranking for live alpha
1. **High confidence:** multi-level OFI/OBI, basis/perp premium/funding (with OI context).
2. **Medium confidence:** liquidation bursts and OI changes as confirmation/regime signals.
3. **Low confidence standalone:** VPIN and raw CVD (retain as auxiliary stress/context).

### 13.2 Feature formulas and horizons
**A) Order flow imbalance / order book imbalance (execution horizon)**
- Features:
  - `ofi_z_10s`, `ofi_z_1m`, `ofi_z_5m`
  - `imbalance_top5 = (bid_depth_top5 - ask_depth_top5) / (bid_depth_top5 + ask_depth_top5)`
  - `depth_collapse_rate`, `spread_expansion_rate`
- Typical horizon: seconds to a few minutes.
- Suggested trigger band: `|ofi_z| > 2`, with no extreme spread/depth deterioration.

**B) Funding / perp premium / basis (state + carry horizon)**
- Features:
  - `funding_z_30d`
  - `perp_premium_z_30d`
  - `annualized_basis_front`, `basis_curve_slope`
  - interaction: `funding_z * oi_z * depth_z`
- Typical horizon: 1 hour to 1 week depending on basis tenor.
- Suggested trigger band: `z > 2` or `z < -2`, especially persistent across windows.

**C) Liquidation and OI stress (hazard layer)**
- Features:
  - `liq_notional_15m / open_interest`
  - `liq_imbalance = long_liq - short_liq`
  - `liq_acceleration`
  - `oi_change_1h`, `oi_change_4h`
- Typical horizon: 15 minutes to 6 hours.
- Suggested hazard trigger: top-decile liquidation burst or ~0.5%-1.0% OI shock with thinning depth.

**D) VPIN/CVD usage policy**
- VPIN: stress/toxicity gate only, not directional alpha.
- CVD: smoothed signed-flow proxy only; de-prioritize when OFI is available.

### 13.3 Deployment policy
1. Route OFI/OBI into entry timing and slippage model (Phase 4), not just directional ranker.
2. Route funding/basis/OI into regime router and directional model interactions (Phase 3).
3. Route liquidation and VPIN into risk suppressors and exposure caps.
4. Re-estimate thresholds per exchange fee regime and market microstructure changes.

### 13.4 Regime Framework and Sizing Overlay (from completed subagent track)

### Primary regime predictors
1. **Volatility state** (primary gate).
2. **Session/liquidity state** (execution modifier).
3. **Macro risk state** (stress throttle; VIX/rates prioritized, DXY low-weight).
4. **Structural break state** (hard safety gate).

### Two-stage operating model
1. **Stage 1 regime gate**: outputs `tradable` + regime label.
2. **Stage 2 strategy router**:
   - Calm/liquid -> allow MR + small trend.
   - Trend/risk-on -> allow momentum/breakout.
   - Shock/high-vol -> cut size or require stronger edge.
   - Transition/break -> flat or minimal exploratory sizing.

### Recommended sizing multipliers
- Vol percentile <30 and no macro event: `1.0x` to `1.25x`.
- Vol percentile 30-80: `0.5x` to `1.0x`.
- Vol percentile >80 or VIX spike: `0.25x` to `0.5x`.
- Structural break active: `0x` to `0.25x`.
- Weekend/thin-liquidity windows: capped sizing unless weekend-specialized edge.

## 14) Source Registry (primary references)
- [NBER w24877: Risks and Returns of Cryptocurrency](https://www.nber.org/papers/w24877)
- [NBER w25882: Common Risk Factors in Cryptocurrency](https://www.nber.org/papers/w25882)
- [NBER w30796: Leverage and Stablecoin Pegs](https://www.nber.org/papers/w30796)
- [NY Fed Staff Report 1052: The Bitcoin-Macro Disconnect](https://www.newyorkfed.org/research/staff_reports/sr1052.html)
- [BIS Working Paper 1087: Crypto Carry (rev. Oct 2025)](https://www.bis.org/publ/work1087.pdf)
- [NAJEF: Dynamic Time Series Momentum of Cryptocurrencies](https://community.portfolio123.com/uploads/short-url/amrMsuqIKzdHcHHyvMud4YNPwZB.pdf)
- [SSRN: Intraday Return Predictability in Crypto Markets: Momentum, Reversal, or Both](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4080253)
- [JFDS: Predicting Bitcoin Returns Using High-Dimensional Technical Indicators](https://doi.org/10.1016/j.jfds.2018.10.001)
- [SSRN: The Price Impact of Order Book Events](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1712822)
- [ArXiv: Cross-Impact of Order Flow Imbalance](https://arxiv.org/abs/2112.13213)
- [SSRN: Fee Structure and Order Flow Informativeness in the Cryptocurrency Market](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5051291)
- [ArXiv: Deep Learning for Digital Asset Limit Order Books](https://arxiv.org/abs/2010.01241)
- [SSRN: Liquidation, Leverage and Optimal Margin in Bitcoin Futures Markets](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3781646)
- [SSRN: Breaking the Stablecoin Buck](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4109307)
- [SSRN: Empirical Investigation on Risk Factors in Cryptocurrency Futures](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4657014)
- [ArXiv: Reconciling Open Interest with Traded Volume in Perpetual Swaps](https://arxiv.org/abs/2310.14973)
- [Binance Academy: What Are Funding Rates in Crypto Markets?](https://academy.binance.com/articles/what-are-funding-rates-in-crypto-markets)
- [Coinbase Learn: Understanding Funding Rates in Perpetual Futures](https://www.coinbase.com/en-au/learn/perpetual-futures/understanding-funding-rates-in-perpetual-futures)
- [SSRN: Cross-Cryptocurrency Return Predictability](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3974583)
- [SSRN: Bitcoin Network Activity and Bitcoin Price Return Volatility](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4619010)

## 15) Validation Protocol (adopted from completed subagent track)

### 15.1 Leakage controls (mandatory)
1. Label in event-time and preserve horizon metadata.
2. Freeze features at decision timestamp; no post-event recomputation.
3. Purge overlapping-label samples between train/test folds.
4. Apply embargo >= max label horizon (+ data-latency allowance).

### 15.2 CV and model selection
1. Use purged time-series CV for tuning.
2. Use CPCV for final model path distribution, not single-path luck.
3. Keep final holdout untouched by feature/threshold tuning.

### 15.3 Multiple testing correction
1. White Reality Check / SPA / MCS at strategy-selection layer.
2. DSR and PBO as promotion requirements, not optional diagnostics.
3. Promotion is blocked if only raw Sharpe is good but corrected metrics fail.

### 15.4 Probability calibration
1. Calibrate on a time-separated calibration split.
2. Track log loss, Brier, calibration slope/intercept, and ECE.
3. If calibration drifts, reduce sizing and demote model even if AUC is unchanged.

### 15.5 Live drift and retrain triggers
1. Trigger on residual/loss stream drift and calibration decay (not feature drift alone).
2. Add retrain cooldown to prevent oscillation.
3. Deploy challenger in shadow/canary before replacing champion.

### 15.6 Feature health operations
1. Monitor missingness, staleness, out-of-range, distribution drift, and join integrity.
2. Quarantine failed features in live scoring.
3. Version every feature contract and keep last-known-good snapshot.

### 15.7 Deployment pass/fail gate
A model is deployable only if all pass:
1. Leakage audit clean.
2. Purged/embargoed CV + CPCV competitive.
3. Survives multiple-testing correction (DSR/PBO/SPA/MCS policy).
4. Calibrated probabilities on separate fold.
5. Live feature-health checks green in shadow/canary.
6. Stable after costs and across regimes.

### 15.8 Core references for validation policy
- White, 2000 reality check: https://bashtage.github.io/kevinsheppard.com/files/teaching/mfe/advanced-econometrics/White.pdf
- Hansen, 2005 SPA: https://bashtage.github.io/kevinsheppard.com/files/teaching/mfe/advanced-econometrics/Hansen.pdf
- Model Confidence Set (Hansen, Lunde, Nason): https://www.kevinsheppard.com/files/teaching/mfe/advanced-econometrics/Hansen_Lunde_Nason.pdf
- Probability of Backtest Overfitting: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253
- Deflated Sharpe Ratio: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551
- ADWIN (adaptive windowing): https://www.cs.upc.edu/~gavalda/papers/adwin06.pdf
- Calibration of modern networks: https://proceedings.mlr.press/v70/guo17a.html

## 16) Round 2 Integration (Completed)

### 16.1 Model routing policy by horizon
1. `1m`: LOB/event-time stack first (`Hawkes`/LOB-aware + GBM); deep LOB models only if true depth data and stable retraining exist.
2. `15m`: GBM default (`LightGBM/CatBoost`) with microstructure/funding/regime features; shallow sequence residual optional.
3. `4h`: GBM + regularized linear baseline; optional small GRU/TCN residual only if post-cost walk-forward uplift is persistent.
4. `1d`: ElasticNet/Ridge + GBM with exogenous overlays (on-chain, macro, cross-asset).
5. Deep/transformer models are challenger-only and require demonstrated net-of-cost advantage before promotion.

### 16.2 Execution cost stack (required in all score-to-trade decisions)
Use per-leg expected edge accounting:

```text
NetEdge_bps = AlphaGross_bps(H_eff) - Sum(CostLeg_bps) - TransferBorrow_bps
Trade only if NetEdge_bps > SafetyBuffer_bps
```

Cost legs must include:
1. Explicit fees/rebates.
2. Spread half-cost (taker) or non-fill + adverse selection (maker).
3. Market impact (book sweep + square-root fallback).
4. Latency drift and stale-book penalty.
5. Perp funding carry over expected holding window.
6. Transfer/settlement delay where cross-venue hedging is used.

### 16.3 Portfolio sizing policy (risk-first)
1. Universe liquidity gate: 30d ADV >= 20x expected daily turnover.
2. Base allocation: HRP (>=4 assets), else inverse-vol with hard caps.
3. Vol forecast: conservative `sigma_i = max(EWMA_20d, EWMA_60d)`.
4. Vol targeting: default crypto sleeve target around 10% annualized.
5. Kelly policy: fractional only (0.10x-0.25x default, 0.50x hard cap) and only for validated edges.
6. Drawdown governor:
   - DD <10% -> 1.00x risk
   - 10-15% -> 0.75x
   - 15-20% -> 0.50x
   - 20-25% -> 0.25x
   - >25% -> 0.00x-0.25x (defensive mode)

### 16.4 Labeling and objective schema (new default)
Default stack for non-stationary crypto:
`event-driven sampling + volatility-scaled triple-barrier + meta-labeling + calibrated probabilities + cost/utility-aware loss`.

Recommended starting labels:
1. 4h model:
   - Triple barrier target `{-1,0,+1}`
   - PT ≈ `1.25σ-1.5σ`, SL ≈ `1.0σ`, vertical barrier `24h-48h`
2. 1d model:
   - Triple barrier target `{-1,0,+1}`
   - PT ≈ `2σ-3σ`, SL ≈ `1.5σ-2σ`, vertical barrier `5-10 days`
3. Meta-label target:
   - `1` if realized post-cost return positive, else `0`

Objective guidance:
1. Direction model: cost-sensitive BCE/asymmetric directional loss.
2. Entry/size model: calibrated probability with monotone size mapping.
3. Policy objective: include turnover, drawdown, and execution-cost penalties.

### 16.5 Revised deployment gates from Round 2
1. No model promotion without post-cost alpha pass under execution stress tests (2x spread/latency/impact scenario).
2. No sizing from uncalibrated probabilities.
3. No deep model promotion unless it outperforms GBM baseline post-cost in repeated walk-forward windows.
4. No trade if latency-adjusted edge half-life implies expected alpha decay below cost stack.

## 17) Round 2 Additional Sources
- [Hawkes-based cryptocurrency forecasting via limit order book data](https://arxiv.org/abs/2312.16190)
- [Exploring Microstructural Dynamics in Cryptocurrency Limit Order Books](https://arxiv.org/abs/2506.05764)
- [HLOB: Information Persistence and Structure in Limit Order Books](https://arxiv.org/abs/2405.18938)
- [DeepLOB: Deep CNNs for Limit Order Books](https://arxiv.org/abs/1808.03668)
- [A Million Metaorder Analysis of Market Impact on Bitcoin](https://arxiv.org/abs/1412.4503)
- [The Good, the Bad, and Latency: Exploratory Trading on Bybit and Binance](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4677989)
- [Perpetual Futures Contracts and Cryptocurrency Market Quality](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4218907)
- [Adverse Selection in Cryptocurrency Markets](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4175306)
- [Volatility-Managed Portfolios](https://www.nber.org/papers/w22208)
- [On the Performance of Volatility-Managed Portfolios](https://www.sciencedirect.com/science/article/pii/S0304405X2030132X)
- [Risk-Constrained Kelly Gambling](https://arxiv.org/abs/1603.06183)
- [Can Adaptive Seriational Risk Parity Tame Crypto Portfolios?](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3877143)
- [Algorithmic crypto trading using information-driven bars, triple barrier labeling and deep learning](https://link.springer.com/article/10.1186/s40854-025-00866-w)
- [Enhanced GA-driven triple-barrier labeling for crypto pair trading](https://www.mdpi.com/2227-7390/12/5/780)
- [Mean Absolute Directional Loss (MADL)](https://arxiv.org/abs/2309.10546)

---

**Status:** Draft v2.0 (Round 2 integrated; ready for implementation task breakdown).
