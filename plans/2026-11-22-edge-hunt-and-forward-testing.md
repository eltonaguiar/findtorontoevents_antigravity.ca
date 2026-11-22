# Project plan — find, prove, and forward-test an edge

Status: awaiting approval
Date: 2026-11-22
Owner: zoo / zoo-savant
Scope: `findtorontoevents_antigravity.ca` (measurement + hypothesis pipeline), `antigravity_review_Nov192026` (published reviews)

---

## 0 Premise, stated honestly

Right now there is **no proven edge anywhere**: `n_proven` 0, `n_candidate` 0, `n_proven_classes` 0 across 374 tested cells
`[SRC: docs/audit_review_2026-11-22/_raw/audit3_audit3_ledger.json:62]`. Selection alpha overall is **negative**
(-0.3696, CI [-0.5673, -0.1674]) `[SRC: docs/audit_review_2026-11-22/_raw/audit3_audit3_ledger.json:150]`, and CRYPTO is
flagged `beta_dominant` `[SRC: docs/audit_review_2026-11-22/_raw/audit3_audit3_ledger.json:1632]`.

The reason to run this project is not that edge is likely. It is that the *process* which could detect edge is currently
not trustworthy: the gate covers 24.2% of CRYPTO rows, two surfaces publish different cost constants, and 96.8% of
excluded rows carry one undifferentiated label. A hedge fund would fix the measurement before deploying capital, and
would pre-register hypotheses so that a discovery cannot be relabelled as a confirmation.

**The deliverable of this project is a decision, not a strategy.** Either a forward-tested cell clears the gate with
honest costs, or we have a documented, quantified "no" across a defined search space. Both are worth more than an
unverified PF.

---

## 1 What already exists (so the plan builds, not duplicates)

| Capability | Where it already lives |
|---|---|
| Promotion rule with n, net CI, halves, symbol/source share, BH q, DSR, alpha G8, 2x-cost G9 | `conventions.promotion_rule` `[SRC: docs/audit_review_2026-11-22/_raw/audit3_audit3_ledger.json:50]` |
| Multiplicity: discovery vs confirmatory namespaces, BH, Bonferroni | `multiplicity.families` `[SRC: docs/audit_review_2026-11-22/_raw/audit3_audit3_ledger.json:1479]` |
| Verdict churn + persistence-across-2-runs | `[SRC: docs/audit_review_2026-11-22/_raw/audit3_audit3_ledger.json:56]` |
| Selection alpha (beta-neutral) with bootstrap CI | `[SRC: docs/audit_review_2026-11-22/_raw/audit3_audit3_ledger.json:51]` |
| Intrabar-honest resolution + rejection of daily rows as evidence | `alpha_engine/intrabar_resolver.py:5` |
| Forward ledger contract + writer | `alpha_engine/forward_observations.py:2`, `alpha_engine/forward_observations_ingest.py:2` |
| Observe-pod emitter | `tools/emit_observe_pods.py:10` |
| Pilot to forward bridge | `tools/pilot_forward_bridge.py:5` |
| Live paper simulator with day-30/60 kill | `tools/live_simulator.py:17` |
| 5-axis scrutiny (concentration, fat-tail, OOS, batch artifact, binomial) | `tools/per_class_scrutiny_engine.py:1` |
| Hypothesis registry | `reports/hypothesis_registry.json` |
| Portfolio / regime sizing / risk modules | `paper_trading/`, `risk_management/`, `alpha_engine/regime_position_sizer.py` |

The plan's job is to connect these into one gated pipeline and fix the places where they lie.

---

## 2 Phase E0 — Repair the measurement substrate (blocking)

Nothing downstream is trustworthy until these are closed. Each is small and each invalidates a number we would
otherwise build on.

