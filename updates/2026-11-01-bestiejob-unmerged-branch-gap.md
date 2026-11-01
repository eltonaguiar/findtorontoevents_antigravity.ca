# bestiejob — postings stranded in unmerged branches (2026-11-01)

Follow-up to `2026-10-31-bestiejob-readme-sync-world-forum.md`. Question asked: *is there anything
new for ServiceNow / Salesforce missing from the README — either postings elsewhere, or work in a
pull request that never reached the README?*

## What was broken

Two separate failure modes, both measured against `origin/main` HEAD `b39ee81`.

### 1. Nine branches were never "unmerged" at all — they were squash-merged

`git rev-list origin/main..<branch>` reports 19 non-main branches with unmerged commits. That is
misleading. PRs #2–#10 were **squash**-merged, so the branch heads never became ancestors of
`main` and every one still reports "unmerged" commits. The genuinely unmerged set is 10:

```
auto-2026-10-30            buffy-2026-10-30              kilo-2026-10-30
auto/2026-10-30            buffy/servicenow-jobs-2026-10-30   kilo/2026-10-30
copilot-sdk-servicenow-jobs-2026-10-30                opencode-2026-10-30
copilot/fix-bestiejob-issue                           zoo/2026-10-30
```

The only open PR is **#1 [WIP] Fix issue in BestieJob application** — no job rows in it.

### 2. 41+ Canadian employers existed in those branches but nowhere in the README

Those 10 branches hold **396 Canadian ServiceNow/Salesforce rows**. A company-token check against
the live README found these absent entirely — not reordered, absent:

Slalom, ATB Financial, Take-Two Interactive, Electric Mind, Journey Capital, Compunnel, ServiceIO,
The Stafford Gray Group, Havas CX Canada, Parkland, Mindlance, Aquiva, Arkhya Tech, Zodiac
Solutions, Nityo Infotech, Pacer Group, HCL Canada, Dawn InfoTek, RSM, CMHC, Trans Mountain,
Intercast, LTM, Interac, Desjardins, Forhyre, Ledcor, Jolera, ExcelGens, Zachary Piper, Coaxxion,
MNP, Workhoppers, Sapsol, ConfigureTek, Hanalytica, LeverageTek, PrecisionERP, Yudrio,
Astra-North Infoteck, Dentsu, Infgrp.

The earlier "673 links" figure overstated the problem (many were alternate URLs for jobs already
listed); the 41-employer figure is the accurate one.

## What changed

`bestiejob@fb08a50` — new `## 2026-11-01 addendum` section at the top of the README (above the
generated index, so a regenerator cannot clobber it):

| Group | Count | Basis |
|---|---|---|
| Live-verified Canadian postings | 9 | Opened 2026-11-01, title + company confirmed |
| Peer-claimed, Adzuna 403 | 7 | Could not open; marked unverified explicitly |
| Outstanding employer list | 25 | Unverified targets so the next pass doesn't re-derive them |
| External finds (outside repo) | 5 | Lightspeed, Scotiabank ILM, Infgrp, Johnson Controls (Mexico — out of scope), S.i. Systems (blocked) |

Live-verified rows: Slalom *Salesforce Developer – Enhance & Operate* (GTA, 2026-10-31), ATB
Financial *Salesforce DevOps Developer* (Calgary, 10-30), Aquiva and Hapi *Senior Salesforce
Engineer* (Vancouver, 10-30), Trans Mountain *Senior ServiceNow Specialist* (Calgary, 10-28),
Take-Two Interactive *Senior Lead, ServiceNow ITOM* (Toronto, 10-25), plus Interac, HCL Canada,
Dawn InfoTek and RSM Canada from Eluta.

## Verification

- `curl` of `raw.githubusercontent.com/.../main/README.md`: addendum present, 670 lines.
- 9/16 candidate URLs opened in headless Chromium: LinkedIn + Workopolis returned 200 with matching
  title and location. Adzuna returned **403** for all 7 `adzuna.ca/details/*` links, so those are
  published as unverified rather than dropped.
- Eluta served a bot-check marker on 3 pages — title/company still rendered, so they are marked
  "Live; page served a bot-check marker" instead of "verified".
- Eluta/Adzuna rows carry "date not on page" rather than an invented date.

## Known gaps

- S.i. Systems is F5-blocked ("Request Rejected"); its Senior Salesforce DevOps req has a job end
  date of 2026-10-31 and is probably expired.
- Johnson Controls *ServiceNow Platform Owner & Chief Architect* is in Mexico, not Canada — recorded
  so a future scan doesn't re-surface it.
- 25 employers still need individual verification before they can be listed as postings.
