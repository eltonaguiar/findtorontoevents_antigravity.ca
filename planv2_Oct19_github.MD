# Audit Top Picks: Data Integrity, Evidence and Reliable Publication

**Version:** 2.1, October 19, 2026 -- follow-up live/browser analysis and local-AI refutation

**Deliverable:** GitHub-ready implementation plan, not an implementation or investment recommendation.

**Priority:** Goal #1 -- trustworthy picks and measured performance across every asset class.

**Decision:** Publish no actionable pick when evidence is weak; keep useful fundamental research and forward-paper candidates visible in separate lanes.

## Executive decision

Repair the measurement and publication contract before attempting to optimize picks. A fresh, high-scoring recommendation is not necessarily a good trade. Conversely, a legitimate long-term position must not disappear or receive a fabricated exit because its original entry opportunity expired.

Deliver two independently assessable outcomes:

1. **Software/data outcome:** reproducible eligibility, correct identities and units, timestamped marks, reconciled cohorts, explicit abstention and reliable publication.
2. **Investment-research outcome:** preregistered, cost-aware, point-in-time research that earns forward evidence. This may correctly produce **zero qualified strategies**.

No production gates, capital locks, deliberate class freezes, historical outcomes or execution permissions change merely because this plan exists or multiple AIs agree with it.

**New first priority from the follow-up:** the live Money Ready verdict contains literal `NaN` and fails browser JSON parsing despite HTTP 200. Repair strict serialization and evidence-unavailable handling before treating this surface as usable. Section 11 records the reproduction, source trace, current per-class observations and narrowed release order; the earlier baseline remains historical evidence, not today's current count.

## 1. What changed after AI review

The first plan covered nine workstreams. V2 retains their intent but corrects the following weaknesses:

| V1 weakness | V2 improvement |
|---|---|
| A universal proposed WR>52% floor could become another conflicting policy | Separate the existing charter, deployed gate configuration and proposed research criteria. Do not change any production floor through this document. Evaluate payoff asymmetry explicitly. |
| PF, per-pick compounded drawdown and real portfolio risk could be conflated | Require explicit return units, position sizing, cash accounting and synchronized portfolio NAV. Label per-pick synthetic curves as diagnostics. |
| "n>=100" could be mistaken for proof | Require raw, deduplicated and clustered observation counts, dependence-aware uncertainty, prospective trial accounting and time coverage. A minimum count is necessary, not sufficient. |
| A two-hour artifact and five-minute quote rule might exceed current infrastructure capabilities | Separate hourly recommendation freshness from executable quote freshness. Measure provider timestamp/entitlement support before enabling an executable label. |
| A snapshot ID alone does not prevent mixed FTP generations | Publish immutable versioned bundles and switch a manifest/pointer only after all required files pass HTTP content/hash verification. |
| Cohort discrepancies were identified without adapter-level tests | Prioritize source-backed unit conversion, cost-fallback, event-time and denominator hazards before interpreting apparent alpha. |
| Membership-derived gate flags could look like successful gate execution | Preserve actual final decision inputs and reason codes; replay the decision rather than infer it from publication membership. |
| Research sat behind an unnecessarily long all-or-nothing dependency chain | Ship integrity fixes in small PRs; allow offline hypothesis registration in parallel, but prohibit promotion until its evidence dependencies pass. |
| AI consultation could appear to certify the plan | Record useful, rejected and incomplete responses. Model agreement does not certify a dataset or an investment strategy. |

## 2. Actual AI consultation and adjudication

### Method and confidentiality

- Local endpoint health was checked before inference.
- Local vLLM reviewed the full original draft plus a grounded public-data brief.
- A small local Ollama model ran with `num_gpu=0` and unload-after-request, avoiding a second large GPU-model load beside vLLM.
- Hosted providers received only a manually prepared public-facts/design brief. No private source files, secrets, personal memory or credential contents were sent.
- Credentials were resolved through the existing consultation helper, not pasted into prompts or this document.
- Requests were independent. Models had no browsing/DB access and were explicitly told not to invent fetches, statistics or allocation recommendations.
- Five model identities produced text. Response completion and quality varied; they are not five verified endorsements.

### Consultation results

| Reviewer | Route and identity evidence | Outcome | Disposition |
|---|---|---|---|
| Local Qwen | vLLM requested and returned `Qwen/Qwen2.5-14B-Instruct`; finish `stop` | Complete response, 743 completion tokens; largely reinforced existing controls | Retain final-gate eligibility, stable dedup, distinct clocks, mark states and dated fundamental evidence. No new performance claim. |
| Local Llama | Ollama requested and returned `llama3.2:3b`; finish `stop` | Complete response; useful problem list but several weak remedies | Keep measurement, dependence and forward-admission questions; reject moving-average WR floors, generic stratified-sampling fixes and independently updated files as a substitute for atomic publication. |
| GPT-OSS | Groq requested `openai/gpt-oss-120b` after catalog discovery; helper did not preserve returned-model metadata | Substantive response, but several unsafe or incorrect recommendations | Keep explicit cohort/window/coverage labeling. Reject its arbitrary asset-class priority, blanket position-age archive, expired-outcome exclusion and capital-enabling suggestions. |
| Gemini | Requested `gemini-flash-latest`; concise retry returned `gemini-3.8-flash`, finish `STOP` | Complete critique after an initial incomplete response | Adopt payoff-aware analysis, point-in-time availability, vehicle/exposure separation, portfolio accounting and coherent bundle publishing. Constrain overbroad dedup and deployment assumptions as described below. |
| Nemotron | NVIDIA requested `nvidia/nemotron-3-super-120b-a12b`; separate readiness call returned that model | Incomplete response; final content cuts off mid-item; helper did not preserve review finish metadata | Use only fully expressed price-coverage and identity concerns. Do not count missing sections as reviewed or accept its unsupported class TTLs. |

Failed attempts were preserved separately: Groq's default model request HTTP 404; Fireworks default HTTP 404; Mistral HTTP 429; NVIDIA Kimi request HTTP 404 despite being listed in its catalog. Catalog availability did not establish callable inference. The Groq replacement and NVIDIA readiness/fallback were bounded alternatives, not repeated retries against the same failure.

The first Gemini response was incomplete; the retry disabled optional thinking and requested a concise answer, producing explicit `STOP` metadata. No exact spend is asserted: billing totals were not retrieved.

A second local Qwen pass reviewed the assembled V2 and returned "NO MATERIAL CONTRADICTIONS FOUND." That is a text-review outcome, not proof of correct implementation, data or profitable strategies.

### Suggestions explicitly rejected

1. **"SPY and TIP share one ID."** Incorrect reading: each instrument has its own repeated identity; the evidence does not say their IDs equal each other.
2. **Keep the duplicate with the highest-priority class or newest score.** Mutable class/score cannot decide identity. Recompute from frozen inputs; quarantine unresolved conflicts.
3. **Archive every position after 48h.** This would hide actual exposure and violate long-term holding semantics.
4. **Drop expired outcomes from the main WR denominator.** This can recreate the known win-rate inflation. Keep the all-resolved denominator and separately label decisive-only WR.
5. **Set every open position's PnL to null until closed.** Valid unrealized PnL is useful; separate realized, unrealized and unavailable marks instead.
6. **Shift COT signal timestamps by a fixed number of days.** Keep original timestamps and use actual publication/available-at times, including exceptional release schedules.
7. **Deduplicate every signal sharing economic exposure/release time.** That would merge genuinely different strategies and trades. Distinguish trade identity from statistical dependence clusters.
8. **Lower WR floors automatically or enable sizing to make the dashboard useful.** Neither is authorized. Keep current policy; preregister any proposed policy change separately.
9. **Treat a local directory swap or symlink as FTP-wide atomicity.** The production host has no shell; use a manifest protocol validated against its actual FTP/HTTP behavior.
10. **Interpret "no-edge" as proof gates are too cautious.** Zero survivors can be the correct result.

