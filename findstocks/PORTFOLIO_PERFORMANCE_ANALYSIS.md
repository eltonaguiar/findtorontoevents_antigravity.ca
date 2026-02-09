# Stock Portfolio System — Performance Analysis (Live API)

**Source:** Live API calls to `https://findtorontoevents.ca/findstocks/api/`  
**Date:** 2025-02-09

---

## 1. All Algorithms — Buy & Hold Style (TP=999, SL=999, max_hold=999)

*Single backtest with no algorithm filter; effective picks = Blue Chip Growth only (other algos have no picks imported).*

| Metric | Value |
|--------|--------|
| **Algorithm** | All (Blue Chip Growth only in DB) |
| **Total trades** | 350 |
| **Winning trades** | 212 |
| **Losing trades** | 138 |
| **Win rate** | 60.57% |
| **Total return %** | 1648.23% |
| **Sharpe ratio** | 0.3715 |
| **Sortino ratio** | 0.6954 |
| **Max drawdown %** | 9.3338 |
| **Profit factor** | 2.9043 |
| **Expectancy** | 8.8083 |
| **Avg win %** | 20.33 |
| **Avg loss %** | 8.90 |
| **Initial capital** | $10,000 |
| **Final value** | $174,823.47 |
| **Total commissions** | $30,241.28 |
| **CDR trades** | 252 |
| **US forex trades** | 98 |

### Top 3 best individual trades (from sample)

| Rank | Ticker | Company | Return % | Entry | Exit |
|------|--------|---------|----------|-------|------|
| 1 | CAT | Caterpillar Inc | 114.26 | 2025-04-01 | 2026-02-06 |
| 2 | GOOG | Alphabet Inc | 105.98 | 2025-04-01 | 2026-02-06 |
| 3 | CAT | Caterpillar Inc | 101.45 | 2025-03-03 | 2026-02-06 |

### Bottom 3 worst individual trades (from sample)

| Rank | Ticker | Company | Return % | Entry | Exit |
|------|--------|---------|----------|-------|------|
| 1 | UNH | UnitedHealth Group | -48.24 | 2025-02-07 | 2026-02-06 |
| 2 | UNH | UnitedHealth Group | -42.26 | 2025-03-03 | 2026-02-06 |
| 3 | AMT | American Tower Corp | -26.05 | 2025-04-01 | 2026-02-06 |

---

## 2. Individual Algorithm Backtests (TP=10%, SL=5%, max_hold=30d, fee_model=questrade)

### 2.1 CAN SLIM

**Status:** No data — picks not imported.

```json
{"ok":false,"error":"No picks found for the selected algorithms. Import picks first.","params":{"algorithms":"CAN SLIM","strategy":"custom","take_profit":10,"stop_loss":5,"max_hold_days":30}}
```

**Action:** Run import for CAN SLIM picks before backtesting.

---

### 2.2 Technical Momentum

| Metric | Value |
|--------|--------|
| **Algorithm** | Technical Momentum |
| **Total trades** | 12 |
| **Winning trades** | 3 |
| **Losing trades** | 9 |
| **Win rate** | 25% |
| **Total return %** | -2.84 |
| **Sharpe ratio** | -0.3911 |
| **Sortino ratio** | -0.405 |
| **Max drawdown %** | 3.488 |
| **Profit factor** | 0.3865 |
| **Expectancy** | -2.2868 |
| **Avg win %** | 7.74 |
| **Avg loss %** | 5.63 |
| **Initial capital** | $10,000 |
| **Final value** | $9,715.94 |
| **Gross wins** | $178.95 |
| **Gross losses** | $463.03 |

#### Top 3 best trades (Technical Momentum)

