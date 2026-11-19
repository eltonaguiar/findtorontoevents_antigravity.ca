# Glossary

**Agent:** Kilo (deepseek-flash) · **Updated:** 2026-11-19 · **Docs release:** Australia

Every term used in this guide, defined before you need it.

---

## A

**ACC (Agent Client Collector)** — ServiceNow software installed on a host that runs checks
and sends data back through a MID Server. Used for deep host telemetry, inventory in isolated
networks, and log collection.

**Agentless** — Discovery without permanent software on the target. A MID Server runs probes
over SSH, WMI, or SNMP.

**AIOps** — Applying analytics, machine learning, and automation to IT operations data.
In ServiceNow docs, **ITOM AIOps** is the product family that includes Event Management,
Health Log Analytics, reliability, observability, and synthetic monitoring.

**Alert** — The deduplicated, enriched, prioritised work item generated from one or more
events. Stored in `em_alert`, bound to a CI, and worked by a person or automation.

**Alert correlation** — Grouping related alerts under a primary alert so operators see one
root cause instead of many symptoms.

**Alert management rule** — A rule that responds to an alert by opening an incident, running a
subflow, launching a remediation action, or performing another configured action.

**Anomaly** — Behaviour that deviates from a learned baseline. HLA and Metric Intelligence
detect anomalies and can raise events.

**Application service / service instance** — The mapped representation of a service built from
CIs and relationships. With CSDM v5, the label for `cmdb_ci_service_discovered` is **service
instance**.

**Assignment group** — The team that receives work. For Event Management team operators, the
role must be associated with a group or the operator sees no alerts.

---

## C

**CI (configuration item)** — Any managed component: server, application, database, network
device, service, certificate. Stored in a `cmdb_ci_*` table.

**CMDB (Configuration Management Database)** — The database of CIs and their relationships.
The foundation for impact analysis, service maps, and almost every ITOM answer.

**CSDM (Common Service Data Model)** — ServiceNow's recommended model for representing
services, service instances, and their relationships in the CMDB. ITOM Visibility and AIOps
reference CSDM explicitly.

**Classifier** — A Discovery record that decides which probe or pattern runs for a device or
application.

**Cloud Accelerate** — The ITOM family for cloud request, account lifecycle, and governance:
Cloud Services Catalog, Cloud Account Management, Cloud Configuration Governance, and Cloud
Action Library.

**Cloud Account Management (CAM)** — Automates cloud account/subscription/project creation,
suspension, reactivation, and certification. Available with the ITOM Cloud Accelerate licence.

**Cloud Configuration Governance (CCG)** — Scans cloud resources against policy sets and
remediates non-compliant configuration.

**Cloud Services Catalog (CSC)** — The catalog-driven cloud management application that
replaces the CPG user/admin portals for new work.

**CPG (Cloud Provisioning and Governance)** — The older cloud management application, renamed
and transformed into Cloud Services Catalog. From Brazil onward it is prepared for deprecation
and is not installed on new instances.

**Connector (Event Management)** — An integration that pulls or pushes events from a
monitoring tool, cloud provider, or other source.

---

## D

**Discovery** — ServiceNow's horizontal discovery product. Scans networks, classifies devices,
identifies CIs, explores attributes, and updates the CMDB.

**Discovery phase** — Official phases: **Scanning** (Shazzam), **Classification**
(classifiers/probes), **Identification** (identifiers/reconciliation), **Exploration**
(details and relationships).

**Discovery schedule** — The configuration that defines what to scan, which MID Server to use,
and when to run.

**Discovery status** — The record of one discovery run: state, probes, sensors, log, ECC
queue, timeline, and device history.

**Dynamic CI group** — A query-defined group of CIs stored in
`cmdb_ci_query_based_service`, used for monitoring and impact.

---

## E

**ECC queue (External Communication Channel)** — The message queue between the ServiceNow
instance and MID Servers. Output records carry instructions; input records carry results.
States: Ready, Processing, Processed, Error.

**Entry point** — The point where clients access a service, such as a URL, host/port, or load
balancer. Stored in `cmdb_ci_endpoint`. Do not use localhost.

