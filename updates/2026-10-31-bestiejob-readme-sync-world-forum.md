# bestiejob — README sync audit + World Forum partner portal scan (2026-10-31)

**Agent:** Buffy (Freebuff) · **Date:** 2026-10-31
**Target:** https://github.com/eltonaguiar/bestiejob (clone `~/bestiejob`)
**Baseline:** `origin/main` @ `40cd0fd` · **Local clone was on** `opencode-2026-10-30` @ `b33c3bf`, **11 commits behind main**

---

## 1. Why the README looked empty of Oct-30/31 jobs

Two independent causes, both confirmed by measurement:

### 1a. The README genuinely had no 2026-10-31 rows

Counted rows in the date-sorted index block of `origin/main:README.md`:

| Posting date | Rows |
|---|---|
| `2026-10-31` | **0** |
| `2026-10-30` | 3 |
| everything else | ≤ 2026-10-29 |

Meanwhile the Adzuna CA sweep produced **28** Canadian postings dated 2026-10-31. So the index was a full day stale, not merely incomplete.

### 1b. Nine peer branches were never merged

`git fetch --all` revealed 20 remote branches. PRs #2–#10 were merged; these were not:

| Branch | Job file(s) | URLs | Missing from README |
|---|---|---|---|
| `zoo/2026-10-30` | `ZOO_JOB_2026-10-30.MD`, `ZOO_TOP20_…MD` | 311 | 303 |
| `auto/2026-10-30` | `AUTO_JOB_…MD`, `AUTO_HQ_JOBS_…MD`, `ZOO_TOP20_…MD` | 258 | 236 |
| `kilo/2026-10-30` | `KILO_JOB_2026-10-30.MD` | 169 | 161 |
| `opencode-2026-10-30` | `opencode-…jobs.md`, `auto-…jobs.md` | 118 | 88 |
| `kilo-2026-10-30` | `kilo-…jobs.md`, `job-scan-prompt-template.md` | 61 | 35 |
| `buffy-2026-10-30` | `buffy-…jobs.md` | 40 | 17 |
| `copilot-sdk-servicenow-jobs-2026-10-30` | `COPILOT_SDK_…MD` | 14 | 13 |
| `auto-2026-10-30` | `auto-…jobs.md` | 37 | 8 |
| `buffy/servicenow-jobs-2026-10-30` | `BUFFY_SERVICENOW_JOBS_…MD` | 6 | 6 |

**Union of links absent from the README: 673.** Only PR #1 (`copilot/fix-bestiejob-issue`, WIP since 2026-01-30) is still open, and it has zero changed files.

Note the local clone also held four **untracked** files from another agent (`REPORT_SN_SF_2026-10-31.md`, `SERVICENOW_WORLD_FORUM_CROSSREF.md`, `recent_sn_sf_scan.json`, `scripts/*.mjs`) plus modified `package.json`/`package-lock.json`. Those were left untouched and **not** committed.

---

## 2. What was changed

Work done in a clean worktree from `origin/main` so unrelated local edits stayed untouched:

1. **README.md** — new top section `## 2026-10-31 update — dated postings, unsynced branches, World Forum portals`, placed above the auto-generated `DATE-SORTED-PLATFORM-INDEX` block (so a regenerator cannot clobber it). Contains:
   - 28 Oct-31 Canadian postings + the 1 portal-only Procom find (29 rows)
   - 12 Oct-30 postings with dates/salaries/cert language
   - the branch inventory table above (673 links)
   - the World Forum sponsor → portal crosswalk
   - general-application capability matrix
   - agency portal status table
2. **`Buffy-2026-10-31-world-forum-portals.md`** — long-form version of the forum/portal crosswalk (per-sponsor detail, ATS, cert language, stale-listing flags).
3. **PR coverage table** — added the missing PR #10 row.

Nothing from another author was staged or pushed.

---

## 3. World Forum research

The official agenda page is **HTTP 403 (Akamai)** to plain fetch and to headless Chromium (`errors.edgesuite.net` reference), so the roster was assembled from sponsor announcements, partner event pages and secondary listings:

- Vendelux NYC attendee page (renders, but attendee names are gated)
- NewRocket event page — confirms **Toronto on its city list** ("More information coming soon")
- Dynatrace Toronto page — confirms **2026-11-03, Metro Toronto Convention Centre**
- Infosys event page (403), Instagram/LinkedIn sponsor announcements for SageX, Pentio, Advance Solutions, Wind River

