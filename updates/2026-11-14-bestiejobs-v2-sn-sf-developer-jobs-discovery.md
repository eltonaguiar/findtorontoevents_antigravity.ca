# ServiceNow & Salesforce Developer Job Discovery — Final Findings
**Worktree:** `bestiejobs-v2` · **Date:** 2026-11-14 · **Author:** Kilo · **Target board:** BESTIEJOB

---

## 1. Executive summary

- Analyzed the live BESTIEJOB dataset (`jobs.json`, 5,376 postings) for ServiceNow (SN) and
  Salesforce (SF) **developer** roles in Toronto/GTA/Ontario/Canada/Remote-Canada.
- Cross-checked market patterns with **SubQ** (`subq-snap-1.2`) via the Decisions API
  (`POST /v1/systemone`) — SubQ keys in `dbpasses.txt` are live (free + paid).
- Ran a **3-agent discovery swarm** (ATS boards / LinkedIn guest / partner+agency) against fresh feeds.
- **Net result:** 85 mergeable candidate rows (absolute dates) + 9 partner-firm ServiceNow leads
  (undated — need date verification before merging). Workday was in outage this run.

---

## 2. Discovery run — what was executed

| Agent | Channel | Method | Result |
|---|---|---|---|
| ATS sweep | Workday CXS / Greenhouse / Lever | `wday/cxs` POST + `boards-api.greenhouse.io` | Workday in outage (all tenants 500). **NeuraFlash Greenhouse: 16 SF/Agentforce rows (Remote Canada, real dates)** |
| LinkedIn guest | `ca.linkedin.com/jobs-guest/...` | harvester.py, 23 search rounds | **69 rows passed strict classification** (Toronto-GTA 54, Ontario 14, Remote-Canada 1) |
| Partner/agency | Direct ATS + career sites + Indeed | webfetch/curl | **9 ServiceNow leads** (CGI, BDO, Cognizant, Deloitte×3, KPMG, BMO×2) — all `date relative — unverified` |

**Anti-fabrication:** every mergeable row has a real HTTP-200 URL + a real `YYYY-MM-DD` posted date
from the feed. No dates/URLs invented. Undated leads are kept separate and marked unverified.

---

## 3. Pattern findings (from live board data)

### 3.1 Role mix — the feed skews senior
- SN: 575 developer-class titles of 1,076 (53%); 55% of those are senior/lead/principal.
- SF: 711 developer-class titles of 1,069 (67%); 51% senior/lead.
- **Implication:** target junior/mid explicitly — senior roles are over-served.

### 3.2 Location mix
| Bucket | SN | SF |
|---|---|---|
| Toronto/GTA | 348 | 433 |
| Ontario | 43 | 24 |
| Canada (other) | 372 | 336 |
| Remote | 52 | 66 |
| Other/ambiguous | 239 | 192 |
| US | 22 | 18 |

Toronto/GTA + Canada ≈ 70–80% of rows. US/other creep is real (SubQ `us_creep` noul = **0.83**).
→ Keep the hard Canada geo-filter on every round.

### 3.3 Top employers (developer rows)
- **SN:** KPMG Canada (76), ServiceNow direct, Deloitte (25), CGI (22), Accenture Federal Services (21),
  Harris Computer, TCS, NewRocket, BDO, Scotiabank, Cognizant, Bell.
- **SF:** Salesforce direct (50), Canadian Cancer Society (18), Cognizant (17), NeuraFlash (17),
  Maarut (13), TCS, Epsilon, McKesson, Slalom, iA Financial, Acestack.

### 3.4 SubQ decision cross-check
| Question | Decision | Confidence |
|---|---|---|
| Best SN developer channel | **big5_consultancies** | p=0.887, conf 0.86 |
| Best SF developer channel | **product_vendor** (Salesforce direct); close 2nd specialist_partners | p=0.515 / 0.393, conf 0.39 |
| Agency noise dominating? | noul 0.41 → moderate | — |
| US/other-country creep | noul **0.83** → keep strict geo filters | — |

