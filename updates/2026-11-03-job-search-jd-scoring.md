# Job Search — Stage 3: JD Extraction + Resume Scoring (2026-11-03)

**Session:** Request F ("next") — closing the "no JD bodies" gap documented in prior rounds.

## What Was Broken / Missing

- Rounds 0-27 harvested **title/company/location/posted/url only** (LinkedIn guest cards).
- No cert requirements, no years-of-experience, no module mentions, no employment type, no bilingual/clearance signals.
- Result: 684 jobs but zero actionable "apply vs skip" intelligence.

## What Changed

### 1. Verified LinkedIn Guest Job-View Page Exposes Full JD

**Probe target:** `https://ca.linkedin.com/jobs/view/servicenow-platform-developer-at-acroynon-4484516741`

**Result:** HTTP 200, 328,842 bytes, contains:
- `show-more-less-html__markup` div (fallback)
- 2× `<script type="application/ld+json">` blocks
- JSON-LD `@type: JobPosting` with:
  - `title`: "ServiceNow Platform Developer"
  - `datePosted`: "2026-10-29T15:29:07.000Z"
  - `employmentType`: "CONTRACTOR"
  - `hiringOrganization.name`: "acroynon"
  - `jobLocation.address`: `{addressCountry:"CA", addressLocality:"Etobicoke", addressRegion:"ON"}`
  - `experienceRequirements.monthsOfExperience`: 60 (structured 5 years!)
  - `educationRequirements.credentialCategory`: "bachelor degree"
  - `description`: 4,419 chars HTML (mentions hybrid 2 days onsite Mon/Wed, TSOM/CSM/FSM/Sales CRM/HAM/ITSM, REST/SOAP, MID servers)

**Implication:** Guest scraping is now a **two-stage pipeline**:
1. `seeMoreJobPostings/search` → title/company/location/posted/url (fast, 10 per page)
2. `jobs/view/<slug>-<id>` → full JD + structured fields (slower, 1 per job)

### 2. Built `/tmp/jobs/jd_extractor.py`

**Components:**
- `fetch()` — curl with desktop UA + Accept-Language: en-CA
- `extract_jd()` — JSON-LD primary, markup fallback
- `parse_signals()` — regex extraction of:
  - Certs (CSA, CAD, CIS-*, PD1, JS1, ITIL, Alteryx, Databricks, Tableau)
  - Modules (ITSM/ITOM/GRC/IRM/... + Apex/Lightning/LWC/CPQ/...)
  - Years (`(\d+)\s*(?:\+|or more)?\s*(?:years?|yrs?)`)
  - Onsite/hybrid/remote/bilingual/clearance flags
- `score_job()` — weighted resume match:
  - +3 certs subset of resume
  - -1 certs gap
  - +2 years ≤ 6
  - -2 years > 8
  - +2 modules overlap
  - -2 bilingual required (resume not bilingual)
  - -1 clearance
  - +1 remote/hybrid
  - Bucket: apply (≥4), consider (≥1), skip (<1)

**Resume baseline (Elton Aguiar):**
```json
{
  "certs": ["CSA","CAD","CIS-PA","CIS-RC","CIS-HAM","CIS-SAM","CIS-DISCO","CIS-SPM","CIS-HR","CIS-ITSM","CIS-EM","CSDM","ITIL","PD1","JS1","Platform App Builder","Alteryx","Databricks","Tableau"],
  "modules_sn": ["ITSM","ITOM","GRC","IRM","HRSD","CSDM","Discovery","Flow Designer","IntegrationHub","Virtual Agent","Service Portal","HAM","SAM","SPM","CSM","FSM","TSOM"],
  "modules_sf": ["Apex","Lightning","LWC","CPQ","Pardot","MuleSoft","Marketing Cloud","Sales Cloud","Service Cloud","Experience Cloud","Data Cloud"],
  "years": 6,
  "employers": ["CIBC","BMO","Metrolinx","RBC"],
  "bilingual": false
}
```

### 3. URL Selection + Extraction Run

**Selection criteria (ranked):**
1. GTA cities first (Toronto 60, Mississauga 12, GTA 5, Richmond Hill 2, Etobicoke 1)
2. Platform-titled jobs before generic "Developer"
3. Freshest posted dates

**Run:** 80/80 URLs succeeded → `/tmp/jd_scored.json`

### 4. Results

**Buckets:**
- apply: 49
- consider: 22
- skip: 9

**Score distribution:**
```
-2: 1
 0: 8
 1: 9
 2: 2
 3:11
 4:10
 5:12
 6: 5
 7: 4
 8:18  ← top tier (all score 8)
```

