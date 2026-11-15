# Negative Result Diagnosis & Strategic Governance Pivot (`negative_result_diagnosis.md`)

**Run ID:** `2026-11-15_0725_inspect-wt` | **Audit Verdict:** `0 / 9` Strategies Pass Non-Negotiable 10-Step Proof (`PROVEN = 0`)  
**Scope:** Formal diagnosis of every tested candidate failure, explicit Near-Miss Sample-Size Protocol (**Question 1**), and Concrete Passive Asset-Allocation Dashboard Pivot Blueprint for `findtorontoevents.ca/audit` (**Question 2**).

---

## 1. Candidate-by-Candidate Failure Diagnosis Table

Every candidate in the seeded 9-trial battery (`SEED = 42`, `run_proof_suite.py`) underwent the full 10-step Proof Standard. Below is the exact primary breakdown mechanism per strategy from observed outputs (`experiment_results.json`, `proof/*.json`).

| Trial ID | Observed Verdict | Gates Passed | Primary Statistical & Structural Failure Mechanism | Recoverable? |
|---|---|---|---|---|
| **`M1`** (`Mutual Funds`) | `PROMISING (NEAR-MISS)` | `7/10` | Cleared WFO (`WFE 3.50`, `OOS Sharpe 0.708`), Block MC (`93.5%+`), Friction (`16.2x`), Regimes (`4/5 +`). **Failed** significance (`t=1.67, p=0.097`, Block CI `[-0.07%, +1.00%]`), `DSR(N=646)=0.029`, and `Shuffle p=0.655` (did not beat shuffled asset-drift price paths; trailed static `SPY B&H` `12.82%` CAGR / `0.747` Sharpe and matched `60/40` `7.31%` CAGR at higher `12.3%` vol). | **Shadow Test (`>=24m`)** via pure TFSA / 0.15% MER index funds |
| **`E1`** (`ETFs`) | `PROMISING (NEAR-MISS)` | `7/10` | Identical structural mechanism to `M1`: `10 bps` RT cost reduces net CAGR slightly (`+7.31%` vs `+7.49%`), `t=1.62 (p=0.108)`, `DSR(N=646)=0.026`, `Shuffle p=0.655`. Strong crash-protection behavior vs `DBC/TLT`, weak marginal alpha above `60/40` in a secular US equity bull. | **Shadow Test (`>=24m`)** as benchmarked passive+momentum sleeve |
| **`CM1`** (`Commodities`) | `REJECT` *(Anomaly Note)* | `7/10` | Achieved the **highest net return (`+9.08%`, PF `1.99`, WR `70.3%`, Block MC `96.2%+ / p5 +5.19%`) and ONLY significant Shuffle Control (`p=0.0050`)** among all 9 candidates—confirming genuine trend-timing skill over `GLD_BH` (`-37.4%` DD) & `DBC_BH` (`-61.7%` DD). **Failed** pre-registered WFO because the 2013–2019 commodity bear produced `IS Sharpe = -0.403` (`WFE = 0`), plus `DSR(N=646) = 0.083` and Block CI `[-0.019%, +1.20%]` barely crossing zero. | **Watchlist Only** (requires full secular commodity cycle OOS) |
| **`MA2`** (`Multi-Asset Combo`) | `REJECT` | `7/10` | Risk-parity blending (`E1 + B1 + CM1 + TLT/IEF`) cut volatility (`6.03%`) and MaxDD (`-12.57%`) cleanly across 4/5 regimes (`Shuffle p=0.065`), **but** fixed-income allocation (`B1`) dragged CAGR down to `+3.99%` (`+2.95%` CG tax), yielding `Sharpe 0.269`, `t=0.96`, and `DSR(N=646)=0.006`. | **Re-weight w/o `B1` trend drag** or keep as low-vol passive core |
| **`MA1`** (`Variant C /audit`) | `REJECT` | `5/10` | Beat random 6-strategy picks almost significantly (`p=0.055`, net Sharpe `0.754`, MaxDD `-6.63%`), **but** suffered insufficient OOS span (`n=237` trades across `179d`), unstable IS (`-0.124` -> OOS `+1.663`), `t=0.636 (p=0.526)`, `BlockMC 74.0%+` (<75% bar), and `DSR(N=646)=0.0007`. | **Shadow Collection** until `n>=500` clean OOS trades |
| **`S1`** (`Stocks /audit`) | `REJECT` | `5/10` | Classic **overfitting / regime break**: `IS Sharpe +2.427` collapsed to **`OOS Sharpe -0.694` (`WFE = -0.286`, `25%` positive folds)** and `-46.15%` annualized in high volatility, with `14`-trade losing streaks and `t=0.811`. | **No** — Retire swing/intraday stock pick emitter |
| **`B1`** (`Bonds`) | `REJECT` | `5/10` | Avoided `TLT_BH` `-54.5%` crash, yet delivered `+0.74%` net (`+0.13%` after Canadian ordinary tax), **`Sharpe -0.203`** vs `2.5%` cash, `20.4%` MC positive paths, and negative IS/OOS Sharpe (`-0.104 -> -0.390`). Active bond rotation destroys value after tax vs holding short T-bills (`CBIL/CASH`). | **No** — Hold T-bills / short ladder passively |
| **`C1`** (`Crypto 1h` + Live Cohort + OKX Funding) | `REJECT` | `3/10` | **Complete failure across every horizon:** 1h causal BTC trend lost `-24.93%` ann (`Sharpe -2.58`, `WR 25%`, `PF 0.54`, `breakeven 0 bps`); `/audit` live `CRYPTO` cohort (`n=1,966`) lost **`-0.351%` gross / `-0.551%` net (`PF 0.716`)**; OKX 51d funding yield (`+0.09–0.36 bps/8h`) delivered only `+0.29%/yr` net on `BTC` and `-0.41%/yr` net on `SOL` after `20 bps` turnover. | **No** — Kill all active crypto pick emitters |
| **`FX1`** (`Forex /audit`) | `REJECT` | `3/10` | Raw cohort (`n=187`) lost `-0.155%` gross and contained **19 `EURUSDT` crypto leaks** + 10 zero-PnL zombies. Clean cohort (`n=158`) scraped `+4.12 bps` gross, turning **`-3.88 bps` net (`-1.04%` CAGR, `Sharpe -1.965`, `PF 0.872`)** once conservative `8 bps` retail spread+swap applied (`breakeven 4.2 bps < 8.0 bps`). Disallowed in Canadian TFSA accounts. | **Hard-Disable Permanently** (`FOREX_HARD_DISABLE=1`) |

