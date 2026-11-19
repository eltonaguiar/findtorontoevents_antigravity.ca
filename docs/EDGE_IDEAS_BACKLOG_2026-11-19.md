# External reviews → edge idea backlog (2026-11-19)

**Status:** living backlog. Nothing here is proven; every entry names the test
that would kill it.
**Owners of the surfaces referenced:** `audit3` (this repo), `/audit` (read-only
here), `alpha_engine/*`.

This doc exists because five independent reviews said roughly the same thing in
five different vocabularies, and the repo had no single place where that advice
lived next to our own measurements. Re-proposing things we already built is a
real cost: four of the "new" ideas below are already implemented and untested.

---

## 0. Provenance — who said what

| Source | What they actually contributed | Where it lives now |
|---|---|---|
| **Grok** | Implement Deflated Sharpe Ratio; statistical-arbitrage pairs; "we forgot forex" | this doc §4 (E1, E4, E11) |
| **Gemini** | Meta-labelling ML for regime filtering; Polymarket/Kalshi arbitrage scanner; market-neutral cross-sectional crypto | this doc §4 (E5, E6, E3) |
| **Mercury (Inception Labs)** | Full finance-DB schema inventory across 10 databases | `docs/FINANCE_DB_SCHEMA_SPEC.md` (merged to main 2026-11-19, with a verified-corrections appendix); §3 here summarises it |
| **Arena agent** | Long review: risk premia over prediction, TSMOM/FX-carry/PEAD pods, prune-then-test, barbell portfolio | §4 (E8, E9, E10, E15) |
| **Arena external review (longer)** | Same thesis with citations (Moskowitz–Ooi–Pedersen, Bernard–Thomas, SPIVA), phase 0–3 plan | §4, §6 |
| **Our own audit3 work** | Beta accounting, point-in-time gate replay, M1b selection alpha | §§1–2, anchors every claim below |

Mercury's spec now lives at `docs/FINANCE_DB_SCHEMA_SPEC.md` (merged to main
2026-11-19) and carries an Appendix A with the corrections this review made —
chiefly that it omitted every price table. Arena's `EDGE_REVIEW_2026-11-19.md`
is still **not in this repo**: its findings are summarised here instead.

---

## 1. ELI5 — the findings, in plain English

**The question was:** the win rates look bad — can we find a real edge?

**Short answer:** no, and the reason is understandable.

1. **"Crypto shorts win, crypto longs lose" is not a skill.** Imagine a river
   flowing downhill and two boats: one pointing down (short), one pointing up
   (long). The down-boat "wins" every time. That is not sailing skill — it is the
   river. Over these nine months crypto drifted about **−1% per trade window**.
   Longs lost 1.14%, shorts gained 0.89%, and those two numbers add up to almost
   exactly what you'd pay in fees. Nothing left over.

2. **Our "quality gate" was a rear-view mirror.** The system grades each pick by
   how the strategy has done so far. But that grade was filled in *after* the
   trade closed, so it partly knows the answer. When I re-ran it honestly —
   letting a strategy use only picks that had already finished before this one
   started — the edge vanished (top-rated picks: **−0.19%**). A gate that peeks
   is not a gate.

3. **The real test is "did we pick the right thing?" and we now measure it.**
   Take every pick and ask: would I have done better just buying the same thing
   and holding it for the same time? For crypto longs the answer is **yes, by
   0.44% per pick** — the profit-taking and stop-losses are cutting winners short.
   For ETFs, holding beat us by **0.27% per pick**. For equities it was a wash.
   Nowhere did we beat holding.

4. **Why this is normal, not embarrassing.** Everyone with public price data is
   competing with firms that see order books and pay for satellite data. The
   durable public edges are not predictions — they are being *paid to hold risk*
   (trend, carry, value) and *not losing money to costs*. Mutual funds looked
   best in our data for exactly that boring reason: low turnover.

