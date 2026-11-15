# Forward-Test Tracking Protocol — Fast Eliminate vs Hold Longer
**Date:** 2026-11-15  
**Worktree:** scratch-hippodraco  
**Purpose:** An easy-to-run protocol to forward-test candidate strategies, eliminate losers fast, and decide when to hold longer vs promote vs kill.  
**Core principle:** You cannot prove profitability in a backtest. You can only disprove it quickly in forward testing. The protocol is biased toward **fast elimination** to save capital and attention.

---

## 0. Pre-registration (do this BEFORE forward testing starts)

Forward testing without pre-registration is just backtesting in disguise. Before month 1 of forward testing, write down and commit:

| Field | Value (example) |
|-------|-----------------|
| Strategy name | `eq-mom-lb12-skip0-nl8` |
| Asset class | EQUITY |
| Benchmark | SPY total return |
| Entry rule | Top-8 by 12-month momentum, monthly rebalance, long-only |
| Cost per trade | 20 bps round-trip |
| Position sizing | Equal weight across n_long |
| Start date | First trading day of next month |
| Planned duration | ≥ 6 months (n≥6 trades minimum to evaluate) |
| T2 gate targets | PF≥1.5, WR≥50%, MDD≤20%, n≥100 |
| Kill criteria | See Section 3 |

**Save this as:** `reports/forward_test_<strategy>_preregistration_<YYYYMM>.md`  
**Do not change it during the forward test.** Changes = new test, reset the clock.

---

## 1. Monthly tracking log (one row per month)

Track in `reports/forward_test_<strategy>_log.csv`. Columns:

| Column | Meaning |
|--------|---------|
| month | YYYY-MM |
| start_date | First trading day |
| end_date | Last trading day |
| n_long_held | Number of positions held |
| positions | Comma-separated tickers |
| gross_return_pct | Gross monthly return before costs |
| cost_bps | Cost deducted (bps) |
| net_return_pct | Gross − cost (this is the trade PnL) |
| cumulative_net_pct | Compounded cumulative net return |
| peak_cumulative_pct | Running peak of cumulative |
| mdd_pct | Max drawdown from peak this month |
| spy_return_pct | SPY total return same month (benchmark) |
| excess_vs_spy_pct | net_return − spy_return |
| win | 1 if net_return>0 else 0 |
| running_n | Cumulative trades so far |
| running_wr_pct | Win rate over running_n |
| running_pf | Profit factor over running_n |
| running_sharpe | Annualized Sharpe over running_n |
| status | ACTIVE / WATCH / ELIMINATED / PROMOTED |

**Example row:**
```
2026-12,2026-12-01,2026-12-31,8,GOOGL,AVGO,NVDA,JNJ,XOM,WMT,HD,PG,-0.5,20,-0.7,-0.7,-0.7,-0.7,-1.2,0.5,1,1,1,2.62,1.27,ACTIVE
```

---

## 2. Decision gates (evaluate at each month-end)

### Gate A — Fast elimination (can eliminate as early as month 2)

Eliminate immediately if **ANY** of these are true:

| Kill rule | Threshold | Rationale |
|-----------|-----------|-----------|
| K1: Catastrophic month | single month net_return < −10% | One bad month blows up the edge |
| K2: Cumulative drawdown | running MDD > 25% | Breaches the 20% T2 cap with buffer |
| K3: Negative expectancy | running mean net_return < −0.1%/trade | Edge is negative after costs |
| K4: Benchmark trauma | cumulative excess vs SPY < −15% AND running_n ≥ 6 | Clearly worse than doing nothing |
| K5: Zero trades | running_n = 0 for 2 consecutive months | Strategy not emitting |

**Eliminate →** log status `ELIMINATED`, write a one-page postmortem, do not revisit for 6 months.

### Gate B — Hold longer / continue (default state)

Continue if **ALL** of these are true:
- None of K1–K5 triggered
- running_n < 100 (need more data to reach T2)
- running MDD ≤ 25%
- Not yet at promotion gate

**Hold longer →** log status `ACTIVE`, continue to next month.

### Gate C — Watch (warning, not elimination)

Move to `WATCH` if **ANY** of these (warning zone):
- running MDD 18–25% (approaching the 20% cap)
- running WR < 45% (approaching coin-flip)
- cumulative excess vs SPY < −5% AND running_n ≥ 6
- 2 consecutive losing months

**Watch →** log status `WATCH`, reduce size by 50% if trading, increase scrutiny. If WATCH persists 2 consecutive months → re-evaluate for elimination.

### Gate D — Promote (only after sufficient evidence)

Promote to paper-pilot/live consideration only if **ALL** of these:
- running_n ≥ 100 (≥100 forward trades)
- running PF ≥ 1.5 (post-cost)
- running WR ≥ 50% (post-cost, EXPIRED-inclusive)
- running MDD ≤ 20%
- running Sharpe ≥ 1.0
- Cumulative excess vs SPY > 0
- ≥ 6 months of forward data
- No month worse than −8%

**Promote →** log status `PROMOTED`, proceed to ¼-Kelly live pilot with DD-halt (see Section 5).

