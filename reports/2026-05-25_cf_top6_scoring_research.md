# Cloudflare Workers AI — Top-6 Diverse Panel — Stock Algorithm Scoring Research

**Date:** 2026-05-25
**Endpoint:** https://api.cloudflare.com/client/v4/accounts/{acct}/ai/run/{model}
**Parameters:** temperature=0.4, max_tokens=4096

Panel: @cf/meta/llama-3.3-70b-instruct-fp8-fast, @cf/meta/llama-4-scout-17b-16e-instruct, @cf/nvidia/nemotron-3-120b-a12b, @cf/openai/gpt-oss-120b, @cf/zai-org/glm-4.7-flash, @cf/mistralai/mistral-small-3.1-24b-instruct

---

# Model: `@cf/meta/llama-3.3-70b-instruct-fp8-fast`

## Q1 — Original ask

**Prompt:**

> Give me a scoring method to determine if an algorithm for predicting stocks is high quality or not?

**Response:**

Evaluating the quality of a stock prediction algorithm can be done using various metrics. Here's a scoring method that combines multiple metrics to provide a comprehensive assessment:

**Scoring Method:**

1. **Accuracy** (30%): Measure the algorithm's ability to predict the correct direction of stock price movement (up or down). You can use metrics like:
	* Directional Accuracy (DA): (Number of correct predictions / Total number of predictions)
	* Mean Absolute Error (MAE): Average difference between predicted and actual stock prices
2. **Return on Investment (ROI)** (25%): Evaluate the algorithm's ability to generate profits. You can use metrics like:
	* Annualized Return: (Ending value / Beginning value) ^ (1 / Number of years) - 1
	* Sharpe Ratio: (Average return - Risk-free rate) / Standard deviation of returns
3. **Risk Management** (20%): Assess the algorithm's ability to manage risk. You can use metrics like:
	* Maximum Drawdown (MDD): Maximum peak-to-trough decline in the algorithm's performance
	* Value-at-Risk (VaR): Estimated loss with a given probability (e.g., 95th percentile)
4. **Robustness and Stability** (15%): Evaluate the algorithm's ability to perform consistently across different market conditions. You can use metrics like:
	* Walk-forward optimization: Test the algorithm on out-of-sample data to ensure it generalizes well
	* Sensitivity analysis: Measure the algorithm's performance under different market scenarios (e.g., bull, bear, or sideways markets)
5. **Data Quality and Feature Engineering** (10%): Assess the algorithm's ability to handle noisy or missing data, as well as its feature engineering capabilities. You can use metrics like:
	* Data coverage: Percentage of available data used in the algorithm
	* Feature importance: Measure the contribution of each feature to the algorithm's performance

**Weighted Scoring:**

Assign weights to each category based on their relative importance. The weights should add up to 100%. For example:

* Accuracy: 30%
* ROI: 25%
* Risk Management: 20%
* Robustness and Stability: 15%
* Data Quality and Feature Engineering: 10%

Calculate the weighted score for each category by multiplying the metric value by its corresponding weight. Then, sum up the weighted scores to get an overall score.

**Interpretation:**

* **High-quality algorithm:** Overall score ≥ 80%
* **Medium-quality algorithm:** Overall score between 60% and 79%
* **Low-quality algorithm:** Overall score < 60%

Note that this scoring method is just a suggestion, and you may need to adjust the weights and metrics based on your specific requirements and market conditions. Additionally, it's essential to backtest the algorithm on a large dataset and evaluate its performance over a significant period to ensure its reliability and robustness.

---

## Q2 — Concrete formula

**Prompt:**

> Now give me ONE concrete scoring formula that combines the dimensions you listed into a single 0-100 score. Specify explicit weights, exact metric thresholds, and the minimum-sample-size floor below which the score should be treated as unreliable. Return as pseudocode plus a worked example on a hypothetical algorithm with Sharpe 1.2, Sortino 1.8, max drawdown 18%, win-rate 56% on n=240 trades.

**Response:**

**Scoring Formula:**

Let's define a scoring formula that combines the dimensions of accuracy, ROI, risk management, robustness, and data quality. We'll use the following metrics:

* Sharpe Ratio (SR)
* Sortino Ratio (SOR)
* Maximum Drawdown (MDD)
* Win Rate (WR)
* Sample Size (n)

The scoring formula is:

`score = (0.3 * (WR - 0.5) / 0.5 + 0.2 * (SR - 0.5) / 1.5 + 0.2 * (SOR - 0.5) / 2.5 + 0.3 * (1 - MDD / 100)) * (n / (n + 100)) * 100`

**Weights and Thresholds:**

* Win Rate (WR): 30% weight, threshold = 50% ( neutral), range = 0% to 100%
* Sharpe Ratio (SR): 20% weight, threshold = 0.5 ( neutral), range = 0 to 2
* Sortino Ratio (SOR): 20% weight, threshold = 0.5 ( neutral), range = 0 to 3
* Maximum Drawdown (MDD): 30% weight, threshold = 0% ( ideal), range = 0% to 100%
* Sample Size (n): minimum sample size floor = 200 trades

**Pseudocode:**
```python
def calculate_score(WR, SR, SOR, MDD, n):
  if n < 200:
    return "Unreliable"
  score = (0.3 * (WR - 0.5) / 0.5 + 
           0.2 * (SR - 0.5) / 1.5 + 
           0.2 * (SOR - 0.5) / 2.5 + 
           0.3 * (1 - MDD / 100)) * (n / (n + 100)) * 100
  return score
```

**Worked Example:**

Suppose we have a hypothetical algorithm with the following metrics:

* Sharpe Ratio (SR) = 1.2
* Sortino Ratio (SOR) = 1.8
* Maximum Drawdown (MDD) = 18%
* Win Rate (WR) = 56%
* Sample Size (n) = 240 trades

Plugging these values into the scoring formula, we get:

`score = (0.3 * (0.56 - 0.5) / 0.5 + 0.2 * (1.2 - 0.5) / 1.5 + 0.2 * (1.8 - 0.5) / 2.5 + 0.3 * (1 - 0.18 / 100)) * (240 / (240 + 100)) * 100`
`score = (0.3 * 0.12 / 0.5 + 0.2 * 0.7 / 1.5 + 0.2 * 1.3 / 2.5 + 0.3 * 0.982) * 0.706 * 100`
`score = (0.072 + 0.0933 + 0.104 + 0.2946) * 0.706 * 100`
`score = 0.564 * 0.706 * 100`
`score = 39.86 * 100`
`score = 73.45`

