# Review: `render_board.py`, `scan_boards.py`, `AGENT-RUNBOOK (2).md` (GitHub: `eltonaguiar/BESTIEJOB`)

**Date:** 2026-11-18 (UTC)  
**Source:** `https://github.com/eltonaguiar/BESTIEJOB` (main/root) — fetched via `raw.githubusercontent.com`  
**Requester:** review new files for usefulness; COMS message to reference this MD.

## Files reviewed

### 1) `scan_boards.py` (root)
- **Purpose:** read-only discovery against documented public ATS job-list APIs; emits **keyword leads (not verified jobs)**.
- **Adapters:** `lever`, `greenhouse`, `ashby`, `smartrecruiters` (allowlisted); source config from `employer-watchlist.csv` (`source_id`, `adapter`, `board_token`, `organization`).
- **Safety/controls:** default offline/`--plan` (prints endpoints, no network); `--read` required for GETs; bounded caps (`--max-pages` 1–20, `--max-details` 1–100, `--delay/--timeout` 1–60s); custom opener blocks redirects; 20 MB payload guard; polite UA; stops/defer host on 401/403/429 (honors `Retry-After` logging); refuses to overwrite `--out` (JSONL append via new file).
- **Extraction:** keyword regex over title+body into tracks `ServiceNow` (`service now`, `gliderecord/ajax/system`, `script includes`, `integrationhub`), `Salesforce` (`salesforce`, `lwc`, `soql`, `apex triggers`), `Other` (data engineer/programmer, MDM, technical integrator, Informatica, integration, Power Platform/BI, ETL, workflow automation). SmartRecruiters fetches per-posting detail (bounded) because list rows can omit duties; Greenhouse uses `content=true`.
- **Date semantics surfaced:** GH emits `updated_at (NOT posted)`, Ashby `publishedAt (LAST published)`, SR `releasedDate`; records `time_field/time_value`, `status=lead_only`, `observed_at_utc`.
- **Gaps/limits:** no Workday/BambooHR/TalentNet/ADP/Phenom/Oracle CE adapters; no geo/eligibility filter (emits out-of-scope countries/false positives by design); keyword-only (misses body-only/cert signals like **CSA/CAD/CIS/ITSM/CMDB/ITAM**, French variants, many platform-build synonyms); depends on curated `employer-watchlist.csv`; no dedupe/normalization/verification/dead-link/freshness gating.

### 2) `render_board.py` (root)
- **Purpose:** offline, deterministic renderer that builds `board.html` from a reviewed single-batch `job-snapshot.csv` in the same directory (atomic write via temp+replace). No network/deps/auto-verification.
- **Inputs/validation:** requires non-empty snapshot; unique `(publisher, posting_id)`; single `checked_local_date` across rows (no mixed-batch labeling); tracks `{ServiceNow, Salesforce, Other}`; geo buckets `{Remote from Ontario, Toronto, Global — confirm Ontario}`.
- **Output/UI:** standalone filterable HTML (track/geo/date/channel/search) grouping into Remote from Ontario, Toronto (office/hybrid/etc., not “no-office remote”), and Global-remote-confirm (not counted as Ontario-eligible). Shows platform vs adjacent vs confirm counts, evidence/access details, date freshness (`<=30d` recent/older/undated), issuer/agency channel, apply/corroborating links, posting IDs, print-friendly styling. Escapes content/URLs; asserts absolute http/https posting URLs.
- **Gaps/limits:** expects a specific CSV schema (not the canonical repo feed/inbox schema); not a replacement for `tools/build_site.py`/site publishing; no sourcing/verification logic; usefulness depends on having a curated, verified snapshot.

### 3) `AGENT-RUNBOOK (2).md` (root)
- **Purpose:** comprehensive operator/agent runbook (dated 2026-11-17, Toronto) for finding Toronto and remote (Ontario-eligible) SN/SF/adjacent developer jobs with evidence-first, rights-aware practice.
- **Strengths/alignment:** employer-first sourcing (repeat hirers, SN/SF partners, ISVs, Toronto conferences/events/sponsors, end-customer orgs) with cadence and source-record fields; strict rights policy (`manual_discovery/permitted_api_private/own_site_attributed/redistribution_approved/unknown`); documented ATS interfaces (Lever/GH/Ashby/SR) with correct date/field semantics; `scan_boards.py` positioned as leads-only; duty/geo/date/pay/liveness verification and closure decisions; identity/dedupe order and separate reporting (`new_unique/existing_rechecked/canonical_upgrades/changed/closed/review/source_failed`); BESTIEJOB contribution path (inbox + `scripts/check_inbox.py` + `tools/jobs_merge_inbox.py`, hourly single-writer `bestiejob-main-write`, invariants, no competing publisher) and 7-day pilot metrics.
- **Caveats:** some examples/revision refs may be time-bound; operational guidance must be reconciled with current `main` workflows/gates.

