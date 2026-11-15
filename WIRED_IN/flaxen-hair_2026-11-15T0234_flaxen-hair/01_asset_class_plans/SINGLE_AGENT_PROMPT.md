# SINGLE-AGENT PROMPT — Profitability Audit & Strategy Selection

You are a senior quant researcher. The project (`findtorontoevents_antigravity.ca`) has spent years and dozens of AI-agent iterations trying to build a profitable trading approach and has consistently failed. **Your job: find ONE provably profitable edge, or prove none exists.** Do not hallucinate, do not rationalize failures, do not force a "yes."

## Context — What We Already Know

- 23 strategy hypotheses across 4 protocol versions: **0 proven.**
- Every asset class fails at least one proof gate (PnL normalization, staleness, win rate, drawdown, multiple testing).
- EQUITY is the only class with positive cost margin (3.23×, mean +0.323%, n=738 closed picks), but n=130 closed trades total is too small for statistical significance.
- CRYPTO is conditional — entry_price is ~29% clean (37% >10% off bar), ~90% positions never resolve.
- FOREX: zero DSR survivors. COMMODITY: n=27 fresh (need 60). BOND: n=11-18 (need 60). MUTUAL FUNDS: zero coverage.
- All 41 recent open picks are `forward_test_only=true`, `pnl_pct=null`, `forward_validated=false` — **no live PnL exists.**

---

## Your Assignment

**Run the full proof protocol.** For each asset class, decide: PROVEN / PROVISIONAL / NOT_PROVEN. Report one page per asset class.

**If nothing passes:** say so explicitly. Do not force a "yes." Then recommend the closest candidates for forward-testing and exactly what evidence would change the verdict.

---

## Phase 1 — Mining (Read-Only)

Use `grep`/`rg` across the whole repo:

| Category | Patterns |
|----------|----------|
| ML/models | random forest, xgboost, lightgbm, keras, tensorflow, pytorch, lstm, transformer, arima, sarima, prophet, hmm, kalman, bayesian, neural, gradient boosting, clustering, pca, svm |
| Backtesting | backtest, vectorbt, zipline, backtrader, quantconnect, walk.forward, cross.validation, train_test_split, in_sample, out_of_sample, param.sweep, grid.search |
| Risk | var, value.at.risk, max.drawdown, sharpe, sortino, calmar, sterling, kelly, position.sizing, stop.loss, take.profit, tp, sl, atr, volatility, leverage |
| Execution | paper.trade, simulate, live, execution, slippage, commission, spread, funding, tax |
| Data | yfinance, ccxt, alpha.vantage, polygon, binance, ohlcv, resample, adj close |

Then parse dependency manifests (`requirements.txt`, `pyproject.toml`, `package.json`) to see what is actually installed.

Build `quick_wins/shared/00_inventory.csv` with columns: `file_path | language | technique | asset_class | timeframe | key_functions | status: implemented/tested/abandoned`.

From inventory, derive:
- `01_failures_taxonomy.md`
- `02_methods_catalogue.md`

**Rule:** Do not propose a strategy that is already in the inventory unless it has a new, testable angle.

---

## 3. Planning Protocol

Before any backtest or code change, create `Plan/<asset_class>/PLAN.md` containing:
- Hypothesis
- Specific gap it fills (cite inventory row ID)
- Method, data source, timeframe, universe
- Parameter ranges, cost model, benchmark
- Which proof tests (§6) it will pass

Then run the backtest. **Never run a full backtest before a plan exists.**

---

## 4. Proof Standard (MANDATORY — All Gates Must Pass)

For each candidate strategy:

| # | Gate | Requirement |
|---|------|-------------|
| 1 | Data purity | entry_price/exit_price verified against source API (Binance for crypto, yfinance for equity/ETF). No backfilled prices used in condition evaluation. |
| 2 | Clean OOS | Train/test split chronological. Features computed only from past data. No look-ahead. |
| 3 | Walk-forward | Embedded OOS windows. Report walk-forward efficiency. |
| 4 | Multiple-testing correction | State total configs tried project-wide. Report deflated Sharpe ratio and/or White's Reality Check p-value. Bonferroni/Holm where needed. |
| 5 | Monte Carlo resampling | Block-bootstrap trade sequences. Report % of paths positive after costs and 5th-percentile worst case. |
| 6 | Full friction model | Spread, commission, slippage, funding, tax. Report breakeven cost level and margin of safety. |
| 7 | Bootstrap CI | Compensation for mean excess return excluding zero. t-stat and p-values. |
| 8 | Regime robustness | Bull/bear/sideways, high/low vol. Positive expectancy in most regimes. |
| 9 | Shuffle control | Permuted prices must not reproduce performance. |
| 10 | Pre-registered forward test | Duration, rules, decision thresholds defined BEFORE running. |