**Net:** ServiceNow = consultancies & banks/telecom (employer-direct). Salesforce = vendor-direct +
specialist partners (NeuraFlash/Slalom/OSF/Plative). Agency rows acceptable but should carry an
"original employer ATS" note.

---

## 4. Mergeable candidate rows (85 — absolute dates)

> These satisfy the merger's rules (real URL + absolute `YYYY-MM-DD`). They are candidates for the
> BESTIEJOB `inbox/` flow — not yet merged.

### 4.1 LinkedIn guest — 69 rows

| Posted | Role | Company | Location | URL |
|---|---|---|---|---|
| 2026-11-03 | Intermediate Technology Specialist, ServiceNow Developer | Equitable | Waterloo, ON | https://ca.linkedin.com/jobs/view/intermediate-technology-specialist-service-now-developer-at-equitable-4485018083 |
| 2026-11-04 | ServiceNow Strategic Portfolio Management (SPM) Consultant | RSM Canada | Kitchener, ON | https://ca.linkedin.com/jobs/view/servicenow-strategic-portfolio-management-spm-consultant-at-rsm-canada-4405749125 |
| 2026-11-06 | Salesforce CPQ Developer / Support Engineer | UST | Ontario | https://ca.linkedin.com/jobs/view/salesforce-cpq-developer-support-engineer-at-ust-4486258340 |
| 2026-11-07 | Développeur de solutions ServiceNow | KPMG Canada | Ottawa, ON | https://ca.linkedin.com/jobs/view/conseiller-%C3%A8re-conseiller-%C3%A8re-principal-e-d%C3%A9veloppeur-de-solutions-servicenow-at-kpmg-canada-4480381892 |
| 2026-11-07 | Consultant/Senior Consultant - ServiceNow Solution Developer | KPMG Canada | Ottawa, ON | https://ca.linkedin.com/jobs/view/consultant-senior-consultant-servicenow-solution-developer-at-kpmg-canada-4480500031 |
| 2026-11-07 | Directeur.rice - Architecte de solutions ServiceNow | KPMG Canada | Ottawa, ON | https://ca.linkedin.com/jobs/view/directeur-rice-architecte-de-solutions-servicenow-at-kpmg-canada-4480395256 |
| 2026-11-07 | Manager - ServiceNow Solution Architect | KPMG Canada | Ottawa, ON | https://ca.linkedin.com/jobs/view/manager-servicenow-solution-architect-at-kpmg-canada-4480397232 |
| 2026-11-07 | Conseiller fonctionnel ServiceNow | KPMG Canada | Ottawa, ON | https://ca.linkedin.com/jobs/view/conseiller-%C3%A8re-conseiller-%C3%A8re-principal-e-fonctionnel-le-service-now-at-kpmg-canada-4480500034 |
| 2026-11-07 | Functional Consultant / Senior Consultant – ServiceNow | KPMG Canada | Ottawa, ON | https://ca.linkedin.com/jobs/view/functional-consultant-senior-consultant-%E2%80%93-servicenow-at-kpmg-canada-4480389738 |
| 2026-11-09 | Senior Salesforce Developer | Webflow | Ontario | https://ca.linkedin.com/jobs/view/senior-salesforce-developer-at-webflow-4488879234 |
| 2026-11-09 | Salesforce Technical Lead | March Networks | Ottawa, ON | https://ca.linkedin.com/jobs/view/salesforce-technical-lead-at-march-networks-4489131103 |
| 2026-11-12 | ServiceNow Senior Developer | BDO Canada | Ottawa, ON | https://ca.linkedin.com/jobs/view/servicenow-senior-developer-at-bdo-canada-4489934361 |
| 2026-11-12 | ServiceNow Senior Developer | BDO Canada | Barrie, ON | https://ca.linkedin.com/jobs/view/servicenow-senior-developer-at-bdo-canada-4489939243 |
| 2026-11-13 | Senior Consultant - ServiceNow HRSD | Avance Consulting | Ontario | https://ca.linkedin.com/jobs/view/senior-consultant-servicenow-hrsd-at-avance-consulting-4489814875 |
| 2026-11-10 | Software Engineer (Salesforce) — CANADA REMOTE | Motorola Solutions | Greater Vancouver | https://ca.linkedin.com/jobs/view/software-engineer-salesforce-canada-remote-at-motorola-solutions-4487847136 |
| 2026-10-31 | Senior Consultant, AI – NowAssist | Deloitte | Toronto, ON | https://ca.linkedin.com/jobs/view/senior-consultant-artificial-intelligence-nowassist-at-deloitte-4460501313 |
| 2026-10-31 | Forward Deployed Engineer (Mid/Senior) | Salesforce | Toronto, ON | https://ca.linkedin.com/jobs/view/forward-deployed-engineer-fde-mid-senior-level-at-salesforce-4460136898 |
| 2026-11-01 | Senior Consultant, ServiceNow Platform (DTC) | Deloitte | Toronto, ON | https://ca.linkedin.com/jobs/view/senior-consultant-servicenow-platform-deloitte-technology-canada-dtc-platform-team-at-deloitte-4460515123 |
| 2026-11-01 | Conseiller principal, AI NowAssist | Deloitte | Toronto, ON | https://ca.linkedin.com/jobs/view/conseiller-principal-ou-conseill%C3%A8re-principale-intelligence-artificielle-now-assist-at-deloitte-4459418991 |
| 2026-11-01 | Conseiller principal, ITOM ServiceNow | Deloitte | Toronto, ON | https://ca.linkedin.com/jobs/view/conseiller-principal-ou-conseill%C3%A8re-principale-itom-servicenow-at-deloitte-4459429838 |
| 2026-11-01 | Senior Consultant, ITOM / Discovery | Deloitte | Toronto, ON | https://ca.linkedin.com/jobs/view/senior-consultant-it-operations-management-discovery-at-deloitte-4460512143 |
| 2026-11-01 | Process Lead Architect, Customer Service Management | Deloitte | Toronto, ON | https://ca.linkedin.com/jobs/view/process-lead-architect-customer-service-management-at-deloitte-4460519030 |
| 2026-11-02 | Salesforce Technical Architect — Revenue Cloud (RCA) | LTM | Toronto, ON | https://ca.linkedin.com/jobs/view/salesforce-technical-architect-with-revenue-cloud-rca-at-ltm-4484622096 |
| 2026-11-04 | Salesforce Revenue Cloud Solution Architect | Slalom | GTA | https://ca.linkedin.com/jobs/view/salesforce-revenue-cloud-solution-architect-toronto-at-slalom-4449798982 |
| 2026-11-05 | Salesforce Marketing Cloud BA / Solution Consultant | Galent | Mississauga, ON | https://ca.linkedin.com/jobs/view/salesforce-marketing-cloud-sfmc-business-analyst-solution-consultant-at-galent-4485866051 |
| 2026-11-06 | ServiceNow Administrator/Developer | CGI | Toronto, ON | https://ca.linkedin.com/jobs/view/servicenow-administrator-developer-at-cgi-4462044907 |
| 2026-11-06 | Salesforce Technical Architect — FSC/MC/Data360 | EY | Toronto, ON | https://ca.linkedin.com/jobs/view/salesforce-technical-architect-financial-services-cloud-marketing-cloud-data360-manager-at-ey-4459555582 |
| 2026-11-07 | Développeur de solutions ServiceNow | KPMG Canada | Toronto, ON | https://ca.linkedin.com/jobs/view/conseiller-%C3%A8re-conseiller-%C3%A8re-principal-e-d%C3%A9veloppeur-de-solutions-servicenow-at-kpmg-canada-4480397231 |
| 2026-11-07 | Consultant/Senior Consultant - ServiceNow Solution Developer | KPMG Canada | Toronto, ON | https://ca.linkedin.com/jobs/view/consultant-senior-consultant-servicenow-solution-developer-at-kpmg-canada-4480380944 |
| 2026-11-07 | Manager - ServiceNow Solution Architect | KPMG Canada | Toronto, ON | https://ca.linkedin.com/jobs/view/manager-servicenow-solution-architect-at-kpmg-canada-4480398115 |
| 2026-11-07 | Directeur.rice - Architecte de solutions ServiceNow | KPMG Canada | Toronto, ON | https://ca.linkedin.com/jobs/view/directeur-rice-architecte-de-solutions-servicenow-at-kpmg-canada-4480399040 |
| 2026-11-07 | Salesforce Senior Developer | IKO North America | Mississauga, ON | https://ca.linkedin.com/jobs/view/salesforce-senior-developer-at-iko-north-america-4477710726 |
| 2026-11-07 | Conseiller fonctionnel ServiceNow | KPMG Canada | Toronto, ON | https://ca.linkedin.com/jobs/view/conseiller-%C3%A8re-conseiller-%C3%A8re-principal-e-fonctionnel-le-service-now-at-kpmg-canada-4480387793 |
| 2026-11-07 | Manager, ServiceNow Technical Lead | KPMG Canada | Toronto, ON | https://ca.linkedin.com/jobs/view/manager-servicenow-technical-lead-at-kpmg-canada-4453621290 |
| 2026-11-07 | Functional Consultant / Senior Consultant – ServiceNow | KPMG Canada | Toronto, ON | https://ca.linkedin.com/jobs/view/functional-consultant-senior-consultant-%E2%80%93-servicenow-at-kpmg-canada-4480501034 |
| 2026-11-07 | Senior CRM Developer | York University | North York, ON | https://ca.linkedin.com/jobs/view/senior-crm-developer-at-york-university-4472078182 |
| 2026-11-09 | Senior Salesforce Developer | CGI | Toronto, ON | https://ca.linkedin.com/jobs/view/senior-salesforce-developer-at-cgi-4408542861 |
| 2026-11-09 | Sr. Salesforce Developer | Genesys | Toronto, ON | https://ca.linkedin.com/jobs/view/sr-salesforce-developer-at-genesys-4487960730 |
| 2026-11-09 | Salesforce Revenue Cloud Developer | Tekgence Inc | Toronto, ON | https://ca.linkedin.com/jobs/view/salesforce-revenue-cloud-developer-at-tekgence-inc-4487949008 |
| 2026-11-10 | Salesforce FSC Developer | Quantum World Technologies | Toronto, ON | https://ca.linkedin.com/jobs/view/salesforce-fsc-developer-at-quantum-world-technologies-inc-4489612151 |
| 2026-11-10 | Sr. Salesforce Developer — FSC | Sagen | Oakville, ON | https://ca.linkedin.com/jobs/view/sr-salesforce-developer-%E2%80%93-financial-services-cloud-at-sagen-4480274599 |
| 2026-11-10 | Salesforce Senior FSC Developer / Technical Lead | Apptoza Inc. | Toronto, ON | https://ca.linkedin.com/jobs/view/salesforce-senior-fsc-developer-technical-lead-at-apptoza-inc-4489489495 |
| 2026-11-10 | Principal Applied AI Architect | Salesforce | Toronto, ON | https://ca.linkedin.com/jobs/view/principal-applied-ai-architect-at-salesforce-4487978961 |
| 2026-11-10 | Salesforce Architect | Lyft | Toronto, ON | https://ca.linkedin.com/jobs/view/salesforce-architect-at-lyft-4473050209 |
| 2026-11-11 | ServiceNow Software Asset Management Developer | Cognizant | Toronto, ON | https://ca.linkedin.com/jobs/view/servicenow-software-asset-management-developer-at-cognizant-4489032943 |
| 2026-11-11 | Senior Consultant - ServiceNow HRSD | Infosys | Mississauga, ON | https://ca.linkedin.com/jobs/view/senior-consultant-servicenow-hrsd-at-infosys-4488259704 |
| 2026-11-11 | Salesforce Developer (360) | Rang Technologies | Mississauga, ON | https://ca.linkedin.com/jobs/view/salesforce-developer-salesforce-360-at-rang-technologies-inc-4490021104 |
| 2026-11-11 | Lead Solution Engineer, ECS Public Sector | Salesforce | Toronto, ON | https://ca.linkedin.com/jobs/view/lead-solution-engineer-ecs-public-sector-at-salesforce-4482014686 |
| 2026-11-11 | ServiceNow Implementation Architect | Avanciers Inc. | Toronto, ON | https://ca.linkedin.com/jobs/view/servicenow-implementation-architect-at-avanciers-inc-4488236748 |
| 2026-11-11 | Senior Salesforce Marketing Cloud Engineer | 407 ETR | Woodbridge, ON | https://ca.linkedin.com/jobs/view/senior-salesforce-marketing-cloud-engineer-at-407-etr-4489031805 |
| 2026-11-12 | ServiceNow Senior Developer | BDO Canada | Toronto, ON | https://ca.linkedin.com/jobs/view/servicenow-senior-developer-at-bdo-canada-4489928639 |
| 2026-11-12 | ServiceNow Senior Developer | BDO Canada | Markham, ON | https://ca.linkedin.com/jobs/view/servicenow-senior-developer-at-bdo-canada-4489936310 |
| 2026-11-12 | ServiceNow Senior Developer | BDO Canada | Oakville, ON | https://ca.linkedin.com/jobs/view/servicenow-senior-developer-at-bdo-canada-4489940190 |
| 2026-11-12 | ServiceNow Senior Technical Consultant | Cognizant | Toronto, ON | https://ca.linkedin.com/jobs/view/servicenow-senior-technical-consultant-at-cognizant-4481180659 |
| 2026-11-12 | ServiceNow Technical Consultant | Cognizant | Toronto, ON | https://ca.linkedin.com/jobs/view/servicenow-technical-consultant-at-cognizant-4481192199 |
| 2026-11-12 | ServiceNow Developer | Swoon | Toronto, ON | https://ca.linkedin.com/jobs/view/servicenow-developer-at-swoon-4490348678 |
| 2026-11-12 | Salesforce Developer | OSI Digital | Toronto, ON | https://ca.linkedin.com/jobs/view/salesforce-developer-at-osi-digital-4490093184 |
| 2026-11-12 | Salesforce Developer | Cognizant | Toronto, ON | https://ca.linkedin.com/jobs/view/salesforce-developer-at-cognizant-4489273359 |
| 2026-11-12 | Salesforce OmniStudio Developer | Galent | Toronto, ON | https://ca.linkedin.com/jobs/view/salesforce-omnistudio-developer-at-galent-4488534223 |
| 2026-11-12 | Technical Architect Director — PubSec MuleSoft Canada | Salesforce | Toronto, ON | https://ca.linkedin.com/jobs/view/technical-architect-director-pubsec-mulesoft-canada-at-salesforce-4473930835 |
| 2026-11-12 | Sr. Cloud Consultant — Salesforce | Mphasis | Toronto, ON | https://ca.linkedin.com/jobs/view/sr-cloud-consultant-salesforce-at-mphasis-4488567972 |
| 2026-11-12 | Salesforce Technical Architect Revenue Cloud CPQ (RCA) | Smart IT Frame LLC | Toronto, ON | https://ca.linkedin.com/jobs/view/salesforce-technical-architect-revenue-cloud-cpq-rca-at-smart-it-frame-llc-4486765411 |
| 2026-11-12 | ServiceNow Technical Lead | CAAT Pension Plan | Toronto, ON | https://ca.linkedin.com/jobs/view/servicenow-technical-lead-at-caat-pension-plan-4481155245 |
| 2026-11-12 | Senior/Lead Salesforce Marketing Cloud Engineer | Diligente Technologies | Mississauga, ON | https://ca.linkedin.com/jobs/view/senior-lead-salesforce-marketing-cloud-engineer-at-diligente-technologies-4477699547 |
| 2026-11-13 | Senior Salesforce Developer | Zodiac Solutions | Toronto, ON | https://ca.linkedin.com/jobs/view/senior-salesforce-developer-at-zodiac-solutions-inc-4488960373 |
| 2026-11-13 | Solution Architect — Healthcare/LS or FS | Salesforce | Toronto, ON | https://ca.linkedin.com/jobs/view/solution-architect-healthcare-life-sciences-or-financial-services-at-salesforce-4457037698 |
| 2026-11-13 | Salesforce Technical Architect — Revenue Cloud Advanced RCA | Smart IT Frame LLC | Toronto, ON | https://ca.linkedin.com/jobs/view/salesforce-technical-architect-strong-in-revenue-cloud-advanced-rca-at-smart-it-frame-llc-4489587262 |
| 2026-11-13 | ServiceNow Architect / Solution Architect | Hire'in Solutions | Toronto, ON | https://ca.linkedin.com/jobs/view/servicenow-architect-servicenow-solution-architect-at-hire-in-solutions-4489582503 |
| 2026-11-13 | Salesforce Marketing Cloud Developer | McKesson | Mississauga, ON | https://ca.linkedin.com/jobs/view/salesforce-marketing-cloud-developer-at-mckesson-4428388178 |