5. **The nearest thing to free money is stopping the bleeding.** −0.44% per
   crypto-long pick and −0.27% per ETF pick are bigger than anything the system
   claims to earn. Fixing those is worth more than any new strategy.

**One-sentence version:** we do not have a prediction edge, we have a cost and
exit-design problem, and the honest next step is to stop destroying value before
hunting for alpha.

---

## 2. What every reviewer agreed on (and our data already confirms)

1. **Directional prediction on public daily data is the low-probability path.**
   Our measurement: selection alpha ≤ 0 in every slice, negative where significant
   (CRYPTO LONG −0.442%/pick, ETF LONG −0.272%/pick).
2. **Costs, not signals, decide survival.** 1bp/day ≈ 20%/yr leakage (Arena);
   our crypto round-trip slippage is 6% of a median win, ETF 2% — small per trade,
   fatal at this turnover.
3. **The research process must be validated, not the best backtest.** 700+
   strategies is a multiple-testing engine. Our own tribunal kills 11 strategies
   and 34 `WEAK` cells precisely because raw p-values don't survive BH.
4. **Risk premia > prediction.** Trend, carry, value/quality, PEAD are the only
   edges with century-scale public evidence.
5. **Fewer, deeper hypotheses with an economic prior.** Pre-register, then test
   once.

Where they differ, and it matters:
- Arena says *freeze generation entirely* and run 2 pods. Gemini wants three new
  scanners built. Both are right for different budgets; §5 resolves it by
  ordering (stop the bleed → prove one premium → only then build scanners).

---

## 3. What is already built (stop re-proposing it)

Verified by scanning `alpha_engine/`, `audit_trail/`, `tools/`, `ml_*`,
`copy_trader_intel/`, `paper_trading/`:

| Capability the reviews ask for | Already exists | Files found | State |
|---|---|---|---|
| Deflated Sharpe Ratio | yes | ~130 files reference DSR; `alpha_engine/audit3_tribunal.py::deflated_sharpe` | **wired as gate G4** in audit3, with `n_trials` = tested cells |
| PBO / CSCV | yes | ~47 files (`rigorous_backtest_harness.py`, `admissibility_pipeline.py`, `eagle_gates.py`) | implemented in the harness; **not** in audit3 |
| Cointegration / pairs | yes | ~35 files incl. `alpha_engine/crypto_pairs_arb.py`, `hurst_exponent.py`, `quant_algorithms.py` | built; no forward-validated verdict |
| Meta-labelling | yes | ~17 files incl. `alpha_engine/meta_labeler.py`, `winner_predictor.py`, `ml_ranker.py` | built; no calibration/Brier proof |
| Polymarket/Kalshi arb | partially | ~15 files incl. `pm_consensus_overlay.py`, `sports_arbitrage_scanner.py`, `prediction_market_whales.py` | consensus/whales yes; **cross-venue + bracket arb scanner no** |
| Funding/basis carry | yes | `alpha_engine/funding_rate_arb.py` | built; capacity-adjusted return below T-bills per earlier audit |
| Benchmark gates | partially | `alpha_engine/benchmark_closed_ledger.py`, `audit3_selection_alpha.py` | live for audit3; never run across `/audit` classes |

**Mercury's DB inventory (recorded here because the source file was lost):**

| DB | Tables | Status at 2026-11-19 |
|---|---|---|
| `stocks` | **409** | Active — `trading_picks`, `at_raw_picks`, `at_pick_outcomes`, `at_signal_outcomes` written within hours |
| `backtests` | 10 | **Stale** — `bt_backtest_runs` last import 2026-03-06; `bt_backtest_trades` ≈ 32.7M rows |
| `memecoin` | 58 | Dormant — last wrote 2026-05-04 |
| `sportsbet` | 49 | Dormant — last wrote 2026-05-16/24 |
| `backups` | 414 | Archive by design |
| `deals` | 0 | Empty — decommission candidate |

