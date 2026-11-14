# PEER REVIEW R2 — finpredict v1 (Archive A) Master-Plan Inputs

**Reviewer:** R2 peer-review subagent · **Mode:** READ-ONLY · **Date:** 2026-11-14 ~17:55Z
**Reviewed archive:** `.kilo/worktrees/finpredict/2026-11-14/finpredict/2026-11-14T160004Z/`

---

## 1. Inventory (complete)

| Path | Role |
|---|---|
| `README.md` (43 lines) | Archive header; peer cross-reference table; unique v1 additions; verdict; reproducibility |
| `updates/2026-11-14-prediction-system-audit.md` (178 lines) | Full quantitative audit (Actions, per-class, frozen data, closed picks, statistics, peer cross-ref, UNVERIFIED) |
| `master-plan/PLAN.md` (76 lines) | The v1 MASTER PLAN (Phase 0–3, veto list, implementation order, verification) |
| `master-plan/inputs/01-crypto.md` | CRYPTO consolidated review (125 lines) |
| `master-plan/inputs/02-equity-etf.md` | EQUITY+ETF consolidated review (87 lines) |
| `master-plan/inputs/03-forex.md` | FOREX consolidated review (122 lines) |
| `master-plan/inputs/04-futures-commodity.md` | FUTURES+COMMODITY consolidated review (97 lines) |
| `master-plan/inputs/05-bond-mutual-funds.md` | BOND+MUTUAL FUNDS consolidated review (93 lines) |
| `master-plan/inputs/06-overall-statistical.md` | OVERALL+STATISTICAL consolidation (186 lines) |
| `master-plan/inputs/07-infra-ci.md` | INFRA/CI consolidation (148 lines) |
| `master-plan/inputs/folder-review/{ml,v2,v3,v4}.md` | Folder reviews of 4 peer archives (45/142/62/119 lines) |

Read in full. Missing items: **NOT FOUND** — `inputs/` has no `00_INDEX.md`; no standalone acceptance-tests doc (v2's `acceptance_tests.md` is referenced in PLAN.md:76 but not present in this archive).

---

## 2. Key claims / numbers (quoted, attributed)

- **Verdict (unanimous):** "WR 41.8% / PF 0.94 / Sharpe −1.31 / compounded −99%; policy-clean PF 0.2657; 0/9 classes money-ready; 658 strategies → E[false-positives]≈33 at p=5%" (PLAN.md:7).
- **Frozen/phantom core:** "123/127 (96.9%) frozen at pnl 0" verified batch (audit.md:29); "fabricated flat-3% cohort … every win exactly 3.00% with zero losers (286 trades)" (audit.md:51); "11 frozen closed phantoms" FOREX/SOFI (audit.md:50).
- **Statistical root cause:** "126 systems, 365 workflows, 112+ strategy names"; "16,126 → 7,914 valid (49%)" survivors; "CRYPTO z=−22.69, FOREX z=−6.02, EQUITY z=−3.03" below 50%; "PBO=0.0 degenerate… DSR uses n_trials=80" (06.md:28-40).
- **Metrics liveness:** "EDGE 0/20, Track 2/20, FWD WR 2/20 … 19/20 curated picks pnl==0.0" (06.md:51-52).
- **summary_picks impossible math:** 7 classes WR>100% (INDEX 1,141.2%, FUTURES 363.9%, COMMODITY 240.2%, ETF 232.9%, EQUITY 162.4%, FOREX 147.0%, BOND 127.8%) at `tools/sync_summary_picks_json.py:63-65,161` (06.md:56).
- **Infra:** 365 workflows; Python 3.14 masquerade via `update-environment: false` in 197 files; audit-dashboard cron 61/168 cancels; `scanner.py:2942` `KeyError:'LONG'` kills 93 runs/24h (07.md:19-22).

## 3. Strengths

- **Traced attributions.** Every fix row names a proposer and `file:line`; every number names its peer. Conflicts are collected (e.g. 06.md §4: five resolved/named disputes).
- **Veto list is principled** (PLAN.md:59-66): blocks destructive SQL, `current_price=entry_price` backfill, pre-emitter MUTUAL_FUND, pre-feed FUTURES/COMMODITY unblock, audit-dashboard `push:` re-trigger.
- **Folder-reviews add corrective value** (v4 review catches stale-copy "0 active/26-day" overstatement; v3 review flags ML_VALIDATION committed code change `d8c8dd25581`; v2 review adds GA1–GA4 deep-dive material — self-cancelling audit cron, 56.6-min FTP deploy, PEAD 60/60 push-retry exhaustion).
- **Phase gating is sane:** Phase 3 statistical re-validation explicitly waits for Phase 0+1 green.

## 4. Weaknesses / gaps

- **No single canonical source of truth.** PLAN.md and 06.md quote overlapping but inconsistent headline PF (0.94 survivor vs 0.2657 policy-clean) and P0 numbering differs across class docs (crypto F-1..F-23 vs equity F1..F15 vs forex A–F vs PLAN P0-x). The master plan does **not** present one unified fix registry with dedup IDs across classes.
- **Planned vs evidence mismatch:** PLAN.md:71 "targeted pytest `tests/test_dedup_cross_source.py`, `test_asset_class_status_labels.py`, `test_price_coverage_gate.py` (new)" — these tests are stated as to-be-written; no evidence they exist. NOT FOUND in this archive.
- **Line-number currency risk:** several docs flag that line numbers were verified against peer worktrees, not `origin/main` (05.md:75). Plan should re-verify line anchors on the merge target.
- **Conflicting decisions left open** (acceptable but must be closed pre-implementation): quote-status enum (2-value vs 5-value), dedup key (three variants), FUTURES restart-vs-retire, COMMODITY keep-bucket vs rebuild, `FOREX_HARD_DISABLE` default (OFF per v2 vs "HARD_DISABLED" per v4).
- **v1 unique additions under-quoted in PLAN.md:** the frozen 127-pick seed batch, fabricated flat-3% cohort, and the EQUITY n=8-vs-n=759/738 reconciliation are strong evidence in audit.md §2/§7 but appear only implicitly in PLAN P0-10/P0-2.

## 5. Recommended merge / adjust for the master plan

1. **Adopt as the planning backbone** — the phase/verdict/veto structure and per-class fix tables are strong; keep them.
2. **Build one canonical fix registry** (single table: ID, class, file:line, proposers, effort/risk, destructure flag, P0/P1/P2 phase) so P0 priorities are not re-listed differently in 7 docs. Reuse each class doc's existing IDs (F-1…F-23, F1…F15, etc.) instead of inventing new ones.
3. **Resolve the 4 open decision conflicts up front** (quote enum, dedup key, FUTURES/COMMODITY end-state, FOREX hard-disable default) — list them as a "decision gate" prerequisite to any P1, mirroring the existing FUTURES retire-vs-restart gate.
4. **Incorporate v2 GA1–GA4 deep-dive** (self-cancelling 60-min-vs-97min cron, FTP deploy step, queue saturation) as explicit Phase-0 infra items; the current PLAN P0-4 only says "space cron to ≥p95".
5. **Surface v1's unique evidence** (127-pick batch, flat-3% cohort, EQUITY rewrite) in the master-plan body, not just in inputs.
6. **Mark all "new test" claims as TODO** until the files exist; do not cite them as green.
7. **Re-verify line anchors vs main** during implementation; treat them as starting points.

## 6. Verdict

Strong, evidence-dense planning set; **merge as the master-plan foundation**, with the canonical-registry consolidation and decision-gate additions above. No fabricated numbers found; missing items explicitly marked NOT FOUND.
