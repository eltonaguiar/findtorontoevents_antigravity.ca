
# Investigation of the "Rolling 100" Performance Metric

**Summary:**
The reported figure of "+313.43%" for the "rolling 100" metric was not found in the codebase and appears to be based on a misunderstanding or outdated information. The actual calculated metric, `total_pnl_pct_compounded_rolling_100`, shows -41.63%. This metric is derived from the compounded PnL of the last 100 trades, with individual trade PnLs capped at +/- 10%. While this provides a bounded view of recent performance, it can be misleading when considered in isolation.

---

## 1. Origin of the +313.43% Figure

**Search Results:**
Extensive `grep` searches across the codebase, including Python scripts, HTML templates, and JavaScript files within the `audit_dashboard/` directory, failed to find any instance of "+313.43%" or variations thereof being displayed as a performance metric. The `grep` results from peer reports (`reports/peer_claude-*`) explicitly state that this figure could not be found and is likely erroneous or based on stale data.

**Conclusion:** The "+313.43%" figure is not a currently active or calculated metric within the `audit_dashboard/` codebase.

---

## 2. Data Flow and Calculation of `total_pnl_pct_compounded_rolling_100`

**Script/Function:** `audit_trail/dashboard_generator.py`
**Calculation Function:** `_compound_rolling_window(picks, window=100, max_pnl_pct=10.0)`

**Details:**
*   **Base Data Source:** The function operates on `resolved_closed` trades, which are presumably derived from pick data.
*   **Calculation Method:**
    *   It considers the **last 100 closed trades** (chronologically sorted by timestamp and symbol).
    *   The per-trade `pnl_pct` is **capped** at `+/- max_pnl_pct` (10.0% by default). This is intended to neutralize the impact of extreme outliers or potential data errors.
    *   The capped per-trade PnLs are then **geometrically compounded** (`prod *= 1.0 + capped / 100.0`).
    *   The final result is the compounded percentage return over the window.
*   **Rendering:** The `audit_dashboard/template.html` file displays this metric with the label "Rolling 100". The tooltip associated with this metric accurately describes its calculation: "Last 100 closed trades compounded equal-weight, ±10% per-trade cap. Bounded headline metric for recent performance."

---

## 3. Assessment of Validity

*   **Compounding:** The metric uses geometric compounding over the last 100 trades.
*   **Trustworthiness:**
    *   **Misleading Potential:** While the 10% cap per trade and the rolling 100-trade window attempt to bound the metric, it can still be misleading. A compounded return over a fixed, short window might not accurately represent the overall strategy's long-term performance or risk profile. High variance within the capped trades, even if the individual returns are not astronomical, can still lead to a figure that doesn't reflect the general market conditions or the strategy's consistency.
    *   **Comparison:** The metric shows -41.63%, while `total_pnl_pct_compounded_ew` (compounded over the entire ledger) shows -92.95%. This significant difference indicates a substantial performance change over time, making the "Rolling 100" metric a potentially optimistic, but incomplete, snapshot.
    *   **Overall Assessment:** The metric is **not trustworthy** as a sole indicator of the strategy's viability or overall performance due to its limited scope and potential for creating a skewed perception of recent success or failure.

---

## 4. Recommendation

The "Rolling 100" metric, as currently presented, is insufficient and potentially misleading. It should not be the primary headline metric.

**Recommended Actions:**

1.  **Prioritize Comprehensive Metrics:** Display metrics that offer a more complete view of performance and risk.
    *   **`total_pnl_pct_compounded_ew` (-92.95%):** This provides the compounded return over the entire trading history, offering a grounded perspective on the strategy's historical aggregate performance.
    *   **Risk-Adjusted Return:** Implement and display a Sharpe Ratio. Metrics like `mercury_net_sharpe_daily_annual` or `mercury_net_sharpe_per_trade_annual` (if available and correctly calculated) are crucial for understanding returns relative to the risk taken.

2.  **Contextualize Rolling Metrics:** If a rolling window metric is still desired for recency:
    *   **Rolling Sharpe Ratio:** Display a rolling Sharpe Ratio (e.g., 30-day) to show how risk-adjusted performance has evolved.
    *   **Rolling Win Rate:** Display a rolling Win Rate (e.g., over the last 100 trades) to indicate recent consistency in profitable trades.

3.  **Clarify Display:** Ensure any displayed metric has clear, unambiguous labeling and tooltips that explain its calculation, limitations, and what it represents (e.g., compounded vs. arithmetic, window size, capping, risk adjustment).

**Conclusion:** Replace the potentially misleading "Rolling 100" headline metric with more robust indicators of overall performance and risk-adjusted returns, such as the full-ledger compounded PnL or a Sharpe Ratio.
