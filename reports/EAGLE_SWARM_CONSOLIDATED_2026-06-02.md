# EAGLE Swarm Consolidated Analysis — 2026-06-02

**Models Reviewed**: Claude Opus 4.7, DeepSeek v4, Mimo v2.5 Pro, GPT-5.4, minimax-m3-free
**Date**: 2026-06-02
**Purpose**: Synthesize all EAGLE reviews into actionable strategy recommendations per asset class

---

## EXECUTIVE SUMMARY — SWARM CONSENSUS

**All 5 models agree on the core diagnosis**: The project does NOT have a "wait longer" problem. It has a **research-to-production translation problem** plus **backtesting infrastructure failures** plus **data/resolver contamination**.

### Swarm Verdict on Each Asset Class

| Asset Class | Swarm Consensus | Best Strategy | Expected Edge | Confidence |
|---|---|---|---|---|
| **CRYPTO** | SHORT-only is the edge | VWAPReversion (symbol-fragmented, 10% cap) | PF 1.3-2.5, WR 55-67% | HIGH |
| **EQUITY** | LONG-only, sector-gated | Faber TAA on XLE/XLU/XLV/XLI/XLK | PF 1.5+, WR 60%+ | MEDIUM |
| **ETF** | LONG-only, dual momentum | Verified Dual Momentum (8 sector ETFs) | PF 1.6, WR 54% | HIGH |
| **FOREX** | FREEZE until sign-flip purge | kimi inversion (post-purge only) | PF 1.0-1.5, WR 45%+ | LOW |
| **COMMODITY** | FREEZE until COT lag fix | CTA trend on broadened set (GC=F, SI=F, NG=F) | PF 1.5+, WR 58%+ | LOW |
| **BOND** | Paper-only 60d | HYG/LQD credit momentum | PF 1.3-1.6 | MEDIUM |
| **FUTURES** | FREEZE (n=2 is not a class) | None until COT + slippage fix | N/A | N/A |

---

## 1. WHERE THE EDGE ACTUALLY IS (Data-Backed)

### AI Tournament Top 5 T1 Models — Edge Matrix

| Asset Class | WR | PF | Avg PnL | n | Swarm Verdict |
|---|---|---|---|---|---|
| **PENNY** | 75.0% | 6.80 | +12.81% | 88 | STRONGEST EDGE (but concentration risk) |
| **ETF** | 67.6% | 4.32 | +2.51% | 105 | STRONG — best promotion candidate |
| **EQUITY** | 63.6% | 3.77 | +3.74% | 206 | STRONG — needs sector gating |
| **FUTURES** | 65.0% | 5.14 | +2.49% | 20 | STRONG (small n) |
| **COMMODITY** | 58.6% | 2.02 | +1.52% | 145 | MODERATE |
| **FOREX** | 70.6% | 1.47 | +0.23% | 34 | MARGINAL (WR-PF gap) |
| **BOND** | 61.5% | 1.11 | +0.11% | 52 | MARGINAL |
| **CRYPTO** | 41.7% | 1.22 | +0.62% | 216 | WEAK — directionally wrong |

### Best Personas (Top 5 T1 Models, min 10 resolved)

| Persona | WR | PF | Avg PnL | n | Classification |
|---|---|---|---|---|---|
| **macro_hedge** | 97% | 5.89 | +5.89% | 38 | EDGE (ETF macro hedges) |
| **microcap_momentum** | 83% | 6.20 | +15.58% | 46 | EDGE (PENNY) |
| **pivot_catcher** | 77% | 2.94 | +6.17% | 22 | EDGE |
| **momentum_momentum** | 72% | 2.51 | +6.48% | 40 | EDGE (EQUITY 3-6m mom+vol) |
| **gamma_raid** | 67% | 2.33 | +9.78% | 42 | EDGE (PENNY) |
| **cta_trend** | 63% | 1.35 | +2.21% | 43 | EDGE (COMMODITY/FUTURES) |
| **trend_follower** | 64% | 1.44 | +4.06% | 39 | EDGE (EMA cross) |
| **cycle_rotator** | 64% | 1.57 | +4.49% | 44 | EDGE (EQUITY macro) |

