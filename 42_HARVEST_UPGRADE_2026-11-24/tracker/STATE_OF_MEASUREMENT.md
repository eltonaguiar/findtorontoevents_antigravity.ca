# State of measurement: what the programme cannot answer yet

Written 2026-11-25T15:50Z. Five questions the programme cannot currently answer, plus a short
note on options and futures.

**How to read this.** Each section has three parts: the answer *if fully measured*, why the data
cannot support it now, and a **Predictability** paragraph labelled **JUDGEMENT**. Only numbers
tagged `[SRC: …]` were re-read from an artifact on `origin/main` in this session. Numbers tagged
`[FROM BRIEF]` come from the task statement and were not independently re-derived here. Nothing
in a Predictability paragraph is a measured result; those are reasoned estimates.

---

## 1. Is any asset class profitable?

**The answer if fully measured.** A per-class verdict: for each of the twelve classes, net
expectancy after cost with a 95% CI, and whether that CI clears zero and a 4.32% T-bill. Today
four classes have a money-ready verdict of `NOT_READY` and seven are `INSUFFICIENT_DATA`, so the
honest fully-measured answer would most likely be "no class clears the hurdle, and here is the CI
that says so for each".

**Why the data cannot support it now.** The scored population is badly unbalanced. The audit3
ledger scores 8,991 rows, of which CRYPTO is 7,041 (78.3%): CRYPTO 7041, EQUITY 961, ETF 593,
FOREX 298, COMMODITY 55, BOND 37, FUTURES 6 [SRC: `audit_dashboard/data/audit3_ledger.json`
`classes[].n`]. The brief states one class holds 95.5% of live-resolver rows [FROM BRIEF]; that is a
different denominator from the ledger's 78.3%, and both say the same thing: the sample is one
class. The per-class minimum-detectable-effect already computed in the ledger shows the small
classes cannot resolve anything: COMMODITY `mde_pct` 1.9303 and FUTURES 8.7582 against CRYPTO
0.1515 [SRC: `audit3_ledger.json` `classes[].mde_pct`]. The money-ready gate confirms there is no
ready class: 0 READY verdicts across 190 archived days, latest file 4 `NOT_READY` / 7
`INSUFFICIENT_DATA` [SRC: `audit_dashboard/data/money_ready_archive/`]. The cost gate already fails
for CRYPTO at PF 0.2617 on n 3733 [SRC: `money_ready_archive/money_ready_2026-11-25.json`].

**Predictability.** JUDGEMENT. Low for anything but CRYPTO, and low even there. If I had to bet on
the fully-measured answer: no class is profitable after cost, CRYPTO stays clearly negative (its PF
is far below 1 on the largest sample), and the small classes land as "unknown", not "profitable",
because their MDE is larger than any plausible edge. I would expect EQUITY and ETF to be the only
ones with a chance of a positive but sub-hurdle mean. This is a guess from the direction of the
numbers, not a measurement.

---

## 2. Do analyst rating changes predict returns?

**The answer if fully measured.** A per-event excess return with a CI, and a yes/no on whether the
mean is distinguishable from zero. If the true effect is small, the answer might honestly be "a
positive point estimate we cannot distinguish from zero".

**Why the data cannot support it now.** The 63-day test interval includes zero, so the effect is
not separated from noise [FROM BRIEF]. The power of the test is the binding limit. The programme's
own power note gives the formula and the numbers: MDE on the daily mean at 95% confidence / 80%
power is `2.8016 × σ_daily / √n_days`, e.g. CRYPTO MDE 11.48 bp/day at σ≈43%, EQUITY 7.17,
ETF 4.86 [SRC: `reports/2026-11-22-cost-floor-and-power.md:30-41`]. At that sensitivity, only effects
larger than the MDE become detectable; a rating-change edge of a few bp is under it.

**Predictability.** JUDGEMENT. Whatever the point estimate, it will stay inside the interval until
either n grows or the noise falls. With the MDE as computed, the smallest effect this data could
reliably detect is on the order of the MDE above (roughly 5–12 bp/day depending on class). A genuine
rating-change edge is more likely smaller than that, so my expectation is "still inconclusive even
after more data, unless events are pooled across firms and years". I would predict a positive but
non-significant point estimate, and I would not trust a significant one from this design without a
pre-registered multiplicity correction.

---

## 3. Does entry timing drive the bucket means?

**The answer if fully measured.** A decomposition of each bucket's mean into "which months you
entered" versus "which names you held", with event-level intervals. It would say whether a
bucket's headline mean is an entry-timing artifact or a real per-name effect.