**Event** — A raw record that something happened, stored in `em_event`. Events are not work
items; alerts are.

**Event field mapping** — A rule that maps source fields and values to alert fields. Stored in
`em_mapping_rule` and `em_mapping_pair`.

**Event rule** — The rule that decides whether an event generates an alert, and how the alert
is transformed, composed, thresholded, or bound to a CI.

**Error budget** — The amount of unreliability an SLO allows. When the budget is exhausted,
the team stops feature work and fixes reliability.

---

## H

**Health Log Analytics (HLA)** — Ingests logs, structures them into key-value data, learns
patterns, detects anomalies, and sends events to Event Management. A separate licence.

**Horizontal discovery** — Discovery's network scan that finds CIs and direct relationships.
It does not understand business services.

---

## I

**Identification** — The Discovery phase that decides whether a discovered device matches an
existing CI or needs a new one.

**Identifier** — The rule that specifies which attributes identify a CI. Also called an
identification rule.

**IRE (Identification and Reconciliation Engine)** — The platform engine that identifies CIs
and reconciles attribute values from multiple data sources.

**ITOM** — IT Operations Management: the ServiceNow product family for visibility, monitoring,
reliability, cloud operations, and AI-assisted operations.

**ITOM Visibility** — The family that produces the CMDB view: Discovery, Service Mapping,
Certificate Inventory and Management, Tag Governance, Firewall Audits and Reporting, ITOM
Content Service, Cloud Discovery Workspace, Cloud License Estimator, AI Agent Topology
Mapping, and LEAP.

---

## L

**LEAP (Learning Enhanced Automation Platform)** — AI-assisted ITOM capability for generating
knowledge and playbooks, including problem records and automation recommendations.

**Log correlator** — A key or value in log data that links related alerts across sources or
service instances.

---

## M

**Metric Intelligence** — Monitors historical metric data, detects anomalies, and can raise
alerts. Complements event-based monitoring.

**MID Server** — A ServiceNow process inside your network that executes probes, patterns,
connectors, and agent communication. It starts the connection (SOAP over HTTPS), so no
inbound firewall rule is usually required.

**MCP (Model Context Protocol) Server Console** — The ITOM console used to manage the MCP
server that exposes ITOM capabilities to AI agents.

---

## O

**Observability** — The ability to understand a system's internal state from its outputs:
metrics, logs, traces, and events.

**Otto for ITOM** — ServiceNow's AI assistant/agent capability for ITOM in the Australia era,
replacing the older Now Assist packaging direction. Verify current naming and availability.

---

## P

**Pattern** — A sequence of operations, written in Neebula Discovery Language (NDL), that
identifies CI attributes and connections. Used by Discovery and Service Mapping.

**PCIE** — A teaching mnemonic (Probe, Classifier, Identifier, Explorer) for the discovery
phases. The official phase names are Scanning, Classification, Identification, Exploration.

**Predictive Intelligence** — ServiceNow's machine-learning capability. In Service Mapping it
ranks connections and suggests service candidates; it needs training and repeated runs.

**Probe** — A script that collects data from a target. Sensors parse the result.

---

## R

**Reconciliation** — Deciding which data source wins for each CI attribute after identification.

**Reliability stack** — This guide's shorthand for SRM, SLO Management, Service Observability,
and Synthetic Monitoring working together.

**Role** — A named permission set. ITOM examples: `discovery_admin`, `sm_admin`,
`evt_mgmt_admin`, `evt_mgmt_operator`, `evt_team_operator`, `evt_mgmt_user`.

---

## S

**Service instance** — See application service. Stored in `cmdb_ci_service_discovered`,
`cmdb_ci_service_by_tags`, or `cmdb_ci_service_manual` depending on the mapping method.

**Service Mapping** — Top-down discovery that builds service instances from entry points and
CI connections.

**Service Observability** — Brings third-party observability telemetry into the Service
Operations Workspace next to CMDB service data.

**Service Reliability Management (SRM)** — A workflow for responding to, collaborating on, and
tracking reliability work. Requires ITSM Standard and ITOM Operator Professional.

