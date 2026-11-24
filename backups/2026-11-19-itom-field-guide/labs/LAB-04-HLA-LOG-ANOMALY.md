# Lab 04 — Health Log Analytics

**Agent:** Kilo (deepseek-flash) · **Updated:** 2026-11-19 · **Time:** 60–90 min · **Risk:** medium (log ingestion + alerts)

You will design one log data input, map a sample log to a service instance and component, define
one anomaly rule, and prove what event/alert should result. Then you will break the mapping and
show how the signal degrades.

HLA requires a **separate licence**. If you do not have it, use the design-only path.

---

## Goal

By the end you can:

- choose a passive vs active data input for a source,
- explain the three auto-mapping tags,
- use Test mode safely,
- define an anomaly rule and predict its alert,
- bind logs to a CI/service instance,
- diagnose an unmapped or noisy source.

---

## Prerequisites

| Item | Required |
|---|---|
| Separate HLA subscription and Store app | Yes |
| Event Management | Yes |
| MID Server (for most sources) | Yes |
| A log source you own | Yes |
| `evt_mgmt_admin` (or the HLA admin role) | Yes |
| A service instance/CI to bind to | Yes |
| A non-production instance | Yes |

---

## Part A — Pick the source and input type (10 min)

Choose one:

- a local log file shipped by Beats/Rsyslog (passive),
- a test Kafka/Elasticsearch/S3 bucket (active),
- a REST API push (passive).

Write:

| Question | Answer |
|---|---|
| Source | |
| Passive or active | |
| Transport | |
| Expected volume | |
| Retention need | |
| Who owns the source | |

---

## Part B — Model the mapping (15 min)

For a sample log line, write the expected tags:

| Tag | Expected value | Evidence |
|---|---|---|
| Service instance | | |
| Component | | |
| Source type | | |

Then decide:

- Can auto-mapping handle it?
- Does it need a JavaScript mapping function?
- Does it need AI-assisted mapping (Otto for ITOM)?
- What would make the mapping wrong?

---

## Part C — Configure the data input (20 min)

1. Open the HLA data input configuration.
2. Create the input from Part A.
3. Set the service instance.
4. Configure the source type/format.
5. Use **Test mode** before publishing.
6. Verify the parsed fields and tags.
7. Publish and exit Test mode.

Record:

| Item | Value |
|---|---|
| Data input name | |
| Service instance | |
| Parsed fields | |
| Mapping method | |
| Test mode result | |

---

## Part D — Define an anomaly rule (15 min)

Choose one:

- a lexical keyword threshold (`failed`, `crashed`, `timeout`),
- an alert metric threshold,
- a custom alert rule.

Write:

| Item | Value |
|---|---|
| Rule type | |
| Condition | |
| Severity | |
| Expected event | |
| Expected alert | |

Then trigger or simulate the condition.

---

## Part E — Verify the signal (15 min)

Check:

- [ ] The log line is ingested.
- [ ] It maps to the right service instance/component/source type.
- [ ] The anomaly produces an event.
- [ ] Event Management produces an alert.
- [ ] The alert is bound to the right CI/service.
- [ ] The severity matches the mapping table.
- [ ] The alert has an owner.

If no alert:

| Check | Result |
|---|---|
| Data input healthy? | |
| Logs parsed? | |
| Mapping correct? | |
| Rule active? | |
| Severity mapped? | |
| Event Management rule match? | |

---

## Part F — Break the mapping (10 min)

Change the mapping so the component is wrong or missing. Re-ingest a sample.

Record:

1. What changed in the tags?
2. What changed in the alert?
3. How would an operator notice?
4. What would you fix first?

---

## Part G — Teach-back (5 min)

Explain:

1. What HLA does that Event Management does not.
2. The three tags.
3. Why Test mode matters.
4. One source of noise.
5. One thing that would make an alert useless.

---

## Design-only path

If HLA is not entitled:

1. Choose a source and input type.
2. Write the expected tags for three sample log lines.
3. Write the severity mapping for `INFO`, `WARN`, `ERROR`, `CRITICAL`.
4. Define one anomaly rule and the expected event/alert.
5. Write the binding to a service instance/CI.
6. List the missing prerequisites and the licence you would need.

---

## Pass test

You can show:

- one data input (or a complete design),
- three correctly mapped tags,
- one anomaly rule,
- one event/alert (or a predicted one with evidence),
- one broken mapping and its effect,
- a written explanation of the signal chain.

---

## Official sources

- Health Log Analytics — <https://www.servicenow.com/docs/r/australia/it-operations-management/health-log-analytics/hla-landing-page.html>
- Architecture — <https://www.servicenow.com/docs/r/australia/it-operations-management/health-log-analytics/hla-architecture.html>
- Supported data inputs — <https://www.servicenow.com/docs/r/australia/it-operations-management/health-log-analytics/hla-data-input-supported.html>
- Log data auto-mapping — <https://www.servicenow.com/docs/r/australia/it-operations-management/health-log-analytics/hla-data-input-automapping.html>
- How HLA generates alerts — <https://www.servicenow.com/docs/r/australia/it-operations-management/health-log-analytics/hla-op-anomalies-detecting.html>
- Severity mapping — <https://www.servicenow.com/docs/r/australia/it-operations-management/health-log-analytics/hla-severity-mapping.html>
