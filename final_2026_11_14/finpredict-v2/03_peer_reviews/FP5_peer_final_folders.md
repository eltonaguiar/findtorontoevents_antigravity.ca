**COVERAGE: PASS** — all five named peer packages read on `origin/main`; see "Coverage verdict" below.

# FP5 — Final-Stage Review of Peer `final_2026_11_14/` Packages

**Reviewer:** FP5
**Review clock:** 2026-11-14T20:35Z
**Root:** `/home/eaguiar2015/findtorontoevents_antigravity.ca`
**Method:** read-only. Peer trees were extracted from `origin/main` into `/tmp/kilo/fp5` (`git archive origin/main final_2026_11_14`) so no repo source, data, or peer artifact was touched. The only file written is this report.
**Baseline compared against:** `05_final/FINAL_SYNTHESIS.md`, `05_final/PEER_CLAIMS_MATRIX.md`, `README.md`, `03_peer_reviews/FP4_peer_folder_sweep.md`.

---

## Coverage verdict

**PASS** — all five named peer folders exist on `origin/main` and every mandated index/executive-summary/peer-review-synthesis file was read. Two path corrections to the brief:

| Brief said | Actual on `origin/main` |
|---|---|
| `quant-audit-2026-11-14/01_peer_reviews/*` | Present **and** tracked (5 per-peer adjudications). The 6-peer synthesis is in `03_peer_reviews/PEER_REVIEW_SYNTHESIS.md`, not `01_peer_reviews/`. |
| `finpredict-v3/02_tools_guardian/` for both tools | `pi_data_hygiene.py` and `pi_fundamental_ranker.py` are in `02_tools_guardian/tools/`; `pi_horizon_validation.py` is duplicated byte-identically in `02_tools_guardian/tools/` and `04_research_validation/` (`diff` clean). |

Also present but **not** on `origin/main`: `final_2026_11_14/childlike-airport/` (local only; its VWAP claim is already falsified in our package). Out of scope here.

`final_2026_11_14/` on `origin/main` now contains exactly: `finpredict/`, `finpredict-v2/`, `finpredict-v3/`, `flaxen-hair/`, `quant-audit-2026-11-14/`. Our `FINAL_SYNTHESIS.md` §4.5/§8 statement that "no peer folders existed at review time" is **stale as of 20:24Z** and must be corrected.

---

## 1. Per-folder inventory

### 1.1 `final_2026_11_14/finpredict/` (v1) — 28 files

**Purpose:** full live-system audit → peer reconciliation → master remediation plan → pre-registered profitability research (ITERATION-001..005).

**Index/exec:** `README.md` (55 lines); `03-peer-review/PEER_RECONCILIATION.md` (116); `04-master-plan/PLAN.md` (76).

**Key findings and numbers:**
- Verdict FAIL, unanimous 5/5 peers. WR 41.8%, PF 0.94, expectancy −0.11/trade, Sharpe −1.31, compounded −62.65% (rolling-100) / −99% (equal-weight), 30d maxDD 31.2%; policy-clean PF 0.2657.
- 365 workflows (361 active), 28 last-run failures; 4,148 raw actives; 3,377 EXPIRED in `active_raw`; 691 OPEN of which only 123 (17.8%) carry a live entry-differing quote.
- 127-pick "verified strategies" batch, 123 (96.9%) frozen; 11 frozen FOREX closed phantoms; fabricated flat-3% cohort (286 trades, every win exactly +3.00%, zero losers); `stock_forex_prices.json` 217 d stale.
- Research: 683-zoo has no edge (ITERATION-001..003); diversified vol-targeted trend claimed **"PROVEN"** in ITERATION-005 (Sharpe 2.13, CI [1.25,3.25], t=5.56); author admits B&H of the same 10 had Sharpe ≈2.2.
- Master plan: Phase 0 P0-1..P0-12, Phase 1 data gates, Phase 2 resolver, Phase 3 re-validation; binding veto list.

**New claims not in our matrix:** ITERATION-005 "PROVEN" trend (C3), P0-3's `update-environment:false` root cause (see §2, contradicted), `resolution_kind` split, P0-9 vacuous PASS, P0-11 sidecar hide-if-stale, P0-12 tracked Google API keys.

### 1.2 `final_2026_11_14/finpredict-v3/` — 22 files

**Purpose:** data-hygiene audit + runnable guardian + ML/horizon validation + R2 peer reviews.

**Index/exec:** `README.md`, `05_final/FINAL_SUMMARY.md`, `03_peer_reviews/00_INDEX.md`, `03_peer_reviews/PEER_REVIEW_R2_OVERALL.md` (the review synthesis).

**Key findings:** 2 stale crypto prices pinned to entry, 11 frozen closed FOREX phantoms, 3 date-only seeds, null-price BOND/FUTURES, survivorship 7,914/16,126 (49%), dead metric sections; guardian exit-1 on findings (14 tests); horizon harness **0/6 groups pass at n≥60, 0/26 at n≥30**; ML target leakage in `ml_gatekeeper/gatekeeper.py:170-186`, masked ON by default via `d8c8dd25581` on `origin/main` (needs sign-off); "0 rows have both `bt_trades>0` and `fwd_trades>0`"; recommends adopting v2 as reconciliation backbone and scratch `QW-ALL-1..9` as checklist.

