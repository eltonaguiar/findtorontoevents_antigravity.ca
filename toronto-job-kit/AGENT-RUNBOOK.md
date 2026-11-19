# Toronto Platform Jobs — Agent Runbook

**Scope**: Salesforce & ServiceNow platform-development roles open to Ontario (fully remote) or located in Toronto (hybrid/on-site).  
**Date of record**: 2026-11-17, America/Toronto.  
**Goal**: keep the board fresh, verified, and deduplicated; surface new repeat hirers; never publish closed or unverifiable postings.

---

## 1. Daily heartbeat (≤20 min)

1. **Open the board** (`board.html`) and review the filter counts.
2. **Run the ATS discovery script** (`discover-ats.py`) against the registered portals (see watchlist below).
3. **Diff the results** against `job-evidence.csv`.
4. **For every new or changed posting**:
   - Visit the canonical URL (never rely on aggregator).
   - Capture: role title, company, pay, location text, arrangement, posted/closes date, requisition ID, ATS.
   - Classify: `remote_on`, `toronto`, `other`, `global`, or `excluded`.
   - Append one row to `job-evidence.csv` (or update the existing row).
5. **Re-generate board** (`python3 render-board.py`) and commit only the changed files.
6. **Update source-watchlist.md** if a new portal or repeat hirer is discovered.

---

## 2. Verification rules (MANDATORY)

- **Fully remote (Ontario)**: the posting must explicitly allow working from Ontario/Canada. “Remote within Canada” or “Toronto eligible remote” counts. “Remote” alone does NOT.
- **Toronto hybrid/on-site**: any role that lists a Toronto office requirement, even if some remote days are permitted.
- **Excluded**:
  - Indexed Salesforce job now returning “Job not found”.
  - Toronto role that claims remote but requires office visits.
- **Closed/expired ads**: keep as *employer evidence* (where to watch next). Never republish as openings.
- **Duplicate across platforms**: keep the canonical employer/ATS link only; record the aggregator URL in notes if useful.
- **Global remote**: record separately unless Ontario hiring is explicit.

---

## 3. Source watchlist (24 entries)

### Repeat-hirer portals (check daily)
1. Alldus — recruiter feed (ServiceNow & Salesforce)
2. Alimentiv (Lever) — two active requisitions observed
3. Versapay (Lever)
4. Ensiti (SmartRecruiters)
5. Traction Rec (BambooHR)
6. Acronym Solutions / Hydro One (Talentnet)
7. Cognizant (Workday) — closes Nov 30
8. TD Bank (Workday) — closes Nov 28
9. Centre for Effective Altruism (Ashby) — closes Nov 22

### Partner & event sources (weekly sweep)
10. ServiceNow Elite/Global Elite partner list
11. Pentio (Toronto Select partner)
12. Salesforce consulting partners (AppExchange)
13. Salesforce Toronto sponsor catalog (May 2026)
14. ServiceNow Toronto sponsor roster (2026)
15. Ateko careers page (routes ServiceNow → FX Innovation; Salesforce → ADP)

### Consolidators (discovery only — never proof)
16. Himalayas remote API (no-key)
17. Adzuna Canada API
18. LinkedIn (signed-out alerts)
19. Indeed (native alerts)
20. Monster (authorized access)

### Platform-specific leaderboards / copy-trader style feeds
21. OKX copy-trader leaderboard (already scraped)
22. Bitget copy-trader leaderboard (already scraped)
23. Bybit / BingX / Gate / MEXC leaderboards (already scraped)
24. Hyperliquid / Drift / dYdX / GMX on-chain trader profiles (already scraped)

---

## 4. Discovery → verification → deduplication → BestieJob inbox

1. **Discovery** — run `discover-ats.py` or manual signed-out browsing.
2. **Verification** — open canonical URL, apply the rules above, capture evidence row.
3. **Deduplication** — compare requisition ID + company + role title; keep one canonical row.
4. **BestieJob inbox** — only rows that pass verification and are still open go to the inbox feed. Closed rows stay in `job-evidence.csv` only.
5. **Recheck** — any row older than 7 days is re-verified before the next board publish.

---

## 5. Output artefacts (committed)

- `board.html` — filterable job board (single file, no external deps).
- `job-evidence.csv` — canonical source of truth (one row per verified or excluded posting).
- `source-watchlist.md` — the 24-entry list above (update when new portals appear).
- `discover-ats.py` — read-only script that walks the registered ATS feeds.
- `AGENT-RUNBOOK.md` — this file.
- `Toronto-Platform-Jobs-Kit.zip` — snapshot containing the above plus the current `board.html`.

No applications are submitted by the agent. The repository is never modified except for the artefacts listed.

---

## 6. Edge cases & notes

- **Traction Rec** and **Alimentiv** were found by reading duties, not titles — keep that pattern.
- **Ensiti** ATS map disagrees with remote flag — always confirm in writing.
- **CEA** global-remote role requires Platform Developer I; Ontario employment not explicit — treat as separate class.
- **High hourly rate** (Acronym) is contract, not FTE — record accurately.

---

**Last updated**: 2026-11-18 04:40Z by kilo (code agent)  
**Next cron run**: every 20 min until all remaining action items are complete or 12 runs elapsed.
