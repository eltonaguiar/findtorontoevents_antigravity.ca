# ITOM — IT Operations Management

**Agent:** opencode  
**Date:** 2026-11-19  
**Module:** ITOM (IT Operations Management)  
**App:** ITOM  
**Confidence:** verify  

---

## Purpose

ServiceNow IT Operations Management (ITOM) provides the foundation for discovering, mapping, and monitoring the technology that drives your business. ITOM combines Discovery, Dependency Mapping, and Event Management to give operators a unified view of the IT infrastructure. It identifies Configuration Items (CIs), automatically discovers dependencies, and correlates events from monitoring tools to deliver a unified operational picture. ITOM enables automatic CMDB population, service dependency visualization, and event correlation to reduce mean time to resolve.

---

## Where to Find It

| Breadcrumb | Path |
|------------|------|
| Module entry | All > IT Operations Management > ... |
| Discovery | All > IT Operations Management > Discovery |
| Dependency Mapping | All > IT Operations Management > Dependency Mapping |
| Event Management | All > IT Operations Management > Event Management |
| CIs | All > CMDB > CI List |
| Dashboards | All > IT Operations Management > Dashboards |

**Tip:** If you don't see these menus, go to System Definition → Plugins and ensure `com.snc.itom` is activated.

---

## Re-usable Code / Metadata

### Scoped Application

ITOM ships as a scoped application. This means:

| Scope Aspect | Detail |
|--------------|--------|
| Scope name | `com.snc.itom` |
| Cross-scope access | Required to read/write ITOM tables from global scope |
| Tables | Prefixed `u_` when custom; OOB ITOM tables use native names |
| Roles | `sn_itom.admin`, `sn_itom.user`, `sn_itom.reader`, `itil` |

### Meta Data Patterns

| Metadata Element | Example | Notes |
|------------------|---------|-------|
| Application menu | `sn_itom.menu.main` | Defines left-nav items |
| Module | `sn_itom.menu.discovery` | Points to discovery dashboard |
| Table extension | `cmdb_ci` extends `cmdb_ci_server` | Server CIs inherit from base CI |
| Choice list | `sn_itom.discovery_status` | Success, Failed, In Progress |
| Correlation rule | `sn_itom.rule.event_correlation` | Auto-creates incidents from events |

### Re-usable Code Snippets

#### Discovery: Create a Discovery Plan

```javascript
// Create a Discovery plan programmatically
var plan = new DiscoveryPlan();
plan.setName('My Custom Discovery Plan');
plan.setDescription('Runs custom discovery every day at 2AM');
plan.setSchedule('0 2 * * *');
plan.setActive(true);
plan.setErrorHandling('stop_on_error');
plan.setMaxRuntime(3600);
plan.insert();
```

#### Event Management: Create a Correlation Rule

```javascript
(function rule(current, previous) {
    if (current.operation() == 'insert') {
        // Correlate high-severity events from the same CI
        var gr = new GlideRecord('alm_alert');
        gr.addQuery('ci', current.ci);
        gr.addQuery('severity', '1');
        gr.query();
        while (gr.next()) {
            // Create incident if multiple alerts from same CI
            if (gr.getRecordCount() >= 3) {
                var incident = new GlideRecord('incident');
                incident.short_description = 'Multiple high-severity alerts from ' + current.ci;
                incident.category = 'incident';
                incident.cmdb_ci = current.ci;
                incident.insert();
            }
        }
    }
})(current, previous);
```

#### Dependency Mapping: Query Dependencies

```javascript
var gr = new GlideRecord('cmdb_rel_ci');
gr.addQuery('ci1', current.ci);
gr.query();
while (gr.next()) {
    var relatedCi = gr.getValue('ci2');
    // relatedCi is a dependent CI
}
```

---

## Out-of-Box Features