**New claims:** horizon harness result (independent corroboration of 0 proved); backtest↔forward overlap = 0; `d8c8dd25581` needs coordinator sign-off; v3's claim "361 families + 285 baby + mutation lab ⇒ ~260 lucky PF>1.5 survivors expected at p=5%" — see §2, arithmetic suspect.

### 1.3 `final_2026_11_14/flaxen-hair/` — 518 files (135 md, 197 json, 13 py, 173 other)

**Purpose:** audit + "statistically valid profitable edge" (mega_mutation) + peer-review copies of v4's contest research and scoring framework.

**Index/exec:** `README.md`; `03_profitable_approach/{PROFITABLE_APPROACH_PROVEN,TRUE_PROFITABILITY_VALIDATED}.md`; `07_recommendations/README.md`.

**Key findings:** mixed PnL units (ratio vs percent, up to 100×), 4,202 closed picks; mega_mutation claimed forward n=50, WR 84%, PF 8.32; Task-10 bootstrap on n=8/n=9 (PF 11.71/7.40); 8 tournament combos; recommends `production_enable=true`.

**Inventory gap:** the `README.md` advertises 8 subfolders, but only 5 exist on `origin/main` (`01_audit_findings`, `02_peer_review` incl. nested `scratch-hippodraco_audit/`, `03_profitable_approach`, `05_statistical_validation`, `07_recommendations`). Advertised but **absent**: `04_gated_scanner/`, `06_data_fixes/`, `08_raw_evidence/` (the README calls the last "reserved for future dumps"). The scripts it cites (`gated_scanner.py`, `daily_forward_tracker.py`, `normalize_pnl_units.py`) are therefore not in this package — they live in the worktree/`quick_wins/` tree, so the "production-ready scanner" claim is not carryable from the deliverable alone.

**Internal contradictions (within flaxen-hair itself):**
- `README.md:50` and `TRUE_PROFITABILITY_VALIDATED.md:45` say `production_enable=true`, `promotion_ready=true`; `PROFITABLE_APPROACH_PROVEN.md:58` says **both false** (blocked by `pf_drift>30%`).
- `PROFITABLE_APPROACH_PROVEN.md:12` says "MC pct=0.99"; `TRUE_PROFITABILITY_VALIDATED.md:25,30` says 0.949 (m084) and 0.692 (m048) — "1 of 4 clears MC top decile".
- It states "positive forward drift (8.32 vs lab 2.79) is confirmation, not a problem" — i.e. a risk gate was **loosened** to admit the anomaly. That is a process red flag, not validation.
- It repeats "live dashboard shows 0 active picks (Alpha Engine dead)" (`07_recommendations/README.md:31`), the stale-repo-snapshot error our package already refuted (live = 20 curated).

### 1.4 `final_2026_11_14/quant-audit-2026-11-14/` — 23 files, two authors

**Purpose:** (a) opencode 166-cell money-ready screener; (b) a later independent "Freebuff" pass that adjudicates every peer claim by re-execution.

**Index/exec:** `00_executive_summary/README.md` (70 lines), `05_final/VERDICT.md`, `03_peer_reviews/PEER_REVIEW_SYNTHESIS.md`, `01_peer_reviews/{deepai_live_audit,kilo_childlike_airport,iteration_005,finpredict_family,seer_scratch_flaxen}`.

**Key findings:**
- 0/166 strategy×class×direction cells pass the Tier-2 gate; all 166 are single-source; only 1 cell clears n≥100 (`luxalgo_confluence` CRYPTO LONG, n=563) and it fails WR/PF/MDD.
- deepAI variant C **reproduced exactly** on the live 34.58 MB payload: n=237, WR 47.3%, PF 1.26, +98.7pp, null 0/800, **z=−0.84** (peer omitted z).
- Kilo VWAP refuted on its own numbers: implied annualized vol 1.84% at 40% sizing is impossible; PBO gate written as `<0.5` is inverted; repo's own `docs/BACKTEST_ADMISSIBILITY_STANDARD.md` requires PBO ≤ 0.10.
- ITERATION-005: internally consistent but "PROVEN" is wrong — t=5.56 tests mean>0, which beta passes; independent TSMOM365 OOS Sharpe 0.57, null p=0.200.
- `resolution_method` is `None` for **all 3,500** `recent_closed` rows; 3,500 rows = LOST 2,043 / WON 1,446 / CLOSED 11; only 11 exact-zero PnL (0.3%); range 2026-02-21 → 2026-11-14.
- 30-day screen: PF 0.804, Σ −443.1pp, WR 41.8%; 0 emitters at Bonferroni 2.82e-4.

**Internal contradiction:** `05_final/VERDICT.md:48,83` and `README.md:98` still **recommend deploying Kilo's VWAP** as the first production candidate, while `00_executive_summary/README.md` and `01_peer_reviews/kilo_childlike_airport/REVIEW.md` refute it as arithmetically impossible. The VERDICT section is stale relative to the same folder's exec summary.

### 1.5 `final_2026_11_14/finpredict-v2/` (ours)

Reviewed as baseline only: `FINAL_SYNTHESIS.md`, `PEER_CLAIMS_MATRIX.md`, `README.md`, `FP4_peer_folder_sweep.md`. Our synthesis is correct on verdict and on VWAP/deepAI/mega-mutation/path-to-profitability falsification, but it **omits ITERATION-005**, and its deepAI status is now superseded (§2, C1).

---

## 2. Agreements and contradictions vs our synthesis

`[OURS]` = `FINAL_SYNTHESIS.md` / `PEER_CLAIMS_MATRIX.md` position.

