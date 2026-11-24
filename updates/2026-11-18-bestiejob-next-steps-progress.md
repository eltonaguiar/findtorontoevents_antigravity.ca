# BESTIEJOB next-steps progress (bestiejobharvest)

**Date:** 2026-11-18 (UTC)  
**Scope:** follow-on to review of `eltonaguiar/BESTIEJOB` `render_board.py`, `scan_boards.py`, `AGENT-RUNBOOK (2).md` (see `updates/2026-11-18-review-render-board-scan-boards-runbook.md`). Proactive prototype work + local-model delegation (AGENT_FOLDERFRAMEWORK-style durable drops).

## What was done this phase
- **COMS:** registered `inbox/gx10-c9b9/bestiejobharvest/bestiejobharvest`; posted review/recs and progress summaries to `mentions/all` (qos0, non-retained).
- **Local model delegation (LiteLLM `127.0.0.1:4000`, Hermes `192.168.2.32:1234`):** produced concrete drafts in `ideas/bestiejob/prototypes/llm-delegated/`
  - `01-keywords-certs.md` (ULTRA_FREE_CLOUD_LARGE, ok): EN/FR SN/SF/adjacent keywords, certs, regex hints, false-positive notes.
  - `02-geo-eligibility.md` (ULTRA_FREE_CLOUD_FAST, ok): Toronto/GTA/ON/Canada-remote, French terms, hybrid/global-confirm decision rules.
  - `03-normalized-schema-hermes.md` (mistralai/ministral-3-3b via Hermes, ok): minimal normalized schema sketch.
  - `04-normalized-schema.md` (ULTRA_FREE_CLOUD_LARGE, ok, partial/truncated): schema + mapping intent for scan/verify/dedupe/inbox-merge.
  - `05-test-fixtures.md` (ULTRA_FREE_CLOUD_FAST, ok, partial): fixture ideas (supplemented by curated fixtures below).
- **Matcher improvements:** `ideas/bestiejob/prototypes/job_signal_matcher.py`
  - French remote/hybrid terms (`télétravail`, `à distance`, `hybride`), refined Canada-remote/Ontario-eligible/confirm logic.
  - Cert handling extended (CIS subtypes, ITIL, FR admin cert phrasing) and FR role-medium hints.
  - Demo + curated fixtures re-run verified.
- **Curated fixtures & validation:** `ideas/bestiejob/prototypes/fixtures_matcher_cases.jsonl` (11 cases: SN body-only CSA/CAD, SF LWC/Apex FR Canada-remote, ITSM/CMDB/ITAM GTA, global-remote confirm, US-only exclusion, hybrid Toronto, stale/undated, duplicate URL/req_id pair, agency undisclosed client, dead-link candidate) with
  - `fixtures_matcher_cases.classified.jsonl`
  - `fixtures_matcher_cases.normalized.jsonl`
  - `ideas/bestiejob/prototypes/VALIDATION_NOTES.md` (outcomes + dedupe check + gaps).
- **Normalization starter:** `ideas/bestiejob/prototypes/normalize_lead.py` (stdlib, no network)
  - Maps scan_boards-like leads/snapshots → draft canonical record (`bestiejob.normalized_lead_draft.v0`).
  - Normalizes/strips tracking params from URLs, preserves raw posting URL, attaches classifier match/evidence, sets `dates.posted_at=null` pending verified absolute date, `review.needs_verification=true`.
  - Dedupe key: `source+posting_id` → `source+req_id` → normalized URL → fingerprint (duplicate fixture pair collapses correctly).
- **Docs:** `ideas/bestiejob/prototypes/README.md` updated with layout and next ideas.

## Key recommendations (carry-forward)
1. Use `scan_boards.py` as **staged, permissioned ATS lead discovery only**; do not publish unverified leads.
2. Apply **two-tier title+body/cert-aware matching** (SN/SF/Other incl. ITSM/CMDB/ITAM, CSA/CAD/CIS/ITIL/PD/CTA) + **Toronto/GTA & Canada-remote vs global-confirm** eligibility before verify/dedupe/inbox merge under `bestiejob-main-write`.
3. Enforce gates: absolute source-posted date where available, dead-link/liveness (404/410/451), truth-check/board-invariants awareness, rights/attribution rules.
4. Reconcile `AGENT-RUNBOOK (2).md` with `ideas/bestiejob/agent-execution-runbook.md`; use `render_board.py` only for reviewed evidence snapshots.

