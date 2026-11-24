# Lab 01 — Discovery

**Agent:** Kilo (deepseek-flash) · **Updated:** 2026-11-19 · **Time:** 60–90 min · **Risk:** low (one scoped target)

You will run a tightly scoped discovery, verify each phase, break a credential on purpose, read
the ECC evidence, and fix it.

---

## Goal

By the end you can:

- create a schedule that scans one safe target,
- explain what happened in each discovery phase,
- read a discovery status, log, ECC record, and device history,
- diagnose a credential failure without guessing,
- state what changed in the CMDB — and what did not.

---

## Prerequisites

| Item | Required |
|---|---|
| ITOM Visibility subscription + `com.snc.discovery` plugin | Yes |
| MID Server, Up and Validated | Yes |
| `discovery_admin` role | Yes |
| A target you own (one IP/host) | Yes |
| Credentials for that target | Yes |
| A non-production instance | Yes |

If you do not have these, use the **design-only path** at the end. Do not scan a range you do not
own.

---

## Part A — Scope the target (10 min)

Pick **one** target:

- a lab VM you own,
- a test network device,
- a cloud test instance with a known IP.

Write:

| Question | Answer |
|---|---|
| Target IP/host | |
| Target OS/type | |
| Credential type | |
| MID Server that can reach it | |
| Why this target is safe | |

Keep the range to one IP. A first lab is not a census.

---

## Part B — Credentials (10 min)

1. Open `Discovery > Credentials` (or the ITOM Configuration Console).
2. Create the credential type your target needs.
3. Give it a clear name.
4. Set **Order** so the correct credential is tried first.
5. Mark it active.
6. Test it against the target if the UI offers a test.

Write down:

| Item | Value |
|---|---|
| Credential name | |
| Type | |
| Order | |
| Alias (if used) | |

Do not paste the password into your notes.

---

## Part C — Schedule (10 min)

1. `Discovery > Discovery Schedules > New`.
2. Name it `LAB-01 <your initials> <date>`.
3. **Discover**: Configuration items.
4. **MID Server selection method**: Specific MID Server.
5. Select the MID Server that can reach the target.
6. **Quick ranges**: the single target IP.
7. Set **Max run time** to a small value (for example, 15 minutes).
8. Set **Max idle time** if the field is available.
9. Leave the schedule **inactive** if you do not want it to recur.
10. Save.

---

## Part D — Run and observe (15 min)

1. Click **Discover now**.
2. Open the **Discovery Status** record.
3. Watch the state: Starting → Active → Completed (or Canceled).
4. Open **Discovery log**. Look for classification, authentication, and CMDB update messages.
5. Open **ECC queue**. Find at least one output and one input record.
6. Open **Device history**. Find your target and the action taken.
7. Find the CI in the CMDB (if one was created/updated).

Record:

| Evidence | What you saw |
|---|---|
| Status state | |
| Probes started/completed | |
| Log message (one) | |
| ECC record state | |
| Device history action | |
| CI created/updated? | |
| CI class | |
| CI identifiers | |

---

## Part E — Break it on purpose (15 min)

Choose one:

- deactivate the credential,
- change the credential password to a wrong value,
- change the target port,
- point the schedule at an IP with no host.

Rerun. Then find the evidence:

| Question | Answer |
|---|---|
| Which phase failed? | |
| What did the discovery log say? | |
| What did the ECC queue show? | |
| Was a CI still created? | |
| Did device history show the target? | |

Write one paragraph: **what broke, where you saw it, and what you expected instead.**

---

## Part F — Fix and verify (10 min)

Restore the credential/port/target. Rerun.

Confirm:

- [ ] Status completes.
- [ ] The log no longer shows the error.
- [ ] The ECC record is processed, not error.
- [ ] The CI is present and has the expected identifiers.
- [ ] There is no obvious duplicate.
- [ ] You can name the phase that previously failed.

---

## Part G — Teach-back (5 min)

Write five sentences:

1. What Discovery does.
2. The four phases.
3. Where the evidence lives.
4. What you broke.
5. Why identification matters more than scanning.

---

## Design-only path (no entitlement or MID Server)

Produce the same artifact without running:

1. Draw the four phases.
2. For each phase, name the record that proves it (status, log, ECC, device history, CI).
3. Write the credential type you would use and why.
4. Write the schedule fields you would set and why.
5. Write the exact error you would look for if the credential failed.
6. List the prerequisites your instance is missing.

A correct design plus an honest gap list is a valid lab result.

---

## Pass test

You can show:

- one scoped schedule,
- one status record,
- one log line,
- one ECC record,
- one CI or device history entry,
- one broken-and-fixed dependency,
- one paragraph explaining the evidence.

---

## Official sources

- Exploring Discovery — <https://www.servicenow.com/docs/r/australia/it-operations-management/discovery/c_GetStartedWithDiscovery.html>
- Discovery schedule reference — <https://www.servicenow.com/docs/r/australia/it-operations-management/discovery/discovery-schedule-form.html>
- Discovery status — <https://www.servicenow.com/docs/r/australia/it-operations-management/discovery/c_DiscoveryStatus.html>
- ECC queue — <https://www.servicenow.com/docs/r/australia/it-operations-management/discovery/r_DiscoveryStatusECCQueue.html>
- Create IP credentials — <https://www.servicenow.com/docs/r/australia/it-operations-management/discovery/create-ip-credentials.html>
