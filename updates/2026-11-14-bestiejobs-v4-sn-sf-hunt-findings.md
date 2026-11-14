# BESTIEJOB — ServiceNow / Salesforce Hunt: Patterns, Methodology & Results

**Worktree:** `bestiejobs-v4` · **Run date:** 2026-11-14 (08:05–09:15 UTC) · **Author:** Kilo
**Board:** https://eltonaguiar.github.io/BESTIEJOB/ · **Repo:** eltonaguiar/BESTIEJOB
**Subagents used:** 5 (LinkedIn guest harvest, ATS direct, partner firms, BESTIEJOB GHA investigation, general GHA investigation)

---

## 1. Scope

1. Reverse-engineer the job-posting discovery methodology that feeds the BESTIEJOB board.
2. Mine the live board for patterns in ServiceNow (SN) and Salesforce (SF) postings.
3. Run a fresh discovery round for SN/SF developer roles in Toronto / GTA / Ontario / Canada-remote.
4. Report unique verified postings, methodology improvements, and pipeline/cron findings.

---

## 2. How BESTIEJOB finds SN/SF jobs today

Sources: `.claude/skills/job-hunt/SKILL.md` (validated 2026-11-03: +87, +101 net-new postings, zero fabricated rows), `bestiejob/docs/JOB_SUBMISSION_METHODOLOGY.md`, `bestiejob/docs/SERVICENOW_EXHAUSTIVE_HUNT_PLAN.md`, and the live workflows.

| Phase | What it does |
|---|---|
| 0 Baseline | Dedup baseline = `README.md` links + `jobs.json[].url` + LinkedIn numeric job IDs |
| 1 Harvest | LinkedIn guest API, Workday CXS, Greenhouse, Lever, Ashby, SmartRecruiters, Job Bank, vendor careers |
| 2 Keyword mining | Mine README SN/SF sections for 2–3-gram title patterns + companies with ≥3 postings → feed back as queries |
| 3 Classification | Dual-AI consensus (2+ voters), strict reject list |
| 4 Merge/publish | Inbox file → `tools/jobs_merge_inbox.py --max-per-table <high>` → merge + CI guards |
| 5 Anti-fabrication | Every row needs a real URL + source-shown date; audit peers before merging |

**Search-round playbook (value-ordered):** Toronto+GTA cities → Remote Canada → partner firms (Deloitte, Accenture, KPMG, CGI, Cognizant, EY, Capgemini, IBM, Infosys, TCS; boutiques Thirdera, GlideFast, NewRocket, Ateko/FX, Slalom, NeuraFlash, OSF, Plative) → IT staffing agencies → product-line keywords → French titles for QC.

**ATS direct:** Workday CXS (`td/TD_Bank_Careers`, `manulife/MFCJH_Jobs`, `bmo/External`, `cibc/search`, `sunlife/Experienced-Jobs`), Greenhouse (`neuraflash`), Lever, Ashby, SmartRecruiters, Job Bank.

**Merging is the dangerous part:** always `--max-per-table` well above the live per-family count (the default 150 silently evicts in-window rows); never run the merger in a dirty/shared checkout; pre-push guards = removed-URL diff vs base (only aged-out rows), `check_readme_sort.mjs`, `readme_job_row_guard.py`.

---

## 3. Patterns in the live board (2026-11-14)

Data: live page `JOBS` payload (5,133 rows: SN 907 · SF 962 · Other 3,264) + clone `jobs.json` (5,376 rows). Full artifact: `patterns_v4.json`.

### 3.1 Sources
- **SN:** LinkedIn 208 · Adzuna 132 · Workday 47 · Workopolis 43 · Greenhouse 42 · jobs.ca 35 · careers.servicenow.com 31 · SmartRecruiters 24 · BuiltIn 20.
- **SF:** LinkedIn 299 · Adzuna 230 · Greenhouse 46 · jobs.ca 45 · Workday 42 · Workopolis 29 · Eluta 18 · Lever 17.

### 3.2 Top employers
- **SN:** ServiceNow 31+5 · Deloitte 23 · CGI 19 · KPMG 17+4 · Accenture Federal 17 · Alldus 10 · Cognizant 9 · BMO 7 · GDIT 7 · TCS 7 · NewRocket 7.
- **SF:** Salesforce 25 · Cognizant 18 · NeuraFlash 16+13+7 · Epsilon 11 · Smart IT Frame 10 · Pacer 9 · Deloitte 9 · TCS 8 · Acestack 8.

### 3.3 Title / role patterns
- **SN:** developer 244 · senior 201 · architect 145 · consultant 118 · analyst 88 · engineer 88 · specialist 59 · lead 57 · manager 50 · administrator 46. Top 2-grams: "servicenow developer" (167), "senior servicenow" (71), "servicenow architect" (42).
- **SF:** developer 322 · architect 173 · senior 153 · lead 80 · consultant 73 · administrator 72 · engineer 66. Top 2-grams: "salesforce developer" (200), "senior salesforce" (92), "salesforce technical" (59), "marketing cloud" (51), "revenue cloud" (39).

