# bestiejob — improvement spec from the Oct 30 → Nov 1 scan audits

Derived from: the README audits in this repo (`2026-10-31-bestiejob-readme-sync-world-forum.md`,
`2026-11-01-bestiejob-unmerged-branch-gap.md`) plus the external agent's transcripts (Arlo's daily
checks, partner sweeps, and PR-blocked README attempts).

Measured against `bestiejob@fb08a50`, `jobs.json` = **14,356 records**.

---

## 0. The measurement that explains everything else

| Job age (`postedDate` → 2026-11-01) | Records |
|---|---|
| 0–1 days | 53 |
| 1–7 days | 20 |
| **7–21 days** | **0** |
| **21–60 days** | **0** |
| **60+ days** | **14,165** |
| future-dated / unparseable | 0 / 85 |

98.7% of the database is one frozen import. `dateSource` confirms it: `scraped` 14,250,
`adzuna-api-scan-2026-10-31` 73, `unknown` 33. There is no 7–60 day tail at all, which is not how
a job board ages — it means the bulk import never got retired and the weekly scan only ever appends.
`JOB_SOURCES_STATUS.md` still advertises "13,329 jobs from 10 reliable sources" as if volume were
the goal.

**Every symptom in the transcripts follows from this.** "Fresh ServiceNow scan: zero genuinely new
postings", "mostly the same roles recrawling", "today's Indeed copy is a recrawl" — the pipeline has
no way to distinguish a live job from a February corpse, so agents burn whole sessions re-verifying
the same listings by hand.

---

## 1. P0 — the record has no lifecycle, so stale data can never leave

Present on every record: `id, source, company, title, location, url, dateSource`.
Missing, and required before any dedupe/verification work can be automated:

```jsonc
{
  "canonicalId":     "greenhouse:kensingtontours:5206208007",  // stable, cross-source
  "status":          "live | filled | expired | dead | wrong-country | excluded",
  "statusEvidence":  "employer-ATS | aggregator | none",       // HOW we know
  "statusCheckedAt": "2026-11-01T02:40:00Z",
  "lastSeenAt":      "2026-11-01T02:40:00Z",                   // scraper heartbeat per record
  "postedAt":        "2026-10-30",                             // employer's date only
  "postedAtSource":  "employer | aggregator | scan",           // <- the conflation fix
  "expiresAt":       "2026-11-06",                              // deadline / apply-by
  "countryCode":     "CA",                                      // ISO, resolved not guessed
  "employmentType":  "permanent-ft | contract | part-time | unknown",
  "certsRequired":   ["CSA", "CAD"],                            // mandatory only
  "certsPreferred":  ["CIS-ITSM"],
  "seniority":       "junior | intermediate | senior | lead | architect",
  "moduleTags":      ["ITSM", "CMDB", "SAM-Pro", "GRC-IRM"]
}
```

Field coverage today proves the gap: `deadline` on **94/14,356 (0%)**, `recruiter` 1%,
`scrapedAt` **19%**. A job can therefore be "active" forever with no evidence anyone looked at it.

Concrete consequences already observed:

- **Filled roles can't be retired.** Bell 432824 + 432829 (filled), Rogers 317411 (filled),
  City of Toronto 59812 (closed Mar 3), BMO CMDB Admin (Mar 4 deadline), Arthur Grand ×2 (expired),
  Cognizant 00070907531 (dead), Scotiabank 603030017 ("not accepting"). Each one was found by a human
  or agent opening the page; none can be recorded.
- **`countryCode` absent** → Cooley (US-only), Yudrio (US federal + Public Trust), ConfigureTek
  (US work-auth), Redpath and the "Security Clearance" cluster all sit in Canadian tables.
  One branch file even labelled Yudrio "remote Canada" — it is a US-citizenship contract.
- **`employmentType` is free text** → the user asked twice for permanent full-time over variable-hour
  consulting, and nothing in the data can filter on it.
- **`expiresAt` absent** → the deadlines that actually matter (CCS Nov 6, TD Nov 9, Cognizant
  Nov 15, Lightspeed Nov 22) live in the external agent's memory, not in the product.
- **No exclusion list** → CIBC (ineligible until ~Apr 2027) must be manually skipped every run.

## 2. P0 — no canonical identity, so the same job is counted many times

- **1,042 duplicate (company,title) groups covering 2,380 rows — 1,338 redundant records** (9.3%).
  Tim Hortons "Team Member" ×17; "Essence Coaching Group" senior engineer ×9.