Since the sample size (n = 240) is above the minimum floor of 200 trades, we can consider the score reliable.

Therefore, the hypothetical algorithm scores approximately **73.45** out of 100.

---

## Q3 — Per-asset-class weights

**Prompt:**

> Our dashboard scores algorithms across CRYPTO, EQUITY, COMMODITY, FOREX, BOND, ETF asset classes. How should the weights in your single-score formula differ per asset class? Give a 6x10 weight matrix (6 asset classes × your 10 dimensions) with one-line justification per cell that you change.

**Response:**

Here's a 6x10 weight matrix for the different asset classes, with adjustments to the original formula:

| Asset Class | Win Rate | Sharpe Ratio | Sortino Ratio | Maximum Drawdown | Sample Size | Risk-Free Rate | Volatility | Market Impact | Liquidity | Data Quality |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CRYPTO | 0.25 | 0.15 | 0.20 | 0.20 | 0.10 | 0.05 | 0.05 | 0.00 | 0.00 | 0.00 | Higher win rate importance due to high volatility in crypto markets.
| EQUITY | 0.30 | 0.20 | 0.20 | 0.20 | 0.10 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | No change, as equity markets are generally well-behaved.
| COMMODITY | 0.20 | 0.25 | 0.20 | 0.25 | 0.10 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | Increased importance on Sharpe Ratio and Maximum Drawdown due to commodity market volatility.
| FOREX | 0.20 | 0.20 | 0.25 | 0.20 | 0.15 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | Higher importance on Sample Size due to high liquidity and frequent trading in FOREX.
| BOND | 0.10 | 0.30 | 0.20 | 0.30 | 0.10 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | Increased importance on Sharpe Ratio and Maximum Drawdown due to bond market sensitivity to interest rates.
| ETF | 0.25 | 0.20 | 0.20 | 0.20 | 0.15 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | Similar to EQUITY, but with slightly higher importance on Sample Size due to ETF trading frequency.

Note that I've introduced the following new dimensions, which were not part of the original formula:

* Risk-Free Rate: Not used in this matrix, as it's not directly relevant to the scoring formula.
* Volatility: Not used in this matrix, as it's already captured by the Sharpe and Sortino Ratios.
* Market Impact: Not used in this matrix, as it's not directly relevant to the scoring formula.
* Liquidity: Not used in this matrix, as it's already captured by the Sample Size dimension.

The changes are justified as follows:

* CRYPTO: Higher win rate importance due to high volatility.
* COMMODITY: Increased importance on Sharpe Ratio and Maximum Drawdown due to commodity market volatility.
* FOREX: Higher importance on Sample Size due to high liquidity and frequent trading.
* BOND: Increased importance on Sharpe Ratio and Maximum Drawdown due to bond market sensitivity to interest rates.
* ETF: Similar to EQUITY, but with slightly higher importance on Sample Size due to ETF trading frequency.

Keep in mind that these adjustments are subjective and may vary depending on your specific use case and requirements.

---

## Q4 — Deploy thresholds

**Prompt:**

> Give me three hard cutoff bands on your 0-100 score: DEPLOY (real money), RESEARCH (paper trade only), JUNK (kill). For each band, list the specific gate conditions (e.g. 'Sharpe>=1.0 AND maxDD<=20% AND n>=200 AND Bonferroni-p<0.05') that must ALSO be true beyond the composite score. Goal: 1-glance Y/N promotion decision for findtorontoevents.ca/audit's 'is this algorithm real-money-grade?' verdict.

**Response:**

Here are three hard cutoff bands on the 0-100 score, along with specific gate conditions that must also be true:

**Band 1: DEPLOY (real money) - Score ≥ 85**

* Gate conditions:
	+ Sharpe Ratio ≥ 1.2 AND Sortino Ratio ≥ 1.5
	+ Maximum Drawdown ≤ 15%
	+ Sample Size (n) ≥ 500 trades
	+ Bonferroni-corrected p-value < 0.01 (to account for multiple testing)
	+ Win Rate ≥ 55%
* Justification: This band represents algorithms that have demonstrated exceptional performance, robustness, and statistical significance. The gate conditions ensure that the algorithm has a strong risk-adjusted return profile, low drawdown, and sufficient sample size to support its performance.

**Band 2: RESEARCH (paper trade only) - Score ≥ 60 AND Score < 85**

* Gate conditions:
	+ Sharpe Ratio ≥ 0.8 AND Sortino Ratio ≥ 1.0
	+ Maximum Drawdown ≤ 25%
	+ Sample Size (n) ≥ 200 trades
	+ Bonferroni-corrected p-value < 0.05
	+ Win Rate ≥ 50%
* Justification: This band represents algorithms that show promise but require further refinement or testing. The gate conditions ensure that the algorithm has a reasonable risk-adjusted return profile, moderate drawdown, and sufficient sample size to support its performance.

**Band 3: JUNK (kill) - Score < 60**

* Gate conditions: None (algorithm is rejected outright)
* Justification: This band represents algorithms that have failed to demonstrate sufficient performance, robustness, or statistical significance. The algorithm is rejected without further consideration.

These bands provide a clear and concise framework for evaluating algorithm performance and making promotion decisions. By considering both the composite score and the gate conditions, you can quickly determine whether an algorithm is suitable for real-money deployment, further research, or rejection.

---

# Model: `@cf/meta/llama-4-scout-17b-16e-instruct`

## Q1 — Original ask

**Prompt:**

> Give me a scoring method to determine if an algorithm for predicting stocks is high quality or not?

**Response:**

Evaluating the quality of a stock prediction algorithm! There are several metrics and methods to help you assess its performance. Here's a scoring method that combines multiple metrics to give you a comprehensive picture:

**Method: Composite Scoring**

Assign scores to your algorithm based on the following metrics:

1. **Mean Absolute Error (MAE)**: Measures the average difference between predicted and actual stock prices.
	* Score: (1 - (MAE / (max( actual prices ) - min( actual prices )))) * 100
	* Lower MAE values are better.
2. **Mean Squared Error (MSE)**: Similar to MAE, but penalizes larger errors more.
	* Score: (1 - (MSE / (max( actual prices ) - min( actual prices ))^2)) * 100
	* Lower MSE values are better.
3. **Root Mean Squared Percentage Error (RMSPE)**: Measures the square root of the average squared percentage errors.
	* Score: (1 - (RMSPE / 100)) * 100
	* Lower RMSPE values are better.
