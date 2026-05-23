# Mercury Workflow Critique — 2026-04-20

Scope: critical review of Mercury's proposed 6-step pipeline (arch.bootstrap +
skfolio + pypbo), inventory of `arch.bootstrap`'s actual feature set, and a
corrected workflow sized to this repo's real data shape (per-pick `pnl_pct`,
signal-selection not capital-allocation).

## 1. Mercury's errors

1. **pypbo is not Bayesian optimization.** pypbo implements Bailey & Lopez de
   Prado's **Probability of Backtest Overfitting** (PBO) + Deflated Sharpe / PSR
   — it is a *diagnostic on a matrix of strategy trials*, not a hyperparameter
   optimizer. Step 5 as written ("Bayesian optimise hyperparams") is a
   category error. Use `optuna`/`scikit-optimize` if BO is actually wanted,
   and use pypbo for what it does (PBO, DSR) against the WF trial matrix.

2. **Step 2 bootstraps the wrong object.** Mercury says "bootstrap historical
   returns for uncertainty" but we are selecting discrete **picks** with
   `pnl_pct` — not running a continuous return stream per asset. A block
   bootstrap on a daily return series gives distributional CIs for an
   *allocation*; for us the unit of analysis is the closed pick, and the
   relevant statistic is Sharpe/PF/WR **on pnl_pct arrays per feed**
   (`tools/block_bootstrap_ci.py` already does this correctly).

3. **Step 3 double-counts signal.** Blending LSTM/XGBoost point forecasts with
   bootstrap means of realised returns produces a Frankenstein moment vector:
   the forecast already encodes a conditional mean; replacing or averaging
   with the unconditional bootstrap mean destroys the conditioning. If you
   want uncertainty around the *forecast*, bootstrap the **forecast residuals
   on a held-out fold**, not raw returns.

4. **Step 4 solves a problem we don't have.** skfolio's MV optimiser assumes
   a portfolio with weights summing to 1 and a covariance matrix across
   **held assets over time**. Our picks are event-driven, variable-duration,
   one-at-a-time; there is no simultaneous weight vector to optimise. skfolio
   is still useful here — but for `WalkForward` + `CombinatorialPurgedCV`,
   not `MeanVariance`. Using MV would force us to invent a fake
   asset-by-time matrix and would bias selection toward low-variance
   strategies regardless of edge.

5. **Step 5 invites overfitting the gates.** BO over gate thresholds
   (`scoreCompoundFloor`, `forwardWRMinPct`, etc.) against the *same* closed
   book we already mined is textbook selection bias. If any tuning happens,
   it must be under Combinatorial Purged CV with a held-out OOS slice, and
   the trial count must be fed to **Deflated Sharpe / PBO** before any
   accepted config is shipped.

6. **Pipeline mis-targets our goals.** Our three goals are (a) identify
   tradeable edge, (b) rank picks, (c) gate Guide-band activation. Mercury's
   flow optimises a portfolio weight vector we never deploy and skips the
   part that actually matters: **per-feed risk-adjusted CIs + multiple-
   testing correction** before a banner claim goes live.

## 2. `arch.bootstrap` feature inventory (verified from docs)

- **Classes**: `IIDBootstrap(*args, seed=...)`,
  `IndependentSamplesBootstrap`, `StationaryBootstrap(block_size, *args, seed=...)`,
  `CircularBlockBootstrap(block_size, ...)`, `MovingBlockBootstrap(block_size, ...)`.
  Helper: `optimal_block_length(x)` returns Politis-White optimal block size.
- **Iterator**: `for data, kwargs in bs.bootstrap(n_reps): ...` — yields
  resampled positional + keyword args.
- **High-level**: `bs.apply(func, reps)` → array of replicated statistics.
- **`bs.conf_int(func, reps, method=..., size=0.95, tail='two', extra_kwargs=..., std_err_func=..., studentize_reps=...)`**
  with methods: `percentile`, `basic`, `norm` (a.k.a. `var`/`cov`),
  `studentized`, `bc`, **`bca`** (bias-corrected + jackknife acceleration).
- **Joint multi-stat CIs**: `func` may return a 1-D numpy array / pandas
  Series; `conf_int` returns a `(2, k)` matrix of lower/upper bounds — so
  `[mean, sigma, sharpe]` CIs come out of **one** resampling pass.
- **State**: `.seed()`, `.reset()`, `.clone()`, `.get_state()`, `.set_state()`
  for reproducibility and branching runs.
- **No built-in joblib/Ray parallelism** — parallelise externally by cloning
  bootstraps with distinct seeds.