---

## 2. Structural Root-Cause Diagnosis: Why Years of Iteration Failed

1. **Multiplicity Explosion Without Wired Deflation (`N_repo = 646+` vs. `ANTI_OVERFIT_VALIDATOR_ENABLED=0`):**
   Building `anti_overfit_validator.py`, `purged_cv.py`, and `deflated_sharpe.py` while leaving them disabled in production (`audit_trail/quality_gates.py:81`) allowed **86.3% overfit strategies** (`69/80` in `live_anti_overfit_audit.json`) onto `/audit` while paying an insurmountable statistical multiplicity penalty (`SR_0` grows with $\sqrt{2\ln N}$).
2. **Short-Timeframe Friction Death:**
   Attempting to harvest `0.04%–0.30%` gross edges on intraday crypto (`-55 bps/trade` net), FX (`+4.1 bps` gross vs `8 bps` spread/swap), and ETF swings (`267%` cost/PnL per `per_class_cost_gate.py`) is mathematically negative-expectancy regardless of ML architecture (`XGBoost`, `LightGBM`, `Transformer`, `GRU-Attention`).
3. **Implementation & Data Hygiene Leaks:**
   `EURGBP=X = 688.17`, `XRPUSDT = 0.0`, `EURUSDT` tagged `FOREX`, sports bets in active financial feeds, `2026-06-04` resolver backfill injections, `78.6%` expired `0%` zombies, and daily duplicate SQL inserts made dashboard metrics completely unrepresentative of live fill outcomes.

---

## 3. Question 1 Resolution — The Near-Miss Sample-Size & Statistical Power Protocol

When a strategy (`E1`, `M1`, or `MA1`) shows plausible structural risk-adjusted properties (`7/10` gates or `p_random = 0.055`), failing solely on **sample size / statistical power / `DSR(N=646)`** requires a strict pre-registered protocol—**never curve-fitting existing history**:

1. **Statistical Power Calculation ($N^*$ Requirement):**
   To detect a true annualized excess Sharpe of $SR = 0.45$ (like `E1`/`M1` over `rf`) at one-sided $\alpha = 0.05$ (`z=1.645`) and 80% power (`z=0.842`):
   $$T_{\text{years}} \ge \frac{(z_{1-\alpha} + z_{\beta})^2}{SR^2} = \frac{(1.645 + 0.842)^2}{0.45^2} \approx \mathbf{30.5\text{ years (}\sim 366\text{ months)}}$$
   - Even against a loose single-strategy hurdle over `13.8` years (`165` months), an observed Sharpe of `0.45` yields $t \approx 0.45 \times \sqrt{13.8} = 1.67$ ($p \approx 0.097$)—**insufficient statistical power to distinguish real timing skill from market drift**, explaining why `Shuffle p = 0.655`!
   - By contrast, for swing cohorts (`MA1`, expected Sharpe `0.75` or per-trade expectancy `+0.32%` at `std = 3.5%`, per-trade `SR_t = 0.091`), statistical significance at $t \ge 2.5$ (`Bonferroni`-adjusted) requires $n^* \ge (2.5 / 0.091)^2 \approx \mathbf{755\text{ independent non-overlapping trades}}$ (consistent with `TESTING_PROTOCOL.MD`'s `n >= 500` floor vs current `n = 237`).
2. **Mandatory Near-Miss Execution Rules (Zero Post-Hoc Snooping):**
   - **Rule 1 (Cryptographic Freeze):** Lock code, universe, lookback `12-1`, vol-target `12%`, and cost parameters by SHA-256 hash (`experiment_configs.json`). Any parameter tweak creates a *new* pre-registered hypothesis and restarts sample count `n = 0`.
   - **Rule 2 (Fresh Forward Clock Beats Historical Multiplicity):** Because `N_repo = 646` already contaminated the historical dataset, `N=646` DSR cannot easily be overcome on old bars. Pre-registering **`N_forward = 2` (`E1`, `M1`) strictly on unseen future dates** evaluates statistical significance cleanly on fresh out-of-sample data free of legacy snooping!
   - **Rule 3 (Strict Shadow Accumulation Until Milestone):** Hold $0 real speculative capital (`PAPER / SHADOW_WATCH` in `tracker/predictions_tracker.csv`) until pre-registered checkpoint (`24` forward months for `E1/M1`; `n = 500` resolved OOS trades for `MA1`) **OR** hit an automatic abort circuit breaker (`MDD < -20%` or `PF < 0.95`).

---

## 4. Question 2 Resolution — Passive Asset-Allocation Dashboard Pivot Blueprint (`findtorontoevents.ca/audit`)

The single highest-EV upgrade to `findtorontoevents.ca/audit` is **pivoting the product from an active short-term pick casino (`0/9` profitable) into a transparent Canadian Quantitative Benchmark & Low-Turnover Portfolio Audit Platform**:

1. **Immediate Production Kills (Config Changes):**
   - Set `FOREX_HARD_DISABLE=1` (`alpha_engine/config.py:329`), permanently remove `CRYPTO` intraday/ML/scanners emitting negative `-0.55%/trade` expectancy, ban sports/futures leaks via asset-class allowlist validation, and set `ANTI_OVERFIT_VALIDATOR_ENABLED=1` (`audit_trail/quality_gates.py:81`) by default—not opt-in.
2. **Replace "Active Picks Feed" With Passive Core + Evidence Benchmarks:**
   - Default homepage panel compares user/portfolio allocations directly against **CAD-adjusted low-cost passive baselines** proven in this audit:
     - **Equity Growth Core (`100%` / `80/20` / `60/40` Canadian Asset-Allocation ETF equivalents, e.g., `XEQT/VEQT` or `SPY/AGG`):** Historical `SPY` `+12.82%` (`+9.47%` taxable), `60/40` `+7.31%` (`0.538` Sharpe, `-21.0%` MDD) at `0.15%–0.22%` MER.
     - **Canadian Tax-Location Router (`TFSA / RRSP` vs. `Non-Registered`):** Automatically display **Gross vs. Net-of-MER (`0.15%` vs `1.80%`) vs. After-Tax Ontario Returns** (`0%` TFSA/RRSP, `26.76%` Cap Gains, `53.53%` Ordinary/Bond Interest), demonstrating visually why bond rotation (`+0.13%` after ordinary tax) belongs out of taxable accounts and active `1.80%` funds destroy `+1.54%/yr`.
3. **Quarantined Research Sandbox Tab (Shadow Proof Lab):**
   - Demote all `PROMISING (NEAR-MISS)` (`E1`, `M1`) and watchlists (`MA1`, `CM1`) into a clearly badged **`UNPROVEN SHADOW LAB`** tab showing live: (a) days/months elapsed toward `N*` power threshold, (b) live realized vs. modelled slippage (`bps`), (c) live drawdown vs. `-20%` abort line, and (d) rolling **excess return over `60/40` and `SPY`**, preventing premature real-money deployment.
4. **Enforce Hygiene Invariants in `dashboard_generator.py`:**
   - Reject rows lacking live quote verification (`entry != 0`, `|entry - quote|/quote <= 10%`), forbid `pnl=0` zombie resolution overwrites, deduplicate by immutable `(strategy, symbol, entry_time)` primary key, and link every dashboard output directly to reproducible seeded proof JSON (`experiment_results.json`).