| # | Fix | Evidence | Gate |
|---|---|---|---|
| E0.1 | Explain `invalid_row` per branch. Wire `audit_trail/excluded_cohorts.summarize_excluded` `[SRC: audit_trail/excluded_cohorts.py:31]` to publish n/WR/mean-PnL/side/top-symbols for the dropped rows instead of one count | 5,891 of 6,087 excluded rows are `invalid_row` `[SRC: docs/audit_review_2026-11-22/_raw/audit3_audit3_ledger.json:97]` | every excluded row attributed to one of the 9 predicate branches in `audit_trail/dashboard_generator.py:4924` |
| E0.2 | Unify or explicitly label cost constants. `/audit` CRYPTO 15bp `[SRC: alpha_engine/money_ready_verdict.py]` `SLIPPAGE_BPS` vs `/audit3` 9.96bp `[SRC: docs/audit_review_2026-11-22/_raw/audit3_audit3_ledger.json:16]` | one PF per class per surface, each stamped with its cost basis |
| E0.3 | Add the missing `FUTURES` key to `class_cost_pct` — FUTURES is currently charged COMMODITY's 0.15 while `slippage_pct_by_class` says 0.1 `[SRC: docs/audit_review_2026-11-22/_raw/audit3_audit3_ledger.json:27]` | FUTURES cost = 0.1 everywhere |
| E0.4 | Extend selection alpha to cover the class sample, or rename the verdict to "subset alpha" with the coverage printed beside it. Today alpha_n is 1,674 of 6,926 for CRYPTO `[SRC: reports/class_metric_reconciliation_20261122.md]` | `alpha_coverage_ok` true, or the label states the subset |
| E0.5 | Reconcile the forward ledger: served `n_rows` 447 `[SRC: docs/audit_review_2026-11-22/_raw/audit3_audit3_ledger.json:1218]` vs local 430 rows | one number, with the difference explained row by row |
| E0.6 | Orphan hypothesis: H-119 holds all 430 forward rows but no pod owns it. Bind it to a pod or retire it | every forward row maps to a registered pod with `registered_at` |
| E0.7 | Refresh stale payloads (Mercury3's ops runbook: 34-day-stale `dashboard_data.json`, fx_prices backfill) | dashboard freshness within the guardian's threshold (`tools/db_freshness_check.py`) |
| E0.8 | Publish the daily-vs-intrabar inversion per class; the ETF 100.28x `[SRC: docs/audit_review_2026-11-22/_raw/audit_data_money_ready_verdict.json]` must be visible next to the headline PF | no surface shows a daily PF without the intrabar PF adjacent |

**E0 exit criterion:** every class PF is reproducible from a named cohort, a named cost, and a named resolution mode.

---

## 3 Phase E1 — Freeze the honest baseline ("the clock")

Before hunting, define the one number every hypothesis is measured against, per class: canonical cohort, net of
per-class measured slippage, intrabar first-touch, with selection alpha and its CI. Freeze it to a JSON with a sha256
and never change it mid-project (changing the clock after seeing results is how backtest overfitting happens).

- Output: `reports/edge_baseline_<date>.json` + sha in `_MANIFEST.json`.
- Also record, per class, the **null distribution**: what a coin flip or a buy-and-hold would score in this cohort.
  A strategy that cannot beat its own class's buy-and-hold is beta, not edge.

---

## 4 Phase E2 — Pre-registration discipline (the part that makes "prove" possible)

Every hypothesis is written to `reports/hypothesis_registry.json` **before** any test is run, with:

```
id, registered_at, owner, namespace (discovery|confirmatory),
economic rationale (why would this edge exist and who pays for it),
universe + symbols, entry rule, exit rule (TP/SL/time),
cost model, n_target, predicted sign and magnitude,
kill rule, and the exact test that will decide it
```

Rules:
- **No post-hoc edits.** An edit creates a new id; the old one stays with its result.
- **Discovery and confirmatory namespaces do not share data.** If a hypothesis was discovered on a window, confirmation
  uses a disjoint window. This is the single defence against the `mega_mutation` failure mode: it was found and
  "validated" on 2026-04-02..2026-06-11 `[SRC: reports/per_class_scrutiny_20261004.json:6]`, an in-sample split.
- The rationale is mandatory because a hypothesis with no economic story is a data-mining artifact by default.

---

## 5 Phase E3 — Hypothesis generation (structured, multiplicity-aware)

Sources, in order of prior quality:

1. **Existing families with an economic story**: momentum/TSMOM, carry (FX carry + VIX regime), mean-reversion
   (Bollinger/RSI), cross-sectional value/quality, event-driven (IPO post-listing), seasonality (commodity planting/harvest).
   These already have implementations in `baby_strategies/`, `paper_trading/strategies/`, `alpha_engine/`.
2. **The 374 tested cells**: for each `WEAK` cell, ask whether it is a sizing problem, a cost problem, or a real
   absence of edge. Only the first two are actionable.
3. **Regime conditioning**: does a family's sign flip by regime? `alpha_engine/regime_flip_detector.py` and
   `regime_position_sizer.py` exist for this. A strategy that works in one regime is a real thing if the regime is
   detectable in real time — and a trap if it is only detectable in hindsight.

**Multiplicity accounting is mandatory.** If we test 200 hypotheses, ~10 clear p<0.05 by chance. The confirmatory family
gets BH at q 0.1 `[SRC: docs/audit_review_2026-11-22/_raw/audit3_audit3_ledger.json:53]` and the finalist also needs
DSR >= 0.95 `[SRC: docs/audit_review_2026-11-22/_raw/audit3_audit3_ledger.json:12]`. The number of tests performed is
recorded and reported with every result. A result without its trial count is not a result.

---

## 6 Phase E4 — Screening harness (cheap, wide, honest)

- Reuse `tools/per_class_scrutiny_engine.py` for the 5 axes, but **with a cost model** (E0.2) so a gross PASS can no
  longer masquerade as a candidate.
- Walk-forward with purged/embargoed folds (no leakage across the hold period): train, purge a gap, test, roll.
- Report per hypothesis: n, WR, gross PF, net PF, net CI, 2x-cost CI, split-half, top symbol/source share, DSR, alpha CI.
- **Screening cannot promote.** Its only output is "advance to confirmatory" or "kill".

Gate to advance: net PF CI-LB > 1.0 AND alpha CI-LB > 0 AND split halves stable AND no symbol >60% AND n >= 100.

---

## 7 Phase E5 — Confirmatory stage (narrow, expensive, decisive)

Only survivors enter. Each is run once against the locked holdout.

- BH across the confirmatory family; DSR >= 0.95; Bonferroni as the strict cross-check.
- 2x-cost stress must stay positive `[SRC: docs/audit_review_2026-11-22/_raw/audit3_audit3_ledger.json:52]`.
- Benchmark comparison: must beat a same-asset buy-and-hold, direction-adjusted (that is what alpha is).
- Persistence: the verdict must survive 2 consecutive runs `[SRC: docs/audit_review_2026-11-22/_raw/audit3_audit3_ledger.json:56]`.
- Output: at most a `CANDIDATE`. **Nothing is called PROVEN from backtest data.** Ever.

---

## 8 Phase E6 — Forward testing (the only path to proven)

This is where the repo already has the machinery and where the project actually proves something.

1. **Register the pod** in `reports/hypothesis_registry.json` with `registered_at`. Only rows closed after that count
   `[SRC: docs/audit_review_2026-11-22/_raw/audit3_audit3_ledger.json:1216]`.
2. **Emit rows** via `tools/emit_observe_pods.py` (`--dry-run` first, `--apply` appends) and
   `alpha_engine/forward_observations_ingest.py --apply` from honest intrabar rows.
3. **Simulate live** with `tools/live_simulator.py` (kill at day 30/60 if forward CI-LB <= 0 `[SRC: tools/live_simulator.py:17]`).
4. **Bridge** pilot closes with `tools/pilot_forward_bridge.py` so pilot pods stop sitting at `n_forward 0`.
5. **Gate** (unchanged, from the ledger): n >= 100, net PF CI-LB > 1.0 or IR >= 0.5, intrabar first-touch 100%,
   benchmark coverage >= 90%.

**This is the bottleneck.** Today every pod has 0, 2 or 1 forward rows `[SRC: docs/audit_review_2026-11-22/_raw/audit3_audit3_ledger.json:1222]` and the entire ledger is one hypothesis in one class. At the current emission rate, reaching n=100 is an open-ended wait, so the plan must include **increasing the emission rate**, not just waiting: more symbols, more frequent scans, and multiple pods in parallel so the dozens of hypotheses can accumulate rows simultaneously.

Minimum time-box: 8 weeks of forward rows before any promotion decision, with a weekly clock report.

---

## 9 Phase E7 — Portfolio and risk (only after a candidate exists)

- Correlation matrix across candidates (`alpha_engine` already computes cross-asset correlation `[SRC: audit_trail/dashboard_generator.py:11625]`).
- Position sizing by regime (`alpha_engine/regime_position_sizer.py`), capped per symbol and per source.
- Kill switches: drawdown limit, per-pod loss limit, correlation spike, data-staleness halt.
- Capital ladder: paper -> shadow -> micro-size -> size, each requiring a forward record at the previous rung.

---

## 10 Phase E8 — Operations and monitoring

- GHA cron for the forward clock, the freshness guardian, and the reconciliation tool (`tools/reconcile_class_metrics.py`).
- Weekly report: per-pod forward n, PF CI, days-to-gate, verdict churn, and any NEW kill.
- Alerts on: pod approaching kill, verdict flip, forward ledger growth stall (`tools/forward_growth_watchdog.py` exists).
- Everything published to the review repo with `[SRC:]` markers so `tools/doc_source_lint.py` gates it.

---

## 11 Phase E9 — Decision gates and honest stopping

| Gate | Decision |
|---|---|
| G-A after E0 | measurement trustworthy? if no, stop and fix |
| G-B after E4 | any hypothesis advances? if none of 200 do, the search space is documented as empty |
| G-C after E5 | any CANDIDATE? if no, publish the negative result |
| G-D after 8 weeks of E6 | any pod clears n>=100 with CI-LB>1? if no, kill it and record why |
| G-E | promote to micro-size only on a PROVEN_T2 record, never on a backtest |

Stopping rule: the project ends with either one PROVEN_T2 forward-tested cell, or a written "no edge found in this
space" with every hypothesis, its trial count, and its result. Both outcomes close the loop.

---

## 12 What this plan refuses to do

- It will not call a backtest "proven". The strongest backtest label is CANDIDATE.
- It will not paper-trade a cell with no symbol, direction, entry, TP or SL (that is what `PAPER_PILOT.md` documents).
- It will not quote a PF without n, cost basis, cohort and resolution mode.
- It will not celebrate a 4-row alpha (FUTURES +1.3353 `[SRC: docs/audit_review_2026-11-22/_raw/audit3_audit3_ledger.json]`).
- It will not double-count an exclusion (the 5,891 vs 11,782 mistake I made and corrected).
- It will not run `check_active_picks.py` or `smart_picks_engine.py` unprompted.

---

## 13 Immediate next steps (E0, executable now)

The DB is reachable (`mysql.50webs.com/ejaguiar1_stocks`, 52,608 closed rows, read-only verified 2026-11-22), so:

1. E0.1 publish the per-branch `invalid_row` split (generator change + `summarize_excluded`).
2. E0.4 print alpha coverage beside every class verdict.
3. E0.8 add the intrabar PF next to every daily PF in the three surfaces.
4. E0.5/E0.6 reconcile 447 vs 430 and bind H-119 to a pod.

Items 1-3 are code changes to the generator and the verdict module; 4 is data reconciliation.

---

## 14 Delegation track (multi-AI review of each phase)

The repo has a working multi-provider consult path: `tools/consult_multi.py`, which reads keys from
`~/dbpasses.txt` and exposes 14 providers. Verified 2026-11-22 with `--list`: nvidia, groq, cerebras,
together, fireworks, github_models, huggingface, gemini_api, cloudflare, deepinfra, nous, mistral,
aimlapi, hypereal all report `has_key yes`.

Mechanism (exact, from the tool's own contract):

```bash
python3 tools/consult_multi.py --fanout diverse5 --prompt-file /tmp/q.md --out-dir /tmp/fanout_results
python3 tools/consult_multi.py --fanout reasoning4 --prompt-file /tmp/q.md --out-dir /tmp/fanout_results
python3 tools/consult_multi.py --provider gemini_api --model gemini-flash-latest --prompt "..."
```

Each peer writes one `.md` file into `--out-dir`. The workflow is therefore:

1. I write the question to a prompt file and fan it out.
2. Peers drop their suggestions as `.md`.
3. I read every file, cross-check each claim against the frozen evidence (a suggestion that cites a
   number I cannot find in `_raw/` is rejected, not adopted).
4. I record the outcome in the review repo: what was suggested, what I accepted, what I rejected and why.

Delegated reviews, one per phase:

| Id | Phase reviewed | Prompt | Preset | Deliverable |
|---|---|---|---|---|
| D1 | E0 fixes | Are the 8 measurement fixes the right ones, and which is missing? Which of the 9 predicate branches most likely explains the 18,610 unexplained rows? | diverse5 | `_delegated/D1_e0_review.md` |
| D2 | E2/E3 design | Critique the pre-registration schema and the hypothesis families. What would a quant desk add or cut? | reasoning4 | `_delegated/D2_prereg_review.md` |
| D3 | E4/E5 statistics | Is the gate sequence (net CI, alpha CI, BH, DSR, 2x-cost, persistence) correctly ordered and powered? What is the false-discovery risk? | reasoning4 | `_delegated/D3_stats_review.md` |
| D4 | E6 forward testing | What is the fastest legitimate route from 0 forward rows to n>=100, and what would invalidate it? | diverse5 | `_delegated/D4_forward_review.md` |
| D5 | Red team | Argue that the whole project cannot find edge, and name the strongest reason. | all or reasoning4 | `_delegated/D5_redteam.md` |

Rules for the delegation track:
- **Peers are advisors, not evidence.** Nothing is adopted on consensus; it is adopted only if it survives a check against `_raw/`.
- Every consulted model and its response file are recorded in the Provenance footer of the document it influenced.
- A failed or empty peer response is recorded as `UNMEASURED` for that peer, never silently dropped.
- The fan-out prompt never contains credentials; keys stay in `~/dbpasses.txt` and are read only by the tool.
- The red-team (D5) is run even if D1-D4 agree, because agreement among similar models is not independent evidence.

---

## Provenance

- model: none (curator-written plan from frozen evidence and the sources cited inline)
- delegated: consult_multi.py (14 providers verified 2026-11-22); peer outputs land in `_delegated/` and are reviewed before adoption
- evidence: `docs/audit_review_2026-11-22/_raw/` (sha256 in `_MANIFEST.json`),
  `reports/class_metric_reconciliation_20261122.json`
- COMS reviewed 2026-11-22T07:41Z: Mercury3 CI fix PR #1048, equity momentum paper-trade spec at review-repo main 774bff9,
  ops runbook for the stale dashboard payload
- snapshot: `/audit3/audit3_ledger.json` `88606e1e…` generated 2026-11-22T06:35:41Z
