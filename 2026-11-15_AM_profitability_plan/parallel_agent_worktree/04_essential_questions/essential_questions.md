# Essential Questions to Find a Profitable Algorithm

These are the questions that must be answered before any capital is deployed. They go beyond the final_v3/final_v4 plan and address the deeper structural problems.

---

## Measurement & Data Integrity (P0)

1. **What is the ground truth for PnL?** Are we computing PnL from entry/exit prices vs real market data (Binance, Nasdaq, er-api), or from potentially corrupted ledger entries? 53 picks are frozen at pnl_pct=0% — is that real or a bug?

2. **What is the exact cost model per asset class?** Spread, commission, slippage, fees, funding, bid-ask, market impact. Are these included in ALL backtests or only some?

3. **What is the true resolution_method distribution?** All 3,500 closed rows are missing valid resolution_method. How were WON/LOST/CLOSED/EXPIRED actually determined? Is EXPIRED→WON mislabeling still happening?

4. **What is the true dedup logic?** sync_summary_picks_json.py deduplicates by timestamp key, but active picks may have different `signal_time` vs `closed_at` across files. Are duplicate picks inflating n?

5. **Is the price feed alive?** `fetch_prices.php` returns HTTP 404 since 2026-04-29. Are live PnL numbers real or stale?

6. **What is the cross-ledger reconciliation?** money_ready_verdict (CRYPCO n=3,705) vs pf_registry (CRYPCO n=22,055) — a 6× difference. Which is right? Row-level reconciliation not published.

---

## Statistical Rigor (P0)

7. **What is the effective N after multiple-testing correction?** 683-strategy zoo tested without Bonferroni/Benjamini-Hochberg. How many false positives survive?

8. **What is the PBO (Probability of Backtest Overfitting)?** PBO ≤ 0.10 required. Has PBO been computed for any strategy?

9. **What is the DSR (Deflated Sharpe Ratio) with cumulative trial count?** DSR ≥ 0.95 required. Has DSR been computed?

10. **What is the SPA (Superior Predictive Ability) test result?** Family-wise alpha 0.10 required. Has SPA been run?

11. **What is the block-bootstrap CI on net expectancy?** Lower bound must exceed 0. Has this been computed?

12. **What is the walk-forward result with purged/embargoed windows?** Fixed 60-day calendar intervals required. Has this been implemented?

---

## Asset Class Specific Questions

### Mutual Funds
13. Can a mutual fund ever be an active pick class given daily NAV strikes, no intraday TP/SL, frequent-trading limits, and load/12b-1 costs?
14. If mutual funds are only a passive core allocation, what is the optimal low-fee universe (ER ≤ 0.09%, AUM ≥ $1B, turnover ≤ 20%, track record ≥ 10 years)?
15. What is the expected return of a 60/40 low-cost index allocation vs the prediction system's alpha? (Likely: beta wins.)

### Equity
16. Does EQUITY have any alpha beyond SPY beta? The pre-registered SPY gate FAILED (t=1.05, beat-SPY 45.53%, median excess -0.57%).
17. What is the optimal sector-neutral QVM universe? Can mutual fund top-10 holdings serve as the equity screen universe?
18. What is the cost-adjusted PF threshold for equity to be money-ready? (Currently 1.154 at n=738 — marginal.)

### Crypto
19. After the gap-aware fill fix, does CRYPCO reach breakeven (PF ≈ 1.00) or can it exceed PF ≥ 1.15 after all costs (taker fees + funding + slippage)?
20. Which specific strategies are responsible for the negative expectancy (-5.86%)? Can they be killed without killing the whole class?
21. Is there any crypto strategy with SubQ coverage ≥ 7/10?

### ETF
22. What explains the ETF cohort mismatch (official PF 0.022 vs registry PF 1.788)? Which is correct?
23. Can any ETF strategy overcome 267% cost ratio?

### Forex / Commodity / Bond / Futures
24. Is there any path to profitability for these classes, or should they remain blocked indefinitely?
25. What minimum data quality (n, feed, contract identity) is required before unblocking?

---

## Structural Questions

26. **Beta vs Alpha separation:** What fraction of the system's apparent returns are just market beta (long bias, equity risk premium) vs genuine alpha?
27. **Single-source concentration:** All 166 cells are single-source. CRYPCO top-source share 0.9847; EQUITY 1.0. Can any multi-source confirmation be obtained?
28. **Direction bias:** 100% LONG-biased active picks (25/25 STRONG_BUY/WATCH). Is there any short-side edge, or is the system structurally long-only?
29. **Time decay:** Do strategies decay over time? Are older backtests still valid in current regimes?
30. **Capital constraints:** What position sizing (1-2% risk per trade, quarter-Kelly) makes the system viable? What is the maximum drawdown tolerance?

---

## The "Real Money" Question

31. **If you were given $100,000 to paper trade tomorrow, which single strategy would you trade, at what size, with what stop loss, and what is your expected monthly return?** This question must have a concrete, auditable answer before any live deployment.

32. **What is the kill-switch condition?** At what drawdown level (daily/weekly/monthly) does the system halt all trading?

33. **What is the proof of repeatability?** Has any strategy demonstrated profitability across ≥ 3 distinct market regimes (bull, bear, sideways) with ≥ 100 forward closes?

---

## Bottom Line

Until questions 1-12 (measurement + statistical rigor) are answered with clean data, and question 31 has a concrete answer, no asset class should be considered for real-money deployment. The system is research infrastructure, not a money engine.