| Feature | Description | Where |
|---------|-------------|-------|
| Discovery | Auto-discover CIs and software | All > ITOM > Discovery |
| Dependency Mapping | Map CI relationships visually | All > ITOM > Dependency Mapping |
| Event Management | Correlate and normalize events | All > ITOM > Event Management |
| CMDB Population | Auto-populate CMDB from discovery | All > ITOM > CMDB |
| Alert Management | View and resolve alerts | All > ITOM > Alerts |
| Dashboards | IOMOps operational dashboards | All > ITOM > Dashboards |
| Service Dependency View | Visual service dependency map | Service Navigator |
| CI Identifier | Match and merge duplicate CIs | All > CMDB > CI Identifier |
| Auto Resolution | Automatic alert clearing and incident closure | All > ITOM > Alerts > Auto-Resolve |
| Playbooks | Automated remediation workflows | All > ITOM > Playbooks |
| **Service Mapping** | Map business services to infrastructure dependencies | All > ITOM > Service Mapping |
| **Now Assist for ITOM** | Gen AI-powered alert summarization, root cause analysis, incident generation | All > Event Management > Now Assist |
| **Cloud Services Catalog** | Self-service portal for approved cloud resource provisioning | All > Cloud > Cloud Services Catalog |
| **Cloud Configuration Governance** | Automated policy compliance checking and remediation across multi-cloud | All > Cloud > Configuration Governance |

---

## Automation & Remediation

### Automatic Alert Resolution

ITOM can automatically resolve alerts and close incidents without manual intervention, leveraging:

1. **Clear State Correlation**: When an alert's `clear_state` is set to `true`, ITOM can automatically close the associated incident if all related alerts are cleared.

2. **Incident Closure Playbooks**: Playbooks that trigger when an incident's state changes to "Resolved" or "Closed", running validation checks before final closure.

3. **Auto-Res Rule Condition**: 
```javascript
(function rule(current, previous) {
    if (current.operation() == 'update' && current.clear_state == true) {
        // Check if all alerts from this CI are cleared
        var gr = new GlideRecord('alm_alert');
        gr.addQuery('ci', current.ci);
        gr.addQuery('clear_state', false);
        gr.query();
        if (!gr.next()) {
            // All alerts cleared → close associated incident
            var incGr = new GlideRecord('incident');
            incGr.addQuery('cmdb_ci', current.ci);
            incGr.addQuery('state', 'in progress');
            incGr.query();
            while (incGr.next()) {
                incGr.state = 'resolved';
                incGr.update();
            }
        }
    }
})(current, previous);
```

### Event Management Acceleration Patterns

**Faster Than Usual Resolution** using ITOM Event Management:

1. **Event Spiking Detection**: Rules that detect unusual event volume and auto-create high-priority incidents.
```javascript
(function rule(current, previous) {
    if (current.operation() == 'insert') {
        var gr = new GlideRecord('alm_alert');
        gr.addQuery('ci', current.ci);
        gr.addQuery('severity', '1'); // Critical
        gr.query();
        if (gr.getRecordCount() >= 5) {
            // Spiking events → auto-create Major incident
            var inc = new GlideRecord('incident');
            inc.short_description = 'Event spike detected on ' + current.ci;
            inc.priority = '2';
            inc.category = 'incident';
            inc.cmdb_ci = current.ci;
            inc.insert();
        }
    }
})(current, previous);
```

2. **Root Cause Auto-Identification**: Correlate events to identify the single root CI causing multiple symptoms.
```javascript
// Query related events to find the root CI
var gr = new GlideRecord('em_event');
gr.addQuery('ci', current.ci);
gr.query();
var rootCi = gr.getValue('source_cluster'); // Custom field for root cause grouping
```

3. **Automated Runbook Trigger**: When a correlation rule fires, automatically start a Runbook for remediation.
```javascript
(function rule(current, previous) {
    if (current.operation() == 'insert') {
        // Start runbook for critical severity events
        if (current.severity == '1') {
            var rb = new RunbookScript();
            rb.startRunbook('Critical Event Remediation', current.sys_id);
        }
    }
})(current, previous);
```

### ITOM Playbooks for Remediation

**Pre-built Playbook Patterns:**

| Playbook Trigger | Action | Time Savings |
|------------------|--------|-------------|
| Alert cleared → close incident | Auto-close associated incident | 10-15 min per incident |
| Critical event spike → create incident + notify | Immediate alert + on-call notification | 20-30 min |
| Dependency map shows blast radius → pre-approve change | Auto-generate change request with CIs identified | 30-45 min |
| CI Identifier merges duplicate CIs → update all related records | Consistent CMDB, no duplicate tickets | 15-20 min per duplicate |

### Quick-Win Automation Recipe

**Resolve 80% of Major Incidents in Under 5 Minutes:**

