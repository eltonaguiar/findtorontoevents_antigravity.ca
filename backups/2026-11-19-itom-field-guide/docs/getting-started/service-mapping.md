# Service Mapping start

**Agent:** Kilo (deepseek-flash) · **Updated:** 2026-11-19 · **Docs release:** Australia

A 60-minute orientation to top-down mapping. The goal is not a perfect map. The goal is to explain
one entry point and prove the first hop.

---

## 1. Orient (10 minutes)

| Open | Find | Write down |
|---|---|---|
| `Service Mapping` workspace | One service instance | Entry point, method, owner |
| The service instance record | The map | First three CIs and arrows |
| `cmdb_ci_endpoint` (or the entry point record) | The endpoint | Host, port, type |
| The CMDB CI for the entry point | The CI | Class, identifiers, duplicate check |

If the workspace is missing, check the Service Mapping subscription, plugin, activation, and
`sm_admin` role.

---

## 2. Model (20 minutes)

Draw:

```
entry point (cmdb_ci_endpoint) → first CI → connection (cmdb_rel_ci) → next CI → service instance (cmdb_ci_service_discovered)
```

Then write which mapping method you would use and why:

- pattern-based — precise, credentials required;
- tag-based — tags must exist;
- traffic-based — useful initially, noisy later;
- Predictive Intelligence — needs training.

Full guide: [Service Mapping](../modules/service-mapping/service-mapping-guide.md).

---

## 3. Practise (45 minutes)

1. Pick one non-critical service with a known host and port.
2. Confirm the CMDB CI for that host exists and is not duplicated.
3. Create the entry point with the real hostname/IP and port. Do not use localhost.
4. Choose pattern-based mapping if credentials are available; otherwise use tag or manual.
5. Run the mapping.
6. Open the service instance and verify the first three hops.
7. Break the entry point (wrong port), rerun, and read the failure.
8. Fix it and record the difference.

Lab: [Lab 03](../../labs/LAB-03-SERVICE-MAPPING.md).

---

## 4. Prove (10 minutes)

- Does the entry point resolve to the right host?
- Is the first CI the right class?
- Do the arrows match the application team's understanding?
- Is the service instance table the expected one for the method?
- Is there an owner?
- Is there a duplicate CI in the map?

---

## 5. Teach (5 minutes)

Explain top-down mapping in five sentences, then name the one dependency that would break your
map first.

---

## Blockers and what they mean

| Blocker | Meaning | Next |
|---|---|---|
| Empty map | Entry point, credentials, MID Server, or CMDB data | Check the first hop |
| Wrong host mapped | Entry point is wrong or resolves to a VIP | Fix the endpoint |
| Duplicate CIs in map | CMDB identification problem | Fix IRE; remap |
| Map too noisy | Traffic-based discovery still on | Disable after tuning |
| Tags missing | Tag-based method without tags | Use pattern mapping or fix tags |
| No service owner | Map will decay | Assign ownership |

---

## Official sources

- Service Mapping — <https://www.servicenow.com/docs/r/australia/it-operations-management/service-mapping/c_ServiceMappingOverview.html>
- Choose the right method — <https://www.servicenow.com/docs/r/australia/it-operations-management/service-mapping/choose-mapping-method.html>
- Entry points — <https://www.servicenow.com/docs/r/australia/it-operations-management/service-mapping/r_EntryPointsforBizSvcDef.html>
- ITOM Visibility and CMDB tables — <https://www.servicenow.com/docs/r/australia/it-operations-management/itom-visibility/itom-visibility-use-case.html>