**Why the data cannot support it now.** Only two monthly cohorts exist [FROM BRIEF]. With two
cohorts you cannot separate month effects from name effects; the event-level intervals are too
narrow by an unknown factor because events inside a cohort are not independent.

**Predictability.** JUDGEMENT. To estimate month effects with any stability you want enough
cohorts that the within-month correlation is estimable: on the order of a dozen or more monthly
cohorts, i.e. a year or more of entries, is the usual rule of thumb; two is nowhere near it. My
prediction is that once enough cohorts exist, entry timing will explain a meaningful but minority
share of the bucket means, and the per-name effect will dominate. That is an expectation, not a
finding, and the current two-cohort data cannot even rank those two explanations.

---

## 4. Does Track A firm skill exist?

**The answer if fully measured.** For each tracked firm, a skill estimate with a CI, and a
programme-level verdict on whether any firm's edge is distinguishable from zero after multiple-testing.

**Why the data cannot support it now.** No firm reaches the 750 clean-event floor; the maximum is
439 [FROM BRIEF]. At 439 the per-firm CI is wide, and with many firms tested the multiplicity
penalty is heavy, so even the best firm's point estimate is not separable from luck.

**Predictability.** JUDGEMENT. With a 750-event floor and a best firm at 439, the best firm is at
roughly 59% of the required sample (439/750), so its interval is about 1.3× wider than the floor
would give (√(750/439) ≈ 1.31). My expectation: the leading firm's estimate will regress toward
the pool mean as events accumulate, and "firm skill" will most likely end up unproven rather than
proven. If a real edge exists it is more likely to show up as a small persistent difference than
as one standout firm. All of this is judgement.

---

## 5. Does backfill versus live performance differ?

**The answer if fully measured.** Two net-expectancy estimates, backfilled vs live, with a CI on
their difference. It would tell whether a backfilled row is an unbiased proxy for a live one.

**Why the data cannot support it now.** Backfill is perfectly confounded with label case: the
backfilled cohort and the live cohort are produced by different pipelines, so any difference is
attributable to the pipeline, not to backfill per se. The repo already documents that a PF is
meaningless without naming which population it came from, and that a 2026-06-04 backfill of 5,960
commodity rows is hard-excluded for this reason [SRC:
`docs/audit_review_2026-11-22/METRIC_DEFINITIONS.md:135-138`]. The forward ledger also quarantines
backfilled rows: H-119 has 430 ledger rows "all backfilled and quarantined" [SRC:
`docs/edge_research/25_DRAFT_RANKED_LIST_2026-11-23.md:116`].

**Predictability.** JUDGEMENT. Because the confound is structural, my prediction is that backfilled rows will look better than live rows (survivorship and look-ahead in how they were selected), and that no amount of the current data will separate "backfill is optimistic" from "the backfill pipeline is different". Answering it needs the same rows through both pipelines, which does not exist. I would treat any backfilled performance figure as an upper bound on live performance until then.

---

## Options and futures

**Options are forward-only.** A live Yahoo options chain works today (full strikes, bid, ask,
volume, open interest, implied volatility; SPY returns 30 expiries) [FROM BRIEF], but a historical
option contract returns zero bars, so no historical option price exists from that source. That
makes options performance **not measurable retroactively**: you can only measure it forward, by
recording chains as they arrive. Note also that `lm_bridge_options` holds only 12 rows of
`net_gex` and `pc_oi_ratio` aggregates with no strikes [FROM BRIEF], so it is not a price history
either.

**Futures are measurable now.** ES=F provides 6,613 daily bars since 2000-09-18 [FROM BRIEF], which
is enough to measure. Two caveats travel with it: the continuous series has **unmodelled roll gaps**
(a front-month splice jumps at each roll), and there is **no contract-level data**, so you cannot
study individual expiries or their spreads. The repo's own edge-research notes make the same point
about roll corruption for commodity series (a −37.63 print and a recurring −23.6% print are not a
price history) [SRC: `docs/edge_research/22_FINAL_SYNTHESIS_2026-11-22.md:61`]. In this checkout the
local ES caches start later than 2000 (2012-01-03 in `data/research_cache/ES_F.csv`, 2021-11-22 in
`data/cache/asset_class_review/ES_F_5y.csv`, neither on `origin/main`), so I did not independently
confirm the 6,613 / 2000-09-18 figure here; I record it as stated.

**Verdict:** OPTIONS = FORWARD-ONLY · FUTURES = MEASURABLE-NOW (with roll-gap and contract-level caveats).