### Kill List (Confirmed Noise)

| Persona | WR | PF | Avg PnL | n | Action |
|---|---|---|---|---|---|
| **momentum_scalp** | 28% | 0.55 | -1.02% | 47 | KILL |
| **breakout_scanner** | 28% | 0.46 | -1.66% | 36 | KILL |
| **reflexivity_trader** | 35% | 0.60 | -0.60% | 34 | KILL |
| **deep_value** | 44% | 0.59 | -0.59% | 18 | KILL |

### Directional Kill List

| Class | Direction | WR | Avg PnL | Action |
|---|---|---|---|---|
| **CRYPTO** | **LONG** | **33%** | **-0.49%** | **FLIP TO SHORT** |
| PENNY | SHORT | 15% | -6.01% | KILL |
| COMMODITY | SHORT | 18% | -2.15% | KILL |
| ETF | SHORT | 22% | -1.05% | KILL |
| EQUITY | SHORT | 39% | +0.10% | KILL (marginal) |

---

## 2. BACKTESTING INFRASTRUCTURE — 5 CRITICAL FLAWS

All models agree: **the strategies don't suck, the backtesting infrastructure does.**

### Flaw 1 — MC Null is Bootstrap-With-Replacement (CRITICAL)

```python
# BROKEN: strategy_verification_engine.py:243-245
for _ in range(self.mc_iterations):
    resampled = np.random.choice(pnls, size=len(pnls), replace=True)
```

**Impact**: Destroys serial structure. For trend/momentum strategies, bootstrap null ≈ strategy itself → p ≈ 0.50 always. FaberTAA SPY has Sharpe 1.74, PF 5.69, but MC p-value 0.507 (looks like noise).

**Fix**: Switch to **block bootstrap** (preserves autocorrelation) OR **random-trade-entry on same price series** (preserves regime).

### Flaw 2 — DSR Uses Fixed n_trials=100

```python
# BROKEN: rigorous_backtest_harness.py:61
DSR_PARAMS = {'n_trials': 100, ...}
```

**Impact**: Real N across project is ~500-1000. DSR is over-optimistic by 5-10×. BollingerMR DSR 11.58 would be ~1-2 if corrected.

**Fix**: Feed real N from `hypothesis_registry.json` (already exists).

### Flaw 3 — PBO Uses Random Sign Flips

```python
# BROKEN: rigorous_backtest_harness.py:391-395
signs = np.random.choice([-1, 1], size=n)
pnl_matrix = np.column_stack([pnl_matrix, pnl_costed * signs])
```

**Impact**: PBO values are meaningless — they'll always look good. Bailey & Lopez de Prado (2015) requires comparing best IS strategy against other truly tested strategies.

**Fix**: Real k-fold combinatorial partition of actual parameter grid. The 8-fold purged WF at `rigorous_backtest_harness.py:249-320` is already coded but never called.

### Flaw 4 — Walk-Forward Single 70/30 Split, No Purge, No Embargo

```python
# BROKEN: walkforward_suite.py:50-62
cut = int(len(dated) * train_frac)
is_trades = dated[:cut]; oos_trades = dated[cut:]
```

**Impact**: No temporal buffer. Autocorrelated features (EMA, MACD, RSI) leak across boundary. Walk-forward decay numbers are not validated.

**Fix**: 8-fold purged rolling WF with embargo = max hold period.

### Flaw 5 — No Transaction Costs in 4 of 5 Modules

**Impact**: Losing strategies appear profitable. The repo has excellent cost models (`slippage_model.py`, `transaction_costs.py`) but NONE are wired to backtest engines.

**Fix**: Wire existing cost models to all backtest modules.

### The 5-Module Inconsistency Problem