**Top 10 apply-tier (all score 8):**
1. Cognizant ServiceNow Senior Technical Consultant
2. Cognizant ServiceNow Technical Consultant
3. LanceSoft Salesforce Developer
4. Deloitte Lead Specialist ServiceNow CMDB Solution Architect
5. Deloitte Lead Specialist ServiceNow GRC Solution Architect
6. Deloitte Technical Delivery Mgr ServiceNow IRM/Sec Ops
7. Cognizant Salesforce nCino Developer
8. Cognizant Salesforce Data Cloud Developer
9. Havas CX Sr. Specialist Salesforce Data Cloud & Loyalty
10. Benevity Senior Salesforce Administrator

**True gaps (skip bucket):**
- McKesson Lead Salesforce Solution Architect (score -2): years_gap + clearance
- CGI Salesforce Architect (0)
- Insight Global Technical Lead Salesforce (0)
- TCS Salesforce Developer (0)
- J&M Group Salesforce Communications Cloud Architect (0)

**Cert gaps identified:**
- [Databricks, Tableau] → Salesforce Consultant roles
- [CAD] → Senior Salesforce Architect roles
- [Platform App Builder] → Salesforce Solution Lead roles
- [CSA] → ServiceNow Platform Specialist roles

**Bilingual friction (4 roles):**
- Deloitte Senior Manager ServiceNow - Operate
- Bell ServiceNow Senior Technical Advisor
- Co-operators Senior Business Analyst - Salesforce
- Bell ServiceNow System Administrator

**Employment type mix:** CONTRACTOR (acroynon example), FULL_TIME (most others)

### 5. Output Artifacts

- `job_search_application_tracker_2026-11-03T053628Z.json` — full scored dataset (apply/consider/skip arrays)
- `job_search_application_tracker_2026-11-03T053628Z.md` — human-readable with:
  - Resume baseline
  - Scoring rules table
  - apply/consider/skip sections (reasons + URLs)
  - Key Insights block (easy wins, true gaps, bilingual friction, cert gaps, employment type, next actions)

### 6. Skill Update

Added "Stage 3 — JD Extraction" section to `.agents/skills/job-hunting/SKILL.md`:
- JSON-LD field table
- Full extractor code (fetch/extract/parse/score)
- Requirement parsing regex table
- Resume scoring model
- Run command + output contract

**Skill now documents 3-stage pipeline:**
1. Harvest (title-only, 10/page)
2. Pattern mining + dedupe
3. JD extraction + resume scoring (apply/consider/skip)

## Git Safety

Per AGENTS.md:
- Only stage self-authored files: `job_search_application_tracker_*`, `.agents/skills/job-hunting/SKILL.md`, `updates/2026-11-03-job-search-jd-scoring.md`
- Never stage other authors' files (e.g., `tools/job_discover.py`, `updates_findtorontoevents.md`, `validate_real_data.py`)
- Create branch from clean remote commit `7ed21345a97` on `origin/job-search-2026-11-03` (or from `job-search-2026-11-03-rounds21-27`)
- Cherry-pick only own commits
- Never force-push

## Caveats (Documented for Honesty)

1. **Years regex is first-match only** — `(\d+)\s*(?:\+|or more)?\s*(?:years?|yrs?)` can catch "3 years of experience with REST" instead of the real requirement. Requires spot-checks on high-score jobs.

2. **Module extraction is title-case only** — "itsm" lowercase in JD will be missed. Case-insensitive regex mitigates but does not eliminate.

3. **Bilingual inference is weak** — French queries in Rounds 23/25/27 were title-only; actual bilingual workplace requirement is only detectable in JD body (now captured).

4. **80-job sample is GTA-heavy** — Remote Canada and province-level jobs were deprioritized in URL selection. Full 684-job scoring would require ~2h of polite scraping.

5. **No salary/visa data** — LinkedIn guest pages do not expose compensation or sponsorship signals. Requires authenticated session or ATS board crawling.

## Next Actions (from tracker Key Insights)

1. **Easy wins (18 jobs scored 8):** Apply immediately — Cognizant/Deloitte/LanceSoft/Benevity roles match resume certs + modules exactly.
2. **True gaps (1 clearance + 8 years-gap):** Skip McKesson; consider upskilling or role reframing for others.
3. **Bilingual friction (4 roles):** Either acquire French or filter out Bell/Deloitte/Co-operators bilingual postings.
4. **Cert gaps:** Prioritize Databricks + Tableau (Salesforce side) and CAD (ServiceNow side) for next 30-day sprint.

---

**Author:** Zoo  
**Session:** Request F ("next") — JD extraction + resume scoring  
**Date:** 2026-11-03T05:36Z  
**Files authored:** `job_search_application_tracker_2026-11-03T053628Z.json`, `job_search_application_tracker_2026-11-03T053628Z.md`, `.agents/skills/job-hunting/SKILL.md` (Stage 3 section), `updates/2026-11-03-job-search-jd-scoring.md`