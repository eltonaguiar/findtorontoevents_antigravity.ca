# BESTIEJOB — Consolidated ideas (enhancement, bug-fix, QA)

**Purpose:** single collection of pipeline enhancement, bug-fix, and QA ideas for finding ServiceNow/Salesforce (and related ITSM/CMDB/ITAM) jobs in Toronto/GTA and Canada-remote markets. Includes session findings + source-first strategy inputs. **Not deduplicated** (see `clean-ideas/clean-ideas.md`).

**Legend:** `[BUG]` defect/reliability, `[QA]` quality gate/process, `[ENH]` capability/yield, `[STRAT]` architecture/strategy. **Status:** `observed` (evidence from repo/CI), `proposed`, `<uncertain>` needs verification.

---

## A. Current-state observations (evidence-backed)
- `[OBS]` BESTIEJOB is multi-source (Adzuna, Workday CXS, SmartRecruiters, Greenhouse/Lever/Ashby, LinkedIn guest, Job Bank, Eluta, Workable, Phenom, Oracle CE, agency boards) with absolute-date requirements, liveness checks, URL+fingerprint dedupe, inbox→merge→README/feed/site flow, and serialized pushers. (repo: `.github/workflows/*`, `scripts/*`, `tools/*`)
- `[OBS][BUG]` **Job Source Truth Check failing on remote main** (run 44223129196, HEAD `7851e00`): 35 gated rows (`theladders.com`/`jobleads.com`) in canonical artifacts; `--check` exits 1. Indicates paywall/signup URLs ingested/retained. `observed`
- `[OBS][BUG]` **Gap channels publish failure** (run 44211439366): sweep/merge/build succeeded but `Commit and push` failed with single-retry push under `bestiejob-main-write` contention. `observed`
- `[OBS][BUG]` **board invariants failing** (run 44123817042): published-board audit vs baseline/ratchet; per-class debt/triage required. `observed`
- `[OBS][ENH]` Relevance is largely title/keyword-regex driven (`daily_job_scan.mjs`, `fresh_ca_scan.py` classify) — postings mentioning ServiceNow/Salesforce/CSA/CAD/CIS/ITSM/CMDB/ITAM mainly in body/requirements may be missed. `observed`
- `[OBS][QA]` COMS bus supports live wakeups/roster but has no offline inbox read/history; messages non-retained (operational coordination gap, not job data). `observed`
- `[OBS]` Unlanded local truth-check remediation bundle exists (`updates/2026-11-18-bestiejob-truthcheck-fix*`): ingest gate, domain config, purge-to-ledger script; claims local pass, not pushed/validated vs current HEAD. `observed`

## B. Bug-fix / reliability ideas
- `[BUG][QA]` Enforce gated-domain blocklist (`job_source_truth.domain_is_gated`, `config/gated_domains.txt`, env extras) at **ingest + inbox/merge preflight + final build**; never publish paywall/signup-trap URLs as canonical links.
- `[BUG]` Purge existing gated rows from canonical artifacts and retain roles in a ledger with cross-ref search links (Google Jobs/LinkedIn/Indeed/Adzuna) only when no verified employer/ATS URL is known.
- `[BUG]` Harden push steps for shared-writer workflows (gap-channels, others) with bounded multi-attempt fetch/rebase/push loops and clear conflict handling to avoid stranded successful pipelines.
- `[BUG]` Triage `board_invariants` failures against `reports/board_invariants_baseline.json`; fix data/logic to reduce counts or re-baseline only with justified, reviewed evidence; keep report artifacts.
- `[BUG][QA]` Make truth-check/invariant failures actionable: emit grouped root causes and affected URLs/rows; fail on canonical README when policy requires, but only after cleanup path is deterministic.
- `[BUG][QA]` Prevent duplicate/near-duplicate reintroduction by strengthening canonical apply-URL resolution for redirectors (where safe) and keeping requisition/content fingerprints.

## C. QA / data-quality ideas
- `[QA]` **Freshness:** accept only source-published absolute dates; reject/hold undated guesses; prefer today/yesterday fast paths for hot leads.
- `[QA]` **Liveness:** keep dead-only policy (404/410/451) with bot-wall/transport-safe handling; reverify on schedule and before merge/publish.
- `[QA]` **Dedupe:** normalized URL primary key + `title|company|city` fingerprint + ATS requisition ID when available; collapse mirrors/reposts/geo variants of same req.
- `[QA]` **Geo/remote precision:** eligible if Toronto/GTA/ON/Canada or explicit Canada-remote signals; exclude US-only/other-country remote and ambiguous bare "Remote" without Canada eligibility.
- `[QA]` **Relevance precision:** require strong platform/cert signal + role intent for body matches; keep sales/intern exclusions context-aware (never exclude legit "Salesforce Developer" etc.).
- `[QA]` **Observability:** per-run metrics — net-new by profile/geo/source, drops (gated/undated/dead/dupe/out-of-geo/off-topic), median posting age, top-yield queries/tenants.
- `[QA]` **Human review queue:** low-confidence/ambiguous classifications and high-impact changes routed for review, not auto-misclassified.

