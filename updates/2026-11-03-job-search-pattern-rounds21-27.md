# Job Search — Pattern-Driven Rounds 21-27 (2026-11-03)

**Date:** 2026-11-03T04:12:43Z
**Follows:** `updates/2026-11-03-job-search-rounds20-aggregate.md` (624 unique jobs)

## Why these rounds

Title-token mining over the 624-job set surfaced six under-harvested signals:

| Signal | Evidence from Rounds 0-20 |
|---|---|
| ServiceNow modules | ITOM 4, GRC 1, IRM 1, Discovery 2 titles |
| Salesforce modules | Marketing Cloud 6, MuleSoft 5, CPQ 3 titles |
| Bilingual (French) | only ~2% of titles; Montreal had 36 core jobs |
| Seniority | Lead/Principal/Architect 75 vs Senior 43 |
| Sector | Scotiabank, Bell, Interac, Purolator present but not swept |
| Boutiques | Mindlance, OnX, Alimentiv, acroynon, BULL-IT all posting |

Unigrams confirmed the shape: `salesforce 130`, `servicenow 75`, `developer 55`, `architect 50`, `senior 43`, `cloud 28`.
Bigrams confirmed the demand: `salesforce developer 24`, `servicenow developer 14`, `solution architect 11`, `data cloud 8`.

## Rounds executed

| Round | Focus | Queries × pages | Raw rows |
|---|---|---|---|
| 21 | SN modules — ITOM, GRC, IRM, HRSD, CSDM, Flow Designer, IntegrationHub, Virtual Agent | 14 × 2 | 260 |
| 22 | SF modules — LWC, CPQ, Experience Cloud, MuleSoft, Marketing Cloud, Sales Cloud, Service Cloud | 14 × 2 | 280 |
| 23 | Bilingual French — développeur / administrateur / conseiller / bilingue | 12 × 2 | 210 |
| 24 | Senior tier — Senior / Lead / Principal / Technical Architect / Solution Architect | 14 × 2 | 230 |
| 25 | Banks, telcos, insurers — CIBC, BMO, RBC, TD, Scotiabank, Bell, Rogers, Telus, Manulife, Sun Life | 20 × 2 | 360 |
| 26 | Public sector — Ontario gov, City of Toronto, TTC, Metrolinx, OPG, Hydro One, UHN, SickKids | 16 × 2 | 300 |
| 27 | Boutiques + staffing — Mindlance, OnX, Alimentiv, acroynon, BULL-IT, Alldus, Chapman Tate, Zaelab, Benevity, McKesson, Co-operators, Ateko | 20 × 2 | 350 |
| | **Total** | **110 × 2** | **1,990** |

## Result

- **New raw rows:** 1,990
- **New unique jobs added** (URL dedupe against prior 624): **60**
- **Total unique jobs:** 684
- ServiceNow-titled: 287 · Salesforce-titled: 360 · GTA: 363

The 97% dedupe rate is expected and healthy — it confirms Rounds 0-20 already saturated the GTA/remote surface for these exact platforms. The 60 genuinely new postings came almost entirely from Rounds 26 (public sector) and 27 (boutiques), which are the two areas Rounds 0-20 only touched indirectly.

## Honest caveats

1. **No JD bodies.** LinkedIn guest cards expose title/company/location/posted/url only. Module and cert keywords therefore come from *titles*, not full descriptions — module counts are a floor, not a ceiling.
2. **No workplace-type field.** "Remote" is inferred from the query keyword plus a country/province-level location. Never asserted.
3. **French titles ≠ bilingual workplace.** Round 23 surfaces French-language postings; it does not verify the role requires French.
4. **URL dedupe only.** The same posting under multiple LinkedIn slugs will appear more than once.

## Deliverables

- `job_search_pattern_rounds_2026-11-03T041243Z.json` — merged payload, 684 jobs
- `job_search_pattern_report_2026-11-03T041243Z.md` — top-freshest summary
- `.agents/skills/job-hunting/SKILL.md` — reusable harvester + pattern-mining skill (new)

## Reusable tooling

`/tmp/jobs/harvest_lib.py` exposes `harvest(queries, location, pages, sleep, tag)` returning a list of normalized rows. Documented in the skill file above with classification rules, region allow-lists, fit scoring, and round templates.

## Git

Committed only self-authored files. Branch state unchanged from Rounds 0-20 (`job-search-harvest-2026-11-03`), which remains unpushable due to an OpenRouter key in another author's earlier commit `faad94a9c0e` (`tools/ai_second_opinion.py`). No force-push used. No other authors' files staged.