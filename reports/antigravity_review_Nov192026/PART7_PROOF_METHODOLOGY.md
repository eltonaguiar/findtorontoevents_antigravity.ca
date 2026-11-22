# PART 7 — What Statistics Actually Prove An Edge (and why ours couldn't)
**Author:** githubcopilot-mercury3AI · **Date:** 2026-11-22 · **Status:** research → simulation
**Depends on:** `PART6_WORTH_THE_MONEY_PLAN.md`, `reports/hypothesis_registry.json`, `tools/edge_stability_harness.py`

---

## 0. The finding that reframes everything

Before proposing a single new statistic, I read what this repo has already done. Result:

> `reports/EDGE_HUNT_EXHAUSTED_2026-05-18.md`: **"11 pre-registered causal hypotheses tested. 11 killed. 0 admissible."**
> H-001 COMMODITY COT · H-006 CRYPTO funding-z · H-007 COMMODITY roll-yield · H-008 BOND 2s10s momentum · **H-010 EQUITY PEAD 30-day drift** · H-012 CRYPTO funding carry · H-013 EQUITY/ETF options flow · H-014 CRYPTO on-chain · H-017 CRYPTO liquidation cascade · H-019 CRYPTO exchange net-flow · H-020 CRYPTO Coinbase premium.

And the failure mode was almost always the **same**: not "no effect measured" but **sign-split** —
`H-008: sign-split 144+/182−`, `H-010: sign-split 3+/2−`, `H-006: sign-unstable 4+/4−`, `H-020: 23+/22−`.

That is the signature of a test with **low statistical power**, not necessarily of an efficient market. Two hypotheses explain "11/11 sign-split":
- **H-A (market):** the effects are absent or already arbitraged.
- **H-B (instrument):** the detector — `edge_stability_harness` with `EFF_MIN=0.30`, `MIN_WINDOW_N=80`, `MIN_STABLE_WINDOWS=3` — has a true-positive rate so low that it kills real effects too.

**These are distinguishable by experiment, and nobody has run that experiment.** That is Part 7's first job. It is also, to be blunt, the highest-value thing available: if H-B is true, we have been discarding real edges for six months; if H-A is true, we can finally stop re-testing dead families with a clear conscience.

The user's instinct — *"for stocks, if something continually beats their earnings release or seems to go up over time"* — maps to **exactly two hypotheses that are already in the registry**, and one of them is already dead:

| User's idea | Formal name | Registry status |
|---|---|---|
| "continually beat their earnings release → keeps going up" | **PEAD** (Ball & Brown 1968; Bernard & Thomas 1989) | **H-010 REJECTED** (30-day daily holds, sign-split 3+/2−). H-002 shadow, pooled WR 53.2% n=1964, harness "UNTESTED (too few windows)". H-016 (intraday-anchored retry) **blocked on paid 1-min data**. |
| "seems to go up over time, may dip but consistent" | **time-series momentum / trend** (Moskowitz-Ooi-Pedersen 2012) | H-007 (commodity roll) killed; ETF trend survived as *risk control* only (`TAA_SETTLE_2026-11-19.md`) |

So the honest answer to "prove PEAD works" is: **the 30-day daily-bar version is already falsified in this repo**, and re-running it on the same data is explicitly forbidden by `EDGE_HUNT_EXHAUSTED_2026-05-18.md`. What is *not* falsified is whether the gate was capable of detecting it. That's the gap.

---

## 1. Why the statistics we have been using cannot prove profitability

| Statistic we use | What it actually measures | Why it fails as proof |
|---|---|---|
| **Win rate (WR)** | P(outcome = WON) | Ignores payoff. A 90% WR at 0.2R loses money. Our ledger has exactly this pathology (CRYPTO WR 40% with PF 0.83 vs other cells WR 55% with PF<1). |
| **Profit factor (PF)** | gross win / gross loss | Unstable at small n (PF 1265 on n=22 — see `PART5_P0_P3_FINDINGS.md`), unbounded, no CI. |
| **Sharpe ratio** | mean/sd × √12 | Assumes iid normal; ignores skew/kurtosis/autocorrelation; is an **estimate** whose uncertainty is not reported; and is the *maximised* statistic when you try many variants. |
| **Max drawdown** | worst peak-to-trough | One observation from one path. Has an enormous sampling distribution; never comparable across different-length samples. |
| **`eff` sign stability** | score separation WON vs LOST per window | **Measures discrimination, not profitability.** Also has no power analysis and no multiplicity control. |
| **`n`** | count | Everyone quotes it; nobody computes whether it was enough. |

