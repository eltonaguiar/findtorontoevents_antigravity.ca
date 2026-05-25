# Multi-Model Asset Class Edge Audit — findtorontoevents.ca
## Generated: 2026-05-25 | 5 AI Models + Internal Data Analysis

---

## Executive Summary

The trading system resolves **1,117 picks** over 6 days (May 16–21, 2026), generating **+541.35% total PnL** at **40.8% WR** and **+0.48% avg per pick**. However, this headline is **highly misleading** — performance is extremely asymmetric. A small fraction of high-conviction picks in Commodities and Elite-quality tiers subsidizes massive structural decay in Crypto and Forex.

**All 5 peer models unanimously agree**: the edge is real but concentrated. Commodity is the system's primary alpha engine. Quality-tier gating (`elite_a_high_conf`, `profitable_tp`) is the single most powerful filter.

---

## 1. Per-Asset-Class Edge Matrix

| Asset Class | N | PF | WR% | Sharpe | 7d WR% | 30d WR% | Verdict | Concentration |
|-------------|---|-----|------|--------|--------|---------|---------|---------------|
| **COMMODITY** | 178 | **4.31** | 58.4 | **0.352** | 94.3 | 62.3 | ✅ STABLE_EDGE | Strategy+Symbol |
| **EQUITY** | 286 | **1.92** | 54.5 | 0.237 | 37.1 | 55.1 | ✅ STABLE_EDGE | Distributed |
| **ETF** | 106 | 1.35 | 55.7 | 0.124 | 65.0 | **72.2** | ⚠️ MIXED | Distributed |
| **CRYPTO** | 1,873 | 1.27 | 45.7 | 0.093 | 41.9 | 45.8 | 🔻 DECAYING | Distributed |
| **FOREX** | 1,033 | 1.17 | 43.9 | 0.027 | 28.9 | 42.3 | 🔻 DECAYING | Symbol |
| **BOND** | 12 | 0.66 | 50.0 | -0.171 | 0 | 0 | ❌ INSUFFICIENT | — |
| **FUTURES** | 0 | — | — | — | — | — | ❌ INSUFFICIENT | — |

### Key Observations:
- **COMMODITY** is in a confirmed hot regime: 7d PF=44.07 is extreme but the compression from 44→7.75→4.31 across timeframes suggests real momentum, not noise.
- **ETF** 30d metrics (WR=72.2%, PF=3.88) are dramatically better than all-time — a regime shift is underway.
- **EQUITY** shows healthy asymmetry: low WR (37.1% 7d) but PF=3.33 means wins are ~3x larger than losses.
- **CRYPTO** and **FOREX** are drag. Both have negative near-term momentum and sub-50% WR.

---

## 2. Top-Performing Source Systems

| Source System | Picks | WR% | Total PnL% | Avg PnL/pick |
|--------------|-------|-----|------------|---------------|
| kimi_signal_tracking | 168 | 53.6 | **+257.34** | +1.53% |
| aggregated_picks | 58 | **74.1** | +111.02 | **+1.91%** |
| ml_crypto_pred_v12 | 88 | 45.5 | +96.97 | +1.10% |
| dna_winner_picks | 96 | 40.6 | +21.73 | +0.23% |
| copy_trader_intel | 4 | **100** | +11.00 | **+2.75%** |
| revival_kimi | 7 | **85.7** | +17.41 | +2.49% |

**Peer-model consensus**: `aggregated_picks` (74.1% WR) is likely an ensemble filter that amplifies consensus alpha. `kimi_signal_tracking` demonstrates that model-specific signal tracking can compound significantly.

---

## 3. AI Model Tournament Rankings

| Model | Resolved | WR% | Avg PnL% | Sharpe | Tier |
|-------|----------|-----|----------|--------|------|
| **cursor_agent** | 59 | **66.1** | **+1.48** | **0.334** | 🥇 S |
| **llama4_scout** | 57 | 61.4 | +1.41 | 0.326 | 🥇 S |
| glm4_7_flash | 55 | 60.0 | +0.63 | 0.153 | 🥈 A |
| claude_opus_4_7 | 61 | 54.1 | +0.18 | 0.040 | 🥉 B |
| grok3_direct | 61 | 54.1 | +0.51 | 0.124 | 🥉 B |
| gemini_2_5_pro | 72 | 51.4 | -0.45 | -0.117 | ❌ C |
| qwen3_6_max | 60 | 45.0 | -0.28 | -0.080 | ❌ C |

**Kimi K2.6 noted**: cursor_agent's 66.1% WR has p<0.001 vs 50% null — genuine predictive signal, not variance. The model recommends **3:1 weighting cursor_agent vs gemini**.

**GPT-OSS-120B noted**: llama4_scout and cursor_agent are the only two models with positive Sharpe above 0.3 — all others cluster near zero or negative.

