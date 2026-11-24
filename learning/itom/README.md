# ServiceNow ITOM Learning

**Agent:** Kilo
**Date:** 2026-11-19
**Source Repo:** https://github.com/eltonaguiar/ServiceNowLearning_ITOM
**Live Site:** https://eltonaguiar.github.io/ServiceNowLearning_ITOM/

---

## Purpose

This repository contains comprehensive learning guides for ServiceNow IT Operations Management (ITOM). All content is researched from official ServiceNow documentation, certification blueprints, and training courses.

ITOM combines **Discovery**, **Event Management**, **Service Mapping**, **Orchestration**, **Cloud Management**, and **Now Assist for ITOM** (Gen AI-powered AIOps) to give IT operations teams a unified view of infrastructure health, automated incident response, and proactive issue resolution.

---

## Repository Structure

```
ServiceNowLearning_ITOM/
├── README.md                          # This file
├── index.md                           # GitHub Pages landing page
├── _config.yml                        # Jekyll configuration
├── docs/modules/
│   ├── itom/
│   │   └── itom-guide.md              # ITOM suite overview
│   ├── discovery/
│   │   └── discovery-guide.md         # Discovery module deep dive
│   ├── eventmanagement/
│   │   └── eventmanagement-guide.md   # Event Management deep dive
│   ├── servicemapping/
│   │   └── servicemapping-guide.md    # Service Mapping deep dive
│   ├── orchestration/
│   │   └── orchestration-guide.md     # Orchestration deep dive
│   ├── cloudmanagement/
│   │   └── cloudmanagement-guide.md   # Cloud Management deep dive
│   ├── midserver/
│   │   └── midserver-guide.md         # MID Server deep dive
│   ├── cmdb/
│   │   └── cmdb-guide.md              # CMDB (ITOM perspective)
│   └── nowassist-itom/
│       └── nowassist-guide.md         # Now Assist for ITOM deep dive
├── getting-started/
│   ├── foundation.md                  # 5-step rapid learning methodology
│   └── itom.md                        # Your first hour with ITOM
├── labs/
│   ├── discovery-plan/                # Discovery Plan lab
│   └── event-correlation/             # Event Correlation lab
├── data/
│   └── modules.json                   # Machine-readable module metadata
└── meta/
    └── AGENT.md                       # Agent instructions
```

---

## The 5-Step Rapid Learning Loop

Every module guide follows the same repeatable process:

| Step | Name | What You Do | Output |
|------|------|-------------|--------|
| 1 | **Orient** | Read the ELI5 glossary + breadcrumbs for the module | Mental map of where things are |
| 2 | **Configure** | Turn the module on (if needed). Set roles. Create a test record. | Working instance with module active |
| 3 | **Build** | Do the lab: create a record, run a flow, call an integration | Tangible artifact (record, flow, integration) |
| 4 | **Verify** | Confirm the artifact works end-to-end | Evidence it works |
| 5 | **Teach Back** | Write a summary using the concept summary template | You can explain it simply |

**Time target:** Complete Steps 1–5 in under 2 hours per module.

---

## Module Quick Reference

| Module | Primary Table | Key Tables | Key Roles |
|--------|-------------|------------|-----------|
| **Discovery** | `cmdb_ci` | `discovery_schedule`, `ecc_queue`, `sys_mid_server`, `discovery_result` | `sn_itom.admin`, `sn_itom.user`, `itil` |
| **Event Management** | `em_event` | `em_alert`, `em_metric`, `incident` | `sn_itom.admin`, `sn_itom.user`, `itil` |
| **Service Mapping** | `cmdb_rel_ci` | `cmdb_ci_service`, `cmdb_ci_appl`, `sa_service` | `sn_itom.admin`, `sn_itom.user`, `itil` |
| **Orchestration** | `wf_workflow` | `wf_activity`, `sys_hub_flow`, `orchestration_activity` | `sn_itom.admin`, `sn_itom.orchestration`, `itil` |
| **Cloud Management** | `cmdb_ci_cloud` | `cm_gcp_instance`, `cm_aws_instance`, `cloud_account` | `sn_itom.admin`, `sn_itom.cloud`, `itil` |
| **MID Server** | `sys_mid_server` | `ecc_queue`, `sys_credentials`, `sys_user_group` | `sn_itom.mid_server`, `sn_itom.admin`, `itil` |
| **CMDB** | `cmdb_ci` | `cmdb_rel_ci`, `cmdb_ci_service`, `cmdb_ci_appl` | `itil`, `admin`, `cmdb_admin` |
| **Now Assist for ITOM** | `em_alert` | `incident`, `em_event`, `now_assist_analysis` | `sn_itom.now_assist`, `sn_itom.admin`, `itil` |