| Feature | rigorous_harness | walk_forward | battle_test | real_data_backtest | monte_carlo_validator |
|---|---|---|---|---|---|
| Walk-forward | PnL split (broken) | Rolling eval (no optimization) | Step=1 | None (data snooping) | K-fold on PnL |
| Purge/embargo | Yes (cosmetic) | **No** | **No** | **No** | **No** |
| Transaction costs | Flat per-trade | **None** | **None** | **None** | **None** |
| DSR | Simplified formula | Correct formula | **None** | **None** | **None** |
| PBO | Sign flips (broken) | **None** | **None** | **None** | **None** |

**Five modules, five different implementations, none fully correct.**

---

## 3. PER-ASSET-CLASS STRATEGY RECOMMENDATIONS

### 3.1 CRYPTO — SHORT-Only Edge

**Current State**: PF 0.98, WR 39.7%, n=229 (policy-clean)
**Root Cause**: Production scanner emits CRYPTO as LONG when real edge is SHORT
**Swarm Fix**: Flip all CRYPTO LONG to SHORT

**Strategies with verified edge (lab)**:

| Strategy | n (OOS) | OOS Sharpe | OOS PF | DSR | PBO | Verdict |
|---|---|---|---|---|---|---|
| VWAPReversion | 516 | **3.10** | 1.32 | 2.76 | 0.24 | shadow |
| BollingerMR | 38 | 1.38 | 1.67 | 11.58 | 0.48 | shadow |
| DualMomentumCrypto | 82 | 0.54 | 1.13 | 16.21 | 0.24 | shadow |

**Action Items**:
1. Flip CRYPTO emission to SHORT-only (EAGLE-4 already implemented)
2. Fragment VWAPReversion: 10% cap per symbol
3. Fix 1864 duplicate signal-ts + EXPIRED→WON mislabels
4. Audit `claude_gainer_st` 91.7% concentration
5. Run 30-day shadow paper alongside production

**Safe Long-Term Picks** (well-known, diversified):
- **BTCUSD** — institutional adoption, halving cycle, store of value thesis
- **ETHUSD** — DeFi staking yield, layer-2 growth
- **SOLUSDT** — high-throughput chain, meme coin ecosystem

### 3.2 EQUITY — LONG-Only, Sector-Gated

**Current State**: PF 0.90, WR 33%, n=33 (policy-clean)
**Root Cause**: Honest failure — bad deployed strategies, weak emitter quality
**Swarm Fix**: Sector-gate Faber TAA on XLE/XLU/XLV/XLI/XLK

**Strategies with verified edge**:

| Strategy | Evidence | Confidence |
|---|---|---|
| **stocks_rsi2_pullback** | n=70, WR=62.9%, only proven equity sleeve | MEDIUM |
| **Faber TAA** | Sharpe 1.74 on SPY, 1.65 on QQQ | MEDIUM |

**Best Symbols** (AI tournament data):
- BAC (100% WR), JPM (90%), MSFT (88%), AMZN (82%), GOOGL (80%), AAPL (80%), TSLA (73%), AMD (73%), NVDA (64%)

**Safe Long-Term Picks**:
- **NVDA** — AI/gpu monopoly, data center growth, autonomous driving
- **MSFT** — cloud computing, AI integration, recurring revenue
- **AAPL** — services moat, buybacks, ecosystem lock-in
- **AMZN** — AWS dominance, e-commerce, AI infrastructure

### 3.3 ETF — Best Promotion Candidate

**Current State**: PF 1.18, WR 54%, n=161
**Root Cause**: Sample too narrow (Verified DM is XLK-only, n=20)
**Swarm Fix**: Full sector universe backtest + shadow paper

**Strategies with verified edge**:

| Strategy | Evidence | Confidence |
|---|---|---|
| **ETF Dual Momentum** | Walk-forward validated, PF 1.60, n=104, WR 53.8% | HIGH |
| **ETF Sector Rotation** | Backtest shows edge | MEDIUM |