### 4.2 NeuraFlash (Greenhouse) — 16 rows, Remote Canada (AB/BC/ON)

| Posted | Role | Company | Location | URL |
|---|---|---|---|---|
| 2026-10-27 | Forward Deployed Engineer, AI & Agentforce | NeuraFlash | Remote Canada | https://job-boards.greenhouse.io/neuraflash/jobs/6225939004 |
| 2026-10-27 | Functional Lead, AI & Agentforce Delivery | NeuraFlash | Remote Canada | https://job-boards.greenhouse.io/neuraflash/jobs/6228522004 |
| 2026-10-27 | Health Cloud Solution Architect | NeuraFlash | Remote Canada | https://job-boards.greenhouse.io/neuraflash/jobs/6190286004 |
| 2026-11-09 | Marketing Cloud Next Solution Architect | NeuraFlash | Remote Canada | https://job-boards.greenhouse.io/neuraflash/jobs/6253608004 |
| 2026-10-27 | Salesforce Engagement Manager | NeuraFlash | Remote Canada | https://job-boards.greenhouse.io/neuraflash/jobs/6220891004 |
| 2026-10-27 | Salesforce Experience Architect, AI & Agentforce | NeuraFlash | Remote Canada | https://job-boards.greenhouse.io/neuraflash/jobs/5764374004 |
| 2026-10-27 | Salesforce Manager, AI & Agentforce Delivery | NeuraFlash | Remote Canada | https://job-boards.greenhouse.io/neuraflash/jobs/6206506004 |
| 2026-10-27 | Salesforce Project Manager | NeuraFlash | Remote Canada | https://job-boards.greenhouse.io/neuraflash/jobs/6220750004 |
| 2026-10-27 | Salesforce Solution Architect, Field Service | NeuraFlash | Remote Canada | https://job-boards.greenhouse.io/neuraflash/jobs/6011721004 |
| 2026-10-27 | Salesforce Solution Architect, Revenue Cloud | NeuraFlash | Remote Canada | https://job-boards.greenhouse.io/neuraflash/jobs/6222627004 |
| 2026-10-27 | Salesforce Solution Architect, Service Cloud | NeuraFlash | Remote Canada | https://job-boards.greenhouse.io/neuraflash/jobs/5730028004 |
| 2026-10-27 | Salesforce Solution Engineer, RCA & RCB | NeuraFlash | Remote Canada | https://job-boards.greenhouse.io/neuraflash/jobs/6015378004 |
| 2026-10-27 | Salesforce Technical Architect | NeuraFlash | Remote Canada | https://job-boards.greenhouse.io/neuraflash/jobs/6222640004 |
| 2026-10-27 | Salesforce Technical Architect, AI & Agentforce | NeuraFlash | Remote Canada | https://job-boards.greenhouse.io/neuraflash/jobs/6218548004 |
| 2026-11-11 | Solution Architect, Salesforce Voice | NeuraFlash | Remote Canada | https://job-boards.greenhouse.io/neuraflash/jobs/5993680004 |
| 2026-10-27 | Sr. Developer, AI & Agentforce | NeuraFlash | Remote Canada | https://job-boards.greenhouse.io/neuraflash/jobs/6231605004 |

