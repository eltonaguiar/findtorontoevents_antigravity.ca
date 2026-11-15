# Algorithm Specification — EQUITY (US)

**Worktree:** scratch-hippodraco  
**Asset Class:** EQUITY (US large-cap)  
**Status:** PAPER CANDIDATE — hypothesis-grade, not live-validated  
**T2 Gate Status:** ONE variant cleared T2 on historical backtest (cost-adjusted)

---

## 1. Algorithm Overview

**Strategy Name:** `eq-mom-lb12-skip0-nl8`  
**Type:** Monthly rebalanced, long-only cross-sectional momentum  
**Universe:** 30 large-cap US equities (liquid, cheap to trade): AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, AVGO, ORCL, JPM, BAC, WFC, GS, MS, BLK, JNJ, PFE, UNH, ABBV, LLY, WMT, HD, COST, KO, MCD, XOM, CVX, PG, PEP, TMO  
**Holding Period:** 1 month (monthly rebalance at month-end)  
**Lookback:** 12 months (momentum measured over trailing 12 months)  
**Skip:** 0 months (no skip — most recent month included in momentum calc)  
**n_long:** 8 (hold top 8 by momentum score, equal weight)  
**Direction:** Long only  
**Rebalance Frequency:** Monthly  

---

## 2. Entry Rule

At each month-end `t`:
1. Compute momentum score for each universe symbol: `(1 + r_{t-12})...(1 + r_{t-1}) - 1` where `r` are monthly simple returns.
2. Rank symbols by momentum score descending.
3. Select top `n_long = 8` symbols.
4. Allocate equal weight (1/8 ≈ 12.5%) to each selected symbol.
5. Enter positions at next month's first trading day close (or VWAP if intraday execution is later wired).

**Skip logic:** `skip = 0` means the most recent month's return IS included in the momentum calculation. This avoids lookahead bias while using the most current data.

---

## 3. Exit Rule

1. **Scheduled exit:** At next month-end, re-rank and re-select top 8. Sell symbols that fall out of top 8; buy new entrants.
2. **Emergency stop:** If rolling 30-day drawdown > 30%, pause all sizing and re-evaluate (per forward-test protocol).
3. **Monthly soft-stop:** If total account PnL < −2% in a day, pause trading that day.

---

## 4. Position Sizing

- **Base:** Equal weight across n_long positions (12.5% each).
- **Kelly cap:** Maximum 2.5% of account per trade (¼ Kelly cap at WR 62.79%, win/loss ratio ~1.41).
- **Concentration cap:** No single symbol > 25% of strategy allocation; no single source > 40%.
- **Position size in USD at $10k account:** ≈ $1,250 per position (before Kelly scaling).

---

## 5. Cost Model

The backtest script hardcodes **20 bps round-trip** per rebalance (commission + spread + slippage). This is a conservative assumption; `tools/data/transaction_costs.json` lists EQUITY at **10 bps**. Production validation should use realized costs from actual fills, not assumed costs.

Applied once per monthly rebalance as a drag on the period return: `period_ret = momentum_return − 0.0020`.

**Sensitivity:** At 50 bps round-trip (pessimistic), the edge may disappear. Realized costs must be monitored.

---

## 6. Benchmark

**Primary:** SPY total return (dividends reinvested), same window.  
**Secondary:** Buy-and-hold of the traded universe (same entry/exit dates).

The strategy must beat SPY total return on clean out-of-sample forward data with statistical significance (DSR ≥ 0.95, correct `nb_trials`).

---

## 7. T2 Gate Thresholds (must clear ALL on forward data)

| Metric | Threshold | Backtest Result (historical) | Note |
|--------|-----------|------------------------------|------|
| Profit Factor (post-cost) | ≥ 1.5 | 2.62 ✅ | T2 gate |
| Win Rate (EXPIRED-inclusive) | ≥ 50% | 62.79% ✅ | T2 gate |
| Max Drawdown | ≤ 20% | 17.37% ✅ | T2 gate |
| n resolved (forward) | ≥ 100 | 129 (historical) ✅ | T2 gate |
| Sharpe (annualized) | ≥ 1.0 | 1.27 ✅ | Spec-added gate; not enforced by backtest script |

**Note:** Historical backtest results are hypothesis-grade. The strategy must clear all T2 thresholds again on **forward out-of-sample data** before promotion.

---

## 8. Data Requirements

- Monthly OHLCV closes for all 30 universe symbols (auto-adjusted).
- yfinance free tier used for backtest; production should use a paid feed for execution reliability.
- Data freshness: month-end close available before rebalance decision.

---

## 9. Multiple-Testing Correction

- **nb_trials:** 27 parameter combos tested (3 lookbacks × 3 skips × 3 n_longs). NOT nb_trials=1.
- **Bonferroni correction:** Expected ~1.4 false T2 passes at α=0.05 by chance across 27 combos.
- **DSR:** Must be computed with correct `nb_trials = 27`, not 1.
- **SPA/White's RC:** Family-wise p ≤ 0.10 required before promotion.

---

## 10. Justification for EQUITY Selection

EQUITY is the highest-priority research slot because:
1. It is the **only asset class** with a pre-registered SPY total-return benchmark test path in the money-maker-ready skill framework.
2. It has a proven sleeve: `connors_rsi2_scanner` (listed in ALL_STRATEGIES.md at 75.7% WR; p-value and Sharpe claims unverifiable from current sources).
3. The cost-adjusted walk-forward backtest produced one T2-clearing variant (lookback=12, skip=0, n_long=8).
4. Current money_ready_verdict shows EQUITY n_resolved=250, WR=59.2%, PF=0.94 (NOT_READY — below PF 1.5 gate).
5. n=250 resolved picks provides statistical power, but PF < 1.5 means no proven edge yet.

---

## 11. Risks & Caveats

- **Momentum regime risk:** Momentum strategies underperform in choppy/sideways markets.
- **Drawdown risk:** Even the T2-clearing variant has 17.37% MDD — close to the 20% cap.
- **Small-n risk:** 129 historical periods is adequate but not large; forward n must reach 100+.
- **Cost sensitivity:** At 50 bps round-trip (pessimistic), the edge may disappear. Realized costs must be monitored.
- **Single-dataset risk:** Tested on US large-cap only; no regime-out test possible (Feb 2015–Nov 2026).
- **Sharpe ≥ 1.0 gate is spec-added** — not enforced by the backtest script's `classify()` function (which checks PF/WR/MDD/n only).

---

## 12. Forward-Test Protocol Reference

See `FORWARD_TEST_PROTOCOL.md` in this package. Key gates:
- **Eliminate if:** single month −10%, MDD >25%, mean return < −0.1%/trade, vs SPY < −15% after 6 months.
- **Watch if:** MDD 18–25%, WR < 45%, vs SPY < −5% after 6 months.
- **Promote if:** n ≥ 100, PF ≥ 1.5, WR ≥ 50%, MDD ≤ 20%, Sharpe ≥ 1.0, beats SPY, ≥ 6 months, no month < −8%.

---