**Shazzam** — The Discovery probe that scans for open ports and identifies device types.

**SLI / SLO / SLA** — Indicator (what you measure), objective (the target), agreement (the
contract). SLO Management defines and tracks SLIs, SLOs, and error budgets.

**SOW (Service Operations Workspace)** — The operator workspace used by AIOps, SRM,
observability, and synthetic monitoring.

**Synthetic monitoring** — Automated tests that call HTTP endpoints on a schedule and alert
when availability, response time, or response content fails the criteria.

---

## T

**Tag** — A key-value pair on a CI or cloud resource. Used for cost allocation, governance,
and tag-based service mapping.

**Tag Governance** — Audits and remediates tag compliance for on-premises and cloud resources.

**Top-down discovery** — Service Mapping's method: start at an entry point and follow
connections to build a service instance.

**TSOM** — Telecom Service Operations Management, a separate telecom product family adjacent
to ITOM.

---

## V / W

**Visibility suite** — This guide's shorthand for the specialist ITOM Visibility apps beyond
Discovery and Service Mapping.

**Workflow Studio** — The modern flow/subflow authoring environment. CPG legacy workflows are
being migrated to Workflow Studio flows and subflows.

---

## Automation, containers, and assurance

**Alert automation** — The SOW sequence Ignore → Enrich → Group → Respond. Each type runs only on
new incoming alerts.

**Alert analysis** — An AI-generated, human-readable brief of an alert plus technical context,
available in the Express List via ServiceNow Otto.

**Backup plan / backup vault / backup item** — Cloud resources (AWS Backup Plan/Vault, Azure
Recovery Services Vault Backup Item) that Discovery patterns can find and represent in the CMDB.
They are evidence of configuration, not proof of restore.

**Capacity limit** — A restriction on cloud request attributes such as VM count, vCPUs, or
aggregate storage, set per logical datacenter.

**CMDB 360** — The application providing a multi-source view of CI data and change over time;
one of the data providers to ITOM Visibility.

**Container / Kubernetes discovery** — Pattern-based discovery (and the Kubernetes Visibility
Agent) that finds Kubernetes/OpenShift components, events, service mesh, and container images,
updating the CMDB.

**Cost center / resource pool** — A way to restrict the cost center a requester can select in the
cloud catalog request form (for example, the `UserCostCenter` resource pool).

**Probable RCA** — A ranked list of probable root causes for an alert, using alerts, CI topology,
and change requests.

**Remediation** — Automatically correcting a problem: alert/CI remediation workflows, cloud
remediation actions, tag remediation, and LEAP playbooks.

**Service Graph Connector** — A Store app that ingests third-party data into the CMDB;
complements Discovery and is subject to reconciliation.

**Service instance** — The CSDM v5 label for `cmdb_ci_service_discovered` (formerly Application
Service); the anchor for impact and alert context.

---

## Official sources

- ITOM overview — <https://www.servicenow.com/docs/r/australia/it-operations-management/r_ITOMApplications.html>
- Exploring Discovery — <https://www.servicenow.com/docs/r/australia/it-operations-management/discovery/c_GetStartedWithDiscovery.html>
- Event Management — <https://www.servicenow.com/docs/r/australia/it-operations-management/event-management/c_EM.html>
- Event Management process flow — <https://www.servicenow.com/docs/r/australia/it-operations-management/event-management/em-process-flow.html>
- Service Mapping — <https://www.servicenow.com/docs/r/australia/it-operations-management/service-mapping/c_ServiceMappingOverview.html>
- Health Log Analytics — <https://www.servicenow.com/docs/r/australia/it-operations-management/health-log-analytics/hla-landing-page.html>
- Cloud Services Catalog — <https://www.servicenow.com/docs/r/australia/it-operations-management/cloud-services-catalog/exploring-cloud-services-catalog.html>
- Agent Client Collector — <https://www.servicenow.com/docs/r/australia/it-operations-management/agent-client-collector/exploring-agent-client-collector.html>
- ITOM licensing — <https://www.servicenow.com/docs/r/australia/it-operations-management/explore-itom-licensing.html>
