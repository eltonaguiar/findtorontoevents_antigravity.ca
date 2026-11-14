# ServiceNow & Salesforce Developer Job Discovery — Pattern Analysis & Methodology

Date: 2026-11-14 · Author: Kilo (bestiejobs-v2 worktree) · For: BESTIEJOB board (eltonaguiar/bestiejob)

## 0. Scope

This document answers two questions for the BESTIEJOB board:

1. What patterns exist in the current ServiceNow (SN) and Salesforce (SF) developer job postings?
2. What methodology should be used to keep finding SN/SF developer roles in Toronto / GTA / Ontario /
   Canada / Remote-Canada?

It is grounded in the live board data (`jobs.json`, 5,376 postings), the existing
`job-hunt`/`job-location-audit` skills, and a SubQ decision-model cross-check (`subq-snap-1.2`).

---

## 1. How BESTIEJOB currently finds SN/SF jobs (the methodology)

The proven pipeline (from `.claude/skills/job-hunt/SKILL.md`, validated 2026-11-03: +87 +101
net-new postings, zero fabricated rows):

| Phase | What it does |
|---|---|
| 0 Baseline | Dedup baseline = `README.md` links + `jobs.json[].url` + LinkedIn numeric job IDs |
| 1 Harvest | LinkedIn guest API (`ca.linkedin.com/jobs-guest/...`), ATS boards (Workday CXS, Greenhouse, Lever), Job Bank |
| 2 Keyword mining | Mine README SN/SF sections for 2–3-gram title patterns + companies with ≥3 postings → feed back as queries |
| 3 Classification | Dual-AI consensus (2+ voters), never single model; strict reject list |
| 4 Merge/publish | Inbox file → `tools/jobs_merge_inbox.py --max-per-table 500` → merge + CI guards |
| 5 Anti-fabrication | Every row needs a real URL + source-shown date; audit peers before merging |

### Search-round playbook (value-ordered)
1. Toronto + GTA cities (Mississauga, Markham, Etobicoke, Vaughan, Brampton)
2. Remote Canada (`f_WT=2`), then ambiguous Canada
3. **Partner firms** — richest vein: Deloitte, Accenture, KPMG, CGI, Cognizant, EY, Capgemini, IBM,
   Infosys, TCS; boutiques Thirdera, GlideFast, NewRocket, Ateko/FX, Slalom, NeuraFlash, OSF, Plative
4. IT staffing agencies: Raise, Procom, TEKsystems, Akkodis, Insight Global, Randstad, Hays, Robert Half,
   S.i. Systems, Motion, Alldus, Epsilon, Acestack, Tamanna, Delpath, Maarut, J&M, Zodiac
5. Product-line keywords: SN — HRSD, SPM, SecOps, IRM/GRC, Now Assist, CSM, SAM Pro, Platform Specialist,
   Service Mapping, Integration Hub, CMDB, ITOM Discovery. SF — Marketing/Revenue/Data/Commerce/Financial
   Services Cloud, OmniStudio, Vlocity, MuleSoft, Copado, Agentforce, Apex, LWC, nCino
6. French titles for QC

### ATS direct (Phase 1b)
- Workday CXS tenants: `td/TD_Bank_Careers`, `manulife/MFCJH_Jobs`, `bmo/External`, `cibc/search`,
  `sunlife/Experienced-Jobs` (all wd3). Normalize `postedOn`; job URL = `<tenant>.wd3.myworkdayjobs.com/en-US/<site><externalPath>`.
- Greenhouse: `boards-api.greenhouse.io/v1/boards/<slug>/jobs` (slug `neuraflash` verified). Patch Posted from
  `updated_at[:10]`. Hard geo-filter: require "Canada" in location.
- Lever: `api.lever.co/v0/postings/<slug>?mode=json` (no Canada slugs verified yet).

---

## 2. Patterns in the current postings (from live data)

Data: `bestiejob/jobs.json`, 5,376 postings, 2026-11-11 scraped. SN ≈ 1,076 rows; SF ≈ 1,069 rows.

### 2.1 Role mix (developer focus)
- **ServiceNow**: 575 developer/engineer/architect/admin/implementation titles of 1,076 (53%). Of those,
  314 (55%) are senior/lead/principal — the market skews senior. 385 dev rows are fresh since Nov 1.
- **Salesforce**: 711 dev-class titles of 1,069 (67%). 361 (51%) senior/lead. 483 fresh since Nov 1.
- Takeaway: the feed is already heavily developer-shaped, but senior titles dominate. Junior/mid SN/SF
  developer roles are the scarcer, higher-value find.

### 2.2 Location distribution
| Bucket | SN | SF |
|---|---|---|
| Toronto/GTA | 348 | 433 |
| Ontario | 43 | 24 |
| Canada (other/unsp.) | 372 | 336 |
| Remote | 52 | 66 |
| Other/ambiguous | 239 | 192 |
| US | 22 | 18 |

- Toronto/GTA + Canada = the core (paired, ~70–80%).
- **US/other creep is real**: SubQ `us_creep` noul = **0.83** → keep the strict geo-filter on every round.