Independently re-verified while writing this doc: `stocks` has 409 tables;
`crypto_ohlcv` = 1,708,142 rows / 333 symbols through 2026-11-19; `bt_backtest_runs`
= 285 rows. Mercury's summary holds.

---

## 4. The backlog

Priority = (evidence we can get) × (cost to test)⁻¹. **P0 means "do before any
new strategy exists".**

### P0 — stop destroying value, make measurement honest

| ID | Idea | From | Why / evidence today | First test | Kill criterion |
|---|---|---|---|---|---|
| **E11** | **Backfill FX prices and fix symbol mapping** | Grok ("we forgot forex") | `fx_prices` = 3,855 rows, **span ends 2026-02-09**, 15 pairs, names `AUDCAD`; ledger uses `AUDJPY=X`/`AUD-USD` and runs to Nov 2026. Result: **211 forex picks have no computable alpha** | backfill 2026-02→11 daily bars; map `XXXYYY=X`/`XXX-YYY` → `XXXYYY` | if backfill can't reach ≥90% coverage, declare forex unmeasurable and stop emitting it |
| **E12** | **Hold-benchmark pilot** | our audit3 §M1b; Arena "benchmark legs everywhere" | selection alpha already computed offline: CRYPTO LONG −0.442, ETF LONG −0.272 | emit pick **and** same-symbol hold side by side in paper for 90 days; promote only on alpha CI > 0 | alpha CI ≤ 0 after 90 days → the entry logic adds nothing over holding |
| **E13** | **Stamp gate inputs at issue time** | our PIT replay | `at_issue_strat_fwd_wr` exists on **215/3,500** rows; `wf_verdict` scored +0.96%/trade until replayed PIT (then −0.19%) | write `at_issue_*` for 100% of rows; re-run `audit3_edge_hunt.py` | if PIT replay still shows no discrimination after 100% stamping, retire `wf_verdict` as a gate |
| **E14** | **Kill the negative-alpha expressions** | our measurement | crypto LONG −0.442%/pick vs hold with median TP +2.50%/SL −1.50%; ETF LONG −0.272%/pick | A/B paper: current TP/SL vs symmetric vol-scaled time exit on the same signals | if the new expression doesn't clear alpha > 0 in 2 regimes, stop emitting the cell |
| **E1** | **DSR at true cumulative N** | Grok | DSR exists but computes `n_trials` from cells *in one run*, not the 700+ strategies ever tried | feed a global trial counter into `deflated_sharpe` | any cell that passes today and fails at true N is reclassified, not deleted |

### P1 — prove one premium properly (2–6 weeks each, max 2 concurrent)

| ID | Idea | From | Economic prior | First test | Kill criterion |
|---|---|---|---|---|---|
| **E8** | Vol-targeted TSMOM across liquid futures/ETFs | Arena P1 | ~140 yrs of trend evidence; crisis alpha | 3–12m ensemble, monthly, symmetric exits, no TP/SL, 20–60 instruments, 2× costs + 1-bar delay | IR < 0.5 or alpha t < 2 at Bonferroni N |
| **E9** | G10 FX carry + 200d trend overlay | Arena P2, Grok | carry is paid crash risk; trend cuts the crash | needs E11 first; rank by forward discount, long top-3/short bottom-3, vol-targeted | carry drawdown > trend overlay's benefit, or < T-bills after costs |
| **E3** | Market-neutral cross-sectional crypto | Gemini | 333 symbols × 1h bars already in DB = genuine breadth; strips beta | rank top-50 perps on 14d momentum / funding-adjusted carry; long top decile, short bottom, dollar-neutral | alpha CI ≤ 0 after costs, or turnover > 50%/month |
| **E7** | Delta-neutral funding/basis carry | Gemini, Mercury | paid by over-leveraged longs; no direction | spot long + perp short on funding spikes, capacity-capped | capital-adjusted return < T-bills (already happened once — do not re-run unchanged) |

### P2 — only after a P1 pod survives

