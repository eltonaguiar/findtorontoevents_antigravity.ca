# Getting Started with Event Management

**Agent:** Kilo  
**Date:** 2026-11-19  
**Module:** Event Management  
**Prerequisites:** CMDB Foundation, Discovery (for CI Binding)  
**Confidence:** high  

---

## Contents

- [Learning Objectives](#learning-objectives)
- [Prerequisites](#prerequisites)
- [Core Concepts](#core-concepts)
- [Event Flow Architecture](#event-flow-architecture)
- [Step-by-Step Setup](#step-by-step-setup)
- [Hands-On Labs](#hands-on-labs)
- [Troubleshooting Guide](#troubleshooting-guide)
- [Verification Checklist](#verification-checklist)
- [Next Steps](#next-steps)

---

## Learning Objectives

By completing this guide, you will be able to:

1. **Explain** the Event → Transform → Bind → Correlate → Alert flow
2. **Configure** Event Rules for each phase
3. **Implement** CI Binding using node/component/CI identifier
4. **Create** Correlation Rules (time-based, topology-based, field-based)
5. **Manage** Alerts through lifecycle (acknowledge, resolve, close)
6. **Leverage** Now Assist for summarization, RCA, incident generation

---

## Prerequisites

| Requirement | Status |
|-------------|--------|
| CMDB Foundation completed | ✅ |
| Discovery populated CIs (for binding) | ✅ |
| `evt_mgmt_admin` role | ✅ |
| Event source (monitoring tool, REST API) | 🔄 Prepare |

---

## Core Concepts

### Event Flow (Memorize This)

```
EXTERNAL SOURCE
      │
      ▼
┌─────────────┐
│   EVENT     │  ← Raw event lands here (em_event)
│  [em_event] │
└──────┬──────┘
       │ Transform Rules
       ▼
┌─────────────┐
│  TRANSFORM  │  ← Normalize fields, enrich, categorize
│  [em_event] │
└──────┬──────┘
       │ Bind Rules
       ▼
┌─────────────┐
│    BIND     │  ← Map to CMDB CI (node, component, CI identifier)
│  [em_event] │
└──────┬──────┘
       │ Correlate Rules
       ▼
┌─────────────┐
│  CORRELATE  │  ← Group related events (time, topology, fields)
│  [em_event] │
└──────┬──────┘
       │ Alert Rules
       ▼
┌─────────────┐
│   ALERT     │  ← Actionable notification (em_alert)
│  [em_alert] │
└─────────────┘
```

**Mnemonic:** **T**ransform **B**inds **C**orrelates **A**lerts — **TBCA** — **T**o **B**e **C**ertain **A**lways

### Key Tables

| Table | Purpose |
|-------|---------|
| `em_event` | Raw and processed events |
| `em_alert` | Actionable alerts (created from correlated events) |
| `em_event_rule` | Transform, Bind, Correlate, Alert rules |
| `em_alert_rule` | Alert management (severity, auto-close, notifications) |
| `em_correlation_rule` | Correlation definitions |

---

## Event Flow Architecture

### Event Fields (Critical for Binding)

| Field | Description | Example |
|-------|-------------|---------|
| `source` | Monitoring system name | `SolarWinds`, `Datadog`, `Custom` |
| `node` | Hostname/FQDN of originating system | `web01.prod.example.com` |
| `component` | Application/service component | `Apache`, `MySQL`, `CPU` |
| `resource` | Specific resource | `/dev/sda1`, `eth0`, `jvm_memory` |
| `type` | Event category | `Performance`, `Availability`, `Configuration` |
| `severity` | 1=Critical, 2=Major, 3=Minor, 4=Warning, 5=Info | `1` |
| `description` | Human-readable message | `CPU usage 98% for 15 minutes` |
| `additional_info` | JSON payload with extra data | `{"metric": "cpu", "value": 98}` |

---

## Step-by-Step Setup

### 1. Configure Event Source Integration

**Option A: REST API (Generic)**
```bash
# Send test event
curl -X POST "https://devXXXXX.service-now.com/api/em/event" \
  -H "Authorization: Basic <credentials>" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "TestSource",
    "node": "web01.prod.example.com",
    "component": "CPU",
    "type": "Performance",
    "severity": 1,
    "description": "CPU usage 98% for 15 minutes",
    "additional_info": "{\"metric\":\"cpu\",\"value\":98}"
  }'
```

**Option B: MID Server Event Connector** (for tools like SolarWinds, Nagios)
- **All > Event Management > Connectors > New**
- Configure connector for your monitoring tool

### 2. Create Transform Rules

**All > Event Management > Rules > Transform Rules > New**

| Field | Example |
|-------|---------|
| **Name** | `Normalize CPU Events` |
| **Order** | `100` |
| **Source** | `TestSource` |
| **Condition** | `component=CPU` |
| **Script** | `event.severity = parseInt(event.severity);` |

**Common Transforms:**
- Map external severity → ServiceNow severity (1-5)
- Enrich with CMDB data (lookup CI by node)
- Set `event_class` for routing

### 3. Create Bind Rules (Critical)

**All > Event Management > Rules > Bind Rules > New**

| Field | Example |
|-------|---------|
| **Name** | `Bind by Node to Linux Server` |
| **Order** | `100` |
| **Source** | `TestSource` |
| **Condition** | `node IS NOT NULL` |
| **CI Identifier** | `name` (matches `cmdb_ci.name`) |
| **CI Class** | `cmdb_ci_linux_server` |
| **Field Mapping** | `node → name` |

**Bind Strategies (in order):**
1. **CI Identifier** — Direct match (sys_id, correlation_id)
2. **Node + Class** — Match `node` to `cmdb_ci.name` for specific class
3. **Component + Node** — Match component to CI relationship
4. **Tag-based** — Match via CI tags (cloud resources)

### 4. Create Correlation Rules

**All > Event Management > Rules > Correlation Rules > New**

#### Time-Based Correlation
| Field | Value |
|-------|-------|
| **Name** | `Time-based: Same CI, 5 min window` |
| **Type** | `Time` |
| **Time Window** | `300` (seconds) |
| **Group By** | `ci` (or `node` if no CI) |

#### Topology-Based Correlation
| Field | Value |
|-------|-------|
| **Name** | `Topology: Parent-Child relationship` |
| **Type** | `Topology` |
| **Relationship Types** | `Contains::Contained by`, `Runs on::Runs`, `Virtualized on::Virtualizes` |
| **Direction** | `Upstream` (child alerts correlate to parent) |

#### Field-Based Correlation
| Field | Value |
|-------|-------|
| **Name** | `Field-based: Same application` |
| **Type** | `Field` |
| **Fields** | `component`, `resource` |

### 5. Create Alert Rules

**All > Event Management > Rules > Alert Rules > New**

| Field | Example |
|-------|---------|
| **Name** | `Critical Alert - Auto Create Incident` |
| **Condition** | `severity = 1` |
| **Alert Fields** | `short_description: ${event.description}` |
| **Auto Close** | `true` (with resolution event) |
| **Notification** | `IT Operations` group |

---

## Hands-On Labs

### Lab 1: Send First Event (15 min)

1. **Use REST API** (see Step 1 above) to send test event
2. **Verify:** `All > Event Management > Events` → New event appears
3. **Check Fields:** `source`, `node`, `component`, `severity`, `description`

### Lab 2: Transform Rule (20 min)

1. **Create Transform Rule** to map severity string → integer
2. **Send Event** with `severity: "Critical"`
3. **Verify:** Event `severity` field = `1` (integer)

### Lab 3: CI Binding (30 min)

1. **Prerequisite:** Discovery has created `cmdb_ci_linux_server` named `web01.prod.example.com`
2. **Create Bind Rule:** `node → name` for `cmdb_ci_linux_server`
3. **Send Event** with `node: "web01.prod.example.com"`
4. **Verify:** Event `ci` field populated with CI `sys_id`
5. **Test Failure:** Send event with unknown node → `ci` empty, check `binding_failed` reason

### Lab 4: Time-Based Correlation (30 min)

1. **Create Correlation Rule:** Time-based, 5 min window, Group by `ci`
2. **Send 3 Events** within 2 minutes: same `node`, different `component` (CPU, Memory, Disk)
3. **Verify:** Events grouped → Single Alert created
4. **Check Alert:** `em_alert` has `event_count = 3`, `related_events` list

### Lab 5: Topology-Based Correlation (30 min)

1. **Prerequisite:** Service Mapping created topology: DB → App → Web
2. **Create Correlation Rule:** Topology, Upstream, `Runs on::Runs`
3. **Send Event** on DB (component: Database, severity: 1)
4. **Send Event** on App (component: Tomcat, severity: 2) — within correlation window
4. **Verify:** Both events correlate → Single Alert with `root_cause_ci = DB`

### Lab 6: Alert Management (20 min)

1. **Open Alert Console:** `All > Event Management > Alert Console`
2. **Filter:** `State = New`
3. **Acknowledge** alert → State → `In Progress`
4. **Assign** to yourself
5. **Resolve** → State → `Resolved`
6. **Auto-Close:** Send resolution event (severity 5) → Alert → `Closed`

### Lab 7: Now Assist Integration (30 min)

1. **Prerequisite:** Now Assist for ITOM active, Guardrails configured
2. **Open Alert Console** → Select correlated alert group (5+ events)
3. **Click Now Assist Panel** → **Summarize**
4. **Verify Output:** Service-level summary, root cause hypotheses
5. **Click Analyze Root Cause** → Review hypotheses with confidence
6. **Click Create Incident** → Verify Incident auto-populated:
   - `short_description`
   - `description` (with context)
   - `cmdb_ci` (probable root cause)
   - `business_service` (from topology)

---

## Troubleshooting Guide

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Events not appearing | Wrong API endpoint / auth | Verify REST URL, credentials, Content-Type |
| Binding fails (ci empty) | Node name mismatch / CI not in CMDB | Check `node` value vs `cmdb_ci.name`, run Discovery |
| No alerts created | No Alert Rule matches / Correlation groups but no alert rule | Create Alert Rule for severity, check correlation output |
| Too many alerts (no correlation) | Correlation rules missing / wrong grouping | Add Time/Topology/Field correlation rules |
| Alerts not auto-closing | No resolution event / Auto-close not configured | Send clearance event (severity 5), enable auto-close |
| Now Assist not showing | Skills not active / Guardrails blocking | Enable skills, check confidence threshold |
| Duplicate alerts | Multiple alert rules firing | Consolidate alert rules, use conditions |

### Debug Event Flow

```javascript
// Background Script - Trace event processing
var evt = new GlideRecord('em_event');
evt.addQuery('source', 'TestSource');
evt.orderByDesc('sys_created_on');
evt.setLimit(5);
evt.query();
while (evt.next()) {
    gs.log('Event: ' + evt.sys_id + ' | Node: ' + evt.node + ' | CI: ' + evt.ci + ' | State: ' + evt.state);
}
```

---

## Verification Checklist

- [ ] Events ingest via REST API (or connector)
- [ ] Transform Rules normalize severity, enrich fields
- [ ] Bind Rules resolve `node` to CMDB CI (`ci` field populated)
- [ ] Time-based correlation groups events within window
- [ ] Topology-based correlation uses Service Mapping relationships
- [ ] Alert Rules create actionable alerts from correlated events
- [ ] Alert lifecycle: New → Acknowledged → In Progress → Resolved → Closed
- [ ] Now Assist: Summarizes alert groups, provides RCA, generates incidents
- [ ] Auto-close works with resolution events

---

## Next Steps

1. **Complete** [Service Mapping Getting Started](../servicemapping.md) — enables topology correlation
2. **Complete** [Orchestration Getting Started](../orchestration.md) — auto-remediation from alerts
3. **Review** [Event Management Deep Dive Guide](../../docs/modules/eventmanagement/eventmanagement-guide.md)
4. **Practice** CIS-Event Management exam questions (KB0011604)

---

## Quick Reference Card

```
EVENT MANAGEMENT QUICK REFERENCE

Flow: Event → Transform → Bind → Correlate → Alert

Key Tables:
  em_event        → Events (raw + processed)
  em_alert        → Actionable alerts
  em_event_rule   → Transform/Bind/Correlate/Alert rules
  em_correlation_rule → Correlation definitions

Event Fields for Binding:
  node        → Hostname (matches cmdb_ci.name)
  component   → Application component
  resource    → Specific resource
  type        → Category
  severity    → 1=Critical ... 5=Info

Rule Types & Order:
  100-199  → Transform
  200-299  → Bind
  300-399  → Correlate
  400-499  → Alert

Correlation Types:
  Time       → Group by time window + field (ci, node)
  Topology   → Group by CMDB relationships (upstream/downstream)
  Field      → Group by matching field values

Bind Strategies (Priority):
  1. CI Identifier (sys_id, correlation_id)
  2. Node + CI Class
  3. Component + Node (via relationships)
  4. Tags (cloud resources)

Alert States:
  New → Acknowledged → In Progress → Resolved → Closed

Now Assist Skills:
  Alert Summarization    → Group summary + root causes
  Root Cause Analysis    → Ranked hypotheses with evidence
  Incident Generation    → Auto-populated incident
```

---

*Complete the labs in order. Use your PDI. Refer to the deep-dive guide for advanced topics.*