None of these establishes the three things a desk actually requires:
1. **Is the estimate distinguishable from luck, given how many things we tried?** (multiplicity)
2. **Would it survive being executed?** (costs, slippage, capacity)
3. **Is there a reason it should persist, and who is losing?** (economic mechanism)

---

## 2. The statistic stack we are missing — and why each one

Tier A and B are the ones that turn "measurement" into "proof". Tier C is what turns "proof" into "allocatable".

### Tier A — Significance with honesty about multiplicity

**(A1) Probabilistic Sharpe Ratio (PSR)** — Bailey & López de Prado (2012).
$$\mathrm{PSR}(SR^*) \;=\; \Phi\!\left(\frac{(\hat{SR}-SR^*)\sqrt{n-1}}{\sqrt{1-\gamma_3\hat{SR}+\frac{\gamma_4-1}{4}\hat{SR}^2}}\right)$$
*Why:* replaces "Sharpe = 1.2" with **"P(true SR > benchmark) = 0.94 given n, skew, kurtosis"**. Directly fixes the four Sharpe sins above. Our repo has `alpha_engine/risk_metrics.py` + `tools/sharpe_lower_bound.py` — wire these into every verdict.

**(A2) Minimum Track Record Length (MinTRL)** — same paper.
$$n^* \;=\; 1+\Big[1-\gamma_3\hat{SR}+\tfrac{\gamma_4-1}{4}\hat{SR}^2\Big]\left(\frac{Z^{-1}[1-\alpha]}{\hat{SR}-SR^*}\right)^{2}$$
*Why:* answers "**how many months of forward data must we collect before we can believe it?**" *before* starting the forward test. This is what makes P6.6's promotion gate a number instead of a vibe.

**(A3) Deflated Sharpe Ratio (DSR)** — Bailey & López de Prado (2014).
$$E[\max SR]\approx\sqrt{V[\{\widehat{SR}_n\}]}\left((1-\gamma)Z^{-1}\!\Big[1-\tfrac1N\Big]+\gamma Z^{-1}\!\Big[1-\tfrac1{Ne}\Big]\right)$$
*Why:* we tested 27 equity-momentum variants, 576 TAA cells, 11 causal hypotheses. The **best of N is a biased estimator**; DSR discounts the observed Sharpe by the expected maximum of N zero-edge trials. Without it, "best of 27" is meaningless. Existing tool: `tools/deflated_sharpe_per_feed.py`, `tools/run_anti_overfit_audit.py`.

**(A4) White's Reality Check / Hansen SPA** — the family-level test: *"is the BEST of my K strategies better than chance, after accounting for K?"* Existing tool: `tools/whites_reality_check.py`. This is the correct test for "we tried a whole family, did anything survive", as opposed to per-cell DSR.

**(A5) Probability of Backtest Overfitting (PBO) via CSCV** — Bailey, Borwein, López de Prado, Zhu (2015). Combinatorially split the timeline into S blocks, compute the rank of the in-sample-best configuration out-of-sample. PBO = P(the strategy you would have selected is a loser OOS). Existing tool: `tools/pbo.py`. *Why:* this is the only statistic that directly quantifies "we picked the winner of a grid, and grids produce winners from noise".

### Tier B — Robustness of the *instrument* (the missing piece)

**(B1) Statistical power / Minimum Detectable Effect (MDE).** For a two-sample effect size $d$ with $n$ per group:
$$\mathrm{MDE} \approx (z_{1-\alpha/2}+z_{1-\beta})\sqrt{2/n}$$
At $\alpha=0.05,\ \beta=0.20$, $n=80$ per window ⇒ **MDE ≈ 0.44 sd**. Our gate asks for `eff ≥ 0.30` while its own sample-size floor of 80 can only reliably detect **0.44**. ⇒ **The gate is under-powered by construction: it can pass an effect it cannot detect.** That single arithmetic fact explains `H-010: sign-split 3+/2−` better than "PEAD is dead" does.

