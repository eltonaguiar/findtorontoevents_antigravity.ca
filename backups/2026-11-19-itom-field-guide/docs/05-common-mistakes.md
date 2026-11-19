# Common ITOM mistakes

**Agent:** Kilo (deepseek-flash) · **Updated:** 2026-11-19 · **Docs release:** Australia

Each row is a failure mode that looks like progress until someone tries to operate it. The
fix is usually smaller than the cleanup.

---

## Discovery

| # | Mistake | Symptom | Fix |
|---|---|---|---|
| 1 | Scanning a huge range with one schedule | The run never completes; the ECC queue is enormous; nobody knows which device failed | Split by subnet, use Shazzam batching, set max run time and max idle time |
| 2 | No credentials, or credentials in the wrong order | Devices are found but not classified; authentication errors in the discovery log | Add the right credential types; set order; remember lockout policies |
| 3 | MID Server cannot reach the target subnet | Zero CIs from a range that is definitely alive | Place a MID Server in the network segment; verify firewall routes and MID Server IP ranges |
| 4 | Treating "found" as "reconciled" | A device appears in device history but no CI is updated | Read the identification phase; check identifiers and reconciliation rules |
| 5 | Ignoring the ECC queue | Discovery "fails" with no explanation | Inspect ECC records, discovery log, timeline, and device history |
| 6 | No IP exclusions | Discovery scans load balancers, printers, or forbidden ranges | Use Global IP Exclusion and range scoping |
| 7 | Discovery creates duplicate CIs | Multiple records for one server; maps and alerts split | Fix identification rules before adding more schedules |
| 8 | Only testing as admin | The schedule works for you, but the discovery admin cannot see it | Test with `discovery_admin` and the real assignment groups |

---

## Service Mapping

| # | Mistake | Symptom | Fix |
|---|---|---|---|
| 9 | Mapping before the CMDB is clean | The service map is a duplicate-ridden mess | Fix Discovery and IRE first |
| 10 | Using localhost or `127.0.0.1` as an entry point | Mapping cannot reach the service or maps the wrong host | Use the real hostname, alias, IP, or VIP |
| 11 | Tag-based mapping with bad tags | The map misses key CIs | Enforce tag policy first; use Tag Governance |
| 12 | Leaving traffic-based discovery on forever | The map fills with irrelevant CIs | Use it during discovery, then disable it after tuning |
| 13 | Expecting Predictive Intelligence to work on the first run | Suggestions are poor or absent | Train with repeated discovery runs; review connection rules |
| 14 | No owner for the service instance | The map exists; nobody maintains it | Assign a service owner and a review cadence |

---

## Event Management

| # | Mistake | Symptom | Fix |
|---|---|---|---|
| 15 | No event rules for a connector | Events arrive but no alerts appear | Create an event rule with a source and filter; test with event simulation |
| 16 | Event rule with no filter | Every event matches; the rule becomes unpredictable | Add a source filter and, where needed, an additional-information filter |
| 17 | No CI binding | Alerts are unbound; impact and root cause are guesses | Configure implicit node binding or CI field matching; verify against the CMDB |
| 18 | Correlation without a parent | Hundreds of alerts for one outage | Create alert correlation rules; designate primary and secondary |
| 19 | Alert management rule opens duplicates | Several incidents for one parent alert | Let grouping run first; sync alert response with grouping; test on secondary alerts |
| 20 | No maintenance rules | Every change window creates an alert storm | Create maintenance rules for planned work; verify how CIs in maintenance behave |
| 21 | Silencing instead of fixing | The alert count falls; the outage remains | Fix binding, correlation, or thresholds; use suppression deliberately |
| 22 | Severity values assumed | Priority is wrong or alerts are dropped | Check the field mapping and the actual severity choice list; `OK` does not produce a priority score |
| 23 | Testing only with perfect data | Works in the lab; fails on a real connector payload | Test with a real sample event, including missing fields |

---

## Health Log Analytics

| # | Mistake | Symptom | Fix |
|---|---|---|---|
| 24 | No log mapping | Logs arrive but are not tied to service instances or components | Configure data input mapping; use Test mode before publishing |
| 25 | Too many source types | Storage grows; alerts are noisy | Use source limits, filters, and extraction controls |
| 26 | Ignoring time sync | Correlators and anomaly baselines are wrong | Fix NTP on sources and MID Servers |
| 27 | Treating every anomaly as an incident | Operators burn out | Use significance feedback, muting, advanced filters, and custom rules |
| 28 | Forgetting the licence | The logs stream; the bill or the entitlement does not match the design | Confirm the separate HLA subscription before onboarding sources |

---

## Cloud Accelerate

