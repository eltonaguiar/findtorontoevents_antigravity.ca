# Core Statistical & Risk Measures — Cross-Asset Proof Standard
## Minimum metrics, backtest requirements, forward-test requirements, and asset-class-specific adjustments

**Date:** 2026-11-15  
**Worktree:** hilarious-seer  
**Location:** `WIRED_IN/2026-11-15T065338Z_hilarious-seer/`

---

## Must-Pass Metrics (compute net of all costs)

| Metric | Backtest minimum | Forward-test minimum | Why it matters |
|--------|------------------|----------------------|---------------|
| Expectancy per trade | > 0 after costs | > 0 and stable | Absolute edge |
| Profit factor | ≥ 1.3 | ≥ 1.2 | Gross wins / gross losses |
| Sharpe (annualized) | ≥ 0.7 (deflated) | ≥ 0.5 realized | Risk-adjusted return |
| Sortino | ≥ 1.0 | ≥ 0.7 | Downside risk |
| Calmar / Sterling | ≥ 0.4 | ≥ 0.3 | Return / max drawdown |
| Max drawdown | ≤ 20–25% | ≤ same or better | Capital preservation |
| Win rate + payoff | Win ≥ 40% or payoff ≥ 1.8 | Same direction | Consistency of edge |
| Bootstrap CI on mean excess return | Excludes 0 at 95% | Same | Statistical significance |
| t-stat on returns | ≥ 2.0 | ≥ 1.5–2.0 | |
| Deflated Sharpe / White’s Reality Check | p < 0.05 after all trials | n/a (already corrected) | Multiple-testing control |
| Walk-forward efficiency | ≥ 50–60% | n/a | Parameter stability |
| Monte Carlo (block bootstrap) | ≥ 70% of paths positive; 5th-percentile not catastrophic | Same on realized trades | Path dependence / luck |
| Regime robustness | Positive expectancy in ≥ 3 of 4 regimes (bull/bear/sideways/high-vol) | Same | Not a single-regime artifact |
| Shuffle control | Shuffled prices do **not** reproduce edge | n/a | No look-ahead / leakage |

---

## Risk-Management Methods That Must Be Present and Validated

- Explicit position sizing (fixed fractional, volatility targeting, or Kelly fraction ≤ 0.25)
- Hard stop or ATR-based stop + take-profit (or time-based exit)
- Portfolio-level constraints (max concentration, max sector/asset-class exposure, correlation cap)
- Full friction model (spread + commission + slippage + funding/borrow + taxes)
- Drawdown circuit breakers

---

## Backtest Requirements (all asset classes)

- Strict chronological train / test / walk-forward (no future data in features)
- Rolling recalibration
- Full cost model specific to the asset class
- Multiple-testing correction using the project-wide trial count (~871 strategies in this repo)
- Reproducible code + fixed seeds + versioned data
- Control experiments (permuted prices)

---

## Forward-Test Requirements (all asset classes)

- Pre-registered before any live/paper results are known (rules, universe, parameters, TP/SL, sizing frozen)
- Minimum independent trades: 60 for significance; 100+ preferred
- Same metrics as backtest, computed only on the forward window
- Public or internal audit trail (timestamped picks → outcomes)
- Decision thresholds declared in advance (e.g., “kill if 90-day Sharpe < 0 after 40 trades”)

---

## Asset-Class Specific Adjustments

| Asset class | Extra considerations | Typical cost model | Sample-size notes | Special risks |
|-------------|----------------------|--------------------|-------------------|---------------|
| **Stocks** | Survivorship bias, corporate actions, liquidity | Spread + commission + slippage (higher for small caps) | Need longer history; many strategies thin | Earnings gaps, delistings |
| **ETFs** | Tracking error, expense ratio | Lower spreads; still model bid-ask + commissions | Outcomes table has only ~181 ETF rows — treat as under-powered | Sector concentration |
| **Crypto** | Funding rates, weekend gaps, exchange risk | Spread + taker fees + funding + slippage (volatile) | Largest sample (36k+ outcomes) — highest priority for proof | Regime shifts, exchange outages |
| **Forex** | Swap/rollover, session liquidity | Spread + commission + swap | Second-largest sample (16k+) | Overnight gaps, central-bank events |
| **Bonds / Fixed income** | Duration, credit spreads, yield curve | Bid-ask + transaction costs (often higher) | Usually lower frequency | Interest-rate regime dependence |
| **Commodities** | Roll costs, contango/backwardation | Futures commission + roll + slippage | Futures data preferred | Storage, seasonality |
| **Mutual funds** | Load fees, expense ratios, cash drag, delayed pricing | Expense ratio + any load + trading costs inside fund | Harder to prove alpha; often better as benchmark | Survivorship, style drift |

For mutual funds and some bond products, "beating" usually means information ratio vs. a proper benchmark after fees, not raw directional edge.

---

## Ideal Operational Setup for Daily Picks → Database

Given the existing architecture (`ejaguiar1_stocks.trading_picks` as the live book, outcomes tables, and GitHub as the source of research):

### Recommended Flow (daily generation + weekly bulk load)

**1. Daily pick generation (GitHub Actions or scheduled job)**
- A workflow (or local/self-hosted agent) runs the current pre-registered strategies.
- Outputs a timestamped JSON (or CSV) with columns matching the schema:
  ```
  timestamp, asset, asset_class, strategy_id, direction, expected_return,
  tp, sl, horizon, confidence, regime, position_size, data_version, code_version
  ```
- Commits the JSON to a dated path, e.g. `picks/2026-11-15/picks.json` (or pushes to a private artifact store).
- This creates an immutable, auditable record.

**2. Weekly (or daily) ingestion job**
- A separate job (cron, GitHub Action, or simple script) reads the new JSON files since last run.
- Validates schema and that the `strategy_id` exists in the hypothesis registry.
- Inserts into `trading_picks` (live book).
- Later, when outcomes are known, a resolver job writes to `at_pick_outcomes` / `at_signal_outcomes`.

**3. Why this shape works for investors**
- Pre-registration is enforced by the Git commit timestamp of the JSON.
- No retroactive changes to picks.
- Outcomes can be independently joined and scored.
- You can publish a public "picks ledger" or signed hashes if desired.
- Matches the near-miss rule: parameters stay frozen; only the paper/live clock extends.

### Minimal Viable Version Right Now

- Keep generating picks into JSON (or directly into a staging table).
- Nightly or weekly job that upserts into `trading_picks`.
- A scoring job that joins closed trades to outcomes and writes the Phase 5 metrics into a `strategy_performance` table or report.
- Surface only strategies that have passed (or are actively in a pre-registered forward test) on the audit page.

This setup, combined with the metrics and proof standard above, is what lets you show an investor: **"Here is the pre-registered rule, here is the immutable pick history, here are the net-of-cost metrics, and here is the multiple-testing correction."** That is the practical definition of statistically valid for this kind of system.

---

## Related Files in This WIRED_IN Folder

- `MASTER_PROMPT.md` — merged self-engineering + proof standard prompt
- `NEGATIVE_RESULT_DIAGNOSIS_TEMPLATE.md` — failure classification matrix
- `README.md` — consolidated reference with full prompts and Q&A
- `ETF_MF_AUDIT.md` — completed ETF/MF subagent audit
- `CRYPTO_AUDIT.md` — completed CRYPTO subagent audit
- `PENNY_STOCK_AUDIT.md` — completed penny stock subagent audit

---

*Generated by hilarious-seer worktree, 2026-11-15*