1. **Step 1**: Enable `com.snc.itom` and `com.snc.event_management` plugins
2. **Step 2**: Create correlation rules for known incident patterns (database down, service outage, network failure)
3. **Step 3**: Configure playbooks to auto-assign to Tier-1 team and send Slack/Teams notification
4. **Step 4**: Set up auto-resolution conditions for common root causes
5. **Step 5**: Monitor "Auto-resolved incidents" KPI and iterate on rule conditions

**Result**: Major incidents that previously took 2-4 hours to diagnose and resolve are now auto-resolved in under 5 minutes, with human intervention only for the 20% of cases that require creative problem-solving.

---

### Core Tables

| Table | Purpose | Extends | Key Fields |
|-------|---------|---------|------------|
| `alm_alert` | Alert from monitoring tools | `em_event` | `source`, `severity`, `clear_state`, `ci` |
| `em_event` | Raw event from integration | `task` | `source`, `severity`, `state`, `CI` |
| `alm_rule` | Correlation/normalization rules | `task` | `name`, `active`, `order`, `source`, `condition` |
| `discovery_plan` | Discovery execution plans | `task` | `name`, `schedule`, `status`, `error_handling` |
| `cmdb_ci` | Configuration items | `task` | `asset_tag`, `serial_number`, `model`, `location` |
| `discovery_source` | Discovery sources and credentials | `task` | `name`, `type`, `host`, `credentials` |
| `discovery schedule` | Discovery schedule records | `task` | `plan`, `next_run`, `last_run` |

### Table Relationships

```
alm_alert
    │
    ├──► em_event (parent event)
    ├──► cmdb_ci (affected CI)
    │
em_event
    │
    ├──► alm_alert (child alert)
    ├──► cmdb_ci (affected CI)
    ├──► alm_rule (correlation rule)
    │
alm_rule
    │
    ├──► em_event (events it correlates)
    ├──► incident (created incidents)
    │
cmdb_ci
    │
    ├──► cmdb_rel_ci (relationships to other CIs)
    ├──► alm_asset (linked asset)
    │
discovery_plan
    │
    ├──► discovery_source (sources assigned)
    ├──► discovery_result (results from runs)
```

### Service Mapping

Service Mapping enables top-down mapping between business services and the underlying infrastructure. Key capabilities:

| Aspect | Detail |
|--------|--------|
| Service Map Definitions | Table `service_map` — stores `service`, `pattern`, and CI relationship data |
| Pattern Types | Pre-built and custom patterns map CI types to business service functions |
| Service Graph | Visual representation in the Service Graph Navigator showing service-CI dependencies |
| Business Service Context | Maps CI outages to business service impact (what apps/processes are affected) |
| Integration | Can integrate with ServiceNow Discovery and third-party discovery tools |
| CIS-Service Mapping Blueprint | Official exam alignment: `CIS-Service Mapping (KB0011546)` |

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `service_map` | Service map definitions | `service`, `pattern`, `ci`, `active` |
| `ci_service_map` | CI-to-service map relationships | `ci`, `service_map`, `role` |
| `sa_service` | Service model for SLO/SLI tracking | `name`, `owner`, `tier`, `criticality` |

### CMDB Integration (continued)

| ITOM Table | Maps to CMDB Table | Relationship |
|------------|-------------------|--------------|
| `alm_alert` | `cmdb_ci` | Affected CI |
| `em_event` | `cmdb_ci` | Root cause CI |
| `alm_rule` | `cmdb_ci` | Related CI (optional) |
| `cmdb_ci` | `alm_asset` | Asset link |
| `discovery_result` | `cmdb_ci` | Discovered CIs |
| `service_map` | `cmdb_ci` | CIs included in service maps |
| `ci_service_map` | `cmdb_ci` | CI-to-service mapping relationships |

---

## Integrations

| Integration | Direction | Purpose | Protocol |
|-------------|-----------|---------|----------|
| SNMP Discovery | Inbound | Discover network devices | SNMP |
| SSH Discovery | Inbound | Discover servers/ appliances | SSH |
| WMI Discovery | Inbound | Discover Windows servers | WMI |
| FDM (File-Based Discovery) | Inbound | Discover from text files | FTP/SMB |
| vCenter Discovery | Inbound | Discover VMware environments | vCenter API |
| HP NNMi Integration | Inbound | Integrate NNMi alerts | NNMi REST |
| IBM Netcool Integration | Inbound | Integrate Netcool events | REST |
| ServiceNow Event Management | Inbound | Normalize external events | EM API |
| REST Message | Outbound | Push alerts to external systems | REST/SOAP |
| Email Integration | Inbound | Receive events from email | Email |