### 2.3 Top employers (developer rows)
- **ServiceNow** (dev rows): KPMG Canada (76), ServiceNow direct, Deloitte (25), CGI (22), Accenture
  Federal Services (21), Harris Computer, TCS, NewRocket, BDO, Scotiabank, Cognizant, Bell, Pomerleau.
  Big-5 consultancies + banks/telecom dominate.
- **Salesforce** (dev rows): Salesforce direct (50), Canadian Cancer Society (18), Cognizant (17),
  NeuraFlash (17), Maarut (13), TCS, Epsilon, McKesson, Slalom, iA Financial, Acestack, jobgether.
  Vendor-direct + specialist partners (NeuraFlash/Slalom) + agencies.

### 2.4 SubQ decision cross-check (subq-snap-1.2)
| Question | Decision | Confidence |
|---|---|---|
| Best SN developer channel | **big5_consultancies** | p=0.887, conf 0.86 |
| Best SF developer channel | **product_vendor** (Salesforce direct), close 2nd specialist_partners | p=0.515 / 0.393, conf 0.39 |
| Agency noise dominating? | noul 0.41 → moderate, not dominant | — |
| US/other-country creep | noul **0.83 → keep strict geo filters** | — |

Implication for future rounds:
- ServiceNow: prioritize Big-5 consultancies + banks/telecom employer-direct ATS + partner boutiques.
- Salesforce: prioritize Salesforce's own careers + specialist partners (NeuraFlash, Slalom, OSF, Plative)
  over generic agencies.
- Maintain the hard Canada geo-filter; agency rows are acceptable but should carry an "original employer ATS"
  note when they mirror direct postings.

---

## 3. Recommended discovery methodology (Toronto/GTA/Canada-remote, SN/SF developer)

This is the playbook used for this run and recommended for recurring rounds.

### 3.1 Source priority (employer-direct first)
1. **Workday CXS** (known tenants) + discover new tenants via career-site links.
2. **Greenhouse / Lever** boards for partner firms (Slalom, NeuraFlash, OSF, Plative, Deloitte, TCS).
3. **LinkedIn guest API** rounds (Toronto+GTA, Remote Canada, partner-firm keyword rounds).
4. **Vendor direct**: `careers.servicenow.com`, `careers.salesforce.com` (Canada filter).
5. **Staffing agencies** only as a supplement, with ATS-origin notes.

### 3.2 Search-round order (value)
1. Developer-keyword rounds in Toronto/GTA (SN: "ServiceNow Developer", "ServiceNow Engineer",
   "ServiceNow Architect", "ServiceNow Admin". SF: "Salesforce Developer", "Salesforce Engineer",
   "Salesforce Architect", "Salesforce Admin", "LWC", "Apex").
2. Remote Canada (`f_WT=2`) + ambiguous Canada.
3. Partner-firm keyword rounds: `ServiceNow Deloitte`, `ServiceNow KPMG`, `ServiceNow CGI`,
   `ServiceNow Accenture`, `ServiceNow BDO`, `ServiceNow Scotiabank`, `Salesforce NeuraFlash`,
   `Salesforce Slalom`, `Salesforce OSF`, `Salesforce Plative`.
4. Product-line keywords (HRSD, SPM, SecOps, CSM, SAM Pro, ITOM; Agentforce, Marketing Cloud,
   OmniStudio, MuleSoft, Vlocity, nCino) mapped to GTA + Ontario.
5. QC rounds in French for Québec (optional).

### 3.3 Classification rules (dual-AI consensus)
- Voters: 2+ of {local vLLM Qwen2.5-14B, Groq qwen3.8-27b, LLM7 codestral, Mistral, **SubQ
  subq-snap** as a lightweight decision voter}.
- Accept only SN/SF developer/engineer/architect/admin/implementation/integration/consultant titles.
- REJECT: sales/BDR/CSM/GTM/RevOps-manager/executive/strategy/BIM/helpdesk/generic HR-finance; US-only/India-only.
- Geo buckets: `toronto_gta`, `ontario`, `canada_other`, `remote_canada` only.

### 3.4 Anti-fabrication invariants
- Every row: real URL (HTTP 200) + source-shown absolute date. Never invent dates/URLs.
- Run `jobs_merge_inbox.py --max-per-table 500` (default 150 silently evicts in-window rows).
- Pre-push: removed-URL diff vs origin/main == only aged-out (>30d) rows; `check_readme_sort.mjs`;
  `readme_job_row_guard.py`.

---

## 4. This run (2026-11-14)

- Dispached 3 parallel subagents (ATS boards / LinkedIn guest / partner+agency) to harvest fresh SN/SF
  developer postings for Toronto-GTA-Canada-remote.
- Results land in `/tmp/jobrounds/agent_{ats,linkedin,partners}.md` and are summarized in the run report.

## 5. Key takeaway

**ServiceNow = consultancies & banks/telecom (employer-direct). Salesforce = vendor-direct + specialist
partners. Both skew senior — target junior/mid explicitly. Keep the Canada geo-filter hard; US/other creep
is the #1 filter to enforce.**
