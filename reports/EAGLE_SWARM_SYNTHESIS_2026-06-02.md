# EAGLE Swarm Synthesis — 2026-06-02

**Generated:** 2026-06-02T12:12:52Z
**EAGLE files (72h):** 22

## 1. Executive consensus (all EAGLE models + live JSON)

| Finding | Status |
|---------|--------|
| Production `/audit` money-ready | **0 classes** — NOT_READY / INSUFFICIENT |
| Real edge location | **AI tournament** (paper) + **verified lab** (ETF dual momentum) |
| Main blocker | Research≠production, resolver/contamination, concentration |
| EAGLE-4/5 in scanner | CRYPTO SHORT flip, persona kills, symbol boosts (wired) |

## 2. Profitable-pick surface ranking

| Surface | Edge? | Use for capital? | Why |
|---------|-------|----------------|-----|
| `/audit` policy-clean | No | **No** | Live PF<1 most classes; money_ready empty |
| `/audit/ai-tournament.html` | **Best paper** | Paper only | deepseek_v4 PF~3.5, n=200+ resolved |
| `/audit/ai_leaderboard.html` | Thin | No | ~1 engine ranked; 503 candidates unattributed |
| `/audit/pick_funnel.html` | Discovery | No | Cells often concentration/dispute flagged |
| `/audit/research_index.html` | Hypothesis catalog | Pre-register only | M-107 registry |

## 3. Live asset-class snapshot (policy-clean)

- **BOND**: n=0 WR=0.0 PF=0.0 → INSUFFICIENT_DATA
- **COMMODITY**: n=4 WR=0.5 PF=1.6758 → INSUFFICIENT_DATA
- **CRYPTO**: n=368 WR=0.3614 PF=0.919 → NOT_READY
- **EQUITY**: n=52 WR=0.2692 PF=0.3269 → NOT_READY
- **ETF**: n=3 WR=0.6667 PF=1.4581 → INSUFFICIENT_DATA
- **FOREX**: n=32 WR=0.2812 PF=0.4812 → INSUFFICIENT_DATA
- **FUTURES**: n=13 WR=0.1538 PF=0.5193 → INSUFFICIENT_DATA
- **PENNY_STOCK**: n=1 WR=0.0 PF=0.0 → INSUFFICIENT_DATA
- **UNKNOWN**: n=9 WR=0.6667 PF=0.724 → INSUFFICIENT_DATA

## 4. DB strategy inventory (ejaguiar1_stocks / backtests)

- Backtest DB tables: `[]`

### Top resolved strategies (90d, n≥10)

| Class | Strategy | n | WR | PF |
|-------|----------|---|-----|-----|
| CRYPTO | unknown | 43408 | 0.3347 | 0.5030 |
| CRYPTO | multi_period_rsi_confluence_eth | 1764 | 0.6111 | 1.5714 |
| CRYPTO | crypto_liquidity_wick_reversal_v1 | 1666 | 0.8824 | 7.5000 |
| CRYPTO | drawdown_recovery_rsi_eth | 1078 | 0.6364 | 1.7500 |
| CRYPTO | atr_percentile_gate | 882 | 0.7778 | 3.5000 |
| CRYPTO | ensemble | 408 | 0.4265 | 0.7436 |
| CRYPTO | drawdown_recovery_rsi_sol | 392 | 0.5000 | 1.0000 |
| CRYPTO | drawdown_recovery_rsi_xrp | 198 | 0.9899 | 98.0000 |
| CRYPTO | None | 118 | 0.8644 | 6.3750 |
| CRYPTO | reddit/reddit:u/ogroyalsfan1911 | 89 | 1.0000 | 999 |
| CRYPTO | volume_spike_breakout | 71 | 0.9437 | 16.7500 |
| CRYPTO | macd_crossover | 67 | 0.0000 | 0.0000 |
| CRYPTO | macd_rsi_confluence | 56 | 1.0000 | 999 |
| CRYPTO | B_flip_PriceRocMeanReversion | 54 | 0.6852 | 2.1765 |
| CRYPTO | luxalgo_confluence | 43 | 0.6047 | 1.5294 |
| CRYPTO | reddit/reddit:u/SscorpionN08 | 32 | 1.0000 | 999 |
| CRYPTO | enhanced_ml_A_xgboost | 30 | 0.6333 | 1.7273 |
| CRYPTO | prediction_market_consensus | 28 | 0.7857 | 3.6667 |
| CRYPTO | hoffman_ema_trend | 23 | 0.3043 | 0.4375 |
| CRYPTO | ml_crypto_pred | 22 | 0.6364 | 1.7500 |

