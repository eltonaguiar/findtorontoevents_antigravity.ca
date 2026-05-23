# Multi-Agent Routing Map — Who Handles What

This document defines how research questions and tasks are routed to the appropriate specialist researcher.

## Routing Logic Overview

The `ResearchCoordinator` uses a combination of:
1. **Keyword matching** between question description and researcher specialization
2. **Explicit assignment** (can manually assign to specific researcher)
3. **Dependency resolution** (questions with dependencies wait for prerequisites)
4. **Priority ordering** (higher priority questions processed first)

## Researcher Specializations & Keywords

### Deep Learning Architecture Researchers

| Researcher ID | Specialization | Keywords | Best For |
|--------------|----------------|----------|----------|
| `sequence_models` | LSTM/GRU/CNN temporal models | temporal, sequence, LSTM, GRU, CNN, recurrent, time series | Questions about temporal architectures, sequence length optimization |
| `transformers` | Attention-based models | transformer, attention, multi-head, positional encoding | Questions about attention mechanisms, long sequence modeling |
| `ensemble` | Stacking/boosting methods | ensemble, stacking, boosting, bagging, combination | Questions about combining multiple models or signals |
| `feature_engineering` | Automated feature discovery | features, synthesis, selection, importance, SHAP, autoencoder | Questions about feature generation, selection, representation |

### Strategy & Signal Researchers

| Researcher ID | Specialization | Keywords | Best For |
|--------------|----------------|----------|----------|
| `momentum` | Trend-following strategies | momentum, trend, breakout, moving average, MACD, ROC | Questions about trend-capturing signals, lookback optimization |
| `mean_reversion` | Statistical arbitrage | mean reversion, pairs, cointegration, z-score, spread, stat arb | Questions about reversion signals, pair selection, market-neutral |
| `regime_detection` | Market state identification | regime, market state, clustering, HMM, change point, volatility regime | Questions about identifying market conditions, regime-gating |
| `alternative_data` | Sentiment & on-chain metrics | sentiment, news, social, options flow, on-chain, alternative data | Questions about non-price data, sentiment analysis, blockchain metrics |

### Risk & Validation Researchers

| Researcher ID | Specialization | Keywords | Best For |
|--------------|----------------|----------|----------|
| `execution` | Market microstructure | execution, slippage, spread, liquidity, order type, fill, impact | Questions about trading costs, order placement, liquidity |
| `risk_management` | Portfolio construction | risk, portfolio, position sizing, Kelly, drawdown, leverage, factor exposure | Questions about capital allocation, risk control, sizing |
| `validation` | Overfitting detection | validation, overfitting, walk-forward, cross-validation, PBO, significance | Questions about strategy robustness, statistical validity |
| `robustness` | Stress testing | stress, adversarial, robustness, failure, kill-switch, extreme | Questions about extreme scenarios, failure modes, protective measures |

### Data & Governance Researchers

| Researcher ID | Specialization | Keywords | Best For |
|--------------|----------------|----------|----------|
| `data_quality` | Data integrity & bias | data quality, leakage, survivorship bias, corporate actions, missing data | Questions about data issues, look-ahead bias, data cleaning |
| `governance` | Compliance & auditability | governance, compliance, explainability, SHAP, audit, reproducibility, model card | Questions about model interpretability, audit trails, regulatory compliance |

## Routing Examples

### Example 1: Momentum Strategy Research

**Question:** "Which lookback period is optimal for momentum strategies?"

**Route to:** `momentum` researcher
**Why:** Keywords: "momentum", "lookback" → direct match with specialization

**Dependencies:** None
**Priority:** High (1)

---

### Example 2: Execution Cost Analysis

**Question:** "How does slippage affect strategy profitability?"

**Route to:** `execution` researcher
**Why:** Keywords: "slippage", "profitability" → execution specialist

**Dependencies:** None
**Priority:** High (1)

---

### Example 3: Model Explainability

**Question:** "Can we explain why the model made this trade?"

**Route to:** `governance` researcher
**Why:** Keywords: "explain", "why" → explainability/audit focus

**Dependencies:** None
**Priority:** Medium (2)

---

### Example 4: Data Validation

**Question:** "Are we leaking future information in our features?"

**Route to:** `data_quality` researcher
**Why:** Keywords: "leaking", "future information" → data leakage detection

**Dependencies:** None
**Priority:** Critical (1) - must fix before any other research

---

### Example 5: Stress Testing

**Question:** "What happens to the portfolio if BTC drops 80%?"

**Route to:** `robustness` researcher
**Why:** Keywords: "stress", "what happens if" → stress scenario analysis

**Dependencies:** Should wait for `risk_management` to complete portfolio construction
**Priority:** High (1)

---

## Dependency Graph

```
Data Quality (dq_*) ──────┐
                         ↓
Signal Researchers (mom_*, mr_*) ───→ Validation (val_*) ───→ Governance (gov_*)
                         ↓                    ↓
                    Regime Detection (reg_*) ↓
                         ↓                    ↓
                    Risk Management (risk_*) ↓
                         ↓                    ↓
                    Execution (exec_*) ──────┘
                         ↓
                    Robustness (rob_*)
```

**Key Dependencies:**
- All signal research depends on `data_quality` (no leakage, clean data)
- Validation depends on signal research having results to validate
- Risk management depends on having strategies to allocate
- Execution depends on knowing what trades to execute
- Robustness depends on having a complete portfolio to stress-test
- Governance is final gate before deployment

## Priority Levels

- **Priority 1 (High):** Foundational research that blocks others (data quality, signal discovery, validation)
- **Priority 2 (Medium):** Complementary research that enhances but doesn't block (alternative data, explainability)
- **Priority 3 (Low):** Nice-to-have, can run in parallel (some optimization studies)

## Manual Override

If automatic routing misassigns a question, use:

```python
coordinator.add_research_question(question, assignee="specific_researcher_id")
```

## Routing Configuration

The routing algorithm weights:
- Specialization keyword matches: 60%
- Literature alignment: 20%
- Question ID prefix hints: 20%

Question IDs encode the intended researcher:
- `seq_*` → sequence_models
- `trans_*` → transformers
- `mom_*` → momentum
- `mr_*` → mean_reversion
- `reg_*` → regime_detection
- `exec_*` → execution
- `risk_*` → risk_management
- `val_*` → validation
- `alt_*` → alternative_data
- `rob_*` → robustness
- `gov_*` → governance
- `dq_*` → data_quality
- `feat_*` → feature_engineering

---

## Quick Reference: Which Researcher for Which Question?

| If you're asking about... | Use Researcher |
|---------------------------|----------------|
| "Is my data clean and unbiased?" | `data_quality` |
| "Which ML architecture is best?" | `sequence_models` or `transformers` |
| "What's the optimal momentum lookback?" | `momentum` |
| "How do I detect regimes?" | `regime_detection` |
| "What position size should I use?" | `risk_management` |
| "Is my backtest overfitted?" | `validation` |
| "What if there's a crash?" | `robustness` |
| "Can you explain this trade?" | `governance` |
| "How much slippage will I incur?" | `execution` |
| "Can I use social media sentiment?" | `alternative_data` |
| "How do I find pairs to trade?" | `mean_reversion` |
| "How do I combine features?" | `feature_engineering` |

---

*Last updated: 2025-02-22*
