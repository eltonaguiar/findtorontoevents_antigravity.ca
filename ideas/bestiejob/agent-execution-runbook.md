# AI Agent Execution Runbook — Automated ServiceNow & Salesforce Developer Job Sourcing (Toronto + Remote)

**Objective:** build and operate a compliant, source-first pipeline that discovers, ingests, normalizes, classifies, deduplicates, and publishes **ServiceNow** and **Salesforce** (and related ITSM/CMDB/ITAM) developer/admin/platform roles eligible for **Toronto/GTA or Canada-remote**.

**Non-negotiable constraints**
- Prefer official APIs, feeds, sitemaps, open data, and JSON-LD on permitted pages.
- Respect `robots.txt`, ToS, rate limits, and auth walls. **No** login/CAPTCHA/IP-block evasion, no proxy/account farming, no automated Apply circumvention.
- Never expose/output private phone numbers or emails.
- Store minimum necessary data; link to canonical original postings. Treat uncertain descriptions/licensing conservatively.
- Cite only sources you are certain of in outputs; mark `<uncertain>` otherwise.

---

## 1) Agent methodology (step by step)

### Phase 0 — Preflight & policy
1. **Load policy:** allowed sources/methods, per-domain rate limits, user-agent, retention rules, blocklists (e.g. gated/paywall domains).
2. **Load targets:** company universe, ATS tenant/site registry, query library, geo allow/deny rules, profile definitions.
3. **Load state:** last run cursors, known URLs/hashes/requisition IDs, lifecycle table, baseline metrics.
4. **Health checks:** endpoint reachability probes (lightweight), credential/config presence for permitted APIs, disk/queue sanity.

### Phase 1 — Build/refresh company universe (discovery, source-first)
1. **Seed from verified directories:** ServiceNow Partner Finder and Salesforce Partner Finder/consultant ecosystems (tiers/segments where exposed) — *concepts certain; specific exports/lists `<uncertain>` unless programmatically accessible and permitted*.
2. **Enrich:** Toronto/GTA presence, known ATS platform, careers domain, historical hiring signal (repeat posters), verified conference/event employers `<uncertain>` until confirmed.
3. **Normalize entities:** company name/domain/aliases, location, ATS slug/board/tenant/site, confidence, `last_verified_at`.
4. **Prioritize batches:** few tenants/employers at a time per run to control rate/timeout risk.

### Phase 2 — Ingest from primary sources (permitted)
1. **ATS adapters (preferred):** poll per-company public endpoints (Greenhouse, Lever, Ashby, Workable, SmartRecruiters, Workday CXS where public, Phenom/Oracle CE where accessible) on schedule.
2. **Career sites (permitted):** fetch allowed pages, extract JSON-LD `JobPosting`/structured fields and canonical URLs; hash content.
3. **Supplementary permitted sources:** Job Bank/open data and other verified date-exposing boards/indices where adapters are proven.
4. **Aggregators/discovery-only:** use only compliant/manual/authorized mechanisms to discover employer/ATS targets; resolve to employer canonical posting before ingestion.
5. **Capture raw metadata:** `source_system`, `source_url`, retrieval time, response status, parser version.

### Phase 3 — Parse, normalize, and validate
1. **Normalize fields** to canonical schema (Section 3).
2. **Validate requireds:** non-empty title, canonical/apply URL, employer (or resolvable), location signal.
3. **Freshness gate:** keep only records with **source-published absolute date** (`YYYY-MM-DD` or parseable ISO) within window policy; never guess dates.
4. **Liveness gate:** verify URL status (treat 404/410/451 as dead per policy; handle bot-walls/429/5xx conservatively).
5. **Policy gate:** drop gated/paywall/signup-trap domains, listing/search pages, and out-of-scope geos (US-only remote, non-CA where ineligible).

### Phase 4 — Classify and enrich
1. **Deterministic rules (first pass):**
   - Category: `servicenow` | `salesforce` | `other` based on strong platform/product/cert/module signals.
   - Subcategory/seniority/employment/remote hints from title+structured fields.
   - Relevance: require platform/cert evidence; for body-only matches require role-intent tokens and context-aware exclusions (do not exclude legit dev/admin roles due to generic sales terms).
2. **AI/LLM classification (ambiguity only):** strict JSON output with `category`, `subcategory`, `seniority`, `remote_status`, `is_toronto_eligible`/`is_canada_remote`, `confidence`, `evidence[]`, `reject_reason`; no invented facts.
3. **Human/agent review queue:** low confidence, conflicting signals, or policy-sensitive cases.

