# Metric Intelligence

**Agent:** Kilo (deepseek-flash) · **Updated:** 2026-11-19 · **App:** Metric Intelligence · **Confidence:** high (official docs)

Metric Intelligence watches metric history and flags behaviour that is abnormal for a specific
CI. It catches the slow drift that an event threshold misses: the disk that is filling faster
than usual, the queue that is growing, the response time that is creeping.

It is a complement to Event Management, not a replacement.

---

## Contents

- [Purpose](#purpose)
- [ELI5](#eli5)
- [Where to find it](#where-to-find-it)
- [How it works](#how-it-works)
- [What you configure](#what-you-configure)
- [Roles](#roles)
- [How it fits with events and SLOs](#how-it-fits-with-events-and-slos)
- [Common mistakes](#common-mistakes)
- [Quiz](#quiz)
- [Official sources](#official-sources)
- [Related guides](#related-guides)

---

## Purpose

Metric Intelligence helps identify and prevent potential service outages. Based on historical
metric data, it indicates anomalous behaviour of CIs that events might not capture.

Two detection styles are described in the official content:

- **Unsupervised machine learning** — abnormal pattern detection with no user intervention.
- **Deterministic alert rules** — a static threshold you set manually.

You can use either or both, depending on the metric and the consequence of being wrong.

---

## ELI5

A heart-rate monitor beeps when the rate crosses a fixed line. That is an event threshold.

A doctor looks at the trend and says, "this rate is normal for most people, but abnormal for
this patient." That is Metric Intelligence.

It knows the CI's normal, not just the global normal.

---

## Where to find it

| Task | Breadcrumb |
|---|---|
| Metric definitions | `All > Metric Intelligence > ...` (label varies) |
| Connector settings | Metric Intelligence configuration |
| Metric rules | Metric Intelligence rules |
| Metric Explorer | Metric Intelligence / SOW views |

Use the official docs search if the Store app labels differ on your instance.

---

## How it works

```mermaid
flowchart LR
    SRC[Metric sources<br/>ACC · connectors · MetricBase] --> DEF[Metric definitions]
    DEF --> HIST[Historical baseline]
    HIST --> DET{Anomaly?}
    DET -- ML -- yes --> ALERT[Alert]
    DET -- rule -- yes --> ALERT
    ALERT --> EM[Event Management]
    HIST --> EXPLORE[Metric Explorer]
```

1. A metric source supplies data for a CI.
2. A metric definition says what the metric is and how to interpret it.
3. The system learns or applies a threshold.
4. An anomaly produces an alert.
5. The alert follows the Event Management pipeline (mapping, binding, grouping, response).
6. Operators use Metric Explorer to see the raw metric behind the alert.

---

## What you configure

| Element | What it decides |
|---|---|
| **Metric definition** | The metric identity, source, and interpretation |
| **Connector settings** | Where the metric data comes from |
| **Metric rule** | The condition that should produce an alert (static threshold, or anomaly-based) |
| **Alert properties** | Severity, description, and the fields the operator sees |
| **Significance / noise controls** | Which anomalies are worth promoting |

Start with a metric you can explain and a consequence you can tolerate. Then widen.

---

## Roles

| Role | Scope |
|---|---|
| `evt_mgmt_admin` | Configure metric definitions and connector settings |
| `evt_mgmt_operator` | View metric definitions and connector settings |
| `evt_mgmt_user` | View alerts and their underlying metrics |

If your instance uses a different role for Metric Intelligence, follow the product's reference
page.

---

## How it fits with events and SLOs

| Tool | Detects | Best for |
|---|---|---|
| **Event Management** | Discrete events and thresholds from monitoring tools | Known failure conditions |
| **Metric Intelligence** | Abnormal metric behaviour against history | Slow drift and unusual patterns |
| **Health Log Analytics** | Abnormal log patterns | Log-only signals |
| **SLO Management** | Whether the service promise is at risk | Business-level reliability |

A mature design uses all four where they add signal, and suppresses the rest.

---

## Common mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| Turning on anomaly detection for every metric | Alert noise | Start with business-critical CIs and a few metrics |
| No baseline | False anomalies during normal peaks | Allow a learning period; exclude known events |
| Static threshold copied from a dashboard | Wrong for the CI's normal | Use history or a per-CI rule |
| No CMDB binding | Alert lacks context | Ensure metrics map to CIs |
| Ignoring Metric Explorer | Operators cannot verify the alert | Train operators to inspect the raw metric |
| Duplicating Event Management thresholds | Two alerts for one condition | Choose one detection path per condition |

---

## Quiz

1. **What does Metric Intelligence use to decide what is abnormal?**
   <details><summary>Answer</summary>Historical metric data for the CI, using ML anomaly detection and/or deterministic rules.</details>

2. **How is it different from Event Management?**
   <details><summary>Answer</summary>Event Management processes discrete events and thresholds; Metric Intelligence looks for abnormal metric behaviour that events may not capture.</details>

3. **What is Metric Explorer for?**
   <details><summary>Answer</summary>Viewing the raw metric data behind an alert so an operator can verify and investigate.</details>

4. **Which role configures metric definitions?**
   <details><summary>Answer</summary>`evt_mgmt_admin` in the documented model.</details>

---

## Official sources

- Exploring Metric Intelligence — <https://www.servicenow.com/docs/r/australia/it-operations-management/metric-intelligence/exploring-metric-intelligence.html>
- Configuring Metric Intelligence — <https://www.servicenow.com/docs/r/australia/it-operations-management/metric-intelligence/configuring-metric-intelligence.html>
- Optimizing Metric Intelligence — <https://www.servicenow.com/docs/r/australia/it-operations-management/metric-intelligence/optimizing-metric-intelligence.html>
- Metric Intelligence reference — <https://www.servicenow.com/docs/r/australia/it-operations-management/metric-intelligence/metric-intelligence-reference.html>
- Event Management — <https://www.servicenow.com/docs/r/australia/it-operations-management/event-management/c_EM.html>

---

## Related guides

- [Event Management](../event-management/event-management-guide.md)
- [Health Log Analytics](../health-log-analytics/health-log-analytics-guide.md)
- [Reliability stack](../reliability-stack/reliability-stack-guide.md)
- [Agent Client Collector](../agent-client-collector/acc-guide.md)
