---
layout: default
title: Getting started
---

# Getting started with ITOM

**Agent:** Kilo (deepseek-flash) · **Updated:** 2026-11-19 · **Docs release:** Australia

This track is for the first two hours. It does not try to cover every product. It gets you to a
working orientation, a real record, and a written gap.

---

## 1. Choose your starting point

| If you are… | Start with | Then |
|---|---|---|
| New to ServiceNow | [ELI5](../01-ELI5.md) | [Lab 00](../../labs/LAB-00-ORIENTATION.md) |
| A NOC operator | [Event Management start](event-management.md) | [Lab 02](../../labs/LAB-02-EVENT-TO-INCIDENT.md) |
| A CMDB/discovery admin | [Discovery start](discovery.md) | [Lab 01](../../labs/LAB-01-DISCOVERY.md) |
| A service owner | [Service Mapping start](service-mapping.md) | [Reliability stack](../modules/reliability-stack/reliability-stack-guide.md) |
| A cloud operator | [Cloud start](cloud-accelerate.md) | [Cloud Accelerate](../modules/cloud-accelerate/cloud-accelerate-guide.md) |
| An AI/automation lead | [AI start](itom-ai.md) | [AI in ITOM](../modules/itom-ai/itom-ai-guide.md) |

---

## 2. Before you click

- [ ] You have a non-production instance (PDI or sandbox).
- [ ] You know which ITOM products your instance is entitled to.
- [ ] You have a role that can see the product you are studying.
- [ ] You know where the MID Server is, or you know it is missing.
- [ ] You have a place to write the artifact (a note, a doc, a ticket).

If you do not know the entitlement, read [Licensing and prerequisites](../03-licensing-prerequisites.md)
first. A missing menu item is usually a licence, plugin, or role, not a broken platform.

---

## 3. The first two hours

| Time | Do | Output |
|---|---|---|
| 0–20 | Read [ELI5](../01-ELI5.md); write the five words (CI, CMDB, event, alert, incident) in your own words | A one-page vocabulary |
| 20–40 | Open three lists: Discovery schedules, Event rules, CMDB CIs | Three breadcrumbs |
| 40–60 | Run [Lab 00](../../labs/LAB-00-ORIENTATION.md) | A platform map |
| 60–90 | Pick one module and run its Orient + Model gates | A one-page record model |
| 90–120 | Write the gap list: what you could not see, run, or verify | Your next session's plan |

---

## 4. The one rule

Do not confuse reading with learning. A session that ends without an artifact — a breadcrumb, a
record, a diagram, a gap list — did not happen.

---

## Foundation

The layer every ITOM product assumes:

- users, groups, and assignment groups,
- locations and schedules,
- CMDB classes and identification rules,
- MID Servers and credentials,
- tags and ownership,
- maintenance windows.

See [Foundation](foundation.md).

---

## Official sources

- ITOM overview — <https://www.servicenow.com/docs/r/australia/it-operations-management/r_ITOMApplications.html>
- ServiceNow Developer portal (PDI) — <https://developer.servicenow.com/dev.do>
- ServiceNow University / Now Learning — <https://learning.servicenow.com/lxp>
- ITOM licensing — <https://www.servicenow.com/docs/r/australia/it-operations-management/explore-itom-licensing.html>
