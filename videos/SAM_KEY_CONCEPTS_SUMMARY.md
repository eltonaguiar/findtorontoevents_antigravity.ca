# ServiceNow SAM (Software Asset Management) - Key Concepts Summary for Video Production

## Source Materials
- **GitHub Repo**: https://github.com/eltonaguiar/alt_parallelswarm_SAM (23 commits, multi-agent fleet work)
- **GitHub Pages Guide**: https://eltonaguiar.github.io/ServiceNow_Learning_TSOM-_CSM_FSM_SalesCRM_HAM_ITSM/docs/modules/sam/sam-guide/
- **Agents involved**: deepseek-flash, grok-4.6, beam, perplexity (external review)

---

## CORE CONCEPT: The One-Sentence Definition
**SAM reconciles what you own (entitlements) against what exists and is used (normalized installs + usage) per software model and license metric, and turns the difference into a compliance position.**

---

## THE CHAIN (Memorize This Order)
```
CI (CMDB/IRE)
  └─ cmdb_sam_sw_install            # one install on one device
       └─ cmdb_sam_sw_discovery_model  # raw fingerprint, normalized
            └─ cmdb_software_product_model  # purchased product profile
                 └─ alm_license             # rights + metric + dates
                      └─ reconciliation     # rights vs demand
                           ├─ samp_product_result
                           ├─ Software Model Results
                           └─ samp_license_metric_result
```
**Install → Discovery Model → Software Model → Entitlement → Result**

---

## THE FOUR GATES (Prerequisites for SAM to Work)

| Gate | Pass Condition |
|------|----------------|
| Schema + edition | Correct plugin; SAM tables present |
| CMDB + CI identity | One CI per device; IRE rules reviewed |
| Discovery feed | One trusted source populating installs |
| Normalization + entitlements | Models normalize; every entitlement has model + metric |

---

## IRE RULE FAMILIES (CMDB Only)

| Rule Family | Insert? | Update? | One-Liner |
|-------------|---------|---------|-----------|
| **Identification** | Yes | Yes | Same CI or new CI? |
| **Reconciliation** (static/dynamic) | No | Yes | Which source may write this field? |
| **Data refresh** | No | Yes | Is the value stale enough to hand off? |
| **IRE data source** | Yes (blocks) | No | May this source create this class? |

**Order**: Identify first. Match → reconcile + data refresh. No match → data source rule gates the insert.

---

## NORMALIZATION STATUSES (Six, Not Four)

| Status | Manual Normalize? | Revert? |
|--------|-------------------|---------|
| New | No | No |
| Match Not Found | Yes | No |
| Publisher Normalized | Yes | Yes |
| Partially Normalized | Yes | Yes |
| Normalized | No | Yes |
| Manually Normalized | No | No |

**Key**: All reverts go to **Match Not Found**. Pattern-normalized models cannot be reverted.

---

## RECONCILIATION RESULTS (Three Tiers)

| Tier | Table | Answers |
|------|-------|---------|
| Product | `samp_product_result` | Is the product compliant? Cost/savings? |
| Software Model | Software Model Results | Which model is the problem? |
| License Metric | `samp_license_metric_result` | Rights owned vs used vs available, by metric |

**Run record**: `samp_reconciliation_result`. No documented single `sam_sw_reconciliation_result` analysis table.

---

## RIGHTS ALGEBRA (The Core Math)

```
Rights Owned = active entitlements sharing the metric
Rights Used = allocated in use + not allocated in use + installed
Rights Available = Owned − Used
Allocated Not In Use = wasted rights → remove allocations
Not Allocated In Use = unallocated consumption → create allocations or remove unallocated installs
```

---

## KEY TABLES (Must Know for Interviews)

| Table | Purpose |
|-------|---------|
| `cmdb_sam_sw_install` | Installs (source of truth for current software) |
| `cmdb_sam_sw_discovery_model` | Raw fingerprints + normalized fields + status |
| `cmdb_software_product_model` | Purchased product profile |
| `alm_license` | Entitlement |
| `samp_sw_usage` | Usage evidence (product-level, not install-level) |
| `samp_product_result` | Product compliance/cost |
| `samp_license_metric_result` | Rights per metric |
| `samp_reconciliation_result` | Reconciliation run record |
| `samp_sw_reclamation_candidate` | Reclamation candidates |
| `sam_sw_dedup_rule` | Custom dedup rules |

---

## KEY PROPERTIES (System Config)

| Property | Purpose |
|----------|---------|
| `com.snc.samp.recon.group` / `.subgroup` | Weekly reconciliation grouping |
| `com.snc.samp.automaticsmrcreation` | Auto-create models for licensable products |
| `com.snc.samp.exclude_device_flag` | Exclude CIs from SAM |
| `com.snc.samp.manage.published.products` | Phase-wise scope |
| `com.snc.samp.oracle.reconlevel` | Oracle VMware aggregation |
| `com.snc.samp.enable.ml_normalization` | ML normalization |
| `com.snc.samp.wide_net_normalization.enabled` | Wide-net normalization |
| `sn_sam_workspace.sam_license_operations_list_count` | Workspace list count threshold |

---

## KEY JOBS (Cadence)

| Job | Cadence |
|-----|---------|
| SAM - Normalize discovery models using content library rules | Daily |
| SAM - Discovery Model Normalization job | Daily |
| SAM - Daily Job | Daily |
| SAM - Trigger Full Scan | Weekly |
| SAM — Adjust Installs for excluded CIs | Not documented |
| SAM - Software License Reconciliation | Weekly default (schedule configurable) |
| SAM – Discovery Model to Software Model matching | Not documented |

---

## TOP TRAPS (Interview Gold)