- **MCS test** (`arch.bootstrap.MCS`) for Hansen Model Confidence Set — useful
  for "is strategy A provably non-dominated in the top set?"

## 3. Corrected workflow for this repo

Our unit: closed pick with `pnl_pct`, feed membership (All/HC/Smart/Verified
Alpha/AC:*), strategy_id, timestamp.

1. **Generate picks** (unchanged): existing scanners → `pnl_pct` on close.
2. **Per-feed point metrics**: PF, Sharpe (annualised), Sortino, WR, MaxDD,
   Expectancy. (Already in `tools/hf_validation_stats.py`.)
3. **Per-feed bootstrap CIs with `arch.bootstrap`**:
   - `StationaryBootstrap(block, pnls, seed=...).conf_int(vector_fn, reps=10_000, method='bca')`
     where `vector_fn` returns `[pf, sharpe, wr, maxdd]` — one pass, joint CIs.
   - Block size via `optimal_block_length` (Politis-White), with floor 2 /
     fallback `ceil(n^(1/3))` for small n (matches current code).
   - **BCa** over percentile: Sharpe on crypto pnl is heavy-tailed +
     skewed; BCa corrects both bias and acceleration.
   - Auxiliary `CircularBlockBootstrap` cross-check; keep `IIDBootstrap`
     only for the strategy-group resample (picks within a strategy are
     exchangeable under the null).
4. **Walk-forward + Combinatorial Purged CV** via `skfolio.model_selection`
   (`WalkForward`, `CombinatorialPurgedCV`) — feed the closed-pick stream as
   a time-indexed `y`. This replaces Mercury's step 4 and answers
   "does edge survive OOS" without inventing a weight vector.
5. **Multiple-testing correction** via `pypbo`:
   - Assemble the `(trials × folds)` matrix of in-sample Sharpes across
     all strategy variants tested → `pbo()` for PBO, `deflated_sharpe_ratio()`
     for DSR. A strategy may only arm the banner if `DSR > 0` at p ≤ 0.05
     **and** PBO ≤ 0.5.
6. **Gate activation** is deterministic from (3)+(5):
   - Banner armed ⇔ HC-feed PF BCa-CI lower bound > 1.0 AND DSR p ≤ 0.05 AND
     PBO ≤ 0.5. No Bayesian tuning of thresholds.
7. **MCS** (`arch.bootstrap.MCS`) on the strategy set to produce the
   "provably non-dominated" cohort that feeds Verified Alpha.

## 4. Non-obvious code sketches

### 4a. Joint BCa CI for [PF, Sharpe, WR, MaxDD] in one pass
```python
from arch.bootstrap import StationaryBootstrap, optimal_block_length
import numpy as np

def vstat(x):
    x = np.asarray(x, float)
    pos, neg = x[x>0].sum(), -x[x<0].sum()
    pf = pos/neg if neg>0 else np.nan
    sh = x.mean()/x.std(ddof=1)*np.sqrt(252) if x.std(ddof=1)>0 else np.nan
    wr = (x>0).mean()
    eq = np.cumsum(x); dd = (eq - np.maximum.accumulate(eq)).min()
    return np.array([pf, sh, wr, dd])

b = int(optimal_block_length(pnls)["stationary"].iloc[0]) or 2
bs = StationaryBootstrap(b, pnls, seed=20260420)
ci = bs.conf_int(vstat, reps=10_000, method="bca")   # shape (2, 4)
```

### 4b. Double-bootstrap for PSR stability
```python
# Outer: resample closed picks; inner: BCa CI on Sharpe; record CI width.
outer = StationaryBootstrap(b, pnls, seed=1)
widths = []
for (inner_pnls,), _ in outer.bootstrap(500):
    inner = StationaryBootstrap(b, inner_pnls[0], seed=2)
    lo, hi = inner.conf_int(lambda x: np.array([sharpe(x)]), 2000, method="bca").ravel()
    widths.append(hi - lo)
# Stability score = 1 - IQR(widths)/median(widths)
```

### 4c. MCS to cut the strategy zoo
```python
from arch.bootstrap import MCS
# losses: (T, K) matrix — negative pnl per strategy per period
mcs = MCS(losses, size=0.10, reps=5000, block_size=b, method="max")
mcs.compute()
survivors = mcs.included  # strategies provably non-dominated at 10%
```

---
_No commits made. Implementation lives behind `tools/block_bootstrap_ci.py`;
extensions should route through BCa + joint-vector `conf_int` before any
banner threshold change._