| # | Claim | Peer position | Ours | Resolution |
|---:|---|---|---|---|
| A1 | System not money-ready | v1 0/9 classes; v3 0/9; quant 0/166 cells; every peer FAIL | 0/9 money-ready, fleet PF 0.2657 | **AGREE.** Add quant's 0/166 cell count as the finest-grained independent confirmation. |
| A2 | PnL-unit mix is the #1 correctness defect | v1, v3, flaxen, quant all rank it first | C0 canonical unit | **AGREE on defect, disagree on canonical unit** (see C7). |
| A3 | Zombie/EXPIRED drain is #2 | v3 + quant + v1 | C1 terminal resolver | **AGREE.** Add A3's missing field: `resolution_method` (see A6). |
| A4 | Single-source concentration | quant: all 166 cells single-source; 94–98.5% one source | 84.9% of outcomes from 2 emitters; 21 winners in one cluster | **AGREE.** Quant's cell-level gate is stronger evidence than our aggregate share. |
| A5 | Backtest↔forward disconnect | v3: **0 rows** have both `bt_trades>0` and `fwd_trades>0` | Not stated | **NEW — adopt.** It independently explains why "forward validation" in the dashboard is vacuous. |
| A6 | `resolution_method` missing | quant/deepAI review: `None` for 100% of 3,500 `recent_closed` | Not stated (we say 63% never resolve) | **NEW — adopt.** "You cannot tell TP from timeout" blocks certifying any PF, including variant C. |
| A7 | VWAP claim is invalid | quant refutes independently (implied vol 1.84%/yr; PBO gate inverted; regime `UNKNOWN` trades anyway) | FALSIFIED (Sharpe ~1.18, t=0.91, CSCV PBO 0.84–0.97, intrabar PF 0.81) | **AGREE, complementary.** Add the PBO-gate inversion and the repo's own PBO≤0.10 standard. |
| A8 | Edge search negative | quant 0/40 with pre-committed nulls | 0/40 verified negative | **AGREE.** |
| A9 | mega_mutation | flaxen: PROVEN, production_enable=true; quant: LF/MDD table shows MDD 209.6% (implausible) | NOT_PROVED / FALSIFIED as "proven"; strict TP n=16, WR 68.75%, PF 5.19 | **AGREE with ours.** Quant's MDD 209.6% is itself a unit/denominator defect (see U4). |
| A10 | Vacuous PASS | v1 P0-9 (and our own recommendations) | Not in FINAL §7 | **AGREE + MISSING from synthesis.** Add to next steps. |
| A11 | Horizon/stationarity negative | v3: 0/6 (n≥60), 0/26 (n≥30) | 23 candidates, 0 proved | **AGREE.** Strong independent corroboration; add to §3. |
| C1 | deepAI variant C | quant: **REPRODUCED EXACTLY** on the live 2026-11-14 payload (n=237, PF 1.26, z=−0.84, null 0/800, p≤0.00125) | `PEER_CLAIMS_MATRIX` #6: **"FALSIFIED as stated / UNVERIFIED"**; our FP2 got n=764, PF 0.906 on the **Oct-23** payload | **CORRECTION to ours.** Change status to: *headline REPRODUCED on the live payload; still NOT an edge* — z=−0.84 (WR below coin flip), the null tests selection-vs-random-selection over clone re-emissions (2,262), resolution provenance unknown, slippage undeducted, Bonferroni over 4 variants only. Keep "not capital-ready"; drop "unverified". Our Oct-23 flip stays as a separate payload-sensitivity note. |
| C2 | Funding carry | quant: Sharpe is a volatility artifact; run-length-preserving block null turns p 0.002 → **1.000** | "Funding carry is **real** but capital-adjusted 3.7–4.8% vs 4.5% cash"; "Is there a real edge anywhere? Only low-vol carry" | **CONTRADICTION — tighten ours.** Nominal carry economics exist, but the risk-adjusted claim is null-unconfirmed. Reword §1 and §4/§6: "no proven risk-adjusted edge; nominal carry < cash." Do not headline funding carry as "the only real edge". |
| C3 | Closed-ledger PF | quant/deepAI: 30-day PF 0.804, Σ −443.1pp, WR 41.8%; v3/our earlier review: 42.21% | 0.2657 policy-clean, WR 42.21%, z −23.60 | **SURFACE, not contradiction.** WR agrees (~42%); PF differs because policy-clean full-ledger ≠ 30-day window. Name array + window for every PF; never quote one as "the" PF. |
| C4 | Active-pick count | v1/v2/v3 20 curated / 4,148 raw; quant 10 displayed / 4,361 tracked at −1.90% | 691 OPEN, 177 quoted, 123 non-zero | **SURFACE.** 123 non-zero is common to v1 and ours. Name array and clock. |
| C5 | Workflow count | v1/quant 365; our MASTER 365 | 365 | **MINOR UNVERIFIED:** repo has 360 `.yml/.yaml` files at 20:35Z (plus `.retired/.disabled/.draft`). 365 may include API-registered/retired entries. Do not restate without the counting rule. |
| C6 | `update-environment:false` root cause | v1 P0-3: "**197** workflows set `update-environment:false`, so setup-python never activates" | We don't state the mechanism, only the "Python-3.14/pandas cluster" | **PEER IS FACTUALLY WRONG — verified.** `grep -rl "update-environment: false" .github/workflows` → **0 files**; `update-environment: true` → **197 files**. The named failing cluster (`signal_tracking`, `alpha-engine-fast`, `forward-test-new-strategies`, `autonomous_trading`, `copy-trader-intelligence`) all use `setup-python@v6`, `update-environment: true`, pinned 3.11/3.12. Do **not** adopt P0-3's diagnosis; the 3.14 masquerade root cause is UNVERIFIED. |
| C7 | Canonical PnL unit | flaxen `normalize_pnl_units.py`: recompute as **decimal ratio** | C0 + FP4: **percent-at-write**, `pnl_source`, recompute-or-NULL, never magnitude-guess | **DESIGN CONTRADICTION.** Percent-at-write wins: the ratio convention is what silently turns +150% into 1.5%. Adopt scratch `QW-ALL-2`; do not use flaxen's normalizer as canonical. |
| C8 | mega_mutation production state | flaxen docs disagree with themselves (true vs false) and loosened `pf_drift` to accept forward PF 8.32 vs lab 2.79 | NOT_PROVED; do not enable | **RESOLVED in our favour.** A gate was relaxed to admit the claim; that is itself disqualifying. Keep production disabled. |
| C9 | ITERATION-005 trend | v1: "PROVEN"; quant: PARTIAL, mislabelled; independent TSMOM365 OOS 0.57, null p=0.200; 2,490 bars/7.4y = 336/yr (8% gap); PF 1.40 is a bar ratio | **Absent from FINAL and from PEER_CLAIMS_MATRIX. FP4 covered it but the synthesis did not carry it.** | **NEW CLAIM — must add.** Label `PILOT / risk-premium harvest, benchmark-relative alpha unproven`: B&H Sharpe ≈2.2 > 2.13; PF 1.40 < its own PROOF_PROTOCOL PF>1.5 gate; no DSR at N=683; no full walk-forward; bull-only window. |
| C10 | Sample sizes for multiple testing | v1/ours 658–683; v1 PROOF_PROTOCOL α=7.3e-5 at N=683; quant Bonferroni 2.82e-4 (implies N≈177 emitters); flaxen framework example m=150; v3 "~260 expected PF>1.5 survivors" | 658 strategies, E[FP]=32.9, α=0.05/683 | **RESOLVE BY SCOPE.** 658 = ledger strategy search space; 683 = pre-registered research universe; 177 = emitter-level. v3's "~260" is inconsistent with 646×0.05≈32 — **mark UNVERIFIED/arithmetic-suspect**; do not adopt. flaxen's m=150 understates the family. |
| C11 | "0 active picks / 26-day-old dashboard" | v4 INDEX (already refuted by us); flaxen `07_recommendations` repeats it | live 14:30Z payload: 20 curated, 3,500 closed, 1.63 h | **PEER STILL WRONG.** Keep our refutation; add flaxen's repetition to the stale-claim list. |
| C12 | `PF 1.40` meaning | quant: bar-level ratio, not trade PF | Not stated | **NEW — adopt as a definition footnote** wherever ITERATION-005 is cited. |

