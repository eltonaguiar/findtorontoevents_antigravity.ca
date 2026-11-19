# Resilience, security, and compliance

**Agent:** Kilo (deepseek-flash) · **Updated:** 2026-11-19 · **App:** ITOM Visibility / AIOps / Cloud Accelerate · **Confidence:** high (official docs)

ITOM does not replace your backup platform, your SecOps team, or your compliance programme. It
gives them **evidence**: what exists, what depends on what, what changed, what is exposed, and
what policy says should be true.

This guide covers the cross-cutting assurance work that the three ITOM pillars support:

- resilience and recovery visibility,
- change and configuration control,
- security alignment,
- regulatory and audit evidence.

---

## Contents

- [The boundary](#the-boundary)
- [Resilience and recovery visibility](#resilience-and-recovery-visibility)
- [Change and configuration control](#change-and-configuration-control)
- [Security alignment](#security-alignment)
- [Regulatory and audit evidence](#regulatory-and-audit-evidence)
- [Roles](#roles)
- [Common mistakes](#common-mistakes)
- [Quiz](#quiz)
- [Official sources](#official-sources)
- [Related guides](#related-guides)

---

## The boundary

| Concern | Owner | What ITOM contributes |
|---|---|---|
| ServiceNow platform backup/DR | Platform administration / ServiceNow | Not an ITOM product; ITOM does not back up the platform |
| Application/data backup | Backup platform and application teams | Discovery of backup plans/vaults as CIs, relationships, tags |
| Security operations | SecOps | Certificate, firewall, AI-agent, and configuration exposure data |
| Change management | ITSM Change Management | CMDB impact, service maps, change-correlated RCA |
| Regulatory compliance | Risk/compliance | Policy scans, attestations, audit records |

Saying this explicitly prevents the most common overclaim: "ITOM will handle our backup and
compliance." It will not. It will make the evidence visible.

---

## Resilience and recovery visibility

### Backup resources as CIs

Discovery patterns can find backup infrastructure and represent it in the CMDB. Examples from
the Australia documentation:

| Cloud | Resource | Pattern output |
|---|---|---|
| AWS | Backup Plan | `cmdb_aws_backup_backup_plan` (non-CMDB detail) and Cloud Resource `cmdb_ci_cmp_resource`; `Hosted on::Hosts` relationship to AWS Datacenter |
| AWS | Backup Vault | `cmdb_aws_backup_backup_vault` and Cloud Resource; retention days, recovery points, vault state/type |
| Azure | Recovery Services Vault Backup Item | `cmdb_azure_recovery_services_vault_backup_item` and Cloud Resource; backup status, policy, protection state, VM ID |

These patterns are **disabled by default** in the current content. Enable the one you need, and
confirm the resource is not in the Resource Inclusion List to avoid duplicate discovery.

### Why it matters

- You can see which workloads have a backup plan and which do not.
- You can relate a backup vault to the datacenter and the protected resource.
- You can use tags for ownership and cost.
- You can include backup CIs in impact analysis and service maps.

### What it does not do

- It does not run backups.
- It does not restore data.
- It does not prove a restore works.
- It does not replace a DR test.

A backup CI is evidence of configuration, not evidence of recoverability. Pair it with a restore
test owned by the backup team.

---

## Change and configuration control

### Impact analysis

Event Management calculates alert impact from:

- impact rules,
- the number of related active alerts,
- the CI's past history,
- CI relationships,
- whether the CI includes network or storage devices,
- service configuration associations (`svc_ci_assoc`) and `cmdb_rel_ci`.

Impact is displayed on impact trees, service maps, and dashboards. Alerts on CIs in maintenance
are excluded; a CI can be in maintenance because of an active change request or because its
Status is **In Maintenance**.

### Change-correlated root cause

Probable Root Cause Analysis (RCA) uses three factors:

1. alerts,
2. CI topology,
3. change requests on the CIs.

It extracts CIs from an alert or alert group, analyses CMDB relationships, filters relevant
change requests, and calculates a root cause score. It shows the top five probable root causes
with an explanation of how the alert correlates to the change.

For alert groups, it identifies upstream **topology origin CIs** that may explain cascading
failures. Changes on those CIs score higher.

This is how ITOM connects change control to incident resolution: the change record is not just
approval paperwork; it becomes evidence in the RCA.

### Analyze potential impact (agentic workflow)

With Service Mapping Plus 1.16.3, Otto for ITOM 2.3.0, and Otto for ITSM 11.1.3, the **Analyze
potential impact** agentic workflow reviews a change request and highlights potentially impacted
servers and suggested services. It updates the change request work notes.

Role: `sn_change_write` (plus the configured AI access controls).

This is an AI-assisted impact assessment. Verify the suggested services against the service map
before approving the change.

### Grouping by shared service

For deep service topologies, **Shared impacted services alert grouping** groups alerts under the
most critical business service (Top Service), regardless of CI distance. CMDB-based grouping is
better for relatively flat topologies (within about four hops). Choose the grouping method that
matches the topology, not the one that sounds newer.

---

## Security alignment

### Certificates

**Certificate Inventory and Management** discovers TLS certificates and supports expiry
management, ownership, renewal, and attestation.

- Discovery sources include port/URL scans, IP-based discovery, bulk upload, file import, and
  certificate authority queries.
- Cloud patterns cover AWS Certificate Manager, GCP Certificate Manager, and Azure Key Vault.
- Java KeyStore and Windows Certificate Store discovery are supported.
- Automated certificate management supports ACME and CyberArk Certificate Manager SaaS.
- **Certificate attestation** emails owners at intervals so they can attest or reject ownership.

An expired certificate is a predictable outage. The inventory is only useful if it has an owner
and an expiry alert.

### Cryptographic Asset Compliance

Cryptographic Asset Compliance inventories cryptographic assets, tracks risk indicators, and
supports post-quantum cryptography (PQC) readiness.

- Inventory includes certificates (on-premises and URL-based) and keys from AWS KMS and Azure
  Key Vault.
- Risk indicators include outdated algorithms, quantum vulnerability, and expiring certificates.
- Dashboards track PQC compliance and quantum vulnerability.
- AI-assisted risk assessment helps identify actions.

This is the forward-looking security layer above certificate inventory. It answers "what
cryptography do we depend on, and what is at risk?"

### Firewalls

**Firewall Audits and Reporting** inventories firewall security policies, devices, device
groups, and manager information. It supports rule requests through the Service Catalog and audits
of firewall security policies over time.

The audit value depends on linking a rule to a service and an owner. An inventory of rules with
no ownership is archaeology, not governance.

### AI agents and models

**AI Agent Topology Mapping** discovers AI agents, models, and prompts across cloud platforms
using patterns, with CMDB visibility. Use it to answer:

- Which AI agents/models exist?
- Where do they run?
- What do they depend on?
- Who owns them?

This is a newer, fast-moving area. Verify the supported clouds and CI classes in your release.

### Cloud configuration

**Cloud Configuration Governance** scans cloud resources against policy sets and remediates
violations. Approval-gated remediation creates a change request. That change request is the audit
trail.

**Tag Governance** audits tag policies (count, presence, key-value) and can remediate tags in
AWS/Azure. Tags are the join key for ownership, cost, and service mapping, so tag compliance is
security-adjacent even when the policy is financial.

---

## Regulatory and audit evidence

| Question an auditor asks | ITOM evidence |
|---|---|
| "What certificates do we have and who owns them?" | Certificate Inventory + attestation records |
| "Which cryptographic algorithms are at risk?" | Cryptographic Asset Compliance risk indicators |
| "What firewall rules exist and why?" | Firewall Audits inventory + catalog requests + audit history |
| "Which cloud resources violate policy?" | CCG scan results + remediation requests/change requests |
| "Are resources tagged to an owner/cost centre?" | Tag Governance audit + remediation records |
| "What changed before the outage?" | Probable RCA change correlation + change records |
| "What is the impact of this change?" | Service map + impact analysis + Analyze potential impact |
| "Which AI agents/models are deployed?" | AI Agent Topology Mapping |
| "Do we have backups for this workload?" | Backup Plan/Vault/Backup Item CIs and relationships |

The common thread: **the record is the evidence**. A dashboard screenshot is not an audit trail.
Export or retain the record, and make sure it has an owner.

---

## Roles

| Role | Scope |
|---|---|
| `discovery_admin` | Certificate/backup/AI topology discovery |
| `sm_admin` | Service maps and impact analysis |
| `evt_mgmt_admin` | Impact rules, grouping, RCA configuration |
| `sn_change_write` | Analyze potential impact workflow |
| `sn_itom_ccg.ccg_operator` | Cloud remediation |
| `sn_itom_tag.tag_governance_admin` | Tag policy and remediation |
| Compliance/risk owner (business role) | Accepts evidence and exceptions |

Role names for certificate/firewall administration vary by app version. Check the product page
and the instance role list.

---

## Common mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| Treating ITOM as the backup platform | False assurance | Use backup patterns for visibility; keep backup/restore with the backup team |
| Discovering backup resources without an owner | Inventory exists; nobody acts | Assign ownership and review cadence |
| Assuming a backup plan proves restore | A failed restore surprises everyone | Test restores; record the result |
| Impact calculation with a bad service map | Wrong blast radius | Fix CMDB/service map first |
| RCA without change data | Root cause list is weak | Ensure change requests are linked to CIs |
| Certificate inventory without attestation | Stale ownership | Configure attestation intervals |
| Firewall inventory without rule owners | Audit cannot decide what to keep | Link rules to services/owners |
| Tag policy without enforcement | Tags drift | Auto-remediation + provisioning guardrails |
| AI impact analysis accepted blindly | Wrong change approval | Verify against the service map |
| No audit retention | Evidence disappears | Define retention/export for each record type |

---

## Quiz

1. **Does ITOM back up the ServiceNow platform?**
   <details><summary>Answer</summary>No. Platform backup/DR is a platform administration responsibility. ITOM discovers backup resources and provides visibility.</details>

2. **What three factors does Probable RCA use?**
   <details><summary>Answer</summary>Alerts, CI topology, and change requests on the CIs.</details>

3. **What is certificate attestation?**
   <details><summary>Answer</summary>Periodic emails to certificate owners asking them to attest or reject ownership.</details>

4. **What does Cryptographic Asset Compliance add beyond certificate inventory?**
   <details><summary>Answer</summary>Cryptographic asset risk indicators, PQC readiness, keys from AWS KMS/Azure Key Vault, and AI-assisted risk assessment.</details>

5. **When is Shared impacted services grouping better than CMDB-based grouping?**
   <details><summary>Answer</summary>When the service topology is deep/complex and CIs are more than about four hops from the Top Service.</details>

6. **What record does an approval-gated CCG remediation create?**
   <details><summary>Answer</summary>A change request that tracks the approval.</details>

---

## Official sources

- AWS Backup Plan pattern — <https://www.servicenow.com/docs/r/australia/it-operations-management/discovery-and-service-mapping-patterns/aws-backup-plan.html>
- AWS Backup Vault pattern — <https://www.servicenow.com/docs/r/australia/it-operations-management/discovery-and-service-mapping-patterns/aws-backup-vault.html>
- Azure Recovery Services Vault Backup Item — <https://www.servicenow.com/docs/r/australia/it-operations-management/discovery-and-service-mapping-patterns/azure-recovery-services-vault-backup.html>
- Alert impact calculation — <https://www.servicenow.com/docs/r/australia/it-operations-management/event-management/c_EMImpactCalculation.html>
- Probable Root Cause Analysis — <https://www.servicenow.com/docs/r/australia/it-operations-management/event-management/probable-rca.html>
- Analyze potential impact — <https://www.servicenow.com/docs/r/australia/it-operations-management/service-mapping/use-now-assist-analyze-impact-agentic-workflow.html>
- Shared impacted services grouping — <https://www.servicenow.com/docs/r/australia/it-operations-management/event-management/shared-impacted-services-grouping.html>
- Certificate Inventory and Management — <https://www.servicenow.com/docs/r/australia/it-operations-management/discovery/cert-inventory-mgmt.html>
- Certificate attestation — <https://www.servicenow.com/docs/r/australia/it-operations-management/discovery/attestation-for-cert-owner.html>
- Cryptographic Asset Compliance — <https://www.servicenow.com/docs/r/australia/it-operations-management/itom-visibility/CAC-landing-page.html>
- Firewall Audits and Reporting — <https://www.servicenow.com/docs/r/australia/it-operations-management/discovery/firewall-audit-reporting.html>
- AI Agent Topology Mapping — <https://www.servicenow.com/docs/r/australia/it-operations-management/itom-visibility/ai-agent-topology-mapping-landing.html>
- Cloud Configuration Governance remediation — <https://www.servicenow.com/docs/r/australia/it-operations-management/itom-cloud-accelerate/ccg-remediation.html>
- Tag policies and remediation — <https://www.servicenow.com/docs/r/australia/it-operations-management/tag-governance/tag-governance-policies-remediate.html>

---

## Related guides

- [CMDB foundation](../cmdb/cmdb-guide.md)
- [Service Mapping](../service-mapping/service-mapping-guide.md)
- [Event Management](../event-management/event-management-guide.md)
- [Cloud Accelerate](../cloud-accelerate/cloud-accelerate-guide.md)
- [Automation and remediation](../automation-remediation/automation-remediation-guide.md)
