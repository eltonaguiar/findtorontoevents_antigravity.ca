# Standard Research Report Template

All researchers must produce results following this template to ensure consistency and comparability across the multi-agent research framework.

---

## Research Report Structure

### 1. Executive Summary (2-3 paragraphs)

- **Research Question:** Clear statement of what was investigated
- **Key Findings:** Top 3-5 discoveries (bullet points)
- **Conclusion:** Answer to the research question (Yes/No/Partial)
- **Recommendation:** Actionable next steps (deploy, refine, reject)

---

### 2. Research Context

#### 2.1 Researcher Information
- **Researcher ID:** `[researcher_id]`
- **Researcher Name:** `[Full Name]`
- **Specialization:** `[Area of expertise]`
- **Academic Foundations:** `[Key papers/references]`

#### 2.2 Research Question Details
- **Question ID:** `[unique_id]`
- **Title:** `[Short descriptive title]`
- **Priority:** `[1=High, 2=Medium, 3=Low]`
- **Dependencies:** `[List of prerequisite question IDs]`

#### 2.3 Hypothesis
> Original hypothesis statement from ResearchQuestion

---

### 3. Methodology

#### 3.1 Experimental Design
- **Data Period:** `[Start date - End date]`
- **Assets Universe:** `[e.g., BTC, ETH, top 50 coins]`
- **Timeframe:** `[e.g., 1h, 4h, 1d]`
- **Train/Validation/Test Split:** `[e.g., 70%/15%/15% chronological]`

#### 3.2 Implementation Details
- **Models/Algorithms Tested:** `[List all variants]`
- **Hyperparameters:** `[Key parameters and search space]`
- **Features Used:** `[Number and types of features]`
- **Validation Method:** `[e.g., walk-forward, purged CV, rolling window]`

#### 3.3 Baselines and Benchmarks
- **Baseline Strategies:** `[e.g., buy & hold, equal-weighted]`
- **Competing Approaches:** `[Alternative methods compared]`

---

### 4. Results

#### 4.1 Primary Metrics

| Metric | Strategy | Benchmark | Δ vs Benchmark |
|--------|----------|-----------|----------------|
| Sharpe Ratio | `[value]` | `[value]` | `[%]` |
| CAGR | `[value]` | `[value]` | `[%]` |
| Max Drawdown | `[value]` | `[value]` | `[%]` |
| Win Rate | `[value]` | `[value]` | `[%]` |
| Profit Factor | `[value]` | `[value]` | `[%]` |
| AUC-ROC | `[value]` | `[value]` | `[%]` |

#### 4.2 Performance Charts

**Include visualizations:**
- Equity curve (strategy vs benchmark)
- Drawdown chart
- Rolling Sharpe (6-month)
- Feature importance (if applicable)
- Confusion matrix / ROC curve (if classification)

*Note: Charts should be saved to `results/research/[researcher_id]/figures/` and referenced here.*

#### 4.3 Statistical Significance

- **Hypothesis Test:** `[e.g., t-test, bootstrap]`
- **p-value:** `[value]`
- **Confidence Interval:** `[95% CI]`
- **Multiple Testing Correction:** `[Bonferroni, BH FDR, etc.]`
- **Significant After Correction?** `[Yes/No]`

#### 4.4 Overfitting Diagnostics

- **In-Sample vs Out-of-Sample Gap:** `[% difference in Sharpe]`
- **PBO (Probability of Backtest Overfitting):** `[value]`
- **Parameter Stability:** `[Std dev of optimal params across periods]`
- **Walk-Forward Performance Degradation:** `[%]`

---

### 5. Analysis and Interpretation

#### 5.1 Hypothesis Evaluation

> **Original Hypothesis:** `[Restate]`

**Verdict:** ✅ Supported / ⚠️ Partially Supported / ❌ Rejected

**Evidence:**
- Point 1: `[Metric or finding that supports/contradicts]`
- Point 2: `[Another piece of evidence]`
- Point 3: `[Statistical significance result]`

