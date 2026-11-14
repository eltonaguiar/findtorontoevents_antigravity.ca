# ServiceNow & Salesforce Developer Job Discovery — Final Wrap-Up
**Worktree:** `bestiejobs-v2` · **Date:** 2026-11-14 · **Author:** Kilo · **Target:** BESTIEJOB board

This is the consolidated close-out for the SN/SF developer job-discovery run. It records the key
insights, what was actioned/merged, and the remaining open items.

---

## 1. Key insights (from live board + SubQ decisions)

1. **ServiceNow roles skew senior.** 575 dev-class titles of 1,076 SN rows; 55% are
   senior/lead/principal. Target junior/mid explicitly.
2. **Salesforce also skews senior but has a bigger dev share.** 711 dev-class of 1,069 SF rows (67%);
   51% senior/lead.
3. **Toronto/GTA + Canada = the core** (~70–80% of rows). US/other-country creep is real:
   SubQ `us_creep` noul = **0.83** → keep hard geo-filters.
4. **ServiceNow channel = Big-5 consultancies + banks/telecom** (SubQ: `big5_consultancies`
   p=0.887, conf 0.86). Top employers: KPMG Canada, Deloitte, CGI, Accenture FS, BMO, Scotiabank.
5. **Salesforce channel = vendor-direct + specialist partners** (Salesforce direct, NeuraFlash,
   Slalom, OSF, Plative). Agency volume is moderate (noul 0.41), not dominant.
6. **Workday is a high-yield employer-direct channel** for the banks that use it (TD/Manulife/BMO/
   CIBC/Sun Life). Scotiabank and RBC do NOT use Workday (see §4).

---

## 2. What was actioned

| Item | Result |
|---|---|
| Inbox submission | 92 verified rows → `bestiejob/inbox/kilo-bestiejobs-v2--2026-11-14--v1.md` |
| Merge | +4 net-new rows on BESTIEJOB main (commit `11dde88`); 88 dup skips; README 6,892 |
| Pre-push guards | `check_readme_sort` OK; `readme_job_row_guard` PASS, 0 net loss |
| README repair | split 3 glued rows on line 1234 (pre-existing corruption) |
| Reports on findtorontoevents main | patterns-methodology (`a3adf286b34`) + discovery (`c91b2c497d7`) |

---

## 3. Subagent deployment (this wrap-up run)

| Subagent | Task | Outcome |
|---|---|---|
| ATS scrape (earlier) | Workday/Greenhouse/Lever | NeuraFlash 16 rows; Workday outage (then cleared) |
| LinkedIn guest | 23 search rounds | 69 rows passed strict classification |
| Partner/agency | Direct ATS + Indeed | 9 ServiceNow leads (subsequently verified live) |
| Date verification | 9 partner leads | 2 verified (BMO, 2026-11-12); 7 unverified |
| Workday re-probe | Bank tenants | TD/Manulife/BMO/CIBC/SunLife 200 → 7 genuine rows |
| **7-lead re-verify** | Alternate sources | All 7 confirmed live via LinkedIn; dates remain relative/unverified |
| **Scotiabank/RBC** | Workday site-ID recovery | Neither uses Workday → Scotiabank=SuccessFactors, RBC=Phenom; 0 rows |

---

## 4. Findings from post-run subagents

### 4.1 The 7 partner-firm ServiceNow leads — confirmed live, dates unverified
All 7 (CGI, BDO, Cognizant, Deloitte CMDB, Deloitte GRC, Deloitte DTC, KPMG) were re-confirmed as
**live, matching, Canada-relevant roles** on LinkedIn (HTTP 200). LinkedIn exposes only relative age, so
exact posted dates remain unverified → they cannot enter the board without violating the
anti-fabrication rule (real absolute date required).

- **5 of the 7 are already on the board** (same jobs were in the 92-row merged submission):
  CGI 4462044907, BDO 4489928639, Cognizant 4481192199, Deloitte DTC 4460515123, KPMG 4453621290.
- **Only 2 are net-new-but-undated** (Deloitte *Remote* CMDB + GRC Solution Architect leads):
  - https://ca.linkedin.com/jobs/view/lead-specialist-servicenow-cmdb-solution-architect-deloitte-global-technology-at-deloitte-4474558762
  - https://ca.linkedin.com/jobs/view/lead-specialist-servicenow-grc-solution-architect-deloitte-global-technology-at-deloitte-4474570325
- These 2 are good fresh candidates for a future round **once an absolute date is recovered**
  (e.g. from Deloitte's Workday when careers.deloitte.ca is back from maintenance).

### 4.2 Scotiabank & RBC — no Workday board exists
- **Scotiabank** runs SAP **SuccessFactors** (`jobs.scotiabank.com`). The Workday `scotiabank` tenant is
  not live (CXS 422 identical to a bogus-tenant control; landing 500). SuccessFactors search is a JS SPA
  with no public dated JSON; server-rendered Technology pages list Toronto/GTA roles but no dates.
- **RBC** runs **Phenom People** (`jobs.rbc.com`, tenant `RBCAA0088`). The Workday `rbc` tenant is
  recognized but resolves no posting site (CXS 404 S21 for all slugs). Phenom public API requires auth
  (`Tenant not identified`).
- **Conclusion:** neither bank can be harvested via Workday. Future rounds should target:
  - Scotiabank SuccessFactors (no dates today; may need per-posting page fetch or an SPA API discovery),
  - RBC Phenom (auth required; may need the Phenom `embed`/search API or page-level date extraction).

---

## 5. Remaining items (open)

- [ ] **2 Deloitte Remote CMDB/GRC leads** — recover an absolute date (Deloitte Workday, once
      careers.deloitte.ca exits maintenance) so they can be merged.
- [ ] **Scotiabank SuccessFactors** dated harvest (SPA API discovery or per-posting date fetch).
- [ ] **RBC Phenom** dated harvest (auth'd search API or page-level date extraction).
- [ ] **Quebec/QC + non-GTA Canadian cities** pass (excluded from allowed buckets this run).
- [ ] **Junior/mid SN/SF developer roles** — a dedicated junior-targeted round (under-served).
- [ ] **SubQ as a standing classification voter** in the dual-AI consensus loop (validated via
      `POST /v1/systemone`; `subq-snap-1.2`, $0.04/1M input tokens, output free).

---

## 6. Close-out note

All harvest, classification, merge, verification, and reporting tasks are complete. The board's remote
`main` tracks the merged rows (`11dde88`) and this repo's remote `main` tracks the pattern, discovery,
and wrap-up reports. The remaining items above are concrete, well-scoped follow-ups for future rounds —
none block the current deliverable.
