# Quantitative Edge Analysis Plan — findtorontoevents.ca/audit

## Objective
Analyze prediction system performance across all asset classes (stocks, crypto, forex, ETFs, bonds, commodities, futures), identify statistical unbiased edges, evaluate ML algorithms & backtesting integrity, and produce actionable recommendations to reach Quant/Hedge-fund-grade prediction quality.

---

## Stage 1 — Data Collection (Parallel)
1. **Website Audit** — Visit findtorontoevents.ca/audit to scrape current performance dashboard, pick history, and metrics displayed.
2. **GitHub Repository Analysis** — Clone and analyze the codebase structure, ML models, backtesting framework, data pipelines, and feature engineering.
3. **MySQL Database Analysis** — Connect to ejaguiar1_stocks and ejaguiar1_backtests databases, extract performance tables, pick history, backtest results, and feature data.
4. **Industry Standards Research** — Research quantitative finance industry standards for edge detection, bias avoidance, regime change detection, and walk-forward analysis best practices.

## Stage 2 — Performance Analysis (Parallel, after Stage 1 data available)
1. **Short-term Performance Analysis** — Break down last 7 days of picks by asset class, daily PnL, win rate, Sharpe, Sortino, max drawdown.
2. **Long-term Performance Analysis** — Aggregate performance over 30d, 90d, 1y+ horizons per asset class. Identify which asset classes show consistent edge.
3. **Rolling Window Edge Stability** — Compute edge metrics on rolling 7d, 30d, 90d, 1y windows to detect decay patterns.
4. **Cross-Symbol Variance Analysis** — Within each asset class, measure if edge is driven by a few lucky symbols or is class-wide.

## Stage 3 — Statistical Edge Detection & ML Evaluation (Parallel)
1. **Unbiased Edge Detection** — Apply industry-standard filters (out-of-sample testing, walk-forward validation, regime-aware analysis) to find true edges per asset class.
2. **ML Algorithm Strength Assessment** — Evaluate predictive power, feature importance stability, overfitting indicators, and generalization capability.
3. **Backtesting Integrity Audit** — Check for lookahead bias, survivorship bias, data snooping, overfitting, and proper cross-validation.
4. **Edge Decay Analysis** — Track how edge metrics degrade as lookback horizon expands per asset class.

## Stage 4 — Recommendations & Report Writing
1. **Asset Class Reliability Ranking** — Which asset classes are ready for real capital deployment.
2. **Edge Filters per Asset Class** — Specific unbiased filters that identify winning picks.
3. **System Enhancement Roadmap** — Concrete steps to improve PnL per asset class.
4. **Industry Best Practices Integration** — How to implement continuous edge discovery, regime detection, and automated model validation.
5. **Final Report** — Comprehensive HTML report suitable for publishing on findtorontoevents.ca/updates/

## Skills Used
- `deep-research-swarm` — Industry standards research on quantitative edge detection
- `report-writing` — Final comprehensive report
- Data analysis via Python/MySQL connectors

---