### Phase 5 — Deduplicate and resolve lifecycle
1. **Canonical identity:** exact normalized URL; then `employer_domain + normalized_title + location`; then content/requisition similarity.
2. **Cross-source precedence:** prefer employer ATS/career record over aggregator/discovery records.
3. **Merge:** union evidence/skills, keep best dates/locations, retain provenance.
4. **Lifecycle:** set `first_seen/posted/updated/last_seen/removed_at`, `is_active`, `status` (`active|possibly_closed|closed|expired|unknown`).

### Phase 6 — Score, publish, and report
1. **Score/rank:** category match, Toronto/Canada-remote fit, direct-source preference, freshness, completeness (transparent weights).
2. **Publish artifacts:** canonical store + `jobs.json`/`jobs.csv`/UI or README tables as per product; link to originals.
3. **Diffs & metrics:** new/updated/closed counts, net-new by profile/geo/source, drop reasons, yield per query/tenant.
4. **Feedback loop:** promote high-yield sources/queries; demote noisy/off-topic patterns; update blocklists and adapters (with verification).

### Phase 7 — Continuous improvement & incident handling
1. **Monitor CI/guards** (truth, liveness, invariants, schema parse, push health).
2. **On failure:** classify (data leak, source drift, parser break, publish contention), create durable incident note, fix at correct layer (ingest > merge > build > gate).
3. **Change control:** small batches, dry-run/report, verify on sample before merge; document in updates.

---

## 2) How to query ATS APIs for open roles

> **General rules:** per-company endpoints (not global search). Discover the company’s board token/tenant/site first. Authenticate only where you are explicitly authorized; prefer public endpoints. Cache responses, respect rate limits/backoff, and store request timestamps.

### 2.1 Common public ATS patterns (verified/common)
| ATS | Typical public endpoint pattern | Key fields (typical) | Notes |
|---|---|---|---|
| Greenhouse | `GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs` (optional `?content=true`) | id, title, location, departments, updated_at, absolute_url, content | Board token per company; paginate/iterate as returned |
| Lever | `GET https://api.lever.co/v0/postings/{company}?mode=json` | id, text (title), categories (location/team/commitment), createdAt, hostedUrl, applyUrl, descriptionPlain | Company slug; JSON mode for structured data |
| Ashby | `GET https://api.ashbyhq.com/posting-api/job-board/{board_name}` (and job posting details where exposed) | title, location, employmentType, publishedAt/updatedAt, jobUrl, department | Public posting API for board; confirm exact board name |
| Workable | `GET https://apply.workable.com/api/v1/widget/accounts/{account}` (and job details endpoints) | title, city/country/remote, employment_type, published_on, shortcode/url | Widget/account token; handle location objects |
| SmartRecruiters | `GET https://api.smartrecruiters.com/v1/companies/{company}/postings` (list) + posting detail endpoint | id/name, releasedDate, location, function/experience, applyUrl | Company identifier required; support paging/filters if available |
| Workday (CXS, public) | `POST https://{tenant}.{wd}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs` with JSON body `{"appliedFacets":{},"limit":20,"offset":0,"searchText":"<query>"}`; detail via CXS posting path | title, locationsText, postedOn (relative) in list; detail `startDate` (absolute), externalUrl, jobReqId | Tenant/wd/site must be discovered/validated; resolve absolute date from detail |
| Phenom People (tenant-specific) | `GET/POST https://{jobs-host}/api/apply/v2/jobs?...` (query/params vary by tenant) | title, location, posted/create dates, apply/job URLs, ids | Shape varies; probe and fail closed on unknowns `<uncertain per tenant>` |
| Oracle Cloud Recruiting (CE) | `GET https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true&expand=requisitionList&finder=...` | Title, PrimaryLocation, PostedDate/PostingStartDate, Id | `siteNumber`/finder vary by tenant `<uncertain per tenant>` |

### 2.2 Query strategy (targeted, not brute-force)
- **Keyword sets (rotate/batch):** platform (`ServiceNow`, `Salesforce`), role (`Developer`, `Administrator`, `Architect`, `Consultant`, `Platform`), cert/module (`CSA`, `CAD`, `CIS`, `ITSM`, `ITOM`, `ITAM`, `CMDB`, `Apex`, `LWC`, `Flow`, `CPQ`).
- **Geo filters:** `Toronto`, `Ontario`, `Mississauga`, `Markham`, Canada/remote where supported; post-filter to **Toronto/GTA or Canada-remote eligible**.
- **Recency:** prefer API sort by date and `max_days_old`/time-range params when available; otherwise filter by source `posted/created/released/start` date.

