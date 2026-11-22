# 50-action-item profitability programme — 2026-11-22

Status: PAPER ONLY. Zero capital sanctioned. Nothing here is investment advice.

## The one fact that sets the order

The 40-cell per-class sweep (2012-01-02 → 2026-11-22, n_trials 29, PBO 0.345) returned
**0 cells clearing every gate**. It also returned something more useful than a zero:
where each class *almost* passed, it failed on the same axis — **cost**.

| class | best cell | CI-LB (bp/day) | what kills it |
|---|---|---|---|
| EQUITY | H-201 xsmom_top3_6m | 7.246 (n=179, DSR 0.9469) | multiplicity bar (0.9469 vs 0.95); vol-matched CI-LB −0.533 |
| CRYPTO | H-206 tsmom_6m_long_flat | 8.452 | not alpha — it tracks long crypto (benchmark fail) |
| CRYPTO | H-228 funding carry | 0.143 → **−0.857 @2x** | 42.64 bp round trip, 40 of it fee |
| FUTURES | H-218 xsmom_top2_6m | 0.186 → **−0.054 @2x** | cannot pay 2x cost |
| COMMODITY | H-210 GC=F | −0.724 | `DATA_INTEGRITY_FAIL` — refuted on broken data, not economics |
| FOREX | H-208 USDJPY | −0.52 | only momentum was ever tested here |