## 5. Statistical readiness (Bonferroni → ideal)

- **Bare minimum:** Bonferroni α/N tests; 70/30 split; PF≥1.5; MDD≤30%; flat 5bps costs.
- **Production ideal:** Purged+embargo WF, block bootstrap, DSR/PBO/SPA, HHI<0.20, forward n≥30–50, 8w shadow.
- **Current repo:** `alpha_engine/admissibility_pipeline.py`, `verified_strategies/pipeline/`, `tools/run_eagle_suite.py`.
- **Bonferroni note:** With ~80+ emitters tested historically, α_adj ≈ 0.05/80 ≈ **0.000625** per test — explains why raw green funnel cells fail under SPA.

## 6. Best picks TODAY (evidence-bound)

| Symbol | Class | Evidence | Verdict |
|--------|-------|----------|---------|
| **EEM, IWM, GLD** | ETF | EAGLE3 tournament ≥60% WR | Paper edge; not production money-ready |
| **BAC, JPM, MSFT** | EQUITY | Tournament LONG-only edge | Paper; production EQUITY PF=0.33 |
| **BTC/ETH SHORT** | CRYPTO | Tournament SHORT 67% WR vs LONG 33% | EAGLE-4 flip applied in scanner |
| **NVDA** | EQUITY | ~64% tournament WR, active confluence picks | **Monitor only** — production book weak |
| **KULR, RGTI** | PENNY | 100% WR tournament (tiny n) | High artifact risk; do not size |

Safe long-term (academic, not from live audit PF): broad ETF dual-momentum sleeves — **shadow pilot only** until forward n≥100.

## 7. LiteLLM ollama mode smoke tests

- `ollama-cloud-large`: OK
- `ollama-cloud`: OK
- `ollama-cloud-local`: OK

## 8. Per-model swarm insights

### Model: `hybrid-model`
## Required output sections

### 1. **Where is profit today?**

| Source | Profit Factor (PF) | Win Rate (WR) | n (resolved) | Verdict |
| --- | --- | --- | --- | --- |
| /audit | 1.19 | 53.9% | 269 | STRONG EDGE (LONG-only) |
| ai_leaderboard | 1.22 | 41.7% | 216 | WEAK (directionally wrong) |
| ai-tournament | 6.80 | 75.0% | 88 | STRONGEST EDGE (but concentration risk) |
| pick_funnel | 1.18 | 54.0% | 161 | STRONG EDGE |

### 2. **Best picks NOW**

Insufficient evidence to recommend specific symbols.

### 3. **Gap vs ideal pipeline**

The current pipeline is far from the ideal pipeline. The Bonferroni correction is not applied, and the DSR/PBO/block-bootstrap ideal is not met.

### 4. **Per asset class**

| Asset Class | Top 2 Strategy Actions |
| --- | --- |
| CRYPTO | 1. More backtests to confirm the SHORT-only edge. 2. Mutation of VWAPReversion to improve performance. |
| EQUITY | 1. More backtests to confirm the LONG-only edge. 2. Mutation of Faber TAA to improve performance. |
| ETF | 1. More backtests to confirm the LONG-only edge. 2. Mutation of Verified Dual Momentum to improve performance. |
| FOREX | 1. Fix the COT lag issue. 2. More backtests to confirm the edge. |
| COMMODITY | 1. Fix the COT lag issue. 2. More backtests to confirm the edge. |
| BOND | 1. More backtests to confirm the edge. 2. Mutation of HYG/LQD credit momentum to improve performance. |
| FUTURES | 1. Fix the COT lag issue. 2. More backtests to confirm the edge. |

### 5. **Forward-test minimum**

The minimum number of picks and weeks before scaling is not specified.

### 6. **Bonferroni**

The number of hypotheses tested is not specified. Adjusted alpha suggestion is not provided.

### Model: `ollama-cloud-large`
## 1. Where is profit today? – Ranking of the four evidence streams  