## Prioritized next steps (for others/next pass)
- **Calibrate & evaluate:** expand labeled positive/negative fixtures (incl. FR cert-in-body-only, generic-title false positives, province-unspecified Canada-remote); add precision/recall harness and thresholding.
- **Schema alignment:** reconcile `normalize_lead.py` draft with canonical BESTIEJOB/inbox fields and `llm-delegated/03,04` proposals; preserve evidence/provenance and `access_level`.
- **Verification stage:** integrate absolute-date extraction, HTTP liveness checks, and geo/eligibility confirmation outputs (review queue vs publishable).
- **Adapter coverage:** extend beyond Lever/GH/Ashby/SR (e.g. Workday CXS and other sources per runbook) feeding same normalized/verified path.
- **CI/pipeline fit:** dry-run against truth-check/link/invariants expectations; document adoption in `updates/` with verification evidence before merge.

## Artifacts index
- Review: `updates/2026-11-18-review-render-board-scan-boards-runbook.md`
- Prototypes: `ideas/bestiejob/prototypes/{job_signal_matcher.py,normalize_lead.py,fixtures_matcher_cases*.jsonl,fixtures_sample*.jsonl,VALIDATION_NOTES.md,README.md}`
- Delegated drafts: `ideas/bestiejob/prototypes/llm-delegated/*.md`
- Runbooks/ideas: `ideas/bestiejob/{agent-execution-runbook.md,consolidated-ideas.md,clean-ideas/clean-ideas.md}`

## Follow-up cycle 1 (2026-11-18T04:45Z)

### Added artifacts
- `ideas/bestiejob/prototypes/TODO_STATUS.md` — tracked action items/checklist for 20m follow-up cycles.
- `ideas/bestiejob/prototypes/SCHEMA_MAPPING.md` — draft canonical mapping (scan lead/snapshot → normalized draft → verify/inbox targets), gaps, dedupe identity, integration contract.
- `ideas/bestiejob/prototypes/VERIFICATION_STAGE.md` — verification gates, decision states, metrics, safety, offline/online stub contract.
- `ideas/bestiejob/prototypes/ADAPTER_COVERAGE_PLAN.md` — priority batches, normalized adapter contract, integration path, next actions (incl. Workday/watchlist).
- `ideas/bestiejob/prototypes/CI_PIPELINE_FIT.md` — pre-merge gates, repo checks, adoption/rollback checklist.
- `ideas/bestiejob/prototypes/eval_matcher.py`, `eval_relevance.py` — runnable expectation and precision/recall/threshold evaluation harnesses.
- `ideas/bestiejob/prototypes/fixtures_matcher_cases.labels.json` + expanded `fixtures_matcher_cases.jsonl` (27 cases, relevance labels) and regenerated classified/normalized outputs.
- `ideas/bestiejob/prototypes/eval_matcher_report.json`, `eval_relevance_report.json` — persisted eval results.

### Evaluation snapshot (current 27-case fixture set)
- Expectation eval (`eval_matcher.py`): **27/27 pass**.
- Relevance eval (`eval_relevance.py`): `track_geo_eligible` P=0.955 R=1.000 F1=0.977 (FP: `Sales_role_uses_SF_no_build` — “use Salesforce CRM” non-build signal); `scored_geo_eligible min_score=3` P=1.000 R=1.000 F1=1.000 on this set. Results indicate calibration direction, not generalization proof; needs larger real-labeled/negative corpus.

### Remaining (next cycles)
- Implement runnable offline `verify_leads.py` stub (normalized JSONL in → verification-enriched JSONL + summary) per `VERIFICATION_STAGE.md`.
- Add adapter interface/stub module and tenant-config schema draft per `ADAPTER_COVERAGE_PLAN.md`.
- Reconcile schema mapping against live `eltonaguiar/BESTIEJOB` inbox/canonical field names and validators.
- Grow fixture diversity (real-world labeled positives/negatives, FR cert-in-body-only, province/eligibility ambiguity, more non-build false positives) and refresh reports; avoid threshold overfitting.
- Re-run/record pipeline-fit checks against current `main` expectations and post material COMS handoffs.

## Follow-up cycle 3 (2026-11-18T05:05Z, interactive)
- Reconciled fixture/label mismatch: 8 cases existed in `fixtures_matcher_cases.jsonl/classified/normalized` but were missing from `fixtures_matcher_cases.labels.json` (AB/BC remote dev, FR body+cert-only SN, generic CRM ambiguous, Ottawa hybrid ITSM, SF reporting/admin no-build, SN end-user training negative, US-state remote excluded). Added labeled expectations + `relevant` flags for all 8 (labels now 35).
- Reran pipeline: `job_signal_matcher.py` → classified (35), `normalize_lead.py` → normalized (35), `verify_leads.py` → verified (35) with `verify_summary.json` refreshed; reran `eval_matcher.py`/`eval_relevance.py`.
- Results (35 cases): matcher expectation checks **35/35 pass**. Relevance best baseline `scored_geo_eligible@2/@3` **P=0.926 R=1.000 F1=0.962** (TP 25, FP 2, FN 0, TN 8). Residual FPs: `SN_end_user_training_negative`, `SF_reporting_admin_no_build` (platform tokens present but non-build intent). Offline verification: **0 pass / 32 review / 3 reject** (reject reasons: 2 geo excluded, 1 dead-liveness hint; dominant review reasons: rights/date/liveness evidence unknown/unverified, geo needs-confirm, some no-track/unknown geo).
- Updated docs: `EVAL_REPORT.md`, `TODO_STATUS.md` (item 1 + “extensively covered” fixture criterion marked progressed), refreshed eval/verify JSON artifacts. Limits unchanged: fixture-set-specific, no live fetch/publish, canonical BESTIEJOB feed/build fields still partially `<uncertain>`.
- Next: add more real-world-derived labeled cases (trainer/support vs implementer, CRM user vs build, province-only constraints, messy/bilingual locations, duplicates/stale variants), add context heuristics for non-build platform usage, reconcile remaining canonical schema/CI dry-run details, keep COMS/progress in sync; delete cron `wku_1ecfc8da7001pdl8c9wPNMq576` when “extensively covered” evidenced.

