# Key Principles Research Notes — Salesforce DevOps Engineering

**Research File:** research/salesforce/salesforceyetagain-v4/2026-11-14T02-11-53Z/key_principles.md
**Source:** Salesforce crash course, ServiceNow TSOM curriculum, Salesforce DevOps best practices
**Author:** opencode
**Date:** 2026-11-14

## Core Salesforce DevOps Engineering Principles

### Principle 1: "Bulkify Everything" (Scalability Principle)

**Definition:** Code, queries, and operations must be designed to handle 200 records per transaction (max Apex batch size).

**Why It Matters:** Salesforce platform is multi-tenant; resource-heavy operations can impact all customers.

**Key Practices:**

- **SOQL:** Collect IDs first, query once, process in memory
- **DML:** Batch updates — collect records, one DML operation
- **Triggers:** Use `Trigger.new` (new records) and `Trigger.old` (old records)
- **Callouts:** Process asynchronously when possible

**Example:**
```
// ❌ BAD - query inside loop
for (Case c : Trigger.new) {
    Account a = [SELECT Id, Name FROM Account WHERE Id = :c.AccountId];
}

// ✅ GOOD - bulkified
Set<Id> accountIds = new Set<Id>();
for (Case c : Trigger.new) {
    if (c.AccountId != null) accountIds.add(c.AccountId);
}
Map<Id, Account> accountMap = new Map<Id, Account>(
    [SELECT Id, Name FROM Account WHERE Id IN :accountIds]
);
```

### Principle 2: "Most Specific Query Wins" (Query Efficiency)

**Definition:** Always query only what you need, filter on indexed fields, avoid `*` operations.

**Why It Matters:** Database performance is critical; efficient queries reduce resource consumption.

**Best Practices:**

- Use selective queries: filter on ID, Name, CreatedDate, custom indexed fields
- Avoid unindexed fields in WHERE clauses
- Do not query fields you don't need
- Use appropriate Salesforce operations (GET instead of LIST)

**Example:**
```
// ❌ INEFFICIENT - unindexed field in WHERE, all fields selected
[SELECT Id, Phone, Salary, Notes FROM Account WHERE Industry = 'Technology']

// ✅ EFFICIENT - selective field, indexed, only needed fields
[SELECT Id, Name, CreatedDate FROM Account WHERE Id = '001xx000003DGb2']
```

### Principle 3: "Security First" (Principle of Least Privilege)

**Definition:** Users should have minimum access necessary to perform their job function.

**Why It Matters:** Salesforce security model is central to data protection, compliance, and trust.

**Key Areas:**

- **Profiles:** Baseline access levels
- **Permission Sets:** Supplemental access beyond profiles
- **Roles:** Record-level sharing hierarchy
- **Field-Level Security:** Hide sensitive data from non-authorized users

**Design Philosophy:**

1. Start with minimum access (Public Read Only)
2. Add specific access via Permission Sets
3. Grant record access via Roles and Sharing Rules
4. Always review access regularly

**Example:**
```
// Profile: "HR Representative"
- Object: Employee
  - Permissions: Read only
  - Field Level: Hide Salary
  - Page Layout: Basic fields only

// Permission Set: "Salary Manager"
- Add "Edit" permission on "Salary" field

// Roles: "HR Manager" > "HR Representative"
- Org-wide default: Private
- Sharing rule: HR Manager sees all Employee records
```

### Principle 4: "Govern the Governors" (Limit Awareness)

**Definition:** Must be aware of Salesforce governor limits and enforce them in code.

**Why it Matters:** Limits protect the platform from abuse and ensure stability.

**Core Limits:**

- **SOQL queries:** 100 per transaction (sync)
- **DML rows:** 10,000 per transaction
- **Heap size:** 6 MB sync / 12 MB async
- **Callouts:** 100 per transaction
- **CPU time:** 10,000 ms sync / 60,000 ms async

**Handling Strategies:**

- **Asynchronous Processing:** `@future`, Queueable, Batch Apex
- **Batch Processing:** Handle > 200 records with Batch Apex
- **Error Handling:** Try-catch with custom exception handling
- **Monitoring:** Use Debug Logs for troubleshooting

