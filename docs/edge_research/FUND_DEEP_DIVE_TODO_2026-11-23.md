# Fund deep-dive — remediation & research plan (173 items)

**Date:** 2026-11-23
**Scope:** `tools/fund_deep_dive.py`, `reports/fund_deep_dive.json`, `docs/edge_research/FUNDS_WHAT_TO_BUY_2026-11-23.md`
**Branch:** `feat/fund-deep-dive-fixes-2026-11-23` (branched from `5660b25cb51`, Kilo's analysis; his branch is untouched)
**Status legend:** `[ ]` todo · `[x]` done · `[~]` deferred with reason · `[!]` needs operator decision

> **Paper only. Not investment advice.** Everything here is measurement, not a recommendation.
> `/db-schema`, `/hypothesis-registry` rules apply where a claim becomes an edge claim; this is a
> beta/buying study, so M-107 pre-registration is **not** triggered — but B-block still applies
> because rankings are claims.

## Provenance of this list

Derived from a peer review (subq) plus my own verification of the artifact. **Four of the twelve
review items were factually wrong** (numbers 4, 8, 10, 12 below are marked `REFUTED` with evidence),
and four defects the reviewer missed were added (A5, A6, A7, I3). Nothing here was accepted on
assertion: every "confirmed" item was checked against the code or re-run.

---

## A. Metric correctness (the numbers are wrong today)

- [ ] **A1** — Compute Sharpe as `(R_p − R_f)/σ_p` with SGOV net return as `R_f`. Today it is a fee-adjusted return/vol ratio. *Done when:* true and raw Sharpe both printed and labelled.
- [ ] **A2** — Same for Sortino: `(R_p − R_f)/σ_down`. *Done when:* both variants reported.
- [ ] **A3** — Relabel the column. A ratio called "Sharpe" that isn't Sharpe is a representation lying about truth. *Done when:* headers read `ret/vol` for the unadjusted variant.
- [ ] **A4** — SGOV Sharpe must not print unqualified. *Done when:* JSON and console both emit `null`/`"n/a (cash)"` rather than `15.886`.
- [ ] **A5** — **Fix the Sortino denominator.** `dsd = sqrt(Σ min(0,r)² / len(downside))` divides by the count of *negative* days; standard downside deviation divides by **all N**. This inflates σ_down and understates every Sortino — a bug independent of A2. *Done when:* both conventions implemented, difference documented.
- [ ] **A6** — `net_cagr = cagr − mer` is additive. Exact is `(1+cagr)(1−mer)−1`. *Done when:* compounded form used; delta reported (≈ cagr·mer).
- [ ] **A7** — `st.pstdev` (population) → sample stdev (`st.stdev`). *Done when:* vol recomputed; delta at n=1254 quantified.
- [ ] **A8** — CAGR should be geometric, not `prod(1+r)^(252/n) − 1` on daily returns with gaps. Verify the series has no zero/duplicate dates before trusting the exponent. *Done when:* date-gap audit printed.
- [ ] **A9** — Max drawdown is computed on the daily-return chain, not on the price series. For buy-and-hold that is correct, but confirm no dividend-reinvestment drift vs adjusted close. *Done when:* reconstructed NAV matches first/last adjusted close within 1e-6.
- [ ] **A10** — Define and report Calmar (`CAGR/|MDD|`) and ulcer index; drawdown depth alone is not a risk summary. *Done when:* both in JSON.
- [ ] **A11** — Report rolling 1y worst/best and % of positive years, not just endpoint CAGR. *Done when:* distribution stats emitted.
- [ ] **A12** — Assert every metric against an independent recomputation (numpy/pandas) in CI. *Done when:* `tests/test_fund_metrics.py` cross-checks to 1e-9.

## B. Statistical rigor — every number needs an interval

- [ ] **B1** — Moving-block bootstrap (block ≈ 21 days, 2,000 draws, seed fixed) for CAGR. *Done when:* 5th–95th percentile printed per fund.
- [ ] **B2** — Bootstrap vol and max drawdown on the same resamples. *Done when:* CIs in JSON.
- [ ] **B3** — Bootstrap the **FXAIX − SPY difference** directly, not each series separately — the paired/differenced interval is the correct test. *Done when:* CI on the gap reported.
- [ ] **B4** — State explicitly that overlapping CIs ⇒ no ranking. *Done when:* the doc stops ranking funds whose intervals overlap.
- [ ] **B5** — Block length sensitivity: 5/21/63 days. *Done when:* table shows the estimate is not block-length artefactual.
- [ ] **B6** — Effective sample size: autocorrelation of daily returns, Newey–West-adjusted standard errors. *Done when:* AC(1) and adj. SE reported.
- [ ] **B7** — t-test / bootstrap p-value on the FXAIX−SPY mean daily difference. *Done when:* p-value printed.
- [ ] **B8** — Multiple-comparison correction (Holm/BH) across the 7 funds and 5 portfolios. *Done when:* adjusted p-values reported.
- [ ] **B9** — Split the window: 2021-11→2024-11 and 2024-11→2026-11, both reported. *Done when:* two-column table exists.
- [ ] **B10** — Identify the dominant regime in each half (bull / drawdown / recovery) and label it. *Done when:* regime tag per sub-period.
- [ ] **B11** — Rolling 12-month CAGR chart/stats to show the endpoint is not cherry-picked. *Done when:* min/median/max rolling 1y emitted.
- [ ] **B12** — Report the number of independent *drawdown episodes*, not just the max. *Done when:* episode count + durations in JSON.
- [ ] **B13** — Sensitivity to start date: shift the start by ±1, ±3, ±6 months. *Done when:* CAGR range across starts printed.
- [ ] **B14** — State the detection floor: with n≈1,254 and σ≈17%, what annual excess is distinguishable from zero? *Done when:* the MD quotes the floor rather than implying precision.

## C. Data quality & provenance

- [ ] **C1** — Verify `market_prices.csv` provenance: who generated it, from what source, on what date. *Done when:* a `SOURCE` block exists in the doc and JSON.
- [ ] **C2** — Confirm adjusted-close semantics: are dividends reinvested, or prices merely split-adjusted? This silently changes every return. *Done when:* documented with evidence.
- [ ] **C3** — Check for survivorship bias — all 7 funds still exist; the universe was chosen knowing they survived. *Done when:* stated as a limitation.
- [ ] **C4** — Check date alignment across funds: any fund with a shorter series silently truncates the others via `n=min(...)` in `portfolio()`. *Done when:* per-fund first/last date printed.
- [ ] **C5** — Detect and handle stale/repeated closes (holiday carry-forward inflates vol-at-zero). *Done when:* duplicate-print days counted.
- [ ] **C6** — Assert no zero or negative prices (log-return safety). *Done when:* assertion in loader.
- [ ] **C7** — Verify 1,254 rows against trading-day count for the period (should be ≈1,255). *Done when:* gap list printed.
- [ ] **C8** — Cross-check 3–5 spot returns against an independent source. *Done when:* discrepancies < 1bp.
- [ ] **C9** — Record a data hash in the JSON so a later run is provably the same input. *Done when:* sha256 of CSV in output.
- [ ] **C10** — Confirm MER values against issuer prospectuses (SPY 0.0945%, FXAIX 0.015%, FZROX 0.00%, VTSAX 0.04%, VTI 0.03%, BND 0.03%, SGOV 0.09%). *Done when:* each cited.
- [ ] **C11** — Note that FZROX has no ETF twin and Fidelity ZERO funds are non-portable (can't transfer in kind). *Done when:* in decision table.
- [ ] **C12** — Flag that 2021-11-15→2026-11-13 is a **bull-heavy** window; disclose the selection. *Done when:* header states it (already partly true).

## D. Portfolio construction & costs

- [ ] **D1** — **Implement real rebalancing.** `portfolio()` accepts `rebal=21` and ignores it; `port[i]=Σw·r_i` is *daily* rebalanced. *Done when:* `--rebal` actually rebalances on a schedule.
- [ ] **D2** — Compare daily vs monthly vs quarterly vs buy-and-hold. The spread is the volatility-harvesting effect. *Done when:* 4-row comparison table.
- [ ] **D3** — Quantify rebalancing turnover and cost (spread + commission) per schedule. *Done when:* cost-adjusted CAGR per schedule.
- [ ] **D4** — Model bid-ask spread per vehicle (SPY/VTI/BND ~1bp; MFs at NAV 0bp; SGOV ~1bp). *Done when:* net-of-spread CAGR.
- [ ] **D5** — Add a cash sleeve with realistic T-bill yield rather than SGOV-only. *Done when:* cash return is explicit.
- [ ] **D6** — Test 90/10, 70/30, 50/50, 40/60 as well as 60/40 and 80/20. *Done when:* glide-path table.
- [ ] **D7** — Compute the efficient frontier (or at least the min-variance mix) for SPY/BND. *Done when:* mix + expected return/vol printed.
- [ ] **D8** — Report the **dispersion** of outcomes, not one path: with monthly rebalancing the path is single, so bootstrap it too. *Done when:* CI per portfolio.
- [ ] **D9** — Model contribution flows (DCA), since retail buys monthly — lump-sum vs DCA materially changes the -24.5% DD experience. *Done when:* DCA variant reported.
- [ ] **D10** — Compute drawdown in *money* terms for a stated account size ($10k/$100k), not just %. *Done when:* $ table.
- [ ] **D11** — Time-to-recovery after the max drawdown for each vehicle. *Done when:* days-to-recover column.
- [ ] **D12** — Sequence-of-returns risk note (matters if decumulating). *Done when:* stated.
- [ ] **D13** — Blended-MER arithmetic is recomputed but never charged as a drag in `portfolio()` — verify. *Done when:* confirmed applied once, not twice.
- [ ] **D14** — Fee drag recomputation: `+$75 / $200 / $472` per $100k over 5y must be re-derived from the compounded net CAGRs. *Done when:* numbers recompute in the script.

## E. Tax & account structure

- [ ] **E1** — Note that the MD **already** covers capital-gains distributions (review item 8 was wrong) — extend rather than duplicate. *Done when:* section expanded, not restated.
- [ ] **E2** — Model a plausible tax drag: assume 0.3%/yr distribution for VTSAX vs ~0 for VTI in a taxable account. *Done when:* taxable-vs-registered CAGR comparison.
- [ ] **E3** — State the assumed marginal rate and jurisdiction (Ontario, ~43% combined for the relevant bracket) — or mark it as unmodelled. *Done when:* explicit.
- [ ] **E4** — Clarify Canadian vs US account wrapper naming (TFSA/RRSP vs Roth/IRA) — the doc mixes them. *Done when:* consistent terminology.
- [ ] **E5** — Note FX-hedging/unhedged exposure for a CAD investor holding USD funds. *Done when:* FX caveat added.
- [ ] **E6** — Note withholding tax on US-domiciled ETFs in a Canadian registered account. *Done when:* flagged.
- [ ] **E7** — Confirm FZROX is US-only (Fidelity US) and unavailable to Canadian residents. *Done when:* availability column.
- [ ] **E8** — Note the 30-day wash-sale / superficial-loss rules differ by jurisdiction. *Done when:* caveat.
- [ ] **E9** — Add tax-lot / ACB tracking note. *Done when:* stated.
- [ ] **E10** — Recommend the account wrapper decision *before* the MF-vs-ETF decision (the ordering is currently backwards). *Done when:* doc restructured.

## F. Forward-looking anchors (trailing CAGR is a bad forecast)

- [ ] **F1** — Use current T-bill yield as the cash expectation, not the trailing SGOV CAGR. *Done when:* anchored number with date + source.
- [ ] **F2** — Use BND's current **yield-to-maturity** as its forward expectation, not −0.29% trailing. *Done when:* YTM quoted.
- [ ] **F3** — Add an earnings-yield or CAPE-style note for equity forward expectations. *Done when:* anchor quoted with source + date.
- [ ] **F4** — State clearly that a 5y trailing CAGR is not a forecast input. *Done when:* disclaimer present.
- [ ] **F5** — Provide a forward return decomposition: dividend yield + earnings growth + valuation change. *Done when:* three-component estimate.
- [ ] **F6** — Show that the *ranking* of SPY vs VTI is regime-stable even if the *level* is not. *Done when:* sub-period ranking table.
- [ ] **F7** — Record the anchor-fetch date and make stale anchors fail loudly. *Done when:* TTL check in script.
- [ ] **F8** — Do not present any forward figure without an interval. *Done when:* intervals attached.
- [ ] **F9** — Note inflation: real vs nominal returns. *Done when:* both reported.
- [ ] **F10** — Note that the cash hurdle changes the entire Sharpe ranking; show the ranking at two different `R_f` levels. *Done when:* sensitivity table.

## G. Futures & asset-class coverage

- [ ] **G1** — **Scope futures explicitly.** The user asked for them; the analysis silently omits them. *Done when:* the doc has a one-paragraph "out of scope: requires contract-level data" or a real section.
- [ ] **G2** — Document why adjusted closes are invalid for futures: front-month contracts expire; a continuous series embeds roll assumptions. *Done when:* written.
- [ ] **G3** — If in scope: obtain front-month settlement prices + roll dates. *Done when:* data source identified or declined.
- [ ] **G4** — Compute roll yield and identify contango/backwardation per contract. *Done when:* roll yield series exists.
- [ ] **G5** — Model margin, financing, and the leverage ratio honestly. *Done when:* described.
- [ ] **G6** — Compare futures vs ETF replication of the same exposure (e.g. ES vs SPY) net of roll + financing. *Done when:* comparison table.
- [ ] **G7** — Note tax treatment (60/40 in the US) if in scope. *Done when:* flagged.
- [ ] **G8** — State that futures are inappropriate for the retail "what should I buy" question unless explicitly wanted. *Done when:* said.

## H. Decision support & output shape

- [ ] **H1** — Emit a decision table: vehicle type, MER, minimum, tax efficiency, fractional shares, best fit. *Done when:* table renders.
- [ ] **H2** — Make the recommendation **account-aware** (taxable vs registered) as the primary branch. *Done when:* two-column "what to buy".
- [ ] **H3** — Add an explicit "if you cannot tolerate −25%, do X" risk-tolerance branch. *Done when:* decision tree present.
- [ ] **H4** — Quantify the cost of the 60/40 choice: 7.05% vs 11.59% CAGR over 5y ≈ 4.5pp/yr forgone — state it in dollars. *Done when:* $ impact shown.
- [ ] **H5** — Add a "what would change this answer" section. *Done when:* falsifiers listed.
- [ ] **H6** — Remove or explicitly subordinate the "clear what-to-buy answer" framing in the commit/report title — it overclaims. *Done when:* framing corrected.
- [ ] **H7** — Separate "measured" from "judgement" with visually distinct sections. *Done when:* structure reflects it.
- [ ] **H8** — Machine-readable JSON schema for the report, versioned. *Done when:* `schema_version` in JSON.
- [ ] **H9** — Include a `caveats` array in the JSON so consumers see limits programmatically. *Done when:* field exists.
- [ ] **H10** — Ensure the console table is readable at 80 cols (current fixed-width overflows). *Done when:* output wraps cleanly.

## I. Testing & engineering

- [ ] **I1** — `tests/test_fund_metrics.py`: unit tests for Sharpe/Sortino/CAGR/MDD with hand-computed fixtures. *Done when:* tests pass and are in the gating suite.
- [ ] **I2** — Property test: portfolio weights summing to 1.0 reconstruct the single fund when weight=1.0. *Done when:* test passes.
- [ ] **I3** — Remove the `__import__("datetime").UTC` dependency (Python ≥3.11 only, undocumented). *Done when:* `timezone.utc` used or dependency documented.
- [ ] **I4** — Make `SRC` path resolution repo-relative, not cwd-relative. *Done when:* script runs from any cwd.
- [ ] **I5** — Handle the `_adj` suffix fragility: derive columns from data, don't hardcode `MER` keys. *Done when:* unknown column raises a clear error.
- [ ] **I6** — Add `--rebal`, `--rf`, `--bootstrap-n`, `--seed`, `--period` CLI flags. *Done when:* flags documented in `--help`.
- [ ] **I7** — Add `--out` so the JSON path is not hardcoded. *Done when:* flag exists.
- [ ] **I8** — Fail loudly if the CSV is missing rather than raising a bare traceback. *Done when:* clean error message.
- [ ] **I9** — Emit a machine-readable `warnings` list for every degraded assumption (no dividends, short series, etc.). *Done when:* populated.
- [ ] **I10** — Add the script to CI so the numbers can't silently rot. *Done when:* a workflow runs it and diffs the JSON.
- [ ] **I11** — Verify the script runs on Python 3.11 **and** 3.12 (matches the CI matrix). *Done when:* both green.
- [ ] **I12** — Add type hints and a `--self-check` mode. *Done when:* `mypy`/`py_compile` clean.

## J. Peer review & adversarial checks

- [ ] **J1** — Run `/consult-multi` fan-out on the **revised** metrics and ask specifically: "is this Sharpe definitionally correct?" *Done when:* ≥3 independent model replies recorded.
- [ ] **J2** — Ask a second engine to red-team the bootstrap (block length, paired-vs-unpaired, stationarity). *Done when:* critique recorded and addressed.
- [ ] **J3** — Send the corrected FXAIX/SPY arithmetic to subq's author for re-check, since its unit error drove a false "over-predicts" claim. *Done when:* round-trip documented.
- [ ] **J4** — Adversarial test: replace SGOV with a synthetic constant 4% series — does any metric change in a way that proves `R_f` is (not) wired? *Done when:* test exists.
- [ ] **J5** — Re-derive every headline number by hand in a notebook and diff against JSON. *Done when:* all match.
- [ ] **J6** — Have an independent agent recompute CAGR from the CSV without reading the script; compare. *Done when:* agreement documented.
- [ ] **J7** — Review the corrected doc for remaining overclaims (grep for "clear", "proven", "guaranteed"). *Done when:* each is either evidenced or removed.
- [ ] **J8** — Ask two models to independently answer "what should I buy" from the corrected doc only; if they diverge wildly, the doc is ambiguous. *Done when:* divergence assessed.
- [ ] **J9** — Record the peer-review transcripts under `reports/` with hashes. *Done when:* archived.
- [ ] **J10** — Re-run the whole review suite after fixes and confirm the previously-wrong claims (4, 8, 10, 12) are now marked refuted in the doc. *Done when:* errata section exists.

## K. Documentation & repo hygiene

- [ ] **K1** — Add an **errata** section to the MD listing the four refuted review claims with evidence. *Done when:* published.
- [ ] **K2** — Commit the fixes on `feat/fund-deep-dive-fixes-2026-11-23`, not on Kilo's branch. *Done when:* branch pushed, Kilo's untouched.
- [ ] **K3** — Update `reports/fund_deep_dive.json` with the corrected numbers and a `supersedes` field. *Done when:* JSON regenerated.
- [ ] **K4** — Add the corrected numbers to the `updates/` card per repo convention. *Done when:* `updates/2026-11-23-*.md` exists.
- [ ] **K5** — Cross-link from `docs/edge_research/` index if one exists. *Done when:* linked.
- [ ] **K6** — Record the data hash + script version in the doc so the result is reproducible. *Done when:* both present.
- [ ] **K7** — State the exact reproduce command in the doc. *Done when:* one-liner present.
- [ ] **K8** — Do **not** merge or push to `main`; leave the PR/branch for operator review. *Done when:* confirmed.

---

## Execution order (my recommendation)

1. **A5, A1, A2, A6, A7** — the metrics are wrong; nothing else matters until they are right. (one block)
2. **A3, A4, I1** — labelling + tests so the fix is locked in. (one block)
3. **D1, D2, D3** — real rebalancing; the 60/40 number is currently mislabelled. (one block)
4. **B1–B4, B9** — bootstrap + sub-periods; stop ranking overlapping intervals. (one block)
5. **F1–F3** — forward anchors, so the doc stops implying the past predicts the future.
6. **G1, H1, H2, E10** — scope futures out, restructure the decision output.
7. **J1–J5** — peer review the corrected numbers before publishing.
8. **K1–K7** — errata, docs, updates card.

Deferred pending operator decision: **E3/E4/E5/E6** (jurisdiction), **G3–G7** (futures data acquisition — needs contract-level feed).

---

# Part II — Research, peer review, acceptance, operations

Added 2026-11-23 after block A landed. Part I is "fix what is wrong"; Part II is
"establish what we do not yet know". Nothing in L is answerable by editing code —
each needs evidence gathered from outside this repo.

## L. Open research questions (17)

- [ ] **L1** — Does adjusted-close data from this CSV actually reinvest dividends, or is it split-adjusted only? *Why it matters:* if not reinvested, every CAGR here understates total return by ~1.3%/yr for equity and the whole comparison shifts. *Method:* reconstruct SPY total return and compare to a known benchmark.
- [ ] **L2** — What is the achievable *net* return for a Canadian retail investor holding US-domiciled ETFs? Withholding tax, FX conversion cost, and MER together may exceed the fee gap that drives the recommendation. *Method:* model 15% WHT vs treaty rate; add 1.5% FX round-trip if applicable.
- [ ] **L3** — Is the FXAIX − SPY gap explainable entirely by fee + dividend-timing, or is there a tracking-error component? *Method:* decompose into fee, dividend timing, and residual tracking error; test whether residual is distinguishable from zero.
- [ ] **L4** — What is the true forward equity risk premium today? *Method:* earnings yield (or CAPE) minus the current real risk-free rate, with the caveat that both are noisy.
- [ ] **L5** — How large is the volatility-harvesting bonus from rebalancing 60/40, empirically, in this window? *Method:* buy-and-hold vs monthly vs quarterly vs daily, already scaffolded by D2.
- [ ] **L6** — Does the 60/40 recommendation survive a 1970s-style stagflation regime? Five years of data cannot answer this. *Method:* cite the literature; do not extrapolate.
- [ ] **L7** — What is the actual distribution of drawdown recovery times for a 100% equity portfolio? A single −24.5% observation is n=1. *Method:* extend history or cite long-run studies.
- [ ] **L8** — Are index mutual funds still distributing capital gains in 2026, or has the practice faded? The tax argument depends on it. *Method:* check recent distribution history for VTSAX.
- [ ] **L9** — What is the empirically correct block length for a moving-block bootstrap on daily equity returns? *Method:* spectral analysis / Politis–White; compare 5/21/63.
- [ ] **L10** — Does SGOV net CAGR represent the *investor's* cash alternative, or should it be a money-market fund / HISA rate? *Method:* compare SGOV, a HISA, and a T-bill index.
- [ ] **L11** — Is BND's −0.29% a rate-hike artefact, and what does its current YTM imply? *Method:* pull current YTM and duration; compute expected 5y return if rates hold.
- [ ] **L12** — What is the minimum viable account size for each vehicle (whole-share friction, MF minimums, fractional-share brokers)? *Method:* check each broker's current policy.
- [ ] **L13** — Do the seven funds have equivalent securities-lending and tax-treatment profiles? *Method:* read prospectuses; note any material differences.
- [ ] **L14** — What survivorship bias is introduced by choosing these seven funds today? *Method:* enumerate index funds that closed/merged in the window.
- [ ] **L15** — Is a 5-year window ever sufficient to rank same-index vehicles? *Method:* show that the *fee* ranking is robust while the *return* ranking is not.
- [ ] **L16** — What would falsify the "low MER is the whole argument" conclusion? *Method:* find a case where a higher-fee vehicle beat a lower-fee one persistently on the same index.
- [ ] **L17** — Does the repo's own alpha work justify the index-fund recommendation, or is that outside this document's remit? *Method:* cite `docs/edge_research/ALPHA_GATE_POWER_CORRECTION_2026-11-23.md` rather than restating.

## M. Peer review protocol (14)

Every claim in the corrected document gets external review before publication. Repo has `/consult-multi`, `/consult-local`, `/consult-PROXY`, `/consult-nvidia-models`.

- [ ] **M1** — Fan the corrected metric definitions to ≥4 independent engines and ask one question only: "Is this Sharpe definitionally correct?" *Done when:* replies archived with engine names.
- [ ] **M2** — Ask a second set to red-team the Sortino denominator (`all-N` vs `downside-count`) and record the consensus. *Done when:* verdict recorded; if split, report the split.
- [ ] **M3** — Ask a third set to attack the bootstrap design specifically (block length, pairing, stationarity). *Done when:* each objection is either addressed or logged as a limitation.
- [ ] **M4** — Return the FXAIX/SPY unit-error finding to the original reviewer for re-check. *Done when:* round-trip documented; if they disagree, say so.
- [ ] **M5** — Blind test: give two engines the corrected numbers **without** the recommendation and ask "what should I buy?" *Done when:* compare their answer to the doc's; divergence ⇒ doc is ambiguous.
- [ ] **M6** — Adversarial numeric check: have an engine recompute CAGR from the raw CSV without seeing the script. *Done when:* agreement to 2dp documented.
- [ ] **M7** — Ask an engine to find any remaining overclaim by grepping for absolutes ("clear", "guaranteed", "proven", "always"). *Done when:* each instance evidenced or removed.
- [ ] **M8** — Have an engine review only the *decision table* for retail-actionability. *Done when:* gaps listed.
- [ ] **M9** — Cross-check the tax claims with an engine that has tax knowledge; tax is the most likely place to be confidently wrong. *Done when:* claims either sourced or softened.
- [ ] **M10** — Record which claims were *refuted* by review and keep them visible in an errata section. *Done when:* errata published.
- [ ] **M11** — Do not accept a review claim without reproducing it — four of twelve in the first review were wrong. *Done when:* this rule is stated in the doc.
- [ ] **M12** — Archive transcripts + hashes under `reports/peer_review/`. *Done when:* files committed.
- [ ] **M13** — Re-run the full review suite after every subsequent metric change. *Done when:* a checklist exists.
- [ ] **M14** — Note explicitly in the doc which numbers were peer-reviewed and which were not. *Done when:* per-number provenance column.

## N. Acceptance criteria & risk register (12)

- [ ] **N1** — No metric is labelled Sharpe/Sortino unless it is `(R − R_f)/risk`. *Accept when:* code review confirms.
- [ ] **N2** — The cash vehicle never prints a finite ratio. *Accept when:* JSON `sharpe` is `null` for SGOV.
- [ ] **N3** — Every headline number carries an interval or the word "point estimate". *Accept when:* grep finds no bare number in a headline.
- [ ] **N4** — No ranking is asserted between funds whose CIs overlap. *Accept when:* ranking table shows overlap flags.
- [ ] **N5** — Portfolio rows state their rebalancing assumption. *Accept when:* label present.
- [ ] **N6** — The doc states its data window, source, and that it is a bull-heavy sample. *Accept when:* header block complete.
- [ ] **N7** — Futures are either analysed properly or explicitly scoped out. *Accept when:* a sentence exists.
- [ ] **N8** — Risk 1: **precision overclaim** — a 5y CAGR presented as an expectation. Mitigation: F-block anchors + intervals.
- [ ] **N9** — Risk 2: **tax error** — a US-centric tax claim applied to a Canadian investor. Mitigation: E3/E4 explicit jurisdiction.
- [ ] **N10** — Risk 3: **data artefact** — adjusted close not total return. Mitigation: L1 before publishing any return.
- [ ] **N11** — Risk 4: **unit confusion** — the exact error the first review made (annual vs 5-year fee gap). Mitigation: quote units on every delta.
- [ ] **N12** — Risk 5: **recommendation laundering** — measurement quietly becoming advice. Mitigation: keep the "not investment advice / buying analysis (beta)" banner and never phrase as "you should".

## O. Operationalisation (10)

- [ ] **O1** — Make the script re-runnable monthly with a single command. *Done when:* documented one-liner.
- [ ] **O2** — Add a GHA workflow that runs it and fails if the JSON schema drifts. *Done when:* workflow green.
- [ ] **O3** — Store a dated snapshot per run so history is visible. *Done when:* `reports/fund_deep_dive_YYYY-MM-DD.json`.
- [ ] **O4** — Add a diff report: what changed vs the previous run and why. *Done when:* diff emitted.
- [ ] **O5** — Alert if the cash hurdle moves >50bp (it changes the whole Sharpe ranking). *Done when:* threshold check exists.
- [ ] **O6** — Alert if any fund's data goes stale >5 trading days. *Done when:* freshness check exists.
- [ ] **O7** — Publish the corrected doc to the repo `docs/edge_research/` index. *Done when:* linked.
- [ ] **O8** — Add an updates/ card per repo convention. *Done when:* `updates/2026-11-23-*.md` written.
- [ ] **O9** — Record the reproduce command + data hash in the doc. *Done when:* both present.
- [ ] **O10** — Explicitly do NOT merge to `main` — leave for operator review. *Done when:* confirmed in the PR description.

---

## Roll-up

| Part | Section | Items |
|---|---|---:|
| I | A metric correctness | 12 |
| I | B statistical rigor | 14 |
| I | C data provenance | 12 |
| I | D portfolio & costs | 14 |
| I | E tax & accounts | 10 |
| I | F forward anchors | 10 |
| I | G futures & coverage | 8 |
| I | H decision output | 10 |
| I | I testing & engineering | 12 |
| I | J peer review | 10 |
| I | K docs & hygiene | 8 |
| II | L open research | 17 |
| II | M peer-review protocol | 14 |
| II | N acceptance & risk | 12 |
| II | O operationalisation | 10 |
| | **TOTAL** | **173** |

### Progress

- **Block A — DONE** (`07e958e932a`): A1, A2, A4, A5, A6, A7. FXAIX Sharpe 0.728→0.457, SPY 0.714→0.443, SGOV 15.886→null.
- Next block: **I1** (tests to lock the metrics) then **D1–D3** (real rebalancing).