---

## 3. Contest research — `flaxen-hair/02_peer_review/finpredict_tradingview_contest_research.md`

### 3.1 Are the claims sourced?

| Claim class | Source | Reproducible? |
|---|---|---|
| Leaderboard winners: BenBernanke1 +5,220.72%/94% WR/59,187 contestants; yxiao8911 +1,673.74%; Me-tis +155.95%; Manishh_jain92 +271.78%; ICT_Hispanohablantes +308.07%; KingBob09 +45.58%/43%; prodigy5284 +17.58%/95% | TradingView "The Leap" URL, "accessed 2026-11-14" | **No.** No archived page, no leaderboard-entry URL, no snapshot. **UNVERIFIED** from this host. |
| "Live results are 60–70% of backtests"; 4+ timeframe alignment; daily −5%/monthly −20% caps | LuneFi blog URL | **No** — secondary blog, no dataset. **UNVERIFIED.** |
| Repainting/look-ahead in >90% WR strategies | Forex Factory thread | Plausible and widely documented, but the specific thread content is **UNVERIFIED**. |
| "MomentumEMA is #1 family: 42 of 155 (27.1%)"; "76 of 155 winners closed at 14:00Z/21:00Z"; "RSI<35 / volume>2× / BB width<0.04" | Internal: `reports/2026-10-22-top10-winners-reverse-engineered.md`, `alpha_engine/{prove_winners,winner_reverse_engineer}.py` | **Yes — verified.** The report exists on `origin/main`; line 56 gives 42 (27.1%), line 65 gives 21:00Z=44 + 14:00Z=32 = 76. Arithmetic checks out. `/tmp`-style absence does **not** apply here; these files are in-repo. |

### 3.2 Is it reproducible as a *method*?

Partly. `alpha_engine/winner_reverse_engineer.py` and `alpha_engine/prove_winners.py` exist, and `alpha_engine/data/prove_winners_results.json` is committed, so the internal reverse-engineering can be re-run. The external leaderboard numbers cannot be re-derived from anything in the repo, and no contest-id / trade-log snapshot is stored.

### 3.3 Does it support the conclusion drawn?

**No.** Three defects make it non-probative:

1. **Outcome-selected cohort, no control group.** The 155 rows are "genuine **WON** rows", ranked by realized PnL. Every "winner feature" (MomentumEMA share, close-hour cluster, RSI/volume signatures) is computed on winners only. With no losing cohort, this describes what winners *look like*, not what *predicts* winning. It cannot distinguish an edge from the base rate.
2. **Two post-hoc selection layers presented as action items.** "Add the missing proven-winner symbols" (AUDJPY, GBPJPY, BAT-USD, CRV-USD, ZECUSDT, WLD-USD, XTZ-USD, MINAUSDT) and "schedule/locate entries to capture the 14:00Z/21:00Z resolution windows" are data-mined from the outcome-selected set. The time-of-day cluster is especially suspect: our audit already documents batched `last_checked` stamps, hourly cron, and resolver batching. **Resolution time is a property of the resolver clock, not the signal.** Scheduling *entries* to match *exit* clustering is a category error.
3. **Extreme-order-statistic fallacy.** Winners are the max of 25k–107k contestants. Matching their surface features is expected by chance; the document lists the base rate (contestant counts) but never conditions on it. Its own §9 acknowledges survivorship, then §10 recommends copying the survivors — the acknowledgement and the recommendation contradict each other.

### 3.4 Does it add a valid edge or another multiple-testing layer?

**Another multiple-testing layer.** It is a legitimate *descriptive* study of an outcome-selected sample, and the two archetypes (high-WR grinder vs high-R:R sniper) are a reasonable hypothesis taxonomy. As evidence of a tradeable edge it is non-probative, and its recommendations would add two new unregistered trials (8 symbols × 2 time windows) to a search space that is already the reason the system's 683-zoo fails. Treat as hypothesis generation only.

One claim in it *is* useful and should be kept: "paper contest winners are not position-sizing like real traders — 10–20% of equity per trade because there is no drawdown consequence" (§4, §7). That is the correct explanation for the +5,220% headline and should be quoted whenever a contest number is used as a benchmark.

---

## 4. Scoring framework — `flaxen-hair/02_peer_review/finpredict_profitable_scoring_framework.md` + `.py`

### 4.1 What it gets right

- A 6-gate structure (data quality → significance → walk-forward → gross → net-of-cost → direction) is **materially better than a single composite score**. It operationalises "n≥100/200", "PF CI lower > 1.0", "net of costs", and "score LONG and SHORT separately".
- Direction-specific certification (§7) is a genuine addition: it would have caught the path-to-profitability 25-row/64-row SHORT/LONG cell artifact.
- §9.1 ("never filter closed trades by profitability before scoring; the only valid filter is temporal") is exactly right and is the correct rule.

### 4.2 What invalidates it as a certification gate

1. **The DSR implementation re-creates the VWAP bug and saturates at 1.0.** `sharpe_ratio()` returns an **annualized** Sharpe (`×√252`, line 121-132), but `deflated_sharpe_ratio()` (line 169-203) builds `sr_var` from the **per-period** standard error `1/(n-1)` and then computes `z = sr_adj / sr_std`. Passing an annualized Sharpe into a per-period SE inflates z by ≈√252 ≈ 15.9×. Reproduced with the framework's own formula:

   ```
   n=252, m=150, annualized SR=0.50
     as implemented          DSR = 1.0000   (PASS)
     correct (per-period SR) DSR = 0.0241   (FAIL)
   ```

   A true Sharpe of 0.50 with 150 trials must fail; the gate returns 1.0. This is the same "DSR 1.0000" pathology that got the VWAP claim refuted.
2. **The cross-trial variance `V` is never estimated.** The call site passes `v_ratio=0.0` always ("for single-strategy cert, V=0"), so the deflation only uses a Sidak `ppf(1−1/m)` term. The variance of Sharpe across trials — the core of Lopez de Prado's DSR — is absent.
3. **No PBO/CSCV, no SPA/Reality Check.** The two tests that actually killed VWAP and the 683-zoo are not in the framework. DSR ≠ PBO.
4. **i.i.d. bootstrap.** §5.1 resamples trade returns independently, ignoring autocorrelation/serial dependence; our protocol uses block bootstrap/CSCV precisely because daily/4h returns are serially dependent.
5. **The document's sample-size examples contradict its own code by ~2×.** The formula in §2.1 with the stated z-values gives **783** for 50%→55% and **194** for 50%→60%; the document states **385** and **100**. `minimum_sample_size()` in the `.py` implements the formula correctly, so the *document* is wrong and the `n≈385` teaching example is wrong. At n=100 the framework is underpowered to detect the 5pp edge it claims to detect.
6. **It cannot certify the claim it is said to validate.** Gate 0 requires n≥200 for money-ready and n≥100 for validation; mega_mutation has forward n=50 and Task-10 ledgers n=8/n=9. `flaxen-hair/README.md:58` says the framework "validates our mega_mutation edge" — **it cannot**; mega_mutation fails Gate 0 before any statistic is computed. This is a direct, checkable contradiction inside the peer package.
7. **Metric definitions omit PBO and effective-N.** The example JSON uses `m=150`; the measured ledger family is 658 strategies (emitter family 177). Using 150 understates the correction.

### 4.3 Verdict

The framework **adds a useful checklist but not a valid gate**; as implemented it is a **new false-certification layer**, because a saturating DSR gate will pass almost anything. Do not adopt as-is. Adopt its gate *structure* (Gates 0–4) merged into our C2, with:
- per-period Sharpe inside DSR (or deflate annualized Sharpe with the matching annualized SE),
- `V` estimated from the actual trial set,
- CSCV PBO ≤ 0.10, SPA/Reality Check,
- block bootstrap,
- N = measured family size (658 ledger / 683 research), not 150,
- Unit contract applied before any metric (C0).

