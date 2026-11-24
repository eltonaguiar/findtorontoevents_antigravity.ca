# Cloud Accelerate

**Agent:** Kilo (deepseek-flash) · **Updated:** 2026-11-19 · **App:** ITOM Cloud Accelerate · **Confidence:** high (official docs)

Cloud Accelerate is the ITOM family for operating cloud resources. It is easy to blur three
different problems together:

1. **Request and provision** a resource — Cloud Services Catalog.
2. **Own and certify** a cloud account/subscription/project — Cloud Account Management.
3. **Prove the configuration complies** with policy — Cloud Configuration Governance.

If you solve all three with one app, you usually solve none of them well.

---

## Contents

- [The product map](#the-product-map)
- [Cloud Services Catalog](#cloud-services-catalog)
- [Cloud Account Management](#cloud-account-management)
- [Cloud Configuration Governance](#cloud-configuration-governance)
- [Cost and capacity controls](#cost-and-capacity-controls)
- [Cloud Action Library](#cloud-action-library)
- [Cloud Migration Assessment is retired](#cloud-migration-assessment-is-retired)
- [Cloud Provisioning and Governance (legacy)](#cloud-provisioning-and-governance-legacy)
- [Entitlements](#entitlements)
- [Common mistakes](#common-mistakes)
- [Quiz](#quiz)
- [Official sources](#official-sources)
- [Related guides](#related-guides)

---

## The product map

| Product | Problem | Primary user |
|---|---|---|
| **Cloud Services Catalog** | "I need a cloud resource, provisioned correctly" | Requester, service owner |
| **Cloud Account Management** | "Who owns this account, and is it certified?" | Cloud admin, certifier, approver |
| **Cloud Configuration Governance** | "Does this resource comply with policy?" | Security/compliance, cloud admin |
| **Cloud Action Library** | "Run an action against a cloud resource" | Cloud operator, developer |
| **CPG (legacy)** | The older unified cloud portal; being replaced | Existing customers only |

---

## Cloud Services Catalog

### What it is

Cloud Services Catalog is the single place for automating cloud management tooling. The official
docs describe it as replacing and improving the capabilities offered by the Cloud Provisioning
and Governance user and admin portals.

### What it gives you

- A **Cloud Services Catalog Request page** in Employee Center.
- Day 1 provisioning, Day 2 patching/maintenance, and lifecycle operations (start, stop,
  deprovision).
- Out-of-box catalogs for AWS and Azure, plus GCP request support.
- **My Stacks** and **My Resources** pages for viewing and operating on deployed resources.
- Terraform Connector (multi-repo support).
- Ansible integration.
- Azure DevOps CI/CD pipeline integration.
- Guided Setup.

### Supported platforms

AWS, Microsoft Azure, Google Cloud Platform, and VMware are the recurring platforms in the
official content.

### What to verify

- The Store apps are installed at compatible versions.
- Cloud credentials/accounts are configured.
- The catalog items point at the correct cloud account and network.
- Approvals and budget checks are defined.
- The requester can see the catalog item in Employee Center.

---

## Cloud Account Management

### What it is

Cloud Account Management automates the lifecycle of cloud accounts: creation, suspension,
reactivation, and certification. It also onboards accounts created outside the tool.

### What it gives you

- Standardised account requests and approvals.
- Request policies that automate creation, approval, and budget checks.
- Account certification to confirm legitimate ownership/control.
- A compliance dashboard that consolidates ITOM Visibility and CAM data.
- A home dashboard showing critical/high severity accounts, suspended accounts, accounts due for
  certification, and accounts with undefined budgets.
- A clear terminology map: Azure subscriptions, AWS management/member accounts, GCP projects.

### Personas

| Persona | Responsibility |
|---|---|
| Requester | Requests account creation, suspension, or reactivation |
| Approver | Approves or denies requests |
| Admin | Aligns configuration, customises the certification policy, onboards unmanaged accounts |
| Certifier | Certifies or fails an account |
| Asset viewer | Views CIs in Asset Explorer and the compliance dashboard |
| Account manager | Views account details and assets; edits primary-owned accounts |

### Entitlements

- Cloud Account Management is available with the **ITOM Cloud Accelerate** licence.
- **Cloud Governance Suite (CGS)** is a prerequisite for **Cloud Workspace** and provides the
  home page and asset explorer.
- **CGS + CAM** adds account overview, requests/approvals, certification, compliance dashboard,
  configuration, and request policies.

---

## Cloud Configuration Governance

### What it is

Cloud Configuration Governance scans cloud resources against policy sets and identifies
violations. You then run remediation actions to fix non-compliant configuration.

### The workflow

1. Install Cloud Configuration Governance.
2. Install the CCG Content Pack for base content.
3. Assign CCG roles.
4. Set up AWS and/or Azure.
5. Create a scan configuration with one or more policy sets.
6. Run the scan.
7. Run remediation for the non-compliant resources.

### What to verify

- The cloud account has the permissions the scanner needs.
- The policy set matches the control framework you are actually audited against.
- Remediation is safe and approved; not every violation should be auto-fixed.
- Scan frequency matches the rate of change.

---

## Cost and capacity controls

Cloud is also a budget and a capacity problem.

### Resource pools and cost centers

With the **Cost Management** plugin (`com.snc.cost_management`), you can limit the choices a
requester sees in the cloud catalog request form. The base-system `UserCostCenter` resource pool
limits users to the cost center associated with their user record. This is a JavaScript filter on
the resource pool, tied to a blueprint's Cloud variable.

The pattern to learn:

1. Activate Cost Management.
2. Define cost centers and associate users.
3. Create a resource pool with an `All` query filter and a `UserCostCenter` script filter.
4. Point the blueprint's CostCenter variable at the pool and filter.
5. Publish the blueprint.

Role: `sn_cmp_cloud_admin` (records the guide under the CPG-era Cloud Admin portal). Verify the
equivalent controls in your current Cloud Services Catalog version.

### Capacity limits on requests

Capacity limits restrict attributes such as the number of virtual machines, vCPUs, or aggregate
storage, and can be set per logical datacenter in a cloud account:

- **Discovered** — the value discovered for all resources in the service account.
- **Provisioned** — the value provisioned for the service account.
- **Capacity Limit** — the maximum allowed value.
- **Unit** — for example, storage in GB.

Configure on the Cloud Admin portal (`Manage > Cloud Accounts > Datacenters > Capacity Limits`),
set the state to **Draft**, update, then **Publish**. These pages are documented under the CPG
era; confirm the equivalent controls in the current Cloud Services Catalog for new deployments.

Role: `sn_cmp.cloud_admin`.

The lesson: cost and capacity are governance, not just reporting. If everyone can request
anything, the dashboard is a post-hoc regret report.

---

## Cloud Action Library

Cloud Action Library provides actions and workflows that interact with cloud resources. The
official workflow is:

1. Install Cloud Action Library.
2. Set it up for AWS and/or Azure.
3. Use the actions and workflows against cloud resources.

It is a building block for **day-2 automation**: patching, lifecycle operations, and remediation
against cloud resources. It is not a governance product by itself; pair it with a clear approval
and audit path.

---

## Cloud Migration Assessment is retired

The earlier description of this pillar included "tools to plan cloud migrations". The current
Australia documentation is explicit: **Cloud Migration Assessment is no longer deployed, enhanced,
or supported.** Do not plan new work on it.

Use instead:

- current Cloud Services Catalog / Cloud Account Management guidance for the target environment,
- the official migration and adoption guidance for your release,
- your own migration plan records in ServiceNow (for example, portfolio and change records).

If you see an old reference to Cloud Migration Assessment, treat it as historical, not a
recommendation.

---

## Cloud Provisioning and Governance (legacy)

CPG is the older unified cloud management application. Important facts from the Australia
documentation:

- It is renamed/transformed into **Cloud Services Catalog**.
- From the **Brazil** release onward it is being prepared for future deprecation: it is no longer
  installed on new instances but remains supported for existing customers.
- It is incompatible with the legacy v1 Cloud Management application; it is compatible starting
  with the Jakarta release.
- Legacy workflows are being migrated to **Workflow Studio flows and subflows**.
- Default uncustomised workflows migrate automatically; customised workflows are not migrated and
  continue to use the existing workflow.
- Policy Rule Actions can use Workflow Studio subflows.
- Guided Setup is available under **Guided Setup > ITOM Guided Setup**.

### What this means for you

- **New deployment:** evaluate Cloud Services Catalog, not CPG.
- **Existing CPG:** inventory customised workflows before planning a migration.
- **Any CPG:** do not assume the old workflow names survive; check the migration notes and KBs.

---

## Entitlements

Cloud Accelerate is licensed separately from Visibility and AIOps. The exact packaging can be
complex; verify:

- ITOM Cloud Accelerate subscription
- Cloud Governance Suite (CGS) where Cloud Workspace is required
- Cloud Account Management entitlement
- Cloud Services Catalog Store apps and Terraform Connector
- Cloud provider credentials and permissions

Full notes: [Licensing and prerequisites](../../03-licensing-prerequisites.md).

---

## Common mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| Designing new work on CPG | App not installed on the new instance | Use Cloud Services Catalog |
| Customising legacy CPG workflows | Migration blocked | Avoid customisation or plan the migration explicitly |
| Confusing request, account, and compliance | One app is expected to do everything | Map each problem to Catalog, CAM, or CCG |
| No account owner | Accounts exist; nobody certifies them | Use CAM personas and certification |
| No tag policy | Cost and governance reports are wrong | Use Tag Governance and cloud tag policies |
| Auto-remediating every violation | Outage caused by a "fix" | Approve remediation by policy and risk |
| No budget guardrail | Surprise spend | Use request policies and budget checks |

More: [Common mistakes](../../05-common-mistakes.md).

---

## Quiz

1. **Which app should a new deployment use for cloud requests?**
   <details><summary>Answer</summary>Cloud Services Catalog. CPG is prepared for deprecation and is not installed on new instances.</details>

2. **What does Cloud Account Management certify?**
   <details><summary>Answer</summary>That a person or entity has legitimate ownership/control of an account, for security, compliance, and audit purposes.</details>

3. **What does Cloud Configuration Governance scan?**
   <details><summary>Answer</summary>Cloud resources against one or more policy sets, identifying policy violations for remediation.</details>

4. **What is the CGS prerequisite for?**
   <details><summary>Answer</summary>Cloud Workspace (home page and asset explorer). CGS + CAM adds account lifecycle, certification, compliance dashboard, and request policies.</details>

5. **What happened to CPG workflows?**
   <details><summary>Answer</summary>They are being migrated to Workflow Studio flows/subflows; uncustomised defaults migrate automatically, customised ones do not.</details>

6. **What is the status of Cloud Migration Assessment?**
   <details><summary>Answer</summary>It is no longer deployed, enhanced, or supported. Do not plan new work on it.</details>

7. **What does the UserCostCenter resource pool do?**
   <details><summary>Answer</summary>It limits a requester to the cost center associated with their user record, using a script filter on the resource pool.</details>

---

## Official sources

- Cloud Provisioning and Governance — <https://www.servicenow.com/docs/r/australia/it-operations-management/cloud-configuration-governance/cloud-management-v2-landing-page.html>
- Exploring Cloud Services Catalog — <https://www.servicenow.com/docs/r/australia/it-operations-management/cloud-services-catalog/exploring-cloud-services-catalog.html>
- Cloud Account Management — <https://www.servicenow.com/docs/r/australia/it-operations-management/cloud-account-management/cam-landing.html>
- Exploring Cloud Account Management — <https://www.servicenow.com/docs/r/australia/it-operations-management/cloud-account-management/exploring-cam.html>
- Exploring Cloud Configuration Governance — <https://www.servicenow.com/docs/r/australia/it-operations-management/itom-cloud-accelerate/exploring-cloud-configuration-governance.html>
- Exploring Cloud Action Library — <https://www.servicenow.com/docs/r/australia/it-operations-management/itom-cloud-accelerate/exploring-cloud-actions-library.html>
- Cloud Migration Assessment (retired) — <https://www.servicenow.com/docs/r/australia/it-operations-management/itom-cloud-accelerate/cloud-migration-landing-page.html>
- Set capacity limits on requests — <https://www.servicenow.com/docs/r/australia/it-operations-management/cloud-configuration-governance/set-capacity-limits-cloud-mgt.html>
- Example resource pool limited to cost center — <https://www.servicenow.com/docs/r/australia/it-operations-management/cloud-configuration-governance/use-case-resource-pool.html>
- Cloud Action Library — <https://www.servicenow.com/docs/r/australia/it-operations-management/itom-cloud-accelerate/exploring-cloud-actions-library.html>

---

## Related guides

- [ITOM overview](../itom-overview/itom-overview-guide.md)
- [Discovery](../discovery/discovery-guide.md)
- [Visibility suite](../visibility-suite/visibility-suite-guide.md)
- [Licensing and prerequisites](../../03-licensing-prerequisites.md)
