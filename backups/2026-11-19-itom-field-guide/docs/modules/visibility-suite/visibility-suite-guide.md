# The Visibility suite

**Agent:** Kilo (deepseek-flash) · **Updated:** 2026-11-19 · **App:** ITOM Visibility · **Confidence:** high (official docs)

Discovery and Service Mapping are the two best-known ITOM Visibility products, but the family
contains several specialist apps. They are easy to ignore until an audit, a certificate expiry,
or a tagging argument makes them urgent.

This guide is a map. Each section answers: what it is, why it exists, and where to start.

---

## Contents

- [Certificate Inventory and Management](#certificate-inventory-and-management)
- [Tag Governance](#tag-governance)
- [Firewall Audits and Reporting](#firewall-audits-and-reporting)
- [AI Agent Topology Mapping](#ai-agent-topology-mapping)
- [ITOM Content Service](#itom-content-service)
- [Cloud Discovery Workspace](#cloud-discovery-workspace)
- [Cloud License Estimator](#cloud-license-estimator)
- [LEAP](#leap)
- [ITOM Infra Services Workspace](#itom-infra-services-workspace)
- [How to choose](#how-to-choose)
- [Common mistakes](#common-mistakes)
- [Official sources](#official-sources)
- [Related guides](#related-guides)

---

## Certificate Inventory and Management

**What it is:** Discovery, inventory, and proactive management of TLS certificates. Supports
IPv6.

**Why it exists:** An expired certificate is an outage with a known date. Most organisations
find out too late because certificates live in spreadsheets, load balancers, Java keystores,
Windows stores, cloud key vaults, and certificate authorities.

**What it covers (Australia docs):**

- Certificate discovery via port scans, URL scans, IP-based discovery, bulk upload, file import,
  and certificate authority queries.
- Cloud certificate discovery patterns for AWS Certificate Manager, GCP Certificate Manager,
  and Azure Key Vault.
- Java KeyStore and Windows Certificate Store discovery.
- Automated certificate management with ACME and CyberArk Certificate Manager SaaS.
- Renewal, revocation, attestation, and notifications (email, Slack, Teams).
- Certificate chain relationships and a certificate management workspace.
- AI-assisted renewal (where entitled).

**Where to start:**

1. Pick one certificate authority and one environment.
2. Discover a small set of certificates.
3. Prove the inventory matches reality (issuer, subject, expiry, owner).
4. Define an expiry alert and an owner.
5. Only then automate renewal.

---

## Tag Governance

**What it is:** An app that identifies and remediates on-premises or cloud resources that are
inconsistent or do not comply with your tag policies.

**Why it exists:** Tags are the join key for cost allocation, ownership, service mapping,
observability, and cloud governance. When tags are wrong, every dashboard built on them is
wrong.

**What it does:**

- Defines tag policies (the standards to audit).
- Audits resources against those policies.
- Updates tags on cloud resources in real time.
- Supports remediation of tag issues.

**Where to start:**

- Define the minimum tag set: owner, cost centre, environment, service, data classification.
- Audit a small cloud account.
- Fix the top three violations.
- Make the tag policy part of the provisioning request (Cloud Services Catalog).

Tag Governance is not glamorous. It is the difference between a service map and a guess.

---

## Firewall Audits and Reporting

**What it is:** An inventory of firewall security policies, devices, device groups, and manager
information. It supports requests for new firewall rules through the Service Catalog and audits
of firewall security policies over time.

**Why it exists:** Firewall rules accumulate. Nobody knows which rules are still needed, who
requested them, or whether they still match policy. An audit trail turns a rule review into
evidence instead of archaeology.

**Where to start:**

- Inventory one firewall manager/device group.
- Map rules to the services they support.
- Define an audit window and an owner.
- Connect rule requests to the catalog so new rules have a request record.

---

## AI Agent Topology Mapping

**What it is:** Uses patterns to identify AI infrastructure components across cloud platforms:
AI agents, models, and prompts, with centralized CMDB visibility.

**Why it exists:** AI deployments are infrastructure too. Security, compliance, and vulnerability
teams need to know which models and agents exist, where they run, and what they depend on.

**Where to start:**

- Confirm the app is installed and the cloud accounts are connected.
- Discover a small AI workload.
- Inspect the CI classes and relationships.
- Define ownership and a review cadence.
- Connect findings to security and compliance processes.

This is a newer area. Verify the CI classes and supported clouds in your release.

---

## ITOM Content Service

**What it is:** A weekly-updated content service that identifies products in your infrastructure
using AI to classify running process fingerprints and SNMP system OIDs. It delivers new CIs and
suggestions.

**Why it exists:** Discovery patterns cover specific products and versions. Your estate contains
software nobody wrote a pattern for. ITOM Content Service widens visibility and keeps it current.

**What it does:**

- Reviews the products you are using weekly and delivers new CIs.
- Identifies running process fingerprints and SNMP OIDs.
- Filters out processes that are not suitable CI candidates.
- Integrates with Software Asset Management to show running versus installed software and find
  redundancy.
- Works with Service Mapping via Service Fingerprints suggestions.
- Uses the Continuance Delivery System (CDS) for data sharing; customers opt in and control
  permissions.

**Where to start:**

- Install the app and review the Content 360 suggestions in Discovery Admin Workspace.
- Approve a small number of high-value suggestions.
- Measure the inventory improvement before expanding.

**Privacy note:** Sharing process fingerprints and SNMP data is opt-in. Read the data-sharing
section before enabling it.

---

## Cloud Discovery Workspace

**What it is:** A workspace for managing cloud operations, including a dashboard, Kubernetes
Explorer, and dependency views.

**Why it exists:** Cloud resources are numerous, dynamic, and spread across accounts. A workspace
that combines discovery, inventory, and dependency context is easier to operate than a set of
lists.

**Where to start:**

- Install the workspace.
- Connect the cloud accounts Discovery already uses.
- Review the dashboard and Kubernetes Explorer.
- Use dependency views to validate relationships.

---

## Cloud License Estimator

**What it is:** Estimates the resource count for cloud resources that are eligible for licensing.

**Why it exists:** ITOM licensing is usage-based. You need to know what will be counted before
you migrate packaging or expand discovery.

**Where to start:**

- Configure cloud credentials.
- Configure the accounts to estimate.
- Generate a report.
- Compare the estimate with the licensing dashboard and your contract.

This is a planning tool, not an invoice. Verify assumptions with your ServiceNow account team.

---

## LEAP

**What it is:** The Learning Enhanced Automation Platform: AI-driven insights and automation for
IT operations, including problem records and playbooks.

**Why it exists:** Operators spend time writing the same problem record and remediation steps.
LEAP proposes content and automation so humans can review instead of starting from a blank page.

**Where to start:**

- Read the AI governance checklist in [AI in ITOM](../itom-ai/itom-ai-guide.md).
- Generate one knowledge article or playbook for a low-risk, well-understood issue.
- Review it with the owning team.
- Publish only after verification.

---

## ITOM Infra Services Workspace

**What it is:** An ITOM Visibility workspace that includes a MID Server workspace and related
infrastructure views.

**Why it exists:** MID Server health is a prerequisite for Discovery, Event Management pull
connectors, HLA, and ACC. A workspace makes the dependency visible.

**Where to start:** Use it to check MID Server status, version, and assignment before blaming
Discovery.

---

## How to choose

| Problem | Product |
|---|---|
| "We do not know what certificates we have" | Certificate Inventory and Management |
| "Our tags are inconsistent" | Tag Governance |
| "We cannot audit firewall rules" | Firewall Audits and Reporting |
| "We do not know what AI agents/models exist" | AI Agent Topology Mapping |
| "Discovery misses software" | ITOM Content Service |
| "We need a cloud operations view" | Cloud Discovery Workspace |
| "How many cloud resources will be licensed?" | Cloud License Estimator |
| "We need AI-generated problem/playbook content" | LEAP |
| "Is the MID Server healthy?" | ITOM Infra Services Workspace |

---

## Common mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| Buying the whole suite before a use case | Shelfware | Start with the audit or outage that hurts |
| Certificate discovery without an owner | Expiry still surprises you | Assign owners and expiry alerts |
| Tag policy without enforcement | Tags drift again | Enforce at provisioning and remediate |
| Firewall inventory without rule ownership | Audit cannot decide what to keep | Link rules to services and owners |
| AI topology discovery without security review | Findings go nowhere | Connect to security/compliance |
| Content Service opt-in without privacy review | Data-sharing surprise | Read the CDS terms; control permissions |
| Cloud License Estimator treated as an invoice | Budget mismatch | Reconcile with the licensing dashboard and contract |

---

## Official sources

- ITOM Visibility — <https://www.servicenow.com/docs/r/australia/it-operations-management/itom-visibility/itom-visibility-landing-page.html>
- Certificate Inventory and Management — <https://www.servicenow.com/docs/r/australia/it-operations-management/discovery/cert-inventory-mgmt.html>
- Tag Governance — <https://www.servicenow.com/docs/r/australia/it-operations-management/tag-governance/landing-page-tag-governance.html>
- Firewall Audits and Reporting — <https://www.servicenow.com/docs/r/australia/it-operations-management/discovery/firewall-audit-reporting.html>
- AI Agent Topology Mapping — <https://www.servicenow.com/docs/r/australia/it-operations-management/itom-visibility/ai-agent-topology-mapping-landing.html>
- ITOM Content Service — <https://www.servicenow.com/docs/r/australia/it-operations-management/itom-visibility/discovery-content-services.html>
- Cloud Discovery Workspace — <https://www.servicenow.com/docs/r/australia/it-operations-management/cloud-discovery-workspace/cow-landing-page.html>
- Cloud License Estimator — <https://www.servicenow.com/docs/r/australia/it-operations-management/cloud-license-estimator/cloud-license-estimator-landing.html>
- LEAP — <https://www.servicenow.com/docs/r/australia/it-operations-management/aiops-leap-learning-enhanced-automation-playbooks/aiops-leap.html>
- ITOM Infra Services Workspace — <https://www.servicenow.com/docs/r/australia/it-operations-management/itom-visibility/itom-infra-srv-wrksp-mid.html>

---

## Related guides

- [Discovery](../discovery/discovery-guide.md)
- [Service Mapping](../service-mapping/service-mapping-guide.md)
- [Cloud Accelerate](../cloud-accelerate/cloud-accelerate-guide.md)
- [AI in ITOM](../itom-ai/itom-ai-guide.md)
