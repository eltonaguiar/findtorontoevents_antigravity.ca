# Event Management start

**Agent:** Kilo (deepseek-flash) · **Updated:** 2026-11-19 · **Docs release:** Australia

A 60-minute orientation to the event → alert → incident path.

---

## 1. Orient (10 minutes)

| Open | Find | Write down |
|---|---|---|
| `Event Management > Rules > Event Rules` | One rule | Source, order, whether it has a filter |
| `Event Management > Alerts > All Alerts` | One alert | Severity, state, CI |
| `Event Management > Events > All Events` | One event | Source, severity, node |
| `Event Management > Rules > Alert Management Rules` | One rule | Filter and action |

If you cannot see the modules, check the AIOps subscription, plugins, and `evt_mgmt_*` role.

---

## 2. Model (20 minutes)

Draw the pipeline:

```
event (em_event) → event rule → field mapping → alert (em_alert) → CI binding → grouping → alert management rule → incident
```

Under each arrow, write what can stop it:

- no matching rule,
- rule ignored,
- no severity,
- no message key match,
- no CI binding,
- no grouping,
- no response rule.

That list is your troubleshooting checklist.

Full guide: [Event Management](../modules/event-management/event-management-guide.md).

---

## 3. Practise (45 minutes)

Use the generic JSON endpoint or a test connector, not a production monitoring tool.

1. Confirm an event rule exists for your test source, or create one with a source filter.
2. Send or create one test event.
3. Find it in `em_event`.
4. Confirm the alert in `em_alert`, or explain why not.
5. Bind the alert to a real CI. Verify the CI field.
6. Create a second related event and group it under the first (correlation rule or grouping).
7. Create an alert management rule that opens exactly one incident for the parent.
8. Break the CI binding and observe what changes.

Lab: [Lab 02](../../labs/LAB-02-EVENT-TO-INCIDENT.md).

---

## 4. Prove (10 minutes)

- Does the alert have the right severity and state?
- Is it bound to the right CI?
- Is the parent/secondary relationship correct?
- Did exactly one incident open?
- Does the event still exist for evidence?
- Can you explain every step from event to incident?

---

## 5. Teach (5 minutes)

Explain the difference between an event, an alert, and an incident, and name one thing that
prevents each from becoming the next.

---

## Blockers and what they mean

| Blocker | Meaning | Next |
|---|---|---|
| Events arrive but no alerts | Rule/filter/severity/mapping | Walk the process flow backwards |
| Alert has no CI | Binding not configured or CI missing | Configure binding; verify the CI exists |
| Too many incidents | No grouping or response sync | Group first; make the response idempotent |
| No incident | No alert management rule or action | Create a rule; check execution history |
| Operator sees nothing | Role, assignment group, or ACL | Impersonate the operator; check the group |

---

## Official sources

- Event Management — <https://www.servicenow.com/docs/r/australia/it-operations-management/event-management/c_EM.html>
- Process flow — <https://www.servicenow.com/docs/r/australia/it-operations-management/event-management/em-process-flow.html>
- Event rules — <https://www.servicenow.com/docs/r/australia/it-operations-management/event-management/create-or-edit-event-rule.html>
- CI binding — <https://www.servicenow.com/docs/r/australia/it-operations-management/event-management/ci-binding-alert.html>
- Alert management rules — <https://www.servicenow.com/docs/r/australia/it-operations-management/event-management/alert-management-rule.html>
- Connectors — <https://www.servicenow.com/docs/r/australia/it-operations-management/event-management/connectors-and-listeners.html>
