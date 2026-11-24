# Cloud Accelerate start

**Agent:** Kilo (deepseek-flash) · **Updated:** 2026-11-19 · **Docs release:** Australia

A 45-minute orientation to the cloud family. The first job is to name the problem correctly.

---

## 1. Name the problem

| Problem | Product | First proof |
|---|---|---|
| "I need a resource, provisioned correctly" | Cloud Services Catalog | A catalog item reaches a request and a deployed resource |
| "Who owns this account, and is it certified?" | Cloud Account Management | An account has an owner and a certification date |
| "Does this resource comply with policy?" | Cloud Configuration Governance | A scan finds a violation and a remediation path |
| "Run an action against a cloud resource" | Cloud Action Library | An action runs against a non-production resource |

If you cannot pick one, you are not ready to configure. Write the problem statement first.

---

## 2. Check entitlements

- ITOM Cloud Accelerate subscription
- Cloud Governance Suite (CGS) where Cloud Workspace is required
- CAM entitlement
- Cloud Services Catalog and Terraform Connector Store apps
- Cloud credentials and account access

See [Licensing and prerequisites](../03-licensing-prerequisites.md).

---

## 3. Orient (15 minutes)

| Open | Find | Write down |
|---|---|---|
| Cloud Workspace / Cloud Services Catalog | Home / request page | What the user sees |
| Cloud Account Management | Account list | One account, owner, status |
| Cloud Configuration Governance | Scan configuration | One policy set |
| Cloud Action Library | Actions | One action and its target |

---

## 4. Model (15 minutes)

Draw three lanes:

```
Request → Cloud Services Catalog → resource
Ownership → Cloud Account Management → certified account
Compliance → Cloud Configuration Governance → scan → remediate
```

Then draw where tags and CMDB data cross the lanes. If tags are missing, all three lanes are
weaker.

---

## 5. Practise (15 minutes)

Use a non-production account:

1. Request one small catalog item (or walk the request without submitting).
2. Find the account that owns it.
3. Run a policy scan against a small resource set.
4. Review one finding and decide whether remediation is safe.
5. Record the evidence and the owner.

If you cannot run it, produce the design and the missing-prerequisite list.

---

## 6. The one rule

**Do not design new cloud work on CPG.** It is prepared for deprecation and is not installed on
new instances. Use Cloud Services Catalog and verify the migration path for existing CPG.

---

## Official sources

- Cloud Services Catalog — <https://www.servicenow.com/docs/r/australia/it-operations-management/cloud-services-catalog/exploring-cloud-services-catalog.html>
- Cloud Account Management — <https://www.servicenow.com/docs/r/australia/it-operations-management/cloud-account-management/exploring-cam.html>
- Cloud Configuration Governance — <https://www.servicenow.com/docs/r/australia/it-operations-management/itom-cloud-accelerate/exploring-cloud-configuration-governance.html>
- CPG deprecation note — <https://www.servicenow.com/docs/r/australia/it-operations-management/cloud-configuration-governance/cloud-management-v2-landing-page.html>
- ITOM licensing — <https://www.servicenow.com/docs/r/australia/it-operations-management/explore-itom-licensing.html>