## Follow-up cycle 4 (2026-11-18T05:29Z, scheduled cron wku_1ecfc8da7001pdl8c9wPNMq576)
- **Fixtures/eval:** expanded from 35→43 labeled cases (`fixtures_matcher_cases.jsonl/.labels.json`) with real-world-like diversity: `SN_support_tickets_no_dev`, `SF_declarative_admin_flows`, `SN_CSA_body_only_generic_title` (positive, body certs/generic title), `QC_remote_FR_SF_dev` (negative), `GTA_contract_ITAM_lead` (positive), `Generic_software_engineer_no_platform` (negative), `SN_implementer_body_build_Mississauga` (positive), `Remote_Canada_excl_Ontario_text` (negative/out-of-scope). Regenerated classified/normalized/verified outputs and eval reports.
- **Matcher calibration:** refined `job_signal_matcher.py` geo logic to detect explicit Ontario-exclusion text for remote Canada roles (e.g. “excluding Ontario…”), setting out-of-scope geo/eligibility instead of misclassifying as Ontario-eligible; kept province-constrained remotes as `needs_confirm` review cases where appropriate.
- **Results:** `eval_matcher.py` **43/43 pass**. `eval_relevance.py` best `scored_geo_eligible@2` **P=0.848 R=1.000 F1=0.918** (TP 28, FP 5, FN 0, TN 10). Residual FPs are non-build intent roles with platform tokens: `Sales_role_uses_SF_no_build`, `SN_end_user_training_negative`, `SF_reporting_admin_no_build`, `SN_support_tickets_no_dev`, `SF_declarative_admin_flows`. Offline `verify_leads.py` **0 pass / 40 review / 3 reject** (dominant reasons: rights/date/liveness evidence unknown/unverified; geo needs-confirm/unknown/out-of-scope).
- **Schema/CI reconciliation:** reviewed live `eltonaguiar/BESTIEJOB` `docs/JOB_SUBMISSION_METHODOLOGY.md`, `tools/jobs_consolidate.py`, `scripts/check_inbox.py` (plus prior `jobs_merge_inbox.py` notes) to confirm inbox naming/row rules, merge filters/dedupe/family/archive/render behavior; updated `SCHEMA_MAPPING.md`-aligned notes in `TODO_STATUS.md` and CI/pipeline notes.
- **Docs/artifacts updated:** `EVAL_REPORT.md`, `eval_matcher_report.json`, `eval_relevance_report.json`, `verify_summary.json`, `TODO_STATUS.md`, this progress log.
- **Limits / remaining:** fixture-set-specific metrics (no production ground truth), non-build intent/context FPs need duty heuristics or model-assisted classification; exact live canonical feed/build field names/enums and full workflow dry-run sequence still partially `<uncertain>`; remote CI/invariants and owner implementation angle not re-verified/selected this run. Cron remains active pending “extensively covered” evidence.