| ID | Idea | From | Note |
|---|---|---|---|
| **E6** | Polymarket/Kalshi cross-venue + bracket arb scanner | Gemini, Arena | maker-only (Kalshi 0 fee, Polymarket 15–25% rebate); taker fees 3.5–6.3% of stake kill it. Resolved n=1 today ⇒ build the resolver before the scanner |
| **E5** | Meta-labelling for regime filtering | Gemini | `meta_labeler.py` exists; must be scored on calibration (Brier), purged CV + embargo, never as price prediction |
| **E4** | Cointegration pairs | Grok | `crypto_pairs_arb.py` exists; require ADF/Engle-Granger with rolling stability, multi-day holds, not correlation |
| **E10** | PEAD on large caps | Arena P3 | needs 500+ names and SUE data; fix the 60/60 pipeline first |
| **E15** | Barbell portfolio (70–85% beta core, 10–25% premia sleeve, ≤5% speculative) | Arena | allocation policy, not a strategy; not something code can validate |

---

## 5. Sequencing rule (resolves the reviewers' disagreement)

Gemini proposes three new scanners; Arena says freeze generation. Both cannot be
first. The ordering that respects both:

1. **E11, E13, E14** (this week) — make forex measurable, stop the gate from
   peeking, stop the two proven value-destroying expressions.
2. **E12** — the hold-benchmark pilot starts the 90-day clock immediately, because
   it is the only test that can say "the entry logic is worth anything".
3. **E8 or E3** (one only) — one premium pod, pre-registered, untouched holdout.
4. **E6/E5/E4** — infrastructure building only after one pod clears its gates.

Rule: **no new strategy may be generated while a P0 item is open.** That is the
single sentence the reviews agree on.

---

## 6. The forex gap (what "we forgot forex" actually means)

Measured today:

| Fact | Value |
|---|---|
| forex picks in the ledger | 211 |
| picks with computable alpha | **0** |
| `fx_prices` rows / span | 3,855 / 2025-02-10 → **2026-02-09** |
| ledger span | 2026-02-21 → 2026-11-19 |
| symbol formats | table `AUDCAD`; ledger `AUDJPY=X`, `AUD-USD`, `EURUSDT` |

So there are **two** defects, and only one is a bug in my code:

- **Mapping**: `symbol_candidates()` in `audit3_selection_alpha.py` only swaps
  dot/dash, so `AUDJPY=X` never matches `AUDJPY`.
- **Staleness**: the price table ends 2026-02-09, before 96% of the ledger. Even
  a perfect mapping yields almost no coverage. Backfill is required first.

`EURUSDT` is also mis-filed as FOREX while being a crypto pair — the class
derivation should treat a `USDT` quote as CRYPTO regardless of the claimed class.

---

## 7. Things I would not do (with reasons)

- **Invert the crypto-long book.** The loss is beta plus exit geometry; inverting
  flips the beta sign and keeps the exit problem.
- **Run more AI-generated strategies to "find" the edge.** Trial inflation is what
  makes every apparent winner die. 700 strategies bought a lot of p-values.
- **Trade Polymarket as a taker.** Fee is 3.5–6.3% of stake; the maker side is the
  only structurally sound seat, and capacity is small.
- **Copy-trading as a core sleeve.** It pays the fee twice and inherits leaderboard
  survivorship.
- **Trust `wf_verdict` as a sizing input** until E13 lands.

---

## 8. Open questions for the operator

1. Which single P1 pod gets the next two weeks — E8 (TSMOM, strongest evidence) or
   E3 (cross-sectional crypto, cheapest data we already have)?
2. Is there a budget/critical path for an FX backfill (E11), or does forex get
   retired as unmeasurable?
3. Do we commit Mercury's schema spec and Arena's review as real files, or keep
   this doc as the single source of truth for them?
4. For E12, is a 90-day paper clock acceptable, or does the review cadence need
   to be 30 days with a smaller n?

---

## 9. Integrity notes