---

## 5. `quant-audit-2026-11-14` peer reviews — agreement and corrections

### 5.1 Do they agree with our verdict?

**Yes, without dissent.** `01_peer_reviews/finpredict_family/RECONCILIATION.md` rates the finpredict family **CORROBORATED** ("four independent methods, one conclusion"), endorses our veto list verbatim, and calls our correction table "the most useful reconciliation artifact produced by any peer". `03_peer_reviews/PEER_REVIEW_SYNTHESIS.md` records consensus on NOT money-ready, broken pipeline, EXPIRED→WON, single-source concentration, PnL-unit contract, zombie drain.

### 5.2 Corrections to our numbers / statuses

| Item | Quant-audit finding | Effect on us |
|---|---|---|
| deepAI variant C | Reproduced exactly on the live payload; z=−0.84; 4/8 months negative; null tests selection over clones | **Change matrix #6 from UNVERIFIED to REPRODUCED-BUT-NOT-AN-EDGE.** Keep all our methodological objections. |
| `resolution_method` | `None` for 100% of 3,500 rows | **Add to C1**; it is prior to any PF certification. |
| recent_closed composition | 3,500 = 2,043 LOST / 1,446 WON / 11 CLOSED; 11 exact-zero; range Feb 21 → Nov 14 | **Name the array.** Our "42.2% WR" vs their 41.3% (1,446/3,500) differ by ~31 rows; our "63% never resolve" refers to the full picks population, not this array. Add both denominators. |
| 30d PF | 0.804, Σ −443.1pp, WR 41.8% | **Surface difference** from our 0.2657 policy-clean; do not merge. |
| QW/acceptance tests | Our acceptance tests are mostly "field exists", not "number is honest"; proposes `resolved+expired+open = emissions` and "synthetic null panel must reject ≥95%" | **Adopt both as falsifiable acceptance gates.** |
| deepAI branch | Based on `f54efb3b4ac`, 23,488 files / 29.7M deletions apart; no merge base | **Confirms our copy-don't-merge warning**; we independently re-confirmed empty `merge-base` and 8,781/85,617 commit divergence. |
| Workflow hygiene | 7 workflows failing (quant scope) vs our 24/24h, 88/7d | Different windows/scopes; no conflict. |
| `resolution_method` vs deepAI's earlier claim | deepAI's DB report says 28,218 zero rows are `resolution_method=TIME_EXPIRED` in `at_signal_outcomes`; quant says `None` in the `recent_closed` payload | **Surface mismatch, not contradiction** — two tables. State both. |
| MDD 209.6% / 289.5% | Presented for mega_mutation and `luxalgo_confluence` | **Implausible >100% drawdown** → unit/denominator defect. **UNVERIFIED;** do not cite. |

### 5.3 Internal defect in the peer folder we must not propagate

`05_final/VERDICT.md:48` and `:83` and `README.md:98` recommend **deploying Kilo's VWAP** as the first production candidate, while `00_executive_summary/README.md` §3 and `01_peer_reviews/kilo_childlike_airport/REVIEW.md` refute it as arithmetically impossible. A reader who opens only `VERDICT.md` would deploy a falsified strategy. Our synthesis should cite the exec summary/peer review, never `VERDICT.md §2/§5`.

---

## 6. Tools and master-plan actionables we missed

### 6.1 `finpredict-v3/02_tools_guardian/tools/pi_data_hygiene.py` (324 lines)

Adoptable: exit 0/1/2, `--asof`, `--show`, CI-gateable; tags `STALE_CRYPTO_PRICE`, `FROZEN_CLOSED_PHANTOM`, `DATE_ONLY_SEED`, `NULL_PRICE`, `PLACEHOLDER_ENTRY`; `FABRICATED_FLAT_PNL_COHORT`; per-class live-quote vs signal-age table; `ACTIVE_RAW ZOMBIE SCAN`.

Defects to fix before adopting:
- `FLAT_PNL_TARGET = 3.0` assumes **percent** units. Under the very unit-mix bug it is auditing, a fraction-unit row of `0.03` is not flagged → the flat cohort detector under-reports. Must accept {3.0, 0.03} or run after C0.
- `classify_closed` only flags `pnl==0 & reason=="UNKNOWN" & exit==entry`; misses nonzero-PnL rows with `UNKNOWN` exit provenance.
- No machine-readable JSON output (only `--json` *input*); no severity/`--fail-on`.

### 6.2 `finpredict-v3/04_research_validation/pi_horizon_validation.py` (204 lines)

Adoptable: phantom filter, chronological windows, Wilson lower bound, PF>1.05, win-majority windows, explicit survivorship warning. It produces the strongest independent negative we have: **0/6 at n≥60, 0/26 at n≥30** on 3,489 resolved trades.

Defect: **`MIN_WINDOWS = 4` is declared and documented but never used.** `run()` accepts a group with 1 non-empty window, and `win_ok = win_windows >= 0.66*nonempty_windows` makes `2/2` a pass. The stationarity gate is therefore weaker than advertised. Add `nonempty_windows >= MIN_WINDOWS` before the win-majority test. Also, exit code `0 if groups_passed == 0 else 1` is inverted relative to the guardian's convention; document it.

### 6.3 `finpredict/04-master-plan/PLAN.md` — items absent from our `FINAL_SYNTHESIS §7`