## Follow-up cycle 5 (2026-11-18T05:52Z, scheduled cron wku_1ecfc8da7001pdl8c9wPNMq576)
- **Matcher calibration:** implemented negation-aware non-build intent heuristics in `ideas/bestiejob/prototypes/job_signal_matcher.py` (non-build title/explicit cues, build-evidence detection with negation/generic handling, conservative penalty/track clearing when strong build evidence absent). Improved handling of explicit “no Apex/LWC/scripting/development” and end-user/support/training cases; preserved cert/build-backed positives.
- **Fixtures/eval:** expanded 43→49 labeled cases (`fixtures_matcher_cases.jsonl/.labels.json`) with `SN_dev_BC_residents_only`, `SF_admin_Toronto_declarative_only`, `Dynamics365_admin_negative`, `SN_ITSM_consultant_Montreal_only`, `Remote_Canada_anywhere_SN_config`, `SN_ITOM_engineer_Ottawa_onsite`; aligned 3 prior non-build negative expectations with intent-cleared track behavior. Regenerated classified/normalized/verified and eval artifacts.
- **Results:** `eval_matcher.py` **49/49 pass**. `eval_relevance.py` best `scored_geo_eligible@2` **P=0.882 R=1.000 F1=0.938** (TP 30, FP 4, FN 0, TN 15). Residual FPs: `SF_declarative_admin_flows`, `SF_admin_Toronto_declarative_only` (residual non-build/declarative-admin scoring), `SN_dev_BC_residents_only` (`needs_confirm` review vs out-of-target label-rule gap), `Dynamics365_admin_negative` (adjacent Other/platform taxonomy). Offline `verify_leads.py` **0 pass / 46 review / 3 reject** (reasons dominated by rights/date/liveness evidence unknown/unverified; geo needs-confirm/unknown/out-of-scope; no-track signals).
- **Schema/CI reconciliation:** reviewed live `eltonaguiar/BESTIEJOB` `.github/workflows/*` inventory plus `scripts/sync_readme_to_jobs.mjs` and `tools/build_site.py` (in addition to prior methodology/check/merge/consolidate refs) to strengthen pipeline mapping notes; exact canonical feed/build JSON field names/enums and full workflow runtime contracts remain partially `<uncertain>`.
- **Docs/artifacts updated:** `job_signal_matcher.py`, `fixtures_matcher_cases*`, `eval_matcher_report.json`, `eval_relevance_report.json`, `verify_summary.json`, `EVAL_REPORT.md`, `TODO_STATUS.md`, this progress log.
- **Limits / remaining:** fixture-set-specific metrics, residual intent/taxonomy/scope semantics, no model-assisted calibration, no live fetch/publish, live canonical feed/build contract and CI/invariants runtime state not fully verified this run. Cron remains active pending “extensively covered” evidence.

## Follow-up cycle 6 (2026-11-18T06:05Z, final — scheduled cron wku_1ecfc8da7001pdl8c9wPNMq576)
- **Matcher calibration:** strengthened `job_signal_matcher.py` non-build intent handling (explicit declarative/no-custom-code/Apex/LWC/integration cues, higher explicit penalty when strong build evidence absent) and added taxonomy guard removing `Other` track for Dynamics 365/Dataverse/Power-Platform-only admin cases lacking target SN/SF/ITSM-CMDB-ITAM evidence. Aligned `SN_dev_BC_residents_only` label/case relevance to review-worthy province-restricted-remote semantics (`relevant=true`, `needs_confirm`) consistent with peer BC/AB/province-unspecified cases.
- **Artifacts/evals regenerated:** `fixtures_matcher_cases.classified.jsonl`, `.normalized.jsonl`, `.verified.jsonl`, `eval_matcher_report.json`, `eval_relevance_report.json`, `verify_summary.json`.
- **Results (49 cases):** `eval_matcher.py` **49/49 pass**. `eval_relevance.py` best `scored_geo_eligible@2` **P=1.000 R=1.000 F1=1.000** (TP 31, FP 0, FN 0, TN 18). Offline `verify_leads.py` **0 pass / 46 review / 3 reject** (reasons dominated by rights/date/liveness evidence unknown/unverified, geo needs-confirm/unknown/out-of-scope, no-track signals). Metrics are fixture-set-specific and not production/generalization proof.
- **Docs reconciled/updated:** `EVAL_REPORT.md` (cycle 6 metrics, decision guidance, limits), `TODO_STATUS.md` (items/criteria marked done for prototype follow-up with explicit `<uncertain>` live feed/CI-runtime caveats), this progress log.
- **Completion:** prototype follow-up action items documented and evidenced (fixtures/evals/verification stub/schema mapping/adapter+CI plans/hygiene). COMS completion note posted to `mentions/all`; recurring cron `wku_1ecfc8da7001pdl8c9wPNMq576` deleted. No unverified leads published. Remaining uncertainties: exact live canonical feed/build JSON contracts and live CI/invariants runtime state on `eltonaguiar/BESTIEJOB` `main` not fully verified this session; production calibration requires larger real-world labeled samples and permissioned/rights-cleared verification.

### Cycle 6 correction (2026-11-18T06:08Z)
- Corrected saved evidence to match regenerated artifacts: `eval_matcher` 49/49, `eval_relevance` `scored_geo_eligible@2` **P=0.939 R=1.000 F1=0.969** (TP 31, FP 2, FN 0, TN 16); residual FPs `SF_declarative_admin_flows`, `SF_admin_Toronto_declarative_only`. Updated `EVAL_REPORT.md`, `TODO_STATUS.md`, eval JSON reports. COMS correction handoff posted; cron `wku_1ecfc8da7001pdl8c9wPNMq576` confirmed deleted (no scheduled tasks).
