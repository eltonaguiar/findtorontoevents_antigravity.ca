# Strategy Proof Request — 2026-11-22

**Question asked:** do we have ANY strategy proven at least in backtest — and specifically
evidence on **VALUE** stocks and **stocks that continually beat earnings (PEAD)**?

**Answer in one line:** **No. Nothing here is proven even in backtest once deflation is
applied correctly** — including the one candidate that passed its own backtest — and for
VALUE specifically there is **no backtest at all**, only a document that calls it a proven
edge while containing zero measurements. PEAD has been backtested twice and failed both
ways (with the drift, and against it).

---

## 0. The trial count, because it drives everything below

`reports/hypothesis_registry.json` holds **146 unique pre-registered hypotheses** (158
`H-` records before de-duplication). [SRC: reports/hypothesis_registry.json, counted by
walking the tree for dicts whose `id` starts with `H-`]

Status distribution across those 146:

| status | n | | status | n |
|---|---|---|---|---|
| PRE_REGISTERED | 33 | | PAPER_PILOT | 7 |
| FORWARD_OBSERVATION | 19 | | FORWARD_SHADOW | 5 |
| REFUTED | 16 | | SHADOW_IMPLEMENTATION | 1 |
| REJECTED | 15 | | SHADOW_LIVE | 1 |
| UNTESTED | 15 | | TESTED_PASS_BACKTEST_FORWARD_PENDING | 1 |
| TESTED_KILL | 11 | | NEAR_ADMISSIBLE | 1 |
| (mixed/other spellings) | 22 | | | |