| # | Mistake | Symptom | Fix |
|---|---|---|---|
| 29 | Designing on CPG for a new instance | The app is not installed; the design cannot ship | Use Cloud Services Catalog for new work; CPG is supported for existing customers and prepared for deprecation |
| 30 | Customising legacy CPG workflows | The migration to Workflow Studio flows is blocked | Avoid customisation, or plan the migration explicitly |
| 31 | No account ownership model | Cloud accounts exist; nobody certifies or owns them | Use Cloud Account Management personas and certification |
| 32 | No tag policy | Cost and governance dashboards are wrong | Use Tag Governance and cloud tag policies |
| 33 | Confusing request, account, and compliance | One team tries to solve all three with one app | Map the problem to the right app: Catalog, CAM, or CCG |

---

## Agents and AI

| # | Mistake | Symptom | Fix |
|---|---|---|---|
| 34 | Installing an agent without a MID Server plan | Agents cannot check in or data is delayed | Size and place the MID Server first |
| 35 | Assuming AI output is evidence | A confident summary is wrong | Verify against the record, map, or log line; keep human oversight |
| 36 | Turning on AI without governance | Data leaves the region or a model is unavailable | Review AI Control Tower, model availability, data processing, and opt-out |
| 37 | Forgetting certificate rotation | Agents stop checking in after a certificate expires | Monitor ACC certificates and rotation |

---

## Containers and cross-cutting

| # | Mistake | Symptom | Fix |
|---|---|---|---|
| 38 | Running the Kubernetes pattern as CI discovery, not Serverless | Kubernetes resources are missed | Use a serverless discovery schedule for the Kubernetes pattern |
| 39 | Configuring two Kubernetes authentication methods | Credential rejected | Use user/password **or** a Bearer token, not both |
| 40 | MID Server cannot reach the API server | Empty Kubernetes discovery | Check reachability, RBAC, and pattern version |
| 41 | No per-namespace RBAC binding | Incomplete large-cluster discovery | Ensure a RoleBinding exists in every namespace the LP pattern enumerates |
| 42 | Installing a Service Graph Connector without an owner | Data conflicts and duplicates | Assign ownership, precedence, and refresh cadence |
| 43 | Using the wrong service table | Alerts/SLOs cannot find the service | Match the table to the mapping method (top-down/tag/manual) |
| 44 | Automation without an approval gate | An automation makes an outage worse | Gate destructive actions; require a change record where relevant |
| 45 | Non-idempotent responses | Duplicate incidents | Make the response idempotent; group before respond |
| 46 | Auto-remediation set too broad | Non-compliant but safe resources are changed | Scope remediation; review violation types first |
| 47 | Planning new cloud work on Cloud Migration Assessment | A retired app | It is no longer deployed/enhanced/supported; use current Cloud Services Catalog guidance |
| 48 | Assuming a backup CI proves recovery | Failed restore surprises everyone | Backup CI is evidence of configuration; test restores |

---

## The meta-mistake

**Treating ITOM as a product you install instead of a data pipeline you operate.**

Every item above is a data-quality or ownership failure dressed as a configuration problem.
The recurring fix is:

1. Name the record.
2. Name the owner.
3. Name the evidence that proves it is right.
4. Put a review cadence around it.

---

## Official sources

- Discovery phases and MID Server — <https://www.servicenow.com/docs/r/australia/it-operations-management/discovery/c_GetStartedWithDiscovery.html>
- Discovery schedule reference — <https://www.servicenow.com/docs/r/australia/it-operations-management/discovery/discovery-schedule-form.html>
- ECC queue — <https://www.servicenow.com/docs/r/australia/it-operations-management/discovery/r_DiscoveryStatusECCQueue.html>
- Service Mapping methods — <https://www.servicenow.com/docs/r/australia/it-operations-management/service-mapping/choose-mapping-method.html>
- Event Management process flow — <https://www.servicenow.com/docs/r/australia/it-operations-management/event-management/em-process-flow.html>
- Event rules — <https://www.servicenow.com/docs/r/australia/it-operations-management/event-management/create-or-edit-event-rule.html>
- Alert management rules — <https://www.servicenow.com/docs/r/australia/it-operations-management/event-management/alert-management-rule.html>
- Health Log Analytics alert generation — <https://www.servicenow.com/docs/r/australia/it-operations-management/health-log-analytics/hla-op-anomalies-detecting.html>
- Cloud Account Management — <https://www.servicenow.com/docs/r/australia/it-operations-management/cloud-account-management/exploring-cam.html>
- Cloud Provisioning and Governance deprecation — <https://www.servicenow.com/docs/r/australia/it-operations-management/cloud-configuration-governance/cloud-management-v2-landing-page.html>
- Agent Client Collector — <https://www.servicenow.com/docs/r/australia/it-operations-management/agent-client-collector/exploring-agent-client-collector.html>
- AI in ITOM — <https://www.servicenow.com/docs/r/australia/it-operations-management/now-assist-for-it-operations-management.html>