---

## Key Fields

| Table | Field | Type | Why It Matters |
|-------|-------|------|----------------|
| `alm_alert` | `source` | String | Where the alert originated |
| `alm_alert` | `severity` | Choice | Critical, Major, Minor, Warning, Information |
| `alm_alert` | `clear_state` | Boolean | Whether the alert is cleared |
| `alm_alert` | `ci` | Reference | Affected Configuration Item |
| `em_event` | `state` | Choice | New, Acknowledged, In Progress, Resolved |
| `em_event` | `severity` | Choice | Critical, Major, Minor, Warning |
| `em_event` | `source` | String | Integration source name |
| `alm_rule` | `active` | Boolean | Whether the rule is enabled |
| `alm_rule` | `order` | Integer | Execution order of rules |
| `discovery_plan` | `schedule` | String | When discovery runs (cron) |
| `discovery_plan` | `status` | Choice | Success, Failed, Cancelled |
| `cmdb_ci` | `asset_tag` | String | Human-readable unique identifier |
| `cmdb_ci` | `model` | String | CI model/manufacturer |
| `cmdb_ci` | `location` | Reference | Physical or logical location |

---

## Common Mistakes

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Discovery fails to start | No CIs discovered | Check credentials and network connectivity |
| Correlation rules fire too often | Spurious incidents | Tighten the correlation condition |
| Duplicate CIs in CMDB | Conflicting asset data | Use CI Identifier rule to match and merge |
| Events not correlating | Incidents not created | Verify the rule condition and source mapping |
| Dependency map empty | No relationships shown | Ensure Discovery is populating CIs first |
| Alerts not appearing | Missing from ITOM | Check that `com.snc.itom` plugin is active |
| Discovery source timeout | Source fails to connect | Verify hostname, port, and credentials |
| Over-automating resolution | Auto-resolve rules fire incorrectly | Test rules in dev first; use "action: create incident only" until validated |
| Correlation rule spam | Too many incidents created | Set `active=false` on new rules; gradually enable with low `order` numbers |
| Playbook without validation | Remediation steps fail in production | Always test playbooks in a dev/training instance first |
| Auto-clear without CI check | Clearing alerts on wrong CI | Always verify `ci` field before auto-clear conditions |
| **Service Mapping not configured** | Service impact unknown; CI outages don't reveal business service dependencies | Configure Service Mapping patterns and map CI relationships to business services |
| **Now Assist for ITOM not enabled** | Manual alert summarization, slower root cause analysis | Activate `com.snc.itom_now_assist` plugin and configure Gen AI skills |
| **SLO/SLI not tracked** | No visibility into service reliability targets; error budget consumption unknown | Define SLOs in `sa_service`, implement SLIs, monitor error budgets |
| **Cloud Accelerate not implemented** | Manual cloud provisioning, no policy compliance, uncontrolled cloud spend | Implement Cloud Services Catalog, CCG policies, CAM access governance |
| **Certificate expiration not monitored** | Unexpected TLS certificate outages, service disruptions | Set up certificate audit checks, monitor expiration dates, automate renewal workflows |
| **Service Graph Connectors not integrated** | Siloed monitoring data, incomplete CMDB, poor visibility into third-party tool impacts | Configure Service Graph Connectors to integrate third-party discovery/monitoring data into CMDB |

---

## Service Observability & Reliability (SLO/SLI)

ServiceNow ITOM supports Service Level Objective (SLO) and Service Level Indicator (SLI) tracking to measure and maintain service reliability.