## 3. Grounded baseline and its limits

### Live snapshot reviewed

The baseline comes from public artifacts retrieved around 05:08-05:10 UTC on October 19, 2026, not newly queried DB rows.

| Artifact | Content generation time |
|---|---|
| [Dashboard payload](https://findtorontoevents.ca/audit/data/dashboard_data.json) | `2026-10-19T03:58:18.875263+00:00` |
| [Money Ready verdict](https://findtorontoevents.ca/audit/data/money_ready_verdict.json) | `2026-10-19T03:56:39.674728+00:00` |
| [PF registry](https://findtorontoevents.ca/audit/data/pf_registry.json) | `2026-10-19T03:58:15Z` |
| [14-day diagnostics](https://findtorontoevents.ca/audit/data/pick_summary_stats_14d.json) | `2026-10-19T04:10:35+00:00` |
| [48-hour diagnostics](https://findtorontoevents.ca/audit/data/pick_summary_stats_48h.json) | `2026-10-19T04:10:36+00:00` |
| [Navigation surface matrix](https://findtorontoevents.ca/audit/data/nav_surface_edge_matrix.json) | `2026-10-19T04:10:57+00:00` |

Dashboard metadata identifies deployed SHA `62d32d7f52561e6c6cf5894e2c0c0f06ffcd14ea`.

- Zero of nine reported classes are Money Ready. All eight navigation surfaces report `no-edge`.
- Downloaded snapshot: 21 active rows; 4,244 raw-active rows; 3,437 auto-expired raw rows; zero Smart Picks.
- Four active rows have `_gate_passed=false` and `_visibility_floor=per_class`.
- SPY and TIP each appear twice under their respective identical ID/strategy/timestamp, with inconsistent scores.
- Sixteen active rows have numeric zero PnL. Separately, the 61-symbol stock-price sidecar lacks matching symbols for 15 of 18 non-crypto active rows. Neither fact proves all those rows are unmarked; other price paths must be traced.
- Browser inspection found current truth tables alongside historical performance prose. Its raw count was 4,242 rather than the downloaded 4,244: preserve retrieval identity rather than claim the observations are one immutable snapshot.
- Local June-dated recency files were stale mirrors; the corresponding live files were current. Do not "fix production" from local mirror age alone.
- PR #735 remained OPEN and unmerged when rechecked during V2 work. Reuse its verified price-universe/classification work after reconciling its actual diff and deployed state.

### Per-class evidence and posture

The intrabar aggregates below lack fully comparable disclosed window metadata. They are attributed published results, **not independent certifications of clean edge**.

| Class | Published evidence basis | n | WR | PF | V2 posture |
|---|---|---:|---:|---:|---|
| CRYPTO | Intrabar | 3,497 | 35.46% | 0.881 | NOT_READY; prioritize entry selection, conflicts and source dependence |
| EQUITY | Intrabar | 229 | 55.90% | 0.8365 | NOT_READY; high WR does not offset losing payoff economics |
| FOREX | Intrabar | 547 | 30.71% | 0.6111 | NOT_READY; reconcile tiny-window spikes before mutation |
| COMMODITY | Intrabar | 227 | 40.09% | 1.0281 | WATCH, not proven; preserve policy freezes |
| ETF | Policy-clean discovery | 15 | 73.33% | 1.8251 | INSUFFICIENT_DATA; separate intrabar cohort is n=28, WR=0%, PF=0 |
| BOND | Policy-clean discovery | 0 | unavailable | unavailable | INSUFFICIENT_DATA; separate intrabar cohort is n=21, WR=9.52%, PF=0.5281 |
| FUTURES, diagnostic | Intrabar | 47 | 40.43% | 1.0402 | Thin sample; do not mix with commodity-exposure aggregates |

Recent-window investigation triggers:

- FOREX: published 48h n_closed=36, PF=49.403 versus 14d n_closed=1,140, PF=0.913.
- EQUITY: 2,414 closes in the published 48h window, all attributed to one source family; 48h PF=1.514 versus 14d PF=1.475.
- CRYPTO: 14d n_closed=2,068 versus n_decisive=2,050; duplicate, source-concentration and EXPIRED-positive-PnL caveats.
- BOND: 14d n_closed=18, PF=11.011 versus zero 48h closes and poor separate intrabar results.
- COMMODITY: absent from the reviewed 14d/48h class rows.

These are investigation triggers, not proof of manipulation, actual independent trade count or investable alpha. Separate signal date, actual exit time, resolution processing time and backfill time.

### Additional source-backed hazards found while refining V2

These patterns were read in the working checkout; determine their deployed status and actual impact before any repair/backfill:

1. [Outcome adapter](tools/build_pf_registry.py): the outcomes loader queries `pnl_pct` with percent-unit sanity caps but converts to a fraction only when `abs(value)>1`. Values at or below 1 require an explicit source-unit contract; magnitude-based inference is unsafe. It also reads only WON/LOST and falls back from `entry_date` to pick ID/resolution information, which cannot substitute for true entry time.
2. [Cost adapter](tools/build_pf_registry.py): `_net_pnl` can return gross PnL when cost deduction fails. A labeled net promotion artifact must become unavailable, not silently gross.
3. [Gate-status join key](audit_trail/profitable_filtered_observer.py): `_pick_key` uses `signal_id` or symbol/strategy/direction, omitting entry timestamp and ordinary `id` on fallback. Its reuse for publication diagnostics can conflate distinct entries. Do not turn it into a new universal primary key without tracing callers.
4. [PF registry drawdown](tools/build_pf_registry.py): its class curve compounds ordered per-pick returns as if sequentially invested. This can be a consistent diagnostic; it is not a cash- and overlap-aware portfolio NAV.
5. [DSR implementation](alpha_engine/money_ready_verdict.py): `_dsr_gate` annualizes its input using `sqrt(252)` and sets `nb_trials=1`. Trace input frequency and strategy-selection provenance; do not call per-trade observations daily returns or ignore upstream selection trials.
6. [Performance charter](docs/PERFORMANCE_CHARTER.md) defines Tier-2 PF>=1.5, WR>=50%, MDD<=20%, n>=100 and three consecutive clean months, but its historical WR definition excludes flat outcomes. Newer integrity requirements demand an all-resolved view. Reconcile definitions through a versioned policy proposal; do not silently change the canonical charter.

## 4. Target behavior and data contracts

### 4.1 Keep three independent state axes

- **Signal:** candidate -> entry-valid / entry-expired / rejected.
- **Position:** not executed / paper open / filled open / closed / unresolved.
- **Evidence:** unavailable / discovery / forward-developing / validated.

An expired entry opportunity can coexist with an open position. A validated strategy can have no valid entry today. A good fundamental thesis can have no proven trading history.

Public presentation:

| Lane/posture | Meaning | Sizing |
|---|---|---|
| `ACTIONABLE` | Passes final entry, data, evidence and existing risk/capital policy | Only as already permitted by policy; a UI label does not authorize execution |
| `FUNDAMENTAL_RESEARCH` | Dated, sourced thesis and invalidation, not a proven trading signal | Disabled |
| `FORWARD_PAPER` | Prospectively registered hypothesis and tracked admissions | Disabled |
| `ABSTAIN` | Valid assessment found no eligible entry | Disabled |
| `POLICY_FROZEN` | Deliberate policy prevents new admission | Disabled |
| `DATA_UNAVAILABLE` | Cannot establish a trustworthy assessment | Disabled |

Retain raw diagnostics and the legacy monitored book under explicit names. Do not rename `active` to `actionable` and assume the old semantics disappeared. Migrate consumers deliberately. Failed-gate representation rows can remain in research if safe; raw data remains available for audit.

### 4.2 Required publication record

Add the smallest versioned schema compatible with existing consumers:

- Identity: immutable source event ID, stable entry identity, original ID aliases and separately recorded revision.
- Instrument: canonical symbol, venue, currency, contract/expiry, multiplier, wrapper type and economic exposure.
- Decision: frozen normalized inputs, final scores, gate result/reasons, code SHA, policy/config hash and decision time.
- Clocks: original event time, knowledge available-at time, entry validity, quote market time, retrieval time and publication time.
- Evidence: cohort ID/version, basis, window boundaries, n_raw/n_unique/n_clusters, cost/denominator version, forward/OOS state and uncertainty.
- Risk: stop/invalidation, horizon, liquidity/execution restrictions, policy freeze and current sizing permission.
- Quality: missing/invalid fields and explicit unknown states; no success-shaped fallback.

Identity must not depend on mutable score, class, a rounded entry price alone or a re-published parent timestamp. Repeated distinct entries remain distinct. Dependence clustering is a statistical layer, not deletion of valid trades.

### 4.3 Freshness and "regular picks"

Regular means a regular **assessment**, not a guaranteed new trade.

| Surface | Proposed service policy | Safe degradation |
|---|---|---|
| Hourly dashboard/verdict bundle | Expected each existing publish cycle; stale after two hours by content time | Disable actionable promotion; show last-good timestamp and stale reason |
| Executable quote | Proposed maximum five minutes while its venue/session is open; require actual market timestamp, feed delay and bid/ask where needed | Mark delayed/non-executable; do not claim execution-grade service from an hourly last-price feed |
| Closed market | Last official close and next valid session identified | `PRIOR_CLOSE` / `MARKET_CLOSED`, not a fresh executable price |
| Intraday idea | Proposed maximum four hours or the strategy horizon, whichever is shorter | Entry expires; monitoring continues if a position exists |
| Crypto swing idea | Proposed maximum 24h without recorded revalidation | Research/monitor only |
| Other swing idea | Proposed maximum one completed trading session without revalidation | Use venue calendars, holidays and overnight sessions |
| Long-term thesis | Strategy-specific review deadline and latest expected filing/release | Research stale or thesis-break state; no generic intraday expiry |
| COT/macro inputs | Actual release available-at time and expected publication schedule | Explain late/missing release; do not rewrite historical signals |

These TTLs are conservative proposed entry-lane defaults, not measured optimal holding periods or changes to the resolver. Baseline current capabilities before enforcing a new executable-service claim. Unknown/future/malformed times never count as fresh.

### 4.4 Measurement contract

1. **Units:** normalized decimal return internally; explicitly named percent/bps fields at boundaries. Convert from declared source units, never `abs(value)` heuristics. Futures need multiplier/currency conversion; bonds may need accrued interest/total return; equity/ETF prices need consistent corporate-action adjustments.
2. **PnL:** distinguish realized and unrealized base-currency PnL; missing mark produces null unrealized PnL, not zero. An attributed unchanged quote can produce genuine zero.
3. **Costs:** disclose spread, fees, slippage, funding/borrow, FX conversion and roll costs as applicable. Prevent double deduction. A failed model cannot publish gross as net.
4. **WR:** publish all-resolved wins/(wins+losses+expired+flat), with unresolved rows reported separately. Optional decisive-only WR must have a different field/label. Do not infer "win" from an arbitrary positive expiry mark without the outcome policy.
5. **PF:** compute positive net PnL / absolute negative net PnL on an explicit cohort and weighting basis. If there is no loss denominator, report null plus reason, not 999/infinity/"proven."
6. **Portfolio risk:** NAV includes cash, sized positions, costs, financing and FX. MDD is `max(1-NAV/running_peak_NAV)` on synchronized valuations. Missing material marks make risk metrics incomplete rather than silently flat.
7. **Comparability:** preserve genuine differences between intrabar, policy-clean, raw, entry-window and exit-window cohorts. Reconcile by immutable IDs and reason buckets, not by forcing totals to match.
8. **Inference:** keep observed sample counts, unique trade counts and dependence clusters. Use blocked/clustered uncertainty and fixed admission rules; no post-hoc profitable buckets or selective replay.

### 4.5 Promotion without policy drift

- Read the charter, actual deployed settings and capital locks as separate versioned inputs.
- V2 does **not** enact V1's extra WR>52% floor or Gemini's suggestion to remove WR floors.
- Target at least the existing Tier-2 floor and its time-coverage requirements before live promotion. Respect stricter active policies where applicable.
- Additional proposed evidence controls: positive net expectancy, defensible PF/expectancy lower confidence bounds, OOS validation, honest trial counts, concentration limits and at least four weeks of prospectively tracked paper operation.
- The confidence level, resampling/block rule, trial family, benchmark, evaluation checkpoints and stopping rule must be registered before evaluation. An uncertainty result cannot be chosen after seeing which test passes.
- Report block-bootstrap uncertainty for portfolio returns and clustered uncertainty for trade PF; insufficient independent clusters means unknown.
- A 40%-WR asymmetric strategy can be a legitimate research candidate; it remains outside a higher-WR production policy until a separately reviewed policy exception is approved.
- n>=100 is not a statistical guarantee; slow long-term strategies cannot manufacture independent samples to satisfy it.
- Record effect sizes, drawdown, turnover, capacity and benchmark-relative results, not just p-values.

### 4.6 FTP-compatible coherent publishing

Proposed design, subject to host capability tests:

1. Build a bundle ID using code/config/cohort identities; retain source timestamps inside each artifact.
2. Upload immutable required files under a versioned prefix. Verify complete HTTP bodies, hashes, schema and cross-file invariants.
3. Commit a small manifest pointer only after verification. Test whether FTP rename within the same directory is atomic on the actual host.
4. The client loads one validated manifest and fetches only its referenced immutable files. It must not mix those with independently refreshed live endpoints.
5. If pointer rename atomicity is not supported, use a verified immutable manifest selected by a small pointer and treat pointer parse/hash mismatch as unavailable; keep a validated cached last-good bundle visibly stale.
6. Quotes may update independently only through an explicit overlay joined to instrument/position IDs and quote sequence/time. They cannot silently replace the frozen recommendation inputs or outcome cohort.
7. Keep legacy endpoints during migration, labeled outside bundle guarantees. Do not claim the whole site is atomic while old consumers still bypass the manifest.

Never require shell access, a symlink flip or an in-place multi-file overwrite to be atomically visible on 50webs.

## 5. GitHub work packages

These are proposed issue titles and PR boundaries, **not issues already created**. `AUD-*` labels are planning identifiers, not GitHub issue numbers. Every code PR must first quote actual pre-change source, add a failing regression, implement the smallest change, then verify the relevant surface. Reuse existing helpers and pending work rather than add another framework.

### AUD-00 -- Freeze evidence and map deployed dependencies

**Priority:** P0. **Depends on:** none.

**Files:** [prior improvement plan](updates/2026-10-18-picks-per-asset-class-improvement-plan.md), [dashboard generator](audit_trail/dashboard_generator.py), [publish workflow](.github/workflows/audit-dashboard.yml), [price fetcher](audit_trail/fetch_stock_prices.py).

- Record deployed SHA, effective non-secret config, artifact retrieval time/hash and PR #735's current diff/status.
- Classify existing raw/live split, honest UEPS status and smart-funnel changes as deployed, pending or superseded.
- Build a small immutable fixture for duplicates, quota rows, old ARB entry, missing timestamp and valid weekend zero.
- Use a clean branch/worktree; never stash/reset unrelated shared edits.

**Acceptance:** inherited work is mapped to exact revisions; fixture hashes and facts reconcile; no generator/scanner/production write ran locally.

**Validation:** small stdlib fixture/metadata checks plus focused existing tests when executing later; no full dataset in a test fixture.

### AUD-01 -- Eliminate return-unit, cost and cohort ambiguity

**Priority:** P0. **Depends on:** AUD-00.

**Files:** [PF registry builder](tools/build_pf_registry.py), [verdict](alpha_engine/money_ready_verdict.py), [funnel extraction](tools/audit_pick_funnel/extract_funnel.py), [surface matrix](tools/audit_pick_funnel/build_nav_surface_matrix.py), [charter](docs/PERFORMANCE_CHARTER.md).

- First implement the strict JSON/non-finite verdict repair in section 11, including [snapshot serialization](tools/money_ready_snapshot.py). A recent timestamp and successful Python parse do not establish browser-readable evidence.
- Trace source units and provenance for each adapter, including percent values <=1, futures point returns and intrabar/net costs.
- Replace magnitude inference with declared adapter contracts; fail closed for promotion when costs/units are unknown.
- Reconcile ETF 15/28, BOND 0/21 and the FOREX/EQUITY recent batches by immutable IDs and distinct event/processing windows.
- Preserve gross/decisive-only diagnostics under unambiguous labels; publish all-resolved and net contracts separately.
- Propose, but do not silently enact, charter/denominator reconciliation.

**Tests:** existing [slippage tests](tests/test_charter_slippage.py), [source-concentration tests](tests/test_pf_registry_source_concentration.py), [intrabar sizing tests](tests/test_money_ready_intrabar_sizing_p1a.py); new `tests/test_audit_cohort_units.py` and `tests/test_audit_cohort_reconciliation.py`.

**Acceptance:** fixture percent values `0.25`, `1.0`, `2.0` normalize to fractions `0.0025`, `0.01`, `0.02`; already-fraction inputs remain correct through explicit adapters. Missing costs cannot pass as net. Every discrepancy is explained or promotion-blocked; no historical writes in this PR.

### AUD-02 -- Publish replayable decisions, not quota membership

**Priority:** P0. **Depends on:** AUD-00. Final evidence promotion also depends on AUD-01 and AUD-05.

**Files:** [generator](audit_trail/dashboard_generator.py), [gates](audit_trail/quality_gates.py), [observer key](audit_trail/profitable_filtered_observer.py), [HC rules](tools/dashboard_hc_rules.py), [template](audit_dashboard/template.html), [HC JS](audit_dashboard/hc_filter.js), [Money Ready JS](audit_dashboard/money_ready_filter.js).

- Trace the deployed injection path; do not assume the floor logic still exists in the local revision.
- Record final normalized/scored decision inputs before rendering; remove publication-membership-derived proof.
- Deduplicate genuine repeated identities before rank/count; preserve distinct entries and all source aliases.
- Quarantine irreconcilable score/identity conflicts; no highest-score or arbitrary class-priority winner.
- Add explicit lanes/class posture, keep legacy monitoring/raw data, and wire Top/Smart/HC/Money Ready consumers.
- Enforce nested actionable memberships with the actual per-pick evaluator and class capital posture; class verdict alone is not a per-pick recommendation.
- Close the demonstrated missing/malformed-evidence path in the legacy Money Ready filter; distinguish configured historical strategies from actual surviving rows. Replace vacuous empty-class success with explicit assessment/availability states, migrating consumers rather than silently reversing a health-check Boolean.

**Tests:** existing [generator regressions](tests/test_dashboard_generator_regressions.py), [smart funnel](tests/test_smart_gate_funnel.py), [HC filter tests](tests/test_hc_filter.js); new `tests/test_audit_decision_replay.py`.

**Acceptance:** failed-gate quota rows never enter actionable; SPY/TIP repeated identities each count once; distinct same-symbol/strategy entries do not join; replay yields identical membership and reason codes without network/current-time mutation. A clearly synthetic positive-control unit fixture that satisfies every policy/evidence gate must appear in actionable; never count this test fixture as a real performance observation.

### AUD-03 -- Restore attributed marks and truthful PnL

**Priority:** P0. **Depends on:** AUD-00 and AUD-02.

**Files:** [price fetcher](audit_trail/fetch_stock_prices.py), [generator](audit_trail/dashboard_generator.py), [template](audit_dashboard/template.html).

- Reuse compatible PR #735 symbol-universe changes after inspecting its exact diff.
- Enumerate every required instrument across all providers; the stock sidecar is not the whole quote universe.
- Add source timestamp, delay/session, provider, quote type and error status alongside compatible legacy mappings.
- Differentiate current/delayed/prior-close/missing/invalid marks and realized/unrealized PnL; disclose marked/total positions and notional coverage.
- Preserve current crypto fallback chains; do not start a new single-endpoint dependency.

**Tests:** existing [UEPS integration](tests/test_ueps_dashboard_integration.py); new `tests/test_stock_price_universe.py` and `tests/test_pick_mark_status.py`.

**Acceptance:** each monitored instrument has an attributed mark or a visible missing reason; unknown marks never become zero; valid unchanged marks can be zero; 100% of actionable rows meet their declared quote capability policy.

### AUD-04 -- Separate entry expiry from position lifecycle

**Priority:** P0. **Depends on:** AUD-02 and AUD-03.

**Files:** [gates](audit_trail/quality_gates.py), [resolver](audit_trail/universal_pick_resolver.py), [generator](audit_trail/dashboard_generator.py).

- Enforce original-event, available-at and valid-until clocks independently of PnL.
- Expire entry opportunities without closing filled positions or changing historical exit times.
- Preserve original lineage through genuine revalidation; never rejuvenate an idea from its containing file timestamp.
- Keep invalid/unknown/future times non-actionable and expose diagnostic partition counts.
- Revalidate entry economics against an attributed quote: remaining stop/target distance, net reward/risk and movement outside the original entry band. The fresh PA=F case in section 11 is a required regression fixture; do not choose an arbitrary universal drift cutoff.

**Tests:** existing [hold windows](tests/test_pick_hold_windows.py), [resolver](tests/test_universal_pick_resolver.py), [freshness](tests/test_data_integrity_freshness.py); new `tests/test_actionable_entry_freshness.py`.

**Acceptance:** both old losing and old winning ideas expire as entries; actual positions continue marking/risk monitoring; calendars distinguish crypto weekends, exchange holidays, FX sessions and long-term thesis reviews. No fabricated zero/close.

### AUD-05 -- Correct risk evidence and gate authority

**Priority:** P0 for promotion evidence; shadow-first for changed statistical/risk policy. **Depends on:** AUD-01 and AUD-03.

**Files:** [verdict](alpha_engine/money_ready_verdict.py), [PF builder](tools/build_pf_registry.py), [existing portfolio engine](tools/portfolios/engine.py), [portfolio risk helpers](tools/portfolios/risk.py), [portfolio gates](audit_trail/portfolio_gates.py), [charter](docs/PERFORMANCE_CHARTER.md).

- Trace actual capital/sizing/PnL semantics before modifying an authority; verify whether each referenced metric is diagnostic or enforcing.
- Report sized, overlapping cash-aware portfolio NAV separately from ordered per-pick return curves.
- Review daily-return construction, crypto/equity annualization calendars, DSR trial count, selection history and PBO applicability.
- Record actual vs recommended/enforced risk gates; `None`/missing must not look like a passing measured control.
- Treat approved policy changes as separate gated PRs with shadow evidence; no automatic removal of WR floors.

**Tests:** existing [portfolio engine](tests/test_portfolio_engine.py), [portfolio gates](tests/test_portfolio_gates.py), [verdict](tests/test_money_ready_verdict.py); new `tests/test_audit_nav_evidence.py`.

**Acceptance:** fixture +10% then -10% fully invested sequentially ends at 0.99 NAV, not 1.00; concurrent position sizing and cash reconcile independently; missing marks make completeness explicit; adding failed trials cannot improve a selection-adjusted score by pretending only one trial existed.

### AUD-06 -- Attach point-in-time fundamentals and instrument taxonomy

**Priority:** P1. **Depends on:** AUD-01, AUD-02 and AUD-03.

**Files:** [classification](audit_trail/asset_classification.py), [fundamentals fetcher](alpha_engine/fundamentals_fetcher.py), [valuation strategies](alpha_engine/fundamental_valuation_strategies.py), [macro gates](alpha_engine/fundamental_macro_gates.py), [UEPS runner](tools/run_ueps_pickers.py), [ETF filters](alpha_engine/etf_quality_filters.py), [template](audit_dashboard/template.html).

- Separate ETF/futures wrapper from economic exposure; SPY is an equity-exposure ETF, TIP/VCSH bond-exposure ETFs.
- Record taxonomy version and compare before/after counts; do not rewrite historical classifications without a reviewed migration.
- Attach source/fiscal/publication/available-at dates, observed inputs, assumptions, thesis/invalidation, uncertainty and missingness.
- Keep COT survey date distinct from actual release availability; support holidays/revisions.
- Use quantitative price signals and fundamental economic evidence as separate axes; no invented valuation fields or LLM confidence boosts.

**Tests:** existing [contract type](tests/test_contract_type.py), [UEPS active sync](tests/test_run_ueps_pickers_active_sync.py); new `tests/test_pick_fundamental_evidence.py`.

**Acceptance:** no fundamental label without dated evidence; missing fields do not receive neutral-as-positive scores; changing a wrapper does not double-count exposure; facts released after entry cannot be replayed as known at entry.

### AUD-07 -- Build unbiased class research and a forward admission register

**Priority:** P1. **Depends on:** AUD-00 to register hypotheses; AUD-01/04/05/06 before promotion evidence can qualify.

**Files:** existing per-class scanners and registries; [hypothesis registry](reports/hypothesis_registry.json), [mutation protocol](docs/MUTATION_THREE_AXIS_PROTOCOL.md), [investigate-before-kill protocol](docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md), [testing protocol](TESTING_PROTOCOL.MD).

- Register strategy/version, universe, available-at inputs, costs, benchmark, trials, acceptance test and stopping/checkpoint rule before examining outcomes.
- Freeze candidate admissions and include rejected, unfilled, expired and losing cases in the appropriate prospective ledger; do not quietly restart the clock after a bad run.
- Maintain separate hypothesis validation, executable-signal quality and portfolio evaluation. Price-based paper entries are not actual fills.
- Compare net strategies against appropriate benchmarks and baselines; adjust for regime, capacity, turnover and dependence.
- Existing deliberate freezes stay in force. Underperformance invokes the mandated rehabilitation/deep-dive workflow, not an automatic blacklist.

**Acceptance:** all six classes have an assessed prospectively registered hypothesis or explicit justified abstention. No promotion on high score/model vote/thin PF spike; all failed trials remain in the research accounting.

### AUD-08 -- Publish immutable validated bundles

**Priority:** P1. **Depends on:** AUD-01, AUD-02, AUD-03 and AUD-04; risk/evidence bundle includes AUD-05.

**Files:** [deploy helper](tools/deploy_audit_files.py), [publish workflow](.github/workflows/audit-dashboard.yml), [template](audit_dashboard/template.html), [local mirror helper](tools/refresh_local_audit_mirror.py).

- Implement the manifest protocol from Section 4.6 using capabilities proven against the FTP host.
- Verify all required files and content hashes before committing the pointer; keep code/config/source watermark identities.
- Cache/range-response handling must reject incomplete JSON and mixed versions. Retries are idempotent and do not advance the pointer on failure.
- Retain last-good data with an honest stale/unavailable state; never silently count last-good as current.

**Tests:** new `tests/test_audit_bundle_publish.py`; fixture browser tests in AUD-09.

**Acceptance:** inject failure before/during each upload, during pointer update and during client fetch. Client sees a complete validated old/new bundle or an explicit unavailable state, never accepted mixed data. Rollback reselects a verified prior manifest without rewriting source history.

### AUD-09 -- Unify monitoring, browser contracts and production proof

**Priority:** P1. **Depends on:** AUD-02/03/04/06; bundle proof additionally depends on AUD-08.

**Files:** [class freshness report](tools/generate_asset_class_freshness_report.py), [DB guardian](tools/db_freshness_check.py), [freshness UI](audit_dashboard/dashboard_freshness.js), [healthchecks](audit_dashboard/healthchecks.html), [watchdog workflow](.github/workflows/asset-class-freshness-watchdog.yml).

- Emit one consistent service-health interpretation while distinguishing transport, source event, quote, signal, outcome and evidence age.
- Monitor emission/evaluation cadence, unexplained resolver backlog, mark coverage, duplicates, missing timestamps, independent source concentration and cohort reconciliation.
- Show six class cards even with zero picks. `ABSTAIN` is not an outage; `DATA_UNAVAILABLE` is not a successful assessment.
- Test every callable surface and deep link against the same recorded decisions, including separate AI/legacy curator panels. Unsupported legacy panels must be explicitly research/historical, not implied actionable.
- Use existing scheduled/manual workflows; do not restore dashboard push-trigger cancellation cascades.

**Tests:** existing [freshness report](tests/test_asset_class_freshness_report.py) and [payload contract](tests/test_dashboard_payload_contract.py); new `tests/audit_actionable_picks.spec.ts`.

**Acceptance:** stale/malformed/404/mixed evidence blocks actionable publication with reasons; unknown is never green. All relevant Top/Smart/HC/Money Ready panels agree with their snapshot decisions; actual FTP-served version/content checks pass.

### AUD-10 -- Review, document and integrate only owned changes

**Priority:** required for every code package, plus final handoff. **Depends on:** each package being integrated.

**Files:** per-fix `updates/2026-10-19-audit-*.md`, [PR template](.github/pull_request_template.md), affected documentation/dependency registries.

- Fix and verification documentation travel in the same commit/PR; use the repository PR template, not a replacement template.
- Obtain required independent verbatim pre-change source evidence before any code-change PR. AI text-only critique is not that source verification.
- Record exact commands/results, fixture hashes, deployed SHA, effective flags, no-write scope and rollback.
- Update integration documentation and pipeline path registry only where actual dependencies/integrations change.
- Keep unrelated shared edits out. Pull/rebase only within the isolated branch and push only owned changes.
- If a public updates card changes, follow its insertion and FTP deployment rules. A Git push is not production deployment.

**Acceptance:** code reviewed, owned diff only, directly related documentation present, live post-publish proof recorded. No claim that software completion established profitable alpha.

## 6. Per-class research brief

Every candidate must use point-in-time inputs and net costs. These are research directions, not recommendations or proven edges.

| Class | Required economic/fundamental context | First investigation | Baseline and disqualifiers |
|---|---|---|---|
| CRYPTO | Venue/liquidity/spread, funding/OI, actual network/economic evidence if available | Entry regime/selection, opposing legs, duplicated correlated consensus, independent event count | Compare simple time-matched market/flat baselines; no source-count vote as proof; include fees/funding |
| EQUITY | Cash-flow quality, profitability/leverage, valuation assumptions, earnings and corporate actions | Why WR55.9% still PF<1; SPY attribution; weekend closes and point-in-time financials | Matched equity benchmark and cash with dividends; adjusted-price/filing leakage disqualifies |
| FOREX | Rate differential/carry net of financing, session/liquidity, scheduled macro risk | Reconcile 48h spike, losses by pair/session/regime and resolver behavior | Costed no-signal/trend baselines; exclude no legitimate row solely because it spoils a favorable WR |
| COMMODITY | Contract rolls, curve carry, inventory/seasonality, actual COT publication time | Deduplicate re-emissions and diagnose freeze/intake/display boundaries | Contract-aware trend/carry baselines; no Tuesday-as-Friday knowledge or back-adjustment leakage |
| ETF | Holdings/exposure, fees, spread/AUM, leverage/inverse resets and overlap | Resolve 15/28 cohort conflict before studying existing tactical allocation/dual momentum | Buy-and-hold, cash and volatility-matched allocation; wrapper labels cannot hide bond/commodity risk |
| BOND | Duration/DV01, yield/credit, accrued/distributed income, inflation and rate-shock scenarios | Resolve 0/21 cohort gap, TIP duplication and genuine score provenance | Duration-matched bond/cash benchmarks; price-only changes cannot masquerade as complete total return |

FUTURES remains a diagnostic instrument/exposure boundary. MEME/PENNY receive integrity and posture handling but no expansion of emissions in this scope.

## 7. Release sequence and ownership

| Stage | Packages | Exit condition |
|---|---|---|
| Baseline | AUD-00 | Grounded fixtures and deployed/pending map |
| Small integrity PRs | AUD-01, AUD-02, AUD-03 | Correct units/cohorts, decisions/identity, attributed marks; unresolved evidence stays blocked |
| Lifecycle/risk | AUD-04, AUD-05 | Entry and position states independent; risk metrics have correct economic meaning |
| Research/taxonomy | AUD-06; AUD-07 registration can start earlier | Dated research evidence and prospectively frozen hypotheses |
| Coherent publication | AUD-08, AUD-09 | Fault-injection, browser and FTP content verification |
| Per-package integration | AUD-10 | Reviewed fix-plus-doc commits, deploy proof, safe rollback |

Assign an accountable implementer and an independent reviewer to each accepted GitHub issue before coding. These roles are not fulfilled by model names. Serialize generator/template edits even when research can run independently.

The dependency graph is not a promise that discovering alpha is required to ship data fixes. AUD-08/09 can complete with all classes abstaining.

## 8. Test matrix and planned commands

The following commands are **planned execution validation**, not claimed run in this documentation-only task. Use the smallest related subset first; new test files must be introduced by their owning package.

```bash
python3 -m pytest -q \
  tests/test_smart_gate_funnel.py \
  tests/test_dashboard_generator_regressions.py \
  tests/test_ueps_dashboard_integration.py \
  tests/test_money_ready_intrabar_sizing_p1a.py \
  tests/test_charter_slippage.py \
  tests/test_pf_registry_source_concentration.py \
  tests/test_pick_hold_windows.py \
  tests/test_universal_pick_resolver.py \
  tests/test_portfolio_engine.py \
  tests/test_portfolio_gates.py \
  tests/test_asset_class_freshness_report.py \
  tests/test_contract_type.py
npm run test:hc-filter
npx playwright test tests/audit_actionable_picks.spec.ts --project="Desktop Chrome"
```

| Case | Required assertion |
|---|---|
| Duplicate SPY/TIP vs genuinely different same-symbol entries | Repeated identity counts once; real distinct entries remain; conflicting score is recomputed or quarantined |
| Failed gate/quota/final-score mutation | Zero actionable bypasses; final replay and Python/JS membership match |
| Synthetic positive-control eligible candidate | Appears in actionable and appropriate nested views; demonstrates the implementation did not simply hardcode an empty result; excluded from real evidence |
| 124h ARB, profitable old entry, unknown/future dates | Expire entry independently of PnL; never manufacture source time |
| Weekend/holiday/overnight/long-term position | Correct session/thesis rules; monitoring survives entry expiry |
| Missing quote vs unchanged valid quote | Null vs genuine zero; correct provenance and coverage |
| Percent/fraction/bps/futures currencies | Explicit adapter conversions, no magnitude inference, no silent net-to-gross fallback |
| EXPIRED/FLAT/unresolved, no-loss PF | Declared denominators and null reasons; no winner-only exclusion |
| Two concurrent positions, unequal sizes and cash | NAV/MDD differ correctly from sequential per-pick compounding |
| COT delayed release/revision, financial report published after entry | Available-at controls replay; original dates preserved |
| Failed trials/repeated emissions/one shock cluster | Counts and uncertainty reflect dependence and selection history |
| FTP upload/pointer/interrupted HTTP/cache mix | Validated coherent bundle or explicit unavailable/last-good state |
| Empty six-class screen | Six explicit postures; no vacuous pass, no invented picks |

Offline tests must not call live scanners, mutate production or execute generators. Provider/DB responses are fixtures. Tests missing optional local generated JSON must not be mistaken for a verified production contract; use pinned fixtures in the PR and mandatory CI-generated contract checks.

## 9. Hard acceptance gates

1. **Publication:** zero actionable failed-gate, duplicate, expired-entry, unknown-identity or unexplained-unmarked rows.
2. **Coverage:** every actionable row has a valid attributed quote for its advertised capability; all monitored rows expose mark status and coverage.
3. **Metrics:** units/costs/window/denominator/cohort/source are explicit; same-cohort ID reconciliation has zero unexplained differences.
4. **Risk:** reported portfolio drawdown derives from sized NAV, not averaged position percentages or an unlabeled sequential pick curve.
5. **Fundamentals:** actual dated source/invalidation for every fundamental label; missing inputs cannot improve a score.
6. **Evidence:** no borrowing success across incompatible cohorts; minimum sample alone never proves edge; all failed trials preserved.
7. **UX:** all six classes assessed; abstention and unavailable data distinguished; historical panels cannot impersonate current recommendations; positive-control fixtures prove valid candidates are not indiscriminately suppressed.
8. **Operations:** content/version/HTTP hash checks and failure-injection tests pass; last-good is visibly old, never success-shaped.
9. **Governance:** no unauthorized policy relaxation, freeze lift, trade, historical rewrite, destructive cleanup or undocumented fix.
10. **Claim discipline:** the data platform can be repaired even if every class remains non-actionable. Proven performance requires actual future evidence, not completing a checklist.

## 10. GitHub handoff and current status

- **This change:** one requested Markdown deliverable. No trading/data/gate implementation, DB mutation, real-money sizing or deployment.
- **GitHub:** work packages are ready to become issues and small PRs; this task does not create, commit, push or merge them.
- **Existing work to reconcile:** [October 18 improvement plan](updates/2026-10-18-picks-per-asset-class-improvement-plan.md), [prior per-class review](updates/2026-10-18-audit-picks-quality-per-class-review.md), and pending #735.
- **Policy authority:** [performance charter](docs/PERFORMANCE_CHARTER.md), deployed versioned settings and existing capital locks; any reconciliation needs an explicit reviewed change.
- **Rollback:** revert only the relevant owned code changes and reselect a verified prior bundle. Keep actionable promotion disabled if integrity is uncertain; preserve monitored positions and original evidence.

### Definition of done for this plan

Deliver an evidence-grounded, source-linked, AI-critiqued plan with bounded GitHub packages, explicit dependencies, falsifiable acceptance tests, preserved policy controls and honest limitations. Do not call any class profitable or production-ready without the required measured evidence.

## 11. Follow-up: specific live analysis and local-AI challenge

### 11.1 Scope, timestamps and reproducibility

This additional inspection was performed on October 19 around 05:39-05:45 UTC using the rendered production page, downloaded public payloads and the exact deployed filter script. These are related retrievals, not an atomic multi-file snapshot.

- Dashboard `generated_at`: `2026-10-19T05:28:41.631138+00:00`; `metadata.repo_sha`: `ae30274bc1226c597bd5e404db734481a4d7b78d`.
- Current downloaded dashboard: **11 active, 4,197 raw-active, 3,437 auto-expired and zero Smart Picks**. Five active rows carry `_gate_passed=false` with `_visibility_floor=per_class`. Do not overwrite the earlier 21/4,244 baseline or describe the count change as proof of a fix.
- Verdict `generated_at`: `2026-10-19T05:27:50.992444+00:00`; summary still has zero Money Ready classes and COMMODITY on WATCH.
- DB-health `generated_at`: `2026-10-19T05:13:23.197425+00:00`.
- Captured dashboard SHA-256: `38af054c80cdc07f63d65d767b5b33fe2777757f55818cc76a51221b9423619f`.
- Captured verdict SHA-256: `7d381d07b54aa3f73f623f6c44c5a087ca54078444d05839d06d2035873152f9`.
- Captured DB-health SHA-256: `ad4bc86a23cc66765e4379e1f0c2afc19a7c7ab67686a6cb9d10b1144e989f16`.

Payloads, isolated fixture results and the local AI request/response are retained in the session evidence directory, not committed as large datasets. These hashes identify the captured versions; a subsequent live fetch may differ.

### 11.2 Verified findings, not inferred alpha

| Priority / owner | Direct observation | Consequence and boundary |
|---|---|---|
| P0 / AUD-01, AUD-08 | HTTP 200 verdict contains four non-finite values: `classes.COMMODITY.dsr_score`, its nested `details.dsr.dsr_score`, and the same two MEME paths. Browser `response.json()` and independent Node `JSON.parse()` reject it. Dashboard and DB-health captures parse strictly. | Transport success conceals unusable evidence. The browser freshness panel's "No data available" is reproducibly a parse failure, not proof that the file or producer timestamp is missing. |
| P0 / AUD-02, AUD-09 | Deployed [Money Ready filter](audit_dashboard/money_ready_filter.js) matches local bytes. Failed verdict fetch/parse caches `{}`; missing classes/class passes its intrabar evidence check. | A synthetic whitelist-qualified historical research row survives missing evidence. This is a demonstrated filter failure, **not** proof that an actual live row survived, a trade executed or capital was unlocked. |
| P0 / AUD-02 | One identical SPY ID/strategy/timestamp appears twice: score 69 with gate false/floor, versus score 12 with gate true. | Deduplicating display alone does not repair contradictory decision provenance. Preserve both inputs, replay and resolve/quarantine before recommendation. |
| P1 / AUD-02, AUD-09 | BOND and FUTURES have zero active/Smart rows but `asset_class_summary.thresholdPass=true`. | [Generator](audit_trail/dashboard_generator.py) explicitly sets this Boolean true for `active_count == 0`. It is not proof of passing performance or a current candidate; establish its existing health semantics and migrate all consumers. |
| P1 / AUD-03, AUD-04 | PA=F SHORT is only 0.1h old, score 19, gate true; entry 1,113.3, mark 1,133.5, stop 1,135.566, target 1,079.901. | Adverse mark drift is 1.814% and consumes 90.7% of original entry-to-stop distance. A newly emitted timestamp cannot certify an intact entry opportunity. No executable quote timestamp or actual fill was established. |
| P1 / AUD-01, AUD-09 | DB-health reports 22,947 heuristic ghost rows in ten low-entry-diversity/repeated-value cohorts, mostly MEMECOIN `meta_strategy`; query `ok=true`, quality tier yellow. | `ok` means check execution succeeded, not clean data. The heuristic does not establish 22,947 true duplicates, impact on these top picks or fraud. Require lineage intersection before any historical correction. |
| P1 / AUD-08, AUD-09 | Live [freshness JS](audit_dashboard/dashboard_freshness.js) differs from the local file; deployed script has additional tab-staleness code. Money Ready filter bytes match. | A top-level repository SHA cannot prove every served asset belongs to that revision. Confirm file hashes and deployed behavior before using local source as exact production evidence. |

The Money Ready button already includes an honest "historical only / not a sizing signal" warning. Preserve it. Its banner nevertheless calls every configured whitelist strategy "Surviving strategies", independent of the actual filtered rows. Correct the result label/count, not merely add another disclaimer.

### 11.3 Root-cause trace and narrow repair contracts

**A. Strict JSON is a release gate, not a formatting preference.**

The inspected [DSR computation](alpha_engine/money_ready_verdict.py) returns `round(dsr, 4)` without a finite-value guard. The [snapshot writer](tools/money_ready_snapshot.py) parses with default `json.loads`, validates keys/verdict enums but not numerical finiteness, and serializes with default `json.dumps`. Python accepts/emits non-standard `NaN`; browser JSON does not. This demonstrates how the invalid value can cross the publication boundary. It does **not** yet prove which numerical input produced the non-finite DSR.

Implementation must:

1. Preserve the offending class/input fixture and trace non-finite inputs, invalid estimator variance and output at the DSR boundary. Do not fabricate a statistical result.
2. Represent an unavailable optional metric as `null` with a machine-readable reason, and ensure it cannot satisfy an evidence-required gate. Reject structurally invalid/non-finite required inputs before publication.
3. Use strict parsing at process/file boundaries and strict serialization (`allow_nan=False` or equivalent existing helper) for current snapshots, archives and machine-readable stdout. Catch the invalid state before replacing any last-good artifact.
4. Require successful browser-compatible parsing/schema validation of the exact uploaded bytes. Report HTTP, parsing, schema, timestamp and policy health separately.
5. Never regex-replace `NaN` text with `0`, permissively parse around it in the UI, or turn an unavailable DSR into a successful result.

**B. Separate historical research qualification from current Money Ready evidence.**

An isolated Node VM executed the captured filter with a synthetic `cot_positioning` / CT=F row, confidence 0.9 and score 100. Missing classes produced one research row; missing class produced one; intrabar `wr_ok=false,pf_ok=false` produced zero; a policy-clean NOT_READY/capital-disabled fixture produced one. These are **test fixtures, not live observations or strategy evidence**.

The repair must make missing/malformed/stale required evidence explicitly unavailable to a current actionable/Money Ready lane. A separately labeled historical research lane may still display the same research idea without claiming promotion. Do not indiscriminately rewrite every research filter as a capital gate; trace callers and apply the existing canonical decision contract. Missing source, explicit NOT_READY and disabled capital posture must never be interpreted as positive current eligibility.

**C. Empty-class assessment is not strategy success.**

Keep six class cards even with no candidates. Add distinct candidate-count, assessment availability and qualification states, with reasons for no entries, no current assessment, policy freeze and failed evidence. Audit [quality-monitor consumers](audit_trail/quality_monitor.py) and UI before changing `thresholdPass`. No zero-row or unknown-evidence class may receive an affirmative investment-quality badge. Zero mean/WR must not impersonate measured performance.

**D. Freshness includes entry economics.**

For the PA=F fixture, `abs(mark-entry)/abs(stop-entry)` is a diagnostic of movement relative to the original risk distance, not an executable-price or futures-contract risk calculation. At a valid new quote, recompute directional remaining target/stop geometry, costs, spread, contract multiplier and permissible entry band. A mark already across a stop/target or outside the frozen entry contract blocks a **new entry** with a reason; a real position remains monitored. Never use a smaller remaining stop distance as an automatic quality boost or tighten the stop merely to manufacture a favorable reward/risk ratio.

### 11.4 Current per-class shortlist investigation

These are current monitoring-feed examples, **not endorsed top picks**. Counts include duplicates and floor rows until repaired.

| Class | Observed feed | Specific next investigation |
|---|---|---|
| CRYPTO | Three rows: XRPUSDT, SUIUSDT, ARBUSDT; all carry conflict flags. ARB is 125.5h old, score 0, PnL -6.98%; SUI is 53.5h old. | Separate opposing independent theses from correlated re-emissions and accidental conflicts; identify actual position vs entry. Require current source/economic evidence, liquidity/costs and clean strategy history before recommendation. A conflict flag alone is neither an automatic winner nor proof every leg is invalid. |
| EQUITY | Two SPY rows for one identity; gate/score conflict. | Reconcile identity and classification: SPY is an ETF vehicle with equity exposure. Verify weekend/session and quote provenance, then explain the strategy's expected edge against a matched benchmark. No duplicate may inflate coverage. |
| FOREX | EURGBP=X score 62 and GBPUSD=X score 58 are floor rows with gate false. | Keep them out of actionable; expose exact rejection reasons, session/spread/carry and macro event context. Reconcile source/forward performance before interpreting scores. |
| COMMODITY | GC=F score 63 is a failed-gate floor row; PA=F score 19 passes the legacy gate flag but has moved close to its original stop. | Respect any existing class freeze; distinguish entry validity, contract/roll/curve context and class WATCH evidence. Neither freshness nor the gate flag establishes quality. |
| ETF | XLV score 51 is a failed-gate floor row; TQQQ score 10 is gate true. Both around 60h old across the weekend. | Check exchange sessions, new-entry eligibility and attribution. For TQQQ include leverage/daily-reset exposure, not just nominal score or equity overlap. Wall-clock age alone is insufficient to declare either stale. |
| BOND | No active or Smart row; summary threshold Boolean true. | Show no candidate with an explicit assessment/evidence state, not pass. Preserve duration/yield/credit/total-return fundamentals and the previously identified cohort reconciliation work; do not force a replacement TIP pick. |

### 11.5 Local AI contribution and adjudication

Local vLLM was healthy and returned `Qwen/Qwen2.5-14B-Instruct`, finish `stop`, 952 completion tokens. The model received the concrete observations above inline, including limitations and already-planned controls; it had no browsing capability. Prompt SHA-256: `bc0fab4fb6657887d26b00a3034c96396cd2577628d1173c8c477191ca49ad8b`. No hosted API was used for this follow-up.

- **Accepted and sharpened:** strict serialization/validation; fail-closed required evidence; lineage investigation of heuristic health issues.
- **Corrected:** Qwen suggested adding a historical label, but the live banner already has one. The missing part is truthful configured-versus-surviving counts and separation from the current capital verdict.
- **Rejected:** uniqueness of a "strategy identifier within a timestamp" would merge distinct symbols/entries. Keep event/instrument/source identity and preserve genuinely separate signals.
- **Constrained:** Qwen suggested resolving conflicts by timestamp/score/gate status. Those are precisely disputed here; use reproducible provenance and policy, not the largest score or latest processing time.
- **Not novel:** identity/conflict concerns were already covered by AUD-02. New live fixtures strengthen those tests; they do not justify duplicate work packages.

The local critique is advisory. Browser failures, deployed-byte checks and synthetic execution establish the findings; the model does not certify their financial implications.

### 11.6 Revised first releases and exact additional acceptance cases

1. **First small repair: AUD-01 strict verdict contract plus AUD-08 publication check.** Valid optional-metric unavailability becomes reasoned null; required invalid evidence prevents promotion. No statistical/policy floor is relaxed. This repair need not wait for portfolio research.
2. **Second: AUD-02/AUD-09 evidence-unavailable behavior, historical-result labels and empty-class states.** Preserve current warnings/research access; current actionable qualification must use the canonical decision, not a legacy whitelist exception.
3. **Then: existing identity/mark/lifecycle packages.** Add the exact SPY, PA=F, ARB and weekend ETF fixtures. Diagnose the suspicious DB cohorts through read-only lineage before proposing targeted historical remediation.

| Additional fixture | Required result / owning package |
|---|---|
| Four captured non-finite DSR paths; positive/negative Infinity; valid finite zero | Strict JSON succeeds only after legitimate null/reason normalization; zero remains zero, not missing. Invalid required values prevent replacing last-good. AUD-01/08. |
| HTTP 200 with invalid JSON vs HTTP failure vs missing timestamp vs stale but valid evidence | Different visible reason codes; no green/current-qualified state merely from HTTP/timestamp. AUD-08/09. |
| Missing cache/classes/class, explicit NOT_READY, stale generation and malformed required booleans | Zero current-qualified rows; historical research stays separately labeled if supported. Test both initial asynchronous loading and failure recovery. AUD-02/09. |
| All configured historical strategies, zero actual survivors | Banner displays configured research universe separately and actual surviving count zero; no implied surviving/current edge. AUD-02/09. |
| BOND/FUTURES with zero rows, nonempty failing class, valid positive control | Explicit no-candidate/assessment states; no vacuous investment pass; real eligible fixture can still qualify. AUD-02/09. |
| PA=F near stop, crossed stop/target, reversed/missing quote, adverse/favorable drift | Recompute from attributed quote and frozen entry contract; block invalid entry, retain actual position monitoring, no arbitrary universal drift rule. AUD-03/04. |
| Heuristic DB-health cohort does/does not intersect a displayed outcome | Report intersection counts/IDs and uncertainty separately from query success; no automatic deletion or class-wide condemnation. AUD-01/09. |
| Top-level SHA matches but one served JS file differs | Detect component mismatch using manifest/content checks; do not assert coherent deployment from SHA alone. AUD-08. |

**Checks actually performed for this follow-up:** browser verdict fetch/parse reproduction; independent strict Node parsing of all three captured feeds; recursive non-finite-path inspection; captured/local JS byte comparison; isolated synthetic execution of the deployed Money Ready filter; source trace of DSR/snapshot and empty-class behavior; local Qwen critique. Planned production/regression tests above have **not** been executed as fixes, because this remains a documentation task. No generator, scanner, DB cleanup, policy change, trade or deployment was run.
