# Fresh Job Scan — Today & Yesterday (2026-11-03)

**Run:** 2026-11-03T18:30Z
**Filter:** `f_TPR=r172800` (48 hours — today 2026-11-03 + yesterday 2026-11-02)
**Source:** LinkedIn guest jobs API (`/jobs-guest/jobs/api/seeMoreJobPostings/search`) + job-view JSON-LD extraction

---

## Pipeline

| Stage | Detail |
|-------|--------|
| Harvest | 26 queries × 3 pages = 78 requests → **731 raw rows** |
| Round 28 | GTA ServiceNow/Salesforce, 10 queries × 3 pages |
| Round 29 | Remote Canada ServiceNow/Salesforce, 8 queries × 3 pages |
| Round 30 | Banks / Telcos / Public sector, 8 queries × 3 pages |
| Dedupe | vs prior 684-URL corpus + intra-run URL + title/company/location |
| JD extract | 197 URLs → JSON-LD `@type: JobPosting` (description, `monthsOfExperience`, `employmentType`) |
| Scoring | Weighted resume match → apply / consider / skip |

---

## Recency Verification (IMPORTANT)

LinkedIn's `f_TPR` filter is **approximate**. Actual `datePosted` values were verified from JSON-LD:

| Posted date | Raw rows | Net-new unique |
|-------------|----------|----------------|
| 2026-11-03 (today) | 487 | **107** |
| 2026-11-02 (yesterday) | 214 | **61** |
| 2026-11-01 | 30 | 4 |
| **Total** | **731** | **172** |

**96% of raw rows were posted in the last 48h** — the filter worked as intended.

---

## Dedupe Breakdown

| Reason dropped | Count |
|----------------|-------|
| Already in prior 684-job corpus | 173 |
| Duplicate URL within this run | 382 |
| Duplicate title/company/location | 4 |
| **Net-new unique** | **172** |

The 382 intra-run duplicates come from overlapping queries (e.g. "ServiceNow Developer Toronto" and "ServiceNow Platform Developer GTA" return the same postings).

Note: an earlier pass reported "197 net-new" because the prior-684 file was not on the checked-out branch, so only the original 259-URL set was loaded. Re-run against the correct 684-URL corpus gives the accurate **172**.

---

## Net-New Results

### By category (title+company classification — never query text)

| Category | Count |
|----------|-------|
| Salesforce | 38 |
| ServiceNow | 11 |
| Adjacent (ITSM/CRM/Cloud roles) | 123 |
| **Total** | **172** |

### By region

| Region | Count |
|--------|-------|
| GTA | 105 |
| Canada-level (remote-ambiguous) | 51 |
| Ontario-other | 16 |

### Scoring buckets (172 net-new)

| Bucket | Count |
|--------|-------|
| apply (score ≥ 4) | 81 |
| consider (score 1–3) | 76 |
| skip (score ≤ 0) | 15 |

### Score distribution

```
score  8: 11      score  2: 50
score  7:  8      score  1:  9
score  6: 25      score  0:  6
score  5: 17      score -1:  3
score  4: 20      score -2:  2
score  3: 17      score -3:  4
```

---

## ServiceNow — all 11 net-new (posted today/yesterday)

| Bucket | Score | Title | Company | Region |
|--------|-------|-------|---------|--------|
| apply | 8 | Administrateur ServiceNow | Pomerleau | Other-Province |
| apply | 8 | ITSM Service Desk Manager | Poly Tech Talent | **GTA** |
| apply | 7 | ServiceNow Administrator | Pomerleau (×3 postings) | Other-Province |
| apply | 7 | ServiceNow specialist | Tata Consultancy Services | Other-Province |
| apply | 7 | ServiceNow CMDB | Tata Consultancy Services | Other-Province |
| apply | 6 | ServiceNow Specialist – CMDB / CSDM (Montreal, onsite) | AceStack | Other-Province |
| apply | 4 | ServiceNow Consultant – REMOTE | NTT DATA North America | Ontario-Other |
| apply | 4 | Sr. CRM Account Executive | ServiceNow | Other-Province |
| consider | 3 | Conseiller gestion des vulnérabilités | Desjardins | Other-Province |
| consider | 2 | Conseiller gestion des vulnérabilités | Desjardins | Other-Province |

**Observation:** GTA ServiceNow supply was thin in this 48h window — only 1 GTA ServiceNow role (ITSM Service Desk Manager, Poly Tech Talent). The bulk is Montreal/Toronto-adjacent.

---

## Salesforce — apply-tier highlights (22 roles of 38)

