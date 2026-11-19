# Lab 00 — Orientation

**Agent:** Kilo (deepseek-flash) · **Updated:** 2026-11-19 · **Time:** 30–45 min · **Risk:** none (read-only)

You will learn to read the platform before changing anything. No records are created, modified,
or deleted.

---

## Goal

By the end you can:

- reach the four ITOM surfaces without searching menus,
- explain what a CI, event, alert, and discovery status record are,
- write a one-page map of what your instance actually has,
- list the prerequisites your instance is missing.

---

## Before you start

- A non-production instance (PDI or sandbox).
- A role that can read Discovery, Event Management, and the CMDB.
- A note-taking surface.

If a module is missing, write it down. Missing modules are data, not failure.

---

## Part 1 — Find the surfaces (10 min)

Open each and write the exact breadcrumb you used:

| Surface | Breadcrumb | Exists? |
|---|---|---|
| Discovery schedules | | |
| Discovery status | | |
| CMDB CIs | | |
| Service Mapping | | |
| Event rules | | |
| Alerts | | |
| MID Servers | | |
| Service Operations Workspace | | |

If a surface is missing, check (in this order): role, plugin, subscription, Store app.

---

## Part 2 — Read four records (15 min)

Do not change anything. Open one record of each type and write:

| Record | What to capture |
|---|---|
| **CI** | Table, class, name, identifiers, owner, relationships |
| **Discovery status** | State, started/completed, one log line, one ECC state |
| **Event** | Source, node, severity, timestamp, whether an alert exists |
| **Alert** | Severity, state, CI, parent/secondary role, priority |

For each, answer: *what would make this record wrong?*

---

## Part 3 — Draw the map (10 min)

Draw five boxes and connect them:

```
Discovery → CMDB CI → Service instance → Alert → Incident
```

Under each box, write the table name you actually saw. If you did not see a box, write "not
available" and the reason.

---

## Part 4 — The gap list (5 min)

Write three columns:

| I could see | I could not see | What I need |
|---|---|---|
| | | |

Examples:

- "I could see `em_event` but not `em_alert`." → Maybe no event rule, no severity, or no alert
  generated yet.
- "I could see Discovery schedules but not MID Servers." → Missing role or plugin.
- "I could see Service Mapping but not a service instance." → No mapping has run.

---

## Pass test

You can point to each of the four surfaces and say:

1. what record it shows,
2. which table stores it,
3. one reason it could be empty.

---

## Do not do this

- Do not run a discovery against a range you do not own.
- Do not create, edit, or delete a record.
- Do not use admin as your only test.
- Do not paste customer data into your notes.

---

## Official sources

- ITOM overview — <https://www.servicenow.com/docs/r/australia/it-operations-management/r_ITOMApplications.html>
- Exploring Discovery — <https://www.servicenow.com/docs/r/australia/it-operations-management/discovery/c_GetStartedWithDiscovery.html>
- Discovery status — <https://www.servicenow.com/docs/r/australia/it-operations-management/discovery/c_DiscoveryStatus.html>
- Event Management — <https://www.servicenow.com/docs/r/australia/it-operations-management/event-management/c_EM.html>
- Service Mapping — <https://www.servicenow.com/docs/r/australia/it-operations-management/service-mapping/c_ServiceMappingOverview.html>