## Usefulness (for BESTIEJOB SN/SF/Other, Toronto/GTA + Canada-remote)

| Item | Useful now | Main value | Key limitation |
|---|---|---|---|
| `scan_boards.py` | **Yes (discovery primitive)** | Safe, bounded ATS lead generation for Lever/GH/Ashby/SR; good fit for Batch 1 (company portals/ATS) feeding a staging/verify step | Narrow keywords, no geo/body-cert expansion, 4 adapters only, leads≠verified |
| `render_board.py` | **Conditional** | Good for reviewed, dated, human/agent snapshot boards with strong evidence/geo labeling (separate from main site) | Requires curated `job-snapshot.csv`; schema/toolchain parallel to main build |
| `AGENT-RUNBOOK (2).md` | **Yes (process reference)** | High-quality sourcing/verification/rights/dedupe/measurement playbook; reinforces constraints we track | Needs merge with existing runbooks and cert/body-aware + GTA-geo enhancements |

## Suggested approach

1. **Adopt as staged discovery, not direct publish:** run `scan_boards.py --plan/--read` per-permissioned `employer-watchlist.csv` sources → normalize leads to canonical schema → verify (issuer, duties, geo/remote eligibility, absolute posted date, liveness/dead-link 404/410/451) → dedupe (URL/tenant+posting_id, `title|company|city`, fingerprint/req ID) → merge via `tools/jobs_merge_inbox.py`/build path under `bestiejob-main-write` (no parallel publisher).
2. **Relevance lift (align to our target):** extend matching beyond title keywords to **body/cert-aware, two-tier** signals (ServiceNow, Salesforce, CSA, CAD, CIS, ITSM, CMDB, ITAM + platform-build terms), with geo precision for **Toronto/GTA cities (Toronto/Mississauga/Markham/Etobicoke, etc.) + Canada-remote**; keep global-remote/uncertain in confirm/review.
3. **Adapter/coverage expansion:** prioritize direct ATS/company portals and add adapters/sources already relevant in repo (Workday CXS, SmartRecruiters/GH/Lever/Ashby coverage checks, agency boards, gov/city portals) per `ideas/bestiejob/agent-execution-runbook.md` batches; treat conference/partner rosters as employer leads (not vacancies).
4. **Quality gates & observability:** require absolute source-published date where available; enforce dead-link/truth-check policy and board invariants/baseline awareness; emit per-source counts (scanned/leads/deduped/gated/verified), coverage gaps, and failures.
5. **Snapshot rendering (optional):** use `render_board.py` only for reviewed, dated evidence snapshots (`job-snapshot.csv`) when a standalone audit/review artifact is useful; keep it decoupled from main site generation.
6. **Runbook consolidation:** reconcile `AGENT-RUNBOOK (2).md` with `ideas/bestiejob/agent-execution-runbook.md` and current `eltonaguiar/BESTIEJOB` workflows/gates; codify cert/body-aware matching, GTA-remote rules, and inbox/merge/CI flow.

## Work started (this session)
- **COMS:** sent review/recommendation summary to `mentions/all` referencing this MD (qos0, non-retained; delivery depends on active listeners).
- **Prototype:** `ideas/bestiejob/prototypes/job_signal_matcher.py` (+ `README.md`) — stdlib, no-network starter classifier for body/cert-aware track signals (SN/SF/Other incl. ITSM/CMDB/ITAM, CSA/CAD/CIS) and Toronto/GTA + Canada/Ontario-remote geo/eligibility heuristics. Demo run verified: `python3 ideas/bestiejob/prototypes/job_signal_matcher.py --demo`.

## Validation before integration
- Dry-run on a small, permitted watchlist slice; manually sample leads for SN/SF/Other duty fit, Toronto/GTA or Canada-remote eligibility, and date/liveness correctness.
- Confirm no regressions to `tools/job_source_truth.py --check`, link verification (404/410/451), and `board-invariants`/baseline handling.
- Document any adopted changes in `updates/` (what/why/verification) and avoid committing secrets or paywalled/gated content.

## Related local artifacts
- `ideas/bestiejob/agent-execution-runbook.md`
- `ideas/bestiejob/consolidated-ideas.md`
- `ideas/bestiejob/clean-ideas/clean-ideas.md`
- `updates/2026-11-18-bestiejob-fix-investigation.md`
