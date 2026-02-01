# Stock Algorithm Validation Methodology

This document outlines the standardized, multi-phase process for developing, testing, and validating any stock selection algorithm within the STOCKSUNIFY ecosystem. The goal is to ensure robustness, guard against overfitting, and provide a clear measure of real-world performance.

---

## Guiding Principles

1.  **Falsifiability**: Every strategy must make specific, testable predictions that can be proven right or wrong.
2.  **No Look-Ahead Bias**: The testing environment must never allow an algorithm to use information that would not have been available at the time of the decision.
3.  **Real-World Costs**: Performance must account for assumed transaction costs and slippage.
4.  **Benchmark Awareness**: All strategies must be compared against a relevant benchmark (e.g., SPY) to determine if they provide true alpha.

---

## Phase 1: In-Sample Optimization (Historical Backtest)

This phase is for initial discovery and parameter tuning. It is performed on a distinct historical dataset.

-   **Objective**: To find the optimal parameters for an algorithm.
-   **Dataset**: A defined historical period (e.g., Jan 2020 - Dec 2023).
-   **Process**:
    1.  Define the tunable parameters for the strategy (e.g., moving average lengths, RSI thresholds, scoring weights).
    2.  Run the algorithm repeatedly over the In-Sample dataset, adjusting parameters to maximize a primary **Objective Function**.
    3.  **Objective Function**: Typically the **Sharpe Ratio** (risk-adjusted return), but could also be the Profit Factor or Calmar Ratio depending on the strategy's goal.
-   **Outcome**: A single "optimal" set of parameters for the given strategy based on historical data.
-   **Warning**: High performance in this phase is expected but proves nothing on its own. It is simply a measure of how well the model can be *fit* to past data.

## Phase 2: Out-of-Sample Validation (Walk-Forward Test)

This is the most critical phase for guarding against **overfitting**.

-   **Objective**: To verify if the optimized parameters from Phase 1 hold up on data the model has never seen.
-   **Dataset**: A subsequent historical period that was NOT used in Phase 1 (e.g., Jan 2024 - Present).
-   **Process**:
    1.  Take the single, "optimal" set of parameters from Phase 1.
    2.  Run the algorithm **only once** over the entire Out-of-Sample dataset.
-   **Success Criteria**:
    *   **Primary Rule**: The key performance metrics (Sharpe Ratio, Total Return) must not degrade by more than **30%** from the In-Sample results. A larger drop indicates the model was overfit to the historical data.
    *   **Secondary Rule**: The strategy must still outperform its benchmark (e.g., buy-and-hold SPY) during the OOS period.
-   **Outcome**: A "Pass" or "Fail" verdict. A strategy that passes is considered robust and may proceed to live deployment. A strategy that fails must be redesigned or have its parameters re-evaluated.

## Phase 3: Live Forward-Testing (The "Truth Engine")

This is the ultimate, unbiased test of a strategy's real-world efficacy. This is already implemented in our project.

-   **Objective**: To measure the true, "walk-forward" performance of a deployed algorithm.
-   **Dataset**: Real-time market data from the moment a strategy is deployed.
-   **Process**:
    1.  The algorithm is run daily via the GitHub Actions job, and its picks are timestamped and archived in an immutable ledger (`/data/v2/history`).
    2.  The `scripts/v2/verify-performance.ts` script (The "Truth Engine") runs weekly.
    3.  It checks the ledger for any picks that have completed their designated `timeframe` (e.g., a "7d" pick made 7 or more days ago).
    4.  It fetches the current market price (the "exit price") and calculates the real performance.
    5.  Results are written to a performance report, which is aggregated and displayed on the V2 Dashboard.
-   **Outcome**: An ever-growing, unbiased track record of the strategy's live performance. This is the "ground truth" that all other tests are measured against.

## Key Metrics for Evaluation (All Phases)

For any given test run, the following metrics will be calculated and reviewed:

-   **Total Return (%)**: The total percentage gain or loss over the period.
-   **Benchmark Return (%)**: The total return of a buy-and-hold position in SPY over the same period.
-   **Win Rate (Hit Ratio)**: The percentage of trades that were profitable.
-   **Profit Factor**: Gross winnings from all winning trades divided by the absolute gross losses from all losing trades. A value > 2.0 is considered strong.
-   **Sharpe Ratio**: The measure of risk-adjusted return. (Assumes a risk-free rate of 0).
-   **Max Drawdown (%)**: The largest peak-to-trough percentage drop in portfolio value during the period.
-   **Expectancy**: `(Win Rate * Average Win Size) - (Loss Rate * Average Loss Size)`. A positive value indicates a profitable system over time.
