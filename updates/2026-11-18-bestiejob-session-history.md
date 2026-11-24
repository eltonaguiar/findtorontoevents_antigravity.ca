# BESTIEJOB session history (detailed)

- **Date (UTC):** 2026-11-18
- **Agent/worktree:** `kilo` @ `gx10-c9b9/bestiejobharvest` (`/home/eaguiar2015/findtorontoevents_antigravity.ca/.kilo/worktrees/bestiejobharvest`, branch `bestiejobharvest`, HEAD at start context `280e1a067c13`)
- **Target reviewed:** `eltonaguiar/BESTIEJOB` (GitHub API + `gh` CLI; no direct clone of BESTIEJOB in this worktree)

## Timeline of actions

1. **Pipeline review (BESTIEJOB)**
   - Inspected repo via GitHub: workflows, scripts, recent commits.
   - Reviewed orchestrators/serializers: `hourly-scan.yml` (hourly, `bestiejob-main-write`), `fresh-ca-scan.yml` (every 3h, freshness-first), `gap-channels-daily.yml` (every 6h), `linkedin-sweep.yml` (daily), `agency-board-scan.yml` (daily), `scrape_jobs.yml`, guards (`truth-check.yml`, `board-invariants.yml`, readme/inbox guards, pages).
   - Reviewed core scripts/methods: `daily_job_scan.mjs` (Adzuna, SmartRecruiters, Workday CXS, Greenhouse/Lever/Ashby, LinkedIn guest+Playwright fallback, RemoteOK/Jobicy/Remotive; tag/geo/age filters), `fresh_ca_scan.py` (Adzuna `created` sort, Job Bank, Eluta via shared parsers, bounded LinkedIn guest; windowed absolute dates, URL verify, URL+fingerprint dedupe, board-skip), `ats_discovery.py` (Workday/SmartRecruiters employer list endpoints; today/yesterday signals + `ats_date_resolve`), `gap_channels_scan.py` (Workday discovery/probe, Job Bank, Workable, Phenom, Oracle CE; absolute-date-only, CA geo, title-first relevance, board dedupe), `linkedin_guest_scan.py`, `agency_board_scan.py`, link liveness `tools/verify_links.py`, merge/build/parse guards.
   - Identified key behaviors: absolute source dates required (no guessing), 404/410/451 dead-link gate, normalized-URL + `title|company|city`/content fingerprint dedupe, inbox→merge→README/feed/site publish path, relevance largely title/keyword-regex driven (potential misses when SN/SF/CSA/CAD/CIS appear in body).

2. **Batched subagent methodology design**
   - Defined target profiles: ServiceNow, Salesforce, Other = ServiceNow ITSM/CMDB/ITAM Platform Analyst/Developer (Toronto/GTA, Canada-remote focus).
   - Produced 4 sourcing-angle batches with Angle/Sources/Search queries/Freshness check/Dedupe key and yield ranking:
     - Company portals (direct ATS, few tenants/batch) — highest expected yield.
     - Canadian government job boards (Job Bank + verified public-sector) — moderate/reliable.
     - Toronto/GTA cities (Toronto, Mississauga, Markham, Etobicoke) + Canada-remote geo precision — high.
     - SN/SF partners, customers, latest-conference attendees — opportunistic (<uncertain> rosters need verification).
   - Recommended cert/body-aware matching expansion (CSA/CAD/CIS, modules/skills), stronger geo/remote disambiguation, ingest-time quality gates.

3. **Peer/worktree checks**
   - Inspected `bestiejobharvest-v2/-v3/-v4` (status/log/files): all clean on trading-automation HEADs during checks; no local bestiejob commits/diffs. `v2` contained pre-existing `updates/2026-11-14-bestiejobs-*` docs only.
   - COMS roster later showed `bestiejobharvest-v2/kilo` and `bestiejobharvest-v3/kilo` registered with done/todo for pipeline review + 4-angle methodology (awaiting owner pick of sourcing angle); `bestiejobharvest-v4` unregistered.
   - Scheduled wakeups: `wku_1ec7cdc1c001QMhgElYgQ72e8D` (02:49:28Z, peer recheck) executed; `wku_1ec8c19f6001izeWF6oqgpOndB` (03:16:07Z, COMS/QA reconciliation) pending.

