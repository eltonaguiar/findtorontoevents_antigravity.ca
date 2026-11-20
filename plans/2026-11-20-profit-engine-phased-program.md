# A profit engine we can actually defend — phased program

**Date:** 2026-11-20 · **Author:** Buffy (freebuff-deepseek-v4-flash)
**Status:** program plan, phase 0 not started
**Extends:** [`2026-11-20-market-profit-system-plan.md`](2026-11-20-market-profit-system-plan.md) (Zoo, same day)
— same skeleton, but this version is built on numbers measured today rather than on the plan's
inherited claims, and it adds the one finding that changes the architecture (§2).

**Machine-readable todo ledger:** [`2026-11-20-profit-program-todos.json`](2026-11-20-profit-program-todos.json)

---

## 1. What the corpus actually says (read this session, not remembered)

| Source | Claim | What survives scrutiny |
|---|---|---|
| `reports/asset_class_edge_review_2026-11-20.json` | CRYPTO/STOCK/ETF/FUTURES "candidates" | **All four are volatility artifacts.** Up-rate rises, down-rate rises *more*, mean forward return *lower* than the rest. FOREX (oos_n=14) and BOND (oos_n=0) are **inconclusive, not negative** — no power, not no edge |
| `reports/TAA_SETTLE_2026-11-19.md` | ETF TAA "Sharpe 0.88 vs SPY 0.74, MaxDD −19%" | **Not reproduced in 576 lagged cells.** Best lag-1 = 0.795 Sharpe, −41.7% DD. Real result: −38% relative drawdown cut for ~0.5%/yr CAGR give-up. Drawdown control, not excess return |
| `reports/CLASS_DIVERGENCE_2026-11-19.md` | "/audit vs /audit3 disagree 3.2×" | Row-population difference + gross-vs-net field confusion. **ETF PF 1.82 is gross while its own net expectancy is −2.26%** |
| `docs/EDGE_IDEAS_BACKLOG_2026-11-19.md` | external reviews (Arena, Gemini, Grok, Mercury) | Selection alpha **−0.276%/trade**, CI [−0.506, −0.043], n=3,192. Costs decide survival. `wf_verdict` was peeking (+0.96% → −0.19% after PIT replay) |
| `tools/data/latest_scorecard.md` | per-class strategy tiers | **0/7 asset classes have a PROVEN strategy.** Every strategy reads UNPROVEN n/a |
| `paper_trading/sleeves.json` + `sleeve_summary.json` | $2k plan: 70% beta / 20% rotation / 10% sandbox | All four sleeves `collecting`, `n_marks=1`, forward n=0. Rotation picked QQQ/SPY/IWM/VNQ/EFA on 2026-11-19 |
| `docs/GRADUATION_RUNBOOK.md` | promotion gates | n≥200 forward, net CI>0 at 2× slippage, DSR≥0.95, split-half, beats random **and** beta-matched hold arms |
| `docs/BACKTEST_ADMISSIBILITY_STANDARD.md` (M-108) | 6-stage admissibility | Pre-register → real data → purged WF + costs → DSR/PBO → robustness → forward n≥100 |
| `reports/kimi_ultimate_proven_edge_2026-05-16.md` | "COMMODITY PF 13.1 n=49 = T1 edge" | **Backtest artifact.** n=49 with PF 13.1 cannot survive a 700-strategy trial history; it is exactly the class audit3 kills |
| `KIMI_RISEOFTHECLAW/STRATEGY_STATUS_REPORT.md` | 635 strategies, "12–18% annual, Sharpe 1.2–1.5" | Wish-list document. Its own §"management validation" is unfalsifiable. The *useful* part is the 90-day live follow-up: of 24 backtest "winners", only RSI(2) on SPY/QQQ stayed positive |
| `docs/ALL_STRATEGIES.md` | 700+ strategies, 15 systems | A discovery catalog (`Last updated 2026-03-17`), **not** an inventory of working edges. Breadth is the multiple-testing problem, not the asset |
| `reports/hypothesis_registry.json` | 108 hypotheses | 22 PRE_REGISTERED, 15 REFUTED, 19 FORWARD_OBSERVATION, 7 PAPER_PILOT, **1 SUPPORTED**. The registry is healthy; the evidence base is thin |

