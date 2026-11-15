# Further Essential Questions — to Find a Profitable Algorithm
**Date:** 2026-11-15  
**Purpose:** Questions that must be answered (with data, not opinion) before any claim of a profitable algorithm is credible.  
**Core rule:** Every answer must carry `(asset_class \| n \| timeframe)` and be reproducible from `pf_registry.json`, `money_ready_verdict.json`, `dashboard_data.json`, or `ejaguiar1_stocks`/`ejaguiar1_backtests` via `tools/db_env.py`.

---

## 1. Measurement & data integrity (must answer first)

Q1.1 What fraction of `recent_closed` rows have blank `entry_time` (currently ~49.9%)? How does WR/PF change when those are excluded vs. imputed?
Q1.2 How many `TIME_EXIT` rows have `exit_price == entry_price` (fabricated flats)? What is the PF impact of removing them?
Q1.3 What fraction of `active_raw` picks have blank `current_price` (currently ~87.4%)? Are any "0.0% PnL" displayed picks actually stale/unpriced?
Q1.4 Is `total_picks` null on every class row? If so, what is the true `n` behind each published PF/WR?
Q1.5 Is `dashboard_data.json` stale (>2h old)? Is the local copy (26 days stale) being mistaken for live?

## 2. Statistical validity & multiple testing

Q2.1 For any claimed edge, what is `nb_trials` = the total number of strategies/families tested that season? Is DSR computed with this correct `nb_trials` (not nb_trials=1)?
Q2.2 Does the edge survive SPA (White's Reality Check, family-wise p≤0.10) and PBO (≤0.55, requires ≥5 strategies)?
Q2.3 Is the edge stable across 2d/7d/30d windows, or does WR/PF swing wildly (regime noise)?
Q2.4 Is the edge multi-source (>60% from one `source_system` = concentration, not edge)?
Q2.5 Was the selection rule pre-registered and never shown the test month (walk-forward)?
Q2.6 Were realistic per-class costs applied (fees/spreads/funding/roll)? What is the breakeven cost per trade?

## 3. Per-class diagnosis

Q3.1 EQUITY: Does `stocks_rsi2_pullback` (75.7% WR, p=6×10⁻⁶, Sharpe 4.84) hold on clean out-of-sample vs SPY total return with n≥500?
Q3.2 ETF: Can the ETF universe be expanded (XLF/XLE/XLK) to clear n≥150 for OOS_READY? Does PF≥1.3 hold after costs?
Q3.3 CRYPTO: Can `crypto_ohlcv` be backfilled to ≥180 days of 1h bars? Does intrabar-re-resolved CRYPTO pass clean OOS vs BTC-USD?
Q3.4 COMMODITY/FUTURES: Is there a real commodity feed (no crypto proxies labelled COMMODITY)? What is n post-dedup?
Q3.5 FOREX: Is there any directional filter with clean WR≥50% and PF≥1.5 after spread costs, or should FOREX remain blocked?
Q3.6 BOND: Is `FRED_API_KEY` set? Can n rise from 18 toward 100?
Q3.7 MUTUAL FUNDS: Is MF registered as a class? Is NAV data sourced? (Probability near 0% until then.)

## 4. Economic & execution reality

Q4.1 What are the realistic round-trip costs per class (fees + spread + slippage + funding + roll + commissions)? Source: `tools/data/transaction_costs.json` plus real broker data.
Q4.2 What is the breakeven cost per trade for the claimed edge? If realized costs exceed it, the edge dies.
Q4.3 What is the maximum drawdown at the proposed position sizing (Kelly / ¼ Kelly)? Does it exceed the 20% MDD cap?
Q4.4 Is position sizing capacity-aware (does the edge degrade at larger size)?

## 5. Promotion & kill gates

Q5.1 Has the edge passed clean OOS with n≥100, PF≥1.5, WR≥50%, MDD<20% on the forward record (T2 charter)?
Q5.2 Is there a pre-registered kill criterion (e.g., any month PF<0.5 twice, or 3-month rolling PF<1.0 → stop and re-audit)?
Q5.3 Is there a separate risk-management dashboard (`audit_dashboard/risk_management.html`) independent of signal quality?

## 6. The "boring alternative" question

Q6.1 Would deploying capital into low-cost broad index ETFs/mutual funds (ER ≤0.20%, high AUM, low turnover) produce higher risk-adjusted returns than any unproven signal from this system?
Q6.2 If yes, why is the research system being funded at all rather than allocating to the boring alternative while research continues?

---

**Answering standard:** A question is "answered" only when backed by a reproducible query against canonical data, with `(asset_class \| n \| timeframe)` stated, and all mandatory data-integrity filters applied. Otherwise it remains open.

---
