# bestiejob — the 12 stranded kilo-2026-10-30 postings (2026-11-01)

`kilo-2026-10-30` was the last branch holding README rows that existed nowhere on `main`: **12
rows**. Each one was opened in a browser before being added, which is why two thirds were not added.

## Added (3, verified live)

| Posted | Role | Company | Location | Finding |
|---|---|---|---|---|
| not shown | Senior ServiceNow Developer (ITOM) | Systematix | Remote – Canada | HTTP 200, title matches. 6-month contract, CSA/CAD preferred, CIS-Discovery an asset |
| not shown | ServiceNow Administrator / Developer (Intermediate) | BFG Enterprise Services | Markham, ON | HTTP 200; page states **CAD 70,000–85,000** |
| 2026-10-08 | ServiceNow Developer | Brock Solutions | Cambridge, ON | HTTP 200; **$60,000–$80,000/yr** |

The Systematix row matters most: `main` previously mentioned Systematix only as a dead careers link
(`systematixgroup.com` → 404) in a portal table, never as the posting.

## Rejected (9), with evidence

| Row | Outcome | Evidence |
|---|---|---|
| Scotiabank ServiceNow Developer (603030017) | Closed | Page loads, Apply path closed |
| BMO ServiceNow Sr Developer ITSM/AI/GRC (R260027442) | Gone | **HTTP 410** |
| Brookfield ServiceNow Developer (contract) | Gone | jobs.ca **410** "posting is no longer available" |
| LanceSoft ServiceNow IRM Developer (GRC) | Closed | Closed; own "Posted: 04/20/2026" makes $83–100/hr six months stale |
| Alimentiv ServiceNow Platform Specialist | Gone | Greenhouse board **404** |
| Lightspeed ServiceNow Developer (remotive) | Duplicate | Same req as the Oct 23 row; corroborates **$85,000–$105,000** |
| Deloitte Lead Specialist, ServiceNow CMDB | Duplicate | Already 135342; kilo link is an Indeed click-tracking redirect |
| RSC Solutions ServiceNow Architect | Out of scope | Jersey City, NJ |
| Cooley Technology ServiceNow Administrator | Out of scope | US-only |

Pushed as `bestiejob@5ff439e`. README 737 → **762 lines**, job rows 373 → **376**.

## Verification

- README job-row guard, run on the change itself: base 349 rows/315 unique → head 352/318,
  **removed 0, added 3**, duplicate URLs flat at 34 → **PASS**.
- All three new links return HTTP 200 on the live page; the section marker and both 2026-11-01
  sections plus the restored Cognizant row are all still present on `main`.

## Why 10 rows still show as "missing"

After the push, a kilo-vs-main URL diff reports 10, not 9. That is the Systematix mirror: kilo cited
`jobs.ca/systematix/...` while the row landed under `systematix.com/opportunity/...`, the canonical
employer page. Same posting, different URL — so the job is covered and the mirror URL is expected to
stay "missing".

## Side effect worth knowing

The Alimentiv Greenhouse posting is 404, which means the Oct 27 Alimentiv row already in the README
is now unbacked. It was left in place rather than deleted, since deleting rows is what the new guard
exists to flag and a temporary 404 is not proof of closure.