| Item | Why it matters |
|---|---|
| P0-5 entry-price sanity gate + stop `None→0.0` (`prediction_market_consensus.py:589-591`) | Prevents the XRP entry=0.0 garbage row; we only mention it indirectly. |
| P0-9 vacuous PASS (`activeCount==0 → INSUFFICIENT_DATA`/`NOT_BUILT`) | BOND currently renders green PASS with 0 picks. |
| P0-11 sidecar freshness manifest + hide-if-stale | We list stale sidecars but have no hide-if-stale gate in §7. |
| P0-12 security (tracked Google API keys ×2; `dbpasses.txt` not gitignored) | Not in our ordered next steps. |
| P1 `resolution_kind` split (`price_resolved`/`clock_expired`/`never_priced`) | The missing companion to `resolution_method`. |
| P1 class-health contract + `tests/test_dashboard_payload_contract.py` | Turns labels into CI assertions. |
| Phase 3 PBO with T≥1000 (not 21) + Reality Check | Our C2 names PBO but not the T≥1000 requirement. |
| P2 server quote pipeline with **fail build <80% coverage** | Our C4 lacks the coverage-gate threshold. |

Do **not** adopt P0-3 (`update-environment:false`) — see C6, verified wrong.
Also correct v1's P0-4: it spaces the cron to p95 **84.5 min**; our GA measurement is p95 **111.6 min** (p50 97.2). Use 111.6.

---

## 7. Required `FINAL_SYNTHESIS.md` edits (exact targets)

| # | Target file / section | Change |
|---:|---|---|
| 1 | `05_final/FINAL_SYNTHESIS.md` §4.5 and §8 bullet 2 | Delete "no peer `final_2026_11_14/<peer>/` folders existed at review time". Replace with: five peer folders present on `origin/main` at 20:24Z, reviewed in `03_peer_reviews/FP5_peer_final_folders.md`. |
| 2 | `05_final/FINAL_SYNTHESIS.md` §1 table, row "Is any peer claim proved?" | Change "No" to "No — but deepAI variant C reproduces on the live payload as a selection result, and ITERATION-005 is a credible risk-premium harvest; neither is an edge." |
| 3 | `05_final/FINAL_SYNTHESIS.md` §4.3 | Replace "No Nov-14 payload … UNVERIFIED" with: quant-audit reproduced n=237/PF 1.26 on the live payload; **z=−0.84**, null 0/800 (p≤0.00125), 4/8 months negative, selection-over-clones, `resolution_method` unknown, slippage undeducted. Keep our Oct-23 payload flip (n=764/PF 0.906) as a payload-sensitivity note. |
| 4 | `05_final/FINAL_SYNTHESIS.md` §1 row "Is there a real edge anywhere?" and §4/§6 funding-carry sentences | Remove "Only low-vol carry" / "Funding carry is real". Replace: "No proven risk-adjusted edge. Nominal funding carry exists but is below cash after capital (3.7–4.8% vs 4.5%) and its Sharpe is not significant under a run-length-preserving block null (p=1.000)." |
| 5 | `05_final/FINAL_SYNTHESIS.md` §4 (new §4.6) | Add **ITERATION-005 / diversified vol-targeted trend**: Sharpe 2.13, CI [1.25,3.25], t=5.56, 10/10 assets; B&H same 10 ≈2.2; PF 1.40 is a bar ratio and fails its own PF>1.5 gate; 2,490 bars/7.4y = 336/yr; no DSR at N=683; independent TSMOM365 OOS 0.57, null p=0.200. Verdict `PILOT — risk premium, benchmark-relative alpha unproven`. |
| 6 | `05_final/FINAL_SYNTHESIS.md` §5 root cause C1 | Add: `resolution_method` is `None` for 100% of the 3,500-row `recent_closed` ledger; exit provenance must be a required terminal field before any PF is certifiable. |
| 7 | `05_final/FINAL_SYNTHESIS.md` §3 research table | Add a footnote row: independent horizon harness (v3) — 0/6 groups at n≥60, 0/26 at n≥30; 0 rows with both `bt_trades>0` and `fwd_trades>0`. |
| 8 | `05_final/FINAL_SYNTHESIS.md` §7 next steps | Insert into C1/C4: vacuous-PASS fix, entry-price sanity gate, sidecar hide-if-stale, `resolution_kind` split, quote-coverage build gate (<80% fails), Wilson CI + excluded counts in the payload. Add P0 security item (tracked Google keys, `dbpasses.txt` gitignore). Do **not** add `update-environment` (C6). |
| 9 | `05_final/PEER_CLAIMS_MATRIX.md` row 6 | Update deepAI status as in §5.2/C1. |
| 10 | `05_final/PEER_CLAIMS_MATRIX.md` — append rows 14–19 | 14 ITERATION-005 trend `PILOT/NOT_PROVED`; 15 flaxen 6-gate framework `INVALID AS IMPLEMENTED` (DSR saturates); 16 TradingView contest research `UNVERIFIED externally / descriptive-only`; 17 `resolution_method=None` `VERIFIED DEFECT`; 18 funding carry `ARTIFACT under block null`; 19 mega_mutation `production_enable` `SELF-CONTRADICTORY`. |
| 11 | `01_audit/PEER_CROSSREF.md:15` and `:63` | Correct the stale "not on origin" statement — the branch is `origin/audit/live-audit-2026-11-14` @ `cc0226bdaf0`; no merge base, copy-don't-merge. |
| 12 | `03_peer_reviews/FP4_peer_folder_sweep.md` §5 header + §6 table | Mark the "no peer folders / 05_final empty" coverage FAIL as **superseded at 20:24Z**; point to this report. |
| 13 | `03_peer_reviews/FP2_deepAI_profitable_v1.md` header (or an appended erratum) | Add a one-line erratum: headline reproduces on the live payload; our Oct-23 run is a payload-sensitivity result, not a refutation of the live claim. |