## D. Enhancement / yield ideas (sourcing & matching)
- `[ENH]` Two-tier matching: Tier A auto-accept (platform/cert in title/company/strong fields); Tier B body/description match requires platform/cert + role-intent tokens and exclusion guards.
- `[ENH]` Expand token/query library: ServiceNow, Service Now, CSA, CAD, CIS-*, ITSM/ITOM/ITAM/CMDB/HRSD/CSM/GRC/SecOps, Flow Designer, Service Catalog, Discovery, Integration Hub; Salesforce, Apex, SOQL, LWC, Visualforce, Flow, CPQ, Revenue/Marketing/Data Cloud, Agentforce, Platform Admin/Developer/App Builder; geo terms Toronto/Mississauga/Markham/Etobicoke/GTA/Ontario/Canada/Remote Canada.
- `[ENH]` Run cert/module-led and variant-title queries per engine (Adzuna, LinkedIn guest, ATS search endpoints, Job Bank/indices) in rate-aware batches.
- `[ENH]` Batch 1 — **Company portals/ATS (few tenants at a time):** Workday CXS + detail, SmartRecruiters, Greenhouse/Lever/Ashby/Workable/Phenom/Oracle; probe tenants before trust.
- `[ENH]` Batch 2 — **Canadian government/public sector:** Job Bank (certain) + verified provincial/municipal/federal boards with proven absolute-date adapters `<uncertain>` sources require verification.
- `[ENH]` Batch 3 — **Toronto/GTA cities:** Toronto (jobs.toronto.ca, certain) plus Mississauga/Markham/Etobicoke-area civic/municipal portals `<uncertain>` exact endpoints/adapters until verified; include GTA geo filters on aggregators.
- `[ENH]` Batch 4 — **Partners/customers/conference attendees:** ServiceNow Partner Finder segments and Salesforce Partner Finder/consulting ecosystem (certain concepts) to build employer universe; conference sponsor/exhibitor/attendee lists and specific rosters `<uncertain>` until verified; convert to direct ATS/career sources.
- `[ENH]` Grow ATS tenant discovery from live board/feed URLs, employer career pages, and verified partner/customer lists; health-check endpoints.
- `[ENH]` Curate agency boards (`config/agency_boards.json`) only with date-proven adapters and relevance/value.

## E. Source-first strategy ideas (user-provided, to incorporate)
- `[STRAT]` Build a **company universe** (partners, consultancies, customers, repeat hirers, conference employers) as core asset; ingest jobs primarily from **direct ATS APIs/career sites**; use aggregators/boards for discovery & validation, not as scraping backbone.
- `[STRAT]` Respect ToS/robots/rate limits/auth walls; **no circumvention** (no login/CAPTCHA/IP-block evasion, no proxy/account farming). Prefer official APIs/RSS/sitemaps/open data/JSON-LD.
- `[STRAT]` Store minimum necessary fields + hashes/evidence; link to original posting; avoid republishing full descriptions where licensing uncertain.
- `[STRAT]` Lifecycle tracking (`first_seen/posted/updated/last_seen/removed/status`) and source-priority resolution (employer ATS/career > aggregator).
- `[STRAT]` Two-stage classification (rules then AI for ambiguity) with confidence/evidence and review queue.
- `[STRAT]` Transparent ranking (category/location-remote fit/directness/freshness/completeness) and daily diffs/datasets.

## F. Requested deliverable ideas captured
- `[ENH]` AI agent execution runbook for automated SN/SF developer job sourcing in Toronto and remote markets (step-by-step methodology, ATS API querying, normalized schema). → `ideas/bestiejob/agent-execution-runbook.md`
- `[ENH]` Consolidated ideas store + deduplicated clean ideas. → this file + `ideas/bestiejob/clean-ideas/clean-ideas.md`
- `[ENH]` <uncertain> "Job market intelligence dashboard (Toronto/remote postings, tech stacks, compensation benchmarks)" — requires data/model design beyond current pipeline evidence; record as future product idea with privacy/compliance constraints.