### 3.4 Product-line keywords
- **SN:** ITAM 40 · ITOM 35 · CMDB 22 · GRC 21 · CSM 19 · SAM 19 · HRSD 14 · IRM 11 · SPM 10 · SecOps 10 · Discovery 8 · Service Mapping 3.
- **SF:** Marketing Cloud 55 · Revenue Cloud 38 · CPQ 29 · Agentforce 23 · Data Cloud 22 · FSC 18 · Commerce Cloud 13 · Service Cloud 13 · Apex 12 · nCino 9 · LWC 8 · OmniStudio 4 · MuleSoft 4.

### 3.5 Location & freshness
- **SN:** Canada/Remote 366 · Toronto/GTA 272 · Ontario 16 · Québec 18 · other 235.
- **SF:** Canada/Remote 347 · Toronto/GTA 342 · GTA-other 64 · other 192.
- Date histogram is spiky (2026-11-03/04 and 2026-11-11 are bulk-scan days); the 30-day window is the board's real constraint.
- French-language SN postings: 35 rows — a real QC segment, not noise.

### 3.6 Decision cross-check (SubQ Snap 1.2)
SubQ (free key, `https://api.subq.ai/v1/systemone`, model `subq-snap-1.2`) was used as a decision voter for channel selection and per-row classification. Channel read: **agencies over consultencies for raw volume, but consultancies/banks-telecom are the higher-signal SN channel; Salesforce is vendor-direct + specialist partners.** US/non-Canada creep remains the #1 filter to enforce.

---

## 4. Discovery methodology used by this run

Swarm style: parallel subagents, one per channel, each writing to a shared `/tmp/jobrounds/` drop; the lead cross-dedupes, classifies with dual-AI consensus, and merges.

1. **Baseline first** — union of live page `JOBS`, clone `jobs.json`, and `README.md` links; normalized URL + LinkedIn ID dedup.
2. **Parallel harvest** — LinkedIn guest (GTA + remote + product-line + French), ATS direct (Workday/Greenhouse/Lever/Ashby/SmartRecruiters/vendor), partner & agency career pages.
3. **QA gates per row** — HTTP 200 liveness; absolute `YYYY-MM-DD` date from the source; Canada geo; platform-role title check; dedup.
4. **Dual-AI classification** — SubQ Snap 1.2 (decision model) + local vLLM `Qwen2.5-14B-Instruct`; disagreements arbitrated by keyword rule (title must contain a platform keyword to live, else REJECT).
5. **Inbox → isolated worktree → push** — never merge in a shared checkout; `--max-per-table 5000`.

### Subagent results
| Agent | Raw | New after dedup | Verified HTTP 200 | Kept SN/SF |
|---|---|---|---|---|
| LinkedIn guest (A) | 930 | 59 | 59 | 13 / 18 (+8 OTHER) |
| ATS direct (B) | 190 Workday + Greenhouse/SmartRecruiters | 72 | 72 | 1 / 3 (+68 OTHER) |
| Partner firms (C) | ~30 firms probed | 2 | 2 | 1 / 1 |

Consolidated candidate pool: 179 rows → dual-AI classified → 8 SF, 5 SN, 25 OTHER, 141 REJECT. After Canada geo-filter, title+company dedup and a re-dedup against the **latest** `origin/main` (the board moves several times per hour), **9 rows were genuinely new** and were pushed.

---

## 5. Results — fresh postings added to the board

Pushed as commit `b7fcb27` on `eltonaguiar/BESTIEJOB@main`; README guard passed; GitHub Pages deploy succeeded (run 43578196215). Live page went **5,133 → 5,142 postings** (SN 907→910, SF 962→967).

| Posted | Role | Company | Location | Source |
|---|---|---|---|---|
| 2026-11-13 | Technical Architect Director - PubSec - Mulesoft Canada | Salesforce | Greater Montreal | LinkedIn |
| 2026-11-12 | ServiceNow Technology Lifecycle Analyst | BMO | Toronto, ON | employer ATS |
| 2026-11-12 | ServiceNow CMDB Administrator | BMO | Toronto, ON | employer ATS |
| 2026-11-11 | Q2C Senior Business Analyst | Salesforce Partner Canada | Toronto, ON | LinkedIn |
| 2026-11-11 | CSM/FSO Developer | Alldus | Toronto, ON | employer site |
| 2026-10-30 | IT Operations & CMDB Analyst | Purolator Inc | Mississauga, ON | LinkedIn |
| 2026-10-29 | Senior ServiceNow Discovery & Service Mapping Engineer | RBC | Toronto, ON | LinkedIn |
| 2026-10-28 | Salesforce Technical Architect | Orion Global Solutions | Toronto, ON | LinkedIn |
| 2026-10-21 | Salesforce Marketing and Data Cloud Consultant | Accenture | Toronto, ON | Workday |

