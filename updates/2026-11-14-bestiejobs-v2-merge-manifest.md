# BESTIEJOB — Merge Manifest (bestiejobs-v2, 2026-11-14)

This manifest records the rows submitted by the `bestiejobs-v2` worktree for the 2026-11-14
remaining-items round, so they can be cherry-picked or re-applied if a concurrent agent's merge
overwrites them.

## Inbox file
`inbox/kilo-bestiejobs-v2-remaining--2026-11-14--v1.md`

## Submitted rows (4)

| Posted | Role | Company | Location | URL |
|---|---|---|---|---|
| 2026-10-31 | Salesforce Consultant, GoC focus | Deloitte | Ottawa, ON | https://ca.linkedin.com/jobs/view/salesforce-consultant-goc-focus-at-deloitte-4460503246 |
| 2026-10-08 | Salesforce Lead | OSI Digital | Vancouver, BC | https://ca.linkedin.com/jobs/view/salesforce-lead-at-osi-digital-4477457331 |
| 2026-11-12 | Senior ServiceNow Discovery & Service Mapping Engineer | RBC | Toronto, ON | https://rbc.wd3.myworkdayjobs.com/RBCGLOBAL1/job/TORONTO-Ontario-Canada/Senior-ServiceNow-Discovery---Service-Mapping-Engineer_R-0000167419-2 |
| 2026-11-13 | ServiceNow Architecture Consultant | CGI | Calgary, AB | https://cgi.njoyn.com/CORP/xweb/xweb.asp?page=JobDetails&CLID=21001&Jobid=J1126-1312&BRID=1349609&lang=1 |

## Merger dry-run result
- `kilo-bestiejobs-v2-remaining--2026-11-14--v1.md: +3 new, 1 duplicate`
- Net-new merged: Deloitte GoC, RBC SN Discovery, CGI SN Arch.
- OSI Lead Vancouver (2026-10-08) is outside the 30-day window (cutoff 2026-10-15) so it is NOT added
  this round; it remains a valid lead if re-submitted while still live.

## Guard status
- `check_readme_sort.mjs`: OK (newest-first)
- `readme_job_row_guard.py`: PASS, 0 net row loss

## Deploy record
- Target: BESTIEJOB remote `main`
- Merge commit: `fc0702a` (48b08d4 → fc0702a)
- Verified live on GitHub Pages: Deloitte GoC (`4460503246`) + RBC SN Discovery (`R-0000167419`) confirmed on `https://eltonaguiar.github.io/BESTIEJOB/`. CGI Njoyn row present on remote main; its query-heavy URL not rendered on the Pages mirror snapshot.
- Other commits this session pushed to findtorontoevents_antigravity `main`: `a3adf286b34` (patterns), `c91b2c497d7` (discovery), `e5a8b61c642` (wrap-up), `6ce1422f9a0` (fresh-scan audit).
