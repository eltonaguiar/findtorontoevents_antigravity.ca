# CI / pipeline fit checklist (BESTIEJOB)

Use before integrating prototype outputs into `eltonaguiar/BESTIEJOB` (`main`, single-writer `bestiejob-main-write`).

## 1. Pre-merge gates (local/dry-run)
- [ ] **Source/rights:** each scanned source permissioned; `rights/reuse` recorded; no secrets/PII/paywalled content committed.
- [ ] **Lead vs verified:** only verified records eligible for publish/inbox; `dates.posted_at` is absolute and source-backed (or explicitly null-with-reason and excluded from fresh/publish windows).
- [ ] **Liveness:** dead-link/access states checked (404/410/451/closed/removed vs blocked/unknown handled distinctly).
- [ ] **Dedupe:** stable identity applied (posting/req/URL/fingerprint as appropriate); no title+city-only merges; provenance preserved.
- [ ] **Classification/geo:** SN/SF/Other duty+evidence reviewed; Toronto/GTA vs Canada/Ontario-remote vs global-confirm labeled; US/excluded filtered from in-scope counts.
- [ ] **Format/validators:** `scripts/check_inbox.py --file <inbox-file>` (if staged), `tools/jobs_merge_inbox.py --dry-run` reviewed for full diff/parse/family effects.

## 2. Repo checks (as applicable)
- [ ] `tools/job_source_truth.py --check` (truth-check gate) — no new gated/paywall violations.
- [ ] Link verification expectations (404/410/451) satisfied for affected rows/sources.
- [ ] `scripts/board_invariants.py` / baseline impact understood (ratchet not worsened without justified re-baseline).
- [ ] Feed/build sync steps if merged (`scripts/sync_readme_to_jobs.mjs`, `tools/build_site.py`) produce expected, reviewable diffs.
- [ ] No competing publisher workflows; changes respect serialized write paths.

## 3. Adoption workflow
1. Run adapter in `--plan`/bounded `--read` on permissioned sources → normalize + classify.
2. Verify (date/liveness/geo/duty/rights) → dedupe/review; export only eligible rows.
3. Stage per conventions (e.g. `inbox/<agent>--YYYY-MM-DD--vN.md`), validate, dry-run merge, inspect full diff.
4. Commit fix + `updates/YYYY-MM-DD-*.md` doc (what/why/sources/verification/metrics) in same change set.
5. Monitor CI runs (Hourly/Gap/Truth/Board invariants) and reconcile failures with evidence.

## 4. Prototype-specific checks
- [ ] `job_signal_matcher.py` + `eval_matcher.py`/`eval_relevance.py` pass on fixture set; review FP/FN cases before threshold changes.
- [ ] `normalize_lead.py` output reviewed for dedupe_key stability, URL normalization, preserved raw evidence, and `needs_verification=true`.
- [ ] No direct write to live feeds/README from prototype tools.

## 5. Rollback/containment
- Keep changes additive and source-attributed; isolate new adapters/flags behind config.
- If CI/gates regress, revert the specific ingestion change, document cause, and update fixtures/rules with evidence.