- In the README it is worse than duplicated rows: Randstad `6LPQLY8PROEN` and Kensington were both
  added **twice** by different agents (entries #86/#87 plus a separate section), and the "Alldus SPM,
  Remote Canada" lead turned out to be the already-listed Alldus Montreal role.
- The earlier "673 unique links stranded in unmerged branches" figure was inflated the same way —
  jobs.ca + Workopolis + LinkedIn + Adzuna variants of one req. Job-level dedupe gives 41 employers.

Fix: dedupe on `canonicalId`, fall back to `(normalised company, normalised title, location city)`,
and keep every source URL as an array on the surviving record.

## 3. P1 — 149 rows are not job postings

Rows whose URL is a careers landing page or a search results page, not a requisition — e.g.
`Sun Life Financial / "Careers"`, `Sun Life Canada`, `Sun Life United States`, `Sun Life India`.
`status` + a URL-shape rule (`/careers/?$`, `q-`, `search?`, no job id) would drop these at ingest.
Related: 85 `postedDate` values are RFC-2822-ish (`"Fri, 06 Feb 2026 00:04:37 +000"`) and fail
`fromisoformat`; 33 are missing entirely. Normalise at ingest to ISO-8601 UTC.

## 4. P1 — the README is the database, and it is destructively editable

- 116 KB / 670 lines of hand-edited markdown, 378 table rows, **no generator** (`grep` for README in
  `scripts/` returns nothing; only `public/career/app.js` mentions it).
- It has been truncated twice. Commit `8c25626` was titled "add 2 rows" and diffed **+6 / −508**,
  deleting 210 posting rows plus five documentation sections. An earlier peer commit took it from
  583 lines to 85.
- Because it is hand-maintained, every agent invents its own section: the current file mixes
  "## 2026-10-31 update", "## Restored postings — rows deleted in commit 8c25626",
  "### ### Latest verified Canadian additions" (literal double-hash headings), and two different
  numbering schemes (#1–#88 and #89–#93) that collided.
- `## 2026-11-01 addendum` and the restored tables now describe overlapping sets of jobs, which is
  why "is anything missing?" has no cheap answer.

Fix: `jobs.json` → `README.md` generated by a script, with the prose sections kept in a separate
template. Add a CI check that fails when a README commit removes more posting rows than it adds, plus
a duplicate-row check. This is the same guard I proposed after the first truncation, and the second
truncation happened without it.

## 5. P2 — agents have no write path, so verified work evaporates

The external agent's own words: "this machine has no git credentials for a direct push", "the browser
isn't signed in to GitHub", "don't apply that patch as-is — the live README has moved". Result: six
**verified** postings still absent from the repo — IT Connex (Toronto on-site), iVedha (Toronto
hybrid), Zaelab ServiceNow Developer (remote Canada), Systematix Sr ServiceNow Developer/ITOM (remote
Canada), Cognizant 00070906481 (remote Canada, $77–125K, until Nov 15), AML Oceanographic (BC
permanent). Each was verified on a real board and then lost to a patch-conflict.

Fix: a service account / PAT for the agent, or a documented `scan-results/<agent>-<date>.json`
contract that a maintainer merges — never freeform markdown sections applied as patches. One schema,
one directory, dedupe on ingest, so branch sprawl (21 branches, 10 genuinely unmerged, six
differently-named scan `.MD` files) stops being the sync mechanism.

## 6. P2 — date semantics are conflated, which makes "new today" unanswerable

Three different dates are all called "posted": the scrape date, the aggregator's listing date, and the
employer's publication date. The README's 28 "2026-10-31" rows are Adzuna listing dates and the section
itself admits they were never confirmed on employer boards. The external agent's audit of the same repo
concluded "there is no posting published Oct 31 anywhere in the repo" — and it was right about
employer-posted dates. `postedAtSource` above is the fix; UI should show `postedAt` + provenance, and
only employer-sourced dates should count as "new today".

## 7. P3 — what the user actually asked for isn't queryable

Recurring asks across the transcripts that no field supports:

1. "full-time standard contracts preferably, not just consulting where hours vary" → needs
   `employmentType` normalised + a permanent-first sort.
2. "certs mandatory vs preferred" (CSA+CAD+CIS mandatory at CGI; "an asset" at Canadian Cancer
   Society) → needs `certsRequired` / `certsPreferred` split.
3. "apply by Nov 6" style urgency → needs `expiresAt` + a closing-soon view.
4. "not obviously labelled" roles (Application Specialist, ITSM Analyst, Business Specialist,
   CRM Data Engineer, GTM Systems Administrator) → needs `moduleTags` so ITSM/SPM/CMDB/SAM-Pro/GRC
   postings surface without the word "ServiceNow" in the title.
5. Exclusion by employer (CIBC until Apr 2027) → needs an `exclusions` list honoured by scrapers, the
   site and the daily check alike.

## Recommended order

1. Add the lifecycle fields + normalise dates at ingest (§1, §3). Nothing else works without it.
2. Dedupe on `canonicalId` (§2) — immediately removes 1,338 rows and the double-added README entries.
3. Generate README from data + add the destructive-commit CI guard (§4). Stops the recurring loss.
4. Give agents a write path / scan-results contract (§5) so verified work stops evaporating.
5. Add the filters in §7 to the site once the fields exist.

Items 1–3 are self-contained and can be done without touching the scrapers' fetching logic.
