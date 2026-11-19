# Study plan

**Agent:** Kilo (deepseek-flash) · **Updated:** 2026-11-19 · **Docs release:** Australia

You do not need to read all of ITOM. You need one route through it, one artifact per session,
and a way to prove the artifact is right.

---

## 1. The 95-minute module loop

| Minute | Gate | Do | Produce |
|---|---|---|---|
| 0–10 | **Orient** | Open three lists; find the primary table | Three breadcrumbs + table |
| 10–30 | **Model** | Read the architecture/process page only; draw the records | One-page model |
| 30–75 | **Practise** | Run the lab; break one dependency; fix it | Working config + "what broke" |
| 75–85 | **Prove** | Inspect the real records; compare to your model | Observation sheet + gap list |
| 85–95 | **Teach** | Five sentences + one diagram, from memory | Teach-back note |

If you only have 30 minutes, do Orient + Model on one product. If you only have 15, read the
ELI5 section for that product and write down the three tables you expect to see.

---

## 2. Three-day ramp (from zero)

| Day | 90-minute block | Output | Proof |
|---|---|---|---|
| 0 (30 min) | Get a PDI; log in; run [Lab 00](../labs/LAB-00-ORIENTATION.md) | Platform map | You can reach Discovery, Event Management, and the CMDB |
| 1 | [ELI5](01-ELI5.md) + [family map](02-family-map.md) + Discovery loop | A discovery status you can read | One CI you can explain, or a documented reason discovery cannot run |
| 2 | Event Management loop + [Lab 02](../labs/LAB-02-EVENT-TO-INCIDENT.md) | One event → alert → CI → incident | The alert is bound and the incident exists |
| 3 | Service Mapping loop + one reliability product | One service map or a design | You can explain impact without the screen |

After day 3, each additional product is one 95-minute loop.

---

## 3. Four-week plan

| Week | Focus | Artifacts | Pass test |
|---|---|---|---|
| 1 | Visibility: Discovery + CMDB | Discovery status, ECC evidence, CI model | You can explain the four phases and where a failure appears |
| 2 | AIOps: Event Management + HLA | Event rule, field mapping, alert, CI binding, correlation | You can trace one alert back to its event and CI |
| 3 | Service Mapping + reliability | Service instance map, SLO or synthetic monitor design | You can explain impact and one reliability metric |
| 4 | Cloud + AI + governance | Cloud app choice, licence map, AI governance checklist | You can defend the design to an operator and an auditor |

---

## 4. Role-based tracks

### NOC operator / service desk

1. ELI5: event vs alert vs incident.
2. Event Management guide: process flow, severity, states, priority.
3. Lab 02.
4. HLA guide: how log anomalies arrive as alerts.
5. Reliability stack: SOW, SRM, Service Observability.

**You are done when:** you can take a raw event payload and explain every step to the incident.

### Discovery / CMDB admin

1. Family map and licensing.
2. Discovery guide: phases, MID Server, credentials, schedules.
3. Lab 01.
4. Roles & tables: `cmdb_ci`, `cmdb_rel_ci`, `ecc_queue`, `ip_service_affinity`.
5. Service Mapping guide: how Discovery feeds top-down mapping.

**You are done when:** you can read a failed discovery status and name the phase that failed.

### Service owner / SRE

1. Service Mapping guide: methods and entry points.
2. Reliability stack: SLOs, error budgets, observability, synthetic tests.
3. Event Management: alert priority and impact.
4. Lab 03 (or the design-only path).

**You are done when:** you can draw a service, its CIs, its entry point, and its SLO.

### Cloud operations

1. Licensing: Cloud Accelerate entitlements.
2. Cloud Accelerate guide: Catalog vs CAM vs CCG.
3. Tag Governance and Cloud Discovery Workspace.
4. Design a request → account → compliance flow on paper.

**You are done when:** you can choose the right app for a request, an ownership problem, and a
compliance problem without mixing them.

### AI / automation lead

1. AI in ITOM guide.
2. Event Management and HLA: where AI output lands.
3. Governance: AI Control Tower, model availability, data processing, opt-out.
4. Define one assisted workflow with a human approval gate.

**You are done when:** you can state what the AI may do, what it may not do, and how a human
verifies the result.

### CMDB / platform architect

1. CMDB foundation guide: tables, CSDM, identification/reconciliation, Service Graph Connectors.
2. Discovery and Service Mapping: how they write the CMDB.
3. Event Management impact: how alerts consume the CMDB.
4. Coverage map: find the gaps in your environment.

**You are done when:** you can explain which table holds a service instance, how a duplicate CI
breaks every pillar, and how a connector is governed.

### Automation / compliance lead

1. Automation and remediation guide: SOW automation, remediation, guardrails.
2. Resilience, security, and compliance guide: backups, change, certificates, audit evidence.
3. Event Management + Cloud Accelerate: where the automations live.
4. Pick one automation and define its approval and audit path.

**You are done when:** you can name a record for every automation, a guardrail for every
destructive action, and the owner of the audit evidence.

---

## 5. Session checklist

Before:

- [ ] I know which product I am studying and its primary record.
- [ ] I know whether my instance has the entitlement/plugin.
- [ ] I have a safe, non-production target.

During:

- [ ] I oriented before reading.
- [ ] I drew the model before clicking.
- [ ] I broke one thing on purpose.
- [ ] I wrote down the error and the fix.

After:

- [ ] I inspected the real records, not just the UI.
- [ ] I have a gap list.
- [ ] I can teach it in five sentences.
- [ ] I linked the official page I used.

---

## 6. What to do when you are stuck

| Symptom | Try |
|---|---|
| The menu item is missing | Check plugin, subscription, and role; search the table name |
| Discovery finds nothing | Check MID Server status, credentials, IP range, and ECC queue |
| Alerts do not appear | Check event rule source/filter, field mapping, and severity |
| The service map is empty | Check entry point, credentials, CMDB data, and mapping method |
| The lab cannot run on a PDI | Switch to the design-only path; document the missing prerequisite |
| The AI answer sounds plausible | Verify the record; if you cannot verify it, do not teach it |

---

## Official sources

- ITOM overview — <https://www.servicenow.com/docs/r/australia/it-operations-management/r_ITOMApplications.html>
- ServiceNow Developer portal (PDI) — <https://developer.servicenow.com/dev.do>
- ServiceNow University / Now Learning — <https://learning.servicenow.com/lxp>
- Discovery phases — <https://www.servicenow.com/docs/r/australia/it-operations-management/discovery/c_GetStartedWithDiscovery.html>
- Event Management process flow — <https://www.servicenow.com/docs/r/australia/it-operations-management/event-management/em-process-flow.html>
- Service Mapping methods — <https://www.servicenow.com/docs/r/australia/it-operations-management/service-mapping/choose-mapping-method.html>