4. **COMS usage and diagnosis**
   - Located `COMS` (`/home/eaguiar2015/.local/bin/COMS`, broker `192.168.2.52:1883`, mosquitto active).
   - Sent job-hunt pipeline/strategy updates to `mentions/all` and `inbox/gx10-c9b9/bestiejobharvest/all` (no secrets).
   - Verified: `status/roster/listen/send` available; **no `check`/`--inbox` read verb**. Messages non-retained (retained probes timed out) → offline “what arrived while away?” unanswerable via bus; durable state must live in Git/registry/logs.

5. **GH Actions QA (`eltonaguiar/BESTIEJOB`, `main`)**
   - Enumerated latest run per workflow (200-run window). Unresolved latest failures:
     - **Job Source Truth Check** [44223129196](https://github.com/eltonaguiar/BESTIEJOB/actions/runs/44223129196) (HEAD `7851e00`, 02:25:23Z): `scanned=3 total=13616 gated=35`, `theladders.com`/`jobleads.com` in canonical artifacts; `tools/job_source_truth.py --check` exits 1.
     - **Gap channels (Workday/Phenom/Oracle/Job Bank/Workable)** [44211439366](https://github.com/eltonaguiar/BESTIEJOB/actions/runs/44211439366) (HEAD `6c21857`, 00:53:02Z): sweep/validate/merge/parse/rebuild succeeded, **Commit and push failed** (single-retry push under `bestiejob-main-write`).
     - **board invariants** [44123817042](https://github.com/eltonaguiar/BESTIEJOB/actions/runs/44123817042) (2026-11-17T16:16:12Z): audit step failed vs baseline/ratchet.
   - Healthy latest in sample: Hourly Job Scan, Fresh CA sweep, Deploy Pages, agency-board-scan, Daily LinkedIn sweep, Scrape Jobs, README job-row guard.

6. **Fix investigation (agents/others + remote main)**
   - Confirmed remote `main` HEAD `7851e0073844` (hourly scan refresh 02:18:33Z) with scan/lesson churn; no commits fixing red gates.
   - Found **unlanded** local bundle `/home/eaguiar2015/findtorontoevents_antigravity.ca/updates/2026-11-18-bestiejob-truthcheck-fix*` (buffy/Freebuff, 2026-11-18): ingest gate in merge, `config/gated_domains.txt`, `purge_gated_rows.py`, `PAYWALL_ROLES.md`; claims local-clone `truth-check exit=0` — **not pushed/validated vs current remote HEAD** (remote still gated).
   - Verdict recorded: **no fixes landed on remote `main`**; peers/design-only; gates and build direction unowned/blocked pending owner action.
   - Wrote `updates/2026-11-18-bestiejob-fix-investigation.md` and sent COMS references.

7. **Consolidation (this step)**
   - Produced session summary (less detailed), consolidated ideas, deduplicated clean ideas, and AI agent execution runbook (methodology, ATS API querying, normalized schema) under `updates/` and `ideas/bestiejob/`.

## Artifacts created/updated by this session
- `updates/2026-11-18-bestiejob-fix-investigation.md` (fix/CI/peer investigation; remote-main referenced)
- `updates/2026-11-18-bestiejob-session-history.md` (this file)
- `updates/2026-11-18-bestiejob-session-summary.md`
- `ideas/bestiejob/consolidated-ideas.md`
- `ideas/bestiejob/clean-ideas/clean-ideas.md`
- `ideas/bestiejob/agent-execution-runbook.md`
- COMS messages to `mentions/all` and `inbox/gx10-c9b9/bestiejobharvest/all` (summaries; references to investigation and session docs)

## Open items / ownership gaps
- **Owner decision needed:** which sourcing angle to build first for SN/SF Toronto/remote (v2/v3 parked). Recommended start: direct ATS/company portals + cert/body-aware matching.
- **Unowned red gates on `BESTIEJOB` main:** truth-check gated leakage/ingest enforcement, gap-channels push hardening, board-invariants baseline/ratchet remediation.
- **COMS product gap:** no offline inbox read/history command.
- **Unlanded bundle:** truth-check fix artifacts require rebase/validation on current HEAD and CI proof before merge.

## Constraints observed
- No private phone numbers/emails emitted. Sources cited only when certain from repo/observed evidence; others marked `<uncertain>` where applicable.