---

## 3. Fast elimination vs hold longer — decision tree

```
Month-end review
│
├─ K1–K5 triggered? ──────────────────→ ELIMINATED (stop, postmortem)
│
├─ running_n ≥ 100 AND all Gate D met? ──→ PROMOTED (¼-Kelly pilot)
│
├─ WATCH zone (MDD 18–25% or WR<45% or excess<−5% for 2+ months)?
│   │
│   ├─ Yes, 2 consecutive months ──→ ELIMINATED (or reduce to 0 size)
│   └─ Yes, 1st month ──────────────→ WATCH (reduce size 50%, scrutinize)
│
├─ running_n < 100 AND no kill rules ──→ ACTIVE (hold longer, continue)
│
└─ running_n ≥ 100 but FAILS any Gate D criterion
   │
   ├─ PF<1.5 or WR<50% or MDD>20% ──→ ELIMINATED (edge not real)
   └─ Sharpe<1.0 or excess_vs_SPY<0 ──→ ELIMINATED (no alpha over passive)
```

**Bias:** Default to eliminate. The burden of proof is on the strategy to keep surviving. Most strategies should die by month 3–6.

---

## 4. Minimum forward-test duration before ANY decision

| Decision | Minimum duration | Minimum trades |
|----------|-----------------|----------------|
| Fast eliminate (K1–K5) | Month 2 | 2 |
| Watch | Month 2 | 2 |
| Promote (T2) | 6 months | 100 |
| Eliminate after Gate D failure | 6 months | 100 |

**Never promote before 6 months and 100 trades.** A 3-month "hot streak" is noise.

---

## 5. Risk controls during forward test

Even in forward testing (paper or small size):

| Control | Rule |
|---------|------|
| Position size | Max 2.5% of account per trade (¼ Kelly cap) |
| Daily soft-stop | −2% total account PnL → pause trading that day |
| Monthly halt | Rolling 30-day drawdown > 30% → pause all sizing, re-evaluate |
| Concentration | No single symbol > 25% of the strategy's allocations |
| Cost tracking | Record actual realized costs, not assumed; if actual > assumed by 2×, re-run cost gate |

---

## 6. Template: forward test log (CSV header)

Copy this into `reports/forward_test_<strategy>_log.csv`:

```
month,start_date,end_date,n_long_held,positions,gross_return_pct,cost_bps,net_return_pct,cumulative_net_pct,peak_cumulative_pct,mdd_pct,spy_return_pct,excess_vs_spy_pct,win,running_n,running_wr_pct,running_pf,running_sharpe,status
```

**Example (first 3 months):**
```
2026-12,2026-12-01,2026-12-31,8,GOOGL,AVGO,NVDA,JNJ,XOM,WMT,HD,PG,1.2,20,1.0,1.0,1.0,1.0,0.8,1,1,100.0,inf,inf,ACTIVE
2027-01,2027-01-01,2027-01-31,8,GOOGL,AVGO,NVDA,JNJ,XOM,WMT,HD,PG,-2.4,20,-2.6,-1.6,-1.6,-1.6,-0.4,1,2,50.0,2.0,1.41,ACTIVE
2027-02,2027-02-01,2027-02-28,8,GOOGL,AVGO,NVDA,JNJ,XOM,WMT,HD,PG,3.1,20,2.9,1.3,1.3,1.3,1.5,1,3,66.7,3.0,1.73,ACTIVE
```

---

## 7. When to eliminate vs hold longer — quick reference

| Situation | Action |
|-----------|--------|
| One month −10% or worse | **Eliminate immediately** (K1) |
| Running MDD > 25% | **Eliminate immediately** (K2) |
| Running mean return < −0.1%/trade | **Eliminate immediately** (K3) |
| Cumulative vs SPY < −15% after 6 months | **Eliminate immediately** (K4) |
| MDD 18–25% (first month) | **WATCH** — reduce size 50% |
| MDD 18–25% (2 consecutive months) | **Eliminate** |
| WR < 45% (any month after month 3) | **WATCH** |
| n≥100, PF≥1.5, WR≥50%, MDD≤20%, beats SPY | **PROMOTE** |
| n≥100 but fails any T2 criterion | **Eliminate** |
| n<100, no kill rules, no watch | **Hold longer** (continue) |

---

## 7. Files to create per forward test

| File | Purpose |
|------|---------|
| `reports/forward_test_<strategy>_preregistration_<YYYYMM>.md` | Pre-registered spec (immutable) |
| `reports/forward_test_<strategy>_log.csv` | Monthly tracking log |
| `reports/forward_test_<strategy>_postmortem.md` | Only if eliminated — why it died |

---

## 8. Bottom line

This protocol is designed to **kill strategies fast**. Most candidates will be eliminated by month 3–6. The single T2-clearing variant from our backtest (lookback=12, skip=0, n_long=8) should enter forward testing with this protocol. It needs ≥100 forward trades (≥6 months monthly) and must clear PF≥1.5 / WR≥50% / MDD≤20% / beat SPY — **all post-cost** — before any promotion. If it fails any gate, it is eliminated, not "given more time."

---