**Deviations from Expected:**
- `[What surprised us? What didn't match the hypothesis?]`

#### 5.2 Key Discoveries

1. **Discovery 1:** `[Specific finding with metric]`
2. **Discovery 2:** `[Specific finding with metric]`
3. **Discovery 3:** `[Specific finding with metric]`

#### 5.3 Failure Modes and Limitations

- **Known Limitations:**
  - Limitation 1: `[e.g., data period limited to 2020-2024]`
  - Limitation 2: `[e.g., only tested on BTC/ETH, not alts]`
  - Limitation 3: `[e.g., assumes sufficient liquidity]`

- **Failure Conditions:**
  - When does this strategy fail? `[e.g., in high volatility regimes, during exchange outages]`
  - What are the tail risks? `[e.g., 5% worst loss per trade]`

---

### 6. Robustness Checks

#### 6.1 Parameter Sensitivity

| Parameter | Optimal | ±10% Performance Δ | Robust? |
|-----------|---------|-------------------|---------|
| `[param1]` | `[value]` | `[%]` | `[Yes/No]` |
| `[param2]` | `[value]` | `[%]` | `[Yes/No]` |

**Robust Region:** `[Describe parameter ranges that maintain >95% of optimal performance]`

#### 6.2 Stress Test Results

| Scenario | Portfolio Loss | Pass/Fail |
|----------|----------------|-----------|
| BTC -50% | `[%]` | `[Pass/Fail]` |
| BTC -80% | `[%]` | `[Pass/Fail]` |
| Correlation → 1.0 | `[%]` | `[Pass/Fail]` |
| Volatility ×3 | `[%]` | `[Pass/Fail]` |
| Liquidity Crisis | `[%]` | `[Pass/Fail]` |

**Stress Threshold:** `[Max acceptable loss, e.g., 30%]`

#### 6.3 Regime Analysis

| Regime | Sharpe | Win Rate | Recommendation |
|--------|--------|----------|----------------|
| Trending Up | `[value]` | `[%]` | `[Trade/Avoid]` |
| Trending Down | `[value]` | `[%]` | `[Trade/Avoid]` |
| Mean-Reverting | `[value]` | `[%]` | `[Trade/Avoid]` |
| High Volatility | `[value]` | `[%]` | `[Trade/Avoid]` |
| Low Volatility | `[value]` | `[%]` | `[Trade/Avoid]` |

---

### 7. Comparison to Alternatives

#### 7.1 Alternative Approaches Tested

| Approach | Sharpe | Max DD | Comments |
|----------|--------|--------|----------|
| **This Research** (proposed) | `[value]` | `[%]` | `[Best]` |
| Alternative 1 | `[value]` | `[%]` | `[Why worse?]` |
| Alternative 2 | `[value]` | `[%]` | `[Why worse?]` |
| Benchmark (B&H) | `[value]` | `[%]` | `[Baseline]` |

#### 7.2 Ablation Study (if applicable)

| Component Removed | Sharpe Δ | Significance |
|-------------------|----------|--------------|
| Component A | `[%]` | `[Yes/No]` |
| Component B | `[%]` | `[Yes/No]` |
| Component C | `[%]` | `[Yes/No]` |

**Critical Components:** `[List components that significantly degrade performance when removed]`

**Redundant Components:** `[List components with minimal impact]`

---

### 8. Implementation and Deployment

#### 8.1 Code and Artifacts

**Produced Code:**
- `[file1.py]` - `[Description]`
- `[file2.py]` - `[Description]`
- `[file3.py]` - `[Description]`

**Models Saved:**
- `[model1.pkl]` - `[Location, format, version]`
- `[model2.pkl]` - `[Location, format, version]`

**Configuration:**
- Recommended parameters: `[dict of hyperparameters]`
- Feature set: `[list of feature names or reference to feature set ID]`

#### 8.2 Resource Requirements