---

## 5. Leads requiring date verification (not yet mergeable) — 9 ServiceNow rows

| Role | Company | Location | URL | Note |
|---|---|---|---|---|
| ServiceNow Administrator/Developer | CGI | Toronto, ON (hybrid) | https://ca.indeed.com/viewjob?jk=cf4ffdcf78006e60 | $80k–130k |
| ServiceNow Senior Developer | BDO | Toronto, ON | https://ca.indeed.com/viewjob?jk=c956b22cc281049c | $84k–128k |
| ServiceNow Technical Consultant | Cognizant | Toronto, ON (hybrid) | https://ca.indeed.com/viewjob?jk=313df0ff89bf9a48 | $77.5k–91k |
| Lead Specialist, ServiceNow CMDB Solution Architect | Deloitte | Remote Toronto, ON | https://ca.indeed.com/viewjob?jk=8481424a81ab3122 | $85k–156k |
| Lead Specialist, ServiceNow GRC Solution Architect | Deloitte | Remote Toronto, ON | https://ca.indeed.com/viewjob?jk=036a5fbaa761375b | $85k–156k |
| Senior Consultant, ServiceNow Platform (DTC) | Deloitte | Toronto, ON (hybrid) | https://ca.indeed.com/viewjob?jk=159ae9b051d0cc56 | $69k–114k |
| Manager, ServiceNow Technical Lead | KPMG | Toronto, ON | https://ca.indeed.com/viewjob?jk=8c270c710f6166a5 | $101k–135k |
| ServiceNow Technology Lifecycle Analyst | BMO | Toronto, ON | https://ca.indeed.com/viewjob?jk=05f036360fb6560a | $55.5k–120k |
| ServiceNow CMDB Administrator | BMO | Toronto, ON | https://ca.indeed.com/viewjob?jk=30440f8a6ac0a835 | $55.5k–120k |

---

## 6. Recommendations / next steps

1. **Feed the 85 mergeable rows** through the BESTIEJOB `inbox/` flow:
   `python3 tools/jobs_merge_inbox.py --max-per-table 500` (in the `bestiejob` clone).
2. **Verify the 9 partner leads' dates** (fetch each ATS page for `postedOn`/`startDate`) so they
   can enter the board.
3. **Re-run Workday CXS** when the outage clears (TD/Manulife/BMO/CIBC/Sun Life) — the largest
   employer-direct gap this run.
4. **Prioritize by channel:** ServiceNow → Big-5 consultancies + banks/telecom; Salesforce →
   vendor-direct + specialist partners (NeuraFlash/Slalom/OSF/Plative).
5. **Keep the hard Canada geo-filter** (`us_creep` noul 0.83) and target junior/mid roles, which are
   under-served relative to senior titles.
