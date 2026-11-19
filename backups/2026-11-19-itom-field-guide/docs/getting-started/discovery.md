# Discovery start

**Agent:** Kilo (deepseek-flash) · **Updated:** 2026-11-19 · **Docs release:** Australia

A 60-minute orientation to Discovery. Do not scan the corporate estate. Find one safe target, read
the evidence, and write the gap list.

---

## 1. Orient (10 minutes)

| Open | Find | Write down |
|---|---|---|
| `Discovery > Discovery Schedules` | One schedule (yours or a sample) | The Discover type and MID Server method |
| `Discovery > Status` | One completed run | State, probes started/completed |
| `Discovery > Output and Artifacts > ECC Queue` | One record | State and payload size |
| `All > MID Server > Servers` | The MID Server | Status and version |

If any menu is missing, check the plugin and role before assuming a platform problem.

---

## 2. Model (20 minutes)

Draw four boxes: **Scan → Classify → Identify → Explore**. Under each, write:

- what runs (Shazzam, classifier, identifier, probes/patterns),
- what record proves it happened (discovery status, log, ECC, device history, CMDB CI).

Then write one sentence: "Discovery is not finished until the CI is reconciled, not just found."

Full guide: [Discovery](../modules/discovery/discovery-guide.md).

---

## 3. Practise (45 minutes)

Use the smallest possible target:

1. Create or edit a schedule.
2. Set **Discover** to Configuration items.
3. Select one MID Server (not auto-select, for the first run).
4. Add a **Quick range** with one IP or a tiny range.
5. Set **Max run time** and **Max idle time**.
6. Run **Discover now**.
7. Open the **Discovery Status** record.
8. Check the log for classification/authentication failures.
9. Check the ECC queue for an error or a successful probe.
10. Find the CI or device history result.

Break it on purpose: disable the credential or change the port, rerun, and read the error. Fix
it. Write one paragraph: "What broke, where I saw it, and what fixed it."

Full lab: [Lab 01](../../labs/LAB-01-DISCOVERY.md).

---

## 4. Prove (10 minutes)

- Does the CI exist in the CMDB?
- Is it the right class?
- Does it have the expected identifiers?
- Is there a duplicate?
- Does the discovery status show the phase that failed (if any)?
- Does the ECC record explain the failure?

If you cannot answer, you have a gap, not a failure.

---

## 5. Teach (5 minutes)

Explain to a colleague:

1. What Discovery does.
2. The four phases.
3. Where the evidence lives.
4. One thing that breaks it.
5. Why identification matters more than scanning.

---

## Blockers and what they mean

| Blocker | Meaning | Next |
|---|---|---|
| No `com.snc.discovery` plugin | Not entitled/installed | Use the design-only path |
| No MID Server | Discovery cannot execute | Install/validate a MID Server or use a sandbox with one |
| No credentials | Cannot classify/explore | Create a test credential for one target |
| No CI classes/identification | Discovery may duplicate | Fix IRE before scanning more |
| Discovery finds devices but no CIs | Likely identification or credentials | Read the discovery log and ECC queue |

---

## Official sources

- Exploring Discovery — <https://www.servicenow.com/docs/r/australia/it-operations-management/discovery/c_GetStartedWithDiscovery.html>
- Discovery schedule reference — <https://www.servicenow.com/docs/r/australia/it-operations-management/discovery/discovery-schedule-form.html>
- Discovery status — <https://www.servicenow.com/docs/r/australia/it-operations-management/discovery/c_DiscoveryStatus.html>
- ECC queue — <https://www.servicenow.com/docs/r/australia/it-operations-management/discovery/r_DiscoveryStatusECCQueue.html>
- Create IP credentials — <https://www.servicenow.com/docs/r/australia/it-operations-management/discovery/create-ip-credentials.html>