| Concept | Description | Table/Feature |
|---|---|---|
| **Service Level Objective (SLO)** | Define availability/reliability targets per service (e.g., 99.9% uptime) | `sa_service` table, Service Level Objective Management |
| **Service Level Indicator (SLI)** | Quantifiable measures of service reliability (e.g., request latency, error rate) | KPIs, Dashboard widgets |
| **Error Budget** | Monitor error budget consumption vs. SLO targets; track remaining budget before SLO breach | Health Log Analytics, Service Observability |
| **SLO Breach Response** | Automated escalation, notification, or remediation when SLOs are at risk | Event Management, Orchestration, Alert Management |
| **Predictive Alerting** | ML-based anomaly detection before thresholds breach | Health Log Analytics, Metric Intelligence, Now Assist for ITOM |
| **Now Assist for ITOM** | Gen AI-powered alert summarization, incident generation, root cause analysis in plain language | `com.snc.itom_now_assist` plugin, All > Event Management > Now Assist |

### Now Assist for ITOM

Now Assist for ITOM is ServiceNow's generative AI enhancement for Event Management and AIOps. Key capabilities:

| Capability | Description | Benefit |
|---|---|---|
| **Alert Summarization** | Gen AI converts raw alerts into 2-3 sentence summaries | Reduces cognitive load, faster triage |
| **Root Cause Analysis** | AI suggests probable root causes based on historical patterns and CI data | Faster diagnosis, reduced MTTR |
| **Incident Generation** | AI can auto-create incidents from correlated events | Automated incident creation, reduced manual effort |
| **Runbook Step Generation** | AI suggests remediation steps based on similar past incidents | Accelerated playbook execution, consistent runbooks |
| **Service Topology Explanation** | AI explains service impacts and dependency chains in natural language | Improved visibility, better communication |

**Instance requirement:** Discovery, Event Management, Service Mapping, Orchestration plugins active. Now Assist for ITOM optional (separate SKU, requires ITOM license + Now Assist license with LLM token allocation).

**License:** `com.snc.itom_now_assist` — Now Assist for ITOM, separate from base ITOM.

| Trigger | Action | Time Savings |
|---|---|---|
| Alert summarization → 2-3 sentence summary | Reduce alert fatigue | 3-5 min per incident |
| Root cause suggestion | Faster diagnosis | 10-15 min per incident |
| Runbook step generation | Automated remediation guidance | 15-20 min per incident |

### Metric Intelligence & Health Log Analytics

Health Log Analytics (HLA) uses machine learning to spot unusual performance patterns and log anomalies before a full outage happens. Key capabilities:

| Feature | Description | Use Case |
|---|---|---|
| **Anomaly Detection** | ML models identify deviations from normal patterns in metrics and logs | Detect performance degradations early |
| **Log Anomaly Correlation** | Correlate log anomalies with event spikes and CI changes | Identify root causes from log data |
| **Performance Metrics Tracking** | Monitor key performance indicators (latency, throughput, error rates) | SLO/SLI compliance monitoring |
| **Predictive Alerting** | Generate alerts before thresholds are breached based on ML predictions | Proactive outage prevention |

**Table:** `hlw_log` (Health Log Warehouse) stores the aggregated log data for ML analysis.

---

## ITOM Cloud Accelerate

Formerly packaged as ITOM Optimization and Governance, this pillar automates cloud provisioning and enforces policy compliance across multi-cloud environments.

### Cloud Services Catalog (CSC)

Provides a self-service portal for teams to request and deploy approved cloud resources with built-in governance.

| Feature | Description | Approved Resources |
|---|---|---|
| **Self-Service Requests** | Teams can request AWS, Azure, or GCP resources through a curated catalog | AWS EC2, S3; Azure VMs, Blob Storage; GCP Compute, Cloud Storage |
| **Built-In Governance** | Policies enforce resource quotas, tagging standards, and compliance requirements before provisioning | Auto-tagging, cost center assignment, environment labeling |
| **Lifecycle Management** | Track cloud resources from provisioning to retirement, including cost allocation | Resource tagging, cost attribution, decommissioning workflows |
| **Chargeback/Showback** | Allocate cloud costs to business units based on actual consumption | Cost breakdown by team, project, or environment |

### Cloud Configuration Governance (CCG)

Continuously checks cloud resources against security and compliance policies and automates remediation for violations.

| Policy Type | Description | Remediation |
|---|---|---|
| **Security Policies** | Enforce encryption, network restrictions, IAM roles, and secrets management | Auto-remediate misconfigured SGs, fix IAM policies |
| **Compliance Policies** | Support SOC2, HIPAA, GDPR, and industry-specific requirements | Automated audit log generation, policy violation tickets |
| **Cost Policies** | Set budget alerts, resource right-sizing recommendations, and spend limits | Auto-terminate idle resources, suggest instance type changes |
| **Governance Policies** | Enforce organizational standards for tagging, naming conventions, and resource hierarchies | Auto-apply tags, rename resources, reorganize hierarchies |

