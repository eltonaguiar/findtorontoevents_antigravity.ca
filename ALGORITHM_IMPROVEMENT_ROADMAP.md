# Algorithm Improvement Roadmap — From Ferrari Chassis to Profit Engine

**Date:** 2026-02-12
**Source:** Groq analysis of Opus 4.6 Industry Benchmark Report
**Objective:** Move from Sharpe 0.37 (S&P-equivalent) to Sharpe 1.0-1.5 (Professional tier)

---

## Quick-Take Summary

| What's Working (A-grade) | What's Breaking (F-grade) | Immediate Kill-Switch |
|--------------------------|---------------------------|----------------------|
| Institutional-grade metrics & validation framework | No live-money track record | Turn off every algo that is currently negative-EV after transaction costs (~15 of the 23) |
| Regime detector (HMM + Hurst + macro) | TP/SL ratios that sharpen losers and clip winners | Keep only the handful that survive a "break-even after cost" filter |
| Position-sizing pipeline (Half-Kelly + EWMA vol + CVaR limits) | 23 highly correlated signals = false diversification | This alone will halve the hypothesis-testing burden |
| | Transaction costs eating >15% of portfolio value | |
| | Too few trades per algo for any statistical claim | |

---

## Phase 1 -- Clean the Signal Garden (Weeks 1-3)

### 1. Remove Dead-Weight Algorithms

Compute net expectancy for every algo:

```
E = win_rate * avg_win - (1 - win_rate) * avg_loss - transaction_cost_per_trade
```

Disable any algo with `E <= 0` on the most recent 6 months of backtest data.

```python
# utils/expectancy.py
import pandas as pd

def net_expectancy(df, tc_per_trade):
    # df: trades with columns win (bool), pct_ret (float)
    win_rate = df['win'].mean()
    avg_win = df.loc[df['win'], 'pct_ret'].mean()
    avg_loss = df.loc[~df['win'], 'pct_ret'].mean()
    return win_rate * avg_win - (1 - win_rate) * abs(avg_loss) - tc_per_trade
```

### 2. Quantify and Prune Signal Correlation