All 9 URLs were verified HTTP 200 before submission; the live `jobs-data.json` carries the roles (some collapsed onto an existing mirror URL by `build_site.py`, which is the board's intended dedup).

---

## 6. Pipeline & cron findings (investigated by subagents)

### 6.1 BESTIEJOB GitHub Actions — 11 failed runs, root causes
- **Gap channels + Fresh CA sweep** failed at "Merge inbox into README": `README.md` had rows glued onto one line, so `extract_rows()` parsed 1 of 3. Fixed by `11dde886`.
- **board invariants** failed on every push: the 2026-11-11 baseline recorded only 2 of 11 kinds, so all other debt (non-canada 1108, split-row 80, vendor-sales 5, …) failed the ratchet.
- **Deploy Pages + board invariants** crashed on a `jobs.json` committed with Git conflict markers (`8f5987f8`). Fixed by `37401f40`.
- **Hourly scan + Fresh CA** push conflicts on generated files (transient).

### 6.2 General repo GitHub Actions — 11 failures, 4 patterns, **none job-hunting**
- `pandas==2.1.4` source build fails on Python 3.14 (5 runs) — `update-environment: false` + Ubuntu 26.04.
- `KeyError: 'LONG'` at `alpha_engine/scanner.py:2942` (4 runs).
- CI Tests `ValueError: Invalid frequency: ME` (pandas 2.1 vs ≥2.2).
- Playwright 1.58.2 unsupported on ubuntu26.04.
- All 365 workflows in the main repo enumerated: **zero** job/bestie/career pipelines.

### 6.3 Local cron (the real job-hunter gap)
- `node` is installed at `~/.hermes/node/bin`, but both `daily_scan.sh` and `cron_scan_30min.sh` only add `~/.local/bin` + nvm → **exit 127 on every run since 2026-11-08 (257 consecutive failures)**.
- `daily_scan.sh` merged with `--max-per-table 400` (live per-family ≈ 1,300) → would archive ~900 in-window rows per run.
- `cron_scan_30min.sh` merged with the 150 default and pointed at a **stale clone** (`/home/eaguiar2015/bestiejob`, last push 2026-11-08) while the working clone is inside the main repo.

---

## 7. Fixes shipped (commits on `eltonaguiar/BESTIEJOB@main`)

1. `68f7eb6` — **ci(jobs)**: serialize main pushes with a shared `bestiejob-main-write` concurrency group (hourly-scan, fresh-ca-scan, gap-channels, linkedin-sweep); `gap-channels` merge now passes `--max-per-table 5000`; `jobs_merge_inbox.insert_rows` no longer searches file-wide for a `| Posted | Role |` header (the job tables have none, so every new row was landing in the submission guide); every workflow that commits `jobs.json` now fails fast when it does not parse; invariants baseline re-recorded at the published 2026-11-14 counts.
2. `320bd2f` — **fix(jobs)**: local cron node PATH (`~/.hermes/node/bin`), `daily_scan.sh` inbox cap 400→5000, `cron_scan_30min.sh` cap 150→5000 + rebase-before-retry; cron repointed from the stale clone to the current one.

---

## 8. Recommendations

1. **Automate Phase 2 (keyword mining).** Mine the live board nightly for new 2–3-gram title patterns and append them to the LinkedIn sweep keyword list automatically (today it is a manual AI-panel export).
2. **Make dual-AI classification a standard pre-merge gate.** Add `scripts/classify_inbox.py` (SubQ optional + local model) and call it from `hourly-scan.yml` before the merger.
3. **Repair the legacy board debt** the re-recorded baseline now ratchets: 1,108 non-Canada rows, 413 identity-date conflicts, 80 split rows, 43 outside-window, 5 vendor-sales, 2 clock-date, 1 duplicate-URL, 1 count-disagreement. The gate will now fail when these grow.
4. **Reconcile the two bestiejob clones.** The stale `/home/eaguiar2015/bestiejob` clone is no longer referenced by cron but still exists.
5. **Keep the Canada geo-filter hard.** US/other-country creep is the top quality risk.

---

## 9. Other worktrees checked

| Worktree | State |
|---|---|
| `bestiejobs` (v1) | clean at `1d9354ab9e2`; session busy |
| `bestiejobs-v2` | finished; findings at `updates/2026-11-14-sn-sf-developer-jobs-patterns-and-methodology.md`; its 15 rows were merged to main (`11dde88`) |
| `swarmmethodquality` v1/v4 | commits present (README collision audit; swarm performance analysis) |
| `swarmmethodquality` v2/v3 | clean |
| `spice-hyena` / `dutiful-chicken` | unrelated review branches |
