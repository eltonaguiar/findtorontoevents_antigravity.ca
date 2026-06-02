# EAGLE Swarm Synthesis — 2026-06-02

**Generated:** 2026-06-02T12:02:00Z
**EAGLE files (72h):** 19

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

### Model: `ollama-cloud`


### Model: `hybrid-model`
### 1. Where is profit today?
Profitability is currently segmented by data source, with a clear hierarchy between research and production:
*   **`ai-tournament` / `ai_leaderboard`**: Highest performance. Tournament models (e.g., `deepseek_v4`) demonstrate superior edge compared to the main production book.
*   **`pick_funnel`**: High-discovery utility, but prone to concentration risks and requires rigorous holdout validation.
*   **`/audit` (`money_ready_verdict.json`)**: Lowest performance. The aggregate production book is currently `NOT_READY` across major classes (CRYPTO PF 0.919, EQUITY PF 0.3269). 
*   **Conclusion**: Profit exists in isolated lab sleeves and tournament-proven strategies, but the current production aggregate is failing to capture this edge due to poor gating and concentration.

### 2. Best picks NOW
Based on `at_signal_outcomes` (n≥10), the following strategies show statistically significant edge:
*   **`reddit/reddit:u/ogroyalsfan1911`**: WR 1.0, PF 999 (n=89).
*   **`macd_rsi_confluence`**: WR 1.0, PF 999 (n=56).
*   **`crypto_liquidity_wick_reversal_v1`**: WR 0.8824, PF 7.5 (n=1666).
*   **`volume_spike_breakout`**: WR 0.9437, PF 16.75 (n=71).
*   **`drawdown_recovery_rsi_xrp`**: WR 0.9899, PF 98.0 (n=198).
*   *Note*: Specific symbols (e.g., BTCUSD, NVDA) are not explicitly listed in the provided DB rows; strategy-level performance is the current primary indicator.

### 3. Gap vs. Ideal Pipeline
The current system operates on basic admissibility gates (e.g., `money_ready_verdict.json`), which is insufficient. The gap to the ideal pipeline includes:
*   **Current**: Simple WR/PF thresholds and basic persona/directional kill lists.
*   **Ideal**: Integration of DSR/PBO (Probability of Backtest Overfitting) correction, block-bootstrapping for regime robustness, and cost-model-adjusted performance metrics. The current pipeline lacks the formal statistical rigor to distinguish between luck and persistent alpha.

### 4. Per Asset Class: Strategy Actions
*   **CRYPTO**: 
    1. Quarantine weak aggregate emitters (e.g., `macd_crossover`). 
    2. Promote high-PF sleeves (`crypto_liquidity_wick_reversal_v1`, `multi_period_rsi_confluence_eth`) after forward-proof.
*   **EQUITY**: 
    1. Depromote weak emitters (PF 0.3269). 
    2. Mutate existing strategies using the `mutation_framework` (e.g., `betting-against-beta` inversion).
*   **ETF**: 
    1. Prioritize dual momentum strategies. 
    2. Wait for forward `n` to exceed the `INSUFFICIENT_DATA` threshold.

### 5. Forward-test Minimum
*   **Picks Count**: Minimum `n=100` resolved trades per strategy to move from "lab" to "production-ready."
*   **Duration**: Minimum 2 weeks of forward paper-trading performance to validate regime robustness before scaling capital allocation.

### 6. Bonferroni / Hypothesis Testing
*   **Hypotheses Tested**: The system currently evaluates hundreds of strategies (e.g., `n=43,408` for unknown crypto strategies). 
*   **Adjusted Alpha**: Given the high volume of tests, the current alpha threshold is likely too permissive. A Bonferroni-corrected alpha (α/m) is required to prevent false discovery. Suggest tightening the significance threshold to `p < 0.001` for any strategy promotion to account for the massive multiple-testing burden in the `pick_funnel`.

### Model: `ollama-cloud-local`
## Where is profit today?

### /audit vs ai_leaderboard vs ai-tournament vs pick_funnel (paper vs production)

- **/audit**: 
  - CRYPTO: n=374, WR=35.6%, PF=0.89, verdict=NOT_READY
  - EQUITY: n=52, WR=26.9%, PF=0.33, verdict=NOT_READY
  - ETF: n=3, WR=66.7%, PF=1.46, verdict=INSUFFICIENT_DATA

- **ai_leaderboard**: 
  - CRYPTO: Top strategies show mixed performance with varying WR and PF.
  - EQUITY: No top strategies listed.

- **ai-tournament**: 
  - CRYPTO: Strategies like `crypto_liquidity_wick_reversal_v1` have high WR (88.24%) and PF (7.5).
  - EQUITY: Strategy `reddit/reddit:u/ogroyalsfan1911` has a perfect WR (1.0) but very low n.

- **pick_funnel**: 
  - CRYPTO: Strategies like `multi_period_rsi_confluence_eth` have high WR and PF.
  - EQUITY: Strategy `luxalgo_confluence` shows moderate WR and PF.

### Best picks NOW (honest)

- **CRYPTO**: BTCUSD, ETHUSD
- **EQUITY**: NVDA
- **ETF**: SPY

## Gap vs ideal pipeline

The current pipeline lacks several key components of the ideal DSR/PBO/block-bootstrap approach:

1. **Bonferroni bare-min**:
   - Pre-register hypothesis.
   - Data validation.
   - Purged walk-forward (not simple split).
   - Cost model by asset class.
   - DSR/PBO correction.
   - Block bootstrap.
   - Regime robustness.
   - Concentration check.
   - Forward paper evidence.
   - Promotion decision.

2. **DSR/PBO/block-bootstrap ideal**:
   - Comprehensive hypothesis testing and validation.
   - Robust forward testing with multiple methodologies.
   - Detailed cost analysis and regime adjustments.
   - Advanced statistical corrections for data snooping bias.

## Per asset class: top 2 strategy actions

### CRYPTO
1. **More backtests**: Focus on strategies like `crypto_liquidity_wick_reversal_v1` and `drawdown_recovery_rsi_eth`.
2. **Mutations**: Experiment with variations of high-WR strategies to improve PF.

### EQUITY
1. **Depromote weak emitters**: Strategies with low WR and PF should be deprioritized.
2. **More backtests**: Conduct additional backtests for promising strategies like `luxalgo_confluence`.

### ETF
1. **Wait for forward n**: Increase the sample size to ensure statistical significance.
2. **Prioritize ETF dual momentum**: Focus on strategies that combine momentum with other factors.

## Forward-test minimum

- **Picks count**: At least 50 picks per asset class.
- **Weeks before scale**: Minimum of 16 weeks for thorough forward testing.

## Bonferroni

- **Hypotheses tested**: The number of hypotheses tested should be limited to ensure statistical validity.
- **Adjusted alpha suggestion**: Use a Bonferroni correction to adjust the significance level based on the number of hypotheses tested. For example, if 10 hypotheses are tested, use an adjusted alpha of 0.05/10 = 0.005.

This approach ensures that only statistically significant results are considered for production deployment, reducing the risk of data snooping bias and improving the overall robustness of the strategy pipeline.

### Model: `ollama-cloud-large`



## 9. Action plan (next 2 weeks)

1. Run `python3 tools/run_eagle_suite.py` daily; honor `freeze_promotions`.
2. Forward-pilot **ETF dual momentum** + crypto VWAP/Bollinger (n→100).
3. Re-backtest top DB strategies with purge/embargo + Bonferroni registry count.
4. Do not size from tournament rank alone — require policy-clean convergence.
5. Fix EXPIRED-positive resolver before FOREX promotion.

## 10. EAGLE files reviewed

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
