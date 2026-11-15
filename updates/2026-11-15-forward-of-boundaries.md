# 2026-11-15 — O'Brien-Fleming interim looks, implemented; median hold measured

Two follow-ups on the forward test: the pre-registered interim looks were a *design* with no code
behind them, and `rs-breakout-scout`'s median hold was recorded as "not measured".

## 1. Interim looks now produce verdicts

`tools/forward_tracker.py` gains:

| Function | What it does |
|---|---|
| `of_boundaries(looks, n_final, alpha)` | Solves `c_k = C/√t_k` for C through the **exact** joint distribution of the sequential z-scores (standardised, correlation `√(t_j/t_k)`), so the total one-sided crossing probability under H0 equals alpha. Cached — the solve costs ~0.3s. |
| `interim_verdict(cfg, trades, today)` | Clusters ledger rows into `(opened, closed)` windows, computes the window-mean endpoint, and reports the observed z against the boundary of the most recent scheduled look. |
| `_endpoint(rows)` | Uses `excess_pp` when every row carries it — the **pre-registered** statistic — else net return, **and returns the name** so the verdict states which statistic it actually tested. |

Solved for the registered schedule `[25, 50, 100, 152]` at `n_final=152`, alpha 0.05:

| Look | Windows | Boundary (one-sided z) |
|---|---:|---:|
| 1 | 25 | **4.21** |
| 2 | 50 | **2.98** |
| 3 | 100 | **2.11** |
| 4 | 152 | **1.71** |

`C = 1.7077`; achieved alpha **0.0500** vs a 0.05 target — the solver reports the alpha it actually achieved, so any drift from 0.05 is visible rather than assumed.

Raising the final bar from 1.645 to 1.73 is the price of looking early; raising the *first* bar to 4.27
is what stops "we saw a big number at 25 windows" from becoming a promotion.

Verdicts at a look: `KILL` if a plan `kill_rules` entry fires, else `PROMOTE` only on crossing that
look's boundary, else `CONTINUE`. The kill rules are data in `plan.json`, not constants in the code:

```json
"kill_rules": [
  {"at_n_windows": 20, "if_mean_lt_pp": 0.0, "and_pf5_lt": 1.0},
  {"at_n_windows": 50, "if_mean_lt_pp": 0.25}
]
```

`status` now prints an interim section and `status.json` carries an `interim` object per strategy.

### Two conflicts this resolved

1. `plan.json` previously said both "an early large effect can promote" (design) and "no promotion off
   interim looks" (kill rule). Promotion at an interim look is now **allowed and explicitly
   expensive**, which is the only coherent reading of an O'Brien-Fleming design.
2. The registered endpoint is *excess vs benchmark*, but synced ledger rows carry no benchmark. Rather
   than silently testing net return and calling it the registered test, `_endpoint` labels the
   fallback. **Today every forward verdict would be on `net_return_pp`**, because the dashboard payload
   carries no benchmark series — that is a real gap, stated here rather than buried.

## 2. Median hold measured

From `reports/pick_excess_returns.json` (`hold_hours`, n=45, EQUITY only):

| | |
|---|---:|
| Median | **119.12h = 4.96d** |
| p25 / p75 | 48.5h / 167.6h |
| Max | 168.9h |

The max sits just under 168h because the rule carries a 168-hour time stop — the distribution is
censored by design, which is worth knowing when reading the mean. Filled in: `FORWARD_TEST.md` §1
("not measured" → ~5 days) and §2b, plus `plan.json` (`median_hold_hours`, `median_hold_days`).

Note 4.96d is just under the 5-day fast/slow split. The plan registers `hold_type: long`, so the slow
clock applies regardless; the borderline value is recorded rather than smoothed to 5.

## Verification

| Check | Result |
|---|---|
| `of_boundaries([25,50,100,152], 152, 0.05)` | C=1.7077, boundaries [4.211, 2.978, 2.105, 1.708], achieved alpha 0.0500 |
| Monotone decreasing | yes |
| Final boundary vs z_0.95 | 1.73 ≥ 1.645 (conservative, as OF requires) |
| `selftest` | 8/8 rule cases + 7 OF checks |
| `status` | interim section renders; 0 windows → `CONTINUE`, next look 25 |
| `build_forward_clock` | n/a this commit |

## Limits

- **Every existing strategy has 0 windows**, so the interim machinery reports `CONTINUE` and
  `0/25 windows to the first look`. Nothing about its statistical behaviour has been observed on real
  forward data yet — the OF checks exercise synthetic series, not the ledger.
- **The endpoint gap is real**: until synced rows carry `excess_pp`, the interim test runs on net
  return and says so. Fixing it means computing the benchmark leg at sync time.
- The boundary solve is a 240-node trapezoid grid. `achieved_alpha` is reported so any drift is visible
  rather than assumed away.
