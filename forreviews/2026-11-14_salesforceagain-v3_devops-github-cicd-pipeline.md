# Salesforce DevOps GitHub CI/CD Pipeline Best Practices

> **Version:** 1.0
> **Date:** 2026-11-14
> **Worktree:** salesforceagain-v3
> **Objective:** Document GitHub + Salesforce CI/CD pipeline patterns for Salesforce DevOps Engineer role

## Table of Contents

1. [Overview](#overview)
2. [GitHub Actions Pipeline Architecture](#github-actions-pipeline-architecture)
3. [Branch Strategy & Environment Mapping](#branch-strategy--environment-mapping)
4. [Pipeline Stages & Gates](#pipeline-stages--gates)
5. [Salesforce CLI Integration](#salesforce-cli-integration)
6. [Gearset Integration](#gearset-integration)
7. [Testing Strategy](#testing-strategy)
8. [Approval Gates & Compliance](#approval-gates--compliance)
9. [Rollback Strategy](#rollback-strategy)
10. [Pipeline Monitoring & Alerts](#pipeline-monitoring--alerts)
11. [Complete YAML Examples](#complete-yaml-examples)

---

## 1. Overview

A modern Salesforce CI/CD pipeline combines Git version control with automated deployment to Salesforce environments. Key components:

- **GitHub** as version control and CI orchestration
- **Salesforce CLI (sf)** for org operations
- **Gearset** for metadata-aware deployments
- **Sandbox strategy** with multiple environment tiers
- **Approval gates** at production transitions
- **Automated testing** at every stage
- **Rollback capability** for failed deployments

---

## 2. GitHub Actions Pipeline Architecture

### Recommended Pipeline Structure

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌──────────┐
│   PR    │───▶│  Build  │───▶│  Test   │───▶│ Validate│───▶│  Deploy  │
│  Open   │    │  Check  │    │  Apex   │    │  Deploy │    │  Staging │
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └──────────┘
                                                                   │
                                                                   ▼
                                                         ┌──────────────┐
                                                         │   Prod-    │
                                                         │   Approval │───▶│ Production│
                                                         │   Gate     │    │  Deploy   │
                                                         └──────────────┘
```

### Reusable Pipeline Patterns

Pattern 1: **Simple Branch-based** - Feature branches → Sandbox → Production
Pattern 2: **Environment-based** - Dev → QA → UAT → Production with manual gates
Pattern 3: **GitOps** - Git commits trigger automatic deployments to mapped orgs

### Workflow File Structure

```
.github/workflows/
├── ci-pr.yml              # Pull request validation
├── ci-dev-deploy.yml      # Deploy to dev sandbox on push
├── ci-qa-deploy.yml       # Deploy to QA sandbox after QA gate
├── ci-prod-deploy.yml     # Deploy to production after approval
├── ci-backup.yml          # Daily backup of production
└── ci-nightly-tests.yml   # Nightly test suite execution
```

---

## 3. Branch Strategy & Environment Mapping

### Branch-to-Environment Mapping

| Branch Pattern | Target Environment | Auto-Deploy | Approval Required |
|----------------|--------------------|-------------|-------------------|
| `main` | Production | No | Yes (security + lead) |
| `develop` | Integration Sandbox | Yes | No |
| `release/*` | Staging/UAT Sandbox | Yes | No |
| `feature/*` | Dev Sandbox | Yes | No |
| `hotfix/*` | Production | Yes | Yes (expedited) |

### Branch Naming Conventions

| Type | Pattern | Example |
|------|---------|---------|
| Feature | `feature/TICKET-NAME` | `feature/SCOT-123-profile-update` |
| Bugfix | `bugfix/TICKET-NAME` | `bugfix/SCOT-456-validation-rule` |
| Release | `release/VERSION` | `release/2026-Q4-1` |
| Hotfix | `hotfix/TICKET-NAME` | `hotfix/SCOT-789-security-patch` |
| Support | `support/TICKET-NAME` | `support/SCOT-001-user-access` |

---

## 4. Pipeline Stages & Gates

### Stage Definitions

| Stage | Purpose | Success Criteria |
|-------|---------|------------------|
| **PR Build** | Validate PR changes compile | All Apex classes parse without errors |
| **Test** | Run Apex tests | 75%+ overall code coverage, all tests pass |
| **Validate** | Metadata validation | No deployment errors, dependencies resolved |
| **Deploy Staging** | Deploy to staging sandbox | All metadata deployed, smoke tests pass |
| **Prod Approval** | Manual approval gate | Security review + team lead sign-off |
| **Deploy Prod** | Deploy to production | Deployment succeeds, post-deploy checks pass |

### Approval Gate Requirements

For production deployments:
- **Security Review**: Confirm no security-sensitive metadata changes without review
- **Change Advisory Board (CAB)**: For regulated environments (banking/financial)
- **Team Lead Sign-off**: Technical review of changes
- **Business Stakeholder**: Confirm business requirements met
- **Rollback Plan**: Documented rollback procedure ready

---

## 5. Salesforce CLI Integration

### Required CLI Plugins

```bash
# Install Salesforce CLI
sf plugins install @salesforce/cli

# Required plugins
sf plugins install sfdx-hardis    # HardIS for complex deployments
sf plugins install sfpackager     # Package management
```

### CLI Commands in Pipeline

```bash
# Authorize dev hub
sf org login web -a devhub -r https://login.salesforce.com

# Create scratch org
sf org create scratch -f config/project-scratch-def.json -a my-scratch-org

# Push source
sf project deploy start

# Run tests
sf project deploy start --test-level RunLocalTests

# Pull source
sf project retrieve start

# Delete scratch org
sf org delete scratch -a my-scratch-org --no-prompt
```

### Environment Variables Required

| Variable | Description | Example |
|----------|-------------|---------|
| `SFDX_AUTH_URL` | Dev hub authorization URL | `5|...` |
| `SF_SANDBOX_USERNAME` | Sandbox username | `admin@company.sandbox` |
| `SF_SANDBOX_PASSWORD` | Sandbox password | `encrypted` |
| `GEARSET_API_KEY` | Gearset API key for CI/CD | `abcd1234` |
| `SALESFORCE_API_VERSION` | Salesforce API version | `61.0` |

---

## 6. Gearset Integration

### Gearset CI/CD Pipeline Steps

1. **Connection Setup**
   - Connect GitHub repository to Gearset
   - Configure Salesforce org credentials
   - Set up pipeline with environment mapping

2. **Pipeline Configuration**
   ```yaml
   # Gearset pipeline.yml example
   pipeline:
     name: "Salesforce DevOps Pipeline"
     stages:
       - name: "Development"
         org: "dev-sandbox"
         autoDeploy: true
       - name: "QA"
         org: "qa-sandbox"
         autoDeploy: false
         approvalRequired: true
       - name: "Production"
         org: "production"
         autoDeploy: false
         approvalRequired: ["security", "lead"]
   ```

3. **CI/CD Trigger**
   - Push to `main` → Production pipeline with approval
   - Push to `feature/*` → Dev sandbox auto-deploy
   - Pull Request → Validation only, no deploy

### GitHub Actions + Gearset Example

```yaml
name: Deploy to Sandbox via Gearset
on:
  push:
    branches: [feature/*]
jobs:
  gearset-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Gearset Deploy
        uses: gearset/gearset-action@v1
        with:
          api-key: ${{ secrets.GEARSET_API_KEY }}
          comparison-id: ${{ steps.compare.outputs.id }}
          target-org: dev-sandbox
```

---

## 7. Testing Strategy

### Test Levels

| Test Level | Description | When to Run |
|------------|-------------|-------------|
| **RunLocalTests** | Tests in local org only | Development, PR validation |
| **RunAllTestsInOrg** | All tests in target org | Sandbox deployment |
| **RunSpecifiedTests** | Specific test classes | Targeted validation |
| **NoTestRun** | Skip test execution | Metadata-only changes (profiles, etc.) |

### Code Coverage Requirements

- **Overall org coverage**: 75% minimum (Salesforce requirement)
- **Individual class coverage**: No minimum per class, but overall must be 75%
- **Trigger coverage**: 1% minimum per trigger
- **Production deployment**: 75% overall coverage required

### Test Pipeline Configuration

```yaml
# Example: Apex test stage in GitHub Actions
- name: Run Apex Tests
  run: |
    sf project deploy start \
      --test-level RunLocalTests \
      --target-org ${{ secrets.SF_SANDBOX_USERNAME }} \
      --json > test-results.json
    cat test-results.json | jq '.result.passed'
```

---

## 8. Approval Gates & Compliance

### Production Approval Workflow

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Dev       │───▶│   QA        │───▶│   Staging   │───▶│   Prod Gate │
│   Deploy    │    │   Deploy    │    │   Deploy    │    │   Review    │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                                                             │
                                            ┌────────────────┴────────────────┐
                                            ▼                                 ▼
                                     ┌─────────┐                       ┌─────────┐
                                     │ Approve │                       │ Reject  │
                                     └─────────┘                       └─────────┘
                                            │                                 │
                                            ▼                                 ▼
                                    ┌──────────────┐                   ┌──────────┐
                                    │ Prod Deploy  │                   │ Notify   │
                                    └──────────────┘                   │ Requestor│
                                                                       └──────────┘
```

### Required Approvers for Production

| Role | Responsibility | When Required |
|------|----------------|---------------|
| **Security Review** | Review security-sensitive changes | Always for production |
| **Team Lead** | Technical review | Always for production |
| **Business Owner** | Business requirement validation | For feature releases |
| **Change Manager** | Change advisory board | For banking/regulated environments |
| **Release Manager** | Deployment scheduling | Always for production |

### Audit Trail Requirements

- All pipeline runs logged with timestamps
- All approvals recorded with user identity
- All deployment metadata tracked (what changed, when, by whom)
- Rollback procedures documented for each deployment
- Compliance reports available on request

---

## 9. Rollback Strategy

### Rollback Triggers

| Trigger | Condition | Action |
|---------|-----------|--------|
| **Test Failure** | >25% of tests fail after deployment | Automatic rollback |
| **Deployment Error** | Deployment fails mid-process | Automatic rollback |
| **Post-Deploy Issue** | Critical bug found after deploy | Manual rollback |
| **Performance Degradation** | Org performance impacted | Manual rollback |

### Rollback Methods

1. **Gearset Rollback** - Use Gearset deployment history to revert
2. **Git Revert** - Revert git commit and redeploy previous state
3. **Backup Restore** - Restore from Gearset backup snapshot
4. **Manual Metadata Removal** - Manually remove deployed components

### Rollback Procedure

```yaml
# Rollback pipeline example
name: Rollback Production
on:
  workflow_dispatch:
    inputs:
      deployment-id:
        description: "Deployment ID to rollback"
        required: true
jobs:
  rollback:
    runs-on: ubuntu-latest
    steps:
      - name: Gearset Rollback
        uses: gearset/gearset-action@v1
        with:
          api-key: ${{ secrets.GEARSET_API_KEY }}
          action: rollback
          deployment-id: ${{ github.event.inputs.deployment-id }}
```

---

## 10. Pipeline Monitoring & Alerts

### Alert Channels

| Channel | Purpose | Recipients |
|---------|---------|------------|
| **Slack #deployments** | Deployment status updates | DevOps team |
| **Slack #alerts** | Failure notifications | On-call engineer |
| **Email** | Daily backup summaries | Management |
| **PagerDuty** | Critical production failures | On-call rotation |

### Key Metrics to Monitor

- **Deployment success rate** (target: >95%)
- **Mean time to recovery** (target: <30 minutes)
- **Deployment frequency** (target: daily for dev, weekly for prod)
- **Change failure rate** (target: <15%)
- **Pipeline duration** (target: <15 minutes for PR validation)

### Alert Rules

| Condition | Severity | Notification |
|-----------|----------|--------------|
| Production deployment fails | Critical | PagerDuty + Slack + Email |
| Test coverage drops below 75% | Warning | Slack #deployments |
| Backup fails | Warning | Slack #alerts |
| Pipeline runs >30 minutes | Info | Slack #deployments |
| Unauthorized production change | Critical | PagerDuty + Security team |

---

## 11. Complete YAML Examples

### Example 1: PR Validation Pipeline

```yaml
name: CI - PR Validation
on:
  pull_request:
    branches: [main, develop]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Salesforce CLI
        run: npm install @salesforce/cli
      - name: Authorize Dev Hub
        run: sf org login web -a devhub -r https://login.salesforce.com
        env:
          SFDX_AUTH_URL: ${{ secrets.SFDX_AUTH_URL }}
      - name: Deploy and Run Tests
        run: |
          sf project deploy start \
            --target-org devhub \
            --test-level RunLocalTests \
            --json
```

### Example 2: Production Deployment with Approval

```yaml
name: CD - Production Deploy
on:
  workflow_dispatch:
    inputs:
      environment:
        description: "Target environment"
        required: true
        default: "production"

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4
      - name: Authorize Production Org
        run: sf org login web -a prod -r https://login.salesforce.com
        env:
          SFDX_AUTH_URL: ${{ secrets.PROD_AUTH_URL }}
      - name: Deploy Metadata
        run: |
          sf project deploy start \
            --target-org prod \
            --test-level RunAllTestsInOrg \
            --json
```

---

## Appendices

### A. GitHub Secrets Required

| Secret Name | Description | Where to Set |
|-------------|-------------|--------------|
| `SFDX_AUTH_URL` | Dev hub auth URL | Repository Settings > Secrets |
| `PROD_AUTH_URL` | Production org auth URL | Repository Settings > Secrets |
| `GEARSET_API_KEY` | Gearset API key | Repository Settings > Secrets |
| `SLACK_WEBHOOK_URL` | Slack notifications webhook | Repository Settings > Secrets |
| `PAGERDUTY_KEY` | PagerDuty integration key | Repository Settings > Secrets |

### B. Required GitHub Environments

| Environment | Protection Rules | Required Reviewers |
|-------------|------------------|--------------------|
| `staging` | None | None |
| `production` | Required reviewers | Security, Team Lead |
| `production-hotfix` | Required reviewers + wait timer | Security, Team Lead, Change Manager |

### C. Pipeline Troubleshooting

| Issue | Cause | Resolution |
|-------|-------|------------|
| Auth failed | Expired auth URL | Regenerate auth URL in Salesforce |
| Test coverage <75% | Insufficient tests | Add test classes, increase coverage |
| Deployment error | Missing dependencies | Deploy dependencies first |
| Pipeline timeout | Large deployment | Break into smaller deployments |
| Gearset API error | Invalid API key | Regenerate Gearset API key |

---

**Document generated:** 2026-11-14  
**Worktree:** salesforceagain-v3  
**Next review:** 2026-12-14