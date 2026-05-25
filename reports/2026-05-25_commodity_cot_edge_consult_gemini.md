# Commodity COT Edge Triangulation — Google Gemini CLI reply

- Engine: Google Gemini CLI
- Model: gemini-default
- Date: 2026-05-25
- Prompt: /tmp/commodity_edge_prompt.txt
- Candidate edge: top_edges_per_class.json::by_class.COMMODITY (multi_asset_copytrader + cot, n=137, PF 3.274)
- Prior context: H-001 REJECTED 2026-05-20 (M-095 look-ahead leakage, same source+family)

---

1. **Verdict**: **DATA_QUALITY_LEAKAGE**. Confidence: **95%**. The proximity to the rejected H-001 hypothesis and the window straddling the "fix" date is a smoking gun for look-ahead contamination.

2. **Residual Leakage Probability**: **>90%**.
   **Sanity Check**: `select (entry_time >= '2026-05-20') as post_fix, count(*), avg(win), sum(profit)/sum(abs(loss)) as pf from trades group by 1;` 
   If the edge is real, performance should be stable; if it's leakage, the `post_fix=True` bucket will show a sub-1.0 PF.

3. **71/200 Bonferroni Pass**: **Systemic Contamination (Common Leakage)**. This is not a "gold mine"; it is a "data spill." The cells are massively correlated because they all likely exploit the same look-ahead window in the COT report. Bonferroni assumes independent tests; when tests are perfectly correlated, the effective $n$ of the search is 1, not 200, making the adjusted alpha meaningless.

4. **Slippage Estimate**: **40–60 bps**. Scraping an external signal source implies you are the last to know. You are chasing the move of the copy-trader, who is chasing the move of the COT-positioned whales. Expect significant "alpha decay" between signal generation and execution. A 3.27 PF in backtest likely collapses to ~1.40 or lower in production.

5. **Sizing**: **NO**.
   **Pre-trade Test**: **Clean OOS Verification**. Performance must remain significant ($PF > 1.5, n > 50$) on data strictly generated after 2026-05-20 using the 3-day publication-lag guard.

6. **Sharpest Experiment**: **Time-Partitioned Attribution**. Filter the 137 candidate trades to include only those with `entry_time` at least 4 days after the COT `as_of_date`. If $n$ drops by >70% or the $PF$ drops below 1.1, the edge is a ghost of the look-ahead bug. This is a zero-cost SQL/Python check that will likely invalidate the edge in seconds.
