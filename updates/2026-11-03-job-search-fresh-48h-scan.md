# Job Search — Fresh 48-Hour Scan (2026-11-03)

**Request:** "proceed and scan for jobs from today / yesterday"

## What Was Done

Ran a targeted 48-hour harvest using `f_TPR=r172800` (2-day recency filter) instead of the default 14-day `f_TPR=r1209600`.

| Stage | Result |
|-------|--------|
| Queries | 26 (Rounds 28/29/30) × 3 pages = 78 requests |
| Raw rows | 731 |
| Verified posted today (2026-11-03) | 487 raw → 107 net-new |
| Verified posted yesterday (2026-11-02) | 214 raw → 61 net-new |
| Posted 2026-11-01 (filter leak) | 30 raw → 4 net-new |
| Already in prior 684-job corpus | 173 |
| Intra-run duplicate URL | 382 |
| Duplicate title/company/location | 4 |
| **Net-new unique** | **172** |

**96% of raw rows were genuinely posted in the last 48 hours** — verified against JSON-LD `datePosted`, not just the filter flag.

## Rounds

| Round | Scope | Queries | Raw |
|-------|-------|---------|-----|
| 28 | GTA ServiceNow/Salesforce | 10 × 3 pages | 300 |
| 29 | Remote Canada ServiceNow/Salesforce | 8 × 3 pages | 240 |
| 30 | Banks / Telcos / Public sector | 8 × 3 pages | 191 |
| **Total** | | **26 × 3** | **731** |

## Bug Found and Fixed Mid-Run

**Symptom:** First aggregation reported 197 net-new.

**Cause:** The dedupe script looked for `job_search_pattern_rounds_2026-11-03T041243Z.json` and `job_search_rounds20_2026-11-03T035753Z.json` in the working directory — but those files belong to branch `job-search-2026-11-03-rounds21-27`, not the branch checked out at the time. `load_prior_urls()` silently swallowed the `FileNotFoundError` (bare `except Exception: continue`) and fell back to the original 259-URL file only.

**Evidence:** `Prior known URLs: 259` printed instead of 684.

**Fix:** Extracted the real prior files via `git show job-search-2026-11-03-rounds21-27:<path>` into `/tmp/jobs/prior/`, then re-ran dedupe with the full **684-URL** corpus. Corrected result: **172 net-new** (not 197).

**Lesson:** silent `except: continue` in data-loading code produces plausible-but-wrong numbers. The printout of the loaded-count is what caught it. Keep that diagnostic line in every aggregator.

## Results

### Category (title+company only — never query text)

| Category | Count | Apply tier |
|----------|-------|------------|
| Salesforce | 38 | 22 |
| ServiceNow | 11 | 9 |
| Adjacent (ITSM/CRM/Cloud) | 123 | 50 |
| **Total** | **172** | **81** |

### Region

| Region | Count |
|--------|-------|
| GTA | 105 |
| Canada-level (remote-ambiguous) | 51 |
| Ontario-other | 16 |

### Buckets

- apply: 81
- consider: 76
- skip: 15

### Score distribution

```
 8: 11    2: 50
 7:  8    1:  9
 6: 25    0:  6
 5: 17   -1:  3
 4: 20   -2:  2
 3: 17   -3:  4
```

## Notable Findings

**ServiceNow GTA supply is thin.** Only 1 GTA ServiceNow role in 48h (Poly Tech Talent — ITSM Service Desk Manager, score 8). Volume sits in Montreal: Pomerleau (Administrateur ServiceNow ×5 variants), TCS (ServiceNow Specialist + CMDB), AceStack (CMDB/CSDM Montreal onsite). Two ServiceNow Inc. postings were sales roles (Sr. CRM Account Executive), not delivery.

**Salesforce GTA supply is healthy.** 22 apply-tier roles. Top: Co-operators (bilingual Systems Developer, score 8), IKO North America (Salesforce Senior Developer, 7), Canadian Cancer Society (Senior Salesforce Engineer ×4 regional variants, 6), Smart IT Frame (SFMC consultant + BA, 6).

**Adjacent ITSM is the strongest secondary channel.** Interac Incident Management Lead (8), UHN Incident Coordinator (7), Poly Tech ITSM Service Desk Manager (8), TEKsystems Controls Transformation Consultant (8), Deloitte Manager Data Analysis (8) — these reward ITIL v4 + ITSM depth without requiring the ServiceNow title.

**Duplicate requisitions inflate raw counts.** Pomerleau posted "ServiceNow Administrator" 4× and "Administrateur ServiceNow" 1×; Canadian Cancer Society posted Senior Salesforce Engineer 4×; Salesforce posted Canadian Public Sector Engagement Delivery Leader 3×. Apply once per requisition, not per posting.

**~20% of fresh roles are bilingual.** Co-operators, Canadian Cancer Society, Alithya, Desjardins, Pomerleau, Schneider Electric all posted French titles. Resume is not bilingual (scored −2) but cert/module overlap still pushed several into apply tier.

## Files

- `job_search_fresh_2026-11-03T183000Z.json` — 172 net-new jobs with category/region/score/reasons/signals
- `job_search_application_tracker_2026-11-03T183000Z.json` — merged tracker: 80 prior + 172 fresh, totals apply 130 / consider 98 / skip 24
- `job_search_fresh_report_2026-11-03T183000Z.md` — human-readable report
- `updates/2026-11-03-job-search-fresh-48h-scan.md` — this document

## Reusable Scripts (in `/tmp/jobs/`)

- `harvest_fresh.py` — parameterized 2-day harvest (Round 28/29/30 query sets)
- `aggregate_fresh.py` — dedupe + region/category classification + posted-date verification
- `jd_extractor.py` — JSON-LD JD extraction + signal parsing + resume scoring

## Caveats

1. `f_TPR=r172800` leaked 30 rows dated 2026-11-01 — always verify `datePosted` from JSON-LD.
2. `years_min` regex takes the first `N years` match; can catch incidental phrases. Spot-check before applying.
3. Dedupe is URL-based — same requisition across regional variants counts multiple times.
4. 51 "Canada-level" rows are remote-ambiguous; hybrid/onsite signals come from JD keyword matching, not structured fields.
5. Agency postings (Smart IT Frame, LTM, TEKsystems, Poly Tech Talent, Zodiac, SS&C) obscure the end client.

---

**Author:** Zoo
**Date:** 2026-11-03T18:30Z