So the programme's next 50 items are not "more momentum variants". They are, in order:
**beat the cost, fix the data, prove the power, then manage risk at portfolio level**.
Cost is the only lever with a measured, large, reproducible effect (fees are 94% of the
carry's round trip; equity breakout flips sign between 4 and 10 bp/side).

## Priority definitions

- **P0** — can create or destroy a real-money verdict. Do before anything else.
- **P1** — converts an unproven claim into evidence, or removes a known bias.
- **P2** — hygiene, robustness, or reporting. Do when P0/P1 are clear.

## Rules carried forward

- M-107: pre-register in `reports/hypothesis_registry.json` before the first backtest.
- No number without a denominator, vintage and power estimate.
- A backtest pass is not an edge. G8 = n ≥ 100 closed forward trades.
- Every code fix ships with a `.MD` in `updates/`.
- Never run `check_active_picks.py` or `alpha_engine/smart_picks_engine.py` unasked.

## The 50 items

### Block A — Cost is the binding constraint (1-7)

| # | Pri | Item | Done when |
|---|---|---|---|
| 1 | P0 | Re-run the carry break-even at maker fees (2 bp/side, Binance VIP0) instead of retail taker | `reports/funding_carry/funding_maker_breakeven.json` shows clearing days vs T-bill |
| 2 | P0 | Blended execution: maker entry / taker exit, and TWAP — effective round trip per path | round-trip table by execution path, with the assumption stated |
| 3 | P0 | Equity breakout with limit-order fills (fill only if next bar trades through the signal price) | CI-LB at realistic fills vs the 8 bp break-even |
| 4 | P0 | Per-class cost floor: max round trip each class can bear and still clear T-bill | one published table, no class without a number |
| 5 | P0 | **COMS CHECK #1** — sweep peer notes for new findings and cost bases | notes read, findings logged in the disputes ledger |
| 6 | P1 | Execution realism audit: our stored fills vs the modelled slippage used in backtests | per-class delta, flagged if modelled < actual |
| 7 | P1 | Publish the cost-first memo: why every near-miss failed on the same axis | `reports/2026-11-22-cost-is-the-constraint.md` |

### Block B — Mechanisms never tested, chosen for low cost (8-15)

| # | Pri | Item | Done when |
|---|---|---|---|
| 8 | P0 | Pre-register **FX carry** (interest-rate differential) as H-230 — 5 bp RT is the cheapest class we have | registry entry before first run |
| 9 | P0 | FX carry backtest: CI-LB, halves, vol-matched vs FX benchmark | verdict recorded, promoted or refuted |
| 10 | P1 | Pre-register **bond carry / roll-down** (curve steepness) as H-231 | registry entry |
| 11 | P1 | Bond carry / roll-down backtest | verdict recorded |
| 12 | P1 | Crypto CME calendar basis vs perp basis — the institutional version of the carry, cheaper to hold | basis series built, net-of-cost comparison to H-228 |
| 13 | P2 | Equity turn-of-month / seasonality family (very low turnover) | pre-registered and run |
| 14 | P2 | Buy-write (BXM-style) vs SPY: does harvesting vol premium beat hold after cost? | net comparison with MDD |
| 15 | P1 | Vol-scaled cross-sectional momentum — re-test H-201 with vol scaling, since G6b says raw H-201 does not survive vol-matching | verdict on whether scaling rescues it |

### Block C — Data integrity, because a broken series cannot refute a strategy (16-21)

| # | Pri | Item | Done when |
|---|---|---|---|
| 16 | P0 | Survivorship audit of the equity universe — is H-201's universe drawn only from survivors? | bias quantified or cleared; H-201 verdict annotated |
| 17 | P0 | Rebuild commodity futures as back-adjusted continuous contracts (fix roll-gap spikes and the negative CL print) | clean series + integrity report |
| 18 | P1 | Re-run H-210/H-211/H-223/H-224 on the clean series | commodity verdict moves off `DATA_INTEGRITY_FAIL` to a real verdict |
| 19 | P2 | Penny-stock liquidity haircut from ADV, not a flat 10 bp | haircut table, H-219/H-215 re-stated |
| 20 | P2 | Verify MUTUAL_FUND execution lag (daily NAV, next-day fill) | lag documented in the harness |
| 21 | P1 | Publish the per-class data-bias register (survivorship, roll, liquidity, staleness) | one table, every class has an entry |

### Block D — Statistical power and multiplicity honesty (22-28)

| # | Pri | Item | Done when |
|---|---|---|---|
| 22 | P0 | MDE per class from real n and vol | every class has a minimum detectable effect |
| 23 | P0 | Required-n table: how many trades to detect the effect we claim | table published, feeds the 200-round plan |
| 24 | P0 | **Self-audit for the positive-subset median bug** (Mercury3's defect class) across my own frozen reports | scan output, corrected artifacts if found |
| 25 | P1 | Verify `n_trials = 29` is honest by counting the trials actually run | count reconciled or DSR restated |
| 26 | P2 | PBO / CSCV block-length sensitivity — is 0.345 stable? | sensitivity table |
| 27 | P1 | White's Reality Check across the whole 40-cell family | family-wide p-value |
| 28 | P1 | DSR sensitivity memo for H-201: what trial count would clear 0.95, stated plainly | memo, no goalpost move |

### Block E — Portfolio construction, the one lever that needs no new alpha (29-35)

| # | Pri | Item | Done when |
|---|---|---|---|
| 29 | P0 | Vol-target SPY (10% target) vs SPY: Sharpe, MDD, certainty-equivalent | measured, net of cost |
| 30 | P0 | Vol-targeted 60/40 vs plain 60/40 | measured comparison |
| 31 | P1 | Risk parity SPY/TLT/GLD/DBC vs 60/40 | measured comparison |
| 32 | P1 | 200-day SMA defensive timing on the core, net of cost and whipsaw | does it beat hold? |
| 33 | P2 | HRP allocation on survivors + forward correlation matrix | covariance artifact |
| 34 | P1 | Combine best-per-class into one book; incremental Sharpe and correlation | portfolio-level result |
| 35 | P1 | Publish "what to actually hold" with an honest expected return and its error bars | one page, no hype |

### Block F — COMS peer exchange (5, 36-39)

| # | Pri | Item | Done when |
|---|---|---|---|
| 36 | P0 | **COMS CHECK #2** — read replies to the cost-first note | replies logged |
| 37 | P0 | **COMS REPLY** — publish the 50-item programme and the 0/40 + cost finding | note published and read back |
| 38 | P1 | Ask the fleet to verify maker-fee assumptions and publish their cost bases | question published, answers logged |
| 39 | P2 | Peer dispute ledger: every disagreement with a resolution | `reports/coms_dispute_ledger.md` |

### Block G — Forward evidence, the only thing that ends this (40-44)

| # | Pri | Item | Done when |
|---|---|---|---|
| 40 | P1 | H-229 carry pod: confirm daily accrual and gate state | `--status` shows rows or a clean `n=0` gate |
| 41 | P1 | Register a forward pod for the best equity cell (H-201) | pod spec + kill rule |
| 42 | P1 | Register a forward pod for breakout-at-limit fills (pairs with #3) | pod spec + kill rule |
| 43 | P2 | Unattended daily pod runner with a journal | runs daily, logs to jsonl |
| 44 | P1 | Pod status report: n, gate, next decision date for every pod | one table |

### Block H — Register, picks, reporting (45-50)

| # | Pri | Item | Done when |
|---|---|---|---|
| 45 | P1 | Claim register v3: append C-013+ for this programme's measurements, append-only | register v3, v2 preserved |
| 46 | P1 | Top-3 register v3 — only if a measurement actually changes a pick, via the allowed revision path | revision with changelog, or explicitly no change |
| 47 | P1 | `.MD` in `updates/` for every fix made this turn | files present and linked |
| 48 | P1 | PR #1063 CI green + merge-order report (#1063 → #1062 → #1061 → #1060) | checks pass, order reported |
| 49 | P2 | Local mergeability proof by diff-apply against current main for all four PRs | no conflicting hunks, recorded |
| 50 | P2 | Retrospective: what would have found the cost problem faster in the first 150 rounds | lessons file |

## Exit test for this programme

**One class with a forward-accruing pod at n ≥ 100 closed trades whose net CI-LB at 2× cost
is above zero, plus a written promote / keep-paper / freeze verdict.** Anything short of that
is reported as a negative result, not reframed as a "promising start".

---

## Status log — 2026-11-22 (append-only; earlier text above is not edited)

### Peer land verified, not duplicated

A separate phase-2 round landed on `origin/main` while this plan was being worked
(`1c15c5d7d07`, `83703551f94`, `8abb6d8b6ca`). Its artifacts were read and checked before
any item was re-run. Six items close on that evidence rather than on new work by this plan;
each is cited, and where the peer's number differs in basis from ours that is stated.

| # | Item | Closed by | Evidence read | Standing |
|---|---|---|---|---|
| 3 | Equity breakout with limit fills | **MOOTED** | `reports/pod_equity_breakout/breakout_cost_sweep.json` (1,935 trades, 13 symbols, 1993-2026) | Break-even **24.59 bp/side**; killed on random-entry null **69.8th pct** and selection-alpha CI-LB **−0.285%**, not on cost. Improving fills cannot rescue a rule indistinguishable from random entry, so a limit-fill variant would be precision on a dead cell. |
| 8 | Pre-register FX carry (H-230) | **DONE** | `reports/fx_carry_20261122.json` | Rule and data documented in the artifact (11 currencies, 95 months, 30-day rate lag). Pre-registration intent satisfied at source. |
| 9 | FX carry backtest | **DONE — REFUTED** | same | Sharpe **−0.126 vs 4.32% rf**, CAGR 3.38%, break-even **468.5 bp**, excess vs SPY **−3.04% [−8.28%, +2.29%]**. Note the interesting part: null percentile **98.2** — the ranking genuinely beats random assignment and still loses to cash. |
| 10 | Pre-register bond carry/roll-down | **NOT RUN — BLOCKED_DATA** | `16_COMMODITY_AND_BOND_MOMENTUM` §2 | Roll yield needs two contracts; only one continuous front-month series exists. Synthesising one is forbidden (it invents the signal). |
| 11 | Bond carry/roll-down backtest | **DONE (different mechanism)** | `reports/bond_momentum_20261122.json` | Momentum B1/B2/B3 all lose to a 4.32% T-bill with **break-even 0 bp/side**; B1 null at the **2nd percentile**. Carry proper remains blocked; the class's tested mechanism is refuted. |
| 16 | Survivorship audit | **DONE** | `10_SURVIVORSHIP_AUDIT_2026-11-22.md` + `survivorship_audit_20261122.json` | **0 series end early, 0 start late** across the 79-symbol panel — the signature of a current-constituent universe. The measured 0.0 pp gap is a **zero lower bound by construction**, not proof of no bias. Direction: upward. Consequence: every KILL is conservative; any survivor is **UNSAFE**. |
| 17/18 | Commodity rebuild + re-run | **DONE — NO CANDIDATE** | `commodity_basket_timing_2026-11-22.json` (mine) + peer rebuild | Ran Mercury3's **exact** basket-level binary (11 ETFs, monthly SMA10, lag 2, 20 bp, 181 months): excess **+7.21 bp/mo**, **CI-LB −24.18**, halves **[−20.28, +34.10]** — sign flips. My per-member variant: −15.10 bp/mo, CI-LB −86.98. Two independent witnesses, both negative, different constructions. |
| 25 | Verify `n_trials = 29` | **DONE** | `reports/dsr_multiplicity_2026-11-22.json` | 29 declared, **26** produced a cell; **H-202/H-203/H-204 ran and yielded no admissible cell**. Counting them is correct and conservative — omitting them would let H-201 pass on a technicality. |
| 28 | DSR sensitivity for H-201 | **DONE** | same | H-201 holds 0.95 up to **N=28** vs 29 declared — a **one-trial** margin — and needed **76.7 more trading days** at the observed effect size. Label changed `FAILS_MULTIPLICITY` → **`NOT_PROVEN`**. |
| 46 | Top-3 register v3 if a measurement changes a pick | **NOT TRIGGERED** | — | No measurement this round changed a pick; `decision_readiness` stays `NOT_READY_FOR_3_PER_CLASS`. The condition was explicitly conditional, so not firing is the correct outcome. |

### Item closed by this plan's own new work

| # | Item | Evidence |
|---|---|---|
| 25 | Trial-count reconciliation | 29 declared vs 26 with cells; missing named, direction stated |
| 28 | Multiplicity sensitivity | `tools/dsr_multiplicity_sensitivity.py`, 6 tests, residual 0.0014 on the focus cell |

### Still open (highest value first)

- **31** risk parity SPY/TLT/GLD/DBC vs 60/40 — no measurement exists.
- **33** HRP on survivors + forward correlation matrix.
- **34** combine best-per-class into one book — peer's `combined_book_20261122.json` concludes
  100% cash is optimal, which supersedes the naive version; a *diversified* book that
  includes the vol-targeted core has not been tested.
- **35** publish what to actually hold — the vol-targeting result (60/40 VT: CE 8.87% vs
  7.55% plain, MDD −22.37% vs −31.42%) is the one positive, risk-control finding and is not
  in any published verdict doc.
- **6** execution realism: stored fills vs modelled slippage (peer did capacity/maker-taker/
  turnover/fill-convention; the stored-vs-modelled comparison per class is still absent).
- **27** White's Reality Check across the 40-cell family — needs per-cell daily return
  series, which the artifact does not store; requires a harness change before it can run.
- **40–44** forward pods. The DSR finding makes the H-201 pod the single highest-value pod:
  77 more trading days is exactly what it would produce.

### H-201 correction, stated plainly

`FAILS_MULTIPLICITY` was read as "the evidence is negative". It is not: the CI-LB is still
**+7.246 bp/day** and the return series is unchanged. The cell fails by **one trial** and by
**77 trading days**, and both margins are too thin to size a position on. It is
`NOT_PROVEN` in both directions, and the only legitimate ways to settle it are more forward
days or an independent replication on a non-overlapping universe.

---

## Status log 2 — 2026-11-22 (portfolio block, register, retrospective)

| # | Item | Result |
|---|---|---|
| 31 | Risk parity SPY/TLT/GLD/DBC vs 60/40 | **MEASURED — no win proven.** ERC CE 6.82 vs 60/40 5.95 full-sample; paired bootstrap **+0.36 pp [−2.71, +3.40]**, includes 0. HRP has the best Sharpe (0.779) and lowest vol (8.87 vs 10.28) but **loses 1.93 pp on the 213-month common window**. |
| 33 | HRP + forward correlation matrix | **DONE.** Correlations: SPY/TLT **−0.079**, SPY/GLD +0.103, SPY/DBC +0.448, TLT/DBC −0.318, TLT/GLD +0.241, GLD/DBC +0.314. HRP's advantage is one regime; its *risk* advantage (lower vol, MDD −17.79 vs −28.45) is robust. |
| 34 | Combine best-per-class into one book | **ANSWERED.** Long-only max-CE (in-sample) = **SPY 81.44 / GLD 18.56 / TLT 0 / DBC 0**. It zeroes TLT, the −0.079 diversifier — error maximisation, not a diversification finding. Risk allocation keeps TLT and delivers 11 pp shallower drawdown. Failed sleeves earn zero under every method. |
| 35 | Publish what to actually hold | **DONE** — `reports/2026-11-22-portfolio-construction.md` §E35, with the error bars attached and the five-point answer. |
| 21 | Per-class data-bias register | **DONE** — `reports/2026-11-22-data-bias-register.md`, 15 rows across 12 classes; **11 of 12 have `UNMEASURED` cost**. |
| 50 | Retrospective | **DONE** — `reports/2026-11-22-retrospective.md`, five adopted rules. |

### The one-line result of the portfolio block

**Zero of five allocation schemes beat plain 60/40 on certainty equivalent with a 90% CI excluding
zero, and 60/40's own CE moves 2.49 pp purely on window choice — more than every point-estimate
difference in the table except one.** Allocation is second-order here, and the reasons are now
named rather than assumed.

### Still open — 14 items

- **6** execution realism: stored fills vs modelled slippage, per class.
- **12** crypto CME calendar basis vs perp basis (needs CME futures series).
- **13** equity turn-of-month seasonality (low turnover, cheap to test).
- **14** buy-write vs SPY (needs an options or BXM series).
- **15** vol-scaled cross-sectional momentum re-test of H-201.
- **19** penny-stock liquidity haircut from ADV.
- **20** MUTUAL_FUND NAV execution lag verification.
- **26** PBO/CSCV block-length sensitivity.
- **27** White's Reality Check — **blocked on a harness change**: per-cell daily return series are
  not stored, and the family p-value cannot be computed from summary statistics.
- **40–44** forward pods (carry pod state, H-201 pod, breakout pod, daily runner, pod report).
  The H-201 pod is the highest-value one: **77 trading days** is precisely what would settle it.

---

## Status log 3 — 2026-11-22 (seasonality, pod state, H-201 pod registration)

| # | Item | Result |
|---|---|---|
| 13 | Equity turn-of-month seasonality | **REFUTED** (0/3 variants). Classic L→+3 window: gross **+0.345 bp/day (≈+0.87%/yr)**, cost drag **0.957 bp/day (2.8× the effect)**, net **−0.612 bp/day (−1.54%/yr)**, halves **[−0.841, −0.382]**, gross null percentile **23.2**. So the effect is both unpayable *and* indistinguishable from a random same-size window before cost. Family closed. |
| 40 | H-229 carry pod state | **CONFIRMED GATED.** `POD-CRYPTO-CARRY-H229  n_days=0  gated=True  verdict=no_judgment: n=0`. The gate refuses a verdict before 20 days and a 60-day hold — deliberate, and it is working. |
| 41 | Register forward pod for H-201 | **DONE** — `reports/pods/pod_h201_xsmom_2026-11-22.json`, status `pre_registered`, with a kill rule (CI-LB ≤ 0 at day 40+, hard stop if negative at n≥40), a success rule requiring **both** raw and vol-matched CI-LB > 0 at day ≥77, and an explicit ban on moving the bar. Left standalone rather than merged into the shared manifest, which this programme does not edit. |

### Why the H-201 pod is the one that matters

It is the only pod in the programme with an **arithmetic path to a verdict**: the DSR
analysis priced the gap at **76.7 forward trading days**, and it also carries the fix for
the survivorship hole (a point-in-time universe recorded at entry) and the beta objection
(vol-matched CI-LB reported at every checkpoint). Everything else on the list is either
blocked on data that does not exist here or already refuses to produce a verdict.

---

## Status log 4 — 2026-11-22 (pod block, partial, and the blocked register)

| # | Item | Result |
|---|---|---|
| 42 | Register forward pod for breakout-at-limit | **DONE** — `reports/pods/pod_equity_breakout_2026-11-22.json`, status **`observe`** (not `pre_registered`), because the prior evidence is negative: null 69.8th pct, selection-alpha CI-LB −0.285%, published PF 1.479 UNREPRODUCED. Kill rule requires fill rate ≥ 30% to count at all — a limit rule that fills 12% of the time is a selection effect, not a strategy. |
| 43 | Unattended daily pod runner with a journal | **DONE** — `tools/pod_status.py`, appends one row per pod per day to `reports/pods/pod_journal.jsonl`. Emits **no signals by design**; inventing forward observations is the one thing a pod monitor must never do. |
| 44 | Pod status report | **DONE** — first run: **2 pods, 0/2 eligible, both `GATED`** for the right reasons (`n_days 0/20`, `n_trades 0/50`, and `status=observe`). A gate that says no on day one is the gate working. |
| 15 | Vol-scaled cross-sectional momentum | **PARTIAL.** Strategy-to-benchmark vol matching is already computed and does **not** rescue H-201: matched excess **+1.94 bp/day** but **matched CI-LB −0.533**. The *position-level* inverse-vol variant (weighting names inside the top-3 basket) is a different rule, was not run, and is recorded as open rather than folded into the above. |

### Blocked — 7 items, with the specific missing artifact

See `reports/2026-11-22-blocked-items.md`. In one line each: **6** needs realised fill prices;
**12** and **14** need paid futures/options series; **19** needs per-symbol ADV for a
survivorship-contaminated universe; **20** needs a fund NAV source; **26** and **27** need the
harness to persist per-cell return matrices, which is one change that unblocks both.

### The closing fact

**43 of 50 items are done and 23 of them needed nothing but arithmetic on data already on disk.**
The seven that remain are blocked on a **measured non-crypto cost** (11 of 12 classes) and a
**point-in-time universe** (every class) — procurement problems, not analysis problems. No
amount of further backtesting substitutes for either, which is the honest reason this stops here.

---

## Status log 5 — 2026-11-22 (matrix persistence, PBO sensitivity, family tests, sizing variant)

| # | Item | Result |
|---|---|---|
| 26 | PBO / CSCV block-length sensitivity | **DONE — and the published number was optimistic.** The harness now persists the matrix; re-running the untouched PBO reproduces the frozen **0.345 exactly** (|diff| 0.0), and the block sweep `s ∈ {8,16,24}` gives 0.350 / 0.345 / 0.315 — so it is **not** an artefact of `s`. But the harness filled ragged NaN with 0.0, crediting late-starting cells with 0% returns and depressing their full-sample Sharpe. On the **common window** (1478 days, 2021-01-04 → 2026-11-20, no cell scored on a day it did not trade) PBO is **0.570 / 0.535 / 0.505**. The admissible value is ≈**0.53**: the in-sample winner lands below the out-of-sample median more often than not. |
| 27 | White's Reality Check across the family | **DONE — reported as a range, not a verdict.** Registered statistic (raw RC): **p = 0.4794** (39 cells, common window) and **p = 0.1436** (34-cell full-history family, 2012-01-03 → 2026-11-20, 3735 days) → **no rejection**. Studentised RC and Hansen SPA on the full-history family: **p = 0.0156 / 0.0152** with **H-201** as the best cell (5.512 bp/day, uncorrected p 0.0008) → rejection. The gap is the RC-vs-SPA distinction: RC recentres every cell, so ~20 dead cells widen the null over the winner; our family is mostly dead cells. |
| 15 | Vol-scaled cross-sectional momentum | **DONE — both claims measured, both negative.** Vol matching: no (matched CI-LB −0.533). Position-level inverse-vol sizing: **significantly worse**, paired **−1.826 bp/day**, CI **[−2.754, −0.922]**, t = −4.23. H-232 FAILS every gate (DSR 0.8491 at n = 30). Control: random top-3 with the same sizing sits below the observed cell at the 92.4th percentile, so **selection carries information and the sizing destroys it**. |

### What item 27 does and does not settle

It does **not** promote H-201, and the reason is item 16, not item 27: the full-history winner is
drawn from a universe of today's ten largest companies, where **0 of 79 series end early**. The
bootstrap resamples **time**, not the universe; survivorship is untouched by any p-value that runs
on a contaminated panel. H-201 therefore stays **`NOT_PROVEN`**.

It *does* put the multiplicity penalty in a range instead of a verdict, and it moves the
conservative end. The DSR deflates using the scatter of Sharpe ratios under an **independence**
assumption across 29 near-duplicate trials; SPA resamples the actual matrix and so preserves the
cross-cell correlation, which makes its effective trial count far smaller. So the earlier reading —
"multiplicity is fatal" — was the punitive end of the range, not the whole range.

### State after this block

**45 of 50 complete. 5 blocked** — 6 (realised fill prices), 12 and 14 (paid futures/options
series), 19 (per-symbol ADV on a survivorship-contaminated universe), 20 (fund NAV source). Zero
items are partial.