**One line:** we do not have a prediction edge, we have a measurement system that is finally
capable of saying no. That is the prerequisite for profit, not the profit.

---

## 2. The finding that changes the architecture (measured today)

Corpus claim under test: *"RSI(2) on SPY/QQQ is the only survivor of the Kimi 90-day live test."*

I did not take the number on trust. Ran it myself on fresh data (`yfinance`, 5y to 2026-11-20):
RSI(2) < 10 entry with close > 200d SMA, exit on close > 5d SMA or RSI > 70 or 10 bars, **decision
at close → execution at the next close (1-bar lag)**, cash between trades, cost charged per
transition.

| Symbol | in market | trades | strat CAGR | hold CAGR | strat Sharpe | hold Sharpe | strat MaxDD | hold MaxDD | **alpha per in-market day** |
|---|---|---|---|---|---|---|---|---|---|
| SPY | 23.6% | 111 | **5.0%** | 10.1% | 0.72 | 0.64 | **−6.2%** | −24.5% | **+7.2 bps** |
| QQQ | 23.1% | 102 | **7.6%** | 10.2% | 0.77 | 0.53 | **−11.3%** | −35.1% | **+11.3 bps** |
| BTC-USD | 19.5% | 120 | **8.5%** | −0.0% | 0.42 | 0.21 | −22.6% | −73.6% | **+17.4 bps** |
| SOL-USD | 15.7% | 89 | **9.0%** | −20.5% | 0.36 | 0.18 | −48.4% | −95.9% | **+23.7 bps** |
| SPY (no trend filter) | 33.9% | 157 | 9.7% | 10.1% | **0.86** | 0.64 | −8.9% | −24.5% | +10.2 bps |

Net of 4 bps round trip (equity) / 10 bps (crypto).

**Three conclusions, in order of importance:**

1. **The signal is real per exposed day and it is not a return engine.** Alpha is positive in
   *all five* configurations, including the one without a trend filter. But the strategy is only
   invested ~1 day in 4, so it forfeits three quarters of the market's drift. It "trails hold" on
   SPY/QQQ while beating hold by 8–29 CAGR points on BTC/SOL (where hold is negative).
2. **Therefore the architecture must scale exposure, not switch it.** An all-in/all-out
   implementation throws away the beta it needs to compound. The correct shape is
   **core position + signal-driven exposure tilt** (or leverage only while in-signal, financing
   the tilt), so total return is not capped by time-in-market. This is a design correction to
   both Zoo's plan and Copilot's, which treat these signals as standalone sleeves.
3. **The benchmark must be time-matched.** Comparing a 24%-invested strategy's CAGR to a
   100%-invested buy-and-hold conflates *selection skill* with *market exposure*. Any evaluation
   that does not report both alpha-per-exposed-day **and** time-in-market is uninterpretable —
   this is the same denominator error the audit pages were making with `scored_share_of_valid`.

**Honest limits of this measurement:** one 5-year window, one parameter set, no purge/embargo, no
financing cost on the leverage idea, close-to-close execution, and a single data source. It is a
**harness calibration and an architecture test — not admissible evidence.** Promotion still
requires the §4 gates.

---

## 3. Program phases

Rule inherited from the edge backlog and kept: **no new strategy may be generated while a Phase 0
or Phase 1 todo is open.** Each phase ends in an artifact another agent can re-run.

### Phase 0 — Make the truth instrumented (1–2 sessions, no strategy work)

Goal: every published number has a denominator, a vintage and a power estimate, and the freshness
of each class's inputs is enforced rather than described.