**Zero hypotheses sit at LIVE_TESTING, PROVEN, or PRODUCTION.** The highest tier anything
has reached is `PAPER_PILOT` (7 hypotheses, H-041…H-047), and those have no resolved
outcomes — the outcome resolver that would produce them shipped today
(`tools/provenance_resolver.py`, PR #1064).

So the honest denominator is **146 trials**, and any backtest in this repo must clear a
multiple-testing haircut for 146 trials, not 1.

---

## 1. Is anything proven at least in backtest? — one candidate, and it fails deflation

Exactly one hypothesis is recorded as **`TESTED_PASS_BACKTEST_FORWARD_PENDING`**:

### H-103 — `etf_dual_momentum_crossasset`

| field | value |
|---|---|
| **universe** | 6 cross-asset ETFs: SPY / QQQ / EFA / AGG / GLD vs BIL cash [SRC: registry H-103 `description`] |
| **rule** | trailing 12m absolute filter (must beat cash) + relative top-1, **monthly** rebalance, fixed textbook params, no fitting |
| **sample n** | ~48 months daily bars; purged-embargoed OOS **train n→test n=19** (below the 20 minimum it set for itself) |
| **gross / net** | PF **3.57**, Sharpe **1.62**, MDD **−12%**, WR **73%**; attribution vs SPY **alpha t=2.36**, IR 0.37, beta 0.34 → real alpha, not SPY beta; bootstrap PF 95% CI **[1.64, 9.69]**; **cost-robust to 20bp** |
| **OOS decay** | purged-embargoed CV: train PF 2.30 → test PF **5.37**, no decay (caveat: test n=19 < 20) |
| **trial count** | **146** (the registry) |
| **survives deflation?** | **NO** — see below |

This is genuinely the best-looking thing in the repo, and it is not a curve-fit: the
parameters are textbook, there is an alpha-vs-SPY attribution, a bootstrap CI, and an
out-of-sample CV that did not decay. It is a legitimate *backtest pass*. It is **not** a
proven edge, for two reasons.

**Reason 1 — four years of monthly data cannot establish a Sharpe of 1.62.**
48 monthly observations gives SE(SR) ≈ 0.171 in monthly units = **0.59 annualised**. A
recorded Sharpe of 1.62 is therefore ~2.7 standard errors from zero *before any deflation
haircut*. That is suggestive, not established.

**Reason 2 — under correct deflation it does not survive at any plausible setting.**
DSR = Φ((SR − E[max SR under N trials]) / SE(SR)), with N=146, T=48 monthly, SR_ann 1.62,
skew −0.5 / kurtosis 4.0 assumed (both unrecorded):

| SD(Sharpe across the 146 trials) | E[max] | **DSR** | verdict |
|---|---|---|---|
| 0.10 | 0.266 | **0.881** | FAIL |
| 0.20 | 0.532 | **0.353** | FAIL |
| 0.30 | 0.798 | **0.026** | FAIL |
| 0.40 | 1.064 | **0.0002** | FAIL |
| 0.50 | 1.330 | **0.0000** | FAIL |
| 1.00 | 2.661 | **0.0000** | FAIL |

**Breakeven is SD(Sharpe) ≈ 0.070.** H-103 survives deflation only if the 146 hypotheses
in this registry have a cross-trial Sharpe dispersion below 0.07. A registry spanning
crypto, forex, ETF, commodity, bond and prediction-market hypotheses at wildly different
sample sizes has dispersion far above that. At a conservative 0.30, **DSR = 0.026**.

> **So: H-103 passed its backtest and then failed deflation. That is the complete list of
> "proven at least in backtest" in this repo — one candidate, and it does not clear the
> multiple-testing gate.**

---

## 2. The deflation gate in this repo is broken — so "survives deflation" was never actually measured

`tools/deflated_sharpe_results.json` (generated 2026-06-06) reports
**29 of 45 strategies surviving = 64.4%**. That headline is not a deflation result. Four
defects, all verified in source:

**Defect 1 — `dsr` is a z-score, not a probability.** [SRC: tools/deflated_sharpe.py:82-86]

```python
def _deflated_sharpe(sr_obs, sr_star, se_sr):
    """DSR = (SR_observed - SR_haircut) / SE(SR)."""
    if se_sr < 1e-15:
        return 0.0
    return (sr_obs - sr_star) / se_sr        # <-- missing Φ(.)
```

The real Deflated Sharpe Ratio is `Φ(that whole expression)`. Without the normal CDF the
output is unbounded, and the shipped results range **[−23.88, +15.08]** — impossible for a
probability, which must lie in [0, 1]. A reader sees `dsr: 15.0783` and reasonably
concludes 1507%.

**Defect 2 — the pass gate is `dsr > 0`, which is a 50% significance level.**
[SRC: tools/deflated_sharpe.py:118] `z > 0` ⇔ one-sided p < 0.500. A 95% gate is
z > 1.645. Under the correct 95% threshold the survivor count is **28/45**, not 29/45 —
so the two thresholds happen to agree here, but only because the underlying z-scores are
inflated by Defect 3. The gate is calibrated by accident, not by construction.

**Defect 3 — a hardcoded 2190 trades/year inflates every Sharpe by 46.8×.**
[SRC: tools/deflated_sharpe.py:104; config `annual_trades: 2190`]
`sr_ann = sr_trade * sqrt(2190)` regardless of how often the strategy actually trades. A
strategy with 14 trades gets the same 46.80× annualisation multiplier as one with 1,900.
Result: the artifact reports annualised Sharpes of **43.93, 93.20**, and **15 of 45
strategies above 10**. Those are unit errors, not strategies.

**Defect 4 — unit mismatch in the standard error.** [SRC: tools/deflated_sharpe.py:105]
`_sharpe_se(sr_ann, skew, kurt, T)` passes an *annualised* Sharpe into a formula whose
`T` is a count of *trades*. The SE formula is defined per-period; mixing an annualised SR
with a per-trade T is dimensionally inconsistent.

**Consequence:** no candidate in this repo has been meaningfully deflated. "Does it survive
deflation?" has the answer **not determinable as recorded**, and the 64.4% figure should be
retired rather than cited. Fixing this is a prerequisite for ever promoting anything.

---

## 3. VALUE stocks — no backtest exists. The "proven" label is a document with zero measurements

### 3a. The claim, and why it cannot be used

`output/EDGE_VALIDATION_ANALYSIS.md` assigns VALUE (Fama-French HML) the verdict:

> **Verdict**: ✅ **GENUINE EDGE** - But currently experiencing longest drawdown in history

Its own header calls itself *"Brutally honest analysis of which strategies have genuine
edge vs. which are curve-fitted garbage"* and claims *"Only ~20% of the 635+ catalogued
strategies have genuine, durable edge."*

That document was generated **2026-02-17** and contains **zero** occurrences of `n=`, `sharpe`,
or `t-stat` anywhere in its 941 lines. [SRC: `grep -cE '\bn=[0-9]+|sharpe|t-stat'
output/EDGE_VALIDATION_ANALYSIS.md` → **0**]

It is a **literature-and-reasoning document**, not a validation. Its "GENUINE EDGE" badges
are prior beliefs dressed as verdicts. It predates the entire harness/verdict programme
(`reports/EDGE_VERDICT_2026-05-18.md`, `tools/edge_stability_harness.py`) and is
superseded by it. **It must not be cited as evidence that value works.**

### 3b. What VALUE infrastructure actually exists

`alpha_engine/value_screener.py` (29,402 bytes) is real and substantive — it computes
Piotroski F-score, Beneish M-score, debt-to-equity score, a value composite and a quality
composite. [SRC: functions `compute_piotroski_f_score`, `compute_beneish_m_score`,
`compute_value_composite`, `compute_quality_composite`]

But it is a **live screener, not a backtest**: there is no `slippage`, no `cost`, and no
net-of-cost return path in the file. It ranks names today; it does not tell you whether the
ranking made money.

### 3c. The realised record for value strategies is thin-to-negative

| candidate | universe | n | net-of-cost result | trial count | survives deflation? |
|---|---|---|---|---|---|
| `magic_formula_x_piotroski_x_acquirers` (ueps) | US equity value screen via SEC EDGAR + yfinance | **6** closed | WR 83.3%, PF 9.42, PnL +0.1314 | 146 | **N/A — n=6 is not a sample.** 5 wins; the 95% Wilson lower bound on 5/6 is ~0.44, and PF 9.42 on 6 trades is arithmetic, not evidence |
| `goldmine_stocks` | US equity fundamental | **270** closed | WR 50%, **PF 0.42**, PnL −4.6 | 146 | **NO — losing** |
| `Quality Compounders` | CRYPTO + EQUITY | 14 | WR 50%, PF 1.65 | 146 | NO — n=14, mixed asset classes |
| value composite / Piotroski screen | — | **0** backtested | **UNMEASURED** | — | **No backtest artifact exists** |

[SRC: `2026-11-14/finpredict-v2_20261114-1602/raw/per_strategy_agg.csv`;
`final_v2/finpredict-v3/2026-11-14T174500Z/ML_VALIDATION/README.md`]

That ML_VALIDATION README states the position plainly and correctly:

> "Fundamental/earnings stock picking: modules exist ... but have zero/failed realized
> evidence. … **No fundamental methodology is proven.**"

**VALUE bottom line: there is no value backtest in this repo. The single largest-sample
value-ish strategy (goldmine_stocks, n=270) loses money at PF 0.42. The only positive
value record is n=6.**

---

## 4. PEAD — backtested properly, twice, and it fails in both directions

This is the part of the answer I can be most confident about, because PEAD has been
pre-registered, tested with leakage controls, and gate-checked more carefully than anything
else here. Two independent tests, opposite signs, both fail.

### 4a. H-010 — EQUITY PEAD with the drift (SUE-driven) — **REJECTED**

| field | value |
|---|---|
| **universe** | 247 large-cap liquid US equities (S&P-100-style), price > $5 floor at entry — microcaps excluded structurally; 242 names had usable earnings history |
| **signal** | SUE = (actual − estimated EPS) / rolling std of the firm's **own past** surprises, needing ≥4 strictly-prior surprises before scoring (standardiser never peeks forward); act on \|SUE\| ≥ 0.5 |
| **sample n** | **6,988 earnings-event picks** |
| **entry / hold** | first bar **strictly after** the announcement; hold **30 trading days** |
| **cost** | **100 bp round-trip**, subtracted before WON/LOST resolution |
| **net result** | pooled OOS WR **52.7% net of 100bp**; harness **5 of 22 windows strong, signs split 3+/2−** |
| **trial count** | 146 |
| **survives deflation?** | **NO — struck down before deflation: `edge_stability_harness` REJECTED it (kill #6).** It never reached the deflation stage |

[SRC: `reports/h010_equity_pead_2026-05-18.md`; registry `H-010` → `"REJECTED - tested,
sign-unstable (regime noise)"`]

Note the shape of the failure: pooled 52.7% net WR looks like a small edge, but the
walk-forward effect sizes **change sign** across windows (−0.15, −0.52, −0.09, +0.25,
−0.15, +0.15, +0.25, +0.17, +0.01, +0.44, …). A pooled win rate over sign-unstable windows
is not an edge; it is an average of regime noise. The report's own conclusion: *"do NOT
re-test this signal family on this sample — archive it."*

### 4b. H-034 — anti-PEAD 1-day over-reaction reversal — **UNTESTED, and net-negative**

The deliberate mirror image: **fade** the earnings-day gap rather than ride the surprise.
Uses the price gap `close_d/close_{d−1} − 1` (not SUE), trades **against** the gap, holds
**1 day**, entering open d+1 and exiting close d+2. Tercile threshold uses only earnings
strictly before the event.

| field | value |
|---|---|
| **universe** | 50 large-caps with usable price + earnings history (AAPL…SBUX basket) |
| **sample n** | **1,985** earnings events; **709** qualifying strong-gap over-reaction events |
| **gross result** | **+22.15 bp/trade** (mean per-trade return 0.002215) |
| **cost** | **30 bp** round-trip |
| **net result** | **−7.85 bp/trade** (mean per-trade −0.000785) |
| **cost survival** | 92.1% of trades have \|gross\| > 30bp (gate ≥60%: PASS) |
| **trial count** | 146 |
| **survives deflation?** | **NO — and it does not even reach the deflation stage.** Harness verdict **UNTESTED: 0/0 scored windows** |

[SRC: `reports/h034_anti_pead_reversal_2026-05-19.md`]

**This is the cleanest illustration of the programme's central finding.** A gross edge of
**+22.15 bp** looks like a real anomaly and is exactly the order of magnitude the PEAD
literature would predict for a short-horizon reversal. Against **30 bp** of round-trip cost
it is **−7.85 bp net**. The edge exists; the cost is larger.

The report is also honest about *why* the verdict is UNTESTED rather than FAIL: with
quarterly events per name, even a 50-name basket yields too few 14-day windows to score the
harness. **The blocker is event density, not design.** So 709 trades of real signal sit
unscored — and net-negative.

### 4c. EQ-1 PEAD mid-cap (S1) — **FAIL**

| field | value |
|---|---|
| **universe** | **63 mid-caps** (GEN, JBL, MANH, WEX, ACIW, LSCC … FHB) |
| **sample n** | **216** trades from 216 events, 2020-01-01 → 2025-12-31 |
| **spec** | SUE ±2.5, hold 30 days, stop at CAR −5%, **30 bp round-trip**, entry next trading day **open** (conservative — FMP free-tier timestamp precision unverified, so same-day-close entry was rejected as look-ahead risk) |
| **result** | **FAIL.** IS Sharpe **−0.02**, WR **36.6%** (Wilson LB 0.304), OOS2 Sharpe **−0.28** < 0.7×IS |
| **mean / median per trade** | mean **+14.04 bp NET**, median **−5.47%**, stop-hit rate 56.5% |
| **gross / cost** | gross ≈ **+44.04 bp** − 30 bp RT = **+14.04 bp net** (verified: `pnl_net = final_pnl − 30/10_000`, and `mean_pnl = pnls.mean()` over `pnl_net`) |
| **trial count** | 146 |
| **survives deflation?** | **NO — failed its own S1 criteria outright** |

[SRC: `docs/backtests/EQ1_PEAD_S1_RESULTS.md`; `backtest_results/eq1_pead_S1.json`;
cost application verified at `tools/eq1_pead_backtest.py:371` (`pnl_net = final_pnl -
TXN_BPS_RT/10_000`) and `:421` (`pnls = df["pnl_net"]`) — so `mean_pnl` is already net.]

Worth reading the mean-vs-median split: mean **+14 bp net** but **median −5.47%**. The mean
is carried by a handful of large winners while the typical trade loses 5%. Win rate 36.6%
with a 56.5% stop-hit rate. That is a distribution you cannot size — which is precisely what
a negative Sharpe and negative median are telling you.

The yearly split makes the instability explicit [SRC: `backtest_results/eq1_pead_S1.json`
`yearly`]: mean net per trade **2020 −3.29%**, 2021 +0.97%, 2022 +3.43%, 2023 +3.24%,
**2024 −1.41%**, 2025 +0.20%; and across the sample partitions IS **−0.086%**, OOS1
**+2.28%**, OOS2 **−0.90%**. Positive in three years, negative in two, with the final
out-of-sample block negative. A strategy whose sign flips by calendar year is not a
strategy — and note this one *was* net-positive on average and was still correctly failed.

### 4d. H-002 PEAD shadow (pooled) — **UNTESTED**

n=**1,964** pooled, WR **53.2%**, status `SHADOW_IMPLEMENTATION`, harness verdict
**"UNTESTED (too few walk-forward windows, harness needs ≥3)"**. [SRC: registry `H-002`]
This is the largest PEAD sample in the repo and it still has no verdict. It is the natural
place to spend the next unit of effort — see §6.

### PEAD summary table

| candidate | universe | n | gross bp/trade | cost | **net bp/trade** | trial count | survives deflation? |
|---|---|---|---|---|---|---|---|
| H-010 SUE drift | 247 US large-caps | 6,988 | not reported | 100 bp RT | WR 52.7% net | 146 | **NO** — harness REJECTED first (3+/2− sign split) |
| H-034 anti-PEAD fade | 50 US large-caps | 709 (of 1,985) | **+22.15** | 30 bp RT | **−7.85** | 146 | **NO** — UNTESTED (0/0 windows) and net-negative |
| EQ-1 PEAD mid-cap | 63 mid-caps | 216 | **+44.04** | 30 bp RT | **+14.04** (median **−5.47%**) | 146 | **NO** — failed S1: IS Sharpe −0.02, WR 36.6% |
| H-002 PEAD shadow | undisclosed pool | 1,964 | not reported | not reported | WR 53.2% | 146 | **NO** — UNTESTED (needs ≥3 windows) |

---

## 5. Everything else worth naming, for completeness

| candidate | class | universe | n | gross → net bp/trade | trial count | survives deflation? |
|---|---|---|---|---|---|---|
| **H-103** dual momentum | ETF | 6 cross-asset ETFs | 48 mo (OOS n=19) | PF 3.57 / Sharpe 1.62 / alpha t=2.36 | 146 | **NO — DSR 0.026 @ SD 0.30** (breakeven SD 0.070) |
| H-004 inventory×roll-yield | COMMODITY | futures curve | 3,722 | **+22.07 → +8.07** | 146 | **NO** — HARNESS_REJECTED, 0/18 windows, cost survival 36.56% |
| H-037 VIX term-structure carry | ETF | 11 SPDR sectors + ^VIX | 1,185 | WR 58.9%, PF 1.295, WF eff 0.75 | 146 | **NO** — status `TESTED_WEAK` |
| H-003 XS momentum | ETF | 20 ETFs (own criterion: ≥30/leg) | — | Sharpe threshold 0.7 | 146 | **NO** — `SHADOW_LIVE`, and violates its own `min_etfs_per_leg: 30` |
| H-120 daily-resolution inflation | MULTI | non-crypto + FX | 135 / 120 | daily PF 2.67 → honest **1.28**; 1.26 → **1.07** | 146 | N/A — this one is a *method-defect* result (SUPPORTED), not a strategy |
| H-021 COT small-spec exhaustion | COMMODITY | CFTC COT futures | 2 of 3 windows | eff_z 1.51 / 1.25, same sign | 146 | **NO** — `NEAR_ADMISSIBLE`, killed on data volume (`DATA_VOLUME_ARTIFACT`) |

Note H-004: **+22.07 bp gross → +8.07 bp net is still positive**, and it was still rejected —
not for weak economics but because the effect was unstable across 0 of 18 windows. Net
positivity without stability is not a tradeable edge; it is a number that might not repeat.

Note H-120: the most useful result in the registry is not a strategy at all. It proves that
**daily-resolved PnL inflates profit factor by ~2.1×** versus honest first-touch resolution.
Every backtest in this document that reports a PF should be read against that finding.

---

## 6. What this means, and the highest-value next step

**Direct answers:**

1. **Any strategy proven at least in backtest?** One candidate passed its backtest —
   H-103 dual momentum (PF 3.57, alpha t=2.36 vs SPY, cost-robust to 20bp, no OOS decay).
   It **fails correct deflation (DSR 0.026)**, and 48 monthly observations cannot establish
   a Sharpe of 1.62 in the first place. **So: no.**
2. **VALUE?** **No backtest exists.** The only "GENUINE EDGE" label comes from a 2026-02-17
   document with zero measurements. The largest value sample (n=270) loses at PF 0.42. The
   only positive value record is **n=6**.
3. **PEAD?** Better tested than anything else here, and it fails in **both** directions:
   with the drift (H-010, 6,988 events, harness REJECTED on sign instability) and against
   it (H-034, 709 events, **+22.15 bp gross → −7.85 bp net**). The pattern repeats the
   programme's central finding: **gross edge ≈ round-trip cost.**
4. **Survives deflation?** **Nothing does** — and the repo's deflation tool is itself
   miscalibrated in four ways, so this question has never actually been answered by
   machinery. The 64.4% survivor headline should be retired.

**The highest-value next step is not another strategy.** It is `H-002` (n=1,964, packaged,
pre-registered, already collecting): it needs **event density**, not new design. Two
concrete options: (a) widen the basket so ≥3 harness windows populate, or (b) replace the
14-day window with an event-count-based window so quarterly-density signals can be scored
at all. Until the harness can score a quarterly-event strategy, **every PEAD variant will
keep returning UNTESTED regardless of whether the edge is real** — which is a measurement
failure masquerading as a null result.

Second: **fix `tools/deflated_sharpe.py`** (apply `Φ(·)`, replace the hardcoded
`ANNUAL_TRADES` with the observed trade rate, fix the SE unit mismatch, and require an
explicit measured `Var(SR_trials)`). Without it, no future candidate can be deflated, and
the promotion gate has no top to it.

---

## 7. Standing constraints on everything above

- Zero capital is sanctioned. Nothing here is investment advice.
- Every figure above is sourced from a named file; nothing is extrapolated or filled in.
  Where a quantity is not recorded (H-103/PEAD skew and kurtosis, cross-trial Sharpe
  dispersion, several gross bp/trade columns), it is labelled **not reported** /
  **UNMEASURED** rather than estimated silently.
- `gross` and `net` are reported together throughout; a gross number alone is not a result.
- Sample sizes below ~100 are flagged as not evidence, not ranked.
- The two candidates closest to promotable (H-103, H-020/H-002) have **no forward record**
  — the outcome resolver that would create one shipped 2026-11-22.

---

**Provenance:** every number in this document traces to a repository file named inline in a
`[SRC: …]` marker or in the table's source footnote. Cross-trial counts come from
`reports/hypothesis_registry.json` (146 unique pre-registered hypotheses). Deflation numbers
are computed from `tools/deflated_sharpe.py` source and `tools/deflated_sharpe_results.json`
with the correct `Φ(·)` applied offline; the shipped tool does not apply it. Where a figure
is not present in any file it is marked UNMEASURED and no value is invented.
