# Getting Started with Orchestration

**Agent:** Kilo  
**Date:** 2026-11-19  
**Module:** Orchestration  
**Prerequisites:** CMDB Foundation, Discovery (for target CIs), MID Server active  
**Confidence:** high  

---

## Contents

- [Learning Objectives](#learning-objectives)
- [Prerequisites](#prerequisites)
- [Core Concepts](#core-concepts)
- [Flow Designer vs Action Designer](#flow-designer-vs-action-designer)
- [Step-by-Step Setup](#step-by-step-setup)
- [Hands-On Labs](#hands-on-labs)
- [Troubleshooting Guide](#troubleshooting-guide)
- [Verification Checklist](#verification-checklist)
- [Next Steps](#next-steps)

---

## Learning Objectives

By completing this guide, you will be able to:

1. **Explain** Orchestration architecture: Flow Designer, Activities, MID Server
2. **Build** flows using SSH, PowerShell, REST, Script activities
3. **Create** reusable Actions for common operations
4. **Integrate** with Event Management for auto-remediation
5. **Use** Now Assist to generate runbooks from natural language
6. **Implement** approval gates for production safety

---

## Prerequisites

| Requirement | Status |
|-------------|--------|
| CMDB Foundation completed | ✅ |
| Discovery populated target CIs | ✅ |
| `orchestration_admin` role | ✅ |
| MID Server with SSH/WinRM capabilities | ✅ |
| Credentials for target systems | 🔄 |

---

## Core Concepts

### Orchestration Components

| Component | Purpose |
|-----------|---------|
| **Flow Designer** | Visual workflow builder (no-code/low-code) |
| **Action Designer** | Reusable action definitions (inputs/outputs) |
| **Activities** | Pre-built steps: SSH, PowerShell, REST, Script, etc. |
| **MID Server** | Executes activities on target systems |
| **Credentials** | Secure storage for target authentication |

### Activity Packs (Key Ones)

| Pack | Activities | Use For |
|------|------------|---------|
| **Core** | Script, Decision, Delay, Log | Flow logic |
| **SSH** | SSH Command, SSH Script | Linux/Unix/Network |
| **PowerShell** | PowerShell Command, Script | Windows |
| **REST** | REST Request, REST Step | API integrations |
| **ServiceNow** | Create/Update/Query Records | Platform operations |
| **Cloud** | AWS, Azure, GCP actions | Cloud management |

---

## Flow Designer vs Action Designer

| Aspect | Flow Designer | Action Designer |
|--------|---------------|-----------------|
| **Purpose** | End-to-end workflows | Reusable atomic operations |
| **Reusability** | Subflows | Actions (callable from flows) |
| **Inputs/Outputs** | Flow variables | Defined input/output schemas |
| **Versioning** | Flow versions | Action versions |
| **Use Case** | "Restart Tomcat on all app servers" | "Restart Tomcat on one server" |

**Best Practice:** Build **Actions** for single operations, compose into **Flows** for business processes.

---

## Step-by-Step Setup

### 1. Verify Activity Packs Installed

**All > Flow Designer > Spokes** — Check these are installed:
- `Core` (built-in)
- `SSH`
- `PowerShell`
- `REST`
- `ServiceNow`
- `Cloud Management` (if using cloud)

### 2. Create Credentials (if not from Discovery)

**All > Orchestration > Credentials** — Same as Discovery credentials:
- SSH (Linux)
- WinRM (Windows)
- SNMP (Network)
- API Key (Cloud/REST)

### 3. Test MID Server Connectivity

1. **All > MID Server > Servers** → Select your MID
2. **Test Connection** to target hosts
3. Verify capabilities: `ssh`, `powershell`, `rest`

---

## Hands-On Labs

### Lab 1: First Flow — Hello World (15 min)

1. **All > Flow Designer > Flows > New**
2. **Name:** `Hello World Test`
3. **Trigger:** `Manual` (no inputs)
4. **Add Core > Log** activity:
   - Message: `Hello from Orchestration!`
5. **Save** → **Test** → **Run**
6. **Verify:** Flow completes, log shows message

### Lab 2: SSH Activity — Linux Command (30 min)

**Prerequisite:** Linux target with SSH credentials in CMDB

1. **Create Flow:** `Run Linux Command`
2. **Trigger:** Manual → Add Input: `target_ip` (String), `command` (String)
3. **Add SSH > SSH Command** activity:
   - **MID Server:** Auto
   - **Target:** `{{trigger.target_ip}}`
   - **Credentials:** Select SSH credential (or reference from CI)
   - **Command:** `{{trigger.command}}`
   - **Timeout:** `60`
4. **Add Core > Log** to output result
5. **Test:** Run with `target_ip=10.0.1.50`, `command=uptime`
6. **Verify:** Flow returns uptime output

### Lab 3: PowerShell Activity — Windows Command (30 min)

**Prerequisite:** Windows target with WinRM credentials

1. **Create Flow:** `Run Windows Command`
2. **Trigger:** Manual → Inputs: `target_ip`, `command`
3. **Add PowerShell > PowerShell Command:**
   - **Target:** `{{trigger.target_ip}}`
   - **Credentials:** WinRM credential
   - **Command:** `{{trigger.command}}`
4. **Test:** Run with `Get-Service wuauserv` (Windows Update service)
5. **Verify:** Returns service status

### Lab 4: REST Activity — API Call (20 min)

1. **Create Flow:** `Call REST API`
2. **Trigger:** Manual → Inputs: `url`, `method`, `headers`, `body`
3. **Add REST > REST Request:**
   - **URL:** `{{trigger.url}}`
   - **Method:** `{{trigger.method}}`
   - **Headers:** `{{trigger.headers}}`
   - **Body:** `{{trigger.body}}`
4. **Test:** Call `https://httpbin.org/get` (GET)
5. **Verify:** Returns JSON response

### Lab 5: Create Reusable Action (30 min)

**Goal:** Encapsulate "Restart Service on Linux" as Action

1. **All > Flow Designer > Actions > New**
2. **Name:** `Restart Linux Service`
3. **Inputs:**
   - `target_ip` (String, required)
   - `service_name` (String, required)
   - `credentials` (Reference, `discovery_credentials`)
4. **Flow Logic:**
   - SSH Command: `sudo systemctl status {{service_name}}`
   - Decision: If active → SSH Command: `sudo systemctl restart {{service_name}}`
   - SSH Command: `sudo systemctl status {{service_name}}` (verify)
   - Output: `restarted` (Boolean), `status_output` (String)
5. **Save & Publish**
6. **Test:** Call from a Flow with test server

### Lab 6: Auto-Remediation from Alert (45 min)

**Prerequisite:** Event Management with alerts, target CI in CMDB

1. **Create Flow:** `Auto-Remediate High CPU`
2. **Trigger:** `Record` → Table: `em_alert`, Condition: `severity=1 AND cmdb_ci.sys_class_name=cmdb_ci_linux_server`
3. **Flow Logic:**
   - Get CI from alert: `alert.cmdb_ci`
   - Get CI IP: `ci.ip_address`
   - **Call Action:** `Restart Linux Service` (if service known) OR
   - **Script Activity:** Analyze `top` output, identify process
   - **Decision:** If safe to restart → Restart offending service
   - **Create Incident** if manual intervention needed
4. **Test:** Simulate high CPU alert → Verify flow triggers

### Lab 7: Now Assist Runbook Generation (20 min)

1. **Open Flow Designer** → Create new Flow
2. **Click Now Assist Panel** (sparkle icon)
3. **Prompt:** `Create a runbook to restart Apache on Linux web servers, check status before and after, handle errors`
4. **Review Generated Flow:**
   - SSH activities for status check
   - Decision logic
   - Restart command
   - Verification step
   - Error handling branches
5. **Customize** for your environment
6. **Save & Test**

---

## Troubleshooting Guide

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Flow fails at SSH activity | Wrong credentials / MID can't reach target | Test SSH from MID Server CLI |
| "MID Server not found" | No MID with required capability | Check MID capabilities, IP ranges |
| Activity times out | Command hangs / target slow | Increase timeout, check command |
| PowerShell fails | WinRM not configured / HTTPS cert | Run `winrm quickconfig` on target |
| REST returns 401/403 | Wrong auth / token expired | Verify credentials, token refresh |
| Flow doesn't trigger from Alert | Trigger condition mismatch | Check `em_alert` field values |
| Now Assist generates invalid flow | Missing context / vague prompt | Be specific: target OS, service name, credential type |

### Debug Flow Execution

```javascript
// Background Script - Check recent flow executions
var fe = new GlideRecord('sys_flow_execution');
fe.addQuery('flow.name', 'Auto-Remediate High CPU');
fe.orderByDesc('sys_created_on');
fe.setLimit(5);
fe.query();
while (fe.next()) {
    gs.log('Execution: ' + fe.sys_id + ' | State: ' + fe.state + ' | Started: ' + fe.started);
}
```

---

## Verification Checklist

- [ ] Flow Designer accessible, Core activities work
- [ ] SSH Activity executes commands on Linux target
- [ ] PowerShell Activity executes commands on Windows target
- [ ] REST Activity calls external APIs successfully
- [ ] Reusable Action created, tested, and published
- [ ] Flow triggers from Alert (Event Management integration)
- [ ] Now Assist generates usable runbook skeleton
- [ ] Approval gates work for production flows

---

## Next Steps

1. **Complete** [Cloud Management Getting Started](../cloudmanagement.md) — orchestrate cloud resources
2. **Complete** [Now Assist Getting Started](../nowassist.md) — Gen AI for all modules
3. **Review** [Orchestration Deep Dive Guide](../../docs/modules/orchestration/orchestration-guide.md)
4. **Explore** Spoke Gallery for pre-built integrations (Ansible, Terraform, Kubernetes, etc.)

---

## Quick Reference Card

```
ORCHESTRATION QUICK REFERENCE

Flow vs Action:
  Flow  → Business process (end-to-end)
  Action → Atomic operation (reusable)

Key Activities:
  SSH Command          → Linux/Unix/Network
  PowerShell Command   → Windows
  REST Request         → Any HTTP API
  Script               → JavaScript logic
  Decision             → If/Else branching
  Create/Update Record → ServiceNow platform

MID Server Requirements:
  SSH      → capability: ssh, port 22
  WinRM    → capability: powershell, port 5985/5986
  REST     → capability: rest, outbound internet

Trigger Types:
  Manual        → Button click
  Record        → Table trigger (insert/update)
  Schedule      → Recurring
  Application   → API/Webhook
  Subflow       → Called from another flow

Best Practices:
  1. Build Actions for single operations
  2. Compose Actions into Flows
  3. Use Decision for error handling
  4. Add Approval for prod changes
  5. Log inputs/outputs for debugging
  6. Version Actions and Flows

Now Assist Prompts:
  "Restart [service] on [OS] servers"
  "Create incident from alert with context"
  "Scale [cloud resource] based on metric"
```

---

*Complete the labs in order. Use your PDI. Refer to the deep-dive guide for advanced topics.*