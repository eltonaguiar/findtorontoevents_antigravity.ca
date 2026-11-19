# MID Server — ServiceNow MID Server

**Agent:** Kilo  
**Date:** 2026-11-19  
**Module:** MID Server  
**App:** IT Operations Management (Foundation for Discovery, Orchestration, Event Management)  
**Confidence:** high  

---

## Contents

- [Purpose](#purpose)
- [Where to Find It](#where-to-find-it)
- [MID Server Architecture](#mid-server-architecture)
- [Key Plugins & Licensing](#key-plugins--licensing)
- [MID Server Capabilities](#mid-server-capabilities)
- [Installation & Deployment](#installation--deployment)
- [Configuration](#configuration)
- [High Availability & Clustering](#high-availability--clustering)
- [Security & Networking](#security--networking)
- [Monitoring & Troubleshooting](#monitoring--troubleshooting)
- [Upgrades & Maintenance](#upgrades--maintenance)
- [Out-of-Box Values & Dropdowns](#out-of-box-values--dropdowns)
- [Re-usable Code / Metadata](#re-usable-code--metadata)
- [Key Table Hierarchy](#key-table-hierarchy)
- [Integrations](#integrations)
- [Key Fields](#key-fields)
- [Common Mistakes](#common-mistakes)
- [Lab: End-to-End MID Server Deployment](#lab-end-to-end-mid-server-deployment)
- [Quiz](#quiz)
- [Memory Aids & Mnemonics](#memory-aids--mnemonics)
- [Related Guides](#related-guides)
- [Official Learning Resources](#official-learning-resources)

---

## Purpose

The **MID Server** (Management, Instrumentation, and Discovery Server) is a lightweight Java application that runs inside your network to facilitate communication between the ServiceNow cloud instance and on-premises systems. It acts as a **secure proxy** enabling Discovery, Orchestration, and Event Management to reach resources that are not directly accessible from the internet.

**Key value:** Enables hybrid cloud management without opening inbound firewall ports or exposing internal systems to the internet.

---

## Where to Find It

| Breadcrumb | Path |
|------------|------|
| Module entry | All > MID Server > ... |
| MID Servers | All > MID Server > MID Servers |
| ECC Queue | All > MID Server > ECC Queue |
| Capabilities | All > MID Server > Capabilities |
| Logs | All > MID Server > Logs (links to MID Server file system) |

---

## MID Server Architecture

```mermaid
graph TD
    subgraph "ServiceNow Cloud"
        A[Discovery/Orchestration/EM]
        B[ECC Queue]
        C[Instance Scheduler]
    end
    subgraph "Customer Network (DMZ/Internal)"
        D[MID Server 1]
        E[MID Server 2]
        F[MID Server N]
    end
    subgraph "Target Systems"
        G[Linux Servers (SSH)]
        H[Windows Servers (WinRM/PowerShell/WMI)]
        I[Network Devices (SNMP/SSH)]
        J[Databases (JDBC)]
        K[Cloud APIs (REST)]
        L[Monitoring Tools (Syslog/REST)]
        M[Kubernetes (kubectl)]
    end

    A -->|Probes| B
    B -->|HTTPS Poll| D
    B -->|HTTPS Poll| E
    D -->|SSH| G
    D -->|WinRM| H
    D -->|SNMP| I
    E -->|JDBC| J
    E -->|REST| K
    E -->|Syslog| L
    D -->|kubectl| M
    G -.->|Sensor Data| D
    H -.->|Sensor Data| D
    I -.->|Sensor Data| D
    J -.->|Sensor Data| E
    K -.->|Sensor Data| E
    L -.->|Events| E
    D -.->|Sensor Data| B
    E -.->|Sensor Data| B
    B -->|Process| A

    style A fill:#e8eaf6,color:#000
    style B fill:#fff3e0,color:#000
    style C fill:#e3f2fd,color:#000
    style D fill:#fff3e0,color:#000
    style E fill:#fff3e0,color:#000
    style F fill:#fff3e0,color:#000
    style G fill:#e1f5e1,color:#000
    style H fill:#e1f5e1,color:#000
    style I fill:#e1f5e1,color:#000
    style J fill:#e1f5e1,color:#000
    style K fill:#e1f5e1,color:#000
    style L fill:#e1f5e1,color:#000
    style M fill:#e1f5e1,color:#000
```

### Communication Flow

1. **ServiceNow** creates **Probe** record in **ECC Queue** (Topic=Probe, Queue=Input)
2. **MID Server** polls ECC Queue via **HTTPS** (outbound only, port 443)
3. **MID Server** executes probe against **Target System** using appropriate protocol
4. **Target System** returns data to **MID Server**
5. **MID Server** runs **Sensor** script to parse/transform data
6. **MID Server** posts **Sensor** record to **ECC Queue** (Topic=Sensor, Queue=Output)
7. **ServiceNow** processes sensor → Updates CMDB / Completes workflow

**Key Point:** All communication is **outbound from MID Server** — no inbound firewall rules needed.

---

## Key Plugins & Licensing

| Plugin | Name | Included In |
|--------|------|-------------|
| `com.snc.mid_server` | MID Server Core | ITOM License, Orchestration Add-on |
| `com.snc.mid_server.installer` | MID Server Installer | All |

**License:** Included with ITOM License and Orchestration Add-on. No separate license.

---

## MID Server Capabilities

Each MID Server can have multiple **Capabilities** that determine what work it can perform.

### Standard Capabilities

| Capability | Probes/Activities Enabled | Use Case |
|------------|---------------------------|----------|
| **SSH** | Linux/Unix commands, file transfer | Linux discovery, orchestration |
| **PowerShell** | Windows PowerShell scripts/commands | Windows discovery, orchestration |
| **WinRM** | Windows Remote Management | Modern Windows management |
| **WMI** | Windows Management Instrumentation | Legacy Windows discovery |
| **SNMP** | SNMP v1/v2c/v3 Get/Walk/Set | Network device discovery |
| **JDBC** | Database queries (SQL, Oracle, MySQL, PostgreSQL) | Database discovery, orchestration |
| **REST** | HTTP/HTTPS REST API calls | Cloud APIs, custom integrations |
| **SOAP** | SOAP web service calls | Legacy integrations |
| **Kubernetes** | kubectl, Helm operations | Container discovery, orchestration |
| **Docker** | Docker CLI commands | Container management |
| **Ansible** | Ansible Tower/AWX playbook execution | Configuration management |
| **Terraform** | Terraform Cloud/Enterprise operations | Infrastructure as Code |
| **Syslog** | Receive syslog events | Event Management ingestion |
| **JMS** | JMS message consumption | Event Management ingestion |
| **Email** | POP3/IMAP email retrieval | Event Management ingestion |

### Capability Assignment

- **Automatic:** MID Server registers capabilities based on installed tools
- **Manual:** Add/remove capabilities in **All > MID Server > MID Servers > Capabilities** related list
- **IP Affinity:** Assign MID Server to specific IP ranges for targeted discovery

### Special Capabilities

| Capability | Description |
|------------|-------------|
| **Discovery** | Runs Discovery probes (Shazzam, Identity, Exploration) |
| **Orchestration** | Runs Orchestration activities |
| **Event Management** | Receives events via Syslog, JMS, Email |
| **Agent Client Collector** | ACC communication endpoint |

---

## Installation & Deployment

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **OS** | Linux (RHEL 8+, CentOS 8+, Ubuntu 20.04+) or Windows Server 2019+ | Linux (RHEL 9, Ubuntu 22.04) |
| **Java** | JDK 17 (bundled) | JDK 17 (bundled) |
| **Memory** | 4 GB RAM | 8-16 GB RAM |
| **CPU** | 2 vCPU | 4 vCPU |
| **Disk** | 10 GB free | 50 GB free (logs, temp files) |
| **Network** | Outbound HTTPS (443) to ServiceNow | + Access to target subnets |

### Deployment Models

| Model | Description | Use Case |
|-------|-------------|----------|
| **Single MID Server** | One MID Server for all | Small environments (< 1000 CIs) |
| **Multiple MID Servers** | Multiple MID Servers, auto-load-balance | Large environments, network segmentation |
| **MID Server Cluster** | Clustered for HA (active-active) | High availability requirements |
| **DMZ + Internal** | DMZ MID for internet-facing, Internal for private | Security zones |
| **Per-Region/Cloud** | Dedicated MID per cloud region/VPC | Multi-cloud, latency optimization |

### Installation Methods

#### Linux (RPM/DEB)
```bash
# Download installer from ServiceNow
wget https://<instance>.service-now.com/mid_installer_linux.sh

# Make executable
chmod +x mid_installer_linux.sh

# Run installer (interactive)
sudo ./mid_installer_linux.sh

# Or silent install
sudo ./mid_installer_linux.sh --silent \
  --url https://<instance>.service-now.com \
  --user mid_user \
  --password <password> \
  --name MID-PROD-01
```

#### Windows (MSI)
```powershell
# Download MSI from ServiceNow
# Run installer GUI or silent:
msiexec /i mid_installer_windows.msi /qn ^
  INSTANCE_URL=https://<instance>.service-now.com ^
  MID_USER=mid_user ^
  MID_PASSWORD=<password> ^
  MID_NAME=MID-PROD-01
```

#### Docker (Containerized)
```dockerfile
# Dockerfile
FROM servicenow/mid-server:latest
ENV MID_INSTANCE_URL=https://<instance>.service-now.com
ENV MID_USER=mid_user
ENV MID_PASSWORD=<password>
ENV MID_NAME=MID-DOCKER-01
```

```bash
docker run -d \
  --name mid-server \
  -e MID_INSTANCE_URL=https://<instance>.service-now.com \
  -e MID_USER=mid_user \
  -e MID_PASSWORD=<password> \
  -e MID_NAME=MID-DOCKER-01 \
  servicenow/mid-server:latest
```

### Post-Installation Verification

1. **Check Service Status:**
   - Linux: `systemctl status mid-server` or `service mid-server status`
   - Windows: Services.msc → "MID Server" → Running

2. **Verify in ServiceNow:**
   - Navigate to **All > MID Server > MID Servers**
   - Confirm MID Server appears with **Status: Up**

3. **Test Capabilities:**
   - Open MID Server record → **Capabilities** related list
   - Verify expected capabilities present

---

## Configuration

### Key Configuration Files

| File | Location | Purpose |
|------|----------|---------|
| `config.xml` | `agent/conf/` | Main configuration |
| `logger.properties` | `agent/conf/` | Logging configuration |
| `wrapper.conf` | `agent/conf/` | Java service wrapper (Windows) |

### Critical config.xml Parameters

```xml
<parameters>
    <!-- Instance Connection -->
    <parameter name="mid.instance.url" value="https://your-instance.service-now.com"/>
    <parameter name="mid.user" value="mid_user"/>
    <parameter name="mid.password" value="encrypted_password"/>
    
    <!-- MID Server Identity -->
    <parameter name="mid.name" value="MID-PROD-01"/>
    <parameter name="mid.description" value="Production MID Server - US East"/>
    
    <!-- Threading & Performance -->
    <parameter name="threads.max" value="50"/>
    <parameter name="threads.probe.max" value="25"/>
    <parameter name="threads.sensor.max" value="25"/>
    
    <!-- Timeouts -->
    <parameter name="probe.timeout" value="300"/>
    <parameter name="sensor.timeout" value="60"/>
    <parameter name="mid.http.timeout" value="120"/>
    
    <!-- Proxy (if required) -->
    <parameter name="mid.proxy.host" value="proxy.company.com"/>
    <parameter name="mid.proxy.port" value="8080"/>
    <parameter name="mid.proxy.user" value="proxy_user"/>
    <parameter name="mid.proxy.password" value="encrypted_proxy_password"/>
    
    <!-- SSL/TLS -->
    <parameter name="mid.ssl.trust_all" value="false"/>
    <parameter name="mid.ssl.keystore" value="keystore.jks"/>
    <parameter name="mid.ssl.keystore_password" value="encrypted_keystore_password"/>
    
    <!-- Logging -->
    <parameter name="log.level" value="INFO"/>
    <parameter name="log.max_files" value="10"/>
    <parameter name="log.max_size" value="10MB"/>
    
    <!-- Auto-Upgrade -->
    <parameter name="mid.auto_upgrade" value="true"/>
    <parameter name="mid.auto_upgrade.window_start" value="02:00"/>
    <parameter name="mid.auto_upgrade.window_end" value="04:00"/>
</parameters>
```

### Credential Configuration

MID Server uses **Credential IDs** (references to `discovery_credentials` in ServiceNow) — never stores actual credentials locally.

**Credential Flow:**
1. Probe includes `credential_id` parameter
2. MID Server requests credential from ServiceNow via secure API
3. ServiceNow returns decrypted credential (over HTTPS)
3. MID Server uses credential for target authentication
4. Credential cleared from memory after use

---

## High Availability & Clustering

### MID Server Clustering (Active-Active)

**Requirements:**
- 2+ MID Servers with identical capabilities
- Shared network access to target systems
- Load balancer (optional, for external access)

**Configuration:**
1. Install multiple MID Servers with same capabilities
2. Assign to same **IP Range** or **Cluster** (All > MID Server > Clusters)
3. ServiceNow distributes probes across cluster members
4. If one fails, others pick up its queue

### Cluster Benefits

| Benefit | Description |
|---------|-------------|
| **Failover** | Automatic redistribution of work |
| **Load Balancing** | Even distribution of probes |
| **Rolling Upgrades** | Upgrade one at a time |
| **Maintenance** | Take one offline without downtime |

### IP Affinity

**IP Affinity** ensures the same MID Server always handles a specific IP range.

- Configure in: **All > MID Server > IP Affinity**
- Maps CIDR blocks → MID Server
- Useful for: Network devices requiring persistent connections, rate-limited APIs

---

## Security & Networking

### Network Requirements

| Direction | Protocol | Port | Purpose |
|-----------|----------|------|---------|
| **MID → ServiceNow** | HTTPS | 443 | ECC Queue polling, API calls |
| **MID → Targets** | SSH | 22 | Linux/Unix |
| **MID → Targets** | WinRM | 5985/5986 | Windows |
| **MID → Targets** | WMI | 135, 445 | Windows (legacy) |
| **MID → Targets** | SNMP | 161 | Network devices |
| **MID → Targets** | JDBC | 1433, 3306, 5432, 1521 | Databases |
| **MID → Targets** | REST/HTTPS | 443, 80, custom | APIs, Cloud |
| **Targets → MID** | Syslog | 514 (UDP/TCP) | Event ingestion |
| **Targets → MID** | JMS | Various | Event ingestion |

### Security Best Practices

1. **Dedicated Service Account** — Create `mid_user` in ServiceNow with minimal roles (`mid_server` role only)
2. **Network Segmentation** — Place MID Server in management subnet, not DMZ
3. **Firewall Rules** — Allow only required outbound ports to target subnets
4. **Proxy Support** — Use corporate proxy for ServiceNow communication if required
5. **Certificate Validation** — Don't disable SSL verification (`mid.ssl.trust_all=false`)
6. **Audit Logging** — Enable MID Server audit logs for compliance
7. **Regular Patching** — Keep OS and Java updated

### ServiceNow User for MID Server

**Required Role:** `mid_server`
**Optional Roles:** `discovery_admin` (if MID Server admin), `orchestration_admin`

**User Creation:**
1. Create user: `mid_prod_01`
2. Add role: `mid_server`
3. Set password (complex, rotated regularly)
4. Use in `config.xml`

---

## Monitoring & Troubleshooting

### Health Indicators

| Indicator | Location | Healthy Value |
|-----------|----------|---------------|
| **Status** | MID Server record | `Up` |
| **Last Contact** | MID Server record | < 5 minutes ago |
| **Thread Usage** | MID Server record | < 80% max threads |
| **Queue Depth** | ECC Queue (Agent=MID) | < 100 Ready probes |
| **Error Rate** | ECC Queue (State=Error) | < 1% |
| **Disk Space** | MID Server host | > 20% free |
| **Memory** | MID Server host | < 80% used |

### Key Log Files

| Log File | Location | Purpose |
|----------|----------|---------|
| `mid.log` | `logs/` | Main application log |
| `probe.log` | `logs/` | Probe execution details |
| `sensor.log` | `logs/` | Sensor processing details |
| `wrapper.log` | `logs/` | Java wrapper (Windows service) |
| `upgrade.log` | `logs/` | Auto-upgrade history |

### Common Issues & Fixes

| Issue | Symptoms | Resolution |
|-------|----------|------------|
| **Status: Down** | MID Server not polling | Check service, network, `config.xml` URL/credentials |
| **Status: Warning** | High thread usage, slow | Increase `threads.max`, check target responsiveness |
| **Probe Timeouts** | ECC Queue: Error, "Timeout" | Increase `probe.timeout`, check network latency |
| **Credential Failures** | "Authentication failed" | Verify credentials in ServiceNow, test connectivity |
| **No Capabilities** | Discovery/Orchestration fails | Check `capabilities` in MID Server record |
| **Auto-Upgrade Failed** | Version mismatch | Manual upgrade, check `upgrade.log` |
| **High Memory** | OOM errors, slow | Increase heap: `wrapper.java.maxmemory=4096` |

### Troubleshooting Commands

```bash
# Check MID Server status (Linux)
systemctl status mid-server

# View live logs
tail -f /opt/mid/logs/mid.log

# Check ECC Queue for this MID
# In ServiceNow: All > MID Server > ECC Queue > Filter: Agent=MID-PROD-01

# Test target connectivity from MID Server host
ssh user@target-host
nc -zv target-host 22
winrm identify -r:http://target-host:5985/wsman -u:user -p:pass

# Restart MID Server
systemctl restart mid-server
# Windows: net stop "MID Server" && net start "MID Server"
```

---

## Upgrades & Maintenance

### Auto-Upgrade (Default)

- **Enabled by default** (`mid.auto_upgrade=true`)
- Runs during **maintenance window** (default 02:00-04:00)
- Downloads new version from ServiceNow
- Restarts service automatically
- Rolls back on failure

### Manual Upgrade

```bash
# Linux
cd /opt/mid
./stop_mid.sh
# Download new installer from ServiceNow
./mid_installer_linux.sh --upgrade
./start_mid.sh

# Windows
net stop "MID Server"
# Run new MSI installer
net start "MID Server"
```

### Version Compatibility

| ServiceNow Release | MID Server Version | Notes |
|--------------------|-------------------|-------|
| Vancouver | Vancouver | Must match |
| Washington | Washington | Must match |
| Xanadu | Xanadu | Must match |
| Yokohama | Yokohama | Must match |

**Rule:** MID Server version **must match** ServiceNow instance version (major release).

### Maintenance Checklist (Monthly)

- [ ] Verify all MID Servers show **Status: Up**
- [ ] Check **Last Contact** < 5 minutes
- [ ] Review **ECC Queue Errors** for patterns
- [ ] Check **Disk Space** > 20% free
- [ ] Review **Thread Usage** < 80%
- [ ] Verify **Auto-Upgrade** succeeded (check version)
- [ ] Rotate **MID User password** (quarterly)
- [ ] Archive old **log files** (> 30 days)
- [ ] Validate **capabilities** match requirements

---

## Out-of-Box Values & Dropdowns

### MID Server Status (sys_mid_server.status)

| Value | Label | Meaning |
|-------|-------|---------|
| `Up` | Up | Running, polling, healthy |
| `Down` | Down | Not reachable, service stopped |
| `Warning` | Warning | Running but issues (threads, queue, version) |
| `Validating` | Validating | Starting up, registering capabilities |

### MID Server Type

| Value | Label |
|-------|-------|
| `standard` | Standard MID Server |
| `clustered` | Cluster Member |

### Capability Status

| Value | Label |
|-------|-------|
| `active` | Active |
| `inactive` | Inactive |

---

## Re-usable Code / Metadata

### Re-usable Metadata Inventory

| Piece | Location | Purpose |
|-------|----------|---------|
| **MID Servers** | All > MID Server > MID Servers | Server definitions |
| **Capabilities** | MID Server record > Capabilities related list | Assigned capabilities |
| **IP Affinity** | All > MID Server > IP Affinity | IP-to-MID mapping |
| **Clusters** | All > MID Server > Clusters | HA groups |
| **ECC Queue** | All > MID Server > ECC Queue | Message queue monitoring |

### Re-usable Code Snippets

#### Script Include: MID Server Health Check

```javascript
var MIDServerHealth = Class.create();
MIDServerHealth.prototype = Object.extendsObject(AbstractAjaxProcessor, {
    // Get health status for all MID Servers
    getAllHealth: function() {
        var gr = new GlideRecord('sys_mid_server');
        gr.query();
        var results = [];
        while (gr.next()) {
            var eccGr = new GlideAggregate('ecc_queue');
            eccGr.addQuery('agent', gr.sys_id);
            eccGr.addQuery('state', 'Ready');
            eccGr.addQuery('queue', 'input');
            eccGr.count('sys_id');
            eccGr.query();
            var queueDepth = 0;
            if (eccGr.next()) queueDepth = eccGr.getAggregate('COUNT', 'sys_id');
            
            var errorGr = new GlideAggregate('ecc_queue');
            errorGr.addQuery('agent', gr.sys_id);
            errorGr.addQuery('state', 'Error');
            errorGr.addQuery('queue', 'output');
            errorGr.addQuery('sys_created_on', '>=', gs.daysAgo(1));
            errorGr.count('sys_id');
            errorGr.query();
            var errorCount = 0;
            if (errorGr.next()) errorCount = errorGr.getAggregate('COUNT', 'sys_id');
            
            results.push({
                sys_id: gr.sys_id,
                name: gr.name,
                status: gr.status,
                last_contact: gr.last_contact,
                version: gr.version,
                capabilities: this.getCapabilities(gr.sys_id),
                queue_depth: queueDepth,
                error_count_24h: errorCount,
                thread_usage: this.getThreadUsage(gr.sys_id)
            });
        }
        return JSON.stringify(results);
    },
    
    getCapabilities: function(midSysId) {
        var caps = [];
        var gr = new GlideRecord('sys_mid_server_capability');
        gr.addQuery('mid_server', midSysId);
        gr.query();
        while (gr.next()) {
            caps.push(gr.capability);
        }
        return caps;
    },
    
    getThreadUsage: function(midSysId) {
        // Would need JMX or MID Server API for real-time
        return 'N/A - Check MID Server logs';
    },
    
    type: 'MIDServerHealth'
});
```

#### Business Rule: Alert on MID Server Down

```javascript
(function rule(current, previous) {
    if (current.status.changesTo('Down') || current.status.changesTo('Warning')) {
        var event = new GlideRecord('em_event');
        event.initialize();
        event.node = current.name;
        event.resource = 'MID Server';
        event.type = 'availability';
        event.message = 'MID Server ' + current.name + ' status changed to ' + current.status;
        event.severity = current.status == 'Down' ? 1 : 2; // Critical or Major
        event.source = 'MID Server Monitor';
        event.insert();
        
        // Also create incident for Down
        if (current.status == 'Down') {
            var inc = new GlideRecord('incident');
            inc.initialize();
            inc.short_description = 'MID Server Down: ' + current.name;
            inc.description = 'MID Server ' + current.name + ' has been down since ' + gs.nowDateTime();
            inc.priority = '1';
            inc.category = 'Infrastructure';
            inc.subcategory = 'MID Server';
            inc.assignment_group = 'NOC';
            inc.insert();
        }
    }
})(current, previous);
```

#### Flow Designer: MID Server Capacity Check

```javascript
// Flow Designer Action - Check if MID Server can handle more work
var midServer = inputs.mid_server; // Reference to sys_mid_server

var gr = new GlideRecord('sys_mid_server');
gr.get(midServer);

var threadMax = parseInt(gr.getValue('threads_max') || '50');
var currentThreads = getCurrentThreadCount(gr.sys_id); // Custom function

var usagePercent = (currentThreads / threadMax) * 100;

outputs.can_accept_work = usagePercent < 80;
outputs.usage_percent = usagePercent;
outputs.current_threads = currentThreads;
outputs.max_threads = threadMax;
outputs.status = gr.status;

function getCurrentThreadCount(midSysId) {
    // Query ECC Queue for active probes assigned to this MID
    var agg = new GlideAggregate('ecc_queue');
    agg.addQuery('agent', midSysId);
    agg.addQuery('state', 'Processing');
    agg.addQuery('queue', 'input');
    agg.count('sys_id');
    agg.query();
    if (agg.next()) return agg.getAggregate('COUNT', 'sys_id');
    return 0;
}
```

---

## Key Table Hierarchy

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `sys_mid_server` | MID Server definitions | `name`, `status`, `version`, `ip_address`, `last_contact`, `threads_max` |
| `sys_mid_server_capability` | MID Server capabilities | `mid_server`, `capability`, `status` |
| `sys_mid_server_cluster` | MID Server clusters | `name`, `members` (list) |
| `sys_mid_server_ip_affinity` | IP affinity rules | `mid_server`, `ip_range`, `cidr` |
| `ecc_queue` | Message queue | `agent`, `topic`, `name`, `source`, `state`, `queue` |
| `sys_mid_server_log` | MID Server logs (remote) | `mid_server`, `level`, `message`, `timestamp` |

### Table Relationships

```
sys_mid_server
    │
    ├──► sys_mid_server_capability (MID → Capabilities)
    │
    ├──► sys_mid_server_cluster (MID → Cluster membership)
    │
    ├──► sys_mid_server_ip_affinity (MID → IP Ranges)
    │
    └──► ecc_queue (MID → Queue messages)
            │
            ├──► Probes (Input queue)
            └──► Sensors (Output queue)
```

---

## Integrations

| Integration | Direction | Purpose | Protocol |
|-------------|-----------|---------|----------|
| **ServiceNow Instance** | Bidirectional | ECC Queue, API, Upgrades | HTTPS (443) |
| **Linux/Unix** | Outbound | Discovery, Orchestration | SSH (22) |
| **Windows** | Outbound | Discovery, Orchestration | WinRM (5985/5986), WMI (135/445), PowerShell |
| **Network Devices** | Outbound | Discovery | SNMP (161), SSH (22) |
| **Databases** | Outbound | Discovery, Orchestration | JDBC (various ports) |
| **Cloud Providers** | Outbound | Discovery, Orchestration | REST/HTTPS (443) |
| **Kubernetes** | Outbound | Discovery, Orchestration | kubectl/REST |
| **Monitoring Tools** | Inbound | Event Ingestion | Syslog (514), JMS, Email |
| **Ansible Tower** | Outbound | Orchestration | REST |
| **Terraform Cloud** | Outbound | Orchestration | REST |

---

## Key Fields

| Table | Field | Type | Why It Matters |
|-------|-------|------|----------------|
| `sys_mid_server` | `status` | Choice | Up/Down/Warning - primary health indicator |
| `sys_mid_server` | `last_contact` | Date/Time | When MID last polled ECC Queue |
| `sys_mid_server` | `version` | String | Must match ServiceNow release |
| `sys_mid_server` | `threads_max` | Integer | Max concurrent probes |
| `sys_mid_server` | `ip_address` | String | MID Server's IP (for affinity) |
| `sys_mid_server_capability` | `capability` | Choice | SSH, PowerShell, SNMP, etc. |
| `ecc_queue` | `agent` | Reference | Which MID Server |
| `ecc_queue` | `state` | Choice | Ready/Processing/Processed/Error |
| `ecc_queue` | `topic` | Choice | Probe vs Sensor |
| `ecc_queue` | `queue` | Choice | Input (to MID) vs Output (from MID) |

---

## Common Mistakes

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Single MID Server for everything | Bottleneck, no HA | Deploy multiple MID Servers, use clusters |
| MID Server in wrong network zone | Can't reach targets | Place MID Server in each network segment |
| No IP affinity for network devices | Discovery load-balances, breaks sessions | Configure IP affinity for network devices |
| Default thread limits | Slow discovery, timeouts | Increase `threads.max` based on hardware |
| Auto-upgrade disabled | Version drift, compatibility issues | Enable auto-upgrade with maintenance window |
| No monitoring/alerting | Silent failures | Alert on status=Down, high queue depth |
| Shared MID User across environments | Security, audit issues | Dedicated MID User per environment |
| Ignoring SSL validation | Man-in-the-middle risk | Keep `mid.ssl.trust_all=false` |
| Not testing after upgrade | Broken capabilities | Verify capabilities post-upgrade |
| Insufficient disk for logs | Disk full, service stops | Configure log rotation, monitor disk |

---

## Lab: End-to-End MID Server Deployment

**Prerequisites:** Linux server (RHEL/Ubuntu) or Windows Server, network access to targets and ServiceNow.

### Step 1: Prepare Target Host
1. Provision Linux VM (4 GB RAM, 2 vCPU, 20 GB disk)
2. Install Java 17 (if not bundled): `sudo dnf install java-17-openjdk` or `sudo apt install openjdk-17-jdk`
3. Create service account: `sudo useradd -m -s /bin/bash miduser`
4. Configure sudo for discovery commands (if needed)

### Step 2: Create ServiceNow MID User
1. Navigate to **All > User Administration > Users**
2. Click **New** → Create `mid_prod_01`
3. **Roles:** `mid_server` only
4. **Password:** Generate strong password
5. **Active:** true

### Step 3: Download & Install MID Server
1. In ServiceNow: **All > MID Server > MID Servers** → Click **Download Installer**
2. Copy installer to target host
3. Run installer:
   ```bash
   chmod +x mid_installer_linux.sh
   sudo ./mid_installer_linux.sh --silent \
     --url https://your-instance.service-now.com \
     --user mid_prod_01 \
     --password 'your-password' \
     --name MID-PROD-01
   ```

### Step 4: Verify Installation
1. Check service: `systemctl status mid-server`
2. In ServiceNow: **All > MID Server > MID Servers** → Verify `MID-PROD-01` shows **Status: Up**
3. Check **Capabilities** related list → Verify SSH, PowerShell, SNMP, etc.

### Step 5: Configure Capabilities & IP Affinity
1. Open `MID-PROD-01` record
2. **Capabilities:** Add/remove as needed
3. **IP Affinity:** If multiple MID Servers, assign CIDR blocks
   - Navigate to **All > MID Server > IP Affinity**
   - Click **New** → MID Server: `MID-PROD-01`, IP Range: `10.0.1.0/24`

### Step 6: Test Discovery
1. Navigate to **All > Discovery > Discovery Schedules**
2. Create schedule targeting `10.0.1.0/24`
3. **MID Server:** Select `MID-PROD-01`
4. **Run Now** → Monitor **Discovery Status**

### Step 7: Test Orchestration
1. Navigate to **All > Flow Designer**
2. Create flow with **SSH - Run Command** action
3. **MID Server:** `MID-PROD-01`
4. **Target:** Test Linux host IP
5. **Credentials:** Select SSH credential
6. **Command:** `hostname`
7. **Run Flow** → Verify success

### Step 8: Configure Monitoring
1. Create Business Rule on `sys_mid_server` for status changes (Down/Warning)
2. Create Event Management alert for MID Server availability
3. Add to NOC dashboard

---

## Quiz

1. What does MID stand for in MID Server?
   <details><summary>Answer</summary>Management, Instrumentation, and Discovery</details>

2. What is the default communication port between MID Server and ServiceNow?
   <details><summary>Answer</strong>443 (HTTPS)</details>

3. What direction does MID Server communication flow?
   <details><summary>Answer</strong>Outbound only (MID Server polls ServiceNow)</details>

4. What table stores MID Server definitions?
   <details><summary>Answer</strong>`sys_mid_server`</details>

5. What are the three MID Server status values?
   <details><summary>Answer</strong>Up, Down, Warning</details>

6. What capability is required for Linux Discovery?
   <details><summary>Answer</strong>SSH</details>

7. What is IP Affinity used for?
   <details><summary>Answer</strong>Ensure same MID Server handles specific IP ranges</details>

8. What is the default auto-upgrade maintenance window?
   <details><summary>Answer</strong>02:00-04:00</details>

9. What log file contains probe execution details?
   <details><summary>Answer</strong>`probe.log`</details>

10. What role does the ServiceNow MID User need?
    <details><summary>Answer</strong>`mid_server`</details>

---

## Memory Aids & Mnemonics

<details>
<summary>💡 Click to reveal mnemonics & mnemonics</summary>

### MID Server — MID
**M**anagement
**I**nstrumentation
**D**iscovery

---

### Capabilities — SPWJKAD
**S**SH, **P**owerShell, **W**inRM, **J**DBC, **K**ubernetes, **A**nsible, **D**ocker

---

### Communication Flow — POSE
**P**robe Created → **O**utbound Poll → **S**ensor Execution → **E**CC Queue Return

---

### Status Values — UDW
**U**p, **D**own, **W**arning

---

### Network Ports — SSH WSNJ
**S**SH (22), **S**NMP (161), **W**inRM (5985), **N** (WMI 135/445), **J**DBC (various)

---

### Troubleshooting — DLT
**D**own = Service/Network
**L**ag = Threads/Timeouts
**T**hreads = Capacity

---

### Upgrade Rule — MV
**M**ID **V**ersion = Instance Version (must match)

---

</details>

---

## Related Guides

- [ITOM Overview](../itom-guide.md)
- [Discovery Guide](../discovery/discovery-guide.md)
- [Orchestration Guide](../orchestration/orchestration-guide.md)
- [Event Management Guide](../eventmanagement/eventmanagement-guide.md)
- [Cloud Management Guide](../cloudmanagement/cloudmanagement-guide.md)
- [MID Server Getting Started](../../getting-started/midserver.md)

---

## Official Learning Resources

### Now Learning (Structured Training)
- [MID Server Fundamentals](https://nowlearning.servicenow.com/) — Search "MID Server" on Now Learning Portal
- [Discovery Fundamentals](https://nowlearning.servicenow.com/) — MID Server section

### Product Documentation (Technical Reference)
- [ServiceNow Product Documentation — MID Server](https://docs.servicenow.com/) → Search "MID Server", "MID Server Installation", "MID Server Clustering", "MID Server Troubleshooting"
- [ServiceNow Product Documentation — MID Server Capabilities](https://docs.servicenow.com/) → Search "MID Server Capabilities"

### Official Videos & Playlists
- [ServiceNow YouTube Channel](https://www.youtube.com/c/ServiceNow) — Search "ServiceNow MID Server", "ServiceNow MID Server Installation", "ServiceNow MID Server Troubleshooting"

---

*Generated by Kilo on 2026-11-19. Based on official ServiceNow documentation and product guides.*