| Rank | Ticker | Company | Return % | Entry | Exit | Exit reason |
|------|--------|---------|----------|-------|------|-------------|
| 1 | META | Meta Platforms, Inc. | 9.45 | 2026-01-28 | 2026-01-29 | take_profit |
| 2 | XOM | Exxon Mobil Corp | 7.85 | 2026-01-28 | 2026-02-06 | end_of_data |
| 3 | CVX | Chevron Corporation | 5.92 | 2026-01-28 | 2026-02-06 | end_of_data |

#### Bottom 3 worst trades (Technical Momentum)

| Rank | Ticker | Company | Return % | Entry | Exit | Exit reason |
|------|--------|---------|----------|-------|------|-------------|
| 1 | GM | General Motors Company | -6.90 | 2026-01-28 | 2026-02-06 | end_of_data |
| 2 | F | Ford Motor Company | -5.44 | 2026-01-28 | 2026-02-06 | end_of_data |
| 3 | ABBV | AbbVie Inc | -5.48 | 2026-01-28 | 2026-02-04 | stop_loss |

---

### 2.3 ML Ensemble

**Status:** No data — picks not imported.

```json
{"ok":false,"error":"No picks found for the selected algorithms. Import picks first.","params":{"algorithms":"ML Ensemble","strategy":"custom","take_profit":10,"stop_loss":5,"max_hold_days":30}}
```

**Action:** Run import for ML Ensemble picks before backtesting.

---

### 2.4 Blue Chip Growth (TP=10%, SL=5%, max_hold=30d)

| Metric | Value |
|--------|--------|
| **Algorithm** | Blue Chip Growth |
| **Total trades** | 312 |
| **Winning trades** | 114 |
| **Losing trades** | 198 |
| **Win rate** | 36.54% |
| **Total return %** | -29.89 |
| **Sharpe ratio** | -0.2221 |
| **Sortino ratio** | -0.2259 |
| **Max drawdown %** | 35.22 |
| **Profit factor** | 0.6043 |
| **Expectancy** | -1.4074 |
| **Avg win %** | 6.21 |
| **Avg loss %** | 5.79 |
| **Initial capital** | $10,000 |
| **Final value** | $7,011.45 |
| **Gross wins** | $4,563.80 |
| **Gross losses** | $7,552.32 |
| **CDR trades** | 221 |
| **US forex trades** | 91 |

#### Top 3 best trades (Blue Chip Growth, 10/5/30 — from sample)

| Rank | Ticker | Return % | Entry | Exit | Exit reason |
|------|--------|----------|-------|------|-------------|
| 1 | AMT | 5.78 | 2025-02-07 | 2025-03-03 | take_profit |
| 2 | BRK-B | 5.78 | 2025-02-07 | 2025-03-18 | take_profit |
| 3 | JNJ | 9.45 | 2025-02-07 | 2025-03-04 | take_profit |

*(Many trades hit take_profit at 9.45%; above are representative.)*

#### Bottom 3 worst trades (Blue Chip Growth, 10/5/30 — from sample)

| Rank | Ticker | Return % | Entry | Exit | Exit reason |
|------|--------|----------|-------|------|-------------|
| 1 | CAT | -8.88 | 2025-02-07 | 2025-02-12 | stop_loss |
| 2 | UNP | -8.88 | 2025-02-07 | 2025-03-21 | stop_loss |
| 3 | PEP | -8.89 | 2025-03-03 | 2025-04-07 | stop_loss |

---

## 3. Optimal Finder (top 10 by total_return_pct)

**Request:**  
`GET https://findtorontoevents.ca/findstocks/api/optimal_finder.php?quick=1&top=10&sort_by=total_return_pct`

**Result:** Request **timed out** when fetching from the live site. The endpoint runs a grid search (quick=1 still runs many backtest combinations: TP × SL × hold × vol × fee_model), which can exceed typical HTTP timeouts.

**Recommendation:**  
- Run optimal_finder locally (e.g. `php findstocks/api/optimal_finder.php` with same query string) or from a script with a long timeout.  
- Or call with a single algorithm to reduce work:  
  `optimal_finder.php?quick=1&top=10&sort_by=total_return_pct&algorithms=Blue%20Chip%20Growth`