| Rank | Source (surface) | Asset class(s) with **positive** PF / WR | PF (median) | WR (median) | Comment |
|------|------------------|------------------------------------------|------------|-------------|---------|
| **1** | **AI‑Tournament** (`ai‑tournament`) | PENNY (PF 6.80, WR 75 %), ETF (PF 4.32, WR 67.6 %), EQUITY (PF 3.77, WR 63.6 %), FUTURES (PF 5.14, WR 65 %) | **4.8** | **68 %** | The tournament (5 T1 models, 3 692 resolved picks) shows the strongest, data‑backed edge – especially in PENNY, ETF and EQUITY. |
| **2** | **AI‑Leaderboard** (`ai_leaderboard`) – DB top 90‑day strategies (n ≥ 10) | CRYPTO (several strategies with PF ≥ 1.5, WR ≥ 0.6) – e.g. `crypto_liquidity_wick_reversal_v1` (PF 7.5, WR 0.882) and `drawdown_recovery_rsi_eth` (PF 1.75, WR 0.636) | **≈ 2.0** (median of listed PFs) | **≈ 0.71** (median of listed WRs) | Only CRYPTO meets the “ready” threshold; other classes have too few live trades (see /audit). |
| **3** | **Live Production** (`/audit` – *money_ready_verdict.json*) | ETF (PF 1.458, WR 0.667, n = 3) – **INSUFFICIENT_DATA**; EQUITY (PF 0.327, WR 0.269, n = 52) – **NOT_READY**; CRYPTO (PF 0.919, WR 0.361, n = 368) – **NOT_READY** | **≈ 0.9** (overall median) | **≈ 0.35** (overall median) | Production is dominated by “NOT_READY” verdicts; many classes have < 10 live trades, so edge estimates are unreliable. |
| **4** | **Pick‑Funnel / Paper‑Only** (`pick_funnel`) | No concrete numbers supplied in the prompt – the live dashboard shows many “paper‑only” symbols (e.g., BTC‑USD) but no PF/WR. | – | – | **Insufficient evidence** to rank; treat as “unknown”. |

**Take‑away:** The AI‑Tournament is the only source with a statistically meaningful, positive edge across multiple asset classes. Live production lags far behind, especially for CRYPTO (directional bug) and


## 9. Action plan (next 2 weeks)

1. Run `python3 tools/run_eagle_suite.py` daily; honor `freeze_promotions`.
2. Forward-pilot **ETF dual momentum** + crypto VWAP/Bollinger (n→100).
3. Re-backtest top DB strategies with purge/embargo + Bonferroni registry count.
4. Do not size from tournament rank alone — require policy-clean convergence.
5. Fix EXPIRED-positive resolver before FOREX promotion.

## 10. EAGLE files reviewed

- `reports/EAGLE_SWARM_SYNTHESIS_2026-06-02.md`
- `EAGLE_SWARM_SYNTHESIS_2026-06-02.MD`
- `reports/EAGLE_SWARM_CONSOLIDATED_2026-06-02.md`
- `EAGLE4_2026-06-02_minimax-m3-free.MD`
- `EAGLE2_2026-06-02_MIMO_FINAL.MD`
- `updates/EAGLE_JUNE2_GPT-5.4.MD`
- `reports/EAGLE_REVIEW_2026-06-02_GROK.md`
- `reports/EAGLE_2026-06-02_GROK.md`
- `reports/EAGLE2_2026-06-02_deepseek_v4.MD`
- `reports/EAGLE2_2026-06-02_COMPOSER.md`
- `reports/EAGLE2_2026-06-02_CLAUDE_CODE.MD`
- `EAGLE_JUNE2_claude-opus-4-7.md`
- `EAGLE3_2026-06-02_minimax-m3-free.MD`
- `reports/EAGLE2_2026-06-02_GROK.md`
- `EAGLE2_JUNE2_MIMO_V2_5_PRO.MD`
- `EAGLE2_2026-06-02_CLAUDE_OPUS_4_7.MD`
- `reports/EAGLE_JUNE2_COMPOSER.md`
- `reports/EAGLE_JUNE2_CLAUDE_CODE.MD`
- `EAGLE_JUNE2_MIMO_V2_5_PRO.MD`
- `EAGLE_JUNE2_CLAUDE_OPUS_4_7.MD`
- `reports/EAGLE_JUNE2_GROK.md`
- `reports/EAGLE_session_2026-05-27_1047_EST_signal_outcomes_refresh.md`