---

## Certification Alignment

This repository maps to four official ServiceNow ITOM certifications:

| Certification | Knowledge Base | Domains | Exam Weights |
|---------------|----------------|---------|--------------|
| CIS-Discovery | KB0011545 | Discovery Configuration (35%), Discovery Pattern Design (35%), CMDB (15%), Other (15%) | [Blueprint](https://www.servicenow.com/training-certification/certifications/cis-discovery.html) |
| CIS-Event Management | KB0011604 | Event Configuration and Use (27%), Alerts and Tasks (30%), Other (43%) | [Blueprint](https://www.servicenow.com/training-certification/certifications/cis-event-management.html) |
| CIS-Service Mapping | KB0011546 | Service Mapping Design (35%), Service Mapping Implementation (35%), Service Mapping Administration (15%), Other (15%) | [Blueprint](https://www.servicenow.com/training-certification/certifications/cis-service-mapping.html) |
| CIS-Cloud Management | KB0011547 | Cloud Account Setup (25%), Cloud Resource Discovery (35%), Cloud Operations (25%), Other (15%) | [Blueprint](https://www.servicenow.com/training-certification/certifications/cis-cloud-management.html) |

---

## How to Use This Repo

1. **New to ServiceNow?** Start with `getting-started/foundation.md` (ELI5 glossary + 5-step loop)
2. **Learning a specific module?** Pick a module from `docs/modules/`, follow the 5-step loop
3. **Building an integration?** Start at `labs/event-correlation/` or `labs/discovery-plan/`
4. **Need a quick reference?** Use the module quick reference table above and the breadcrumbs in each guide
5. **Stuck?** Check the Common Mistakes section in each module guide first

---

## Core Principles

1. **No configuration without a purpose.** Every field you touch must map to a business need.
2. **Evidence over memory.** If you can't show it in a screenshot or list view, you haven't learned it.
3. **Break things safely.** Use a developer instance. Never practice on production.
4. **Certifications are a side effect, not the goal.** CIS comes from doing, not memorizing.

---

## GitHub Pages

This repository is deployed to GitHub Pages via GitHub Actions. The site is automatically built and deployed on every push to the `main` branch.

**Live site:** `https://eltonaguiar.github.io/ServiceNowLearning_ITOM/`

### Workflow

The `.github/workflows/pages.yml` workflow:
1. Checks out the repository
2. Builds the site (if needed)
3. Deploys to GitHub Pages

---

## Scripts

| Script | Purpose |
|--------|---------|
| (none yet) | Placeholder for future helper scripts |

---

## Data

| File | Purpose |
|------|---------|
| `data/modules.json` | Machine-readable metadata for all 8 ITOM modules including tables, fields, roles, breadcrumbs, OOB features, integrations, quizzes |

---

## Related Repositories

- [ServiceNow_Learning_TSOM-_CSM_FSM_SalesCRM_HAM_ITSM](https://github.com/eltonaguiar/ServiceNow_Learning_TSOM-_CSM_FSM_SalesCRM_HAM_ITSM) — Broad ServiceNow module guides (TSOM, CSM, FSM, HAM, ITSM, Discovery)
- [ServiceNow_Learning](https://github.com/eltonaguiar/ServiceNow_Learning) — Foundational ServiceNow learning methodology
- [ServiceNow_Learning_SAM](https://github.com/eltonaguiar/ServiceNow_Learning_SAM) — Software Asset Management track

---

*Generated by Kilo on 2026-11-19. Part of the ServiceNowLearning_ITOM repository at github.com/eltonaguiar/ServiceNowLearning_ITOM.*