**Grid in quick=1:**  
- TP: 5, 10, 20, 50, 999  
- SL: 3, 5, 10, 999  
- Hold: 1, 7, 30, 90 days  
- Vol: off, skip_high  
- Fee: questrade, flat_10  

---

## 4. Summary Table (Comparable Metrics)

| Algorithm | Trades | Wins | Losses | Win rate | Total return % | Sharpe | Max DD % | Profit factor | Expectancy |
|-----------|--------|------|--------|----------|----------------|--------|----------|---------------|------------|
| All (buy & hold) | 350 | 212 | 138 | 60.57% | 1648.23 | 0.37 | 9.33 | 2.90 | 8.81 |
| Technical Momentum (10/5/30) | 12 | 3 | 9 | 25% | -2.84 | -0.39 | 3.49 | 0.39 | -2.29 |
| Blue Chip Growth (10/5/30) | 312 | 114 | 198 | 36.54% | -29.89 | -0.22 | 35.22 | 0.60 | -1.41 |
| CAN SLIM (10/5/30) | — | — | — | — | — | — | — | — | — |
| ML Ensemble (10/5/30) | — | — | — | — | — | — | — | — | — |

---

## 5. Insights for Algorithm Design

1. **Buy & hold (no TP/SL) on current Blue Chip picks is highly profitable** (1648% return, 60% win rate, Sharpe 0.37) but with large total commissions ($30k) and long holds; many exits are "end_of_data".
2. **Tight rules (TP=10%, SL=5%, max_hold=30) hurt Blue Chip Growth:** 36% win rate, -30% return, 35% max drawdown. Winners are cut at 10% while losers hit -5% or hold to max_hold — negative expectancy.
3. **Technical Momentum** has very few trades (12) and negative return with 25% win rate; sample is too small and recent (Jan–Feb 2026).
4. **CAN SLIM and ML Ensemble** have no picks in the DB; import picks to compare.
5. **Worst single-name risk:** UNH and AMT show large drawdowns in buy & hold; consider sector/position limits or volatility filter.
6. **Optimal finder** is useful for discovering better TP/SL/hold/vol combinations but must be run in an environment that allows long runtimes (e.g. local PHP or async job).

---

## 6. Raw API Response Summaries (for scripting)

### All algorithms (TP=999, SL=999, max_hold=999)

```json
{
  "summary": {
    "initial_capital": 10000,
    "final_value": 174823.47,
    "total_return_pct": 1648.2347,
    "total_trades": 350,
    "winning_trades": 212,
    "losing_trades": 138,
    "win_rate": 60.57,
    "avg_win_pct": 20.3339,
    "avg_loss_pct": 8.8977,
    "max_drawdown_pct": 9.3338,
    "sharpe_ratio": 0.3715,
    "sortino_ratio": 0.6954,
    "profit_factor": 2.9043,
    "expectancy": 8.8083
  }
}
```

### Technical Momentum (10/5/30)

```json
{
  "summary": {
    "total_trades": 12,
    "winning_trades": 3,
    "losing_trades": 9,
    "win_rate": 25,
    "total_return_pct": -2.8406,
    "sharpe_ratio": -0.3911,
    "max_drawdown_pct": 3.488,
    "profit_factor": 0.3865,
    "expectancy": -2.2868
  }
}
```

### Blue Chip Growth (10/5/30)

```json
{
  "summary": {
    "total_trades": 312,
    "winning_trades": 114,
    "losing_trades": 198,
    "win_rate": 36.54,
    "total_return_pct": -29.8855,
    "sharpe_ratio": -0.2221,
    "max_drawdown_pct": 35.2204,
    "profit_factor": 0.6043,
    "expectancy": -1.4074
  }
}
```

---

*End of report. Optimal finder full results not available due to timeout; run locally or with single-algorithm + long timeout to retrieve top 10 configs.*