**Example:**
```
// Governor limit check
Integer queriesUsed = Limits.getQueries();
Integer queriesLimit = Limits.getLimitQueries();
if (queriesUsed > 95) {
    System.debug('Approaching SOQL limit: ' + queriesUsed + ' / ' + queriesLimit);
}
```

### Principle 5: "Master-Detail vs Lookup Relationship" (Data Architecture)

**Definition:** Choose relationship type based on business needs and data integrity requirements.

**Why It Matters:** Impacts data integrity, user experience, and query performance.

**Relationship Types:**

- **Master-Detail:**
  - Child cannot exist without parent
  - Deleting parent deletes child
  - Roll-up summary available
  - Stronger referential integrity

- **Lookup:**
  - Child can exist without parent
  - Parent deletion does not affect child
  - No roll-up summary
  - More flexible

**Decision Factors:**

1. **Data Integrity Requirements:** Need child deletion? Use Master-Detail.
2. **Business Logic:** Need to protect child records? Use Master-Detail.
3. **Flexibility Requirements:** Child can exist independently? Use Lookup.
4. **Query Performance:** Roll-up summary needs? Use Master-Detail.
5. **User Experience:** Simpler interface? Use Master-Detail.

### Principle 6: "Named Credentials are Your Friend" (Integration Security)

**Definition:** Use Named Credentials for secure integration with external systems.

**Why It Matters:** Avoids hardcoding passwords, provides OAuth support, better governance.

**Best Practices:**

1. **Never hardcode:**
   ```
   // BAD - don't do this
   HttpRequest req = new HttpRequest();
   req.setEndpoint('https://api.example.com/data');
   req.setHeader('Authorization', 'Bearer hardcoded_token');

   // GOOD - use Named Credential
   HttpRequest req = new HttpRequest();
   req.setEndpoint('callout:MyExternalAPI/data');
   ```

2. **Use Remote Site Settings:** Required for Apex callouts (not needed for Named Credentials)
3. **Add specific authentication:** OAuth2.0, Basic Auth, etc.
4. **Document:** Document use of Named Credentials for audit purposes

### Principle 7: "Design for Troubleshooting" (DevOps Debugging)

**Definition:** Build systems that are easy to debug, monitor, and maintain.

**Why It Matters:** Real-world systems need monitoring, error handling, and performance optimization.

**Key Practices:**

- **Debug Logs:** Use Trace Flags for user-specific debugging
- **Error Handling:** Comprehensive exception handling with user-friendly messages
- **Performance Monitoring:** Monitor governor limits, CPU usage, callout times
- **Logging:** Strategic use of System.debug for development, but remove before production
- **Auditing:** Enable Field Audit Trail, Setup Audit, and Apex debugging

**Example:**
```
// Good debugging approach
HttpRequest req = new HttpRequest();
req.setEndpoint('callout:MyExternalAPI/data');
req.setMethod('GET');

Http http = new Http();
try {
    HttpResponse response = http.send(req);
    if (response.getStatusCode() == 200) {
        // Process response
    } else {
        System.debug('API callout failed: ' + response.getStatusCode() + ' - ' + response.getBody());
    }
} catch (Exception e) {
    // Log error to Apex Debug Log
    System.debug('API callout exception: ' + e.getMessage() + ' (' + e.getStackTrace() + ')');
    // Inform user appropriately
    throw new MyApiException('Failed to fetch data: ' + e.getMessage());
}
```

### Principle 8: "Sandboxes are Your Friend" (Release Management)

**Definition:** Use Salesforce Sandboxes for development and testing before deploying to Production.

**Why It Matters:** Protects production data, tests changes in isolated environment.

**Sandbox Types (for different editions):**

- **Developer Edition:** Free, limited data, manual refresh
- **Partial Copy:** Data subset, manual refresh
- **Full Copy:** Complete data, nightly refresh (higher cost)
- **Feature:** For feature delivery (needs permission)

**Best Practices:**

