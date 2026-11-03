# Job Search — Rounds 0-20 Aggregate (2026-11-03)

**Date:** 2026-11-03T03:57:53Z  
**Branch:** `job-search-2026-11-03`  
**Commit:** (pending push)

## Summary

Executed 20 search rounds against the LinkedIn guest jobs API (`f_TPR=r1209600` = 14-day recency) covering:

- Toronto core (SN + SF)
- GTA suburbs (Mississauga, Markham/Vaughan/Richmond Hill, Etobicoke/North York/Scarborough, Brampton/Oakville/Burlington/Hamilton, Durham/York)
- SW Ontario, Ottawa, Montreal, Vancouver, Calgary, Edmonton
- Fully remote Canada (explicit "remote" keyword)
- Ambiguous Canada (province-level or blank location)
- Cert-gated queries (CSA, CAD, CIS-*, PD1, JS1, Platform App Builder)
- ServiceNow/Salesforce partner consultancies (Deloitte, Accenture, CGI, KPMG, EY, PwC, IBM, Cognizant, Infosys, TCS, Wipro, HCL, Capgemini, DXC, Slalom, Traction, CloudKettle, etc.)
- IT contracting / staffing agencies (Robert Half, Randstad, TEKsystems, Modis/Akkodis, Hays, Procom, Eagle, S.i. Systems, Ian Martin, Experis, Talentify, Altis, BeachHead, Compugen, etc.)
- Banks + telcos + insurers (CIBC, BMO, TD, RBC, Scotiabank, Bell, Rogers, Telus, Manulife, Sun Life, Canada Life, Metrolinx, OLG)
- Public sector / hospitals / utilities (Ontario gov, City of Toronto, TTC, OPG, Hydro One, UHN, SickKids, TDSB)

**Raw rows harvested:** 4,549 (18 round files + prior 259)  
**Unique jobs after URL dedupe:** **624**

## Classification (title-based only)

| Bucket | Count |
|--------|-------|
| ServiceNow (title match) | 89 |
| Salesforce (title match) | 172 |
| Adjacent / unspecialised | 363 |
| GTA | 130 |
| Remote-likely (inferred) | 37 |
| Posted today (2026-11-03) | 1 |
| Posted last 7 days | 157 |

**Accuracy note.** LinkedIn's public guest endpoint returns no workplace-type field, so "remote" is *inferred* from the search keyword plus a country/province-level location — it is never asserted. All dates and URLs are verbatim from the posting card.

## Deliverables

- `job_search_rounds20_2026-11-03T035753Z.json` — full payload (624 jobs, stats, metadata)
- `job_search_report_rounds20_2026-11-03T035753Z.md` — human-readable report with GTA-SN, GTA-SF, Remote-likely, and province-level sections
- `job_search_cert_keyword_bank_2026-11-03.md` — title-signal keyword bank (weak because guest cards expose titles only, not JD bodies)

## Top 5 GTA ServiceNow (fit ≥ 4)

1. **Global ServiceNow Alliance Performance and Operations Lead, Deloitte Global Ecosystem and Alliances** — Deloitte — Toronto — 2026-11-02 — fit 5
2. **ServiceNow Developer** — Rexall Pharmacy Group Ltd. — Mississauga — 2026-11-02 — fit 4
3. **Senior Consultant, ServiceNow Platform - Deloitte Technology Canada (DTC), Platform Team** — Deloitte — Toronto — 2026-11-01 — fit 5
4. **Conseiller principal ou conseillère principale, ITOM, ServiceNow** — Deloitte — Toronto — 2026-11-01 — fit 5
5. **ServiceNow Discovery Developer** — Scotiabank — Toronto — 2026-10-31 — fit 4

## Top 5 GTA Salesforce (fit ≥ 4)

1. **Senior Salesforce Developer** — BULL TECHNICAL SERVICES LIMITED — Toronto — 2026-11-03 — fit 4
2. **Salesforce Developer** — Lightspeed Commerce — Toronto — 2026-10-28 — fit 4
3. **Salesforce Technical Architect** — Mindlance — Toronto — 2026-10-28 — fit 4
4. **Salesforce Developer** — Lightspeed Commerce — Toronto — 2026-10-28 — fit 4
5. **Salesforce Developer** — BDO Canada LLP — Toronto — 2026-10-27 — fit 4

## Git Safety

- Created branch `job-search-2026-11-03` from main
- Staged **only** the 3 new files authored in this session (prior commit 7ed21345a97)
- No other authors' modified files touched
- No force-push

## Round 20 Keyword Mining

The cert keyword bank (`job_search_cert_keyword_bank_2026-11-03.md`) is intentionally weak because the LinkedIn guest API only returns title/company/location/posted/url — no JD body. A full JD scrape would require authenticated LinkedIn sessions or ATS board crawling (Greenhouse/Ashby/Lever), which is out of scope for this harvest.

## Next Steps (user decision)

- Merge PR or cherry-pick the 3 files into main
- Optionally run authenticated ATS crawlers (Greenhouse, Ashby, Lever) for deeper JD text
- Optionally run the cert keyword bank against full JDs if authenticated access is available

---

**Files added in this commit (to be pushed):**
- `job_search_rounds20_2026-11-03T035753Z.json`
- `job_search_report_rounds20_2026-11-03T035753Z.md`
- `job_search_cert_keyword_bank_2026-11-03.md`
- `updates/2026-11-03-job-search-rounds20-aggregate.md` (this file)