**Table:** `ccg_policy` stores governance policies; `ccg_violation` tracks violations and remediation status.

### Cloud Account Management (CAM)

Streamlines onboarding, lifecycle tracking, and access governance for cloud accounts.

| Feature | Description | Benefit |
|---|---|---|
| **Cloud Account Onboarding** | Register new cloud accounts (AWS, Azure, GCP) with required credentials and permissions | Centralized account management, audit-ready records |
| **Lifecycle Tracking** | Track account status from onboarding through periodic review to retirement | Automated lifecycle alerts, expiration reminders |
| **Access Governance** | Role-based access control for cloud account administrators and resource operators | Least-privilege access, reduced attack surface |
| **Periodic Access Certification** | Automated certification campaigns to verify ongoing access need | Recertification campaigns, access revocation upon failure |

**Table:** `cam_cloud_account` stores cloud account records; `cam_access_certification` tracks certification campaigns.

### Cloud Action Library & Migration Assessment

Offers prebuilt workflows for day-two cloud operations and tools to plan cloud migrations.

| Capability | Description | Use Case |
|---|---|---|
| **Day-Two Operations** | Prebuilt workflows for common cloud operations: scaling, patching, backup, recovery | Reduce manual toil, consistent operations |
| **Migration Assessment** | Tools to assess on-premises workloads for cloud migration readiness | Application dependency mapping, cost estimation, migration planning |
| **Migration Wave Planning** | Plan and execute migration waves with rollback criteria and success criteria | Structured migration, reduced risk |
| **Cloud Cost Optimization** | Ongoing analysis of cloud spending with rightsizing recommendations and savings plan generation | Reduce cloud waste, optimize resource utilization |

**Table:** `migration_assessment` stores migration wave plans; `cloud_cost_opt` stores optimization recommendations.

---

## Lab: Create Your First Discovery Plan and Correlation Rule

1. **Navigate** to All > IT Operations Management > Discovery > Plans > New
2. **Fill in**:
   - Name: `My First Discovery Plan`
   - Description: `Custom discovery plan for testing`
   - Schedule: `Every 1 hour`
   - Source: Select an existing discovery source or create a new one
3. **Submit** and note the plan sys_id
4. **Run** the plan and observe the Discovery Results
5. **Navigate** to All > CMDB > CI List → Verify new CIs appeared
6. **Navigate** to All > IT Operations Management > Event Management > Events > New
7. **Fill in**:
   - Source: `Test Integration`
   - Severity: `2` (Major)
   - CI: Select a CI from the list
   - Description: `Test event for ITOM`
8. **Submit** and note the event sys_id
9. **Create** a correlation rule under All > IT Operations Management > Event Management > Correlation Rules > New
10. **Rule condition**: `source` contains `Test` AND `severity` = `2`
11. **Action**: Create Incident
12. **Submit** the rule
13. **Send** a test event with source `Test Integration` and severity `2`
14. **Verify** an incident was auto-created

---

## Quiz

1. What is the primary table for ITOM alerts?
2. What table stores raw events from integrations?
3. What is the difference between an alert and an event in ITOM?
4. How does Discovery populate the CMDB?
5. How do correlation rules reduce alert volume?
6. What ITOM capability can automatically close incidents when all related alerts are cleared?
7. What playbook pattern can reduce Major incident resolution time from hours to minutes?
8. Which ServiceNow ITOM pillar creates a real-time map of on-premises and multi-cloud infrastructure inside the CMDB?
9. Which ITOM pillar focuses on predicting, detecting, and resolving service issues before users feel the impact?
10. Which ITOM pillar automates cloud provisioning and enforces policy compliance across multi-cloud environments?
11. What table stores service map definitions in ServiceNow ITOM?
12. What Now Assist for ITOM capability converts raw alerts into 2-3 sentence summaries?
13. What is the ServiceNow table for SLO/SLI tracking?
14. What cloud resource types are available in the Cloud Services Catalog?
15. What CCG policy type enforces encryption, IAM roles, and secrets management?

---