**(B2) Operating-characteristic curve of the gate (TPR/FPR vs true effect).** Not a formula — a **simulation**. Plant a known edge, run the real gate, count detections. See §4. This is the "simulation" the user asked for, and it is the only way to know whether 11/11 kills is a market fact or an instrument fact.

**(B3) Block / stationary bootstrap** (Politis-Romano) rather than iid bootstrap, because monthly/daily strategy returns are autocorrelated and vol-clustered; iid resampling understates tail risk and overstates significance.

**(B4) Purged & embargoed walk-forward, and CPCV.** López de Prado's purging removes train/test leakage across overlapping labels; embargo removes serial correlation bleed. Existing: `tools/wfe.py`, `tools/forward_signal_research.py` (both mention embargo/purged). *Why:* PEAD holds 30-60 days — a naive k-fold CV leaks because adjacent folds share the same drift window.

### Tier C — Executability, path, and economics

| Stat | Question it answers | Threshold we will use |
|---|---|---|
| **Cost cushion / break-even cost** | "at what cost per trade does this die?" | must be ≥ 3× our modelled cost |
| **Capacity proxy** (ADV participation) | "how much AUM before we are the market?" | ≥ $10M at 1% ADV |
| **CVaR 95% / Expected Shortfall** | "when it goes wrong, how wrong?" | — |
| **Longest underwater (days)** | "how long does the investor stare at red?" | ≤ 24 months |
| **Ulcer / Pain index** | drawdown depth × duration | — |
| **Skew / kurtosis / tail ratio** | hidden short-vol profile | kurtosis < 10 |
| **HHI / top-name P&L share** | is it one trade? | top-decile share < 50% |
| **Effective N** (independent bets) | "how many real observations?" | ≥ 30 — existing `tools/effective_n_reporter.py` |
| **Factor alpha** (FF3/FF5+Carhart, Newey-West t) | "is it just beta to momentum/quality?" | t ≥ 2 net |
| **Cross-sectional IC / IR** (equities & crypto panels) | does the signal rank the cross-section? | mean IC ≥ 0.02, IR ≥ 0.3 |
| **Post-publication decay haircut** (McLean-Pontiff 2016: ~58% decay) | "what's left after everyone knows?" | apply 50% haircut to any published anomaly |

*Why the last one matters:* every anomaly we can find in a paper has already been harvested. Any equity factor must be discounted ~50% before it is believed, or validated on data after its publication date.

---

## 3. Per-asset-class proof specification

Each class fails for a *different* reason, so each needs a different proof. This table is the contract.

| Class | Structural trap | Required data | The decisive test | Why this is the right test |
|---|---|---|---|---|
| **EQUITY** | survivorship + look-ahead in filing dates | point-in-time prices incl. delisted; **actual** report timestamps | cross-sectional **IC by horizon** + long-short decile portfolio net of 20bp, with purged WF and factor-neutral alpha | Single-name event tests have no breadth; IC uses the whole cross-section per date → effective N is large, and it measures ranking skill directly |
| **CRYPTO** | survivorship of dead coins; illiquidity; 24/7 | exchange-listed history incl. delisted pairs; funding | same IC framework + funding/basis carry decomposed from price | Most reported "crypto edge" is either dead-coin survivorship or funding carry mislabelled as alpha |
| **ETF** | **few independent bets** — correlated assets ⇒ effective N tiny; short history | 15+ yrs total-return | portfolio-level vs real mutual-fund counterfactual (done in Part 6) + regime split | With ~10 correlated ETFs you cannot get significance from breadth; only the *portfolio* comparison is meaningful |
| **FOREX** | tiny per-trade edge; carry dominates; CB regimes | spot + forward points / rate differentials | carry-decomposed return, Sharpe vs a passive carry basket benchmark | A "Sharpe 1.0" FX strategy that is long high-yielders is just carry beta; must be benchmarked to it |
| **COMMODITY** | **roll yield ≠ spot**; COT publication lag T+3 | futures curves, not spot ETFs | roll-inclusive return, lagged COT, seasonality-controlled | Any commodity test on spot/ETF prices omits the dominant return component (that is what killed H-001/H-007) |
| **BOND** | duration beta; smoothed NAVs inflate Sharpe | total-return indices, treasury curve | excess-return (duration-hedged) alpha vs curve carry+roll-down | Duration beta is beta; smoothed marks auto-correlate and manufacture Sharpe |

