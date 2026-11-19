# Lab 02 — Event to incident

**Agent:** Kilo (deepseek-flash) · **Updated:** 2026-11-19 · **Time:** 75–90 min · **Risk:** medium (creates alerts/incidents in a test instance)

You will send a test event, create the rule that turns it into an alert, bind the alert to a CI,
group a related alert, and open exactly one incident with an alert management rule. Then you will
break the binding and prove what changes.

Use a non-production instance. Do not send test events to a production monitoring pipeline.

---

## Goal

By the end you can:

- trace an event through `em_event` to `em_alert`,
- explain why an alert did or did not appear,
- bind an alert to the right CI,
- show a parent/secondary relationship,
- open one incident with an alert management rule,
- diagnose an unbound alert.

---

## Prerequisites

| Item | Required |
|---|---|
| ITOM AIOps subscription and Event Management plugins | Yes |
| `evt_mgmt_admin` for configuration | Yes |
| `evt_mgmt_operator` for operation testing | Yes |
| A CI that exists in the CMDB | Yes |
| An assignment group with a real owner | Yes |
| A way to send a test event (generic JSON endpoint, API Explorer, or test connector) | Yes |
| A non-production instance | Yes |

If you lack the entitlement, use the **design-only path**.

---

## Part A — Pick the CI (10 min)

1. Find a CI you own in the CMDB (`cmdb_ci_server` or similar).
2. Record its **name**, **FQDN**, **IP**, and **class**.
3. Confirm there is no duplicate.
4. Decide which attribute your event will use for binding (node/name, FQDN, or IP).

| Field | Value |
|---|---|
| CI name | |
| FQDN | |
| IP | |
| Class | |
| Binding attribute | |

---

## Part B — Create the event rule (15 min)

1. `Event Management > Rules > Event Rules > New`.
2. **Source**: the source name you will send (for example, `LAB-02` or `genericJson`). It must
   match the event's source.
3. **Order**: a low number so it runs early.
4. **Description**: `LAB-02 test rule`.
5. **Event filter**: restrict to your test source.
6. **Transform and compose**: set the alert fields you care about (description, severity,
   assignment group, CI binding).
7. **Binding**: configure CI binding using the attribute from Part A.
8. Save and activate.

> A rule without a filter is ignored. If nothing happens, this is the first thing to check.

---

## Part C — Send the test event (10 min)

Use the generic JSON endpoint documented by ServiceNow:

```
POST https://<instance>/api/sn_em_connector/em/inbound_event?source=genericJson
```

Example body (field names may need mapping in your event rule; use the payload your connector
documents):

```json
{
  "source": "LAB-02",
  "node": "lab-web-01",
  "resource": "cpu",
  "type": "CPU",
  "severity": "1",
  "description": "LAB-02 CPU above threshold",
  "time_of_event": "2026-11-19 10:00:00",
  "additional_info": "{\"metric\":\"cpu\",\"value\":98}"
}
```

Use API Explorer or your approved REST client. Do not store credentials in the lab notes.

If the endpoint requires an event rule first, Part B is not optional.

---

## Part D — Verify the event and alert (10 min)

1. `Event Management > Events > All Events`. Find your event. Record its source, node, severity,
   and timestamp.
2. `Event Management > Alerts > All Alerts`. Find the alert.
3. If there is no alert, walk the process flow backwards:

| Check | Result |
|---|---|
| Does the event exist? | |
| Does an event rule match the source? | |
| Does the rule have a filter? | |
| Was the rule ignored? | |
| Did transformation produce a severity? | |
| Did field mapping run? | |
| Was a message key matched? | |

4. Record the alert's **severity**, **state**, **CI**, and **priority**.

---

## Part E — Bind and verify the CI (10 min)

1. Confirm the alert's CI field is your Part A CI.
2. If it is empty, fix the binding in the event rule or bind manually for the lab.
3. Send a second event with a **wrong** node (one that does not exist). Confirm the alert is
   unbound or bound to a different CI.
4. Write the difference between the two alerts.

| Event | CI bound? | Why |
|---|---|---|
| Correct node | | |
| Wrong node | | |

---

## Part F — Group a related alert (10 min)

Choose one:

- create an alert correlation rule that designates a primary and secondary, or
- use the Group automation in the Service Operations Workspace.

Send a second related event (same service/CI, different resource). Confirm:

- [ ] One alert is the parent/primary.
- [ ] The other is secondary.
- [ ] The priority reflects the relationship.
- [ ] The operator can see the relationship.

If grouping does not work, check the rule order and whether the alerts share the expected keys.

---

## Part G — Open one incident (15 min)

1. `Event Management > Rules > Alert Management Rules > New`.
2. Filter to your test alerts (for example, description contains `LAB-02`).
3. Action: open an incident (or run the provided create-incident subflow).
4. Save and activate.
5. Trigger the rule (wait for the scheduled job or run it manually if your role allows).
6. Verify exactly **one** incident exists for the parent alert.
7. Check the rule's execution history.
8. Verify the secondary alert did **not** create a duplicate incident.

| Check | Result |
|---|---|
| Incident created | |
| Incident linked to alert | |
| Only one incident | |
| Execution history recorded | |
| Secondary did not duplicate | |

---

## Part H — Break it on purpose (10 min)

Break one:

- change the event's node to a non-existent host,
- remove the binding from the rule,
- set severity to `OK`,
- remove the rule filter.

Rerun. Then explain:

1. Which step of the process flow stopped?
2. What record proves it?
3. What would you change in production to prevent it?

---

## Part I — Teach-back (5 min)

Explain in five sentences:

1. Event vs alert vs incident.
2. The role of the event rule.
3. The role of CI binding.
4. The role of grouping.
5. The role of the alert management rule.

---

## Design-only path

If you cannot send events:

1. Draw the process flow with the six decision points.
2. Write the event rule fields you would set.
3. Write the field mapping for `Low/Medium/High` → alert severity.
4. Write the CI binding method and the attribute it uses.
5. Write the alert management rule filter and action.
6. Write the evidence you would collect at each step.
7. List the missing prerequisites.

---

## Pass test

You can show:

- one event in `em_event`,
- one alert in `em_alert`,
- the CI bound (or an explained unbound alert),
- a parent/secondary relationship,
- exactly one incident created by the rule,
- one broken-and-explained dependency.

---

## Official sources

- Event Management — <https://www.servicenow.com/docs/r/australia/it-operations-management/event-management/c_EM.html>
- Process flow — <https://www.servicenow.com/docs/r/australia/it-operations-management/event-management/em-process-flow.html>
- Event rules — <https://www.servicenow.com/docs/r/australia/it-operations-management/event-management/create-or-edit-event-rule.html>
- Generic JSON connector / connectors — <https://www.servicenow.com/docs/r/australia/it-operations-management/event-management/connectors-and-listeners.html>
- CI binding — <https://www.servicenow.com/docs/r/australia/it-operations-management/event-management/ci-binding-alert.html>
- Alert correlation rule — <https://www.servicenow.com/docs/r/australia/it-operations-management/event-management/t_EMConfigureAnEventCorrelationRule.html>
- Alert management rules — <https://www.servicenow.com/docs/r/australia/it-operations-management/event-management/alert-management-rule.html>