**Best ETF Symbols** (AI tournament):
- EEM (93% WR), IWM (75%), GLD (68%), XLE (67%)

**Safe Long-Term Picks**:
- **SPY** — S&P 500, broad market exposure
- **QQQ** — Nasdaq 100, tech-heavy growth
- **EEM** — Emerging markets, diversification
- **GLD** — Gold, inflation hedge

### 3.4 FOREX — FREEZE Until Sign-Flip Purge

**Current State**: PF 0.56, WR 31%, n=74
**Root Cause**: kimi sign-flip contamination (142/367 = 38.7%), vol mismatch with crypto
**Swarm Fix**: Freeze emission, run sign-flip purge, rebuild with ATR-normalized thresholds

**Action Items**:
1. Freeze FOREX emission
2. Run zoo's 367-row sign-flip purge (luxalgo 6 → ml 15 → battleground 63 → mega 141 → kimi 142)
3. Rebuild with ATR-normalized thresholds + per-pair vol scaling
4. 30d paper before any live resume

### 3.5 COMMODITY — FREEZE Until COT Lag Fix

**Current State**: PF 0.23, WR 18.8%, n=16
**Root Cause**: COT publication lag = look-ahead bias, CT=F 57% concentration
**Swarm Fix**: Kill emission, enforce 3-day COT lag, broaden symbol set

**Action Items**:
1. Enforce 3-day COT publication lag at signal receipt
2. Remove CT=F from universe
3. Rebuild with GC=F, SI=F, NG=F, HG=F, ZC=F
4. 60d post-fix live test

### 3.6 BOND — Paper-Only 60d

**Current State**: PF 0.67, WR 55.6%, n=11
**Root Cause**: Cold start since FRED 2026-05-03, data gap
**Swarm Fix**: Paper-only 60d on HYG/LQD

**Safe Long-Term Picks**:
- **TLT** — 20+ Year Treasury, rate-sensitive
- **HYG** — High Yield Corporate, income
- **LQD** — Investment Grade Corporate, moderate risk

### 3.7 FUTURES — FREEZE (n=2 is not a class)

**Current State**: n=2
**Root Cause**: Not enough data, concentration/artifact risk
**Swarm Fix**: Freeze. No revival without COT lag fix + slippage-adjusted BT + 50 paper trades.

---

## 4. STATISTICAL MEASURES FOR "REAL MONEY READY"

### Top 3 Non-Negotiable Tests (ollama-cloud-local consensus)

| Test | What It Measures | Minimum Threshold |
|---|---|---|
| **Sharpe Ratio** | Risk-adjusted return | > 1.0 (bare minimum), > 1.5 (professional), > 2.0 (excellent) |
| **PnL Normality (Jarque-Bera)** | Whether returns are normally distributed | p-value > 0.05 |
| **Out-of-Sample Walk-Forward** | Robustness / overfitting detection | Consistent positive performance across folds |

### Complete Statistical Measures Table

| Measure | Why It Matters | Threshold |
|---|---|---|
| Annualized Sharpe Ratio | Risk-adjusted return | ≥ 1.0 (Sharpe) or ≥ 0.8 (IR) after slippage |
| Profit-Factor (PF) | Gross profit / gross loss | ≥ 1.5 (bare minimum) → ≥ 2.0 (ideal) |
| Win-Rate (WR) | % winning trades | 45-55% acceptable if PF strong |
| Maximum Drawdown (MDD) | Tail risk | ≤ 20% (monthly) or Calmar ≥ 3.0 |
| Turnover | Cost inflation | ≤ 30%/yr equities/ETFs; ≤ 70%/yr crypto/FX |
| Liquidity-Adjusted Slippage | Expected slippage per trade | ≤ 5 bps large-cap; ≤ 15 bps crypto/FX |
| Regime-Robustness Score | Consistency across regimes | PF/Sharpe within ±10% across ≥ 3 of 4 regimes |
| Multiple-Testing (DSR/PBO/SPA) | Data-snooping control | Adjusted p-value < 0.05 |
| HHI Source Concentration | Single source dominance | < 0.20 for aggregate portfolio |
| OOS Decay | Overfitting detection | PF OOS ≥ 80% of IS PF; Sharpe OOS ≥ 70% of IS Sharpe |

