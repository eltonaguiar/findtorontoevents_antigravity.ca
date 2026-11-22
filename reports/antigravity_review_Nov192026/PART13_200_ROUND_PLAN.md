# PART 13 — THE 200-ROUND PROGRAM

**Author:** `githubcopilot-mercury3AI`
**Date:** 2026-11-22 03:59 EST
**Supersedes:** the ad-hoc "next steps" lists in PART8–PART12
**End goal:** one or more asset classes that are (a) **back-test proven**, (b)
**monitored in GitHub Actions** for TP/SL outcomes, and (c) running as a
**paper-trading portfolio** with a forward record.

---

## 0. WHY THIS PLAN LOOKS DIFFERENT FROM THE LAST ONE

Rounds 1–12 asked *"is there edge?"* The answer came back **yes, gross — and it
is destroyed by fees.** Measured twice, independently:

| Harness | Universe | RT cost | Gross | Fees | Net | Fees/gross |
|---|---|---|---:|---:|---:|---:|
| `live_daytrade_sim.py` | 3 majors, next-bar-open fill | 12 bp | +$1,095.96 | $6,751.82 | −$5,655.86 | **616%** |
| `realtime_challenge.py` | 30 alts, same-bar-close fill | 20 bp | +28.22% | 250.80% | −222.58% | **889%** |

So the program's central question changes from:

> ~~Can I find a signal with a statistically significant edge?~~

to:

> **Which (asset class × horizon × execution style × cost) combinations have a
> gross edge large enough to survive their own cost of capture — and which of
> those survive out of sample?**

Every round below is organized around **cost-adjusted expectancy**, not
significance. Significance without cost survival is a rounding error with a
p-value.

---

## 1. THE ROUND CONTRACT (non-negotiable for all 200)

A round is only a round if it produces **all five**:

1. **One falsifiable question**, written before the data is touched.
2. **Pre-registration** in `reports/hypothesis_registry.json` under rule M-107.
3. **One reproducible artifact** — a script or command that regenerates the
   number from raw data, pinned by `n_trials` and data sha.
4. **A verdict** — `PASS` / `FAIL` / `INCONCLUSIVE` / `DATA_INTEGRITY_FAIL`,
   with the **least survivable number** named explicitly.
5. **A deploy** — pushed with a report, broadcast on COMS, and logged in the
   running scoreboard.

**Hard rules carried forward:**
- Publish `MDD_daily` alongside `MDD_month_end`.
- Disclose `n_trials` beside every Sharpe.
- Never head a comparison table with one window while computing each series on
  its own availability.
- A number is not verified because it appears in a report. Re-run it.
- Any gross result must be reported **beside** its fee and net, never alone.

---

## 2. PROMOTION GATES

### Gate C — "Cost-surviving" (NEW, gates everything)
Net expectancy after realistic cost > 0 with a **lower CI bound above zero**,
and `gross_edge / round_trip_cost ≥ 3.0`. A strategy whose gross edge is less
than 3× its cost is not tradeable regardless of its p-value.

### Gate B — "Back-test proven"
All six of the existing ALLOCATABLE test (PART 6) **plus** Gate C:
- **A1** net Sharpe ≥ SPY + 0.20 and ≥ 0.70 absolute
- **A2** `MDD_daily` ≤ 0.6 × benchmark
- **A3** both halves of a split-half sample positive
- **A4** bootstrap CI on net Sharpe excludes 0
- **A5** ≥ 80% of the variant grid within 25% of the best (not a lone spike)
- **A6** beats the "boring alternative" on ≥ 2 of 3 axes
- **C** cost-adjusted, as above

### Gate F — "Forward proven"
100 complete forward monthly observations (or 300 forward trades at higher
frequency) with realised net expectancy CI-LB > 0, and **no written kill
criterion triggered**. Until Gate F, the honest label is *back-test proven*,
never *profitable*.

---

## 3. THE 200 ROUNDS

### PHASE 0 — Measurement integrity (R1–R10)
*Nothing measured before the ruler is trusted.*

| # | Round | Question |
|---|---|---|
| R1 | Fee reality audit | Actual taker/maker fees per venue per tier — **is 20 bp right?** Binance spot is 10 bp taker, 7.5 bp with BNB; futures 2–4 bp. If our fee model is 2–5× reality, the whole fee conclusion must be restated |
| R2 | Slippage model | Measured vs assumed slippage as a function of order size and ATR |
| R3 | Fill-convention audit | next-bar-open vs same-bar-close vs VWAP — quantify how much gross edge is a convention artefact |
| R4 | Spread & funding audit | Half-spread and perpetual funding as recurring costs, not one-offs |
| R5 | Data integrity sweep | Negative/zero closes, gaps, stale bars, duplicate timestamps — the `CL=F` class of bug, across every series we use |
| R6 | Survivorship audit | Are delisted/merged tickers missing from any universe? |
| R7 | Ledger safety | Prove the forward ledger cannot be clobbered (the 430-row collapse lesson) with an automated guard test |
| R8 | Gate calibration refresh | Re-run the power curve at cost-adjusted effect sizes, not raw ones |
| R9 | Reproducibility harness | One command rebuilds every published number from raw + sha |
| R10 | **GATE 0**: no number may be cited from a phase that failed R1–R9 |

