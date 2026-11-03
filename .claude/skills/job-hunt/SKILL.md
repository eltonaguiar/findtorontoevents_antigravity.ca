---
name: job-hunt
description: End-to-end ServiceNow/Salesforce/IT job-hunting pipeline for the BESTIEJOB board. Use when the user says "/job-hunt", "find jobs", "more job hunting", "job search rounds", or wants fresh SN/SF/other postings harvested, classified and merged to eltonaguiar/BESTIEJOB. Covers LinkedIn guest harvesting, ATS boards (Workday/Greenhouse/Lever), dual-AI classification consensus, keyword mining, and the safe inbox→merger→push flow. Aliases - jobhunt, job-rounds, bestiejob-scan.
---

# Job Hunt — reusable pipeline for BESTIEJOB

Proven over 2026-11-03 sessions: +87, +101 net-new postings pushed with zero
fabricated rows and zero in-window row loss. Five phases; each has a tool or
exact recipe in this folder.

## Phase 0 — Baseline (always first)

Dedup baseline = union of BOTH files in the bestiejob clone
(`bestiejob/` inside this repo, remote `eltonaguiar/bestiejob`):

- `README.md` → all `](url)` markdown links
- `jobs.json` → `jobs[].url`
- Plus LinkedIn numeric job IDs extracted from those URLs
  (`/jobs/view/...-<ID>` and `/jobs/view/<ID>`): two different URLs with the
  same ID are the SAME job.

`git pull --rebase` the clone first; if it fails due to other agents'
uncommitted files, DO NOT stash/clean — read the files as-is.

## Phase 1 — Harvest (use `harvester.py` in this folder)

```bash
cp .claude/skills/job-hunt/harvester.py /tmp/jobrounds/harvester.py
python3 -c "import sys; sys.path.insert(0,'/tmp/jobrounds'); from harvester import run_round; ..."
```

**LinkedIn guest API** (no auth): `https://ca.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search`
- params: `keywords`, `location`, `start` (0/25/50…), `f_TPR` (r259200=3d,
  r604800=7d, r1209600=14d), `f_WT=2` (remote)
- Posted date comes from `<time datetime="YYYY-MM-DD">` — NEVER invent dates.
- Pace ≥2.5s between calls; on 429 sleep ~9s and retry once; expect bursts of
  429 after ~10 rapid queries.
- Desktop UA required.

**Search-round playbook** (order by value, measured):
1. Toronto + GTA cities (Mississauga, Markham, Etobicoke, Vaughan, Brampton)
2. Remote Canada (`f_WT=2`), then ambiguous Canada (no WT filter)
3. **Partner firms — richest vein (+87 in one session):** Deloitte, Accenture,
   KPMG, CGI, Cognizant, EY, Capgemini, IBM, Infosys, TCS; boutiques Thirdera,
   GlideFast, NewRocket, Ateko/FX Innovation, Slalom, NeuraFlash, OSF Digital,
   Plative. Query style: `keywords="ServiceNow Accenture"`.
4. IT staffing agencies: Raise, Procom, TEKsystems, Akkodis, Insight Global,
   Randstad, Hays, Robert Half, S.i. Systems, Motion Recruitment, Alldus,
   Epsilon Solutions, Acestack, Tamanna, Delpath, Maarut, J&M, Zodiac.
5. Product-line keywords (from pattern mining): SN — HRSD, SPM, SecOps, IRM/GRC,
   Now Assist, CSM, SAM Pro, Platform Specialist, Service Mapping, Integration
   Hub, CMDB, ITOM Discovery. SF — Marketing/Revenue/Data/Commerce/
   Communications/Financial Services Cloud, OmniStudio, Vlocity, MuleSoft,
   Copado, Agentforce, Apex, LWC, nCino.
6. French titles for QC: Développeur/Conseiller/Administrateur ServiceNow|Salesforce.

