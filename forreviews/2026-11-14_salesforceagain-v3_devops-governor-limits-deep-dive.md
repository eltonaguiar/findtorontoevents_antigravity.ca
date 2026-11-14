# Salesforce Governor Limits & System Properties — Deep Dive

This document is the exhaustive reference for Salesforce limits, system properties, and deployment constraints that a Salesforce DevOps Engineer must understand when building CI/CD pipelines, designing environments, and troubleshooting deployment failures.

It maps directly to the Scotiabank DevOps Engineer (Salesforce) job description line:

> **"Understanding of Salesforce limits, metadata dependencies, and deployment constraints"**

---

## Table of Contents

- [Apex Governor Limits (Synchronous)](#apex-governor-limits-synchronous)
- [Apex Governor Limits (Asynchronous)](#apex-governor-limits-asynchronous)
- [Flow Limits](#flow-limits)
- [SOQL / SOSL Limits](#soql--sosl-limits)
- [DML Limits](#dml-limits)
- [Apex Code Size & Class Limits](#apex-code-size--class-limits)
- [Package & Deployment Limits](#package--deployment-limits)
- [Metadata Component Limits](#metadata-component-limits)
- [System Properties & Context](#system-properties--context)
- [Org-Wide & Edition Limits](#org-wide--edition-limits)
- [Deployment Constraints & Failure Modes](#deployment-constraints--failure-modes)
- [Practical Examples: How Limits Break Deploys](#practical-examples-how-limits-break-deploys)
- [Quick Reference Table](#quick-reference-table)

---

## Apex Governor Limits (Synchronous)

Governor limits are per-transaction, per-namespace runtime caps enforced by the Salesforce platform. They are not per-org or per-user — they are per execution context. Every trigger, class, anonymous block, Flow, and Lightning component execution is subject to these.

### Most Important Governor Limits (Sync Context)

| Limit | Sync Limit | Notes |
|-------|-----------|-------|
| Total SOQL queries issued | 100 | Per transaction |
| Total records returned by SOQL queries | 50,000 | Aggregate across all queries |
| Records retrieved by `Database.getQueryLocator` | 10,000 | For Batch Apex / read-only |
| Records processed by a Batch Apex `execute` | 200 | Default batch size |
| Total DML statements issued | 150 | insert/update/delete/upsert/merge/undelete |
| Total records processed by DML | 10,000 | Aggregate across all DML |
| Total CPU time | 10,000 ms (10 sec) | Synchronous Apex |
| Total CPU time (read-only context) | 60,000 ms | Visualforce / Lightning read-only pages |
| Total heap size | 6 MB | Synchronous; 12 MB async |
| Total callouts (HTTP requests) | 100 | Per transaction |
| Total callout timeout | 120 seconds | Cumulative |
| Total email messages sent via `SingleEmailMessage` | 10 | Per transaction |
| Total email messages sent via `MassEmailMessage` | 1 | Per transaction |
| Total `future` method calls | 50 | Per transaction |
| Total `Queueable` jobs chained | 50 | Per transaction (chain limit) |
| Total `Scheduled Apex` jobs scheduled | 100 | Per 24 hours (per org) |
| Total `Batch Apex` jobs queued | 5 | Per 24 hours (concurrent active) |
| Total `Batch Apex` `execute` batches per job | 2,000 | Max chunks |
| Stack depth for trigger invocations | 16 | Nested trigger recursion |
| Inbound email size limit | 25 MB | |
| Anonymous block size | 200,000 characters | |

### Critical Nuances

1. **CPU time includes everything**: Apex execution, Formula evaluation, Workflow field updates, Process Builder, Flows (before-save and after-save), and callouts all count toward the same 10,000 ms budget.

2. **Heap size is per transaction, not per class**: If a trigger calls a helper class, both share the same 6 MB heap. Large collections (Maps, Lists) can blow heap quickly.

3. **SOQL governor limits apply per transaction, not per query**: You cannot "reset" limits by making a second transaction within the same request. A single Visualforce page load or Lightning action is one transaction.

4. **Bulkification is mandatory**: If your code processes 200 records in one trigger execution (the standard Trigger.new batch size), you must bulkify SOQL and DML. A query inside a `for` loop is the #1 deployment risk.

5. **Test methods share governor limits**: Tests run in the same governor context. A test that inserts 200 records consumes DML rows. Tests that don't create their own data will fail in sandboxes where those rows don't exist.

---

## Apex Governor Limits (Asynchronous)

| Limit | Async Limit | Context |
|-------|------------|---------|
| Total CPU time | 60,000 ms (60 sec) | Future, Queueable, Batch |
| Total heap size | 12 MB | Future, Queueable, Batch |
| Total SOQL queries | 200 | Future, Queueable |
| Total DML statements | 150 | Future, Queueable |
| Batch Apex `start` method query records | 50,000,000 | QueryLocator max |
| Batch Apex concurrency (active jobs) | 5 | Per org |
| Queueable jobs per transaction | 50 | Chain depth |
| `@future` calls per transaction | 50 | |
| Scheduled Apex per 24 hours | 250,000 (org-wide) | All scheduled jobs |

**Implication for DevOps**: Async Apex is where you move heavy processing to avoid sync limits. But async is not "unlimited" — it just has a larger budget. Your pipeline should still test async classes against realistic data volumes.

---

## Flow Limits

Flows (Screen Flows, Auto-launched Flows, Before-Save / After-Save) are subject to their own governor limits, AND they count against Apex governor limits when invoked from triggers or processes.

| Flow Limit | Value |
|------------|-------|
| Total Flow elements executed per flow interview | 2,000 |
| Total SOQL queries in a flow | 100 (shared with Apex transaction) |
| Total DML statements in a flow | 150 (shared with Apex transaction) |
| CPU time consumed by flow | Counts against 10,000 ms Apex limit |
| Scheduled Flow batch size | 200 records |
| Scheduled Flow max interviews per day | 250,000 (org) |
| Before-save flow DML | Auto-committed, no explicit DML needed |
| After-save flow DML | Explicit DML actions allowed |
| Loop iterations in a flow | Limited by 2,000 element limit |

### Before-Save vs After-Save Flow

| | Before-Save | After-Save |
|---|-------------|------------|
| When it runs | Before record is saved to DB | After record is saved |
| Can update triggering record | Yes (no DML needed) | Requires DML/update element |
| Governor limit impact | Counts against transaction | Counts against transaction |
| Best for | Field updates, validation, default values | Related record creation, callouts, emails |
| Risk | Can cause recursion if it updates the same object | Can cause infinite loops with record-triggered flows on same object |

**DevOps implication**: A before-save Flow that updates the triggering record can recursively trigger after-save flows on the same object. This is a common deployment failure that only appears under real volume — not in a Developer sandbox with 5 records.

---

## SOQL / SOSL Limits

| Limit | Value |
|-------|-------|
| SOQL queries per transaction | 100 |
| Records returned per SOQL query | 50,000 |
| `LIMIT` clause max | 50,000 |
| OFFSET max | 2,000 |
| Child-to-parent relationship levels | 5 |
| Parent-to-child relationship levels | 1 |
| `WITH SECURITY_ENFORCED` | Enforces FLS in Apex |
| `WITH SHARING` / `WITHOUT SHARING` | Sharing model enforcement |
| SOSL queries per transaction | 20 |
| SOSL records returned | 2,000 |
| `COUNT()` queries | Count toward query limit |

### Relationship Queries

```
SELECT Id, Name, (SELECT Id FROM Contacts) FROM Account
```

The child subquery counts as **one** additional query toward the 100-query limit. Nested subqueries are limited: one level of parent-to-child (no grandchildren in subqueries).

**Deployment risk**: A SOQL query that works in Dev (10 Accounts) returns 50,001 records in Prod and fails with `QueryException: Too many query rows: 50001`. This is a data-volume governor failure, not a code failure.

---

## DML Limits

| Limit | Value |
|-------|-------|
| DML statements per transaction | 150 |
| Records processed per DML statement | 10,000 |
| `Database.insert(list, false)` (partial success) | Allowed, still counts as 1 statement |
| `Database.rollback(Savepoint)` | Allowed within transaction |
| Rollback savepoints per transaction | 10 |

**Key rule**: A `for` loop containing `update record` is 1 DML statement per iteration. 201 iterations = governor limit exception. Always collect records into a `List<sObject>` and call `update list` once outside the loop.

---

## Apex Code Size & Class Limits

| Limit | Value |
|-------|-------|
| Apex class size | 1 MB |
| Apex trigger size | 1 MB |
| Total Apex code in an org (unmanaged) | 3 MB (Developer Edition); varies by edition |
| Number of Apex classes | Limited by org storage |
| Anonymous Apex block | 200,000 characters |
| Maximum characters in a single string | 6 MB (heap limit) |

**Deployment risk**: Unlocked packages have their own code coverage and package size limits. A managed package class cannot be modified in a subscriber org — attempting to deploy changes to managed components returns `CANNOT_MODIFY_MANAGED_OBJECT`.

---

## Package & Deployment Limits

| Limit | Value |
|-------|-------|
| Components in a single deploy (Metadata API) | 10,000 |
| File size per component | 10 MB |
| Total deploy zip size | 400 MB (recommended); hard limits vary |
| Metadata API async deploy timeout | 10 minutes (polling window) |
| Quick Deploy window | 10 days after successful validation |
| Test coverage required for production deploy (with Apex) | 75% org-wide; 100% for each trigger (if trigger has coverage) |
| `RunAllTestsInOrg` | Runs every test; slowest |
| `RunSpecifiedTests` | Runs only named tests; must cover deployed code |
| `RunLocalTests` | Runs local (non-managed) tests |
| `NoTestRun` | No tests; rejected in production with Apex |

### Unlocked Package Limits

| Limit | Value |
|-------|-------|
| Package version creation wait | ~5-15 minutes typical |
| Unlocked package install | No namespace required |
| Dependencies between unlocked packages | Supported via `sfdx-project.json` |
| Upgrade path | Versioned; can upgrade but not downgrade |

### Managed Package Limits

| Limit | Value |
|-------|-------|
| Components modifiable in subscriber org | None (managed components are read-only) |
| Namespace | Required |
| Patch org | Required for 1GP patches |
| 2GP | No patch org; create new version |

---

## Metadata Component Limits

These matter when you construct `package.xml` or select components in Gearset/Copado.

| Metadata Type | Deployment Notes |
|---------------|------------------|
| CustomObject | Must include fields in same deploy or they already exist |
| CustomField | Parent object must exist |
| ApexClass | Must compile against target org dependencies |
| ApexTrigger | Requires at least 1% test coverage on the trigger itself |
| Flow / FlowDefinition | Version must be Active to be usable by users |
| Profile | Huge XML; conflicts easily; prefer Permission Sets |
| PermissionSet | Smaller, merge-friendly |
| RecordType | Depends on BusinessProcess, Picklist, Page Layout |
| CustomTab | Depends on CustomObject or Visualforce page |
| Layout / FlexiPage | Layout assignment lives on Profile/RecordType |

**Dependency order matters**: Deploy objects before fields, fields before record types, record types before layouts, layouts before profiles/permission sets. Gearset and Copado handle dependency ordering automatically, but raw `sf` CLI does not — you must order `package.xml` members correctly.

---

## System Properties & Context

### System Class Properties

| Property | Value / Description |
|----------|---------------------|
| `System.isBatch()` | True if running in Batch Apex context |
| `System.isFuture()` | True if running in `@future` context |
| `System.isQueueable()` | True if running in Queueable context |
| `System.isScheduled()` | True if running in Scheduled Apex |
| `System.isExecutingTests()` / `Test.isRunningTest()` | True during test execution |
| `System.now()` | Returns current Datetime (org timezone) |
| `UserInfo.getOrganizationId()` | Returns 15/18-char Org ID |
| `UserInfo.getUserId()` | Returns running user Id |
| `UserInfo.isMultiCurrencyOrganization()` | Boolean |
| `UserInfo.getDefaultCurrency()` | Iso code |
| `UserInfo.getSessionId()` | Returns session ID (not available in async) |
| `UserInfo.getUiThemeDisplayed()` | Returns theme (Theme3, Theme4d, etc.) |
| `System.URL.getSalesforceBaseUrl()` | Returns base URL per environment |

### Organization-Wide Defaults (OWD)

| Setting | Values |
|---------|--------|
| Account OWD | Private, Public Read Only, Public Read/Write, Public Read/Write/Transfer |
| Contact OWD | Controlled by Parent (default), Private, Public Read Only, Public Read/Write |
| Case OWD | Private, Public Read Only, Public Read/Write |
| Lead OWD | Private, Public Read Only, Public Read/Write |
| Custom Object OWD | Private, Public Read Only, Public Read/Write, Public Read/Write/Transfer |

**Deployment impact**: Changing OWD can trigger massive sharing recalculation. In production, this can take hours and lock metadata changes. DevOps must schedule OWD changes outside peak windows.

### Sharing Rules

| Type | Scope |
|------|-------|
| Owner-based sharing | Grant access based on record owner |
| Criteria-based sharing | Grant access based on field values |
| Manual sharing | User-to-user (not deployable via metadata easily) |
| Apex managed sharing | Programmatic (requires `with sharing` classes) |

---

## Org-Wide & Edition Limits

| Limit | Developer Edition | Enterprise | Unlimited | Professional |
|-------|-------------------|------------|-----------|--------------|
| Custom objects | 200 | Unlimited (licensed) | Unlimited | Limited |
| Custom fields per object | 500 | 800 | 800 | Limited |
| Custom tabs | 25 | Unlimited | Unlimited | Limited |
| Data storage | 5 MB | Varies | Varies | Varies |
| File storage | 5 MB | Varies | Varies | Varies |
| API requests per 24 hours | 15,000 | 15,000-1M+ | 1M+ | Limited |
| Concurrent API requests | 25 | 25+ | 25+ | Limited |
| Sandbox types available | None | Developer, Pro, Partial, Full | All | Limited |

**Enterprise (Commercial Banking typical)**: Full sandbox, unlimited custom objects (licensed), high API limits, change sets, Metadata API, CLI, unlocked packages.

---

## Deployment Constraints & Failure Modes

### 1. Cross-Reference Errors

```
Invalid cross reference id
```

**Cause**: A field, record type, layout, or picklist value references a component not in the deploy payload and not already in the target org.

**Fix**: Include the parent metadata component in the same deploy. E.g., deploying a Record Type without its Business Process fails.

### 2. Entity Not Found / Apex Dependency

```
ApexClass.MyClass depends on ApexClass.Dependency which is not in the org
```

**Cause**: Deploying Class A without Class B, where A references B.

**Fix**: Deploy all dependent classes in the same payload. Gearset's dependency analyzer catches this.

### 3. Missing Test Coverage

```
Code coverage warning: Average test coverage for all Apex Classes is 60%, at least 75% is required
```

**Cause**: Production deploy with Apex requires 75% org-wide coverage and 100% trigger coverage (if any trigger exists).

**Fix**: Run `RunLocalTests` or `RunSpecifiedTests` in CI before production. Don't rely on `NoTestRun`.

### 4. Managed Component Modification

```
CANNOT_MODIFY_MANAGED_OBJECT: entity is managed
```

**Cause**: Attempting to modify a component from a managed package (e.g., an AppExchange app).

**Fix**: Do not deploy changes to managed components. Configure around them via declarative tools, or upgrade the package version.

### 5. Profile Field Permission Conflicts

```
Field Level Security: field Account.Custom_Field__c is not accessible
```

**Cause**: Profile in payload grants FLS on a field that doesn't exist in target, or revokes FLS on a field that profiles depend on.

**Fix**: Use Permission Sets instead of profiles for story-level access. Deploy field and profile/permission set together.

### 6. Flow Version Not Active

**Symptom**: Flow deploy succeeds, but users see the old screen logic.

**Cause**: The deployed Flow version is `Draft`, not `Active`. Gearset/Copado can set activation on deploy; `sf` CLI requires explicit activation.

**Fix**: Activate the Flow version in the deploy, or deploy with `activeVersion=true`.

### 7. Record Type Visibility Missing

**Symptom**: Record Type deploys but users can't select it.

**Cause**: Missing Page Layout assignment or missing visibility on Profile/Permission Set.

**Fix**: Deploy RecordType + Layout + Permission Set/Profile in one payload.

---

## Practical Examples: How Limits Break Deploys

### Example 1: SOQL in a Loop (Trigger)

```apex
// BAD: 200 records × 1 query each = 200 SOQL queries → Limit Exception
trigger AccountTrigger on Account (before insert) {
    for (Account a : Trigger.new) {
        List<Contact> contacts = [SELECT Id FROM Contact WHERE AccountId = :a.Id];
    }
}
```

**Deployment impact**: Passes in Developer sandbox (10 Accounts), fails in QA sandbox (200+ Accounts) and production.

**Fix**: Bulkify — query all contacts outside the loop:

```apex
// GOOD: 1 query total
Set<Id> accountIds = new Set<Id>();
for (Account a : Trigger.new) accountIds.add(a.Id);
Map<Id, List<Contact>> contactsByAccount = new Map<Id, List<Contact>>();
for (Contact c : [SELECT Id, AccountId FROM Contact WHERE AccountId IN :accountIds]) {
    if (!contactsByAccount.containsKey(c.AccountId))
        contactsByAccount.put(c.AccountId, new List<Contact>());
    contactsByAccount.get(c.AccountId).add(c);
}
```

### Example 2: Test Data Missing in Empty Sandbox

```apex
// BAD: Assumes an Account exists
@isTest
static void testDiscount() {
    Account a = [SELECT Id FROM Account LIMIT 1]; // Fails in empty QA sandbox
    // ...
}
```

**Fix**: Tests create their own data:

```apex
@isTest
static void testDiscount() {
    Account a = new Account(Name = 'Test Account');
    insert a;
    // ...
}
```

### Example 3: Before-Save Flow Recursion

A before-save Flow on Account updates Account fields. An after-save Flow on Account creates a child record, which fires another Account update... infinite loop under bulk data.

**DevOps check**: Review Flow entry conditions and update actions before promoting to production. Use `IsFirstTransactionOperationContext` or recursion guards in Apex if Flows call invocable methods.

### Example 4: Heap Size in Batch Apex

Processing 10,000 records with large collections in a single `execute` batch can exceed 12 MB heap (async limit).

**Fix**: Reduce batch size (`Database.executeBatch(myClass, 100)`), clear collections between iterations, avoid storing entire query results in memory.

---

## Quick Reference Table

| Category | Key Limit | Why DevOps Cares |
|----------|-----------|------------------|
| SOQL queries (sync) | 100 / transaction | Bulkify triggers; don't query in loops |
| SOQL rows returned | 50,000 / transaction | Test with prod-like data volumes |
| DML statements | 150 / transaction | Batch DML operations outside loops |
| DML records | 10,000 / transaction | Bulk update patterns |
| CPU time (sync) | 10,000 ms | Flows + Apex + formulas share this |
| Heap size (sync) | 6 MB | Large collections break deployment |
| Heap size (async) | 12 MB | Batch/Future can process more, but still bounded |
| Test coverage (prod) | 75% org-wide | Gate in CI; RunLocalTests before window |
| Components per deploy | 10,000 | Package.xml size management |
| Quick Deploy window | 10 days | Validate early, quick-deploy in window |
| Batch Apex concurrent | 5 jobs | Don't schedule too many simultaneous batches |
| Scheduled Apex per day | 250,000 (org) | Monitor scheduled job count |
| Cross-reference id | Must exist in target | Deploy dependencies together |
| Managed object | Cannot modify | Don't deploy changes to managed components |

---

## DevOps Checklist: Limits Before Production

- [ ] No SOQL inside `for` loops in any Apex class/trigger
- [ ] No DML inside `for` loops
- [ ] Tests create their own data (no reliance on org records)
- [ ] 75%+ code coverage in QA/UAT/Pre-Prod
- [ ] No changes to managed package components
- [ ] Flow versions set to Active on deploy
- [ ] Record Types deployed with Page Layouts and visibility
- [ ] Permission Sets used instead of profile edits for story-level access
- [ ] Batch Apex batch size tuned for data volume
- [ ] Asynchronous processing used for operations > 10,000 records
- [ ] OWD changes scheduled outside business hours

---

*This document is part of the Salesforce DevOps Engineer training track based on requisition 276046 (Scotiabank Commercial Banking Engineering, Toronto).*
