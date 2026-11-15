# Backtesting Methodology & Results

**Worktree:** scratch-hippodraco  
**Date-time:** 2026-11-15T0130Z  
**Script:** `tools/backtest_cost_adjusted_wf.py`  
**Outputs:** `audit_dashboard/data/cost_adjusted_walkforward_backtest.json` + `.md`

---

## 1. Methodology

### 1.1 What Was Tested

A grid of 27 parameter combos on a monthly rebalanced, long-only momentum universe:

| Dimension | Values Tested | Combos |
|-----------|--------------|--------|
| Lookback (months) | 6, 9, 12 | 3 |
| Skip (months, anti-lookahead) | 0, 1, 2 | 3 |
| n_long (positions held) | 3, 5, 8 | 3 |
| **Total combos** | | **27** |

### 1.2 Data Source

- 30 large-cap US equities (liquid, cheap to trade)
- yfinance free tier, monthly OHLCV, auto-adjusted
- Window: 2015-01-01 → 2026-11-15 (142 monthly periods)

### 1.3 Cost Model

| Component | Value |
|-----------|-------|
| Commission | ~2.5 bps (IB-style $0.005/share on ~$200 avg share price) |
| Spread | ~5 bps (estimated half-spread) |
| Slippage | ~10 bps (conservative equity slippage) |
| **Total round-trip** | **20 bps** (hardcoded in backtest script) |

**Note:** `tools/data/transaction_costs.json` lists EQUITY at **10 bps** round-trip. The backtest script deliberately uses a conservative **20 bps** hardcoded value. Production validation should use realized costs from actual fills.

**Sensitivity:** At 50 bps round-trip (pessimistic), the edge may disappear. Realized costs must be monitored.

### 1.4 Benchmark

SPY buy-and-hold total return (dividends reinvested), same window.

### 1.5 Multiple-Testing Honesty

- **nb_trials = 27** (all combos tested), NOT nb_trials=1
- **Bonferroni correction:** Expected ~1.4 false T2 passes at α=0.05 by chance across 27 combos
- Best variant treated as **hypothesis until forward-tested**

### 1.6 T2 Gate (must clear ALL)

| Metric | Threshold | Enforced by backtest script? |
|--------|-----------|------------------------------|
| Profit Factor (post-cost) | ≥ 1.5 | Yes |
| Win Rate (EXPIRED-inclusive) | ≥ 50% | Yes |
| Max Drawdown | ≤ 20% | Yes |
| n resolved | ≥ 100 | Yes |
| Sharpe (annualized) | ≥ 1.0 | **No** — spec-added gate only |

**Note:** Sharpe ≥ 1.0 is a spec-added gate; it is NOT enforced by the backtest script's `classify()` function (which checks PF/WR/MDD/n only).

---

## 2. Results

### 2.1 Top 8 Variants (ranked by profit factor)

| lookback | skip | n_long | PF | WR% | Sharpe | MDD% | Total% | n | Tier |
|----------|------|--------|----|-----|--------|------|--------|----|------|
| 6 | 2 | 3 | 2.94 | 61.65 | 1.30 | 29.49 | 3699 | 133 | BELOW_T3 |
| 12 | 2 | 3 | 2.71 | 64.57 | 1.21 | 31.16 | 2695 | 127 | BELOW_T3 |
| 6 | 0 | 3 | 2.69 | 65.93 | 1.25 | 35.87 | 3461 | 135 | BELOW_T3 |
| 6 | 0 | 5 | 2.66 | 64.44 | 1.28 | 25.57 | 1986 | 135 | BELOW_T3 |
| 6 | 1 | 3 | 2.65 | 62.69 | 1.25 | 27.61 | 3269 | 134 | BELOW_T3 |
| **12 | 0 | 8** | **2.62** | **62.79** | **1.27** | **17.37** | **1021** | **129** | **TIER_2** |
| 12 | 1 | 3 | 2.61 | 60.94 | 1.16 | 31.89 | 2247 | 128 | BELOW_T3 |
| 9 | 2 | 3 | 2.57 | 60.77 | 1.16 | 30.06 | 2274 | 130 | BELOW_T3 |

### 2.2 Benchmark: SPY Buy-and-Hold

| Metric | SPY |
|--------|-----|
| Total return | 359.03% |
| Max drawdown | 23.93% |
| Sharpe (annualized) | 0.95 |
| Periods | 142 |

### 2.3 What Passed T2

**Exactly one variant cleared all T2 thresholds:**
- **lookback=12, skip=0, n_long=8**: PF 2.62, WR 62.79%, MDD 17.37%, n=129, Sharpe 1.27
- Beats SPY on total return (1021% vs 359%), Sharpe (1.27 vs 0.95), MDD (17.37% vs 23.93%)

### 2.4 What Failed

- **Best-by-PF variant** (lookback=6, skip=2, n_long=3, PF 2.94) FAILED on MDD (29.49% > 20% cap) → BELOW_T3
- 5 of top 8 by PF failed MDD
- High PF consistently came with high drawdown **except** the slower/diversified variant (lookback=12, n_long=8)
- 4 of 27 combos raw-passed T2; expected ~1.4 false passes at α=0.05 → cannot claim statistical significance yet

---

## 3. Honest Interpretation

### 3.1 This Backtest Does NOT Prove Profitability

It shows:
1. A cost-adjusted momentum strategy CAN clear T2 thresholds on historical data (one variant)
2. After Bonferroni correction, we cannot distinguish skill from luck (4 raw passes vs 1.4 expected false)
3. MDD is the binding constraint, not PF or WR

### 3.2 Path Forward

Forward-test the T2-clearing variant (lookback=12, skip=0, n_long=8) on unseen data:
- ≥6 months forward, ≥100 trades
- Must clear T2 again: PF ≥ 1.5, WR ≥ 50%, MDD ≤ 20%, beats SPY
- If it fails any gate → eliminate, not "give more time"

---

## 4. Reproduction Commands

```bash
# Run full grid (27 combos, Bonferroni-aware)
python3 tools/backtest_cost_adjusted_wf.py \
  --start 2015-01-01 --end 2026-11-15 \
  --cost-bps 20 \
  --out audit_dashboard/data/cost_adjusted_walkforward_backtest.json \
  --summary-md audit_dashboard/data/cost_adjusted_walkforward_backtest.md

# Sensitivity: optimistic (10 bps) and pessimistic (50 bps) costs
python3 tools/backtest_cost_adjusted_wf.py --cost-bps 10
python3 tools/backtest_cost_adjusted_wf.py --cost-bps 50
```

### 4.1 Output Files

| File | Purpose |
|------|---------|
| `tools/backtest_cost_adjusted_wf.py` | Backtest simulation script |
| `audit_dashboard/data/cost_adjusted_walkforward_backtest.json` | Full JSON results (all 27 variants) |
| `audit_dashboard/data/cost_adjusted_walkforward_backtest.md` | Human-readable summary |

---