### PHASE 1 — Cost is the constraint (R11–R25)
*Directly attack the binding constraint from four directions.*

| # | Round | Question |
|---|---|---|
| R11 | Maker-first entries | Does a limit/maker entry flip gross-positive into net-positive? **Highest-value single test in the program** |
| R12 | Cost-break-even horizon | At what holding period does gross edge / cost cross 3.0? Per class |
| R13 | Trade-count minimisation | Minimum viable trade count to hold the same exposure |
| R14 | Low-cost venue mapping | Effective cost per class across venues; rank |
| R15 | Fee-tier sensitivity | Results under retail / VIP / maker-rebate schedules |
| R16 | Turnover vs net-return curve | Net return as a f(turnover) — find the interior optimum |
| R17 | Transaction-cost-aware sizing | Does sizing to cost (not to volatility) improve net? |
| R18 | Cost decay per class | Which classes have structurally low cost (bonds, ETFs) |
| R19 | Execution-timing study | Time-of-day / day-of-week cost variation |
| R20 | Cost model v2 | Publish a defensible per-class cost table with sources |
| R21–R25 | Cost-survival screen | Apply Gate C across the full existing ledger; publish survivors and casualties |

### PHASE 2 — Frequency ladder (R26–R45)
*Find the horizon where edge/cost is maximised, per asset class.*

- **R26–R29**: Crypto horizons — 1m, 5m, 15m, 1h, 4h, 1d, 1w (7 horizons × cost audit)
- **R30–R33**: Equity horizons — intraday, daily, weekly, monthly
- **R34–R36**: FX, commodity, bond horizons
- **R37–R40**: Horizon-optimality curve per class; identify the argmax of
  (gross edge / cost)
- **R41–R43**: Cross-class horizon comparison; is there a universal optimum?
- **R44–R45**: **GATE 2C**: per class, declare the single most cost-efficient
  horizon. All later rounds use only that horizon.

### PHASE 3 — Signal re-adjudication (R46–R65)
*The 11-killed / 0-admissible result was a process defect — the gate's MDE at
n=80 was 0.443 against a 0.30 bar. Redo it properly.*

- **R46–R50**: Re-adjudicate the four sign-split kills (H-008 144+/182−, H-010
  3+/2−, H-006 4+/4−, H-020 23+/22−) with **pooled cluster-robust estimation**
  instead of per-window sign counting
- **R51–R55**: Rebuild the gate with correct power; re-run all 11 with
  cost-adjusted Net Sharpe as the statistic
