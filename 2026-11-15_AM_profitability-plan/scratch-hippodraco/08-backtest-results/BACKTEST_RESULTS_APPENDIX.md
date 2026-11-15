# Backtest Results Appendix — Cost-Adjusted Walk-Forward Simulation
**Date:** 2026-11-15  
**Worktree:** scratch-hippodraco  
**Script:** `tools/backtest_cost_adjusted_wf.py`  
**Outputs:** `audit_dashboard/data/cost_adjusted_walkforward_backtest.json` + `.md`

---

## 1. What we tested

A grid of 27 parameter combos on a monthly-rebalanced, long-only momentum universe (30 large-cap US equities, 2015-01-01 → 2026-11-15, 142 monthly periods):

| Dimension | Values tested |
|-----------|---------------|
| Lookback (months) | 6, 9, 12 |
| Skip (months, to avoid lookahead) | 0, 1, 2 |
| n_long (number held) | 3, 5, 8 |

**Cost model:** 20 bps round-trip per rebalance (commission + spread + slippage, conservative for equity).

**Benchmark:** SPY buy-and-hold (total return, dividends reinvested) over the same window.

**Multiple-testing honesty:** Bonferroni correction acknowledged — 27 combos tested, expected ~1.4 false T2 passes at alpha=0.05 by chance. Best variant is a HYPOTHESIS until forward-tested.

---

## 2. Results (top 8 variants ranked by profit factor)

| lookback | skip | n_long | PF | WR% | Sharpe | MDD% | Total% | n | T2 tier |
|---|---|---|---|---|---|---|---|---|---|
| 6 | 2 | 3 | 2.94 | 61.65 | 1.30 | 29.49 | 3699.12 | 133 | BELOW_T3 |
| 12 | 2 | 3 | 2.71 | 64.57 | 1.21 | 31.16 | 2695.31 | 127 | BELOW_T3 |
| 6 | 0 | 3 | 2.69 | 65.93 | 1.25 | 35.87 | 3461.37 | 135 | BELOW_T3 |
| 6 | 0 | 5 | 2.66 | 64.44 | 1.28 | 25.57 | 1986.16 | 135 | BELOW_T3 |
| 6 | 1 | 3 | 2.65 | 62.69 | 1.25 | 27.61 | 3269.40 | 134 | BELOW_T3 |
| **12 | 0 | 8** | **2.62** | **62.79** | **1.27** | **17.37** | **1021.41** | **129** | **TIER_2** |
| 12 | 1 | 3 | 2.61 | 60.94 | 1.16 | 31.89 | 2247.62 | 128 | BELOW_T3 |
| 9 | 2 | 3 | 2.57 | 60.77 | 1.16 | 30.06 | 2274.61 | 130 | BELOW_T3 |

**Benchmark SPY buy-and-hold:** Total 359.03%, MDD 23.93%, Sharpe 0.95, n=142.

---

## 3. Honest interpretation

### What PASSED the T2 gate (post-cost)
Exactly **one** variant cleared all T2 thresholds:
- **lookback=12, skip=0, n_long=8**: PF 2.62, WR 62.79%, MDD 17.37%, n=129, Sharpe 1.27

This beats SPY on total return (1021% vs 359%) AND on Sharpe (1.27 vs 0.95) AND on MDD (17.37% vs 23.93%).

### What FAILED
- The **best-by-PF** variant (lookback=6, skip=2, n_long=3, PF 2.94) FAILED on MDD (29.49% > 20% cap) → BELOW_T3.
- 5 of the top 8 by PF failed MDD. High PF came with high drawdown.
- 4 of 27 combos raw-passed T2; expected ~1.4 false passes at alpha=0.05 by chance. So we cannot yet claim statistical significance — the single T2 pass may be noise.

### The core tension
High profit factor (2.6–2.9) is achievable, but it consistently comes with MDD > 20% **except** the one long-lookback/diversified variant (lookback=12, n_long=8). This is the classic momentum trade-off: faster lookbacks capture more trades with higher PF but crash harder; slower lookbacks smooth drawdown but trade less.

---

## 4. The "prove profitability" verdict

**This backtest does NOT prove profitability.** It shows:
1. A cost-adjusted momentum strategy CAN clear T2 thresholds on historical data (one variant).
2. But after Bonferroni multiple-testing correction, we cannot distinguish skill from luck (4 raw passes vs 1.4 expected false).
3. MDD is the binding constraint, not PF or WR.

**Path forward:** Forward-test the T2-clearing variant (lookback=12, skip=0, n_long=8) on unseen data with the tracking protocol below. If it clears T2 again on forward data with n≥100, it becomes a pilot candidate.

---

## 5. Reproduction commands

```bash
# Run the full grid (27 combos, Bonferroni-aware)
python3 tools/backtest_cost_adjusted_wf.py \
  --start 2015-01-01 --end 2026-11-15 \
  --cost-bps 20 \
  --out audit_dashboard/data/cost_adjusted_walkforward_backtest.json \
  --summary-md audit_dashboard/data/cost_adjusted_walkforward_backtest.md

# Sensitivity: test higher/lower costs
python3 tools/backtest_cost_adjusted_wf.py --cost-bps 10  # optimistic
python3 tools/backtest_cost_adjusted_wf.py --cost-bps 50  # pessimistic
```

---

## 6. Files produced

| File | Purpose |
|------|---------|
| `tools/backtest_cost_adjusted_wf.py` | The backtest simulation script (new) |
| `audit_dashboard/data/cost_adjusted_walkforward_backtest.json` | Full JSON results (all 27 variants) |
| `audit_dashboard/data/cost_adjusted_walkforward_backtest.md` | Human-readable summary |

These are **uncommitted** — will be committed with the forward-test protocol in the next step.

---
