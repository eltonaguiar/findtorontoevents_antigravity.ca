# ServiceNowLearning_ITOM

**A source-backed field guide to ServiceNow IT Operations Management (ITOM).**

Website: <https://eltonaguiar.github.io/ServiceNowLearning_ITOM/>

This repository teaches the ITOM product family the way the existing
[ServiceNow Learning](https://github.com/eltonaguiar/ServiceNow_Learning) and
[Module Guides](https://github.com/eltonaguiar/ServiceNow_Learning_TSOM-_CSM_FSM_SalesCRM_HAM_ITSM)
repositories teach their modules: one repeatable learning loop, a small number of official
sources, a hands-on proof, and a teach-back. It is written to be merged into the new ITOM
section of the larger guide later; see `research/05_MERGE_HANDOFF.md`.

**Agent:** Kilo (deepseek-flash) · **Updated:** 2026-11-19 · **Docs release:** Australia

---

## Start here

| Read | Why |
|---|---|
| [index.md](index.md) | The landing page and track picker |
| [docs/01-ELI5.md](docs/01-ELI5.md) | ITOM in plain English, with every term defined before it is used |
| [docs/00-methodology.md](docs/00-methodology.md) | The 95-minute loop: Orient → Model → Practise → Prove → Teach |
| [docs/02-family-map.md](docs/02-family-map.md) | Visibility, AIOps, Cloud Accelerate, ACC, AI, and how they connect |
| [labs/LAB-00-ORIENTATION.md](labs/LAB-00-ORIENTATION.md) | A zero-risk first session on your own instance |

Then pick one module, run one loop, and produce one artifact.

## What is inside

| Area | Guides |
|---|---|
| **ITOM Visibility** | [Overview](docs/modules/itom-overview/itom-overview-guide.md) · [CMDB foundation](docs/modules/cmdb/cmdb-guide.md) · [Discovery](docs/modules/discovery/discovery-guide.md) · [Service Mapping](docs/modules/service-mapping/service-mapping-guide.md) · [Visibility suite](docs/modules/visibility-suite/visibility-suite-guide.md) |
| **ITOM AIOps** | [Event Management](docs/modules/event-management/event-management-guide.md) · [Health Log Analytics](docs/modules/health-log-analytics/health-log-analytics-guide.md) · [Reliability stack](docs/modules/reliability-stack/reliability-stack-guide.md) · [Metric Intelligence](docs/modules/metric-intelligence/metric-intelligence-guide.md) |
| **ITOM Cloud Accelerate** | [Cloud Accelerate](docs/modules/cloud-accelerate/cloud-accelerate-guide.md) |
| **Agents & AI** | [Agent Client Collector](docs/modules/agent-client-collector/acc-guide.md) · [AI in ITOM](docs/modules/itom-ai/itom-ai-guide.md) |
| **Automation & assurance** | [Automation & remediation](docs/modules/automation-remediation/automation-remediation-guide.md) · [Resilience · security · compliance](docs/modules/resilience-security/resilience-security-guide.md) |
| **Reference** | [Licensing](docs/03-licensing-prerequisites.md) · [Roles & tables](docs/04-roles-tables.md) · [Common mistakes](docs/05-common-mistakes.md) · [Glossary](docs/07-glossary.md) · [Source ladder](docs/08-source-ladder.md) |
| **Labs** | [00 Orientation](labs/LAB-00-ORIENTATION.md) · [01 Discovery](labs/LAB-01-DISCOVERY.md) · [02 Event → incident](labs/LAB-02-EVENT-TO-INCIDENT.md) · [03 Service Mapping](labs/LAB-03-SERVICE-MAPPING.md) · [04 HLA](labs/LAB-04-HLA-LOG-ANOMALY.md) |

## The methodology

Every guide uses the same five gates:

| Gate | Target | Artifact | Pass test |
|---|---|---|---|
| Orient | 10 min | 3 breadcrumbs + primary table | Reach any list without searching menus |
| Model | 20 min | One page: records, states, roles, arrows | Explain it without the screen |
| Practise | 45 min | Working configuration + "what broke" note | It works, and you know why it stopped |
| Prove | 10 min | Instance observations → gap list | The instance matches your model |
| Teach | 10 min | Five sentences + one diagram | A beginner's follow-up gets a real answer |

The point is not the timebox. The point is that each session ends with an artifact and a
written gap, so the next session starts from evidence instead of rereading.

## Research protocol

This build followed an `AGENT_FOLDERFRAMEWORK`-style protocol: a charter, an isolated
research pass, a source matrix, explicit content decisions, verification, and a merge
handoff. The durable artifacts are in [`research/`](research/):

- `research/00_CHARTER.md` — scope, success criteria, non-goals
- `research/01_RESEARCH_PLAN.md` — module matrix and questions
- `research/02_SOURCE_MATRIX.md` — official URL per guide and what was used
- `research/03_CONTENT_DECISIONS.md` — release pinning, naming, corrections
- `research/04_VERIFICATION.md` — lint, links, build, deployment
- `research/05_MERGE_HANDOFF.md` — how to merge into the ITOM section

## Source policy

- Facts are paraphrased from **official ServiceNow sources only**: product documentation,
  Now Learning, the Developer portal, the Store, and Now Support.
- No documentation pages are mirrored or bulk-scraped into this repo.
- Every guide ends with an **Official sources** section containing the exact URLs read.
- The docs are release-pinned to **Australia** where a versioned URL exists. Deep links move
  between releases; the source ladder explains how to search forward.
- Anything that depends on your subscription, plugins, or instance configuration is marked
  as something to verify, not as a universal truth.

## Repository map

```
README.md                  GitHub landing page
index.md                   Published site landing page
docs/                      Methodology, ELI5, reference, module guides
labs/                      Hands-on labs with break-it-on-purpose phases
data/modules.json          Structured knowledge base for the guides
data/sources.json          Official source catalog and allowlist
research/                  Charter, plan, source matrix, decisions, verification, handoff
meta/                      Agent and changelog records
scripts/sn_lint.py         Enforces stamps, sources, links, and data integrity
assets/                    Site CSS and JS (Jekyll)
_layouts/                  Jekyll layout
.github/workflows/         Pages deployment and content checks
```

## Local checks

```bash
python3 scripts/sn_lint.py
```

The lint enforces: H1 title, agent stamp, updated date, an official-sources section with
allowlisted URLs, no unfinished markers, resolving relative links, valid module data, and
resolving navigation targets. It runs in GitHub Actions on every push.

## Official sources

- ServiceNow product documentation — <https://www.servicenow.com/docs/>
- ITOM documentation home (Australia) — <https://www.servicenow.com/docs/r/australia/it-operations-management>
- ServiceNow University / Now Learning — <https://learning.servicenow.com/lxp>
- ServiceNow Developer portal — <https://developer.servicenow.com/dev.do>
- ServiceNow Store — <https://store.servicenow.com/store>
- ServiceNow Community — <https://community.servicenow.com/>
- Now Support — <https://support.servicenow.com/now>