| Score | Title | Company | Region |
|-------|-------|---------|--------|
| 8 | Développeur systèmes – Salesforce | Co-operators Assurance | **GTA** |
| 8 | Développeur systèmes – Salesforce | Co-operators Assurance | SW-Ontario |
| 7 | Salesforce Senior Developer | IKO North America | **GTA** |
| 7 | Senior Consultant – Oracle Field Service Cloud | Infosys | **GTA** |
| 6 | Senior Salesforce Engineer | Canadian Cancer Society | **GTA** + 3 other regions |
| 6 | Salesforce Marketing Cloud (SFMC) consultant | Smart IT Frame LLC | **GTA** |
| 6 | Salesforce Marketing Cloud – SFMC, BA | Smart IT Frame LLC | **GTA** |
| 6 | Conseiller architecture technique Salesforce | Alithya | Other-Province |
| 5 | Salesforce Implementation Consultant & Platform Admin | SS&C Technologies | **GTA** |
| 5 | Solutions Architect, Salesforce Migrations (Data360) | Salesforce Partner Canada | **GTA** |
| 5 | Salesforce Release Engineer | Cognizant | **GTA** |
| 5 | Salesforce Consultant – FSC Cloud | Enterprise Solutions Inc | **GTA** |
| 5 | QA Engineer – Salesforce Marketing Cloud | Tru | **GTA** |
| 4 | Salesforce Technical Architect | LTM | **GTA** |
| 4 | Salesforce Technical Architect with Revenue Cloud (RCA) | LTM | Ontario-ProvinceLevel |

---

## GTA apply-tier, score ≥ 6 (18 roles)

Includes high-fit adjacent roles worth reviewing:

- **Interac Corp.** — Incident Management, Lead (score 8) — ITSM-aligned, Toronto
- **TEKsystems** — Controls Transformation Program Consultant (8)
- **Microsoft** — Cloud Solution Architect / Cloud + AI Platform (8)
- **Deloitte** — Manager, Data Analysis Discovery & Requirements (8)
- **Poly Tech Talent** — ITSM Service Desk Manager (8)
- **Zodiac Solutions** — Application Support Analyst – Front Office (8)
- **University Health Network** — Incident Coordinator (7) — ITSM
- **Salesforce** — Canadian Public Sector Engagement Delivery Leader (3 postings)
- **Manulife** — Project Manager – PeopleComms Tech PMO (6)
- **Softchoice** — Architecte principal solutions technologiques (6, ×2)
- **Float** — Acquisition (Sales) Operations Manager (6)
- **Co-operators** — Systems Developer – Salesforce (5, ×2)

---

## Key Insights

**1. ServiceNow GTA supply is thin this week.** Only 1 GTA ServiceNow role in 48h. The Montreal market (Pomerleau, TCS, AceStack) is where ServiceNow volume sits. Two ServiceNow Inc. postings appeared but they are sales roles (Sr. CRM Account Executive), not delivery.

**2. Salesforce GTA supply is healthy.** 27 apply-tier roles, led by Canadian Cancer Society (4 regional variants of Senior Salesforce Engineer), Smart IT Frame (SFMC ×2), Co-operators (bilingual Systems Developer), and IKO North America.

**3. Bilingual roles are ~20% of the fresh set.** Co-operators, Canadian Cancer Society, Alithya, Desjardins, Pomerleau, Schneider Electric all posted French-language titles. Resume is not bilingual → these score −2 but still landed in apply tier because certs/modules overlap dominated.

**4. Adjacent ITSM roles are a strong secondary channel.** Interac Incident Management Lead, UHN Incident Coordinator, Poly Tech ITSM Service Desk Manager — these reward the ITIL v4 + ServiceNow ITSM depth without requiring the ServiceNow title.

**5. High-volume reposting detected.** Pomerleau posted "ServiceNow Administrator" 4× (and "Administrateur ServiceNow" 1×), Salesforce posted "Canadian Public Sector Engagement Delivery Leader" 3×, Canadian Cancer Society posted Senior Salesforce Engineer 4×. These are likely single requisitions with regional variants — apply once, not four times.

---

## Caveats

1. **`f_TPR` is approximate** — 30 raw rows were posted 2026-11-01 (outside the stated 48h window). Trust the JSON-LD `datePosted`, not the filter.
2. **`years_min` regex is first-match only** — can catch "3 years of experience with REST" rather than the true requirement. Spot-check before applying.
3. **No workplace-type field** — 51 "Canada-level" rows are remote-ambiguous; JD body signals (hybrid/onsite) were parsed but are keyword-based, not authoritative.
4. **Duplicate requisitions inflate counts** — deduped by URL, not by requisition ID. Pomerleau ×5 and Cancer Society ×4 are the same roles.
5. **Recruiter/agency postings included** — Smart IT Frame, LTM, TEKsystems, Poly Tech Talent, Zodiac, SS&C are agencies; the end client is not disclosed in the card.

---

## Artifacts

- `job_search_fresh_2026-11-03T183000Z.json` — 172 net-new jobs with category/region/scoring
- `job_search_application_tracker_2026-11-03T183000Z.json` — merged tracker (80 prior + 172 fresh = 252 scored)
- `job_search_fresh_report_2026-11-03T183000Z.md` — this report

---

**Author:** Zoo
**Method:** LinkedIn guest API, 2-day recency filter, title-based classification, JSON-LD JD scoring