| ID | Todo | Done when |
|---|---|---|
| P0.1 | Price freshness per class with SLA: fetch equity/ETF/FX/futures/crypto, write `last_bar` per class, fail CI when a class exceeds its tolerance | `db_freshness.json` internally consistent; one check does not report 42 min while its `last_pick_at` is 2026-05-23 |
| P0.2 | Fix FX coverage: backfill 2026-02→11 daily bars **and** map `AUDJPY=X` / `AUD-USD` → `AUDJPY`; retire `EURUSDT` from FOREX | ≥90% of FX picks have computable alpha, or FX is declared unmeasurable and stops emitting |
| P0.3 | Publish **MDE per class** from real n and vol | a reader can distinguish "no edge" from "no power" (FOREX n=460, BOND n=0) |
| P0.4 | Selection alpha (vs same-instrument hold) as a per-class headline with CI, not a footnote | negative alpha is visible on `/audit` before any PF |
| P0.5 | Global trial counter threaded into `deflated_sharpe` | DSR cannot be computed with an understated `n_trials` |
| P0.6 | Publish `pf_gross` + `pf_net` + `expectancy_net` as separate keys; delete bare `pf` | no PF<1 with positive expectancy beside it |
| P0.7 | Fix or remove `policy_clean_*`: assert `policy_clean_n <= n_resolved` and that a changed n changes the ratio | the CRYPTO "clean n=22,633 vs published 21,928" contradiction is resolved or the columns are renamed |

**Exit test:** a stranger reads the dashboard and knows, per class: rows, price vintage, MDE, net
alpha vs hold. No number lacks a denominator.

### Phase 1 — Calibrate the harness against two knowns (1 session)

Goal: prove our own tribunal can tell a real edge from a dead one, using results we already know
the sign of.

| ID | Todo | Done when |
|---|---|---|
| P1.1 | Port the §2 RSI(2) spec into `alpha_engine` as a first-class strategy (lag 1, costs, cash leg, time-matched benchmark) | same numbers reproduce inside the repo, not just in a `/tmp` probe |
| P1.2 | Run it through `audit3_tribunal` **unmodified** | verdict recorded; if it fails, that is a finding about the gates and gets written up, not tuned away |
| P1.3 | Run the identical code on BTC/SOL and record both signs | harness reproduces the positive and the negative |
| P1.4 | Implement `alpha_per_exposed_day` + `time_in_market` as first-class metrics and add them to the audit3 coverage block | every verdict carries utilization, so an all-in/all-out strategy can never again look like a return engine |
| P1.5 | Write the overlay-vs-standalone decision memo (§2 conclusion 2) with a spec for the core+overlay shape | one document other agents can attack |

**Exit test:** our harness reproduces the sign of a known-positive and a known-negative result, and
every verdict reports utilization.

### Phase 2 — Stop destroying value before adding any (1–2 sessions)

Goal: the −0.44%/pick crypto-long and −0.27%/pick ETF selection alpha is an exit-design and cost
problem, and it is bigger than anything the system claims to earn.

| ID | Todo | Done when |
|---|---|---|
| P2.1 | A/B on the *same* signals: current median TP +2.5% / SL −1.5% vs symmetric vol-scaled time exit, paired bootstrap | no more independent-sample comparisons |
| P2.2 | Reconcile modelled slippage against measured fills per class (crypto telemetry says 0.0997%) | one canonical cost base, per side vs round trip stated |
| P2.3 | Kill any expression whose alpha vs hold is ≤ 0 in two regimes | retired cells stay in an observe pod with their record |
| P2.4 | Store `expected_move_pct` / `floor_pct` on entries so the 4× cost-floor refusals are auditable | refusal reasons are queryable |

**Exit test:** crypto-long and ETF selection alpha each improved to ≥ 0 in at least one regime on
identical entry signals, or the cell is retired with a written post-mortem.

### Phase 3 — One premium, pre-registered, on a forward clock (calendar-bound, 6–12 weeks)

Goal: exactly one real edge, chosen for the quality of its prior and the data we already hold.

Candidates, ranked by our evidence, **pick one**:

1. **Cross-sectional crypto momentum/carry** — 1.7M bars, 333 symbols already in the DB, genuine
   breadth, beta stripped by dollar-neutrality, cheap to test. This is what §2's alpha-per-day
   result argues for.
2. Vol-targeted TSMOM on liquid ETFs/futures — the strongest century-scale prior, already
   reproduced at Sharpe 0.795 lag-1; a drawdown-control allocation, not a return engine.

