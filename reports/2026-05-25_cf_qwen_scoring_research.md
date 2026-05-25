# Cloudflare Workers AI — Qwen Family — Stock Algorithm Scoring Research

**Date:** 2026-05-25
**Endpoint:** https://api.cloudflare.com/client/v4/accounts/{acct}/ai/run/{model}
**Parameters:** temperature=0.4, max_tokens=4096

Note: user asked for qwen3-max which is not on CF Workers AI. Used the two largest qwen variants available: `@cf/qwen/qwen3-30b-a3b-fp8` and `@cf/qwen/qwq-32b` (reasoning).

---

# Model: `@cf/qwen/qwen3-30b-a3b-fp8`

## Q1 — Original ask

**Prompt:**

> Give me a scoring method to determine if an algorithm for predicting stocks is high quality or not?

**Response:**

{"id": "chatcmpl-14a520a445884db79598b3dffd7e895f", "object": "chat.completion", "created": 1779685389, "model": "@cf/qwen/qwen3-30b-a3b-fp8", "choices": [{"index": 0, "message": {"role": "assistant", "content": "\n\nTo evaluate the quality of a stock prediction algorithm, a **comprehensive scoring method** should consider multiple dimensions of performance, risk, and adaptability. Below is a structured approach to create a scoring framework:\n\n---\n\n### **1. Prediction Accuracy Metrics**\nMea

---

## Q2 — Concrete formula

**Prompt:**

> Now give me ONE concrete scoring formula that combines the dimensions you listed into a single 0-100 score. Specify explicit weights, exact metric thresholds, and the minimum-sample-size floor below which the score should be treated as unreliable. Return as pseudocode plus a worked example on a hypothetical algorithm with Sharpe 1.2, Sortino 1.8, max drawdown 18%, win-rate 56% on n=240 trades.

**Response:**

{"id": "chatcmpl-ee03469f05c84a63ae32d85ddecda68d", "object": "chat.completion", "created": 1779685425, "model": "@cf/qwen/qwen3-30b-a3b-fp8", "choices": [{"index": 0, "message": {"role": "assistant", "content": null, "refusal": null, "annotations": null, "audio": null, "function_call": null, "tool_calls": [], "reasoning_content": "\nOkay, the user wants a single scoring formula that combines various dimensions of a stock prediction algorithm into a 0-100 score. They mentioned specific metrics l

---

## Q3 — Per-asset-class weights

**Prompt:**

> Our dashboard scores algorithms across CRYPTO, EQUITY, COMMODITY, FOREX, BOND, ETF asset classes. How should the weights in your single-score formula differ per asset class? Give a 6x10 weight matrix (6 asset classes × your 10 dimensions) with one-line justification per cell that you change.

**Response:**

{"id": "chatcmpl-6895897eed814791914bb6cd2bd31bcb", "object": "chat.completion", "created": 1779685489, "model": "@cf/qwen/qwen3-30b-a3b-fp8", "choices": [{"index": 0, "message": {"role": "assistant", "content": "\n\nHere\u2019s a **6x10 weight matrix** (6 asset classes \u00d7 10 dimensions) with **justifications for each cell**. Weights are normalized to sum to 100% per asset class. Adjustments reflect the unique characteristics of each asset class.  \n\n---\n\n### **Weight Matrix (6 Asset Clas

---

## Q4 — Deploy thresholds

**Prompt:**

> Give me three hard cutoff bands on your 0-100 score: DEPLOY (real money), RESEARCH (paper trade only), JUNK (kill). For each band, list the specific gate conditions (e.g. 'Sharpe>=1.0 AND maxDD<=20% AND n>=200 AND Bonferroni-p<0.05') that must ALSO be true beyond the composite score. Goal: 1-glance Y/N promotion decision for findtorontoevents.ca/audit's 'is this algorithm real-money-grade?' verdict.

**Response:**

{"id": "chatcmpl-95ef8ba5fad442a0ae23a43576cb534a", "object": "chat.completion", "created": 1779685537, "model": "@cf/qwen/qwen3-30b-a3b-fp8", "choices": [{"index": 0, "message": {"role": "assistant", "content": "\n\nHere\u2019s a **3-tiered cutoff system** with **hard gate conditions** for real-money deployment, paper trading, or rejection. The thresholds are designed to enforce **statistical rigor**, **risk control**, and **sample size reliability**.  \n\n---\n\n### **1. DEPLOY (Real Money Gra

---

# Model: `@cf/qwen/qwq-32b`

## Q1 — Original ask

**Prompt:**

> Give me a scoring method to determine if an algorithm for predicting stocks is high quality or not?

**Response:**

Okay, the user wants a scoring method to determine if a stock prediction algorithm is high quality. Let me think about what factors are important here. First, accuracy is key, but there's more to it than just being right. Maybe metrics like accuracy score, precision, recall, F1-score? But wait, stock markets are time-series data, so maybe time-based metrics are better. 

Hmm, they might also care about how the algorithm performs over time. Like, does it hold up in different market conditions? So maybe backtesting over various periods, including volatile times. But how do you quantify that? Maybe include a consistency score across different time frames.

Risk-adjusted returns could be important too. If the algorithm makes big gains but with huge volatility, that's risky. Metrics like Sharpe Ratio or Sortino Ratio might help here. Also, maximum drawdown is a common measure in finance, so that's worth including.

Then there's overfitting. If the model is too tailored to historical data, it won't generalize. So maybe a cross-validation score, like out-of-sample performance. Or a train-test split where the test is on more recent data since the market changes over time.

Computational efficiency might matter too. How fast does the algorithm run? Especially for real-time trading, but maybe that's more about practicality than quality. Still, the user might want to know.

What about the model's ability to handle transaction costs? Real-world trading incurs costs, so maybe a profit factor after costs. Or a Sharpe Ratio that includes slippage and fees.

Also, the user might need a composite score combining these factors. Like, each metric gets a weight and they're averaged. But how to decide the weights? Maybe let the user choose based on their priorities.

Wait, let me list possible metrics:

1. Accuracy metrics: Accuracy, Precision, Recall, F1, but for time series maybe Mean Absolute Error (MAE) or Mean Squared Error (MSE) for regression, or hit rate for classification.

2. Profitability: Total return, CAGR (Compound Annual Growth Rate), Sharpe Ratio, Sortino Ratio, Calmar Ratio (return over max drawdown).

3. Risk measures: Maximum drawdown, volatility, Value at Risk (VaR), Conditional Value at Risk (CVaR).

4. Consistency: Performance across different market regimes (bull, bear), time periods, sectors.

5. Overfitting: Out-of-sample performance, cross-validation, maybe a complexity penalty like AIC or BIC.

6. Robustness: Sensitivity analysis, how the model performs with slight changes in parameters or data.

7. Efficiency: Execution time, computational resources needed.

8. Practical considerations: Transaction costs, slippage, liquidity impact.

Now, how to combine these into a scoring method? Maybe each category has a score, then overall score is a weighted sum. But need to define each metric's calculation.

For example:

- Accuracy: Use hit rate (correct predictions / total) for classification, or R-squared for regression. But R-squared might not be great for stock prediction since it's noisy. Maybe use correlation between predicted and actual returns?

- Profitability: Calculate the total return over the test period. Compare to a benchmark like the S&P 500. Sharpe Ratio = (Return - Risk-Free Rate)/Volatility. Higher is better.

- Risk: Max drawdown is the peak to trough decline. Lower is better. Maybe invert it for scoring.

- Consistency: Maybe average Sharpe Ratio across different time windows, or standard deviation of monthly returns. Lower volatility here is good.

- Overfitting: Compare in-sample vs out-of-sample performance. If the out-of-sample Sharpe is significantly lower, it's overfitted. Maybe a ratio of out-of-sample to in-sample Sharpe.

- Robustness: Perturb input data slightly and see how predictions change. Lower sensitivity is better.

- Efficiency: Execution time, maybe normalized by some baseline.

But how to turn these into a score? Maybe normalize each metric to a 0-100 scale, then assign weights. For example, if accuracy is 40% of the score, profitability 30%, etc. But the weights depend on what the user values. Maybe provide a framework where they can choose weights.

Also, need to consider that some metrics are inversely related. Like, lower max drawdown is better, so when scoring, higher score for lower values.

Another thought: The user might not have a finance background, so need to explain terms. But since they asked for a method, maybe just outline the components.

Possible steps for the scoring method:

1. Define evaluation metrics covering accuracy, risk, profitability, overfitting, etc.

2. For each metric, calculate its value and normalize it to a 0-100 scale, with higher being better.

3. Assign weights to each metric based on importance (user-defined).

4. Compute the weighted average to get an overall score.

Examples of normalization:

- For a metric like Sharpe Ratio, higher is better. So normalize by (value - min)/(max - min) where min and max are based on typical values.

- For max drawdown, lower is better. So normalize as (max - value)/(max - min).

But need to set min and max thresholds. Maybe use industry benchmarks or historical data.

Alternatively, use z-scores and then normalize.

Wait, maybe it's better to have each metric's score calculated as:

If the metric is better when higher: score = (value - lower_bound)/(upper_bound - lower_bound) * 100

If better when lower: score = (upper_bound - value)/(upper_bound - lower_bound) * 100

But the user needs to define what's good. For example, a Sharpe Ratio above 2 is good, below 1 is bad. So set lower and upper bounds accordingly.

Alternatively, use percentiles. Like, if a model has a Sharpe Ratio in the 90th percentile, it gets a higher score.

But this requires knowing the distribution of possible values, which might be hard without data.

Alternatively, use thresholds. For example:

- Sharpe Ratio: <1 = 0, 1-2 = 50, 2-3 = 80, >3 = 100.

But this is arbitrary.

Hmm, perhaps the key is to provide a framework rather than exact numbers, letting the user adjust parameters.

Also, need to mention that no single metric is sufficient, and the combination is important.

Another point: Backtesting period should be sufficiently long and include different market conditions. Maybe split into training and test sets, with test covering recent years.

Also, walk-forward optimization to prevent overfitting.

Including a composite score that combines these aspects would help in comparing different algorithms.

I think structuring the answer with a list of metrics, how to calculate them, normalization, and then the scoring formula with weights would be good. Also, mention that the user can adjust weights based on their priorities.
</think>

To evaluate the quality of a stock prediction algorithm, a comprehensive scoring method should consider multiple dimensions of performance, risk, and robustness. Below is a structured approach to assess and score the algorithm's effectiveness:

---

### **1. Key Evaluation Metrics**
#### **A. Accuracy & Prediction Quality**
- **Hit Rate (Classification):**  
  \[
  \text{Hit Rate} = \frac{\text{Number of Correct Predictions}}{\text{Total Predictions}} \times 100
  \]  
  Measures how often the model correctly predicts direction (e.g., up/down).

- **Mean Absolute Error (MAE) or Mean Squared Error (MSE) (Regression):**  
  \[
  \text{MAE} = \frac{1}{n}\sum_{i=1}^n |y_i - \hat{y}_i|, \quad \text{MSE} = \frac{1}{n}\sum_{i=1}^n (y_i - \hat{y}_i)^2
  \]  
  Lower values indicate better accuracy in predicting numerical returns.

- **Correlation Coefficient (Regression):**  
  \[
  \text{Correlation} = \frac{\text{Cov}(y, \hat{y})}{\sigma_y \sigma_{\hat{y}}}
  \]  
  Measures linear alignment between predicted and actual returns (closer to 1 is better).

---

#### **B. Profitability**
- **Total Return:**  
  \[
  \text{Total Return} = \frac{\text{Final Portfolio Value} - \text{Initial Investment}}{\text{Initial Investment}} \times 100
  \]  
  Measures overall growth over the test period.

- **Compound Annual Growth Rate (CAGR):**  
  \[
  \text{CAGR} = \left(\frac{\text{Final Value}}{\text{Initial Value}}\right)^{\frac{1}{t}} - 1
  \]  
  Annualized return, useful for comparing across time horizons.

- **Profit Factor:**  
  \[
  \text{Profit Factor} = \frac{\text{Total Profit from Winning Trades}}{\text{Total Loss from Losing Trades}}
  \]  
  Higher values indicate better risk-adjusted profitability.

---

#### **C. Risk Management**
- **Sharpe Ratio:**  
  \[
  \text{Sharpe Ratio} = \frac{(\text{Portfolio Return} - \text{Risk-Free Rate})}{\text{Volatility of Returns}}
  \]  
  Higher ratios indicate better risk-adjusted returns.

- **Sortino Ratio:**  
  \[
  \text{Sortino Ratio} = \frac{(\text{Portfolio Return} - \text{Risk-Free Rate})}{\text{Downside Deviation}}
  \]  
  Focuses on downside risk (losses).

- **Maximum Drawdown (MDD):**  
  \[
  \text{MDD} = \max\left(\frac{\text{Peak Value} - \text{Trough Value}}{\text{Peak Value}}\right) \times 100
  \]  
  Measures the largest peak-to-trough loss during the test period (lower is better).

- **Value at Risk (VaR):**  
  Estimates the maximum potential loss over a period with a given confidence level (e.g., 95% confidence over 1 day).

---

#### **D. Robustness & Generalization**
- **Out-of-Sample Performance:**  
  Compare performance on a **held-out test set** (unseen data) to training data. A significant drop indicates overfitting.

- **Cross-Validation Score:**  
  Use time-series cross-validation (e.g., expanding window) to ensure consistency across time periods.

- **Regime Consistency:**  
  Test performance across different market regimes (bull, bear, sideways) and economic conditions (recessions, expansions).

- **Sensitivity Analysis:**  
  Perturb input data (e.g., add noise) and measure prediction stability. Lower sensitivity = better robustness.

---

#### **E. Practical Considerations**
- **Transaction Costs:**  
  Subtract fees, slippage, and bid-ask spreads from returns to reflect real-world profitability.

- **Computational Efficiency:**  
  Measure execution time and resource usage (e.g., memory, CPU). Critical for real-time trading.

---

### **2. Scoring Framework**
#### **Step 1: Normalize Metrics**
Convert each metric to a **0–100 score** based on its importance and direction:
- **For metrics where higher is better** (e.g., Sharpe Ratio):  
  \[
  \text{Score} = \frac{\text{Value} - \text{Min}}{\text{Max} - \text{Min}} \times 100
  \]  
  *Example:* Sharpe Ratio with Min=0.5, Max=3 → a value of 2.0 gets \( \frac{2-0.5}{3-0.5} \times 100 = 66.67 \).

- **For metrics where lower is better** (e.g., MDD):  
  \[
  \text{Score} = \frac{\text{Max} - \text{Value}}{\text{Max} - \text{Min}} \times 100
  \]  
  *Example:* MDD with Min=5%, Max=30% → a value of 15% gets \( \frac{30-15}{30-5} \times 100 = 66.67 \).

#### **Step 2: Assign Weights**
Define weights (\(w_i\)) for each metric based on priorities (sum to 1). For example:
- Accuracy: 20%
- Profitability: 25%
- Risk: 30%
- Robustness: 15%
- Practicality: 10%

#### **Step 3: Compute Overall Score**
\[
\text{Overall Score} = \sum_{i=1}^n (w_i \times \text{Metric}_i \text{ Score})
\]

---

### **3. Example Scoring Table**
| **Metric**          | **Value** | **Score (0–100)** | **Weight** | **Weighted Score** |
|----------------------|-----------|-------------------|------------|--------------------|
| Hit Rate             | 75%       | 75                | 0.20       | 15.0               |
| Sharpe Ratio         | 1.8       | 60                | 0.30       | 18.0               |
| Max Drawdown         | 12%       | 70                | 0.25       | 17.5               |
| Out-of-Sample Perf.  | 85%       | 85                | 0.15       | 12.8               |
| Execution Time       | 0.5 sec   | 90                | 0.10       | 9.0                |
| **Total Score**      |           |                   | **1.00**   | **72.3**           |

---

### **4. Interpretation**
- **High-Quality Algorithm (Score >80):** Consistently profitable, low risk, robust across markets, and computationally efficient.  
- **Moderate Quality (60–80):** Competent but may underperform in extreme conditions or require optimization.  
- **Low Quality (<60):** Unreliable, risky, or overfitted—avoid for real-world use.

---

### **5. Best Practices**
- **Backtest Thoroughly:** Use at least 5 years of data, including crises (e.g., 2008, 2020).  
- **Avoid Overfitting:** Use walk-forward optimization and out-of-sample testing.  
- **Compare to Benchmarks:** Outperform passive strategies (e.g., S&P 500) to justify active management.  

This framework balances quantitative rigor with practicality, allowing customization to your specific goals and risk tolerance.

---

## Q2 — Concrete formula

**Prompt:**

> Now give me ONE concrete scoring formula that combines the dimensions you listed into a single 0-100 score. Specify explicit weights, exact metric thresholds, and the minimum-sample-size floor below which the score should be treated as unreliable. Return as pseudocode plus a worked example on a hypothetical algorithm with Sharpe 1.2, Sortino 1.8, max drawdown 18%, win-rate 56% on n=240 trades.

**Response:**

[ERROR: [{'message': 'AiError: AiError: Request timeout (8ac21f5e-e2a4-4ee3-9adf-fe3cde910e76)', 'code': 3046}]]

---

## Q3 — Per-asset-class weights

**Prompt:**

> Our dashboard scores algorithms across CRYPTO, EQUITY, COMMODITY, FOREX, BOND, ETF asset classes. How should the weights in your single-score formula differ per asset class? Give a 6x10 weight matrix (6 asset classes × your 10 dimensions) with one-line justification per cell that you change.

**Response:**

[ERROR: [{'message': 'AiError: AiError: Request timeout (ad24aee1-0a2f-46c9-84ab-6920dff1fbd8)', 'code': 3046}]]

---

## Q4 — Deploy thresholds

**Prompt:**

> Give me three hard cutoff bands on your 0-100 score: DEPLOY (real money), RESEARCH (paper trade only), JUNK (kill). For each band, list the specific gate conditions (e.g. 'Sharpe>=1.0 AND maxDD<=20% AND n>=200 AND Bonferroni-p<0.05') that must ALSO be true beyond the composite score. Goal: 1-glance Y/N promotion decision for findtorontoevents.ca/audit's 'is this algorithm real-money-grade?' verdict.

**Response:**

Okay, the user wants three cutoff bands for their algorithm scoring system: DEPLOY, RESEARCH, and JUNK. Each band needs specific gate conditions beyond just the composite score. Let me start by recalling the previous parts of the conversation. 

First, the user had asked for a scoring method combining various metrics into a 0-100 score with weights and thresholds. Then they wanted the weights adjusted per asset class, which I couldn't provide due to an error. Now, they need the cutoff bands with explicit conditions for each.

The goal is to make a quick yes/no decision for real-money deployment. The DEPLOY band should have the strictest conditions, ensuring the algorithm is reliable. RESEARCH is for potential but needing more testing, and JUNK is for those that clearly don't meet basic criteria.

Starting with DEPLOY: The composite score needs to be high, say 80+. But they also want gate conditions. Sharpe Ratio is crucial here because it measures risk-adjusted returns. Maybe Sharpe >=1.5 to ensure good risk-adjusted performance. Max Drawdown should be under 20% to avoid huge losses. The number of trades (n) should be sufficiently large, like >=200, to reduce overfitting. Also, a statistical significance test like Bonferroni-corrected p-value <0.05 to ensure the results aren't due to chance. Maybe also a minimum profit factor, say 1.5, to ensure more profit than loss.

For RESEARCH, the score could be 60-79. Here, the conditions can be a bit looser. Maybe Sharpe >=1.0, Max DD <=25%, n>=100 (since it's still in research phase), and a lower p-value threshold but maybe not as strict. Profit factor could be 1.2. The idea is that it shows promise but needs more testing.

JUNK would be below 60, but also must fail at least one critical condition. So if any of the key metrics are way off, like Sharpe <0.5, Max DD >30%, or n<50, it's junk. Also, if the profit factor is below 1, meaning losses exceed profits, that's a red flag. Bonferroni p>=0.1 would indicate statistical insignificance.

Wait, the user mentioned "specific gate conditions that must ALSO be true beyond the composite score." So even if the score is in the DEPLOY band, it has to meet all those conditions. Similarly, for JUNK, if the score is low AND fails any of those, it's junk.

Need to ensure that the conditions are logical and cover key aspects: risk (Sharpe, Sortino, DD), statistical significance, profitability (profit factor), and sample size (n). Also, maybe include Sortino in some conditions since it focuses on downside risk, which is important.

Let me structure each band with the composite score range and the AND conditions. Make sure each condition is necessary. For example, in DEPLOY, all conditions must be met. For JUNK, if any of the conditions are not met (OR), then it's junk. Wait, the user says "must ALSO be true beyond the composite score." So for DEPLOY, the score must be >=80 AND all the conditions are met. For JUNK, it's either the score <60 OR any of the critical conditions are not met (like Sharpe too low). Hmm, but the user wants three bands where each has conditions that must be true in addition to the composite score.

Wait, the exact wording: "list the specific gate conditions (e.g. 'Sharpe>=1.0 AND maxDD<=20% AND n>=200 AND Bonferroni-p<0.05') that must ALSO be true beyond the composite score." So for DEPLOY, the algorithm must have a score in the DEPLOY band AND satisfy all the listed conditions. Similarly for RESEARCH, the score is in its band AND the conditions are met. JUNK is either score <60 OR fails any critical condition, but the user might want JUNK to have conditions that if any are met, it's junk regardless of the score. Hmm, need to clarify.

Alternatively, the bands are based on the composite score, but to be in DEPLOY, you must also meet those conditions. So even if the score is 85, if it doesn't meet the Sharpe condition, it can't be DEPLOY. Similarly, JUNK is if the score is below 60 OR any of the critical conditions (like Sharpe too low) are not met, even if the score is mid-range. But the user might want the bands to be based on the composite score first, then the conditions are additional requirements. So the DEPLOY band is composite >=80 AND conditions met. RESEARCH is 60-79 AND conditions met. JUNK is composite <60 OR fails any critical conditions.

But the user's example in the query says "must ALSO be true beyond the composite score", so the conditions are additional. So for DEPLOY, it's composite score in DEPLOY band AND all the conditions are true. For JUNK, it's either composite <60 OR any of the critical conditions are not met. Wait, but the user might want each band to have its own set of conditions. Let me proceed as per the user's example.

The user provided an example in the first question: "DEPLOY (real money), RESEARCH (paper trade only), JUNK (kill). For each band, list the specific gate conditions [...] that must ALSO be true beyond the composite score."

So each band's conditions are in addition to the composite score. So DEPLOY requires the score to be in its band AND meet all the listed conditions. RESEARCH requires its score band AND its conditions. JUNK is either below 60 OR doesn't meet DEPLOY/RESEARCH conditions. Hmm, maybe the JUNK conditions are the negation of the DEPLOY and RESEARCH conditions. Alternatively, JUNK has its own conditions that if met, it's automatically junk regardless of score. But the user wants three bands with their own conditions.

Alternatively, the JUNK band is defined as composite <60 OR any of the critical failure conditions (like Sharpe <0.5, etc.), even if the composite is higher. So JUNK is a catch-all for algorithms that fail critical conditions regardless of their score. But the user wants three bands with conditions that must be met in addition to the composite. Maybe better to structure it as:

- DEPLOY: composite 80-100 AND all DEPLOY conditions met (e.g., Sharpe >=1.5, etc.)

- RESEARCH: composite 60-79 AND all RESEARCH conditions met (e.g., Sharpe >=1.0, etc.)

- JUNK: composite <60 OR any of the critical failure conditions (e.g., Sharpe <0.5, etc.)

This way, even a high-scoring algorithm that fails a critical condition (like Sharpe too low) would be JUNK. The user probably wants this because some metrics are non-negotiable.

Now, setting the exact conditions. Let's think:

DEPLOY (80-100):

- Sharpe >=1.5 (good risk-adjusted return)

- Sortino >=1.8 (focus on downside risk)

- Max Drawdown <=15% (manageable risk)

- Profit Factor >=1.5 (more profit than loss)

- n >=200 (sufficient sample)

- Bonferroni-corrected p-value <0.01 (statistical significance)

- CAGR >=15% (good growth)

Wait, but the user's previous example included CAGR, but maybe better to stick to the metrics mentioned earlier: Sharpe, Sortino, MaxDD, Profit Factor, n, and p-value. Also, maybe include a minimum hit rate or something else? The user's example in the first question had hit rate, MAE, etc., but the current problem is about gate conditions beyond the composite score. The user might prefer key metrics that are critical for real money.

Alternatively, the conditions should be a subset of the most critical metrics. Let's pick:

DEPLOY:

- Sharpe >=1.5

- Sortino >=1.8

- Max Drawdown <=20%

- Profit Factor >=1.5

- n >=200

- Bonferroni-p <0.05

Wait, in the user's example in the first question, they had a worked example with Sharpe 1.2, Sortino 1.8, MaxDD 18%, win rate 56% on n=240. So maybe the DEPLOY conditions can be slightly higher than that. Let me see:

DEPLOY Conditions:

- Sharpe Ratio >=1.5

- Sortino Ratio >=1.8

- Max Drawdown <=18% (since in the example it was 18% but that's close)

Wait, but in the example, the MaxDD was 18% which might be acceptable. Maybe set MaxDD <=20% for DEPLOY.

- Profit Factor >=1.5 (the example had 56% win rate, but profit factor is total profit over loss. If the example's profit factor is not given, but maybe assume it's okay.)

- Minimum number of trades n >=200 (the example had 240, so that's okay)

- Bonferroni-corrected p-value <0.05 (statistical significance)

RESEARCH (60-79):

- Sharpe >=1.0

- Sortino >=1.5

- Max Drawdown <=25%

- Profit Factor >=1.2

- n >=100

- Bonferroni-p <0.10 (less strict)

JUNK (<60 OR any of these):

- Sharpe <0.5 OR

- Sortino <1.0 OR

- Max Drawdown >30% OR

- Profit Factor <1.0 (losing money) OR

- n <50 OR

- Bonferroni-p >=0.10 (statistically insignificant)

Additionally, maybe include a condition like "No extreme outliers in predictions" but that's harder to quantify. Alternatively, include a minimum CAGR, but maybe stick to the given metrics.

Wait, the user's example had a Sharpe of 1.2, which would fall into RESEARCH if DEPLOY requires 1.5. So the example would be in RESEARCH. But the user might want the example to be in DEPLOY? Not sure, but the conditions need to be clear.

Also, the Bonferroni correction is important to adjust for multiple testing. The p-value threshold should be adjusted based on the number of tests, but here it's a single test, so maybe just p<0.05. But the user might want it as part of the conditions.

Putting it all together, the three bands with their conditions:

DEPLOY (80-100):

- Score >=80

AND

- Sharpe >=1.5

- Sortino >=1.8

- Max Drawdown <=20%

- Profit Factor >=1.5

- n >=200

- Bonferroni-p <0.05

RESEARCH (60-79):

- Score 60-79

AND

- Sharpe >=1.0

- Sortino >=1.5

- Max Drawdown <=25%

- Profit Factor >=1.2

- n >=100

- Bonferroni-p <0.10

JUNK (Else):

- Score <60

OR

- Sharpe <0.5

- Sortino <1.0

- Max Drawdown >30%

- Profit Factor <1.0

- n <50

- Bonferroni-p >=0.10

This way, even an algorithm with a high score but failing any of the DEPLOY conditions is automatically JUNK. The JUNK band includes both low scores and failing critical metrics regardless of score.

Now, the user also wants a minimum sample size floor where the score is unreliable. Earlier, in the first question, the example had n=240. So maybe the minimum n for the score to be reliable is 50, but the JUNK includes n<50 as a condition. So if n<50, the score is unreliable and thus JUNK.

The worked example in the first question had n=240, which is above the threshold, so it would be considered reliable. The example's Sharpe was 1.2, which is below DEPLOY's 1.5 but above RESEARCH's 1.0, so it would be in RESEARCH.

I think this structure meets the user's needs. Now, to present it clearly with each band's conditions.
</think>

Here’s a **three-tier scoring system** with explicit cutoff bands, gate conditions, and a minimum sample size floor. The conditions ensure real-world viability while balancing statistical rigor and practicality.

---

### **1. Scoring Bands & Conditions**
#### **A. DEPLOY (Real Money)**  
**Score Range:** 80–100  
**Gate Conditions (ALL MUST BE TRUE):**  
- **Sharpe Ratio ≥ 1.5** (Strong risk-adjusted returns)  
- **Sortino Ratio ≥ 1.8** (Controls downside risk)  
- **Max Drawdown ≤ 20%** (Avoids catastrophic losses)  
- **Profit Factor ≥ 1.5** (Profitable net of losses)  
- **n ≥ 200 trades** (Sufficient sample size)  
- **Bonferroni-corrected p-value < 0.05** (Statistically significant outperformance)  

**Rationale:** Ensures robustness, profitability, and statistical validity for real-world deployment.

---

#### **B. RESEARCH (Paper Trade Only)**  
**Score Range:** 60–79  
**Gate Conditions (ALL MUST BE TRUE):**  
- **Sharpe Ratio ≥ 1.0** (Baseline risk-adjusted returns)  
- **Sortino Ratio ≥ 1.5** (Acceptable downside risk)  
- **Max Drawdown ≤ 25%** (Moderate risk tolerance)  
- **Profit Factor ≥ 1.2** (Positive net returns)  
- **n ≥ 100 trades** (Minimally sufficient testing)  
- **Bonferroni-corrected p-value < 0.10** (Marginal statistical significance)  

**Rationale:** Shows promise but requires further validation before real money.

---

#### **C. JUNK (Kill)**  
**Triggers:**  
- **Score < 60**  
- **OR ANY OF THE FOLLOWING (single failure disqualifies):**  
  - **Sharpe Ratio < 0.5** (Poor risk-adjusted returns)  
  - **Sortino Ratio < 1.0** (Unacceptable downside risk)  
  - **Max Drawdown > 30%** (Excessive volatility)  
  - **Profit Factor < 1.0** (Net loss over time)  
  - **n < 50 trades** (Insufficient sample size)  
  - **Bonferroni-corrected p-value ≥ 0.10** (Statistically insignificant)  

**Rationale:** Eliminates algorithms with fundamental flaws or insufficient evidence.

---

### **2. Minimum Sample Size Floor**  
- **n < 50 trades:** Score is **unreliable** and automatically classified as **JUNK**, regardless of other metrics.  
- **Why?** Small samples are prone to noise, overfitting, and survivorship bias.

---

### **3. Worked Example**  
**Hypothetical Algorithm Stats:**  
- **Sharpe = 1.2**  
- **Sortino = 1.8**  
- **Max Drawdown = 18%**  
- **Profit Factor = 1.4**  
- **n = 240**  
- **Bonferroni-p = 0.04**  
- **Composite Score = 72.3** (from prior example)  

**Classification:**  
- **Score (72.3) → RESEARCH Band**  
- **Gate Check:**  
  - Sharpe (1.2) < 1.5 → **DEPLOY fails**  
  - All RESEARCH conditions met → **RESEARCH approved**  
  - No JUNK triggers → **Not Junk**  

**Verdict:** Paper trade only (RESEARCH).

---

### **4. One-Line Audit Decision Flow**  
```python
def classify_algorithm(score, sharpe, sortino, mdd, profit_factor, n, bonf_p):
    if n < 50:
        return "JUNK (insufficient data)"
    
    if score >= 80 and (sharpe >=1.5 and sortino >=1.8 and mdd <=20 and profit_factor >=1.5 and n >=200 and bonf_p <0.05):
        return "DEPLOY (real money)"
    
    elif 60 <= score <80 and (sharpe >=1.0 and sortino >=1.5 and mdd <=25 and profit_factor >=1.2 and n >=100 and bonf_p <0.10):
        return "RESEARCH (paper trade)"
    
    else:
        return "JUNK (kill)"
```

---

### **Key Justifications**  
- **DEPLOY:** High bar to ensure survival in real markets.  
- **RESEARCH:** Balances potential with caution.  
- **JUNK:** Cuts losses early on statistically invalid or dangerous strategies.  
- **Bonferroni p-value:** Adjusts for multiple testing (e.g., if backtested across 10+ assets, p=0.05/10 = 0.005 threshold).  

This system provides a clear, actionable "traffic light" for algorithm promotion.

---

