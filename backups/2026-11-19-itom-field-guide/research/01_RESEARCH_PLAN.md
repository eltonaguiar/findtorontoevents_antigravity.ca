# 01 — Research plan

**Agent:** Kilo (deepseek-flash) · **Date:** 2026-11-19 · **Release:** Australia

---

## 1. Questions the research had to answer

For each product:

1. What problem does it solve, in one sentence?
2. Where does it live in the current documentation family?
3. What is the primary record/table?
4. What are the states, severities, or lifecycle values?
5. Which roles configure and operate it?
6. What are the prerequisites and entitlements?
7. How does work flow from source to outcome?
8. What are the three most common failure modes?
9. What can be proven on a PDI, and what cannot?
10. Which official page is the citation of record?

## 2. Module matrix

| Module | Official section | Key questions | Primary sources |
|---|---|---|---|
| ITOM overview | ITOM root | Family map, licensing, adoption order | ITOM overview, Visibility landing, licensing |
| Discovery | ITOM Visibility | Phases, MID Server, credentials, schedules, ECC | Exploring Discovery, schedule reference, status, ECC |
| Service Mapping | ITOM Visibility | Methods, entry points, tables, prerequisites | Service Mapping overview, method chooser, entry points |
| Event Management | ITOM AIOps | Process flow, rules, mapping, binding, grouping, priority | Event Management, process flow, rules, binding, priority |
| Health Log Analytics | ITOM AIOps | Inputs, mapping, anomaly detection, severity | HLA landing, architecture, inputs, mapping, alerts, severity |
| Reliability stack | ITOM AIOps | SRM, SLO, observability, synthetic | SRM, SLO, Service Observability, synthetic |
| Cloud Accelerate | ITOM Cloud Accelerate | Catalog vs account vs governance; CPG deprecation | CPG, CSC, CAM, CCG, Action Library |
| Agent Client Collector | ACC | Agent vs agentless, components, certificates | Exploring ACC, configuring, ACC reference |
| Metric Intelligence | Metric Intelligence | Baseline, rules, roles | Exploring and configuring Metric Intelligence |
| AI in ITOM | AI in ITOM | Deprecation, Otto, MCP, governance | Now Assist, Otto, MCP, LEAP |
| Visibility suite | ITOM Visibility | Certificates, tags, firewalls, AI topology, content | Each product landing page |

## 3. Method

1. **Enumerate** the official ITOM documentation map for the Australia release.
2. **Read** the landing, architecture/process, configuration, and reference pages for each
   product. Prefer the process/architecture page over the form page for the model.
3. **Extract** facts only: definitions, phases, table names, role names, states, entitlements,
   and caveats.
4. **Paraphrase** into original prose. Do not copy long passages. Do not store documentation
   pages in the repo.
5. **Cross-check** every table/role against a second official page where possible.
6. **Mark uncertainty** explicitly (for example, priority table underscore naming, menu labels).
7. **Design a proof** for each module: a lab or a design-only artifact.
8. **Lint** the repository and fix every error before deployment.

## 4. Source strategy

- Primary: product documentation (`www.servicenow.com/docs`).
- Secondary: Now Learning, Developer portal, Store, Now Support.
- Community: only to discover a question, never as the citation of record.
- Release pinning: use `/r/australia/` deep links where available; link the unversioned ITOM
  home for future readers.
- No bulk scraping, no mirroring, no screenshots of customer data.

## 5. Timebox and sequencing

| Phase | Work | Output |
|---|---|---|
| 1 | Enumerate the docs map and product families | Family map |
| 2 | Read and extract core Visibility | Discovery and Service Mapping guides |
| 3 | Read and extract core AIOps | Event Management, HLA, reliability guides |
| 4 | Read and extract cloud, ACC, metrics, AI | Remaining guides |
| 5 | Write labs and getting-started pages | Proof paths |
| 6 | Build the site and data files | Deployable repo |
| 7 | Lint, deploy, verify | Verification record |

## 6. Risks

| Risk | Mitigation |
|---|---|
| Release drift | Pin to Australia; add a re-check date and release note |
| Table/role names differ by instance | Mark as verify-on-instance; link the reference page |
| PDI lacks entitlements | Design-only path in every lab |
| AI features change fast | Separate the governance model from the feature list |
| Copyright | Paraphrase, cite, no mirroring |
| Cloud deprecation confusion | State the CPG/Brazil fact and point to Cloud Services Catalog |

---

**Agent:** Kilo (deepseek-flash) · **Updated:** 2026-11-19
