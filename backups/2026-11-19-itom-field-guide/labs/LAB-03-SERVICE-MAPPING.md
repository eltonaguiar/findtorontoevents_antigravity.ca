# Lab 03 — Service Mapping

**Agent:** Kilo (deepseek-flash) · **Updated:** 2026-11-19 · **Time:** 75–90 min · **Risk:** medium (creates a service instance)

You will define an entry point, build a minimal service instance, verify the first hops, break the
entry point, and prove what the map does and does not know.

---

## Goal

By the end you can:

- choose the right mapping method for a service,
- create a valid entry point (not localhost),
- explain the table that stores the service instance,
- verify the first three hops,
- diagnose an empty or wrong map.

---

## Prerequisites

| Item | Required |
|---|---|
| ITOM Visibility subscription | Yes |
| `com.snc.service-mapping` plugin and activation | Yes |
| `sm_admin` role | Yes |
| MID Server with Service Mapping capability | Yes |
| CMDB CIs for the service's hosts | Yes |
| Credentials for the application/host | Yes |
| A non-critical service you own | Yes |

If Service Mapping is not available, use the **design-only path**.

---

## Part A — Choose the method (10 min)

Pick one method and write why:

| Method | Choose when | Your choice |
|---|---|---|
| Pattern-based | You can provide credentials and want precision | |
| Tag-based | Tags are reliable and complete | |
| Traffic-based | You need a broader net initially | |
| Predictive Intelligence | Large environment; can train over repeated runs | |

Default recommendation for a first lab: **pattern-based** if credentials are available.
Otherwise use manual mapping and document why.

---

## Part B — Validate the entry point (15 min)

1. Choose a real hostname, alias, IP, or VIP for the service.
2. Confirm the CMDB has a CI for it (or that mapping can create one).
3. Confirm the port.
4. Confirm there is no duplicate CI.
5. Do **not** use `localhost` or `127.0.0.1`.

| Field | Value |
|---|---|
| Host | |
| Port | |
| URL (if used) | |
| Entry point type | |
| CI (if known) | |

---

## Part C — Create the service instance (20 min)

Use the Service Mapping workspace or the Application Service wizard (label varies by release).

1. Create a new service instance.
2. Enter the entry point from Part B.
3. Select the mapping method from Part A.
4. If pattern-based, select the appropriate pattern or let Service Mapping choose.
5. Save and run the mapping.
6. Open the service instance and wait for the map to populate.

Write:

| Item | Value |
|---|---|
| Service instance name | |
| Table | `cmdb_ci_service_discovered` / `cmdb_ci_service_by_tags` / `cmdb_ci_service_manual` |
| First CI | |
| Second CI | |
| Third CI | |
| Relationship type(s) | |

---

## Part D — Verify the first hops (15 min)

Check:

- [ ] The entry point resolves to the intended host.
- [ ] The first CI is the right class.
- [ ] The arrows match the application team's understanding.
- [ ] There are no duplicate CIs in the first three hops.
- [ ] The service instance has an owner.
- [ ] You can explain the map without the screen.

If the map is empty, check:

| Check | Result |
|---|---|
| MID Server reachable? | |
| Credentials valid? | |
| Entry point correct? | |
| CMDB CI exists? | |
| Pattern/method appropriate? | |
| Domain constraints? | |

---

## Part E — Break it on purpose (10 min)

Change the entry point to a wrong port or a non-existent host. Rerun.

Record:

| Question | Answer |
|---|---|
| What did the map show? | |
| What error or log evidence appeared? | |
| Did it create a wrong CI? | |
| How did you detect the error? | |

Then restore the entry point and rerun. Confirm the map returns to the expected state.

---

## Part F — Teach-back (5 min)

Explain:

1. What top-down mapping is.
2. Why the entry point matters.
3. Why the CMDB must be clean.
4. Which table stores the mapped service instance.
5. One thing that would break the map.

---

## Design-only path

If Service Mapping is not available:

1. Draw the entry point and the first three hops.
2. Name the table for the method you would use.
3. Write the credentials and permissions you would need.
4. Write the verification queries/views.
5. Write the exact symptoms of a wrong entry point and a duplicate CI.
6. List the missing prerequisites.

---

## Pass test

You can show:

- one valid entry point,
- one service instance (or a complete design),
- the first three hops,
- one broken-and-restored entry point,
- a written explanation of the map's limits.

---

## Official sources

- Service Mapping — <https://www.servicenow.com/docs/r/australia/it-operations-management/service-mapping/c_ServiceMappingOverview.html>
- Choose the right method — <https://www.servicenow.com/docs/r/australia/it-operations-management/service-mapping/choose-mapping-method.html>
- Entry point attributes — <https://www.servicenow.com/docs/r/australia/it-operations-management/service-mapping/r_EntryPointsforBizSvcDef.html>
- ITOM Visibility and CMDB tables — <https://www.servicenow.com/docs/r/australia/it-operations-management/itom-visibility/itom-visibility-use-case.html>