### 2.3 Example requests (illustrative)
```bash
# Greenhouse (public board)
curl -sS "https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"

# Lever (public postings)
curl -sS "https://api.lever.co/v0/postings/{company}?mode=json"

# Ashby (public board)
curl -sS "https://api.ashbyhq.com/posting-api/job-board/{board_name}"

# Workable (widget)
curl -sS "https://apply.workable.com/api/v1/widget/accounts/{account}"

# SmartRecruiters (company postings)
curl -sS "https://api.smartrecruiters.com/v1/companies/{company}/postings?limit=100&offset=0"

# Workday CXS (search) — tenant/site must be valid
curl -sS -X POST "https://{tenant}.{wd}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs" \
  -H "Content-Type: application/json" \
  -d '{"appliedFacets":{},"limit":20,"offset":0,"searchText":"ServiceNow Developer"}'
```
```text
Workday detail/date resolution (pattern): fetch posting detail via CXS externalPath/job endpoint and read absolute `startDate`;
do not convert relative "Posted N days ago" by guesswork except explicit today/yesterday when policy allows.
```

### 2.4 Normalization from ATS responses
- Map to canonical schema (Section 3); preserve `source_system`, raw IDs (`requisition_id`, `posting_id`), and original URLs.
- Parse dates to ISO-8601; mark timezone assumptions if unknown `<uncertain>`.
- Derive `is_toronto`, `is_gta`, `is_canada_remote`, `remote_status` from structured location/remote flags + text rules (Canada-eligible required for remote).

---

## 3) Data schema for normalized job postings

### 3.1 Canonical record (JSON example)
```json
{
  "job_id": "sha256:employer_domain|canonical_url|requisition_id?",
  "employer": {
    "name": "Example Consulting",
    "normalized_name": "example-consulting",
    "domain": "example.com",
    "ats_platform": "greenhouse",
    "ats_board_or_tenant": "example",
    "company_source": "servicenow_partner|salesforce_partner|direct|agency|unknown",
    "hq_location": "Toronto, Ontario, Canada"
  },
  "posting": {
    "title_raw": "Senior ServiceNow Developer (ITSM/CMDB)",
    "title_normalized": "senior-servicenow-developer-itsm-cmdb",
    "category": "servicenow",
    "subcategory": "developer",
    "seniority": "senior",
    "employment_type": "full_time",
    "remote_status": "hybrid",
    "locations_raw": ["Toronto, ON, Canada"],
    "locations_normalized": ["Toronto, Ontario, Canada"],
    "is_toronto": true,
    "is_gta": true,
    "is_canada_remote": false,
    "salary": {
      "min": null,
      "max": null,
      "currency": "CAD",
      "period": "year",
      "source": "posting|inferred|unknown"
    },
    "posted_at": "2026-11-17",
    "updated_at": "2026-11-17",
    "first_seen_at": "2026-11-18T02:00:00Z",
    "last_seen_at": "2026-11-18T02:00:00Z",
    "removed_at": null,
    "is_active": true,
    "status": "active",
    "apply_url": "https://boards.greenhouse.io/example/jobs/123",
    "source_url": "https://boards.greenhouse.io/example/jobs/123",
    "canonical_url": "https://boards.greenhouse.io/example/jobs/123",
    "source_system": "greenhouse",
    "requisition_id": "123",
    "description_hash": "sha256:...",
    "evidence": ["ServiceNow", "ITSM", "CMDB", "CSA/CAD <if present>"]
  },
  "classification": {
    "method": "rules|llm|hybrid",
    "category": "servicenow",
    "confidence": 0.97,
    "signals": ["ServiceNow Developer", "ITSM", "CMDB"],
    "review_required": false,
    "reject_reason": null
  },
  "quality": {
    "is_gated_source": false,
    "is_duplicate": false,
    "duplicate_of": null,
    "date_source_reliable": true,
    "liveness_status": "live",
    "data_completeness": 0.9
  },
  "provenance": {
    "ingested_at": "2026-11-18T02:00:00Z",
    "pipeline_run_id": "run-...",
    "parser_version": "v1"
  }
}
```