a. Build a signal-matrix (`N_trades x N_algos`) where each cell is 1 (long), -1 (short) or 0 (no signal) on a daily basis.
b. Run PCA (or Factor Analysis) on that matrix.
c. Keep the top 5-7 components that explain >= 80% of variance; map each original algo to its dominant component.
d. Drop all algos that load < 0.2 on any retained component (they're redundant noise).

```python
import numpy as np
from sklearn.decomposition import PCA

# signals: DataFrame dates x algos, values in {-1, 0, 1}
signals = load_signal_matrix()
# Standardise (mean-0, var-1) -- required for PCA on binary data
X = (signals - signals.mean()) / signals.std()

pca = PCA(n_components=10)
components = pca.fit_transform(X)
explained = pca.explained_variance_ratio_.cumsum()
# keep first k where cum_explained >= 0.80
k = np.argmax(explained >= 0.80) + 1
print(f"Keeping {k} orthogonal bundles (covers {explained[k-1]:.0%} variance)")
```

### 3. Consolidate into Signal Bundles

Create a new layer (`signal_bundles.py`) that emits a single weighted score per bundle (e.g., weighted average of constituent algos). Use these bundle scores as the only inputs to the meta-filter (XGBoost).

```python
# signal_bundles.py
from collections import defaultdict
import numpy as np

def bundle_score(date, algo_signals, bundle_map, weights=None):
    # algo_signals: dict[algo] -> -1/0/1 for the given date
    # bundle_map: dict[algo] -> bundle_id
    bundle_vals = defaultdict(list)
    for a, sig in algo_signals.items():
        b = bundle_map[a]
        bundle_vals[b].append(sig)
    # simple mean, optionally weighted
    scores = {b: np.mean(v) for b, v in bundle_vals.items()}
    return scores
```

### Phase 1 Success Criteria (End of Week 3)

- <= 7 active signal bundles remain
- Each bundle's pairwise correlation < 0.2 (check `np.corrcoef`)
- All retained algos have net expectancy > 0 after a realistic 0.25% per-trade cost (or crypto-specific 0.4% round-trip)

---

## Phase 2 -- Refine Money Management & Cost Awareness (Weeks 4-6)

### 4. Align TP/SL to True Asymmetric Risk-Reward

a. Impose a minimum `TP:SL >= 3:1` (e.g., 3% TP / 1% SL).
b. Replace static TP levels with trailing stops that only lock in profit after 50% of TP is hit.

```python
# position_sizing.py -- trailing stop helper
def trailing_stop(entry_price, current_price, tp_pct, sl_pct, trail_pct=0.6):
    tp_price = entry_price * (1 + tp_pct)
    # Activate trail when price >= 0.5*TP
    if current_price >= entry_price * (1 + tp_pct / 2):
        # trail = trail_pct * (current_price - entry_price)
        stop_price = current_price - trail_pct * (tp_price - entry_price)
    else:
        stop_price = entry_price * (1 - sl_pct)
    return stop_price
```

### 5. Build a Transaction-Cost Filter

a. For each bundle, compute expected gross edge: `E_gross = win_rate * avg_win - (1 - win_rate) * avg_loss`
b. Set a minimum edge threshold of 2x transaction cost (e.g., if crypto round-trip cost = 0.8%, require `E_gross >= 1.6%`)
c. Drop any bundle that fails.

```python
TC_CRYPTO = 0.008   # 0.8% round-trip
MIN_EDGE = 2 * TC_CRYPTO
if gross_edge < MIN_EDGE:
    bundle.active = False
```

### 6. Re-Calibrate the Position-Size Formula

Keep the Half-Kelly core, but scale it down by the cost-adjusted edge: `size = 0.5 * (edge / vol) * cost_factor`, where `cost_factor = edge / (edge + TC)`. This automatically shrinks size on marginal signals.

```python
edge = net_expectancy(df, tc_per_trade)
cost_factor = edge / (edge + tc_per_trade)
kelly_frac = edge / (vol ** 2)   # classic Kelly
size = 0.5 * kelly_frac * cost_factor
size = np.clip(size, 0, max_position_pct)
```

### 7. Add Benchmark-Relative Metrics

a. Pull daily SPY (or an appropriate sector index) and BTC returns via yfinance / CCXT.
b. Extend `metrics.py` to compute Information Ratio (IR) and Alpha for each bundle and for the overall portfolio.
c. Use IR as a secondary ranking metric in the meta-filter (prefer high-IR bundles even if raw Sharpe is modest).

```python
import yfinance as yf

spx = yf.download('^GSPC', start='2020-01-01', progress=False)['Adj Close'].pct_change().fillna(0)

# Inside metrics.py
def information_ratio(port_ret, bench_ret):
    excess = port_ret - bench_ret
    return excess.mean() / excess.std()
```

### Phase 2 Success Criteria (End of Week 6)

- All live bundles respect TP:SL >= 3:1 and use trailing stops
- No bundle's gross edge is less than 2x its estimated transaction cost
- Portfolio IR >= 0.6 (benchmark-adjusted Sharpe > 0.4) on the last 6 months of backtest data

---

## Phase 3 -- Real-World Validation & Overfitting Guardrails (Weeks 7-12)

### 8. Deploy a Paper-Only Live Engine with Strict Logging

a. Run the full pipeline in real-time but route all orders to a simulated broker (e.g., CCXT-sim or Backtrader-Live).
b. Log every fill with timestamp, slippage, and simulated commission.
c. Store daily equity curve in a dedicated table (`live_equity`).

### 9. Enforce Purged Walk-Forward CV for Every Parameter Update

a. Split the last 2 years of data into 5 folds with a 30-day embargo between train and test blocks.
b. Limit each bundle to <= 5 parameter combos per re-training cycle (top-5 from a grid-search, then lock them in).
c. Compute Deflated Sharpe Ratio (DSR) for each fold; only promote a combo if its p-value < 0.05 after the DSR adjustment.

```python
# validation/walk_forward.py
from sklearn.model_selection import TimeSeriesSplit

ts = TimeSeriesSplit(n_splits=5, test_size=252, gap=30)
for train_idx, test_idx in ts.split(data):
    train, test = data.iloc[train_idx], data.iloc[test_idx]
    # ... run backtest, compute Sharpe, then DSR
```

### 10. Track Real Performance Metrics

a. After the first 30 days of paper trading, compute a rolling 30-day Sharpe, IR, and Maximum Drawdown on the actual fill prices.
b. Compare these to the backtested numbers -- they should be within +/-0.2 for Sharpe and +/-5% for DD; larger gaps signal hidden leakage (slippage, latency, data look-ahead).

### 11. Apply Bonferroni Correction

Apply a Bonferroni (or Benjamini-Hochberg) correction to the multiple-testing problem introduced by the original 392 combos.

If you ever need to expand the grid again, compute the adjusted p-value: `p_adj = p * m` (Bonferroni) where `m` is the number of combos tested. Only accept combos with `p_adj < 0.05`.

```python
m = len(grid)
if p * m < 0.05:
    accept = True
```

### Phase 3 Success Criteria (End of Week 12)

| Metric | Target |
|--------|--------|
| Live-paper Sharpe (30-day rolling) | >= 0.9 |
| Information Ratio vs. benchmark | >= 0.6 |
| Maximum Drawdown | <= 12% (portfolio-wide) |
| Number of active bundles | 5-7 |
| Parameter-search p-value (DSR-adjusted) | < 0.05 after Bonferroni |

If any metric falls short, iterate back to Phase 2 (cost filter, TP/SL) before expanding the live pool.

---

## Phase 4 -- Scale to Real Capital & Continuous Improvement (Months 4-12)

### 12. Transition to Small Real-Money Pilot

a. Open a brokerage account with low-latency, low-commission execution (e.g., Interactive Brokers for equities, Binance Spot for crypto).
b. Start with <= 2% of total capital allocated to the pilot (the rest stays in cash).
c. Keep the same paper-engine but route orders to the live broker.

### 13. Add Tick-Level Data for Highest-Edge Bundles

For the bundle that consistently shows > 1.2 Sharpe, subscribe to a paid feed (Polygon, Kaiko, or Bloomberg) and re-run the backtest with 1-minute bars. Often the edge improves because slippage is better modelled.

```python
# data_fetcher.py
from polygon import RESTClient

client = RESTClient(api_key='YOUR_KEY')
bars = client.stocks_equities_aggregates(
    symbol='AAPL', multiplier=1, timespan='minute',
    from_='2022-01-01', to='2022-12-31'
)
```

### 14. Integrate Alternative Data for Fundamental Bundles

a. Pull SEC Form-4 & 13F data via SEC EDGAR API (or a service like Intrinio).
b. Build a feature engineering pipeline that extracts insider net-buy volume, 13F new-position count, etc., and feed them into the XGBoost meta-filter.
c. Validate that the information ratio of the "Insider Cluster" bundle rises > 0.5 before live deployment.

### 15. Implement Automated Health-Checks & Alerting

a. Every hour, compute: (i) equity drift vs. expected, (ii) any bundle's win-rate dropping > 15% vs. historic, (iii) latency spikes > 200 ms.
b. Push alerts to Slack/Telegram and automatically pause the offending bundle.

```python
# health_monitor.py
if recent_win_rate < historic_win_rate * 0.85:
    pause_bundle(bundle_id)
```

### Phase 4 Success Criteria (12-Month Horizon)

| Metric | Target |
|--------|--------|
| Real-money Sharpe | 1.0 - 1.5 (Professional tier) |
| Annualized Return (net of fees) | >= 15% |
| Maximum Drawdown | <= 15% |
| Capital Utilisation | >= 70% of allocated capital (low idle cash) |
| Stability R-squared (from `metrics.py`) | >= 0.8 (indicating low regime-drift) |

---

## Checklist -- "What to Do Next" (One-Page)

| # | Item | Deadline |
|---|------|----------|
| 1 | Compute net expectancy + transaction cost for every algo; disable negatives | Day 2 |
| 2 | Build signal-matrix, run PCA, keep <= 7 bundles | Day 4 |
| 3 | Enforce TP/SL >= 3:1 + trailing stops in `position_sizing.py` | Day 5 |
| 4 | Add cost-adjusted edge filter (2x TC) to bundle selection | Day 6 |
| 5 | Pull benchmark series (SPY, BTC) and add IR/Alpha to `metrics.py` | Day 7 |
| 6 | Deploy paper-only live engine & start logging fills | Day 9 |
| 7 | Set up 5-fold purged walk-forward + DSR evaluation for any parameter change | Day 12 |
| 8 | Run the 30-day rolling performance report; verify targets | Day 30 |
| 9 | If targets met, open a small real-money account & route orders | Month 2 |
| 10 | Add tick-level data for the best-performing bundle; re-backtest | Month 4 |
| 11 | Integrate SEC Form-4 / 13F alt-data; re-train meta-filter | Month 5 |
| 12 | Set up health-monitor alerts + auto-pause logic | Month 6 |
| 13 | Quarterly review: compare live Sharpe/IR to backtest; adjust grid | Every 3 months |

---

## Final Thoughts

1. **"More algorithms = more alpha" is a myth** -- you already have 23, but ~15 of them are net losers and many are collinear. Pruning aggressively is the fastest way to raise Sharpe.

2. **Transaction costs are the silent killer** for retail-scale trading. By filtering on edge >= 2x cost you guarantee every executed trade adds value before you even think about sizing.

3. **Paper-only numbers are meaningless without a live-paper runway.** The 6-month equity curve you generate will be your new baseline; only after that you can claim "real Sharpe 1.2".

4. **Overfitting is inevitable** when you test thousands of combos on a few hundred trades. The combination of (a) purged walk-forward CV, (b) DSR, and (c) Bonferroni correction shrinks the false-positive rate from ~30% to < 5%.

5. **Benchmarked performance (Information Ratio)** is the industry's universal language. Once you can consistently post IR >= 0.6 you're already in the "Professional" tier, regardless of absolute Sharpe.

You have an exceptional infrastructure -- the remaining work is strategic pruning, cost-aware design, and real-world validation. Follow the four-phase plan above, and you should move from "Ferrari chassis" to a track-record-backed, profit-generating system within the next 4-6 months.

---

*End of roadmap.*