| ID | Todo | Done when |
|---|---|---|
| P3.1 | Pre-register the chosen hypothesis (event, direction, cost model, `n_trials`, kill rule) in `reports/hypothesis_registry.json` **before** the first run | registry entry exists with a falsification criterion |
| P3.2 | Freeze the spec; ≤5 configurations total; every trial logged | DSR uses the true count |
| P3.3 | Purged walk-forward + embargo, 2× measured slippage, 1-bar execution delay | OOS PF and net CI published |
| P3.4 | Control arms: random-entry (timing) and beta-matched hold (selection) | sleeve cannot be judged without both |
| P3.5 | Forward paper clock to n ≥ 100 | rows accrue unattended, marks idempotent |

**Exit test:** one pod with forward rows, a net CI at 2× cost, and a written verdict — promote,
keep-paper, or freeze. A negative verdict is a success for the program.

### Phase 4 — Portfolio, not pick list (after one survivor)

| ID | Todo | Done when |
|---|---|---|
| P4.1 | Correlation matrix on **forward** returns of survivors, not backtests | sizing uses measured covariance |
| P4.2 | Vol targeting + evidence weight (DSR, CI width) + hard per-sleeve risk budget | no position without an evidence weight |
| P4.3 | Regime caps (trend/chop/high-vol) with a tested response time | the 2020/2022 failure modes are simulated |
| P4.4 | Drawdown circuit breaker ≤ −15% from high-water mark, freeze + 48h post-mortem | kill switch tested, not described |
| P4.5 | Allocation shape: core beta + premia sleeve + ≤5% sandbox, and **exposure tilt** per §2 | total return is not capped by time-in-market |

**Exit test:** paper portfolio beats 60/40 **and** buy-and-hold on the same universe after costs,
with a smaller max drawdown — or it reports honestly that it only matches.

### Phase 5 — Reconcile, calibrate, decay-check (ongoing)

| ID | Todo | Done when |
|---|---|---|
| P5.1 | Daily reconciliation: sleeve equity vs summed positions + cash, incident at >$1 | three consecutive clean months |
| P5.2 | Brier score of our own verdicts (predicted confidence vs realised) | calibration curve published |
| P5.3 | Sabotage suite: inject a known-bogus strategy (must reject) and a known-real one (must accept) | CI fails if either misclassifies |
| P5.4 | Quarterly decay review per surviving edge (IC slope) | retirement is a scheduled decision, not a surprise |

**Exit test:** an outside reviewer recomputes any published verdict and gets the same answer, and
watches the system reject a deliberately fake edge.

---

## 4. Gates (unchanged, deliberately hard)

Promotion to real money requires **all** of: forward n ≥ 200 · net CI lower bound > 0 at 2× measured
slippage · DSR ≥ 0.95 with declared `n_trials` · both split halves net-positive · no symbol > 60%,
no source > 90% · beats **both** control arms · 3 clean reconciliation months · inputs not stale.

A sleeve that fails any gate is **unproven**, not "almost ready". Micro-live is ≤10% of target
allocation and ≤2% account risk, drawn from the core, never new money.

## 5. Where I expect the money to actually come from

1. **Exposure-tilted mean reversion** (§2) — measured positive alpha per exposed day, structurally
   capacity-limited, currently mis-implemented as all-in/all-out.
2. **Beta, cheaply held** — still the only defensible base allocation at $2k; every cost basis
   point is a guaranteed return that no signal has matched yet.
3. **Cross-sectional crypto momentum** — best data-to-hypothesis ratio we hold, unproven.
4. **Trend/rotation** — real drawdown reduction, no demonstrated excess return; suitable for risk
   control, must never be sold as alpha.
5. **Forex and bonds** — *currently unknowable*: stale prices plus no power (MDE). Not "no edge".

## 6. What this program refuses

- To publish a return target. Any "12–18% annually" without a forward clock is a wish.
- To count the 700-strategy catalog, or 635 Kimi strategies, as progress.
- To call an inconclusive class a failure or a success.
- To promote on backtest evidence, including the §2 result above.
- To compare a partially-invested strategy to a fully-invested benchmark without saying so.
- To run a new discovery pass while any Phase 0/1 todo is open.