### 3.2 Field dictionary (core)
| Field | Type | Required | Description / rules |
|---|---|---|---|
| `job_id` | string | yes | Stable hash/id from canonical employer+URL(+req id) |
| `employer.name` | string | yes | Display employer/company |
| `employer.domain` | string | no | Canonical domain when known |
| `employer.ats_platform` | enum/string | no | `greenhouse|lever|ashby|workable|smartrecruiters|workday|phenom|oracle|custom|unknown` |
| `posting.title_raw` | string | yes | Original title |
| `posting.category` | enum | yes | `servicenow|salesforce|other` |
| `posting.subcategory` | string | no | developer/admin/architect/consultant/analyst/platform/other |
| `posting.locations_*` | array/string | yes | Raw + normalized locations |
| `posting.is_toronto` / `is_gta` / `is_canada_remote` | bool | yes | Eligibility flags per geo policy |
| `posting.remote_status` | enum | no | `remote|hybrid|onsite|unknown` |
| `posting.posted_at` | date | yes | **Source-published absolute date** |
| `posting.canonical_url` / `apply_url` / `source_url` | url | yes (>=1 canonical) | Prefer employer ATS/career canonical |
| `posting.requisition_id` | string | no | ATS req/job id when available (dedupe aid) |
| `posting.description_hash` | string | no | Hash of normalized text; avoid storing restricted full text |
| `posting.evidence` | array[string] | no | Matched tokens/fields supporting classification |
| `classification.confidence` | number | yes | 0..1 |
| `quality.is_gated_source` | bool | yes | Must be `false` for published canonicals |
| `quality.liveness_status` | enum | yes | `live|dead|unknown|blocked` |

### 3.3 Enumerations (recommended)
- **Profiles/signals:** ServiceNow (ITSM, ITOM, ITAM, CMDB, HRSD, CSM, GRC, SecOps, CSA, CAD, CIS, Flow Designer, Service Catalog, Discovery) / Salesforce (Apex, SOQL, LWC, Visualforce, Flow, CPQ, Revenue/Marketing/Data Cloud, Agentforce, Admin/Platform Dev/App Builder).
- **Drop reasons:** `gated_domain`, `undated`, `dead_link`, `duplicate_url`, `duplicate_content`, `out_of_geo`, `not_canada_remote`, `off_topic`, `excluded_role`, `policy_blocked`.

---

## 4) Batched execution plan (operational)
1. **Batch A — Company portals/ATS (few tenants):** probe → query (platform/role/cert) → detail/date resolve → normalize → gate → classify → dedupe → publish. *(highest yield)*
2. **Batch B — Toronto/GTA + Canada-remote feeds:** geo-targeted aggregator/guest/indices with same gates.
3. **Batch C — Canadian public sector/verified boards:** Job Bank + proven adapters only.
4. **Batch D — Partner/customer/event ecosystem:** verify employers/rosters `<uncertain>` → map to ATS/career sources → ingest.

**Per-batch acceptance:** source-published date, live URL, in-geo/remote-eligible, not gated, deduped, classified with evidence/confidence; emit run report.

---

## 5) References (certain / in-repo or commonly documented)
- BESTIEJOB pipeline components (reviewed): `hourly-scan.yml`, `fresh-ca-scan.yml`, `gap-channels-daily.yml`, `agency-board-scan.yml`, `linkedin-sweep.yml`, `scripts/{daily_job_scan.mjs,fresh_ca_scan.py,ats_discovery.py,gap_channels_scan.py,linkedin_guest_scan.py,agency_board_scan.py}`, `tools/{verify_links.py,jobs_merge_inbox.py,job_source_truth.py}`.
- ATS public endpoint families: Greenhouse boards API, Lever postings API, Ashby posting API, Workable widget API, SmartRecruiters postings API, Workday CXS jobs/detail (tenant-specific) — patterns above; tenant parameters/fields vary `<uncertain per tenant>`.
- Directories/ecosystem concepts: ServiceNow Partner Finder, Salesforce Partner Finder/consulting partners — specific partner/attendee lists require verification `<uncertain>`.

*Companion docs:* `ideas/bestiejob/consolidated-ideas.md`, `ideas/bestiejob/clean-ideas/clean-ideas.md`, `updates/2026-11-18-bestiejob-session-history.md`, `updates/2026-11-18-bestiejob-session-summary.md`, `updates/2026-11-18-bestiejob-fix-investigation.md`.