1. **Regular Refresh:** Schedule regular sandbox refreshes
2. **Data Sync:** For larger deployments, use data sync tools
3. **Version Control:** Always push changes to sandbox via Git
4. **Testing Strategy:** Test all functionality in sandbox before production
5. **Rollback Strategy:** Always have rollback plan ready

**DevOps Integration:**

- Git sync with sandbox branch
- Automated deployment pipelines
- Change Set generation from sandbox
- Performance testing in staging environment

### Principle 9: "CI/CD is Not Optional" (Continuous Integration/Deployment)

**Definition:** All changes should go through automated testing and deployment pipelines.

**Why It Matters:** Ensures consistency, reduces human error, speeds delivery, and improves quality.

**DevOps Stack:**

1. **Source Control:** Git with feature branch workflow
2. **Automated Builds:** CI pipeline (GitHub Actions, Jenkins, etc.)
3. **Testing:** Unit tests, integration tests, sandbox testing
4. **Deployment:** Automated deployment to sandboxes, staging, production
5. **Monitoring:** Post-deployment validation, rollback capability

**Pipeline Stages:**

1. **Code Commit:** Push to main branch with proper commit messages
2. **Build:** Automated build and package creation
3. **Unit Test:** Execute all tests
4. **Sandbox Deployment:** Deploy to Developer Sandbox for quick testing
5. **Integration Sandbox:** Deploy to Partial/Full Copy for comprehensive testing
6. **Staging:** Deploy to staging environment for user acceptance
7. **Production:** Final deployment with rollback readiness

**Example GitHub Actions Workflow:**

```yaml
name: Salesforce Deploy

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Salesforce Deploy
        uses: ./deploy-action
        with:
          sfdx_auth_url: ${{ secrets.SFDX_AUTH_URL }}
          package: force-app/main/default
          namespace: your_namespace
```

### Principle 10: "Documentation is Your Best Friend" (Knowledge Management)

**Definition:** All technical decisions, configurations, and procedures should be documented.

**Why It Matters:** Reduces onboarding time, prevents knowledge loss, ensures consistency.

**Documentation Types:**

1. **Technical Documentation:** Code, architecture, design decisions
2. **User Documentation:** Procedures, workflows, troubleshooting
3. **Configuration Documentation:** Settings, permissions, customizations
4. **Architecture Documentation:** System design, integration patterns
5. **Best Practices Documentation:** Standards, conventions, recommendations

**Documentation Strategy:**

- Use Markdown format for all technical documentation
- Store documentation in repository alongside code
- Link documentation to related code and tickets
- Regular documentation reviews and updates
- Cross-reference between documents

**Example Documentation Structure:**

```
/docs/
  /architecture/     # System design docs
  /deployment/       # Deployment procedures
  /development/      # Development guides
  /troubleshooting/  # Common issues and solutions
  /api/             # API documentation
  /standards/       # Standards and conventions
```

## Integration with Salesforce DevOps Engineer Role

These principles are particularly relevant for the DevOps Engineer role because:

### 1. Release Management
- Sandboxes + CI/CD pipelines
- Change Sets management
- Rollback strategies

### 2. Security
- Permission Sets management
- Field-Level Security
- Profile and Role hierarchy

### 3. Automation
- Flow automation
- Apex automation
- Integration automation

### 4. Scalability
- Bulkification techniques
- Governor limit awareness
- Performance optimization

### 5. Monitoring & Troubleshooting
- Debug Logs strategy
- Performance monitoring
- Error handling

## Evidence Sources

- Salesforce crash course documentation
- ServiceNow TSOM Salesforce DevOps curriculum
- Salesforce developer documentation
- GitHub repository: eltonaguiar/TSOM-Salesforce-DevOps-Learning

## Related Files in This Research Folder

- `research/salesforce/salesforceyetagain-v4/2026-11-14T02-11-53Z/crash_course.md` - Technical crash course details
- `research/salesforce/salesforceyetagain-v4/2026-11-14T02-11-53Z/_research_plan.md` - Research plan methodology
- `research/salesforce/salesforceyetagain-v4/2026-11-14T02-11-53Z/certifications.md` - Certification requirements