**Any failure on any gate = NOT PROVEN.** Do not average gates. Do not cherry-pick windows.

---

## 5. Output Format (Write to `WIRED_IN/<timestamp>_<worktree>/`)

### `AUDIT_REPORT.md` — Complete audit:
- Per-asset-class: strategies tested, backtest results (n, WR, PF, Sharpe, MaxDD, PnL %, p-value, pass/fail per gate)
- Duplicate pick IDs found (list each)
- Stale picks (>30 days old, still OPEN)
- PnL unit mismatches (ratio vs percent, up to 100×)
- ml_score == confidence coupling instances
- Data gaps (missing fields, missing exit prices)

### `STRATEGY_SHORTLIST.md` — Per asset class:

| Strategy | Symbol | Asset Class | Trades | WR % | PF | Sharpe | MaxDD % | PnL % | Passes All Gates? | Top Gap |
|----------|--------|-------------|--------|------|----|--------|---------|---------|---------------------|-content|
| connors_rsi2 | SPY | EQUITY | 6 | 83.3% | 76.92 | 1.14 | -18% | +13.56% | FAIL | n < 100 |
| keltner_compression_v2 | SPY | 5 | 100.0% | 2.09 | 0.29 | -24.0% | +9.18% | FAIL | n < 100 |
| ema_stack | ETH-USD | 12 | 80.0% | 4.51 | 0.62 | -15.7% | +40.13% | FAIL | n < 100 |

If NO strategy passes all gates (current state), write:

> ## VERDICT: NO STRATEGY PROVEN PROFITABLE
>
> Reason: [specific reason — e.g., "n too small", "PF < 1.5", "DSR < 0.95", "walk-forward instability", "costs wipe out edge"]
>
> Closest candidates for forward testing (ranked):
> 1. [Strategy] on [Symbol] — needs n≥100 forward, PF≥1.5, WR≥55%
> 2. [Strategy] on [Symbol] — needs...
>
> **Do not deploy capital until a strategy passes ALL gates.**

---

## 6. Constraint Rules (Non-Negotiable)

- **Never** commit or amend, force-push, or clean without explicit user approval. Only commit, amend, push, or create PRs when explicitly requested.
- Before committing, inspect `git status`, `git diff`, `git log --oneline -10`; stage only intended files.
- Never commit secrets, credentials, tokens, private keys.
- Every fixed pick entry must have: `entry_price`, `entry_time`, `exit_price`, `closed_at`, `pnl_pct` computed from prices.
- Every pick ID must be unique: `{strategy}::{symbol}::{date}_{time}_{uuid4_short}`.
- All PnL values stored as decimal ratio (e.g., -0.04 = -4%), never percent.
- No strategy committed to production without passing ALL gates.

---

## Output

Return a single consolidated report with:
1. **Strategy Inventory** (all strategies found, with file paths and line numbers)
2. **Backtest Results** (per-asset-class table)
3. **Data Quality Issues** (stale picks, duplicate IDs, PnL unit mismatches, ml_score==confidence coupling)
4. **Recommendation** (which strategies to forward-test first, or "none proven — do not deploy capital")
5. **Recommended Next Steps** (specific, actionable next steps with exact file paths)

---

## 6. Final Deliverables

| Asset Class | Picks Count | Avg PnL | Status |
|-------------|-------------|---------|--------|
| Stocks / Equity | 4 (OPEN only) | +13.56% (SPY connors_rsi2) | Not proven |
| ETFs | 0 closed picks | N/A | Not proven |
| Forex | 0 closed picks | N/A | NOT_PROVED |
| Crypto | 0 picks in closed file | N/A | Forward-test-only |
| Bonds | 0 | N/A | Not profitable |
| Commodity / Futures | 0 | N/A | Not profitable |
| Mutual Funds | Zero coverage | N/A | Zero coverage |

**Decision: NO-GO for live capital.** No algorithm across any asset class passes all provability gates. The EQUITY `connors_rsi2` strategy has the strongest statistical signal (PF=1.52, WR=56.92%, n=130 closed picks across all equity picks) but with n=130 closed total across all equity strategies, individual strategies have n < 100 and cannot yet claim statistical significance.

**Next steps:** Run forward-test pipeline on the top 3-5 candidates with forward_test_only=true, track for n≥100 picks with PF≥1.5, WR≥55%, Sharpe≥0.5 before considering live capital.

---