**ATS direct (Phase-1b):**
- Workday CXS: `POST https://<t>.wd3.myworkdayjobs.com/wday/cxs/<t>/<site>/jobs`
  body `{"searchText":"ServiceNow","limit":20,"offset":0,"appliedFacets":{}}`.
  Known-good tenants: `td/TD_Bank_Careers`, `manulife/MFCJH_Jobs`,
  `bmo/External`, `cibc/search`, `sunlife/Experienced-Jobs` (all wd3).
  (scotiabank=422, rbc=404, wtw=none — tenant/site names wrong, rediscover before use.)
  Normalize `postedOn` ("Posted Today/Yesterday/30+ Days Ago") to real dates;
  drop or re-date rows the merger would reject.
  Job URL = `https://<t>.wd3.myworkdayjobs.com/en-US/<site><externalPath>`.
- Greenhouse: `GET https://boards-api.greenhouse.io/v1/boards/<slug>/jobs`
  (known-good slug: `neuraflash`). **Patch Posted from `updated_at[:10]`.**
  GEO-FILTER HARD: "Remote - United States/India/Colombia" rows must be dropped
  (require `Canada` in location).
- Lever: `GET https://api.lever.co/v0/postings/<slug>?mode=json` (no Canada
  slugs verified yet).
- Job Bank: scrape `jobbank.gc.ca/jobsearch/jobsearch?searchstring=<kw>` — rows
  lack dates; fetch per-posting pages or drop (undated rows are merger-rejected).

## Phase 2 — Keyword mining (self-improving loop)

Mine the current README SN/SF sections for 2-3-gram title patterns and
companies with ≥3 postings; feed both back as Phase-1 queries. Recruiters that
post many reqs (Alldus, Epsilon…) are standing queries.

## Phase 3 — Classification (dual-AI consensus; NEVER single-model)

- Voters: pick 2+ from the capability map
  `/home/eaguiar2015/dbpasses_ASK_2026-11-02.txt` (latest UPDATE wins; keys in
  `/home/eaguiar2015/dbpasses.txt`). Proven ladder: groq `qwen/qwen3.8-27b` →
  llm7 `codestral-latest` (key or "unused") → **local vLLM :8000
  Qwen2.5-14B (no rate limits — best fallback)** → mistral keys ×3.
  Gemini free tier exhausts quickly on bulk days.
- Chunk ≤140 rows/prompt (45 for the local 14B). Prompt in
  `classify_rules.md` (this folder). Output JSON `[{"i":N,"c":"SN|SF|OTHER|REJECT"}]`.
- Consensus: both agree → take it. Disagree → keyword arbitration
  (title must contain a platform keyword to live; else REJECT).
- STRICT rejects: sales/CSM/GTM/RevOps-manager, exec/strategy, BIM,
  business-continuity, helpdesk, generic mgmt/ops/HR/finance, US/India-only.
  Keyword-query hits ≠ platform roles ("Portfolio Management Analyst" from a
  "CMDB" query is REJECT).

## Phase 4 — Merge & publish (the dangerous part — follow exactly)

1. Inbox file `inbox/<model-slug>--YYYY-MM-DD--v1.md` per
   `bestiejob/docs/JOB_SUBMISSION_METHODOLOGY.md`
   (6-col table: Posted|Role|Company|Location|URL|Note; Posted must be real
   YYYY-MM-DD; escape `|` as `/`).
2. NEVER run the merger in a dirty/shared checkout. Always:
   `git worktree add /tmp/bj-mainX -b <branch> origin/main`
3. **ALWAYS `python3 tools/jobs_merge_inbox.py --max-per-table 500`** — the
   default cap of 150 SILENTLY EVICTS in-window rows (would have deleted 556
   live postings once).
4. Pre-push verification (all mandatory):
   - removed-URL diff vs origin/main == only aged-out (>30d) rows
   - `node scripts/check_readme_sort.mjs`
   - `python3 .github/scripts/readme_job_row_guard.py --base origin/main --head HEAD`
5. Commit everything the merger touched (README, README.BAK, inbox renames) +
   Copilot co-author trailer; push `HEAD:main`; confirm CI guards green via
   `gh run list --repo eltonaguiar/bestiejob`; remove the worktree.

## Phase 5 — Anti-fabrication invariants

- Every row needs a real URL + source-shown date. 0-fabrication is the bar.
- Audit other agents' job datasets before merging: schema check, URL/date spot
  check, dedup vs board, reclassify with consensus (their SN sections often
  contain keyword-bycatch junk).
- Don't trust "vLLM is down" style claims — probe `:8000/v1/models` yourself.
