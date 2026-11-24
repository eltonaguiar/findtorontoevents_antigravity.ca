# Foundation

**Agent:** Kilo (deepseek-flash) · **Updated:** 2026-11-19 · **Docs release:** Australia

ITOM does not start with Discovery. It starts with the data every ITOM product assumes:
people, groups, locations, CI classes, identification, credentials, and ownership.

This page is the minimum foundation that makes the first lab behave.

---

## 1. People and groups

| Item | Why ITOM needs it | Check |
|---|---|---|
| Users | Caller, assignee, approver, certifier | `User Administration > Users` |
| Assignment groups | Alert routing and team ownership | `User Administration > Groups` |
| Group managers | Escalation and accountability | Group record |
| Roles | Who can configure vs operate | `User Administration > Roles` |

A group with no manager is an orphan queue. A team operator role with no group sees no alerts.

---

## 2. Locations and schedules

| Item | Why ITOM needs it | Check |
|---|---|---|
| Locations | CI ownership and reporting; discovery schedule location | `Organization > Locations` |
| Time zones | SLAs and schedules compute against them | Location record |
| Business hours / schedules | Maintenance windows and SLAs | `Service Level Management > Schedules` |
| Maintenance windows | Change work should not create alert storms | Event Management maintenance rules |

---

## 3. CMDB and CSDM

The CMDB is the shared contract. Before ITOM:

- CI classes exist for what you manage.
- Identification rules make CIs unique.
- Reconciliation rules decide which source wins.
- Relationships are meaningful (`cmdb_rel_ci`).
- CSDM is the target model for services and service instances, not an afterthought.

If the CMDB is a duplicate-ridden inventory, Discovery will add more duplicates, Service Mapping
will draw them, and Event Management will bind alerts to the wrong one.

---

## 4. MID Server

| Question | Why it matters |
|---|---|
| Is a MID Server installed? | Discovery, pull connectors, HLA, ACC, and orchestration need one |
| Is it Up and Validated? | A down MID Server looks like a discovery failure |
| Can it reach the target subnet? | Credentials cannot fix routing |
| Does it have the right applications/capabilities? | Discovery, Service Mapping, Event Management, ACC, HLA |
| Is it sized for the scan? | Large ranges need batching or clusters |
| Is it time-synced? | Logs, events, and correlation depend on it |

Check `MID Server > Servers` before changing a schedule.

---

## 5. Credentials

- Use the right credential type for the target (SSH, Windows, SNMP, cloud API, VMware, etc.).
- Set credential order. Failed logins can lock accounts.
- Use credential aliases so rotation is one edit, not many.
- Store secrets in the approved secret store, not in a schedule description.
- Test one target before scanning a range.

---

## 6. Tags and ownership

- Define a minimum tag set: owner, cost centre, environment, service, data classification.
- Apply it at provisioning (Cloud Services Catalog, catalog items, templates).
- Audit it with Tag Governance.
- Use tags for Service Observability and tag-based Service Mapping only after the discipline
  exists.

---

## 7. The first-lab checklist

- [ ] A non-production instance.
- [ ] A role that can see the product.
- [ ] A MID Server, or a documented reason there is none.
- [ ] One credential type for one target.
- [ ] One small IP range or one test event payload.
- [ ] One assignment group with a real owner.
- [ ] A place to write the evidence.

---

## Official sources

- ITOM overview — <https://www.servicenow.com/docs/r/australia/it-operations-management/r_ITOMApplications.html>
- Exploring Discovery (MID Server) — <https://www.servicenow.com/docs/r/australia/it-operations-management/discovery/c_GetStartedWithDiscovery.html>
- Create IP credentials — <https://www.servicenow.com/docs/r/australia/it-operations-management/discovery/create-ip-credentials.html>
- ITOM Visibility and CMDB tables — <https://www.servicenow.com/docs/r/australia/it-operations-management/itom-visibility/itom-visibility-use-case.html>
- ITOM licensing — <https://www.servicenow.com/docs/r/australia/it-operations-management/explore-itom-licensing.html>
