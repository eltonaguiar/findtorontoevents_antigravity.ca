# Salesforce DevOps Gearset UI Deep Dive

> **Version:** 1.0
> **Date:** 2026-11-14
> **Worktree:** salesforceagain-v3
> **Objective:** Comprehensive documentation of Gearset UI workflows for Salesforce CI/CD, deployment management, and backup operations.

## Table of Contents

1. [Gearset Overview & Key Benefits](#gearset-overview--key-benefits)
2. [User Interface Layout](#user-interface-layout)
3. [Comparison Workflow](#comparison-workflow)
4. [Deployment Operations](#deployment-operations)
5. [Backup & Recovery](#backup--recovery)
6. [CI/CD Integration](#cicd-integration)
7. [Best Practices & Tips](#best-practices--tips)
8. [Governor Limits Considerations](#governor-limits-considerations)
9. [Metadata Dependency Awareness](#metadata-dependency-awareness)

---

## 1. Gearset Overview & Key Benefits

Gearset is a Salesforce-specific CI/CD and deployment tool that integrates seamlessly with the Salesforce metadata model. Key benefits:

- **Metadata-aware deployment** - Understands Salesforce dependency relationships
- **Sandbox refresh safety** - Prevents deployment failures after sandbox refreshes
- **Automated CI/CD pipelines** - Git integration with GitHub, Azure DevOps, Bitbucket
- **Change set alternatives** - Replaces manual change sets with automated deployments
- **Backup & recovery** - Automated daily backups of production org metadata
- **Version control** - Tracks every deployment with rollback capabilities
- **Multi-org management** - Manage sandbox, dev, and production from single interface

---

## 2. User Interface Layout

### Main Navigation Sections

| Section | Description | Key Features |
|---------|-------------|------------|
| **Home** | Dashboard showing org status, recent activity | Org selector, quick stats, recent deployments |
| **Comparisons** | Side-by-side metadata comparison between orgs or git branches | Diff view, selective inclusion/exclusion, merge conflicts |
| **Deployments** | Deploy metadata between orgs or from git | Deployment wizard, rollback, deployment reports |
| **Backups** | Schedule and manage automated backups | Backup schedules, restore points, retention policies |
| **Pipelines** | CI/CD pipeline configuration and monitoring | Git integration, trigger conditions, pipeline runs |
| **Alerts** | Deployment failure notifications and monitoring | Slack/Email alerts, failure patterns, SLA monitoring |

### Comparison Page Layout

```text
+----------------------------------------------------------+
|  Source Org/Branch          |  Target Org/Branch      |
|  ▼                           ▼                        |
|  [Select source]                                          |
|                                                           |
|  Diff Results:                                            |
|  ▶ Apex Classes: 12 changed                              |
|  ▶ Triggers: 3 added                                      |
|  ▶ Profiles: 5 modified                                  |
|  ▶ Permission Sets: 2 added                               |
|  ▶ Flow: 1 modified                                       |
|  ▼                                                       |
|  [Include/Exclude buttons] [Compare] [Cancel]            |
+----------------------------------------------------------+
```

### Deployment Page Layout

```text
+----------------------------------------------------------+
|  Source                                          |  Target  |
|  ▼                                                  ▼        |
|  [Select source org/branch]                          |
|                                                           |
|  Select metadata components to include:                  |
|  ☐ Apex Classes                                       |
|  □ Apex Triggers                                      |
|  □ Profiles                                           |
|  □ Permission Sets                                    |
|  □ Email Templates                                    |
|  □ Flows                                              |
|  □ Record Types                                       |
|  □ Object fields                                      |
|  □ Validation Rules                                   |
|  □ Static Resources                                    |
|                                                           |
|  [Add All] [Remove All] [Deploy]                        |
+----------------------------------------------------------+
```

---

## 3. Comparison Workflow

### Step-by-Step Comparison Process

1. **Select Source and Target Orgs**
   - Choose source: development org, feature branch, or production
   - Choose target: sandbox, next sandbox refresh, or production
   - Gearset automatically maps metadata relationships

2. **Run Comparison**
   - Click **Compare** to analyze metadata differences
   - Review auto-categorized changes (added, modified, deleted)
   - Use filter options to exclude specific metadata types

3. **Review Diff Results**
   - **Included**: Changes selected for deployment
   - **Excluded**: Changes filtered out
   - **Conflict**: Changes that may cause deployment issues
   - **View Details**: Expand any component to see specific changes

4. **Selective Inclusion/Exclusion**
   - Toggle individual components on/off
   - Exclude test classes if not needed for quick deploy
   - Include only specific versions of Apex classes

5. **Merge Conflicts**
   - Gearset detects deployment conflicts
   - Manual resolution required for conflicting changes
   - Review component-level changes before proceeding

---

## 4. Deployment Operations

### Deployment Types

| Deployment Type | Description | Use Case |
|-----------------|-------------|----------|
| **Sandbox to Sandbox** | Deploy from one sandbox to another | Feature branch integration, testing workflows |
| **Sandbox to Production** | Deploy validated changes to production | Production release after full QA |
| **Git to Sandbox** | Deploy from git repository to sandbox | CI/CD pipeline from version control |
| **Git to Production** | Deploy from git to production | Automated production releases |
| **Backup Restore** | Restore from backup to any org | Disaster recovery, sandbox refresh recovery |

### Deployment Wizard Steps

1. **Select Source**
   - Choose from connected orgs or git integrations
   - Select specific branch or tag if using git

2. **Select Target**
   - Choose destination org (sandbox or production)
   - Verify target org is accessible and licensed

3. **Select Metadata**
   - Check/uncheck component types to include/exclude
   - Review dependency warnings
   - Salesforce automatically includes required dependencies

4. **Review & Deploy**
   - Review deployment summary
   - Add deployment notes/comments
   - Click **Deploy** to initiate deployment
   - Monitor deployment progress in real-time

### Deployment Best Practices

- **Never deploy directly to production from comparison** - Always validate in sandbox first
- **Use "Selective Deployment"** - Include only changed components, not entire org
- **Check dependency warnings** - Gearset shows required dependencies
- **Schedule deployments** - Off-peak hours for production deployments
- **Enable auto-rollback** - Configure automatic rollback on failure

### Post-Deployment Verification

- Review deployment report for success/failure counts
- Check **Setup > Deployment Status** in target org
- Verify critical metadata types (profiles, permissions, Apex classes)
- Run **Run All Tests** if Apex changes were deployed
- Validate **record counts** and **data integrity** after deployment

---

## 5. Backup & Recovery

### Automated Backup Configuration

1. **Enable Backup for Org**
   - Navigate to **Backups** section
   - Select org to protect
   - Configure backup schedule (daily, weekly, or manual)

2. **Backup Frequency Recommendations**
   - **Production**: Daily automatic backups
   - **Critical sandboxes**: Weekly automatic backups
   - **Dev sandboxes**: Manual backups before major changes

3. **Retention Policies**
   - Keep last 7 days of daily backups
   - Keep last 4 weeks of weekly backups
   - Keep last 3 major releases of monthly backups

### Manual Backup Process

1. Navigate to **Backups** > **Create Manual Backup**
2. Add descriptive name/notes for the backup
3. Click **Create Backup**
4. Backup becomes immediately available for restore

### Restore Process

1. Navigate to **Backups** > **Select Backup Point**
2. Choose from available backup snapshots
3. Select target org (can restore to same or different org)
4. Click **Restore** - Gearset handles metadata dependency resolution
5. Verify restored org metadata after completion

### Backup Best Practices

- **Always backup before sandbox refreshes** - Prevents loss of customizations
- **Backup before production deployments** - Safety net for rollback
- **Test restore procedures quarterly** - Ensure backups are valid
- **Document backup retention policy** - Compliance and governance requirements
- **Monitor backup storage usage** - Avoid exceeding org limits

---

## 6. CI/CD Integration

### Git Integration Setup

1. **Connect Git Repository**
   - Supported: GitHub, Azure DevOps, Bitbucket, GitLab
   - Generate OAuth token for repository access
   - Select branch mapping (default: main → production)

2. **Pipeline Configuration**
   - Define pipeline stages: Test → Validate → Deploy
   - Set trigger conditions: Push events, Pull Request merges, Scheduled
   - Configure environment mappings: dev → sandbox, test → sandbox, prod → production

3. **Pipeline Stages**
   ```yaml
   # Example GitHub Actions + Gearset pipeline
   stages:
     - name: "Run Apex Tests"
       stage: "test"
       command: "sf apex run test --testlevel RunLocal"
     - name: "Validate Metadata"
       stage: "validate"
       gearset_action: "compare"
     - name: "Deploy to Sandbox"
       stage: "deploy"
       gearset_action: "deploy"
       target: "sandbox-env"
     - name: "Deploy to Production"
       stage: "prod-deploy"
       gearset_action: "deploy"
       target: "production"
       approvals: ["team-lead", "security-review"]
   ```

3. **Environment Promotion Flow**
   - **Feature branch** → **Dev sandbox** → **Test sandbox** → **Staging** → **Production**
   - Each stage has automated Gearset deployment
   - Manual approval gates at critical transitions
   - Automatic rollback on test failures

### GitHub Integration Example

```json
{
  "repository": "eltonaguiar/findtorontoevents_antigravity",
  "branches": {
    "dev": "dev-sandbox",
    "feature/*": "feature-sandboxes",
    "main": "production"
  },
  "triggers": {
    "pull_request": "deploy-to-test-sandbox",
    "push-to-main": "production-approval-required"
  }
}
```

### Pipeline Monitoring

- **Real-time deployment status** in Gearset UI
- **Failure notifications** via Slack, email, or webhook
- **Deployment history** with rollback capabilities
- **Audit logs** for compliance and governance

---

## 7. Best Practices & Tips

### Daily Workflow Best Practices

| Practice | Recommendation | Rationale |
|----------|----------------|-----------|
| **Morning check** | Review overnight deployments and backup status | Catch failures early |
| **Feature branch sync** | Keep feature branches in sync with dev sandbox | Prevent merge conflicts |
| **Pre-deployment checklist** | Run tests, validate dependencies, check governor limits | Reduce deployment failures |
| **Post-deployment verification** | Verify critical metadata, run key tests | Ensure changes work as expected |
| **End-of-day backup** | Manual backup of production if changes were made | Disaster recovery |

### Common Gearset UI Patterns

- **Ctrl+Click** to select multiple metadata components
- **Drag-and-drop** to reorder deployment priority
- **Filter bar** to quickly find specific components by name
- **Search** to find components across large deployments
- **Comparison heatmap** visual shows change density across orgs

### Avoid These Common Mistakes

❌ **Deploying without checking dependencies** - Always review dependency warnings
❌ **Deploying multiple metadata types with circular dependencies** - Resolve order first
❌ **Skipping test validation** - Always run tests in sandbox before production
❌ **Overwriting custom configurations** - Use selective deployment, not "Add All"
❌ **Ignoring governor limit warnings** - Monitor CPU time, heap size, SOQL queries

---

## 8. Governor Limits Considerations

### Gearset Operations & Salesforce Limits

| Operation | Potential Limit | Mitigation Strategy |
|-----------|-----------------|---------------------|
| **Apex Tests** | 6 min cumulative CPU time per execution context | Run tests in parallel, reduce test granularity |
| **SOQL Queries** | 100 queries per Apex transaction | Bulk query, selective filtering, use SOSL for text search |
| **DML Rows** | 10,000 rows per transaction | Bulk API, batch sizes, chunk processing |
| **Heap Size** | 6 MB per Apex transaction | Stream processing, avoid large collections in memory |
| **API Calls** | 15,000 per 24-hour period for synchronous calls | Batch operations, cache results, async where possible |
| **Batch Apex** | 2,000,000 rows per batch | Process in smaller batches, use future methods |

### Gearset-Specific Considerations

- **Comparison operations** count against SOQL/query limits in source/target orgs
- **Deployment metadata size** - Large deployments may exceed org daily API limits
- **Test execution** - Gearset runs Apex tests as part of deployment; monitor CPU time
- **Change set alternatives** - Gearset bypasses change set limits but still respects org limits

### Pre-Deployment Limit Checks

```bash
# Example: Check governor limits before deployment
sf governor list --target-url <sandbox-url>

# Key metrics to monitor:
- Apex CPU Time: Current / Limit
- Heap Size: Current / Limit  
- SOQL Queries: Current / Limit
- DML Statements: Current / Limit
- API Calls: Current / 24hr Limit
```

---

## 9. Metadata Dependency Awareness

### Core Metadata Types & Dependency Order

| Metadata Type | Depends On | Depended By | Deployment Order |
|---------------|------------|-------------|------------------|
| **Apex Classes** | - | Triggers, Flows, Validation Rules | After dependencies |
| **Apex Triggers** | Apex Classes | Flows, Apex Classes | After classes |
| **Profiles** | - | Users, Apex Classes (with "Apex Class Access") | After Apex |
| **Permission Sets** | - | Profiles, Users | After Apex |
| **Record Types** | - | Page Layouts, Flows | After dependencies |
| **Page Layouts** | Record Types | Profiles | After record types |
| **Flows** | Apex Classes, Record Types | Profiles, Permission Sets | After dependencies |
| **Objects** | - | Fields, Page Layouts, Triggers | Foundation |
| **Fields** | Objects | Page Layouts, Validation Rules | After objects |
| **Workflow Rules** | - | Escalation Rules, Apex Triggers | After dependencies |
| **Validation Rules** | - | Before Save Triggers | After dependencies |
| **Email Templates** | - | Flows, Apex Classes | After dependencies |
| **Static Resources** | - | Aura Components, Visualforce | After dependencies |

### Dependency Resolution in Gearset

- **Automatic detection** - Gearset scans and resolves metadata dependencies
- **Warning indicators** - Components with unresolvable dependencies show warnings
- **Safe deployment order** - Gearset sequences deployments to respect dependencies
- **Manual override** - For advanced users, can override dependency order (not recommended)

### Common Dependency Failure Patterns

| Pattern | Symptom | Resolution |
|---------|---------|------------|
| **Circular dependency** | Deployment fails with "maximum deployment depth exceeded" | Reorder components, remove circular dependency |
| **Missing dependency** | Component fails to deploy, "dependent component not found" | Deploy dependencies first, use "Add All" intelligently |
| **Version mismatch** | "Incompatible version" errors | Ensure compatible API versions, update metadata |
| **Permission dependency** | "User does not have access" | Grant profile/permission set access, check FLS |

### Pre-Deployment Dependency Checklist

- [ ] All Apex Classes deployed before Triggers
- [ ] All Objects deployed before Fields
- [ ] All Record Types deployed before Page Layouts
- [ ] All Profiles deployed after Apex Classes/Triggers
- [ ] All Permission Sets deployed after relevant Apex
- [ ] Flows deployed after Apex Classes and Record Types
- [ ] Validation Rules deployed after dependent objects
- [ ] Email Templates deployed after Flows/Apex using them

### Post-Departure Dependency Verification

- [ ] Verify all Apex classes are accessible in target org
- [ ] Check trigger coverage percentages
- [ ] Validate profile permissions are correct
- [ ] Confirm record types and page layouts deployed correctly
- [ ] Test Flows in target org environment
- [ ] Validate object-field relationships intact

---

## Appendices

### A. Gearset Shortcut Keys

| Key | Action |
|-----|--------|
| `Ctrl + N` | New comparison |
| `Ctrl + D` | New deployment |
| `Ctrl + B` | Create manual backup |
| `Ctrl + R` | Restore from backup |
| `F5` | Refresh comparison |
| `Esc` | Close current view |

### B. Typical Deployment Timings

| Deployment Scope | Estimated Time | Factors |
|------------------|----------------|---------|
| **Small** (profiles, permission sets, few classes) | 2-5 minutes | Component count, test execution |
| **Medium** (flows, record types, multiple objects) | 5-15 minutes | Test coverage, dependency resolution |
| **Large** (full sandbox refresh, production release) | 15-45 minutes | Test execution, API limits, dependency chain |

### C. Integration Points

| Integration | Description |
|-------------|-------------|
| **GitHub Actions** | Trigger Gearset deployments from PR merges |
| **Azure DevOps** | Multi-stage pipelines with Gearset deployment |
| **Slack** | Deployment failure notifications |
| **Email** | Daily backup summaries, deployment reports |
| **Salesforce CLI** | sf CLI commands complementary to Gearset UI |

---

**Document generated:** 2026-11-14  
**Worktree:** salesforceagain-v3  
**Next review:** 2026-12-14 or after significant Gearset UI changes