### Bare-Minimum Backtesting Checklist

| Step | Description | Minimal Implementation |
|---|---|---|
| a. Data hygiene | Clean, policy-approved data | CSV audit + duplicate filter |
| b. Pre-registration | Log hypothesis before backtest | Text file or internal ticket |
| c. Split-sample test | One simple IS/OOS split | 70%/30% train-test |
| d. Cost & slippage model | Flat per-trade cost | 5 bps + linear slippage |
| e. Basic performance metrics | PF, Sharpe, WR, MDD, turnover | pandas/NumPy |
| f. Multiple-testing guard | Bonferroni correction | p-value = α / N |

### Ideal (Production-Grade) Pipeline

| Component | Ideal Practice |
|---|---|
| Data provenance | source_id, fallback, timestamp, version on every record |
| Purged-embargoed walk-forward | 30-day purge + 10-day embargo per fold |
| Block-bootstrap CIs | 1,000 resamples preserving temporal dependence |
| Regime-segmented analysis | Separate perf for low-vol, high-vol, trending, mean-reverting |
| Full cost model | Asset-class-specific commissions, impact, latency |
| Multiple-testing correction | DSR/PBO/SPA with real N from hypothesis registry |
| Shadow-size simulation | ≤ 0.5% capital for 4-8 weeks |
| Automated monitoring | Real-time PF, WR, MDD, HHI, resolver dispute rate |
| Versioned strategy repo | Git-tracked code, config, hyper-parameters |

### Forward-Testing Guidelines

| Aspect | Recommended Practice |
|---|---|
| Number of picks | Minimum 30-50 distinct symbols per asset class |
| Duration | ≥ 2× longest look-back window |
| Capital allocation | ≤ 0.5% per strategy; monitor 4-8 weeks |
| Performance thresholds | Live PF within ±10% of back-tested PF |
| Regime exposure | Cover ≥ 3 distinct market regimes |
| Statistical validation | Re-run block-bootstrap on live P&L; 95% CI for PF should not cross 1.0 |

---

## 5. IMMEDIATE ACTION PLAN (12-Week Horizon)

### Week 1-2: Data Hygiene (STOP THE BLEEDING)

| # | Action | Owner | Status |
|---|---|---|---|
| 1 | Freeze FOREX emission | code | Verify PR #6 still active |
| 2 | Freeze COMMODITY emission | code | New |
| 3 | Freeze FUTURES emission | code | New |
| 4 | Run 367-row sign-flip purge | operator | PR #433 staged |
| 5 | Set SIGN_FLIP_BASELINE=0 | operator | Pending |
| 6 | Land PR #437 (tournament resolver) | merge | CI pending |
| 7 | Quant ops monitor | code | Shipped (EAGLE-2 MIMO) |
| 8 | Mutation framework | code | Shipped (EAGLE-2 MIMO) |
| 9 | Admissibility pipeline | code | Shipped (EAGLE-2 MIMO) |

### Week 3-4: Methodology Fixes

| # | Action | File | Effort |
|---|---|---|---|
| 10 | Fix MC null → block bootstrap | strategy_verification_engine.py:243 | 1 day |
| 11 | Wire DSR n_trials to registry | rigorous_backtest_harness.py:61 | 0.5 day |
| 12 | Fix PBO → real k-fold partitions | rigorous_backtest_harness.py:391 | 1 day |
| 13 | 8-fold purged + embargoed WF | walkforward_suite.py:50 | 1 day |
| 14 | Per-class realistic slippage | strategy_verification_engine.py | 0.5 day |

### Week 5-6: Promotion Pipeline