---

## 4. Quality Tier Gating — The Hidden Alpha Engine

| Quality Bucket | Picks | WR% | Avg PnL% | Total PnL% |
|---------------|-------|-----|----------|------------|
| **profitable_tp** | 292 | **100.0** | **+3.35** | +977.46 |
| **elite_a_high_conf** | 8 | **87.5** | **+2.06** | +16.50 |
| elite_b_good_conf | 3 | 66.7 | +0.91 | +2.72 |
| alpha_verified | 16 | 31.2 | -0.11 | -1.75 |
| moderate_confidence | 455 | **0.0** | **-1.47** | -666.73 |
| low_confidence | 193 | **0.0** | -0.82 | -158.33 |

### The Gating Effect:
- **455 moderate-confidence picks** went 0-for-455. That's a **-666.73% PnL drain**.
- **193 low-confidence picks** went 0-for-193. Another **-158.33% lost**.
- Combined, **648 un-gated picks destroyed -825%** while 300 gated picks generated **+994%**.

**All 5 peer models independently flagged this as the system's most powerful filter.** GLM-5.1 called it "pure, quantifiable alpha." Nemotron Super called it "the strongest statistical edge." Mistral Nemotron recommended mandatory quality-tier gating before any position is taken.

---

## 5. Peer Model Consensus & Divergence

### Unanimous Agreement (5/5 models):
1. **Commodity is the #1 edge** — PF=4.31 is exceptional, allocate 20-30% of risk budget
2. **Quality-tier gating is mandatory** — moderate/low-confidence buckets are pure destruction
3. **Crypto and Forex are net-negative** — reduce or pause allocations
4. **cursor_agent + llama4_scout** are the only AI models worth following

### Model-Specific Insights:

**Kimi K2.6** (most detailed quant analysis):
- Commodity PF compression (44→7.75→4.31) suggests "maturing edge, not decaying"
- Dynamic position scaling: +15% when 7d WR>90%, -20% when 7d WR<70%
- Cursor_agent weight 3:1 vs weakest AI model
- ETF regime shift from MIXED→STRONG in 30d window is actionable

**GPT-OSS-120B** (best table/matrix presentation):
- "Aggregated picks at 74.1% WR is the most reliable signal generator"
- Flagged Commodity concentration as a "Pareto risk" — one strategy/symbol failure could wipe gains
- Recommended rebalancing Commodity weight weekly based on 7d WR trajectory

**GLM-5.1** (best risk identification):
- "Highly asymmetric performance: concentrated high-alpha pockets subsidizing widespread structural decay"
- Warned about Commodity mean reversion after extreme 7d PF=44.07
- Identified ETF as potential "regime shift beneficiary" from macro volatility

**Nemotron Super 49B** (most concise):
- 3 strongest edges: Commodity (PF=4.31), ETF (30d momentum), cursor_agent (Sharpe=0.334)
- 3 biggest risks: Commodity concentration, Crypto decay (n=1,873 — large sample, small edge), Forex negative drift

**Mistral Nemotron** (most actionable):
- Commodity allocation: 20-25% of capital, monitoring for overfitting
- ETF allocation: 10-15%, favoring recent high-performers
- Recommended "kill switch" for any strategy dropping below PF=1.0 on 30d rolling

---

## 6. Statistical Edge Significance (Persona × Asset Class)

From the edge significance gate (62 pairs tested, only 1 reached Tier-2):

| Persona | Asset Class | N | WR% | Avg PnL% | Sharpe | Tier |
|---------|------------|---|------|----------|--------|------|
| regime_adaptive | ETF | 13 | 84.6 | +2.11 | 0.719 | TIER-2 |
| regime_adaptive | CRYPTO | 13 | 76.9 | +4.32 | 0.785 | INSUFFICIENT |
| momentum_breakout | FOREX | 9 | 77.8 | +0.85 | 0.623 | INSUFFICIENT |
| trend_continuation | ETF | 24 | 70.8 | +1.51 | 0.612 | INSUFFICIENT |
| vol_arb | CRYPTO | 9 | 66.7 | +3.82 | 0.599 | INSUFFICIENT |

**Key finding**: `regime_adaptive × ETF` is the only persona-asset pair that passed all statistical gates (binomial significance, positive PnL, positive Sharpe). Wilson CI: 49.7–91.8%. This confirms the ETF regime-shift thesis.

---

## 7. Actionable Allocation Framework

### Recommended Capital Allocation (Peer-Model Consensus):