- Every number in §2 comes from `alpha_engine/audit3_edge_hunt.py` and
  `alpha_engine/audit3_selection_alpha.py` run against the live
  `dashboard_data.json` of 2026-11-19 (3,500 closed picks, 246 days).
- Reviewer claims were not taken on trust: DSR/PBO/pairs/meta-labelling were
  verified to exist in code before being listed in §3, and the DB inventory was
  re-queried where practical (409 tables, 285 `bt_backtest_runs`, 1.7M crypto bars).
- Nothing in this doc is investment advice, and no entry is a signal.

---

## §14 arena.ai v3 delta (2026-11-19) — what is actually left

Status of the v3 P0 list against what shipped today. Kept here so the next session does
not re-derive it from a chat transcript.

| v3 item | Status |
|---|---|
| canonical `resolved_closed_picks_net` view both pages query | **done** — sidecar + payload block + declared denominator; audit3 reports `mode=canonical\|payload_slice` |
| excluded-cohort panel ("judging 21.4% of the book") | **done** (#893) |
| selection-alpha-vs-hold as the per-class headline | **done** (#893, `--alpha` sidecar + demoted PF) |
| one smart-picks definition, one number | **open** |
| kill the dead tier2 panel, the "Renaissance T1/T2/T3" labels, the PF-lift "POSITIVE" card | **done** — panel markup retired, branding stripped, PF-lift tile removed |
| gates ON by default, fail-open paths closed | **done** — FDR + single-source default on, cost gate strict |
| rehab children inherit the parent's cumulative trial count | **open** — TESTING_PROTOCOL §6–§8 still resets multiplicity |
| audit3 expectancy-CI as G1 | **done** (#895) |
| confirmatory vs discovery multiplicity families | **done** (#898, pods in #901) |
| KILL → denylist wiring | **done** (#898 ingest, #900 writer, #901 class gate) |
| reconcile the H-119 two-vintage tiles | **done** — fallback labelled as a dated snapshot and the vintage named in the card header; `gate_eta: ~2026-06-25` retired at source (that date passed with no promotion, n≥150 was already met at n=431, and only `net_ci_lb_gt_1.15` still fails) |
| one vocabulary for the two kill lists | **done** (deliberately *not* merged) — `tools/kill_list_reconcile.py` publishes the union with provenance per name: 10 audit3 KILL cells vs 64 legacy names, 1 shared (`futures_momentum`) |

Three notes where v3 is right in a way that changes work order:

1. **`STRATEGY_DISCOVERY_PROTOCOL.md` has no "why should this edge exist" filter.** Its
   novelty and correlation-prune gates screen the *statistics* of a candidate, not its
   economic prior, and its cost table predates the measured slippage telemetry
   (0.0997% CRYPTO, 0.05% EQUITY, ETF = 234% of per-trade PnL). Prepend an economics
   pre-filter before anything else in that protocol is reused.
2. **`TESTING_PROTOCOL.MD` §6–§8 is a variant-generation machine.** Seven rehab stages
   mutating failing parents into children silently resets multiplicity — each child
   arrives looking like a fresh trial. Its Section 0 gates are sound; the rehab pipeline
   needs `cumulative_trials` threaded through before it can run again.
3. **EAGLE Grok-4.3's Tier-1 picks were backtest-size, not realized.** `stocks_rsi2`
   PF 4.76 and `crypto_liquidity_wick_reversal_v1` n=4,904 are backtest rows; the
   realized cohort is n=43 at +0.15%/trade, which is below round-trip cost. This is the
   most expensive confusion in the repo and the reason the coverage panel now states the
   denominator on every audit3 render.

Agreed with v3's bottom line: **nothing on `/audit` is worth sizing today.** The
difference is that the mechanism to prevent it is now enforced rather than described —
killed cells are blocked at ingest and at write, class kills admit only
CANDIDATE/PROVEN_T2 cells, and only a pre-registered pod can promote.