4. **R-squared (R2)**: Measures the proportion of variance in actual prices explained by the predicted prices.
	* Score: R2 * 100
	* Higher R2 values are better.
5. **Directional Accuracy (DA)**: Measures the percentage of times the algorithm correctly predicts the direction of the stock price change (up or down).
	* Score: (DA / 100) * 100
	* Higher DA values are better.
6. **Sharpe Ratio**: Measures the excess return of the algorithm over a risk-free investment, relative to its volatility.
	* Score: (Sharpe Ratio / max(Sharpe Ratios)) * 100
	* Higher Sharpe Ratio values are better.

**Composite Score**

Calculate a composite score by taking a weighted average of the individual metric scores:

Composite Score = (0.2 * MAE Score) + (0.2 * MSE Score) + (0.15 * RMSPE Score) + (0.25 * R2 Score) + (0.1 * DA Score) + (0.1 * Sharpe Ratio Score)

**Interpretation**

Normalize the composite score to a range between 0 and 100:

* 0-20: Low quality
* 21-40: Fair quality
* 41-60: Good quality
* 61-80: High quality
* 81-100: Excellent quality

**Example**

Suppose your algorithm has the following metrics:

* MAE: 5
* MSE: 25
* RMSPE: 10
* R2: 0.8
* DA: 0.7
* Sharpe Ratio: 1.2

Assuming a max actual price of 100 and a min actual price of 50, you can calculate the individual scores:

* MAE Score: (1 - (5 / 50)) * 100 = 90
* MSE Score: (1 - (25 / 50^2)) * 100 = 90
* RMSPE Score: (1 - (10 / 100)) * 100 = 90
* R2 Score: 0.8 * 100 = 80
* DA Score: (0.7 / 1) * 100 = 70
* Sharpe Ratio Score: (1.2 / 2) * 100 = 60 (assuming a max Sharpe Ratio of 2)

The composite score would be:

Composite Score = (0.2 * 90) + (0.2 * 90) + (0.15 * 90) + (0.25 * 80) + (0.1 * 70) + (0.1 * 60) = 83.5

This would correspond to a "High quality" score.

Keep in mind that this is just one possible scoring method, and you may need to adjust the weights or metrics based on your specific requirements and goals. Additionally, it's essential to consider other factors, such as the algorithm's complexity, interpretability, and computational efficiency, when evaluating its overall quality.

---

## Q2 — Concrete formula

**Prompt:**

> Now give me ONE concrete scoring formula that combines the dimensions you listed into a single 0-100 score. Specify explicit weights, exact metric thresholds, and the minimum-sample-size floor below which the score should be treated as unreliable. Return as pseudocode plus a worked example on a hypothetical algorithm with Sharpe 1.2, Sortino 1.8, max drawdown 18%, win-rate 56% on n=240 trades.

**Response:**

**Scoring Formula:**

```pseudocode
FUNCTION stock_prediction_algorithm_score(
  sharpe_ratio,
  sortino_ratio,
  max_drawdown,
  win_rate,
  n_trades
)
  IF n_trades < 100 THEN
    RETURN NULL  // treat as unreliable if fewer than 100 trades

  // Sharpe Ratio (0-5)
  sharpe_score = MAX(0, MIN(5, (sharpe_ratio / 2) * 50))

  // Sortino Ratio (0-5)
  sortino_score = MAX(0, MIN(5, (sortino_ratio / 3) * 50))

  // Max Drawdown (0-30)
  max_drawdown_score = MAX(0, MIN(30, (1 - (max_drawdown / 30)) * 30))

  // Win Rate (0-20)
  win_rate_score = MAX(0, MIN(20, ((win_rate - 0.5) / 0.2) * 20))

  // Composite Score (0-100)
  score = (0.3 * sharpe_score) + (0.25 * sortino_score) + (0.2 * max_drawdown_score) + (0.25 * win_rate_score)

  RETURN score
```

**Worked Example:**

Suppose we have a hypothetical algorithm with:

* Sharpe Ratio: 1.2
* Sortino Ratio: 1.8
* Max Drawdown: 18%
* Win Rate: 56%
* Number of Trades: 240

```pseudocode
sharpe_score = MAX(0, MIN(5, (1.2 / 2) * 50)) = MAX(0, MIN(5, 30)) = 30
sortino_score = MAX(0, MIN(5, (1.8 / 3) * 50)) = MAX(0, MIN(5, 30)) = 30
max_drawdown_score = MAX(0, MIN(30, (1 - (0.18 / 0.3)) * 30)) = MAX(0, MIN(30, 24)) = 24
win_rate_score = MAX(0, MIN(20, ((0.56 - 0.5) / 0.2) * 20)) = MAX(0, MIN(20, 6)) = 6

score = (0.3 * 30) + (0.25 * 30) + (0.2 * 24) + (0.25 * 6) = 9 + 7.5 + 4.8 + 1.5 = 22.8
```

The final score is approximately **22.8**.

Note that this scoring formula uses the following thresholds:

* Sharpe Ratio: 2 (target), 0 (minimum)
* Sortino Ratio: 3 (target), 0 (minimum)
* Max Drawdown: 30% (target), 100% (minimum)
* Win Rate: 50% (minimum), 70% (target)

You can adjust these thresholds and weights to suit your specific requirements and goals. Additionally, keep in mind that this is just one possible scoring formula, and you may want to consider other factors when evaluating the quality of a stock prediction algorithm.

---

## Q3 — Per-asset-class weights

**Prompt:**

> Our dashboard scores algorithms across CRYPTO, EQUITY, COMMODITY, FOREX, BOND, ETF asset classes. How should the weights in your single-score formula differ per asset class? Give a 6x10 weight matrix (6 asset classes × your 10 dimensions) with one-line justification per cell that you change.

**Response:**

**Weight Matrix:**

| Asset Class | Sharpe Ratio | Sortino Ratio | Max Drawdown | Win Rate | n_trades (reliability) |
| --- | --- | --- | --- | --- | --- |
| CRYPTO | 0.25 | 0.2 | 0.15 | 0.1 | 0.3 | **Crypto markets are highly volatile, so reliability (n_trades) and risk metrics (Sharpe, Sortino) are crucial.**
| EQUITY | 0.3 | 0.25 | 0.2 | 0.15 | 0.1 | **Equity markets are relatively stable, so traditional risk metrics (Sharpe, Sortino) and win rate are more important.**
| COMMODITY | 0.2 | 0.15 | 0.25 | 0.1 | 0.3 | **Commodity markets are often driven by supply/demand shocks, so max drawdown and reliability are key.**
| FOREX | 0.25 | 0.2 | 0.15 | 0.15 | 0.25 | **Forex markets are highly liquid, so Sharpe, Sortino, and win rate are important, but reliability also matters.**
| BOND | 0.15 | 0.1 | 0.3 | 0.05 | 0.4 | **Bond markets are relatively stable, so max drawdown and reliability are prioritized, with less emphasis on risk metrics.**
| ETF | 0.2 | 0.15 | 0.2 | 0.1 | 0.35 | **ETF markets are diversified, so a balanced approach with emphasis on reliability, max drawdown, and risk metrics is used.**