- **R56–R60**: Multiple-testing deflation across the whole registry
  (DSR / White's Reality Check / PBO-CSCV)
- **R61–R65**: **GATE 3**: publish a re-adjudicated hypothesis table with
  honest FDR control

### PHASE 4 — Per-class deep dives (R66–R85)
*Two rounds per class × 10 classes, each with a written kill criterion.*

Classes: CRYPTO, EQUITY, ETF, MUTUAL_FUND, INDEX, FOREX, COMMODITY, BOND,
FUTURES, PENNY_STOCK.

| Rounds | Contents |
|---|---|
| R66–R67 | CRYPTO |
| R68–R69 | EQUITY |
| R70–R71 | ETF |
| R72–R73 | MUTUAL_FUND |
| R74–R75 | INDEX |
| R76–R77 | FOREX |
| R78–R79 | COMMODITY |
| R80–R81 | BOND |
| R82–R83 | FUTURES |
| R84–R85 | PENNY_STOCK |

Each pair: (1) best cost-surviving candidate with full Gate B/C test;
(2) adversarial falsification attempt + external-replication options.
**No class may be silently dropped.** `DATA_UNAVAILABLE` is a legitimate
verdict but must be stated, not omitted.

### PHASE 5 — Execution realism (R86–R105)
*Moves the challenge from "simulated" to "honestly simulated".*

- **R86–R90**: Port execution to **ccxt sandbox** (binance / bybit / okx
  testnet). Real order types, real fee schedules, queue position
- **R91–R93**: Market vs limit vs stop-entry comparison under sandbox fills
- **R94–R96**: Partial fills, rejection handling, rate-limit backoff
- **R97–R99**: Latency budget: signal → order → fill, measured
- **R100–R102**: `alpaca-py` paper for the equity arm (4 bp-equivalent, honest fills)
- **R103–R105**: **GATE 5**: the challenge harness executes through a real
  matching engine, not a hand-rolled simulator

*(The REALTIMECHALLENGE rounds RT-2…RT-6 map onto R86, R91, R94, R100 and R103.)*

### PHASE 6 — Portfolio construction (R106–R125)
*Goal #1 is phenomenal performance across ALL classes — that is an allocation
problem, not a signal problem.*

- **R106–R110**: Correlation matrix of all cost-surviving candidates
- **R111–R115**: Risk-parity / HRP / CVaR-optimal weights (evaluate
  `PyPortfolioOpt`, `riskfolio-lib`, `skfolio` — adopt only if they beat
  hand-rolled)
- **R116–R120**: Regime-conditional allocation (trend overlay as a regime switch)
- **R121–R125**: **GATE 6**: a combined portfolio that beats the best single
  class on net Sharpe **and** on drawdown

### PHASE 7 — Deflation & robustness (R126–R145)
*The test most likely to kill our own results. Run it before believing them.*

- **R126–R130**: PBO/CSCV per class on the chosen configuration family
- **R131–R135**: Deflated Sharpe with honest `n_trials` including cross-class
  selection (the selection is **not** currently deflated)
- **R136–R139**: Regime split — is the result just 2008/2020/2022?
- **R140–R143**: True out-of-sample: train pre-2010, test post-2010
- **R144–R145**: **GATE 7**: publish which results survive deflation; retract
  the rest loudly

### PHASE 8 — Forward proof clock (R146–R165)
*Nothing is "proven" without forward evidence.*

- **R146–R150**: Register every survivor as a pre-registered forward hypothesis
  with written kill criteria — **before** the first observation
- **R151–R155**: Build GHA monitoring: scheduled runs that record TP/SL
  outcomes per signal (extend `live_daytrade_sim.py`, which currently runs in
  **no** workflow)
- **R156–R160**: Forward observation ledger with idempotent, clobber-proof
  append; automated integrity assertions
- **R161–R165**: 100-observation clock running; interim CI-LB reporting
- **GATE F** at 100 complete observations

### PHASE 9 — Paper-trading portfolios (R166–R185)
*Real portfolios, real forward P&L, no capital.*

- **R166–R170**: Launch paper portfolios (one per surviving class) via
  `paper_trading/portfolio_manager.py`
- **R171–R175**: Daily reconciliation: paper fills vs theoretical, slippage drift
- **R176–R180**: Risk limits live — 1%/trade, daily −5%, monthly −20%, 3-loss stop
- **R181–R185**: Publish a live paper-performance dashboard page under `/audit`

### PHASE 10 — Verdict & fiduciary answer (R186–R200)
*The user asked a real question: what is the best use of this money?*

- **R186–R190**: Assemble the final per-class scoreboard with everything marked
  back-test proven / forward proven / rejected
- **R191–R195**: Fiduciary comparison: GIC vs T-bills vs 60/40 vs the best
  proven strategy, net of all costs, with the honest probability of each
- **R196–R198**: Publish the recommendation, including the possibility that the
  answer is "a laddered GIC beats everything we could prove"
- **R199**: Full retraction sweep — every claim re-verified or withdrawn
- **R200**: Final program review

---

## 4. STANDING OBLIGATIONS (every round)

1. **Check COMS between every round** (standing user instruction). Diff retained
   topics; reply to peers with either a reproducible defect, a re-runnable
   computation, or a named research idea.
2. **Document every fix** in `updates/` with what broke, what changed, how verified.
3. **Never push files you did not author.**
4. **Pre-register before backtesting.** No exceptions.
5. **Report gross, fee and net together — always.**

---

## 5. WHAT WOULD MAKE ME ABANDON THIS PROGRAM

Writing the stop conditions down before starting, so they cannot be moved later:

- If **Gate C fails for all 10 classes** after Phase 1–2, then no tradeable edge
  exists at any cost we can access, and the honest recommendation becomes
  **low-cost index allocation + a GIC floor**, with the trend overlay offered
  purely as drawdown insurance.
- If **Phase 7 (deflation) kills every survivor**, the same conclusion follows.
- If after **R200** nothing has reached Gate F, the answer to "where should the
  money go" is *not* "keep searching" — it is to state plainly that this
  research program did not find a tradeable edge and to recommend accordingly.

**Current state: 0 classes back-test proven, 0 forward proven, 0 paper
portfolios, $0 sanctioned.**
