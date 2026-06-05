# Methodology for Real-Money Readiness - June 2026 (Revised)

This document defines the rigorous approach for moving asset classes from "INSUFFICIENT_DATA" or "NOT_READY" to "READY" status.

## 1. Data Accumulation & Signal Expansion
**Goal:** Reach $n_{resolved} \ge 100$ per asset class with a stable, non-correlated edge.

### Methodology:
- **Gap Analysis:** Identify classes with $n < 100$.
- **Signal Sourcing:**
    - **Equity:** Integrate Analyst Consensus, Earnings Surprises, and Fundamental screens (Debt/Equity, ROE).
    - **Crypto:** Integrate On-chain flows (Whale alerts), Funding Rate anomalies, and Social Sentiment.
    - **Commodity/Forex:** Integrate COT (Commitments of Traders) and Macro Indicators (Interest Rate Diff).
- **Validation Pipeline:**
    - **Dedup:** strictly apply `(symbol, timestamp, source)` dedup.
    - **Concentration Check:** Any signal source providing $>60\%$ of wins is flagged as "concentration" and requires multi-source corroboration.
    - **OOS Stability:** Compare 7d vs 30d vs 90d WR/PF. If the variance exceeds $15\%$, the edge is "unstable".
    - **Signal Decay:** Add a rolling window analysis (compare last 30 vs previous 70 signals). If recent WR is significantly lower (e.g., >15%), flag for review or reduce sizing.
    - **Signal Correlation:** Run a correlation matrix of *signals* within a class. Correlation $>0.7$ requires consolidation or dropping one to ensure true diversification.

## 2. Strategy Wire-up (Backtest $\to$ Production)
**Goal:** Convert proven historical edges into live signals.

### Methodology:
- **Mining:** Query `ejaguiar1_backtests` for strategies where $\text{PF} \ge 1.5$, $\text{WR} \ge 50\%$, and $n \ge 30$.
- **Wire-up Protocol:**
    - Implement the logic in `alpha_engine` (or relevant scanner).
    - Use a "Shadow Mode" period:
        - Emit picks to DB marked as `shadow=True`.
        - **Shadow Exit Condition:** Min 30 resolved signals **or** 60 calendar days, whichever comes first.
        - **Shadow Failure:** If `Shadow PF < 0.5` after $n=15$, kill shadow test and flag for review.
        - **Validation:** Compare Shadow PF vs Backtest PF. If $\text{Shadow PF} \ge 0.8 \times \text{Backtest PF}$, move to production.

## 3. Risk Management Implementation
**Goal:** Cap MDD at $\le 20\%$ using quantitative sizing.

### Methodology:
- **Sizing Engine:** Deploy `alpha_engine/kelly_position_sizer.py`.
- **Formula:** Quarter-Kelly ($\text{Fraction} = 0.25$).
- **Hyro Overlay:**
    - **Daily Soft-Stop:** If daily PnL $< -2\%$ *per asset class*, pause new emissions for that class only.
    - **DD Halt:** If rolling 30d MDD $> 30\%$, the class is "kill-switched."
    - **Re-Entry:** Manual review + 10-day period with rolling 30d MDD $< 15\%$.
- **Verification:** Simulation on `at_raw_picks` to evaluate MDD impact.

## 4. System Maintenance & Audit Parity
**Goal:** Ensure the audit surface is a truthful reflection of the DB.

### Methodology:
- **EST Fix:** Update `render_incidents_page.py` to convert UTC to `America/New_York`.
- **Smart Picks Refactor:**
    - SQL query-based (dedup + concentration-aware).
- **Verification:** Dashboard vs. raw SQL `status=decisive` counts.
- **Data Freshness:** Add dashboard status cell for `max(timestamp)` across data sources (flag if $> 24h$ stale).
