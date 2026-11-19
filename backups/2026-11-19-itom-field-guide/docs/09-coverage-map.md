# Coverage map

**Agent:** Kilo (deepseek-flash) · **Updated:** 2026-11-19 · **Docs release:** Australia

This page checks the guide against the ServiceNow-specific ITOM model: three pillars and the
shared CMDB foundation. It exists so a reader can see **where each subtopic is covered** and
where the guide deliberately stops.

---

## The model used

ServiceNow organizes ITOM into three pillars, all built on the CMDB:

1. **ITOM Visibility** — create and maintain an accurate map of on-premises, cloud, container,
   and Kubernetes infrastructure.
2. **ITOM Health (AIOps)** — detect, correlate, and resolve service issues before users feel the
   impact.
3. **ITOM Cloud Accelerate** — request, govern, and account for multi-cloud resources.

Cross-cutting concerns — CMDB foundation, automation/remediation, and
resilience/security/compliance — are covered as supporting guides, not as additional pillars.

---

## Coverage table

### 1. ITOM Visibility

| Subtopic | Where covered | Status |
|---|---|---|
| Discovery of servers and network devices | [Discovery](modules/discovery/discovery-guide.md) — phases, MID Server, credentials, schedules, ECC | Core |
| Discovery of cloud accounts/resources | [Discovery](modules/discovery/discovery-guide.md) — cloud discovery type, cloud credentials, Cloud Discovery Workspace | Core |
| Discovery of containers | [Discovery](modules/discovery/discovery-guide.md#containers-and-kubernetes) — containerized resources, container registries/images | Core |
| Discovery of Kubernetes/OpenShift clusters | [Discovery](modules/discovery/discovery-guide.md#containers-and-kubernetes) — Kubernetes pattern, OpenShift extension, large-cluster LP pattern, Visibility Agent, Kubernetes Explorer | Core |
| Service Mapping / dependencies | [Service Mapping](modules/service-mapping/service-mapping-guide.md) — top-down mapping, methods, entry points, tables | Core |
| Certificate management | [Visibility suite](modules/visibility-suite/visibility-suite-guide.md#certificate-inventory-and-management) + [Resilience/security](modules/resilience-security/resilience-security-guide.md#certificates) | Core |
| Firewall audits | [Visibility suite](modules/visibility-suite/visibility-suite-guide.md#firewall-audits-and-reporting) + [Resilience/security](modules/resilience-security/resilience-security-guide.md#firewalls) | Core |
| Service Graph Connectors | [CMDB foundation](modules/cmdb/cmdb-guide.md#service-graph-connectors-and-cmdb-360) | Core (conceptual + governance) |
| CMDB as shared foundation | [CMDB foundation](modules/cmdb/cmdb-guide.md) — tables, CSDM, identification, SGC, impact | Core |
| Specialist Visibility apps | [Visibility suite](modules/visibility-suite/visibility-suite-guide.md) — tags, AI topology, content, cloud workspace, license estimator, LEAP | Core |
| Cryptographic assets / PQC | [Resilience/security](modules/resilience-security/resilience-security-guide.md#cryptographic-asset-compliance) | Core |

### 2. ITOM Health (AIOps)

| Subtopic | Where covered | Status |
|---|---|---|
| Event collection and alerting | [Event Management](modules/event-management/event-management-guide.md) — sources, connectors, process flow | Core |
| Deduplication and alert noise | [Event Management](modules/event-management/event-management-guide.md) — message keys, event rules, thresholds, ignore, correlation | Core |
| Event correlation into incidents | [Event Management](modules/event-management/event-management-guide.md) — correlation, alert management rules, incident creation | Core |
| Metric Intelligence | [Metric Intelligence](modules/metric-intelligence/metric-intelligence-guide.md) | Core |
| Health Log Analytics | [Health Log Analytics](modules/health-log-analytics/health-log-analytics-guide.md) | Core |
| Service Observability | [Reliability stack](modules/reliability-stack/reliability-stack-guide.md#service-observability) | Core |
| SLOs / SLIs / error budgets | [Reliability stack](modules/reliability-stack/reliability-stack-guide.md#slo-management) | Core |
| Synthetic monitoring | [Reliability stack](modules/reliability-stack/reliability-stack-guide.md#synthetic-monitoring) | Core |
| SRM workflow | [Reliability stack](modules/reliability-stack/reliability-stack-guide.md#service-reliability-management) | Core |
| Now Assist / Otto in SOW | [AI in ITOM](modules/itom-ai/itom-ai-guide.md#now-assist-and-otto-inside-the-service-operations-workspace) | Core (with deprecation caveat) |
| Alert summaries and past-incident summaries | [AI in ITOM](modules/itom-ai/itom-ai-guide.md#now-assist-and-otto-inside-the-service-operations-workspace) | Core |
| Probable root cause (alerts + topology + changes) | [AI in ITOM](modules/itom-ai/itom-ai-guide.md#probable-root-cause-analysis) + [Resilience/security](modules/resilience-security/resilience-security-guide.md#change-correlated-root-cause) | Core |
| AI governance / model availability | [AI in ITOM](modules/itom-ai/itom-ai-guide.md) | Core |
| CMDB dependency | [CMDB foundation](modules/cmdb/cmdb-guide.md) + [Roles/tables](04-roles-tables.md) | Core |

### 3. ITOM Cloud Accelerate

| Subtopic | Where covered | Status |
|---|---|---|
| Cloud Services Catalog (request/provision) | [Cloud Accelerate](modules/cloud-accelerate/cloud-accelerate-guide.md#cloud-services-catalog) | Core |
| Cloud Configuration Governance | [Cloud Accelerate](modules/cloud-accelerate/cloud-accelerate-guide.md#cloud-configuration-governance) + [Automation](modules/automation-remediation/automation-remediation-guide.md#cloud-remediation) | Core |
| Cloud Account Management | [Cloud Accelerate](modules/cloud-accelerate/cloud-accelerate-guide.md#cloud-account-management) | Core |
| Cloud Action Library | [Cloud Accelerate](modules/cloud-accelerate/cloud-accelerate-guide.md#cloud-action-library) | Core |
| Cloud Migration Assessment | [Cloud Accelerate](modules/cloud-accelerate/cloud-accelerate-guide.md#cloud-migration-assessment-is-retired) | Corrected: retired, not a new-work option |
| Cost/capacity controls | [Cloud Accelerate](modules/cloud-accelerate/cloud-accelerate-guide.md#cost-and-capacity-controls) | Core (CPG-era caveat) |
| Cloud orchestration trail | [Automation](modules/automation-remediation/automation-remediation-guide.md#orchestration-and-execution) | Supporting |
| Tag governance for cloud cost/ownership | [Visibility suite](modules/visibility-suite/visibility-suite-guide.md#tag-governance) + [Automation](modules/automation-remediation/automation-remediation-guide.md#tag-remediation) | Core |

### Cross-cutting

| Subtopic | Where covered | Status |
|---|---|---|
| CMDB / CSDM / IRE / SGC | [CMDB foundation](modules/cmdb/cmdb-guide.md) | Core |
| Automation (alert, cloud, tag, LEAP, Ansible) | [Automation and remediation](modules/automation-remediation/automation-remediation-guide.md) | Core |
| Resilience (backup visibility, recovery evidence) | [Resilience/security](modules/resilience-security/resilience-security-guide.md#resilience-and-recovery-visibility) | Core (visibility, not backup execution) |
| Change/configuration control | [Resilience/security](modules/resilience-security/resilience-security-guide.md#change-and-configuration-control) | Core |
| Security alignment | [Resilience/security](modules/resilience-security/resilience-security-guide.md#security-alignment) | Core |
| Regulatory/audit evidence | [Resilience/security](modules/resilience-security/resilience-security-guide.md#regulatory-and-audit-evidence) | Core |
| Licensing and prerequisites | [Licensing](03-licensing-prerequisites.md) | Core |
| Roles and tables | [Roles and tables](04-roles-tables.md) | Core |
| Common mistakes | [Common mistakes](05-common-mistakes.md) | Core |
| Glossary | [Glossary](07-glossary.md) | Core |

---

## What "sufficient" means here

For each subtopic, the guide provides at least:

1. **A definition** in plain English.
2. **The record/table** where the fact lives.
3. **The roles** that configure and operate it.
4. **The flow** from source to outcome.
5. **A proof** (lab, checklist, or verification query).
6. **Official sources** for re-checking.

A topic is not "covered" because the name appears. It is covered when a reader can find the
record, explain the flow, and verify the result.

---

## Deliberate boundaries

| Not covered deeply | Why |
|---|---|
| **TSOM (Telecom)** | Separate product family with telecom data models |
| **SecOps / Security Incident Response** | Adjacent product; ITOM provides exposure data, not SOC workflow |
| **Platform backup and disaster recovery** | Platform administration responsibility; ITOM only discovers backup resources |
| **Pricing and contracts** | Contractual and not published by ServiceNow docs |
| **Certification exam blueprints** | Change frequently; use Now Learning and the official certification programme |
| **Every Store app and connector** | The guide covers the operating model and the major apps, not an exhaustive app catalogue |
| **Every CI class** | The guide teaches the class hierarchy and the ITOM-critical tables, not the full CMDB schema |

These boundaries are intentional. A guide that claims to cover everything is usually shallow
everywhere.

---

## Official sources

- ITOM overview — <https://www.servicenow.com/docs/r/australia/it-operations-management/r_ITOMApplications.html>
- ITOM Visibility — <https://www.servicenow.com/docs/r/australia/it-operations-management/itom-visibility/itom-visibility-landing-page.html>
- Event Management — <https://www.servicenow.com/docs/r/australia/it-operations-management/event-management/c_EM.html>
- Health Log Analytics — <https://www.servicenow.com/docs/r/australia/it-operations-management/health-log-analytics/hla-landing-page.html>
- Cloud Services Catalog — <https://www.servicenow.com/docs/r/australia/it-operations-management/cloud-services-catalog/exploring-cloud-services-catalog.html>
- Cloud Account Management — <https://www.servicenow.com/docs/r/australia/it-operations-management/cloud-account-management/exploring-cam.html>
- Cloud Configuration Governance — <https://www.servicenow.com/docs/r/australia/it-operations-management/itom-cloud-accelerate/exploring-cloud-configuration-governance.html>
- ITOM Visibility and CMDB tables — <https://www.servicenow.com/docs/r/australia/it-operations-management/itom-visibility/itom-visibility-use-case.html>
- ITOM licensing — <https://www.servicenow.com/docs/r/australia/it-operations-management/explore-itom-licensing.html>

---

## Related guides

- [ITOM overview](modules/itom-overview/itom-overview-guide.md)
- [Family map](02-family-map.md)
- [Study plan](06-study-plan.md)
- [Common mistakes](05-common-mistakes.md)
