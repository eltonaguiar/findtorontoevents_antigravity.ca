# Metadata Dependencies & Deployment Constraints — Deep Dive

This document provides exhaustive coverage of Salesforce metadata dependency chains, deployment ordering, and the failure modes that occur when dependencies are violated. It directly supports:

> **"Understanding of Salesforce limits, metadata dependencies, and deployment constraints"**
> **"Resolve deployment conflicts related to: Profiles and Permission Sets, Record Types & Page Layouts, Flows, Apex, and dependencies"**

---

## Table of Contents

- [Dependency Graph Overview](#dependency-graph-overview)
- [Core Metadata Types & Their Dependencies](#core-metadata-types--their-dependencies)
- [Deployment Order Rules](#deployment-order-rules)
- [Common Dependency Failure Patterns](#common-dependency-failure-patterns)
- [Dependency Resolution in Tools](#dependency-resolution-in-tools)
- [Advanced: Circular Dependencies](#advanced-circular-dependencies)
- [DevOps Checklist for Dependency Validation](#devops-checklist-for-dependency-validation)

---

## Dependency Graph Overview

Salesforce metadata is not a flat list of files. It forms a **directed acyclic graph (DAG)** where each component may depend on zero or more parent components. The Metadata API and deployment tools enforce this graph: a child component cannot be deployed unless its parents already exist in the target org or are included in the same deployment payload.

### Visual Dependency Hierarchy (Top-Down)

```
Organization
├── Global Settings (Company, Security, Email, Sharing)
│   └── Domain / My Domain
├── Security & Access
│   ├── Profile
│   │   ├── Object Permissions (CRUD)
│   │   ├── Field Permissions (FLS)
│   │   ├── User Permissions
│   │   ├── Application Visibility
│   │   ├── Tab Visibility
│   │   ├── Record Type Visibility
│   │   ├── Page Layout Assignment
│   │   └── Login Hours / IP Ranges
│   ├── Permission Set
│   │   ├── Object Permissions
│   │   ├── Field Permissions
│   │   ├── User Permissions
│   │   ├── Application Visibility
│   │   ├── Setup Entity Access
│   │   └── Permission Set Group (container)
│   ├── Permission Set Group
│   │   └── References Permission Sets
│   ├── Sharing Rules
│   │   ├── Owner-based
│   │   └── Criteria-based
│   ├── Role Hierarchy
│   └── Organization-Wide Defaults (OWD)
├── Objects & Schema
│   ├── CustomObject
│   │   ├── CustomField
│   │   │   ├── Picklist Values
│   │   │   ├── Formula References
│   │   │   ├── Validation Rules
│   │   │   └── Field Dependencies
│   │   ├── Record Type
│   │   │   ├── Business Process (for Case, Lead, Opportunity, Order)
│   │   │   ├── Picklist Value Subsets
│   │   │   └── Page Layout Assignment
│   │   ├── Business Process
│   │   ├── Page Layout
│   │   │   ├── Section / Field Order
│   │   │   ├── Related Lists
│   │   │   ├── Buttons / Links / Actions
│   │   │   └── Visualforce Page / Lightning Component
│   │   ├── Compact Layout
│   │   ├── List View
│   │   ├── Validation Rule
│   │   ├── Workflow Rule / Process Builder / Flow
│   │   ├── Trigger
│   │   ├── Approval Process
│   │   └── Sharing Reason
│   ├── Custom Metadata Type
│   └── Custom Setting (Hierarchy / List)
├── Automation & Logic
│   ├── Flow / FlowDefinition
│   │   ├── Flow Variable
│   │   ├── Subflow Reference
│   │   ├── Apex Action (InvocableMethod)
│   │   ├── Connector
│   │   └── Element (Screen, Decision, Assignment, Loop, Collection, etc.)
│   ├── ApexClass
│   │   ├── ApexTrigger
│   │   ├── ApexTestSuite
│   │   └── ApexPage (Visualforce)
│   ├── ApexTrigger
│   │   └── References ApexClass
│   ├── Process (Process Builder - deprecated but still deployed)
│   └── WorkflowRule
├── User Interface
│   ├── FlexiPage (Lightning Record Page / App Page / Home Page)
│   │   ├── Component Instance
│   │   └── Region Assignment
│   ├── LightningApp
│   ├── LightningComponentBundle (Aura)
│   ├── LightningWebComponent (LWC)
│   ├── AuraDefinitionBundle
│   ├── Visualforce Page
│   ├── Visualforce Component
│   ├── Tab (CustomTab)
│   │   ├── CustomObject Tab
│   │   ├── Visualforce Tab
│   │   └── Web Tab
│   ├── AppMenu (App)
│   ├── NavigationMenu
│   └── QuickAction
├── Data & Integration
│   ├── NamedCredential
│   │   ├── External Credential
│   │   └── Principal
│   ├── ExternalDataSource
│   ├── ConnectedApp
│   ├── RemoteSiteSetting
│   ├── AuthProvider
│   ├── PlatformCachePartition
│   └── ChangeDataCapture
├── Analytics & Reporting
│   ├── Report
│   ├── Dashboard
│   ├── ReportType
│   └── Folder
├── Email & Communication
│   ├── EmailTemplate
│   ├── Letterhead
│   ├── BrandSet
│   └── EmailServicesFunction
└── Packaging & Deployment
    ├── Package (1GP / 2GP)
    ├── PackageVersion
    ├── InstalledPackage
    └── Unpackaged Metadata (source deploy)
```

---

## Core Metadata Types & Their Dependencies

### 1. CustomObject → CustomField

```
CustomObject (parent)
  └── CustomField (child)
        ├── Depends on: CustomObject exists
        ├── Depends on: Picklist ValueSet (if Picklist)
        ├── Depends on: BusinessProcess (if Record Type dependent)
        ├── Validation Rule can reference this field
        ├── Formula Field can reference this field
        └── Page Layout can include this field
```

**Deployment rule**: Deploy CustomObject before CustomField. If deploying both in same payload, order in `package.xml` doesn't strictly matter for Metadata API (it resolves), but for CLI and some tools, order matters.

### 2. CustomField → RecordType → BusinessProcess → Picklist

```
CustomObject
  └── BusinessProcess (for Case, Lead, Opportunity, Order, Solution)
        ├── Name, IsActive
        └── Picklist Values (Stage/Status)
              └── RecordType
                    ├── References BusinessProcess
                    ├── References Picklist Value subsets
                    ├── References Page Layout Assignment
                    └── Requires Profile/PermissionSet visibility
```

**Critical**: A RecordType for Case/Lead/Opportunity/Order **requires** a BusinessProcess. You cannot deploy a RecordType without a BusinessProcess for these objects. For Account, Contact, Custom Objects — no BusinessProcess needed.

### 3. RecordType → PageLayout → Profile/PermissionSet

```
RecordType
  └── PageLayoutAssignment (junction)
        ├── RecordTypeId
        ├── PageLayoutId
        └── ProfileId / PermissionSetId
```

**Failure mode**: Deploy RecordType → success. Users can't see it because:
- No PageLayout assigned
- No Profile/PermissionSet grants visibility

**Fix**: Deploy RecordType + PageLayout + Profile/PermissionSet in one payload.

### 4. Flow / FlowDefinition Dependencies

```
Flow
  ├── FlowDefinition (metadata container for versioning)
  │     └── ActiveVersionNumber (points to active Flow version)
  ├── Subflow Reference (Flow A calls Flow B)
  ├── Apex Action Reference (InvocableMethod)
  ├── Object/Field References (Get Records, Update Records)
  ├── Formula References
  └── Choice / Picklist References
```

**Key constraint**: Subflow must be deployed before parent Flow, OR in same payload. If parent Flow references Subflow `API_Name`, that Subflow must exist.

**Activation**: `FlowDefinition` controls which version is Active. Deploying a new Flow version does not automatically activate it — you must update `FlowDefinition.ActiveVersionNumber`.

### 5. ApexClass → ApexTrigger

```
ApexTrigger
  ├── References ApexClass (handler pattern)
  ├── References sObjectType (trigger object)
  └── Trigger Events (before insert, after update, etc.)

ApexClass
  ├── References other ApexClass
  ├── References sObjectType fields
  ├── References Custom Metadata / Custom Settings
  ├── References Named Credential (callouts)
  └── Test Class (separate metadata)
```

**Deployment rule**: ApexTrigger **must** have test coverage. The trigger itself must be covered by tests (at least 1% per trigger, 75% org-wide).

### 6. Profile (The Monolith)

```
Profile
  ├── ObjectPermissions (CRUD per object)
  ├── FieldPermissions (FLS per field)
  ├── UserPermissions (e.g., "Modify All Data")
  ├── ApplicationVisibility
  ├── TabVisibility
  ├── RecordTypeVisibility
  ├── PageLayoutAssignment
  ├── LoginIpRange
  ├── LoginHours
  ├── ApexClassAccess
  ├── ApexPageAccess
  ├── FlowAccess
  ├── CustomPermission
  ├── CustomSettingAccess
  └── SetupEntityAccess
```

**Why Profiles break deployments**: A Profile is a **single XML file** containing all the above. Two developers editing different permissions in the same Profile create a merge conflict. A bad merge can:
- Grant "Modify All Data" accidentally
- Remove field-level security on a sensitive field
- Break layout assignment

**Best practice**: Profiles should only contain **baseline** settings. Story-level access = Permission Sets.

### 7. PermissionSet (Modular)

```
PermissionSet
  ├── ObjectPermissions
  ├── FieldPermissions
  ├── UserPermissions
  ├── ApplicationVisibility
  ├── SetupEntityAccess (ApexClass, ApexPage, Flow, etc.)
  ├── CustomPermission
  └── CustomSettingAccess
```

**Advantage**: Smaller XML. Multiple Permission Sets can be assigned to a user. They merge cleanly in Git (usually).

**PermissionSetGroup** = container for bundling:
```
PermissionSetGroup
  └── PermissionSetGroupComponent (references PermissionSet)
```

### 8. NamedCredential & ExternalCredential

```
NamedCredential
  ├── Endpoint URL
  ├── Auth Protocol (No Auth, Password, OAuth, JWT, AWS SigV4)
  ├── Certificate (for mTLS)
  ├── Allow Merge Fields in HTTP Header/Body
  └── ExternalCredential (reference)

ExternalCredential
  ├── Principal (Named Principal / Per User)
  ├── Authentication Protocol
  └── Parameters
```

**Deployment constraint**: NamedCredential **metadata** deploys. The **secret** (password, token, cert private key) does **not** deploy. You must configure secrets in each target org manually or via a secure secret injection pipeline step.

### 9. FlexiPage (Lightning Record Page)

```
FlexiPage
  ├── Type: RecordPage / AppPage / HomePage
  ├── ObjectApiName (for RecordPage)
  ├── ComponentInstance (regions: header, left, center, right, etc.)
  │     ├── Component: LightningComponentBundle / LWC / Aura / Visualforce
  │     ├── Properties (design attributes)
  │     └── Visibility Rules (filters)
  └── MasterLabel
```

**Dependency**: The referenced Lightning Component / LWC must exist in the target org or be in the same deploy.

### 10. Sharing Rules

```
SharingRule (CriteriaBasedSharingRule / OwnerSharingRule)
  ├── Object (Case, Account, CustomObject__c)
  ├── Criteria (for criteria-based)
  ├── SharedWith (Role / RoleAndSubordinates / Group / Territory)
  └── AccessLevel (Read / Edit)
```

**Dependency**: Roles and Groups must exist. OWD for the object must not be Public Read/Write (sharing rules only apply when OWD is more restrictive).

---

## Deployment Order Rules

### The Golden Rule: Parents Before Children

Deploy in this order (topological sort of dependency graph):

| Order | Metadata Type | Why |
|-------|---------------|-----|
| 1 | Global Settings (Company, Security, Sharing, Domain) | Foundation |
| 2 | CustomObject (no fields yet) | Parent of fields, record types |
| 3 | CustomField | Depends on Object |
| 4 | ValueSet / GlobalValueSet (Picklists) | Referenced by fields |
| 5 | BusinessProcess | Required for RecordType on certain objects |
| 6 | RecordType | Depends on Object, BusinessProcess, Picklists |
| 7 | PageLayout | Depends on Object, Fields, RecordTypes |
| 8 | ValidationRule / Workflow / Flow / Trigger | Depends on Object, Fields |
| 9 | Profile (baseline only) | Depends on Objects, Fields, Layouts, RecordTypes |
| 10 | PermissionSet / PermissionSetGroup | Depends on Objects, Fields, Layouts, RecordTypes |
| 11 | FlexiPage / LightningApp / Tabs / QuickActions | Depends on Objects, Components |
| 12 | ApexClass / ApexTrigger / ApexTest | Depends on Schema |
| 13 | NamedCredential / ExternalCredential | Depends on nothing (but secrets not deployed) |
| 14 | SharingRules / Role / Group | Depends on Objects, Users |
| 15 | Report / Dashboard / ReportType / Folder | Depends on Objects, Fields |

### Tool-Specific Behavior

| Tool | Dependency Resolution |
|------|----------------------|
| **sf CLI (`sf project deploy start`)** | No automatic ordering. You must order `package.xml` correctly or deploy multiple times. |
| **Gearset** | Automatic dependency analysis. UI shows "Missing dependencies" before deploy. Can auto-add. |
| **Copado** | User Story based. Dependency tracking per story. Promotion path handles ordering. |
| **AutoRABIT** | CI job can include dependency analysis. |
| **DevOps Center** | Work item based; Git-backed; promotes changes in order. |
| **Change Sets** | Manual. No dependency analysis. You add components one by one. |

---

## Common Dependency Failure Patterns

### Pattern 1: "Field Does Not Exist"

```
Error: No such column 'Custom_Field__c' on entity 'Account'
```

**Cause**: Apex, Flow, Validation Rule, or Formula references a field that isn't in the target org and wasn't in the deploy payload.

**Fix**: Include the CustomField in the same deploy. Verify field API name matches exactly (case-sensitive).

### Pattern 2: "Record Type Not Found"

```
Error: Record Type 'Custom_Record_Type' not found for 'Case'
```

**Cause**: Deploying a PageLayoutAssignment or Profile visibility for a RecordType that doesn't exist.

**Fix**: Deploy RecordType first. Include BusinessProcess for Case/Lead/Opportunity/Order.

### Pattern 3: "Picklist Value Not Found"

```
Error: Value 'New_Status' not found in picklist 'Status'
```

**Cause**: RecordType or Flow references a picklist value that doesn't exist in the target org's GlobalValueSet or standard picklist.

**Fix**: Deploy GlobalValueSet / CustomField with the picklist values first. Or use a Flow choice that doesn't depend on picklist values.

### Pattern 4: "Flow Version Not Active"

**Symptom**: Deploy succeeds, but users see old Flow behavior.

**Cause**: `FlowDefinition.ActiveVersionNumber` not updated to new version.

**Fix**: 
- In Gearset: Check "Activate Flow" on deploy
- In CLI: Deploy Flow, then update FlowDefinition via Metadata API or Tooling API
- In Copado: Promotion step includes activation

### Pattern 5: "Apex Class Not Found" (Dependency)

```
Error: Dependent class is invalid and needs recompilation
```

**Cause**: Class A references Class B. Class B not in org and not in payload.

**Fix**: Include all referenced classes. Gearset's "Analyze" button catches this.

### Pattern 6: "Invalid Cross Reference ID"

```
Error: Invalid cross reference id
```

**Cause**: A component references another by ID (not API name) and that ID doesn't exist in target. Common in:
- Profile LayoutAssignment (uses Layout ID)
- RecordType PageLayoutAssignment
- Sharing Rules (Role/Group IDs)

**Fix**: Deploy by API name, not ID. Ensure referenced components exist.

### Pattern 7: "Cannot Modify Managed Object"

```
Error: CANNOT_MODIFY_MANAGED_OBJECT
```

**Cause**: Attempting to change a component from a managed package (namespace prefix).

**Fix**: Don't deploy changes to managed components. Configure around them.

### Pattern 8: "Test Fails Due to Missing Data"

```
Error: System.QueryException: List has no rows for assignment to SObject
```

**Cause**: Test queries for a record that exists in Dev but not in QA/Prod.

**Fix**: Tests create their own data. Use `@TestSetup` or insert in test method.

---

## Dependency Resolution in Tools

### Gearset

1. **Compare** → Select source & target orgs
2. **Analyze** → Gearset builds dependency graph
3. **Missing Dependencies** panel → Shows components referenced but not selected
4. **Auto-add dependencies** → Checkbox to include them
5. **Deploy** → Validates, runs tests, shows results

**UI Path**: Compare → [Select Items] → Analyze → [Review Missing Dependencies] → Deploy

### Copado

1. **User Story** → Link metadata components
2. **Promotion** → Moves story through environments
3. **Dependency Tracker** → Shows what each story depends on
4. **Back Promotion** → Moves changes from higher env back to lower

**UI Path**: User Stories → [Select Story] → Promote → [Select Promotion Path] → Validate → Deploy

### sf CLI (Manual)

```bash
# 1. Retrieve from source org
sf project retrieve start --manifest manifest/package.xml --target-org dev

# 2. Dry-run deploy to target (validates dependencies)
sf project deploy start --manifest manifest/package.xml --dry-run --target-org qa

# 3. If errors about missing components, add them to package.xml and repeat

# 4. Real deploy
sf project deploy start --manifest manifest/package.xml --target-org qa
```

### Destructive Changes (Deletes)

```bash
# Deletes are separate from adds/updates
sf project deploy start \
  --manifest manifest/package.xml \
  --post-destructive-changes manifest/destructiveChanges.xml \
  --target-org qa
```

**Pre-destructive** (delete before add): Use `--pre-destructive-changes` for renames that would collide.

---

## Advanced: Circular Dependencies

Salesforce metadata **can** have circular dependencies. Example:

- Flow A calls Subflow B
- Flow B calls Subflow A (directly or indirectly)

Or:
- Apex Class A calls Class B
- Class B calls Class A

Or:
- Object A has lookup to Object B
- Object B has lookup to Object A

**Deployment impact**: Metadata API cannot deploy circular references in a single deploy. You must:

1. Deploy one side without the reference
2. Deploy the other side with the reference
3. Update the first side to add the reference

**Tool support**: Gearset and Copado detect circular deploys and guide you through multi-step deploys.

---

## DevOps Checklist for Dependency Validation

Before any promotion (QA → UAT → Pre-Prod → Prod):

- [ ] Run **Compare/Analyze** in Gearset or equivalent in other tools
- [ ] Review **Missing Dependencies** panel — accept or reject each
- [ ] Verify **Flow activation** settings (Deploy as Active vs Draft)
- [ ] Confirm **RecordType + Layout + Visibility** are all selected
- [ ] Check **Profile vs PermissionSet** — avoid deploying Profile for story access
- [ ] Ensure **NamedCredential secrets** are configured in target (not deployed)
- [ ] Run **dry-run validation** with `RunSpecifiedTests` or `RunLocalTests`
- [ ] Verify **test classes** are included for any Apex changes
- [ ] Confirm **destructiveChanges.xml** is intentional and reviewed
- [ ] Tag the Git commit with the release version for rollback

---

*This document is part of the Salesforce DevOps Engineer training track based on requisition 276046 (Scotiabank Commercial Banking Engineering, Toronto).*