---

## 8. `UNVERIFIED`

- TradingView "The Leap" leaderboard figures (all seven winners, contestant counts, access date) — no archived page or trade log; cannot be reproduced from the repo.
- LuneFi "live results are 60–70% of backtests" and the −5%/−20% loss-cap claims — secondary blog, no dataset.
- Forex Factory repainting thread contents.
- The true root cause of the Python-3.14/pandas workflow cluster. The peer's `update-environment:false` diagnosis is **disproved**; the real mechanism was not identified here.
- v1's "365 workflows" vs 360 `.yml/.yaml` files at 20:35Z — counting rule unknown; not resolved.
- v3's "~260 lucky PF>1.5 survivors expected at p=5%" — inconsistent with 646×0.05≈32; no derivation supplied. Arithmetic suspect.
- quant-audit's MDD 209.6%/289.5% and its 0/166 cell table — the JSON (`06_evidence/screener_results_2026-11-14.json`) was not re-run; >100% MDD is almost certainly a unit/denominator error.
- v3's "0 rows have both `bt_trades>0` and `fwd_trades>0`" — reported, not re-queried.
- flaxen mega_mutation `production_enable` current on-disk value — the shipped docs contradict each other; the live JSON was not opened.
- deepAI variant C on any payload other than the live 2026-11-14 fetch and our Oct-23 copy — payload sensitivity is real but the population window is not pinned.
- Whether `origin/audit/live-audit-2026-11-14`'s unrelated history is genuine or a shallow/grafted clone artifact — `merge-base` is empty (re-confirmed), cause not established.

---

## 9. Top 6 findings

1. **Coverage statement in our synthesis is stale.** All five peer folders are on `origin/main` as of 20:24Z (including the previously missing `quant-audit-2026-11-14/01_peer_reviews/`). `FINAL_SYNTHESIS §4.5/§8` and `FP4 §5` must be corrected; `PEER_CROSSREF.md:15/:63` still carries the old "not on origin" claim.
2. **deepAI variant C is no longer UNVERIFIED.** quant-audit re-ran the peer script on the live 34.58 MB payload and reproduced n=237 / WR 47.3% / PF 1.26 / +98.7pp exactly, with **z=−0.84** and 4/8 negative months. Correct the matrix to "reproduced, but a selection effect over clone re-emissions — not an edge"; keep our slippage, Bonferroni, and resolution-provenance objections.
3. **Our synthesis omits ITERATION-005, the strongest positive peer claim.** It is a credible vol-targeted trend risk-premium harvest (Sharpe 2.13), but B&H of the same 10 was ≈2.2, its PF 1.40 is a bar ratio that fails its own PF>1.5 gate, and an independent bear-inclusive TSMOM365 test gives 0.57 with null p=0.200. It must be added as `PILOT — risk premium, alpha unproven`.
4. **The flaxen/finpredict-v4 6-gate scoring framework is invalid as implemented.** Its DSR takes an annualized Sharpe into a per-period SE: with n=252, m=150, true SR 0.50 it returns **1.0000** instead of **0.0241** — the exact VWAP failure mode. `V` is hard-coded 0, there is no PBO/CSCV or Reality Check, the i.i.d. bootstrap ignores autocorrelation, and the document's n≈385/100 examples contradict its own formula (783/194). It also cannot certify mega_mutation (n=50/8/9 vs its own n≥200 gate) despite the peer's README claiming it does. Adopt the gate *structure*; reject the implementation.
5. **The contest research is descriptive, not predictive, and adds a multiple-testing layer.** Internal numbers verify against the committed winner report (42/155 MomentumEMA, 76/155 at 14:00Z/21:00Z), but the cohort is 155 outcome-selected WON rows with no loser control, the external leaderboard numbers are unarchived/unverifiable, and its "add 8 winner symbols" + "target these exit windows" recommendations are post-hoc data mining — the time cluster is most likely resolver/cron batching, not signal timing.
6. **Two independent peer verdicts now converge on the negative, and one peer doc is internally dangerous.** quant-audit's 0/166 cells and v3's 0/6 (n≥60) / 0/26 (n≥30) horizon harness strengthen the verdict; `resolution_method=None` for 100% of the 3,500-row closed ledger is a newly identified blocker that nobody in our package fixed. Meanwhile quant-audit's own `05_final/VERDICT.md` still recommends deploying the VWAP strategy its exec summary refutes — cite the exec summary, never `VERDICT.md §2/§5`. Also: v1's `update-environment:false` root cause is disproved (0 files false, 197 true) and its p95 84.5 min should be 111.6 min.

---

*FP5 complete, 2026-11-14T20:35Z. Read-only: no repo source, data, or peer artifact was modified. Peer claims are attributed to their authors and artifacts; every item that could not be checked directly is listed under `UNVERIFIED`. Arithmetic checks (DSR saturation, sample-size formula, `update-environment` count) are reproducible from the commands and constants quoted above.*