1. **Metric mismatch** between model and entitlement → silently meaningless result
2. **Duplicate installs** from multiple sources → inflated demand; configure dedup
3. **Unnormalized titles** → unlicensed/unknown; normalize before auto-create
4. **Maintenance treated as a license** → false compliance
5. **Leftover installs on out-of-scope devices** → phantom demand; Retired/Stolen CI status deletes installs, but leased/ignored devices need exclude-CI job
5. **First reconciliation treated as an invoice** → wrong true-up; use it as data-quality loop
6. **Dead SaaS connector** → "no waste" illusion; monitor health
7. **Confusing vendor / publisher / PPN / model / discovery model / catalog item** → wrong links

---

## THE THREE RECORD TYPES (Never Confuse)

1. **Software Model** (`cmdb_software_product_model`) — What you buy
2. **Discovery Model** (`cmdb_sam_sw_discovery_model`) — What Discovery finds
3. **Entitlement** (`alm_license`) — What you own/are entitled to

---

## COMPLIANCE POSITION STATES

| State | Meaning |
|-------|---------|
| Compliant | Rights owned ≥ Rights used |
| Under-licensed | Rights used > Rights owned (audit exposure) |
| Over-licensed | Rights owned > Rights used (wasted spend) |

---

## PUBLISHER-SPECIFIC TRAPS

| Publisher | Trap |
|-----------|------|
| Microsoft | User vs Device metrics; M365 E3/E5 bundle splitting |
| Oracle | Processor metric; VMware/partitioning; audit scripts |
| IBM | PVU/RVU; sub-capacity; ILMT required |
| SAP | Named user vs package; indirect access |
| Adobe | User vs device; Creative Cloud vs Document Cloud |
| Salesforce | User licenses vs permission sets; platform vs app |

---

## SAAS LICENSE MANAGEMENT

- SaaS License Management (SLM) plugin separate from SAM Pro
- Connectors: Microsoft 365, Google Workspace, Salesforce, ServiceNow, Zoom, Slack, Box, Okta, 1Password, GitHub, Atlassian, etc.
- Spend Detection finds SaaS from AP/expense data
- Key metric: **Active users vs entitled users**

---

## OPTIMIZATION & RECLAMATION

| Action | Trigger |
|--------|---------|
| Reclaim allocation | User hasn't used software in X days (configurable) |
| Remove install | Device retired/stolen/excluded |
| Downgrade license | User only needs subset of features |
| Harvest SaaS seat | Inactive user > 30/60/90 days |
| True-up | Under-licensed position before audit/renewal |

---

## CIS-SAM EXAM ALIGNMENT

**Domains** (from official blueprint):
1. SAM Fundamentals (15%)
2. Software Models & Normalization (20%)
3. Entitlements & License Metrics (20%)
4. Reconciliation & Compliance (25%)
5. Optimization & Reclamation (10%)
6. Reporting & Dashboards (10%)

---

## MEMORY AIDS & MNEMONICS

- **IRE**: Identification Before Reconciliation
- **Business Rules**: BAA (Before, After, Async)
- **Client Scripts**: LOCS (onLoad, onChange, onSubmit, onCellEdit)
- **CMDB**: Retire Before Delete
- **Order vs Priority**: Lower = First
- **Transform Script**: Coalesce = Match
- **Debugging**: Log First, Then Debug

---

## LAB FLOW (Teach-Back Ready)

1. Choose and verify a software model
2. Create an entitlement far below demand
3. Confirm installs exist
4. Run reconciliation
5. Prove the fix (buy more or reclaim)
6. Prove normalization matters (change model → re-reconcile)
7. Teach back (write it down)

---

## WORKSPACES & DASHBOARDS

| Workspace | Purpose |
|-----------|---------|
| Software Asset Workspace | Main SAM dashboard |
| License Workbench | Entitlement management |
| Normalization Workspace | Model normalization |
| Publisher Audit Workspace | Audit preparation |

**Key Indicators**: Compliance %, Spend avoided, Reclamation $, True-up $, License utilization %

---

## INTEGRATIONS

| Integration | Purpose |
|-------------|---------|
| Discovery | Primary install source |
| SCCM / Intune / Jamf / Tanium | Endpoint management via SGC |
| ILMT / BigFix | IBM sub-capacity |
| Flexera / Snow / OpenLM / Open iT | Third-party SAM tools |
| SAP / Oracle / Citrix | Publisher-specific |
| Procurement / CSD | Entitlement ingestion |
| SSO / SaaS connectors | SaaS user mapping |

---

## VIDEO SCRIPT OUTLINE IDEAS (Phase 1: Visual Only)

### Video 1: "SAM in 60 Seconds" (Overview)
- The one-sentence definition
- The chain diagram animation
- SAM vs HAM vs ITAM table

### Video 2: "The Four Gates" (Prerequisites)
- Each gate with visual checkmarks
- What happens when a gate fails

### Video 3: "Normalization Statuses" (The Six States)
- State machine animation
- Manual normalize / revert rules

### Video 4: "Reconciliation Deep Dive"
- Three-tier results animation
- Rights algebra visual

### Video 5: "Top 7 Traps" (Interview Prep)
- Each trap with before/after visual
- How to detect and fix

### Video 6: "Publisher Traps" (Microsoft, Oracle, IBM, SAP)
- Metric mismatches
- Audit-specific gotchas

### Video 7: "The Lab Flow" (Hands-on Proof)
- Step-by-step screen recording style
- Teach-back moment

### Video 8: "CIS-SAM Exam Map"
- Domain percentages
- Key topics per domain

---

## PHASE 2 AUDIO NOTES
- Use natural TTS (ElevenLabs, OpenAI TTS, Coqui, Piper)
- Script each video with speaker notes
- Target 3-5 minutes per video
- Include "pause and think" moments for interview prep