---

## 4. The simulation programme (what we will actually run)

**S1 — Gate calibration / power curve (the decisive experiment).**
Synthetic pick streams with a *planted* known edge: latent quality $q\sim N(0,1)$, score $s=q+\varepsilon$, $\varepsilon\sim N(0,\sigma^2)$, outcome $y\sim\text{Bernoulli}(\sigma(\alpha q))$. Sweep true separation α (0 → 1.0), $\sigma$, picks-per-window (40/80/200/500), windows (3/5/10). Run the **real** `edge_stability_harness` decision rule. Report TPR and FPR per cell over ≥1,000 seeded draws.
*Deliverable:* "our gate detects a planted eff=0.45 edge 88% of the time and a planted eff=0.20 edge 12% of the time; false-positive rate at zero edge = X%."
*Consequence:* either the 11 kills stand (H-A) or they must be re-adjudicated with a correctly-powered test (H-B). No third option.

**S2 — Surrogate-data null.** Take real per-class return series, generate 500 IAAFT/block-bootstrap surrogates that preserve autocorrelation and volatility clustering but destroy any conditional signal; run the strategy on each. *Real* edge must beat the 95th percentile of the surrogate distribution. This is the correct null for a time-series strategy; random-entry MC assumes iid returns and is too easy to beat.

**S3 — Effect-injection on real data.** Superimpose a known drift on real bars, verify the pipeline recovers it with the right sign and magnitude. Detects sign conventions, lag errors, and cost-accounting bugs *before* they produce a false kill or false pass.

**S4 — Extensive per-class backtests** (the user's explicit ask): ≥ 20 strategy variants per class, purged walk-forward, 3 cost tiers, with PSR/DSR/PBO/Reality-Check/CVaR/MDD-duration/cost-cushion for each. Every result tagged with the trial count so DSR is computable.

**S5 — Regime-conditional re-adjudication of the 11 killed families** — *only* for families whose kill rested on sign-split, using a **pooled panel regression with cluster-robust standard errors** instead of per-window sign counting. Pre-register the regime definitions before running (so the regime choice itself pays the multiplicity cost).

---

## 5. What we will not accept as proof (unchanged, now with the reason)

| Rejected as proof | Reason |
|---|---|
| best cell of a grid | PBO ≈ 0.5 by construction on noise; needs DSR + PBO |
| one window's Sharpe | window selection; our own TAA claim died this way |
| sign-split "stability" from under-powered windows | MDE 0.44 > threshold 0.30 (§B1) |
| payoff-grid artifacts (MomentumEMA −2.00/+3.00) | synthetic outcome lattice, not a market |
| PF on n<30 | unbounded estimator, CI wider than the value |
| a model's opinion | hypothesis generator only → `DELEGATED_REVIEW.md` |
| a number that "appears in a report" | the 2026-11-20 retraction root cause: *verifying that a number appears is not verifying the number* |

---

## 6. Immediate execution order

1. **S1 gate calibration** — answers whether the 11 kills are trustworthy. *(highest value: it retro-validates or invalidates six months of verdicts)*
2. **S3 effect injection** — proves the pipeline can see what it claims to see.
3. **S4 per-class extensive backtests** — CRYPTO, EQUITY, ETF, FOREX, COMMODITY, BOND, each with the Tier A/B/C stack.
4. **S5 re-adjudication** of sign-split kills with pooled cluster-robust estimation.
5. Only then: a CANDIDATE, forward-tested per P6.6.

---
*Not personalized investment advice. This document specifies measurement, not recommendations.*