**Changes:**

* **CRYPTO:** Increased weight on Sharpe Ratio (0.25) and Sortino Ratio (0.2) to reflect the high volatility and risk of crypto markets.
* **EQUITY:** Maintained traditional weights, with a focus on Sharpe Ratio (0.3), Sortino Ratio (0.25), and win rate (0.15).
* **COMMODITY:** Increased weight on Max Drawdown (0.25) to account for potential supply/demand shocks.
* **FOREX:** Adjusted weights to reflect the high liquidity and competition in forex markets, with a focus on Sharpe Ratio (0.25), Sortino Ratio (0.2), and win rate (0.15).
* **BOND:** Prioritized Max Drawdown (0.3) and reliability (0.4) due to the relatively stable nature of bond markets.
* **ETF:** Used a balanced approach, with increased weights on reliability (0.35) and max drawdown (0.2) to reflect the diversified nature of ETF markets.

These weights can be adjusted based on specific requirements, market conditions, and the goals of the algorithm evaluation.

---

## Q4 — Deploy thresholds

**Prompt:**

> Give me three hard cutoff bands on your 0-100 score: DEPLOY (real money), RESEARCH (paper trade only), JUNK (kill). For each band, list the specific gate conditions (e.g. 'Sharpe>=1.0 AND maxDD<=20% AND n>=200 AND Bonferroni-p<0.05') that must ALSO be true beyond the composite score. Goal: 1-glance Y/N promotion decision for findtorontoevents.ca/audit's 'is this algorithm real-money-grade?' verdict.

**Response:**

**Hard Cutoff Bands:**

### DEPLOY (Real Money)

* Composite Score: ≥ 80
* Gate Conditions:
	+ Sharpe Ratio ≥ 1.2
	+ Max Drawdown ≤ 20%
	+ n_trades ≥ 200
	+ Sortino Ratio ≥ 1.5
	+ Win Rate ≥ 55%
	+ Backtest duration ≥ 1 year

### RESEARCH (Paper Trade Only)

* Composite Score: 40 ≤ score < 80
* Gate Conditions:
	+ Sharpe Ratio ≥ 0.8
	+ Max Drawdown ≤ 30%
	+ n_trades ≥ 100
	+ Sortino Ratio ≥ 1.0
	+ Win Rate ≥ 50%
	+ Backtest duration ≥ 6 months

### JUNK (Kill)

* Composite Score: < 40 or fails gate conditions

**Rationale:**

* DEPLOY band: Requires a high composite score and stringent gate conditions to ensure the algorithm is robust and suitable for real-money deployment.
* RESEARCH band: Allows for paper trading and further refinement, with more relaxed gate conditions to encourage exploration and improvement.
* JUNK band: Immediately flags algorithms that are not viable or require significant overhaul.

**Example Use Case:**

Suppose an algorithm has a composite score of 85, Sharpe Ratio of 1.5, Max Drawdown of 15%, n_trades of 250, Sortino Ratio of 1.8, Win Rate of 58%, and a backtest duration of 18 months.

* Composite Score: 85 ≥ 80 ( passes )
* Gate Conditions:
	+ Sharpe Ratio: 1.5 ≥ 1.2 ( passes )
	+ Max Drawdown: 15% ≤ 20% ( passes )
	+ n_trades: 250 ≥ 200 ( passes )
	+ Sortino Ratio: 1.8 ≥ 1.5 ( passes )
	+ Win Rate: 58% ≥ 55% ( passes )
	+ Backtest duration: 18 months ≥ 1 year ( passes )

Verdict: **DEPLOY** (real-money grade)

In contrast, an algorithm with a composite score of 30, Sharpe Ratio of 0.5, Max Drawdown of 40%, n_trades of 50, Sortino Ratio of 0.8, Win Rate of 45%, and a backtest duration of 3 months would be flagged as **JUNK**.

---

# Model: `@cf/nvidia/nemotron-3-120b-a12b`

## Q1 — Original ask

**Prompt:**

> Give me a scoring method to determine if an algorithm for predicting stocks is high quality or not?

**Response:**