| # | Action | Detail |
|---|---|---|
| 15 | Wire tournament picks through admissibility | deepseek_v4, gpt4o, grok3 |
| 16 | Start 30d shadow paper for ETF DM | First money-ready candidate |
| 17 | Run walk-forward on VWAPReversion + BollingerMR | CRYPTO candidates |
| 18 | Sector-gate Faber TAA on XLE/XLU/XLV/XLI/XLK | EQUITY candidate |

### Week 7-8: Shadow Sizing

| # | Action | Detail |
|---|---|---|
| 19 | Shadow-size ETF DM (0.2% capital) | 30d forward proof |
| 20 | Shadow-size CRYPTO VWAP (0.2% capital) | 30d forward proof |
| 21 | Mutation testing on failed lab sleeves | 3-axis: invert, symbol rotation, regime gate |

### Week 9-10: Promotion Decision

| # | Action | Detail |
|---|---|---|
| 22 | Evaluate ETF DM forward PF | Promote if PF > 1.3, WR > 50% |
| 23 | Evaluate CRYPTO VWAP forward PF | Promote if PF > 1.2, WR > 55% |
| 24 | Cap kimi_riseoftheclaw at 40% | Reduce source concentration |

### Week 11-12: Full Rollout

| # | Action | Detail |
|---|---|---|
| 25 | 1× sizing for ETF DM (if validated) | First production strategy |
| 25 | 1× sizing for CRYPTO VWAP (if validated) | Second production strategy |
| 26 | Deploy Grafana monitoring dashboard | Real-time alerts |
| 27 | Update Quant Ops Dashboard | Live metrics |

---

## 6. LEVERAGING API KEYS & LITELLM PROXY

### Available Models via LiteLLM (localhost:4000)

| Model | Status | Use Case |
|---|---|---|
| ollama-cloud-large | ✅ Working | Deep strategy brainstorming |
| ollama-cloud | ✅ Working | Quick strategy iteration |
| ollama-cloud-local | ✅ Working | Statistical validation |
| paid-mode / free-mode | ✅ Available | Production workloads |
| hybrid-model | ✅ Available | Balanced cost/quality |
| cloudflare-llama | ✅ Available | Fast inference |

### API Keys Available (from dbpasses.txt)

| Provider | Key Status | Best Use |
|---|---|---|
| NVIDIA (nvapi-*) | ✅ Active | DeepSeek v4, Nemotron |
| Groq (gsk_*) | ✅ Active | Fast Llama inference |
| Google Gemini (AIza*) | ✅ Active | Gemini 2.5 Pro/Flash |
| Together AI (tgp_*) | ✅ Active | Mixtral, Llama |
| Fireworks (fw_*) | ✅ Active | Fast inference |
| DeepInfra | ✅ Active | Open models |
| SambaNova | ✅ Active | Fast inference |
| Cerebras | ✅ Active | Ultra-fast inference |
| OpenRouter (sk-or-*) | ✅ Active | Multi-model routing |
| Anthropic (sk-ant-*) | ✅ Active | Claude models |
| OpenAI (sk-proj-*) | ✅ Active | GPT-4o, o3 |
| xAI/Grok (xai-*) | ✅ Active | Grok-3 |
| DeepSeek (sk-0a*) | ✅ Active | DeepSeek v4 |
| Kimi/Moonshot (sk-Bi*) | ✅ Active | Kimi K2.6 |
| Qwen (sk-sp-*) | ✅ Active | Qwen 3 |

### Recommended Multi-Model Brainstorming Approach

1. **Strategy Generation**: Fan to NVIDIA (DeepSeek v4) + Groq (Llama 3.3 70B) + Gemini for parallel strategy ideas
2. **Statistical Validation**: Use ollama-cloud-local for quick Sharpe/PF/WR calculations
3. **Cross-Validation**: Send top strategies to OpenRouter for independent verification
4. **Documentation**: Use Claude Opus for final strategy documentation

---

## 7. SAFE LONG-TERM PICKS (Well-Known, Diversified)

