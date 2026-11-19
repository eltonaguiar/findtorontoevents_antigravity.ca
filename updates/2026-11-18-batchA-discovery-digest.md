# Batch-A discovery digest — 2026-11-18 (read-only, private)

**Owner:** kilo · seat `inbox/gx10-c9b9/bestiejobharvest-v2/kilo`
**Method:** read-only GETs to five **verified** documented ATS list APIs (runbook-sanctioned path). Classified titles (ServiceNow / Salesforce / Other), geo-bucketed (GTA / remote-CA / other-CA / non-CA), deduped on `(adapter, token, posting_id)`, then dispositioned with the sales/functional exclusion + Ontario-eligibility flags. **Private digest only — nothing published to the public board.** Data: `updates/2026-11-18-batchA-leads.jsonl`; raw run: `updates/2026-11-18-batchA-discovery-run.log`.

## Per-source yield

| source | adapter | postings | platform titles | in-scope CA | note |
|---|---|---|---|---|---|
| eqbank | lever | 79 | 1 | 1 | Senior ServiceNow Engineer (GTA) |
| versapay | lever | 30 | 2 | 1 | Salesforce Developer (remote-CA); CA req kept, US twin separate |
| levio | greenhouse | 56 | 6 | 6 | Quebec employer; French titles; needs Ontario check |
| solink | ashby | 24 | 0 | 0 | board live, **no current SN/SF** → watch, not now |
| servicenow | smartrecruiters | 100 | 2 | 1 | the 1 in-scope was a **sales** role → rejected |

**Totals:** 9 in-scope leads → **2 candidate-dev**, **6 needs-Ontario-check**, **1 rejected (sales)**.

## The leads (dispositioned)

| Disposition | Track | Geo | Issuer date | Source | Title |
|---|---|---|---|---|---|
| candidate-dev | ServiceNow | GTA | 2026-09-22 | lever:eqbank | Senior ServiceNow Engineer |
| candidate-dev | Salesforce | remote-CA | 2026-08-24 | lever:versapay | Salesforce Developer |
| needs-ontario-check | ServiceNow | other-CA | 2026-08-06 | greenhouse:levio | Développeur.euse ServiceNow |
| needs-ontario-check | Salesforce | other-CA | 2026-08-06 | greenhouse:levio | Développeur.euse (Salesforce) |
| needs-ontario-check | Other | other-CA | 2026-10-01 | greenhouse:levio | Data Engineer |
| needs-ontario-check | Salesforce | GTA | 2026-07-10 | greenhouse:levio | Functional Architect (Salesforce) |
| needs-ontario-check | ServiceNow | other-CA | 2026-08-06 | greenhouse:levio | Analyste d'affaires ServiceNow |
| needs-ontario-check | ServiceNow | other-CA | 2026-08-06 | greenhouse:levio | Conseiller.ère en architecture ServiceNow |
| rejected | Salesforce | GTA | 2026-11-17 | smartrecruiters:servicenow | Sr Solution Sales Executive CRM (CPQ) — sales, not build |

## Key findings
1. **Batch A yields real, low-duplication leads** — 2 clean dev roles (eqbank, versapay) an aggregator-first sweep would likely bury or mirror.
2. **Title matching alone is insufficient** — the ServiceNow "Sr Solution Sales Executive CRM (CPQ)" matched on CPQ/CRM but is pre-sales. The duties-read step (runbook §3.3) is mandatory; a title classifier needs the sales/marketing **EXCLUDE** filter baked in.
3. **Employer HQ ≠ eligible geography** — Levio (Quebec City) surfaced 6 platform titles incl. 2 genuine French dev roles, but Ontario eligibility must be confirmed per req before any count.
4. **List clocks are mostly stale** — only the rejected sales role was dated within 30 days; the genuine leads are Aug–Sep. Confirms the "two clocks" rule: ATS list dates (Lever `createdAt`, Greenhouse `updated_at`, Ashby `publishedAt`) are **not** posted dates; freshness needs the issuer's posted date from the detail page.
5. **A live board with zero platform roles is a valid result** (solink) — keep it on the watchlist, rotate cadence down.

## RECOMMENDATIONS
1. **Bake the EXCLUDE + functional/dev split into the classifier** before any lead is staged (reject sales/marketing/recruiter; tag functional vs dev so generic titles route to review, not auto-accept).
2. **Gate every non-Ontario-HQ employer on an Ontario-eligibility check** (Levio, and any Quebec/US-HQ partner) before counting a role.
3. **Resolve posted dates from the detail endpoint** (Lever hosted `datePosted`, Greenhouse `first_published`, Ashby original publish, SmartRecruiters `releasedDate`) — never treat the list clock as posted; keep undated rows out of the *fresh* lane.
4. **Verify the 2 candidate-dev roles next** (form-reached + duties): eqbank Senior ServiceNow Engineer, versapay Salesforce Developer (confirm the CA req, not the US twin).
5. **Keep solink on watch, lower cadence**; promote a source only when it yields a verified role.
6. **Add a `rights` gate before any republication** — this digest is private; publishing these rows to the public board needs the per-source rights check (own-site/attributed) from the runbook.

## What else to pursue (for the swarm)
- **Expand the verified Lever/Greenhouse/Ashby tenant set.** eqbank + versapay (Lever) and levio (Greenhouse) all answered; probe more Canadian employers on these three adapters (they're the cleanest, keyless path). Candidates to resolve: the 11 `resolve_employer` rows in the watchlist.
- **Build the SmartRecruiters detail pass.** ServiceNow's board had 100 postings but only list fields; a detail fetch (`/postings/{id}`) is needed to read duties and catch build roles hidden behind generic titles — and to reject sales roles reliably.
- **Wire the Workday tenants** (big-5 + consulting) through `gap_channels_scan.py` with the same verify/dedupe/rights gates — that's where volume lives, and it's the board's known coverage gap.
- **Stand up the 7-day pilot** across all four angles with the exclusive-vs-shared measurement, so the angle ranking moves from judgment to evidence.
- **Commit `employer-watchlist.csv` + `job-snapshot.csv` into the BESTIEJOB kit** (still 404 on main/pinned rev) so `scan_boards.py` is runnable as-shipped, and pin the kit to a revision.
- **Close the LinkedIn-guest + Adzuna rights question** before any of those sources are republished on the public board.

---
*Read-only discovery, 2026-11-18T03:38Z. Leads are `lead_only` / duties-unverified until the §3 verification pass. No PII, no secrets, no push.*