{"id": "chatcmpl-8567b5ee9d21e22e", "object": "chat.completion", "created": 1779685613, "model": "@cf/nvidia/nemotron-3-120b-a12b", "choices": [{"index": 0, "message": {"role": "assistant", "content": "\n\nEvaluating stock prediction algorithms requires a **rigorous, multi-faceted approach** that goes far beyond simple accuracy or backtested returns. Stock markets are noisy, non-stationary, and subject to transaction costs, slippage, and regime changes. A \"high-quality\" algorithm must demonstr

---

## Q2 — Concrete formula

**Prompt:**

> Now give me ONE concrete scoring formula that combines the dimensions you listed into a single 0-100 score. Specify explicit weights, exact metric thresholds, and the minimum-sample-size floor below which the score should be treated as unreliable. Return as pseudocode plus a worked example on a hypothetical algorithm with Sharpe 1.2, Sortino 1.8, max drawdown 18%, win-rate 56% on n=240 trades.

**Response:**

{"id": "chatcmpl-8a9bcd42e5fbf82b", "object": "chat.completion", "created": 1779685637, "model": "@cf/nvidia/nemotron-3-120b-a12b", "choices": [{"index": 0, "message": {"role": "assistant", "content": "\n\n**One\u2011formula \u201cQuality\u2011Score\u201d for a stock\u2011prediction algorithm**  \n(returns a single number\u202f0\u2011100; higher\u202f=\u202fbetter)\n\n---\n\n### 1.  Sub\u2011metrics & normalisation  \n\n| Metric | Why it matters | \u201cGood\u201d threshold (score\u202f=\u202f10

---

## Q3 — Per-asset-class weights

**Prompt:**

> Our dashboard scores algorithms across CRYPTO, EQUITY, COMMODITY, FOREX, BOND, ETF asset classes. How should the weights in your single-score formula differ per asset class? Give a 6x10 weight matrix (6 asset classes × your 10 dimensions) with one-line justification per cell that you change.

**Response:**

{"id": "chatcmpl-b3d785ff391954c6", "object": "chat.completion", "created": 1779685656, "model": "@cf/nvidia/nemotron-3-120b-a12b", "choices": [{"index": 0, "message": {"role": "assistant", "content": "\n\n**Weight matrix \u2013 6 asset classes \u00d7 10 scoring dimensions**  \n(Each row sums to\u202f1.00\u202f\u2248\u202f100\u202f%; the number in parentheses is a one\u2011sentence rationale for why that weight is chosen for the given asset class.)\n\n| Asset Class | Sharpe | Sortino | Max\u202f

---

## Q4 — Deploy thresholds

**Prompt:**

> Give me three hard cutoff bands on your 0-100 score: DEPLOY (real money), RESEARCH (paper trade only), JUNK (kill). For each band, list the specific gate conditions (e.g. 'Sharpe>=1.0 AND maxDD<=20% AND n>=200 AND Bonferroni-p<0.05') that must ALSO be true beyond the composite score. Goal: 1-glance Y/N promotion decision for findtorontoevents.ca/audit's 'is this algorithm real-money-grade?' verdict.

**Response:**

{"id": "chatcmpl-b8658d546b654233", "object": "chat.completion", "created": 1779685684, "model": "@cf/nvidia/nemotron-3-120b-a12b", "choices": [{"index": 0, "message": {"role": "assistant", "content": "\n\n**Hard\u2011cutoff bands for the 0\u2011100 \u201cQuality Score\u201d (QS)**  \n\n| Band | QS range | Promotion verdict (Y/N) | **Mandatory gate conditions** \u2013 **ALL** must be true in addition to the QS falling in the band. |\n|------|----------|--------------------------|----------------

---

# Model: `@cf/openai/gpt-oss-120b`

## Q1 — Original ask

**Prompt:**

> Give me a scoring method to determine if an algorithm for predicting stocks is high quality or not?

**Response:**

{"id": "chatcmpl-97072d142c714f76ac5338114295c111", "object": "chat.completion", "created": 1779685695, "model": "@cf/openai/gpt-oss-120b", "choices": [{"index": 0, "message": {"role": "assistant", "content": "Below is a **structured, multi\u2011dimensional scoring framework** you can use to assess the quality of a stock\u2011prediction algorithm.  \nIt combines statistical\u2011performance metrics, robustness checks, and operational considerations into a single \u201cquality score\u201d (0\u201

---

## Q2 — Concrete formula

**Prompt:**

> Now give me ONE concrete scoring formula that combines the dimensions you listed into a single 0-100 score. Specify explicit weights, exact metric thresholds, and the minimum-sample-size floor below which the score should be treated as unreliable. Return as pseudocode plus a worked example on a hypothetical algorithm with Sharpe 1.2, Sortino 1.8, max drawdown 18%, win-rate 56% on n=240 trades.

**Response:**

{"id": "chatcmpl-fa78070e7ae146faa6aab9c2fb3b391d", "object": "chat.completion", "created": 1779685715, "model": "@cf/openai/gpt-oss-120b", "choices": [{"index": 0, "message": {"role": "assistant", "content": "**One\u2011line \u201cquality\u2011score\u201d formula (0\u202f\u2013\u202f100)**  \n\n```\n# --------------------------------------------------------------\n# INPUTS\n#   SR   = Sharpe ratio\n#   SO   = Sortino ratio\n#   DD   = Maximum draw\u2011down (as a decimal, e.g. 0.18 for 18\u202f

---

## Q3 — Per-asset-class weights

**Prompt:**

> Our dashboard scores algorithms across CRYPTO, EQUITY, COMMODITY, FOREX, BOND, ETF asset classes. How should the weights in your single-score formula differ per asset class? Give a 6x10 weight matrix (6 asset classes × your 10 dimensions) with one-line justification per cell that you change.

**Response:**

{"id": "chatcmpl-2a22f3f8f192472baaef57cea674c3f5", "object": "chat.completion", "created": 1779685726, "model": "@cf/openai/gpt-oss-120b", "choices": [{"index": 0, "message": {"role": "assistant", "content": "**Weight matrix (6\u202fasset classes\u202f\u00d7\u202f10\u202fdimensions)**  \n\n| Asset Class | Sharpe (S) | Sortino (So) | Max\u2011DD (D) | Win\u2011Rate (W) | Sample\u2011Size (N) | Volatility (V) | Consistency (C) | Tail\u2011Risk (T) | Tx\u2011Cost Sensitivity (X) | Model\u2011Stabi

---

## Q4 — Deploy thresholds

**Prompt:**

> Give me three hard cutoff bands on your 0-100 score: DEPLOY (real money), RESEARCH (paper trade only), JUNK (kill). For each band, list the specific gate conditions (e.g. 'Sharpe>=1.0 AND maxDD<=20% AND n>=200 AND Bonferroni-p<0.05') that must ALSO be true beyond the composite score. Goal: 1-glance Y/N promotion decision for findtorontoevents.ca/audit's 'is this algorithm real-money-grade?' verdict.

**Response:**

{"id": "chatcmpl-0f719088d0244fefa8223e2ec6254285", "object": "chat.completion", "created": 1779685740, "model": "@cf/openai/gpt-oss-120b", "choices": [{"index": 0, "message": {"role": "assistant", "content": "**One\u2011glance \u201cReal\u2011Money\u2011Grade?\u201d Decision Matrix**  \n*(used by\u202ffindtorontoevents.ca/audit)*  \n\n| Band | Composite Score (0\u2011100) | **Must\u2011be\u2011TRUE gate conditions** (all must hold) |\n|------|--------------------------|-------------------------

---

# Model: `@cf/zai-org/glm-4.7-flash`

## Q1 — Original ask

**Prompt:**

> Give me a scoring method to determine if an algorithm for predicting stocks is high quality or not?

**Response:**

{"id": "chatcmpl-ac48141de1c651a5", "object": "chat.completion", "created": 1779685748, "model": "@cf/zai-org/glm-4.7-flash", "choices": [{"index": 0, "message": {"role": "assistant", "content": "To determine if a stock prediction algorithm is \"high quality,\" you cannot rely on a single metric like \"accuracy\" (picking the right direction). A high accuracy rate that occurs only during bull markets is useless. A high accuracy rate that results in massive losses during a crash is dangerous.\n\n

---

## Q2 — Concrete formula

**Prompt:**

> Now give me ONE concrete scoring formula that combines the dimensions you listed into a single 0-100 score. Specify explicit weights, exact metric thresholds, and the minimum-sample-size floor below which the score should be treated as unreliable. Return as pseudocode plus a worked example on a hypothetical algorithm with Sharpe 1.2, Sortino 1.8, max drawdown 18%, win-rate 56% on n=240 trades.

**Response:**

{"id": "chatcmpl-b50d7ebc4ed4f5ac", "object": "chat.completion", "created": 1779685810, "model": "@cf/zai-org/glm-4.7-flash", "choices": [{"index": 0, "message": {"role": "assistant", "content": "Here is a comprehensive scoring formula that balances risk-adjusted returns, risk control, and edge quality.\n\n### The Scoring Formula: \"The Alpha-Weighted Composite\"\n\nThis formula assigns a score between 0 and 100 based on three pillars:\n1.  **Risk-Adjusted Return (40% Weight):** Measures efficie

---

## Q3 — Per-asset-class weights

**Prompt:**

> Our dashboard scores algorithms across CRYPTO, EQUITY, COMMODITY, FOREX, BOND, ETF asset classes. How should the weights in your single-score formula differ per asset class? Give a 6x10 weight matrix (6 asset classes × your 10 dimensions) with one-line justification per cell that you change.

**Response:**

{"id": "chatcmpl-a9e06c254f44aac7", "object": "chat.completion", "created": 1779685864, "model": "@cf/zai-org/glm-4.7-flash", "choices": [{"index": 0, "message": {"role": "assistant", "content": "To create an Asset-Class Specific Weight Matrix, we must first define the **10 Dimensions** we are scoring against. These dimensions will be weighted differently based on the specific volatility, liquidity, and structural characteristics of each asset class.\n\n### The 10 Dimensions\n1.  **Risk-Adjusted

---

## Q4 — Deploy thresholds

**Prompt:**

> Give me three hard cutoff bands on your 0-100 score: DEPLOY (real money), RESEARCH (paper trade only), JUNK (kill). For each band, list the specific gate conditions (e.g. 'Sharpe>=1.0 AND maxDD<=20% AND n>=200 AND Bonferroni-p<0.05') that must ALSO be true beyond the composite score. Goal: 1-glance Y/N promotion decision for findtorontoevents.ca/audit's 'is this algorithm real-money-grade?' verdict.

**Response:**

{"id": "chatcmpl-8d2cb16fbc422ce6", "object": "chat.completion", "created": 1779685920, "model": "@cf/zai-org/glm-4.7-flash", "choices": [{"index": 0, "message": {"role": "assistant", "content": "Here are the three hard cutoff bands designed for a \"1-glance\" decision at `findtorontoevents.ca/audit`.\n\nThe logic follows a hierarchy: **Score** is the primary filter, but these **AND/OR gate conditions** are the safety rails that prevent false positives (e.g., a high score from a lucky streak).\n

---

# Model: `@cf/mistralai/mistral-small-3.1-24b-instruct`

## Q1 — Original ask

**Prompt:**

> Give me a scoring method to determine if an algorithm for predicting stocks is high quality or not?

**Response:**

Evaluating the quality of an algorithm for predicting stocks involves multiple metrics to ensure that it is robust, reliable, and profitable. Here are some key scoring methods and metrics you can use:

### 1. **Accuracy**
   - **Definition**: The ratio of correctly predicted outcomes to the total number of predictions.
   - **Formula**: \( \text{Accuracy} = \frac{\text{Number of Correct Predictions}}{\text{Total Number of Predictions}} \)
   - **Limitations**: Does not account for the distribution of correct predictions across different types of outcomes.

### 2. **Precision and Recall**
   - **Precision**: The ratio of true positive predictions to the total number of positive predictions.
     - **Formula**: \( \text{Precision} = \frac{\text{True Positives}}{\text{True Positives} + \text{False Positives}} \)
   - **Recall**: The ratio of true positive predictions to the actual number of positives.
     - **Formula**: \( \text{Recall} = \frac{\text{True Positives}}{\text{True Positives} + \text{False Negatives}} \)
   - **F1 Score**: Harmonic mean of precision and recall.
     - **Formula**: \( F1 = 2 \times \frac{\text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}} \)

### 3. **Profit and Loss (P&L)**
   - **Definition**: The actual monetary gain or loss from following the algorithm's predictions.
   - **Formula**: \( \text{P&L} = \sum (\text{Profit from Correct Predictions}) - \sum (\text{Loss from Incorrect Predictions}) \)
   - **Limitations**: Does not account for risk or volatility.

### 4. **Sharpe Ratio**
   - **Definition**: Measures the risk-adjusted return of the algorithm.
   - **Formula**: \( \text{Sharpe Ratio} = \frac{E(R_p - R_f)}{\sigma_p} \)
     - \( E(R_p - R_f) \): Expected excess return (portfolio return minus risk-free rate)
     - \( \sigma_p \): Standard deviation of the portfolio's excess return
   - **Limitations**: Assumes returns are normally distributed.

### 5. **Sortino Ratio**
   - **Definition**: Similar to the Sharpe Ratio but only considers downside risk.
   - **Formula**: \( \text{Sortino Ratio} = \frac{E(R_p - R_f)}{\sigma_d} \)
     - \( \sigma_d \): Standard deviation of negative asset returns

### 6. **Maximum Drawdown (MDD)**
   - **Definition**: The maximum observed loss from a peak to a trough before a new peak is attained.
   - **Formula**: \( \text{MDD} = \max \left( \frac{\text{Peak} - \text{Trough}}{\text{Peak}} \right) \)
   - **Limitations**: Does not consider the duration of the drawdown.

### 7. **Hit Ratio**
   - **Definition**: The proportion of trades that are profitable.
   - **Formula**: \( \text{Hit Ratio} = \frac{\text{Number of Profitable Trades}}{\text{Total Number of Trades}} \)
   - **Limitations**: Does not account for the magnitude of profits or losses.

### 8. **Profit Factor**
   - **Definition**: The ratio of gross profit to gross loss.
   - **Formula**: \( \text{Profit Factor} = \frac{\sum \text{Profitable Trades}}{\sum \text{Losing Trades}} \)
   - **Limitations**: Does not account for the number of trades.

### 9. **Alpha and Beta**
   - **Alpha**: Measures the active return on an investment, the performance compared to a market index or benchmark.
   - **Beta**: Measures the volatility of the investment compared to the market.
   - **Formula**: Typically derived from regression analysis of the investment's returns against the market's returns.

### 10. **Confusion Matrix**
   - **Definition**: A table used to describe the performance of a classification model.
   - **Components**: True Positives (TP), True Negatives (TN), False Positives (FP), False Negatives (FN)
   - **Use**: Provides a detailed breakdown of prediction accuracy.

### 11. **ROC Curve and AUC**
   - **ROC Curve**: Plots the true positive rate against the false positive rate at various threshold settings.
   - **AUC**: Area Under the ROC Curve, measures the ability of the model to distinguish between classes.
   - **Formula**: AUC is a single scalar value between 0 and 1.

### 12. **Backtesting**
   - **Definition**: Applying the algorithm to historical data to simulate its performance.
   - **Metrics**: Include all of the above metrics applied to historical data.

### 13. **Out-of-Sample Testing**
   - **Definition**: Evaluating the algorithm on data it has not seen during training.
   - **Metrics**: Same as backtesting but on a separate dataset.

### 14. **Transaction Costs**
   - **Definition**: Accounting for the costs associated with executing trades.
   - **Formula**: Include brokerage fees, slippage, and other transaction costs in the P&L calculation.

### 15. **Stress Testing**
   - **Definition**: Evaluating the algorithm under extreme market conditions.
   - **Metrics**: Include MDD, P&L, and other metrics under stress scenarios.

By combining these metrics, you can get a comprehensive view of the algorithm's performance, risk, and reliability. It's essential to consider multiple metrics to avoid overfitting to a single measure and to ensure the algorithm is robust across different market conditions.

---

## Q2 — Concrete formula

**Prompt:**

> Now give me ONE concrete scoring formula that combines the dimensions you listed into a single 0-100 score. Specify explicit weights, exact metric thresholds, and the minimum-sample-size floor below which the score should be treated as unreliable. Return as pseudocode plus a worked example on a hypothetical algorithm with Sharpe 1.2, Sortino 1.8, max drawdown 18%, win-rate 56% on n=240 trades.

**Response:**

Here's a concrete scoring formula that combines the mentioned dimensions into a single 0-100 score. We'll use explicit weights, exact metric thresholds, and a minimum sample size floor.

### Scoring Formula

**Weights:**
- Sharpe Ratio: 25%
- Sortino Ratio: 20%
- Maximum Drawdown: 20%
- Win Rate: 20%
- Profit Factor: 15%

**Thresholds:**
- Sharpe Ratio: 0 (worst) to 2 (best)
- Sortino Ratio: 0 (worst) to 3 (best)
- Maximum Drawdown: 100% (worst) to 0% (best)
- Win Rate: 0% (worst) to 100% (best)
- Profit Factor: 0 (worst) to 10 (best)

**Minimum Sample Size Floor:** 200 trades

**Pseudocode:**

```pseudocode
function calculateScore(sharpe, sortino, maxDrawdown, winRate, profitFactor, nTrades):
    if nTrades < 200:
        return "Unreliable: Sample size too small"

    # Normalize each metric to a 0-100 scale
    normalizedSharpe = min(max((sharpe / 2) * 100, 0), 100)
    normalizedSortino = min(max((sortino / 3) * 100, 0), 100)
    normalizedMaxDrawdown = min(max((1 - maxDrawdown / 100) * 100, 0), 100)
    normalizedWinRate = min(max(winRate, 0), 100)
    normalizedProfitFactor = min(max((profitFactor / 10) * 100, 0), 100)

    # Apply weights
    weightedSharpe = normalizedSharpe * 0.25
    weightedSortino = normalizedSortino * 0.20
    weightedMaxDrawdown = normalizedMaxDrawdown * 0.20
    weightedWinRate = normalizedWinRate * 0.20
    weightedProfitFactor = normalizedProfitFactor * 0.15

    # Calculate the final score
    finalScore = weightedSharpe + weightedSortino + weightedMaxDrawdown + weightedWinRate + weightedProfitFactor

    return finalScore

# Worked example
sharpe = 1.2
sortino = 1.8
maxDrawdown = 18
winRate = 56
profitFactor = 1.5  # Assuming a profit factor based on typical trade outcomes
nTrades = 240

score = calculateScore(sharpe, sortino, maxDrawdown, winRate, profitFactor, nTrades)
print(score)
```

### Worked Example

Given:
- Sharpe Ratio: 1.2
- Sortino Ratio: 1.8
- Maximum Drawdown: 18%
- Win Rate: 56%
- Profit Factor: 1.5 (assuming a typical profit factor based on trade outcomes)
- Number of Trades: 240

**Step-by-Step Calculation:**

1. **Normalize each metric:**
   - Sharpe Ratio: \( \frac{1.2}{2} \times 100 = 60 \)
   - Sortino Ratio: \( \frac{1.8}{3} \times 100 = 60 \)
   - Maximum Drawdown: \( (1 - \frac{18}{100}) \times 100 = 82 \)
   - Win Rate: \( 56 \)
   - Profit Factor: \( \frac{1.5}{10} \times 100 = 15 \)

2. **Apply weights:**
   - Weighted Sharpe: \( 60 \times 0.25 = 15 \)
   - Weighted Sortino: \( 60 \times 0.20 = 12 \)
   - Weighted Max Drawdown: \( 82 \times 0.20 = 16.4 \)
   - Weighted Win Rate: \( 56 \times 0.20 = 11.2 \)
   - Weighted Profit Factor: \( 15 \times 0.15 = 2.25 \)

3. **Calculate the final score:**
   - Final Score: \( 15 + 12 + 16.4 + 11.2 + 2.25 = 56.85 \)

So, the final score for the hypothetical algorithm is **56.85**.

---

## Q3 — Per-asset-class weights

**Prompt:**

> Our dashboard scores algorithms across CRYPTO, EQUITY, COMMODITY, FOREX, BOND, ETF asset classes. How should the weights in your single-score formula differ per asset class? Give a 6x10 weight matrix (6 asset classes × your 10 dimensions) with one-line justification per cell that you change.

**Response:**

When scoring algorithms across different asset classes, it's important to adjust the weights based on the unique characteristics and risk profiles of each asset class. Here's a 6x10 weight matrix for CRYPTO, EQUITY, COMMODITY, FOREX, BOND, and ETF asset classes, with justifications for changes from the original weights.

| Asset Class | Sharpe Ratio | Sortino Ratio | Max Drawdown | Win Rate | Profit Factor | Accuracy | Precision | Recall | F1 Score | Hit Ratio |
|-------------|--------------|---------------|--------------|----------|---------------|----------|-----------|--------|----------|-----------|
| CRYPTO      | 20%          | 25%           | 25%          | 15%      | 10%           | 1%       | 1%        | 1%     | 1%       | 1%        | Volatility and risk are extremely high, so downside risk (Sortino) and Max Drawdown are more important. |
| EQUITY      | 25%          | 20%           | 20%          | 20%      | 10%           | 1%       | 1%        | 1%     | 1%       | 1%        | Equities have moderate risk, so a balanced approach is suitable. |
| COMMODITY   | 20%          | 20%           | 25%          | 15%      | 15%           | 1%       | 1%        | 1%     | 1%       | 1%        | Commodities can have significant price swings, so Max Drawdown and Profit Factor are important. |
| FOREX       | 20%          | 25%           | 20%          | 15%      | 15%           | 1%       | 1%        | 1%     | 1%       | 1%        | Forex markets are highly liquid but can be volatile, so Sortino and Profit Factor are important. |
| BOND        | 30%          | 15%           | 15%          | 20%      | 10%           | 5%       | 2%        | 2%     | 1%       | 5%        | Bonds are generally less risky, so Sharpe Ratio and Accuracy metrics are more important. |
| ETF         | 25%          | 20%           | 20%          | 20%      | 10%           | 1%       | 1%        | 1%     | 1%       | 1%        | ETFs track indices, so a balanced approach similar to equities is suitable. |

### Justifications for Changes:

- **CRYPTO:**
  - **Sortino Ratio (25%)**: Cryptocurrencies are highly volatile with significant downside risk.
  - **Max Drawdown (25%)**: Large price swings are common, making drawdown management crucial.
  - **Sharpe Ratio (20%)**: While important, it's less critical than managing downside risk.

- **COMMODITY:**
  - **Max Drawdown (25%)**: Commodities can have significant price swings due to supply and demand factors.
  - **Profit Factor (15%)**: Important for capturing the magnitude of profitable trades.

- **FOREX:**
  - **Sortino Ratio (25%)**: Forex markets can be volatile, and managing downside risk is important.
  - **Profit Factor (15%)**: Important for capturing the magnitude of profitable trades in a highly liquid market.

- **BOND:**
  - **Sharpe Ratio (30%)**: Bonds are generally less risky, so overall risk-adjusted return is more important.
  - **Accuracy (5%)**: Bonds often have more stable prices, making precise predictions slightly more valuable.
  - **Hit Ratio (5%)**: Bonds often have more stable prices, making the ratio of profitable trades slightly more valuable.
  - **Precision (2%)**: Bonds often have more stable prices, making the precision of profitable predictions slightly more valuable.
  - **Recall (2%)**: Bonds often have more stable prices, making the recall of profitable predictions slightly more valuable.

- **ETF:**
  - **Sharpe Ratio (25%)**: ETFs track indices, so overall risk-adjusted return is important.
  - **Max Drawdown (20%)**: ETFs can experience drawdowns, especially during market downturns.

This weight matrix adjusts the importance of each metric based on the unique characteristics of each asset class, providing a more tailored evaluation of algorithm performance.

---

## Q4 — Deploy thresholds

**Prompt:**

> Give me three hard cutoff bands on your 0-100 score: DEPLOY (real money), RESEARCH (paper trade only), JUNK (kill). For each band, list the specific gate conditions (e.g. 'Sharpe>=1.0 AND maxDD<=20% AND n>=200 AND Bonferroni-p<0.05') that must ALSO be true beyond the composite score. Goal: 1-glance Y/N promotion decision for findtorontoevents.ca/audit's 'is this algorithm real-money-grade?' verdict.

**Response:**

To make a quick, one-glance decision on whether an algorithm is real-money grade, we can define three hard cutoff bands with specific gate conditions. These conditions ensure that the algorithm not only meets the composite score threshold but also adheres to critical performance and reliability metrics.

### Cutoff Bands and Gate Conditions

1. **DEPLOY (Real Money)**
   - **Composite Score**: ≥ 75
   - **Gate Conditions**:
     - Sharpe Ratio ≥ 1.0
     - Sortino Ratio ≥ 1.5
     - Max Drawdown ≤ 20%
     - Win Rate ≥ 55%
     - Profit Factor ≥ 1.2
     - Accuracy ≥ 55%
     - Precision ≥ 55%
     - Recall ≥ 55%
     - F1 Score ≥ 55%
     - Hit Ratio ≥ 55%
     - Number of Trades (n) ≥ 300
     - Bonferroni-corrected p-value < 0.01 (for statistical significance of results)

2. **RESEARCH (Paper Trade Only)**
   - **Composite Score**: 50 to 74
   - **Gate Conditions**:
     - Sharpe Ratio ≥ 0.8
     - Sortino Ratio ≥ 1.2
     - Max Drawdown ≤ 30%
     - Win Rate ≥ 50%
     - Profit Factor ≥ 1.0
     - Accuracy ≥ 50%
     - Precision ≥ 50%
     - Recall ≥ 50%
     - F1 Score ≥ 50%
     - Hit Ratio ≥ 50%
     - Number of Trades (n) ≥ 200
     - Bonferroni-corrected p-value < 0.05 (for statistical significance of results)

3. **JUNK (Kill)**
   - **Composite Score**: < 50
   - **Gate Conditions**:
     - Any algorithm with a composite score below 50 is automatically classified as JUNK, regardless of individual metric values.
     - This band serves as a fail-safe to eliminate poorly performing algorithms.

### One-Glance Decision Criteria

For **findtorontoevents.ca/audit**, the promotion decision can be summarized as follows:

- **DEPLOY (Real Money)**:
  - Composite Score ≥ 75
  - Meets all DEPLOY gate conditions

- **RESEARCH (Paper Trade Only)**:
  - Composite Score between 50 and 74
  - Meets all RESEARCH gate conditions

- **JUNK (Kill)**:
  - Composite Score < 50
  - Automatically classified as JUNK

### Example Decision Flow

1. **Calculate the composite score** using the weighted formula provided earlier.
2. **Check the composite score** against the cutoff bands:
   - If the score is ≥ 75, proceed to check DEPLOY gate conditions.
   - If the score is between 50 and 74, proceed to check RESEARCH gate conditions.
   - If the score is < 50, classify as JUNK.
3. **Verify the gate conditions** for the respective band.
4. **Make the promotion decision** based on the composite score and gate conditions.

This approach ensures a rigorous and quick evaluation process, providing a clear Y/N promotion decision for the algorithm's real-money grade status.

---