Toronto roster used: Ondaro (Platinum), SageX Transformations (Gold, Booth #25), Pentio (Gold), Five9, Wipro (session presenter), Wind River. Other-city partners: EPAM (NYC Gold), Advance Solutions (London Gold), iOPEX (London), Aelum (Mumbai Gold), Quadrafort (Mumbai Gold), Input Zero (Mumbai Gold), Pulse & Patterns (Amsterdam Gold), plus Infosys and Capgemini as global partners.

---

## 4. Portal scan — new tool

Added **`tools/jobscan/partner_portal_scan.py`** (this repo):

```
python3 tools/jobscan/partner_portal_scan.py --out /tmp/portals
python3 tools/jobscan/partner_portal_scan.py --urls my_portals.txt --details
```

- Drives Chromium (`--no-sandbox`), scrolls lazy-loaded job cards, extracts keyword-matched anchors with surrounding context.
- Detects **ATS** from anchor hosts: Workday, Greenhouse, Lever, SmartRecruiters, Jobvite, SuccessFactors/TalentBrew, Zoho Recruit, Cornerstone, iCIMS, Taleo, Workable, Ashby, BambooHR, Phenom, Recruitee, JobDiva, Bullhorn.
- Detects **general/speculative application** copy: talent network, talent community, talent pool, "no perfect role", "don't see a role", "send us your resume", candidature spontanée, evergreen reqs.
- Optional `--details` pass extracts posting date, salary and cert wording per matched req.

Bugs found and fixed during the run: `KeyError: 'ats'` on the exception path (unreachable site), and a dropped trailing comma in the f-string that caused a `SyntaxError`. Both fixed; `py_compile` clean.

### Scan results — 35 portals

| Group | Portals | Reachable | Matched reqs |
|---|---|---|---|
| Forum Toronto | 10 | 9 | 32 |
| Forum global | 7 | 6 | 8 |
| Agencies | 18 | 12 | 10 |

Highlights:
- **Ondaro** — Greenhouse `gh_jid` 4028466007 (ServiceNow Architect) + 4233479007 (Technical Consultant). Canada location unconfirmed (Greenhouse page body did not render to the scanner).
- **Wipro** — 7 ServiceNow reqs, certs quoted verbatim (CSA, CIS-ITSM, CTA), Talent Network general application. None of the 7 exposed a location in the DOM.
- **Aelum** — Zoho Recruit, 2 reqs, both dated **07/01/2025** → stale; has the best speculative form ("No perfect role? No stress" + CV upload).
- **Procom** — 5 reqs, incl. **BSA – ServiceNow SAM/ITAM for Bank of Montreal** (posted 2026-08-06, requires CSA, ITIL) and **IT Security Analyst – SSL/TLS KPI (ServiceNow)**, Toronto hybrid, 3 days ago.
- **Alldus** — reachable; specialism-filter URLs (`?_specialism=servicenow-developer`) are the usable entry point.
- **SageX** — no careers page exists; `/contact-us` only.
- **Infosys** 403; **Capgemini/EPAM/Dynatrace** render client-side with 0 anchors — recorded as limitation, not as "no jobs".
- **Advance Solutions** TLS error; **Quadrafort/Input Zero** 404 on careers.
- **S.i. Systems, Artech, GTT, Hire DigITalent, Maarut, Systematix** — every guessed URL 404. All six were posting SN/SF roles on Adzuna within 7 days, so this is an entry-point problem, not a vacancy problem.

---

## 5. Verification

| Check | Result |
|---|---|
| `git log origin/main` / `git fetch --all` | 20 branches enumerated; 673-link gap computed by URL-normalised set difference |
| README row counts | `grep -c '^| 2026-10-31'` → 0; `'^| 2026-10-30'` → 3 (before change) |
| `py_compile` on both scanners | OK |
| Partner scan | 27 + 8 portals, per-site status/ATS/match counts in `portal_scan.json` |
| Detail pass | 9 postings opened; Procom SAM/ITAM + security analyst quotes captured verbatim |
| README renders | inserted block sits above the generated-index markers; tables use the file's existing pipe style |

**Not verified:** the official forum agenda (403), Ondaro's Canada location, Wipro's req locations, and every Adzuna-derived row (aggregator date only). The 404'd agency portals were not brute-forced.

---

## 6. Appendix — files

- `Buffy-2026-10-31-world-forum-portals.md` in bestiejob (committed)
- `tools/jobscan/partner_portal_scan.py` (this repo, new)
- `tools/jobscan/playwright_job_scan.py` (this repo, from the earlier pass)

---

## 7. Second defect found while pushing — README truncation

`git show --stat` on the commits between `40cd0fd` and `8c25626`:

| Commit | Intent | Actual diff |
|---|---|---|
| `bf3fdb4` | add KPMG/Deloitte/Cognizant rows, fix Salesforce sort | +5/−1 |
| `50c1ed3` | add Harris Computer ServiceNow admin | +1 |
| **`8c25626`** | **add CGI + Cognizant ServiceNow rows** | **+6 / −508** |

Result: README went from **583 lines / 130,781 bytes to 85 lines / 19,988 bytes**.

Measured loss (URL-normalised set difference, `40cd0fd` vs `8c25626`):

- **210 posting table rows**, **189 unique links**
- largest losses: `Additional peer leads` 100 rows, `Recent (within 60 days)` 23, `ServiceNow – Toronto/Canada` 10, `Salesforce – Canada` 13, `Playwright scan additions` 8, `Junior review` 6, `Government source review` 7
- whole sections gone: **Filters**, **Simplify applications source**, **Running locally**, **Add-On Pages**, **Navigation**

Repair: restored every lost row verbatim from `40cd0fd`, each under its original heading and markdown table header (so columns stay typed), plus the four documentation sections. Rows whose URL already exists in the current README are not duplicated — verified `dupes: 0`.

Cause is the silent-file-revert pattern already documented in this repo: a full-file write based on a stale read. Both this and the missing Oct-31 rows are consequences of the same hazard.