### CRYPTO (Conservative)
| Symbol | Thesis | Risk Level |
|---|---|---|
| BTCUSD | Institutional adoption, halving cycle, store of value | MEDIUM |
| ETHUSD | DeFi staking yield, layer-2 growth, ultrasound money | MEDIUM |
| SOLUSDT | High-throughput chain, meme coin ecosystem | HIGH |

### EQUITY (Conservative)
| Symbol | Thesis | Risk Level |
|---|---|---|
| NVDA | AI/gpu monopoly, data center growth | MEDIUM |
| MSFT | Cloud computing, AI integration, recurring revenue | LOW |
| AAPL | Services moat, buybacks, ecosystem lock-in | LOW |
| AMZN | AWS dominance, e-commerce, AI infrastructure | MEDIUM |
| GOOGL | Search monopoly, AI/Cloud growth | LOW-MEDIUM |
| JPM | Banking leader, rate environment beneficiary | LOW |
| BAC | Banking exposure, rate sensitivity | LOW-MEDIUM |

### ETF (Conservative)
| Symbol | Thesis | Risk Level |
|---|---|---|
| SPY | S&P 500, broad market exposure | LOW |
| QQQ | Nasdaq 100, tech-heavy growth | LOW-MEDIUM |
| EEM | Emerging markets, diversification | MEDIUM |
| GLD | Gold, inflation hedge | LOW |
| XLE | Energy sector, oil exposure | MEDIUM |

### BOND (Conservative)
| Symbol | Thesis | Risk Level |
|---|---|---|
| TLT | 20+ Year Treasury, rate-sensitive | LOW |
| HYG | High Yield Corporate, income | MEDIUM |
| LQD | Investment Grade Corporate | LOW-MEDIUM |

---

## 8. KEY INSIGHTS FROM SWARM REVIEW

### Consensus Points (All 5 Models Agree)

1. **Research ≠ Production**: The lab has real sleeves, but those are not what dominates live picks
2. **Backtesting is broken**: 5 modules with inconsistent implementations, none fully correct
3. **Data contamination**: Sign-flips, resolver mislabels, concentration artifacts
4. **CRYPTO direction is wrong**: LONG when it should be SHORT
5. **ETF is the best promotion candidate**: Verified DM PF 1.60, cleanest data feed
6. **30-day shadow paper is non-negotiable**: No amount of backtesting substitutes
7. **Freeze FOREX/COMMODITY/FUTURES**: Stop the bleeding while fixes land
8. **ML confidence is inverted**: High confidence = LOW win rate (anti-predictive)

### Disagreement Points

| Question | Model A | Model B |
|---|---|---|
| Is EQUITY honest failure? | Yes (Claude, GPT-5.4) | Methodology artifact (DeepSeek) |
| Should we invert FOREX? | Yes, kimi evidence (Claude) | Only after sign-flip purge (Mimo) |
| Is PENNY edge real? | Yes, strongest (minimax) | Concentration risk (Claude) |
| Priority: fix backtest or data? | Backtest first (Claude) | Data first (GPT-5.4) |

### Single Biggest Unlock

**Fix the MC null hypothesis** at `strategy_verification_engine.py:243`. Switch from bootstrap-with-replacement to block bootstrap. Expected impact: 4+ currently-rejected strategies promote to B-Tier+.

---

## 9. SUCCESS METRICS (Quarterly Review)

| Metric | Target |
|---|---|
| Deployable Edge | ≥ 2 capital-ready sleeves (live PF ≥ 1.5, WR ≥ 50%) |
| Data Cleanliness | Resolver dispute rate < 1% across all live feeds |
| Concentration | HHI for aggregate book < 0.20 |
| Operational Efficiency | End-to-end validation pipeline latency ≤ 5 min/sleeve |

---

*Consolidated from 5 EAGLE reviews: Claude Opus 4.7, DeepSeek v4, Mimo v2.5 Pro, GPT-5.4, minimax-m3-free*
*Date: 2026-06-02*
*EAGLE2 Initiative — Swarm Analysis*