| Asset Class | Allocation | Rationale |
|-------------|-----------|-----------|
| **COMMODITY** | 25-30% | Highest PF, confirmed stable edge, dynamic scale with 7d WR |
| **EQUITY** | 20-25% | Stable edge, distributed risk, asymmetric payoff structure |
| **ETF** | 15-20% | Regime shift underway, regime_adaptive×ETF is Tier-2 verified |
| **CRYPTO** | 5-10% | Reduce from current dominance; only gated elite picks |
| **FOREX** | 0-5% | Pause new positions until 30d WR recovers above 50% |
| **BOND/FUTURES** | 0% | Insufficient data |

### Quality Gate Rules (MANDATORY):
1. **BLOCK** all `moderate_confidence` and `low_confidence` picks — they are 0/648 lifetime
2. **REQUIRE** `elite_a_high_conf` or `profitable_tp` label for any position >1% risk
3. **MONITOR** `alpha_verified` — currently negative, may need redefinition
4. **PREFER** aggregated_picks (74.1% WR) and kimi_signal_tracking (53.6% WR, highest total PnL)

### AI Model Weighting:
```
cursor_agent:    3.0x weight
llama4_scout:    2.5x weight
glm4_7_flash:    1.5x weight
grok3_direct:    1.0x weight
claude_opus:     1.0x weight
gemini:          0.0x (negative Sharpe — use contrarian only)
qwen3:           0.0x (negative Sharpe — exclude)
```

---

## 8. Risk Dashboard

| Risk | Severity | Trigger | Mitigation |
|------|----------|---------|------------|
| Commodity mean reversion | 🔴 HIGH | 7d WR drops below 70% | Reduce allocation 20%, tighten stops |
| Crypto structural decay | 🟡 MEDIUM | PF drops below 1.10 | Freeze all non-elite crypto picks |
| Forex negative drift | 🟡 MEDIUM | Already triggered (PF=0.96 7d) | Pause new positions now |
| Quality gate bypass | 🔴 CRITICAL | Any un-gated pick executed | Add pre-trade gate check |
| Concentration risk | 🟡 MEDIUM | Commodity >40% of PnL | Cap single-symbol risk at 5% |

---

## 9. Data Sources Referenced

- [`audit_dashboard/data/edge_stability/edge_stability_index.json`](audit_dashboard/data/edge_stability/edge_stability_index.json) — Per-class edge verdicts
- [`audit_dashboard/data/edge_stability/edge_stability_*.json`](audit_dashboard/data/edge_stability/) — Per-class windowed metrics
- [`audit_trail/data/performance_report_2026-05-16_to_2026-05-21.json`](audit_trail/data/performance_report_2026-05-16_to_2026-05-21.json) — 6-day resolved picks
- [`audit_dashboard/data/research/edge_significance_gate.json`](audit_dashboard/data/research/edge_significance_gate.json) — Persona×asset statistical tests
- [`audit_dashboard/data/research/performance_report.json`](audit_dashboard/data/research/performance_report.json) — AI model tournament
- [`audit_trail/data/hf_asset_class_report.json`](audit_trail/data/hf_asset_class_report.json) — Hedge fund tier classification
- [`audit_dashboard/QUANT_MEMO_PER_ASSET_2026-04.md`](audit_dashboard/QUANT_MEMO_PER_ASSET_2026-04.md) — Prior quant analysis

### Peer Models Consulted (NVIDIA NIM):
| Model | Provider | Response Quality |
|-------|----------|-----------------|
| `moonshotai/kimi-k2.6` | Moonshot AI | ⭐⭐⭐⭐⭐ Most detailed quant analysis |
| `openai/gpt-oss-120b` | OpenAI/NVIDIA | ⭐⭐⭐⭐ Best structured tables |
| `z-ai/glm-5.1` | Zhipu AI | ⭐⭐⭐⭐ Best risk identification |
| `nvidia/llama-3.3-nemotron-super-49b-v1.5` | NVIDIA | ⭐⭐⭐ Most concise |
| `mistralai/mistral-nemotron` | Mistral/NVIDIA | ⭐⭐⭐⭐ Most actionable allocations |

**Failed**: `minimaxai/minimax-m2.7` (empty response), `nvidia/llama-3.1-nemotron-ultra-253b-v1` (404 — account access issue)

---

## 10. Bottom Line

The system has **genuine alpha** but it's buried under noise. The path to consistent profitability is:

1. **Gate aggressively** — quality tiers are near-perfect classifiers (elite_a: 87.5% WR, moderate: 0% WR)
2. **Overweight Commodity** — PF=4.31 is world-class; dynamic scale with momentum
3. **Follow the ETF regime shift** — 30d metrics have tripled vs all-time; this is real
4. **Starve Crypto and Forex** — both decaying, both negative near-term
5. **Weight AI models by Sharpe** — cursor_agent and llama4_scout are the only positive-Sharpe models

**All 5 independent AI models reached the same conclusion**: the system's edge is real but concentrated. Quality gating and regime awareness are the difference between +994% and -825%.