- **Compute:** `[e.g., CPU/GPU, training time]`
- **Data:** `[e.g., required data sources, frequency]`
- **Infrastructure:** `[e.g., needs low-latency execution, specific exchange API]`

#### 8.3 Deployment Readiness

| Criterion | Status | Notes |
|-----------|--------|-------|
| Validation Complete | ✅/❌ | `[Walk-forward, OOS tested?]` |
| Robustness Score | `[0-100]` | `[From robustness_researcher]` |
| PBO < 0.5 | ✅/❌ | `[Probability of overfitting]` |
| Stress Test Passed | ✅/❌ | `[All scenarios < threshold?]` |
| Governance Approved | ✅/❌ | `[Model card, audit trail ready?]` |
| Data Quality Certified | ✅/❌ | `[No leakage, survivorship corrected?]` |

**Overall Deployment Recommendation:** ✅ PROCEED / ⚠️ CONDITIONAL / ❌ REJECT

**Conditions (if conditional):**
1. `[Condition 1]`
2. `[Condition 2]`

---

### 9. Knowledge Contribution

#### 9.1 Shared Knowledge Base

This research contributes the following to the collective knowledge:

**New Signals/Features:**
- `[signal_name]`: `[description, expected Sharpe, holding period]`

**New Insights:**
- Insight 1: `[Finding that other researchers should know]`
- Insight 2: `[Finding that other researchers should know]`

**Reusable Components:**
- `[component_name]`: `[description, how to use]`

**Warnings / Pitfalls:**
- `[What others should avoid when building on this work]`

#### 9.2 Dependencies for Future Research

- **Requires:** `[Other research that must complete first]`
- **Enables:** `[Future research that can build on this]`
- **Related:** `[Other researchers that should be aware of these results]`

---

### 10. Appendices

#### Appendix A: Full Hyperparameter Search Space
```json
{
  "param1": [values],
  "param2": [values]
}
```

#### Appendix B: Complete Performance Metrics
`[Link to detailed CSV or JSON with all metrics computed]`

#### Appendix C: Raw Results
`[Link to raw backtest results, trades, predictions]`

#### Appendix D: Code Repository
`[Git commit hash, branch, tag]`

#### Appendix E: Data Version
`[Data version ID, checksum, source]`

---

## Report Metadata

- **Report Generated:** `[ISO 8601 timestamp]`
- **Researcher Version:** `[researcher version]`
- **Coordinator Run ID:** `[if part of multi-researcher campaign]`
- **Review Status:** `[Draft / Reviewed / Approved]`
- **Reviewer:** `[Name of human or AI reviewer]`

---

## Submission Checklist

Before submitting this report, ensure:

- [ ] All primary metrics computed and benchmarked
- [ ] Statistical significance tested (p-values, CIs)
- [ ] Overfitting diagnostics included (PBO, IS-OOS gap)
- [ ] Robustness checks completed (parameter sensitivity, stress tests)
- [ ] Regime analysis performed (if applicable)
- [ ] Ablation study conducted (if complex strategy)
- [ ] All charts generated and saved
- [ ] Code artifacts documented and saved
- [ ] Model files saved with version numbers
- [ ] Limitations clearly stated
- [ ] Recommendations actionable
- [ ] Knowledge contributions identified
- [ ] Dependencies for future work specified
- [ ] Report reviewed for clarity and completeness

---

## Template Usage Notes

1. **Markdown Format:** Reports should be saved as `[question_id]_report.md` in the researcher's results directory.
2. **Metrics Consistency:** Use the standard metric definitions from `validation_researcher` for comparability.
3. **Charts:** Save figures as PNG/SVG and reference them with relative paths.
4. **Code:** Include code snippets inline for key algorithms, but full code should be in separate `.py` files.
5. **Honesty:** Report negative or null results just as prominently as positive ones. Science is about truth, not confirmation bias.
6. **Reproducibility:** Ensure every number can be regenerated from the provided code and data versions.

---

*This template is maintained by the Governance Researcher. Last updated: 2025-02-22.*
