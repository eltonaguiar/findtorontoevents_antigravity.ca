# Getting Started with Discovery

**Agent:** Kilo  
**Date:** 2026-11-19  
**Module:** Discovery  
**Prerequisites:** CMDB Foundation completed, MID Server active  
**Confidence:** high  

---

## Contents

- [Learning Objectives](#learning-objectives)
- [Prerequisites](#prerequisites)
- [Core Concepts](#core-concepts)
- [Step-by-Step Setup](#step-by-step-setup)
- [Hands-On Labs](#hands-on-labs)
- [Troubleshooting Guide](#troubleshooting-guide)
- [Verification Checklist](#verification-checklist)
- [Next Steps](#next-steps)

---

## Learning Objectives

By completing this guide, you will be able to:

1. **Explain** the PCIE discovery phases
2. **Configure** Discovery Schedules and Behaviors
3. **Manage** Credentials for SSH, WinRM, SNMP, JDBC
4. **Read** and troubleshoot ECC Queue payloads
5. **Create** custom Discovery Patterns
6. **Verify** CI creation and relationships in CMDB

---

## Prerequisites

| Requirement | Status |
|-------------|--------|
| CMDB Foundation guide completed | ✅ |
| MID Server installed and **Up** | ✅ |
| `discovery_admin` role | ✅ |
| Network access to target devices | ✅ |
| Credentials for target systems | 🔄 Prepare |

---

## Core Concepts

### PCIE Phases (Memorize This Order)

| Phase | Purpose | Key Tables |
|-------|---------|------------|
| **P**ort Scan | Find open ports on target IPs | `discovery_port_probe` |
| **C**lassification | Identify device type (Linux, Windows, Router, etc.) | `discovery_classifier` |
| **I**dentification | Match to existing CI or create new (via IRE) | `cmdb_identification_rule` |
| **E**xploration | Gather detailed attributes, relationships, apps | `discovery_pattern` |

**Mnemonic:** **P**eople **C**annot **I**gnore **E**xploration

### Key Discovery Tables

| Table | Purpose |
|-------|---------|
| `discovery_schedule` | When/what to discover |
| `discovery_behavior` | Which MID Server, credentials, patterns |
| `discovery_classifier` | Port → CI Class mapping |
| `discovery_pattern` | Exploration logic (steps, parameters, CI creation) |
| `ecc_queue` | Message queue (Input/Output/Processing/Error) |
| `cmdb_ci_*` | Created/updated CIs |

---

## Step-by-Step Setup

### 1. Verify MID Server

1. Navigate to **All > MID Server > Servers**
2. Confirm at least one server with **Status: Up**
3. Check **Capabilities** — should include: `ssh`, `snmp`, `powershell`, `jdbc`, `wmi`
4. If none: Install MID Server (see [MID Server Getting Started](../midserver.md))

### 2. Create Credentials

**All > Discovery > Credentials > [Type]**

| Credential Type | Use For | Key Fields |
|-----------------|---------|------------|
| **SSH** | Linux/Unix, Network gear | Username, Private Key (or Password), Port (22) |
| **WinRM** | Windows (preferred) | Username, Password, Domain, Port (5985/5986) |
| **SSH Key** | Linux key-based auth | Username, Private Key, Passphrase |
| **SNMP v1/v2c** | Network devices (read-only) | Community String, Port (161) |
| **SNMP v3** | Network devices (secure) | Username, Auth Protocol, Auth Pass, Priv Protocol, Priv Pass |
| **JDBC** | Databases | Username, Password, Connection URL, Driver |
| **API Key** | Cloud, REST endpoints | Key, Header Name |

**Best Practice:** Create credential **Sets** (not individual) — group by environment (Prod, Test, Lab).

### 3. Create Discovery Schedule

**All > Discovery > Schedules > New**

| Field | Example Value |
|-------|---------------|
| **Name** | `Daily Prod Network Scan` |
| **Discover** | `IP Range` |
| **IP Range** | `10.0.1.0/24` |
| **Behavior** | `Standard Discovery` (or custom) |
| **Run** | `Daily` at `02:00` |
| **Time Zone** | `UTC` |
| **Active** | `true` |

**Quick Test:** Create ad-hoc schedule with single IP for immediate testing.

### 4. Configure Discovery Behavior

**All > Discovery > Behaviors**

Default `Standard Discovery` works for most. Customize if needed:

| Setting | Recommendation |
|---------|----------------|
| **MID Server Selection** | `Auto` (by IP Range/Capability) or specific MID |
| **Credential Priority** | SSH Key > SSH Password > WinRM > SNMP |
| **Pattern Priority** | Horizontal patterns after classification |
| **Shazzam Batch Size** | 100 (reduce for slow networks) |

### 5. Run First Discovery

1. Open your Schedule → Click **Run Now**
2. Monitor **All > Discovery > ECC Queue**
3. Filter: `Topic = Discovery`, `State = Processing/Output/Error`
4. Wait for **Output** messages → Click **Payload** to inspect

---

## Hands-On Labs

### Lab 1: Basic Network Discovery (30 min)

**Goal:** Discover a single Linux server

1. **Prepare Target:** Linux VM with SSH enabled, known credentials
2. **Create Schedule:** Single IP (`10.0.1.50`), Behavior: `Standard Discovery`
3. **Run:** Click **Run Now**
4. **Monitor ECC Queue:**
   - `Shazzam` (Port Scan) → Output: open ports
   - `Classification` → Output: `Linux` classifier matched
   - `Identification` → Output: CI created/updated
   - `Exploration` → Output: attributes, relationships
5. **Verify CI:** **All > CMDB > Configuration Items** → Filter `sys_class_name=cmdb_ci_linux_server`
6. **Check:** `serial_number`, `mac_address`, `cpu_count`, `ram`, `os_version`

### Lab 2: Windows Discovery with WinRM (30 min)

**Goal:** Discover Windows server

1. **Prepare Target:** Windows Server, WinRM enabled (`winrm quickconfig`), credentials
2. **Create WinRM Credentials** (username, password, domain)
3. **Run Discovery** on Windows IP
4. **Verify CI:** `cmdb_ci_win_server` with `domain`, `os_version`, `cpu_count`
5. **Check Relationships:** Network interfaces, installed software

### Lab 3: Network Device Discovery (SNMP) (30 min)

**Goal:** Discover switch/router

1. **Prepare Target:** Network device with SNMP v2c/v3 enabled
2. **Create SNMP Credentials** (community string or v3 params)
3. **Run Discovery**
4. **Verify CI:** `cmdb_ci_switch` or `cmdb_ci_router`
5. **Check:** `model`, `ios_version`, `interfaces` (child CIs: `cmdb_ci_network_interface`)

### Lab 4: Horizontal Discovery (Applications) (45 min)

**Goal:** Discover Apache, MySQL on Linux server

1. **Prerequisite:** Lab 1 completed (Linux server discovered)
2. **Run Discovery** again on same IP (or wait for schedule)
3. **Monitor ECC Queue** for Exploration phase
4. **Verify Application CIs:**
   - `cmdb_ci_apache` — version, config_path, ports
   - `cmdb_ci_mysql` — version, databases, replication status
5. **Check Relationships:** `Runs on::Runs` → Linux server CI

### Lab 5: Custom Discovery Pattern (60 min)

**Goal:** Create pattern for custom app on port 8080

1. **All > Discovery > Patterns > New**
2. **Fields:**
   - **Name:** `Custom App 8080`
   - **CI Type:** `cmdb_ci_application` (or custom class)
   - **Trigger:** `Port Probe` → Port `8080`
3. **Design Pattern** (Pattern Designer):
   - **Step 1:** SSH Command → `curl -s http://localhost:8080/health`
   - **Step 2:** Parse JSON → Extract `version`, `status`
   - **Step 3:** Create CI → `cmdb_ci_application` with attributes
   - **Step 4:** Create Relationship → `Runs on` → Host server
4. **Save & Activate**
5. **Test:** Run Discovery on target with app on 8080
6. **Verify:** Custom CI created with correct attributes

### Lab 6: ECC Queue Deep Dive (30 min)

**Goal:** Read and understand ECC Queue payloads

1. Open **All > Discovery > ECC Queue**
2. Filter: `Topic = Discovery`, `State = Output`
3. Open a **Shazzam** output → Inspect XML: `<port>`, `<status>`
4. Open **Classification** output → See `probe_name`, `classifier`
5. Open **Identification** output → See `cmdb_ci` fields, `sys_id`
6. Open **Exploration** output → See `parameter` elements (attributes)
7. **Error Example:** Find `State = Error` → Read `error_message` → Diagnose

---

## Troubleshooting Guide

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| **No CIs created** | Credentials wrong / MID Server down | Verify credentials, MID Server status |
| **Classification fails** | No classifier for open port | Add classifier or use pattern trigger |
| **Identification creates duplicates** | Identification rules missing/incorrect | Fix IRE rules (serial_number primary) |
| **Exploration empty** | Pattern not triggered / MID lacks capability | Check pattern trigger, MID capabilities |
| **SSH timeout** | Firewall / wrong port / key format | Test `ssh user@ip` from MID Server |
| **WinRM fails** | WinRM not configured / HTTPS cert | Run `winrm quickconfig`, check cert |
| **SNMP no data** | Wrong community / v3 params / ACL | Verify `snmpwalk` from MID Server |
| **ECC Queue stuck Processing** | MID Server busy / probe timeout | Restart MID, increase probe timeout |

### Debug Commands (Run on MID Server)

```bash
# Test SSH from MID Server
ssh -i /path/key user@target_ip

# Test WinRM
winrm identify -r:http://target_ip:5985/wsman -u:user -p:pass

# Test SNMP
snmpwalk -v2c -c community target_ip

# Check MID Server logs
tail -f /opt/servicenow/mid-server/logs/agent0.log
```

---

## Verification Checklist

- [ ] MID Server shows **Up** with required capabilities
- [ ] Credentials created for SSH, WinRM, SNMP
- [ ] Discovery Schedule runs and creates CIs
- [ ] Linux CI: `cmdb_ci_linux_server` with serial_number, CPU, RAM
- [ ] Windows CI: `cmdb_ci_win_server` with domain, OS version
- [ ] Network CI: `cmdb_ci_switch`/`router` with interfaces
- [ ] Application CIs: Apache, MySQL, etc. with `Runs on` relationships
- [ ] Custom pattern discovers target application
- [ ] Can read ECC Queue: Shazzam → Classification → Identification → Exploration
- [ ] No duplicate CIs (check CMDB Health → Duplication < 1%)

---

## Next Steps

1. **Complete** [Event Management Getting Started](../eventmanagement.md) — consumes Discovery CIs
2. **Complete** [Service Mapping Getting Started](../servicemapping.md) — builds on Discovery topology
3. **Review** [Discovery Deep Dive Guide](../../docs/modules/discovery/discovery-guide.md)
4. **Practice** CIS-Discovery exam questions (KB0011545)

---

## Quick Reference Card

```
DISCOVERY QUICK REFERENCE

PCIE Order: Port → Classify → Identify → Explore

Key Tables:
  discovery_schedule    → When/What
  discovery_behavior    → How (MID, Creds, Patterns)
  discovery_classifier  → Port → Class
  discovery_pattern     → Exploration logic
  ecc_queue             → Message bus
  cmdb_ci_*             → Results

Credentials Priority:
  1. SSH Key
  2. SSH Password  
  3. WinRM
  4. SNMP v3
  5. SNMP v2c
  6. JDBC

ECC Queue States:
  Input      → Sent to MID
  Processing → MID working
  Output     → Results back
  Error      → Failed (check error_message)

Common Probes:
  Shazzam           → Port scan
  Classification    → Identify device type
  Identification    → IRE match/create CI
  Exploration       → Pattern execution

Pattern Designer Steps:
  1. Trigger (Port/Classifier)
  2. Parameters (Commands, Queries)
  3. Parse (Regex, JSON, XML)
  4. Create/Update CI
  5. Create Relationships
```

---

*Complete the labs in order. Use your PDI. Refer to the deep-dive guide for advanced topics.*